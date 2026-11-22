"""The php.ini workers: only a managed php.ini is written, from checked values, in one step."""
import contextlib
import io
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest import mock

from managePHP import phpConfig
from managePHP.test_php_ini_settings import REFUSED_VALUES
from plogical.test_php_extension_worker import load_php_utilities

LSPHP_INI = '/usr/local/lsws/lsphp83/etc/php/8.3/litespeed/php.ini'
FPM_INI = '/etc/php/8.3/fpm/php.ini'
BEFORE = b'[PHP]\n; memory_limit = 1\nmemory_limit = 128M\ndisplay_errors = On\n'
VALUES = dict(allow_url_fopen='1', display_errors='0', file_uploads='1', allow_url_include='0',
              memory_limit='256M', max_execution_time='30', upload_max_filesize='64M', max_input_time='-1',
              post_max_size='128M')
ORDER = ('allow_url_fopen', 'display_errors', 'file_uploads', 'allow_url_include', 'memory_limit',
         'max_execution_time', 'upload_max_filesize', 'max_input_time', 'post_max_size')


class Worker:
    """plogical/phpUtilities.py with the server replaced; the php.ini itself is kept in memory."""

    def __init__(self, test, distro='ubuntu'):
        self.module, self.services = load_php_utilities(distro)
        self.utilities = self.module.phpUtilities
        self.files = {LSPHP_INI: BEFORE, FPM_INI: BEFORE}
        self.replaced = []
        self.links = {}
        self.services.apache.DecidePHPPathforManager.side_effect = \
            lambda apache, selection: phpConfig.managed_ini_path(selection, apache == 1, distro != 'ubuntu')
        self.services.apache.fpmServiceCommand.side_effect = \
            lambda action, selection: ['systemctl', action, '--', phpConfig.fpm_service_for_selection(selection, False)]
        self.staging = tempfile.TemporaryDirectory(prefix='php-ini-worker-test-')
        test.addCleanup(self.staging.cleanup)
        self.utilities.stagingDirectory = self.staging.name
        for patcher in (
                mock.patch.object(self.utilities, 'readIniFile', side_effect=lambda path: self.files[path]),
                mock.patch.object(self.utilities, 'replaceIniFile', side_effect=self.replace),
                mock.patch.object(self.module.os.path, 'realpath', side_effect=lambda path: self.links.get(path, path)),
                mock.patch.object(self.module.os.path, 'exists', return_value=False)):
            patcher.start()
            test.addCleanup(patcher.stop)

    def replace(self, path, content):
        self.replaced.append(path)
        self.files[path] = content

    def stage(self, content, name='phpini.abc123_x'):
        path = os.path.join(self.staging.name, name)
        with open(path, 'wb') as staged:
            staged.write(content)
        return path

    def save_basic(self, selection='PHP 8.3', apache='0', **changes):
        values = dict(VALUES)
        values.update(changes)
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.utilities.savePHPConfigBasic(selection, *([values[name] for name in ORDER] + [apache]))
        return output.getvalue()

    def save_advanced(self, path, staged):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            self.utilities.savePHPConfigAdvance(path, staged)
        return output.getvalue()

    def untouched(self):
        return (not self.replaced and self.services.process.mock_calls == [] and
                self.services.install.mock_calls == [])


class BasicSaveWorkerTests(unittest.TestCase):
    def test_checked_values_replace_assignments_only(self):
        worker = Worker(self)
        self.assertEqual('1,None\n', worker.save_basic())
        self.assertEqual([LSPHP_INI], worker.replaced)
        text = worker.files[LSPHP_INI].decode()
        self.assertTrue(text.startswith('[PHP]\n; memory_limit = 1\nmemory_limit = 256M\ndisplay_errors = Off\n'))
        self.assertIn('\npost_max_size = 128M\n', text)
        worker.services.process.normalExecutioner.assert_not_called()

    def test_apache_save_writes_the_fpm_file_and_restarts_its_service(self):
        worker = Worker(self)
        self.assertEqual('1,None\n', worker.save_basic(apache='1'))
        self.assertEqual([FPM_INI], worker.replaced)
        worker.services.process.normalExecutioner.assert_called_once_with(
            ['systemctl', 'restart', '--', 'php8.3-fpm'])

    def test_a_refused_value_changes_nothing_and_restarts_nothing(self):
        for directive in phpConfig.PHP_SIZES + phpConfig.PHP_SECONDS:
            for value in REFUSED_VALUES:
                with self.subTest(directive=directive, value=value):
                    worker = Worker(self)
                    output = worker.save_basic(**{directive: value})
                    self.assertTrue(output.startswith('0,Invalid value for %s' % directive), output)
                    self.assertTrue(worker.untouched())
        for value in ('allow_url_fopen = On', 'On', 'On\rauto_prepend_file = /x', '2', None):
            with self.subTest(switch=value):
                worker = Worker(self)
                self.assertTrue(worker.save_basic(allow_url_fopen=value).startswith('0,'))
                self.assertTrue(worker.untouched())

    def test_other_selections_and_apache_values_change_nothing(self):
        for selection, apache in (('PHP 8.3 /etc/shadow', '1'), ('PHP ../../etc', '1'), ('8.3/../../x y', '1'),
                                  ('PHP 8.3', '2'), ('PHP 8.3', 'yes'), ('PHP 8.3', None), ('PHP 8.3', '1 1')):
            with self.subTest(selection=selection, apache=apache):
                worker = Worker(self)
                self.assertTrue(worker.save_basic(selection, apache).startswith('0,'))
                self.assertTrue(worker.untouched())

    def test_a_link_in_place_of_the_file_is_not_written_through(self):
        worker = Worker(self)
        worker.links[LSPHP_INI] = '/etc/shadow'
        self.assertTrue(worker.save_basic().startswith('0,This is not a PHP configuration file'))
        self.assertTrue(worker.untouched())


