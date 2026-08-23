import os
import tempfile
import time
import unittest

from plogical.normalBackupUtilities import (
    move_local_backup_archive,
    normalize_backup_retention_days,
    normalize_local_backup_path,
    prepare_local_backup_run,
    prune_expired_local_backup_runs,
)


class NormalBackupUtilitiesTests(unittest.TestCase):
    def test_backup_retention_accepts_only_non_negative_whole_days(self):
        self.assertEqual(35, normalize_backup_retention_days(35))
        self.assertEqual(0, normalize_backup_retention_days('0'))
        for value in (-1, '1.5', '1; touch /tmp/not-run', True, None):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_backup_retention_days(value)


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

    def test_only_expired_backup_run_directories_are_pruned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            now = time.time()
            expired = os.path.join(temp_dir, '08.01.2026_00-00-00')
            recent = os.path.join(temp_dir, '08.13.2026_00-00-00')
            unrelated = os.path.join(temp_dir, 'customer-files')
            for path in (expired, recent, unrelated):
                os.mkdir(path)
            os.utime(expired, (now - (4 * 86400), now - (4 * 86400)))
            os.utime(recent, (now - 3600, now - 3600))
            os.utime(unrelated, (now - (30 * 86400), now - (30 * 86400)))

            removed = prune_expired_local_backup_runs(temp_dir, 3, now=now)

            self.assertEqual([expired], removed)
            self.assertFalse(os.path.exists(expired))
            self.assertTrue(os.path.isdir(recent))
            self.assertTrue(os.path.isdir(unrelated))

    def test_zero_retention_keeps_all_backup_runs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            expired = os.path.join(temp_dir, '08.01.2026_00-00-00')
            os.mkdir(expired)
            removed = prune_expired_local_backup_runs(temp_dir, 0, now=time.time())
            self.assertEqual([], removed)
            self.assertTrue(os.path.isdir(expired))

    def test_backup_run_symlink_is_not_pruned(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            target = os.path.join(temp_dir, 'target')
            link = os.path.join(temp_dir, '08.01.2026_00-00-00')
            os.mkdir(target)
            os.symlink(target, link)
            removed = prune_expired_local_backup_runs(temp_dir, 1, now=time.time() + (2 * 86400))
            self.assertEqual([], removed)
            self.assertTrue(os.path.islink(link))


if __name__ == '__main__':
    unittest.main()
