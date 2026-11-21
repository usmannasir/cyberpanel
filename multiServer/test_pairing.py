"""Pairing without a database: the code, the messages, the number, and the controller against a scripted server.

What a managed server does with a pairing request, on a real MariaDB, is in
multiServer/test_pairing_database.py.
"""
import ast
import base64
import hashlib
import os
from pathlib import Path
import shutil
import socket
import sys
import tempfile
import time
import traceback
import types
import unittest
from unittest import mock

from multiServer import audit, crypto, entitlement, keys, links, pairing, switch, test_transport, transport
from multiServer.test_transport import CERTIFICATES, Node, pin, wire

SEED = b'one-time-pairing-seed-material!!'
PAIRING_KEY = crypto.public_key(SEED).hex()
NODE_ID, TLS = 'b2' * 32, 'd4' * 32
VALUE, COMMITMENT = 'a9' * 32, 'e7' * 32
HERE = '127.0.0.1'  # the controller address a scripted server allows, and the one this suite calls from
PUBLIC_ADDRESS = '93.184.216.34'
NOW = 1795000000
LINK, NONCE = 'a1' * 16, 'c3' * 16
ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ234567'
GENERIC = (b'HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\nContent-Length: 0\r\n'
           b'Cache-Control: no-store\r\n\r\n')
# What the panel's request scanner refuses anywhere in a value (CyberCP/secMiddleware.py).
SCANNER_REFUSES = ('- -', '\n', ';', '&&', '|', '...', '`', '$', '(', ')', "'", '[', ']', '{', '}', ':', '<', '>',
                   '&')
Endpoint = transport.Endpoint


def setUpModule():
    test_transport.setUpModule()


def tearDownModule():
    test_transport.tearDownModule()


class Loopback(Endpoint):
    """The transport's allowance for tests, asked for in one place: this suite's server is on this machine."""
    __slots__ = ()

    def __init__(self, host, port, tls_pin):
        Endpoint.__init__(self, host, port, tls_pin, allow_loopback_for_tests=True)


def code(host=PUBLIC_ADDRESS, port=8090, node_id=NODE_ID, tls_pin=TLS, seed=SEED, commitment=COMMITMENT):
    return pairing._encode(host, port, node_id, tls_pin, seed, commitment)


def packed(payload, check=None):
    """A code built by hand from raw bytes, with a right check unless another is given."""
    text = base64.b32encode(payload + (pairing._check(payload) if check is None else check)).decode().rstrip('=')
    return pairing.PREFIX + '-'.join(text[start:start + 8] for start in range(0, len(text), 8))


def payload(host=b'\x04' + bytes([93, 184, 216, 34]), version=1, port=8090):
    return (bytes([version]) + port.to_bytes(2, 'big') + bytes.fromhex(NODE_ID + TLS) + SEED
            + bytes.fromhex(COMMITMENT) + host)


class Server(Node):
    """A local TLS server in the place of a managed server; `answer` writes whatever it replies."""

    @staticmethod
    def named(seen):
        return {'signature': dict((name.lower(), value) for name, value in seen.headers).get('x-cpms-signature', '')}


class Scripted(object):
    """What a managed server answers to a pairing request, with any part of it changed."""

    def __init__(self, key=None, sign_with=None, request=None, signature=None, status=200,
                 content_type='text/plain', body=None, extra=(), hold=False, value=None, allowed=HERE):
        self.key, self.sign_with, self.request, self.signature = key, sign_with, request, signature
        self.value, self.allowed = value, allowed
        self.status, self.content_type, self.body, self.extra, self.hold = status, content_type, body, extra, hold
        self.requests = []

    def __call__(self, node, connection, seen):
        link_id, pairing_key, controller_key, timestamp, nonce = seen.body.decode('ascii').split('\n')
        signed = crypto.pair_request_message(link_id, pairing_key, controller_key, node.id, node.pin,
                                             dict(seen.headers)['Host'], int(timestamp), nonce)
        verifies = crypto.verify(bytes.fromhex(pairing_key), bytes.fromhex(node.named(seen)['signature']), signed)
        self.requests.append(dict(link_id=link_id, pairing_key=pairing_key, controller_key=controller_key,
                                  timestamp=timestamp, nonce=nonce, signed=signed, verifies=verifies))
        public = self.key or node.public
        told = self.value or crypto.pair_value(node.private, pairing_key)
        value = self.signature(node, seen) if callable(self.signature) else self.signature
        if value is None:
            value = crypto.sign(self.sign_with or node.private, crypto.pair_response_message(
                self.request or signed, public.hex(), told, self.allowed)).hex()
            node.signatures.append(value)
        content = '\n'.join((public.hex(), told, self.allowed)).encode('ascii') if self.body is None else self.body
        headers = [('Content-Type', self.content_type), ('Content-Length', str(len(content)))]
        if value is not False:
            headers.append((transport.HEADERS['signature'], value))
        connection.sendall(wire(self.status, 'OK', headers + list(self.extra)) + content)
        if self.hold:
            node.release.wait(10)


def refuses(node, connection, seen):
    """The one answer a managed server gives to a request it does not accept."""
    connection.sendall(GENERIC)


def secrets_of(*nodes, **more):
    found = [SEED.hex(), SEED.decode(), base64.b64encode(SEED).decode(), base64.b32encode(SEED).decode().rstrip('=')]
    for node in nodes:
        found += [node.private.hex()] + [signature for signature in node.signatures if signature]
    return found + [value for value in more.values() if value]


def texts_of(error):
    texts = [''.join(traceback.format_exception(type(error), error, error.__traceback__))]
    while error is not None:
        texts += [str(error), repr(error), repr(error.args)]
        error = error.__cause__ or error.__context__
    return '\n'.join(texts)


