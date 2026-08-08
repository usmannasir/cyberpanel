from unittest import TestCase
from unittest.mock import patch

from plogical.backupIntegrity import archive_is_ready, resolve_archive_path


class BackupArchiveReadinessTests(TestCase):
    @patch('plogical.backupIntegrity.time.sleep')
    @patch('plogical.backupIntegrity.os.path.exists', return_value=True)
    @patch('plogical.backupIntegrity.os.path.getsize', side_effect=[10, 20, 20, 20])
    def test_archive_must_be_stable_across_three_checks(self, getsize, exists, sleep):
        self.assertTrue(archive_is_ready(
            '/tmp/backup.tar.gz', settle_seconds=1, max_wait_seconds=5, stable_checks=3
        ))
        self.assertEqual(getsize.call_count, 4)

    @patch('plogical.backupIntegrity.time.sleep')
    @patch('plogical.backupIntegrity.os.path.exists', return_value=True)
    @patch('plogical.backupIntegrity.os.path.getsize', return_value=0)
    def test_empty_archive_is_rejected(self, getsize, exists, sleep):
        self.assertFalse(archive_is_ready(
            '/tmp/backup.tar.gz', settle_seconds=1, max_wait_seconds=2, stable_checks=3
        ))

    @patch('plogical.backupIntegrity.os.path.exists')
    def test_resolves_reported_archive_path(self, exists):
        expected = '/home/example.com/backup/backup-example.com.tar.gz'
        exists.side_effect = lambda path: path == expected

        self.assertEqual(
            resolve_archive_path(
                'example.com', '/tmp/missing-backup', 'backup-example.com'
            ),
            expected
        )
