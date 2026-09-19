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
                'protect_private_files'}
module = types.ModuleType('upgrade_source_under_test')
module.__dict__.update(os=os, shutil=shutil, tempfile=tempfile,
                       contextmanager=contextmanager)
parsed_source = ast.parse(source)
helper_tree = ast.Module(body=[node for node in parsed_source.body
                              if isinstance(node, ast.FunctionDef)
                              and node.name in helper_names], type_ignores=[])
exec(compile(helper_tree, 'upgrade.py', 'exec'), module.__dict__)
sys.modules[module.__name__] = module
activate_source = module.activate_source
preserve_installation_state = module.preserve_installation_state
protect_private_files = module.protect_private_files



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
