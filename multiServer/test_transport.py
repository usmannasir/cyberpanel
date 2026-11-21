"""The signed channel to a node: nothing is sent before the certificate matches, nothing comes back unverified."""
import ast
import base64
import collections
import copy
import datetime
import gzip
import hashlib
import inspect
import ipaddress
import os
from pathlib import Path
import pickle
import queue
import shutil
import socket
import ssl
import struct
import sys
import tempfile
import threading
import time
import traceback
import unittest
from unittest import mock
import warnings

from multiServer import crypto, transport

LINK = 'a1' * 16
NONCE = 'c3' * 16
PRIVATE = b'controller-private-key-material!'
PUBLIC = crypto.public_key(PRIVATE)
REQUEST_BODY = b'{"domainName": "request-body-secret.example.com"}'
REPLY_BODY = b'{"status": "reply-body-secret"}'
PUBLIC_ADDRESS = '93.184.216.34'
CERTIFICATES = {}  # name -> (file holding key and certificate, certificate in DER)

Seen = collections.namedtuple('Seen', 'method target path query version headers body')


def setUpModule():
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import ec
    from cryptography.x509.oid import NameOID
    directory = tempfile.mkdtemp()
    CERTIFICATES['directory'] = directory
    for name, last_year in (('node', 2040), ('impostor', 2040), ('expired', 2021)):
        key = ec.generate_private_key(ec.SECP256R1())
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, name)])
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(datetime.datetime(2020, 1, 1))
                       .not_valid_after(datetime.datetime(last_year, 1, 1)).sign(key, hashes.SHA256()))
        path = os.path.join(directory, name + '.pem')
        with open(path, 'wb') as handle:
            handle.write(key.private_bytes(serialization.Encoding.PEM,
                                           serialization.PrivateFormat.TraditionalOpenSSL,
                                           serialization.NoEncryption()))
            handle.write(certificate.public_bytes(serialization.Encoding.PEM))
        CERTIFICATES[name] = (path, certificate.public_bytes(serialization.Encoding.DER))


def tearDownModule():
    shutil.rmtree(CERTIFICATES.pop('directory'))


def pin(name):
    return hashlib.sha256(CERTIFICATES[name][1]).hexdigest()


def read_request(connection):
    """Everything the client wrote and, when that is one whole request, its parts."""
    raw = b''
    while b'\r\n\r\n' not in raw:
        chunk = connection.recv(65536)
        if not chunk:
            return raw, None
        raw += chunk
    head, _, body = raw.partition(b'\r\n\r\n')
    lines = head.decode('ascii').split('\r\n')
    headers = [tuple(line.split(': ', 1)) for line in lines[1:]]
    while len(body) < int(dict(headers).get('Content-Length', '0')):
        chunk = connection.recv(65536)
        if not chunk:
            return raw, None
        raw += chunk
        body += chunk
    method, target, version = lines[0].split(' ')
    path, _, query = target.partition('?')
    return raw, Seen(method, target, path, query, version, headers, body)


def wire(status, reason, headers):
    lines = ['HTTP/1.1 %d %s' % (status, reason)] + ['%s: %s' % header for header in headers]
    return ('\r\n'.join(lines) + '\r\n\r\n').encode('latin-1')


def reply(status=200, content_type='application/json', body=REPLY_BODY, signed=None, signature=None,
          length=None, extra=(), then=b'', hold=False, mangle=None):
    """An answer that writes one reply: `signed` changes what the node signs, the rest what it sends."""
    def answer(node, connection, seen):
        headers = []
        if content_type is not None:
            headers.append(('Content-Type', content_type))
        if length is not False:
            headers.append(('Content-Length', str(len(body)) if length is None else length))
        fields = dict(status=status, content_type=(content_type or '-').split(';')[0], body=body)
        fields.update(signed or {})
        value = signature(node, seen) if callable(signature) else signature
        if value is None:
            value = node.sign(seen, **fields)
        if value is not False:
            headers.append((transport.HEADERS['signature'], value))
        headers.extend(extra)
        data = wire(status, 'OK', headers) + body + then
        connection.sendall(mangle(data) if mangle else data)
        if hold:
            node.release.wait(10)
    return answer


def filling(total, head=False):
    """A signed reply of exactly `total` bytes, counting the whole reply or only its head."""
    def answer(node, connection, seen):
        size = total
        while True:
            body = b'x' * (0 if head else size)
            headers = [('Content-Type', 'text/plain'), ('Content-Length', str(len(body))),
                       (transport.HEADERS['signature'], node.sign(seen, 200, 'text/plain', body)),
                       ('X-Filler', 'x' * (size if head else 0))]
            data = wire(200, 'OK', headers)
            if len(data) + len(body) == total:
                break
            size -= len(data) + len(body) - total
        connection.sendall(data + body)
    return answer


class Node(object):
    """A local TLS server in the place of a node; `answer` writes whatever it replies."""

    def __init__(self, answer=None, certificate='node', speaks_tls=True, reads_slowly=False, address='127.0.0.1'):
        self.private = crypto.generate_private_key()
        self.public = crypto.public_key(self.private)
        self.id = crypto.node_id(self.public)
        self.pin = pin(certificate)
        self.answer = answer or reply()
        self.speaks_tls = speaks_tls
        self.reads_slowly = reads_slowly
        self.names = []  # what each client asked for by name in TLS
        self.signatures = []  # every signature this node saw or made
        self.connections = queue.Queue()  # one record per finished connection
        self.release = threading.Event()
        self.closed = False
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.load_cert_chain(CERTIFICATES[certificate][0])
        self.context.set_servername_callback(lambda connection, name, context: self.names.append(name))
        self.listener = socket.socket(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM)
        if reads_slowly:
            # A small window, set before any connection exists, so that the client's writes have to wait.
            self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 4096)
        self.listener.bind((address, 0))
        self.listener.listen(8)
        self.listener.settimeout(0.05)
        self.port = self.listener.getsockname()[1]
        self._start(self._accept)

    @staticmethod
    def _start(target, *arguments):
        thread = threading.Thread(target=target, args=arguments)
        thread.daemon = True
        thread.start()

    def close(self):
        self.closed = True
        self.release.set()
        self.listener.close()

    def _accept(self):
        while not self.closed:
            try:
                connection = self.listener.accept()[0]
            except socket.timeout:
                continue
            except OSError:
                return
            self._start(self._serve, connection)

    def _serve(self, connection):
        record = dict(tls=False, raw=b'', seen=None, error=None)
        try:
            connection.settimeout(10)
            if not self.speaks_tls:
                self.release.wait(10)
                return
            connection = self.context.wrap_socket(connection, server_side=True)
            record['tls'] = True
            while self.reads_slowly and not self.release.wait(0.02):
                record['raw'] += connection.recv(16384)
            record['raw'], record['seen'] = read_request(connection)
            if record['seen'] is not None:
                self.signatures.append(self.named(record['seen'])['signature'])
                self.answer(self, connection, record['seen'])
        except (OSError, ValueError) as error:
            record['error'] = error
        finally:
            connection.close()
            self.connections.put(record)

    def finished(self):
        return self.connections.get(timeout=5)

    @staticmethod
    def named(seen):
        """The X-CPMS-* fields of a request, read through the same table the client writes from."""
        headers = dict((name.lower(), value) for name, value in seen.headers)
        return dict((field, headers[name.lower()]) for field, name in transport.HEADERS.items())

    def request_message(self, seen, **changes):
        """The signed bytes, rebuilt from nothing but what arrived."""
        headers = dict((name.lower(), value) for name, value in seen.headers)
        named = self.named(seen)
        fields = dict(link_id=named['link'], node_id=named['node'], method=seen.method, host=headers['host'],
                      path=seen.path, query=seen.query, content_type=headers.get('content-type', '-'),
                      body=seen.body, timestamp=int(named['timestamp']), nonce=named['nonce'],
                      actor=named['actor'], mode=named['mode'])
        fields.update(changes)
        return crypto.request_message(**fields)

    def sign(self, seen, status, content_type, body, key=None, link_id=None, node_id=None, nonce=None,
             request=None):
        named = self.named(seen)
        message = crypto.response_message(link_id or named['link'], node_id or self.id,
                                          nonce or named['nonce'], self.request_message(seen, **(request or {})),
                                          status, content_type, body)
        self.signatures.append(crypto.sign(key or self.private, message).hex())
        return self.signatures[-1]


