"""The gateway on a managed server: absent for the panel, exact for a controller.

The first classes need only Python and run anywhere. The others start the
panel's Django and work in a MariaDB database of their own, so they run only on
a server marked as a disposable test server (see multiServer/testing.py): first
through the panel's own middleware with Django's test client, then over TLS
with the controller's real client (multiServer/transport.py).
"""
import ast
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import ssl
import subprocess
import sys
import threading
import unittest
from unittest.mock import MagicMock, PropertyMock, patch
from wsgiref import simple_server

from multiServer import crypto, keys, nodeGateway, schema, switch, testing, transport
from multiServer import test_transport as wire

SKIP = testing.unavailable()
if SKIP is None:
    testing.start_django()
    from django.conf import settings
    from django.contrib.sessions.backends.db import SessionStore
    from django.contrib.sessions.middleware import SessionMiddleware
    from django.contrib.sessions.models import Session
    from django.core.handlers.wsgi import WSGIHandler
    from django.db import connection
    from django.test import Client, RequestFactory, override_settings
    from baseTemplate.models import CyberPanelCosmetic
    from firewall.models import FirewallRules
    from loginSystem.models import ACL, Administrator
    from plogical.acl import ACLManager
    from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
    from multiServer import models, views

GATEWAY = 'multiServer.nodeGateway.NodeGateway'
HELLO = nodeGateway.HELLO
LINK, OTHER_LINK = 'a1' * 16, 'b2' * 16
CONTROLLER = hashlib.sha256(b'the controller of this link').digest()
STRANGER = hashlib.sha256(b'somebody else').digest()
IDENTITY = hashlib.sha256(b'the identity of this node').digest()
NODE_KEY = crypto.public_key(IDENTITY)
NODE = crypto.node_id(NODE_KEY)
HOST = 'node.example.com:8090'
NOW = 1795000000
BODY = b'{"domainName": "request-body-secret.example.com"}'
FIELDS = ('link', 'node', 'timestamp', 'nonce', 'actor', 'mode', 'signature')
SIGNED_HEADERS = dict((field, 'HTTP_' + transport.HEADERS[field].upper().replace('-', '_')) for field in FIELDS)
ROOT = Path(__file__).resolve().parent.parent


class Clock(object):
    """Stands in for the time module inside the gateway alone."""

    def __init__(self, now):
        self.now = now

    def time(self):
        return self.now + 0.6


def sign(key=CONTROLLER, **changes):
    """The X-CPMS-* values of one signed request, by field, and the bytes that were signed."""
    fields = dict(link_id=LINK, node_id=NODE, method='GET', host=HOST, path=HELLO, query='', content_type='-',
                  body=b'', timestamp=NOW, nonce=None, actor='admin', mode='json')
    fields.update(changes)
    if fields['nonce'] is None:
        fields['nonce'] = secrets.token_hex(16)
    message = crypto.request_message(**fields)
    named = dict(link=fields['link_id'], node=fields['node_id'], timestamp=str(fields['timestamp']),
                 nonce=fields['nonce'], actor=fields['actor'], mode=fields['mode'],
                 signature=crypto.sign(key, message).hex())
    return named, message


class FakeRequest(object):
    def __init__(self, **meta):
        self.META = dict(REQUEST_METHOD='GET', PATH_INFO='/base/', QUERY_STRING='', REMOTE_ADDR='203.0.113.9',
                         HTTP_HOST='panel.example.com:8090', HTTP_COOKIE='cyberpanel_sessionid=abc',
                         HTTP_X_FORWARDED_FOR='198.51.100.7', HTTP_AUTHORIZATION='Basic YWRtaW46eA==')
        self.META.update(meta)


class InertTests(unittest.TestCase):
    """Without the role of a managed server, or without an X-CPMS-* header, the middleware is not there."""

    def setUp(self):
        role = patch.object(switch, 'active_role', return_value=keys.NODE)
        self.role = role.start()
        self.addCleanup(role.stop)
        self.answer = object()
        self.next = MagicMock(return_value=self.answer)
        self.gateway = nodeGateway.NodeGateway(self.next)

    def passes_untouched(self, request):
        meta, attributes = dict(request.META), dict(vars(request))
        self.assertIs(self.answer, self.gateway(request))
        self.next.assert_called_once_with(request)
        self.assertIs(request, self.next.call_args[0][0])
        self.assertEqual(meta, request.META)
        self.assertEqual(attributes, vars(request))
        self.next.reset_mock()

    def test_an_ordinary_request_is_handed_on_as_it_came_and_the_role_is_not_even_read(self):
        for role in (keys.NODE, keys.CONTROLLER, keys.OFF):
            self.role.return_value = role
            self.passes_untouched(FakeRequest())
            self.passes_untouched(FakeRequest(REQUEST_METHOD='POST', CONTENT_LENGTH='9', CONTENT_TYPE='text/plain'))
        self.role.assert_not_called()

    def test_only_a_header_under_the_prefix_makes_a_request_the_gateways(self):
        for name in ('HTTP_X_CPMS', 'HTTP_X_CPMSLINK', 'HTTP_XCPMS_LINK', 'X_CPMS_LINK', 'HTTP_X_CPMS-LINK',
                     'http_x_cpms_link', 'HTTP_Y_X_CPMS_LINK', 'REDIRECT_HTTP_X_CPMS_LINK'):
            self.passes_untouched(FakeRequest(**{name: LINK}))
        self.role.assert_not_called()
        self.role.return_value = keys.OFF
        for name in ('HTTP_X_CPMS_', 'HTTP_X_CPMS_LINK', 'HTTP_X_CPMS_SIGNATURE', 'HTTP_X_CPMS_ANYTHING_ELSE'):
            self.passes_untouched(FakeRequest(**{name: LINK}))
            self.role.assert_called_once_with()
            self.role.reset_mock()

    def test_on_a_server_that_is_not_a_managed_server_a_signed_request_is_an_ordinary_one(self):
        named, _ = sign()
        signed = dict((SIGNED_HEADERS[field], value) for field, value in named.items())
        for role in (keys.OFF, keys.CONTROLLER, 'anything else', None):
            self.role.return_value = role
            self.passes_untouched(FakeRequest(**signed))

    def test_what_the_panel_raises_for_an_ordinary_request_is_still_raised(self):
        failure = RuntimeError('the panel failed as it always did')
        self.next.side_effect = failure
        for request in (FakeRequest(), FakeRequest(HTTP_X_CPMS_LINK=LINK)):
            self.role.return_value = keys.OFF
            with self.assertRaises(RuntimeError) as raised:
                self.gateway(request)
            self.assertIs(failure, raised.exception)

    def test_loading_the_gateway_and_passing_requests_on_needs_nothing_but_the_standard_library(self):
        code = ('import sys\n'
                'from multiServer import nodeGateway, switch\n'
                'class R(object):\n'
                '    META = {"REQUEST_METHOD": "GET", "HTTP_COOKIE": "a=b"}\n'
                'assert nodeGateway.NodeGateway(lambda request: 7)(R()) == 7\n'
                'R.META["HTTP_X_CPMS_LINK"] = "x"\n'
                'assert switch.active_role() == "off"\n'
                'assert nodeGateway.NodeGateway(lambda request: 8)(R()) == 8\n'
                'loaded = [name for name in sys.modules if name.split(".")[0] in ("django", "cryptography", '
                '"MySQLdb", "plogical", "loginSystem")]\n'
                'assert not loaded, loaded\n')
        with patch.dict(os.environ, {'PYTHONPATH': str(ROOT)}):
            subprocess.check_call([sys.executable, '-c', code], cwd=str(ROOT))


class TableTests(unittest.TestCase):
    def test_the_gateway_reads_exactly_the_headers_the_controller_writes(self):
        self.assertEqual(dict((name, field) for field, name in SIGNED_HEADERS.items()), nodeGateway._FIELDS)
        self.assertEqual(set(FIELDS), set(transport.HEADERS))

    def test_one_route_and_no_handler_for_any_other_mode(self):
        self.assertEqual([('json', '/multiserver/gateway/hello')], list(nodeGateway.ROUTES))
        route = nodeGateway.ROUTES[('json', HELLO)]
        self.assertEqual(('hello', 'GET', False), route[:3])
        self.assertEqual({}, nodeGateway.MODE_HANDLERS)
        self.assertEqual(['hello'], nodeGateway.capabilities())
        for mode, _ in nodeGateway.ROUTES:
            self.assertIn(mode, crypto.MODES)

    def test_the_limits_are_the_ones_the_controller_uses(self):
        self.assertEqual(90, nodeGateway.WINDOW)
        self.assertEqual(8 * 1024 * 1024, transport.MAX_REQUEST_BODY)
        self.assertLessEqual(nodeGateway.MAX_REPLY_BODY + transport.MAX_RESPONSE_HEAD, transport.MAX_RESPONSE)


class AddressTests(unittest.TestCase):
    def test_an_address_has_one_form(self):
        for given, expected in (('203.0.113.9', '203.0.113.9'), ('2001:db8::9', '2001:db8::9'),
                                ('2001:DB8:0:0:0:0:0:9', '2001:db8::9'), ('::ffff:203.0.113.9', '203.0.113.9'),
                                ('::FFFF:cb00:7109', '203.0.113.9'), ('::1', '::1'), ('127.0.0.1', '127.0.0.1')):
            self.assertEqual(expected, str(nodeGateway._address(given)), given)

    def test_what_is_not_one_plain_address_is_no_address(self):
        for given in (None, '', b'203.0.113.9', 3405803785, ' 203.0.113.9', '203.0.113.9 ', '203.0.113.9\n',
                      '203.0.113.09', '0203.0.113.9', '203.0.113', '203.0.113.9.1', '203.0.113.9/32',
                      '203.0.113.9,203.0.113.9', '203.0.113.9:8090', '[2001:db8::9]', 'fe80::1%eth0', '2001:db8::9%1',
                      'localhost', 'unknown', '3405803785', '0xcb.0.113.9', 'a' * 46):
            self.assertIsNone(nodeGateway._address(given), repr(given))

    def test_a_link_allows_exactly_the_addresses_it_lists(self):
        allowed = nodeGateway._allowed
        self.assertEqual(['203.0.113.9'], [str(address) for address in allowed('203.0.113.9')])
        self.assertEqual(['203.0.113.9', '2001:db8::9', '198.51.100.7'],
                         [str(address) for address in allowed('203.0.113.9,2001:db8::9,198.51.100.7')])
        self.assertIn(nodeGateway._address('::ffff:198.51.100.7'), allowed('203.0.113.9,198.51.100.7'))
        self.assertNotIn(nodeGateway._address('198.51.100.8'), allowed('203.0.113.9,198.51.100.7'))

    def test_a_list_with_one_entry_that_is_not_a_plain_address_allows_nobody(self):
        for listed in (None, '', ',', '203.0.113.9,', ',203.0.113.9', '203.0.113.9, 198.51.100.7', ' 203.0.113.9',
                       '203.0.113.9;198.51.100.7', '203.0.113.9 198.51.100.7', '203.0.113.0/24', '0.0.0.0/0', '*',
                       '203.0.113.9,*', '203.0.113.9,any', '2001:DB8::9', '2001:db8:0::9', '::ffff:203.0.113.9',
                       '203.0.113.9,::ffff:198.51.100.7', '203.0.113.009', b'203.0.113.9', ['203.0.113.9']):
            self.assertEqual(0, len(nodeGateway._allowed(listed)), repr(listed))


class CompatibilityTests(unittest.TestCase):
    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_sources_parse_as_python_3_6(self):
        directory = Path(__file__).resolve().parent
        for name in ('nodeGateway.py', 'views.py', 'test_gateway.py'):
            ast.parse((directory / name).read_text(), feature_version=(3, 6))


def snapshot(response):
    """Everything of a reply that reaches the wire: status line, headers in their order, cookies, body."""
    return (response.status_code, response.reason_phrase, response.serialize(),
            tuple(sorted(cookie.output() for cookie in response.cookies.values())))


