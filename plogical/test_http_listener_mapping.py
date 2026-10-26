import ast
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from plogical.domainAliasUtilities import ensure_http_vhost_mapping
from plogical.httpListenerMapping import update_http_listener_mappings

CONFIG = '''# listener Default commented out
listener Default {
 address *:80
 secure 0
 map old.test old.test,www.old.test
}
listener Default IPv6 {
 address [::]:80
 secure 0
}
listener Renamed HTTP {
 address 127.0.0.2:8080
 secure 0
}
listener SSL IPv6 {
 address [::]:443
 secure 1
}
virtualhost sibling.test {
 configFile conf/vhosts/sibling.test/vhost.conf
}
'''

class HTTPListenerTests(unittest.TestCase):
    def test_all_non_tls_names_and_ipv6(self):
        result = ensure_http_vhost_mapping(CONFIG, 'new.test')
        self.assertEqual(result.count('new.test new.test'), 3)
        self.assertNotIn('new.test', result.split('listener SSL IPv6')[1])
        self.assertIn('map old.test old.test,www.old.test', result)
        self.assertIn('virtualhost sibling.test', result)
        self.assertTrue(result.startswith('# listener Default commented out'))

    def test_existing_map_keeps_aliases_and_is_idempotent(self):
        result = ensure_http_vhost_mapping(CONFIG, 'old.test')
        self.assertIn('map old.test old.test,www.old.test', result)
        self.assertEqual(ensure_http_vhost_mapping(result, 'old.test'), result)

    def test_no_http_listener_fails(self):
        with self.assertRaises(ValueError):
            ensure_http_vhost_mapping('listener SSL {\n secure 1\n}\n', 'new.test')

    def test_atomic_permissions_and_failure_preserves_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'httpd_config.conf'
            path.write_text(CONFIG)
            path.chmod(0o640)
            with patch('plogical.httpListenerMapping.os.replace', side_effect=OSError('fixture')):
                with self.assertRaises(OSError):
                    update_http_listener_mappings(str(path), 'new.test')
            self.assertEqual(path.read_text(), CONFIG)
            self.assertEqual(list(Path(tmp).iterdir()), [path])
            update_http_listener_mappings(str(path), 'new.test')
            self.assertEqual(path.stat().st_mode & 0o777, 0o640)
            self.assertEqual(path.read_text().count('new.test new.test'), 3)

    def test_actual_vhost_entrypoint(self):
        tree = ast.parse(Path(__file__).with_name('vhost.py').read_text())
        klass = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'vhost')
        method = next(node for node in klass.body if isinstance(node, ast.FunctionDef) and node.name == 'createNONSSLMapEntry')
        method.decorator_list = []
        module = ast.Module(body=[method], type_ignores=[])
        namespace = {'logging': type('Log', (), {'CyberCPLogFileWriter': type('Writer', (), {'writeToFile': staticmethod(lambda message: None)})})}
        exec(compile(ast.fix_missing_locations(module), 'vhost.py', 'exec'), namespace)
        with patch('plogical.httpListenerMapping.update_http_listener_mappings') as helper:
            self.assertEqual(namespace['createNONSSLMapEntry']('new.test'), 1)
            helper.assert_called_once_with('/usr/local/lsws/conf/httpd_config.conf', 'new.test')
            helper.side_effect = ValueError('no HTTP listener')
            self.assertEqual(namespace['createNONSSLMapEntry']('new.test'), 0)

if __name__ == '__main__':
    unittest.main()
