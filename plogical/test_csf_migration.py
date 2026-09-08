"""CSF upgrade gates use temporary fixtures and never run firewall commands."""
import argparse
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def source_tree(relative):
    return ast.parse((ROOT / relative).read_text(), filename=relative)


def definitions(relative, names, namespace):
    # Execute unchanged production definitions without application startup,
    # database recovery, or imports that assume an installed panel.
    selected = []
    for node in source_tree(relative).body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in names:
            selected.append(node)
        elif isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id in names
                for target in node.targets):
            selected.append(node)
    exec(compile(ast.Module(body=selected, type_ignores=[]), relative, 'exec'), namespace)
    return namespace


class ReachedUpgradeWork(BaseException):
    pass


class CSFMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.csf = self.root / 'csf'
        self.process = Mock()
        self.process.check_output.side_effect = ReachedUpgradeWork
        self.os = types.SimpleNamespace(
            path=types.SimpleNamespace(
                lexists=lambda p: os.path.lexists(self.csf) if p == '/etc/csf' else False,
                exists=lambda p: self.csf.exists() if p == '/etc/csf' else False,
            ),
            chdir=Mock(),
        )
        namespace = {'os': self.os, 'sys': sys, 'subprocess': self.process, 'shlex': shlex}
        if (ROOT / 'cyberpanel_firewall_migration.py').exists():
            definitions('cyberpanel_firewall_migration.py',
                {'CSF_UPGRADE_MESSAGE', 'requireCSFMigration'}, namespace)
        self.namespace = definitions('plogical/upgrade.py',
            {'CSF_UPGRADE_MESSAGE', 'requireCSFMigration', 'Upgrade'},
            namespace)
        self.upgrade = self.namespace['Upgrade']
        self.upgrade.stdOut = Mock(side_effect=ReachedUpgradeWork)
        self.upgrade.backupCriticalFiles = Mock(side_effect=ReachedUpgradeWork)
        self.upgrade.executioner = Mock(side_effect=ReachedUpgradeWork)

    def create_csf(self, kind='directory'):
        if kind == 'directory':
            self.csf.mkdir()
            (self.csf / 'csf.conf').write_text('TCP_IN = "22,443,2096"\nTCP_OUT = "53,443"\n')
        elif kind == 'file':
            self.csf.write_text('unexpected filesystem object')
        elif kind == 'dangling':
            self.csf.symlink_to(self.root / 'missing-target')
        elif kind == 'symlink':
            target = self.root / 'actual-csf'
            target.mkdir()
            self.csf.symlink_to(target, target_is_directory=True)

    def assert_no_upgrade_work(self):
        self.process.assert_not_called()
        self.assertEqual([], self.process.mock_calls)
        self.upgrade.stdOut.assert_not_called()
        self.upgrade.backupCriticalFiles.assert_not_called()
        self.upgrade.executioner.assert_not_called()
        self.os.chdir.assert_not_called()

    def test_upgrade_refuses_existing_csf_before_commands_or_backup(self):
        self.create_csf()
        before = (self.csf / 'csf.conf').read_bytes()
        with contextlib.redirect_stderr(io.StringIO()) as error:
            with self.assertRaises(SystemExit) as stopped:
                self.upgrade.upgrade('stable')
        self.assertEqual(1, stopped.exception.code)
        self.assertIn('manual firewall migration', error.getvalue())
        self.assert_no_upgrade_work()
        self.assertEqual(before, (self.csf / 'csf.conf').read_bytes())

    def test_upgrade_refuses_soft_upgrade_before_state_changes(self):
        self.create_csf()
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            self.upgrade.upgrade('SoftUpgrade,stable')
        self.assertEqual(0, self.upgrade.SoftUpgrade)
        self.assert_no_upgrade_work()

    def test_upgrade_refuses_unexpected_file_and_symlink_markers(self):
        for kind in ('file', 'symlink', 'dangling'):
            with self.subTest(kind=kind):
                self.create_csf(kind)
                with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                    self.upgrade.upgrade('stable')
                self.assert_no_upgrade_work()
                self.csf.unlink()

    def test_no_csf_upgrade_reaches_existing_package_detection(self):
        with self.assertRaises(ReachedUpgradeWork):
            self.upgrade.upgrade('stable')
        self.process.check_output.assert_called_once_with(['apt', 'list'])

    def test_download_api_refuses_before_backup(self):
        self.create_csf()
        status, message = self.upgrade.downloadAndUpgrade(None, 'stable')
        self.assertEqual(0, status)
        self.assertIn('manual firewall migration', message)
        self.assert_no_upgrade_work()

    def test_download_api_refuses_dangling_csf_marker(self):
        self.create_csf('dangling')
        status, message = self.upgrade.downloadAndUpgrade(None, 'stable')
        self.assertEqual(0, status)
        self.assertIn('CSF', message)
        self.assert_no_upgrade_work()

    def test_no_csf_download_api_reaches_existing_backup_stage(self):
        self.upgrade.stdOut = Mock()
        self.upgrade.downloadAndUpgrade(None, 'stable')
        self.assertIn('Backing up', self.upgrade.stdOut.call_args_list[0].args[0])
        self.upgrade.backupCriticalFiles.assert_called_once_with()

    def test_command_line_refuses_before_database_imports(self):
        self.create_csf()
        original_import = __import__
        imports = []

        def guarded_import(name, *args, **kwargs):
            imports.append(name)
            if name in ('MySQLdb', 'CyberCP', 'cyberpanel_version'):
                raise AssertionError('database/application import reached before CSF refusal')
            return original_import(name, *args, **kwargs)

        original_path = sys.path[:]
        try:
            with patch('builtins.__import__', side_effect=guarded_import), \
                    patch('os.path.lexists', return_value=True), \
                    patch.object(sys, 'argv', ['upgrade.py', 'stable']), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as stopped:
                    exec(compile((ROOT / 'plogical/upgrade.py').read_text(),
                                 'plogical/upgrade.py', 'exec'), {'__name__': '__main__'})
            self.assertEqual(1, stopped.exception.code)
            self.assertNotIn('MySQLdb', imports)
        finally:
            sys.path[:] = original_path