class AdvancedSaveWorkerTests(unittest.TestCase):
    def test_staged_text_replaces_a_managed_file(self):
        for path in (LSPHP_INI, FPM_INI):
            with self.subTest(path=path):
                worker = Worker(self)
                worker.services.process.normalExecutioner.return_value = 1
                self.assertEqual('1,None\n', worker.save_advanced(path, worker.stage(b'memory_limit = 64M\n')))
                self.assertEqual(b'memory_limit = 64M\n', worker.files[path])

    def test_other_destinations_are_refused_before_anything_happens(self):
        for path in ('/etc/shadow', '/etc/cron.d/x', '/etc/php/8.3/fpm/php.ini/../../../../cron.d/x',
                     '/etc/php/8.3/fpm/pool.d/www.conf', '/usr/local/lsws/conf/httpd_config.conf',
                     '/root/.ssh/authorized_keys', '/etc/php/8.3/cli/php.ini', 'php.ini', '', None):
            with self.subTest(path=path):
                worker = Worker(self)
                output = worker.save_advanced(path, worker.stage(b'x = y\n'))
                self.assertTrue(output.startswith('0,This is not a PHP configuration file'), output)
                self.assertTrue(worker.untouched())

    def test_a_managed_name_that_leads_elsewhere_is_refused(self):
        worker = Worker(self)
        worker.links[FPM_INI] = '/etc/cron.d/x'
        self.assertTrue(worker.save_advanced(FPM_INI, worker.stage(b'x = y\n')).startswith('0,This is not'))
        self.assertTrue(worker.untouched())

    def test_only_a_staged_file_of_the_panel_is_read(self):
        worker = Worker(self)
        outside = tempfile.NamedTemporaryFile(prefix='phpini.')
        self.addCleanup(outside.close)
        link = os.path.join(worker.staging.name, 'phpini.link')
        os.symlink(outside.name, link)
        for staged in ('/etc/shadow', outside.name, os.path.join(worker.staging.name, 'other'),
                       os.path.join(worker.staging.name, 'sub', 'phpini.abc'), worker.staging.name, link, '', None):
            with self.subTest(staged=staged):
                output = worker.save_advanced(FPM_INI, staged)
                self.assertTrue(output.startswith('0,'), output)
                self.assertTrue(worker.untouched())
                self.assertEqual(BEFORE, worker.files[FPM_INI])


