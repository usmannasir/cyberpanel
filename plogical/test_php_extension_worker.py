"""The extension worker names one checked PHP package to the package manager, as one argument."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock

from managePHP.test_php_packages import LISTED, NOT_A_PACKAGE


def load_php_utilities(distro='ubuntu'):
    """plogical/phpUtilities.py as a module, with the server and every other panel module replaced."""
    process = mock.Mock(centos='centos', cent8='cent8', debugPath='/nonexistent-debug-marker')
    process.decideDistro.return_value = distro
    process.normalExecutioner.return_value = 1
    services = types.SimpleNamespace(process=process, install=mock.Mock(), logger=mock.Mock(),
                                     mail=mock.Mock(), apache=mock.Mock())
    package = types.ModuleType('plogical')
    package.__path__ = []
    stubs = {'plogical': package}
    for name, attribute, value in (
            ('plogical.CyberCPLogFileWriter', 'CyberCPLogFileWriter', services.logger),
            ('plogical.installUtilities', 'installUtilities', services.install),
            ('plogical.mailUtilities', 'mailUtilities', services.mail),
            ('plogical.processUtilities', 'ProcessUtilities', process),
            ('ApachController.ApacheVhosts', 'ApacheVhost', services.apache),
            ('django.urls', 'reverse', mock.Mock())):
        module = types.ModuleType(name)
        setattr(module, attribute, value)
        stubs[name] = module
        if name.startswith('plogical.'):
            setattr(package, name.split('.')[-1], module)
    source = Path(__file__).with_name('phpUtilities.py')
    spec = importlib.util.spec_from_file_location('_php_utilities_under_test', source)
    module = importlib.util.module_from_spec(spec)
    with mock.patch.dict('sys.modules', stubs):
        spec.loader.exec_module(module)
    return module, services


class ExtensionWorkerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='php-extension-test-')
        self.addCleanup(self.temp.cleanup)
        self.log = Path(self.temp.name) / 'phpExtensionRequestLog'

    def worker(self, distro):
        module, services = load_php_utilities(distro)
        module.phpUtilities.installLogPath = str(self.log)
        return module, services

    def run_worker(self, distro, function, name):
        module, services = self.worker(distro)
        with mock.patch.object(module.subprocess, 'call', return_value=0) as call, \
                contextlib.redirect_stdout(io.StringIO()):
            result = getattr(module.phpUtilities, function)(name, name)
        return result, call, services

    def test_package_manager_gets_the_name_as_one_argument_after_two_dashes(self):
        expected = {
            ('ubuntu', 'installPHPExtension'): ['sudo', 'apt-get', 'install', '-y', '--'],
            ('ubuntu', 'unInstallPHPExtension'): ['sudo', 'apt-get', 'remove', '-y', '--'],
            ('cent8', 'installPHPExtension'): ['sudo', 'yum', 'install', '-y', '--'],
            ('cent8', 'unInstallPHPExtension'): ['sudo', 'rpm', '--nodeps', '-e', '-v', '--'],
        }
        for (distro, function), words in expected.items():
            for name in LISTED:
                with self.subTest(distro=distro, function=function, name=name):
                    result, call, services = self.run_worker(distro, function, name)
                    self.assertEqual(1, result)
                    self.assertEqual(words + [name], call.call_args[0][0])
                    self.assertNotIn('shell', call.call_args[1])
                    services.install.reStartLiteSpeed.assert_called_once_with()
            done = 'PHP Extension Installed.' if function == 'installPHPExtension' else 'PHP Extension Removed.'
            self.assertIn(done, self.log.read_text())

    def test_other_names_run_no_package_manager_and_end_the_page_wait(self):
        endings = {'installPHPExtension': 'Can not be installed.\n',
                   'unInstallPHPExtension': 'Can not un-install Extension.\n'}
        for distro in ('ubuntu', 'cent8'):
            for function, ending in endings.items():
                for name in NOT_A_PACKAGE:
                    with self.subTest(distro=distro, function=function, name=name):
                        result, call, services = self.run_worker(distro, function, name)
                        self.assertEqual(0, result)
                        call.assert_not_called()
                        self.assertEqual(ending, self.log.read_text())
                        # The web server is not restarted for a refused request.
                        services.install.reStartLiteSpeed.assert_not_called()

    def test_command_builder_refuses_names_and_actions_itself(self):
        module, _ = self.worker('ubuntu')
        for name in NOT_A_PACKAGE:
            with self.assertRaisesRegex(ValueError, 'Invalid PHP extension name'):
                module.phpUtilities.packageCommand('install', name)
        for action in ('purge', 'install -y', '', None):
            with self.assertRaisesRegex(ValueError, 'Unsupported package action'):
                module.phpUtilities.packageCommand(action, 'lsphp83-apcu')


if __name__ == '__main__':
    unittest.main()
