import ast
from contextlib import contextmanager, nullcontext
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
    notice = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'ols_site_error_notice')
    klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
    method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == 'upgrade')
    method.decorator_list = []
    upgrade = Mock(CentOSPath='/not-centos', openEulerPath='/not-euler', SoftUpgrade=0)
    ns = {'os':os, 'subprocess':subprocess, 'shlex':shlex, 'Upgrade':upgrade, 'ols_upgrade_lock':nullcontext, 'OLSUpgradeFailure':RuntimeError, 'requireCSFMigration':Mock()}
    ns['load_ols_diagnostic_helper'] = lambda name: SimpleNamespace(
        validate=lambda binary: subprocess.run([binary, '-t']), recovery_hint=lambda *args: '',
        stock_recovery_hint=lambda *args: '', OLSService=Mock())
    exec(compile(ast.fix_missing_locations(ast.Module(body=[helper,notice,method],type_ignores=[])), 'upgrade.py','exec'),ns)
    return ns


class UpgradePreflightTests(unittest.TestCase):
    def test_shared_bundle_lock_refuses_second_owner_without_running_body(self):
        import tempfile
        tree = ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        lock = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'ols_upgrade_lock')
        ns = {'os': os, 'contextmanager': contextmanager, 'OLSUpgradeFailure': RuntimeError}
        exec(compile(ast.Module(body=[lock], type_ignores=[]), 'upgrade.py', 'exec'), ns)
        with tempfile.TemporaryDirectory() as root, ns['ols_upgrade_lock'](root):
            with self.assertRaisesRegex(RuntimeError, 'in progress'), ns['ols_upgrade_lock'](root):
                self.fail('second transaction entered')

    def test_config_migration_authorizes_controller_before_applying_changes(self):
        tree = ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'apply_ols_config_changes')
        for refused in (False, True):
            with self.subTest(refused=refused):
                service = Mock()
                if refused:
                    service.authorize_recovered_jammy_controller.side_effect = RuntimeError('unreviewed bundle')
                helper = Mock(OLSService=Mock(return_value=service))
                def apply(changes, validate, actual):
                    service.verify_stock_recovery_policy.assert_called_once_with()
                    service.authorize_recovered_jammy_controller.assert_called_once_with()
                    self.assertIs(actual, service)
                helper.apply_config_changes.side_effect = apply
                ns = dict(ols_upgrade_lock=nullcontext, load_ols_diagnostic_helper=lambda name: helper,
                          validate_ols_configuration=Mock(), OLSUpgradeFailure=RuntimeError)
                exec(compile(ast.Module(body=[node], type_ignores=[]), 'upgrade.py', 'exec'), ns)
                if refused:
                    with self.assertRaisesRegex(RuntimeError, 'unreviewed bundle'):
                        ns['apply_ols_config_changes']([('config', b'new')])
                    helper.apply_config_changes.assert_not_called()
                else:
                    ns['apply_ols_config_changes']([('config', b'new')])
                    helper.apply_config_changes.assert_called_once()

    def test_policy_refusal_happens_before_native_validation(self):
        ns = load()
        lifecycle, validator = Mock(), Mock()
        lifecycle.OLSService.return_value.verify_stock_recovery_policy.side_effect = RuntimeError('core lacks policy support')
        ns['load_ols_diagnostic_helper'] = lambda name: lifecycle if name == 'olsServiceControl.py' else validator
        with self.assertRaisesRegex(RuntimeError, 'core lacks policy support'):
            ns['validate_ols_configuration']()
        validator.validate.assert_not_called()

    def test_native_exit_codes(self):
        ns = load()
        for code, output, accepted in [(0,'',True),(1,'[WARN] fixture',True),
                                       (1,'[StockRecovery] Native AutoSSL remains inactive to preserve stock behavior',True),
                                       (1,'[StockRecovery] Native AutoSSL remains inactive to preserve stock behavior\n[ERROR] fixture',False),(2,'[ERROR] fixture',False),(-11,'',False),(0,'[ERROR] fixture',False),(1,'[FATAL] fixture',False),(0,'incompatible OpenLiteSpeed core ABI',False)]:
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
        self.run_later_failure(False,Mock(return_value=None))

    def test_success_and_skip_never_reconfigure_or_restart_ols_after_transaction(self):
        # Halt at the next non-OLS stage. Exercise the entry used by both CLI
        # and the panel worker, including the before-helper legacy install.
        class NextStage(Exception):
            pass

        for branch in ('v3.0.8', 'SoftUpgrade,v3.0.8'):
            for result in (True, None):
                with self.subTest(branch=branch, result=result):
                    ns = load()
                    ns['validate_ols_configuration'] = Mock(return_value=None)
                    target = ns['Upgrade']
                    target.installCustomOLSBinaries.return_value = result
                    target.updateRepoURL.side_effect = NextStage()
                    with patch.object(os.path, 'exists', side_effect=lambda path: path == '/usr/local/lsws/bin/openlitespeed'), \
                            patch.object(subprocess, 'check_output', return_value=b''), self.assertRaises(NextStage):
                        ns['upgrade'](branch)
                    target.installCustomOLSBinaries.assert_called_once_with(None, accepted=None)
                    target.configureCustomModule.assert_not_called()
                    target.executioner.assert_not_called()

    ABI = SimpleNamespace(returncode=1, stderr='', stdout='[cyberpanel_ols] Module v2.7.7 DISABLED: '
                          'incompatible OpenLiteSpeed core ABI (expected CyberPanel OLS 2.5.2)')
    BASELINE = {'returncode': 1, 'errors': ['[cyberpanel_ols] Module v2.7.7 DISABLED']}

    def split_namespace(self, state=None, refusal=None, broken=None):
        ns = load()

        class Refused(RuntimeError):
            pass

        def split_state(binary, returncode, output, parser):
            if broken:
                raise broken
            if refusal:
                raise Refused(refusal)
            return state

        ns['load_ols_diagnostic_helper'] = lambda name: SimpleNamespace(
            validate=lambda binary: subprocess.run([binary, '-t']), recovery_hint=lambda *args: '',
            stock_recovery_hint=lambda *args: '', OLSService=Mock(), split_state=split_state,
            SplitStateRefused=Refused)
        return ns

    def test_vendor_core_beside_our_module_is_accepted_only_where_the_transaction_asks(self):
        ns = self.split_namespace(self.BASELINE)
        validate = ns['validate_ols_configuration']
        with patch.object(subprocess, 'run', return_value=self.ABI):
            self.assertEqual(validate(split=True), self.BASELINE)
            self.assertEqual(validate(split=dict(self.BASELINE)), self.BASELINE)
            with self.assertRaisesRegex(RuntimeError, 'validation failed'):
                validate()  # Every other caller keeps refusing this state.
            with self.assertRaisesRegex(RuntimeError, 'no longer present'):
                validate(split={'returncode': 2, 'errors': []})
        with patch.object(subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')):
            self.assertIsNone(validate(split=True))
            self.assertIsNone(validate())
            with self.assertRaisesRegex(RuntimeError, 'no longer present'):
                validate(split=self.BASELINE)  # A rollback target must be the recorded state.

    def test_vendor_core_refusals_and_a_broken_classifier_never_waive_validation(self):
        with patch.object(subprocess, 'run', return_value=self.ABI):
            with self.assertRaisesRegex(RuntimeError, r'^errors the vendor core did not cause: \[ERROR\] x$'):
                self.split_namespace(refusal='errors the vendor core did not cause: [ERROR] x')[
                    'validate_ols_configuration'](split=True)
            for broken in (SyntaxError('broken helper'), AttributeError('incomplete helper')):
                with self.subTest(broken=broken), self.assertRaisesRegex(RuntimeError, 'validation failed.*core ABI'):
                    self.split_namespace(self.BASELINE, broken=broken)['validate_ols_configuration'](split=True)
            # A CyberPanel core that prints the diagnostic is not this state.
            with self.assertRaisesRegex(RuntimeError, 'validation failed'):
                self.split_namespace(None)['validate_ols_configuration'](split=True)

    def run_transaction(self, baseline, installed):
        class NextStage(Exception):
            pass
        ns = load()
        ns['validate_ols_configuration'] = Mock(return_value=baseline)
        target = ns['Upgrade']
        target.installCustomOLSBinaries.return_value = installed
        target.updateRepoURL.side_effect = NextStage()
        with patch.object(os.path, 'exists', side_effect=lambda path: path == '/usr/local/lsws/bin/openlitespeed'), \
                patch.object(subprocess, 'check_output', return_value=b''):
            try:
                ns['upgrade']('v3.0.8')
            except NextStage:
                pass
        ns['validate_ols_configuration'].assert_called_once_with(split=True)
        target.installCustomOLSBinaries.assert_called_once_with(baseline, accepted=None)
        return target

    def test_vendor_core_baseline_reaches_the_bundle_transaction(self):
        self.run_transaction(self.BASELINE, True)

    def test_vendor_core_without_a_bundle_stops_the_upgrade(self):
        with self.assertRaisesRegex(RuntimeError, 'no CyberPanel OpenLiteSpeed bundle is available'):
            self.run_transaction(self.BASELINE, None)
        self.run_transaction(None, None)  # A platform that keeps vendor OLS by design continues.

    def test_recovery_policy_beside_a_vendor_core_is_left_to_the_bundle_transaction(self):
        for custom, split, refused in ((False, True, False), (False, self.BASELINE, False),
                                       (False, None, True), (True, True, True)):
            with self.subTest(custom_core=custom, split=split):
                ns = self.split_namespace(self.BASELINE)
                helper = ns['load_ols_diagnostic_helper']('any')
                helper.OLSService.return_value.verify_stock_recovery_policy.side_effect = RuntimeError(
                    'Installed or candidate core does not support the stock recovery policy')
                helper.custom_core = lambda binary: custom
                ns['load_ols_diagnostic_helper'] = lambda name: helper
                with patch.object(subprocess, 'run', return_value=self.ABI):
                    if refused:
                        with self.assertRaisesRegex(RuntimeError, 'does not support the stock recovery policy'):
                            ns['validate_ols_configuration'](split=split)
                    else:
                        self.assertEqual(ns['validate_ols_configuration'](split=split), self.BASELINE)

    def test_vendor_core_rollback_restarts_only_the_recorded_state(self):
        tree = ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
        method = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == 'installCustomOLSBinaries')
        calls = [ast.unparse(n) for n in ast.walk(method) if isinstance(n, ast.Call)
                 and isinstance(n.func, ast.Name) and n.func.id == 'validate_ols_configuration']
        # Before the stop and in the rollback the recorded state is required;
        # the installed candidate is always validated strictly.
        self.assertEqual(sorted(calls), ['validate_ols_configuration(OLS_BINARY_PATH)',
                                         'validate_ols_configuration(OLS_BINARY_PATH, recorded)',
                                         'validate_ols_configuration(OLS_BINARY_PATH, recorded)'])

    def test_new_bundle_validation_is_inside_rollback_before_start(self):
        tree=ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        klass=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Upgrade')
        method=next(n for n in klass.body if isinstance(n,ast.FunctionDef) and n.name=='installCustomOLSBinaries')
        rollback_try=next(n for n in ast.walk(method) if isinstance(n,ast.Try) and any(isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='validate_ols_configuration' for x in n.body))
        validation=next(x for x in rollback_try.body if isinstance(x,ast.Expr) and isinstance(x.value,ast.Call) and isinstance(x.value.func,ast.Name) and x.value.func.id=='validate_ols_configuration')
        later=ast.unparse(ast.Module(body=[x for x in rollback_try.body if x.lineno>validation.lineno],type_ignores=[]))
        self.assertIn("service.change('start', None)",later)
        self.assertIn('restoring the previous OLS bundle',ast.unparse(rollback_try.handlers))

    # --- A declaration of the CyberPanel module on a server that never received it ---
    MISSING = SimpleNamespace(returncode=2, stderr='', stdout=(
        '2026-11-24 07:52:07.891010 [ERROR] [200193] Failed to load module [cyberpanel_ols], error: '
        '/usr/local/lsws//modules/cyberpanel_ols.so: cannot open shared object file: No such file or directory'))
    STALE = {'state': 'stale-module-stanza', 'returncode': 2, 'errors': ['[ERROR] Failed to load module']}

    def stale_namespace(self, state):
        ns = load()
        ns['load_ols_diagnostic_helper'] = lambda name: SimpleNamespace(
            validate=lambda binary: subprocess.run([binary, '-t']), recovery_hint=lambda *args: '',
            stock_recovery_hint=lambda *args: '', OLSService=Mock(),
            split_state=Mock(side_effect=AssertionError('not a split state')),
            stale_module_stanza=lambda binary, returncode, output: state)
        return ns

    def test_stale_declaration_is_accepted_only_where_the_transaction_asks(self):
        validate = self.stale_namespace(self.STALE)['validate_ols_configuration']
        with patch.object(subprocess, 'run', return_value=self.MISSING):
            self.assertEqual(validate(split=True), self.STALE)
            self.assertEqual(validate(split=dict(self.STALE)), self.STALE)
            with self.assertRaisesRegex(RuntimeError, 'validation failed.*cyberpanel_ols'):
                validate()  # Every other caller keeps refusing this state.
        with patch.object(subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='', stderr='')):
            with self.assertRaisesRegex(RuntimeError, 'no longer present'):
                validate(split=self.STALE)  # A rollback target must be the recorded state.
        # Not this state (another error, or a classifier that says no): refused as before.
        with patch.object(subprocess, 'run', return_value=self.MISSING), \
                self.assertRaisesRegex(RuntimeError, 'validation failed'):
            self.stale_namespace(None)['validate_ols_configuration'](split=True)

    def stale_upgrade(self, branch, installed):
        class NextStage(Exception):
            pass
        ns = load()
        ns['validate_ols_configuration'] = Mock(return_value=dict(self.STALE))
        ns['remove_stale_module_stanza'] = Mock()
        target = ns['Upgrade']
        target.installCustomOLSBinaries.return_value = installed
        target.updateRepoURL.side_effect = NextStage()
        with patch.object(os.path, 'exists', side_effect=lambda path: path == '/usr/local/lsws/bin/openlitespeed'), \
                patch.object(subprocess, 'check_output', return_value=b''):
            try:
                ns['upgrade'](branch)
            except NextStage:
                pass
        ns['validate_ols_configuration'].assert_called_once_with(split=True)
        # Never handed over as a vendor-core state: no Jammy policy, no split message.
        target.installCustomOLSBinaries.assert_called_once_with(None, accepted=self.STALE)
        return ns

    def test_stale_declaration_is_kept_where_the_bundle_installs_the_module(self):
        for branch in ('v3.0.8', 'SoftUpgrade,v3.0.8'):
            with self.subTest(branch=branch):
                ns = self.stale_upgrade(branch, True)
                ns['remove_stale_module_stanza'].assert_not_called()
                ns['Upgrade'].configureCustomModule.assert_not_called()

    def test_stale_declaration_is_removed_where_no_cyberpanel_build_exists(self):
        for branch in ('v3.0.8', 'SoftUpgrade,v3.0.8'):
            with self.subTest(branch=branch):
                ns = self.stale_upgrade(branch, None)
                ns['remove_stale_module_stanza'].assert_called_once_with(self.STALE)

    def test_failed_bundle_leaves_the_stale_declaration_for_the_next_run(self):
        with self.assertRaisesRegex(RuntimeError, 'Custom OLS bundle installation failed'):
            self.stale_upgrade('v3.0.8', False)