class Channel(unittest.TestCase):
    """A controller with a link to a node on this machine."""

    def node(self, *arguments, **options):
        node = Node(*arguments, **options)
        self.addCleanup(node.close)
        return node

    def link(self, node, **changes):
        fields = dict(link_id=LINK, node_id=node.id, host='127.0.0.1', port=node.port, node_key=node.public,
                      private_key=PRIVATE, tls_pin=node.pin, allow_loopback_for_tests=True)
        fields.update(changes)
        return transport.Link(**fields)

    def send(self, node, link=None, **changes):
        fields = dict(method='POST', path='/websites/submitWebsiteCreation', query='',
                      content_type='application/json', body=REQUEST_BODY, actor='admin', mode='json',
                      now=1795000000, nonce=NONCE)
        fields.update(changes)
        return transport.send(link or self.link(node), **fields)

    def refused(self, error, node, because=None, **changes):
        """The exchange ends in exactly this error, nothing is returned, and the error gives nothing away."""
        with self.assertRaises(transport.TransportError) as caught:
            self.send(node, **changes)
        self.assertIs(error, type(caught.exception), repr(caught.exception))
        if because is not None:
            self.assertEqual(because, str(caught.exception))
        self.assert_no_secret(caught.exception, node)
        return caught.exception

    def each_refused(self, error, reasons, within=None):
        """Every answer, grouped under the reason it must be refused for, is refused for that reason."""
        for because, answers in reasons.items():
            for name, answer in answers.items():
                with self.subTest(name):
                    started = time.monotonic()
                    self.refused(error, self.node(answer), because=because)
                    if within is not None:
                        self.assertLess(time.monotonic() - started, within)

    def assert_no_secret(self, error, node=None):
        texts = [''.join(traceback.format_exception(type(error), error, error.__traceback__))]
        while error is not None:
            texts += [str(error), repr(error), repr(error.args)]
            error = error.__cause__ or error.__context__
        secrets = [PRIVATE.decode(), PRIVATE.hex(), base64.b64encode(PRIVATE).decode(), 'request-body-secret',
                   'reply-body-secret', pin('node'), pin('impostor')]
        if node is not None:
            secrets += [node.public.hex(), node.private.hex()] + node.signatures
        for secret in secrets:
            self.assertNotIn(secret, '\n'.join(texts))


class ExchangeTests(Channel):
    def test_a_correct_exchange_returns_the_verified_status_type_and_body(self):
        for expected in ((200, 'application/json', REPLY_BODY), (404, 'text/html', b'<h1>Not here</h1>'),
                         (500, 'text/plain', b''), (200, 'application/octet-stream', bytes(range(256)) * 300)):
            node = self.node(reply(*expected))
            self.assertEqual(expected, self.send(node))

    def test_the_node_sees_exactly_the_signed_request_and_no_credentials(self):
        node = self.node()
        self.send(node, query='page=2&sort=name')
        record = node.finished()
        seen = record['seen']
        self.assertEqual(('POST', '/websites/submitWebsiteCreation?page=2&sort=name', 'HTTP/1.1'),
                         (seen.method, seen.target, seen.version))
        self.assertEqual([
            ('Host', '127.0.0.1:%d' % node.port), ('Connection', 'close'), ('Accept-Encoding', 'identity'),
            ('Content-Type', 'application/json'), ('Content-Length', str(len(REQUEST_BODY))),
            ('X-CPMS-Link', LINK), ('X-CPMS-Node', node.id), ('X-CPMS-Timestamp', '1795000000'),
            ('X-CPMS-Nonce', NONCE), ('X-CPMS-Actor', 'admin'), ('X-CPMS-Mode', 'json')], seen.headers[:-1])
        self.assertEqual('X-CPMS-Signature', seen.headers[-1][0])
        self.assertEqual(REQUEST_BODY, seen.body)
        self.assertTrue(record['raw'].endswith(b'\r\n\r\n' + REQUEST_BODY))
        names = set(name.lower() for name, value in seen.headers)
        self.assertFalse(names & {'cookie', 'authorization', 'proxy-authorization', 'user-agent', 'referer',
                                  'origin', 'x-forwarded-for', 'forwarded'})
        signed = crypto.request_message(
            link_id=LINK, node_id=node.id, method='POST', host='127.0.0.1:%d' % node.port,
            path='/websites/submitWebsiteCreation', query='page=2&sort=name', content_type='application/json',
            body=REQUEST_BODY, timestamp=1795000000, nonce=NONCE, actor='admin', mode='json')
        self.assertTrue(crypto.verify(PUBLIC, bytes.fromhex(seen.headers[-1][1]), signed))
        self.assertEqual(signed, node.request_message(seen))

    def test_a_request_without_a_body_or_a_query_carries_no_trace_of_either(self):
        for query, target in (('', '/websites/listWebsites'), ('page=2', '/websites/listWebsites?page=2')):
            node = self.node()
            self.assertEqual((200, 'application/json', REPLY_BODY), self.send(
                node, method='GET', path='/websites/listWebsites', query=query, content_type='-', body=b'',
                mode='page'))
            seen = node.finished()['seen']
            self.assertEqual(('GET', target, b''), (seen.method, seen.target, seen.body))
            self.assertFalse({'Content-Type', 'Content-Length'} & set(name for name, value in seen.headers))

    def test_an_ipv6_link_signs_and_sends_its_address_in_brackets(self):
        try:
            node = self.node(address='::1')
        except OSError:
            self.skipTest('no IPv6 loopback on this machine')
        self.assertEqual((200, 'application/json', REPLY_BODY), self.send(node, link=self.link(node, host='::1')))
        seen = node.finished()['seen']
        self.assertEqual('[::1]:%d' % node.port, dict(seen.headers)['Host'])
        self.assertIn(b'\n[::1]:%d\n' % node.port, node.request_message(seen))

    def test_time_and_nonce_are_fresh_when_the_caller_gives_none(self):
        node = self.node()
        link = self.link(node)
        before = int(time.time())
        for unused in range(2):
            transport.send(link, 'GET', '/', '', '-', b'', 'admin', 'page')
        named = [node.named(node.finished()['seen']) for unused in range(2)]
        self.assertNotEqual(named[0]['nonce'], named[1]['nonce'])
        for fields in named:
            self.assertRegex(fields['nonce'], '^[0-9a-f]{32}$')
            self.assertTrue(before <= int(fields['timestamp']) <= before + 5)

    def test_parameters_of_the_reply_content_type_are_not_passed_on(self):
        for header, returned in (('text/html; charset=utf-8', 'text/html'), ('text/html ;charset=utf-8', 'text/html'),
                                 (None, '-')):
            node = self.node(reply(content_type=header, signed=dict(content_type=returned)))
            self.assertEqual((200, returned, REPLY_BODY), self.send(node))

    def test_a_reply_may_fill_the_cap_and_not_one_byte_more(self):
        self.assertEqual(8 * 1024 * 1024, transport.MAX_RESPONSE)
        status, content_type, body = self.send(self.node(filling(transport.MAX_RESPONSE)))
        self.assertEqual((200, 'text/plain'), (status, content_type))
        self.assertTrue(transport.MAX_RESPONSE - 1024 < len(body) < transport.MAX_RESPONSE)
        self.refused(transport.ResponseTooLarge, self.node(filling(transport.MAX_RESPONSE + 1)))

    def test_reply_headers_may_fill_their_cap_and_not_one_byte_more(self):
        cap = transport.MAX_RESPONSE_HEAD
        self.assertEqual((200, 'text/plain', b''), self.send(self.node(filling(cap, head=True))))
        self.refused(transport.ResponseTooLarge, self.node(filling(cap + 1, head=True)))
        enough = [('X-Filler-%d' % number, 'x') for number in range(transport.MAX_RESPONSE_HEADERS - 3)]
        self.assertEqual((200, 'application/json', REPLY_BODY), self.send(self.node(reply(extra=enough))))
        self.refused(transport.MalformedResponse, self.node(reply(extra=enough + [('X-One-More', 'x')])))

    def test_proxy_settings_in_the_environment_are_ignored(self):
        proxy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(proxy.close)
        proxy.bind(('127.0.0.1', 0))
        proxy.listen(1)
        address = 'http://127.0.0.1:%d' % proxy.getsockname()[1]
        environment = dict((name, address) for name in ('HTTPS_PROXY', 'HTTP_PROXY', 'ALL_PROXY', 'https_proxy',
                                                        'http_proxy', 'all_proxy'))
        environment.update(NO_PROXY='', no_proxy='')
        node = self.node()
        with mock.patch.dict(os.environ, environment):
            self.assertEqual((200, 'application/json', REPLY_BODY), self.send(node))
        self.assertEqual('POST', node.finished()['seen'].method)
        proxy.settimeout(0.2)
        with self.assertRaises(socket.timeout):
            proxy.accept()