class CSFRemovalTests(unittest.TestCase):
    def setUp(self):
        self.process = Mock()
        self.process.call.return_value = 0
        self.os = types.SimpleNamespace(chdir=Mock())
        self.namespace = definitions('plogical/csf.py', {'CSF', 'main'}, {
            'multi': threading, 'os': self.os, 'sys': sys,
            'subprocess': self.process, 'shlex': shlex, 'argparse': argparse,
            'logging': Mock(), 'ProcessUtilities': Mock(),
        })
        self.csf = self.namespace['CSF']

    def test_direct_removal_refuses_without_changing_firewall(self):
        with contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(0, self.csf('removeCSF', {}).removeCSF())
        self.assertIn('No firewall changes were made', error.getvalue())
        self.assertEqual([], self.process.mock_calls)
        self.os.chdir.assert_not_called()

    def test_controller_propagates_refusal(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(0, self.csf('removeCSF', {}).run())
        self.assertEqual([], self.process.mock_calls)

    def test_cli_entry_point_exits_nonzero(self):
        main_guard = source_tree('plogical/csf.py').body[-1]
        self.namespace['__name__'] = '__main__'
        with patch.object(sys, 'argv', ['csf.py', 'removeCSF']), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as stopped:
                exec(compile(ast.Module(body=[main_guard], type_ignores=[]),
                             'plogical/csf.py', 'exec'), self.namespace)
        self.assertEqual(1, stopped.exception.code)
        self.assertEqual([], self.process.mock_calls)

    def manager(self, admin):
        node = next(n for n in source_tree('firewall/firewallManager.py').body
                    if isinstance(n, ast.ClassDef) and n.name == 'FirewallManager')
        method = next(n for n in node.body
                      if isinstance(n, ast.FunctionDef) and n.name == 'removeCSF')
        acl = Mock()
        acl.loadedACL.return_value = {'admin': admin}
        acl.loadErrorJson.return_value = 'denied'
        namespace = {'ACLManager': acl, 'CSF': self.csf, 'json': json,
                     'HttpResponse': lambda data: data, 'ProcessUtilities': self.process,
                     'time': Mock(), 'virtualHostUtilities': types.SimpleNamespace(cyberPanel='/unused')}
        exec(compile(ast.Module(body=[method], type_ignores=[]),
                     'firewall/firewallManager.py', 'exec'), namespace)
        instance = types.SimpleNamespace(request=types.SimpleNamespace(session={'userID': 12}))
        return namespace['removeCSF'](instance), acl

    def test_admin_removal_reports_failure_without_starting_worker(self):
        response, acl = self.manager(1)
        data = json.loads(response)
        self.assertEqual(0, data['installStatus'])
        self.assertIn('manual migration', data['error_message'])
        acl.loadedACL.assert_called_once_with(12)
        self.assertEqual([], self.process.mock_calls)

    def test_nonadmin_removal_keeps_acl_denial(self):
        response, acl = self.manager(0)
        self.assertEqual('denied', response)
        acl.loadErrorJson.assert_called_once_with('installStatus', 0)
        self.assertEqual([], self.process.mock_calls)


class CSFCloudUpgradeTests(unittest.TestCase):
    def test_cloud_refusal_does_not_backup_or_restore_installation(self):
        os_proxy = types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda p: True))
        namespace = definitions('plogical/CyberPanelUpgrade.py',
                                {'UpgradeCyberPanel'}, {'os': os_proxy})
        cloud = namespace['UpgradeCyberPanel'].__new__(namespace['UpgradeCyberPanel'])
        cloud.branch = 'stable'
        cloud.PostStatus = Mock()
        cloud.RestoreOldCP = Mock()
        original_import = __import__

        def guarded_import(name, *args, **kwargs):
            if name == 'plogical.upgrade':
                raise AssertionError('upgrade import reached before cloud CSF refusal')
            return original_import(name, *args, **kwargs)

        with patch('builtins.__import__', side_effect=guarded_import):
            self.assertEqual(0, cloud.UpgardeNow())
        cloud.RestoreOldCP.assert_not_called()
        cloud.PostStatus.assert_called_once()
        self.assertIn('manual firewall migration', cloud.PostStatus.call_args.args[0])

    def test_cloud_cli_propagates_refusal_as_nonzero(self):
        cloud = Mock()
        cloud.return_value.UpgardeNow.return_value = 0
        namespace = definitions('plogical/CyberPanelUpgrade.py', {'main'},
                                {'argparse': argparse, 'UpgradeCyberPanel': cloud, 'sys': sys})
        namespace['__name__'] = '__main__'
        guard = source_tree('plogical/CyberPanelUpgrade.py').body[-1]
        with patch.object(sys, 'argv', ['CyberPanelUpgrade.py', '--branch', 'stable',
                                      '--mail', '1', '--dns', '1', '--ftp', '1']):
            with self.assertRaises(SystemExit) as stopped:
                exec(compile(ast.Module(body=[guard], type_ignores=[]),
                             'plogical/CyberPanelUpgrade.py', 'exec'), namespace)
        self.assertEqual(1, stopped.exception.code)


