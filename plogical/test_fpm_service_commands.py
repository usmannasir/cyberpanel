"""PHP-FPM services are controlled with an argument list whose unit comes from the version's digits."""
import builtins
import contextlib
import io
from pathlib import Path
import re
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP import phpConfig
from managePHP.test_php_selection import NOT_A_SELECTION, OFFERED
from plogical.test_php_restart_marker import OLS, PHPChange, load_methods
from plogical.vhostConfs import vhostConfs

# A selection the old code turned into two unit names and an option.
SPLIT_SELECTION = 'PHP 8.3\tmulti-user.target --no-block'


def service_calls(process):
    """What was handed to the runner of the privileged worker, in order."""
    return [call[0][0] for call in process.normalExecutioner.call_args_list]


class ApacheVhostLoader:
    """The real ApacheVhost service methods with the distribution and the runner replaced."""

    def __init__(self, distro='ubuntu'):
        self.process = mock.Mock(centos='centos', cent8='cent8', debugPath='/nonexistent-debug-marker')
        self.process.decideDistro.return_value = distro
        self.process.normalExecutioner.return_value = 1
        self.temp = tempfile.TemporaryDirectory(prefix='fpm-service-test-')
        self.files = {}
        self.vhost = NS(configBasePath='/etc/apache2/sites-enabled/', serviceName='apache2',
                        sslBasePath='/etc/apache2/conf-enabled/', deletePHPPath=mock.Mock(),
                        GenerateSelfSignedSSL=mock.Mock(), DecidePHPPath=self.pool_path)
        namespace = dict(
            ProcessUtilities=self.process, ApacheVhost=self.vhost, vhostConfs=vhostConfs, logging=mock.Mock(),
            fpm_service_for_selection=phpConfig.fpm_service_for_selection,
            fpm_pool_name=phpConfig.fpm_pool_name, re=re,
            PHPManager=NS(getPHPString=lambda text: text.split()[1].replace('.', '')),
            Websites=NS(objects=NS(get=lambda domain: NS(externalApp='siteuser'))), ChildDomains=mock.Mock(),
            os=NS(path=NS(exists=lambda path: path.startswith('/etc/apache2/'))), open=self.open)
        names = ['DecideFPMServiceName', 'fpmServiceCommand', 'changePHP', 'perHostVirtualConf',
                 'perHostVirtualConfChild']
        for name, loaded in zip(names, load_methods('ApachController/ApacheVhosts.py', 'ApacheVhost',
                                                    names, namespace)):
            setattr(self.vhost, name, loaded)

    @staticmethod
    def pool_path(php, name):
        return '/etc/php/%s.%s/fpm/pool.d/%s.conf' % (php[0], php[1:], name)

    def open(self, path, mode='r'):
        target = self.files.setdefault(str(path), Path(self.temp.name) / str(len(self.files)))
        return builtins.open(target, mode)

    def text(self, path):
        return self.files[path].read_text()

    def close(self):
        self.temp.cleanup()


