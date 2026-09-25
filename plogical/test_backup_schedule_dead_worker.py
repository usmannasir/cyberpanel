"""createLocalBackup must not wait forever on a backup worker that died."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

from plogical.backupIntegrity import backup_process_is_running


SOURCE = Path(__file__).with_name('backupSchedule.py')


def load_backup_schedule(namespace):
    module = ast.parse(SOURCE.read_text())
    cls = next(node for node in module.body
               if isinstance(node, ast.ClassDef) and node.name == 'backupSchedule')
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['backupSchedule']


class DeadWorkerTests(unittest.TestCase):
    def run_backup(self, ps_outputs, status_text):
        commands = []
        ps = iter(ps_outputs)
        processes = SimpleNamespace(
            fetchCurrentPort=lambda: '8090',
            outputExecutioner=lambda command: next(ps),
            normalExecutioner=commands.append,
            debugPath='/nonexistent/debug',
        )
        status_path = '/home/example.test/backup/status'

        def exists(path):
            return path == status_path

        def fake_open(path, mode='r'):
            if path == status_path:
                return mock.mock_open(read_data=status_text)()
            raise FileNotFoundError(path)

        namespace = {
            'datetime': SimpleNamespace(now=lambda: None),
            'json': json,
            'time': SimpleNamespace(sleep=lambda seconds: None,
                                    strftime=lambda fmt: '09.25.2026_00-00-00'),
            'os': SimpleNamespace(path=SimpleNamespace(exists=exists, join=lambda *p: '/'.join(p)),
                                  remove=lambda path: None),
            'requests': SimpleNamespace(post=lambda *a, **k: SimpleNamespace(
                text=json.dumps({'tempStorage': '/home/example.test/backup/tmp'}))),
            'create_backup_request': lambda domain: '123',
            'ProcessUtilities': processes,
            'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=lambda m: None)),
            'open': fake_open,
            'backup_process_is_running': backup_process_is_running,
        }
        backup_schedule = load_backup_schedule(namespace)
        logged = []
        backup_schedule.remoteBackupLogging = staticmethod(
            lambda path, message, status=0: logged.append((message, status)))
        backup_schedule.completedArchiveIsReady = staticmethod(lambda *args: True)
        result = backup_schedule.createLocalBackup('example.test', '/dev/null')
        return result, commands, logged, backup_schedule

    def test_empty_status_without_worker_gives_up(self):
        limit = load_backup_schedule({'datetime': SimpleNamespace(now=lambda: None)}).WORKER_GONE_MAX_CHECKS
        result, commands, logged, _ = self.run_backup([''] * limit, '')
        self.assertEqual(0, result[0])
        self.assertIn('rm -rf /home/example.test/backup/tmp', commands)
        self.assertIn('sudo rm -f /home/example.test/backup/status', commands)
        self.assertTrue(any('exited without a result' in m for m, _ in logged))

    def test_running_worker_resets_the_counter(self):
        limit = load_backup_schedule({'datetime': SimpleNamespace(now=lambda: None)}).WORKER_GONE_MAX_CHECKS
        # Absent for limit-1 checks, back once, then absent again: must need a
        # full fresh window before giving up.
        outputs = [''] * (limit - 1) + ['BackupRoot /example.test/'] + [''] * limit
        result, _, _, _ = self.run_backup(outputs, '')
        self.assertEqual((0, 'Backup worker exited without reporting a result.'), result)

        # One check short of a fresh window: the loop is still waiting when the
        # fake ps output runs out (surfaced through the function's own handler).
        result, _, _, _ = self.run_backup(
            [''] * (limit - 1) + ['BackupRoot /example.test/'] + [''] * (limit - 1), '')
        self.assertNotEqual('Backup worker exited without reporting a result.', result[1])

    def test_completed_status_still_succeeds(self):
        result, _, _, _ = self.run_backup([''], 'Completed')
        self.assertEqual(1, result[0])


if __name__ == '__main__':
    unittest.main(verbosity=2)
