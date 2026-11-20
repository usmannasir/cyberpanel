"""Restore progress may only be read from a restore's own working directory."""
import ast
import json
import os
from pathlib import Path
import shlex
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical import statusUtilities
from plogical.statusUtilities import (read_restore_status, restore_work_directory,
                                      valid_restore_status_path, valid_status_path)
from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]
DENIED = SimpleNamespace(content=b'{"status": 0, "error_message": "You are not authorized to access this resource."}')


def response(content):
    return SimpleNamespace(content=content.encode())


class RestoreDirectoryTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.backups = Path(holder.name, 'backup')
        self.backups.mkdir()
        self.tenant = Path(holder.name, 'tenant')
        self.tenant.mkdir()
        allowed = patch.object(statusUtilities, 'RESTORE_DIRECTORY', str(self.backups))
        allowed.start()
        self.addCleanup(allowed.stop)

    def test_archive_in_the_backup_directory_selects_its_working_directory(self):
        (self.backups / 'backup-example.com-02.11.2026.tar.gz').write_text('archive')
        self.assertEqual(str(self.backups / 'backup-example.com-02.11.2026'),
                         restore_work_directory('backup-example.com-02.11.2026.tar.gz'))

    def test_transferred_archive_selects_the_numbered_transfer_directory(self):
        expected = str(self.backups / 'transfer-4821' / 'backup-example.com')
        self.assertEqual(expected, restore_work_directory('backup-example.com.tar.gz', '4821'))
        self.assertEqual(expected, restore_work_directory('backup-example.com.tar.gz', 4821))

    def test_paths_and_foreign_transfer_names_select_nothing(self):
        work = self.tenant / 'public_html' / 'x'
        work.mkdir(parents=True)
        (work / 'status').write_text('Done')
        for name in (str(work), str(work) + '.tar.gz', '/etc', '../tenant/public_html/x',
                     'sub/backup.tar.gz', 'backup.tar.gz/..', '..', '.', '', '.tar.gz',
                     'backup\n.tar.gz', None, 7, ['backup.tar.gz']):
            self.assertEqual('', restore_work_directory(name), repr(name))
            self.assertEqual('', restore_work_directory(name, '4821'), repr(name))
        for transfer in ('1 /etc', '../x', '4821/..', 'abc', '', '-1', '1' * 13, None, True, 4.5):
            self.assertEqual('', restore_work_directory('missing.tar.gz', transfer), repr(transfer))

    def test_only_the_status_file_of_a_working_directory_is_a_status_path(self):
        for path in (self.backups / 'backup-example.com' / 'status',
                     self.backups / 'transfer-4821' / 'backup-example.com' / 'status'):
            self.assertTrue(valid_restore_status_path(str(path)), path)
            # Ordinary status polling must not reach restore directories.
            self.assertFalse(valid_status_path(str(path)), path)
        for path in (self.tenant / 'x' / 'status', self.backups / 'status',
                     self.backups / 'backup-example.com' / 'meta.xml',
                     self.backups / 'backup-example.com' / 'sub' / 'status',
                     self.backups / 'transfer-x' / 'backup-example.com' / 'status',
                     self.backups / '..' / 'tenant' / 'status',
                     '%s /etc/shadow' % (self.backups / 'backup-example.com' / 'status')):
            self.assertFalse(valid_restore_status_path(str(path)), path)
        for path in (None, 7, ['status']):
            self.assertFalse(valid_restore_status_path(path), repr(path))

    def test_status_link_inside_a_working_directory_is_refused(self):
        work = self.backups / 'backup-example.com'
        work.mkdir()
        secret = self.tenant / 'secret'
        secret.write_text('root:$6$secret-hash\n')
        os.symlink(str(secret), str(work / 'status'))
        with self.assertRaises(ValueError):
            read_restore_status(str(work))
        for directory in (str(self.tenant), str(self.backups), '/etc', None):
            with self.assertRaises(ValueError):
                read_restore_status(directory)


class RestoreStatusTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.backups = Path(holder.name, 'backup')
        self.backups.mkdir()
        self.tenant = Path(holder.name, 'tenant')
        self.tenant.mkdir()
        allowed = patch.object(statusUtilities, 'RESTORE_DIRECTORY', str(self.backups))
        allowed.start()
        self.addCleanup(allowed.stop)
        self.root = Mock()
        self.status = load_method('backup/backupManager.py', 'BackupManager', 'restoreStatus', dict(
            json=json, os=os, shlex=shlex, HttpResponse=response,
            ACLManager=SimpleNamespace(loadErrorJson=lambda *arguments: DENIED),
            ProcessUtilities=self.root,
            logging=SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=Mock()))))

    def poll(self, **data):
        return json.loads(self.status(None, data).content)

    def restore(self, status=None, name='backup-example.com'):
        (self.backups / (name + '.tar.gz')).write_text('archive')
        work = self.backups / name
        work.mkdir()
        if status is not None:
            (work / 'status').write_text(status)
        return work

    def test_tenant_directory_is_never_read_or_removed(self):
        work = self.tenant / 'public_html' / 'x'
        work.mkdir(parents=True)
        secret = self.tenant / 'secret'
        secret.write_text('root:$6$secret-hash Done\n')
        os.symlink(str(secret), str(work / 'status'))
        for data in (dict(backupFile=str(work)), dict(backupFile=str(work) + '.tar.gz'),
                     dict(backupFile=str(work), dir='4821'),
                     dict(backupFile='x', dir='../../tenant/public_html'),
                     dict(backupFile='x', dir='1 %s' % work)):
            result = self.poll(**data)
            self.assertNotIn('secret-hash', json.dumps(result), data)
            self.assertNotEqual(1, result.get('restoreStatus'), data)
        self.root.outputExecutioner.assert_not_called()
        self.root.executioner.assert_not_called()
        self.assertTrue(work.exists())

    def test_restore_that_has_not_started_is_ready_to_run(self):
        (self.backups / 'backup-example.com.tar.gz').write_text('archive')
        self.assertEqual({'restoreStatus': 1, 'error_message': 'None', 'status': 'OK To Run',
                          'running': 'Halted', 'abort': 1}, self.poll(backupFile='backup-example.com.tar.gz'))

    def test_running_restore_reports_its_progress(self):
        self.restore('Extracting Main Archive!\n')
        result = self.poll(backupFile='backup-example.com.tar.gz')
        self.assertEqual((1, 0, 'Running..', 'Extracting Main Archive!\n'),
                         (result['restoreStatus'], result['abort'], result['running'], result['status']))
        self.root.executioner.assert_not_called()

    def test_working_directory_without_a_status_file_has_just_started(self):
        self.restore()
        result = self.poll(backupFile='backup-example.com.tar.gz')
        self.assertEqual((0, 'Running..', 'Just Started'),
                         (result['abort'], result['running'], result['status']))

    def test_finished_and_failed_restores_remove_only_their_working_directory(self):
        for status, running in (('Done', 'Completed'), ('Could not create database [5009]', 'Error')):
            self.root.reset_mock()
            work = self.restore(status, name='backup-%s' % running)
            result = self.poll(backupFile=work.name + '.tar.gz')
            self.assertEqual((1, running), (result['abort'], result['running']))
            self.root.executioner.assert_called_once_with('sudo rm -rf ' + shlex.quote(str(work)))

    def test_transfer_restore_is_read_from_its_numbered_directory(self):
        work = self.backups / 'transfer-4821' / 'backup-example.com'
        work.mkdir(parents=True)
        (work / 'status').write_text('Restoring databases..\n')
        result = self.poll(backupFile='backup-example.com.tar.gz', dir='4821')
        self.assertEqual('Restoring databases..\n', result['status'])

    def test_status_link_from_a_restored_archive_is_reported_as_an_error_and_kept(self):
        work = self.restore()
        secret = self.tenant / 'secret'
        secret.write_text('root:$6$secret-hash Done\n')
        os.symlink(str(secret), str(work / 'status'))
        result = self.poll(backupFile='backup-example.com.tar.gz')
        self.assertNotIn('secret-hash', json.dumps(result))
        self.assertEqual((1, 'Error'), (result['abort'], result['running']))
        self.root.executioner.assert_not_called()
        self.root.outputExecutioner.assert_not_called()


class RestoreStatusPermissionTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'backup/views.py').read_text())
        view = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'restoreStatus')
        self.manager = Mock()
        self.manager.return_value.restoreStatus.return_value = 'progress'
        self.acl = Mock()
        self.acl.loadErrorJson.return_value = 'denied'
        self.namespace = dict(json=json, BackupManager=self.manager, ACLManager=self.acl,
                              redirect=lambda target: 'login', loadLoginPage=object())
        exec(compile(ast.Module(body=[view], type_ignores=[]), 'backup/views.py', 'exec'), self.namespace)

    def call(self, session, acl=None):
        self.acl.loadedACL.return_value = acl
        request = SimpleNamespace(session=session, body=b'{"backupFile": "backup.tar.gz"}')
        return self.namespace['restoreStatus'](request)

    def test_request_without_a_session_is_sent_to_login(self):
        self.assertEqual('login', self.call({}))
        self.manager.return_value.restoreStatus.assert_not_called()

    def test_user_without_restore_permission_is_refused(self):
        for acl in ({'admin': 0, 'restoreBackup': 0}, {'admin': 0}, {}):
            self.assertEqual('denied', self.call({'userID': 7}, acl))
        self.manager.return_value.restoreStatus.assert_not_called()
        self.acl.loadErrorJson.assert_called_with('restoreStatus', 0)

    def test_administrator_and_restore_permission_may_poll(self):
        for acl in ({'admin': 1}, {'admin': 0, 'restoreBackup': 1}, {'admin': 0, 'scheduleBackups': 1}):
            self.assertEqual('progress', self.call({'userID': 7}, acl))
        self.manager.return_value.restoreStatus.assert_called_with({'backupFile': 'backup.tar.gz'})


if __name__ == '__main__':
    unittest.main()