@unittest.skipIf(SKIP, SKIP)
class Panel(unittest.TestCase):
    """The panel on a database of its own: a managed server with one administrator and one active link."""

    @classmethod
    def setUpClass(cls):
        cls.database = testing.ScratchDatabase()
        try:
            cls.database.give_to_django()
            cls.ready = patch.object(schema, '_READY', False)
            cls.ready.start()
            with connection.cursor() as cursor:
                schema.ensure_tables(connection, cursor)
            with connection.schema_editor() as editor:
                for model in (ACL, Administrator, Session, FirewallRules, CyberPanelCosmetic):
                    editor.create_model(model)
        except BaseException:
            cls.database.drop()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.ready.stop()
        finally:
            cls.database.drop()  # whatever else went wrong, the database does not stay behind

    def setUp(self):
        for name in reversed([table.name for table in schema.TABLES]):
            self.database.run('DELETE FROM `%s`' % name)
        for model in (Session, Administrator, ACL, FirewallRules, CyberPanelCosmetic):
            self.empty(model)
        FirewallRules.objects.create(name='panel', proto='tcp', port='8090')
        CyberPanelCosmetic.objects.create(pk=1)
        self.full = ACL.objects.create(name='admin', adminStatus=1, config=ACLManager.AdminACL)
        self.reseller = ACL.objects.create(name='reseller', config=ACLManager.ResellerACL)
        self.administrator = Administrator.objects.create(
            userName='admin', password='not-a-password', type=1, email='admin@example.com', acl=self.full)
        self.link = models.Link.objects.create(
            link_id=LINK, controller_key=crypto.public_key(CONTROLLER).hex(), pairing_key='d1' * 32,
            allowed_ips='127.0.0.1', admin_id=self.administrator.pk, status=models.ACTIVE, generation=1,
            created_at=NOW - 5000, updated_at=NOW - 5000, activated_at=NOW - 4000, expires_at=NOW + 86400)
        self.clock = Clock(NOW)
        self.log = []
        nodeGateway._NOTED.clear()
        self.role = self.start(patch.object(keys, 'role', return_value=keys.NODE))
        self.identity = self.start(patch.object(keys, 'identity_key', return_value=IDENTITY))
        self.generation = self.start(patch.object(keys, 'generation', return_value=1))
        self.start(patch.object(nodeGateway, 'time', self.clock))
        self.start(patch.object(CyberCPLogFileWriter, 'writeToFile',
                                side_effect=lambda message, *more: self.log.append(message)))
        # Whether the panel's session handling saw a request at all.
        self.sessions = self.start(patch.object(SessionMiddleware, 'process_request', autospec=True,
                                                side_effect=SessionMiddleware.process_request))
        self.client = Client()
        self.seen = []  # (signed bytes, nonce, signature) of every request these tests signed

    def start(self, patcher):
        # Each patch is stopped by itself: patch.stopall() would also end the one the whole class runs under.
        started = patcher.start()
        self.addCleanup(patcher.stop)
        return started

    def empty(self, model):
        # With a plain statement: Django would first look for rows in tables this database does not have.
        self.database.run('DELETE FROM `%s`' % model._meta.db_table)

    # The two answers of this panel to a visitor who is not signed in, at an address that does not exist.

    def absent(self, with_body=False, **environ):
        client = Client()
        if with_body:
            response = client.post('/multiserver/no-such-address', data=b'{"a": 1}', content_type='text/plain',
                                   HTTP_HOST=HOST, **environ)
        else:
            response = client.get('/multiserver/no-such-address', HTTP_HOST=HOST, **environ)
        self.sessions.reset_mock()
        return snapshot(response)

    # Requests.

    def signed(self, key=CONTROLLER, **changes):
        changes.setdefault('timestamp', self.clock.now)
        named, message = sign(key, **changes)
        self.seen.append((message, named['nonce'], named['signature']))
        return named, message

    def deliver(self, named, method='GET', path=HELLO, query='', content_type='-', body=b'', host=HOST,
                **environ):
        """Hand one request to the panel as a web server would: `named` are its X-CPMS-* headers by field."""
        extra = dict((SIGNED_HEADERS.get(field, field), value) for field, value in named.items())
        if host is not None:
            extra['HTTP_HOST'] = host
        if content_type != '-' and not body:
            extra['CONTENT_TYPE'] = content_type
        extra.update(PATH_INFO=path, QUERY_STRING=query)
        extra.update(environ)
        return self.client.generic(method, '/', data=body,
                                   content_type='' if content_type == '-' else content_type, **extra)

    def call(self, sent=None, key=CONTROLLER, environ=None, **signing):
        """Sign a request and deliver it; `sent` changes what is delivered after it was signed.

        Returns the reply, the signed bytes and the headers as they were signed.
        """
        request = dict(method='GET', path=HELLO, query='', content_type='-', body=b'', host=HOST)
        for name in list(signing):
            if name in request:
                request[name] = signing[name]
        named, message = self.signed(key, **signing)
        request.update(sent or {})
        named.update(request.pop('named', {}))
        request.update(environ or {})
        # A header changed to None is a header that is not sent.
        sent = dict((field, value) for field, value in named.items() if value is not None)
        return self.deliver(sent, **request), message, named

    # What must be true afterwards.

    def state(self):
        link = models.Link.objects.filter(pk=LINK).first()
        return (models.Nonce.objects.count(), link and link.last_request_at, Session.objects.count(),
                models.AuditEntry.objects.count())

    def last_audit(self):
        entry = models.AuditEntry.objects.order_by('-id').first()
        return (entry.event, entry.outcome, entry.reason, entry.link_id, entry.actor, entry.source_ip,
                entry.method, entry.path, entry.status, entry.size, entry.dropped)

    def assert_gateway_alone(self, response):
        """The reply came from the gateway: the panel's sessions never saw the request and no cookie is set."""
        self.sessions.assert_not_called()
        self.assertEqual({}, dict(response.cookies))
        self.assertFalse(response.has_header('Set-Cookie'))
        self.assertEqual(str(len(response.content)), response['Content-Length'])

    def refused_unsigned(self, response, reason, before, with_body=False, **audited):
        """Refused before the signature counted: the answer for an absent address, and nothing stored."""
        self.assert_gateway_alone(response)
        self.assertEqual(self.absent(with_body), snapshot(response))
        self.assertFalse(response.has_header(transport.HEADERS['signature']))
        expected = dict(link_id=LINK, source_ip='127.0.0.1', method='GET', path=HELLO, size=0, dropped=0)
        expected.update(audited)
        self.assertEqual(('request', 'refused', reason, expected['link_id'], '', expected['source_ip'],
                          expected['method'], expected['path'], 200 if with_body else 302, expected['size'],
                          expected['dropped']), self.last_audit())
        self.assertEqual(before[:3] + (before[3] + 1,), self.state())

    def assert_signed(self, response, message, named, status, body, link_id=LINK):
        """A reply signed by this server for exactly that request, framed as the controller requires."""
        self.assert_gateway_alone(response)
        self.assertEqual((status, body), (response.status_code, response.content))
        self.assertEqual({'Content-Type': 'application/json', 'Content-Length': str(len(body)),
                          'Cache-Control': 'no-store',
                          'X-CPMS-Signature': response['X-CPMS-Signature']}, dict(response.items()))
        self.assertRegex(response['X-CPMS-Signature'], r'\A[0-9a-f]{128}\Z')
        expected = crypto.response_message(link_id, NODE, named['nonce'], message, status, 'application/json', body)
        self.assertTrue(crypto.verify(NODE_KEY, bytes.fromhex(response['X-CPMS-Signature']), expected))

    def refused_signed(self, response, message, named, reason, status=403, **audited):
        self.assert_signed(response, message, named, status, json.dumps({'error': reason}, separators=(
            ',', ':')).encode())
        expected = dict(method='GET', path=HELLO, size=0, actor='admin')
        expected.update(audited)
        self.assertEqual(('request', 'refused', reason, LINK, expected['actor'], '127.0.0.1', expected['method'],
                          expected['path'], status, expected['size'], 0), self.last_audit())

    def assert_hello(self, response, message, named):
        import cyberpanel_version
        self.assert_signed(response, message, named, 200, json.dumps(
            {'build': cyberpanel_version.BUILD, 'capabilities': ['hello'], 'role': 'node',
             'version': cyberpanel_version.VERSION}, separators=(',', ':')).encode())

    def each_refused(self, reason, cases, with_body=False, **audited):
        for name, options in cases:
            with self.subTest(name):
                before = self.state()
                response = self.call(**options)[0]
                self.refused_unsigned(response, reason, before, with_body, **audited)

    def sign_in(self, client=None):
        session = SessionStore()
        session['userID'] = self.administrator.pk
        session['ipAddr'] = '127.0.0.1'
        session.save()
        (client or self.client).cookies[settings.SESSION_COOKIE_NAME] = session.session_key
        return session.session_key


class HelloTests(Panel):
    def test_the_gateway_is_the_panels_first_middleware(self):
        self.assertEqual(GATEWAY, settings.MIDDLEWARE[0])
        self.assertEqual(1, settings.MIDDLEWARE.count(GATEWAY))
        self.assertEqual('django.contrib.sessions.middleware.SessionMiddleware', settings.MIDDLEWARE[2])
        self.assertEqual('CyberCP.secMiddleware.secMiddleware', settings.MIDDLEWARE[-1])

    def test_a_signed_request_from_the_controller_gets_the_signed_hello(self):
        before = self.state()
        response, message, named = self.call()
        self.assert_hello(response, message, named)
        self.assertEqual(['build', 'capabilities', 'role', 'version'], sorted(json.loads(response.content.decode())))
        self.assertEqual(('request', 'ok', '', LINK, 'admin', '127.0.0.1', 'GET', HELLO, 200, 0, 0),
                         self.last_audit())
        self.assertEqual((before[0] + 1, NOW, before[2], before[3] + 1), self.state())
        self.assertEqual([(LINK, named['nonce'], NOW)],
                         list(models.Nonce.objects.values_list('link_id', 'nonce', 'seen_at')))
        self.assertEqual([], self.log)

    def test_each_request_is_answered_for_itself(self):
        first = self.call()
        second = self.call()
        self.assertNotEqual(first[0]['X-CPMS-Signature'], second[0]['X-CPMS-Signature'])
        self.assert_hello(*first)
        self.assert_hello(*second)
        # The reply to one request is no reply to the other.
        other = crypto.response_message(LINK, NODE, second[2]['nonce'], second[1], 200, 'application/json',
                                        first[0].content)
        self.assertFalse(crypto.verify(NODE_KEY, bytes.fromhex(first[0]['X-CPMS-Signature']), other))

    def test_the_reply_is_made_by_the_gateway_itself_whatever_else_the_request_carries(self):
        key = self.sign_in()
        stored = Session.objects.get(pk=key).session_data
        response, message, named = self.call(environ={
            'HTTP_COOKIE': '%s=%s; django_language=de' % (settings.SESSION_COOKIE_NAME, key),
            'HTTP_AUTHORIZATION': 'Basic YWRtaW46MTIzNDU2Nw==', 'HTTP_X_FORWARDED_FOR': '198.51.100.7',
            'HTTP_ACCEPT_LANGUAGE': 'de', 'HTTP_USER_AGENT': 'Mozilla/5.0', 'HTTP_ORIGIN': 'null'})
        self.assert_hello(response, message, named)
        self.assertEqual([(key, stored)], list(Session.objects.values_list('session_key', 'session_data')))

    def test_an_address_written_as_ipv6_is_the_same_controller(self):
        response, message, named = self.call(environ={'REMOTE_ADDR': '::ffff:127.0.0.1'})
        self.assert_hello(response, message, named)
        models.Link.objects.filter(pk=LINK).update(allowed_ips='203.0.113.9,2001:db8::9')
        for address, recorded in (('2001:db8:0:0:0:0:0:9', '2001:db8::9'), ('203.0.113.9', '203.0.113.9')):
            response, message, named = self.call(environ={'REMOTE_ADDR': address})
            self.assert_hello(response, message, named)
            self.assertEqual(recorded, self.last_audit()[5])

    def test_requests_in_one_second_and_in_later_seconds_are_all_accepted(self):
        for step in (0, 0, 0, 1, 1, 30, 90):
            self.assert_hello(*self.call(timestamp=NOW + step))
        self.assertEqual((7, NOW + 90), self.state()[:2])

    def test_the_edges_of_the_time_window_are_inside_it(self):
        self.assert_hello(*self.call(timestamp=NOW - 90))
        self.assert_hello(*self.call(timestamp=NOW + 90))
        self.clock.now += 180
        self.assert_hello(*self.call(timestamp=NOW + 90))