class CertificateTests(Channel):
    def test_a_server_with_another_certificate_receives_no_request_byte(self):
        for wrong in (pin('node'), pin('impostor')[:-1] + ('0' if pin('impostor')[-1] != '0' else '1')):
            node = self.node(certificate='impostor')
            self.refused(transport.CertificateMismatch, node, link=self.link(node, tls_pin=wrong))
            record = node.finished()
            # TLS was complete and the server was reading: it was simply sent nothing.
            self.assertEqual((True, b'', None), (record['tls'], record['raw'], record['seen']))
        self.send(node)
        self.assertIn(REQUEST_BODY, node.finished()['raw'])

    def test_the_pin_alone_decides_not_an_authority_a_name_or_a_date(self):
        context = transport._tls_context()
        self.assertEqual((ssl.CERT_NONE, False), (context.verify_mode, context.check_hostname))
        self.assertEqual(0, context.cert_store_stats()['x509_ca'])
        node = self.node(certificate='expired')
        self.assertEqual((200, 'application/json', REPLY_BODY), self.send(node))

    def test_old_protocol_versions_are_switched_off_on_every_python(self):
        if hasattr(ssl, 'TLSVersion'):
            self.assertEqual(ssl.TLSVersion.TLSv1_2, transport._tls_context().minimum_version)
        with mock.patch.object(ssl, 'TLSVersion', create=True) as absent, warnings.catch_warnings():
            warnings.simplefilter('ignore')
            del absent.TLSv1_2
            options = transport._tls_context().options
        self.assertEqual(ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1, options & (ssl.OP_NO_TLSv1 | ssl.OP_NO_TLSv1_1))

    def test_the_node_is_asked_for_by_name_only_when_the_link_has_a_name(self):
        node = self.node()
        self.send(node)
        self.assertEqual([None], node.names)


