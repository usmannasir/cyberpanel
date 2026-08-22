import ast
import pathlib
import unittest


class SnappyMailPermissionTests(unittest.TestCase):

    def test_install_and_repair_paths_protect_data_directories(self):
        repository = pathlib.Path(__file__).parents[1]
        repair_sources = (
            'install/install.py',
            'plogical/upgrade.py',
            'plogical/acl.py',
            'mailServer/mailserverManager.py',
            'cyberpanel_upgrade.sh',
        )

        for data_path in (
            '/usr/local/lscp/cyberpanel/snappymail/data',
            '/usr/local/lscp/cyberpanel/rainloop/data',
        ):
            required_commands = (
                f'chown -R lscpd:lscpd {data_path}',
                f'find {data_path} -type d -exec chmod 700 {{}} \\;',
                f'find {data_path} -type f -exec chmod 600 {{}} \\;',
            )
            for relative_path in repair_sources:
                with self.subTest(source=relative_path, data_path=data_path):
                    source = (repository / relative_path).read_text(encoding='utf-8')
                    if relative_path.endswith('.py'):
                        source_commands = {
                            node.value
                            for node in ast.walk(ast.parse(source))
                            if isinstance(node, ast.Constant)
                            and isinstance(node.value, str)
                        }
                    else:
                        source_commands = source
                    for command in required_commands:
                        self.assertIn(command, source_commands)

                    self.assertNotIn(f'chmod -R 775 {data_path}', source)

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
                commands = [
                    (node.lineno, node.value)
                    for node in ast.walk(ast.parse(source))
                    if isinstance(node, ast.Constant)
                    and isinstance(node.value, str)
                ]
                configuration = max(
                    line for line, value in commands if value == configure_command
                )
                for data_path in (
                    '/usr/local/lscp/cyberpanel/snappymail/data',
                    '/usr/local/lscp/cyberpanel/rainloop/data',
                ):
                    ownership = min(
                        line for line, value in commands
                        if line > configuration
                        and value == f'chown -R lscpd:lscpd {data_path}'
                    )
                    directory_mode = min(
                        line for line, value in commands
                        if line > ownership
                        and value == (
                            f'find {data_path} -type d '
                            f'-exec chmod 700 {{}} \\;'
                        )
                    )
                    file_mode = min(
                        line for line, value in commands
                        if line > directory_mode
                        and value == (
                            f'find {data_path} -type f '
                            f'-exec chmod 600 {{}} \\;'
                        )
                    )
                    self.assertGreater(file_mode, configuration)


if __name__ == '__main__':
    unittest.main()
