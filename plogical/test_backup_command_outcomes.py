"""BackupRoot must not publish successful results after failed archive commands."""
import ast
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import sys
import tarfile
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import patch
from xml.etree import ElementTree


class BackupCommandOutcomeTests(unittest.TestCase):
    def run_backup(self, failure=None, user='fixture', error=None):
        scratch = tempfile.TemporaryDirectory(prefix='backup-command-outcome-')
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        staging, backup, storage = [root / value for value in ('staging', 'backup', 'storage')]
        for path in (staging, backup, storage):
            path.mkdir()
        domain = root.name + '.invalid'
        meta = staging / 'meta.xml'
        meta.write_text('<metaFile><masterDomain>' + domain + '</masterDomain><ChildDomains/></metaFile>')
        (storage / 'vhost.conf').write_text('Owned fixture\n')
        archive = backup / 'fixture.tar.gz'
        commands, saved = [], []

        class Logger:
            @staticmethod
            def writeToFile(value):
                pass

            @staticmethod
            def statusWriter(path, value):
                Path(path).write_text(value)

        def perform(command, shell):
            words = shlex.split(command)
            program = words[0]
            commands.append(program)
            self.assertIn(program, ('chown', 'mv', 'tar', 'rm', 'chmod', 'echo'))
            for word in words[1:]:
                if word.startswith('/'):
                    path = Path(word.rstrip('/*')).resolve()
                    self.assertTrue(path == root or root in path.parents)
            if program == 'chown':
                return 1, ''
            if error is not None and program == 'mv':
                raise RuntimeError(error(str(root / 'injected')))
            if failure == program:
                if program == 'tar':
                    archive.write_bytes(b'partial archive')
                return 0, 'controlled command failure'
            if program == 'tar' and failure in ('missing', 'empty'):
                if failure == 'empty':
                    archive.touch()
                return 1, ''
            process = subprocess.run(command if shell else words, shell=shell,
                                     capture_output=True, text=True)
            return int(process.returncode == 0), process.stdout + process.stderr

        class Processes:
            @staticmethod
            def executioner(command, owner=None, shell=False):
                # Preserve the root wrapper's historical behavior so a regression
                # cannot accidentally rely on its unconditional success value.
                perform(command, shell)
                return 1

            @staticmethod
            def outputExecutioner(command, owner=None, shell=None, dir=None, retRequired=None):
                self.assertTrue(retRequired)
                return perform(command, shell)

        row = SimpleNamespace(status=0, size=None, save=lambda: saved.append(True))
        source = Path(__file__).with_name('backupUtilities.py').read_text()
        tree = ast.parse(source)
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'backupUtilities')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'BackupRoot')
        wrapper = ast.ClassDef(name='backupUtilities', bases=[], keywords=[], body=[method], decorator_list=[])
        namespace = {'os': os, 'shlex': shlex, 'copy': shutil.copy, 'ElementTree': ElementTree,
                     'logging': SimpleNamespace(CyberCPLogFileWriter=Logger), 'ProcessUtilities': Processes,
                     'Backups': SimpleNamespace(objects=SimpleNamespace(filter=lambda **kwargs: [row]))}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])),
                     '<BackupRoot>', 'exec'), namespace)
        actual = namespace['backupUtilities']
        actual.Server_root = str(root / 'lsws')
        apache = ModuleType('ApachController.ApacheVhosts')
        apache.ApacheVhost = SimpleNamespace(configBasePath=str(root / 'apache') + '/')
        with patch.dict(sys.modules, {'ApachController.ApacheVhosts': apache}):
            actual.BackupRoot(str(staging), 'fixture', str(backup), str(meta), user, str(storage))
        return SimpleNamespace(root=root, archive=archive, saved=saved, commands=commands,
                               status=(backup / 'status').read_text(),
                               pid_exists=Path(str(backup) + 'BackupRoot').exists())

    def assert_failure(self, result):
        self.assertIn('[5009]', result.status)
        self.assertNotIn('Completed', result.status)
        self.assertFalse(result.saved)
        self.assertFalse(result.archive.exists())
        self.assertFalse(result.pid_exists)

    def test_tar_failure_does_not_complete_or_keep_partial_archive(self):
        self.assert_failure(self.run_backup(failure='tar'))

    def test_move_failure_stops_before_archive_creation(self):
        result = self.run_backup(failure='mv')
        self.assert_failure(result)
        self.assertNotIn('tar', result.commands)

    def test_root_status_writer_receives_archive_failure(self):
        self.assert_failure(self.run_backup(failure='tar', user=None))

    def test_command_success_requires_nonempty_archive(self):
        for failure in ('missing', 'empty'):
            with self.subTest(failure=failure):
                self.assert_failure(self.run_backup(failure=failure))

    def test_complete_archive_updates_row_and_visible_status(self):
        result = self.run_backup()
        self.assertEqual('Completed', result.status.strip())
        self.assertTrue(result.saved)
        self.assertFalse(result.pid_exists)
        with tarfile.open(result.archive, 'r:gz') as archive:
            self.assertTrue({'meta.xml', 'vhost.conf'} <= {member.name.removeprefix('./') for member in archive})

    def test_failure_message_is_literal_even_with_shell_punctuation(self):
        message = lambda path: "can't prepare $(touch " + path + "); check archive"
        result = self.run_backup(error=message)
        self.assert_failure(result)
        self.assertIn(message(str(result.root / 'injected')), result.status)
        self.assertFalse((result.root / 'injected').exists())


if __name__ == '__main__':
    unittest.main()
