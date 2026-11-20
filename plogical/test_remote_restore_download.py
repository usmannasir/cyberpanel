"""A restore downloads its archive; the storage host never receives a key for this server."""
import ast
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from plogical.securityUtils import is_safe_file_name

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'plogical/applicationInstaller.py').read_text()


class FileNameTests(unittest.TestCase):
    def test_single_names_are_accepted(self):
        for name in ('backup-example.com-02.11.2026_10-22-33.tar.gz', 'example.com', 'wp_backup_1', 'a'):
            self.assertTrue(is_safe_file_name(name), name)

    def test_paths_and_other_values_are_refused(self):
        for name in ('a/b', '../a', 'a..b', '/etc/passwd', 'a b', 'a;b', '$(id)', '-a', '.hidden', '',
                     'a\n', 'x' * 256, None, 7, ['a']):
            self.assertFalse(is_safe_file_name(name), repr(name))


class RestoreSourceTests(unittest.TestCase):
    def test_no_restore_gives_a_remote_host_a_key_for_this_server(self):
        for text in ('authorized_keys', 'cyberpanelbackup', 'ssh-keygen', 'scp -o', 'root@{ACLManager.fetchIP()}',
                     'chmod 755 /home/cyberpanel'):
            self.assertNotIn(text, SOURCE, text)

    def test_both_restores_download_over_their_own_connection(self):
        self.assertIn('sftp.get(str(remotepath), str(loaclpath),\n                         callback=self.UpdateDownloadStatus)\n', SOURCE)
        self.assertIn('sftp.get(remotepath, loaclpath, callback=self.UpdateDownloadStatus)\n', SOURCE)
        self.assertIn('if not is_safe_file_name(BackUpFileName):', SOURCE)
        self.assertIn('if not is_safe_file_name(folder) or not is_safe_file_name(backupfile):', SOURCE)


class StopAfterDownload(BaseException):
    pass


class OneClickRestoreTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(SOURCE)
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                   and node.name == 'ApplicationInstaller')
        self.method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                           and node.name == 'StartOCRestore')
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.status = Path(holder.name, 'status')
        self.ssh = MagicMock()
        self.ssh.exec_command.side_effect = AssertionError('a command was run on the backup host')
        self.sftp = self.ssh.open_sftp.return_value
        self.paramiko = MagicMock()
        self.paramiko.SSHClient.return_value = self.ssh
        self.commands = MagicMock()
        self.commands.debugPath = '/does-not-exist'
        self.commands.outputExecutioner.return_value = 'private-key-text\n'
        self.commands.executioner.side_effect = StopAfterDownload()

    def restore(self, folder, backupfile):
        namespace = dict(paramiko=self.paramiko, ProcessUtilities=self.commands, json=json,
                         os=__import__('os'), StringIO=__import__('io').StringIO, logging=MagicMock(),
                         NormalBackupDests=MagicMock(), ACLManager=MagicMock(), time=MagicMock())
        namespace['NormalBackupDests'].objects.get.return_value = SimpleNamespace(config='{"ip": "198.51.100.9"}')
        exec(compile(ast.Module(body=[self.method], type_ignores=[]), 'applicationInstaller.py', 'exec'), namespace)
        installer = SimpleNamespace(extraArgs=dict(id=1, folder=folder, backupfile=backupfile,
                                                   tempStatusPath=str(self.status), userID=1),
                                    UpdateDownloadStatus=lambda transferred, total: None)
        models = SimpleNamespace(OneClickBackups=MagicMock())
        models.OneClickBackups.objects.get.return_value = SimpleNamespace(sftpUser='backupuser')
        with patch.dict(sys.modules, {'IncBackups.models': models}):
            try:
                return namespace['StartOCRestore'](installer)
            except StopAfterDownload:
                return 'downloaded'

    def test_selection_that_is_not_a_plain_name_stops_before_any_connection(self):
        for folder, backupfile in (('example.com', '../../etc/cron.d/x'), ('a/b', 'backup.tar.gz'),
                                   ('example.com', 'backup.tar.gz /root/.ssh/authorized_keys'),
                                   ('example.com; id', 'backup.tar.gz'), ({'a': 1}, 'backup.tar.gz'),
                                   ('example.com', ['backup.tar.gz'])):
            self.assertEqual(0, self.restore(folder, backupfile), (folder, backupfile))
            self.assertIn('[404]', self.status.read_text())
        self.paramiko.SSHClient.assert_not_called()
        self.commands.outputExecutioner.assert_not_called()
        self.commands.executioner.assert_not_called()

    def test_archive_is_downloaded_and_nothing_is_run_on_the_backup_host(self):
        # The routine handles its own errors; what matters is what it did before the
        # first privileged command (stopped here) and that the download happened.
        self.restore('example.com', 'backup-example.com.tar.gz')
        arguments = self.sftp.get.call_args
        self.assertEqual(('cpbackups/example.com/backup-example.com.tar.gz',
                          '/home/cyberpanel/backup-example.com.tar.gz'), arguments.args)
        self.ssh.exec_command.assert_not_called()
        privileged = [call.args[0] for call in self.commands.outputExecutioner.call_args_list
                      + self.commands.executioner.call_args_list]
        for command in privileged:
            self.assertNotIn('.ssh/authorized_keys', command)
            self.assertNotIn('chmod', command)


if __name__ == '__main__':
    unittest.main()
