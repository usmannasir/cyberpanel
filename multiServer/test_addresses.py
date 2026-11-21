"""The one rule for the address of a controller: how it is written down and how a connection is matched.

Needs only Python. That the gateway and pairing both go by this rule, and by
no other, is checked at the end against their sources.
"""
import ast
from pathlib import Path
import sys
import unittest

from multiServer import addresses

DIRECTORY = Path(__file__).resolve().parent
NOT_AN_ADDRESS = (None, '', b'203.0.113.9', 3405803785, ['203.0.113.9'], ' 203.0.113.9', '203.0.113.9 ',
                  '203.0.113.9\n', '203.0.113.09', '0203.0.113.9', '010.0.0.1', '203.0.113', '203.0.113.9.1',
                  '203.0.113.9/32', '203.0.113.9,203.0.113.9', '203.0.113.9:8090', '[2001:db8::9]', 'fe80::1%eth0',
                  '2001:db8::9%1', 'localhost', 'controller.example.com', 'unknown', '3405803785', '0xcb.0.113.9',
                  '::ffff:203.0.113.09', 'a' * 46, '2001:db8::9 ', '2001:db8:::9')


class SpellingTests(unittest.TestCase):
    def test_the_address_of_a_connection_has_one_spelling(self):
        for given, expected in (('203.0.113.9', '203.0.113.9'), ('127.0.0.1', '127.0.0.1'), ('0.0.0.0', '0.0.0.0'),
                                ('2001:db8::9', '2001:db8::9'), ('2001:DB8:0:0:0:0:0:9', '2001:db8::9'),
                                ('2001:0db8:0000::0009', '2001:db8::9'), ('::1', '::1'), ('0:0:0:0:0:0:0:1', '::1'),
                                ('2A01:04F8:0:0:0:0:0:1', '2a01:4f8::1')):
            self.assertEqual(expected, addresses.peer(given), given)
            self.assertEqual(expected, addresses.entry(given), given)
            # The one spelling is its own one spelling.
            self.assertEqual(expected, addresses.peer(expected))
            self.assertEqual(expected, addresses.entry(expected))

    def test_ipv4_reported_as_ipv6_is_that_ipv4_address_and_nobody_may_write_it_so(self):
        for given, expected in (('::ffff:203.0.113.9', '203.0.113.9'), ('::FFFF:cb00:7109', '203.0.113.9'),
                                ('0:0:0:0:0:ffff:203.0.113.9', '203.0.113.9'), ('::ffff:127.0.0.1', '127.0.0.1')):
            self.assertEqual(expected, addresses.peer(given), given)
            self.assertIsNone(addresses.entry(given), given)
        # Only that one form: other ways of carrying IPv4 inside IPv6 are IPv6 addresses of their own.
        for given in ('::203.0.113.9', '64:ff9b::203.0.113.9', '2002:cb00:7109::1'):
            self.assertEqual(addresses.peer(given), addresses.entry(given))
            self.assertIn(':', addresses.peer(given))

    def test_what_is_not_one_plain_address_is_no_address(self):
        for given in NOT_AN_ADDRESS:
            self.assertIsNone(addresses.peer(given), repr(given))
            self.assertIsNone(addresses.entry(given), repr(given))


