import unittest

from CyberCP.session_ip import session_ip_key, session_ip_matches


class SessionIPTests(unittest.TestCase):
    def test_mapped_ipv4_login_and_subsequent_request_match(self):
        for address in ('::ffff:192.0.2.1', '::ffff:c000:201'):
            self.assertEqual('192.0.2.1', session_ip_key(address))
            self.assertTrue(session_ip_matches(session_ip_key(address), address))
            self.assertTrue(session_ip_matches(session_ip_key(address), '192.0.2.1'))

    def test_ipv4_binding_remains_exact(self):
        self.assertFalse(session_ip_matches('192.0.2.1', '192.0.2.2'))
        self.assertFalse(session_ip_matches('192.0.2.1', '::ffff:192.0.2.2'))

    def test_native_ipv6_binding_is_normalized_48_bit_prefix(self):
        key = session_ip_key('2001:db8::1')
        self.assertTrue(session_ip_matches(key, '2001:0db8:0000:1234::2'))
        self.assertFalse(session_ip_matches(key, '2001:db8:1::1'))
        self.assertTrue(session_ip_matches(key, '2001:0DB8:0:0:0:0:0:1'))

    def test_legacy_native_ipv6_session_survives(self):
        self.assertTrue(session_ip_matches('2001:db8:', '2001:db8::1'))
        self.assertFalse(session_ip_matches('2001:db8:', '2001:db8:1::1'))

    def test_legacy_mapped_prefix_cannot_authorize_arbitrary_ipv4(self):
        self.assertFalse(session_ip_matches('::ffff', '::ffff:192.0.2.2'))

    def test_invalid_addresses_do_not_match(self):
        for value in (None, '', 'invalid', '192.0.2.1,192.0.2.2'):
            self.assertFalse(session_ip_matches(value, value))