class ReplaceIniFileTests(unittest.TestCase):
    """The real replacement, on a real directory."""

    def setUp(self):
        self.module, _ = load_php_utilities()
        self.temp = tempfile.TemporaryDirectory(prefix='php-ini-replace-test-')
        self.addCleanup(self.temp.cleanup)
        self.ini = Path(self.temp.name) / 'php.ini'
        self.ini.write_bytes(BEFORE)
        os.chmod(str(self.ini), 0o640)

    def test_file_is_replaced_by_a_new_one_with_the_same_mode(self):
        before = os.stat(str(self.ini))
        self.module.phpUtilities.replaceIniFile(str(self.ini), b'memory_limit = 64M\n')
        after = os.stat(str(self.ini))
        self.assertEqual(b'memory_limit = 64M\n', self.ini.read_bytes())
        self.assertNotEqual(before.st_ino, after.st_ino)
        self.assertEqual(0o640, stat.S_IMODE(after.st_mode))
        self.assertEqual((before.st_uid, before.st_gid), (after.st_uid, after.st_gid))
        self.assertEqual(['php.ini'], os.listdir(self.temp.name))

    def test_a_failed_write_leaves_the_present_file(self):
        with mock.patch('os.replace', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.module.phpUtilities.replaceIniFile(str(self.ini), b'half')
        self.assertEqual(BEFORE, self.ini.read_bytes())
        self.assertEqual(['php.ini'], os.listdir(self.temp.name))

    def test_managed_path_check_uses_the_real_location(self):
        utilities = self.module.phpUtilities
        self.assertEqual(FPM_INI, utilities.managedIniPath(FPM_INI))
        with mock.patch.object(self.module.os.path, 'realpath', return_value='/etc/shadow'):
            with self.assertRaises(ValueError):
                utilities.managedIniPath(FPM_INI)
        with self.assertRaises(ValueError):
            utilities.managedIniPath(str(self.ini))


class ManagedIniLocationTests(unittest.TestCase):
    """Where a managed php.ini may really be: a small tree of real directories, files and links.

    The tree stands for the root of the file system. The worker's questions
    about links are answered from it, so the rule is tried on real links.
    """

    def setUp(self):
        self.module, _ = load_php_utilities()
        self.utilities = self.module.phpUtilities
        self.temp = tempfile.TemporaryDirectory(prefix='php-ini-location-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = os.path.realpath(self.temp.name)
        for patcher in (
                mock.patch.object(self.module.os.path, 'realpath', side_effect=self.realpath),
                mock.patch.object(self.module.os.path, 'islink', side_effect=self.islink)):
            patcher.start()
            self.addCleanup(patcher.stop)

    real_realpath = staticmethod(os.path.realpath)
    real_islink = staticmethod(os.path.islink)

    def realpath(self, path):
        real = self.real_realpath(self.root + path)
        return real[len(self.root):] if real.startswith(self.root + '/') else real

    def islink(self, path):
        return self.real_islink(self.root + path)

    def directory(self, path):
        os.makedirs(self.root + path)

    def file(self, path):
        if not os.path.isdir(os.path.dirname(self.root + path)):
            os.makedirs(os.path.dirname(self.root + path))
        with open(self.root + path, 'w') as handle:
            handle.write('memory_limit = 128M\n')

    def link(self, target, path):
        if not os.path.isdir(os.path.dirname(self.root + path)):
            os.makedirs(os.path.dirname(self.root + path))
        os.symlink(self.root + target, self.root + path)

    def assert_refused(self, path):
        with self.assertRaisesRegex(ValueError, 'not a PHP configuration file that the panel manages'):
            self.utilities.managedIniPath(path)

    def test_a_plain_file_is_accepted(self):
        for path in (FPM_INI, LSPHP_INI, '/usr/local/lsws/lsphp83/etc/php.ini', '/etc/opt/remi/php83/php.ini'):
            with self.subTest(path=path):
                self.file(path)
                self.assertEqual(path, self.utilities.managedIniPath(path))

    def test_a_base_directory_that_is_a_link_to_another_disk_is_accepted(self):
        for base, path in (('/etc/php', FPM_INI), ('/usr/local/lsws', LSPHP_INI),
                           ('/usr/local/lsws', '/usr/local/lsws/lsphp83/etc/php.ini'),
                           ('/etc/opt/remi', '/etc/opt/remi/php83/php.ini')):
            with self.subTest(path=path):
                if not os.path.lexists(self.root + base):
                    disk = '/mnt/disk%d' % len(os.listdir(self.root))
                    self.directory(disk)
                    self.link(disk, base)
                self.file(path)
                self.assertTrue(self.real_islink(self.root + base))
                self.assertEqual(path, self.utilities.managedIniPath(path))

    def test_a_link_below_the_base_directory_is_refused(self):
        self.file('/elsewhere/8.3/fpm/php.ini')
        self.link('/elsewhere/8.3', '/etc/php/8.3')
        self.assert_refused(FPM_INI)
        self.file('/elsewhere/fpm/php.ini')
        self.directory('/etc/php/8.2')
        self.link('/elsewhere/fpm', '/etc/php/8.2/fpm')
        self.assert_refused('/etc/php/8.2/fpm/php.ini')
        self.file('/elsewhere/lsphp83/etc/php.ini')
        self.link('/elsewhere/lsphp83', '/usr/local/lsws/lsphp83')
        self.assert_refused('/usr/local/lsws/lsphp83/etc/php.ini')

    def test_a_link_below_a_linked_base_directory_is_refused(self):
        self.directory('/mnt/disk2')
        self.link('/mnt/disk2', '/etc/php')
        self.file('/elsewhere/8.3/fpm/php.ini')
        self.link('/elsewhere/8.3', '/mnt/disk2/8.3')
        self.assert_refused(FPM_INI)

    def test_a_file_that_is_a_link_is_refused(self):
        self.file('/outside/file')
        self.link('/outside/file', FPM_INI)
        self.assert_refused(FPM_INI)
        # Also when it leads to a file beside it, or back to itself.
        self.file('/etc/opt/remi/php83/php.ini.real')
        self.link('/etc/opt/remi/php83/php.ini.real', '/etc/opt/remi/php83/php.ini')
        self.assert_refused('/etc/opt/remi/php83/php.ini')
        self.link(LSPHP_INI, LSPHP_INI)
        self.assert_refused(LSPHP_INI)

    def test_a_path_without_a_managed_form_is_refused_whatever_is_there(self):
        for path in ('/etc/php/8.3/cli/php.ini', '/etc/php/8.3/fpm/pool.d/www.conf', '/etc/php/php.ini',
                     '/usr/local/lsws/conf/httpd_config.conf', '/etc/opt/remi/php83/php-fpm.conf'):
            with self.subTest(path=path):
                self.file(path)
                self.assert_refused(path)


if __name__ == '__main__':
    unittest.main()
