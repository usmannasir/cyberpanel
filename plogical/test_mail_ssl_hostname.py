"""Mail certificate maintenance must preserve the shared Postfix identity."""
import ast
import contextlib
import io
from pathlib import Path
import tempfile
import unittest
from unittest import mock


class MailSSLHostnameTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.postfix = self.root / 'main.cf'
        self.dovecot = self.root / 'dovecot.conf'
        self.dovecot.write_text('protocols = imap\npostmaster_address = postmaster@server.example\n')
        self.opened = []
        self.paths = {'/etc/postfix/main.cf': self.postfix,
                      '/etc/dovecot/dovecot.conf': self.dovecot}
        self.services = mock.Mock()
        self.ssl = mock.Mock()
        self.ssl.issueSSLForDomain.return_value = [1, 'None']
        self.process = mock.Mock()
        self.os = mock.Mock()
        self.os.path.exists.side_effect = lambda path: (
            self.paths[path].exists() if path in self.paths else True)
        self.env = {
            'os': self.os,
            'open': self.open_config,
            'sslUtilities': self.ssl,
            'virtualHostUtilities': mock.Mock(),
            'ProcessUtilities': self.services,
            'Process': self.process,
            'mailUtilities': mock.Mock(),
            'logging': mock.Mock(),
        }
        # Execute the production method without bootstrapping Django or host services.
        source = Path(__file__).with_name('virtualHostUtilities.py')
        tree = ast.parse(source.read_text(), filename=str(source))
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == 'virtualHostUtilities')
        method = next(node for node in cls.body
                      if isinstance(node, ast.FunctionDef) and node.name == 'issueSSLForMailServer')
        method.decorator_list = []
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(source), 'exec'), self.env)

    def open_config(self, path, mode='r'):
        self.opened.append((path, mode))
        handle = self.paths[path].open(mode)
        self.addCleanup(handle.close)
        return handle

    def issue(self, domain):
        with contextlib.redirect_stdout(io.StringIO()):
            return self.env['issueSSLForMailServer'](domain, '/home/' + domain + '/public_html')

    def test_successive_tenants_preserve_postfix_configuration(self):
        for hostname in ('myhostname = mail.server.example\n', '', '#myhostname = default.example\n'):
            with self.subTest(hostname=hostname):
                original = (hostname + 'myorigin = $myhostname\n'
                            'smtpd_banner = $myhostname ESMTP\n'
                            '# Keep myhostname aligned with the server PTR\n')
                self.postfix.write_text(original)
                self.opened.clear()
                self.services.reset_mock()
                self.process.reset_mock()
                for domain in ('tenant-a.example', 'tenant-b.example'):
                    self.assertEqual((1, 'None'), self.issue(domain))
                    self.assertEqual(original, self.postfix.read_text())
                    self.services.executioner.assert_any_call(
                        'ln -s /etc/letsencrypt/live/' + domain + '/privkey.pem /etc/postfix/key.pem')
                    self.services.executioner.assert_any_call(
                        'ln -s /etc/letsencrypt/live/' + domain + '/fullchain.pem /etc/postfix/cert.pem')
                self.assertFalse(any(path == '/etc/postfix/main.cf' for path, _ in self.opened))
                self.assertEqual(2, self.process.return_value.start.call_count)
                self.process.assert_called_with(target=self.env['mailUtilities'].restartServices, args=())

    def test_missing_postfix_configuration_does_not_skip_certificate_reload(self):
        self.assertEqual((1, 'None'), self.issue('tenant.example'))
        self.assertFalse(self.postfix.exists())
        self.process.return_value.start.assert_called_once_with()

    def test_failed_or_retained_certificate_does_not_mutate_mail_configuration(self):
        original = 'myhostname = mail.server.example\n'
        for status in (0, 2):
            with self.subTest(status=status):
                self.postfix.write_text(original)
                self.ssl.issueSSLForDomain.return_value = [status, 'Certificate unchanged']
                self.assertEqual((status, 'Certificate unchanged'), self.issue('tenant.example'))
                self.assertEqual(original, self.postfix.read_text())
                self.assertEqual([], self.opened)
                self.os.remove.assert_not_called()
                self.services.executioner.assert_not_called()
                self.process.assert_not_called()


if __name__ == '__main__':
    unittest.main()
