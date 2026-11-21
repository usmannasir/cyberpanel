"""A failed panel upgrade returns to the installation it replaced; older releases are refused."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import softUpgrade  # noqa: E402


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        self.local = Path(self.base.name, 'local')
        self.local.mkdir()
        self.installation = self.local / 'CyberCP'
        self.installation.mkdir()
        (self.installation / 'cyberpanel_version.py').write_text("VERSION = '3.0'\nBUILD = 9\nFULL_VERSION = '3.0.9'\n")
        (self.installation / 'marker').write_text('installed before the upgrade\n')
        for name, value in (('INSTALLATION', self.installation), ('STATUS_ROOT', Path(self.base.name, 'status'))):
            patcher = mock.patch.object(softUpgrade, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.job = 'a' * 32

    def swap(self, content='new release\n'):
        """What the upgrader does when the new source goes live."""
        previous = Path(tempfile.mkdtemp(prefix='.cyberpanel-previous-', dir=str(self.local))) / 'CyberCP'
        os.rename(str(self.installation), str(previous))
        self.installation.mkdir()
        (self.installation / 'marker').write_text(content)
        return previous

    def marker(self):
        return (self.installation / 'marker').read_text()


class OlderReleaseTests(Fixture):
    def test_installed_release_is_read_without_running_it(self):
        self.assertEqual((3, 0, 9), softUpgrade.installed_order())
        (self.installation / 'cyberpanel_version.py').write_text("import os\nVERSION = os.getenv('X')\nBUILD = 9\n")
        self.assertIsNone(softUpgrade.installed_order())
        (self.installation / 'cyberpanel_version.py').unlink()
        self.assertIsNone(softUpgrade.installed_order())

    def test_only_the_installed_release_or_a_newer_one_is_accepted(self):
        for branch in ('stable', 'v3.0.9', 'v3.0.10', 'v3.1.0', 'v4.0.0', 'v3.0.10-rc1'):
            softUpgrade.refuse_older_release(branch, (3, 0, 9))
        for branch in ('v3.0.8', 'v3.0.6', 'v2.4.8', 'v1.7.4', 'v2.3.5-design', 'v3.0'):
            with self.subTest(branch), self.assertRaisesRegex(ValueError, 'older than the installed one'):
                softUpgrade.refuse_older_release(branch, (3, 0, 9))
        softUpgrade.refuse_older_release('v2.4.8', None)
        with self.assertRaisesRegex(ValueError, 'Select a stable CyberPanel release branch'):
            softUpgrade.refuse_older_release('v3.0.8; id', (3, 0, 9))

    def test_older_release_is_refused_at_once_with_its_reason(self):
        with mock.patch.object(softUpgrade.subprocess, 'Popen') as popen:
            self.assertEqual(1, softUpgrade.launch_panel_job('v2.4.8', self.job))
            popen.assert_not_called()
        status = softUpgrade.read_status(self.job)
        self.assertEqual('failed', status['state'])
        self.assertIn('older than the installed one', status['message'])
        self.assertFalse(softUpgrade.admission_path(self.job).exists())


class FailureTextTests(unittest.TestCase):
    def test_traceback_is_reduced_to_the_error_and_long_commands_keep_both_ends(self):
        packages = ', '.join("'lsphp%d-pkg%d'" % (version, number) for version in range(74, 86) for number in range(30))
        text = ('Reading package lists...\nE: Could not get lock /var/lib/dpkg/lock-frontend.\n'
                'Traceback (most recent call last):\n  File "/tmp/x/upgrade.py", line 6900, in <module>\n    main()\n'
                '  File "/tmp/x/upgrade.py", line 5747, in upgrade\n    Upgrade.installPHP73()\n'
                "subprocess.CalledProcessError: Command '['apt-get', '-y', 'install', %s]' returned non-zero exit status 100.\n" % packages)
        message = softUpgrade.readable_failure(text)
        self.assertLessEqual(len(message), 900)
        self.assertTrue(message.startswith('Reading package lists...\nE: Could not get lock /var/lib/dpkg/lock-frontend. '
                                           "subprocess.CalledProcessError: Command '['apt-get', '-y', 'install', 'lsphp74-pkg0'"))
        self.assertTrue(message.endswith("returned non-zero exit status 100."))
        self.assertNotIn('File "/tmp/x/upgrade.py"', message)
        self.assertIn(' ... ', message)

    def test_plain_error_output_is_kept(self):
        self.assertEqual('unrecognized native OLS error', softUpgrade.readable_failure('unrecognized native OLS error\n'))
        self.assertEqual('', softUpgrade.readable_failure(''))
        long_text = 'x' * 5000 + ' the end'
        self.assertTrue(softUpgrade.readable_failure(long_text).endswith(' the end'))
        self.assertLessEqual(len(softUpgrade.readable_failure(long_text)), 900)


class RestoreTests(Fixture):
    def test_only_a_tree_set_aside_by_this_upgrade_is_taken(self):
        earlier = self.swap('release of an earlier upgrade\n')
        known = softUpgrade.kept_installations()
        self.assertEqual({earlier.parent.name}, known)
        self.assertIsNone(softUpgrade.replaced_installation(known))
        # Something touching the old tree later must not make it look like this run's.
        os.utime(str(earlier.parent))
        (earlier.parent / 'touched').write_text('x')
        self.assertIsNone(softUpgrade.replaced_installation(known))
        current = self.swap()
        self.assertEqual(current, softUpgrade.replaced_installation(known))
        (self.local / '.cyberpanel-previous-empty').mkdir()
        (self.local / '.cyberpanel-previous-file').write_text('x')
        os.symlink(str(earlier.parent), str(self.local / '.cyberpanel-previous-link'))
        self.assertEqual(current, softUpgrade.replaced_installation(known))
        self.swap()
        with self.assertRaisesRegex(RuntimeError, 'More than one replaced installation'):
            softUpgrade.replaced_installation(known)

    def test_replaced_installation_is_put_back_and_the_failed_one_kept(self):
        known = softUpgrade.kept_installations()
        (self.local / '.cyberpanel-failed-old').mkdir()
        self.swap()
        self.assertEqual('new release\n', self.marker())
        self.assertTrue(softUpgrade.restore_replaced_installation(known))
        self.assertEqual('installed before the upgrade\n', self.marker())
        kept = [path for path in self.local.iterdir() if path.name.startswith('.cyberpanel-failed-')]
        self.assertEqual(1, len(kept))
        self.assertEqual('new release\n', (kept[0] / 'CyberCP' / 'marker').read_text())
        self.assertEqual([], list(self.local.glob('.cyberpanel-previous-*')))
        self.assertFalse(softUpgrade.restore_replaced_installation(known))

    def test_nothing_changes_when_no_tree_was_set_aside(self):
        self.assertFalse(softUpgrade.restore_replaced_installation(softUpgrade.kept_installations()))
        self.assertEqual('installed before the upgrade\n', self.marker())
        self.assertEqual(['CyberCP'], os.listdir(str(self.local)))

    def test_installation_stays_in_place_when_the_old_tree_cannot_be_moved_back(self):
        known = softUpgrade.kept_installations()
        self.swap()
        rename = os.rename

        def failing(source, target):
            if '.cyberpanel-previous-' in source:
                raise OSError('device busy')
            return rename(source, target)
        with mock.patch.object(softUpgrade.os, 'rename', failing):
            with self.assertRaises(OSError):
                softUpgrade.restore_replaced_installation(known)
        self.assertEqual('new release\n', self.marker())


class PanelJobTests(Fixture):
    def job_result(self, run, activate):
        with mock.patch.object(softUpgrade, 'run', side_effect=run), \
                mock.patch.object(softUpgrade, 'activate_panel_runtime', side_effect=activate) as activation, \
                mock.patch.object(softUpgrade.sys, 'stderr'):
            code = softUpgrade.run_panel_job('v3.0.9', self.job)
        return code, softUpgrade.read_status(self.job), activation

    def test_failure_after_the_new_source_went_live_returns_to_the_old_one(self):
        self.older = self.swap('installed before the upgrade\n')  # an earlier upgrade's kept tree stays untouched

        def run(*arguments, **options):
            self.swap()
            raise RuntimeError('Upgrade exited with code 1. MariaDB is unavailable')
        code, status, activation = self.job_result(run, lambda fd: {'http_status': 200})
        self.assertEqual((1, 'failed'), (code, status['state']))
        self.assertEqual('Upgrade exited with code 1. MariaDB is unavailable '
                         'The previous version was put back and the panel restarted.', status['message'])
        self.assertEqual('installed before the upgrade\n', self.marker())
        self.assertEqual(1, activation.call_count)
        self.assertEqual('installed before the upgrade\n', (self.older / 'marker').read_text())

    def test_failure_before_the_new_source_went_live_leaves_the_panel_alone(self):
        def run(*arguments, **options):
            raise RuntimeError('Upgrade exited with code 1. Failed to clone CyberPanel repository')
        code, status, activation = self.job_result(run, lambda fd: {'http_status': 200})
        self.assertEqual('Upgrade exited with code 1. Failed to clone CyberPanel repository', status['message'])
        activation.assert_not_called()
        self.assertEqual('installed before the upgrade\n', self.marker())

    def test_panel_that_does_not_come_back_on_the_new_release_gets_the_old_one(self):
        attempts = []

        def activate(fd):
            attempts.append(self.marker())
            if len(attempts) == 1:
                raise RuntimeError('Panel runtime activation failed: The restarted panel did not return its login page.')
            return {'http_status': 200}
        code, status, activation = self.job_result(lambda *a, **k: self.swap() and 0, activate)
        self.assertEqual((1, 'failed'), (code, status['state']))
        self.assertEqual(['new release\n', 'installed before the upgrade\n'], attempts)
        self.assertIn('did not return its login page. The previous version was put back and the panel restarted.',
                      status['message'])

    def test_report_says_so_when_the_old_release_does_not_start_either(self):
        def activate(fd):
            raise RuntimeError('Panel runtime activation failed: lscpd is not active.')
        code, status, activation = self.job_result(lambda *a, **k: self.swap() and 0, activate)
        self.assertEqual(2, activation.call_count)
        self.assertIn('The previous version was put back, but the panel did not restart cleanly', status['message'])
        self.assertEqual('installed before the upgrade\n', self.marker())

    def test_report_says_so_when_the_old_release_cannot_be_put_back(self):
        def run(*arguments, **options):
            self.swap()
            raise RuntimeError('Upgrade exited with code 1.')
        with mock.patch.object(softUpgrade, 'restore_replaced_installation', side_effect=OSError('device busy')):
            code, status, activation = self.job_result(run, lambda fd: {'http_status': 200})
        self.assertEqual('Upgrade exited with code 1. The previous version could not be put back: device busy',
                         status['message'])
        activation.assert_not_called()

    def test_successful_upgrade_is_untouched(self):
        code, status, activation = self.job_result(lambda *a, **k: self.swap() and 0, lambda fd: {'http_status': 200})
        self.assertEqual((0, 'complete'), (code, status['state']))
        self.assertEqual('new release\n', self.marker())
        self.assertEqual(1, len(list(self.local.glob('.cyberpanel-previous-*'))))


if __name__ == '__main__':
    unittest.main()
