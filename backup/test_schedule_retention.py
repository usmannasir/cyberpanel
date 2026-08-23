import json
import os
import unittest
from types import SimpleNamespace
from unittest import mock

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'CyberCP.settings')

import django

django.setup()

from backup.backupManager import BackupManager


class BackupScheduleRetentionTests(unittest.TestCase):

    def test_schedule_update_saves_numeric_retention(self):
        job = SimpleNamespace(
            config=json.dumps({'frequency': 'Daily'}),
            save=mock.Mock(),
        )
        request = SimpleNamespace(
            session={'userID': 1},
            body=json.dumps({
                'selectedJob': 'daily-sites',
                'backupFrequency': 'Weekly',
                'backupRetention': 35,
            }).encode('utf-8'),
        )

        with mock.patch(
            'backup.backupManager.ACLManager.loadedACL', return_value={'admin': 1}
        ), mock.patch(
            'backup.backupManager.ACLManager.currentContextPermission', return_value=1
        ), mock.patch(
            'backup.backupManager.Administrator.objects.get', return_value=SimpleNamespace()
        ), mock.patch(
            'backup.backupManager.NormalBackupJobs.objects.get', return_value=job
        ):
            response = BackupManager().changeAccountFrequencyNormal(request=request)

        payload = json.loads(response.content)
        self.assertEqual(1, payload['status'])
        self.assertEqual(35, json.loads(job.config)['retention'])
        job.save.assert_called_once_with()

    def test_schedule_update_rejects_non_numeric_retention(self):
        job = SimpleNamespace(
            config=json.dumps({'frequency': 'Daily'}),
            save=mock.Mock(),
        )
        request = SimpleNamespace(
            session={'userID': 1},
            body=json.dumps({
                'selectedJob': 'daily-sites',
                'backupFrequency': 'Weekly',
                'backupRetention': '1; touch /tmp/not-run',
            }).encode('utf-8'),
        )

        with mock.patch(
            'backup.backupManager.ACLManager.loadedACL', return_value={'admin': 1}
        ), mock.patch(
            'backup.backupManager.ACLManager.currentContextPermission', return_value=1
        ), mock.patch(
            'backup.backupManager.Administrator.objects.get', return_value=SimpleNamespace()
        ), mock.patch(
            'backup.backupManager.NormalBackupJobs.objects.get', return_value=job
        ):
            response = BackupManager().changeAccountFrequencyNormal(request=request)

        payload = json.loads(response.content)
        self.assertEqual(0, payload['status'])
        self.assertIn('non-negative number of days', payload['error_message'])
        job.save.assert_not_called()

    def test_existing_schedule_response_includes_saved_retention(self):
        job = SimpleNamespace(
            config=json.dumps({
                'frequency': 'Weekly',
                'retention': 35,
                'allSites': 'all',
                'lastRun': '08.23.2026_00-00-00',
                'currentStatus': 'Idle',
            }),
            normalbackupsites_set=SimpleNamespace(all=lambda: []),
        )
        request = SimpleNamespace(
            session={'userID': 1},
            body=json.dumps({
                'selectedAccount': 'weekly-sites',
                'recordsToShow': 10,
                'page': 1,
            }).encode('utf-8'),
        )

        with mock.patch(
            'backup.backupManager.ACLManager.loadedACL', return_value={'admin': 1}
        ), mock.patch(
            'backup.backupManager.ACLManager.currentContextPermission', return_value=1
        ), mock.patch(
            'backup.backupManager.NormalBackupJobs.objects.get', return_value=job
        ), mock.patch(
            's3Backups.s3Backups.S3Backups.getPagination', return_value={'pages': 1}
        ), mock.patch(
            's3Backups.s3Backups.S3Backups.recordsPointer', return_value=(10, 0)
        ):
            response = BackupManager().fetchgNormalSites(request=request)

        payload = json.loads(response.content)
        self.assertEqual(35, payload['retention'])

    def test_retention_field_explains_that_value_is_days(self):
        template_path = os.path.join(
            os.path.dirname(__file__), 'templates', 'backup', 'backupSchedule.html'
        )
        with open(template_path, encoding='utf-8') as template:
            source = template.read()

        self.assertIn('Backup Retention in days (0 = unlimited)', source)


if __name__ == '__main__':
    unittest.main()
