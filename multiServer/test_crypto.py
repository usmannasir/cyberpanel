"""Link signing: every message is typed, fixed in shape and strict about each field."""
import ast
import hashlib
from pathlib import Path
import unittest

from multiServer import crypto

LINK = 'a1' * 16
NONCE = 'c3' * 16


def keys():
    private = crypto.generate_private_key()
    return private, crypto.public_key(private)


def request(**changes):
    fields = dict(link_id=LINK, node_id='b2' * 32, method='POST', host='203.0.113.20:8090',
                  path='/websites/submitWebsiteCreation', query='', content_type='application/json',
                  body=b'{"domainName": "example.com"}', timestamp=1795000000, nonce=NONCE,
                  actor='admin', mode='json')
    fields.update(changes)
    return crypto.request_message(**fields)


class KeyTests(unittest.TestCase):
    def test_keys_are_raw_ed25519_and_sign_what_they_verify(self):
        private, public = keys()
        self.assertEqual((32, 32), (len(private), len(public)))
        signature = crypto.sign(private, b'message')
        self.assertEqual(64, len(signature))
        self.assertTrue(crypto.verify(public, signature, b'message'))

    def test_known_answer_from_rfc_8032(self):
        private = bytes.fromhex('9d61b19deffd5a60ba844af492ec2cc44449c5697b326919703bac031cae7f60')
        self.assertEqual('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a',
                         crypto.public_key(private).hex())
        self.assertEqual(
            'e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e06522490155'
            '5fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b',
            crypto.sign(private, b'').hex())

    def test_verification_never_raises_and_rejects_anything_altered(self):
        private, public = keys()
        other_public = keys()[1]
        signature = crypto.sign(private, b'message')
        for candidate in ((public, signature, b'messagE'), (other_public, signature, b'message'),
                          (public, signature[:-1] + bytes([signature[-1] ^ 1]), b'message'),
                          (public, signature[:63], b'message'), (public[:31], signature, b'message'),
                          (public, b'', b'message'), (None, signature, b'message'),
                          (public, None, b'message'), (public, signature, None),
                          ('text', 'text', 'text')):
            self.assertIs(False, crypto.verify(*candidate))

    def test_node_id_is_the_fingerprint_of_the_identity_key(self):
        public = keys()[1]
        self.assertEqual(hashlib.sha256(public).hexdigest(), crypto.node_id(public))
        for bad in (public[:31], public + b'x', 'text', None):
            with self.assertRaises(ValueError):
                crypto.node_id(bad)

    def test_self_test_reports_working_signatures(self):
        self.assertIs(True, crypto.self_test())


class RequestMessageTests(unittest.TestCase):
    def test_message_has_a_type_line_and_one_line_per_field(self):
        lines = request().split(b'\n')
        body = b'{"domainName": "example.com"}'
        self.assertEqual([
            b'CPMS1-REQ', LINK.encode(), b'b2' * 32, b'POST', b'203.0.113.20:8090',
            b'/websites/submitWebsiteCreation', b'', b'application/json', str(len(body)).encode(),
            hashlib.sha256(body).hexdigest().encode(), b'1795000000', NONCE.encode(), b'admin', b'json'], lines)

    def test_every_field_changes_the_signed_bytes(self):
        base = request()
        for change in (dict(link_id='a2' * 16), dict(node_id='b3' * 32), dict(method='GET', body=b'',
                       content_type='-'), dict(host='203.0.113.21:8090'), dict(path='/websites/other'),
                       dict(query='page=2'), dict(content_type='text/plain'), dict(body=b'{}'),
                       dict(timestamp=1795000001), dict(nonce='c4' * 16), dict(actor='other'),
                       dict(mode='page', method='GET', body=b'', content_type='-')):
            self.assertNotEqual(base, request(**change), change)

    def test_accepted_field_shapes(self):
        for change in (dict(path='/'), dict(path='/websites/example.com/workspace'),
                       dict(path='/static/baseTemplate/custom-js/system-status.js', method='GET',
                            body=b'', content_type='-', mode='static', query='v=3.0.8-20261101'),
                       dict(host='node-1.example.com:8090'), dict(host='[2001:db8::1]:8090'),
                       dict(actor='first.last@example.com'), dict(query='a=1&b=x%20y'),
                       dict(content_type='application/x-www-form-urlencoded')):
            self.assertTrue(request(**change).startswith(b'CPMS1-REQ\n'), change)

    def test_fields_that_could_be_read_two_ways_are_refused(self):
        refused = (
            dict(path='/websites//x'), dict(path='/websites/./x'), dict(path='/websites/../x'),
            dict(path='/websites/..'), dict(path='websites/x'), dict(path='/websites/%2e%2e/x'),
            dict(path='/websites/x y'), dict(path='/websites/x\nGET'), dict(path='/websites/x;a'),
            dict(path='/websites/x?a=1'), dict(path=''), dict(path='/' + 'a' * 2049),
            dict(query='a=1;b=2'), dict(query='a=1&a=2'), dict(query='a=1\n'), dict(query='a b'),
            dict(query='?a=1'), dict(query='a=' + 'b' * 4097),
            dict(method='DELETE'), dict(method='post'), dict(method='GET', body=b'x'),
            dict(host='203.0.113.20'), dict(host='203.0.113.20:8090/x'), dict(host='a b:8090'),
            dict(host='203.0.113.20:99999'), dict(host='203.0.113.20:0'), dict(host='node\n:8090'),
            dict(link_id='A1' * 16), dict(link_id='a1' * 15), dict(node_id='b2' * 31),
            dict(nonce='c3' * 15), dict(nonce='C3' * 16), dict(nonce='c3' * 16 + '\n'),
            dict(content_type='Application/JSON'), dict(content_type='application/json; charset=utf-8'),
            dict(content_type=''), dict(content_type='text/plain\n'),
            dict(timestamp='1795000000'), dict(timestamp=-1), dict(timestamp=1795000000.5),
            dict(timestamp=True), dict(timestamp=10 ** 11),
            dict(actor=''), dict(actor='a b'), dict(actor='x' * 51), dict(actor='admin\n'),
            dict(mode='shell'), dict(mode=''), dict(body='text'), dict(body=None),
        )
        for change in refused:
            with self.assertRaises(ValueError, msg=change):
                request(**change)


