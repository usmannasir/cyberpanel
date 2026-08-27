import os
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from plogical.backupArchive import archive_path_without_suffix
from plogical.remoteTransferUtilities import remoteTransferUtilities


class BackupArchivePathTests(SimpleTestCase):

    def test_only_the_exact_archive_suffix_is_removed(self):
        self.assertEqual(
            'backup-example.tar',
            archive_path_without_suffix('backup-example.tar.tar.gz'),
        )
        self.assertEqual(
            '/tmp/backup-stage',
            archive_path_without_suffix('/tmp/backup-stage.tar.gz'),
        )
        self.assertEqual(
            'backup-example.zip',
            archive_path_without_suffix('backup-example.zip'),
        )


class RemoteTransferRestoreTests(SimpleTestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.backup_dir = self.temp_dir.name
        self.backup_log = os.path.join(self.backup_dir, 'backup_log')
        open(self.backup_log, 'w').close()

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_archive(self):
        archive = 'backup-example.tar.gz'
        open(os.path.join(self.backup_dir, archive), 'wb').close()
        return archive

    def launcher_with_status(self, status):
        def launch(unused_args):
            restore_dir = os.path.join(self.backup_dir, 'backup-example')
            os.mkdir(restore_dir)
            with open(os.path.join(restore_dir, 'status'), 'w') as status_file:
                status_file.write(status)
            return mock.Mock()
        return launch

    @mock.patch('plogical.remoteTransferUtilities.subprocess.Popen')
    def test_successful_restore_writes_success_marker(self, popen):
        self.create_archive()
        popen.side_effect = self.launcher_with_status('Done')

        remoteTransferUtilities.startRestore(
            self.backup_dir, self.backup_log, '1234'
        )

        with open(self.backup_log) as log_file:
            result = log_file.read()
        self.assertIn('completed[success]', result)
        self.assertNotIn('completed[failed]', result)
        self.assertFalse(os.path.exists(os.path.join(self.backup_dir, 'backup-example')))

    @mock.patch('plogical.remoteTransferUtilities.subprocess.Popen')
    def test_failed_restore_is_not_reported_as_success(self, popen):
        self.create_archive()
        popen.side_effect = self.launcher_with_status('Database error [5009]')

        remoteTransferUtilities.startRestore(
            self.backup_dir, self.backup_log, '1234'
        )

        with open(self.backup_log) as log_file:
            result = log_file.read()
        self.assertIn('completed[failed]', result)
        self.assertNotIn('completed[success]', result)
        self.assertTrue(os.path.exists(os.path.join(self.backup_dir, 'backup-example')))

    @mock.patch('plogical.remoteTransferUtilities.logging.CyberCPLogFileWriter.writeToFile')
    def test_missing_archives_finish_with_failure(self, unused_log):
        remoteTransferUtilities.startRestore(
            self.backup_dir, self.backup_log, '1234'
        )

        with open(self.backup_log) as log_file:
            result = log_file.read()
        self.assertIn('No backup archives were found', result)
        self.assertIn('completed[failed]', result)