class CodeTests(unittest.TestCase):
    def test_a_code_is_letters_digits_and_dashes_and_says_what_it_was_made_from(self):
        for host, length in ((PUBLIC_ADDRESS, 262), ('2a01:4f8::1', 285), ('node-1.example.com', 288),
                             ('a.' * 120 + 'example.com', 708)):
            text = code(host=host)
            self.assertEqual(length, len(text), host)
            self.assertRegex(text, r'^CPMS1-PAIR(-[A-Z2-7]{8})+(-[A-Z2-7]{1,7})?$')
            self.assertLessEqual(len(text), pairing.MAX_CODE)
            endpoint, node_id, seed, commitment = pairing._decode(text)
            self.assertEqual((host, 8090, TLS, NODE_ID, SEED, COMMITMENT),
                             (endpoint.host, endpoint.port, endpoint.tls_pin, node_id, seed, commitment))
            self.assertIs(Endpoint, type(endpoint))
            self.assertIs(False, endpoint.allow_loopback_for_tests)
        longest = '.'.join(['a' * 63] * 3 + ['b' * 61])
        self.assertEqual((253, 711, longest),
                         (len(longest), len(code(host=longest)), pairing.read_code(code(host=longest)).host))
        self.assertEqual(1024, pairing.MAX_CODE)

    def test_the_code_passes_the_panels_request_scanner(self):
        for host in (PUBLIC_ADDRESS, '2a01:4f8::1', 'node-1.example.com'):
            for seed in (SEED, bytes(32), b'\xff' * 32, os.urandom(32)):
                text = code(host=host, seed=seed)
                self.assertEqual(set(), set(text) - set('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-'))
                for refused in SCANNER_REFUSES:
                    self.assertNotIn(refused, text)
        source = Path(__file__).resolve().parent.parent.joinpath('CyberCP', 'secMiddleware.py').read_text()
        scanned = source[source.index('if not isAPIEndpoint and valueAlreadyChecked == 0:'):]
        scanned = scanned[:scanned.index('logging.writeToFile')]
        # The list above is the scanner's own: every string it searches a value for.
        found = set(getattr(node.args[0], 'value', None) or node.args[0].s
                    for node in ast.walk(ast.parse(scanned.strip() + '\n' + ' ' * 40 + 'pass'))
                    if isinstance(node, ast.Call) and getattr(node.func, 'attr', '') == 'find')
        self.assertEqual(set(SCANNER_REFUSES), found)

    def test_what_is_shown_before_connecting_is_the_address_and_the_fingerprints_and_never_the_seed(self):
        for host in (PUBLIC_ADDRESS, '2a01:4f8::1', 'node-1.example.com'):
            shown = pairing.read_code(code(host=host, port=2087))
            self.assertEqual((host, 2087, NODE_ID, TLS), tuple(shown))
            self.assertEqual(('host', 'port', 'node_id', 'tls_pin'), shown._fields)
            for text in (repr(shown), str(shown), repr(pairing._decode(code(host=host))[0])):
                for secret in secrets_of():
                    self.assertNotIn(secret, text)

    def test_any_one_character_changed_is_refused(self):
        for host in (PUBLIC_ADDRESS, 'node-1.example.com'):
            text = code(host=host)
            for position, old in enumerate(text):
                for new in ALPHABET + '-':
                    if new != old:
                        with self.assertRaises(pairing.PairingError, msg=(position, new)) as caught:
                            pairing.read_code(text[:position] + new + text[position + 1:])
                        self.assertEqual('format', caught.exception.reason)

    def test_only_the_one_whole_spelling_of_a_code_is_read(self):
        text = code(host='node-1.example.com')  # a length whose last character has bits to spare
        last = ALPHABET[ALPHABET.index(text[-1]) ^ 1]
        bare = text[len(pairing.PREFIX):].replace('-', '')
        self.assertEqual(base64.b32decode(bare + '=' * (-len(bare) % 8)),
                         base64.b32decode(bare[:-1] + last + '=' * (-len(bare) % 8)), 'a spare bit decodes alike')
        refused = [
            text[:-1] + last, text[:-1], text + 'A', text + '=', text + '-', text + '\n', ' ' + text, text + ' ',
            text.lower(), text.replace('-', ''), text.replace('-', ' '), text.replace('-', '--', 1),
            text[len(pairing.PREFIX):], 'CPMS2-PAIR-' + text[len(pairing.PREFIX):], pairing.PREFIX + bare,
            pairing.PREFIX + '-'.join(bare[start:start + 4] for start in range(0, len(bare), 4)),
            pairing.PREFIX[:-1], pairing.PREFIX, '', 'CPMS1-PAIR-A', text.encode(), None, 205, [text],
            text + '-AAAAAAAA' * 200,
        ]
        for candidate in refused:
            with self.assertRaises(pairing.PairingError, msg=repr(candidate)) as caught:
                pairing.read_code(candidate)
            self.assertEqual(('format', 'This is not a pairing code, or not all of one.'),
                             (caught.exception.reason, str(caught.exception)))
            for secret in secrets_of(code=text):
                self.assertNotIn(secret, texts_of(caught.exception))
        # What is not shaped like a code, or is longer than any code, is refused unread.
        with mock.patch.object(base64, 'b32decode') as decoded:
            for candidate in (text.lower(), ' ' + text, text + '\n', 'CPMS2-PAIR-' + text[len(pairing.PREFIX):],
                              pairing.PREFIX + bare, text + '=', text + '-AAAAAAAA' * 200,
                              pairing.PREFIX + '-'.join(['AAAAAAAA'] * 113)):
                with self.assertRaises(pairing.PairingError):
                    pairing.read_code(candidate)
            decoded.assert_not_called()
        self.assertLess(pairing.MAX_CODE, len(pairing.PREFIX + '-'.join(['AAAAAAAA'] * 113)))

    def test_a_code_with_a_right_check_but_wrong_contents_is_refused(self):
        self.assertEqual(code(), packed(payload()))
        name = b'\x00node-1.example.com'
        self.assertEqual('node-1.example.com', pairing.read_code(packed(payload(name))).host)
        for raw in (
                payload(version=0), payload(version=2), payload(port=0),
                payload(b'\x04' + bytes([93, 184, 216])), payload(b'\x04' + bytes([93, 184, 216, 34, 1])),
                payload(b'\x06' + b'\x20\x01' + bytes(13)), payload(b'\x06' + b'\x20\x01' + bytes(15)),
                payload(b'\x05' + bytes([93, 184, 216, 34])), payload(b'\x01' + bytes([93, 184, 216, 34])),
                # A host has one spelling: an address is never written as a name.
                payload(b'\x00' + PUBLIC_ADDRESS.encode()), payload(b'\x002a01:4f8::1'), payload(b'\x00'),
                payload(b'\x00Node-1.example.com'), payload(b'\x00node-1.example.com.'), payload(b'\x00localhost'),
                payload(b'\x00node_1.example.com'), payload(b'\x00node-1.example.com\n'),
                payload(b'\x00n\xc3\xb6de.example.com'), payload(b'\x00127.1'), payload(b'\x000x7f000001'),
                payload(b'')[:-1], payload(b''), b'', bytes(4)):
            with self.assertRaises(pairing.PairingError, msg=raw) as caught:
                pairing.read_code(packed(raw))
            self.assertEqual('format', caught.exception.reason, raw)
        for check in (bytes(4), hashlib.sha256(payload()).digest()[:4], pairing._check(payload())[::-1]):
            with self.assertRaises(pairing.PairingError):
                pairing.read_code(packed(payload(), check))

    def test_a_code_for_an_address_no_link_may_lead_to_is_refused_before_anything_is_connected(self):
        with mock.patch.object(socket, 'socket') as made, mock.patch.object(socket, 'getaddrinfo') as lookup:
            for address, kind in test_transport.AddressRuleTests.REFUSED:
                with self.assertRaises(pairing.PairingError, msg=address) as caught:
                    pairing.read_code(code(host=address))
                self.assertEqual(('not_allowed', 'A link may not connect to this address (%s).' % kind),
                                 (caught.exception.reason, str(caught.exception)), address)
            for address in test_transport.AddressRuleTests.ALLOWED:
                self.assertEqual(address, pairing.read_code(code(host=address)).host)
            made.assert_not_called()
            lookup.assert_not_called()


