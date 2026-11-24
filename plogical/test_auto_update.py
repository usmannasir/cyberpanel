"""Automatic updates: off unless enabled, signed releases only, one attempt per release."""
import ast
import json
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import autoUpdate, releaseManifest, softUpgrade  # noqa: E402

PUBLISHED = 1795253405  # 2026-11-21T09:30:05Z


def git(directory, *arguments):
    return subprocess.run(['git', '-C', str(directory), '-c', 'user.name=t', '-c', 'user.email=t@example.com']
                          + list(arguments), check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True).stdout.strip()


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        base = Path(self.base.name)
        self.installation = base / 'CyberCP'
        self.installation.mkdir()
        git(self.installation, 'init', '--quiet', '--initial-branch=v3.0.9')
        self.commit_version(9)
        self.older = git(self.installation, 'rev-parse', 'HEAD')
        (self.installation / 'note').write_text('same version, later commit\n')
        git(self.installation, 'add', '.')
        git(self.installation, 'commit', '--quiet', '-m', 'later')
        self.current = git(self.installation, 'rev-parse', 'HEAD')
        git(self.installation, 'checkout', '--quiet', '-b', 'v3.0.10')
        self.commit_version(10)
        self.next = git(self.installation, 'rev-parse', 'HEAD')
        git(self.installation, 'checkout', '--quiet', 'v3.0.9')
        self.now = PUBLISHED + 30 * 3600
        self.release = self.published()
        self.mails, self.upgrades, self.commands, self.fetched = [], [], [], []
        self.outcome = 'success'
        self.fetch_error = None
        self.free = 50 * 1024 ** 3
        self.settings_path = base / 'etc' / 'auto-update.json'
        self.units = base / 'units'
        self.units.mkdir()
        self.updater = autoUpdate.Updater(
            settings=self.settings_path, state=base / 'state', installation=self.installation, units=self.units,
            fetch=self.fetch, verify=self.verify, clock=lambda: self.now,
            mail=lambda *message: self.mails.append(message), upgrade=self.upgrade,
            command=self.command, free=lambda: self.free)
        self.updater.identity = lambda: 'machine-one'

    def commit_version(self, build):
        (self.installation / 'cyberpanel_version.py').write_text("VERSION = '3.0'\nBUILD = %d\n" % build)
        git(self.installation, 'add', '.')
        git(self.installation, 'commit', '--quiet', '-m', 'build %d' % build)

    def published(self, **changes):
        release = {'schema': 1, 'sequence': 5, 'version': '3.0', 'build': 10, 'branch': 'v3.0.10',
                   'commit': self.next, 'published': '2026-11-21T09:30:05Z', 'soak_hours': 24,
                   'spread_hours': 0, 'hold': False}
        release.update(changes)
        return release

    def fetch(self):
        self.fetched.append(self.now)
        if self.fetch_error:
            raise self.fetch_error
        return b'published file'

    def verify(self, document):
        if isinstance(self.release, Exception):
            raise self.release
        return dict(self.release)

    def upgrade(self, job):
        self.upgrades.append(job)
        if self.outcome in ('success', 'incomplete'):
            git(self.installation, 'checkout', '--quiet', 'v3.0.10')
            return 0, '', ['The panel web worker was not rebuilt: no network'] if self.outcome == 'incomplete' else []
        if self.outcome == 'busy':
            return autoUpdate.BUSY, '', []
        if self.outcome == 'wrong commit':
            return 0, '', []
        return 1, 'Upgrade exited with code 1. MariaDB is unavailable', []

    def command(self, *arguments):
        self.commands.append(arguments)
        return subprocess.CompletedProcess(arguments, 0, 'active\n')

    def configure(self, mode, hour=None, email='admin@example.com'):
        hour = time.localtime(self.now).tm_hour if hour is None else hour
        self.updater.configure({'mode': mode, 'hour': hour, 'email': email})
        self.commands.clear()

    def state(self):
        return self.updater.state()


