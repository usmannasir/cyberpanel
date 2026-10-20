"""WP credentials and site fields must reach the executable literally."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from plogical.wordpressInstallerUtilities import (
    build_wordpress_config_command,
    build_wordpress_config_password_command,
    wrap_wordpress_site_shell_script,
    build_wordpress_site_install_command,
)

class WordPressArgumentQuotingTests(unittest.TestCase):
    def test_site_shell_wrapper_keeps_assignment_and_all_stages_in_one_command(self):
        import shlex
        script = 'value=$(printf literal); printf "%s" "$value"'
        command = wrap_wordpress_site_shell_script(script)
        self.assertEqual(shlex.split(command), ['sh', '-c', script])
        result = subprocess.check_output(command, shell=True, text=True)
        self.assertEqual(result, 'literal')

    def test_real_executable_receives_exact_config_and_install_arguments(self):
        with tempfile.TemporaryDirectory(prefix='wp quote ') as folder:
            capture = Path(folder) / "capture's arguments"
            capture.write_text('#!' + sys.executable + '\nimport json, sys\nprint(json.dumps(sys.argv[1:]))\n')
            capture.chmod(0o700)
            sentinel = Path(folder) / 'must-not-exist'
            password = "Strong$HOME 'double\" ;$(touch %s)`touch %s` \\!&123" % (sentinel, sentinel)
            destination = folder + "/site's path"
            config = build_wordpress_config_command(str(capture), destination, 'owned_db', 'owned_user', password, 'localhost:3306')
            config_password = build_wordpress_config_password_command(str(capture), destination, password)
            install = build_wordpress_site_install_command(str(capture), destination, 'http://fixture.example/a b', 'Title $HOME; "literal"', 'admin.name+qa', password, 'qa@example.invalid')
            for command, expected in (
                (config, ['-d', 'error_reporting=0', '/usr/bin/wp', 'core', 'config', '--dbname=owned_db', '--dbuser=owned_user', '--dbpass=' + password, '--dbhost=localhost:3306', '--dbprefix=wp_', '--path=' + destination]),
                (config_password, ['-d', 'error_reporting=0', '/usr/bin/wp', 'config', 'set', 'DB_PASSWORD', password, '--type=constant', '--path=' + destination]),
                (install, ['-d', 'error_reporting=0', '/usr/bin/wp', 'core', 'install', '--url=http://fixture.example/a b', '--title=Title $HOME; "literal"', '--admin_user=admin.name+qa', '--admin_password=' + password, '--admin_email=qa@example.invalid', '--path=' + destination]),
            ):
                with self.subTest(operation=expected[4]):
                    result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
                    self.assertEqual(json.loads(result.stdout), expected)
                    self.assertFalse(sentinel.exists())

if __name__ == '__main__':
    unittest.main()
