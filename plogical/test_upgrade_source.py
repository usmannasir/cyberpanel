import ast
import copy
import os
import shutil
import shlex
import re
import types
import sys
from contextlib import contextmanager
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch, call

# Importing upgrade.py starts database recovery on hosts without CyberPanel.
# Execute its actual standalone file helpers without those unrelated side effects.
source = Path(__file__).with_name('upgrade.py').read_text()
helper_names = {'_copy_path', 'activate_source', 'preserve_installation_state',
                'protect_private_files', 'prune_previous_installations',
                '_literal_installed_apps', 'preserve_installed_plugins',
                '_literal_cookie_hardening', 'merge_cookie_hardening'}
module = types.ModuleType('upgrade_source_under_test')
module.__dict__.update(os=os, shutil=shutil, tempfile=tempfile, ast=ast, re=re,
                       contextmanager=contextmanager, preserving_csf=lambda: False,
                       requireCSFMigration=lambda: None)
parsed_source = ast.parse(source)
helper_tree = ast.Module(body=[node for node in parsed_source.body
                              if isinstance(node, ast.FunctionDef)
                              and node.name in helper_names], type_ignores=[])
exec(compile(helper_tree, 'upgrade.py', 'exec'), module.__dict__)
sys.modules[module.__name__] = module
activate_source = module.activate_source
preserve_installation_state = module.preserve_installation_state
protect_private_files = module.protect_private_files
prune_previous_installations = module.prune_previous_installations



class UpgradeSourceTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.current = self.root / 'CyberCP'
        self.staged = self.root / 'staged'
        self.current.mkdir()
        self.staged.mkdir()
        self.write(self.current / 'old_source.py', 'old application')
        self.write(self.staged / 'new_source.py', 'new application')
        # Rollback deliberately leaves cwd in the installation's parent.
        self.cwd = os.getcwd()
        self.addCleanup(os.chdir, self.cwd)

    @staticmethod
    def write(path, content='test'):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    def preserve(self, configs=None):
        preserve_installation_state(str(self.current), str(self.staged), configs or {})

    def test_embedded_venv_survives_without_stale_application_source(self):
        self.write(self.current / 'pyvenv.cfg', 'home = /usr/bin')
        self.write(self.current / 'bin/python', 'runtime')
        os.chmod(self.current / 'bin/python', 0o755)
        self.write(self.current / 'lib/python3.12/site-packages/django/__init__.py')
        self.write(self.current / 'include/Python.h')
        self.write(self.current / 'share/man/venv.1')
        (self.current / 'lib64').symlink_to('lib')
        self.preserve()
        with activate_source(str(self.current), str(self.staged)) as previous:
            self.assertTrue((self.current / 'new_source.py').exists())
            self.assertFalse((self.current / 'old_source.py').exists())
            self.assertEqual('runtime', (self.current / 'bin/python').read_text())
            self.assertEqual(0o755, stat.S_IMODE((self.current / 'bin/python').stat().st_mode))
            self.assertEqual('lib', os.readlink(self.current / 'lib64'))
            self.assertTrue((self.current / 'lib/python3.12/site-packages/django/__init__.py').exists())
            self.assertTrue((self.current / 'include/Python.h').exists())
            self.assertTrue((self.current / 'share/man/venv.1').exists())
        self.assertTrue((Path(previous) / 'old_source.py').exists())
        self.assertEqual(0o700, stat.S_IMODE(Path(previous).parent.stat().st_mode))

    def test_legacy_virtualenv_without_pyvenv_cfg_survives(self):
        self.write(self.current / 'bin/activate')
        (self.current / 'bin/python').symlink_to('/usr/bin/python3')
        self.write(self.current / 'lib/python3.6/site-packages/MySQLdb/__init__.py')
        self.preserve()
        self.assertEqual('/usr/bin/python3', os.readlink(self.staged / 'bin/python'))
        self.assertTrue((self.staged / 'lib/python3.6/site-packages/MySQLdb/__init__.py').exists())

    def test_separate_runtime_is_untouched_and_source_dirs_are_not_copied(self):
        external = self.root / 'CyberPanel'
        self.write(external / 'bin/python', 'external runtime')
        self.write(self.current / 'lib/old_application.py')
        self.preserve()
        with activate_source(str(self.current), str(self.staged)):
            self.assertEqual('external runtime', (external / 'bin/python').read_text())
            self.assertFalse((self.current / 'lib').exists())

    def test_absolute_runtime_symlinks_remain_symlinks(self):
        self.write(self.current / 'pyvenv.cfg')
        external = self.root / 'external-lib'
        self.write(external / 'dependency.py')
        (self.current / 'lib').symlink_to(external)
        self.preserve()
        self.assertTrue((self.staged / 'lib').is_symlink())
        self.assertEqual(str(external), os.readlink(self.staged / 'lib'))

    def test_private_files_survive_but_settings_and_external_services_are_untouched(self):
        backups = self.root / 'backups'
        configs = {}
        for relative in ('.env', 'secret_key', 'terminal_jwt_secret',
                         'CyberCP/settings.py', 'public/phpmyadmin/config.inc.php'):
            backup = backups / relative
            self.write(backup, 'private ' + relative)
            configs[str(self.current / relative)] = str(backup)
        self.write(self.staged / 'CyberCP/settings.py', 'new applications')
        external = self.root / 'service.conf'
        configs[str(external)] = str(backups / '.env')
        self.preserve(configs)
        self.assertEqual('private .env', (self.staged / '.env').read_text())
        self.assertEqual('private terminal_jwt_secret', (self.staged / 'terminal_jwt_secret').read_text())
        self.assertEqual('new applications', (self.staged / 'CyberCP/settings.py').read_text())
        self.assertFalse(external.exists())

    def test_copy_failure_leaves_live_installation_available(self):
        configs = {str(self.current / '.env'): str(self.root / 'missing-backup')}
        with self.assertRaises(FileNotFoundError):
            self.preserve(configs)
        self.assertEqual('old application', (self.current / 'old_source.py').read_text())

    def test_failed_activation_restores_old_installation(self):
        rename = os.rename
        def fail_new_activation(source, destination):
            if source == str(self.staged):
                raise OSError('failed activation')
            return rename(source, destination)
        with patch('upgrade_source_under_test.os.rename', side_effect=fail_new_activation):
            with self.assertRaisesRegex(OSError, 'failed activation'):
                with activate_source(str(self.current), str(self.staged)):
                    self.fail('new source must not run')
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertTrue((self.staged / 'new_source.py').exists())

    def test_post_activation_failure_rolls_back_runtime_and_source(self):
        self.write(self.current / 'pyvenv.cfg', 'runtime configuration')
        self.preserve()
        with self.assertRaisesRegex(RuntimeError, 'collectstatic failed'):
            with activate_source(str(self.current), str(self.staged)):
                os.chdir(self.current)
                raise RuntimeError('collectstatic failed')
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertFalse((self.current / 'new_source.py').exists())
        self.assertEqual('runtime configuration', (self.current / 'pyvenv.cfg').read_text())

    def test_failed_initial_rename_preserves_live_installation(self):
        with patch('upgrade_source_under_test.os.rename', side_effect=OSError('read only')):
            with self.assertRaises(OSError):
                with activate_source(str(self.current), str(self.staged)):
                    self.fail('activation must fail')
        self.assertTrue((self.current / 'old_source.py').exists())

    def test_private_file_permissions_are_ready_before_activation(self):
        for relative in ('CyberCP/settings.py', '.env', 'secret_key',
                         '.env.backup', 'terminal_jwt_secret'):
            self.write(self.staged / relative, 'secret')
        with patch('upgrade_source_under_test.os.chown') as chown:
            protect_private_files(str(self.staged), 1001, 1002)
        for relative in ('CyberCP/settings.py', '.env', 'secret_key'):
            self.assertEqual(0o640, stat.S_IMODE((self.staged / relative).stat().st_mode))
            self.assertIn(call(str(self.staged / relative), 0, 1002), chown.call_args_list)
        self.assertEqual(0o600, stat.S_IMODE((self.staged / '.env.backup').stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE((self.staged / 'terminal_jwt_secret').stat().st_mode))
        self.assertIn(call(str(self.staged / 'terminal_jwt_secret'), 1001, 1002), chown.call_args_list)

    def test_prune_keeps_current_rollback_and_ignores_unrelated_paths(self):
        keep_parent = self.root / '.cyberpanel-previous-keep'
        old_parent = self.root / '.cyberpanel-previous-old'
        unrelated = self.root / '.cyberpanel-previous-not-an-installation'
        self.write(keep_parent / 'CyberCP/old_source.py', 'latest rollback')
        self.write(old_parent / 'CyberCP/old_source.py', 'superseded rollback')
        self.write(unrelated / 'notes.txt', 'not an upgrade rollback')
        symlink = self.root / '.cyberpanel-previous-link'
        symlink.symlink_to(old_parent, target_is_directory=True)

        removed, failures = prune_previous_installations(
            str(self.current), str(keep_parent / 'CyberCP'))

        self.assertEqual([], failures)
        self.assertEqual([str(old_parent)], removed)
        self.assertTrue(keep_parent.exists())
        self.assertTrue(unrelated.exists())
        self.assertTrue(symlink.is_symlink())
        self.assertFalse(old_parent.exists())


class PluginPreservationTests(unittest.TestCase):
    write = staticmethod(UpgradeSourceTests.write)

    def setUp(self):
        UpgradeSourceTests.setUp(self)
        self.registry = self.root / 'plugins'
        self.write(self.registry / 'examplePlugin', '')
        self.write(self.current / 'examplePlugin/__init__.py', '')
        self.write(self.current / 'examplePlugin/data.txt', 'private plugin data')
        self.write(self.current / 'examplePlugin/pre_install', 'must never run')
        self.write(self.current / 'CyberCP/settings.py',
                   "INSTALLED_APPS = ['old_core', 'examplePlugin']\n")
        self.write(self.staged / 'CyberCP/settings.py', "INSTALLED_APPS = ['new_core']\n")
        self.write(self.current / 'CyberCP/urls.py',
                   "urlpatterns = [\n    url(r'^examplePlugin/', include('examplePlugin.urls')),\n]\n")
        self.write(self.staged / 'CyberCP/urls.py', "urlpatterns = []\n")

    def preserve_plugins(self):
        return module.preserve_installed_plugins(str(self.current), str(self.staged), str(self.registry))

    @unittest.skipUnless(os.geteuid() == 0, 'ownership preservation requires root')
    def test_csf_plugin_private_modes_and_ownership_survive_copy(self):
        (self.registry / 'examplePlugin').rename(self.registry / 'configservercsf')
        (self.current / 'examplePlugin').rename(self.current / 'configservercsf')
        source = self.current / 'configservercsf/data.txt'
        source.chmod(0o600)
        os.chown(source, 1234, 1235)
        with patch.object(module, 'preserving_csf', return_value=True):
            self.preserve_plugins()
        copied = self.staged / 'configservercsf/data.txt'
        self.assertEqual((1234, 1235, 0o600),
                         (copied.stat().st_uid, copied.stat().st_gid,
                          stat.S_IMODE(copied.stat().st_mode)))

    def test_plugin_files_and_activation_survive_source_swap(self):
        self.assertEqual(['examplePlugin'], self.preserve_plugins())
        with activate_source(str(self.current), str(self.staged)) as previous:
            self.assertEqual('private plugin data', (self.current / 'examplePlugin/data.txt').read_text())
            self.assertEqual(['new_core', 'examplePlugin'],
                             module._literal_installed_apps(str(self.current / 'CyberCP/settings.py')))
            self.assertIn("path('examplePlugin/', include('examplePlugin.urls'))",
                          (self.current / 'CyberCP/urls.py').read_text())
            self.assertFalse((self.current / 'old_source.py').exists())
        self.assertTrue((Path(previous) / 'examplePlugin/data.txt').exists())

    def test_second_upgrade_keeps_previously_preserved_app(self):
        self.preserve_plugins()
        with activate_source(str(self.current), str(self.staged)):
            pass
        self.staged.mkdir()
        self.write(self.staged / 'CyberCP/settings.py', "INSTALLED_APPS = ['next_core']\n")
        self.write(self.staged / 'CyberCP/urls.py', "urlpatterns = []\n")
        self.preserve_plugins()
        self.assertEqual(['next_core', 'examplePlugin'],
                         module._literal_installed_apps(str(self.staged / 'CyberCP/settings.py')))

    def test_tuple_settings_remain_valid(self):
        self.write(self.staged / 'CyberCP/settings.py', "INSTALLED_APPS = ('new_core',)\n")
        self.preserve_plugins()
        self.assertEqual(('new_core', 'examplePlugin'),
                         module._literal_installed_apps(str(self.staged / 'CyberCP/settings.py')))

    def test_disabled_plugin_is_copied_without_reenabling(self):
        self.write(self.current / 'CyberCP/settings.py', "INSTALLED_APPS = ['old_core']\n")
        self.write(self.current / 'CyberCP/urls.py', 'urlpatterns = []\n')
        self.preserve_plugins()
        self.assertEqual(['new_core'], module._literal_installed_apps(str(self.staged / 'CyberCP/settings.py')))
        self.assertNotIn('examplePlugin.urls', (self.staged / 'CyberCP/urls.py').read_text())

    def test_missing_plugin_stops_before_activation(self):
        shutil.rmtree(self.current / 'examplePlugin')
        with self.assertRaisesRegex(RuntimeError, 'plugin files missing'):
            self.preserve_plugins()
        self.assertTrue((self.current / 'old_source.py').exists())

    def test_core_collision_does_not_overwrite_release_code(self):
        self.write(self.staged / 'examplePlugin/__init__.py', 'new release')
        with self.assertRaisesRegex(RuntimeError, 'conflicts with release'):
            self.preserve_plugins()
        self.assertEqual('new release', (self.staged / 'examplePlugin/__init__.py').read_text())

    def test_invalid_registry_name_is_rejected(self):
        self.write(self.registry / 'bad-name', '')
        with self.assertRaisesRegex(RuntimeError, 'Invalid plugin registry'):
            self.preserve_plugins()

    def test_linked_plugin_is_rejected(self):
        shutil.rmtree(self.current / 'examplePlugin')
        (self.current / 'examplePlugin').symlink_to(self.root)
        with self.assertRaisesRegex(RuntimeError, 'plugin files missing or linked'):
            self.preserve_plugins()

    def test_custom_route_stops_for_review(self):
        self.write(self.current / 'CyberCP/urls.py',
                   "urlpatterns = [path('custom/', include('examplePlugin.urls'))]\n")
        with self.assertRaisesRegex(RuntimeError, 'Custom plugin route'):
            self.preserve_plugins()


class CookieHardeningTests(unittest.TestCase):
    def test_preserves_only_true_flags_without_running_existing_source(self):
        old = "raise RuntimeError('old settings must not execute')\nSESSION_COOKIE_SECURE = True\nCSRF_COOKIE_SECURE: bool = True\nSESSION_COOKIE_HTTPONLY = True\nCUSTOM_OLD_VALUE = 123\n"
        new = "INSTALLED_APPS = ['new_app']\nNEW_DEFAULT = 42\n"
        merged = module.merge_cookie_hardening(old, new)
        loaded = {}
        exec(merged, loaded)
        self.assertEqual(['new_app'], loaded['INSTALLED_APPS'])
        self.assertEqual(42, loaded['NEW_DEFAULT'])
        self.assertNotIn('CUSTOM_OLD_VALUE', loaded)
        for name in ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', 'SESSION_COOKIE_HTTPONLY'):
            self.assertIs(True, loaded[name])

    def test_old_false_never_weakens_release_defaults(self):
        new = 'SESSION_COOKIE_SECURE = True\nCSRF_COOKIE_SECURE = True\n'
        self.assertEqual(new, module.merge_cookie_hardening(
            'SESSION_COOKIE_SECURE = False\nCSRF_COOKIE_SECURE = False\nSESSION_COOKIE_HTTPONLY = False\n', new))

    def test_updates_existing_false_without_duplicate_and_is_repeatable(self):
        old = 'SESSION_COOKIE_SECURE = True\nCSRF_COOKIE_SECURE = True\n'
        new = "TITLE = 'café'; SESSION_COOKIE_SECURE: bool = False  # keep comment\nCSRF_COOKIE_SECURE = (False)\n"
        merged = module.merge_cookie_hardening(old, new)
        self.assertIn("TITLE = 'café'; SESSION_COOKIE_SECURE: bool = True  # keep comment", merged)
        self.assertIn('CSRF_COOKIE_SECURE = (True)', merged)
        self.assertEqual(merged, module.merge_cookie_hardening(merged, merged))

    def test_ambiguous_assignments_fail_with_named_setting(self):
        cases = [
            'SESSION_COOKIE_SECURE = True\nSESSION_COOKIE_SECURE = True',
            'SESSION_COOKIE_SECURE = bool(1)',
            'SESSION_COOKIE_SECURE = 1',
            'SESSION_COOKIE_SECURE = "True"',
            'if enabled:\n SESSION_COOKIE_SECURE = True',
            'def configure():\n SESSION_COOKIE_SECURE = True',
            'SESSION_COOKIE_SECURE, other = True, False',
            'SESSION_COOKIE_SECURE = other = True',
            'SESSION_COOKIE_SECURE |= True',
            'del SESSION_COOKIE_SECURE',
            'SESSION_COOKIE_SECURE: bool',
            'from custom import SESSION_COOKIE_SECURE',
            'def SESSION_COOKIE_SECURE(): pass',
        ]
        for old in cases:
            with self.subTest(old=old), self.assertRaisesRegex(RuntimeError, 'Cannot safely preserve SESSION_COOKIE_SECURE'):
                module.merge_cookie_hardening(old, '')

    def test_ambiguous_release_setting_also_stops_merge(self):
        with self.assertRaisesRegex(RuntimeError, 'new settings.py'):
            module.merge_cookie_hardening('CSRF_COOKIE_SECURE = True', 'CSRF_COOKIE_SECURE = env_flag()')

    def test_actual_release_settings_keep_all_other_assignments(self):
        source = (Path(__file__).resolve().parents[1] / 'CyberCP/settings.py').read_text()
        flags = ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', 'SESSION_COOKIE_HTTPONLY')
        merged = module.merge_cookie_hardening(
            '\n'.join(name + ' = True' for name in flags), source)
        compile(merged, 'staged-settings.py', 'exec')  # Parse only; never load live settings.
        assignments = module._literal_cookie_hardening(merged, 'staged-settings.py')
        self.assertEqual(set(flags), set(assignments))
        self.assertTrue(all(node.value is True for node in assignments.values()))
        def without_cookie_flags(text):
            tree = ast.parse(text)
            tree.body = [node for node in tree.body if not (
                isinstance(node, ast.Assign) and any(
                    isinstance(target, ast.Name) and target.id in flags for target in node.targets))]
            return ast.dump(tree)
        self.assertEqual(without_cookie_flags(source), without_cookie_flags(merged))

    def test_absent_flags_leave_release_unchanged(self):
        new = 'NEW_DEFAULT = 42\n'
        self.assertEqual(new, module.merge_cookie_hardening('OLD_DEFAULT = 1', new))


class UpgradeEntryPointTests(unittest.TestCase):
    write = staticmethod(UpgradeSourceTests.write)
    def setUp(self):
        UpgradeSourceTests.setUp(self)
        self.write(self.current / 'pyvenv.cfg', 'runtime configuration')
        self.write(self.current / 'bin/python', 'runtime')
        self.write(self.current / '.env', 'SECRET_KEY=existing-key')
        self.write(self.current / 'terminal_jwt_secret', 'existing-terminal-key')
        # Relocate absolute installation paths into the disposable test tree.
        # Everything else is the production method, including source staging.
        root = str(self.root)
        class TestPaths(ast.NodeTransformer):
            def visit_Constant(self, node):
                if isinstance(node.value, str) and node.value.startswith('/usr/local'):
                    return ast.copy_location(ast.Constant(root + node.value[len('/usr/local'):]), node)
                return node
        upgrade_class = copy.deepcopy(next(node for node in parsed_source.body
                                           if isinstance(node, ast.ClassDef) and node.name == 'Upgrade'))
        upgrade_class.body = [node for node in upgrade_class.body
                              if isinstance(node, ast.FunctionDef)
                              and node.name in ('downloadAndUpgrade', 'backupCriticalFiles')]
        tree = ast.fix_missing_locations(TestPaths().visit(
            ast.Module(body=[upgrade_class], type_ignores=[])))
        self.globals = dict(module.__dict__, re=re, shlex=shlex,
                            preserve_installed_plugins=lambda current, staged:
                                module.preserve_installed_plugins(current, staged, str(self.root / 'plugins')),
                            pwd=types.SimpleNamespace(getpwnam=lambda _: types.SimpleNamespace(pw_uid=1001)),
                            grp=types.SimpleNamespace(getgrnam=lambda _: types.SimpleNamespace(gr_gid=1002)),
                            settings=types.SimpleNamespace(DATABASES={
                                'default': {'PASSWORD': "quote'and\\backslash", 'HOST': 'remote-db'},
                                'rootdb': {'PASSWORD': 'admin-secret'},
                            }))
        exec(compile(tree, 'upgrade.py', 'exec'), self.globals)
        self.upgrade = self.globals['Upgrade']
        self.upgrade.stdOut = lambda *args: None
        self.upgrade.staticContent = lambda: None
        for method in ('ensurePostfixLoopbackNetworks', 'ensurePostfixDomainLookup',
                       'ensureDovecot24LdaConfig', 'restoreImunify360', 'finalImunifyPermissions'):
            setattr(self.upgrade, method, lambda: None)
        self.clone_ok = True
        self.checkout_ok = True
        self.upgrade.executioner = self.execute
        self.chown = patch('upgrade_source_under_test.os.chown').start()
        self.addCleanup(patch.stopall)
        mkdtemp = tempfile.mkdtemp
        patch('upgrade_source_under_test.tempfile.mkdtemp',
              side_effect=lambda suffix=None, prefix=None, dir=None: mkdtemp(
                  suffix=suffix, prefix=prefix, dir=dir or root)).start()

    def execute(self, command, *args):
        argv = shlex.split(command)
        if argv[1] == 'clone':
            if not self.clone_ok:
                return False
            destination = Path(argv[-1])
            self.write(destination / 'new_source.py', 'new application')
            self.write(destination / 'CyberCP/settings.py',
                       "INSTALLED_APPS = ['new_app']\nDATABASES = {'default': {}, 'rootdb': {}}\n")
            return True
        if 'checkout' in argv:
            return self.checkout_ok
        self.fail('Unexpected command: ' + command)

    def test_staged_upgrade_preserves_cookie_hardening_and_new_apps(self):
        old = "INSTALLED_APPS = ['old_app']\nSESSION_COOKIE_SECURE = True\nCSRF_COOKIE_SECURE = True\nSESSION_COOKIE_HTTPONLY = True\n"
        self.write(self.current / 'CyberCP/settings.py', old)
        self.assertEqual((1, None), self.upgrade.downloadAndUpgrade(None, 'v3.0.8'))
        loaded = {}
        exec((self.current / 'CyberCP/settings.py').read_text(), loaded)
        for name in ('SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', 'SESSION_COOKIE_HTTPONLY'):
            self.assertIs(True, loaded[name])
        self.assertEqual(['new_app'], loaded['INSTALLED_APPS'])
        self.assertEqual(self.globals['settings'].DATABASES, loaded['DATABASES'])
        backups = list(self.root.glob('cyberpanel_backup_*/**/CyberCP/settings.py'))
        self.assertEqual([old], [path.read_text() for path in backups])

    def test_ambiguous_hardening_stops_before_source_activation(self):
        old = 'SESSION_COOKIE_SECURE = get_security_flag()\n'
        self.write(self.current / 'CyberCP/settings.py', old)
        result = self.upgrade.downloadAndUpgrade(None, 'v3.0.8')
        self.assertEqual(0, result[0])
        self.assertIn('Cannot safely preserve SESSION_COOKIE_SECURE', result[1])
        self.assertEqual(old, (self.current / 'CyberCP/settings.py').read_text())
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertFalse((self.current / 'new_source.py').exists())
        self.assertEqual([], list(self.root.glob('.cyberpanel-previous-*')))

    def test_hardened_staged_settings_roll_back_after_collectstatic_failure(self):
        old = 'SESSION_COOKIE_SECURE = True\nCSRF_COOKIE_SECURE = True\nSESSION_COOKIE_HTTPONLY = True\n'
        self.write(self.current / 'CyberCP/settings.py', old)
        def fail_static():
            loaded = {}
            exec((self.current / 'CyberCP/settings.py').read_text(), loaded)
            self.assertIs(True, loaded['CSRF_COOKIE_SECURE'])
            self.assertEqual(['new_app'], loaded['INSTALLED_APPS'])
            raise RuntimeError('collectstatic failed with hardened staging')
        self.upgrade.staticContent = fail_static
        self.assertEqual((0, 'collectstatic failed with hardened staging'),
                         self.upgrade.downloadAndUpgrade(None, 'v3.0.8'))
        self.assertEqual(old, (self.current / 'CyberCP/settings.py').read_text())
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertFalse((self.current / 'new_source.py').exists())
        self.assertEqual('SECRET_KEY=existing-key', (self.current / '.env').read_text())

    def test_success_preserves_runtime_credentials_and_new_applications(self):
        result = self.upgrade.downloadAndUpgrade(None, 'v3.0.6')
        self.assertEqual((1, None), result)
        self.assertEqual('runtime', (self.current / 'bin/python').read_text())
        self.assertEqual('SECRET_KEY=existing-key', (self.current / '.env').read_text())
        loaded = {}
        exec((self.current / 'CyberCP/settings.py').read_text(), loaded)
        self.assertEqual(['new_app'], loaded['INSTALLED_APPS'])
        self.assertEqual(self.globals['settings'].DATABASES, loaded['DATABASES'])
        self.assertFalse((self.current / 'old_source.py').exists())
        self.assertEqual(0o640, stat.S_IMODE((self.current / '.env').stat().st_mode))

    def test_success_keeps_only_the_newest_source_rollback(self):
        old_parent = self.root / '.cyberpanel-previous-old'
        self.write(old_parent / 'CyberCP/old_source.py', 'superseded rollback')

        self.assertEqual((1, None), self.upgrade.downloadAndUpgrade(None, 'v3.0.6'))

        rollbacks = sorted(self.root.glob('.cyberpanel-previous-*'))
        self.assertEqual(1, len(rollbacks))
        self.assertNotEqual(old_parent, rollbacks[0])
        self.assertEqual('old application',
                         (rollbacks[0] / 'CyberCP/old_source.py').read_text())

    def test_download_upgrade_preserves_registered_plugin_before_activation(self):
        self.write(self.root / 'plugins/examplePlugin', '')
        self.write(self.current / 'examplePlugin/__init__.py', '')
        self.write(self.current / 'CyberCP/settings.py',
                   "INSTALLED_APPS = ['old_core', 'examplePlugin']\n")
        self.write(self.current / 'CyberCP/urls.py',
                   "urlpatterns = [\n path('examplePlugin/', include('examplePlugin.urls')),\n]\n")
        execute = self.execute
        def clone_with_urls(command, *args):
            result = execute(command, *args)
            argv = shlex.split(command)
            if argv[1] == 'clone' and result:
                self.write(Path(argv[-1]) / 'CyberCP/urls.py', 'urlpatterns = []\n')
            return result
        self.upgrade.executioner = clone_with_urls
        self.assertEqual((1, None), self.upgrade.downloadAndUpgrade(None, 'v3.0.8'))
        self.assertTrue((self.current / 'examplePlugin/__init__.py').exists())
        self.assertEqual(['new_app', 'examplePlugin'],
                         module._literal_installed_apps(str(self.current / 'CyberCP/settings.py')))
        self.assertIn("path('examplePlugin/', include('examplePlugin.urls'))",
                      (self.current / 'CyberCP/urls.py').read_text())

    def test_clone_failure_keeps_original_runtime_and_source(self):
        self.clone_ok = False
        self.assertEqual(0, self.upgrade.downloadAndUpgrade(None, 'v3.0.6')[0])
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertTrue((self.current / 'bin/python').exists())

    def test_checkout_failure_does_not_install_default_branch(self):
        self.checkout_ok = False
        self.assertEqual(0, self.upgrade.downloadAndUpgrade(None, 'missing-branch')[0])
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertFalse((self.current / 'new_source.py').exists())

    def test_collectstatic_failure_restores_old_runtime_and_source(self):
        def fail_static():
            raise RuntimeError('collectstatic failed')
        self.upgrade.staticContent = fail_static
        result = self.upgrade.downloadAndUpgrade(None, 'v3.0.6')
        self.assertEqual((0, 'collectstatic failed'), result)
        self.assertTrue((self.current / 'old_source.py').exists())
        self.assertTrue((self.current / 'bin/python').exists())

    def test_private_backup_failure_does_not_start_clone(self):
        with patch('upgrade_source_under_test.shutil.copy2', side_effect=OSError('disk full')):
            result = self.upgrade.downloadAndUpgrade(None, 'v3.0.6')
        self.assertEqual(0, result[0])
        self.assertIn('Failed to backup', result[1])
        self.assertTrue((self.current / 'old_source.py').exists())

    def test_legacy_directories_with_trailing_slashes_are_preserved(self):
        self.write(self.current / 'rainloop/data/_data_/contacts.db', 'contacts')
        self.write(self.current / 'baseTemplate/static/baseTemplate/custom/brand.css', 'branding')
        self.assertEqual((1, None), self.upgrade.downloadAndUpgrade(None, 'v3.0.6'))
        self.assertEqual('contacts', (self.current / 'rainloop/data/_data_/contacts.db').read_text())
        self.assertEqual('branding', (self.current / 'baseTemplate/static/baseTemplate/custom/brand.css').read_text())


    def test_file_valued_custom_configuration_is_preserved(self):
        config = self.current / 'public/phpmyadmin/config.inc.php'
        self.write(config, '<?php $cfg["blowfish_secret"] = "existing-secret";')
        original = config.read_text()
        self.assertEqual((1, None), self.upgrade.downloadAndUpgrade(None, 'v3.0.6'))
        self.assertTrue(config.is_file())
        self.assertEqual(original, config.read_text())

    def test_backup_paths_are_structured_and_do_not_flatten_directory_files(self):
        self.write(self.current / '.git/config', 'git configuration')
        self.write(self.current / 'baseTemplate/static/baseTemplate/custom/config', 'custom configuration')
        self.write(self.current / 'public/phpmyadmin/config.inc.php', 'phpmyadmin configuration')
        backup_dir, files = self.upgrade.backupCriticalFiles()
        for original, backup in files.items():
            self.assertEqual(Path(backup_dir) / original.lstrip(os.sep), Path(backup))
        self.assertEqual('git configuration', Path(files[str(self.current / '.git/config')]).read_text())
        custom = self.current / 'baseTemplate/static/baseTemplate/custom'
        self.assertEqual('custom configuration', (Path(files[str(custom)]) / 'config').read_text())
        self.assertEqual('phpmyadmin configuration', Path(files[str(self.current / 'public/phpmyadmin/config.inc.php')]).read_text())


if __name__ == '__main__':
    unittest.main()
