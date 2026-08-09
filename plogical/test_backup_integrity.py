import io
import os
import tarfile
import tempfile
from unittest import TestCase
from unittest.mock import patch

from plogical.backupIntegrity import (
    UnsafeArchiveError,
    archive_is_ready,
    archive_is_valid,
    resolve_archive_path,
    safe_extract,
)


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

    def test_safe_extract_accepts_regular_backup_content(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                content = b'backup content'
                member = tarfile.TarInfo('public_html/index.html')
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with tarfile.open(archive_path, mode='r:*') as archive:
                safe_extract(archive, destination)
            with open(os.path.join(destination, 'public_html/index.html'), 'rb') as restored:
                self.assertEqual(b'backup content', restored.read())

    @patch('plogical.backupIntegrity.sys.version_info', (3, 11))
    def test_safe_extract_supports_python_before_data_filter(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                content = b'legacy runtime content'
                member = tarfile.TarInfo('public_html/index.html')
                member.size = len(content)
                member.uid = 1234
                member.gid = 1234
                member.mode = 0o4755
                archive.addfile(member, io.BytesIO(content))
            with tarfile.open(archive_path, mode='r:*') as archive:
                safe_extract(archive, destination)
            restored_path = os.path.join(destination, 'public_html/index.html')
            with open(restored_path, 'rb') as restored:
                self.assertEqual(b'legacy runtime content', restored.read())
            self.assertEqual(0, os.stat(restored_path).st_mode & 0o7000)

    def test_safe_extract_rejects_parent_traversal(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            escaped_path = os.path.join(test_dir, 'escaped.txt')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                content = b'escaped'
                member = tarfile.TarInfo('../escaped.txt')
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with tarfile.open(archive_path, mode='r:*') as archive:
                with self.assertRaises(UnsafeArchiveError):
                    safe_extract(archive, destination)
            self.assertFalse(os.path.exists(escaped_path))

    def test_safe_extract_rejects_links_outside_destination(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                member = tarfile.TarInfo('public_html/config-link')
                member.type = tarfile.SYMTYPE
                member.linkname = '../../../etc/passwd'
                archive.addfile(member)
            with tarfile.open(archive_path, mode='r:*') as archive:
                with self.assertRaises(UnsafeArchiveError):
                    safe_extract(archive, destination)

    def test_safe_extract_accepts_links_inside_destination(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                content = b'backup content'
                target = tarfile.TarInfo('public_html/config.php')
                target.size = len(content)
                archive.addfile(target, io.BytesIO(content))
                link = tarfile.TarInfo('public_html/current-config.php')
                link.type = tarfile.SYMTYPE
                link.linkname = 'config.php'
                archive.addfile(link)
            with tarfile.open(archive_path, mode='r:*') as archive:
                safe_extract(archive, destination)
            with open(os.path.join(destination, 'public_html/current-config.php'), 'rb') as restored:
                self.assertEqual(b'backup content', restored.read())

    def test_safe_extract_rejects_hard_links_outside_destination(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                member = tarfile.TarInfo('public_html/config-link')
                member.type = tarfile.LNKTYPE
                member.linkname = '../outside.txt'
                archive.addfile(member)
            with tarfile.open(archive_path, mode='r:*') as archive:
                with self.assertRaises(UnsafeArchiveError):
                    safe_extract(archive, destination)

    def test_safe_extract_rejects_special_files(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            with tarfile.open(archive_path, mode='w:gz') as archive:
                member = tarfile.TarInfo('public_html/named-pipe')
                member.type = tarfile.FIFOTYPE
                archive.addfile(member)
            with tarfile.open(archive_path, mode='r:*') as archive:
                with self.assertRaises(UnsafeArchiveError):
                    safe_extract(archive, destination)

    def test_safe_extract_rejects_existing_symlink_escape(self):
        with tempfile.TemporaryDirectory() as test_dir:
            archive_path = os.path.join(test_dir, 'backup.tar.gz')
            destination = os.path.join(test_dir, 'restore')
            outside = os.path.join(test_dir, 'outside')
            os.makedirs(destination)
            os.makedirs(outside)
            os.symlink(outside, os.path.join(destination, 'public_html'))
            with tarfile.open(archive_path, mode='w:gz') as archive:
                content = b'escaped'
                member = tarfile.TarInfo('public_html/index.html')
                member.size = len(content)
                archive.addfile(member, io.BytesIO(content))
            with tarfile.open(archive_path, mode='r:*') as archive:
                with self.assertRaises(UnsafeArchiveError):
                    safe_extract(archive, destination)
            self.assertFalse(os.path.exists(os.path.join(outside, 'index.html')))