class HostileNodeTests(Channel):
    def test_a_reply_not_signed_by_the_node_for_this_request_is_refused(self):
        def valid(node, seen):
            return node.sign(seen, 200, 'application/json', REPLY_BODY)
        self.each_refused(transport.BadSignature, {
            'The reply is not signed.': {
                'no signature': reply(signature=False),
                'an empty signature': reply(signature=''),
                'a short signature': reply(signature=lambda node, seen: valid(node, seen)[:126]),
                'a long signature': reply(signature=lambda node, seen: valid(node, seen) + '00'),
                'an upper-case signature': reply(signature=lambda node, seen: valid(node, seen).upper()),
                'a signature that is not hex': reply(signature='zz' * 64),
                'a signature in base64': reply(signature=lambda node, seen: base64.b64encode(
                    bytes.fromhex(valid(node, seen))).decode()),
            },
            'The reply is not signed by the node for this request.': {
                'another key': reply(signed=dict(key=crypto.generate_private_key())),
                'the controller key': reply(signed=dict(key=PRIVATE)),
                'another body': reply(signed=dict(body=REPLY_BODY.replace(b'reply', b'other'))),
                'another status': reply(signed=dict(status=500)),
                'another content type': reply(signed=dict(content_type='text/html')),
                'another nonce': reply(signed=dict(nonce='c4' * 16)),
                'another link': reply(signed=dict(link_id='a2' * 16)),
                'another node': reply(signed=dict(node_id='b3' * 32)),
                'a request for another path': reply(signed=dict(request=dict(path='/websites/other'))),
                'a request with another query': reply(signed=dict(request=dict(query='page=2'))),
                'a request with another body': reply(signed=dict(request=dict(body=b'{}'))),
                'a request at another time': reply(signed=dict(request=dict(timestamp=1795000001))),
                'a request by another actor': reply(signed=dict(request=dict(actor='other'))),
                'a request in another mode': reply(signed=dict(request=dict(mode='page'))),
                'a request to another host': reply(signed=dict(request=dict(host='127.0.0.1:1'))),
                'the signature of the request sent back': reply(
                    signature=lambda node, seen: node.named(seen)['signature']),
                'a signature over the request itself': reply(
                    signature=lambda node, seen: crypto.sign(node.private, node.request_message(seen)).hex()),
                'a signature of all zeros': reply(signature='00' * 64),
            },
        })

    def test_a_reply_signed_for_one_request_does_not_answer_the_next(self):
        kept = []

        def replay(node, connection, seen):
            kept.append(kept[0] if kept else node.sign(seen, 200, 'application/json', REPLY_BODY))
            reply(signature=kept[0])(node, connection, seen)
        node = self.node(replay)
        self.assertEqual((200, 'application/json', REPLY_BODY), self.send(node))
        self.refused(transport.BadSignature, node, nonce='c4' * 16)
        self.refused(transport.BadSignature, node, now=1795000001)
        self.refused(transport.BadSignature, node, path='/websites/other')

    def test_a_redirect_is_refused_signed_or_not_and_never_followed(self):
        elsewhere = self.node()
        location = [('Location', 'https://127.0.0.1:%d/websites/submitWebsiteCreation' % elsewhere.port)]
        for status in (301, 302, 303, 307, 308):
            for signature in (None, False):
                with self.subTest(status=status, signed=signature is None):
                    node = self.node(reply(status=status, body=b'', extra=location, signature=signature))
                    self.refused(transport.RedirectRefused, node)
                    node.finished()
                    self.assertTrue(node.connections.empty())
        time.sleep(0.2)
        self.assertTrue(elsewhere.connections.empty())

    def test_a_reply_larger_than_the_cap_is_refused(self):
        def endless_headers(node, connection, seen):
            connection.sendall(b'HTTP/1.1 200 OK\r\n')
            for unused in range(64 * 1024):
                connection.sendall(b'X-Filler: ' + b'x' * 1000 + b'\r\n')

        def endless_header(node, connection, seen):
            connection.sendall(b'HTTP/1.1 200 OK\r\nX-Filler: ')
            for unused in range(64 * 1024):
                connection.sendall(b'x' * 1024)
        self.each_refused(transport.ResponseTooLarge, {
            'The reply is larger than a reply may be.': {
                'a length one past the cap, nothing sent': reply(length=str(transport.MAX_RESPONSE), hold=True),
                'an enormous length, nothing sent': reply(length='9' * 18, hold=True),
            },
            'The node sent too many reply headers.': {
                'headers without end': endless_headers,
                'one header without end': endless_header,
            },
        }, within=5)

    def test_a_reply_that_is_not_as_long_as_it_says_is_refused(self):
        second = wire(200, 'OK', [('Content-Type', 'application/json'), ('Content-Length', '2')]) + b'{}'

        def endless_body(node, connection, seen):
            reply()(node, connection, seen)
            for unused in range(64 * 1024):
                connection.sendall(b'x' * 1024)

        def second_reply_later(node, connection, seen):
            reply()(node, connection, seen)
            time.sleep(0.3)
            connection.sendall(second)
        self.each_refused(transport.MalformedResponse, {'The reply does not have the length it declares.': {
            'one byte more than declared': reply(then=b'x'),
            'a megabyte more than declared': reply(then=b'x' * 1024 * 1024),
            'a body without end': endless_body,
            'a second reply on the same connection': reply(then=second),
            'a second reply a moment after the first': second_reply_later,
            'a second copy of the same signed reply': reply(mangle=lambda data: data + data),
            'one byte less than declared': reply(length=str(len(REPLY_BODY) + 1)),
            'no body at all': reply(length=str(len(REPLY_BODY)), mangle=lambda data: data[:-len(REPLY_BODY)]),
        }}, within=5)

    def test_a_connection_cut_without_the_tls_goodbye_is_judged_by_the_declared_length(self):
        def cut(**options):
            def answer(node, connection, seen):
                reply(**options)(node, connection, seen)
                time.sleep(0.2)
                # Closing now resets the connection instead of ending it in order.
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_LINGER, struct.pack('ii', 1, 0))
            return answer
        real = ssl.SSLSocket.recv

        def raising(connection, size):
            data = real(connection, size)
            if not data:
                raise ssl.SSLError(ssl.SSL_ERROR_SSL, 'unexpected eof while reading')
            return data
        # Python and OpenSSL report such an end as an end or as an error, depending on their versions.
        for recv in (real, raising):
            with mock.patch.object(ssl.SSLSocket, 'recv', recv):
                self.assertEqual((200, 'application/json', REPLY_BODY), self.send(self.node(cut())))
                self.refused(transport.MalformedResponse, self.node(cut(length=str(len(REPLY_BODY) + 1))),
                             because='The reply does not have the length it declares.')
                self.refused(transport.ConnectionFailed, self.node(cut(mangle=lambda data: b'')))

    def test_chunked_compressed_and_unsized_replies_are_refused(self):
        chunked = b'%x\r\n%s\r\n0\r\n\r\n' % (len(REPLY_BODY), REPLY_BODY)
        packed = gzip.compress(REPLY_BODY)
        true_body = dict(body=REPLY_BODY)
        size = len(REPLY_BODY)
        self.each_refused(transport.MalformedResponse, {
            'The node did not send its reply whole and unencoded.': {
                'chunked': reply(body=chunked, signed=true_body, length=False,
                                 extra=[('Transfer-Encoding', 'chunked')]),
                'chunked with a length': reply(body=chunked, signed=true_body,
                                               extra=[('Transfer-Encoding', 'chunked')]),
                'a transfer encoding that changes nothing': reply(extra=[('Transfer-Encoding', 'identity')]),
                'gzip': reply(body=packed, signed=true_body, extra=[('Content-Encoding', 'gzip')]),
                'gzip, signed as sent': reply(body=packed, extra=[('Content-Encoding', 'gzip')]),
                'deflate': reply(extra=[('Content-Encoding', 'deflate')]),
                'an encoding named in upper case': reply(extra=[('Content-Encoding', 'IDENTITY')]),
            },
            'The node did not say how long its reply is.': {
                'no length': reply(length=False),
                'a list of lengths': reply(length='%d, %d' % (size, size)),
                'a length with a sign': reply(length='+%d' % size),
                'a length with a leading zero': reply(length='0%d' % size),
                'a length in hex': reply(length=hex(size)),
                'a negative length': reply(length='-1'),
                'an empty length': reply(length=''),
                'a length of nineteen digits': reply(length='1' + '0' * 18),
            },
            'The node repeated a reply header.': {
                'two lengths': reply(extra=[('Content-Length', str(size))]),
                'two different lengths': reply(extra=[('Content-Length', '0')]),
                'two transfer encodings': reply(extra=[('Transfer-Encoding', 'chunked')] * 2),
                'two content types': reply(extra=[('Content-Type', 'application/json')]),
                'two signatures': reply(extra=[(transport.HEADERS['signature'], '00' * 64)]),
                'the same signature twice': reply(mangle=lambda data: data.replace(b'\r\n\r\n', b'\r\n' + [
                    header for header in data.split(b'\r\n')
                    if header.startswith(transport.HEADERS['signature'].encode())][0] + b'\r\n\r\n', 1)),
                'a header repeated in another case': reply(extra=[('content-length', str(size))]),
            },
        })
        self.assertEqual((200, 'application/json', REPLY_BODY),
                         self.send(self.node(reply(extra=[('Content-Encoding', 'identity')]))))

    def test_a_reply_that_is_not_one_plain_http_reply_is_refused(self):
        def line(old, new):
            return lambda data: data.replace(old, new, 1)
        self.each_refused(transport.MalformedResponse, {
            'The node did not send a final HTTP reply.': {
                'an interim reply first': reply(mangle=lambda data: b'HTTP/1.1 100 Continue\r\n\r\n' + data),
                'an interim status': reply(status=101),
                'a status below 100': reply(mangle=line(b' 200 ', b' 099 ')),
                'a status above 599': reply(mangle=line(b' 200 ', b' 600 ')),
                'a status of two digits': reply(mangle=line(b' 200 ', b' 20 ')),
                'a status of four digits': reply(mangle=line(b' 200 ', b' 2000 ')),
                'another protocol': reply(mangle=line(b'HTTP/1.1', b'HTTP/2')),
                'a protocol in lower case': reply(mangle=line(b'HTTP/1.1', b'http/1.1')),
                'two spaces before the status': reply(mangle=line(b' 200 ', b'  200 ')),
                'a blank line first': reply(mangle=lambda data: b'\r\n' + data),
                'a line feed in the status line': reply(mangle=line(b' 200 OK', b' 200 OK\nX-Odd: x')),
            },
            'The node closed the connection in the middle of its reply headers.': {
                'a status line only, then closed': reply(mangle=lambda data: b'HTTP/1.1 200 OK\r\n'),
                'bare line feeds': reply(mangle=lambda data: data.replace(b'\r\n', b'\n')),
            },
            'The node sent a malformed reply header.': {
                'a header line without a colon': reply(extra=[('X-Odd\r\nbroken', 'x')]),
                'a folded header': reply(extra=[('X-Folded', 'one\r\n two')]),
                'a space before the colon': reply(extra=[('X-Odd ', 'x')]),
                'a header without a name': reply(extra=[('', 'x')]),
                'a line feed inside a header': reply(extra=[('X-Odd', 'x\nContent-Length: 0')]),
                'a carriage return inside a header': reply(extra=[('X-Odd', 'x\rContent-Length: 0')]),
                'a zero byte inside a header': reply(extra=[('X-Odd', 'x\x00y')]),
            },
            'The node named an invalid content type.': {
                'a content type in upper case': reply(content_type='Application/JSON',
                                                      signed=dict(content_type='application/json')),
                'an empty content type': reply(content_type='', signed=dict(content_type='-')),
                'a content type that is only parameters': reply(content_type='; charset=utf-8',
                                                                signed=dict(content_type='-')),
                'a content type with a byte above ascii': reply(content_type='text/pl\xe4in',
                                                                signed=dict(content_type='text/plain')),
                'two content types in one header': reply(content_type='text/html, application/json',
                                                         signed=dict(content_type='text/html')),
            },
        })

    def test_a_node_that_stalls_is_given_up_on_at_the_deadline(self):
        def silent(node, connection, seen):
            node.release.wait(10)

        def drip(node, connection, seen):
            data = wire(200, 'OK', [('Content-Type', 'application/json'), ('Content-Length', str(len(REPLY_BODY))),
                                    (transport.HEADERS['signature'],
                                     node.sign(seen, 200, 'application/json', REPLY_BODY))]) + REPLY_BODY
            for number in range(len(data)):
                connection.sendall(data[number:number + 1])
                if node.release.wait(0.05):
                    return
        cases = {
            'before TLS': dict(speaks_tls=False),
            'before any reply': dict(answer=silent),
            'in the middle of the headers': dict(answer=reply(mangle=lambda data: data[:40], hold=True)),
            'in the middle of the body': dict(answer=reply(length=str(len(REPLY_BODY) + 1), hold=True)),
            'after a whole reply, without closing': dict(answer=reply(hold=True)),
            'one byte at a time': dict(answer=drip),
            'while reading a large request a little at a time': dict(reads_slowly=True),
        }
        with mock.patch.object(transport, 'DEADLINE', 0.6), mock.patch.object(transport, 'CONNECT_TIMEOUT', 0.3):
            for name, options in cases.items():
                with self.subTest(name):
                    body = bytes(transport.MAX_REQUEST_BODY) if 'reads_slowly' in options else REQUEST_BODY
                    started = time.monotonic()
                    self.refused(transport.TimedOut, self.node(**options), body=body)
                    self.assertLess(time.monotonic() - started, 3)

    def test_a_server_that_is_not_a_node_at_all_is_a_failed_connection(self):
        plain = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.addCleanup(plain.close)
        plain.bind(('127.0.0.1', 0))
        plain.listen(1)
        vacant = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        vacant.bind(('127.0.0.1', 0))
        vacant_port = vacant.getsockname()[1]
        vacant.close()

        def not_tls():
            connection = plain.accept()[0]
            connection.sendall(b'HTTP/1.1 400 Bad Request\r\nContent-Length: 0\r\n\r\n')
            connection.close()
        Node._start(not_tls)
        node = self.node(lambda node, connection, seen: None)
        self.refused(transport.ConnectionFailed, node)
        self.refused(transport.ConnectionFailed, node, link=self.link(node, port=plain.getsockname()[1]))
        self.refused(transport.ConnectionFailed, node, link=self.link(node, port=vacant_port))


