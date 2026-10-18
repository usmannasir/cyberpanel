import ast
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock

from plogical.domainAliasUtilities import (
    add_https_alias_mapping, ensure_https_vhost_mapping, has_https_listener,
)


class AliasHTTPSMappingTests(TestCase):
    def test_certificate_install_recognizes_custom_tls_listeners(self):
        source = Path(__file__).with_name('sslUtilities.py').read_text()
        cls = next(node for node in ast.parse(source).body
                   if isinstance(node, ast.ClassDef) and node.name == 'sslUtilities')
        config = '''listener HTTPS {
 address *:443
 secure 1
}
listener IPv6TLS {
 address [ANY]:443
 secure 1
}
'''
        for name in ('checkSSLListener', 'checkSSLIPv6Listener'):
            method = next(node for node in cls.body
                          if isinstance(node, ast.FunctionDef) and node.name == name)
            method.decorator_list = []
            namespace = {'has_https_listener': has_https_listener,
                         'open': mock.mock_open(read_data=config), 'logging': mock.MagicMock()}
            exec(compile(ast.Module(body=[method], type_ignores=[]), '<ssl>', 'exec'), namespace)
            self.assertEqual(namespace[name](), 1)

    def test_certificate_install_preserves_aliases_and_adds_only_missing_parent_maps(self):
        config = '''listener HTTP {
 map main.test main.test
 secure 0
}
listener HTTPS {
 map\tmain.test\tmain.test, old.test # preserve
 map main.test.extra main.test.extra
 secure 1
}
listener IPv6TLS {
 address [ANY]:443
 map other.test other.test
 secure 1
}
'''
        updated = ensure_https_vhost_mapping(config, 'main.test')
        self.assertIn('map\tmain.test\tmain.test, old.test # preserve', updated)
        self.assertIn('map main.test.extra main.test.extra', updated)
        self.assertEqual(updated.count('map                     main.test main.test'), 1)
        self.assertEqual(updated, ensure_https_vhost_mapping(updated, 'main.test'))
        self.assertTrue(has_https_listener(updated, ipv6=True))
        self.assertFalse(has_https_listener('listener SSL {\n address [ANY]:80\n secure 0\n}\n'))

    def worker(self):
        source = Path(__file__).with_name('vhost.py').read_text()
        cls = next(node for node in ast.parse(source).body
                   if isinstance(node, ast.ClassDef) and node.name == 'vhost')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'createAliasSSLMap')
        method.decorator_list = []
        restart = mock.Mock()
        namespace = {
            'add_https_alias_mapping': add_https_alias_mapping,
            'installUtilities': SimpleNamespace(installUtilities=SimpleNamespace(reStartLiteSpeed=restart)),
            'logging': mock.MagicMock(),
            'vhost': mock.MagicMock(),
        }
        namespace['vhost'].checkIfSSLAliasExists.return_value = 0
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<worker>', 'exec'), namespace)
        return namespace['createAliasSSLMap'], restart

    def test_renamed_tls_listeners_and_tabs_route_alias_without_losing_other_maps(self):
        config = '''listener Public {
 map main.test main.test
 secure 0
}
listener HTTPS {
 map main.test.extra main.test.extra
 map\tmain.test\tmain.test, old.test # preserve
 secure 1
}
listener IPv6TLS {
 map main.test main.test
 address [ANY]:443
 secure 1
}
'''
        worker, restart = self.worker()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'httpd_config.conf'
            path.write_text(config)
            worker(str(path), 'main.test', 'alias.test')
            result = path.read_text()
            self.assertEqual(result.count('alias.test'), 2)
            self.assertIn('map main.test.extra main.test.extra\n', result)
            self.assertIn('old.test, alias.test  # preserve', result)
            self.assertTrue(result.startswith('listener Public {\n map main.test main.test\n secure 0\n}'))
            worker(str(path), 'main.test', 'alias.test')
            self.assertEqual(path.read_text(), result)
        self.assertEqual(restart.call_count, 2)

    def test_ssl_named_listener_does_not_drop_prefix_neighbor(self):
        config = 'listener SSL {\n map main.test.extra main.test.extra\n map main.test main.test\n secure 1\n}\n'
        worker, _ = self.worker()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'httpd_config.conf'
            path.write_text(config)
            worker(str(path), 'main.test', 'alias.test')
            self.assertIn('map main.test.extra main.test.extra\n', path.read_text())

    def test_missing_tls_parent_does_not_write_restart_or_hide_failure(self):
        worker, restart = self.worker()
        for config in ('listener HTTPS {\n map other.test other.test\n secure 1\n}\n',
                       'listener SSL {\n map main.test main.test\n secure 0\n}\n'):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / 'httpd_config.conf'
                path.write_text(config)
                with self.assertRaisesRegex(ValueError, 'no HTTPS listener mapping'):
                    worker(str(path), 'main.test', 'alias.test')
                self.assertEqual(path.read_text(), config)
        restart.assert_not_called()