class MessageTests(unittest.TestCase):
    REQUEST = dict(link_id=LINK, pairing_key=PAIRING_KEY, controller_key='c1' * 32, node_id=NODE_ID,
                   tls_fingerprint=TLS, host='93.184.216.34:8090', timestamp=NOW, nonce=NONCE)

    def request(self, **changes):
        return crypto.pair_request_message(**dict(self.REQUEST, **changes))

    def test_the_request_has_a_type_line_and_one_line_per_field(self):
        self.assertEqual([b'CPMS1-PAIR-REQ', LINK.encode(), PAIRING_KEY.encode(), b'c1' * 32, NODE_ID.encode(),
                          TLS.encode(), b'93.184.216.34:8090', b'1795000000', NONCE.encode()],
                         self.request().split(b'\n'))
        for host in ('node-1.example.com:8090', '[2a01:4f8::1]:8090'):
            self.assertIn(b'\n' + host.encode() + b'\n', self.request(host=host))

    def test_every_field_changes_the_signed_bytes_and_none_can_be_read_two_ways(self):
        base = self.request()
        for field, other in (('link_id', 'a2' * 16), ('pairing_key', 'e5' * 32), ('controller_key', 'c2' * 32),
                             ('node_id', 'b3' * 32), ('tls_fingerprint', 'd5' * 32), ('host', '93.184.216.34:8091'),
                             ('timestamp', NOW + 1), ('nonce', 'c4' * 16)):
            self.assertNotEqual(base, self.request(**{field: other}), field)
        for change in (dict(link_id='A1' * 16), dict(link_id='a1' * 15), dict(link_id=LINK + '\n'),
                       dict(link_id=LINK.encode()), dict(pairing_key='e5' * 31), dict(pairing_key='E5' * 32),
                       dict(pairing_key=bytes(32)), dict(controller_key='c1' * 33), dict(controller_key=None),
                       dict(node_id='b2' * 31), dict(tls_fingerprint='D4' * 32), dict(tls_fingerprint=TLS + '\n'),
                       dict(host='93.184.216.34'), dict(host='93.184.216.34:0'), dict(host='a b:8090'),
                       dict(host='node\n:8090'), dict(host=None), dict(timestamp='1795000000'),
                       dict(timestamp=-1), dict(timestamp=True), dict(timestamp=10 ** 11),
                       dict(nonce='c3' * 15), dict(nonce='C3' * 16)):
            with self.assertRaises(ValueError, msg=change):
                self.request(**change)

    def test_the_reply_is_bound_to_exactly_one_pairing_request(self):
        request = self.request()
        answer = ('f6' * 32, VALUE, '203.0.113.9')
        message = crypto.pair_response_message(request, *answer)
        self.assertEqual([b'CPMS1-PAIR-RSP', hashlib.sha256(request).hexdigest().encode(), b'f6' * 32,
                          VALUE.encode(), b'203.0.113.9'], message.split(b'\n'))
        self.assertNotEqual(message, crypto.pair_response_message(self.request(nonce='c4' * 16), *answer))
        for other in (('f7' * 32, VALUE, '203.0.113.9'), ('f6' * 32, 'aa' * 32, '203.0.113.9'),
                      ('f6' * 32, VALUE, '203.0.113.10'), ('f6' * 32, VALUE, '2a01:4f8::9')):
            self.assertNotEqual(message, crypto.pair_response_message(request, *other))
        for bad in ((VALUE.upper(), '203.0.113.9'), (VALUE[:-2], '203.0.113.9'), (None, '203.0.113.9'),
                    (VALUE, '203.0.113.9\n'), (VALUE, 'controller.example.com'), (VALUE, '2A01:4F8::9'),
                    (VALUE, ''), (VALUE, None)):
            with self.assertRaises(ValueError, msg=bad):
                crypto.pair_response_message(request, 'f6' * 32, *bad)
        link_request = crypto.request_message(LINK, NODE_ID, 'GET', '93.184.216.34:8090', '/', '', '-', b'', NOW,
                                              NONCE, 'admin', 'json')
        for bad in ((link_request, 'f6' * 32), (request.decode(), 'f6' * 32), (b'', 'f6' * 32), (None, 'f6' * 32),
                    (b'CPMS1-PAIR-REQ', 'f6' * 32), (b'CPMS1-PAIR-REQUEST\n', 'f6' * 32), (message, 'f6' * 32),
                    (request, 'F6' * 32), (request, 'f6' * 31), (request, bytes(32)), (request, 'f6' * 32 + '\n')):
            with self.assertRaises(ValueError, msg=bad):
                crypto.pair_response_message(*bad + (VALUE, '203.0.113.9'))

    def test_the_value_of_a_pairing_is_the_servers_own_and_a_code_holds_it_to_it(self):
        identity, other = b'i' * 32, b'j' * 32
        value = crypto.pair_value(identity, PAIRING_KEY)
        self.assertRegex(value, '^[0-9a-f]{64}$')
        self.assertEqual(value, crypto.pair_value(identity, PAIRING_KEY), 'worked out again, never stored')
        self.assertNotEqual(value, crypto.pair_value(other, PAIRING_KEY))
        self.assertNotEqual(value, crypto.pair_value(identity, 'e5' * 32))
        for bad in ((identity[:31], PAIRING_KEY), (identity.hex(), PAIRING_KEY), (identity, PAIRING_KEY.upper()),
                    (identity, PAIRING_KEY[:-2]), (identity, None)):
            with self.assertRaises(ValueError, msg=bad):
                crypto.pair_value(*bad)
        fields = dict(value=value, host='93.184.216.34:8090', tls_fingerprint=TLS, controller_ip='203.0.113.9')
        commitment = crypto.pair_commitment(**fields)
        self.assertRegex(commitment, '^[0-9a-f]{64}$')
        self.assertNotIn(value, commitment)
        # Every part is fixed by it: with any one changed, the value in an answer no longer matches the code.
        for field, changed in (('value', crypto.pair_value(other, PAIRING_KEY)), ('host', '93.184.216.35:8090'),
                               ('host', '93.184.216.34:8091'), ('host', 'node-1.example.com:8090'),
                               ('tls_fingerprint', 'd5' * 32), ('controller_ip', '203.0.113.10'),
                               ('controller_ip', '2a01:4f8::9')):
            self.assertNotEqual(commitment, crypto.pair_commitment(**dict(fields, **{field: changed})), field)
        for field, bad in (('value', value.upper()), ('value', value[:-2]), ('host', '93.184.216.34'),
                           ('host', None), ('tls_fingerprint', TLS + '\n'), ('controller_ip', '203.0.113.9\n'),
                           ('controller_ip', 'Controller'), ('controller_ip', None)):
            with self.assertRaises(ValueError, msg=(field, bad)):
                crypto.pair_commitment(**dict(fields, **{field: bad}))

    def test_the_confirmation_is_made_of_what_both_servers_keep(self):
        fields = dict(link_id=LINK, pairing_key=PAIRING_KEY, controller_key='c1' * 32, node_key='f6' * 32,
                      value=VALUE)
        message = crypto.pair_confirmation_message(**fields)
        self.assertEqual([b'CPMS1-PAIR-SAS', LINK.encode(), PAIRING_KEY.encode(), b'c1' * 32, b'f6' * 32,
                          VALUE.encode()], message.split(b'\n'))
        for field, other in (('link_id', 'a2' * 16), ('pairing_key', 'e5' * 32), ('controller_key', 'c2' * 32),
                             ('node_key', 'f7' * 32), ('value', 'aa' * 32)):
            self.assertNotEqual(message, crypto.pair_confirmation_message(**dict(fields, **{field: other})))
            for bad in (other.upper(), other[:-2], other + '\n', None):
                with self.assertRaises(ValueError):
                    crypto.pair_confirmation_message(**dict(fields, **{field: bad}))

    def test_no_message_of_one_type_is_a_valid_message_of_another(self):
        private = crypto.generate_private_key()
        public = crypto.public_key(private)
        link_request = crypto.request_message(LINK, NODE_ID, 'GET', '93.184.216.34:8090', '/', '', '-', b'', NOW,
                                              NONCE, 'admin', 'json')
        messages = [
            link_request, crypto.response_message(LINK, NODE_ID, NONCE, link_request, 200, '-', b''),
            crypto.hello_message(NODE_ID, NONCE, TLS, NOW), self.request(),
            crypto.pair_response_message(self.request(), 'f6' * 32, VALUE, '203.0.113.9'),
            crypto.pair_confirmation_message(LINK, PAIRING_KEY, 'c1' * 32, 'f6' * 32, VALUE),
            b'CPMS1-PAIR-VALUE\n' + PAIRING_KEY.encode(),
            b'CPMS1-PAIR-COMMIT\n' + VALUE.encode() + b'\n93.184.216.34:8090\n' + TLS.encode() + b'\n203.0.113.9']
        self.assertEqual(8, len(set(message.split(b'\n', 1)[0] for message in messages)))
        for number, message in enumerate(messages):
            signature = crypto.sign(private, message)
            self.assertEqual([number == other for other in range(8)],
                             [crypto.verify(public, signature, different) for different in messages])


class ConfirmationTests(unittest.TestCase):
    def transcript(self, link_id=LINK):
        return crypto.pair_confirmation_message(link_id, PAIRING_KEY, 'c1' * 32, 'f6' * 32, VALUE)

    def test_the_number_is_eight_digits_taken_from_the_transcript(self):
        transcript = self.transcript()
        expected = '%08d' % (int.from_bytes(hashlib.sha256(transcript).digest()[:8], 'big') % 10 ** 8)
        self.assertEqual(expected, pairing.confirmation_number(transcript))
        self.assertEqual('93649461', pairing.confirmation_number(
            crypto.pair_confirmation_message('a1' * 16, 'b2' * 32, 'c3' * 32, 'd4' * 32, 'e5' * 32)))
        numbers = set()
        for number in range(400):
            value = pairing.confirmation_number(self.transcript('%032x' % number))
            self.assertRegex(value, '^[0-9]{8}$')
            numbers.add(value)
        self.assertEqual(400, len(numbers))
        self.assertTrue(any(value.startswith('0') for value in numbers), 'a leading zero is kept')

    def test_the_number_changes_with_each_thing_it_is_taken_from(self):
        fields = dict(link_id=LINK, pairing_key=PAIRING_KEY, controller_key='c1' * 32, node_key='f6' * 32,
                      value=VALUE)
        number = pairing.confirmation_number(crypto.pair_confirmation_message(**fields))
        for field, other in (('link_id', 'a2' * 16), ('pairing_key', 'e5' * 32), ('controller_key', 'c2' * 32),
                             ('node_key', 'f7' * 32), ('value', 'aa' * 32)):
            self.assertNotEqual(number, pairing.confirmation_number(
                crypto.pair_confirmation_message(**dict(fields, **{field: other}))), field)

    def test_the_number_is_taken_from_nothing_else(self):
        request = MessageTests().request()
        for other in (request, crypto.pair_response_message(request, 'f6' * 32, VALUE, '203.0.113.9'),
                      self.transcript().decode(),
                      b'CPMS1-PAIR-SAS', b'', None, self.transcript()[1:]):
            with self.assertRaises(ValueError):
                pairing.confirmation_number(other)