class FormatTests(Panel):
    def test_every_link_header_is_required_once_and_in_its_exact_form(self):
        cases = []
        for field in FIELDS:
            value = self.signed()[0][field]
            cases.append(('without ' + field, dict(sent={'named': {field: None}})))
            cases.append(('empty ' + field, dict(sent={'named': {field: ''}})))
            for name, changed in (('twice', value + ',' + value), ('twice with a space', value + ', ' + value),
                                  ('padded', ' ' + value), ('trailing', value + ' '), ('newline', value + '\n')):
                cases.append(('%s %s' % (field, name), dict(sent={'named': {field: changed}})))
        for field in ('link', 'node', 'nonce', 'signature'):
            value = self.signed()[0][field]
            for name, changed in (('upper case', value.upper()), ('short', value[:-1]), ('long', value + '0'),
                                  ('not hex', 'g' + value[1:])):
                cases.append(('%s %s' % (field, name), dict(sent={'named': {field: changed}})))
        for changed in ('0%d' % NOW, '+%d' % NOW, '%d.0' % NOW, '%de0' % NOW, '-1', '1' * 12, 'now',
                        '١٧٩٥٠٠٠٠٠٠'):
            cases.append(('timestamp %r' % changed, dict(sent={'named': {'timestamp': changed}})))
        for changed in ('JSON', 'Json', 'relay', 'json,json', 'js'):
            cases.append(('mode %r' % changed, dict(sent={'named': {'mode': changed}})))
        for changed in ('a' * 51, 'ad min', 'admin;', 'admïn', '<admin>'):
            cases.append(('actor %r' % changed, dict(sent={'named': {'actor': changed}})))
        self.malformed(cases)

    def malformed(self, cases, **audited):
        # Nothing of a malformed request is taken for a link or a length.
        self.each_refused('format', cases, **dict(dict(link_id='', size=None), **audited))

    def test_a_header_under_the_prefix_that_the_link_does_not_use_is_refused(self):
        self.malformed([(name, dict(environ={name: '1'})) for name in (
            'HTTP_X_CPMS_EXTRA', 'HTTP_X_CPMS_', 'HTTP_X_CPMS_LINK_ID', 'HTTP_X_CPMS_BODY_HASH')])

    def test_a_single_link_header_is_enough_to_be_refused_here_and_not_served_by_the_panel(self):
        self.sign_in()
        before = self.state()
        response = self.client.get('/multiserver/status', HTTP_HOST=HOST, HTTP_X_CPMS_LINK=LINK)
        self.refused_unsigned(response, 'format', before, link_id='', path='/multiserver/status', size=None)
        self.sessions.reset_mock()
        self.assertEqual(200, self.client.get('/multiserver/status', HTTP_HOST=HOST).status_code)

    def test_only_get_and_post_as_written(self):
        self.malformed([(method, dict(sent={'method': method})) for method in (
            'HEAD', 'PUT', 'DELETE', 'PATCH', 'OPTIONS', 'TRACE', 'CONNECT', 'get', 'Get', 'post', 'GET ', 'GETS')],
            method='')

    def test_the_host_is_required_with_its_port(self):
        self.malformed([(repr(host), dict(sent={'host': host})) for host in (
            None, '', 'node.example.com', 'node.example.com:', 'node.example.com:0', 'node.example.com:65536',
            'node.example.com:8090,node.example.com:8090', 'node.example.com:8090 ', 'node example:8090',
            'user@node.example.com:8090', 'node.example.com:8090/', '2001:db8::9:8090')])

    def test_the_path_and_query_must_be_ones_a_controller_can_sign(self):
        # As a web server hands them over: the path decoded, the query as it was sent.
        for name, path in (('double slash', '//multiserver/gateway/hello'), ('dot', '/multiserver/./gateway/hello'),
                           ('parent', '/multiserver/gateway/../gateway/hello'),
                           ('semicolon', '/multiserver/gateway/hello;v=1'), ('space', '/multiserver/gateway/hel lo'),
                           ('newline', '/multiserver/gateway/hello\n'), ('null', '/multiserver/gateway/hello\x00'),
                           ('unicode', '/multiserver/gateway/h\xc3\xa9llo'),
                           ('percent', '/multiserver/gateway/%68ello'),
                           ('backslash', '/multiserver/gateway\\hello'), ('long', '/' + 'a' * 2048)):
            with self.subTest(name):
                before = self.state()
                response = self.call(sent={'path': path})[0]
                self.assert_gateway_alone(response)
                self.assertEqual(('refused', 'format', ''), self.last_audit()[1:4])
                self.assertEqual(self.absent(), snapshot(response))
                self.assertEqual(before[:3], self.state()[:3])
        self.malformed([(repr(query), dict(sent={'query': query})) for query in (
            'a=1&a=2', 'a b', 'a=<b>', "a='", 'a=1#b', 'a=\xe9', 'a=' + 'b' * 4096)])

    def test_the_content_type_must_be_a_bare_lower_case_media_type(self):
        self.malformed([(repr(media_type), dict(sent={'content_type': media_type})) for media_type in (
            'application/json; charset=utf-8', 'Application/JSON', 'application/json ', 'json',
            'application/json,application/json', 'text/plain;', '*/*')])
        # A header that says "-" is not the absence of the header, which is what "-" stands for when signed.
        self.malformed([('dash', dict(environ={'CONTENT_TYPE': '-'}))])

    def test_a_coded_request_is_refused(self):
        self.malformed([(repr(environ), dict(environ=environ)) for environ in (
            {'HTTP_TRANSFER_ENCODING': 'chunked'}, {'HTTP_TRANSFER_ENCODING': 'identity'},
            {'HTTP_TRANSFER_ENCODING': ''}, {'HTTP_CONTENT_ENCODING': 'gzip'}, {'HTTP_CONTENT_ENCODING': ''})])
        self.assert_hello(*self.call(environ={'HTTP_CONTENT_ENCODING': 'identity'}))

    def test_the_declared_length_must_be_a_plain_number(self):
        for length in ('1x', '+1', '01', '1.0', ' 1', '-1', '0x1', '1' * 19):
            with self.subTest(length):
                before = self.state()
                response = self.call(method='POST', environ={'CONTENT_LENGTH': length})[0]
                self.assertEqual(('refused', 'format'), self.last_audit()[1:3])
                self.assertEqual(before[:3], self.state()[:3])
                self.assert_gateway_alone(response)
                self.assertFalse(response.has_header('X-CPMS-Signature'))

    def test_a_malformed_request_is_refused_as_such_whatever_else_is_wrong_with_it(self):
        # Unknown link, wrong address, old time and no valid signature: the form is looked at first.
        before = self.state()
        response = self.call(key=STRANGER, link_id=OTHER_LINK, timestamp=NOW - 500,
                             sent={'named': {'nonce': 'NOT-A-NONCE'}}, environ={'REMOTE_ADDR': '198.51.100.7'})[0]
        self.refused_unsigned(response, 'format', before, link_id='', source_ip='198.51.100.7', size=None)


class SizeTests(Panel):
    LIMIT = transport.MAX_REQUEST_BODY

    def test_a_declared_length_over_the_limit_is_refused_and_nothing_of_the_body_is_kept(self):
        before = self.state()
        with patch('django.http.request.HttpRequest.body', new_callable=PropertyMock) as body:
            response = self.call(method='POST', environ={'CONTENT_LENGTH': str(self.LIMIT + 1)})[0]
        body.assert_not_called()
        self.refused_unsigned(response, 'size', before, with_body=True, method='POST', size=self.LIMIT + 1,
                              link_id='')
        before = self.state()
        response = self.call(method='POST', body=b'x' * (self.LIMIT + 1), content_type='text/plain')[0]
        self.refused_unsigned(response, 'size', before, with_body=True, method='POST', size=self.LIMIT + 1,
                              link_id='')

    def test_a_body_of_exactly_the_limit_is_read_and_verified(self):
        body = b'x' * self.LIMIT
        response, message, named = self.call(method='POST', body=body, content_type='text/plain')
        self.refused_signed(response, message, named, 'not_allowed', method='POST', size=self.LIMIT)

    def test_a_get_has_no_body(self):
        before = self.state()
        response = self.call(sent={'body': b'x', 'content_type': 'text/plain'})[0]
        self.refused_unsigned(response, 'size', before, with_body=True, size=1, link_id='')

    def test_a_body_that_is_not_as_long_as_declared_is_refused(self):
        for declared in (len(BODY) + 1, len(BODY) + 4096):
            before = self.state()
            # A stream that ends, as a closed connection does, in place of the test client's own.
            response = self.call(method='POST', body=BODY, content_type='application/json',
                                 environ={'CONTENT_LENGTH': str(declared), 'wsgi.input': io.BytesIO(BODY)})[0]
            self.refused_unsigned(response, 'size', before, with_body=True, method='POST', size=declared)
        # Declared shorter, the rest is never read: what was read is not what was signed.
        before = self.state()
        response = self.call(method='POST', body=BODY, content_type='application/json',
                             environ={'CONTENT_LENGTH': str(len(BODY) - 1)})[0]
        self.refused_unsigned(response, 'signature', before, with_body=True, method='POST', size=len(BODY) - 1)

    def test_nobody_who_fails_an_earlier_check_makes_this_server_keep_a_body(self):
        models.Link.objects.filter(pk=LINK).update(allowed_ips='203.0.113.9')
        for reason, options in (('link', dict(link_id=OTHER_LINK)), ('source_ip', dict()),
                                ('time', dict(timestamp=NOW - 500, environ={'REMOTE_ADDR': '203.0.113.9'}))):
            with patch('django.http.request.HttpRequest.body', new_callable=PropertyMock) as body:
                self.call(method='POST', body=BODY, content_type='application/json', **options)
            body.assert_not_called()
            self.assertEqual(reason, self.last_audit()[2])

    def test_a_body_that_cannot_be_read_is_refused(self):
        # A closed connection, and the error the panel's own web server gives for a read that failed.
        for error in (OSError('connection reset'), SystemError('error return without exception set')):
            before = self.state()
            with patch('django.core.handlers.wsgi.LimitedStream.read', side_effect=error):
                response = self.call(method='POST', body=BODY, content_type='application/json')[0]
            self.refused_unsigned(response, 'size', before, with_body=True, method='POST', size=len(BODY))
        self.assertEqual([], self.log)

    def test_a_request_is_taken_whole_from_the_server_whatever_the_answer(self):
        # The next request arrives on the same stream: the declared body must be gone from it, and no more.
        post = dict(method='POST', body=BODY, content_type='application/json')
        for reason, options in (('format', dict(sent={'named': {'nonce': 'x'}})), ('link', dict(link_id=OTHER_LINK)),
                                ('link', dict(node_id='0' * 64)),
                                ('source_ip', dict(environ={'REMOTE_ADDR': '198.51.100.7'})),
                                ('time', dict(timestamp=NOW - 500)), ('signature', dict(key=STRANGER)),
                                ('not_allowed', dict()), ('not_allowed', dict(mode='page'))):
            with self.subTest(reason):
                stream = io.BytesIO(BODY + b'the next request')
                environ = dict(options.pop('environ', {}))
                environ['wsgi.input'] = stream
                self.call(environ=environ, **dict(post, **options))
                self.assertEqual(reason, self.last_audit()[2])
                self.assertEqual(b'the next request', stream.read())
        stream = io.BytesIO(b'x' * (self.LIMIT + 1) + b'the next request')
        self.call(method='POST', body=b'x', content_type='text/plain',
                  environ={'CONTENT_LENGTH': str(self.LIMIT + 1), 'wsgi.input': stream})
        self.assertEqual('size', self.last_audit()[2])
        self.assertEqual(b'the next request', stream.read())

    def test_a_body_that_cannot_be_taken_does_not_stop_the_answer(self):
        class Broken(object):
            def read(self, *arguments):
                raise RuntimeError('the stream failed')
            readline = read
        before = self.state()
        response = self.call(key=STRANGER, link_id=OTHER_LINK, method='POST', body=BODY,
                             content_type='application/json', environ={'wsgi.input': Broken()})[0]
        self.refused_unsigned(response, 'link', before, with_body=True, method='POST', size=len(BODY), link_id='')


class LinkTests(Panel):
    def refused(self, reason, **options):
        before = self.state()
        audited = options.pop('audited', {})
        self.refused_unsigned(self.call(**options)[0], reason, before, **audited)

    def test_an_unknown_link_is_refused(self):
        # The audit trail does not take a caller's word for the name of a link.
        before = self.state()
        self.refused_unsigned(self.call(link_id=OTHER_LINK)[0], 'link', before, link_id='')
        # Even one signed with a key this server knows, for another link.
        before = self.state()
        self.refused_unsigned(self.call(link_id='a1' * 15 + 'a2')[0], 'link', before, link_id='')

    def test_only_an_active_link_carries_a_request(self):
        for status in (models.PENDING, models.PAUSED, models.REVOKED, '', 'ACTIVE', 'active '):
            with self.subTest(status):
                models.Link.objects.filter(pk=LINK).update(status=status)
                self.refused('link')
        models.Link.objects.filter(pk=LINK).update(status=models.ACTIVE)
        self.assert_hello(*self.call())

    def test_an_expired_link_is_refused_from_the_second_it_expires(self):
        models.Link.objects.filter(pk=LINK).update(expires_at=NOW + 1)
        self.assert_hello(*self.call())
        for expires_at in (NOW, NOW - 1, 0):
            models.Link.objects.filter(pk=LINK).update(expires_at=expires_at)
            self.refused('expired')

    def test_a_link_of_another_generation_is_refused(self):
        for stored, current in ((1, 2), (2, 1), (1, 0), (0, 0), (0, 1), (-1, -1)):
            with self.subTest(stored=stored, current=current):
                models.Link.objects.filter(pk=LINK).update(generation=stored)
                self.generation.return_value = current
                self.refused('generation')
        models.Link.objects.filter(pk=LINK).update(generation=7)
        self.generation.return_value = 7
        self.assert_hello(*self.call())

    def test_the_generation_is_read_for_every_request(self):
        self.assert_hello(*self.call())
        self.assert_hello(*self.call())
        self.assertEqual(2, self.generation.call_count)
        self.generation.return_value = 2  # what a revocation does, in every worker at once
        self.refused('generation')

    def test_a_request_for_another_server_is_refused(self):
        other = crypto.node_id(crypto.public_key(STRANGER))
        self.refused('link', node_id=other, audited={'link_id': ''})
        # And when this server's own key is not the one the controller paired with.
        self.identity.return_value = STRANGER
        self.refused('link', audited={'link_id': ''})

    def test_a_link_without_a_usable_controller_key_is_refused(self):
        for stored in ('', 'zz' * 32, 'AB' * 32, 'ab' * 31, 'ab' * 31 + 'a '):
            models.Link.objects.filter(pk=LINK).update(controller_key=stored)
            self.refused('link')

    def test_without_an_identity_key_nothing_is_served(self):
        self.identity.return_value = None
        self.refused('internal', audited={'link_id': ''})
        # Nothing is written to the panel's log for it: anybody can send this request.
        self.assertEqual([], self.log)

    def test_the_link_is_looked_at_before_the_address_the_time_and_the_signature(self):
        models.Link.objects.filter(pk=LINK).update(status=models.PAUSED)
        self.refused('link', key=STRANGER, timestamp=NOW - 500, environ={'REMOTE_ADDR': '198.51.100.7'},
                     audited={'source_ip': '198.51.100.7'})


