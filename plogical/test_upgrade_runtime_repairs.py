import os
import stat
import subprocess
import tempfile
import unittest
from unittest.mock import call, patch

from plogical.upgrade import Upgrade


class UpgradeRuntimeRepairTests(unittest.TestCase):

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.shutil.copy2')
    @patch('plogical.upgrade.tempfile.mkdtemp', return_value='/tmp/cyberpanel-backup')
    def test_upgrade_backs_up_environment_and_secret_files(
            self, mkdtemp, copy2, std_out):
        protected_files = {
            '/usr/local/CyberCP/.env',
            '/usr/local/CyberCP/.env.backup',
            '/usr/local/CyberCP/secret_key',
        }

        with patch('plogical.upgrade.os.path.exists',
                   side_effect=lambda path: path in protected_files):
            backup_dir, backed_up_files = Upgrade.backupCriticalFiles()

        self.assertEqual('/tmp/cyberpanel-backup', backup_dir)
        self.assertEqual(protected_files, set(backed_up_files))
        self.assertEqual(
            [
                call('/usr/local/CyberCP/.env', '/tmp/cyberpanel-backup/.env'),
                call('/usr/local/CyberCP/.env.backup', '/tmp/cyberpanel-backup/.env.backup'),
                call('/usr/local/CyberCP/secret_key', '/tmp/cyberpanel-backup/secret_key'),
            ],
            copy2.call_args_list,
        )

    def test_static_permissions_are_normalized(self):
        with tempfile.TemporaryDirectory() as static_root:
            nested_directory = os.path.join(static_root, 'admin', 'css')
            os.makedirs(nested_directory, mode=0o700)
            asset = os.path.join(nested_directory, 'base.css')
            with open(asset, 'w') as output:
                output.write('body {}')
            os.chmod(asset, 0o755)

            Upgrade.normalizeStaticPermissions(static_root)

            self.assertEqual(0o755, stat.S_IMODE(os.stat(static_root).st_mode))
            self.assertEqual(0o755, stat.S_IMODE(os.stat(nested_directory).st_mode))
            self.assertEqual(0o644, stat.S_IMODE(os.stat(asset).st_mode))

    def test_missing_postfix_ipv6_loopbacks_are_added(self):
        config = 'mynetworks = 127.0.0.0/8 192.0.2.0/24\nmyhostname = mail.example.com\n'

        updated, changed = Upgrade.addPostfixLoopbackNetworks(config)

        self.assertTrue(changed)
        self.assertIn('127.0.0.0/8 192.0.2.0/24 [::ffff:127.0.0.0]/104 [::1]/128\n', updated)
        self.assertIn('myhostname = mail.example.com\n', updated)

    def test_postfix_inline_comment_is_preserved(self):
        config = 'mynetworks = 127.0.0.0/8  # trusted senders\n'

        updated, changed = Upgrade.addPostfixLoopbackNetworks(config)

        self.assertTrue(changed)
        self.assertEqual(
            'mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128  # trusted senders\n',
            updated,
        )

    def test_postfix_loopback_update_is_idempotent(self):
        config = 'mynetworks = 127.0.0.0/8 [::ffff:127.0.0.0]/104 [::1]/128\n'

        updated, changed = Upgrade.addPostfixLoopbackNetworks(config)

        self.assertFalse(changed)
        self.assertEqual(config, updated)

    def test_implicit_postfix_networks_are_not_replaced(self):
        config = '# mynetworks = 127.0.0.0/8\nmynetworks_style = host\n'

        updated, changed = Upgrade.addPostfixLoopbackNetworks(config)

        self.assertFalse(changed)
        self.assertEqual(config, updated)

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.subprocess.call', side_effect=(0, 0, 0))
    def test_postfix_file_update_is_atomic_and_reloads_active_service(self, call, std_out):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = os.path.join(temporary_directory, 'main.cf')
            with open(config_path, 'w') as config_file:
                config_file.write('mynetworks = 127.0.0.0/8\n')
            os.chmod(config_path, 0o640)

            self.assertEqual(1, Upgrade.ensurePostfixLoopbackNetworks(config_path))

            with open(config_path, 'r') as config_file:
                updated = config_file.read()
            self.assertIn('[::ffff:127.0.0.0]/104 [::1]/128', updated)
            self.assertEqual(0o640, stat.S_IMODE(os.stat(config_path).st_mode))
            self.assertEqual(
                [
                    unittest.mock.call(['postfix', 'check']),
                    unittest.mock.call(['systemctl', 'is-active', '--quiet', 'postfix']),
                    unittest.mock.call(['systemctl', 'reload', 'postfix']),
                ],
                call.call_args_list,
            )

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.subprocess.call', return_value=1)
    def test_invalid_postfix_update_is_reverted(self, call, std_out):
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = os.path.join(temporary_directory, 'main.cf')
            original = 'mynetworks = 127.0.0.0/8\n'
            with open(config_path, 'w') as config_file:
                config_file.write(original)

            self.assertEqual(0, Upgrade.ensurePostfixLoopbackNetworks(config_path))

            with open(config_path, 'r') as config_file:
                self.assertEqual(original, config_file.read())
            call.assert_called_once_with(['postfix', 'check'])

    def test_reserved_postfix_domain_alias_is_removed(self):
        config = "query = SELECT domain AS virtual FROM e_domains WHERE domain='%s'\n"

        updated, replacements = Upgrade.normalizePostfixDomainLookup(config)

        self.assertEqual(1, replacements)
        self.assertEqual(
            "query = SELECT domain FROM e_domains WHERE domain='%s'\n",
            updated,
        )

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.subprocess.call', side_effect=(0, 0))
    @patch('plogical.upgrade.subprocess.run')
    def test_postfix_domain_lookup_is_validated_and_reloaded(
            self, run, call, std_out):
        run.return_value = subprocess.CompletedProcess([], 0, '', '')
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = os.path.join(
                temporary_directory, 'mysql-virtual_domains.cf')
            with open(config_path, 'w') as config_file:
                config_file.write(
                    "query = SELECT domain AS virtual FROM e_domains WHERE domain='%s'\n"
                )
            os.chmod(config_path, 0o640)

            self.assertEqual(1, Upgrade.ensurePostfixDomainLookup(config_path))

            with open(config_path, 'r') as config_file:
                updated = config_file.read()
            self.assertNotIn('AS virtual', updated)
            self.assertEqual(0o640, stat.S_IMODE(os.stat(config_path).st_mode))
            run.assert_called_once_with(
                [
                    'postmap', '-q', '__cyberpanel_config_check__',
                    'mysql:%s' % config_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                universal_newlines=True,
            )
            self.assertEqual(
                [
                    unittest.mock.call(
                        ['systemctl', 'is-active', '--quiet', 'postfix']),
                    unittest.mock.call(['systemctl', 'reload', 'postfix']),
                ],
                call.call_args_list,
            )

    @patch('plogical.upgrade.Upgrade.stdOut')
    @patch('plogical.upgrade.subprocess.run')
    def test_invalid_postfix_domain_lookup_is_reverted(
            self, run, std_out):
        run.return_value = subprocess.CompletedProcess([], 1, '', 'query failed')
        with tempfile.TemporaryDirectory() as temporary_directory:
            config_path = os.path.join(
                temporary_directory, 'mysql-virtual_domains.cf')
            original = (
                "query = SELECT domain AS virtual FROM e_domains "
                "WHERE domain='%s'\n"
            )
            with open(config_path, 'w') as config_file:
                config_file.write(original)

            self.assertEqual(0, Upgrade.ensurePostfixDomainLookup(config_path))

            with open(config_path, 'r') as config_file:
                self.assertEqual(original, config_file.read())


if __name__ == '__main__':
    unittest.main()
