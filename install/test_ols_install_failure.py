"""Fresh installs must stop when the required OLS transaction fails."""
import ast
import os
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


class FreshOLSFailureTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'install/installCyberPanel.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                   and n.name == 'InstallCyberPanel')
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'installLiteSpeed']
        self.os = Mock()
        self.os.path.exists.return_value = False
        namespace = {'os': self.os}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])),
                     str(path), 'exec'), namespace)
        klass = namespace['InstallCyberPanel']
        klass.stdOut = Mock()
        self.installer = klass()
        self.installer.ent = 0
        self.calls = Mock()
        for name in ('install_package', 'installCustomOLSBinaries', 'configureCustomModule'):
            setattr(self.installer, name, getattr(self.calls, name))
        self.notice = Mock(return_value={'status': 'patched'})
        module = types.ModuleType('plogical.olsWebAdmin')
        module.patch_webadmin_release_notice = self.notice
        self.modules = patch.dict(sys.modules, {'plogical.olsWebAdmin': module})
        self.modules.start()
        self.addCleanup(self.modules.stop)

    def assert_no_post_bundle_changes(self):
        self.calls.configureCustomModule.assert_not_called()
        self.notice.assert_not_called()
        self.os.path.exists.assert_not_called()

    def test_failed_transaction_aborts_before_module_or_configuration_changes(self):
        self.calls.installCustomOLSBinaries.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'Custom OLS bundle installation failed'):
            self.installer.installLiteSpeed()
        self.calls.install_package.assert_called_once_with('openlitespeed')
        self.assert_no_post_bundle_changes()

    def test_missing_success_result_also_fails_closed(self):
        self.calls.installCustomOLSBinaries.return_value = None
        with self.assertRaises(RuntimeError):
            self.installer.installLiteSpeed()
        self.assert_no_post_bundle_changes()

    def test_installed_bundle_declares_the_module(self):
        self.calls.installCustomOLSBinaries.return_value = True
        self.installer.installLiteSpeed()
        self.assertEqual([c[0] for c in self.calls.mock_calls],
                         ['install_package', 'installCustomOLSBinaries', 'configureCustomModule'])
        self.notice.assert_called_once_with()

    def test_stock_fallback_continues_without_declaring_the_module(self):
        # No CyberPanel build for this architecture or system: the vendor core
        # stays, and a declaration of the missing module would stop every
        # later upgrade at the OpenLiteSpeed check.
        self.calls.installCustomOLSBinaries.return_value = 'stock'
        self.installer.installLiteSpeed()
        self.assertEqual([c[0] for c in self.calls.mock_calls],
                         ['install_package', 'installCustomOLSBinaries'])
        self.notice.assert_called_once_with()

    def test_any_other_result_fails_closed(self):
        for result in ('', 'Stock', 1, 'installed'):
            with self.subTest(result=result):
                self.calls.reset_mock()
                self.calls.installCustomOLSBinaries.return_value = result
                with self.assertRaises(RuntimeError):
                    self.installer.installLiteSpeed()
                self.assert_no_post_bundle_changes()

    def test_bundle_exception_propagates_without_followup_changes(self):
        self.calls.installCustomOLSBinaries.side_effect = RuntimeError('rollback failed')
        with self.assertRaisesRegex(RuntimeError, 'rollback failed'):
            self.installer.installLiteSpeed()
        self.assert_no_post_bundle_changes()


class FreshOLSSkipTests(unittest.TestCase):
    """The bundle step names a stock fallback; only an installed bundle is True."""

    def setUp(self):
        path = ROOT / 'install/installCyberPanel.py'
        tree = ast.parse(path.read_text(encoding='utf-8'))
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef)
                   and n.name == 'InstallCyberPanel')
        cls.body = [n for n in cls.body if isinstance(n, ast.FunctionDef)
                    and n.name in ('installCustomOLSBinaries', 'configureCustomModule')]
        namespace = {'os': os, 'shutil': shutil, 'subprocess': Mock(), 'logging': Mock()}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])),
                     str(path), 'exec'), namespace)
        klass = namespace['InstallCyberPanel']
        klass.stdOut = Mock()
        self.installer = klass()
        self.installer.install_package = Mock()

    def test_every_skip_returns_the_stock_fallback(self):
        for architecture, platform in ((False, 'ubuntu22'), (True, 'skip'), (True, 'debian12')):
            with self.subTest(architecture=architecture, platform=platform):
                self.installer.detectArchitecture = Mock(return_value=architecture)
                self.installer.detectPlatform = Mock(return_value=platform)
                self.assertEqual(self.installer.installCustomOLSBinaries(), 'stock')
                self.installer.install_package.assert_not_called()

    def test_module_is_declared_only_beside_the_cyberpanel_build(self):
        marked = b'\x7fELF cyberpanel_lsi_api_abi_v1'
        cases = (
            # (core, module, configuration before, configuration after)
            (b'\x7fELF vendor', None, 'serverName x\n', 'serverName x\n'),
            (b'\x7fELF vendor', marked, 'serverName x\n', 'serverName x\n'),
            (marked, None, 'serverName x\n', 'serverName x\n'),
            (marked, b'\x7fELF old module', 'serverName x\n', 'serverName x\n'),
            (b'\x7fELF vendor', None, 'module cyberpanel_ols {\n  ls_enabled 0\n}\n',
             'module cyberpanel_ols {\n  ls_enabled 0\n}\n'),
            (marked, marked, 'serverName x\n',
             'serverName x\n\nmodule cyberpanel_ols {\n  ls_enabled          1\n}\n'),
            (marked, marked, 'module cyberpanel_ols {\n  ls_enabled 0\n}\n',
             'module cyberpanel_ols {\n  ls_enabled          1\n}\n'),
        )
        for core, module, before, after in cases:
            with self.subTest(core=core, module=module, before=before), tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                for name in ('bin', 'modules', 'conf'):
                    (root / name).mkdir()
                (root / 'bin/openlitespeed').write_bytes(core)
                if module is not None:
                    (root / 'modules/cyberpanel_ols.so').write_bytes(module)
                config = root / 'conf/httpd_config.conf'
                config.write_text(before)
                self.installer.configureCustomModule(root=str(root))
                self.assertEqual(config.read_text(), after)


if __name__ == '__main__':
    unittest.main()