class SourceTests(Panel):
    FORGED = ('HTTP_X_FORWARDED_FOR', 'HTTP_FORWARDED', 'HTTP_X_REAL_IP', 'HTTP_CF_CONNECTING_IP',
              'HTTP_X_CLIENT_IP', 'HTTP_CLIENT_IP', 'HTTP_TRUE_CLIENT_IP', 'HTTP_X_CLUSTER_CLIENT_IP',
              'HTTP_X_FORWARDED', 'HTTP_FORWARDED_FOR', 'HTTP_X_ORIGINAL_FORWARDED_FOR', 'HTTP_X_CYBERPANEL_PEER')

    def test_a_request_from_another_address_is_refused(self):
        for address in ('127.0.0.2', '203.0.113.9', '::1', '2001:db8::9', '::ffff:127.0.0.2', '0.0.0.0'):
            with self.subTest(address):
                before = self.state()
                response = self.call(environ={'REMOTE_ADDR': address})[0]
                self.refused_unsigned(response, 'source_ip', before,
                                      source_ip=str(nodeGateway._address(address)))

    def test_an_address_the_server_cannot_name_is_refused(self):
        for address in ('', 'unknown', '127.0.0.1, 127.0.0.1', '127.0.0.1:51324', '127.0.0.01', 'localhost',
                        'fe80::1%eth0'):
            with self.subTest(address):
                before = self.state()
                response = self.call(environ={'REMOTE_ADDR': address})[0]
                self.refused_unsigned(response, 'source_ip', before, source_ip='')

    def test_no_header_can_stand_in_for_the_address_of_the_connection(self):
        models.Link.objects.filter(pk=LINK).update(allowed_ips='203.0.113.9')
        forged = dict((name, '203.0.113.9') for name in self.FORGED)
        forged['HTTP_FORWARDED'] = 'for=203.0.113.9;proto=https'
        before = self.state()
        self.refused_unsigned(self.call(environ=forged)[0], 'source_ip', before)
        for name, value in forged.items():
            before = self.state()
            self.refused_unsigned(self.call(environ={name: value})[0], 'source_ip', before)
        # The other way round: the controller's own address counts whatever the headers claim.
        forged['REMOTE_ADDR'] = '203.0.113.9'
        forged.update((name, '198.51.100.7') for name in self.FORGED)
        response, message, named = self.call(environ=forged)
        self.assert_hello(response, message, named)
        self.assertEqual('203.0.113.9', self.last_audit()[5])

    def test_a_list_that_is_not_plain_addresses_allows_nobody(self):
        for listed in ('', '127.0.0.1,', '127.0.0.1, 127.0.0.2', '127.0.0.0/8', '0.0.0.0/0', '*', '127.0.0.01',
                       '::ffff:127.0.0.1'):
            with self.subTest(listed):
                models.Link.objects.filter(pk=LINK).update(allowed_ips=listed)
                before = self.state()
                self.refused_unsigned(self.call()[0], 'source_ip', before)

    def test_the_address_is_looked_at_before_the_time_and_the_signature(self):
        before = self.state()
        response = self.call(key=STRANGER, timestamp=NOW - 500, environ={'REMOTE_ADDR': '198.51.100.7'})[0]
        self.refused_unsigned(response, 'source_ip', before, source_ip='198.51.100.7')


class TimeTests(Panel):
    def refused(self, **options):
        before = self.state()
        self.refused_unsigned(self.call(**options)[0], 'time', before)

    def test_a_request_signed_outside_the_window_is_refused(self):
        for timestamp in (NOW - 91, NOW + 91, NOW - 3600, NOW + 3600, 0, NOW - 86400 * 365, 10 ** 11 - 1):
            with self.subTest(timestamp):
                self.refused(timestamp=timestamp)

    def test_a_request_older_than_the_newest_accepted_one_is_refused(self):
        self.assert_hello(*self.call(timestamp=NOW + 5))
        for timestamp in (NOW + 4, NOW, NOW - 60):
            self.refused(timestamp=timestamp)
        self.assert_hello(*self.call(timestamp=NOW + 5))
        self.assert_hello(*self.call(timestamp=NOW + 6))
        self.refused(timestamp=NOW + 5)

    def test_setting_this_servers_clock_back_reopens_nothing(self):
        first = self.call(timestamp=NOW)
        self.assert_hello(*first)
        self.assert_hello(*self.call(timestamp=NOW + 60))
        self.clock.now = NOW - 30  # both requests are inside the window again
        self.refused(timestamp=NOW)
        before = self.state()
        again = self.deliver(first[2])
        self.refused_unsigned(again, 'time', before)

    def test_a_request_that_is_refused_does_not_move_the_links_time(self):
        # Otherwise anyone could shut the controller out by naming a time ahead of its clock.
        for options in (dict(key=STRANGER, timestamp=NOW + 90), dict(timestamp=NOW + 90, link_id=OTHER_LINK),
                        dict(timestamp=NOW + 90, environ={'REMOTE_ADDR': '198.51.100.7'}),
                        dict(timestamp=NOW + 90, sent={'query': 'x=1'})):
            self.call(**options)
            self.assertEqual((0, 0), self.state()[:2])
        self.assert_hello(*self.call(timestamp=NOW - 90))

    def test_the_time_is_looked_at_before_the_signature(self):
        self.refused(key=STRANGER, timestamp=NOW - 91)


class SignatureTests(Panel):
    def refused(self, with_body=False, **options):
        before = self.state()
        audited = options.pop('audited', {})
        self.refused_unsigned(self.call(**options)[0], 'signature', before, with_body, **audited)

    def test_a_request_signed_with_another_key_is_refused(self):
        self.refused(key=STRANGER)
        self.refused(key=IDENTITY)
        models.Link.objects.filter(pk=LINK).update(controller_key=crypto.public_key(STRANGER).hex())
        self.refused()

    def test_what_arrives_must_be_what_was_signed(self):
        post = dict(method='POST', body=BODY, content_type='application/json')
        posted = dict(method='POST', size=len(BODY))
        self.refused(sent={'path': '/multiserver/status'}, audited={'path': '/multiserver/status'})
        self.refused(sent={'path': '/multiserver/gateway/hell'}, audited={'path': '/multiserver/gateway/hell'})
        self.refused(sent={'path': '/multiserver/gateway/hello/'}, audited={'path': '/multiserver/gateway/hello/'})
        self.refused(sent={'query': 'x=1'})
        self.refused(query='x=1', sent={'query': ''})
        self.refused(query='x=1&y=2', sent={'query': 'y=2&x=1'})
        self.refused(sent={'host': 'other.example.com:8090'})
        self.refused(sent={'host': 'node.example.com:8091'})
        self.refused(sent={'host': 'NODE.example.com:8090'})
        self.refused(sent={'content_type': 'application/json'})
        self.refused(content_type='application/json', sent={'content_type': '-'})
        self.refused(sent={'method': 'POST'}, audited={'method': 'POST'})
        self.refused(method='POST', sent={'method': 'GET'})
        self.refused(True, sent={'body': BODY.replace(b'request', b'REQUEST')}, audited=posted, **post)
        self.refused(True, sent={'body': BODY[:-1] + b' '}, audited=posted, **post)
        self.refused(True, sent={'body': BODY + b' '}, audited=dict(posted, size=len(BODY) + 1), **post)
        self.refused(True, sent={'content_type': 'text/plain'}, audited=posted, **post)
        self.refused(sent={'body': b''}, audited=dict(method='POST'), **post)

    def test_every_signed_header_is_part_of_what_was_signed(self):
        other = sign(timestamp=NOW)[0]
        self.refused(sent={'named': {'nonce': other['nonce']}})
        self.refused(sent={'named': {'timestamp': str(NOW + 1)}})
        self.refused(sent={'named': {'actor': 'root'}})
        self.refused(sent={'named': {'mode': 'page'}})
        self.refused(sent={'named': {'signature': other['signature']}})
        self.refused(sent={'named': {'signature': '0' * 128}})
        # A second link of the same controller key: a request signed for one is not one for the other.
        models.Link.objects.create(
            link_id=OTHER_LINK, controller_key=self.link.controller_key, pairing_key='d2' * 32,
            allowed_ips='127.0.0.1', admin_id=self.administrator.pk, status=models.ACTIVE, generation=1,
            created_at=NOW, updated_at=NOW, expires_at=NOW + 86400)
        before = self.state()
        response = self.call(sent={'named': {'link': OTHER_LINK}})[0]
        self.refused_unsigned(response, 'signature', before, link_id=OTHER_LINK)

    def test_a_nonce_is_not_used_up_by_a_request_that_was_not_signed(self):
        named, message = self.signed()
        forged = dict(named, signature=sign(STRANGER, nonce=named['nonce'])[0]['signature'])
        before = self.state()
        self.refused_unsigned(self.deliver(forged), 'signature', before)
        self.assert_hello(self.deliver(named), message, named)


