"""Stage failures must stop a backup before databases and archive publication."""
import ast
from contextlib import redirect_stdout
import io
import os
from pathlib import Path
import shlex
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from xml.etree import ElementTree

from plogical.backupExcludes import rsync_exclude_arguments
from plogical.backupIntegrity import backup_command_error


class BackupStagingTests(unittest.TestCase):
    def run_staging(self, diagnostic=None, missing_source=False):
        scratch = tempfile.TemporaryDirectory(prefix='backup-staging-')
        self.addCleanup(scratch.cleanup)
        root = Path(scratch.name)
        backup, staging, source = [root / name for name in ('backup', 'staging', 'source')]
        for path in (backup, staging, source):
            path.mkdir()
        (source / 'index.html').write_text('fixture content')
        meta = root / 'meta.xml'
        meta.write_text('<metaFile><masterDomain>fixture.invalid</masterDomain></metaFile>')
        logged, commands = [], []

        def execute(argv, **kwargs):
            # Substitute only the hardcoded source with an owned fixture. All
            # other arguments and the actual rsync process remain unchanged.
            self.assertEqual('rsync', argv[0])
            self.assertNotIn('sudo', argv)
            self.assertEqual('/home/fixture.invalid/', argv[-2])
            self.assertEqual(str(staging) + '/public_html/', argv[-1])
            commands.append(argv)
            if diagnostic is not None:
                return SimpleNamespace(returncode=23, stdout=diagnostic)
            argv[-2] = str(root / 'missing' if missing_source else source) + '/'
            return subprocess.run(argv, **kwargs)

        def legacy_execute(command):
            execute(shlex.split(command), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    encoding='utf-8', errors='replace')
            return 0

        namespace = {
            'os': os, 'shlex': shlex, 'ElementTree': ElementTree,
            'subprocess': SimpleNamespace(run=execute, PIPE=subprocess.PIPE, STDOUT=subprocess.STDOUT),
            'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(
                writeToFile=logged.append, statusWriter=lambda path, value: Path(path).write_text(value))),
            'ProcessUtilities': SimpleNamespace(normalExecutioner=legacy_execute),
            'rsync_exclude_arguments': rsync_exclude_arguments,
            'backup_command_error': backup_command_error,
        }
        tree = ast.parse(Path(__file__).with_name('backupUtilities.py').read_text())
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'backupUtilities')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'startBackup')
        wrapper = ast.ClassDef(name='backupUtilities', bases=[], keywords=[], body=[method], decorator_list=[])
        exec(compile(ast.fix_missing_locations(ast.Module(body=[wrapper], type_ignores=[])),
                     '<startBackup>', 'exec'), namespace)
        output = io.StringIO()
        with redirect_stdout(output):
            namespace['backupUtilities'].startBackup(str(staging), 'fixture', str(backup), str(meta))
        return SimpleNamespace(status=(backup / 'status').read_text(), output=output.getvalue(),
                               logs=logged, staging=staging, commands=commands,
                               pid_exists=Path(str(backup) + 'startBackup').exists())

    def test_quota_failure_stops_staging_and_preserves_error(self):
        result = self.run_staging(diagnostic='rsync: write failed: Disk quota exceeded (122)')
        self.assertIn('[5009]', result.status)
        self.assertIn('rsync exit 23', result.status)
        self.assertIn('Disk quota exceeded', result.output)
        self.assertNotIn('1,None', result.output)
        self.assertNotIn('Backing up databases', result.status)
        self.assertTrue(any('Disk quota exceeded' in log for log in result.logs))
        self.assertFalse(result.pid_exists)

    @unittest.skipUnless(shutil.which('rsync'), 'requires real rsync')
    def test_real_rsync_copies_complete_fixture(self):
        result = self.run_staging()
        self.assertEqual('fixture content', (result.staging / 'public_html/index.html').read_text())
        self.assertIn('Backing up databases', result.status)
        self.assertIn('1,None', result.output)
        self.assertFalse(result.pid_exists)

    @unittest.skipUnless(shutil.which('rsync'), 'requires real rsync')
    def test_real_rsync_failure_never_advances(self):
        result = self.run_staging(missing_source=True)
        self.assertIn('[5009]', result.status)
        self.assertIn('No such file or directory', result.output)
        self.assertNotIn('1,None', result.output)

    def test_diagnostics_are_bounded_and_empty_output_is_explicit(self):
        error = backup_command_error('tar', 'x' * 10000 + 'Disk quota exceeded')
        self.assertLess(len(error), 4200)
        self.assertTrue(error.endswith('Disk quota exceeded'))
        self.assertIn('without diagnostic output', backup_command_error('tar', ''))


if __name__ == '__main__':
    unittest.main()