class EndpointTests(unittest.TestCase):
    def test_an_endpoint_holds_what_it_was_built_from_and_cannot_be_changed(self):
        for host, authority in ((PUBLIC_ADDRESS, PUBLIC_ADDRESS + ':8090'), ('2a01:4f8::1', '[2a01:4f8::1]:8090'),
                                ('node-1.example.com', 'node-1.example.com:8090')):
            endpoint = Endpoint(host, 8090, TLS)
            self.assertEqual((host, 8090, authority, TLS, False),
                             tuple(getattr(endpoint, name) for name in Endpoint.__slots__))
            self.assertEqual('Endpoint(%s)' % authority, repr(endpoint))
            self.assertNotIn(TLS, repr(endpoint) + str(endpoint))
            self.assertFalse(hasattr(endpoint, '__dict__'))
            for name in Endpoint.__slots__ + ('other',):
                with self.assertRaises(AttributeError):
                    setattr(endpoint, name, getattr(endpoint, name, None))
                with self.assertRaises(AttributeError):
                    delattr(endpoint, name)
            self.assertEqual(host, endpoint.host)

    def test_it_follows_the_rules_of_a_link(self):
        for change in (dict(port=0), dict(port=65536), dict(port='8090'), dict(port=True), dict(port=None),
                       dict(tls_pin='D4' * 32), dict(tls_pin='d4' * 31), dict(tls_pin=TLS + '\n'),
                       dict(tls_pin=bytes(32)), dict(tls_pin=None), dict(allow_loopback_for_tests=1),
                       dict(allow_loopback_for_tests=None), dict(host=''), dict(host='localhost'),
                       dict(host='Node-1.example.com'), dict(host='node-1.example.com.'), dict(host='127.1'),
                       dict(host='2130706433'), dict(host='010.0.0.1'), dict(host='1.1.1.1:8090'),
                       dict(host='[2a01:4f8::1]'), dict(host='2A01:4F8::1'), dict(host='2a01:4f8:0:0:0:0:0:1'),
                       dict(host='2a01:4f8::1%eth0'), dict(host=b'1.1.1.1'), dict(host=None), dict(host=16843009)):
            fields = dict(host=PUBLIC_ADDRESS, port=8090, tls_pin=TLS)
            fields.update(change)
            with self.assertRaises(transport.InvalidLink, msg=change):
                Endpoint(**fields)
        for address, kind in test_transport.AddressRuleTests.REFUSED:
            with self.assertRaises(transport.RefusedAddress, msg=address):
                Endpoint(address, 8090, TLS)
            if kind != 'loopback':
                with self.assertRaises(transport.RefusedAddress, msg=address):
                    Endpoint(address, 8090, TLS, allow_loopback_for_tests=True)
        self.assertEqual('127.0.0.1', Endpoint('127.0.0.1', 8090, TLS, allow_loopback_for_tests=True).host)


class ExchangeTests(unittest.TestCase):
    BODY = b'first line\nsecond line'
    SIGNATURE = bytes(range(64))

    def node(self, *arguments, **options):
        node = Server(*arguments, **options)
        self.addCleanup(node.close)
        return node

    def exchange(self, node, **changes):
        fields = dict(endpoint=Loopback('127.0.0.1', node.port, node.pin), path='/multiserver/pair', body=self.BODY,
                      signature=self.SIGNATURE)
        fields.update(changes)
        with mock.patch.object(transport, 'Endpoint', Loopback):
            return transport.exchange(**fields)

    def test_one_request_goes_out_and_the_one_whole_reply_comes_back_unjudged(self):
        node = self.node(test_transport.reply(content_type='text/plain', body=b'reply', signature='ab' * 64))
        self.assertEqual((200, 'text/plain', b'reply', b'\xab' * 64), self.exchange(node))
        seen = node.finished()['seen']
        self.assertEqual(('POST', '/multiserver/pair', 'HTTP/1.1', self.BODY),
                         (seen.method, seen.target, seen.version, seen.body))
        self.assertEqual([('Host', '127.0.0.1:%d' % node.port), ('Connection', 'close'),
                          ('Accept-Encoding', 'identity'), ('Content-Type', 'text/plain'),
                          ('Content-Length', str(len(self.BODY))), ('X-CPMS-Signature', self.SIGNATURE.hex())],
                         seen.headers)
        self.assertEqual([None], node.names)

    def test_a_server_with_another_certificate_receives_no_request_byte(self):
        node = self.node(certificate='impostor')
        with self.assertRaises(transport.CertificateMismatch):
            self.exchange(node, endpoint=Loopback('127.0.0.1', node.port, pin('node')))
        record = node.finished()
        self.assertEqual((True, b'', None), (record['tls'], record['raw'], record['seen']))

    def test_the_reply_is_framed_as_on_a_link(self):
        reply = test_transport.reply
        for answer, error in ((reply(signature=False), transport.BadSignature), (refuses, transport.BadSignature),
                              (reply(status=302, signature='ab' * 64), transport.RedirectRefused),
                              (reply(signature='ab' * 64, then=b'x'), transport.MalformedResponse),
                              (reply(signature='ab' * 64, length='9' * 18), transport.ResponseTooLarge),
                              (lambda node, connection, seen: None, transport.ConnectionFailed)):
            with self.assertRaises(transport.TransportError) as caught:
                self.exchange(self.node(answer))
            self.assertIs(error, type(caught.exception))
        with mock.patch.object(transport, 'DEADLINE', 0.4):
            with self.assertRaises(transport.TimedOut):
                self.exchange(self.node(test_transport.reply(signature='ab' * 64, hold=True)))

    def test_nothing_is_connected_for_what_is_not_an_endpoint_or_cannot_be_sent(self):
        endpoint = Endpoint(PUBLIC_ADDRESS, 8090, TLS)

        class Lookalike(Endpoint):
            __slots__ = ()
        link = transport.Link(LINK, crypto.node_id(crypto.public_key(SEED)), PUBLIC_ADDRESS, 8090,
                              crypto.public_key(SEED), SEED, TLS)
        with mock.patch.object(socket, 'socket') as made, mock.patch.object(socket, 'getaddrinfo') as lookup:
            for candidate in (None, link, Lookalike(PUBLIC_ADDRESS, 8090, TLS), (PUBLIC_ADDRESS, 8090, TLS), Endpoint,
                              Loopback('127.0.0.1', 8090, TLS)):
                with self.assertRaises(transport.InvalidLink):
                    transport.exchange(candidate, '/multiserver/pair', self.BODY, self.SIGNATURE)
            for change in (dict(path='/multiserver/pair?x=1'), dict(path='/multiserver/pair\r\nX-Injected: 1'),
                           dict(path='multiserver/pair'), dict(path='/multiserver/../pair'), dict(path=None),
                           dict(body='text'), dict(body=None), dict(body=bytearray(self.BODY)),
                           dict(signature=self.SIGNATURE.hex()), dict(signature=self.SIGNATURE[:63]),
                           dict(signature=self.SIGNATURE + b'\x00'), dict(signature=None)):
                fields = dict(endpoint=endpoint, path='/multiserver/pair', body=self.BODY, signature=self.SIGNATURE)
                fields.update(change)
                with self.assertRaises(transport.InvalidRequest, msg=change) as caught:
                    transport.exchange(**fields)
                self.assertNotIn(self.SIGNATURE.hex(), texts_of(caught.exception))
            with mock.patch.object(transport, 'MAX_REQUEST_BODY', len(self.BODY) - 1):
                with self.assertRaises(transport.InvalidRequest):
                    transport.exchange(endpoint, '/multiserver/pair', self.BODY, self.SIGNATURE)
            made.assert_not_called()
            lookup.assert_not_called()

    def test_a_name_that_resolves_to_a_refused_address_is_never_connected_to(self):
        inside = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.5', 8090))]
        with mock.patch.object(socket, 'getaddrinfo', return_value=inside), \
                mock.patch.object(socket, 'socket') as made:
            for endpoint in (Endpoint('node-1.example.com', 8090, TLS), Loopback('node-1.example.com', 8090, TLS)):
                with mock.patch.object(transport, 'Endpoint', type(endpoint)):
                    with self.assertRaises(transport.RefusedAddress):
                        transport.exchange(endpoint, '/multiserver/pair', self.BODY, self.SIGNATURE)
            made.assert_not_called()


class Controller(unittest.TestCase):
    """A licensed controller and a scripted managed server on this machine."""

    def setUp(self):
        self.audited, self.stored, self.prepared, self.kept_for = [], [], [], []
        self.unkept = self.unstored = None  # what the controller's records raise, when a test says so
        self.role = mock.patch.object(switch, 'active_role', return_value=keys.CONTROLLER).start()
        self.licensed = mock.patch.object(entitlement, 'allowed', return_value=True).start()
        mock.patch.object(audit, 'record', side_effect=self.record).start()
        # The controller's records are multiServer/links.py, tested by itself; here they are stood in for.
        mock.patch.object(links, 'pairing_slot').start()
        mock.patch.object(links, 'prepare', side_effect=self.prepare).start()
        mock.patch.object(links, 'store', side_effect=self.store).start()
        mock.patch.object(transport, 'Endpoint', Loopback).start()
        mock.patch.object(pairing, '_now', return_value=NOW).start()
        self.addCleanup(mock.patch.stopall)

    def record(self, event, **fields):
        self.audited.append((event, fields))
        return True

    def prepare(self, *arguments):
        self.prepared.append(arguments)
        if self.unkept is not None:
            raise self.unkept

    def store(self, label, link_id, host, port, node_key, private_key, tls_pin, actor, of_pairing):
        if self.unstored is not None:
            raise self.unstored(private_key, tls_pin)
        self.stored.append((label, link_id, host, port, node_key, private_key, tls_pin))
        self.kept_for.append(actor)
        self.kept_of_pairing = of_pairing

    def node(self, *arguments, **options):
        node = Server(*arguments, **options)
        self.addCleanup(node.close)
        return node

    def code(self, node, **changes):
        fields = dict(host='127.0.0.1', port=node.port, node_id=node.id, tls_pin=node.pin)
        fields.update(changes)
        if 'commitment' not in fields:
            # What an honest server with this identity key writes into a code for a controller at HERE.
            fields['commitment'] = crypto.pair_commitment(
                crypto.pair_value(node.private, crypto.public_key(fields.get('seed', SEED)).hex()),
                ('[%s]:%d' if ':' in fields['host'] else '%s:%d') % (fields['host'], fields['port']),
                fields['tls_pin'], HERE)
        return code(**fields)

    def refused(self, reason, text, because=None, outcome='refused', node=None, recorded=False, link=False,
                **options):
        """Pairing ends in exactly this refusal: nothing is kept, one audit row, nothing secret said."""
        self.audited[:] = []
        with self.assertRaises(pairing.PairingError) as caught:
            pairing.start(text, options.get('label', 'Frankfurt 1'), options.get('actor', 'admin'))
        error = caught.exception
        self.assertEqual(reason, error.reason, str(error))
        if because is not None:
            self.assertEqual(because, str(error))
        self.assertEqual([], self.stored)
        expected = dict(outcome=outcome, reason=reason)
        if isinstance(options.get('actor', 'admin'), str):
            expected['actor'] = options.get('actor', 'admin')
        if link:
            expected['link_id'] = error.link_id
        # A link that could not be stored is put on record by the store itself, and not a second time.
        self.assertEqual([] if recorded else [('pairing', expected)], self.audited)
        self.assertIs(recorded, error.recorded)
        for secret in secrets_of(*([node] if node else []), code=text if isinstance(text, str) else None):
            self.assertNotIn(secret, texts_of(error))
            self.assertNotIn(secret, repr(self.audited))
        return error


