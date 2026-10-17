import ast
import copy
import fcntl
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock
from types import SimpleNamespace

from plogical.olsHtaccessReload import CRON, LEGACY, snapshot_rules, merge_defaults, migrate_cron, run


class WatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.home = self.root / 'home'
        self.site = self.home / 'fixture' / 'public_html'
        self.site.mkdir(parents=True)
        self.rule = self.site / '.htaccess'
        self.rule.write_text('RewriteEngine On')
        os.utime(self.rule, ns=(100, 100))
        self.state = str(self.root / 'private')
        self.reload = mock.Mock()

    def invoke(self):
        return run(self.state, str(self.home), reload=self.reload)

    def test_unchanged_rules_reload_once_then_new_edit_reloads(self):
        self.assertEqual('reloaded', self.invoke())
        self.assertEqual('unchanged', self.invoke())
        self.assertEqual('unchanged', self.invoke())
        self.reload.assert_called_once()
        os.utime(self.rule, ns=(500, 500))
        self.assertEqual('reloaded', self.invoke())
        self.assertEqual(2, self.reload.call_count)
        self.assertEqual(0o700, os.stat(self.state).st_mode & 0o777)
        self.assertEqual(0o600, os.stat(Path(self.state) / 'snapshot.json').st_mode & 0o777)

    def test_future_mtime_does_not_reload_repeatedly(self):
        future = 4_000_000_000_000_000_000
        os.utime(self.rule, ns=(future, future))
        self.assertEqual('reloaded', self.invoke())
        self.assertEqual('unchanged', self.invoke())
        self.assertEqual('unchanged', self.invoke())
        self.reload.assert_called_once()

    def test_preserved_mtime_edit_is_detected_by_other_stat_fields(self):
        self.invoke()
        self.rule.write_text('Changed content with an intentionally restored mtime')
        os.utime(self.rule, ns=(100, 100))
        self.assertEqual('reloaded', self.invoke())
        self.assertEqual('unchanged', self.invoke())

    def test_reload_failure_retries_and_preserves_previous_snapshot(self):
        self.invoke()
        previous = (Path(self.state) / 'snapshot.json').read_text()
        os.utime(self.rule, ns=(300, 300))
        self.reload.side_effect = subprocess.CalledProcessError(1, 'reload')
        with self.assertRaises(subprocess.CalledProcessError):
            self.invoke()
        self.assertEqual(previous, (Path(self.state) / 'snapshot.json').read_text())
        self.reload.side_effect = None
        self.assertEqual('reloaded', self.invoke())

    def test_edit_during_reload_remains_pending_in_next_snapshot(self):
        self.reload.side_effect = lambda: os.utime(self.rule, ns=(300, 300))
        self.assertEqual('reloaded', self.invoke())
        self.reload.side_effect = None
        self.assertEqual('reloaded', self.invoke())
        self.assertEqual('unchanged', self.invoke())

    def test_scan_error_does_not_reload_or_advance(self):
        self.invoke()
        previous = (Path(self.state) / 'snapshot.json').read_text()
        with mock.patch('plogical.olsHtaccessReload.os.scandir', side_effect=PermissionError('fixture')):
            with self.assertRaises(PermissionError):
                self.invoke()
        self.reload.assert_called_once()
        self.assertEqual(previous, (Path(self.state) / 'snapshot.json').read_text())

    def test_overlapping_run_does_not_scan_or_reload(self):
        self.invoke()
        with open(Path(self.state) / 'lock') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.assertEqual('busy', self.invoke())
        self.reload.assert_called_once()

    def test_insecure_or_symlink_state_is_refused(self):
        Path(self.state).mkdir(mode=0o755)
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            self.invoke()
        Path(self.state).rmdir()
        Path(self.state).symlink_to(self.site)
        with self.assertRaisesRegex(RuntimeError, 'Unsafe'):
            self.invoke()
        self.reload.assert_not_called()

    def test_only_regular_rules_in_original_scan_depth(self):
        self.rule.unlink()
        nested = self.site / 'one' / 'two'
        nested.mkdir(parents=True)
        (nested / '.htaccess').write_text('ignored')
        (self.site / '.htaccess').symlink_to(nested / '.htaccess')
        self.assertFalse(snapshot_rules(str(self.home)))
        (self.site / 'one' / '.htaccess').write_text('included')
        self.assertTrue(snapshot_rules(str(self.home)))