class CSFUpgradeRequestTests(unittest.TestCase):
    def panel_request(self, present, admin=1):
        acl = Mock()
        acl.loadedACL.return_value = {'admin': admin}
        acl.loadErrorJson.return_value = 'access denied'
        worker = Mock()
        imports = []
        original_import = __import__

        def test_import(name, *args, **kwargs):
            imports.append(name)
            if name == 'plogical.applicationInstaller':
                return types.SimpleNamespace(ApplicationInstaller=worker)
            return original_import(name, *args, **kwargs)

        namespace = definitions('baseTemplate/views.py', {'upgrade'}, {
            'ACLManager': acl, 'json': json, 'HttpResponse': lambda data: data,
            'os': types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda p: present)),
        })
        request = types.SimpleNamespace(session={'userID': 10},
                                       body=json.dumps({'branchSelect': 'stable'}))
        with patch('builtins.__import__', side_effect=test_import):
            response = namespace['upgrade'](request)
        return response, acl, worker, imports

    def test_panel_admin_request_refuses_before_background_worker_import(self):
        response, acl, worker, imports = self.panel_request(True)
        data = json.loads(response)
        self.assertEqual(0, data['upgrade'])
        self.assertIn('manual firewall migration', data['error_message'])
        worker.assert_not_called()
        self.assertNotIn('plogical.applicationInstaller', imports)

    def test_panel_without_csf_keeps_existing_worker_launch(self):
        response, acl, worker, imports = self.panel_request(False)
        self.assertEqual({'upgrade': 1}, json.loads(response))
        worker.assert_called_once_with('UpgradeCP', {'branchSelect': 'stable'})
        worker.return_value.start.assert_called_once_with()

    def test_panel_nonadmin_keeps_acl_denial(self):
        response, acl, worker, imports = self.panel_request(True, 0)
        self.assertEqual('access denied', response)
        acl.loadErrorJson.assert_called_once_with('fetchStatus', 0)
        worker.assert_not_called()
        self.assertNotIn('cyberpanel_firewall_migration', imports)

    def cloud_request(self, present):
        node = next(n for n in source_tree('cloudAPI/cloudManager.py').body
                    if isinstance(n, ast.ClassDef) and n.name == 'CloudManager')
        method = next(n for n in node.body
                      if isinstance(n, ast.FunctionDef) and n.name == 'SubmitCyberPanelUpgrade')
        ajax = next(n for n in node.body
                    if isinstance(n, ast.FunctionDef) and n.name == 'ajaxPre')
        process = Mock()
        namespace = {'ProcessUtilities': process, 'json': json,
                     'HttpResponse': lambda data: data,
                     'os': types.SimpleNamespace(path=types.SimpleNamespace(lexists=lambda p: present))}
        exec(compile(ast.Module(body=[method, ajax], type_ignores=[]),
                     'cloudAPI/cloudManager.py', 'exec'), namespace)
        instance = types.SimpleNamespace(data={'CyberPanelBranch': 'stable',
                                              'mail': 1, 'dns': 0, 'ftp': 1})
        instance.ajaxPre = types.MethodType(namespace['ajaxPre'], instance)
        return namespace['SubmitCyberPanelUpgrade'](instance), process

    def test_cloud_request_refuses_before_launch(self):
        response, process = self.cloud_request(True)
        data = json.loads(response)
        self.assertEqual(0, data['status'])
        self.assertIn('manual firewall migration', data['error_message'])
        self.assertEqual([], process.mock_calls)

    def test_cloud_request_without_csf_keeps_existing_launch(self):
        response, process = self.cloud_request(False)
        self.assertEqual({'status': 1}, json.loads(response))
        process.executioner.assert_called_once_with(
            '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/CyberPanelUpgrade.py '
            '--branch stable --mail 1 --dns 0 --ftp 1')