class PairingTests(Controller):
    def test_a_correct_pairing_keeps_one_link_and_shows_the_number_both_servers_hold(self):
        script = Scripted()
        node = self.node(script)
        paired = pairing.start(self.code(node), 'Frankfurt 1', 'admin')
        (seen,) = script.requests
        self.assertIs(True, seen['verifies'])
        self.assertEqual(PAIRING_KEY, seen['pairing_key'])
        (label, link_id, host, port, node_key, private_key, tls_pin), = self.stored
        self.assertEqual(('Frankfurt 1', seen['link_id'], '127.0.0.1', node.port, node.public, node.pin),
                         (label, link_id, host, port, node_key, tls_pin))
        self.assertEqual(seen['controller_key'], crypto.public_key(private_key).hex())
        # What was kept is exactly a link the signed channel accepts.
        transport.Link(link_id, node.id, host, port, node_key, private_key, tls_pin, allow_loopback_for_tests=True)
        value = crypto.pair_value(node.private, PAIRING_KEY)
        number = pairing.confirmation_number(crypto.pair_confirmation_message(
            link_id, PAIRING_KEY, seen['controller_key'], node.public.hex(), value))
        self.assertEqual(pairing.Paired(link_id, node.id, '127.0.0.1', node.port, number), paired)
        # Kept with the link, so that the number can be shown again while the link waits.
        self.assertEqual((PAIRING_KEY, value), self.kept_of_pairing)
        self.assertRegex(paired.confirmation, '^[0-9]{8}$')
        # Kept for the administrator who paired; the record of it is the store's own (multiServer/links.py).
        self.assertEqual((['admin'], []), (self.kept_for, self.audited))
        # And what was checked before the code was used is what was kept, but for the key not yet known.
        self.assertEqual([(label, link_id, node.id, host, port, private_key, tls_pin)], self.prepared)

    def test_whether_the_link_can_be_kept_is_settled_before_the_server_hears_anything(self):
        node = self.node(Scripted())
        asked = []
        with mock.patch.object(links, 'prepare', side_effect=lambda *given: asked.append(node.connections.empty())):
            pairing.start(self.code(node), 'Frankfurt 1', 'admin')
        self.assertEqual([True], asked)
        self.assertEqual(1, len(self.stored))

    def test_the_server_is_sent_exactly_the_signed_request_and_nothing_else(self):
        script = Scripted()
        node = self.node(script)
        pairing.start(self.code(node), 'Frankfurt 1', 'admin')
        record = node.finished()
        seen, sent = record['seen'], script.requests[0]
        self.assertEqual(('POST', '/multiserver/pair', 'HTTP/1.1'), (seen.method, seen.target, seen.version))
        self.assertEqual([('Host', '127.0.0.1:%d' % node.port), ('Connection', 'close'),
                          ('Accept-Encoding', 'identity'), ('Content-Type', 'text/plain'),
                          ('Content-Length', str(len(seen.body)))], seen.headers[:-1])
        self.assertEqual('X-CPMS-Signature', seen.headers[-1][0])
        self.assertEqual('\n'.join((sent['link_id'], PAIRING_KEY, sent['controller_key'], str(NOW), sent['nonce'])),
                         seen.body.decode())
        self.assertRegex(seen.body.decode(), '^[0-9a-f]{32}\n[0-9a-f]{64}\n[0-9a-f]{64}\n1795000000\n[0-9a-f]{32}$')
        self.assertLessEqual(len(seen.body), pairing.MAX_BODY)
        self.assertEqual([b'CPMS1-PAIR-REQ', sent['link_id'].encode(), PAIRING_KEY.encode(),
                          sent['controller_key'].encode(), node.id.encode(), node.pin.encode(),
                          b'127.0.0.1:%d' % node.port, b'1795000000', sent['nonce'].encode()],
                         sent['signed'].split(b'\n'))
        # Neither the seed nor the code travels, and the private key of the link never leaves.
        for secret in secrets_of(private=self.stored[0][5].hex(), code=self.code(node)):
            self.assertNotIn(secret.encode(), record['raw'])

    def test_every_pairing_has_a_link_id_a_nonce_and_a_key_of_its_own(self):
        script = Scripted()
        node = self.node(script)
        for unused in range(3):
            pairing.start(self.code(node), 'Frankfurt 1', 'admin')
        for field in ('link_id', 'nonce', 'controller_key'):
            self.assertEqual(3, len(set(sent[field] for sent in script.requests)), field)
        self.assertEqual(3, len(set(stored[5] for stored in self.stored)))

    def test_a_server_named_by_host_name_is_asked_for_by_that_name(self):
        script = Scripted()
        node = self.node(script)
        here = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('127.0.0.1', node.port))]
        with mock.patch.object(socket, 'getaddrinfo', return_value=here):
            paired = pairing.start(self.code(node, host='node-1.example.com'), 'Frankfurt 1', 'admin')
        self.assertEqual(('node-1.example.com', ['node-1.example.com']), (paired.host, node.names))
        self.assertIn(b'\nnode-1.example.com:%d\n' % node.port, script.requests[0]['signed'])
        inside = [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('10.0.0.5', node.port))]
        self.stored[:] = []
        with mock.patch.object(socket, 'getaddrinfo', return_value=inside), \
                mock.patch.object(socket, 'socket') as made:
            self.refused('not_allowed', self.code(node, host='node-1.example.com'),
                         'A link may not connect to this address (private).')
            made.assert_not_called()


