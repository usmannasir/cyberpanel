import os
import stat
import tempfile
import unittest
from unittest.mock import patch

from plogical.upgrade import Upgrade


class UpgradeRuntimeRepairTests(unittest.TestCase):

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


if __name__ == '__main__':
    unittest.main()
