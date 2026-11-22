"""Only PHP packages are named to the package managers, on the page and again in the worker."""
import json
import shlex
import unittest

from managePHP.phpConfig import is_php_package, php_package_prefix
from managePHP.test_php_selection import NOT_A_SELECTION, OFFERED
from managePHP.test_request_methods import load_views, post

# Names as the extension pages list them on Ubuntu, AlmaLinux and for the Apache backend.
LISTED = (
    'lsphp83', 'lsphp83-apcu', 'lsphp83-common', 'lsphp83-curl', 'lsphp83-dbg', 'lsphp83-dev', 'lsphp83-pear',
    'lsphp83-pecl-msgpack', 'lsphp810-apcu', 'lsphp83.x86_64', 'lsphp83-bcmath.x86_64', 'lsphp74-json.noarch',
    'lsphp83-pecl-mcrypt.x86_64', 'php83', 'php83-php-fpm.x86_64', 'php83-php-pecl-apcu.x86_64',
    'php8.1', 'php8.1-fpm', 'php8.1-mbstring', 'php8.10-curl', 'libapache2-mod-php8.1', 'libphp8.1-embed')

# What the request filter lets through and the package managers would act on.
NOT_A_PACKAGE = (
    'lsphp83-apcu openssh-server', 'lsphp83-apcu --allow-downgrades', 'lsphp83-apcu\topenssh-server',
    '"lsphp83-apcu" "openssh-server"', 'lsphp83-apcu\\ x', '-y', '--reinstall', '--', 'openssh-server',
    'sudo', 'kernel', 'libapache2-mod-security2', 'php', 'php-fpm', 'lsphp', 'lsphp8', 'xlsphp83',
    'lsphp83/../../etc/x', './lsphp83.deb', '/tmp/lsphp83.rpm', 'http://x/lsphp83.rpm', 'lsphp83=1.0',
    'lsphp83-apcu*', 'lsphp83;id', 'lsphp83$(id)', 'lsphp83`id`', 'lsphp83&id', 'lsphp83|id', "lsphp83'",
    'lsphp83\n', 'lsphp83\r', ' lsphp83', 'lsphp83 ', 'lsphp83-', 'lsphp83--x', 'LSPHP83', 'lsphp83-' + 'a' * 130,
    '', None, 83, True, ['lsphp83'], {'lsphp83': 1})


class PHPPackageNameTests(unittest.TestCase):
    def test_every_listed_package_is_accepted(self):
        for name in LISTED:
            with self.subTest(name=name):
                self.assertTrue(is_php_package(name))

    def test_anything_else_is_refused(self):
        for name in NOT_A_PACKAGE:
            with self.subTest(name=name):
                self.assertFalse(is_php_package(name))

    def test_listing_prefix_is_built_from_the_digits(self):
        self.assertEqual('lsphp83', php_package_prefix('PHP 8.3', False, False))
        self.assertEqual('lsphp83', php_package_prefix('PHP 8.3', False, True))
        self.assertEqual('php83', php_package_prefix('PHP 8.3', True, True))
        self.assertEqual('php8.3', php_package_prefix('PHP 8.3', True, False))
        for selection in OFFERED:
            for apache in (False, True):
                for rpm_family in (False, True):
                    self.assertTrue(is_php_package(php_package_prefix(selection, apache, rpm_family)))
        for value in NOT_A_SELECTION:
            with self.assertRaises(ValueError):
                php_package_prefix(value, True, False)


class ExtensionRequestTests(unittest.TestCase):
    def setUp(self):
        self.views, self.services, _ = load_views(
            ['submitExtensionRequest', 'getExtensionsInformation'],
            is_php_package=is_php_package, php_package_prefix=php_package_prefix)
        self.process = self.services['ProcessUtilities']

    def submit(self, name, action='install'):
        self.process.reset_mock()
        response = self.views.submitExtensionRequest(
            post('/managephp/submitExtensionRequest', {'extensionName': name, 'type': action}))
        return json.loads(response.content)

    def test_listed_package_reaches_the_worker_as_one_word(self):
        for action, function in (('install', 'installPHPExtension'), ('uninstall', 'unInstallPHPExtension')):
            for name in LISTED:
                with self.subTest(action=action, name=name):
                    self.assertEqual(1, self.submit(name, action)['extensionRequestStatus'])
                    self.process.popenExecutioner.assert_called_once_with(
                        '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/phpUtilities.py %s --extension %s'
                        % (function, name))
                    self.assertEqual(name, shlex.split(self.process.popenExecutioner.call_args[0][0])[-1])

    def test_other_names_start_no_worker(self):
        for action in ('install', 'uninstall'):
            for name in NOT_A_PACKAGE:
                with self.subTest(action=action, name=name):
                    result = self.submit(name, action)
                    self.assertEqual({'extensionRequestStatus': 0, 'error_message': 'Invalid PHP extension name.'},
                                     result)
                    self.assertEqual([], self.process.mock_calls)

    def test_only_the_two_request_types_of_the_page_are_acted_on(self):
        for action in ('remove', 'purge', 'install --reinstall', 'Install', '', None, 1, ['install']):
            with self.subTest(action=action):
                result = self.submit('lsphp83-apcu', action)
                self.assertEqual({'extensionRequestStatus': 0, 'error_message': 'Invalid extension request.'},
                                 result)
                self.assertEqual([], self.process.mock_calls)

    def test_non_administrators_are_still_refused_first(self):
        self.services['ACLManager'].loadedACL.return_value = {'admin': 0}
        self.assertEqual(0, self.submit('lsphp83-apcu')['extensionRequestStatus'])
        self.assertEqual([], self.process.mock_calls)

    def listing_command(self, selection, apache, distro):
        self.process.reset_mock()
        self.process.decideDistro.return_value = self.process.centos if distro == 'rpm' else 'ubuntu'
        self.services['os'].path.exists.side_effect = lambda path: path == '/etc/lsb-release' and distro != 'rpm'
        self.process.outputExecutioner.return_value = ''
        request = post('/managephp/getExtensionsInformation' + ('?apache=apache' if apache else ''),
                       {'phpSelection': selection})
        response = json.loads(self.views.getExtensionsInformation(request).content)
        commands = [call[0][0] for call in self.process.outputExecutioner.call_args_list]
        return response, commands

    def test_extension_list_searches_for_a_prefix_built_from_the_digits(self):
        for apache, distro, expected in (
                (False, 'ubuntu', ['apt list | grep lsphp83']),
                (True, 'ubuntu', ['apt list | grep php8.3']),
                (False, 'rpm', ['yum list installed', 'yum list | grep ^lsphp83 | xargs -n3 | column -t']),
                (True, 'rpm', ['yum list installed', 'yum list | grep ^php83 | xargs -n3 | column -t'])):
            with self.subTest(apache=apache, distro=distro):
                response, commands = self.listing_command('PHP 8.3', apache, distro)
                self.assertEqual(1, response['fetchStatus'], response)
                self.assertEqual(expected, commands)

    def test_extension_list_runs_nothing_for_other_text(self):
        for apache in (False, True):
            for distro in ('ubuntu', 'rpm'):
                for value in ('PHP 8.3 /etc/shadow', 'PHP 8.3;id', 'PHP 8.3\t-r', 'PHP $(id)', 'php 8.3', None, 7):
                    with self.subTest(apache=apache, distro=distro, value=value):
                        response, commands = self.listing_command(value, apache, distro)
                        self.assertEqual(0, response['fetchStatus'])
                        self.assertEqual([], commands)


if __name__ == '__main__':
    unittest.main()