class AddressRuleTests(Channel):
    REFUSED = (
        ('127.0.0.1', 'loopback'), ('127.255.255.254', 'loopback'), ('::1', 'loopback'),
        ('0.0.0.0', 'unspecified'), ('0.1.2.3', 'unspecified'), ('::', 'unspecified'),
        ('10.0.0.1', 'private'), ('10.255.255.255', 'private'), ('172.16.0.1', 'private'),
        ('172.31.255.255', 'private'), ('192.168.0.1', 'private'), ('192.168.255.255', 'private'),
        ('fc00::1', 'private'), ('fdff:ffff::1', 'private'),
        ('169.254.0.1', 'link-local'), ('169.254.255.255', 'link-local'), ('fe80::1', 'link-local'),
        ('febf::1', 'link-local'),
        ('100.64.0.1', 'carrier-grade NAT'), ('100.127.255.255', 'carrier-grade NAT'),
        ('224.0.0.1', 'multicast'), ('239.255.255.255', 'multicast'), ('ff02::1', 'multicast'),
        ('ff0e::1', 'multicast'),
        ('192.0.0.1', 'reserved'), ('192.0.2.1', 'reserved'), ('192.88.99.1', 'reserved'),
        ('198.18.0.1', 'reserved'), ('198.19.255.255', 'reserved'), ('198.51.100.1', 'reserved'),
        ('203.0.113.1', 'reserved'), ('240.0.0.1', 'reserved'), ('255.255.255.255', 'reserved'),
        ('::7f00:1', 'reserved'), ('64:ff9b::7f00:1', 'reserved'), ('100::1', 'reserved'),
        ('2001::1', 'reserved'), ('2001:1ff::1', 'reserved'), ('2001:db8::1', 'reserved'),
        ('2002:7f00:1::1', 'reserved'), ('3fff::1', 'reserved'), ('4000::1', 'reserved'),
        ('fec0::1', 'reserved'), ('e000::1', 'reserved'), ('1fff::1', 'reserved'),
        ('169.254.169.254', 'cloud metadata'), ('169.254.170.2', 'cloud metadata'),
        ('100.100.100.200', 'cloud metadata'), ('168.63.129.16', 'cloud metadata'),
        ('fd00:ec2::254', 'cloud metadata'), ('fd20:ce::254', 'cloud metadata'),
        ('::ffff:127.0.0.1', 'IPv4-mapped'), ('::ffff:10.0.0.1', 'IPv4-mapped'),
        ('::ffff:a9fe:a9fe', 'IPv4-mapped'), ('::ffff:8.8.8.8', 'IPv4-mapped'),
    )
    ALLOWED = (
        '1.1.1.1', '8.8.8.8', PUBLIC_ADDRESS, '9.255.255.255', '11.0.0.0', '100.63.255.255', '100.128.0.0',
        '126.255.255.255', '128.0.0.0', '168.63.129.15', '168.63.129.17', '169.253.255.255', '169.255.0.0',
        '172.15.255.255', '172.32.0.0', '192.0.1.0', '192.0.3.0', '192.88.98.255', '192.167.255.255',
        '192.169.0.0', '198.17.255.255', '198.20.0.0', '198.51.99.255', '203.0.112.255', '203.0.114.0',
        '223.255.255.255', '2000::1', '2001:200::1', '2003::1', '2606:4700:4700::1111', '2a01:4f8::1',
        '3ffe::1',
    )
    NOT_ADDRESSES = ('', 'node.example.com', 'localhost', '1.1.1.1 ', ' 1.1.1.1', '1.1.1.1/32', '1.1.1',
                     'fe80::1%eth0', '2a01:4f8::1%eth0', '2a01:4f8::1%25eth0', '[2a01:4f8::1]', None, 16843009,
                     b'\x01\x01\x01\x01', b'1.1.1.1', ipaddress.ip_address('1.1.1.1'))

    def test_every_class_of_internal_address_is_refused_and_named(self):
        for address, kind in self.REFUSED:
            with self.assertRaises(transport.RefusedAddress, msg=address) as caught:
                transport.check_address(address)
            self.assertEqual('A link may not connect to this address (%s).' % kind, str(caught.exception), address)

    def test_public_addresses_next_to_each_refused_range_are_allowed(self):
        for address in self.ALLOWED:
            self.assertEqual(ipaddress.ip_address(address), transport.check_address(address), address)

    def test_what_is_not_one_plain_address_is_refused(self):
        for address in self.NOT_ADDRESSES:
            for allowance in (False, True):
                with self.assertRaises(transport.RefusedAddress, msg=repr(address)):
                    transport.check_address(address, allowance)

    def test_the_allowance_for_tests_opens_loopback_and_nothing_else(self):
        for address in ('127.0.0.1', '127.9.9.9', '::1'):
            self.assertEqual(ipaddress.ip_address(address), transport.check_address(address, True))
            for not_true in (False, None, 1, 'yes', [True]):
                with self.assertRaises(transport.RefusedAddress, msg=repr(not_true)):
                    transport.check_address(address, not_true)
        for address, kind in self.REFUSED:
            if kind != 'loopback':
                with self.assertRaises(transport.RefusedAddress, msg=address):
                    transport.check_address(address, True)
        for function in (transport.check_address, transport.Link.__init__):
            self.assertIs(False, inspect.signature(function).parameters['allow_loopback_for_tests'].default)
        self.assertNotIn('allow_loopback_for_tests', inspect.signature(transport.send).parameters)

    def test_only_tests_ask_for_the_allowance(self):
        for source in Path(__file__).parent.glob('**/*.py'):
            if source.name != 'transport.py' and not source.name.startswith('test_'):
                self.assertNotIn('allow_loopback_for_tests', source.read_text(), source.name)

    def test_a_link_to_a_refused_address_cannot_be_described(self):
        node = self.node()
        for address, kind in self.REFUSED:
            with self.assertRaises(transport.RefusedAddress, msg=address):
                self.link(node, host=address, allow_loopback_for_tests=False)
            if kind != 'loopback':
                with self.assertRaises(transport.RefusedAddress, msg=address):
                    self.link(node, host=address)

    def answers(self, *addresses):
        return [(socket.AF_INET6 if ':' in address else socket.AF_INET, socket.SOCK_STREAM, 6, '',
                 (address, 8090, 0, 0) if ':' in address else (address, 8090)) for address in addresses]

    def named_link(self, node, **changes):
        return self.link(node, host='node-1.example.com', port=8090, **changes)

    def test_a_name_that_resolves_to_a_refused_address_is_never_connected_to(self):
        node = self.node()
        cases = (['10.0.0.5'], ['169.254.169.254'], ['127.0.0.1'], ['::1'], ['::ffff:127.0.0.1'], ['fe80::1%eth0'],
                 [PUBLIC_ADDRESS, '192.168.1.9'], ['192.168.1.9', PUBLIC_ADDRESS], ['2a01:4f8::1', 'fd00::1'],
                 ['not-an-address'])
        for addresses in cases:
            with mock.patch.object(socket, 'getaddrinfo', return_value=self.answers(*addresses)), \
                    mock.patch.object(socket, 'socket') as made:
                self.refused(transport.RefusedAddress, node,
                             link=self.named_link(node, allow_loopback_for_tests=False))
                made.assert_not_called()
        with mock.patch.object(socket, 'getaddrinfo', return_value=self.answers('127.0.0.1', '10.0.0.5')), \
                mock.patch.object(socket, 'socket') as made:
            self.refused(transport.RefusedAddress, node, link=self.named_link(node))
            made.assert_not_called()

    def test_a_name_is_looked_up_once_and_the_checked_address_is_the_one_used(self):
        node = self.node()
        link = self.link(node, host='node-1.example.com')
        answers = [self.answers('127.0.0.1'), self.answers('127.0.0.2')]
        with mock.patch.object(socket, 'getaddrinfo', side_effect=answers) as lookup:
            self.assertEqual((200, 'application/json', REPLY_BODY), self.send(node, link=link))
        lookup.assert_called_once_with('node-1.example.com', node.port, 0, socket.SOCK_STREAM)
        self.assertEqual('node-1.example.com:%d' % node.port, dict(node.finished()['seen'].headers)['Host'])
        self.assertEqual(['node-1.example.com'], node.names)

    def test_a_name_that_changes_its_answer_cannot_move_the_connection_inside(self):
        node = self.node()
        answers = [self.answers(PUBLIC_ADDRESS, '2a01:4f8::1'), self.answers('127.0.0.1'), self.answers('10.0.0.5')]
        with mock.patch.object(socket, 'getaddrinfo', side_effect=answers) as lookup, \
                mock.patch.object(socket, 'socket') as made:
            made.return_value.connect.side_effect = OSError('unreachable')
            self.refused(transport.ConnectionFailed, node, link=self.named_link(node))
        self.assertEqual(1, lookup.call_count)
        self.assertEqual([((PUBLIC_ADDRESS, 8090),), (('2a01:4f8::1', 8090, 0, 0),)],
                         [call[0] for call in made.return_value.connect.call_args_list])
        self.assertEqual([(socket.AF_INET, socket.SOCK_STREAM), (socket.AF_INET6, socket.SOCK_STREAM)],
                         [call[0] for call in made.call_args_list])

    def test_a_name_that_does_not_resolve_is_a_failed_connection(self):
        node = self.node()
        waiting = threading.Event()
        self.addCleanup(waiting.set)
        for resolver, error in ((dict(side_effect=socket.gaierror(-2, 'Name or service not known')),
                                 transport.ConnectionFailed),
                                (dict(return_value=[]), transport.ConnectionFailed),
                                (dict(side_effect=lambda *arguments: waiting.wait(10)), transport.TimedOut)):
            with mock.patch.object(socket, 'getaddrinfo', **resolver), \
                    mock.patch.object(socket, 'socket') as made, \
                    mock.patch.object(transport, 'CONNECT_TIMEOUT', 0.2):
                self.refused(error, node, link=self.named_link(node))
                made.assert_not_called()