class RefusalTests(Controller):
    def test_only_a_licensed_controller_pairs_and_asks_nobody_else(self):
        node = self.node(Scripted())
        with mock.patch.object(socket, 'socket') as made:
            for role in (keys.OFF, keys.NODE):
                self.role.return_value = role
                self.refused('role', self.code(node), 'This server is not a Multi-Server Manager controller.')
            self.licensed.assert_not_called()
            self.role.return_value = keys.CONTROLLER
            for answer in (False, None, 1, 'yes'):
                self.licensed.return_value = answer
                self.refused('licence', self.code(node), 'This server has no Multi-Server Manager licence.')
            made.assert_not_called()
        self.assertTrue(node.connections.empty())

    def test_what_cannot_be_kept_or_read_is_refused_before_anything_is_connected(self):
        node = self.node(Scripted())
        with mock.patch.object(socket, 'socket') as made:
            for options in (dict(label=''), dict(label='x' * 65), dict(label='two\nlines'), dict(label=None),
                            dict(label=b'Frankfurt 1'), dict(label=' Frankfurt'), dict(label='Frankfurt '),
                            dict(label='<b>Frankfurt</b>'), dict(label='{$ 7 * 7 $}'), dict(label='Frankfurt\x00'),
                            dict(actor=''), dict(actor='a b'), dict(actor=None), dict(actor='x' * 51)):
                self.refused('format', self.code(node), **options)
            # The label is held to the rule of the records it will be kept in, and to no second one.
            with mock.patch.object(links, 'check_label', side_effect=links.InvalidLabel('Not a label.')) as checked:
                self.refused('format', self.code(node), 'Not a label.')
            checked.assert_called_once_with('Frankfurt 1')
            self.assertEqual([], self.prepared)
            text = self.code(node)
            for changed in (text[:-1], text[:20] + ('A' if text[20] != 'A' else 'B') + text[21:], text.lower(), '',
                            None):
                self.refused('format', changed, 'This is not a pairing code, or not all of one.')
            for address, kind in (('10.0.0.5', 'private'), ('169.254.169.254', 'cloud metadata'),
                                  ('0.0.0.0', 'unspecified'), ('192.168.1.9', 'private'),
                                  ('fd00:ec2::254', 'cloud metadata')):
                self.refused('not_allowed', self.code(node, host=address),
                             'A link may not connect to this address (%s).' % kind)
            made.assert_not_called()
        self.assertTrue(node.connections.empty())

    def test_a_link_this_controller_could_not_keep_is_refused_while_the_code_is_still_unused(self):
        node = self.node(Scripted())
        with mock.patch.object(socket, 'socket') as made:
            for raised, reason, outcome, because in (
                    (links.DuplicateNode('This server is already connected.'), 'link', 'refused',
                     'This server is already connected.'),
                    (links.NoMasterKey('The master key of this controller is missing or cannot be used.'),
                     'internal', 'error', 'The master key of this controller is missing or cannot be used.'),
                    (links.UnreadableRow('A server stored earlier has connection details that cannot be read. '
                                         'Remove that server before connecting another.'), 'internal', 'error',
                     'A server stored earlier has connection details that cannot be read. Remove that server '
                     'before connecting another.'),
                    (links.Busy('Another server is being stored at this moment.'), 'internal', 'error',
                     'Another server is being stored at this moment.'),
                    (links.NotController(links.NOT_CONTROLLER), 'role', 'refused', links.NOT_CONTROLLER),
                    (links.InvalidLabel('Not a label.'), 'format', 'refused', 'Not a label.'),
                    (transport.RefusedAddress('A link may not connect to this address (private).'), 'not_allowed',
                     'refused', 'A link may not connect to this address (private).'),
                    # Anything else is said in general, and not in its own words.
                    (links.InvalidRecord('holds %s' % SEED.hex()), 'internal', 'error',
                     'Pairing failed on this server.'),
                    (RuntimeError('cannot seal %s' % SEED.hex()), 'internal', 'error',
                     'Pairing failed on this server.')):
                self.unkept = raised
                error = self.refused(reason, self.code(node), because, outcome=outcome)
                self.assertIsNone(error.__cause__ or error.__context__)
            made.assert_not_called()
        self.assertTrue(node.connections.empty())
        self.assertEqual(9, len(self.prepared))
        # With nothing in the way, the same code still pairs: it was never sent.
        self.unkept = None
        pairing.start(self.code(node), 'Frankfurt 1', 'admin')
        self.assertEqual(1, len(self.stored))

    def test_without_the_allowance_for_tests_this_machine_is_refused_too(self):
        node = self.node(Scripted())
        with mock.patch.object(transport, 'Endpoint', Endpoint):
            self.refused('not_allowed', self.code(node), 'A link may not connect to this address (loopback).')
        self.assertTrue(node.connections.empty())

    def test_a_server_with_another_certificate_is_sent_no_request_byte(self):
        script = Scripted()
        impostor = self.node(script, certificate='impostor')
        self.refused('certificate', self.code(impostor, tls_pin=pin('node')), 'The server at that address did not '
                     'present the certificate the pairing code names. Nothing was sent to it.', node=impostor)
        record = impostor.finished()
        self.assertEqual((True, b'', None), (record['tls'], record['raw'], record['seen']))
        self.assertEqual([], script.requests)

    def test_a_server_that_answers_with_another_identity_key_is_refused(self):
        other = crypto.generate_private_key()
        script = Scripted(key=crypto.public_key(other), sign_with=other)
        node = self.node(script)
        self.refused('signature', self.code(node), 'The server that answered is not the one this pairing code names.',
                     node=node)
        self.assertIs(True, script.requests[0]['verifies'], 'the request itself was in order')

    def test_a_server_whose_identity_key_anybody_can_sign_for_is_refused(self):
        # The neutral point as identity key: this made-up signature verifies under it for every message.
        neutral = bytes.fromhex('01' + '00' * 31)
        made_up = (neutral + bytes(32)).hex()
        for key in (neutral, bytes.fromhex('01' + '00' * 30 + '80'), bytes(32), bytes.fromhex('ec' + 'ff' * 30 + '7f')):
            script = Scripted(key=key, signature=made_up)
            node = self.node(script)
            self.refused('format', self.code(node, node_id=crypto.node_id(key)),
                         'The server did not answer as a managed server does.', node=node)
            # The answer itself would pass: that key is the one the code names, and the signature verifies.
            signed = crypto.pair_response_message(crypto.pair_request_message(
                LINK, PAIRING_KEY, 'c1' * 32, NODE_ID, TLS, '93.184.216.34:8090', NOW, NONCE), key.hex(), VALUE, HERE)
            if key == neutral:
                self.assertTrue(crypto.verify(key, bytes.fromhex(made_up), signed))

    def test_an_answer_not_signed_by_the_named_server_for_this_request_is_refused(self):
        other = crypto.generate_private_key()
        earlier = crypto.pair_request_message(LINK, PAIRING_KEY, 'c1' * 32, NODE_ID, TLS, '93.184.216.34:8090', NOW,
                                              NONCE)

        def sent_back(node, seen):
            return node.named(seen)['signature']

        def over_the_request(node, seen):
            sent = seen.body.decode().split('\n')
            return crypto.sign(node.private, crypto.pair_request_message(
                sent[0], sent[1], sent[2], node.id, node.pin, dict(seen.headers)['Host'], NOW, sent[4])).hex()

        def as_on_a_link(node, seen):
            request = crypto.request_message(LINK, node.id, 'GET', '93.184.216.34:8090', '/', '', '-', b'', NOW,
                                             NONCE, 'admin', 'json')
            return crypto.sign(node.private, crypto.response_message(
                LINK, node.id, NONCE, request, 200, 'text/plain', node.public.hex().encode())).hex()
        for name, script in (
                ('another key', Scripted(sign_with=other)), ('the one-time key', Scripted(sign_with=SEED)),
                ('an earlier request', Scripted(request=earlier)),
                ('the request signature sent back', Scripted(signature=sent_back)),
                ('zeros', Scripted(signature='00' * 64)),
                ('the request itself', Scripted(signature=over_the_request)),
                ('a reply as on a link', Scripted(signature=as_on_a_link))):
            with self.subTest(name):
                node = self.node(script)
                self.refused('signature', self.code(node),
                             'The answer is not signed by the server this pairing code names.', node=node)

    def test_an_unsigned_answer_is_the_servers_refusal_whatever_it_says(self):
        because = ('The server did not accept the pairing code. A code can be used once, for ten minutes, from the '
                   'controller address it was made for.')
        for name, answer in (('the refusal of a managed server', refuses),
                             ('200 without a signature', Scripted(signature=False)),
                             ('a signature that is not one', Scripted(signature='zz' * 64)),
                             ('a short signature', Scripted(signature='ab' * 63)),
                             ('the panel asking for a session', lambda node, connection, seen: connection.sendall(
                                 wire(200, 'OK', [('Content-Type', 'text/html'), ('Content-Length', '2')]) + b'{}'))):
            with self.subTest(name):
                node = self.node(answer)
                self.refused('signature', self.code(node), because, node=node)

    def test_a_signed_answer_that_is_not_an_acceptance_is_refused(self):
        key = crypto.generate_private_key()
        for name, script in (('403', Scripted(status=403)), ('500', Scripted(status=500)),
                             ('201', Scripted(status=201)), ('json', Scripted(content_type='application/json')),
                             ('no body', Scripted(body=b'')),
                             ('a key in upper case', Scripted(body=crypto.public_key(key).hex().upper().encode())),
                             ('a key and a line feed', Scripted(body=crypto.public_key(key).hex().encode() + b'\n')),
                             ('a short key', Scripted(body=b'ab' * 31)),
                             ('raw bytes', Scripted(body=crypto.public_key(key))),
                             ('two keys', Scripted(body=b'ab' * 64)),
                             ('a key and nothing else', Scripted(body=crypto.public_key(key).hex().encode())),
                             ('no address', Scripted(body=b'ab' * 32 + b'\n' + b'cd' * 32)),
                             ('a fourth line', Scripted(body=b'\n'.join((b'ab' * 32, b'cd' * 32, b'127.0.0.1', b'')))),
                             ('a value in upper case', Scripted(body=b'ab' * 32 + b'\n' + b'CD' * 32 + b'\n127.0.0.1')),
                             ('an address spelt another way',
                              Scripted(body=b'ab' * 32 + b'\n' + b'cd' * 32 + b'\n127.000.0.1')),
                             ('IPv4 written as IPv6',
                              Scripted(body=b'ab' * 32 + b'\n' + b'cd' * 32 + b'\n::ffff:127.0.0.1')),
                             ('a name for an address',
                              Scripted(body=b'ab' * 32 + b'\n' + b'cd' * 32 + b'\ncontroller.example.com'))):
            with self.subTest(name):
                node = self.node(script)
                self.refused('format', self.code(node), 'The server did not answer as a managed server does.',
                             node=node)

    def test_an_answer_the_code_does_not_hold_the_server_to_is_refused_and_no_number_is_shown(self):
        because = ('The answer of the server does not match the pairing code. Reject the waiting link on that '
                   'server and pair again with a new code.')
        # A server that picks its value when it has seen the request, or allows another controller address
        # than the code was made for. Its answer is signed and in order; the code is what refuses it.
        for script in (Scripted(value='aa' * 32), Scripted(allowed='203.0.113.9'), Scripted(allowed='2a01:4f8::9')):
            node = self.node(script)
            self.refused('signature', self.code(node), because, node=node, link=True)
        # A code whose commitment was made for another address, port, certificate or controller address.
        node = self.node(Scripted())
        value = crypto.pair_value(node.private, PAIRING_KEY)
        made_for = dict(host='127.0.0.1:%d' % node.port, tls_fingerprint=node.pin, controller_ip=HERE)
        for field, other in (('host', '127.0.0.2:%d' % node.port), ('host', '127.0.0.1:%d' % (node.port ^ 1)),
                             ('host', 'node-1.example.com:%d' % node.port), ('tls_fingerprint', pin('impostor')),
                             ('controller_ip', '127.0.0.2'), ('controller_ip', '::1')):
            commitment = crypto.pair_commitment(value, **dict(made_for, **{field: other}))
            self.refused('signature', self.code(node, commitment=commitment), because, node=node, link=True)
        # The value itself is held to: a code that commits to another one is refused as well.
        other_value = crypto.pair_commitment(crypto.pair_value(SEED, PAIRING_KEY), **made_for)
        self.refused('signature', self.code(node, commitment=other_value), because, node=node, link=True)
        pairing.start(self.code(node), 'Frankfurt 1', 'admin')
        self.assertEqual(1, len(self.stored))

    def test_a_redirect_a_second_reply_or_an_oversized_reply_is_refused_and_nothing_is_followed(self):
        elsewhere = self.node(Scripted())
        location = [('Location', 'https://127.0.0.1:%d/multiserver/pair' % elsewhere.port)]
        for script, because in ((Scripted(status=302, extra=location), 'The node answered with a redirect.'),
                                (Scripted(status=307, extra=location), 'The node answered with a redirect.'),
                                (Scripted(extra=[('Content-Length', '64')]), 'The node repeated a reply header.'),
                                (Scripted(extra=[('Transfer-Encoding', 'chunked')]),
                                 'The node did not send its reply whole and unencoded.'),
                                (Scripted(extra=[('Set-Cookie', 'sessionid=1')], body=b'ab' * 32 + b'x' * 65),
                                 'The server did not answer as a managed server does.')):
            node = self.node(script)
            self.refused('format', self.code(node), because, node=node)
        time.sleep(0.2)
        self.assertTrue(elsewhere.connections.empty())

    def test_a_server_that_is_not_there_or_does_not_answer_is_an_error(self):
        vacant = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        vacant.bind(('127.0.0.1', 0))
        port = vacant.getsockname()[1]
        vacant.close()
        self.refused('unreachable', code(host='127.0.0.1', port=port), 'Could not connect to the node.',
                     outcome='error')
        node = self.node(Scripted(hold=True))
        with mock.patch.object(transport, 'DEADLINE', 0.5):
            started = time.monotonic()
            self.refused('timeout', self.code(node), 'The node did not answer in time.', outcome='error', node=node)
            self.assertLess(time.monotonic() - started, 3)

    def test_a_link_that_cannot_be_kept_is_reported_without_what_it_holds(self):
        kept = []

        def failing(private_key, tls_pin):
            kept.append(private_key)
            return RuntimeError('cannot seal %s for %s' % (private_key.hex(), tls_pin))
        self.unstored = failing
        node = self.node(Scripted())
        error = self.refused('internal', self.code(node), 'The link could not be kept on this server. Reject it on '
                             'the other server and pair again.', outcome='error', node=node, recorded=True, link=True)
        self.assertRegex(error.link_id, '^[0-9a-f]{32}$')
        self.assertIsNone(error.__cause__ or error.__context__)
        self.assertNotIn(kept[0].hex(), texts_of(error))
        self.assertNotIn('cannot seal', texts_of(error))

    def test_a_fault_of_any_kind_is_reported_without_what_caused_it(self):
        node = self.node(Scripted())
        with mock.patch.object(crypto, 'sign', side_effect=RuntimeError('cannot sign with %s' % SEED.hex())):
            error = self.refused('internal', self.code(node), 'Pairing failed on this server.', outcome='error')
        self.assertIsNone(error.__cause__ or error.__context__)
        self.assertTrue(node.connections.empty())

    def test_the_search_for_secrets_would_find_one(self):
        node = self.node(Scripted())
        text = self.code(node)
        for secret in secrets_of(node, code=text):
            self.assertIn(secret, texts_of(pairing.PairingError('format', 'Refused: %s.' % secret)))
            try:
                try:
                    raise ValueError(secret)
                except ValueError:
                    raise pairing.PairingError('format', 'Refused.') from None
            except pairing.PairingError as error:
                self.assertIn(secret, texts_of(error))


