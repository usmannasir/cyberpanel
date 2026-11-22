"""A website's PHP version is read from the digits of its PHP path; nothing found in its configuration is run."""
import shlex
import unittest
from unittest import mock

from plogical.test_php_extension_worker import load_php_utilities

VHOST = '/usr/local/lsws/conf/vhosts/example.test/vhost.conf'
OLS, ENTERPRISE = 'ols', 'lsws'


class PHPVersionFromVhostTests(unittest.TestCase):
    def worker(self, server=OLS, grep_output='', distro='ubuntu'):
        module, services = load_php_utilities(distro)
        services.process.OLS = OLS
        services.process.decideServer.return_value = server
        services.process.outputExecutioner.return_value = grep_output
        services.apache.configBasePath = '/etc/apache2/sites-enabled/'
        patcher = mock.patch.object(module.os.path, 'exists', return_value=False)
        patcher.start()
        self.addCleanup(patcher.stop)
        return module.phpUtilities, services.process

    def commands(self, process):
        return [call[0][0] for call in process.outputExecutioner.call_args_list]

    def test_version_comes_from_the_path_and_no_php_program_is_run(self):
        for server, found in ((OLS, '/usr/local/lsws/lsphp83/bin/lsphp\n'), (ENTERPRISE, 'php83\n')):
            with self.subTest(server=server):
                utilities, process = self.worker(server, found)
                self.assertEqual('PHP 8.3', utilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(VHOST))
                # One fixed search of the file; its result is never a command.
                commands = self.commands(process)
                self.assertEqual(1, len(commands), commands)
                self.assertTrue(commands[0].startswith('grep '))
                self.assertNotIn(' -v', commands[0])
                process.executioner.assert_not_called()
                process.normalExecutioner.assert_not_called()

    def test_several_matches_give_one_path_built_from_the_first(self):
        found = '/usr/local/lsws/lsphp74/bin/lsphp\n/usr/local/lsws/lsphp83/bin/lsphp\n' \
                '/usr/local/lsws/lsphp81/bin/lsphp\n'
        utilities, process = self.worker(OLS, found)
        path = utilities.GetPHPVersionFromFile(VHOST)
        self.assertEqual('/usr/local/lsws/lsphp74/bin/php', path)
        self.assertEqual([path], shlex.split(path))
        utilities, process = self.worker(OLS, found)
        self.assertEqual('PHP 7.4', utilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(VHOST))
        self.assertEqual(1, len(self.commands(process)))

    def test_two_digit_minor_versions_are_read_whole(self):
        utilities, _ = self.worker(OLS, '/usr/local/lsws/lsphp810/bin/lsphp\n')
        self.assertEqual('/usr/local/lsws/lsphp810/bin/php', utilities.GetPHPVersionFromFile(VHOST))
        utilities, _ = self.worker(OLS, '/usr/local/lsws/lsphp810/bin/lsphp\n')
        self.assertEqual('PHP 8.10', utilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(VHOST))

    def test_output_that_is_not_the_searched_pattern_gives_no_path_from_it(self):
        for server, expected in ((OLS, 'php'), (ENTERPRISE, '/usr/local/lsws/ls/bin/php')):
            for found in ('', 'grep: %s: No such file or directory\n' % VHOST, '/bin/sh -c id\n',
                          '/usr/local/lsws/lsphp83/bin/lsphp; id\n/usr/bin/id\n'):
                with self.subTest(server=server, found=found):
                    utilities, process = self.worker(server, found)
                    path = utilities.GetPHPVersionFromFile(VHOST)
                    # Whatever else the output holds, only the digits are used.
                    expected_path = '/usr/local/lsws/lsphp83/bin/php' if 'lsphp83' in found else expected
                    self.assertEqual(expected_path, path)
                    utilities, process = self.worker(server, found)
                    utilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(VHOST)
                    self.assertEqual(1, len(self.commands(process)))

    def test_the_searched_file_is_one_word_of_the_command(self):
        odd = '/usr/local/lsws/conf/vhosts/example.test; id/vhost.conf'
        for server in (OLS, ENTERPRISE):
            utilities, process = self.worker(server, '')
            utilities.GetPHPVersionFromFile(odd)
            words = shlex.split(self.commands(process)[0].split(' | ')[0])
            self.assertEqual(odd, words[-1])

    def test_apache_backend_paths_give_their_version(self):
        utilities, process = self.worker()
        with mock.patch.object(utilities, 'GetPHPVersionFromFile', return_value='/usr/bin/php8.1'):
            self.assertEqual('PHP 8.1', utilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(VHOST))
        with mock.patch.object(utilities, 'GetPHPVersionFromFile', return_value='/opt/remi/php74/root/bin/php'):
            self.assertEqual('PHP 7.4', utilities.WrapGetPHPVersionFromFileToGetVersionWithPHP(VHOST))
        process.outputExecutioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
