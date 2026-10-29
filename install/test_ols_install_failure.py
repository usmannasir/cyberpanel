"""Fresh installs must stop when the required OLS transaction fails."""
import ast
from pathlib import Path
import sys
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

    def test_success_or_intentional_platform_skip_preserves_existing_flow(self):
        # The bundle helper explicitly returns True for supported success and
        # intentional unsupported-architecture/platform skips.
        self.calls.installCustomOLSBinaries.return_value = True
        self.installer.installLiteSpeed()
        self.assertEqual([c[0] for c in self.calls.mock_calls],
                         ['install_package', 'installCustomOLSBinaries', 'configureCustomModule'])
        self.notice.assert_called_once_with()

    def test_bundle_exception_propagates_without_followup_changes(self):
        self.calls.installCustomOLSBinaries.side_effect = RuntimeError('rollback failed')
        with self.assertRaisesRegex(RuntimeError, 'rollback failed'):
            self.installer.installLiteSpeed()
        self.assert_no_post_bundle_changes()


if __name__ == '__main__':
    unittest.main()