class ListTests(unittest.TestCase):
    def test_a_list_names_exactly_the_addresses_written_in_it(self):
        self.assertEqual(('203.0.113.9',), addresses.listed('203.0.113.9'))
        self.assertEqual(('203.0.113.9', '2001:db8::9', '198.51.100.7'),
                         addresses.listed('203.0.113.9,2001:db8::9,198.51.100.7'))

    def test_a_list_with_one_entry_that_is_not_in_its_one_spelling_names_nobody(self):
        for text in (None, '', ',', '203.0.113.9,', ',203.0.113.9', '203.0.113.9,,198.51.100.7',
                     '203.0.113.9, 198.51.100.7', ' 203.0.113.9', '203.0.113.9;198.51.100.7',
                     '203.0.113.9 198.51.100.7', '203.0.113.0/24', '0.0.0.0/0', '*', '203.0.113.9,*',
                     '203.0.113.9,any', '2001:DB8::9', '2001:db8:0::9', '::ffff:203.0.113.9',
                     '203.0.113.9,::ffff:198.51.100.7', '203.0.113.009', b'203.0.113.9', ['203.0.113.9'],
                     ('203.0.113.9',), 3405803785):
            self.assertEqual((), addresses.listed(text), repr(text))

    def test_a_connection_is_allowed_when_its_address_is_one_of_the_list(self):
        text = '203.0.113.9,198.51.100.7,2001:db8::9'
        for came_from in ('203.0.113.9', '198.51.100.7', '::ffff:198.51.100.7', '::FFFF:c633:6407', '2001:db8::9',
                          '2001:DB8:0:0:0:0:0:9'):
            self.assertTrue(addresses.allows(text, came_from), came_from)
        for came_from in ('198.51.100.8', '203.0.113.90', '2001:db8::90', '::ffff:198.51.100.8', '::1', '127.0.0.1',
                          '0.0.0.0', '203.0.113.9,198.51.100.7', text) + NOT_AN_ADDRESS:
            self.assertFalse(addresses.allows(text, came_from), repr(came_from))

    def test_a_list_that_names_nobody_allows_nobody(self):
        for text in ('', '203.0.113.9,', '203.0.113.9, 198.51.100.7', '203.0.113.0/24', '0.0.0.0/0', '*',
                     '::ffff:203.0.113.9', '203.0.113.09', None):
            for came_from in ('203.0.113.9', '::ffff:203.0.113.9', '198.51.100.7', '', None):
                self.assertFalse(addresses.allows(text, came_from), (text, came_from))

    def test_a_list_is_written_only_from_addresses_in_their_one_spelling(self):
        self.assertEqual('203.0.113.9', addresses.joined(['203.0.113.9']))
        self.assertEqual('203.0.113.9,2001:db8::9', addresses.joined(('203.0.113.9', '2001:db8::9')))
        self.assertEqual('203.0.113.9', addresses.joined(address for address in ['203.0.113.9']))
        for given in ((), [], [''], ['203.0.113.9', ''], ['203.0.113.9,198.51.100.7'], ['2001:DB8::9'],
                      ['::ffff:203.0.113.9'], ['203.0.113.09'], [None], [b'203.0.113.9'], None, 7, '203.0.113.9',
                      ['203.0.113.9 ']):
            with self.assertRaises(ValueError, msg=repr(given)):
                addresses.joined(given)
        # What is written is read back as the same addresses.
        for given in (['203.0.113.9'], ['2001:db8::9', '198.51.100.7', '::1']):
            self.assertEqual(tuple(given), addresses.listed(addresses.joined(given)))


class OneRuleTests(unittest.TestCase):
    """The gateway and pairing hold no rule of their own for an address of a controller."""

    def names(self, name):
        tree = ast.parse(DIRECTORY.joinpath(name).read_text())
        found = set(node.id for node in ast.walk(tree) if isinstance(node, ast.Name))
        return found | set(node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute))

    def test_the_gateway_and_pairing_ask_this_module_and_read_no_address_themselves(self):
        for name in ('nodeGateway.py', 'pairing.py'):
            names = self.names(name)
            self.assertIn('addresses', names, name)
            self.assertFalse(names & {'ipv4_mapped', 'ip_network', 'ip_interface', 'inet_aton', 'inet_pton',
                                      '_address', '_allowed'}, name)
        self.assertFalse(self.names('nodeGateway.py') & {'ipaddress', 'ip_address'})
        # Pairing packs the managed server's own address into a code, by its family, and does nothing else with one.
        source = DIRECTORY.joinpath('pairing.py').read_text()
        self.assertEqual(3, source.count('ipaddress.'))
        self.assertEqual(2, source.count('ipaddress.IPv4Address(') + source.count('ipaddress.IPv6Address('))

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_sources_parse_as_python_3_6(self):
        for name in ('addresses.py', 'test_addresses.py'):
            ast.parse(DIRECTORY.joinpath(name).read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