class LinkTests(Channel):
    def fields(self, **changes):
        node_key = crypto.public_key(b'n' * 32)
        fields = dict(link_id=LINK, node_id=crypto.node_id(node_key), host=PUBLIC_ADDRESS, port=8090,
                      node_key=node_key, private_key=PRIVATE, tls_pin='d4' * 32)
        fields.update(changes)
        return fields

    def test_a_link_holds_exactly_what_it_was_built_from(self):
        fields = self.fields()
        link = transport.Link(**fields)
        for name, value in fields.items():
            self.assertEqual(value, getattr(link, name), name)
        self.assertEqual((PUBLIC_ADDRESS + ':8090', False), (link.authority, link.allow_loopback_for_tests))
        for host in ('node-1.example.com', 'xn--80ak6aa92e.com', 'a.b.example.co.uk', '1.example.com',
                     'a' * 63 + '.' + 'b' * 63 + '.' + 'c' * 63 + '.' + 'd' * 61, '1.1.1.1'):
            link = transport.Link(**self.fields(host=host))
            self.assertEqual((host, host + ':8090'), (link.host, link.authority))
        link = transport.Link(**self.fields(host='2a01:4f8::1'))
        self.assertEqual(('2a01:4f8::1', '[2a01:4f8::1]:8090'), (link.host, link.authority))
        for port in (1, 65535):
            self.assertEqual(port, transport.Link(**self.fields(port=port)).port)

    def test_anything_but_an_exact_description_is_refused(self):
        other_key = crypto.public_key(b'o' * 32)
        refused = (
            dict(link_id='A1' * 16), dict(link_id='a1' * 15), dict(link_id='a1' * 17), dict(link_id=LINK + '\n'),
            dict(link_id=LINK.encode()), dict(link_id=None),
            dict(node_id=crypto.node_id(other_key)), dict(node_id='b2' * 31), dict(node_id=None),
            dict(node_id=self.fields()['node_id'].upper()), dict(node_key=other_key),
            dict(node_key=b'n' * 31), dict(node_key=b'n' * 33), dict(node_key='6e' * 32), dict(node_key=None),
            dict(private_key=PRIVATE[:31]), dict(private_key=PRIVATE + b'!'), dict(private_key=PRIVATE.hex()),
            dict(private_key=bytearray(PRIVATE)), dict(private_key=None),
            dict(tls_pin='D4' * 32), dict(tls_pin='d4' * 31), dict(tls_pin='d4' * 33), dict(tls_pin='d4' * 32 + '\n'),
            dict(tls_pin=b'd4' * 32), dict(tls_pin=b'\xd4' * 32), dict(tls_pin=None),
            dict(port=0), dict(port=65536), dict(port=-1), dict(port='8090'), dict(port=8090.0), dict(port=True),
            dict(port=None),
            dict(allow_loopback_for_tests=1), dict(allow_loopback_for_tests='yes'),
            dict(allow_loopback_for_tests=None),
            dict(host=''), dict(host='localhost'), dict(host='node'), dict(host='Node-1.example.com'),
            dict(host='node_1.example.com'), dict(host='-node.example.com'), dict(host='node-.example.com'),
            dict(host='node..example.com'), dict(host='.example.com'), dict(host='node-1.example.com.'),
            dict(host='node-1.example.com:8090'), dict(host='admin@node-1.example.com'),
            dict(host='node-1.example.com/x'), dict(host='node-1.example.com\n'), dict(host='node-1.example.123'),
            dict(host='node-1.example.0x7f'), dict(host='n\xf6de.example.com'), dict(host='a' * 64 + '.example.com'),
            dict(host='.'.join(['a' * 61] * 4) + '.example'), dict(host=b'node-1.example.com'), dict(host=None),
            dict(host=8090), dict(host=ipaddress.ip_address(PUBLIC_ADDRESS)),
            dict(host='127.1'), dict(host='2130706433'), dict(host='0x7f000001'), dict(host='0x7f.0.0.1'),
            dict(host='017700000001'), dict(host='010.0.0.1'), dict(host='93.184.216.034'), dict(host='1.2.3'),
            dict(host='1.2.3.4.5'), dict(host='256.1.1.1'), dict(host='1.1.1.1.'), dict(host=' 1.1.1.1'),
            dict(host='1.1.1.1 '), dict(host='1.1.1.1\n'), dict(host='1.1.1.1:8090'),
            dict(host='[2a01:4f8::1]'), dict(host='2A01:4F8::1'), dict(host='2a01:04f8::1'),
            dict(host='2a01:4f8:0:0:0:0:0:1'), dict(host='2a01:4f8::1%eth0'), dict(host='2a01:4f8::1.2.3.4'),
            dict(host='2a01:4f8::1::'), dict(host='::'.join(['2a01'] * 3)), dict(host=':'),
        )
        with mock.patch.object(socket, 'getaddrinfo') as lookup, mock.patch.object(socket, 'socket') as made:
            for change in refused:
                with self.assertRaises(transport.InvalidLink, msg=change) as caught:
                    transport.Link(**self.fields(**change))
                self.assert_no_secret(caught.exception)
                self.assertNotIn('d4' * 31, str(caught.exception))
            lookup.assert_not_called()
            made.assert_not_called()

    def test_a_link_cannot_be_changed_printed_with_its_secrets_or_stored(self):
        link = transport.Link(**self.fields())
        for name in transport.Link.__slots__ + ('other',):
            with self.assertRaises(AttributeError):
                setattr(link, name, getattr(link, name, None))
            with self.assertRaises(AttributeError):
                delattr(link, name)
        self.assertFalse(hasattr(link, '__dict__'))
        self.assertEqual(PUBLIC_ADDRESS, link.host)
        for text in (repr(link), str(link), '%s' % [link]):
            self.assertEqual('Link(%s at %s:8090)' % (LINK, PUBLIC_ADDRESS), text.strip('[]'))
        for store in (pickle.dumps, copy.copy, copy.deepcopy):
            with self.assertRaises(TypeError):
                store(link)

    def test_only_a_link_description_is_sent_through(self):
        link = transport.Link(**self.fields())

        class Lookalike(transport.Link):
            __slots__ = ()
        imitation = collections.namedtuple('Link', transport.Link.__slots__)(*[
            getattr(link, name) for name in transport.Link.__slots__])
        with mock.patch.object(socket, 'getaddrinfo') as lookup, mock.patch.object(socket, 'socket') as made:
            for candidate in (None, self.fields(), imitation, Lookalike(**self.fields()), 'link', transport.Link):
                with self.assertRaises(transport.InvalidLink):
                    transport.send(candidate, 'GET', '/', '', '-', b'', 'admin', 'page')
            lookup.assert_not_called()
            made.assert_not_called()


