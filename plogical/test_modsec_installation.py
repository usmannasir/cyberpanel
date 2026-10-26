import ast
import contextlib
import io
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


def load_class():
    tree = ast.parse(Path(__file__).with_name('modSec.py').read_text())
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'modSec')
    namespace = {'os': os, 'subprocess': subprocess, 'shlex': shlex,
                 'mailUtilities': SimpleNamespace(checkHome=Mock()),
                 'ProcessUtilities': SimpleNamespace(decideDistro=lambda: 2, centos=0, cent8=1),
                 'logging': SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=Mock())),
                 'virtualHostUtilities': SimpleNamespace(Server_root='unused')}
    exec(compile(ast.Module(body=[klass], type_ignores=[]), 'modSec.py', 'exec'), namespace)
    return namespace['modSec'], namespace


class ModSecInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cls, self.ns = load_class()
        self.cls.installLogPath = str(self.root / 'install.log')
        (self.root / 'conf').mkdir()
        (self.root / 'conf/httpd_config.conf').write_text('listener fixture {\n address *:80\n secure 0\n}\n')
        self.ns['virtualHostUtilities'].Server_root = str(self.root)

    def log(self):
        return Path(self.cls.installLogPath).read_text()

    def test_current_custom_module_route(self):
        with patch.object(self.cls, 'detectPlatform', return_value='ubuntu'), patch.object(self.cls, 'downloadCompatibleModSec', return_value=True) as download:
            self.assertEqual(self.cls.installCompatibleModSecurity(), 1)
            download.assert_called_once_with('ubuntu')
        self.assertIn('[200]', self.log())

    def test_custom_failure_has_no_success(self):
        with patch.object(self.cls, 'detectPlatform', return_value=None), patch.object(self.cls, 'downloadCompatibleModSec', return_value=False):
            self.assertEqual(self.cls.installCompatibleModSecurity(), 0)
        self.assertIn('[404]', self.log())
        self.assertNotIn('[200]', self.log())

    def test_package_exit_100_is_failure(self):
        with patch.object(self.cls, 'isCustomOLSBinaryInstalled', return_value=False), patch.object(subprocess, 'call', return_value=100):
            self.assertEqual(self.cls.installModSec(), 0)
        self.assertNotIn('[200]', self.log())
        self.assertIn('[404]', self.log())

    def test_fallback_module_failure_has_no_success(self):
        with patch.object(self.cls, 'isCustomOLSBinaryInstalled', return_value=False), patch.object(subprocess, 'call', return_value=0), patch.object(os.path, 'exists', return_value=True), patch.object(self.cls, 'detectPlatform', return_value='ubuntu'), patch.object(self.cls, 'downloadCompatibleModSec', return_value=False):
            self.assertEqual(self.cls.installModSec(), 0)
        self.assertNotIn('[200]', self.log())

    def test_config_errors_prevent_restart(self):
        with patch.object(subprocess, 'run', return_value=SimpleNamespace(returncode=2, stdout='[ERROR] fixture', stderr='')) as command, contextlib.redirect_stdout(io.StringIO()) as out:
            self.cls.installModSecConfigs()
        self.assertEqual(command.call_count, 1)
        self.assertNotIn('1,None', out.getvalue())

    def test_warning_only_config_activates(self):
        with patch.object(subprocess, 'run', side_effect=[SimpleNamespace(returncode=1, stdout='[WARN] fixture', stderr=''), SimpleNamespace(returncode=0, stdout='', stderr='')]) as command, contextlib.redirect_stdout(io.StringIO()) as out:
            self.cls.installModSecConfigs()
        self.assertEqual(command.call_args_list[1].args[0][-1], 'restart')
        self.assertIn('1,None', out.getvalue())

    def test_restart_failure_is_visible(self):
        with patch.object(subprocess, 'run', side_effect=[SimpleNamespace(returncode=0, stdout='', stderr=''), SimpleNamespace(returncode=1, stdout='', stderr='fixture')]), contextlib.redirect_stdout(io.StringIO()) as out:
            self.cls.installModSecConfigs()
        self.assertNotIn('1,None', out.getvalue())
        self.assertIn('could not activate', out.getvalue())

if __name__ == '__main__':
    unittest.main()
