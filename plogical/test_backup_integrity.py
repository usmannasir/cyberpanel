import io
import tarfile
import tempfile
from unittest import TestCase
from unittest.mock import patch

from plogical.backupIntegrity import archive_is_ready, archive_is_valid, resolve_archive_path


class BackupArchiveReadinessTests(TestCase):
    @patch('plogical.backupIntegrity.time.sleep')
    @patch('plogical.backupIntegrity.os.path.exists', return_value=True)
    @patch('plogical.backupIntegrity.os.path.getsize', side_effect=[10, 20, 20, 20])
    @patch('plogical.backupIntegrity.archive_is_valid', return_value=True)
    def test_archive_must_be_stable_across_three_checks(
            self, archive_valid, getsize, exists, sleep):
        self.assertTrue(archive_is_ready(
            '/tmp/backup.tar.gz', settle_seconds=1, max_wait_seconds=5, stable_checks=3
        ))
        self.assertEqual(getsize.call_count, 4)
        archive_valid.assert_called_once_with('/tmp/backup.tar.gz')

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

    def test_corrupt_archive_is_rejected(self):
        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as archive:
            archive.write(b'not a tar archive')
            archive.flush()
            self.assertFalse(archive_is_valid(archive.name))

    def test_complete_archive_is_accepted(self):
        with tempfile.NamedTemporaryFile(suffix='.tar.gz') as archive:
            with tarfile.open(fileobj=archive, mode='w:gz') as tar:
                content = b'backup content'
                member = tarfile.TarInfo('metadata.txt')
                member.size = len(content)
                tar.addfile(member, io.BytesIO(content))
            archive.flush()
            self.assertTrue(archive_is_valid(archive.name))

    @patch('plogical.backupIntegrity.os.path.exists', return_value=False)
    def test_reported_archive_path_rejects_parent_components(self, exists):
        self.assertIsNone(
            resolve_archive_path(
                'example.com', None, '../../../../tmp/unrelated'
            )
        )
        exists.assert_not_called()
