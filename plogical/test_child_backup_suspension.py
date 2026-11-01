"""Independent child suspension survives current and legacy backup formats."""
import ast
import contextlib
import json
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree

from plogical.childDomainState import (
    normalize_child_state, child_backup_record, append_child_backup_xml,
)
from plogical import websiteSuspension
from plogical.test_child_creation_suspension import load_creation_methods


def method_ast(file_name, cls_name, method_name):
    source = Path(__file__).with_name(file_name)
    tree = ast.parse(source.read_text(encoding='utf-8'))
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == cls_name)
    return next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == method_name)


class ChildBackupMetadataTests(unittest.TestCase):
    def test_xml_and_json_keep_independent_suspension(self):
        child = SimpleNamespace(domain='child.test', path='/home/site/child', phpSelection='PHP 8.3', state=0)
        record = child_backup_record(child)
        self.assertEqual(json.loads(json.dumps(record))['state'], 0)
        xml = ElementTree.Element('ChildDomains')
        append_child_backup_xml(xml, child)
        parsed = ElementTree.fromstring(ElementTree.tostring(xml))
        self.assertEqual(normalize_child_state(parsed.findtext('domain/state')), 0)
        self.assertEqual(parsed.findtext('domain/domain'), child.domain)

    def test_legacy_missing_state_defaults_active_independent_state(self):
        self.assertEqual(normalize_child_state(None), 1)
        self.assertEqual(normalize_child_state({}.get('state')), 1)
        self.assertEqual(normalize_child_state(ElementTree.fromstring('<domain/>').findtext('state')), 1)

    def test_invalid_backup_state_is_not_silently_restored_as_active(self):
        for value in ('', 'active', '2', 2, -1, {}, [], False, True, 0.0, 1.0):
            with self.subTest(value=value), self.assertRaises(ValueError):
                normalize_child_state(value)

    def test_actual_json_backup_writer_keeps_child_state(self):
        method = method_ast('backupUtilities.py', 'backupUtilities', 'BackupData')
        method.decorator_list = []
        ns = {'ProcessUtilities': MagicMock()}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'BackupData', 'exec'), ns)
        with tempfile.TemporaryDirectory() as temp:
            child = SimpleNamespace(domain='child.test', path='/home/site/child', phpSelection='PHP 8.3', state=0)
            website = MagicMock()
            website.childdomains_set.all.return_value = [child]
            instance = SimpleNamespace(BackupPath=temp, nice=10, extraArgs={'domain': 'site.test'},
                                       CheckIfSleepNeeded=MagicMock(), website=website)
            self.assertEqual(ns['BackupData'](instance), (1, None))
            self.assertEqual(json.loads((Path(temp) / 'data.json').read_text())['ChildDomains'][0]['state'], 0)


class ChildXmlRestoreTests(unittest.TestCase):
    def setUp(self):
        method = method_ast('restoreMeta.py', 'restoreMeta', 'startRestore')
        method.decorator_list = []
        self.worker = MagicMock()
        self.worker.createDomain.return_value = (1, 'None')
        self.ns = {'os': os, 'ElementTree': ElementTree, 'logging': MagicMock(),
                   'Websites': MagicMock(), 'virtualHostUtilities': self.worker}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'restoreMeta', 'exec'), self.ns)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.meta = Path(self.temp.name) / 'meta.xml'

    def restore(self, state):
        xml = '<metaFile><masterDomain>parent.test</masterDomain><ChildDomains><domain>'
        xml += '<domain>child.test</domain><path>/home/site/child</path><phpSelection>PHP 8.3</phpSelection>'
        if state is not None:
            xml += '<state>%s</state>' % state
        xml += '</domain></ChildDomains></metaFile>'
        self.meta.write_text(xml)
        return self.ns['startRestore'](str(self.meta), str(Path(self.temp.name) / 'status'))

    def test_saved_suspension_is_passed_before_creation_and_reconciled(self):
        self.assertEqual(self.restore('0'), 1)
        self.assertEqual(self.worker.createDomain.call_args.kwargs['independentState'], 0)
        self.worker.restoreChildDomainState.assert_called_once_with('child.test', 0, 'parent.test')

    def test_legacy_xml_restore_passes_active_default(self):
        self.assertEqual(self.restore(None), 1)
        self.assertIsNone(self.worker.createDomain.call_args.kwargs['independentState'])

    def test_failed_reconciliation_does_not_report_success_or_remove_metadata(self):
        self.worker.restoreChildDomainState.side_effect = RuntimeError('activation failed')
        self.assertEqual(self.restore('0'), 0)
        self.assertTrue(self.meta.exists())

    def test_invalid_saved_state_stops_before_creation(self):
        self.assertEqual(self.restore('2'), 0)
        self.worker.createDomain.assert_not_called()