class StaleDeclarationRemovalTests(unittest.TestCase):
    """remove_stale_module_stanza on a real file tree with the real classifier."""
    STANZA = '\nmodule cyberpanel_ols {\n  ls_enabled          1\n}\n'
    CONFIG = 'serverName example\nmodule cache {\n  ls_enabled 1\n}\n'

    def setUp(self):
        import importlib.util
        import shutil
        import tempfile
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / 'lsws'
        for name in ('bin', 'modules', 'conf'):
            (self.root / name).mkdir(parents=True)
        self.core = self.root / 'bin/openlitespeed'
        self.core.write_bytes(b'\x7fELF vendor core')
        self.config = self.root / 'conf/httpd_config.conf'
        self.config.write_text(self.CONFIG + self.STANZA)
        self.config.chmod(0o640)
        spec = importlib.util.spec_from_file_location('removal_classifier', str(Path(__file__).with_name('olsStockClassifier.py')))
        self.classifier = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.classifier)
        self.results = []
        self.validator = SimpleNamespace(validate=Mock(side_effect=lambda binary: self.results.pop(0)))
        tree = ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'remove_stale_module_stanza')
        klass = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Upgrade')
        copy = next(n for n in klass.body if isinstance(n, ast.FunctionDef) and n.name == 'copyOLSBackup')
        copy.decorator_list = []
        helpers = {'os': os, 'shutil': shutil}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[copy], type_ignores=[])), 'upgrade.py', 'exec'), helpers)
        self.upgrade = SimpleNamespace(copyOLSBackup=helpers['copyOLSBackup'], stdOut=Mock())
        self.ns = {'os': os, 'OLSUpgradeFailure': RuntimeError, 'Upgrade': self.upgrade,
                   'load_ols_diagnostic_helper': lambda name: self.classifier if name == 'olsStockClassifier.py' else self.validator}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), 'upgrade.py', 'exec'), self.ns)

    def missing(self, *extra):
        line = ('2026-11-24 07:52:07.891010 [ERROR] [200193] Failed to load module [cyberpanel_ols], error: '
                '%s//modules/cyberpanel_ols.so: cannot open shared object file: No such file or directory' % self.root)
        return SimpleNamespace(returncode=2, stdout='\n'.join((line,) + extra), stderr='')

    def remove(self, *results):
        self.results = list(results)
        baseline = self.classifier.stale_module_stanza(self.core, 2, self.missing().stdout)
        self.assertIsNotNone(baseline)
        return self.ns['remove_stale_module_stanza'](baseline, binary=str(self.core))

    def backups(self):
        return sorted(self.root.glob('conf/httpd_config.conf.cyberpanel-*.before-module-removal'))

    def test_exactly_the_declaration_is_removed_and_a_copy_kept(self):
        before = self.config.read_bytes()
        backup = self.remove(self.missing(), SimpleNamespace(returncode=0, stdout='', stderr=''))
        self.assertEqual(self.config.read_text(), self.CONFIG + '\n')
        self.assertEqual(oct(self.config.stat().st_mode & 0o777), '0o640')
        self.assertEqual(self.backups(), [Path(backup)])
        self.assertEqual(Path(backup).read_bytes(), before)
        self.assertEqual(self.validator.validate.call_count, 2)
        self.assertEqual(list(self.root.glob('conf/.httpd_config.*')), [])
        self.assertIn(backup, self.upgrade.stdOut.call_args[0][0])

    def test_website_errors_that_were_there_before_do_not_refuse(self):
        site = ('2026-11-24 07:52:07.9 [ERROR] [200193] [config:server:vhosts:vhost:a.com:epsr:lsphp73] '
                'invalid path - /usr/local/lsws/lsphp73/bin/lsphp')
        self.results = [self.missing(site), SimpleNamespace(returncode=2, stdout=site, stderr='')]
        baseline = self.classifier.stale_module_stanza(self.core, 2, self.missing(site).stdout)
        self.ns['remove_stale_module_stanza'](baseline, binary=str(self.core))
        self.assertNotIn('cyberpanel_ols', self.config.read_text())

    def test_a_changed_state_is_not_touched(self):
        before = self.config.read_bytes()
        changed = self.missing('2026-11-24 07:52:08.0 [ERROR] [1] [PlainConf] something new')
        with self.assertRaisesRegex(RuntimeError, 'changed during the upgrade'):
            self.remove(changed)
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(self.backups(), [])

    def test_failed_validation_puts_the_previous_file_back(self):
        before = self.config.read_bytes()
        for after in (SimpleNamespace(returncode=2, stdout='[ERROR] [1] [PlainConf] broken', stderr=''),
                      SimpleNamespace(returncode=-11, stdout='', stderr='')):
            with self.subTest(after=after):
                with self.assertRaisesRegex(RuntimeError, 'previous configuration was restored'):
                    self.remove(self.missing(), after)
                self.assertEqual(self.config.read_bytes(), before)
                self.assertEqual(oct(self.config.stat().st_mode & 0o777), '0o640')
                self.assertEqual(list(self.root.glob('conf/.httpd_config.*')), [])

    def test_a_failed_write_changes_nothing(self):
        before = self.config.read_bytes()
        real = os.replace
        with patch.object(os, 'replace', side_effect=[OSError('disk full'), real]) as replace:
            with self.assertRaisesRegex(RuntimeError, 'disk full'):
                self.remove(self.missing())
        self.assertEqual(self.config.read_bytes(), before)
        self.assertEqual(list(self.root.glob('conf/.httpd_config.*')), [])

if __name__=='__main__':unittest.main()
