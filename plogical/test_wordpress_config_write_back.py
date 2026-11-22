"""Values read from a site's wp-config.php are written back as quoted arguments, by the site's user."""
from pathlib import Path
import re
import shlex
import unittest

from plogical.wordpressInstallerUtilities import wordpress_config_set_command

SOURCE = (Path(__file__).resolve().parents[1] / 'plogical/applicationInstaller.py').read_text()
PHP = '/usr/local/lsws/lsphp83/bin/php'


class ConfigSetCommandTests(unittest.TestCase):
    def test_value_and_path_are_single_arguments_whatever_they_contain(self):
        for value in ('simple', 'pa ss', 'p"a$(id)`id`\'s', "it's; rm -rf /", '$HOME', 'a\nb', '-x', ''):
            command = wordpress_config_set_command(PHP, '/home/example.com/public_html/my blog/', 'DB_PASSWORD',
                                                   value)
            words = shlex.split(command)
            self.assertEqual([PHP, '-d', 'error_reporting=0', '-d', 'memory_limit=350M', '-d',
                              'max_execution_time=400', '/usr/bin/wp', 'config', 'set', 'DB_PASSWORD', value,
                              '--skip-plugins', '--skip-themes',
                              '--path=/home/example.com/public_html/my blog/'], words, repr(value))

    def test_only_the_three_database_constants_can_be_set(self):
        for key in ('DB_NAME', 'DB_USER', 'DB_PASSWORD'):
            self.assertIn(' config set %s ' % key, wordpress_config_set_command(PHP, '/home/x', key, 'v'))
        for key in ('WP_DEBUG', 'DB_HOST --raw', 'db_name', '', None):
            with self.assertRaises(ValueError):
                wordpress_config_set_command(PHP, '/home/x', key, 'v')

    def test_values_that_are_not_text_are_refused(self):
        for value in (None, 7, ['a'], {'a': 1}):
            with self.assertRaises(ValueError):
                wordpress_config_set_command(PHP, '/home/x', 'DB_NAME', value)


class RestoreSourceTests(unittest.TestCase):
    def live_lines(self):
        return [line for line in SOURCE.splitlines() if not line.lstrip().startswith('#')]

    def test_no_configuration_value_is_substituted_into_a_command_string(self):
        live = '\n'.join(self.live_lines())
        self.assertNotIn('sed -i "s/define(', live)
        self.assertIsNone(re.search(r'wp config set DB_(NAME|USER|PASSWORD) %s', live))

    def test_every_write_back_runs_as_the_site_user_and_ends_the_restore_when_it_fails(self):
        lines = self.live_lines()
        writes = [index for index, line in enumerate(lines) if 'wordpress_config_set_command(Final' in line]
        self.assertEqual(2, len(writes))
        for index in writes:
            self.assertIn('self.restoreStep(wordpress_config_set_command(Final', lines[index])
            self.assertTrue(lines[index + 1].strip().startswith('VHuser,'), lines[index + 1])


if __name__ == '__main__':
    unittest.main()
