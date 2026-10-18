"""Exercise actual cleanup with an isolated config file and no real directories."""
import ast
import builtins
from pathlib import Path
from types import SimpleNamespace as NS
import tempfile
import unittest
from unittest import mock


class VhostDeletionConfigTests(unittest.TestCase):
    def cleanup(self, config, count=2):
        source = Path(__file__).with_name('vhost.py')
        tree = ast.parse(source.read_text())
        method = next(n for n in ast.walk(tree)
                      if isinstance(n, ast.FunctionDef) and n.name == 'deleteCoreConf')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'httpd_config.conf'
            path.write_text(config)
            def isolated_open(filename, *args, **kwargs):
                self.assertEqual('/usr/local/lsws/conf/httpd_config.conf', filename)
                return builtins.open(path, *args, **kwargs)
            scope = {
                'open': isolated_open,
                'os': NS(path=NS(exists=lambda path: False)),
                'ProcessUtilities': NS(OLS=1, decideServer=lambda: 1),
                'vhost': NS(Server_root='/usr/local/lsws'),
                'ApacheVhost': NS(DeleteApacheVhost=mock.Mock()),
                'logging': NS(CyberCPLogFileWriter=NS(writeToFile=mock.Mock())),
            }
            exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), scope)
            result = scope['deleteCoreConf'].__func__('example.com', count)
            self.assertEqual(1, result)
            return path.read_text()

    def test_preserves_domains_with_same_prefix(self):
        target = 'virtualhost example.com {\n  vhRoot /home/example.com\n}\n'
        neighbor = 'virtualhost example.com.au {\n  vhRoot /home/example.com.au\n}\n'
        for count in (1, 2, '2'):
            with self.subTest(count=count):
                self.assertEqual(neighbor, self.cleanup(target + neighbor, count))

    def test_removes_mappings_with_arbitrary_whitespace(self):
        for whitespace in (' ', '\t', '                     '):
            with self.subTest(whitespace=whitespace):
                mapping = '  map' + whitespace + 'example.com example.com\n'
                neighbor = '  map' + whitespace + 'example.com.au example.com.au\n'
                config = 'listener HTTP {\n' + mapping + neighbor + '}\n'
                self.assertEqual('listener HTTP {\n' + neighbor + '}\n', self.cleanup(config))

    def test_last_site_removes_ssl_listener_for_integer_and_string_counts(self):
        http = 'listener HTTP {\n  address *:80\n}\n'
        ssl = ('listener SSL {\n  address *:443\n'
               '  keyFile /etc/letsencrypt/live/example.com/privkey.pem\n'
               '  certFile /etc/letsencrypt/live/example.com/fullchain.pem\n}\n')
        for count in (1, '1'):
            with self.subTest(count=count):
                self.assertEqual(http, self.cleanup(http + ssl, count))
        for count in (2, '2'):
            with self.subTest(count=count):
                self.assertEqual(http + ssl, self.cleanup(http + ssl, count))

    def test_ignores_comments_mentioning_target(self):
        config = '# virtualhost example.com {\nlistener HTTP {\n  address *:80\n}\n'
        self.assertEqual(config, self.cleanup(config))


if __name__ == '__main__':
    unittest.main()