class FPMServiceCommandTests(unittest.TestCase):
    def loader(self, distro='ubuntu'):
        loader = ApacheVhostLoader(distro)
        self.addCleanup(loader.close)
        return loader

    def test_command_is_an_argument_list_with_the_unit_after_two_dashes(self):
        for distro, unit in (('ubuntu', 'php8.3-fpm'), ('cent8', 'php83-php-fpm'), ('centos', 'php83-php-fpm')):
            apache = self.loader(distro).vhost
            for action in ('stop', 'start', 'restart', 'reload'):
                with self.subTest(distro=distro, action=action):
                    self.assertEqual(['systemctl', action, '--', unit], apache.fpmServiceCommand(action, 'PHP 8.3'))

    def test_every_offered_version_has_a_service(self):
        ubuntu, alma = self.loader('ubuntu').vhost, self.loader('cent8').vhost
        for selection in OFFERED:
            major, minor = phpConfig.php_selection_digits(selection)
            self.assertEqual('php%s.%s-fpm' % (major, minor), ubuntu.DecideFPMServiceName(selection))
            self.assertEqual('php%s%s-php-fpm' % (major, minor), alma.DecideFPMServiceName(selection))

    def test_no_command_for_a_text_that_is_not_a_selection(self):
        for distro in ('ubuntu', 'cent8'):
            apache = self.loader(distro).vhost
            for value in NOT_A_SELECTION + (SPLIT_SELECTION,):
                with self.subTest(distro=distro, value=value):
                    with self.assertRaises(ValueError):
                        apache.fpmServiceCommand('restart', value)
                    with self.assertRaises(ValueError):
                        apache.DecideFPMServiceName(value)

    def test_only_service_actions_are_accepted(self):
        apache = self.loader().vhost
        for action in ('enable', 'mask', 'isolate', 'restart --no-block', '', None):
            with self.subTest(action=action):
                with self.assertRaisesRegex(ValueError, 'Unsupported service action'):
                    apache.fpmServiceCommand(action, 'PHP 8.3')

    def test_apache_php_change_restarts_the_selected_service_only(self):
        loader = self.loader()
        self.assertEqual(1, loader.vhost.changePHP('PHP 8.3', '/usr/local/lsws/conf/vhosts/example.test/vhost.conf'))
        self.assertEqual([['systemctl', 'stop', '--', 'php8.3-fpm'], ['systemctl', 'restart', '--', 'php8.3-fpm'],
                          'systemctl restart apache2'], service_calls(loader.process))

    def test_apache_php_change_runs_no_service_command_from_other_text(self):
        loader = self.loader()
        loader.vhost.changePHP(SPLIT_SELECTION, '/usr/local/lsws/conf/vhosts/example.test/vhost.conf')
        self.assertEqual([], service_calls(loader.process))

    def test_site_php_change_on_apache_backend_restarts_with_an_argument_list(self):
        change = PHPChange(OLS, apache_backend=True)
        self.addCleanup(change.close)
        change.apache.fpmServiceCommand.side_effect = \
            lambda action, selection: ['systemctl', action, '--', phpConfig.fpm_service_for_selection(selection, False)]
        result, output = change.run('/usr/local/lsws/conf/vhosts/example.test/vhost.conf', 'PHP 8.1')
        self.assertEqual((1, 'None'), tuple(result), output)
        self.assertEqual([['systemctl', 'restart', '--', 'php8.1-fpm']], change.events)


class ArgumentListRunnerTests(unittest.TestCase):
    def test_argument_list_reaches_the_program_unchanged(self):
        from plogical.processUtilities import ProcessUtilities
        command = ['systemctl', 'restart', '--', 'php8.3-fpm']
        for result, expected in ((0, 1), (5, 0)):
            with mock.patch('plogical.processUtilities.subprocess.call', return_value=result) as call, \
                    mock.patch('plogical.processUtilities.os.path.exists', return_value=False):
                self.assertEqual(expected, ProcessUtilities.normalExecutioner(command))
            self.assertEqual(command, call.call_args[0][0])
            self.assertNotIn('shell', call.call_args[1])

    def test_a_word_with_spaces_or_quotes_stays_one_argument(self):
        from plogical.processUtilities import ProcessUtilities
        command = ['systemctl', 'restart', '--', 'a b\tc "d" \'e\'']
        with mock.patch('plogical.processUtilities.subprocess.call', return_value=0) as call, \
                mock.patch('plogical.processUtilities.os.path.exists', return_value=False):
            ProcessUtilities.normalExecutioner(tuple(command))
        self.assertEqual(command, call.call_args[0][0])

    def test_command_lines_are_still_split_as_before(self):
        from plogical.processUtilities import ProcessUtilities
        with mock.patch('plogical.processUtilities.subprocess.call', return_value=0) as call, \
                mock.patch('plogical.processUtilities.os.path.exists', return_value=False):
            ProcessUtilities.normalExecutioner('systemctl restart apache2')
        self.assertEqual(['systemctl', 'restart', 'apache2'], call.call_args[0][0])


if __name__ == '__main__':
    unittest.main()