class RequestShapeTests(unittest.TestCase):
    """What a managed server takes for a pairing request before it looks anything up."""
    FIELDS = (LINK, PAIRING_KEY, 'c1' * 32, str(NOW), NONCE)
    BODY = '\n'.join(FIELDS).encode()

    def request(self, method='POST', path=pairing.PATH, body=None, **meta):
        body = self.BODY if body is None else body
        fields = dict(CONTENT_LENGTH=str(len(body)), CONTENT_TYPE='text/plain', HTTP_HOST='93.184.216.34:8090',
                      HTTP_X_CPMS_SIGNATURE='ab' * 64, QUERY_STRING='', REMOTE_ADDR='203.0.113.9',
                      HTTP_COOKIE='sessionid=abc', HTTP_X_FORWARDED_FOR='198.51.100.7')
        fields.update(meta)
        return types.SimpleNamespace(method=method, path=path, body=body,
                                     META=dict((name, value) for name, value in fields.items() if value is not None))

    def refused(self, reason, **changes):
        with self.assertRaises(pairing.PairingError, msg=changes) as caught:
            pairing._parse(self.request(**changes))
        self.assertEqual(reason, caught.exception.reason, changes)

    def test_a_well_formed_request_is_read_exactly(self):
        self.assertEqual(((LINK, PAIRING_KEY, 'c1' * 32, NOW, NONCE), b'\xab' * 64, '93.184.216.34:8090'),
                         pairing._parse(self.request()))
        self.assertEqual('HTTP_X_CPMS_SIGNATURE', pairing._SIGNATURE_HEADER)
        for host in ('node-1.example.com:8090', '[2a01:4f8::1]:8090', '127.0.0.1:1'):
            self.assertEqual(host, pairing._parse(self.request(HTTP_HOST=host))[2])
        zero = '\n'.join((LINK, PAIRING_KEY, 'c1' * 32, '0', NONCE)).encode()
        self.assertEqual(0, pairing._parse(self.request(body=zero))[0][3])
        self.assertLess(len('\n'.join((LINK, PAIRING_KEY, 'c1' * 32, '9' * 11, NONCE))), pairing.MAX_BODY)

    def test_anything_else_is_refused_as_malformed(self):
        def lines(*fields):
            return '\n'.join(fields).encode()
        link, pairing_key, controller_key, timestamp, nonce = self.FIELDS
        for changes in (
                dict(method='GET'), dict(method='PUT'), dict(method='HEAD'), dict(method='post'),
                dict(path='/multiserver/pair/'), dict(path='/multiserver/pairing'), dict(path='/'),
                dict(QUERY_STRING='x=1'), dict(QUERY_STRING='?'),
                dict(CONTENT_TYPE='application/json'), dict(CONTENT_TYPE='text/plain; charset=utf-8'),
                dict(CONTENT_TYPE='TEXT/PLAIN'), dict(CONTENT_TYPE=''), dict(CONTENT_TYPE=None),
                dict(CONTENT_LENGTH=None), dict(CONTENT_LENGTH=''), dict(CONTENT_LENGTH='+%d' % len(self.BODY)),
                dict(CONTENT_LENGTH='0%d' % len(self.BODY)), dict(CONTENT_LENGTH='-1'), dict(CONTENT_LENGTH='0x10'),
                dict(CONTENT_LENGTH=str(len(self.BODY) - 1)), dict(CONTENT_LENGTH=str(len(self.BODY) + 1)),
                dict(CONTENT_LENGTH='%d, %d' % (len(self.BODY), len(self.BODY))), dict(CONTENT_LENGTH=len(self.BODY)),
                dict(HTTP_X_CPMS_SIGNATURE=None), dict(HTTP_X_CPMS_SIGNATURE=''),
                dict(HTTP_X_CPMS_SIGNATURE='ab' * 63), dict(HTTP_X_CPMS_SIGNATURE='AB' * 64),
                dict(HTTP_X_CPMS_SIGNATURE='ab' * 64 + ',' + 'ab' * 64), dict(HTTP_X_CPMS_SIGNATURE='zz' * 64),
                dict(HTTP_X_CPMS_SIGNATURE=base64.b64encode(bytes(64)).decode()),
                dict(HTTP_HOST=None), dict(HTTP_HOST=''), dict(HTTP_HOST='93.184.216.34'), dict(HTTP_HOST='a b:8090'),
                dict(HTTP_HOST='93.184.216.34:0'), dict(HTTP_HOST='93.184.216.34:8090, 93.184.216.34:8090'),
                dict(body=b''), dict(body=self.BODY + b'\n'), dict(body=b'\n' + self.BODY),
                dict(body=self.BODY.replace(b'\n', b'\r\n')), dict(body=self.BODY.upper()),
                dict(body=lines(link, pairing_key, controller_key, timestamp)),
                dict(body=lines(link, pairing_key, controller_key, timestamp, nonce, nonce)),
                dict(body=lines(pairing_key, link, controller_key, timestamp, nonce)),
                dict(body=lines(link[:-1], pairing_key, controller_key, timestamp, nonce)),
                dict(body=lines(link, pairing_key + 'ab', controller_key, timestamp, nonce)),
                dict(body=lines(link, pairing_key, controller_key[:-2], timestamp, nonce)),
                dict(body=lines(link, pairing_key, controller_key, '0' + timestamp, nonce)),
                dict(body=lines(link, pairing_key, controller_key, '-1', nonce)),
                dict(body=lines(link, pairing_key, controller_key, '1' * 12, nonce)),
                dict(body=lines(link, pairing_key, controller_key, '1795000000.0', nonce)),
                dict(body=lines(link, pairing_key, controller_key, '', nonce)),
                dict(body=lines(link, pairing_key, controller_key, timestamp, nonce + ' ')),
                dict(body=lines(link, pairing_key, controller_key, timestamp, nonce).replace(b'a', b'\x00', 1)),
                dict(body=b'CPMS1-PAIR-REQ\n' + self.BODY), dict(body=b'{"link": "%s"}' % link.encode())):
            self.refused('format', **changes)

    def test_a_controller_key_that_anybody_can_sign_for_is_refused_as_malformed(self):
        link, pairing_key, controller_key, timestamp, nonce = self.FIELDS
        self.assertIs(True, crypto.usable_public_key(bytes.fromhex(controller_key)))
        for written in ('01' + '00' * 31, '01' + '00' * 30 + '80', '00' * 32, '00' * 31 + '80',
                        'ec' + 'ff' * 30 + '7f', 'ee' + 'ff' * 30 + '7f', 'ed' + 'ff' * 30 + '7f',
                        '26e8958fc2b227b045c3f489f2ef98f0d5dfac05d3c63339b13802886d53fc05',
                        'c7176a703d4dd84fba3c0b760d10670f2a2053fa2c39ccc64ec7fd7792ac03fa',
                        '02' + '00' * 31):
            self.refused('format', body='\n'.join((link, pairing_key, written, timestamp, nonce)).encode())

    def test_a_request_that_is_or_says_it_is_too_large_is_refused_before_its_body_is_read(self):
        class Unread(object):
            method, path = 'POST', pairing.PATH

            def __init__(self, length):
                self.META = dict(CONTENT_LENGTH=length, CONTENT_TYPE='text/plain')

            @property
            def body(self):
                raise AssertionError('the body was read')
        self.assertEqual(256, pairing.MAX_BODY)
        for length in ('257', '4096', '8388609', '9' * 18):
            with self.assertRaises(pairing.PairingError) as caught:
                pairing._parse(Unread(length))
            self.assertEqual('size', caught.exception.reason)
        self.refused('size', body=self.BODY + b'x' * 60)
        self.refused('format', body=self.BODY + b'x' * (256 - len(self.BODY)))