class OtherMessageTests(unittest.TestCase):
    def test_response_is_bound_to_its_request(self):
        signed_request = request()
        fields = dict(link_id=LINK, node_id='b2' * 32, nonce=NONCE, request=signed_request,
                      status=200, content_type='application/json', body=b'{"status": 1}')
        message = crypto.response_message(**fields)
        self.assertEqual([
            b'CPMS1-RSP', LINK.encode(), b'b2' * 32, NONCE.encode(),
            hashlib.sha256(signed_request).hexdigest().encode(), b'200', b'application/json',
            hashlib.sha256(b'{"status": 1}').hexdigest().encode()], message.split(b'\n'))
        for change in (dict(request=request(nonce='c4' * 16)), dict(status=500), dict(body=b'{}'),
                       dict(content_type='text/html'), dict(nonce='c4' * 16)):
            self.assertNotEqual(message, crypto.response_message(**dict(fields, **change)), change)
        for change in (dict(status=99), dict(status=600), dict(status='200'), dict(status=True),
                       dict(content_type='text/html\n'), dict(body='text'), dict(request='text'),
                       dict(nonce='c3' * 15)):
            with self.assertRaises(ValueError, msg=change):
                crypto.response_message(**dict(fields, **change))

    def test_hello_binds_the_served_certificate_to_the_node(self):
        message = crypto.hello_message(node_id='b2' * 32, nonce=NONCE, tls_fingerprint='d4' * 32,
                                       timestamp=1795000000)
        self.assertEqual([b'CPMS1-HELLO', b'b2' * 32, NONCE.encode(), b'd4' * 32, b'1795000000'],
                         message.split(b'\n'))
        for change in (dict(tls_fingerprint='d4' * 31), dict(tls_fingerprint='D4' * 32),
                       dict(nonce='zz' * 16), dict(node_id='b2' * 33), dict(timestamp='now')):
            fields = dict(node_id='b2' * 32, nonce=NONCE, tls_fingerprint='d4' * 32, timestamp=1795000000)
            fields.update(change)
            with self.assertRaises(ValueError, msg=change):
                crypto.hello_message(**fields)

    def test_no_message_of_one_type_is_a_valid_message_of_another(self):
        private, public = keys()
        signed_request = request()
        messages = {
            'request': signed_request,
            'response': crypto.response_message(link_id=LINK, node_id='b2' * 32, nonce=NONCE,
                                                request=signed_request, status=200,
                                                content_type='application/json', body=b''),
            'hello': crypto.hello_message(node_id='b2' * 32, nonce=NONCE, tls_fingerprint='d4' * 32,
                                          timestamp=1795000000),
        }
        prefixes = {name: message.split(b'\n', 1)[0] for name, message in messages.items()}
        self.assertEqual(len(prefixes), len(set(prefixes.values())))
        for name, message in messages.items():
            signature = crypto.sign(private, message)
            for other, different in messages.items():
                self.assertEqual(name == other, crypto.verify(public, signature, different))


class CompatibilityTests(unittest.TestCase):
    """The panel also runs on Python 3.6 with cryptography 3.2.1 (AlmaLinux 8)."""
    SOURCE = Path(__file__).with_name('crypto.py')

    def test_source_parses_as_python_3_6(self):
        ast.parse(self.SOURCE.read_text(), feature_version=(3, 6))

    def test_only_calls_available_in_cryptography_3_2_are_used(self):
        names = {node.attr for node in ast.walk(ast.parse(self.SOURCE.read_text()))
                 if isinstance(node, ast.Attribute)}
        self.assertFalse(names & {'private_bytes_raw', 'public_bytes_raw'}, names)


if __name__ == '__main__':
    unittest.main()