class ReplayTests(Panel):
    def test_a_request_is_accepted_once(self):
        response, message, named = self.call()
        self.assert_hello(response, message, named)
        for _ in range(3):
            before = self.state()
            again = self.deliver(named)
            self.refused_signed(again, message, named, 'replay')
            self.assertEqual(before[:3] + (before[3] + 1,), self.state())

    def test_a_nonce_is_refused_even_under_a_new_signature(self):
        response, message, named = self.call()
        self.assert_hello(response, message, named)
        for changes in (dict(), dict(timestamp=NOW + 1), dict(actor='root'), dict(mode='page'),
                        dict(query='x=1')):
            again, message, repeated = self.call(nonce=named['nonce'], **changes)
            self.refused_signed(again, message, repeated, 'replay', actor=changes.get('actor', 'admin'))
        self.assertEqual((1, NOW), self.state()[:2])

    def test_a_nonce_belongs_to_its_link(self):
        models.Link.objects.create(
            link_id=OTHER_LINK, controller_key=crypto.public_key(STRANGER).hex(), pairing_key='d2' * 32,
            allowed_ips='127.0.0.1', admin_id=self.administrator.pk, status=models.ACTIVE, generation=1,
            created_at=NOW, updated_at=NOW, expires_at=NOW + 86400)
        response, message, named = self.call()
        self.assert_hello(response, message, named)
        response, message, named = self.call(key=STRANGER, link_id=OTHER_LINK, nonce=named['nonce'])
        self.assert_signed(response, message, named, 200, response.content, link_id=OTHER_LINK)
        self.assertEqual(2, models.Nonce.objects.count())

    def test_of_many_copies_arriving_at_once_exactly_one_is_accepted(self):
        named, message = self.signed()
        answers, failures = [], []

        def deliver():
            try:
                extra = dict((SIGNED_HEADERS[field], value) for field, value in named.items())
                answers.append(Client().get(HELLO, HTTP_HOST=HOST, **extra))
            except Exception as error:
                failures.append(error)
            finally:
                connection.close()
        workers = [threading.Thread(target=deliver) for _ in range(12)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual([], failures)
        self.assertEqual([200] + [403] * 11, sorted(response.status_code for response in answers))
        for response in answers:
            expected = crypto.response_message(LINK, NODE, named['nonce'], message, response.status_code,
                                               'application/json', response.content)
            self.assertTrue(crypto.verify(NODE_KEY, bytes.fromhex(response['X-CPMS-Signature']), expected))
            if response.status_code == 403:
                self.assertEqual(b'{"error":"replay"}', response.content)
        self.assertEqual((1, NOW), self.state()[:2])
        self.assertEqual(11, models.AuditEntry.objects.filter(reason='replay').count())
        self.assertEqual(1, models.AuditEntry.objects.filter(outcome='ok').count())

    def test_requests_arriving_at_once_never_leave_the_links_time_behind(self):
        failures = []

        def deliver(step):
            try:
                named = sign(timestamp=NOW + step)[0]
                extra = dict((SIGNED_HEADERS[field], value) for field, value in named.items())
                Client().get(HELLO, HTTP_HOST=HOST, **extra)
            except Exception as error:
                failures.append(error)
            finally:
                connection.close()
        workers = [threading.Thread(target=deliver, args=(step % 4,)) for step in range(16)]
        for worker in workers:
            worker.start()
        for worker in workers:
            worker.join()
        self.assertEqual([], failures)
        self.assertEqual(NOW + 3, models.Link.objects.get(pk=LINK).last_request_at)
        accepted = models.AuditEntry.objects.filter(outcome='ok').count()
        self.assertEqual(accepted, models.Nonce.objects.count())
        self.assertEqual(16, accepted + models.AuditEntry.objects.filter(reason='time').count())
        self.assertGreaterEqual(accepted, 4)

    def test_a_link_changed_while_a_request_was_being_checked_does_not_carry_it(self):
        # What the row said when it was read no longer holds at the moment of acceptance.
        other = Administrator.objects.create(userName='second', password='x', type=1, email='b@example.com',
                                             acl=self.full)
        mine = dict(status=models.ACTIVE, generation=1, expires_at=NOW + 86400, last_request_at=0,
                    controller_key=self.link.controller_key, allowed_ips='127.0.0.1',
                    admin_id=self.administrator.pk)
        for change, reason in ((dict(status=models.REVOKED), 'link'), (dict(status=models.PAUSED), 'link'),
                               (dict(generation=2), 'generation'), (dict(expires_at=NOW), 'expired'),
                               (dict(last_request_at=NOW + 1), 'time'),
                               (dict(controller_key=crypto.public_key(STRANGER).hex()), 'link'),
                               (dict(allowed_ips='203.0.113.9'), 'link'),
                               (dict(allowed_ips='127.0.0.1,203.0.113.9'), 'link'),
                               (dict(admin_id=other.pk), 'link')):
            with self.subTest(reason=reason, change=change):
                models.Link.objects.filter(pk=LINK).update(**mine)
                real = crypto.verify

                def verify_then_change(*arguments):
                    models.Link.objects.filter(pk=LINK).update(**change)
                    return real(*arguments)
                before = self.state()
                with patch.object(crypto, 'verify', side_effect=verify_then_change):
                    response, message, named = self.call()
                self.refused_signed(response, message, named, reason)
                self.assertEqual(before[0], self.state()[0])
                if 'last_request_at' not in change:
                    self.assertEqual(0, self.state()[1])

    def test_dead_nonces_are_removed_when_the_links_time_enters_a_new_minute(self):
        minute = NOW - NOW % 60 + 60
        self.clock.now = minute - 1
        models.Link.objects.filter(pk=LINK).update(last_request_at=minute - 30)
        models.Link.objects.create(
            link_id=OTHER_LINK, controller_key='c2' * 32, pairing_key='d2' * 32, allowed_ips='127.0.0.1',
            admin_id=1, status=models.ACTIVE, generation=1, created_at=NOW, updated_at=NOW, expires_at=NOW + 9)
        for link_id, nonce, seen_at in ((LINK, 'e1' * 16, minute - 200), (LINK, 'e2' * 16, minute - 92),
                                        (LINK, 'e3' * 16, minute - 91), (LINK, 'e4' * 16, minute - 90),
                                        (LINK, 'e5' * 16, minute - 2), (OTHER_LINK, 'e6' * 16, minute - 200)):
            models.Nonce.objects.create(link_id=link_id, nonce=nonce, seen_at=seen_at)
        kept = lambda: sorted(models.Nonce.objects.exclude(nonce__in=[seen[1] for seen in self.seen]).values_list(
            'nonce', flat=True))
        self.assert_hello(*self.call(timestamp=minute - 1))
        self.assertEqual(['e1' * 16, 'e2' * 16, 'e3' * 16, 'e4' * 16, 'e5' * 16, 'e6' * 16], kept())
        self.clock.now = minute
        self.assert_hello(*self.call(timestamp=minute))
        # Only this link's nonces more than the window below its newest time: those can never be accepted again.
        self.assertEqual(['e4' * 16, 'e5' * 16, 'e6' * 16], kept())
        self.assert_hello(*self.call(timestamp=minute))
        self.assert_hello(*self.call(timestamp=minute + 59))
        self.assertEqual(['e4' * 16, 'e5' * 16, 'e6' * 16], kept())
        self.assertEqual(4 + 3, models.Nonce.objects.count())

    def test_a_failure_to_remove_old_nonces_does_not_fail_the_request(self):
        models.Link.objects.filter(pk=LINK).update(last_request_at=NOW - 200)
        with patch('django.db.models.query.QuerySet.delete', side_effect=RuntimeError('lock wait')):
            self.assert_hello(*self.call())
        self.assertEqual(['Multi-Server Manager gateway failed: RuntimeError'], self.log)

    def test_a_replay_is_looked_at_before_the_administrator(self):
        response, message, named = self.call()
        self.assert_hello(response, message, named)
        Administrator.objects.all().update(state='SUSPENDED')
        self.refused_signed(self.deliver(named), message, named, 'replay')


class AdministratorTests(Panel):
    def refused(self):
        before = self.state()
        response, message, named = self.call()
        self.refused_signed(response, message, named, 'admin')
        # The request was the controller's and is spent like any other.
        self.assertEqual((before[0] + 1, NOW), self.state()[:2])
        self.refused_signed(self.deliver(named), message, named, 'replay')

    def test_a_suspended_administrator_carries_no_request(self):
        for state in ('SUSPENDED', '', 'active'):
            Administrator.objects.filter(pk=self.administrator.pk).update(state=state)
            self.refused()
        Administrator.objects.filter(pk=self.administrator.pk).update(state='ACTIVE')
        self.assert_hello(*self.call())

    def test_an_administrator_who_is_no_longer_a_full_one_carries_no_request(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(acl=self.reseller)
        self.refused()
        Administrator.objects.filter(pk=self.administrator.pk).update(acl=self.full)
        ACL.objects.filter(pk=self.full.pk).update(config=ACLManager.ResellerACL)
        self.refused()
        ACL.objects.filter(pk=self.full.pk).update(config='not json')
        self.refused()

    def test_a_removed_administrator_carries_no_request(self):
        self.empty(Administrator)
        self.refused()
        other = Administrator.objects.create(userName='second', password='x', type=1, email='b@example.com',
                                             acl=self.full)
        self.assertNotEqual(other.pk, self.link.admin_id)
        self.refused()

    def test_the_administrator_is_the_one_the_link_names_and_nobody_the_request_names(self):
        reseller = Administrator.objects.create(userName='reseller', password='x', type=1, email='r@example.com',
                                                acl=self.reseller)
        models.Link.objects.filter(pk=LINK).update(admin_id=reseller.pk)
        before = self.state()
        response, message, named = self.call(actor='admin')
        self.refused_signed(response, message, named, 'admin')
        self.assertEqual(before[0] + 1, self.state()[0])

    def test_the_administrator_is_looked_at_before_the_address_asked_for(self):
        Administrator.objects.all().update(state='SUSPENDED')
        response, message, named = self.call(path='/multiserver/status')
        self.refused_signed(response, message, named, 'admin', path='/multiserver/status')


class DispatchTests(Panel):
    PATHS = ('/', '/base/', '/verifyLogin', '/logout', '/multiserver/status', '/multiserver/', '/multiserver/gateway',
             '/multiserver/gateway/', '/multiserver/gateway/hello/', '/multiserver/gateway/Hello',
             '/multiserver/gateway/hello.json', '/api/verifyConn', '/api/', '/cloudAPI/', '/cloudAPI',
             '/firewall/', '/firewall/csf', '/users/', '/users/modifyUsers', '/users/saveModifications',
             '/websites/listWebsites', '/dataBases/', '/backup/localInitiate', '/webmail/login', '/roundcube/',
             '/static/baseTemplate/custom-js/system-status.js', '/no-such-address')

    def setUp(self):
        Panel.setUp(self)
        self.resolver = self.start(patch('django.core.handlers.base.BaseHandler.resolve_request',
                                         side_effect=AssertionError('a view was looked up')))

    def refused(self, **options):
        response, message, named = self.call(**options)
        self.refused_signed(response, message, named, 'not_allowed', method=options.get('method', 'GET'),
                            path=options.get('path', HELLO), size=len(options.get('body', b'')))
        self.resolver.assert_not_called()

    def test_no_other_address_is_served_in_any_mode(self):
        for mode in crypto.MODES:
            for path in self.PATHS:
                with self.subTest(mode=mode, path=path):
                    self.refused(mode=mode, path=path)
                    self.refused(mode=mode, path=path, method='POST', body=BODY, content_type='application/json')

    def test_hello_is_served_in_its_own_mode_alone(self):
        for mode in crypto.MODES:
            if mode != 'json':
                with self.subTest(mode):
                    self.refused(mode=mode)

    def test_hello_takes_a_get_without_a_query(self):
        self.refused(method='POST')
        self.refused(method='POST', body=BODY, content_type='application/json')
        self.refused(query='x=1')
        self.refused(query='capabilities')
        self.assert_hello(*self.call())

    def test_a_signed_in_administrators_cookie_opens_nothing_through_the_gateway(self):
        key = self.sign_in()
        for path in ('/multiserver/status', '/base/', '/users/modifyUsers'):
            self.refused(path=path, environ={'HTTP_COOKIE': '%s=%s' % (settings.SESSION_COOKIE_NAME, key)})

    def test_the_panel_behind_the_gateway_is_never_called(self):
        behind = MagicMock(side_effect=AssertionError('handed on'))
        gateway = nodeGateway.NodeGateway(behind)
        statuses = []
        for sign_options, changed in ((dict(), {}), (dict(path='/base/'), {}), (dict(mode='page'), {}),
                                      (dict(key=STRANGER), {}), (dict(link_id=OTHER_LINK), {}),
                                      (dict(timestamp=NOW - 500), {}), (dict(), {'HTTP_X_CPMS_NONCE': 'x'}),
                                      (dict(), {'REMOTE_ADDR': '198.51.100.7'}), (dict(), {'REQUEST_METHOD': 'PUT'}),
                                      (dict(nonce='e1' * 16), {}), (dict(nonce='e1' * 16), {})):
            named = self.signed(**sign_options)[0]
            environ = dict((SIGNED_HEADERS[field], value) for field, value in named.items())
            environ.update(PATH_INFO=sign_options.get('path', HELLO), HTTP_HOST=HOST,
                           HTTP_COOKIE='%s=%s' % (settings.SESSION_COOKIE_NAME, self.sign_in()))
            environ.update(changed)
            response = gateway(RequestFactory().generic('GET', '/', **environ))
            statuses.append(response.status_code)
            self.assertEqual({}, dict(response.cookies))
        self.assertEqual([200, 403, 403, 302, 302, 302, 302, 302, 302, 200, 403], statuses)
        behind.assert_not_called()
        self.sessions.assert_not_called()
        self.resolver.assert_not_called()
        # The stand-in is what an ordinary request reaches.
        with self.assertRaises(AssertionError):
            gateway(RequestFactory().get('/base/'))


class ExtensionPointTests(Panel):
    """A later mode's handler, stood in for here: what it is given and what happens to what it returns."""

    def setUp(self):
        Panel.setUp(self)
        self.given = []
        self.reply = (200, 'text/html', b'<p>relayed</p>')

        def handler(verified, request, get_response):
            self.given.append((verified, request, get_response))
            if isinstance(self.reply, Exception):
                raise self.reply
            return self.reply
        self.start(patch.dict(nodeGateway.MODE_HANDLERS, {'page': handler}))

    def test_a_handler_is_given_the_request_as_signed_and_nothing_a_client_added(self):
        key = self.sign_in()
        response, message, named = self.call(
            method='POST', path='/websites/submitWebsiteCreation', query='page=2', body=BODY,
            content_type='application/json', mode='page', actor='operator', environ={
                'HTTP_COOKIE': '%s=%s' % (settings.SESSION_COOKIE_NAME, key), 'HTTP_AUTHORIZATION': 'Basic eDp5',
                'HTTP_PROXY_AUTHORIZATION': 'Basic eDp5', 'HTTP_X_FORWARDED_FOR': '198.51.100.7',
                'HTTP_X_FORWARDED_HOST': 'evil.example.com', 'HTTP_X_FORWARDED_PROTO': 'https',
                'HTTP_FORWARDED': 'for=198.51.100.7', 'HTTP_X_REAL_IP': '198.51.100.7',
                'HTTP_CF_CONNECTING_IP': '198.51.100.7', 'HTTP_X_CYBERPANEL_PEER': '198.51.100.7',
                'HTTP_X_HTTP_METHOD_OVERRIDE': 'DELETE', 'HTTP_X_CSRFTOKEN': 'x', 'HTTP_REFERER': 'https://x/',
                'HTTP_ORIGIN': 'https://evil.example.com', 'HTTP_USER_AGENT': 'Mozilla/5.0',
                'HTTP_ACCEPT_LANGUAGE': 'de', 'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'})
        self.assertEqual(200, response.status_code)
        (verified, request, get_response), = self.given
        self.assertEqual(nodeGateway.Verified(
            link_id=LINK, admin_id=self.administrator.pk, actor='operator', mode='page', method='POST', host=HOST,
            path='/websites/submitWebsiteCreation', query='page=2', content_type='application/json', body=BODY,
            source='127.0.0.1'), verified)
        self.assertEqual(['HTTP_HOST'], [name for name in request.META if name.startswith('HTTP_')])
        self.assertEqual({}, request.COOKIES)
        self.assertEqual({'Host': HOST, 'Content-Type': 'application/json', 'Content-Length': str(len(BODY))},
                         dict(request.headers))
        self.assertEqual(BODY, request.body)
        self.assertEqual('127.0.0.1', request.META['REMOTE_ADDR'])
        self.assertFalse(hasattr(request, 'session'))
        self.assertTrue(callable(get_response))
        for value in (named['nonce'], named['signature'], key):
            self.assertNotIn(value, repr(sorted(request.META.items(), key=repr)))

    def test_what_a_handler_returns_is_signed_as_it_is(self):
        for self.reply in ((200, 'text/html', b'<p>relayed</p>'), (404, 'text/html', b''), (500, 'text/plain', b'x'),
                           (201, 'application/octet-stream', bytes(range(256))), (599, 'image/png', b'\x89PNG')):
            response, message, named = self.call(mode='page', path='/base/')
            status, media_type, body = self.reply
            self.assertEqual((status, body, media_type), (response.status_code, response.content,
                                                          response['Content-Type']))
            expected = crypto.response_message(LINK, NODE, named['nonce'], message, status, media_type, body)
            self.assertTrue(crypto.verify(NODE_KEY, bytes.fromhex(response['X-CPMS-Signature']), expected))
            self.assertEqual(['Cache-Control', 'Content-Length', 'Content-Type', 'X-CPMS-Signature'],
                             sorted(name for name, _ in response.items()))
            self.assertEqual(('ok', '', status), (self.last_audit()[1], self.last_audit()[2], self.last_audit()[8]))

    def test_a_reply_the_link_cannot_carry_becomes_a_signed_failure(self):
        for self.reply in ((302, 'text/html', b''), (301, 'text/html', b''), (304, 'text/html', b''),
                           (204, 'text/html', b''), (205, 'text/html', b''), (100, 'text/html', b''),
                           (199, 'text/html', b''), (600, 'text/html', b''), ('200', 'text/html', b''),
                           (True, 'text/html', b''), (200.0, 'text/html', b''), (200, 'text/html', 'text'),
                           (200, 'text/html', None), (200, 'text/html; charset=utf-8', b''),
                           (200, 'Text/HTML', b''), (200, '-', b''), (200, None, b''), (200, '', b''),
                           (200, 'text/html', b'x' * (nodeGateway.MAX_REPLY_BODY + 1)), (200, 'text/html'), None,
                           RuntimeError('reply-secret'), ValueError(BODY.decode())):
            with self.subTest(repr(self.reply)[:60]):
                del self.log[:]
                nodeGateway._NOTED.clear()
                response, message, named = self.call(mode='page', path='/base/')
                self.refused_signed(response, message, named, 'internal', 500, path='/base/')
                self.assertEqual(1, len(self.log))
                self.assertRegex(self.log[0], r'\AMulti-Server Manager gateway failed: [A-Za-z]+\Z')

    def test_a_route_is_not_overridden_by_a_handler_for_its_mode(self):
        with patch.dict(nodeGateway.MODE_HANDLERS, {'json': nodeGateway.MODE_HANDLERS['page']}):
            self.assert_hello(*self.call())
            response, message, named = self.call(method='POST')
            self.refused_signed(response, message, named, 'not_allowed', method='POST')
        self.assertEqual([], self.given)


class NeverRaisesTests(Panel):
    def test_a_failure_before_the_signature_is_an_unsigned_refusal(self):
        for target, name in ((models.Link.objects, 'filter'), (crypto, 'public_key'), (keys, 'generation'),
                             (nodeGateway, '_allowed'), (nodeGateway, '_address'), (nodeGateway, '_strip')):
            with self.subTest(name):
                del self.log[:]
                nodeGateway._NOTED.clear()
                before = self.state()
                with patch.object(target, name, side_effect=RuntimeError('failure-secret')):
                    response = self.call()[0]
                self.assert_gateway_alone(response)
                self.assertEqual(self.absent(), snapshot(response))
                self.assertEqual('internal', self.last_audit()[2])
                self.assertEqual(before[:3] + (before[3] + 1,), self.state())
                self.assertEqual(['Multi-Server Manager gateway failed: RuntimeError'], self.log)

    def test_a_failure_after_the_signature_is_a_signed_refusal(self):
        for target, name in ((nodeGateway, '_accept'), (views, 'active_full_administrator'),
                             (nodeGateway, '_dispatch'), (nodeGateway, 'capabilities')):
            with self.subTest(name):
                del self.log[:]
                nodeGateway._NOTED.clear()
                with patch.object(target, name, side_effect=RuntimeError('failure-secret')):
                    response, message, named = self.call()
                self.refused_signed(response, message, named, 'internal', 500)
                self.assertEqual(['Multi-Server Manager gateway failed: RuntimeError'], self.log)

    def test_a_kind_of_failure_is_written_to_the_panels_log_once_a_minute(self):
        # While something is broken anybody can send the request that fails.
        with patch.object(models.Link.objects, 'filter', side_effect=RuntimeError('failure-secret')):
            for _ in range(5):
                self.call()
            self.assertEqual(['Multi-Server Manager gateway failed: RuntimeError'], self.log)
            with patch.object(keys, 'generation', side_effect=KeyError('another kind')):
                self.call()
            self.assertEqual(['Multi-Server Manager gateway failed: RuntimeError',
                              'Multi-Server Manager gateway failed: KeyError'], self.log)
            self.clock.now += 59
            self.call()
            self.assertEqual(2, len(self.log))
            self.clock.now += 1
            self.call()
            self.call()
            self.assertEqual(3, len(self.log))
        self.assertEqual(9, models.AuditEntry.objects.filter(reason='internal').count())

    def test_a_database_that_fails_on_the_nonce_is_a_failure_not_a_replay(self):
        from django.db import IntegrityError, OperationalError
        for error in (OperationalError(1213, 'Deadlock found'), IntegrityError(1452, 'foreign key fails'),
                      IntegrityError('no cause')):
            with patch.object(models.Nonce.objects, 'create', side_effect=error):
                response, message, named = self.call()
            self.refused_signed(response, message, named, 'internal', 500)
            self.assertEqual((0, 0), self.state()[:2])

    def test_without_the_audit_table_requests_are_still_answered_and_nothing_is_raised(self):
        self.database.run('RENAME TABLE ms_audit TO ms_audit_away')
        try:
            response, message, named = self.call()
            self.assert_signed(response, message, named, 200, response.content)
            refused = self.call(key=STRANGER)[0]
            self.assertEqual(self.absent(), snapshot(refused))
        finally:
            self.database.run('RENAME TABLE ms_audit_away TO ms_audit')

    def test_when_the_reply_cannot_be_signed_the_refusal_is_unsigned(self):
        named = self.signed()[0]
        with patch.object(crypto, 'sign', side_effect=RuntimeError('no signing')):
            response = self.deliver(named)
        self.assert_gateway_alone(response)
        self.assertEqual(self.absent(), snapshot(response))
        self.assertEqual(('refused', 'internal'), self.last_audit()[1:3])

    def test_when_even_the_refusal_fails_the_panel_still_gets_an_answer(self):
        with patch.object(nodeGateway, '_refuse', side_effect=RuntimeError('worse')):
            response = self.call(key=STRANGER)[0]
        self.assert_gateway_alone(response)
        self.assertEqual(self.absent(), snapshot(response))

    def test_django_reports_nothing_about_a_gateway_reply(self):
        records = []
        handler = logging.Handler()
        handler.emit = records.append
        logging.getLogger('django').addHandler(handler)
        self.addCleanup(logging.getLogger('django').removeHandler, handler)
        self.sign_in()
        self.client.get('/no-such-address', HTTP_HOST=HOST)
        # The handler does hear what Django says about a reply of the panel's own.
        self.assertEqual(['Not Found: /no-such-address'], [record.getMessage() for record in records])
        del records[:]
        self.sessions.reset_mock()
        self.client.cookies.clear()
        self.assertEqual(403, self.call(path='/base/')[0].status_code)
        with patch.object(views, 'active_full_administrator', side_effect=RuntimeError('x')):
            self.assertEqual(500, self.call()[0].status_code)
        self.call(key=STRANGER)
        self.call(sent={'host': 'no host at all'})
        self.assertEqual([], records)


class RefusalLooksLikeNothingTests(Panel):
    def test_every_unsigned_refusal_is_the_answer_for_an_address_that_is_not_there(self):
        plain = self.absent()
        self.assertEqual(302, plain[0])
        self.assertIn(b'Location: /\r\n', plain[2])
        answers = set()
        for options in (dict(sent={'named': {'nonce': 'x'}}), dict(link_id=OTHER_LINK),
                        dict(environ={'REMOTE_ADDR': '198.51.100.7'}), dict(timestamp=NOW - 500),
                        dict(key=STRANGER), dict(sent={'method': 'HEAD'}), dict(key=STRANGER, path='/'),
                        dict(key=STRANGER, path='/api/x'), dict(key=STRANGER, path='/verifyLogin'),
                        dict(key=STRANGER, path='/static/x.js'), dict(key=STRANGER, path='/multiserver/status')):
            response = self.call(**options)[0]
            self.assert_gateway_alone(response)
            answers.add(snapshot(response))
        self.assertEqual({plain}, answers)

    def test_with_a_body_it_is_the_answer_the_panel_gives_such_a_request(self):
        with_body = self.absent(True)
        self.assertEqual(200, with_body[0])
        self.assertIn(b'This request need session.', with_body[2])
        answers = set()
        post = dict(method='POST', body=BODY, content_type='application/json')
        for options in (dict(sent={'named': {'nonce': 'x'}}), dict(link_id=OTHER_LINK),
                        dict(environ={'REMOTE_ADDR': '198.51.100.7'}), dict(timestamp=NOW - 500),
                        dict(key=STRANGER), dict(sent={'method': 'PUT'})):
            answers.add(snapshot(self.call(**dict(post, **options))[0]))
        self.assertEqual({with_body}, answers)

    def test_it_follows_the_language_asked_for_as_the_panel_does(self):
        for language in ('de', 'pt-br', 'zz', 'fr;q=0.2, ja;q=0.9', '*', ''):
            with self.subTest(language):
                expected = self.absent(HTTP_ACCEPT_LANGUAGE=language)
                self.assertEqual(expected, snapshot(self.call(key=STRANGER,
                                                              environ={'HTTP_ACCEPT_LANGUAGE': language})[0]))
        self.assertIn(b'Content-Language: de\r\n', self.absent(HTTP_ACCEPT_LANGUAGE='de')[2])

    def test_a_signed_in_administrators_cookie_with_a_bad_signature_gets_that_answer_too(self):
        key = self.sign_in()
        cookie = {'HTTP_COOKIE': '%s=%s' % (settings.SESSION_COOKIE_NAME, key)}
        served = self.client.get('/multiserver/status', HTTP_HOST=HOST)
        self.assertEqual((200, {'role': 'node', 'licensed': None}),
                         (served.status_code, json.loads(served.content.decode())))
        self.sessions.reset_mock()
        self.client.cookies.clear()
        for options in (dict(key=STRANGER), dict(sent={'named': {'signature': '0' * 128}}),
                        dict(sent={'named': {'signature': ''}})):
            before = self.state()
            response = self.call(path='/multiserver/status', environ=cookie, **options)[0]
            self.assert_gateway_alone(response)
            self.assertEqual(self.absent(), snapshot(response))
            self.assertNotIn(b'role', response.content)
            self.assertEqual(before[:3], self.state()[:3])
        self.assertEqual([key], list(Session.objects.values_list('session_key', flat=True)))


class SecretsTests(Panel):
    def test_no_reply_audit_row_or_log_line_holds_a_key_a_signature_a_body_or_a_nonce(self):
        replies = []
        post = dict(method='POST', body=BODY, content_type='application/json')

        def handler(verified, request, get_response):
            raise RuntimeError(BODY.decode() + request.META.get('HTTP_X_CPMS_SIGNATURE', ''))
        with patch.dict(nodeGateway.MODE_HANDLERS, {'page': handler}):
            for options in (dict(), dict(post), dict(post, mode='page'), dict(key=STRANGER), dict(post, key=STRANGER),
                            dict(link_id=OTHER_LINK), dict(environ={'REMOTE_ADDR': '198.51.100.7'}),
                            dict(timestamp=NOW - 500), dict(post, sent={'named': {'mode': 'x'}}),
                            dict(actor='a1' * 16), dict(path='/x/' + 'c3' * 16), dict(query='token=' + 'c4' * 16)):
                replies.append(self.call(**options)[0])
            replies.append(self.deliver(sign(nonce=self.seen[0][1], timestamp=NOW)[0]))
            Administrator.objects.all().update(state='SUSPENDED')
            replies.append(self.call(**post)[0])
        with patch.object(models.Nonce.objects, 'create', side_effect=RuntimeError(self.seen[0][1])):
            replies.append(self.call()[0])
        self.assertEqual({200, 302, 403, 500}, set(response.status_code for response in replies))
        written = [repr(snapshot(response)) for response in replies]
        written += [repr(row) for row in self.database.run('SELECT * FROM ms_audit')]
        written += self.log
        self.assertEqual(len(replies), models.AuditEntry.objects.count())
        secrets_ = [CONTROLLER.hex(), crypto.public_key(CONTROLLER).hex(), IDENTITY.hex(), STRANGER.hex(),
                    'request-body-secret', 'c4' * 16]
        for message, nonce, signature in self.seen:
            secrets_ += [nonce, signature, hashlib.sha256(message).hexdigest()]
        for text in written:
            for secret in secrets_:
                self.assertNotIn(secret, text)
        # What does appear is what the audit trail is for.
        self.assertTrue(any(LINK in text for text in written))


def sample():
    """Ordinary requests to the panel: (name, signed in, method, address, options)."""
    login = json.dumps({'username': 'nobody', 'password': 'wrong', 'languageSelection': 'English'})
    return (
        ('the sign-in page', False, 'get', '/', {}),
        ('the sign-in page in German', False, 'get', '/', {'HTTP_ACCEPT_LANGUAGE': 'de'}),
        ('a failed sign-in', False, 'post', '/verifyLogin', {'data': login, 'content_type': 'application/json'}),
        ('a page without a session', False, 'get', '/base/', {}),
        ('a list without a session', False, 'get', '/websites/listWebsites', {'QUERY_STRING': 'page=2'}),
        ('a call without a session', False, 'post', '/websites/submitWebsiteCreation',
         {'data': '{"domainName": "example.com"}', 'content_type': 'application/json'}),
        ('nothing there, without a session', False, 'get', '/no-such-address', {}),
        ('the gateway address, without a session', False, 'get', HELLO, {}),
        ('the status, without a session', False, 'get', '/multiserver/status', {}),
        ('an address of the API', False, 'get', '/api/no-such-call', {}),
        ('a HEAD request', False, 'head', '/base/', {}),
        ('the status', True, 'get', '/multiserver/status', {}),
        ('nothing there', True, 'get', '/no-such-address', {}),
        ('the gateway address', True, 'get', HELLO, {}),
        ('a HEAD request, signed in', True, 'head', '/no-such-address', {}),
    )


@unittest.skipIf(SKIP, SKIP)
class InertThroughThePanelTests(Panel):
    """The panel answers ordinary requests exactly as it does without the middleware."""

    def setUp(self):
        Panel.setUp(self)
        # Two renderings of one page differ in the masked CSRF token and in the second its cookie expires.
        import django.http.response
        self.start(patch('django.middleware.csrf.get_random_string',
                         side_effect=lambda length, allowed_chars='': 'k' * length))
        self.start(patch.object(django.http.response, 'time', Clock(NOW)))

    def answers(self, extra=None):
        found = {}
        for name, signed_in, method, address, options in sample():
            client = Client()
            if signed_in:
                self.sign_in(client)
            options = dict(options, HTTP_HOST=HOST)
            options.update(extra or {})
            found[name] = snapshot(getattr(client, method)(address, **options))
            Session.objects.all().delete()
        return found

    def with_and_without(self, extra=None):
        self.assertEqual(GATEWAY, settings.MIDDLEWARE[0])
        with_gateway = self.answers(extra)
        with override_settings(MIDDLEWARE=[name for name in settings.MIDDLEWARE if name != GATEWAY]):
            self.assertNotIn(GATEWAY, settings.MIDDLEWARE)
            without = self.answers(extra)
        self.assertEqual(sorted(without), sorted(with_gateway))
        for name in without:
            self.assertEqual(without[name], with_gateway[name], name)
        return with_gateway

    def signed_headers(self):
        return dict((SIGNED_HEADERS[field], value) for field, value in sign()[0].items())

    def test_the_sample_is_a_real_one(self):
        self.role.return_value = keys.OFF
        found = self.answers()
        self.assertEqual({200, 302, 404}, set(answer[0] for answer in found.values()))
        self.assertEqual(200, found['the sign-in page'][0])
        self.assertIn(b'<html', found['the sign-in page'][2])
        self.assertTrue(found['the sign-in page'][3], 'the sign-in page sets its CSRF cookie')
        self.assertNotEqual(found['the sign-in page'][2], found['the sign-in page in German'][2])
        self.assertIn(b'"loginStatus": 0', found['a failed sign-in'][2])
        self.assertIn(b'This request need session.', found['a call without a session'][2])
        self.assertEqual(404, found['nothing there'][0])
        self.assertEqual(302, found['nothing there, without a session'][0])

    def test_on_a_managed_server_requests_without_a_link_header_are_answered_as_before(self):
        found = self.with_and_without()
        self.assertEqual(200, found['the status'][0])
        self.assertEqual(404, found['the gateway address'][0])
        self.assertEqual(0, models.AuditEntry.objects.count())

    def test_with_the_feature_off_requests_are_answered_as_before(self):
        self.role.return_value = keys.OFF
        found = self.with_and_without()
        self.assertEqual(404, found['the status'][0])

    def test_with_the_feature_off_even_a_signed_request_is_answered_as_before(self):
        for role in (keys.OFF, keys.CONTROLLER):
            self.role.return_value = role
            found = self.with_and_without(self.signed_headers())
            self.assertEqual(302, found['the gateway address, without a session'][0])
            self.assertEqual(404, found['the gateway address'][0])
        self.assertEqual((0, 0), (models.AuditEntry.objects.count(), models.Nonce.objects.count()))

    def test_while_the_tables_or_signing_are_unusable_a_signed_request_is_answered_as_before(self):
        with patch.object(schema, 'ready', return_value=False):
            self.with_and_without(self.signed_headers())
        with patch.object(switch, '_SIGNING', False), patch.object(crypto, 'self_test', return_value=False):
            self.with_and_without(self.signed_headers())
        self.assertEqual(0, models.AuditEntry.objects.count())

    def test_the_same_requests_with_a_link_header_are_the_gateways_on_a_managed_server(self):
        # The control for the tests above: here the header does change every answer.
        found = self.answers({'HTTP_X_CPMS_LINK': LINK})
        self.assertEqual({302, 200}, set(answer[0] for answer in found.values()))
        for name, answer in found.items():
            self.assertFalse(answer[3], name)
            self.assertNotIn(b'role', answer[2])
        self.assertEqual(len(found), models.AuditEntry.objects.filter(reason='format').count())


class Handler(simple_server.WSGIRequestHandler):
    def get_environ(self):
        environ = simple_server.WSGIRequestHandler.get_environ(self)
        if self.headers.get('content-type') is None:
            # wsgiref alone reports text/plain for a request that names no content type.
            environ['CONTENT_TYPE'] = ''
        return environ

    def handle(self):
        simple_server.WSGIRequestHandler.handle(self)
        # A web server takes a request whole, read by the application or not; closing on bytes that
        # were not read would reset the connection under the reply.
        try:
            self.connection.setblocking(False)
            while self.rfile.read1(65536):
                pass
        except (OSError, ValueError):
            pass

    def log_message(self, *arguments):
        pass


class Server(object):
    """The panel's own WSGI application behind TLS on this machine, one request per connection."""

    def __init__(self, certificate):
        self.replies = []  # (status, headers) of every reply the application gave
        application = WSGIHandler()

        def recorded(environ, start_response):
            def start(status, headers, *more):
                self.replies.append((status, list(headers)))
                return start_response(status, headers, *more)
            return application(environ, start)
        self.httpd = simple_server.make_server('127.0.0.1', 0, recorded, handler_class=Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(certificate)
        self.httpd.socket = context.wrap_socket(self.httpd.socket, server_side=True)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, kwargs={'poll_interval': 0.02})
        self.thread.daemon = True
        self.thread.start()

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(5)


@unittest.skipIf(SKIP, SKIP)
class OverTheWireTests(Panel):
    """The controller's real client against this panel over TLS: what one sends the other verifies."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        try:
            wire.setUpModule()
            cls.server = Server(wire.CERTIFICATES['node'][0])
        except BaseException:
            super().tearDownClass()
            raise

    @classmethod
    def tearDownClass(cls):
        try:
            cls.server.close()
            wire.tearDownModule()
        finally:
            super().tearDownClass()

    def setUp(self):
        Panel.setUp(self)
        del self.server.replies[:]
        self.authority = '127.0.0.1:%d' % self.server.port
        self.controller = transport.Link(
            link_id=LINK, node_id=NODE, host='127.0.0.1', port=self.server.port, node_key=NODE_KEY,
            private_key=CONTROLLER, tls_pin=wire.pin('node'), allow_loopback_for_tests=True)

    def send(self, link=None, **changes):
        fields = dict(method='GET', path=HELLO, query='', content_type='-', body=b'', actor='admin', mode='json',
                      now=self.clock.now)
        fields.update(changes)
        return transport.send(link or self.controller, **fields)

    def changed_on_the_wire(self, change):
        """What the controller signed is sent with `change` applied to its bytes."""
        real = transport._write
        return patch.object(transport, '_write',
                            side_effect=lambda connection, data, deadline: real(connection, change(data), deadline))

    def head(self, named, method='GET', path=HELLO, query='', content_type='-', length=0, more=()):
        data = transport._request_head(self.controller, method, path, query, content_type, length,
                                       named['timestamp'], named['nonce'], named['actor'], named['mode'],
                                       named['signature'])
        lines = b''.join(line.encode('ascii') + b'\r\n' for line in more)
        return data[:-2] + lines + b'\r\n'

    def raw(self, data, port=None):
        """Send these bytes and return everything that comes back, less the one line that tells the time."""
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        connection = context.wrap_socket(socket.create_connection(('127.0.0.1', port or self.server.port), 10))
        try:
            connection.settimeout(10)
            connection.sendall(data)
            received = b''
            while True:
                try:
                    chunk = connection.recv(65536)
                except OSError:
                    chunk = b''
                if not chunk:
                    break
                received += chunk
        finally:
            connection.close()
        head, separator, body = received.partition(b'\r\n\r\n')
        lines = [line for line in head.split(b'\r\n') if not line.lower().startswith(b'date:')]
        return b'\r\n'.join(lines) + separator + body

    def absent_on_the_wire(self, with_body=False, more=(), port=None, address='/multiserver/no-such-address'):
        lines = ['%s %s HTTP/1.1' % ('POST' if with_body else 'GET', address),
                 'Host: ' + self.authority, 'Connection: close'] + list(more)
        body = b'{"a": 1}' if with_body else b''
        if with_body:
            lines += ['Content-Type: text/plain', 'Content-Length: %d' % len(body)]
        return self.raw('\r\n'.join(lines).encode('ascii') + b'\r\n\r\n' + body, port)

    def gateway_alone(self):
        """The last reply came from the gateway: no session was looked at and it sets no cookie."""
        self.sessions.assert_not_called()
        names = [name.lower() for name, _ in self.server.replies[-1][1]]
        self.assertNotIn('set-cookie', names)
        self.assertEqual(1, names.count('content-length'))
        self.assertNotIn('transfer-encoding', names)

    def refused(self, reason, error=transport.RedirectRefused, link=None, audited=None, **changes):
        before = self.state()
        with self.assertRaises(transport.TransportError) as raised:
            self.send(link, **changes)
        self.assertIs(error, type(raised.exception), repr(raised.exception))
        self.gateway_alone()
        self.assertNotIn('x-cpms-signature', [name.lower() for name, _ in self.server.replies[-1][1]])
        expected = dict(link_id=LINK, source_ip='127.0.0.1', method='GET', path=HELLO, size=0, status=302)
        expected.update(audited or {})
        self.assertEqual(('request', 'refused', reason, expected['link_id'], '', expected['source_ip'],
                          expected['method'], expected['path'], expected['status'], expected['size'], 0),
                         self.last_audit())
        self.assertEqual(before[:3] + (before[3] + 1,), self.state())

    def signed_refusal(self, reason, before=None, **changes):
        before = before or self.state()
        self.assertEqual((403, 'application/json', json.dumps({'error': reason}, separators=(',', ':')).encode()),
                         self.send(**changes))
        self.gateway_alone()
        self.assertEqual(('refused', reason), self.last_audit()[1:3])
        self.assertEqual(before[2], self.state()[2])

    def named(self, **changes):
        changes.setdefault('host', self.authority)
        return self.signed(**changes)

    def test_the_controller_gets_the_verified_hello(self):
        before = self.state()
        status, media_type, body = self.send()
        self.assertEqual((200, 'application/json'), (status, media_type))
        import cyberpanel_version
        self.assertEqual({'build': cyberpanel_version.BUILD, 'capabilities': ['hello'], 'role': 'node',
                          'version': cyberpanel_version.VERSION}, json.loads(body.decode()))
        self.assertEqual(('request', 'ok', '', LINK, 'admin', '127.0.0.1', 'GET', HELLO, 200, 0, 0),
                         self.last_audit())
        self.assertEqual((before[0] + 1, NOW, 0, before[3] + 1), self.state())
        self.gateway_alone()
        self.assertEqual(['200 OK'], [status for status, _ in self.server.replies])

    def test_the_reply_on_the_wire_is_one_whole_signed_reply_without_a_cookie(self):
        named, message = self.named()
        reply = self.raw(self.head(named))
        head, _, body = reply.partition(b'\r\n\r\n')
        lines = head.decode('ascii').split('\r\n')
        self.assertRegex(lines[0], r'\AHTTP/1\.[01] 200 OK\Z')
        headers = [line.partition(': ') for line in lines[1:]]
        names = sorted(name.lower() for name, _, value in headers)
        self.assertEqual(['cache-control', 'content-length', 'content-type', 'server', 'x-cpms-signature'], names)
        values = dict((name.lower(), value) for name, _, value in headers)
        self.assertEqual(('no-store', str(len(body)), 'application/json'),
                         (values['cache-control'], values['content-length'], values['content-type']))
        expected = crypto.response_message(LINK, NODE, named['nonce'], message, 200, 'application/json', body)
        self.assertTrue(crypto.verify(NODE_KEY, bytes.fromhex(values['x-cpms-signature']), expected))
        self.assertNotIn(b'set-cookie', reply.lower())

    def test_a_request_from_an_address_the_link_does_not_allow_is_refused(self):
        models.Link.objects.filter(pk=LINK).update(allowed_ips='203.0.113.9')
        self.refused('source_ip')
        self.refused('source_ip', error=transport.BadSignature, method='POST', body=BODY,
                     content_type='application/json', audited=dict(method='POST', size=len(BODY), status=200))

    def test_a_forwarding_header_does_not_change_where_a_request_came_from(self):
        forged = ['X-Forwarded-For: 203.0.113.9', 'Forwarded: for=203.0.113.9', 'X-Real-IP: 203.0.113.9',
                  'CF-Connecting-IP: 203.0.113.9', 'X_Forwarded_For: 203.0.113.9']
        models.Link.objects.filter(pk=LINK).update(allowed_ips='203.0.113.9')
        before = self.state()
        reply = self.raw(self.head(self.named()[0], more=forged))
        self.assertEqual(self.absent_on_the_wire(), reply)
        self.assertEqual(('refused', 'source_ip', LINK, '', '127.0.0.1'), self.last_audit()[1:6])
        self.assertEqual(before[:3], self.state()[:3])
        # And a controller at the allowed address is not turned away by one.
        models.Link.objects.filter(pk=LINK).update(allowed_ips='127.0.0.1')
        self.assertIn(b' 200 OK\r\n', self.raw(self.head(self.named()[0], more=forged)))
        self.assertEqual(('ok', '', LINK, 'admin', '127.0.0.1'), self.last_audit()[1:6])

    def test_a_replayed_request_is_refused_with_a_signed_reply(self):
        nonce = secrets.token_hex(16)
        self.assertEqual(200, self.send(nonce=nonce)[0])
        before = self.state()
        self.signed_refusal('replay', nonce=nonce)
        self.signed_refusal('replay', nonce=nonce, now=NOW + 1)
        self.assertEqual(before[:3], self.state()[:3])

    def test_a_request_signed_outside_the_window_or_behind_the_newest_is_refused(self):
        self.refused('time', now=NOW - 91)
        self.refused('time', now=NOW + 91)
        self.assertEqual(200, self.send(now=NOW + 5)[0])
        self.refused('time', now=NOW + 4)
        self.assertEqual(200, self.send(now=NOW + 5)[0])

    def test_a_request_changed_after_it_was_signed_is_refused(self):
        post = dict(method='POST', body=BODY, content_type='application/json')
        posted = dict(method='POST', size=len(BODY), status=200)
        host = b'Host: ' + self.authority.encode()
        for name, change, options, audited in (
                ('path', lambda data: data.replace(b'/gateway/hello ', b'/status ', 1), {},
                 dict(path='/multiserver/status')),
                ('query', lambda data: data.replace(b'/hello ', b'/hello?all=1 ', 1), {}, {}),
                ('query removed', lambda data: data.replace(b'?page=1', b'', 1), dict(query='page=1'), {}),
                ('host', lambda data: data.replace(host, b'Host: localhost:%d' % self.server.port, 1), {}, {}),
                ('method', lambda data: data.replace(b'POST ', b'GET ', 1).replace(b'Content-Length: 0\r\n', b''),
                 dict(method='POST'), {}),
                ('content type', lambda data: data.replace(b'Content-Type: application/json',
                                                           b'Content-Type: text/plain', 1), post, posted),
                ('body', lambda data: data.replace(b'request-body-secret', b'another-body-secret', 1), post, posted),
                ('actor', lambda data: data.replace(b'X-CPMS-Actor: admin', b'X-CPMS-Actor: root1', 1), {}, {}),
                ('mode', lambda data: data.replace(b'X-CPMS-Mode: json', b'X-CPMS-Mode: page', 1), {}, {}),
                ('time', lambda data: data.replace(b'X-CPMS-Timestamp: %d' % NOW,
                                                   b'X-CPMS-Timestamp: %d' % (NOW + 1), 1), {}, {})):
            with self.subTest(name):
                with self.changed_on_the_wire(change) as written:
                    self.refused('signature', error=transport.BadSignature if audited.get('status') == 200
                                 else transport.RedirectRefused, audited=audited, **options)
                written.assert_called_once()
        self.sessions.assert_not_called()

    def test_a_signed_in_administrators_cookie_with_a_bad_signature_is_nobody(self):
        cookie = 'Cookie: %s=%s' % (settings.SESSION_COOKIE_NAME, self.sign_in())
        status = ['GET /multiserver/status HTTP/1.1', 'Host: ' + self.authority, 'Connection: close', cookie]
        served = self.raw('\r\n'.join(status).encode('ascii') + b'\r\n\r\n')
        self.assertIn(b' 200 OK\r\n', served)
        self.assertIn(b'{"role": "node", "licensed": null}', served)
        plain = self.absent_on_the_wire()
        self.sessions.reset_mock()
        before = self.state()
        forged = self.named(key=STRANGER, path='/multiserver/status')[0]
        reply = self.raw(self.head(forged, path='/multiserver/status', more=[cookie]))
        self.assertEqual(plain, reply)
        self.assertNotIn(b'role', reply)
        self.assertNotIn(b'set-cookie', reply.lower())
        self.assertEqual(('refused', 'signature'), self.last_audit()[1:3])
        self.assertEqual(before[:3], self.state()[:3])
        self.sessions.assert_not_called()
        # With the controller's signature the cookie still opens no page: only what the gateway serves.
        valid = self.named(path='/multiserver/status')[0]
        reply = self.raw(self.head(valid, path='/multiserver/status', more=[cookie]))
        self.assertIn(b' 403 Forbidden\r\n', reply)
        self.assertTrue(reply.endswith(b'\r\n\r\n{"error":"not_allowed"}'))
        self.assertNotIn(b'set-cookie', reply.lower())
        self.sessions.assert_not_called()
        self.assertEqual(1, Session.objects.count())

    def test_an_unknown_paused_revoked_pending_or_expired_link_is_refused(self):
        unknown = transport.Link(
            link_id=OTHER_LINK, node_id=NODE, host='127.0.0.1', port=self.server.port, node_key=NODE_KEY,
            private_key=CONTROLLER, tls_pin=wire.pin('node'), allow_loopback_for_tests=True)
        self.refused('link', link=unknown, audited=dict(link_id=''))
        for status in (models.PAUSED, models.REVOKED, models.PENDING):
            models.Link.objects.filter(pk=LINK).update(status=status)
            self.refused('link')
        models.Link.objects.filter(pk=LINK).update(status=models.ACTIVE, expires_at=NOW)
        self.refused('expired')

    def test_a_link_of_an_earlier_generation_is_refused(self):
        self.assertEqual(200, self.send()[0])
        self.generation.return_value = 2
        self.refused('generation')

    def test_a_request_for_another_node_is_refused(self):
        other = crypto.public_key(STRANGER)
        elsewhere = transport.Link(
            link_id=LINK, node_id=crypto.node_id(other), host='127.0.0.1', port=self.server.port, node_key=other,
            private_key=CONTROLLER, tls_pin=wire.pin('node'), allow_loopback_for_tests=True)
        self.refused('link', link=elsewhere, audited=dict(link_id=''))

    def test_a_demoted_or_suspended_administrator_carries_no_request(self):
        Administrator.objects.filter(pk=self.administrator.pk).update(state='SUSPENDED')
        self.signed_refusal('admin')
        Administrator.objects.filter(pk=self.administrator.pk).update(state='ACTIVE', acl=self.reseller)
        self.signed_refusal('admin')
        self.empty(Administrator)
        self.signed_refusal('admin')

    def test_a_body_declared_larger_than_the_limit_is_refused(self):
        limit = transport.MAX_REQUEST_BODY
        named = self.named(method='POST', body=b'x' * 16, content_type='text/plain')[0]
        before = self.state()
        reply = self.raw(self.head(named, 'POST', content_type='text/plain', length=limit + 1)
                         + b'x' * (limit + 1))
        self.assertEqual(self.absent_on_the_wire(True), reply)
        self.assertEqual(('refused', 'size', '', '', '127.0.0.1', 'POST', HELLO, 200, limit + 1),
                         self.last_audit()[1:10])
        self.assertEqual(before[:3], self.state()[:3])
        with self.assertRaises(transport.InvalidRequest):
            self.send(method='POST', body=b'x' * (limit + 1), content_type='text/plain')

    def test_a_repeated_header_is_refused(self):
        for name in ('X-CPMS-Nonce', 'X-CPMS-Link', 'X-CPMS-Signature', 'X-CPMS-Timestamp', 'Host'):
            with self.subTest(name):
                named = self.named()[0]
                head = self.head(named)
                line = [line for line in head.split(b'\r\n') if line.startswith(name.encode() + b':')][0]
                before = self.state()
                reply = self.raw(self.head(named, more=[line.decode('ascii')]))
                self.assertEqual(self.absent_on_the_wire(), reply)
                self.assertEqual(('refused', 'format'), self.last_audit()[1:3])
                self.assertEqual(before[:3], self.state()[:3])
                # The same request without the repeat is a good one.
                self.assertIn(b' 200 OK\r\n', self.raw(head))

    def test_nothing_but_hello_is_served(self):
        for mode in crypto.MODES:
            for path in (HELLO, '/multiserver/status', '/base/', '/', '/verifyLogin', '/api/verifyConn',
                         '/cloudAPI/', '/firewall/', '/users/modifyUsers'):
                if (mode, path) != ('json', HELLO):
                    with self.subTest(mode=mode, path=path):
                        self.signed_refusal('not_allowed', mode=mode, path=path)
        self.signed_refusal('not_allowed', method='POST')
        self.signed_refusal('not_allowed', method='POST', body=BODY, content_type='application/json')
        self.signed_refusal('not_allowed', query='x=1')
        self.sessions.assert_not_called()
        self.assertEqual(0, Session.objects.count())

    def test_an_unsigned_refusal_is_byte_for_byte_the_answer_for_an_address_that_is_not_there(self):
        plain = self.absent_on_the_wire()
        self.assertIn(b' 302 Found\r\n', plain)
        for named in (self.named(key=STRANGER)[0], self.named(link_id=OTHER_LINK)[0],
                      self.named(timestamp=NOW - 500)[0], dict(self.named()[0], nonce='x')):
            self.assertEqual(plain, self.raw(self.head(named)))
        german = self.absent_on_the_wire(more=['Accept-Language: de'])
        self.assertNotEqual(plain, german)
        self.assertEqual(german, self.raw(self.head(self.named(key=STRANGER)[0], more=['Accept-Language: de'])))
        with_body = self.absent_on_the_wire(True)
        self.assertIn(b' 200 OK\r\n', with_body)
        named = self.named(key=STRANGER, method='POST', body=b'{"a": 1}', content_type='text/plain')[0]
        self.assertEqual(with_body, self.raw(self.head(named, 'POST', content_type='text/plain', length=8)
                                             + b'{"a": 1}'))

    def test_without_a_link_header_the_panel_answers_on_the_wire_as_it_does_without_the_gateway(self):
        with override_settings(MIDDLEWARE=[name for name in settings.MIDDLEWARE if name != GATEWAY]):
            without = Server(wire.CERTIFICATES['node'][0])  # builds its middleware here, without the gateway
        try:
            cookie = ['Cookie: %s=%s' % (settings.SESSION_COOKIE_NAME, self.sign_in())]
            for options in (dict(), dict(with_body=True), dict(more=['Accept-Language: de']),
                            dict(address='/base/'), dict(address=HELLO), dict(more=cookie, address=HELLO),
                            dict(more=cookie, address='/multiserver/status'), dict(more=cookie)):
                with self.subTest(repr(options)):
                    # The Host names the first server in both requests, so that nothing but the server differs.
                    self.assertEqual(self.absent_on_the_wire(port=without.port, **options),
                                     self.absent_on_the_wire(**options))
        finally:
            without.close()
        self.assertEqual(0, models.AuditEntry.objects.count())


if __name__ == '__main__':
    unittest.main()
