"""An upgrade the server starts itself runs and installs one exact, signed commit."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import softUpgrade  # noqa: E402


def git(directory, *arguments):
    return subprocess.run(['git', '-C', str(directory), '-c', 'user.name=t', '-c', 'user.email=t@example.com']
                          + list(arguments), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True).stdout.strip()


class VerifiedSourceTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        self.origin = Path(self.base.name, 'origin')
        self.origin.mkdir()
        git(self.origin, 'init', '--quiet', '--initial-branch=v3.0.10')
        # GitHub serves any commit reachable from a branch.
        git(self.origin, 'config', 'uploadpack.allowReachableSHA1InWant', 'true')
        (self.origin / 'plogical').mkdir()
        (self.origin / 'plogical' / 'upgrade.py').write_text('signed = True\n')
        os.symlink('/etc/hostname', str(self.origin / 'link'))
        git(self.origin, 'add', '.')
        git(self.origin, 'commit', '--quiet', '-m', 'signed release')
        self.signed = git(self.origin, 'rev-parse', 'HEAD')
        (self.origin / 'plogical' / 'upgrade.py').write_text('signed = False  # pushed after signing\n')
        git(self.origin, 'commit', '--quiet', '-am', 'later, unsigned')
        self.later = git(self.origin, 'rev-parse', 'HEAD')
        patcher = mock.patch.object(softUpgrade, 'REPOSITORY', 'file://' + str(self.origin))
        patcher.start()
        self.addCleanup(patcher.stop)

    def checkout(self):
        directory = Path(self.base.name, 'checkout-%d' % len(os.listdir(self.base.name)))
        directory.mkdir()
        return str(directory)

    def test_files_come_from_the_named_commit_not_from_the_branch(self):
        read = softUpgrade.verified_source(self.checkout(), self.signed)
        self.assertEqual(b'signed = True\n', read('plogical/upgrade.py'))
        self.assertIn(b'pushed after signing', softUpgrade.verified_source(self.checkout(), self.later)('plogical/upgrade.py'))

    def test_only_plain_files_of_the_commit_are_read(self):
        read = softUpgrade.verified_source(self.checkout(), self.signed)
        for path in ('link', 'plogical', 'missing.py'):
            with self.subTest(path), self.assertRaisesRegex(ValueError, 'Missing release file'):
                read(path)

    def test_a_commit_the_repository_does_not_have_is_refused(self):
        with self.assertRaises(subprocess.CalledProcessError):
            softUpgrade.verified_source(self.checkout(), 'f' * 40)
        for commit in ('v3.0.10', self.signed[:12], self.signed.upper(), self.signed + ' --upload-pack=id', ''):
            with self.subTest(commit), self.assertRaisesRegex(ValueError, 'Invalid release commit'):
                softUpgrade.verified_source(self.checkout(), commit)


class PinnedRunTests(unittest.TestCase):
    def run_upgrade(self, **arguments):
        staged, launched = [], []

        def stage(stage, revision, read=None):
            staged.append((revision, read))
            (stage / 'upgrade.py').write_text('')

        class Finished:
            pid = 0

            def wait(self, timeout=None):
                return 0

        def launch(command, **options):
            launched.append((command, options))
            return Finished()

        with mock.patch.object(softUpgrade, 'stage_release', stage), \
                mock.patch.object(softUpgrade, 'verified_source', return_value='reader') as source, \
                mock.patch.object(softUpgrade, 'resolve_release', return_value='1' * 40) as resolve, \
                mock.patch.object(softUpgrade.subprocess, 'Popen', launch):
            softUpgrade.run('v3.0.10', **arguments)
        return staged, launched, source, resolve

    def test_signed_commit_is_staged_from_verified_source_and_passed_to_the_upgrader(self):
        commit = 'a' * 40
        staged, launched, source, resolve = self.run_upgrade(commit=commit)
        self.assertEqual([(commit, 'reader')], staged)
        self.assertEqual(commit, source.call_args[0][1])
        resolve.assert_not_called()
        command, options = launched[0]
        self.assertEqual('SoftUpgrade,v3.0.10', command[-1])
        self.assertEqual(commit, options['env']['CYBERPANEL_UPGRADE_COMMIT'])
        self.assertEqual(os.environ.get('PATH'), options['env'].get('PATH'))

    def test_an_upgrade_from_the_panel_page_is_unchanged(self):
        staged, launched, source, resolve = self.run_upgrade()
        self.assertEqual([('1' * 40, None)], staged)
        source.assert_not_called()
        environment = launched[0][1]['env']
        self.assertNotIn('CYBERPANEL_UPGRADE_COMMIT', environment)
        # A stalled GitHub transfer fails instead of waiting; the upgrader reports skipped steps.
        self.assertEqual('60', environment['GIT_HTTP_LOW_SPEED_TIME'])
        self.assertTrue(environment['CYBERPANEL_UPGRADE_REPORT'].endswith('report.json'))
        self.assertTrue(launched[0][1]['start_new_session'])

    def test_branch_is_checked_before_anything_is_fetched(self):
        with mock.patch.object(softUpgrade, 'verified_source') as source:
            with self.assertRaises(ValueError):
                softUpgrade.run('main; id', commit='a' * 40)
            source.assert_not_called()


class UnattendedTests(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        self.local = Path(self.base.name, 'local')
        self.installation = self.local / 'CyberCP'
        self.installation.mkdir(parents=True)
        (self.installation / 'marker').write_text('installed before the update\n')
        for name, value in (('STATUS_ROOT', Path(self.base.name, 'status')), ('INSTALLATION', self.installation)):
            patcher = mock.patch.object(softUpgrade, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.job = 'a' * 32

    def test_completed_upgrade_is_recorded_after_the_panel_restarted(self):
        order = []
        with mock.patch.object(softUpgrade, 'run', side_effect=lambda *a, **k: order.append(('run', a, k['commit']))), \
                mock.patch.object(softUpgrade, 'activate_panel_runtime',
                                  side_effect=lambda fd: order.append('activate') or {'http_status': 200}):
            self.assertEqual({'http_status': 200}, softUpgrade.run_unattended('v3.0.10', 'b' * 40, self.job))
        self.assertEqual([('run', ('v3.0.10',), 'b' * 40), 'activate'], order)
        self.assertEqual('complete', softUpgrade.read_status(self.job)['state'])

    def test_failure_is_recorded_and_raised(self):
        with mock.patch.object(softUpgrade, 'run', side_effect=RuntimeError('Upgrade exited with code 1. No space left')), \
                mock.patch.object(softUpgrade, 'activate_panel_runtime') as activate:
            with self.assertRaisesRegex(RuntimeError, 'No space left'):
                softUpgrade.run_unattended('v3.0.10', 'b' * 40, self.job)
            activate.assert_not_called()
        self.assertEqual({'state': 'failed', 'message': 'Upgrade exited with code 1. No space left'},
                         softUpgrade.read_status(self.job))

    def test_failed_update_returns_to_the_replaced_installation(self):
        def run(*arguments, **options):
            previous = Path(tempfile.mkdtemp(prefix='.cyberpanel-previous-', dir=str(self.local))) / 'CyberCP'
            os.rename(str(self.installation), str(previous))
            self.installation.mkdir()
            (self.installation / 'marker').write_text('half-installed release\n')
            raise RuntimeError('Upgrade exited with code 1. MariaDB is unavailable')
        with mock.patch.object(softUpgrade, 'run', side_effect=run), \
                mock.patch.object(softUpgrade, 'activate_panel_runtime', return_value={'http_status': 200}) as activate:
            with self.assertRaisesRegex(RuntimeError, 'The previous version was put back and the panel restarted'):
                softUpgrade.run_unattended('v3.0.10', 'b' * 40, self.job)
        activate.assert_called_once()
        self.assertEqual('installed before the update\n', (self.installation / 'marker').read_text())
        self.assertIn('previous version was put back', softUpgrade.read_status(self.job)['message'])

    def test_nothing_starts_while_another_upgrade_holds_the_lock(self):
        import fcntl
        softUpgrade.STATUS_ROOT.mkdir(exist_ok=True)
        with (softUpgrade.STATUS_ROOT / '.lock').open('a') as held:
            fcntl.flock(held, fcntl.LOCK_EX)
            with mock.patch.object(softUpgrade, 'run') as run:
                with self.assertRaises(softUpgrade.Busy):
                    softUpgrade.run_unattended('v3.0.10', 'b' * 40, self.job)
                run.assert_not_called()
        self.assertEqual({'state': 'missing'}, softUpgrade.read_status(self.job))


class UpgraderPinTests(unittest.TestCase):
    def test_upgrader_installs_the_signed_commit_or_stops_before_replacing_anything(self):
        upgrader = (ROOT / 'plogical' / 'upgrade.py').read_text()
        start = upgrader.index("pinned = os.environ.get('CYBERPANEL_UPGRADE_COMMIT')")
        self.assertLess(upgrader.index("'Checkout requested CyberPanel branch'"), start)
        end = upgrader.index('preserve_installation_state(installation, staged, backed_up_files)', start)
        block = upgrader[start:end]
        self.assertIn("if not re.fullmatch(r'[0-9a-f]{40}', pinned):\n                        return 0,", block)
        self.assertIn("'git -C %s checkout --detach %s --' % (shlex.quote(staged), pinned)", block)
        self.assertEqual(2, block.count("subprocess.check_output(revision).decode().strip() != pinned"))
        self.assertIn("return 0, 'The staged source is not the signed release commit'", block)
        self.assertLess(end, upgrader.index('with activate_source(installation, staged) as previous:'))


if __name__ == '__main__':
    unittest.main()
