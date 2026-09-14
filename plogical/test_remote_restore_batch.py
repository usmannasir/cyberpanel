import ast
import fcntl
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical.remoteRestoreBatch import archive_stem, batch_status, run_restore_batch


class RemoteRestoreBatchTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.log = self.root / 'backup_log'

    def archive(self, name='target.tar.gz', old_status=None):
        (self.root / name).write_bytes(b'fixture archive')
        extracted = self.root / archive_stem(name)
        extracted.mkdir(exist_ok=True)
        if old_status is not None:
            (extracted / 'status').write_text(old_status)
        return extracted / 'status'

    def worker(self, status_path, steps):
        steps = iter(steps)
        def poll():
            code, status = next(steps)
            if status is not None:
                status_path.write_text(status)
            return code
        return SimpleNamespace(poll=poll, pid=12345)

    def run_batch(self, workers, **kwargs):
        with patch('plogical.remoteRestoreBatch.subprocess.Popen', side_effect=workers) as launch, \
             patch('plogical.remoteRestoreBatch.time.sleep'):
            result = run_restore_batch(str(self.root), str(self.log), 'test', '/copied/source', **kwargs)
        return result, launch

    def test_empty_directory_fails_instead_of_success(self):
        result, launch = self.run_batch([])
        self.assertFalse(result)
        launch.assert_not_called()
        self.assertIn('[5010]', self.log.read_text())
        self.assertNotIn('completed[success]', self.log.read_text())

    def test_all_archives_must_finish_and_evidence_is_retained(self):
        paths = [self.archive(name) for name in ('a.tar.gz', 'b.tar.gz')]
        result, launch = self.run_batch([self.worker(p, [(0, 'Done')]) for p in paths])
        self.assertTrue(result)
        self.assertEqual(launch.call_count, 2)
        self.assertTrue(all(p.exists() for p in paths))
        self.assertTrue((self.root / 'a.tar.gz').exists())
        self.assertEqual(batch_status(self.log.read_text())['complete'], 1)

    def test_one_failed_archive_fails_the_batch_and_preserves_failure(self):
        paths = [self.archive(name) for name in ('a.tar.gz', 'b.tar.gz', 'c.tar.gz')]
        result, launch = self.run_batch([self.worker(paths[0], [(0, 'Done')]),
                                       self.worker(paths[1], [(0, 'Import failed [5009]')])])
        self.assertFalse(result)
        self.assertEqual(launch.call_count, 2)
        self.assertEqual(paths[1].read_text(), 'Import failed [5009]')
        self.assertIn('after 1 archive(s)', self.log.read_text())
        self.assertNotIn('completed[success]', self.log.read_text())

    def test_missing_status_is_pending_until_the_worker_finishes(self):
        status = self.archive()
        result, _ = self.run_batch([self.worker(status, [(None, None), (None, 'Extracting'), (0, 'Done')])])
        self.assertTrue(result)

    def test_worker_exit_without_status_is_a_terminal_failure(self):
        status = self.archive()
        result, _ = self.run_batch([self.worker(status, [(0, None)])])
        self.assertFalse(result)
        self.assertIn('without a fresh completion status', self.log.read_text())

    def test_worker_exit_failure_overrides_done(self):
        status = self.archive()
        result, _ = self.run_batch([self.worker(status, [(1, 'Done')])])
        self.assertFalse(result)

    def test_done_does_not_finish_a_still_running_worker(self):
        status = self.archive()
        result, _ = self.run_batch([self.worker(status, [(None, 'Done'), (0, 'Finalization failed [5009]')])])
        self.assertFalse(result)

    def test_previous_run_done_cannot_complete_a_failed_launch(self):
        status = self.archive(old_status='Done')
        result, _ = self.run_batch([self.worker(status, [(0, None)])])
        self.assertFalse(result)

    def test_previous_run_failure_can_be_replaced_by_fresh_success(self):
        status = self.archive(old_status='Old failure [5009]')
        result, _ = self.run_batch([self.worker(status, [(0, 'Done')])])
        self.assertTrue(result)

    def test_launch_exception_is_a_terminal_failure(self):
        self.archive()
        result, _ = self.run_batch([OSError('Could not start restore')])
        self.assertFalse(result)
        self.assertIn('Could not start restore', self.log.read_text())

    def test_timeout_retains_running_worker_and_does_not_start_next_archive(self):
        status = self.archive('a.tar.gz')
        self.archive('b.tar.gz')
        worker = Mock(pid=12345)
        worker.poll.return_value = None
        with patch('plogical.remoteRestoreBatch.time.monotonic', side_effect=[0, 20]):
            result, launch = self.run_batch([worker], timeout=10)
        self.assertFalse(result)
        self.assertEqual(launch.call_count, 1)
        worker.terminate.assert_not_called()
        worker.kill.assert_not_called()
        worker.wait.assert_called_once_with()
        self.assertIn('may still be running', self.log.read_text())
        self.assertTrue(status.parent.exists())

    def test_suffix_removal_does_not_strip_filename_characters(self):
        for name in ('target.tar.gz', 'backup-org.tar.gz', '/tmp/target.tar.gz'):
            self.assertEqual(archive_stem(name), name[:-7])
        status = self.archive('target.tar.gz')
        result, launch = self.run_batch([self.worker(status, [(0, 'Done')])])
        self.assertTrue(result)
        self.assertIn('target.tar.gz', launch.call_args.args[0])

    def test_legacy_errors_override_legacy_false_success(self):
        for failure in ('[5010]', '[5009]', 'Error[Failed]', 'completed[failed]'):
            outcome = batch_status(failure + '\ncompleted[success]')
            self.assertEqual(outcome['remoteTransferStatus'], 0)
            self.assertEqual(outcome['complete'], 0)

    def test_symlink_archive_is_not_selected(self):
        target = self.root / 'plain-file'
        target.write_bytes(b'fixture')
        (self.root / 'linked.tar.gz').symlink_to(target)
        result, launch = self.run_batch([])
        self.assertFalse(result)
        launch.assert_not_called()

    def test_status_directory_must_remain_within_batch(self):
        (self.root / 'target.tar.gz').write_bytes(b'fixture')
        with tempfile.TemporaryDirectory() as outside:
            (self.root / 'target').symlink_to(outside, target_is_directory=True)
            result, launch = self.run_batch([])
            self.assertFalse(result)
            launch.assert_not_called()
            self.assertIn('Invalid backup archive path', self.log.read_text())

    def test_explicit_retry_has_its_own_result_and_retains_old_log(self):
        status = self.archive()
        self.run_batch([self.worker(status, [(0, 'Import failed [5009]')])])
        result, _ = self.run_batch([self.worker(status, [(0, 'Done')])])
        self.assertTrue(result)
        log = self.log.read_text()
        self.assertIn('Import failed [5009]', log)
        self.assertEqual(batch_status(log)['complete'], 1)
        self.assertEqual(batch_status(log)['remoteTransferStatus'], 1)

    def test_concurrent_start_does_not_touch_an_active_batch(self):
        self.archive()
        self.log.write_text('Active restore log')
        with (self.root / '.restore.lock').open('w') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            result, launch = self.run_batch([])
        self.assertFalse(result)
        launch.assert_not_called()
        self.assertEqual(self.log.read_text(), 'Active restore log')

    def test_timeout_keeps_the_lock_until_the_child_exits(self):
        self.archive()
        worker = Mock(pid=12345)
        worker.poll.return_value = None
        def still_running():
            self.assertEqual(batch_status(self.log.read_text())['remoteTransferStatus'], 0)
            with (self.root / '.restore.lock').open('a') as lock:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        worker.wait.side_effect = still_running
        with patch('plogical.remoteRestoreBatch.time.monotonic', side_effect=[0, 20]):
            result, _ = self.run_batch([worker], timeout=10)
        self.assertFalse(result)

    def test_progress_is_pending_not_failure(self):
        self.assertEqual(batch_status('Extracting archive')['complete'], 0)
        self.assertEqual(batch_status('Extracting archive')['remoteTransferStatus'], 1)

    def test_ordinary_local_status_api_does_not_remove_batch_evidence(self):
        # Load only this ordinary API method, without importing live Django models.
        # The separate restoreStatus handler is outside this regression's scope.
        path = Path(__file__).parents[1] / 'backup/backupManager.py'
        tree = ast.parse(path.read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'BackupManager')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'localRestoreStatus')
        env = {'json': json, 'HttpResponse': lambda payload: json.loads(payload),
               'os': SimpleNamespace(path=SimpleNamespace(exists=lambda p: True)),
               're': __import__('re'), 'shlex': __import__('shlex'),
               'time': SimpleNamespace(sleep=lambda n: None)}
        acl = Mock()
        acl.currentContextPermission.return_value = 1
        acl.commandInjectionCheck.return_value = 0
        env['ACLManager'] = acl
        commands = Mock()
        env['ProcessUtilities'] = commands
        exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), env)
        for status, expected in [('completed[success]', 1), ('Error[Failed]', 0), ('[5009]\ncompleted[success]', 0)]:
            commands.outputExecutioner.return_value = (1, status)
            result = env['localRestoreStatus'](None, userID=1, data={'backupDir': 'test'})
            self.assertEqual(result['remoteTransferStatus'], expected)
            self.assertEqual(result['status'], status)
        for unavailable in (None, (0, 'cat: No such file'), (0, 'Permission denied'), (1, '')):
            commands.outputExecutioner.return_value = unavailable
            result = env['localRestoreStatus'](None, userID=1, data={'backupDir': 'test'})
            self.assertEqual(result['remoteTransferStatus'], 0)
            self.assertEqual(result['complete'], 0)
        commands.executioner.assert_not_called()
        commands.normalExecutioner.assert_not_called()


if __name__ == '__main__':
    unittest.main()
