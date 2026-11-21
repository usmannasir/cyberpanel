"""Pairing on a real MariaDB, from the code to an active link, and every way it has to fail.

A managed server and a controller share this process: a local TLS server hands
each request it receives to pairing.node_receive, and the controller's half
connects to it over 127.0.0.1 through the transport's allowance for tests.

Runs only as root on a server marked as a disposable test server (see
multiServer/testing.py) and is skipped everywhere else. Each class works in a
database of its own that is dropped afterwards.
"""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
import shutil
import socket
import ssl
import sys
import tempfile
import threading
import unittest
from unittest import mock

from multiServer import (addresses, crypto, entitlement, keys, pairing, schema, test_pairing, test_transport, testing,
                         transport)
from multiServer.test_pairing import GENERIC, Loopback, Server, texts_of
from multiServer.test_transport import CERTIFICATES, pin, read_request, wire

SKIP = testing.unavailable()
if SKIP is None:
    testing.start_django()
    from django.core.handlers.wsgi import WSGIRequest
    from django.db import connection
    from multiServer import test_database
    Base = test_database.DjangoDatabase
else:
    Base = unittest.TestCase

NOW = 1795000000
ADMIN = 1
GENERATION = 7
SIDE = threading.local()  # which of the two servers the running thread is
THE_LINK = object()
REFUSED = ('The server did not accept the pairing code. A code can be used once, for ten minutes, from the '
           'controller address it was made for.')
OTHER_CERTIFICATE = ('The server at that address did not present the certificate the pairing code names. Nothing was '
                     'sent to it.')


def setUpModule():
    test_transport.setUpModule()


def tearDownModule():
    test_transport.tearDownModule()


@contextlib.contextmanager
def on_the_node():
    """What follows is done on the managed server; everything else in a test is done on the controller."""
    SIDE.role = keys.NODE
    try:
        yield
    finally:
        del SIDE.role


def request_of(seen, peer, port):
    """The request a web server would hand to the panel for what arrived on the socket."""
    environ = {'REQUEST_METHOD': seen.method, 'SCRIPT_NAME': '', 'PATH_INFO': seen.path, 'QUERY_STRING': seen.query,
               'SERVER_NAME': '127.0.0.1', 'SERVER_PORT': str(port), 'SERVER_PROTOCOL': seen.version,
               'REMOTE_ADDR': peer, 'wsgi.url_scheme': 'https', 'wsgi.input': io.BytesIO(seen.body),
               'wsgi.errors': sys.stderr, 'wsgi.multithread': True, 'wsgi.multiprocess': False}
    for name, value in seen.headers:
        name = name.upper().replace('-', '_')
        name = name if name in ('CONTENT_TYPE', 'CONTENT_LENGTH') else 'HTTP_' + name
        environ[name] = environ[name] + ',' + value if name in environ else value
    return WSGIRequest(environ)


def hand_over(node, connection_, seen):
    """The managed server: whatever arrives goes to pairing.node_receive and its answer goes back as it is."""
    SIDE.role = node.role
    try:
        # `reports` is how this web server writes the address of a connection; as it is, unless a test says otherwise.
        peer = getattr(node, 'reports', str)(connection_.getpeername()[0])
        response = pairing.node_receive(request_of(seen, peer, node.port))
        node.replies.append(response)
        headers = list(response.items()) + [('Set-Cookie', cookie.output(header='').strip())
                                            for cookie in response.cookies.values()]
        connection_.sendall(wire(response.status_code, response.reason_phrase, headers) + response.content)
    finally:
        connection.close()


def post(port, body, signature, source='127.0.0.1', host=None, headers=(), method='POST', path=pairing.PATH,
         content_type='text/plain'):
    """Send one request as anybody on the network could, and return everything that comes back."""
    lines = ['%s %s HTTP/1.1' % (method, path), 'Host: ' + (host or '127.0.0.1:%d' % port), 'Connection: close']
    if content_type is not None:
        lines.append('Content-Type: ' + content_type)
    lines.append('Content-Length: %d' % len(body))
    if signature is not None:
        lines.append('X-CPMS-Signature: ' + signature)
    lines.extend('%s: %s' % header for header in headers)
    plain = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    plain.settimeout(10)
    plain.bind((source, 0))
    plain.connect(('127.0.0.1', port))
    secured = transport._tls_context().wrap_socket(plain)
    try:
        secured.sendall(('\r\n'.join(lines) + '\r\n\r\n').encode('latin-1') + body)
        received = b''
        while True:
            chunk = secured.recv(65536)
            if not chunk:
                return received
            received += chunk
    finally:
        secured.close()