class DefaultTests(Fixture):
    def test_nothing_happens_until_an_administrator_turns_it_on(self):
        self.assertEqual({'mode': 'off', 'hour': 3, 'email': ''}, self.updater.settings())
        self.assertEqual(0, self.updater.run())
        self.assertEqual(([], [], [], {}), (self.fetched, self.upgrades, self.mails, self.state()))

    def test_a_damaged_settings_file_means_off(self):
        self.settings_path.parent.mkdir()
        for text in ('', 'not json', '[]', '{"mode": "install"}', '{"mode": "install", "hour": 99, "email": ""}',
                     '{"mode": "install", "hour": 3, "email": "", "source": "https://example.com"}'):
            self.settings_path.write_text(text)
            with self.subTest(text):
                self.assertEqual('off', self.updater.settings()['mode'])
                self.updater.run()
                self.assertEqual([], self.upgrades)

    def test_settings_are_checked(self):
        good = {'mode': 'install', 'hour': 0, 'email': 'a.b+c@mail.example.co'}
        self.assertEqual(good, autoUpdate.checked_settings(dict(good)))
        self.assertEqual('', autoUpdate.checked_settings(dict(good, email=''))['email'])
        for change in ({'mode': 'on'}, {'mode': None}, {'hour': 24}, {'hour': -1}, {'hour': '3'}, {'hour': True},
                       {'hour': 3.0}, {'email': 'a@b'}, {'email': 'a b@example.com'}, {'email': 'a@example.com\nBcc: x@y.z'},
                       {'email': 'a@example.com, b@example.com'}, {'email': '$(id)@example.com'}, {'email': 5},
                       {'extra': 1}):
            with self.subTest(change), self.assertRaises(ValueError):
                autoUpdate.checked_settings(dict(good, **change))
        with self.assertRaises(ValueError):
            autoUpdate.checked_settings({'mode': 'install', 'hour': 3})


class NotifyTests(Fixture):
    def test_one_message_per_release_and_nothing_is_installed(self):
        self.configure('notify')
        self.updater.run()
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertEqual(1, len(self.mails))
        recipient, subject, text = self.mails[0]
        self.assertEqual('admin@example.com', recipient)
        self.assertIn('version 3.0.10 is available', subject)
        self.assertEqual('Version 3.0.10 is available. It can be installed from the Version Management page.', text)
        self.assertEqual(text, self.state()['summary'])
        self.release = self.published(sequence=6, build=11, branch='v3.0.11', commit='c' * 40)
        self.now += autoUpdate.CHECK_EVERY
        self.updater.run()
        self.assertEqual(2, len(self.mails))

    def test_no_message_without_an_address(self):
        self.configure('notify', email='')
        self.updater.run()
        self.assertEqual([], self.mails)
        self.assertIn('is available', self.state()['summary'])