class RequestFieldTests(Channel):
    def test_a_request_that_cannot_be_signed_is_refused_before_any_connection(self):
        link = transport.Link(**LinkTests.fields(self))
        refused = (
            dict(method='DELETE'), dict(method='post'), dict(method='GET'), dict(method='GET\r\nX-Injected: 1'),
            dict(path='/websites/../users'), dict(path='/websites//x'), dict(path='websites'), dict(path=''),
            dict(path='/websites/x y'), dict(path='/websites/x\r\nX-Injected: 1'), dict(path='/websites/x?a=1'),
            dict(path='/websites/%2e%2e/x'), dict(path='/' + 'a' * 2049), dict(path=b'/websites'), dict(path=None),
            dict(query='a=1\r\nX-Injected: 1'), dict(query='a=1&a=2'), dict(query='a b'), dict(query='?a=1'),
            dict(query='a=1#b'), dict(query='a=' + 'b' * 4097), dict(query=None),
            dict(content_type='application/json; charset=utf-8'), dict(content_type='Application/JSON'),
            dict(content_type='application/json\r\nX-Injected: 1'), dict(content_type=''), dict(content_type=None),
            dict(body='text'), dict(body=None), dict(body=bytearray(REQUEST_BODY)),
            dict(actor=''), dict(actor='a b'), dict(actor='admin\r\nCookie: sessionid=1'), dict(actor='x' * 51),
            dict(actor=None),
            dict(mode='shell'), dict(mode=''), dict(mode='json\r\n'), dict(mode=None),
            dict(now='1795000000'), dict(now=1795000000.5), dict(now=-1), dict(now=True), dict(now=10 ** 11),
            dict(nonce='c3' * 15), dict(nonce='C3' * 16), dict(nonce=NONCE + '\r\n'), dict(nonce=NONCE.encode()),
            dict(nonce=''),
        )
        with mock.patch.object(socket, 'getaddrinfo') as lookup, mock.patch.object(socket, 'socket') as made:
            for change in refused:
                with self.assertRaises(transport.InvalidRequest, msg=change) as caught:
                    self.send(None, link=link, **change)
                self.assert_no_secret(caught.exception)
            self.assertEqual(8 * 1024 * 1024, transport.MAX_REQUEST_BODY)
            with mock.patch.object(transport, 'MAX_REQUEST_BODY', len(REQUEST_BODY) - 1):
                with self.assertRaises(transport.InvalidRequest):
                    self.send(None, link=link)
            lookup.assert_not_called()
            made.assert_not_called()

    def test_a_request_as_large_as_allowed_is_sent_whole(self):
        body = os.urandom(1024 * 1024)
        node = self.node()
        with mock.patch.object(transport, 'MAX_REQUEST_BODY', len(body)):
            self.assertEqual((200, 'application/json', REPLY_BODY),
                             self.send(node, body=body, content_type='application/octet-stream'))
        self.assertEqual(body, node.finished()['seen'].body)


