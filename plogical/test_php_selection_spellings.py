"""A PHP version kept in an older spelling is used in the panel's own form wherever something is created from it."""
import ast
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest import mock

from managePHP.phpConfig import normalized_php_selection, php_selection_digits, stored_php_selection
from managePHP.test_php_selection import OLDER_SPELLINGS
from plogical.test_php_restart_marker import load_methods

ROOT = Path(__file__).resolve().parents[1]


def method_node(relative_path, class_name, method_name):
    tree = ast.parse((ROOT / relative_path).read_text(encoding='utf-8'))
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    return next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == method_name)


class CommandLineTests(unittest.TestCase):
    """cyberpanel createWebsite, createChild and changePHP take --php 7.4 and, as before, --php 74."""

    def setUp(self):
        self.worker = mock.Mock(Server_root='/usr/local/lsws')
        self.worker.createVirtualHost.return_value = (1, 'None')
        self.worker.createDomain.return_value = (1, 'None')
        self.vhost = mock.Mock()
        self.vhost.changePHP.return_value = (1, 'None')
        websites = mock.Mock()
        websites.objects.get.side_effect = LookupError('no such user')
        namespace = dict(virtualHostUtilities=self.worker, vhost=self.vhost, Websites=websites, logger=mock.Mock(),
                         stack=lambda: [[None, None, None, 'test']], time=mock.Mock(), re=__import__('re'),
                         normalized_php_selection=normalized_php_selection, stored_php_selection=stored_php_selection)
        self.create_site, self.create_child, self.change = load_methods(
            'cli/cyberPanel.py', 'cyberPanel', ['createWebsite', 'createDomain', 'changePHP'], namespace)
        self.cli = mock.Mock()

    def test_every_form_of_the_option_reaches_the_worker_as_a_selection(self):
        for option, selection in (('7.4', 'PHP 7.4'), ('74', 'PHP 7.4'), ('8.3', 'PHP 8.3'), ('83', 'PHP 8.3'),
                                  ('PHP 8.1', 'PHP 8.1')):
            with self.subTest(option=option):
                self.create_site(self.cli, 'Default', 'admin', 'example.test', 'owner@example.test', option, 0, 0, 0)
                self.assertEqual(selection, self.worker.createVirtualHost.call_args[0][2])
                self.create_child(self.cli, 'example.test', 'shop.example.test', 'admin', option, 0, 0, 0, 'shop')
                self.assertEqual(selection, self.worker.createDomain.call_args[0][2])
                self.change(self.cli, 'example.test', option)
                self.assertEqual(selection, self.vhost.changePHP.call_args[0][1])
        self.cli.printStatus.assert_called_with(1, 'None')

    def test_another_option_is_reported_and_starts_nothing(self):
        for option in ('7', 'latest', '7.4.1', ''):
            with self.subTest(option=option):
                self.cli.reset_mock()
                self.create_site(self.cli, 'Default', 'admin', 'example.test', 'owner@example.test', option, 0, 0, 0)
                self.cli.printStatus.assert_called_once_with(0, 'Invalid PHP version selected.')
                self.cli.reset_mock()
                self.create_child(self.cli, 'example.test', 'shop.example.test', 'admin', option, 0, 0, 0, 'shop')
                self.cli.printStatus.assert_called_once_with(0, 'Invalid PHP version selected.')
                self.cli.reset_mock()
                self.change(self.cli, 'example.test', option)
                self.cli.printStatus.assert_called_once_with(0, 'Invalid PHP version selected.')
        self.assertEqual([], self.worker.mock_calls)
        self.assertEqual([], self.vhost.mock_calls)


class BackupRestoreTests(unittest.TestCase):
    """A child domain is restored with the version its backup names, whatever spelling the backup has."""

    def restore_children(self, method_name, php):
        method = method_node('plogical/backupUtilities.py', 'backupUtilities', method_name)
        loop = next(node for node in ast.walk(method) if isinstance(node, ast.For)
                    and isinstance(node.iter, ast.Name) and node.iter.id == 'childDomains')
        worker = mock.MagicMock()
        worker.createDomain.return_value = (1, 'None')
        missing = type('MissingChild', (Exception,), {})
        children = mock.MagicMock()
        children.DoesNotExist = missing
        children.objects.get.side_effect = missing()
        instance = NS(website=NS(domain='parent.test', admin=NS(userName='owner')),
                      extraArgs={'tempStatusPath': '/tmp/test-status'})
        namespace = {'self': instance, 'ChildDomains': children, 'logging': mock.MagicMock(),
                     'childDomains': [{'domain': 'child.test', 'path': '/home/parent.test/child', 'php': php}],
                     'virtualHostUtilities': worker, 'randint': lambda *args: 1234,
                     'normalized_php_selection': normalized_php_selection, 'stored_php_selection': stored_php_selection}
        exec(compile(ast.Module(body=[loop], type_ignores=[]), method_name, 'exec'), namespace)
        return worker

    def test_both_restores_create_the_child_with_the_panels_form(self):
        for method in ('SubmitCloudBackupRestore', 'SubmitS3BackupRestore'):
            for spelling, selection in OLDER_SPELLINGS.items():
                with self.subTest(method=method, spelling=spelling):
                    worker = self.restore_children(method, spelling)
                    self.assertEqual(selection, worker.createDomain.call_args[0][2])

    def test_a_backup_that_names_no_version_leaves_the_refusal_to_the_worker(self):
        # The value goes on as it is; the worker refuses it for this child
        # (plogical.test_php_selection_workers) and the restore handles that
        # refusal as it handles any other.
        for method in ('SubmitCloudBackupRestore', 'SubmitS3BackupRestore'):
            with self.subTest(method=method):
                worker = self.restore_children(method, 'PHP seven')
                self.assertEqual('PHP seven', worker.createDomain.call_args[0][2])

    def test_every_restore_and_sync_call_passes_the_version_through_the_normal_form(self):
        # The other callers hand a stored version to the same three workers.
        # Each such argument is the normal form of the stored value.
        expected = {
            'plogical/backupUtilities.py': 6, 'plogical/restoreMeta.py': 1, 'plogical/ClusterManager.py': 2,
            'plogical/SwitchOldAliasToNew.py': 1,
        }
        for relative_path, count in expected.items():
            with self.subTest(file=relative_path):
                tree = ast.parse((ROOT / relative_path).read_text(encoding='utf-8'))
                calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
                         and isinstance(node.func, ast.Attribute)
                         and node.func.attr in ('createVirtualHost', 'createDomain', 'switchServer')
                         and isinstance(node.func.value, ast.Name) and node.func.value.id == 'virtualHostUtilities']
                self.assertEqual(count, len(calls))
                for call in calls:
                    version = call.args[1] if call.func.attr == 'switchServer' else call.args[2]
                    self.assertIsInstance(version, ast.Call, ast.dump(call))
                    self.assertEqual('stored_php_selection', version.func.id)


