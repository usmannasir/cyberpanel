import ast
from pathlib import Path
from types import SimpleNamespace
from unittest import TestCase, mock
from plogical.domainAliasUtilities import add_http_alias_mapping


class AliasHTTPMappingTests(TestCase):
    def test_all_http_listeners_exact_parent_and_comments(self):
        config = '''listener Public {
 map\tmain.test\tmain.test, old.test # retained
 map main.test.extra main.test.extra
 secure 0
}
listener IPv6 {
 map main.test main.test
 address [ANY]:80
}
listener SSL {
 map main.test main.test
 secure 1
}
'''
        result = add_http_alias_mapping(config, 'main.test', 'alias.test')
        self.assertIn('old.test, alias.test  # retained', result)
        self.assertIn('map                     main.test main.test, alias.test', result)
        self.assertIn('map main.test.extra main.test.extra\n', result)
        self.assertIn('listener SSL {\n map main.test main.test\n secure 1', result)
        self.assertEqual(result.count('alias.test'), 2)
        self.assertNotIn('\t', result)
        self.assertEqual(result, add_http_alias_mapping(result, 'main.test', 'alias.test'))

    def test_missing_http_parent_fails(self):
        for config in ('listener Default{\n map other.test other.test\n}\n',
                       'listener SSL {\n map main.test main.test\n secure 1\n}\n'):
            with self.assertRaisesRegex(ValueError, 'no HTTP listener mapping'):
                add_http_alias_mapping(config, 'main.test', 'alias.test')

    def test_default_listener(self):
        config = 'listener Default{\n  map main.test main.test\n secure 0\n}\n'
        self.assertIn('map                     main.test main.test, alias.test\n',
                      add_http_alias_mapping(config, 'main.test', 'alias.test'))

    def test_worker_does_not_write_config_or_save_alias_after_missing_mapping(self):
        # Exercise the real worker without importing its installed-server dependencies.
        source = Path(__file__).with_name('virtualHostUtilities.py').read_text()
        module = ast.parse(source)
        cls = next(node for node in module.body if isinstance(node, ast.ClassDef) and node.name == 'virtualHostUtilities')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'createAlias')
        method.decorator_list = []
        namespace = {name: mock.MagicMock() for name in (
            'Administrator', 'DNS', 'vhost', 'ProcessUtilities', 'installUtilities',
            'Websites', 'aliasDomains', 'logging', 'sslUtilities')}
        namespace.update(virtualHostUtilities=SimpleNamespace(Server_root='/server'),
                         add_http_alias_mapping=add_http_alias_mapping, __name__=__name__)
        import os
        namespace['os'] = os
        namespace['vhost'].checkIfAliasExists.return_value = 0
        namespace['ProcessUtilities'].decideServer.return_value = namespace['ProcessUtilities'].OLS
        opened = mock.mock_open(read_data='listener Default{\n map other.test other.test\n}\n')
        namespace['open'] = opened
        exec(compile(ast.Module(body=[method], type_ignores=[]), '<worker>', 'exec'), namespace)
        with mock.patch('builtins.print') as output:
            namespace['createAlias']('main.test', 'alias.test', 0, '/home/main.test/public_html', 'test@example.test', 'admin')
        self.assertEqual(opened.call_count, 1)
        namespace['aliasDomains'].assert_not_called()
        namespace['Websites'].objects.get.assert_not_called()
        namespace['installUtilities'].installUtilities.reStartLiteSpeed.assert_not_called()
        self.assertTrue(output.call_args.args[0].startswith('0,Parent domain'))
