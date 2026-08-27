import os
import io
import tempfile
from unittest import mock

from django.test import SimpleTestCase

from plogical.backupArchive import archive_path_without_suffix
from plogical.remoteTransferNetwork import callback_ip_for_remote
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


class RemoteTransferDeliveryTests(SimpleTestCase):

    @mock.patch('plogical.remoteTransferNetwork.socket.socket')
    @mock.patch('plogical.remoteTransferNetwork.socket.getaddrinfo')
    def test_private_remote_uses_the_routed_local_address(
        self, getaddrinfo, socket_factory
    ):
        getaddrinfo.return_value = [
            (2, 2, 17, '', ('172.16.0.20', 8090)),
        ]
        route_socket = socket_factory.return_value
        route_socket.getsockname.return_value = ('172.16.0.30', 43122)

        self.assertEqual(
            '172.16.0.30',
            callback_ip_for_remote('172.16.0.20', '203.0.113.30'),
        )
        route_socket.connect.assert_called_once_with(('172.16.0.20', 8090))

    @mock.patch('plogical.remoteTransferNetwork.socket.socket')
    @mock.patch('plogical.remoteTransferNetwork.socket.getaddrinfo')
    def test_public_remote_keeps_the_configured_address(
        self, getaddrinfo, socket_factory
    ):
        getaddrinfo.return_value = [
            (2, 2, 17, '', ('8.8.8.8', 8090)),
        ]

        self.assertEqual(
            '198.51.100.30',
            callback_ip_for_remote('8.8.8.8', '198.51.100.30'),
        )
        socket_factory.assert_not_called()

    @mock.patch('plogical.remoteTransferUtilities.subprocess.call')
    def test_scp_failure_keeps_the_archive_and_returns_false(self, call):
        call.return_value = 255
        with tempfile.TemporaryDirectory() as directory:
            archive = os.path.join(directory, 'backup-example.tar.gz')
            with open(archive, 'wb'):
                pass
            output = io.StringIO()

            sent = remoteTransferUtilities.sendBackup(
                archive, '172.16.0.30', '1234', output, '2222'
            )

            self.assertFalse(sent)
            self.assertTrue(os.path.exists(archive))
            self.assertIn('[5010]', output.getvalue())
            command = call.call_args.args[0]
            self.assertIn('2222', command)

    @mock.patch.object(remoteTransferUtilities, 'sendBackup', return_value=False)
    @mock.patch(
        'plogical.remoteTransferUtilities.ProcessUtilities.executioner',
        return_value=None,
    )
    @mock.patch('plogical.remoteTransferUtilities.backupSchedule.createLocalBackup')
    def test_failed_scp_is_not_followed_by_a_success_marker(
        self, create_backup, unused_executioner, unused_send
    ):
        with tempfile.TemporaryDirectory() as directory:
            generated = os.path.join(directory, 'generated-example')
            with open(generated + '.tar.gz', 'wb'):
                pass
            destination = os.path.join(directory, 'transfer-1234')
            os.mkdir(destination)
            log_path = os.path.join(destination, 'backup_log')
            create_backup.return_value = [1, generated]

            remoteTransferUtilities.backupProcess(
                '172.16.0.30',
                destination,
                log_path,
                '1234',
                ['example.com'],
                '2222',
            )

            with open(log_path) as log_file:
                result = log_file.read()
            self.assertNotIn(' Sent ', result)
            self.assertNotIn(
                'Backups are successfully generated and received on', result
            )
