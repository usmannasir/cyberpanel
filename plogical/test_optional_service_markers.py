import ast
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import Mock, patch


source = Path(__file__).with_name('upgrade.py').read_text()
cls = next(n for n in ast.parse(source).body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
node = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and n.name == 'enableServices')
node.decorator_list = []
namespace = {'os':os, 'shutil':shutil, 'Upgrade':Mock()}
exec(compile(ast.fix_missing_locations(ast.Module(body=[node],type_ignores=[])),
             '<actual optional-service helper>', 'exec'), namespace)


class OptionalServiceMarkerTests(unittest.TestCase):
    def test_minimal_install_creates_no_optional_flags(self):
        with tempfile.TemporaryDirectory() as directory, patch('shutil.which',return_value=None):
            namespace['enableServices'](directory)
            self.assertEqual([], list(Path(directory).iterdir()))

    def test_binary_without_configuration_is_not_enough(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('shutil.which',return_value='/usr/sbin/installed'), \
                patch('os.path.isfile',return_value=False):
            namespace['enableServices'](directory)
            self.assertEqual([], list(Path(directory).iterdir()))

    def test_only_configured_installed_service_is_marked_and_rerun_is_safe(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch('shutil.which', side_effect=lambda name: '/usr/sbin/postfix' if name == 'postfix' else None), \
                patch('os.path.isfile',side_effect=lambda path: path == '/etc/postfix/main.cf'):
            namespace['enableServices'](directory)
            self.assertEqual(['postfix'], [p.name for p in Path(directory).iterdir()])
            Path(directory,'postfix').write_text('existing state\n')
            namespace['enableServices'](directory)
            self.assertEqual('existing state\n',Path(directory,'postfix').read_text())

    def test_existing_flags_are_not_removed_when_detection_is_unavailable(self):
        with tempfile.TemporaryDirectory() as directory, patch('shutil.which',return_value=None):
            Path(directory,'postfix').write_text('preserved\n')
            namespace['enableServices'](directory)
            self.assertEqual('preserved\n',Path(directory,'postfix').read_text())


if __name__ == '__main__':
    unittest.main()
