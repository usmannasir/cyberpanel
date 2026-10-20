"""Real product wait/deletion methods with simulated procfs and monotonic time."""
import io
import os
import stat
from types import SimpleNamespace as NS
import unittest
from unittest import mock

import test_unix_account_deletion as deletion_tests


PHP = '/usr/local/lsws/lsphp82/bin/lsphp'


def worker(**changes):
    values = dict(uids=(1011,) * 4, gids=(1011,) * 4, executable=PHP,
                  mode=stat.S_IFREG | 0o755, owner=0, inode=20, installed_inode=20)
    values.update(changes)
    return values


class PHPWorkerWaitTests(unittest.TestCase):
    helper = deletion_tests.UnixAccountDeletionTests.helper
    deletion = deletion_tests.UnixAccountDeletionTests.deletion

    def setUp(self):
        deletion_tests.UnixAccountDeletionTests.setUp(self)
        self.frames = [{}]
        self.frame_index = 0
        self.now = 0
        self.sleeps = []
        self.after_sleep = lambda: None
        self.on_list = lambda: None
        self.proc_reads = []
        self.stat_reads = {}

        def listdir(path):
            self.assertEqual('/proc', path)
            self.on_list()
            self.proc_reads.append(self.now)
            return list(self.frame())

        def status(path, *args, **kwargs):
            self.assertTrue(path.startswith('/proc/'))
            entry = self.frame()[path.split('/')[2]]
            if path.endswith('/stat'):
                pid = path.split('/')[2]
                count = self.stat_reads.get(pid, 0)
                self.stat_reads[pid] = count + 1
                start = 100 + int(bool(entry.get('reused')) and count > 0)
                return io.StringIO(pid + ' (lsphp) ' + ' '.join(['S'] + ['0'] * 18 + [str(start)]))
            if entry.get('status_error'):
                raise entry['status_error']
            uids = '\t'.join(map(str, entry['uids']))
            gids = '\t'.join(map(str, entry['gids']))
            return io.StringIO('Name:\tlsphp\nUid:\t%s\nGid:\t%s\n' % (uids, gids))

        def readlink(path):
            entry = self.frame()[path.split('/')[2]]
            if entry.get('exe_error'):
                raise entry['exe_error']
            return entry['executable']

        def file_stat(path):
            if path.startswith('/proc/'):
                entry = self.frame()[path.split('/')[2]]
                if path.count('/') == 2 and entry.get('exited'):
                    raise FileNotFoundError(path)
                inode = entry['inode']
            else:
                entry = next(item for item in self.frame().values() if item['executable'] == path)
                inode = entry['installed_inode']
            return NS(st_mode=entry['mode'], st_uid=entry['owner'], st_dev=1, st_ino=inode)

        self.scope['os'] = NS(path=NS(exists=lambda path: False, isabs=os.path.isabs),
                              listdir=listdir, readlink=readlink, stat=file_stat)
        self.scope['open'] = status
        clock = NS(monotonic=lambda: self.now, sleep=self.sleep)
        self.time_patch = mock.patch.dict('sys.modules', {'time': clock})
        self.time_patch.start()
        self.addCleanup(self.time_patch.stop)

    def frame(self):
        return self.frames[min(self.frame_index, len(self.frames) - 1)]

    def sleep(self, seconds):
        # No account command may run before the product observes an idle UID.
        self.assertFalse(any(event.startswith(('deluser ', 'userdel ', 'groupdel ')) for event in self.events))
        self.assertGreater(seconds, 0)
        self.assertLessEqual(seconds, 1)
        self.sleeps.append(seconds)
        self.now += seconds
        self.frame_index += 1
        self.after_sleep()

    def test_idle_account_runs_immediately_without_delay(self):
        self.assertEqual(1, self.helper())
        self.assertEqual([], self.sleeps)
        self.assertEqual([self.user_command, 'groupdel ' + self.username], self.events)

    def test_ols_and_lsws_natural_worker_wait_follows_reload_then_deletes_once(self):
        transport = self.process.normalExecutioner.side_effect
        def reject_busy_user(command, *args):
            if command.startswith(('deluser ', 'userdel ')) and self.frame():
                self.events.append(command)
                return 0
            return transport(command, *args)
        self.process.normalExecutioner.side_effect = reject_busy_user
        for server in (1, 2):
            with self.subTest(server=server):
                self.server = server
                self.events.clear()
                self.frames = [{'41': worker()}, {'41': worker(), '42': worker()}, {}]
                self.frame_index = 0
                self.user_exists = self.group_exists = self.row_exists = True
                def observed_scan():
                    self.assertIn('restart', self.events)
                    self.assertIn('conf-delete:fixture.test', self.events)
                    self.assertIn('conf-delete:child.fixture.test', self.events)
                self.on_list = observed_scan
                self.assertEqual(1, self.deletion())
                self.assertEqual(1, self.events.count(self.user_command))
                self.assertEqual(2, self.frame_index)
                self.assertEqual(1, self.events.count('groupdel ' + self.username))
                self.assertFalse(self.user_exists or self.group_exists)

    def test_normal_worker_timeout_retains_account_and_issues_no_delete(self):
        self.frames = [{'41': worker()}]
        with self.assertRaisesRegex(RuntimeError, 'still running after 60 seconds'):
            self.helper()
        self.assertEqual(60, sum(self.sleeps))
        self.assertEqual([], self.events)
        self.assertTrue(self.user_exists and self.group_exists)

    def test_unknown_executable_fails_without_wait_or_delete(self):
        self.frames = [{'41': worker(executable='/usr/bin/python3')}]
        with self.assertRaisesRegex(RuntimeError, 'other than a normal PHP worker'):
            self.helper()
        self.assertEqual([], self.events + self.sleeps)

    def test_normal_and_unknown_processes_fail_without_delete(self):
        self.frames = [{'41': worker(), '42': worker(executable='/bin/sh')}]
        with self.assertRaises(RuntimeError):
            self.helper()
        self.assertEqual([], self.events + self.sleeps)

    def test_mixed_real_effective_saved_or_fs_ids_fail(self):
        for field in ('uids', 'gids'):
            for index in range(4):
                with self.subTest(field=field, index=index):
                    values = [1011] * 4
                    values[index] = 0
                    self.frames = [{'41': worker(**{field: tuple(values)})}]
                    with self.assertRaisesRegex(RuntimeError, 'unexpected user or group IDs'):
                        self.helper()
                    self.assertEqual([], self.events + self.sleeps)

    def test_unrelated_uid_does_not_delay_or_require_executable(self):
        self.frames = [{'41': worker(uids=(998,) * 4, executable='/usr/bin/sleep')}]
        self.assertEqual(1, self.helper())
        self.assertEqual([], self.sleeps)

    def test_changed_account_uid_gid_home_or_name_aborts(self):
        for field, value in (('pw_uid', 1012), ('pw_gid', 1012),
                             ('pw_dir', '/home/other'), ('pw_name', 'replacement')):
            with self.subTest(field=field):
                self.frames = [{'41': worker()}, {}]
                self.frame_index = 0
                lookup = self.scope['pwd'].getpwnam.side_effect
                original = lookup(self.username)
                altered = NS(**vars(original))
                setattr(altered, field, value)
                self.after_sleep = lambda: setattr(self.scope['pwd'].getpwnam, 'side_effect', lambda name: altered)
                with self.assertRaisesRegex(RuntimeError, 'account changed'):
                    self.helper()
                self.assertEqual([], self.events)
                self.scope['pwd'].getpwnam.side_effect = lookup

    def test_disappearing_account_while_waiting_is_not_authority_to_delete_group(self):
        self.frames = [{'41': worker()}, {}]
        self.after_sleep = lambda: setattr(self, 'user_exists', False)
        with self.assertRaises(KeyError):
            self.helper()
        self.assertEqual([], self.events)
        self.assertTrue(self.group_exists)

    def test_root_account_identity_is_rejected_before_proc_scan(self):
        self.scope['pwd'].getpwnam.side_effect = lambda name: NS(pw_name=name, pw_uid=0, pw_gid=1011, pw_dir='/home/test')
        with self.assertRaisesRegex(RuntimeError, 'account identity'):
            self.helper()
        self.assertEqual([], self.events + self.proc_reads)

    def test_missing_metadata_on_live_process_is_not_idle(self):
        for failure in ('status_error', 'exe_error'):
            with self.subTest(failure=failure):
                self.frames = [{'41': worker(**{failure: FileNotFoundError('fixture')})}]
                with self.assertRaisesRegex(RuntimeError, 'live process metadata'):
                    self.helper()
                self.assertEqual([], self.events + self.sleeps)

    def test_process_exit_between_reads_can_finish_without_wait(self):
        self.frames = [{'41': worker(exe_error=FileNotFoundError('fixture'), exited=True)}]
        self.assertEqual(1, self.helper())
        self.assertEqual([], self.sleeps)

    def test_unreadable_proc_metadata_is_failure(self):
        self.frames = [{'41': worker(status_error=PermissionError('fixture'))}]
        with self.assertRaises(PermissionError):
            self.helper()
        self.assertEqual([], self.events + self.sleeps)

    def test_untrusted_replaced_or_deleted_php_executable_is_failure(self):
        for changes in ({'owner': 1011}, {'mode': stat.S_IFREG | 0o777},
                        {'mode': stat.S_IFREG | 0o644}, {'installed_inode': 99},
                        {'executable': PHP + ' (deleted)'},
                        {'executable': '/tmp/lsphp82/bin/lsphp'}):
            with self.subTest(changes=changes):
                self.frames = [{'41': worker(**changes)}]
                with self.assertRaises(RuntimeError):
                    self.helper()
                self.assertEqual([], self.events + self.sleeps)

    def test_reused_pid_is_not_one_verified_worker(self):
        self.frames = [{'41': worker(reused=True)}]
        with self.assertRaisesRegex(RuntimeError, 'process identity changed'):
            self.helper()
        self.assertEqual([], self.events + self.sleeps)

    def test_absence_postcondition_still_rejects_transport_success_after_wait(self):
        self.frames = [{'41': worker()}, {}]
        self.user_remains = True
        with self.assertRaisesRegex(RuntimeError, 'Unix user .* remains'):
            self.helper()
        self.assertEqual([self.user_command], self.events)
        self.assertTrue(self.user_exists and self.group_exists)


if __name__ == '__main__':
    unittest.main()