class EarlyGateway(object):
    """Stands where the gateway will stand: first in the panel's chain, before a session exists."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path != pairing.PATH:
            return self.get_response(request)
        with on_the_node():
            return pairing.node_receive(request)


class Attempt(object):
    """One pairing request as a controller makes it, open to being changed before or after it is signed."""

    def __init__(self, code, sign_with=None, **changes):
        endpoint, node_id, seed = pairing._decode(code)
        self.private_key = crypto.generate_private_key()
        self.fields = dict(link_id=os.urandom(16).hex(), pairing_key=crypto.public_key(seed).hex(),
                           controller_key=crypto.public_key(self.private_key).hex(), node_id=node_id,
                           tls_fingerprint=endpoint.tls_pin, host=endpoint.authority, timestamp=pairing._now(),
                           nonce=os.urandom(16).hex())
        self.fields.update(changes)
        self.link_id = self.fields['link_id']
        self.signature = crypto.sign(sign_with or seed, crypto.pair_request_message(**self.fields)).hex()

    def body(self, **changes):
        fields = dict(self.fields, **changes)
        return '\n'.join((fields['link_id'], fields['pairing_key'], fields['controller_key'],
                          str(fields['timestamp']), fields['nonce'])).encode('ascii')


class Relay(object):
    """A machine in the middle: it ends TLS with a certificate of its own and passes on what it is sent."""

    def __init__(self, target, change=None):
        self.target, self.change, self.received, self.handshakes, self.closed = target, change, [], 0, False
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(CERTIFICATES['impostor'][0])
        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.bind(('127.0.0.1', 0))
        self.listener.listen(8)
        self.listener.settimeout(0.05)
        self.port = self.listener.getsockname()[1]
        self.done = threading.Event()
        Server._start(self._accept)

    def close(self):
        self.closed = True
        self.listener.close()

    def _accept(self):
        while not self.closed:
            try:
                accepted = self.listener.accept()[0]
            except socket.timeout:
                continue
            except OSError:
                return
            Server._start(self._serve, accepted)

    def _serve(self, accepted):
        try:
            accepted.settimeout(10)
            secured = self.context.wrap_socket(accepted, server_side=True)
            self.handshakes += 1
            raw, seen = read_request(secured)
            self.received.append(raw)
            if seen is not None:
                head, _, body = raw.partition(b'\r\n\r\n')
                signature = dict((name.lower(), value) for name, value in seen.headers)['x-cpms-signature']
                passed_on = post(self.target, self.change(body) if self.change else body, signature,
                                 host=dict(seen.headers)['Host'])
                secured.sendall(passed_on)
            secured.close()
        except (OSError, ValueError):
            accepted.close()
        finally:
            self.done.set()


@unittest.skipIf(SKIP, SKIP)
class Servers(Base):
    """A managed server and a licensed controller, in one process and one database."""

    def setUp(self):
        super().setUp()
        from plogical import softUpgrade
        self.clock, self.secrets, self.stored, self.nodes = [NOW], [], [], []
        self.identity = [crypto.generate_private_key()]
        self.generation = [GENERATION]
        self.node_key = crypto.public_key(self.identity[0])
        self.secrets.append(self.identity[0].hex())
        self.panel = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(self.panel))
        self.panel.joinpath('cert.pem').write_bytes(Path(CERTIFICATES['node'][0]).read_bytes())
        self.panel.joinpath('bind.conf').write_text('')
        self.administrator = mock.MagicMock(state='ACTIVE', userName='admin', securityLevel=1)
        self.patch(keys, 'role', side_effect=lambda: getattr(SIDE, 'role', keys.CONTROLLER))
        self.patch(keys, 'identity_key', side_effect=lambda: self.identity[0])
        self.patch(keys, 'generation', side_effect=lambda: self.generation[0])
        self.patch(pairing, '_now', side_effect=lambda: self.clock[0])
        self.patch(softUpgrade, 'PANEL_CONF', self.panel)
        self.patch(transport, 'Endpoint', Loopback)
        self.licensed = self.patch(entitlement, 'allowed', return_value=True)
        self.find = self.start(mock.patch('loginSystem.models.Administrator.objects.get',
                                          return_value=self.administrator))
        self.acl = self.start(mock.patch('plogical.acl.ACLManager.loadedACL', return_value={'admin': 1}))
        self.node = self.server()

    def tearDown(self):
        self.nothing_secret()

    def nothing_secret(self):
        """Whatever a test did, nothing secret was written down or said."""
        written = repr([self.database.run('SELECT * FROM `%s`' % name) for name in test_database.NAMES])
        said = b''.join(wire(response.status_code, response.reason_phrase, list(response.items())) + response.content
                        for node in self.nodes for response in node.replies).decode('latin-1')
        for secret in self.secrets:
            self.assertNotIn(secret, written)
            self.assertNotIn(secret, said)

    def again(self):
        """Empty tables for the next round of one test."""
        self.nothing_secret()
        for name in reversed(test_database.NAMES):
            self.database.run('DELETE FROM `%s`' % name)
        self.stored[:] = []

    def start(self, patcher):
        self.addCleanup(patcher.stop)
        return patcher.start()

    def patch(self, target, name, *arguments, **options):
        return self.start(mock.patch.object(target, name, *arguments, **options))

    def server(self, answer=hand_over, **options):
        node = Server(answer, **options)
        node.replies, node.role = [], keys.NODE
        self.addCleanup(node.close)
        self.nodes.append(node)
        return node

    def store(self, *arguments):
        self.secrets.append(arguments[5].hex())
        self.stored.append(arguments)

    def issue(self, controller_ip='127.0.0.1', admin_id=ADMIN, **options):
        with on_the_node():
            code = pairing.issue_code(admin_id, controller_ip, **dict(dict(host='127.0.0.1', port=self.node.port),
                                                                      **options))
        seed = pairing._decode(code)[2]
        self.secrets += [code, seed.hex(), base64.b64encode(seed).decode(),
                         base64.b32encode(seed).decode().rstrip('=')]
        return code

    def attempt(self, code, **changes):
        made = Attempt(code, **changes)
        self.secrets += [made.signature, made.private_key.hex()]
        return made

    def send(self, attempt, body=None, signature=None, **options):
        return post(self.node.port, attempt.body() if body is None else body,
                    attempt.signature if signature is None else signature, **options)

    def pair(self, code):
        return pairing.start(code, 'Frankfurt 1', 'admin', self.store)

    def not_paired(self, code, reason='signature', because=REFUSED):
        with self.assertRaises(pairing.PairingError) as caught:
            self.pair(code)
        self.assertEqual((reason, because), (caught.exception.reason, str(caught.exception)))
        self.assertEqual([], self.stored)
        for secret in self.secrets:
            self.assertNotIn(secret, texts_of(caught.exception))
        return caught.exception

    def audited(self, side=None):
        """(event, outcome, reason, link id, actor, source address, status) of every audit row, oldest first."""
        rows = self.database.run('SELECT event, outcome, reason, link_id, actor, source_ip, status, dropped '
                                 'FROM ms_audit ORDER BY id')
        self.assertEqual(set(), set(row[7] for row in rows) - {0}, 'nothing was left out of a row')
        return [row[:7] for row in rows]

    def links(self):
        return self.database.run('SELECT link_id, controller_key, pairing_key, allowed_ips, admin_id, status, '
                                 'generation, created_at, updated_at, activated_at, expires_at, last_request_at '
                                 'FROM ms_links ORDER BY created_at, link_id')

    def codes(self):
        return self.database.run('SELECT failures, consumed FROM ms_pairing_codes ORDER BY created_at, public_key')

    def refused(self, reply, reason, source='127.0.0.1', link_id='', outcome='refused', failures=0, consumed=0):
        """The one answer for every refusal, its exact reason on record, no link, and the code as stated."""
        self.assertEqual(GENERIC, reply)
        self.assertEqual(('pairing', outcome, reason, link_id, '', source, 403), self.audited()[-1])
        self.assertEqual((), self.links())
        self.assertEqual(((failures, consumed),), self.codes())


class PairingTests(Servers):
    def test_a_correct_pairing_makes_one_pending_link_and_approval_makes_it_active(self):
        code = self.issue()
        self.assertEqual(205, len(code))
        self.assertEqual(('127.0.0.1', self.node.port, crypto.node_id(self.node_key), pin('node')),
                         tuple(pairing.read_code(code)))
        self.assertEqual(((0, 0),), self.codes())
        paired = self.pair(code)
        (label, link_id, host, port, node_key, private_key, tls_pin), = self.stored
        self.assertEqual(('Frankfurt 1', paired.link_id, '127.0.0.1', self.node.port, self.node_key, pin('node')),
                         (label, link_id, host, port, node_key, tls_pin))
        self.assertEqual((crypto.node_id(self.node_key), '127.0.0.1', self.node.port),
                         (paired.node_id, paired.host, paired.port))
        # The same keys on both sides: the server holds the public half of the key the controller kept.
        controller_key = crypto.public_key(private_key).hex()
        pairing_key = crypto.public_key(pairing._decode(code)[2]).hex()
        self.assertEqual(((link_id, controller_key, pairing_key, '127.0.0.1', ADMIN, 'pending', GENERATION, NOW, NOW,
                           None, NOW + 600, 0),), self.links())
        self.assertEqual(((0, 1),), self.codes())
        transport.Link(link_id, paired.node_id, host, port, node_key, private_key, tls_pin,
                       allow_loopback_for_tests=True)
        # The same number on both sides.
        with on_the_node():
            self.assertEqual([pairing.Pending(link_id, '127.0.0.1', ADMIN, NOW, NOW + 600, paired.confirmation)],
                             pairing.pending())
        self.assertRegex(paired.confirmation, '^[0-9]{8}$')
        self.clock[0] = NOW + 599
        with on_the_node():
            self.assertIsNone(pairing.approve(link_id, ADMIN))
            self.assertEqual([], pairing.pending())
        self.assertEqual(((link_id, controller_key, pairing_key, '127.0.0.1', ADMIN, 'active', GENERATION, NOW,
                           NOW + 599, NOW + 599, NOW + 599 + 90 * 24 * 60 * 60, 0),), self.links())
        self.assertEqual([('pairing_code', 'ok', '', '', 'admin', '127.0.0.1', None),
                          ('pairing', 'ok', '', link_id, '', '127.0.0.1', 200),
                          ('pairing', 'ok', '', link_id, 'admin', '', None),
                          ('link_approve', 'ok', '', link_id, 'admin', '', None)], self.audited())

    def test_the_managed_server_keeps_the_public_half_of_a_code_and_nothing_else(self):
        code = self.issue('2A01:04F8:0:0:0:0:0:9')
        seed = pairing._decode(code)[2]
        self.assertEqual(((crypto.public_key(seed).hex(), '2a01:4f8::9', ADMIN, NOW, NOW + 600, 0, 0),),
                         self.database.run('SELECT * FROM ms_pairing_codes'))
        self.assertEqual([('pairing_code', 'ok', '', '', 'admin', '2a01:4f8::9', None)], self.audited())
        self.assertEqual((), self.links())
        self.assertNotEqual(code, self.issue('2a01:4f8::9'))
        self.assertEqual(2, len(self.codes()))

    def test_the_answers_are_one_whole_reply_without_a_cookie_a_redirect_or_a_cache(self):
        code = self.issue()
        attempt = self.attempt(code)
        accepted = self.send(attempt, headers=[('Cookie', 'sessionid=abc; csrftoken=def'),
                                               ('Authorization', 'Basic YWRtaW46cGFzc3dvcmQ=')])
        head, _, body = accepted.partition(b'\r\n\r\n')
        lines = head.decode('ascii').split('\r\n')
        self.assertEqual(self.node_key.hex().encode(), body)
        self.assertEqual(['HTTP/1.1 200 OK', 'Content-Type: text/plain', 'Content-Length: 64',
                          'Cache-Control: no-store'], lines[:2] + lines[3:])
        self.assertRegex(lines[2], '^X-CPMS-Signature: [0-9a-f]{128}$')
        signed = crypto.pair_response_message(crypto.pair_request_message(**attempt.fields), self.node_key.hex())
        self.assertTrue(crypto.verify(self.node_key, bytes.fromhex(lines[2].split(': ')[1]), signed))
        refused = self.send(self.attempt(code))
        self.assertEqual(GENERIC, refused)
        for response in self.node.replies:
            self.assertEqual({}, dict(response.cookies))
            self.assertEqual(1, [name.lower() for name, value in response.items()].count('content-length'))
            self.assertFalse(response.has_header('Location') or response.has_header('Set-Cookie')
                             or response.has_header('Vary') or response.has_header('X-CPMS-Link'))
        self.assertEqual([200, 403], [response.status_code for response in self.node.replies])

    def test_over_ipv6_both_servers_are_named_by_their_one_spelling(self):
        try:
            node = self.server(address='::1')
        except OSError:
            self.skipTest('no IPv6 loopback on this machine')
        code = self.issue('0:0:0:0:0:0:0:1', host='::1', port=node.port)
        self.assertEqual(('::1', node.port), tuple(pairing.read_code(code))[:2])
        paired = self.pair(code)
        self.assertEqual(('::1', [(paired.link_id, '::1')]),
                         (paired.host, [(link[0], link[3]) for link in self.links()]))
        self.assertEqual(('pairing', 'ok', '', paired.link_id, '', '::1', 200), self.audited()[-2])
        self.assertEqual(b'[::1]:%d' % node.port, node.finished()['seen'].headers[0][1].encode())
        # The same server reached over IPv4 is not the address the code was made for.
        other = self.issue('::1')
        self.stored[:] = []
        self.not_paired(other)
        self.assertEqual(('pairing', 'refused', 'source_ip', '', '', '127.0.0.1', 403), self.audited()[-2])

    def test_called_first_in_the_panels_chain_it_needs_no_session_and_its_answer_leaves_as_it_is(self):
        from django.conf import settings
        from django.test import Client, override_settings
        attempt = self.attempt(self.issue())
        sent = dict(content_type='text/plain', HTTP_HOST=attempt.fields['host'],
                    HTTP_X_CPMS_SIGNATURE=attempt.signature, HTTP_X_FORWARDED_FOR='203.0.113.9')
        chain = ['multiServer.test_pairing_database.EarlyGateway'] + list(settings.MIDDLEWARE)
        # As in test_wiring: sessions in a signed cookie, so the panel behind the gateway needs no table here.
        with override_settings(MIDDLEWARE=chain, SESSION_ENGINE='django.contrib.sessions.backends.signed_cookies'):
            client = Client()
            client.cookies['sessionid'] = 'abc'
            refused = client.post(pairing.PATH, data=attempt.body(nonce='c4' * 16), **sent)
            accepted = client.post(pairing.PATH, data=attempt.body(), **sent)
            elsewhere = client.post('/multiserver/pairs', data=attempt.body(), **sent)
        self.assertEqual((403, b'', [('Content-Type', 'text/plain'), ('Content-Length', '0'),
                                     ('Cache-Control', 'no-store')]),
                         (refused.status_code, refused.content, list(refused.items())))
        self.assertEqual((200, self.node_key.hex().encode(), ['Content-Type', 'X-CPMS-Signature', 'Content-Length',
                                                              'Cache-Control']),
                         (accepted.status_code, accepted.content, [name for name, value in accepted.items()]))
        for response in (refused, accepted):
            self.assertEqual({}, dict(response.cookies))
            self.assertFalse(hasattr(response.wsgi_request, 'session'), 'no session was ever opened')
        # Any other address goes on into the panel, which asks for a session as it always does.
        self.assertIn(b'This request need session', elsewhere.content)
        self.assertEqual([attempt.link_id], [link[0] for link in self.links()])
        self.assertEqual([('pairing', 'refused', 'signature', '', '', '127.0.0.1', 403),
                          ('pairing', 'ok', '', attempt.link_id, '', '127.0.0.1', 200)], self.audited()[-2:])

    def test_the_panels_request_scanner_lets_a_pasted_code_through(self):
        from CyberCP.secMiddleware import secMiddleware
        from django.http import HttpResponse
        from django.test import RequestFactory
        reached = []

        def view(request):
            reached.append(json.loads(request.body) if request.content_type.endswith('json') else request.POST.dict())
            return HttpResponse('reached')

        def through(data, content_type='application/json'):
            request = RequestFactory().post('/multiserver/pairing', data=data, content_type=content_type)
            request.session = {'userID': ADMIN, 'ipAddr': '127.0.0.1'}
            return secMiddleware(view)(request).content
        for code in (self.issue(), self.issue(host='2a01:4f8::1'), self.issue(host='node-1.example.com')):
            self.assertEqual(b'reached', through(json.dumps({'code': code, 'label': 'Frankfurt 1'})))
            self.assertEqual(b'reached',
                             through('code=%s&label=Frankfurt' % code, 'application/x-www-form-urlencoded'))
            self.assertEqual([code, code], [seen['code'] for seen in reached[-2:]])
        self.assertEqual([205, 226, 231], [len(seen['code']) for seen in reached[::2]])
        # The scanner is at work on this address: what it refuses does not arrive.
        for refused in test_pairing.SCANNER_REFUSES:
            self.assertIn(b'not accepted', through(json.dumps({'code': 'CPMS1-PAIR-A' + refused + 'B'})), refused)
        self.assertEqual(6, len(reached))

    def test_a_forwarding_header_neither_admits_nor_refuses_anybody(self):
        code = self.issue()
        forged = [('X-Forwarded-For', '127.0.0.1'), ('X-Real-IP', '127.0.0.1'), ('Forwarded', 'for=127.0.0.1'),
                  ('Client-IP', '127.0.0.1'), ('True-Client-IP', '127.0.0.1'), ('CF-Connecting-IP', '127.0.0.1'),
                  ('X-Client-IP', '127.0.0.1'), ('X-Cluster-Client-IP', '127.0.0.1')]
        self.refused(self.send(self.attempt(code), source='127.0.0.2'), 'source_ip', source='127.0.0.2', failures=1)
        self.refused(self.send(self.attempt(code), source='127.0.0.2', headers=forged), 'source_ip',
                     source='127.0.0.2', failures=2)
        attempt = self.attempt(code)
        elsewhere = [(name, value.replace('127.0.0.1', '203.0.113.9')) for name, value in forged]
        self.assertTrue(self.send(attempt, headers=elsewhere).startswith(b'HTTP/1.1 200 OK\r\n'))
        self.assertEqual([attempt.link_id], [link[0] for link in self.links()])
        self.assertEqual(('pairing', 'ok', '', attempt.link_id, '', '127.0.0.1', 200), self.audited()[-1])


class AddressTests(Servers):
    """The controller is named and recognised by the one rule of multiServer/addresses.py."""

    def test_a_server_that_reports_ipv4_as_ipv6_recognises_the_controller_it_wrote_down(self):
        # A web server listening on both families reports the caller 127.0.0.1 as ::ffff:127.0.0.1.
        self.node.reports = lambda address: '::ffff:' + address
        code = self.issue('127.0.0.1')
        paired = self.pair(code)
        self.assertEqual([(paired.link_id, '127.0.0.1')], [(link[0], link[3]) for link in self.links()])
        self.assertEqual(('pairing', 'ok', '', paired.link_id, '', '127.0.0.1', 200), self.audited()[-2])
        # And refuses everybody else, whatever the spelling, each counted against the code.
        other = self.issue('127.0.0.1')
        self.node.reports = lambda address: '::FFFF:7f00:2'
        self.assertEqual(GENERIC, self.send(self.attempt(other)))
        self.assertEqual(('pairing', 'refused', 'source_ip', '', '', '127.0.0.2', 403), self.audited()[-1])
        self.node.reports = lambda address: '127.0.0.01'
        self.assertEqual(GENERIC, self.send(self.attempt(other)))
        self.assertEqual(('pairing', 'refused', 'source_ip', '', '', '', 403), self.audited()[-1])
        self.assertEqual([(0, 1), (2, 0)], sorted(self.codes()))

    def test_the_link_allows_the_one_address_of_the_code_in_the_form_the_gateway_reads(self):
        for written, kept in (('127.0.0.1', '127.0.0.1'), ('0:0:0:0:0:0:0:1', '::1')):
            self.again()
            try:
                node = self.server(address=kept)
            except OSError:
                self.skipTest('no IPv6 loopback on this machine')
            paired = self.pair(self.issue(written, host=kept, port=node.port))
            (link_id, allowed), = [(link[0], link[3]) for link in self.links()]
            self.assertEqual((paired.link_id, kept), (link_id, allowed))
            self.assertEqual((kept,), addresses.listed(allowed))
            self.assertTrue(addresses.allows(allowed, kept))

    def test_a_code_whose_address_is_not_one_address_in_its_one_spelling_admits_nobody(self):
        # Nothing but issue_code writes that column; if something else did, the request is refused, not guessed at.
        for kept in ('127.0.0.1,127.0.0.2', '127.0.0.1,127.0.0.1', '::ffff:127.0.0.1', '127.0.0.01', '127.0.0.0/8',
                     ' 127.0.0.1', '127.0.0.1 ', '*', ''):
            self.again()
            code = self.issue('127.0.0.1')
            self.database.run("UPDATE ms_pairing_codes SET controller_ip = '%s'" % kept)
            self.refused(self.send(self.attempt(code)), 'source_ip', failures=1)

    def test_both_sides_of_the_comparison_go_through_the_one_rule(self):
        code = self.issue('127.0.0.1')
        with mock.patch.object(addresses, 'peer', return_value='203.0.113.9') as peer:
            self.refused(self.send(self.attempt(code)), 'source_ip', source='203.0.113.9', failures=1)
        peer.assert_called_once_with('127.0.0.1')
        with mock.patch.object(addresses, 'listed', return_value=('203.0.113.9',)) as listed:
            self.refused(self.send(self.attempt(code)), 'source_ip', failures=2)
        listed.assert_called_once_with('127.0.0.1')
        with mock.patch.object(addresses, 'entry', return_value=None) as entry, on_the_node(), \
                self.assertRaises(pairing.PairingError):
            pairing.issue_code(ADMIN, '127.0.0.1', host='127.0.0.1', port=self.node.port)
        entry.assert_called_once_with('127.0.0.1')


class LinkRowTests(Servers):
    """What pairing writes is the row the gateway reads (multiServer/nodeGateway.py)."""

    def test_an_approved_link_is_one_the_gateway_carries_requests_on_and_a_pending_one_is_not(self):
        from multiServer import models, nodeGateway
        default = models.Link._meta.get_field('last_request_at')
        # Whatever the column would hold by itself, pairing says that no request was accepted yet.
        with mock.patch.object(default, 'default', NOW - 5):
            paired = self.pair(self.issue())
        link = models.Link.objects.get(pk=paired.link_id)
        self.assertEqual((0, GENERATION, 'pending'), (link.last_request_at, link.generation, link.status))
        self.assertRegex(link.link_id, r'\A[0-9a-f]{32}\Z')
        self.assertRegex(link.controller_key, r'\A[0-9a-f]{64}\Z')
        self.assertEqual(crypto.public_key(self.stored[0][5]).hex(), link.controller_key)
        self.assertEqual(('127.0.0.1',), addresses.listed(link.allowed_ips))
        self.assertEqual('link', nodeGateway._unusable(link, GENERATION, NOW))
        with on_the_node():
            pairing.approve(paired.link_id, ADMIN)
        link = models.Link.objects.get(pk=paired.link_id)
        self.assertIsNone(nodeGateway._unusable(link, GENERATION, NOW))
        self.assertEqual('expired', nodeGateway._unusable(link, GENERATION, NOW + pairing.LINK_LIFETIME))
        self.assertEqual('generation', nodeGateway._unusable(link, GENERATION + 1, NOW))
        self.assertTrue(addresses.allows(link.allowed_ips, '127.0.0.1'))
        self.assertEqual(0, link.last_request_at)

    def test_no_link_is_made_for_a_controller_key_that_anybody_can_sign_for(self):
        code = self.issue()
        for written in ('01' + '00' * 31, '01' + '00' * 30 + '80', '00' * 32, 'ec' + 'ff' * 30 + '7f',
                        '26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05',
                        'c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac037a', '02' + '00' * 31):
            # Signed with the code's own key, from the right address, at the right time: only the key is wrong.
            self.refused(self.send(self.attempt(code, controller_key=written)), 'format')
        # The code is untouched and still makes a link for a real key.
        self.assertTrue(self.send(self.attempt(code)).startswith(b'HTTP/1.1 200 OK\r\n'))
        self.assertEqual(((0, 1),), self.codes())


class AttackTests(Servers):
    def test_a_machine_in_the_middle_with_another_certificate_is_sent_no_request_byte(self):
        code = self.issue()
        impostor = self.server(certificate='impostor')
        real = transport._open
        # Whoever controls the network sends the controller's connection to a server of its own.
        with mock.patch.object(transport, '_open', lambda address, port, deadline: real(address, impostor.port,
                                                                                         deadline)):
            self.not_paired(code, 'certificate', OTHER_CERTIFICATE)
        record = impostor.finished()
        self.assertEqual((True, b'', None), (record['tls'], record['raw'], record['seen']))
        self.assertEqual(([], []), (impostor.replies, self.node.replies))
        self.assertTrue(self.node.connections.empty())
        self.assertEqual(((), ((0, 0),)), (self.links(), self.codes()))
        self.assertEqual(('pairing', 'refused', 'certificate', '', 'admin', '', None), self.audited()[-1])
        self.assertIsInstance(self.pair(code), pairing.Paired)

    def test_a_proxy_that_ends_tls_with_its_own_certificate_is_sent_no_request_byte(self):
        code = self.issue()
        relay = Relay(self.node.port)
        self.addCleanup(relay.close)
        real = transport._open
        with mock.patch.object(transport, '_open', lambda address, port, deadline: real(address, relay.port,
                                                                                         deadline)):
            self.not_paired(code, 'certificate', OTHER_CERTIFICATE)
        self.assertTrue(relay.done.wait(5))
        # TLS was complete and the proxy was reading: it was sent nothing, and had nothing to pass on.
        self.assertEqual((1, b''), (relay.handshakes, b''.join(relay.received)))
        self.assertTrue(self.node.connections.empty())
        self.assertEqual(((), ((0, 0),)), (self.links(), self.codes()))

    def test_a_proxy_can_pass_a_request_on_but_cannot_change_a_word_of_it(self):
        # Without the pin a proxy would sit in the connection. Even then it can do nothing but pass on or lose.
        code = self.issue()
        attempt = self.attempt(code)
        own_key = crypto.public_key(crypto.generate_private_key()).hex().encode()
        changing = Relay(self.node.port,
                         lambda body: body.replace(attempt.fields['controller_key'].encode(), own_key))
        self.addCleanup(changing.close)
        self.refused(post(changing.port, attempt.body(), attempt.signature, host=attempt.fields['host']), 'signature',
                     failures=1)
        passing = Relay(self.node.port)
        self.addCleanup(passing.close)
        reply = post(passing.port, attempt.body(), attempt.signature, host=attempt.fields['host'])
        self.assertTrue(reply.startswith(b'HTTP/1.1 200 OK\r\n'))
        self.assertEqual([(attempt.link_id, attempt.fields['controller_key'])], [link[:2] for link in self.links()])

    def test_a_request_made_for_another_identity_or_another_certificate_does_not_verify(self):
        code = self.issue()
        self.identity[0] = crypto.generate_private_key()
        self.secrets.append(self.identity[0].hex())
        # The server's identity is no longer the one in the code: it refuses, and the controller is told nothing.
        self.not_paired(code)
        self.assertEqual(('pairing', 'refused', 'signature', '', '', '127.0.0.1', 403), self.audited()[-2])
        self.assertEqual(((), ((1, 0),)), (self.links(), self.codes()))
        self.identity[0] = bytes.fromhex(self.secrets[0])
        self.refused(self.send(self.attempt(code, node_id='b3' * 32)), 'signature', failures=2)
        self.refused(self.send(self.attempt(code, tls_fingerprint=pin('impostor'))), 'signature', failures=3)
        self.panel.joinpath('cert.pem').write_bytes(Path(CERTIFICATES['impostor'][0]).read_bytes())
        self.refused(self.send(self.attempt(code)), 'signature', failures=4)

    def test_a_code_is_used_once(self):
        code = self.issue()
        first = self.pair(code)
        self.stored[:] = []
        self.not_paired(code)
        self.assertEqual(GENERIC, self.send(self.attempt(code)))
        self.assertEqual([('pairing', 'refused', 'consumed', '', '', '127.0.0.1', 403),
                          ('pairing', 'refused', 'signature', '', 'admin', '', None),
                          ('pairing', 'refused', 'consumed', '', '', '127.0.0.1', 403)], self.audited()[-3:])
        self.assertEqual([first.link_id], [link[0] for link in self.links()])
        self.assertEqual(((0, 1),), self.codes())

    def race(self, code, controllers=6):
        """Every controller's request passes each check before any of them reaches the step that uses the code up."""
        together, outcomes, verify = threading.Barrier(controllers), [], crypto.verify

        def held(public, signature, message):
            valid = verify(public, signature, message)
            if getattr(SIDE, 'role', None) == keys.NODE and message.startswith(b'CPMS1-PAIR-REQ\n'):
                together.wait(20)
            return valid

        def controller():
            try:
                outcomes.append(self.pair(code))
            except pairing.PairingError as error:
                outcomes.append(error)
            finally:
                connection.close()
        with mock.patch.object(crypto, 'verify', held):
            workers = [threading.Thread(target=controller) for unused in range(controllers)]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join()
        self.assertEqual(controllers, len(outcomes))
        return outcomes

    def test_of_many_controllers_racing_on_one_code_exactly_one_gets_a_link(self):
        for unused in range(3):
            self.again()
            code = self.issue()
            outcomes = self.race(code)
            (paired,) = [outcome for outcome in outcomes if isinstance(outcome, pairing.Paired)]
            self.assertEqual([('signature', REFUSED)] * 5, [(outcome.reason, str(outcome)) for outcome in outcomes
                                                           if outcome is not paired])
            self.assertEqual([paired.link_id], [link[0] for link in self.links()])
            self.assertEqual([paired.link_id], [stored[1] for stored in self.stored])
            self.assertEqual(((0, 1),), self.codes())
            by_the_server = [row[1:4] for row in self.audited() if row[0] == 'pairing' and row[6] is not None]
            self.assertEqual([('ok', '', paired.link_id)] + [('refused', 'consumed')] * 5,
                             sorted(row if row[0] == 'ok' else row[:2] for row in by_the_server))

    def test_the_code_is_used_up_by_one_request_even_where_no_index_stands_behind_it(self):
        self.assertIs(True, schema.ready())
        self.database.run('ALTER TABLE ms_links DROP INDEX ms_links_pairing')
        try:
            code = self.issue()
            outcomes = self.race(code)
            self.assertEqual(1, len([outcome for outcome in outcomes if isinstance(outcome, pairing.Paired)]))
            self.assertEqual(1, len(self.links()))
            self.assertEqual(((0, 1),), self.codes())
        finally:
            self.database.run('DELETE FROM ms_links')
            self.database.run('ALTER TABLE ms_links ADD UNIQUE KEY ms_links_pairing (pairing_key)')

    def test_a_code_ends_ten_minutes_after_it_was_made(self):
        late, in_time = self.issue(), self.issue()
        self.clock[0] = NOW + 600
        self.not_paired(late)
        self.assertEqual(('pairing', 'refused', 'expired', '', '', '127.0.0.1', 403), self.audited()[-2])
        self.assertEqual(GENERIC, self.send(self.attempt(late)))
        self.assertEqual(((), ((0, 0), (0, 0))), (self.links(), self.codes()))
        self.clock[0] = NOW + 599
        self.assertIsInstance(self.pair(in_time), pairing.Paired)

    def test_five_refused_attempts_burn_a_code_and_the_sixth_fails_although_it_is_correct(self):
        code = self.issue()
        for failures in range(1, 6):
            reply = self.send(self.attempt(code, sign_with=crypto.generate_private_key()))
            self.refused(reply, 'signature', failures=failures)
        self.not_paired(code)
        self.assertEqual(('pairing', 'refused', 'burned', '', '', '127.0.0.1', 403), self.audited()[-2])
        self.refused(self.send(self.attempt(code)), 'burned', failures=5)
        self.refused(self.send(self.attempt(code, sign_with=crypto.generate_private_key())), 'burned', failures=5)
        self.refused(self.send(self.attempt(code), source='127.0.0.2'), 'burned', source='127.0.0.2', failures=5)

    def test_a_code_burned_while_a_correct_request_is_being_checked_is_not_used(self):
        code = self.issue()
        verify = crypto.verify

        def burned_meanwhile(public, signature, message):
            valid = verify(public, signature, message)
            if getattr(SIDE, 'role', None) == keys.NODE and message.startswith(b'CPMS1-PAIR-REQ\n'):
                # The fifth refused attempt of somebody else arrives at this very moment.
                self.database.run('UPDATE ms_pairing_codes SET failures = 5')
            return valid
        attempt = self.attempt(code)
        with mock.patch.object(crypto, 'verify', burned_meanwhile):
            self.refused(self.send(attempt), 'burned', link_id=attempt.link_id, failures=5)

    def test_failures_from_a_wrong_address_and_with_a_wrong_signature_are_counted_together_and_at_once(self):
        code = self.issue()
        attempts = [self.attempt(code, sign_with=crypto.generate_private_key()) for unused in range(8)]
        replies = []

        def attempt(number):
            try:
                replies.append(self.send(attempts[number], source='127.0.0.%d' % (1 + number % 2)))
            finally:
                connection.close()
        workers = [threading.Thread(target=attempt, args=(number,)) for number in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual([GENERIC] * 8, replies)
        self.assertEqual(((5, 0),), self.codes())
        reasons = [row[2] for row in self.audited() if row[0] == 'pairing']
        self.assertEqual(8, len(reasons))
        self.assertEqual(set(), set(reasons) - {'signature', 'source_ip', 'burned'})
        # Each of the eight was refused; five were counted, and no count went past the fifth.
        self.assertGreaterEqual(len([reason for reason in reasons if reason != 'burned']), 5)
        self.not_paired(code)
        self.assertEqual(('pairing', 'refused', 'burned', '', '', '127.0.0.1', 403), self.audited()[-2])

    def test_a_request_from_another_address_is_refused_and_counted_however_well_it_is_signed(self):
        code = self.issue()
        self.refused(self.send(self.attempt(code), source='127.0.0.2'), 'source_ip', source='127.0.0.2', failures=1)
        elsewhere = self.issue('203.0.113.9')
        self.not_paired(elsewhere)
        self.assertEqual(('pairing', 'refused', 'source_ip', '', '', '127.0.0.1', 403), self.audited()[-2])
        self.assertEqual(((1, 0), (1, 0)), self.codes())
        self.assertEqual((), self.links())

    def test_a_request_changed_after_it_was_signed_is_refused(self):
        other_key = crypto.public_key(crypto.generate_private_key()).hex()
        for change in (dict(link_id='a2' * 16), dict(controller_key=other_key), dict(timestamp=NOW + 1),
                       dict(timestamp=NOW - 1), dict(nonce='c4' * 16)):
            self.again()
            attempt = self.attempt(self.issue())
            self.refused(self.send(attempt, body=attempt.body(**change)), 'signature', failures=1)
        for host in ('127.0.0.1:1', 'localhost:%d' % self.node.port, 'node-1.example.com:%d' % self.node.port,
                     '[::1]:%d' % self.node.port):
            self.again()
            code = self.issue()
            self.refused(self.send(self.attempt(code), host=host), 'signature', failures=1)
            # One refused attempt does not end a code: the controller it was made for still pairs.
            self.assertIsInstance(self.pair(code), pairing.Paired)

    def test_a_request_that_names_no_code_of_this_server_is_refused(self):
        code = self.issue()
        attempt = self.attempt(code)
        unknown = crypto.public_key(crypto.generate_private_key()).hex()
        self.refused(self.send(attempt, body=attempt.body(pairing_key=unknown)), 'link')
        seed = crypto.generate_private_key()
        never_issued = pairing._encode('127.0.0.1', self.node.port, crypto.node_id(self.node_key), pin('node'), seed)
        self.secrets += [never_issued, seed.hex()]
        self.not_paired(never_issued)
        self.assertEqual(('pairing', 'refused', 'link', '', '', '127.0.0.1', 403), self.audited()[-2])
        self.assertEqual(((0, 0),), self.codes())

    def test_a_malformed_or_oversized_request_is_refused_and_costs_the_code_nothing(self):
        code = self.issue()
        attempt = self.attempt(code)
        body = attempt.body()
        for reason, options in (
                ('size', dict(body=body + b'x' * (257 - len(body)))), ('size', dict(body=b'x' * 4096)),
                ('format', dict(body=body + b'x' * (256 - len(body)))), ('format', dict(body=body + b'\n')),
                ('format', dict(body=body.replace(b'\n', b'\r\n'))), ('format', dict(body=body.upper())),
                ('format', dict(body=body.rsplit(b'\n', 1)[0])), ('format', dict(body=b'{"code": "x"}')),
                ('format', dict(body=b'CPMS1-PAIR-REQ\n' + body)),
                ('format', dict(method='GET')), ('format', dict(method='PUT')),
                ('format', dict(path='/multiserver/pair/')),
                ('format', dict(path='/multiserver/pair?x=1')), ('format', dict(content_type='application/json')),
                ('format', dict(content_type='text/plain; charset=utf-8')), ('format', dict(content_type=None)),
                ('format', dict(signature='')), ('format', dict(signature=attempt.signature.upper())),
                ('format', dict(signature=attempt.signature[:-2])), ('format', dict(signature='zz' * 64)),
                ('format', dict(headers=[('X-CPMS-Signature', attempt.signature)])),
                ('format', dict(host='127.0.0.1')), ('format', dict(host='a b:8090'))):
            self.refused(self.send(attempt, **options), reason)
        self.refused(post(self.node.port, body, None), 'format')
        # None of that was held against the code: the very same request is still accepted.
        self.assertTrue(self.send(attempt).startswith(b'HTTP/1.1 200 OK\r\n'))
        self.assertEqual(([attempt.link_id], ((0, 1),)), ([link[0] for link in self.links()], self.codes()))

    def test_a_request_signed_at_another_time_is_refused_without_counting_against_the_code(self):
        code = self.issue()
        for seconds in (-91, 91, -3600, 86400):
            attempt = self.attempt(code, timestamp=NOW + seconds)
            self.refused(self.send(attempt), 'time', link_id=attempt.link_id)
        for seconds in (-90, 90):
            attempt = self.attempt(self.issue(), timestamp=NOW + seconds)
            self.assertTrue(self.send(attempt).startswith(b'HTTP/1.1 200 OK\r\n'), seconds)
        self.assertEqual(2, len(self.links()))
        self.assertEqual(90, pairing.TIME_WINDOW)

    def test_a_link_id_that_exists_is_refused_and_nothing_changes(self):
        first = self.pair(self.issue())
        before = self.links()
        code = self.issue()
        attempt = self.attempt(code, link_id=first.link_id)
        self.assertEqual(GENERIC, self.send(attempt))
        self.assertEqual(('pairing', 'refused', 'replay', first.link_id, '', '127.0.0.1', 403), self.audited()[-1])
        self.assertEqual(before, self.links())
        self.assertEqual([(0, 0), (0, 1)], sorted(self.codes()))
        self.assertIsInstance(self.pair(code), pairing.Paired)
        self.assertEqual(2, len(self.links()))

    def test_a_server_that_cannot_record_or_sign_makes_no_link_and_keeps_the_code(self):
        code = self.issue()
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            self.assertEqual(GENERIC, self.send(self.attempt(code)))
            self.assertEqual(((), ((0, 0),)), (self.links(), self.codes()))
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')
        for broken, value in ((self.identity, None), (self.generation, 0)):
            kept, broken[0] = broken[0], value
            self.refused(self.send(self.attempt(code)), 'internal', outcome='error')
            broken[0] = kept
        self.panel.joinpath('cert.pem').unlink()
        self.refused(self.send(self.attempt(code)), 'internal', outcome='error')

    def test_a_server_that_is_not_a_managed_server_refuses_like_any_other_refusal(self):
        code = self.issue()
        for role in (keys.OFF, keys.CONTROLLER):
            self.node.role = role
            with mock.patch('multiServer.models.PairingCode.objects.filter') as looked_up:
                self.refused(self.send(self.attempt(code)), 'role')
                looked_up.assert_not_called()

    def test_without_the_allowance_for_tests_the_controller_refuses_this_machine(self):
        code = self.issue()
        with mock.patch.object(transport, 'Endpoint', test_pairing.Endpoint):
            self.not_paired(code, 'not_allowed', 'A link may not connect to this address (loopback).')
        self.assertTrue(self.node.connections.empty())
        text = code[:40] + ('A' if code[40] != 'A' else 'B') + code[41:]
        self.not_paired(text, 'format', 'This is not a pairing code, or not all of one.')
        self.assertTrue(self.node.connections.empty())
        self.assertEqual([('pairing', 'refused', 'not_allowed', '', 'admin', '', None),
                          ('pairing', 'refused', 'format', '', 'admin', '', None)], self.audited()[-2:])
        self.assertEqual(((0, 0),), self.codes())


class CodeIssuingTests(Servers):
    def refused(self, reason, because, *arguments, **options):
        before = len(self.audited())
        with self.assertRaises(pairing.PairingError) as caught, on_the_node():
            pairing.issue_code(*arguments, **options)
        self.assertEqual((reason, because), (caught.exception.reason, str(caught.exception)))
        self.assertEqual((), self.codes())
        (row,) = self.audited()[before:]
        self.assertEqual(('pairing_code', 'error' if reason == 'internal' else 'refused', reason), row[:3])
        return row

    def test_only_an_active_full_administrator_of_a_managed_server_is_given_a_code(self):
        nobody = 'Only a full administrator of this server may do this.'
        for admin_id in (None, '1', 1.0, True, [1]):
            self.refused('admin', nobody, admin_id, '127.0.0.1')
        self.find.assert_not_called()
        for acl in ({'admin': 0}, {}, {'admin': '1'}, {'admin': True}):
            self.acl.return_value = acl
            self.refused('admin', nobody, ADMIN, '127.0.0.1')
        self.acl.return_value = {'admin': 1}
        for state in ('SUSPENDED', '', None):
            self.administrator.state = state
            self.refused('admin', nobody, ADMIN, '127.0.0.1')
        self.administrator.state = 'ACTIVE'
        self.find.side_effect = RuntimeError('Administrator matching query does not exist.')
        self.refused('admin', nobody, 99, '127.0.0.1')
        self.find.side_effect = None
        with self.assertRaises(pairing.PairingError) as caught:
            pairing.issue_code(ADMIN, '127.0.0.1', host='127.0.0.1', port=self.node.port)
        self.assertEqual(('role', 'This server is not a managed server.'),
                         (caught.exception.reason, str(caught.exception)))
        self.assertEqual(('pairing_code', 'refused', 'role', '', '', '', None), self.audited()[-1])
        self.assertEqual((), self.codes())

    def test_the_controller_is_named_by_one_address(self):
        for address in ('', 'controller.example.com', '203.0.113.9/32', '203.0.113.9, 203.0.113.10', '010.0.0.1',
                        '::ffff:203.0.113.9', 'fe80::1%eth0', ' 203.0.113.9', None, 3405803785, b'203.0.113.9'):
            row = self.refused('format', "The controller's address must be one IPv4 or IPv6 address.", ADMIN, address,
                               host='127.0.0.1', port=self.node.port)
            self.assertEqual(('admin', ''), row[4:6])

    def test_a_code_is_not_made_for_an_address_no_controller_would_connect_to(self):
        for host, kind in (('10.0.0.5', 'private'), ('192.168.1.9', 'private'), ('169.254.169.254', 'cloud metadata'),
                           ('0.0.0.0', 'unspecified'), ('fd00::1', 'private')):
            self.refused('not_allowed', 'A link may not connect to this address (%s).' % kind, ADMIN, '127.0.0.1',
                         host=host, port=8090)
        with mock.patch.object(transport, 'Endpoint', test_pairing.Endpoint):
            self.refused('not_allowed', 'A link may not connect to this address (loopback).', ADMIN, '127.0.0.1',
                         host='127.0.0.1', port=8090)
        unusable = 'The address or the port of this server is not one a controller can connect to.'
        for host, port in (('localhost', 8090), ('Node-1.example.com', 8090), ('127.1', 8090), ('', 8090),
                           ('127.0.0.1', 0), ('127.0.0.1', 65536), ('127.0.0.1', '8090'), (b'127.0.0.1', 8090)):
            self.refused('format', unusable, ADMIN, '127.0.0.1', host=host, port=port)

    def test_left_out_the_address_and_the_port_are_the_panels_own(self):
        address = self.panel.joinpath('machineIP')
        self.patch(entitlement, 'ADDRESS_FILE', str(address))
        for content, binding, expected in (('93.184.216.34\n', '', ('93.184.216.34', 8090)),
                                           ('93.184.216.34', '*:2087', ('93.184.216.34', 2087)),
                                           ('2a01:4f8::1\n', '0.0.0.0:8090', ('2a01:4f8::1', 8090))):
            address.write_text(content)
            self.panel.joinpath('bind.conf').write_text(binding)
            with on_the_node():
                shown = pairing.read_code(pairing.issue_code(ADMIN, '203.0.113.9'))
            self.assertEqual(expected + (crypto.node_id(self.node_key), pin('node')), tuple(shown))
        self.database.run('DELETE FROM ms_pairing_codes')
        unreadable = 'The identity key, the certificate or the port of this server could not be read.'
        self.panel.joinpath('bind.conf').write_text('not a binding')
        self.refused('internal', unreadable, ADMIN, '203.0.113.9')
        self.panel.joinpath('bind.conf').write_text('')
        address.write_text('10.0.0.5\n')
        self.refused('not_allowed', 'A link may not connect to this address (private).', ADMIN, '203.0.113.9')
        address.unlink()
        self.refused('format', 'The address or the port of this server is not one a controller can connect to.',
                     ADMIN, '203.0.113.9')

    def test_without_its_identity_key_or_its_certificate_a_server_gives_no_code(self):
        unreadable = 'The identity key, the certificate or the port of this server could not be read.'
        kept, self.identity[0] = self.identity[0], None
        self.refused('internal', unreadable, ADMIN, '127.0.0.1', host='127.0.0.1', port=8090)
        self.identity[0] = kept
        self.panel.joinpath('cert.pem').write_text('not a certificate')
        self.refused('internal', unreadable, ADMIN, '127.0.0.1', host='127.0.0.1', port=8090)

    def test_a_code_that_cannot_be_recorded_is_not_given(self):
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            with self.assertRaises(pairing.PairingError) as caught, on_the_node():
                pairing.issue_code(ADMIN, '127.0.0.1', host='127.0.0.1', port=self.node.port)
            self.assertEqual('internal', caught.exception.reason)
            self.assertEqual((), self.codes())
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')


class DecisionTests(Servers):
    def setUp(self):
        super().setUp()
        self.paired = self.pair(self.issue())
        self.link_id = self.paired.link_id

    def status(self):
        return [(link[0], link[5]) for link in self.links()]

    def refused(self, reason, because, decide=None, link_id=THE_LINK, admin_id=ADMIN, actor='admin'):
        before, links = len(self.audited()), self.links()
        link_id = self.link_id if link_id is THE_LINK else link_id
        with self.assertRaises(pairing.PairingError) as caught, on_the_node():
            (decide or pairing.approve)(link_id, admin_id)
        self.assertEqual((reason, because), (caught.exception.reason, str(caught.exception)))
        self.assertEqual(links, self.links())
        recorded = link_id if reason in ('link', 'not_allowed', 'expired', 'generation') else ''
        self.assertEqual([('link_revoke' if decide is pairing.reject else 'link_approve', 'refused', reason, recorded,
                           actor, '', None)], self.audited()[before:])

    def test_only_an_active_full_administrator_of_the_managed_server_decides(self):
        nobody = 'Only a full administrator of this server may do this.'
        for decide in (pairing.approve, pairing.reject):
            for admin_id in (None, '1', 1.0, True):
                self.refused('admin', nobody, decide, admin_id=admin_id, actor='')
            self.acl.return_value = {'admin': 0}
            self.refused('admin', nobody, decide, actor='')
            self.acl.return_value = {'admin': 1}
            self.administrator.state = 'SUSPENDED'
            self.refused('admin', nobody, decide, actor='')
            self.administrator.state = 'ACTIVE'
            self.find.side_effect = RuntimeError('Administrator matching query does not exist.')
            self.refused('admin', nobody, decide, admin_id=99, actor='')
            self.find.side_effect = None
            with self.assertRaises(pairing.PairingError) as caught:
                decide(self.link_id, ADMIN)
            self.assertEqual('role', caught.exception.reason)
            self.assertEqual(('refused', 'role'), self.audited()[-1][1:3])
        with self.assertRaises(pairing.PairingError) as caught:
            pairing.pending()
        self.assertEqual('role', caught.exception.reason)
        self.assertEqual([(self.link_id, 'pending')], self.status())

    def test_a_link_that_does_not_exist_cannot_be_decided(self):
        for decide in (pairing.approve, pairing.reject):
            self.refused('link', 'There is no such link.', decide, link_id='a2' * 16)
            for link_id in ('', self.link_id.upper(), self.link_id[:-1], self.link_id + '\n', self.link_id.encode(),
                            None, 1, "' OR 1=1 -- "):
                self.refused('format', 'This is not a link.', decide, link_id=link_id)
        self.assertEqual([(self.link_id, 'pending')], self.status())

    def test_a_link_is_approved_once(self):
        with on_the_node():
            pairing.approve(self.link_id, ADMIN)
        active = self.links()
        self.clock[0] = NOW + 60
        for decide in (pairing.approve, pairing.reject):
            self.refused('not_allowed', 'This link is not waiting for a decision.', decide)
        self.assertEqual(active, self.links())
        self.assertEqual('active', active[0][5])

    def test_of_many_approvals_at_once_one_is_carried_out(self):
        outcomes = []

        def decide():
            SIDE.role = keys.NODE
            try:
                outcomes.append(pairing.approve(self.link_id, ADMIN))
            except pairing.PairingError as error:
                outcomes.append(error.reason)
            finally:
                connection.close()
        workers = [threading.Thread(target=decide) for unused in range(8)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual([None] + ['not_allowed'] * 7, sorted(outcomes, key=str))
        self.assertEqual(['ok'] + ['refused'] * 7,
                         sorted(row[1] for row in self.audited() if row[0] == 'link_approve'))

    def test_a_rejected_link_is_closed_for_good(self):
        with on_the_node():
            self.assertIsNone(pairing.reject(self.link_id, ADMIN))
            self.assertEqual([], pairing.pending())
        self.assertEqual([(self.link_id, 'revoked')], self.status())
        self.assertEqual(('link_revoke', 'ok', '', self.link_id, 'admin', '', None), self.audited()[-1])
        for decide in (pairing.approve, pairing.reject):
            self.refused('not_allowed', 'This link is not waiting for a decision.', decide)
        # The code it came from stays used: the unique index refuses a second link from it.
        self.assertEqual(((0, 1),), self.codes())

    def test_a_link_nobody_approved_in_ten_minutes_is_closed(self):
        self.assertEqual(600, pairing.PENDING_LIFETIME)
        late = self.pair(self.issue()).link_id
        self.clock[0] = NOW + 600
        self.refused('expired', 'This link was not approved in time. Pair the two servers again.')
        self.assertEqual([(link_id, 'pending') for link_id in sorted((self.link_id, late))], sorted(self.status()))
        with on_the_node():
            self.assertEqual([], pairing.pending())
        self.assertEqual(sorted([(self.link_id, 'revoked'), (late, 'revoked')]), sorted(self.status()))
        self.assertEqual(sorted(('link_expire', 'ok', '', link_id, '', '', None) for link_id in (self.link_id, late)),
                         sorted(self.audited()[-2:]))
        self.refused('not_allowed', 'This link is not waiting for a decision.', link_id=late)
        with on_the_node():
            self.assertEqual([], pairing.pending())
        self.assertEqual(2, len([row for row in self.audited() if row[0] == 'link_expire']))

    def test_a_link_made_before_a_revocation_cannot_be_approved(self):
        self.generation[0] = GENERATION + 1
        with on_the_node():
            self.assertEqual([], pairing.pending())
        self.refused('generation', 'A link was revoked on this server after this one was made. Pair the two servers '
                     'again.')
        self.generation[0] = 0
        self.refused('generation', 'A link was revoked on this server after this one was made. Pair the two servers '
                     'again.')
        self.generation[0] = GENERATION
        with on_the_node():
            self.assertEqual([self.link_id], [waiting.link_id for waiting in pairing.pending()])
            pairing.approve(self.link_id, ADMIN)
        self.assertEqual([(self.link_id, 'active')], self.status())

    def test_every_waiting_link_is_listed_with_its_own_number(self):
        second = self.pair(self.issue())
        with on_the_node():
            waiting = pairing.pending()
        self.assertEqual(sorted([(self.link_id, self.paired.confirmation), (second.link_id, second.confirmation)]),
                         sorted((link.link_id, link.confirmation) for link in waiting))
        self.assertNotEqual(self.paired.confirmation, second.confirmation)
        kept, self.identity[0] = self.identity[0], None
        with self.assertRaises(pairing.PairingError) as caught, on_the_node():
            pairing.pending()
        self.assertEqual('internal', caught.exception.reason)
        self.identity[0] = kept

    def test_a_decision_that_cannot_be_recorded_is_not_carried_out(self):
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            for decide in (pairing.approve, pairing.reject):
                with self.assertRaises(pairing.PairingError) as caught, on_the_node():
                    decide(self.link_id, ADMIN)
                self.assertEqual('internal', caught.exception.reason)
                self.assertEqual([(self.link_id, 'pending')], self.status())
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')


if __name__ == '__main__':
    unittest.main()
