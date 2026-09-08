"""Advanced PHP saves use the selected runtime, with no host service calls."""

import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile
import types
import unittest
from unittest import mock


class AdvancedPHPRestartTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='php-save-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.destination = self.root / 'php.ini'
        self.destination.write_text('memory_limit = 128M\n')
        self.staged = self.root / 'staged.ini'
        self.content = '; site PHP configuration\nmemory_limit = 256M\n'
        self.staged.write_text(self.content)
        self.events = []
        self.restart_result = 1
        self.handles = []
        self.addCleanup(lambda: [handle.close() for handle in self.handles])

        self.process = mock.Mock()
        self.process.centos = 'centos'
        self.process.cent8 = 'cent8'
        self.process.decideDistro.return_value = 'ubuntu'
        self.process.executioner.side_effect = lambda command: self.events.append(('marker', command))
        self.process.normalExecutioner.side_effect = self._restart_fpm
        self.install = mock.Mock()
        self.install.reStartLiteSpeed.side_effect = lambda: self.events.append(('litespeed', None))
        self.logger = mock.Mock()

        package = types.ModuleType('plogical')
        package.__path__ = []
        stubs = {'plogical': package}
        for name, attribute, value in (
                ('plogical.CyberCPLogFileWriter', 'CyberCPLogFileWriter', self.logger),
                ('plogical.installUtilities', 'installUtilities', self.install),
                ('plogical.mailUtilities', 'mailUtilities', mock.Mock()),
                ('plogical.processUtilities', 'ProcessUtilities', self.process),
                ('ApachController.ApacheVhosts', 'ApacheVhost', mock.Mock()),
                ('django.urls', 'reverse', mock.Mock())):
            module = types.ModuleType(name)
            setattr(module, attribute, value)
            stubs[name] = module
            if name.startswith('plogical.'):
                setattr(package, name.split('.')[-1], module)

        source = Path(__file__).with_name('phpUtilities.py')
        spec = importlib.util.spec_from_file_location('_php_advanced_save_under_test', source)
        self.module = importlib.util.module_from_spec(spec)
        with mock.patch.dict('sys.modules', stubs):
            spec.loader.exec_module(self.module)

    def _restart_fpm(self, command):
        self.events.append(('fpm', command))
        return self.restart_result

    def run_save(self, selected_path, distro='ubuntu'):
        self.process.decideDistro.return_value = distro
        real_open = open

        def fixture_open(path, mode='r', *args, **kwargs):
            if str(path) == selected_path:
                handle = real_open(self.destination, mode, *args, **kwargs)
            elif str(path) == str(self.staged):
                handle = real_open(self.staged, mode, *args, **kwargs)
            else:
                raise AssertionError('Unexpected file access: %s' % path)
            self.handles.append(handle)
            return handle

        output = io.StringIO()
        with mock.patch.object(self.module, 'open', side_effect=fixture_open, create=True), \
                mock.patch.object(self.module.os.path, 'exists', return_value=False), \
                contextlib.redirect_stdout(output):
            self.module.phpUtilities.savePHPConfigAdvance(selected_path, str(self.staged))
        return output.getvalue()

    def assert_saved(self, selected_path, distro, expected_service=None):
        output = self.run_save(selected_path, distro)
        self.assertEqual(self.content, self.destination.read_text())
        self.assertEqual('1,None\n', output)
        self.install.reStartLiteSpeed.assert_called_once_with()
        if expected_service is None:
            self.process.normalExecutioner.assert_not_called()
        else:
            self.process.normalExecutioner.assert_called_once_with('systemctl restart ' + expected_service)
            self.assertLess(self.events.index(('litespeed', None)),
                            self.events.index(('fpm', 'systemctl restart ' + expected_service)))

    def test_el_lsapi_save_does_not_restart_fpm(self):
        self.assert_saved('/usr/local/lsws/lsphp83/etc/php.ini', 'cent8')

    def test_ubuntu_lsapi_save_does_not_restart_fpm(self):
        self.assert_saved('/usr/local/lsws/lsphp83/etc/php/8.3/litespeed/php.ini', 'ubuntu')

    def test_el_remi_save_restarts_selected_fpm(self):
        self.assert_saved('/etc/opt/remi/php83/php.ini', 'cent8', 'php83-php-fpm')

    def test_ubuntu_save_restarts_selected_fpm(self):
        self.assert_saved('/etc/php/8.3/fpm/php.ini', 'ubuntu', 'php8.3-fpm')

    def assert_restart_failure(self, selected_path, distro, service):
        self.restart_result = 0
        output = self.run_save(selected_path, distro)
        self.assertEqual(self.content, self.destination.read_text())
        self.assertNotIn('1,None', output)
        self.assertTrue(output.startswith('0,'), output)
        self.assertIn('saved', output)
        self.assertIn(service, output)
        self.logger.writeToFile.assert_called_once()

    def test_el_fpm_restart_failure_is_not_reported_as_success(self):
        self.assert_restart_failure('/etc/opt/remi/php83/php.ini', 'cent8', 'php83-php-fpm')

    def test_ubuntu_fpm_restart_failure_is_not_reported_as_success(self):
        self.assert_restart_failure('/etc/php/8.3/fpm/php.ini', 'ubuntu', 'php8.3-fpm')

    def test_write_failure_does_not_restart_any_service(self):
        output = io.StringIO()
        with mock.patch.object(self.module, 'open', side_effect=PermissionError('fixture write denied'), create=True), \
                contextlib.redirect_stdout(output):
            self.module.phpUtilities.savePHPConfigAdvance('/etc/php/8.3/fpm/php.ini', str(self.staged))
        self.assertEqual('memory_limit = 128M\n', self.destination.read_text())
        self.assertTrue(output.getvalue().startswith('0,'))
        self.install.reStartLiteSpeed.assert_not_called()
        self.process.normalExecutioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