class CSFShellUpgradeTests(unittest.TestCase):
    def run_prefix(self, kind):
        script = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        # All function definitions and the real early entry-point checks run.
        # Stop before normal initialization, replacing only its initial local
        # cleanup section; no package, service, credential or network stage runs.
        prefix = script[:script.index('\nSet_Default_Variables\n')]
        start = script.index('Set_Default_Variables() {')
        initial = script[start:script.index('export LC_CTYPE=', start)] + '\n}\n'
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            paths = ['/etc/cyberpanel', '/etc/csf', '/etc/cxs', '/var/log',
                     '/usr/local/CyberCP', '/home/cyberpanel/plugins']
            for path in paths:
                (root / path.lstrip('/')).parent.mkdir(parents=True, exist_ok=True)
            (root / 'etc/cyberpanel').mkdir()
            (root / 'var/log').mkdir()
            marker = root / 'etc/csf'
            if kind == 'directory':
                marker.mkdir()
                (marker / 'csf.conf').write_text('existing policy')
            elif kind == 'dangling':
                marker.symlink_to(root / 'missing')
            fixtures = [
                '/usr/local/CyberCP/configservercsf/plugin.py',
                '/usr/local/CyberCP/public/static/configservercsf/plugin.js',
                '/home/cyberpanel/plugins/configservercsf',
                '/usr/local/CyberCP/CyberCP/settings.py',
                '/usr/local/CyberCP/CyberCP/urls.py',
                '/usr/local/CyberCP/baseTemplate/templates/baseTemplate/index.html',
            ]
            before = {}
            for path in fixtures:
                file = root / path.lstrip('/')
                file.parent.mkdir(parents=True, exist_ok=True)
                file.write_text('configservercsf: retained integration\n')
                before[path] = file.read_bytes()
            harness = prefix + '\n' + initial + '\nSet_Default_Variables\nprintf "READY\\n"\n'
            for path in sorted(paths, key=len, reverse=True):
                harness = harness.replace(path, str(root / path.lstrip('/')))
            completed = subprocess.run(['bash', '--noprofile', '--norc', '-c', harness],
                cwd=temporary, env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C'},
                capture_output=True, text=True, timeout=10)
            retained = all((root / p.lstrip('/')).is_file() and
                           (root / p.lstrip('/')).read_bytes() == data
                           for p, data in before.items())
            return completed, retained, list((root / 'var/log').iterdir())

    def test_shell_csf_guard_precedes_log_and_integration_changes(self):
        result, retained, logs = self.run_prefix('directory')
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertIn('manual firewall migration', result.stderr)
        self.assertTrue(retained)
        self.assertEqual([], logs)

    def test_shell_dangling_marker_also_blocks_upgrade(self):
        result, retained, logs = self.run_prefix('dangling')
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertTrue(retained)
        self.assertEqual([], logs)

    def test_shell_without_csf_retains_integration_and_continues(self):
        result, retained, logs = self.run_prefix('absent')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('READY', result.stdout)
        self.assertTrue(retained)

    def test_standalone_upgrader_stages_guard_dependency(self):
        script = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        start = script.index('Download_Upgrade_Source "plogical/upgrade.py"')
        end = script.index('\nif [[ "$Server_Country"', start)
        staging = script[start:end]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            harness = ('Download_Upgrade_Source() { cp "$SOURCE_ROOT/$1" "$2"; }\n' + staging)
            result = subprocess.run(['bash', '-c', harness], cwd=temporary,
                env={'PATH': '/usr/bin:/bin', 'SOURCE_ROOT': str(ROOT)},
                capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual((ROOT / 'cyberpanel_firewall_migration.py').read_bytes(),
                             (root / 'cyberpanel_firewall_migration.py').read_bytes())
            probe = (
                'import os,runpy\n'
                'os.path.lexists=lambda path: path == "/etc/csf"\n'
                'runpy.run_path("upgrade.py",run_name="__main__")\n'
            )
            result = subprocess.run([sys.executable, '-I', '-B', '-c',
                'import sys;sys.path.insert(0,".");' + probe], cwd=temporary,
                env={'PATH': '/usr/bin:/bin'}, capture_output=True, text=True, timeout=10)
            self.assertEqual(1, result.returncode, result.stderr)
            self.assertIn('manual firewall migration', result.stderr)
            self.assertNotIn('ModuleNotFoundError', result.stderr)

    def test_older_upgrader_without_guard_import_does_not_fetch_new_helper(self):
        script = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        start = script.index('Download_Upgrade_Source "plogical/upgrade.py"')
        end = script.index('\nif [[ "$Server_Country"', start)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / 'older-branch'
            (source / 'plogical').mkdir(parents=True)
            (source / 'plogical/upgrade.py').write_text('import os\n')
            (source / 'cyberpanel_version.py').write_text('VERSION = "3.0"\n')
            harness = ('Download_Upgrade_Source() { cp "$SOURCE_ROOT/$1" "$2"; }\n'
                       + script[start:end])
            result = subprocess.run(['bash', '-c', harness], cwd=temporary,
                env={'PATH': '/usr/bin:/bin', 'SOURCE_ROOT': str(source)},
                capture_output=True, text=True, timeout=10)
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('import os\n', (root / 'upgrade.py').read_text())
            self.assertFalse((root / 'cyberpanel_firewall_migration.py').exists())


if __name__ == '__main__':
    unittest.main()
