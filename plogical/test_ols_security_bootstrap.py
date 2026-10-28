"""Upgrade dependencies must come from its release before OLS mutation."""
import ast
import builtins
import importlib.util
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def load_upgrade_methods(upgrade_path):
    tree = ast.parse((ROOT / 'plogical/upgrade.py').read_text(encoding='utf-8'))
    functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                 and node.name == 'load_ols_security_assets']
    original = next(node for node in tree.body if isinstance(node, ast.ClassDef)
                    and node.name == 'Upgrade')
    original.body = [node for node in original.body if isinstance(node, ast.FunctionDef)
                     and node.name in ('installCustomOLSBinaries', 'rollbackOLSBinary')]
    namespace = dict(__file__=str(upgrade_path), os=os, shutil=shutil,
                     subprocess=Mock(), tempfile=tempfile, importlib=importlib)
    exec(compile(ast.fix_missing_locations(ast.Module(
        body=functions + [original], type_ignores=[])), str(upgrade_path), 'exec'), namespace)
    upgrade = namespace['Upgrade']
    upgrade.stdOut = Mock()
    upgrade.detectArchitecture = Mock(return_value=True)
    upgrade.detectPlatform = Mock(return_value='ubuntu')
    upgrade.downloadCustomBinary = Mock(return_value=True)
    upgrade.verifyChecksum = Mock(return_value=True)
    upgrade.checkGlibcCompat = Mock(return_value=True)
    return namespace, upgrade


class SecurityBootstrapTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        self.helper = self.stage / 'olsSecurityAssets.py'
        self.namespace, self.upgrade = load_upgrade_methods(self.stage / 'upgrade.py')

    def test_missing_helper_stops_before_download_or_service_command(self):
        original_import = builtins.__import__

        def legacy_import(name, *args, **kwargs):
            if name == 'plogical.olsSecurityAssets':
                raise ModuleNotFoundError("No module named 'plogical.olsSecurityAssets'")
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=legacy_import):
            self.assertFalse(self.upgrade.installCustomOLSBinaries())
        self.upgrade.downloadCustomBinary.assert_not_called()
        self.namespace['subprocess'].assert_not_called()
        self.assertFalse(self.namespace['subprocess'].mock_calls)

    def test_malformed_helper_stops_before_download_or_service_command(self):
        self.helper.write_text('class SecurityAssetsTransaction(:\n')
        self.assertFalse(self.upgrade.installCustomOLSBinaries())
        self.upgrade.downloadCustomBinary.assert_not_called()
        self.assertFalse(self.namespace['subprocess'].mock_calls)

    def test_incomplete_helper_stops_before_download_or_service_command(self):
        self.helper.write_text('class SecurityAssetsTransaction: pass\n')
        self.assertFalse(self.upgrade.installCustomOLSBinaries())
        self.upgrade.downloadCustomBinary.assert_not_called()
        self.assertFalse(self.namespace['subprocess'].mock_calls)

    def test_adjacent_release_wins_over_installed_modules(self):
        shutil.copy2(ROOT / 'plogical/olsSecurityAssets.py', self.helper)
        # A same-name installed module must never control the paired release.
        import sys
        poison = Mock()
        with patch.dict(sys.modules, {'plogical.olsSecurityAssets': poison,
                                     'olsSecurityAssets': poison}):
            loaded = self.namespace['load_ols_security_assets']()
        self.assertEqual(Path(loaded.__file__).resolve(), self.helper.resolve())
        self.assertTrue(callable(loaded.SecurityAssetsTransaction))
        self.assertTrue(callable(loaded.restore_security_assets))
        poison.assert_not_called()

    def test_installed_layout_loads_the_adjacent_helper(self):
        namespace, _ = load_upgrade_methods(ROOT / 'plogical/upgrade.py')
        loaded = namespace['load_ols_security_assets']()
        self.assertEqual(Path(loaded.__file__).resolve(),
                         (ROOT / 'plogical/olsSecurityAssets.py').resolve())

    def test_unusable_rollback_helper_does_not_stop_service(self):
        backup = self.root / 'backup'
        backup.mkdir()
        (backup / 'openlitespeed.backup').write_bytes(b'old core')
        (backup / 'security_assets_backup.json').write_text('{"backup_dir":"assets"}')
        for content in (None, 'class SecurityAssetsTransaction(:\n',
                        'class SecurityAssetsTransaction: pass\n'):
            with self.subTest(helper=content):
                if content is not None:
                    self.helper.write_text(content)
                self.assertFalse(self.upgrade.rollbackOLSBinary(str(backup), str(self.root / 'core')))
                self.assertFalse(self.namespace['subprocess'].mock_calls)


if __name__ == '__main__':
    unittest.main()
