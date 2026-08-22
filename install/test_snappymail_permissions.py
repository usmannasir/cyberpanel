import pathlib
import unittest


class SnappyMailPermissionTests(unittest.TestCase):

    def test_install_and_repair_paths_own_the_active_data_directory(self):
        repository = pathlib.Path(__file__).parents[1]
        ownership_command = (
            'chown -R lscpd:lscpd '
            '/usr/local/lscp/cyberpanel/rainloop/data'
        )
        repair_sources = (
            'install/install.py',
            'plogical/upgrade.py',
            'plogical/acl.py',
            'mailServer/mailserverManager.py',
            'cyberpanel_upgrade.sh',
        )

        for relative_path in repair_sources:
            with self.subTest(source=relative_path):
                source = (repository / relative_path).read_text(encoding='utf-8')
                self.assertIn(ownership_command, source)

        configure_command = (
            '/usr/bin/php /usr/local/CyberCP/public/snappymail.php'
        )
        for relative_path in (
            'install/install.py',
            'plogical/upgrade.py',
            'plogical/acl.py',
        ):
            with self.subTest(configuration_order=relative_path):
                source = (repository / relative_path).read_text(encoding='utf-8')
                configuration = source.rindex(configure_command)
                ownership = source.index(ownership_command, configuration)
                self.assertGreater(ownership, configuration)


if __name__ == '__main__':
    unittest.main()
