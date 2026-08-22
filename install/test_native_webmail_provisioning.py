import pathlib
import ast
import unittest
from unittest import mock

from plogical import legacyWebmail


class NativeWebmailProvisioningTests(unittest.TestCase):

    def setUp(self):
        self.repository = pathlib.Path(__file__).parents[1]

    def read(self, relative_path):
        return (self.repository / relative_path).read_text(encoding='utf-8')

    def test_install_and_upgrade_configure_native_webmail(self):
        installer = self.read('install/install.py')
        upgrade = self.read('plogical/upgrade.py')

        self.assertEqual(
            installer.count('installCyberPanel.InstallCyberPanel.setupWebmail()'),
            2,
        )
        self.assertIn('Upgrade.setupWebmail()', upgrade)
        self.assertIn('Upgrade.setupSieve()', upgrade)

    def test_postfix_domain_templates_avoid_reserved_alias(self):
        for relative_path in (
            'install/email-configs/mysql-virtual_domains.cf',
            'install/email-configs-one/mysql-virtual_domains.cf',
        ):
            with self.subTest(relative_path=relative_path):
                config = self.read(relative_path)
                self.assertIn(
                    "query = SELECT domain FROM e_domains WHERE domain='%s'",
                    config,
                )
                self.assertNotIn('AS virtual', config)

    def test_downloaded_upgrade_script_has_no_new_top_level_dependency(self):
        upgrade_tree = ast.parse(self.read('plogical/upgrade.py'))
        top_level_imports = [
            node for node in upgrade_tree.body
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        self.assertFalse(any(
            isinstance(node, ast.ImportFrom)
            and node.module == 'plogical.legacyWebmail'
            for node in top_level_imports
        ))

        fix_permissions = next(
            node for node in ast.walk(upgrade_tree)
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
            and node.name == 'fixPermissions'
        )
        self.assertTrue(any(
            isinstance(node, ast.ImportFrom)
            and node.module == 'plogical.legacyWebmail'
            for node in ast.walk(fix_permissions)
        ))

    def test_legacy_client_is_not_provisioned(self):
        active_sources = '\n'.join(
            self.read(relative_path)
            for relative_path in (
                'install/install.py',
                'plogical/upgrade.py',
                'plogical/acl.py',
                'plogical/mailUtilities.py',
                'mailServer/mailserverManager.py',
                'cyberpanel.sh',
                'cyberpanel_upgrade.sh',
                'install/venvsetup.sh',
            )
        )

        for obsolete_fragment in (
            'the-djmaze/snappymail',
            'SnappyVersion',
            'downoad_and_install_raindloop',
            'snappymail_cyberpanel.php',
            'public/snappymail.php',
            'InstallMailBoxFoldersPlugin',
            'AfterEffects --domain',
        ):
            with self.subTest(fragment=obsolete_fragment):
                self.assertNotIn(obsolete_fragment, active_sources)

    def test_permission_repairs_do_not_create_legacy_data(self):
        helper = self.read('plogical/legacyWebmail.py')
        upgrade_script = self.read('cyberpanel_upgrade.sh')

        self.assertNotIn('mkdir', helper)
        self.assertNotIn('mkdir -p /usr/local/lscp/cyberpanel/snappymail', upgrade_script)
        self.assertIn('if [[ -d "$legacy_data_path" ]]', upgrade_script)

        data_paths = (
            '/usr/local/lscp/cyberpanel/snappymail/data',
            '/usr/local/lscp/cyberpanel/rainloop/data',
        )
        expected_commands = []
        for data_path in data_paths:
            with self.subTest(data_path=data_path):
                self.assertIn(data_path, helper)
                expected_commands.extend((
                    'chown -R lscpd:lscpd %s' % data_path,
                    'find %s -type d -exec chmod 700 {} \\;' % data_path,
                    'find %s -type f -exec chmod 600 {} \\;' % data_path,
                ))

        with mock.patch.object(legacyWebmail, 'LEGACY_DATA_PATHS', data_paths), \
                mock.patch.object(legacyWebmail.os.path, 'isdir', return_value=True):
            self.assertEqual(
                list(legacyWebmail.legacy_data_permission_commands()),
                expected_commands,
            )


if __name__ == '__main__':
    unittest.main()