class InstallTests(Fixture):
    def test_release_is_installed_once_at_the_chosen_hour_after_the_waiting_time(self):
        self.configure('install')
        self.now = PUBLISHED + 23 * 3600
        self.configure('install')
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertRegex(self.state()['summary'], r'^Version 3\.0\.10 will be installed automatically after 22 Nov 2026 09:30 UTC, at \d\d:00 server time\.$')
        self.now = PUBLISHED + 25 * 3600
        self.configure('install', hour=(time.localtime(self.now).tm_hour + 5) % 24)
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertRegex(self.state()['summary'], r'will be installed automatically at \d\d:00 server time')
        self.configure('install')
        self.updater.run()
        self.assertEqual(1, len(self.upgrades))
        self.assertRegex(self.upgrades[0], r'^[0-9a-f]{32}$')
        attempt = self.state()['attempt']
        self.assertEqual(('installed', self.next, 'v3.0.10', self.upgrades[0]),
                         (attempt['result'], attempt['commit'], attempt['branch'], attempt['job']))
        self.assertEqual(1, len(self.mails))
        self.assertIn('version 3.0.10 was installed', self.mails[0][1])
        self.updater.run()
        self.assertEqual(1, len(self.upgrades))
        self.assertEqual('This server has the current release (3.0.10).', self.state()['summary'])

    def test_an_installation_whose_steps_did_not_all_complete_says_which(self):
        self.outcome = 'incomplete'
        self.configure('install')
        self.updater.run()
        state = self.state()
        self.assertEqual('installed', state['attempt']['result'])
        self.assertEqual(['The panel web worker was not rebuilt: no network'], state['attempt']['incomplete'])
        self.assertRegex(state['summary'], r'^Version 3\.0\.10 was installed automatically on .*\. These steps did '
                                           r'not complete; .*: The panel web worker was not rebuilt: no network$')
        self.assertIn('version 3.0.10 was installed, but some steps did not complete', self.mails[0][1])

    def test_a_failed_installation_is_reported_and_not_repeated(self):
        self.configure('install')
        self.outcome = 'failed'
        self.updater.run()
        self.updater.run()
        self.now += 24 * 3600
        self.updater.run()
        self.assertEqual(1, len(self.upgrades))
        self.assertEqual(1, len(self.mails))
        self.assertIn('could NOT be installed', self.mails[0][1])
        self.assertIn('MariaDB is unavailable', self.mails[0][2])
        self.assertEqual('failed', self.state()['attempt']['result'])
        self.assertIn('did not succeed: Upgrade exited with code 1. MariaDB is unavailable. It will not be tried again.', self.state()['summary'])
        # The next signed release gets its own single attempt.
        (self.installation / 'cyberpanel_version.py').write_text("VERSION = '3.0'\nBUILD = 9\n")
        self.release = self.published(sequence=6, commit='d' * 40)
        self.now += 24 * 3600
        self.updater.run()
        self.assertEqual(2, len(self.upgrades))

    def test_an_upgrade_that_reports_success_without_the_signed_commit_counts_as_failed(self):
        self.configure('install')
        self.outcome = 'wrong commit'
        self.updater.run()
        self.assertEqual('failed', self.state()['attempt']['result'])
        self.assertIn('could NOT be installed', self.mails[0][1])

    def test_a_running_panel_upgrade_is_not_counted_as_an_attempt(self):
        self.configure('install')
        self.outcome = 'busy'
        self.updater.run()
        self.assertNotIn('attempt', self.state())
        self.assertEqual([], self.mails)
        self.outcome = 'success'
        self.updater.run()
        self.assertEqual(2, len(self.upgrades))
        self.assertEqual('installed', self.state()['attempt']['result'])

    def test_an_interrupted_installation_is_left_for_a_person(self):
        self.configure('install')
        self.updater.save_state({'release': self.release, 'checked': int(self.now),
                                 'attempt': {'commit': self.next, 'branch': 'v3.0.10', 'job': 'a' * 32,
                                             'started': int(self.now) - 7200}})
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertEqual('failed', self.state()['attempt']['result'])
        self.assertIn('interrupted', self.state()['summary'])

    def test_newer_files_of_the_installed_version_are_called_an_update(self):
        self.configure('notify')
        self.release = self.published(build=9, branch='v3.0.9', commit='c' * 40)
        self.updater.run()
        self.assertEqual('An update of version 3.0.9 is available. It can be installed from the Version Management page.',
                         self.state()['summary'])

    def test_paused_release_is_never_installed(self):
        self.configure('install')
        self.release = self.published(hold=True)
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertEqual('CyberPanel has paused the automatic installation of version 3.0.10.', self.state()['summary'])

    def test_servers_take_turns_inside_the_spread_window(self):
        release = self.published(spread_hours=48)
        offsets = {autoUpdate.spread_offset('machine-%d' % number, release) for number in range(40)}
        self.assertGreater(len(offsets), 30)
        self.assertTrue(all(0 <= offset < 48 * 3600 for offset in offsets))
        self.assertEqual(autoUpdate.spread_offset('machine-one', release), autoUpdate.spread_offset('machine-one', release))
        self.assertEqual(0, autoUpdate.spread_offset('machine-one', self.published(spread_hours=0)))
        self.configure('install')
        self.release = release
        self.now = PUBLISHED + 24 * 3600 + autoUpdate.spread_offset('machine-one', release) - 60
        self.configure('install')
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.now += 120
        self.configure('install')
        self.updater.run()
        self.assertEqual(1, len(self.upgrades))

    def test_low_disk_space_stops_the_installation_without_using_the_attempt(self):
        self.configure('install')
        self.free = 2 * 1024 ** 3
        self.updater.run()
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertNotIn('attempt', self.state())
        self.assertEqual(1, len(self.mails))
        self.assertIn('needs attention', self.mails[0][1])
        self.assertIn('less than 3 GB of disk space is free', self.mails[0][2])
        self.free = 50 * 1024 ** 3
        self.updater.run()
        self.assertEqual(1, len(self.upgrades))

    def test_checking_from_the_panel_installs_nothing_and_sends_nothing(self):
        self.configure('install')
        self.updater.run(check_only=True)
        self.assertEqual(([], []), (self.upgrades, self.mails))
        self.assertEqual('Version 3.0.10 is being installed.', self.state()['summary'])
        self.updater.settings_path.unlink()
        self.updater.run(check_only=True)
        self.assertEqual('Version 3.0.10 is available.', self.state()['summary'])