class MetadataRestoreTests(unittest.TestCase):
    """The child domains of a restored website are created from the backup's description."""

    def restore(self, php):
        import os
        import tempfile
        from xml.etree import ElementTree
        method = method_node('plogical/restoreMeta.py', 'restoreMeta', 'startRestore')
        method.decorator_list = []
        worker = mock.MagicMock()
        worker.createDomain.return_value = (1, 'None')
        namespace = {'os': os, 'ElementTree': ElementTree, 'logging': mock.MagicMock(), 'Websites': mock.MagicMock(),
                     'virtualHostUtilities': worker, 'normalized_php_selection': normalized_php_selection, 'stored_php_selection': stored_php_selection}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'restoreMeta', 'exec'), namespace)
        with tempfile.TemporaryDirectory(prefix='php-spelling-test-') as temp:
            meta = Path(temp) / 'meta.xml'
            meta.write_text('<metaFile><masterDomain>parent.test</masterDomain><ChildDomains><domain>'
                            '<domain>child.test</domain><path>/home/parent.test/child</path>'
                            '<phpSelection>%s</phpSelection></domain></ChildDomains></metaFile>' % php)
            return namespace['startRestore'](str(meta), str(Path(temp) / 'status')), worker

    def test_the_child_is_created_with_the_panels_form(self):
        for spelling, selection in OLDER_SPELLINGS.items():
            with self.subTest(spelling=spelling):
                result, worker = self.restore(spelling)
                self.assertEqual(1, result)
                self.assertEqual(selection, worker.createDomain.call_args[0][2])

    def test_a_description_that_names_no_version_leaves_the_refusal_to_the_worker(self):
        result, worker = self.restore('PHP seven')
        self.assertEqual('PHP seven', worker.createDomain.call_args[0][2])


class EnterpriseRecordTests(unittest.TestCase):
    """The LiteSpeed Enterprise record of a website gets the version number of a stored older spelling."""

    def records(self, stored):
        process = mock.Mock(OLS='ols')
        process.decideServer.return_value = 'lsws'
        from plogical.vhostConfs import vhostConfs
        account = NS(pw_uid=1001, gr_gid=1001)
        namespace = dict(
            ProcessUtilities=process, vhostConfs=vhostConfs, logging=mock.Mock(), PHPManager=mock.Mock(),
            vhost=NS(redisConf='/redis'), os=NS(path=NS(exists=lambda path: True)),
            pwd=NS(getpwnam=lambda user: account), grp=NS(getgrnam=lambda user: account),
            php_selection_digits=php_selection_digits, normalized_php_selection=normalized_php_selection, stored_php_selection=stored_php_selection)
        site, child = load_methods('plogical/vhost.py', 'vhost', ['perHostVirtualConf', 'perHostDomainConf'],
                                   namespace)
        results = (site('/vhost.conf', 'owner@example.test', 'siteuser', stored, 'example.test', 0),
                   child('/home/example.test/shop', 'example.test', 'shop.example.test', '/vhost.conf',
                         'owner@example.test', stored, 'siteuser', 0))
        return results, [call[0][0] for call in process.executioner.call_args_list]

    def test_both_records_carry_the_number(self):
        for stored, number in (('PHP 74', '7.4'), ('php 8.1', '8.1'), ('PHP 8.3', '8.3')):
            with self.subTest(stored=stored):
                results, commands = self.records(stored)
                self.assertEqual((1, 1), results)
                self.assertEqual(4, len(commands))
                for command in commands:
                    self.assertIn('"phpVersion": %s,' % number, command)

    def test_a_stored_value_that_is_no_version_writes_no_record(self):
        results, commands = self.records('PHP seven')
        self.assertEqual((0, 0), results)
        self.assertEqual([], commands)


if __name__ == '__main__':
    unittest.main()
