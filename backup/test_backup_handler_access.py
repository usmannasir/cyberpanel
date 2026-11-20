"""Backup progress belongs to a website's owner; a transfer is cancelled only by its number."""
import ast
import json
from pathlib import Path
import shlex
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical import securityUtils
from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]


class BackupStatusOwnershipTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'backup/views.py').read_text())
        view = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'backupStatus')
        self.manager = Mock()
        self.manager.return_value.backupStatus.return_value = 'progress'
        self.acl = Mock()
        self.acl.loadErrorJson.return_value = 'denied'
        self.acl.loadedACL.return_value = {'admin': 0}
        self.administrators = Mock()
        self.namespace = dict(json=json, BackupManager=self.manager, ACLManager=self.acl,
                              Administrator=self.administrators,
                              redirect=lambda target: 'login', loadLoginPage=object())
        exec(compile(ast.Module(body=[view], type_ignores=[]), 'backup/views.py', 'exec'), self.namespace)

    def call(self, session=None, body=None):
        request = SimpleNamespace(session={'userID': 7} if session is None else session,
                                  body=json.dumps(body or {'websiteToBeBacked': 'owned.example'}).encode())
        return self.namespace['backupStatus'](request)

    def test_owner_reads_progress_as_the_signed_in_user(self):
        self.acl.checkOwnership.return_value = 1
        self.assertEqual('progress', self.call())
        self.acl.loadedACL.assert_called_once_with(7)
        self.administrators.objects.get.assert_called_once_with(pk=7)
        self.assertEqual('owned.example', self.acl.checkOwnership.call_args[0][0])
        self.manager.return_value.backupStatus.assert_called_once_with(7, {'websiteToBeBacked': 'owned.example'})

    def test_another_users_website_is_refused(self):
        self.acl.checkOwnership.return_value = 0
        self.assertEqual('denied', self.call(body={'websiteToBeBacked': 'other.example'}))
        self.manager.return_value.backupStatus.assert_not_called()

    def test_unknown_website_or_missing_name_is_refused(self):
        self.acl.checkOwnership.side_effect = RuntimeError('Websites matching query does not exist.')
        self.assertEqual('denied', self.call(body={'websiteToBeBacked': 'missing.example'}))
        self.assertEqual('denied', self.call(body={'something': 'else'}))
        self.manager.return_value.backupStatus.assert_not_called()

    def test_request_without_a_session_is_sent_to_login(self):
        self.assertEqual('login', self.call(session={}))
        self.manager.return_value.backupStatus.assert_not_called()


class CancelRemoteBackupTests(unittest.TestCase):
    def setUp(self):
        self.root = Mock()
        self.root.outputExecutioner.return_value = '4242\n'
        self.remote = Mock()
        self.remote.post.return_value = SimpleNamespace(text='{"cancelStatus": 1}')
        self.acl = Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.loadErrorJson.return_value = SimpleNamespace(content=b'{"cancelStatus": 0}')
        self.cancel = load_method('backup/backupManager.py', 'BackupManager', 'cancelRemoteBackup', dict(
            json=json, shlex=shlex, requests=self.remote, ACLManager=self.acl, ProcessUtilities=self.root,
            logging=SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=Mock())),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode())))

    def run_cancel(self, transfer):
        data = {'ipAddress': '198.51.100.7', 'password': 'remote-password', 'dir': transfer}
        return json.loads(self.cancel(None, userID=1, data=data).content)

    def commands(self):
        return [call[0][0] for call in self.root.outputExecutioner.call_args_list
                + self.root.executioner.call_args_list]

    def test_numbered_transfer_is_cancelled_in_its_own_directory(self):
        self.assertEqual(1, self.run_cancel('4821')['cancelStatus'])
        directory = securityUtils.get_remote_transfer_dir_path('4821')
        self.assertEqual(['sudo cat ' + shlex.quote(directory + '/pid'), 'sudo kill -KILL 4242',
                          'sudo rm -rf ' + shlex.quote(directory)], self.commands())

    def test_anything_but_a_transfer_number_runs_no_command_and_contacts_no_server(self):
        for transfer in ('4821 /etc', '../../etc', '4821/../..', '', 'abc', '-1', None, ['4821'],
                         '1' * 13, '4821\n'):
            self.assertEqual(0, self.run_cancel(transfer)['cancelStatus'], repr(transfer))
        self.assertEqual([], self.commands())
        self.remote.post.assert_not_called()

    def test_process_is_signalled_only_for_a_plain_process_number(self):
        for content in ('1 2', '-1', '4242; id', 'cat: pid: No such file or directory', ''):
            self.root.reset_mock()
            self.root.outputExecutioner.return_value = content
            self.assertEqual(1, self.run_cancel('4821')['cancelStatus'], repr(content))
            self.assertFalse(any('kill' in command for command in self.commands()), repr(content))
            self.assertTrue(any(command.startswith('sudo rm -rf ') for command in self.commands()))


if __name__ == '__main__':
    unittest.main()
