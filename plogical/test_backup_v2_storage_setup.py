"""Backup V2 storage setup: credentials and names from the browser never form a command."""
import ast
import os
from pathlib import Path
import shlex
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from plogical.backupV2Repository import backend_name, rclone_section, remove_section_command

ROOT = Path(__file__).resolve().parents[1]
OTHER_NAMES = ("repo'; id; '", 'repo]\n[other', 'a/b', '../a', '', ' leading', 'x' * 129, None, 7, ['a'], {'a': 1})


class SectionTests(unittest.TestCase):
    def test_section_has_one_line_per_setting(self):
        self.assertEqual('\n[team drive]\ntype = sftp\nhost = backup.example.net\nport = 22\n',
                         rclone_section('team drive', [('type', 'sftp'), ('host', 'backup.example.net'),
                                                       ('port', 22)]))

    def test_name_that_is_not_a_backend_name_is_refused(self):
        for name in OTHER_NAMES:
            with self.assertRaises(ValueError, msg=repr(name)):
                backend_name(name)
            with self.assertRaises(ValueError, msg=repr(name)):
                rclone_section(name, [('type', 'sftp')])

    def test_value_cannot_start_another_line(self):
        for value in ('host\n[other]\ntype = local', 'a\rb', 'a\x00b', None, True, ['a'], {'a': 1}, 1.5):
            with self.assertRaises(ValueError, msg=repr(value)):
                rclone_section('repo', [('host', value)])

    def test_section_is_removed_by_backend_name_only(self):
        command = remove_section_command('team drive.v2', '/home/example.com/.config/rclone/rclone.conf')
        self.assertEqual(['sed', '-i', r'/\[team drive\.v2\]/,/^$/d',
                          '/home/example.com/.config/rclone/rclone.conf'], shlex.split(command))
        for name in OTHER_NAMES:
            with self.assertRaises(ValueError, msg=repr(name)):
                remove_section_command(name, '/home/example.com/.config/rclone/rclone.conf')


class StorageSetupTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'plogical/Backupsv2.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CPBackupsV2')
        self.methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.temporary = Path(holder.name)
        shared = patch('plogical.fileSystemSecurity.SHARED_TEMP_DIRECTORY', holder.name)
        shared.start()
        self.addCleanup(shared.stop)
        modules = patch.dict(sys.modules, {'plogical.acl': SimpleNamespace(
            ACLManager=SimpleNamespace(CreateSecureDir=lambda: None))})
        modules.start()
        self.addCleanup(modules.stop)
        self.calls = []
        self.appended = []

    def output(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        return 'b2JzY3VyZWQ\n' if command.startswith('rclone obscure') else ''

    def execute(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        words = shlex.split(command)
        if words[0] == 'dd':
            self.appended.append(Path(words[1][len('if='):]).read_text())
        if words[0] == 'rm':
            os.remove(words[-1])
        return 1

    def setup(self, config, kind='SFTP'):
        status = type('CPBackupsV2', (), {'SFTP': 1, 'GDrive': 2})
        commands = SimpleNamespace(outputExecutioner=self.output, executioner=self.execute,
                                   debugPath='/does-not-exist')
        from plogical.backupV2Repository import rclone_section as section
        namespace = dict(ProcessUtilities=commands, paramiko=MagicMock(), os=os, shlex=shlex,
                         logging=MagicMock(), CPBackupsV2=status, rclone_section=section)
        for name in ('SetupRcloneBackend', 'AppendRcloneSection'):
            exec(compile(ast.Module(body=[self.methods[name]], type_ignores=[]), 'Backupsv2.py', 'exec'), namespace)
        instance = SimpleNamespace(website=SimpleNamespace(domain='example.com', externalApp='examp1234'))
        instance.AppendRcloneSection = lambda content: namespace['AppendRcloneSection'](instance, content)
        return namespace['SetupRcloneBackend'](instance, getattr(status, kind), config)

    def test_password_is_one_quoted_argument_and_never_reaches_a_privileged_command(self):
        password = "p'a$(id) `id`; ss"
        result = self.setup({'host': 'backup.example.net', 'user': 'backup', 'password': password,
                             'sshPort': '22', 'Repo_Name': 'offsite'})
        self.assertEqual((1, None), result)
        obscure = [(command, user) for command, user in self.calls if command.startswith('rclone obscure')]
        self.assertEqual([(['rclone', 'obscure', password], 'examp1234')],
                         [(shlex.split(command), user) for command, user in obscure])
        for command, user in self.calls:
            if user is None:
                self.assertNotIn('id', shlex.split(command))
                self.assertIn(shlex.split(command)[0], ('chown', 'rm'))
                self.assertTrue(shlex.split(command)[-1].startswith(str(self.temporary)), command)

    def test_section_is_appended_by_the_site_user_from_a_private_file(self):
        self.setup({'host': 'backup.example.net', 'user': 'backup', 'password': 'secret', 'sshPort': 2222,
                    'Repo_Name': 'offsite'})
        self.assertEqual(['\n[offsite]\ntype = sftp\nhost = backup.example.net\nuser = backup\n'
                          'pass = b2JzY3VyZWQ\nport = 2222\n'], self.appended)
        dd = [(command, user) for command, user in self.calls if command.startswith('dd ')]
        self.assertEqual('examp1234', dd[0][1])
        self.assertTrue(dd[0][0].endswith(
            ' of=/home/example.com/.config/rclone/rclone.conf oflag=append conv=notrunc status=none'))
        self.assertEqual([], list(self.temporary.iterdir()))
        self.assertFalse(any(command.startswith('echo') for command, user in self.calls))

    def test_name_or_value_that_would_add_another_section_writes_nothing(self):
        for config in ({'host': 'h', 'user': 'u', 'password': 'p', 'sshPort': '22', 'Repo_Name': 'a]\n[b'},
                       {'host': 'h\n[other]', 'user': 'u', 'password': 'p', 'sshPort': '22', 'Repo_Name': 'ok'},
                       {'host': 'h', 'user': {'a': 1}, 'password': 'p', 'sshPort': '22', 'Repo_Name': 'ok'}):
            self.assertEqual(0, self.setup(config)[0], config)
        self.assertEqual([], self.appended)
        self.assertEqual([], list(self.temporary.iterdir()))

    def test_google_drive_section_is_written_the_same_way(self):
        result = self.setup({'accountname': 'my drive', 'client_id': 'undefined', 'client_secret': 'x',
                             'token': 'ya29.token', 'refresh_token': '1//refresh'}, kind='GDrive')
        self.assertEqual((1, None), result)
        self.assertTrue(self.appended[0].startswith('\n[my drive]\ntype = drive\nscope = drive\nclient_id = \n'))
        self.assertIn('"access_token":"ya29.token"', self.appended[0])


class RepositoryRemovalTests(unittest.TestCase):
    def test_only_a_backend_name_selects_the_section_to_remove(self):
        tree = ast.parse((ROOT / 'plogical/Backupsv2.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CPBackupsV2')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef)
                      and node.name == 'DeleteRepoScheduleV2')
        method.decorator_list = []
        commands = MagicMock()
        namespace = dict(ProcessUtilities=commands, remove_section_command=remove_section_command,
                         os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: True)))
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'Backupsv2.py', 'exec'), namespace)
        delete = namespace['DeleteRepoScheduleV2']
        for name in OTHER_NAMES:
            self.assertEqual(0, delete('example.com', name, 'examp1234')[0], repr(name))
        commands.outputExecutioner.assert_not_called()
        self.assertEqual((1, 'Done'), delete('example.com', 'offsite', 'examp1234'))
        command, user = commands.outputExecutioner.call_args.args[:2]
        self.assertEqual('examp1234', user)
        self.assertEqual(['sed', '-i', r'/\[offsite\]/,/^$/d', '/home/example.com/.config/rclone/rclone.conf'],
                         shlex.split(command))


class ConfigReadTests(unittest.TestCase):
    def test_the_sites_storage_configuration_is_read_as_the_site_user(self):
        source = (ROOT / 'IncBackups/views.py').read_text()
        self.assertEqual(2, source.count("pu.outputExecutioner(command, obj.externalApp)"))
        self.assertNotIn("        command = 'cat %s'%(path)\n        result = pu.outputExecutioner(command)\n", source)


if __name__ == '__main__':
    unittest.main()