class SecretTests(Channel):
    def test_no_refusal_of_any_kind_shows_a_key_a_signature_a_body_or_the_pin(self):
        node = self.node()
        impostor = self.node(certificate='impostor')
        inside = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.5', 8090))]
        with mock.patch.object(transport, 'DEADLINE', 0.5), \
                mock.patch.object(socket, 'getaddrinfo', return_value=inside):
            errors = [
                self.refused(transport.BadSignature, self.node(reply(signed=dict(body=b'{}')))),
                self.refused(transport.BadSignature, self.node(reply(signature=False))),
                self.refused(transport.MalformedResponse, self.node(reply(then=REPLY_BODY))),
                self.refused(transport.MalformedResponse,
                             self.node(reply(content_type='reply-body-secret', signed=dict(content_type='-')))),
                self.refused(transport.ResponseTooLarge, self.node(reply(length='9' * 18))),
                self.refused(transport.RedirectRefused, self.node(reply(status=302))),
                self.refused(transport.TimedOut, self.node(reply(hold=True))),
                self.refused(transport.ConnectionFailed, self.node(lambda node, connection, seen: None)),
                self.refused(transport.CertificateMismatch, impostor, link=self.link(impostor, tls_pin=pin('node'))),
                self.refused(transport.RefusedAddress, node, link=self.link(node, host='node-1.example.com')),
                self.refused(transport.InvalidRequest, node, path='/' + REQUEST_BODY.decode()),
                self.refused(transport.InvalidRequest, node, actor=PRIVATE.decode() + '\n'),
                self.refused(transport.InvalidRequest, node, nonce=pin('node')),
            ]
        for change in (dict(tls_pin=pin('node') + '0'), dict(private_key=PRIVATE + b'!'),
                       dict(node_key=PRIVATE), dict(host=PRIVATE.decode()), dict(link_id=PRIVATE.hex())):
            with self.assertRaises(transport.InvalidLink) as caught:
                self.link(node, **change)
            errors.append(caught.exception)
        self.assertEqual(
            {transport.BadSignature, transport.MalformedResponse, transport.ResponseTooLarge,
             transport.RedirectRefused, transport.TimedOut, transport.ConnectionFailed,
             transport.CertificateMismatch, transport.RefusedAddress, transport.InvalidRequest,
             transport.InvalidLink}, set(type(error) for error in errors))
        for error in errors:
            self.assert_no_secret(error, node)

    def test_the_search_for_secrets_would_find_one(self):
        node = self.node()
        self.send(node)
        for secret in (pin('node'), PRIVATE.hex(), PRIVATE.decode(), REPLY_BODY.decode(), node.signatures[0],
                       node.signatures[1], node.public.hex()):
            with self.assertRaises(AssertionError):
                self.assert_no_secret(transport.TransportError('Refused: %s.' % secret), node)
            try:
                try:
                    raise ValueError(secret)
                except ValueError:
                    raise transport.TransportError('Refused.') from None
            except transport.TransportError as error:
                with self.assertRaises(AssertionError):
                    self.assert_no_secret(error, node)


class CompatibilityTests(unittest.TestCase):
    """The panel also runs on Python 3.6 with cryptography 3.2.1 (AlmaLinux 8)."""
    SOURCES = (Path(__file__).with_name('transport.py'), Path(__file__))

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check for an older Python here')
    def test_sources_parse_as_python_3_6(self):
        for source in self.SOURCES:
            ast.parse(source.read_text(), feature_version=(3, 6))

    def test_only_the_standard_library_and_the_signing_module_are_imported(self):
        tree = ast.parse(self.SOURCES[0].read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertEqual({'hashlib', 'hmac', 'ipaddress', 'os', 're', 'socket', 'ssl', 'threading', 'time',
                          'multiServer'}, imported)

    def test_nothing_newer_than_python_3_6_is_used_without_a_fallback(self):
        tree = ast.parse(self.SOURCES[0].read_text())
        used = set(node.attr for node in ast.walk(tree)
                   if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) and node.value.id == 'ssl')
        self.assertEqual({'SSLContext', 'PROTOCOL_TLS_CLIENT', 'CERT_NONE', 'TLSVersion', 'OP_NO_TLSv1',
                          'OP_NO_TLSv1_1'}, used)
        for source in self.SOURCES:
            names = set(node.attr for node in ast.walk(ast.parse(source.read_text()))
                        if isinstance(node, ast.Attribute))
            self.assertFalse(names & {'removeprefix', 'removesuffix', 'kwargs', 'capture_output', 'utcnow',
                                      'create_default_context', 'private_bytes_raw', 'public_bytes_raw',
                                      'not_valid_after_utc'}, names)


if __name__ == '__main__':
    unittest.main()
