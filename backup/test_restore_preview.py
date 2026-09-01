import json
import os
import unittest
from unittest import mock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

import django

django.setup()

from backup.backupManager import BackupManager


class RestorePreviewTests(unittest.TestCase):

    def test_submit_restore_requires_confirmation(self):
        with mock.patch('backup.backupManager.ACLManager.loadedACL', return_value={'admin': 1}):
            response = BackupManager().submitRestore(
                data={'backupFile': 'example.com-backup.tar.gz'},
                userID=1,
            )

        payload = json.loads(response.content)
        self.assertEqual(0, payload['restoreStatus'])
        self.assertIn('confirmation required', payload['error_message'])

    def test_submit_restore_accepts_confirmed_flag(self):
        with mock.patch('backup.backupManager.ACLManager.loadedACL', return_value={'admin': 1}), mock.patch(
            'backup.backupManager.os.path.exists', return_value=True
        ), mock.patch('backup.backupManager.ProcessUtilities.popenExecutioner') as popen_mock, mock.patch(
            'backup.backupManager.time.sleep'
        ):
            response = BackupManager().submitRestore(
                data={
                    'backupFile': 'example.com-backup.tar.gz',
                    'confirmed': True,
                },
                userID=1,
            )

        payload = json.loads(response.content)
        self.assertEqual(1, payload['restoreStatus'])
        popen_mock.assert_called_once()

    def test_get_backup_file_info_returns_metadata(self):
        backup_name = 'example.com-backup.tar.gz'
        fake_stat = mock.Mock(st_size=1048576, st_mtime=1700000000.0)

        with mock.patch('backup.backupManager.ACLManager.loadedACL', return_value={'admin': 1}), mock.patch(
            'backup.backupManager.os.path.isfile', return_value=True
        ), mock.patch('backup.backupManager.os.stat', return_value=fake_stat), mock.patch(
            'backup.backupManager.os.path.exists', return_value=False
        ), mock.patch('backup.backupManager.time.strftime', return_value='15/11/2023 09:46'):
            response = BackupManager().getBackupFileInfo(
                data={'backupFile': backup_name},
                userID=1,
            )

        payload = json.loads(response.content)
        self.assertEqual(1, payload['infoStatus'])
        self.assertEqual(backup_name, payload['fileName'])
        self.assertEqual('1.00 MB', payload['fileSize'])
        self.assertEqual('15/11/2023 09:46', payload['modified'])
        self.assertEqual(0, payload['restoreInProgress'])

    def test_get_backup_file_info_rejects_path_traversal(self):
        with mock.patch('backup.backupManager.ACLManager.loadErrorJson', return_value=mock.Mock(content=b'{"infoStatus":0}')):
            response = BackupManager().getBackupFileInfo(
                data={'backupFile': '../etc/passwd.tar.gz'},
                userID=1,
            )

        self.assertEqual(b'{"infoStatus":0}', response.content)

    def test_restore_template_includes_confirmation_flow(self):
        template_path = os.path.join(
            os.path.dirname(__file__), 'templates', 'backup', 'restore.html'
        )
        with open(template_path, encoding='utf-8') as template:
            source = template.read()

        self.assertIn('Selected Backup Details', source)
        self.assertIn('Review and Restore', source)
        self.assertIn('Confirm website restore', source)
        self.assertIn('Yes, start restore', source)
        self.assertIn('ng-click="openRestoreConfirm()"', source)

    def test_restore_js_uses_preview_endpoint_and_confirmed_flag(self):
        js_path = os.path.join(os.path.dirname(__file__), 'static', 'backup', 'backup.js')
        with open(js_path, encoding='utf-8') as js_file:
            source = js_file.read()

        self.assertIn('/backup/getBackupFileInfo', source)
        self.assertIn('openRestoreConfirm', source)
        self.assertIn('confirmed: true', source)


if __name__ == '__main__':
    unittest.main()