class CronMigrationTests(unittest.TestCase):
    def test_legacy_variants_deduplicate_and_preserve_other_content(self):
        first = LEGACY % 'systemctl restart lsws'
        second = LEGACY % '/usr/local/lsws/bin/lswsctrl restart'
        untouched = '# disabled custom workaround\n#' + first + '\nMAILTO=root\n1 2 * * * /root/custom\n'
        source = untouched + first + '\n' + second + '\n'
        result = migrate_cron(source, True)
        self.assertEqual(untouched + CRON + '\n', result)
        self.assertEqual(result, migrate_cron(result, True))

    def test_enterprise_removes_only_recognized_watcher(self):
        disabled = '# ' + LEGACY % 'systemctl restart lsws' + '\n'
        custom = '*/3 * * * * /root/custom-watcher\n'
        self.assertEqual(disabled + custom, migrate_cron(disabled + CRON + '\n' + custom, False))
        self.assertEqual(custom, migrate_cron(custom, False))

    def test_merge_defaults_preserves_customized_schedule_and_no_final_newline(self):
        existing = '# retained\n1 2 * * * /root/stock'
        defaults = '0 0 * * * /root/stock\n0 1 * * * /root/new\n'
        result = merge_defaults(existing, defaults)
        self.assertEqual(existing + '\n0 1 * * * /root/new\n', result)
        self.assertEqual(result, merge_defaults(result, defaults))


class InstallerIntegrationTests(unittest.TestCase):
    def test_real_setup_method_preserves_custom_cron_and_skips_enterprise_watcher(self):
        source = Path(__file__).parents[1] / 'install' / 'install.py'
        tree = ast.parse(source.read_text())
        method = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef) and node.name == 'setup_cron')
        for is_ols in (True, False):
            with self.subTest(is_ols=is_ols), tempfile.TemporaryDirectory() as temporary:
                cron = Path(temporary) / 'root-cron'
                existing = '# user disabled stock workaround\n1 2 * * * /root/custom\n'
                cron.write_text(existing)
                class Paths(ast.NodeTransformer):
                    def visit_Constant(self, node):
                        if isinstance(node.value, str) and node.value in (
                                '/var/spool/cron/root', '/var/spool/cron/crontabs/root'):
                            return ast.copy_location(ast.Constant(str(cron)), node)
                        return node
                module = ast.Module(body=[Paths().visit(copy.deepcopy(method))], type_ignores=[])
                ast.fix_missing_locations(module)
                environment = dict(os=os, merge_defaults=merge_defaults, migrate_cron=migrate_cron,
                                   preFlightsChecks=SimpleNamespace(call=mock.Mock()),
                                   logging=SimpleNamespace(InstallLog=SimpleNamespace(writeToFile=mock.Mock())))
                exec(compile(module, str(source), 'exec'), environment)
                installer = SimpleNamespace(is_centos_family=lambda: False,
                                            install_package=mock.Mock(), manage_service=mock.Mock(), distro='ubuntu')
                exists = os.path.exists
                def fixture_exists(path):
                    if path == '/usr/local/lsws/bin/openlitespeed':
                        return is_ols
                    return exists(path)
                with mock.patch('os.path.exists', side_effect=fixture_exists):
                    environment['setup_cron'](installer)
                result = cron.read_text()
                self.assertTrue(result.startswith(existing))
                self.assertEqual(is_ols, CRON in result)
                self.assertIn('findBWUsage.py', result)
                environment['logging'].InstallLog.writeToFile.assert_not_called()


