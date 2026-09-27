"""Exercise metadata creation and lifetime without requiring a panel database."""
import ast
import json
import os
from pathlib import Path
import shlex
import stat
import sys
import tempfile
import time
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from xml.dom import minidom
from xml.etree import ElementTree as ET


class BackupTemporaryMetadataTests(unittest.TestCase):
    def setUp(self):
        self.scratch = tempfile.TemporaryDirectory()
        self.addCleanup(self.scratch.cleanup)
        self.paths = []
        self.logs = []
        self.process = SimpleNamespace(debugPath='/nonexistent-debug', executioner=Mock(),
                                       outputExecutioner=Mock(return_value=''))
        admin = SimpleNamespace(**dict.fromkeys(('userName', 'password', 'firstName', 'lastName',
            'email', 'type', 'owner', 'token', 'api', 'securityLevel', 'state', 'initWebsitesLimit'), 'fixture'))
        admin.acl = SimpleNamespace(name='admin')
        self.website = SimpleNamespace(admin=admin, phpSelection='PHP 8.3', externalApp='fixture',
            config='{}', childdomains_set=SimpleNamespace(all=lambda: []),
            databases_set=SimpleNamespace(all=lambda: []))
        self.row = SimpleNamespace(save=Mock())
        ns = dict(os=os, tempfile=tempfile, shlex=shlex, time=time, Element=ET.Element,
            SubElement=ET.SubElement, ElementTree=ET, minidom=minidom, VERSION='3.0', BUILD=7,
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda **kw: self.website)),
            Backups=lambda **kw: self.row, ProcessUtilities=self.process,
            mysqlUtilities=SimpleNamespace(mysqlUtilities=SimpleNamespace(setupConnection=lambda: (None, None))),
            logging=SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=self.logs.append)),
            build_dns_records_xml=lambda rows: ET.Element('dnsrecords'),
            build_email_accounts_xml=lambda rows: ET.Element('emails'),
            generate_pass=lambda n: 'fixture',
            virtualHostUtilities=SimpleNamespace(cyberPanel='/usr/local/CyberCP'))
        source = ast.parse(Path(__file__).with_name('backupUtilities.py').read_text())
        cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and n.name == 'backupUtilities')
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name in
                    ('prepareBackupMeta', 'cleanupBackupMeta')]
        submit = next(n for n in source.body if isinstance(n, ast.FunctionDef) and n.name == 'submitBackupCreation')
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls, submit], type_ignores=[])),
                     '<backup-metadata>', 'exec'), ns)
        self.backup = ns['backupUtilities']
        self.submit = ns['submitBackupCreation']
        factory = self.real_factory = tempfile.NamedTemporaryFile
        def create(**kw):
            self.assertEqual('/tmp', kw.pop('dir'))
            file = factory(dir=self.scratch.name, **kw)
            self.paths.append(file.name)
            self.assertEqual(0o600, stat.S_IMODE(os.stat(file.name).st_mode))
            return file
        self.factory = patch.object(tempfile, 'NamedTemporaryFile', side_effect=create)
        self.factory.start()
        self.addCleanup(self.factory.stop)

    def prepare(self, inner=0):
        return self.backup.prepareBackupMeta('fixture.invalid', 'fixture', self.scratch.name,
                                             self.scratch.name, inner)

    def test_unique_private_files_preserve_metadata(self):
        previous = os.umask(0)
        try:
            results = [self.prepare() for _ in range(20)]
        finally:
            os.umask(previous)
        self.assertEqual(20, len(set(self.paths)))
        for result in results:
            self.assertEqual(1, result[0])
            self.assertEqual('fixture', ET.parse(result[2]).findtext('userPassword'))
            self.assertEqual(0o600, stat.S_IMODE(os.stat(result[2]).st_mode))

    def test_preparation_error_removes_file(self):
        self.row.save.side_effect = RuntimeError('injected save failure')
        self.assertEqual(0, self.prepare(inner=1)[0])
        self.assertEqual(1, len(self.paths))
        self.assertFalse(os.path.exists(self.paths[0]))

    def test_write_error_removes_partial_file(self):
        create = self.real_factory
        def failing_create(**kw):
            kw['dir'] = self.scratch.name
            file = create(**kw)
            self.paths.append(file.name)
            file.write = Mock(side_effect=OSError('injected disk full'))
            return file
        with patch.object(tempfile, 'NamedTemporaryFile', side_effect=failing_create):
            self.assertEqual(0, self.prepare()[0])
        self.assertFalse(os.path.exists(self.paths[0]))

    def run_submission(self, error=None, output=''):
        self.process.outputExecutioner.return_value = output
        self.process.outputExecutioner.side_effect = error
        scheduler = ModuleType('plogical.IncScheduler')
        scheduler.IncScheduler = object()
        information = ModuleType('plogical.getSystemInformation')
        information.SystemInformation = object()
        # Redirect only the scheduler marker; all real metadata IO remains exercised.
        real_open = open
        def local_open(path, *args, **kwargs):
            if path == '/home/cyberpanel/fixture.invalid-backup.txt':
                path = os.path.join(self.scratch.name, 'scheduler')
            return real_open(path, *args, **kwargs)
        with patch.dict(sys.modules, {'plogical.IncScheduler': scheduler,
                        'plogical.getSystemInformation': information}), patch('builtins.open', local_open):
            self.submit(self.scratch.name, 'fixture', self.scratch.name, 'fixture.invalid')
        self.assertEqual(1, len(self.paths))
        self.assertFalse(os.path.exists(self.paths[0]))

    def test_success_cleans_file_and_preserves_ownership_handoff(self):
        self.run_submission()
        commands = [call.args[0] for call in self.process.executioner.call_args_list]
        self.assertIn('chown fixture:fixture ' + self.paths[0], commands)
        self.assertIn('chown cyberpanel:cyberpanel ' + self.paths[0], commands)
        self.assertTrue(any(' BackupRoot ' in command for command in commands))

    def test_subprocess_exception_cleans_file(self):
        self.run_submission(error=RuntimeError('injected failure'))
        self.assertTrue(any('fixture.invalid: injected failure' in line for line in self.logs))

    def test_subprocess_error_return_cleans_file(self):
        self.run_submission(output='injected failure [5009]')
        self.assertFalse(any(' BackupRoot ' in call.args[0] for call in self.process.executioner.call_args_list))

    def run_incremental(self, move_fails=False):
        source = ast.parse(Path(__file__).parent.parent.joinpath('IncBackups/IncBackupsControl.py').read_text())
        cls = next(n for n in source.body if isinstance(n, ast.ClassDef) and
                   any(isinstance(m, ast.FunctionDef) and m.name == 'prepareBackupMeta' for m in n.body))
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'prepareBackupMeta')
        method.decorator_list = []
        logger = SimpleNamespace(writeToFile=self.logs.append, statusWriter=Mock())
        namespace = dict(os=os, ProcessUtilities=self.process, logging=logger)
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])),
                     '<incremental-metadata>', 'exec'), namespace)
        module = ModuleType('plogical.backupUtilities')
        module.backupUtilities = self.backup
        destination = os.path.join(self.scratch.name, 'meta.xml')
        def move(command, user, **kw):
            if move_fails:
                return 0, 'injected move error'
            os.rename(shlex.split(command)[1], destination)
            return 1, ''
        self.process.outputExecutioner.side_effect = move
        instance = SimpleNamespace(website=SimpleNamespace(domain='fixture.invalid'),
                                   externalApp='fixture', statusPath='fixture-status')
        with patch.dict(sys.modules, {'plogical.backupUtilities': module}):
            result = namespace['prepareBackupMeta'](instance)
        self.assertFalse(os.path.exists(self.paths[0]))
        return result, destination

    def test_incremental_move_preserves_metadata_and_cleans_source(self):
        result, destination = self.run_incremental()
        self.assertEqual(1, result)
        self.assertEqual('fixture', ET.parse(destination).findtext('userPassword'))

    def test_incremental_move_failure_cleans_source_and_reports_failure(self):
        result, destination = self.run_incremental(move_fails=True)
        self.assertEqual(0, result)
        self.assertFalse(os.path.exists(destination))

    def test_site_owned_file_uses_privileged_cleanup(self):
        path = self.prepare()[2]
        real_unlink = os.unlink
        def privileged(command, user, **kw):
            self.assertEqual(['rm', '-f', '--', path], shlex.split(command))
            self.assertEqual('root', user)
            self.assertTrue(kw['retRequired'])
            real_unlink(path)
            return 1, ''
        self.process.outputExecutioner.side_effect = privileged
        with patch.object(os, 'unlink', side_effect=PermissionError('sticky directory')):
            self.backup.cleanupBackupMeta(path)
        self.assertFalse(os.path.exists(path))

    def test_cleanup_failure_is_logged_without_masking_backup_error(self):
        self.process.outputExecutioner.return_value = (0, 'injected transport error')
        with patch.object(os, 'unlink', side_effect=PermissionError('sticky directory')):
            self.backup.cleanupBackupMeta('/tmp/fixture.xml')
        self.assertTrue(any('injected transport error' in line for line in self.logs))


if __name__ == '__main__':
    unittest.main()
