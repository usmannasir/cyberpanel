import os
import tempfile
import unittest

from plogical.normalBackupUtilities import (
    move_local_backup_archive,
    normalize_local_backup_path,
    prepare_local_backup_run,
)


class NormalBackupUtilitiesTests(unittest.TestCase):

    def test_relative_destination_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'absolute path'):
            normalize_local_backup_path('backup')

    def test_parent_directory_component_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'parent-directory'):
            normalize_local_backup_path('/home/backup/../other')

    def test_filesystem_root_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'filesystem root'):
            normalize_local_backup_path('/')

    def test_absolute_destination_is_normalized(self):
        self.assertEqual('/home/backup/daily', normalize_local_backup_path(' /home//backup/daily/ '))

    def test_archive_is_moved_into_prepared_run_directory(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            destination = os.path.join(temp_dir, 'scheduled backups')
            run_path = prepare_local_backup_run(destination, '08.13.2026_10-00-00')
            archive_path = os.path.join(temp_dir, 'backup-example.com.tar.gz')
            with open(archive_path, 'wb') as archive:
                archive.write(b'backup data')

            moved_path = move_local_backup_archive(archive_path, run_path)

            self.assertEqual(os.path.join(run_path, os.path.basename(archive_path)), moved_path)
            self.assertTrue(os.path.isfile(moved_path))
            self.assertFalse(os.path.exists(archive_path))

    def test_missing_archive_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            run_path = prepare_local_backup_run(temp_dir, '08.13.2026_10-00-00')
            with self.assertRaisesRegex(FileNotFoundError, 'missing or empty'):
                move_local_backup_archive(os.path.join(temp_dir, 'missing.tar.gz'), run_path)


if __name__ == '__main__':
    unittest.main()
