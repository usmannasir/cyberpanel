"""Scheduled renewal must not terminate backups owned by the panel daemon."""
import ast
from datetime import datetime, timedelta
from pathlib import Path
import re
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, mock_open, patch

ROOT = Path(__file__).resolve().parents[1]


def load_definition(path, name, namespace):
    tree = ast.parse(path.read_text())
    node = next(node for node in tree.body if getattr(node, 'name', None) == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]


class RenewalServiceTests(unittest.TestCase):
    def setUp(self):
        self.issuer = Mock(return_value=(1, 'issued'))
        self.execute = Mock()
        self.websites = Mock()
        self.children = Mock()
        self.websites.objects.filter.return_value = []
        self.children.objects.all.return_value = []
        self.exists = Mock(return_value=True)
        self.cert = Mock()
        self.cert.get_notAfter.return_value = (datetime.now() + timedelta(days=60)).strftime('%Y%m%d%H%M%SZ').encode()
        self.cert.get_issuer.return_value.get_components.return_value = [(b'C', b'US'), (b'O', b"Let's Encrypt")]
        self.ns = dict(
            datetime=datetime, os=SimpleNamespace(path=SimpleNamespace(exists=self.exists)),
            logging=Mock(), virtualHostUtilities=SimpleNamespace(issueSSL=self.issuer),
            ProcessUtilities=SimpleNamespace(normalExecutioner=self.execute),
            Websites=self.websites, ChildDomains=self.children, time=Mock(),
            OpenSSL=SimpleNamespace(crypto=SimpleNamespace(Error=ValueError, FILETYPE_PEM=1, load_certificate=Mock(return_value=self.cert))),
            open=mock_open(read_data=b'certificate'))
        self.renew = load_definition(ROOT / 'plogical/renew.py', 'Renew', self.ns)()

    def check(self):
        return self.renew._check_and_renew_ssl('example.test', '/home/example.test/public_html', 'admin@example.test')

    def test_valid_certificate_does_not_issue_or_restart(self):
        self.assertFalse(self.check())
        self.issuer.assert_not_called()
        self.execute.assert_not_called()

    def test_missing_certificate_only_public_success_counts(self):
        self.exists.return_value = False
        for code in (0, 1, 2):
            with self.subTest(code=code):
                self.issuer.return_value = (code, 'result')
                self.assertEqual(self.check(), code == 1)

    def test_due_and_expired_outcomes(self):
        for days in (-1, 5):
            self.cert.get_notAfter.return_value = (datetime.now() + timedelta(days=days)).strftime('%Y%m%d%H%M%SZ').encode()
            for code in (0, 1, 2):
                with self.subTest(days=days, code=code):
                    self.issuer.return_value = (code, 'result')
                    self.assertEqual(self.check(), code == 1)

    def test_unreadable_certificate_does_not_count_as_renewed(self):
        self.ns['OpenSSL'].crypto.load_certificate.side_effect = ValueError('bad PEM')
        self.assertFalse(self.check())
        self.issuer.assert_not_called()

    def test_empty_run_restarts_nothing(self):
        self.renew.SSLObtainer()
        self.execute.assert_not_called()

    def test_no_change_run_restarts_nothing(self):
        self.websites.objects.filter.return_value = [SimpleNamespace(domain='example.test', adminEmail='admin@example.test')]
        self.renew.SSLObtainer()
        self.execute.assert_not_called()
        self.issuer.assert_not_called()

    def test_failed_issuance_run_restarts_nothing(self):
        self.exists.return_value = False
        self.issuer.return_value = (0, 'issuance failed')
        self.websites.objects.filter.return_value = [SimpleNamespace(domain='example.test', adminEmail='admin@example.test')]
        self.renew.SSLObtainer()
        self.issuer.assert_called_once()
        self.execute.assert_not_called()

    def test_success_does_not_leak_into_the_next_run(self):
        self.websites.objects.filter.return_value = [SimpleNamespace(domain='example.test', adminEmail='admin@example.test')]
        with patch.object(self.renew, '_check_and_renew_ssl', side_effect=[True, False]):
            self.renew.SSLObtainer()
            self.execute.reset_mock()
            self.renew.SSLObtainer()
        self.execute.assert_not_called()

    def test_mixed_domains_all_checked_and_mail_refreshed_once(self):
        self.websites.objects.filter.return_value = [SimpleNamespace(domain=str(i), adminEmail='admin@example.test') for i in range(3)]
        self.children.objects.all.return_value = [SimpleNamespace(domain='child', path='/home/child', master=SimpleNamespace(adminEmail='admin@example.test'))]
        with patch.object(self.renew, '_check_and_renew_ssl', side_effect=[True, False, False, True]) as check:
            self.renew.SSLObtainer()
        self.assertEqual(check.call_count, 4)
        self.assertEqual([call.args[0] for call in self.execute.call_args_list], [
            'postmap -F hash:/etc/postfix/vmail_ssl.map', 'systemctl restart postfix', 'doveadm reload'])

    def test_child_only_renewal_refreshes_mail_without_restarting_panel(self):
        self.children.objects.all.return_value = [SimpleNamespace(domain='child', path='/home/child', master=SimpleNamespace(adminEmail='admin@example.test'))]
        with patch.object(self.renew, '_check_and_renew_ssl', return_value=True):
            self.renew.SSLObtainer()
        self.assertEqual(self.execute.call_count, 3)
        self.assertFalse(any('lscpd' in call.args[0] for call in self.execute.call_args_list))


class RenewalScheduleTests(unittest.TestCase):
    def test_migration_preserves_custom_schedules_comments_and_other_jobs(self):
        migrate = load_definition(ROOT / 'plogical/upgrade.py', 'stagger_renewal_cron', {'re': re})
        command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py'
        original = '\n'.join(['0 0 * * 4 ' + command + ' >/dev/null 2>&1',
            '15 3 * * 4 ' + command, '# 0 0 * * 4 ' + command,
            '0 0 * * 4 ' + command + '.custom', '0 0 * * 4 other-job']) + '\n'
        result = migrate(original)
        self.assertEqual(result, original.replace('0 0 * * 4 ' + command + ' >', '45 4 * * 4 ' + command + ' >'))
        self.assertEqual(migrate(result), result)

    def test_new_install_and_upgrade_templates_use_staggered_slot(self):
        for name in ('install/install.py', 'plogical/upgrade.py'):
            source = (ROOT / name).read_text()
            lines = [line for line in source.splitlines() if line.startswith(('0 0 * * 4 ', '45 4 * * 4 ')) and '/plogical/renew.py' in line]
            self.assertTrue(lines)
            self.assertTrue(all(line.startswith('45 4 * * 4 ') for line in lines))


if __name__ == '__main__':
    unittest.main()