class ChildJsonRestoreTests(unittest.TestCase):
    def run_loop(self, method_name, metadata, existing=False):
        method = method_ast('backupUtilities.py', 'backupUtilities', method_name)
        loop = next(n for n in ast.walk(method) if isinstance(n, ast.For)
                    and isinstance(n.iter, ast.Name) and n.iter.id == 'childDomains')
        worker = MagicMock()
        worker.createDomain.return_value = (1, 'None')
        missing = type('MissingChild', (Exception,), {})
        children = MagicMock()
        children.DoesNotExist = missing
        if not existing:
            children.objects.get.side_effect = missing()
        instance = SimpleNamespace(website=SimpleNamespace(domain='parent.test', admin=SimpleNamespace(userName='owner')),
                                   extraArgs={'tempStatusPath': '/tmp/test-status'})
        ns = {'self': instance, 'childDomains': [metadata], 'ChildDomains': children,
              'logging': MagicMock(), 'virtualHostUtilities': worker, 'randint': lambda *args: 1234}
        exec(compile(ast.Module(body=[loop], type_ignores=[]), method_name, 'exec'), ns)
        return worker

    def test_both_json_restore_paths_keep_new_and_existing_suspended_child(self):
        child = {'domain': 'child.test', 'path': '/home/site/child', 'php': 'PHP 8.3', 'state': 0}
        for method in ('SubmitCloudBackupRestore', 'SubmitS3BackupRestore'):
            for existing in (False, True):
                with self.subTest(method=method, existing=existing):
                    worker = self.run_loop(method, child, existing)
                    worker.restoreChildDomainState.assert_called_once_with('child.test', 0, 'parent.test')
                    if existing:
                        worker.createDomain.assert_not_called()
                    else:
                        self.assertEqual(worker.createDomain.call_args.kwargs['independentState'], 0)

    def test_both_json_restore_paths_accept_legacy_without_state(self):
        child = {'domain': 'child.test', 'path': '/home/site/child', 'php': 'PHP 8.3'}
        for method in ('SubmitCloudBackupRestore', 'SubmitS3BackupRestore'):
            worker = self.run_loop(method, child)
            self.assertIsNone(worker.createDomain.call_args.kwargs['independentState'])


class ChildRestoreActivationTests(unittest.TestCase):
    def setUp(self):
        self.worker, self.ns = load_creation_methods()
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.worker.Server_root = str(self.root)
        self.path = self.root / 'conf/vhosts/child.test/vhost.conf'
        self.path.parent.mkdir(parents=True)
        self.original = 'docRoot /home/site/child\n'
        self.path.write_text(self.original)
        self.parent = SimpleNamespace(domain='parent.test', state=1)
        self.child = SimpleNamespace(pk=20, master_id=10, state=1, save=MagicMock())
        self.children = MagicMock()
        self.children.objects.get.return_value = self.child
        self.children.objects.select_for_update.return_value.get.return_value = self.child
        websites = MagicMock()
        websites.objects.select_for_update.return_value.get.return_value = self.parent
        self.ns.update(ChildDomains=self.children, Websites=websites)
        db = ModuleType('django.db')
        db.transaction = SimpleNamespace(atomic=contextlib.nullcontext)
        self.patchers = [patch.dict(sys.modules, {'django.db': db}),
                         patch.object(websiteSuspension, 'suspension_lock', lambda *args: contextlib.nullcontext()),
                         patch.object(websiteSuspension, '_checked')]
        for p in self.patchers:
            p.start()
            self.addCleanup(p.stop)

    def test_restore_saved_zero_updates_database_and_actual_vhost(self):
        self.worker.restoreChildDomainState('child.test', 0, 'parent.test')
        self.assertEqual(self.child.state, 0)
        self.assertIn(websiteSuspension.START, self.path.read_text())
        self.child.save.assert_called_once_with(update_fields=['state'])

    def test_restore_active_independent_child_stays_effectively_suspended_by_parent(self):
        self.parent.state = 0
        self.worker.restoreChildDomainState('child.test', 1, 'parent.test')
        self.assertEqual(self.child.state, 1)
        self.assertIn(websiteSuspension.START, self.path.read_text())

    def test_legacy_restore_keeps_existing_independently_suspended_child(self):
        self.child.state = 0
        self.worker.restoreChildDomainState('child.test', None, 'parent.test')
        self.assertEqual(self.child.state, 0)
        self.assertIn(websiteSuspension.START, self.path.read_text())

    def test_backup_cannot_change_another_parents_child(self):
        with self.assertRaisesRegex(ValueError, 'does not belong'):
            self.worker.restoreChildDomainState('child.test', 0, 'other.test')
        self.assertEqual(self.original, self.path.read_text())
        self.child.save.assert_not_called()

    def test_database_save_failure_restores_original_configuration(self):
        self.child.save.side_effect = RuntimeError('database failed')
        with self.assertRaisesRegex(RuntimeError, 'database failed'):
            self.worker.restoreChildDomainState('child.test', 0, 'parent.test')
        self.assertEqual(self.original, self.path.read_text())


if __name__ == '__main__':
    unittest.main()
