"""Execute real binary replacement code in a disposable installation."""
import ast
import os
from pathlib import Path
import shutil
import stat
import tempfile
import types
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).with_name('upgrade.py').read_text()

class UpgradeBinaryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        prefix = str(self.root)
        class Relocate(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, str) and node.value.startswith('/usr/local'):
                    return ast.copy_location(ast.Constant(prefix + node.value[len('/usr/local'):]), node)
                return node
        definitions = []
        for node in ast.parse(SOURCE).body:
            if isinstance(node, ast.FunctionDef) and node.name == 'install_binary_atomically':
                definitions.append(node)
            elif isinstance(node, ast.ClassDef) and node.name == 'Upgrade':
                node.body = [m for m in node.body if isinstance(m, ast.FunctionDef)
                             and m.name in ('installPanelPHP', 'installLSCPD')]
                definitions.append(node)
        namespace = dict(os=os, shutil=shutil, tempfile=tempfile)
        tree = ast.fix_missing_locations(Relocate().visit(ast.Module(body=definitions, type_ignores=[])))
        exec(compile(tree, 'upgrade.py', 'exec'), namespace)
        self.install = namespace['install_binary_atomically']
        self.upgrade = namespace['Upgrade']
        self.upgrade.stdOut = lambda *args: None
        self.namespace = namespace
        self.destination = self.root / 'lscp/fcgi-bin/lsphp'
        self.write(self.destination, b'previous executable')
    @staticmethod
    def write(path, content, mode=0o755):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        path.chmod(mode)
        return path
    def test_missing_empty_or_failed_copy_keeps_installed_binary(self):
        source = self.root / 'source'
        for content in (None, b''):
            if content is not None:
                source.write_bytes(content)
            with self.assertRaises(RuntimeError):
                self.install(str(source), str(self.destination))
            self.assertEqual(b'previous executable', self.destination.read_bytes())
        source.write_bytes(b'new executable')
        with patch.object(shutil, 'copyfile', side_effect=OSError('disk full')):
            with self.assertRaises(OSError):
                self.install(str(source), str(self.destination))
        self.assertEqual(b'previous executable', self.destination.read_bytes())
        self.assertEqual([], list(self.destination.parent.glob('.*.upgrade-*')))
    def test_failed_replace_keeps_symlink_and_target(self):
        target = self.write(self.root / 'external', b'old external executable')
        self.destination.unlink()
        self.destination.symlink_to(target)
        source = self.write(self.root / 'source', b'new executable')
        with patch.object(os, 'replace', side_effect=OSError('read-only filesystem')):
            with self.assertRaises(OSError):
                self.install(str(source), str(self.destination))
        self.assertTrue(self.destination.is_symlink())
        self.assertEqual(b'old external executable', target.read_bytes())
        self.assertEqual([], list(self.destination.parent.glob('.*.upgrade-*')))
    def test_success_replaces_link_without_overwriting_external_target(self):
        target = self.write(self.root / 'external', b'external executable')
        self.destination.unlink()
        self.destination.symlink_to(target)
        source = self.write(self.root / 'source', b'new executable', 0o644)
        self.install(str(source), str(self.destination))
        self.assertFalse(self.destination.is_symlink())
        self.assertEqual(b'new executable', self.destination.read_bytes())
        self.assertEqual(b'external executable', target.read_bytes())
        self.assertEqual(0o755, stat.S_IMODE(self.destination.stat().st_mode))
    def test_php_83_used_when_php_80_is_absent(self):
        self.write(self.root / 'lsws/lsphp83/bin/lsphp', b'PHP 8.3 LSAPI')
        self.upgrade.installPanelPHP()
        self.assertEqual(b'PHP 8.3 LSAPI', self.destination.read_bytes())
    def test_php_84_fallback(self):
        self.write(self.root / 'lsws/lsphp84/bin/lsphp', b'PHP 8.4 LSAPI')
        self.upgrade.installPanelPHP()
        self.assertEqual(b'PHP 8.4 LSAPI', self.destination.read_bytes())
    def test_existing_php_kept_without_release_php(self):
        self.upgrade.installPanelPHP()
        self.assertEqual(b'previous executable', self.destination.read_bytes())
    def test_missing_all_php_fails(self):
        self.destination.unlink()
        with self.assertRaisesRegex(RuntimeError, 'No usable LSAPI PHP'):
            self.upgrade.installPanelPHP()
    def test_missing_lscpd_artifact_fails_and_keeps_previous(self):
        destination = self.write(self.root / 'lscp/bin/lscpd', b'old lscpd')
        self.upgrade.SoftUpgrade = 0
        self.upgrade.UbuntuPath = str(self.root / 'lsb-release')
        self.upgrade.executioner = lambda *args: 1
        self.namespace['subprocess'] = types.SimpleNamespace(
            PIPE=-1, run=lambda *args, **kwargs: types.SimpleNamespace(stdout='Linux x86_64'))
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        with self.assertRaisesRegex(RuntimeError, 'Required executable'):
            self.upgrade.installLSCPD('v3.0.7')
        self.assertEqual(b'old lscpd', destination.read_bytes())

if __name__ == '__main__':
    unittest.main()