class ReleaseTrustTests(Fixture):
    def test_release_already_in_the_installed_source_is_current(self):
        self.configure('install')
        for commit in (self.current, self.older):
            self.release = self.published(build=9, branch='v3.0.9', commit=commit, sequence=5)
            self.updater.save_state({})
            self.updater.run()
            self.assertEqual('This server has the current release (3.0.9).', self.state()['summary'])
        self.assertEqual([], self.upgrades)

    def test_release_older_than_the_installed_version_is_never_installed(self):
        self.configure('install')
        self.release = self.published(build=8, branch='v3.0.8', commit='e' * 40)
        self.updater.run()
        self.assertEqual([], self.upgrades)
        self.assertIn('newer version than the published release', self.state()['summary'])

    def test_a_file_that_does_not_verify_changes_nothing(self):
        self.configure('install', hour=(time.localtime(self.now).tm_hour + 5) % 24)
        self.updater.run()
        known = self.state()['release']
        self.configure('install')
        for failure, expected in ((releaseManifest.Unverified('The release file is not signed by CyberPanel.'), 'could not be verified'),
                                  (releaseManifest.Unavailable('Release signatures cannot be checked here: X'), 'cannot be checked here'),
                                  (OSError('HTTP Error 404: Not Found'), 'could not be fetched: HTTP Error 404')):
            self.release, self.fetch_error = (failure, None) if isinstance(failure, (
                releaseManifest.Unverified, releaseManifest.Unavailable)) else (self.published(), failure)
            self.now += autoUpdate.CHECK_EVERY
            self.configure('install', hour=(time.localtime(self.now).tm_hour + 5) % 24)
            self.updater.run()
            with self.subTest(failure):
                self.assertIn(expected, self.state()['error'])
                self.assertEqual(known, self.state()['release'])
        self.assertEqual([], self.upgrades)

    def test_older_release_information_is_ignored(self):
        self.configure('install', hour=(time.localtime(self.now).tm_hour + 5) % 24)
        self.updater.run()
        known = self.state()['release']
        for replayed in (self.published(sequence=4, commit='f' * 40), self.published(sequence=5, commit='f' * 40)):
            self.release = replayed
            self.now += autoUpdate.CHECK_EVERY
            self.updater.run()
            self.assertEqual(known, self.state()['release'])
            self.assertEqual('Older release information was offered and ignored.', self.state()['error'])
        self.release = self.published(sequence=6, hold=True)
        self.now += autoUpdate.CHECK_EVERY
        self.updater.run()
        self.assertEqual(6, self.state()['release']['sequence'])
        self.assertEqual('', self.state()['error'])

    def test_release_is_looked_up_a_few_times_a_day_and_at_the_update_hour(self):
        self.configure('notify', hour=(time.localtime(self.now).tm_hour + 12) % 24)
        self.updater.run()
        self.now += 3600
        self.updater.run()
        self.assertEqual(1, len(self.fetched))
        self.now += autoUpdate.CHECK_EVERY
        self.updater.run()
        self.assertEqual(2, len(self.fetched))


