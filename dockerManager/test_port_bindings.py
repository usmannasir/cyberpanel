import json
import unittest
from dockerManager.portBindings import build_port_bindings, publish_all_for_saved_bindings

class HostBindingTests(unittest.TestCase):
    def test_explicit_addresses_and_persistence(self):
        for address in ('127.0.0.1', '::1', '::', '0.0.0.0', '192.168.1.4', '2001:db8::1'):
            bindings, publish = build_port_bindings({'5678/tcp': {}}, {'hostIP': address, '5678/tcp': 5678})
            self.assertFalse(publish)
            self.assertEqual(json.loads(json.dumps(bindings)), {'5678/tcp': {'HostIp': address, 'HostPort': '5678'}})
            self.assertFalse(publish_all_for_saved_bindings(json.loads(json.dumps(bindings))))

    def test_bad_addresses(self):
        for address in ('', 'localhost', '127.0.0.1:5678', '[::1]', '224.0.0.1', 'ff02::1', 'fe80::1%eth0', '255.255.255.255', None, 123):
            with self.subTest(address=address), self.assertRaises(ValueError):
                build_port_bindings({'80/tcp': {}}, {'hostIP': address, '80/tcp': 8080})

    def test_bad_ports(self):
        for port in (0, 1023, 65536, True, False, 5678.5, '5678.0', '8080/tcp', {}, [], '-1'):
            with self.subTest(port=port), self.assertRaises(ValueError):
                build_port_bindings({'80/tcp': {}}, {'hostIP': '127.0.0.1', '80/tcp': port})

    def test_all_exposed_ports_must_be_mapped(self):
        with self.assertRaises(ValueError):
            build_port_bindings({'80/tcp': {}, '53/udp': {}}, {'hostIP': '127.0.0.1', '80/tcp': 8080})
        bindings, publish = build_port_bindings({'80/tcp': {}, '53/udp': {}}, {'hostIP': '127.0.0.1', '80/tcp': 8080, '53/udp': 1053})
        self.assertEqual(set(bindings), {'80/tcp', '53/udp'})
        self.assertFalse(publish)

    def test_legacy_api_and_recreation_are_preserved(self):
        bindings, publish = build_port_bindings({'80/tcp': {}, '53/udp': {}}, {'80/tcp': 8080})
        self.assertEqual(bindings, {'80/tcp': 8080})
        self.assertTrue(publish)
        self.assertTrue(publish_all_for_saved_bindings(bindings))

    def test_empty_image_and_extra_keys_do_not_publish(self):
        bindings, publish = build_port_bindings({}, {'hostIP': '127.0.0.1', '80/tcp': 8080})
        self.assertEqual(bindings, {})
        self.assertFalse(publish)

    def test_docker_sdk_accepts_persisted_bindings(self):
        try:
            from docker.utils import convert_port_bindings
        except ImportError:
            self.skipTest('Docker SDK not installed in this environment')
        bindings, _ = build_port_bindings({'5678/tcp': {}}, {'hostIP': '::1', '5678/tcp': 5678})
        self.assertEqual(convert_port_bindings(json.loads(json.dumps(bindings))),
                         {'5678/tcp': [{'HostIp': '::1', 'HostPort': '5678'}]})

if __name__ == '__main__':
    unittest.main()