class NodeHelperTests(unittest.TestCase):
    def test_the_fingerprint_of_the_panel_certificate_is_what_a_controller_pins(self):
        from plogical import softUpgrade
        directory = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, str(directory))
        with mock.patch.object(softUpgrade, 'PANEL_CONF', directory):
            with self.assertRaises(OSError):
                pairing._certificate_fingerprint()
            for content, expected in (
                    (Path(CERTIFICATES['node'][0]).read_bytes(), pin('node')),
                    # The first certificate is the one served; what follows is its chain.
                    (Path(CERTIFICATES['impostor'][0]).read_bytes() + Path(CERTIFICATES['node'][0]).read_bytes(),
                     pin('impostor'))):
                directory.joinpath('cert.pem').write_bytes(content)
                self.assertEqual(expected, pairing._certificate_fingerprint())
            node = Server()
            self.addCleanup(node.close)
            directory.joinpath('cert.pem').write_bytes(Path(CERTIFICATES['node'][0]).read_bytes())
            connection = transport._connect(Loopback('127.0.0.1', node.port, pairing._certificate_fingerprint()),
                                            time.monotonic() + 5)
            connection.close()
            for content in (b'', b'not a certificate', b'-----BEGIN CERTIFICATE-----\nAAAA\n',
                            Path(CERTIFICATES['node'][0]).read_bytes() + b'#' * pairing.MAX_CERTIFICATE):
                directory.joinpath('cert.pem').write_bytes(content)
                with self.assertRaises(ValueError):
                    pairing._certificate_fingerprint()

    def test_a_code_is_usable_until_it_ends_is_used_or_is_burned(self):
        def state(now=NOW, **changes):
            fields = dict(expires_at=NOW + 600, consumed=False, failures=0)
            fields.update(changes)
            return pairing._unusable(types.SimpleNamespace(**fields), now)
        self.assertEqual((600, 5), (pairing.CODE_LIFETIME, pairing.MAX_FAILURES))
        self.assertIsNone(state())
        self.assertIsNone(state(now=NOW + 599, failures=4))
        self.assertEqual('link', pairing._unusable(None, NOW))
        self.assertEqual('expired', state(now=NOW + 600))
        self.assertEqual('expired', state(now=NOW + 600, consumed=True, failures=5))
        self.assertEqual('consumed', state(consumed=True))
        self.assertEqual('consumed', state(consumed=True, failures=5))
        self.assertEqual('burned', state(failures=5))
        self.assertEqual('burned', state(failures=6))


class CompatibilityTests(unittest.TestCase):
    """The panel also runs on Python 3.6 with cryptography 3.2.1 (AlmaLinux 8)."""
    DIRECTORY = Path(__file__).resolve().parent
    SOURCES = ('pairing.py', 'test_pairing.py', 'test_pairing_database.py')

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check for an older Python here')
    def test_sources_parse_as_python_3_6(self):
        for name in self.SOURCES:
            ast.parse(self.DIRECTORY.joinpath(name).read_text(), feature_version=(3, 6))

    def test_pairing_loads_with_the_standard_library_and_this_app_alone(self):
        tree = ast.parse(self.DIRECTORY.joinpath('pairing.py').read_text())
        imported = set()
        for node in tree.body:
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.add(node.module)
        self.assertEqual({'base64', 'collections', 'hashlib', 'hmac', 'ipaddress', 'os', 're', 'ssl', 'time', 'types',
                          'multiServer'}, imported)

    def test_no_part_of_the_app_loads_a_row_and_saves_it_back(self):
        # A link row is changed by conditional updates that name their columns: a whole row saved back would
        # undo what the gateway recorded on it in the meantime.
        for path in sorted(self.DIRECTORY.glob('*.py')):
            if path.name.startswith('test_') or path.name == 'testing.py':
                continue
            called = set(node.func.attr for node in ast.walk(ast.parse(path.read_text()))
                         if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute))
            self.assertFalse(called & {'save', 'save_base', 'bulk_update', 'refresh_from_db', 'update_or_create',
                                       'get_or_create'}, path.name)

    def test_pairing_writes_to_no_log_and_asks_for_no_allowance(self):
        source = self.DIRECTORY.joinpath('pairing.py').read_text()
        names = set(node.id for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Name))
        names |= set(node.attr for node in ast.walk(ast.parse(source)) if isinstance(node, ast.Attribute))
        self.assertFalse(names & {'print', 'logging', 'writeToFile', 'getLogger', 'warn', 'stderr', 'stdout',
                                  'private_bytes_raw', 'public_bytes_raw', 'kwargs', 'capture_output'}, names)
        self.assertNotIn('allow_loopback_for_tests', source)


if __name__ == '__main__':
    unittest.main()