class UpgradeBootstrapTests(unittest.TestCase):
    def test_standalone_upgrade_starts_without_new_helper_in_old_tree(self):
        import builtins
        import sys
        import types
        source = Path(__file__).with_name('upgrade.py').read_text()
        original_import = builtins.__import__
        def old_tree_import(name, *args, **kwargs):
            if name == 'plogical.olsHtaccessReload':
                raise ImportError('Old installation does not contain the new helper')
            return original_import(name, *args, **kwargs)
        old_panel = types.ModuleType('CyberCP')
        old_panel.settings = object()  # Avoid unrelated database recovery side effects.
        old_sys_path = sys.path[:]
        try:
            with mock.patch.dict(sys.modules, {'CyberCP': old_panel, 'MySQLdb': types.ModuleType('MySQLdb')}), \
                    mock.patch('builtins.__import__', side_effect=old_tree_import):
                environment = {'__name__': 'standalone_upgrade_bootstrap_test'}
                exec(compile(source, 'upgrade.py', 'exec'), environment)
            self.assertTrue(callable(environment['main']))
            self.assertTrue(callable(environment['Upgrade'].runSomeImportantBash))
        finally:
            sys.path[:] = old_sys_path

    def test_cron_phase_is_after_checked_source_activation(self):
        source = Path(__file__).with_name('upgrade.py').read_text()
        tree = ast.parse(source)
        method = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef) and node.name == 'upgrade')
        calls = {node.func.attr: node.lineno for node in ast.walk(method)
                 if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                 and isinstance(node.func.value, ast.Name) and node.func.value.id == 'Upgrade'}
        self.assertLess(calls['downloadAndUpgrade'], calls['runSomeImportantBash'])
        guard = next(node for node in method.body if isinstance(node, ast.If)
                     and isinstance(node.test, ast.Compare)
                     and isinstance(node.test.left, ast.Name) and node.test.left.id == 'download_status')
        self.assertTrue(any(isinstance(node, ast.Raise) for node in ast.walk(guard)))
        download = next(node for node in ast.walk(tree)
                        if isinstance(node, ast.FunctionDef) and node.name == 'downloadAndUpgrade')
        self.assertTrue(any(isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                            and node.func.id == 'activate_source' for node in ast.walk(download)))

    def test_real_upgrade_cron_phase_preserves_disabled_and_custom_lines(self):
        source = Path(__file__).with_name('upgrade.py')
        tree = ast.parse(source.read_text())
        method = next(node for node in ast.walk(tree)
                      if isinstance(node, ast.FunctionDef) and node.name == 'runSomeImportantBash')
        for is_ols in (True, False):
            with self.subTest(is_ols=is_ols), tempfile.TemporaryDirectory() as temporary:
                cron = Path(temporary) / 'root-cron'
                disabled = '# ' + LEGACY % 'systemctl restart lsws' + '\n'
                custom = '1 2 * * * /root/retained\n'
                active = LEGACY % 'systemctl restart lsws' + '\n'
                cron.write_text(disabled + custom + active)
                class Paths(ast.NodeTransformer):
                    def visit_Constant(self, node):
                        if isinstance(node.value, str) and node.value in (
                                '/var/spool/cron/root', '/var/spool/cron/crontabs/root'):
                            return ast.copy_location(ast.Constant(str(cron)), node)
                        return node
                fixture = copy.deepcopy(method)
                fixture.decorator_list = []
                module = ast.Module(body=[Paths().visit(fixture)], type_ignores=[])
                ast.fix_missing_locations(module)
                environment = dict(os=os, Upgrade=SimpleNamespace(executioner=mock.Mock()),
                                   stagger_renewal_cron=lambda data: data)
                exec(compile(module, str(source), 'exec'), environment)
                exists = os.path.exists
                def fixture_exists(path):
                    if path == str(cron):
                        return exists(path)
                    if path == '/usr/local/lsws/bin/openlitespeed':
                        return is_ols
                    if path == '/usr/local/lscp/logs':
                        return True
                    return False
                with mock.patch('os.path.exists', side_effect=fixture_exists):
                    environment['runSomeImportantBash']()
                    first = cron.read_text()
                    environment['runSomeImportantBash']()
                self.assertTrue(first.startswith(disabled + custom))
                self.assertEqual(is_ols, CRON in first)
                self.assertEqual(first, cron.read_text())


if __name__ == '__main__':
    unittest.main()