class ScheduleTests(Fixture):
    def test_timer_follows_the_mode(self):
        self.updater.configure({'mode': 'install', 'hour': 4, 'email': ''})
        service = (self.units / autoUpdate.SERVICE).read_text()
        self.assertIn('ExecStart=/usr/local/CyberCP/bin/python -I /usr/local/CyberCP/plogical/autoUpdate.py run\n', service)
        self.assertIn('Type=oneshot\n', service)
        timer = (self.units / autoUpdate.TIMER).read_text()
        self.assertIn('OnCalendar=hourly\n', timer)
        self.assertIn('WantedBy=timers.target\n', timer)
        self.assertEqual([('/usr/bin/systemctl', 'daemon-reload'),
                          ('/usr/bin/systemctl', 'enable', '--now', autoUpdate.TIMER)], self.commands)
        self.assertEqual(0o600, self.settings_path.stat().st_mode & 0o777)
        self.assertEqual(0o644, (self.units / autoUpdate.TIMER).stat().st_mode & 0o777)
        self.commands.clear()
        self.updater.configure({'mode': 'off', 'hour': 4, 'email': ''})
        self.assertEqual(('/usr/bin/systemctl', 'disable', '--now', autoUpdate.TIMER), self.commands[-1])
        with self.assertRaises(ValueError):
            self.updater.configure({'mode': 'always', 'hour': 4, 'email': ''})
        self.assertEqual('off', self.updater.settings()['mode'])

    def test_status_for_the_panel_page(self):
        self.configure('notify')
        self.updater.run()
        status = self.updater.status()
        self.assertEqual({'version': '3.0', 'build': 9, 'commit': self.current}, status['installed'])
        self.assertEqual(self.release, status['release'])
        self.assertEqual(('notify', 'active', ''), (status['settings']['mode'], status['timer'], status['error']))
        self.assertEqual(time.strftime('%d %b %Y %H:%M %Z', time.localtime(self.now)), status['checked_text'])
        self.assertEqual('', autoUpdate.Updater(settings=self.settings_path, state=Path(self.base.name, 'none'),
                                                installation=self.installation, command=self.command).status()['checked_text'])
        json.dumps(status)

    def test_command_line_accepts_only_checked_settings(self):
        text = json.dumps({'mode': 'install', 'hour': 2, 'email': 'a@example.com'}).encode().hex()
        with mock.patch.object(autoUpdate, 'Updater', return_value=self.updater), \
                mock.patch.object(autoUpdate.os, 'geteuid', return_value=0), mock.patch('builtins.print'):
            self.assertEqual(0, autoUpdate.main(['configure', text]))
            self.assertEqual('install', self.updater.settings()['mode'])
            for bad in ('7b7d', json.dumps({'mode': 'x', 'hour': 2, 'email': ''}).encode().hex(), 'zz', "{'mode':'off'}", ''):
                self.assertNotEqual(0, autoUpdate.main(['configure', bad]))
            self.assertEqual('install', self.updater.settings()['mode'])
            self.assertEqual(2, autoUpdate.main(['anything']))
        with mock.patch.object(autoUpdate.os, 'geteuid', return_value=1000), mock.patch('builtins.print'):
            self.assertEqual(1, autoUpdate.main(['run']))


class InstallJobTests(Fixture):
    def test_job_upgrades_to_the_recorded_signed_commit_only(self):
        self.updater.save_state({'attempt': {'commit': self.next, 'branch': 'v3.0.10', 'job': 'a' * 32, 'started': 1}})
        with mock.patch.object(softUpgrade, 'run_unattended') as run:
            self.assertEqual(0, self.updater.install_job('a' * 32))
            run.assert_called_once_with('v3.0.10', self.next, 'a' * 32)
            for job in ('b' * 32, 'a' * 31, '../../etc/passwd', ''):
                self.assertEqual(1, self.updater.install_job(job))
            run.assert_called_once()
            run.side_effect = softUpgrade.Busy('Another panel upgrade is in progress.')
            self.assertEqual(autoUpdate.BUSY, self.updater.install_job('a' * 32))
            run.side_effect = RuntimeError('Upgrade exited with code 1.')
            self.assertEqual(1, self.updater.install_job('a' * 32))
        finished = dict(self.state()['attempt'], result='failed')
        self.updater.save_state({'attempt': finished})
        with mock.patch.object(softUpgrade, 'run_unattended') as run:
            self.assertEqual(1, self.updater.install_job('a' * 32))
            run.assert_not_called()

    def test_module_runs_on_the_oldest_supported_python(self):
        options = {'feature_version': (3, 6)} if sys.version_info >= (3, 8) else {}
        ast.parse((ROOT / 'plogical' / 'autoUpdate.py').read_text(), **options)


if __name__ == '__main__':
    unittest.main()
