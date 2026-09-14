"""Legacy restore must refuse enrolled roots before replacing site or mail data."""
import ast
import os
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch
from xml.etree import ElementTree

from plogical import storageQuota


def restore_method(name, namespace):
    path = Path(__file__).with_name('backupUtilities.py')
    source = ast.parse(path.read_text())
    owner = next(node for node in source.body
                 if isinstance(node, ast.ClassDef) and node.name == 'backupUtilities')
    method = next(node for node in owner.body
                  if isinstance(node, ast.FunctionDef) and node.name == name)
    method.decorator_list = []
    module = ast.Module(body=[method], type_ignores=[])
    exec(compile(ast.fix_missing_locations(module), str(path), 'exec'), namespace)
    return namespace[name]


class StorageRestoreGuardTests(unittest.TestCase):
    def setUp(self):
        self.site = SimpleNamespace(pk=31, domain='example.test')
        self.models = MagicMock()
        self.models.objects.get.return_value = self.site
        self.models.objects.filter.return_value.first.return_value = self.site
        self.log = MagicMock()
        self.process = MagicMock()
        self.utilities = MagicMock()
        self.metadata = ElementTree.ElementTree(ElementTree.fromstring(
            '<backup><masterDomain>example.test</masterDomain>'
            '<VERSION>3.0.6</VERSION><BUILD>1</BUILD></backup>'))
        self.namespace = {
            'Websites': self.models, 'logging': self.log,
            'ProcessUtilities': self.process, 'backupUtilities': self.utilities,
            'os': SimpleNamespace(path=os.path, getpid=lambda: 1, mkdir=MagicMock()),
            'tarfile': MagicMock(), 'safe_extract': MagicMock(),
            'archive_path_without_suffix': lambda name: name[:-len('.tar.gz')],
            'ElementTree': SimpleNamespace(parse=lambda unused: self.metadata),
        }

    def test_cloud_and_s3_refuse_before_extraction_or_download(self):
        for name in ('SubmitCloudBackupRestore', 'SubmitS3BackupRestore'):
            with self.subTest(method=name):
                restore = restore_method(name, self.namespace)
                instance = SimpleNamespace(extraArgs={
                    'domain': 'example.test', 'tempStatusPath': '/fixture/status'})
                with patch.object(storageQuota, 'assert_restore_allowed',
                                  side_effect=storageQuota.StorageQuotaError('maintenance required')) as guard:
                    restore(instance)
                guard.assert_called_once_with(self.site)
                self.process.executioner.assert_not_called()
                self.process.outputExecutioner.assert_not_called()
                self.utilities.fetchAWSKeys.assert_not_called()
                self.assertIn('maintenance required', str(self.log.mock_calls[-1]))

    def test_archive_refuses_before_account_creation_or_live_data_restore(self):
        restore = restore_method('startRestore', self.namespace)
        with patch.object(storageQuota, 'assert_restore_allowed',
                          side_effect=storageQuota.StorageQuotaError('maintenance required')) as guard:
            restore('/fixture/backup.tar.gz', 'CLI')
        guard.assert_called_once_with(self.site)
        self.utilities.createWebsiteFromBackup.assert_not_called()
        self.process.executioner.assert_not_called()
        self.process.outputExecutioner.assert_not_called()
        self.assertIn('maintenance required', str(self.log.mock_calls[-1]))

    def test_unenrolled_website_reaches_existing_restore_workflow(self):
        restore = restore_method('startRestore', self.namespace)
        self.utilities.createWebsiteFromBackup.return_value = (0, 'fixture stop')
        with patch.object(storageQuota, 'assert_restore_allowed', return_value=None) as guard:
            restore('/fixture/backup.tar.gz', 'CLI')
        guard.assert_called_once_with(self.site)
        self.utilities.createWebsiteFromBackup.assert_called_once_with('/fixture/backup.tar.gz', 'CLI')

    def test_new_website_reaches_existing_restore_workflow(self):
        restore = restore_method('startRestore', self.namespace)
        self.models.objects.filter.return_value.first.return_value = None
        self.utilities.createWebsiteFromBackup.return_value = (0, 'fixture stop')
        with patch.object(storageQuota, 'assert_restore_allowed') as guard:
            restore('/fixture/backup.tar.gz', 'CLI')
        guard.assert_not_called()
        self.utilities.createWebsiteFromBackup.assert_called_once_with('/fixture/backup.tar.gz', 'CLI')


if __name__ == '__main__':
    unittest.main()
