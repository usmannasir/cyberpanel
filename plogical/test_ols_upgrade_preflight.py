import ast
import os
from pathlib import Path
import shlex
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, mock_open, patch


def load():
    tree = ast.parse(Path(__file__).with_name('upgrade.py').read_text())
    helper = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'validate_ols_configuration')
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
    method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == 'upgrade')
    method.decorator_list = []
    upgrade = Mock(CentOSPath='/not-centos', openEulerPath='/not-euler', SoftUpgrade=0)
    ns = {'os':os, 'subprocess':subprocess, 'shlex':shlex, 'Upgrade':upgrade, 'requireCSFMigration':Mock()}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[helper,method],type_ignores=[])), 'upgrade.py','exec'),ns)
    return ns


class UpgradePreflightTests(unittest.TestCase):
    def test_native_exit_codes(self):
        ns = load()
        for code, output, accepted in [(0,'',True),(1,'[WARN] fixture',True),(2,'[ERROR] fixture',False),(-11,'',False),(0,'[ERROR] fixture',False)]:
            with self.subTest(code=code,output=output), patch.object(subprocess,'run',return_value=SimpleNamespace(returncode=code,stdout=output,stderr='')):
                if accepted:ns['validate_ols_configuration']()
                else:
                    with self.assertRaises(RuntimeError):ns['validate_ols_configuration']()

    def test_broken_optional_diagnostic_helper_preserves_original_error(self):
        ns = load()
        ns['__file__'] = str(Path(__file__).with_name('upgrade.py'))
        result = SimpleNamespace(returncode=2, stdout='[ERROR] original invalid config', stderr='')
        for failure in (SyntaxError('broken helper'), AttributeError('incomplete helper')):
            with self.subTest(failure=failure), patch.object(subprocess, 'run', return_value=result), \
                    patch('importlib.util.module_from_spec', side_effect=failure):
                with self.assertRaisesRegex(RuntimeError, 'original invalid config'):
                    ns['validate_ols_configuration']()

    def test_invalid_existing_config_stops_before_any_upgrade_action(self):
        ns=load();ns['validate_ols_configuration']=Mock(side_effect=RuntimeError('invalid existing config'))
        with patch.object(os.path,'exists',return_value=True), self.assertRaisesRegex(RuntimeError,'invalid existing'):
            ns['upgrade']('v3.0.8')
        ns['Upgrade'].installCustomOLSBinaries.assert_not_called()
        ns['Upgrade'].executioner.assert_not_called()
        ns['Upgrade'].downloadAndUpgrade.assert_not_called()

    def run_later_failure(self, install_result, validator):
        ns=load();ns['validate_ols_configuration']=validator;ns['Upgrade'].installCustomOLSBinaries.return_value=install_result
        with patch.object(os.path,'exists',side_effect=lambda p:p=='/usr/local/lsws/bin/openlitespeed'), patch.object(subprocess,'check_output',return_value=b''), patch('builtins.open',mock_open(read_data='autoSSL 1\n')), self.assertRaises(RuntimeError):
            ns['upgrade']('v3.0.8')
        ns['Upgrade'].executioner.assert_not_called()
        ns['Upgrade'].updateRepoURL.assert_not_called()
        ns['Upgrade'].downloadAndUpgrade.assert_not_called()

    def test_bundle_failure_aborts_instead_of_later_stop(self):
        self.run_later_failure(False,Mock(return_value=''))

    def test_invalid_edited_config_does_not_stop_running_service(self):
        self.run_later_failure(True,Mock(side_effect=['',RuntimeError('edited invalid')]))

    def test_new_bundle_validation_is_inside_rollback_before_start(self):
        tree=ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Upgrade')
        method=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='installCustomOLSBinaries')
        rollback_try=next(n for n in ast.walk(method) if isinstance(n,ast.Try) and any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='validate_ols_configuration' for x in n.body))
        validation=next(x for x in rollback_try.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='validate_ols_configuration')
        later=ast.unparse(ast.Module(body=[x for x in rollback_try.body if x.lineno>validation.lineno],type_ignores=[]))
        self.assertIn("[control, 'start']",later)
        self.assertIn('restoring the previous OLS bundle',ast.unparse(rollback_try.handlers))

if __name__=='__main__':unittest.main()
