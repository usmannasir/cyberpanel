"""Execute the real fresh installer main with external side effects stubbed."""
import argparse
import ast
import io
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]


class PhpMyAdminFailureTests(unittest.TestCase):
    def setUp(self):
        path = ROOT / 'install/install.py'
        tree = ast.parse(path.read_text())
        main = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'main')
        self.main_ast = main
        self.checks = Mock()
        factory = Mock(return_value=self.checks)
        factory.debug = False
        self.logs = Mock()
        self.scope = dict(argparse=argparse, os=Mock(), open=Mock(return_value=io.StringIO()),
                          logging=SimpleNamespace(InstallLog=self.logs), preFlightsChecks=factory,
                          get_distro=lambda: 'ubuntu', ubuntu='ubuntu', configure_jwt_secret=Mock())
        exec(compile(ast.fix_missing_locations(ast.Module(body=[main], type_ignores=[])), str(path), 'exec'), self.scope)
        self.modules = {}
        server = ModuleType('installCyberPanel')
        server.Main = Mock()
        server.InstallCyberPanel = SimpleNamespace(mysqlPassword='fixture-only')
        self.modules['installCyberPanel'] = server
        for name in ('roundcubeSudo', 'gdriveSudo', 'cloudflareSudo'):
            module = ModuleType('plogical.' + name)
            module.provision = Mock()
            self.modules['plogical.' + name] = module
        terminal = ModuleType('plogical.terminalService')
        terminal.configure_terminal_service = Mock()
        self.modules['plogical.terminalService'] = terminal
        self.module_patch = patch.dict(sys.modules, self.modules)
        self.module_patch.start()
        self.addCleanup(self.module_patch.stop)
        self.argv_patch = patch.object(sys, 'argv', ['install.py', '192.0.2.10', '--remotemysql', 'OFF', '--postfix', 'OFF'])
        self.argv_patch.start()
        self.addCleanup(self.argv_patch.stop)

    def assert_not_completed(self):
        self.checks.setupCLI.assert_not_called()
        self.checks.startDeferredServices.assert_not_called()
        messages = [call.args[0] for call in self.logs.writeToFile.call_args_list]
        self.assertFalse(any('successfully completed' in value for value in messages))

    def test_main_rejects_failure_and_missing_success_result(self):
        for result in (0, False, None):
            with self.subTest(result=result):
                self.checks.reset_mock()
                self.logs.reset_mock()
                self.scope['open'].return_value = io.StringIO()
                self.checks.download_install_phpmyadmin.return_value = result
                with self.assertRaisesRegex(RuntimeError, 'phpMyAdmin'):
                    self.scope['main']()
                self.assert_not_completed()

    def test_main_propagates_setup_exception_without_success(self):
        self.checks.download_install_phpmyadmin.side_effect = RuntimeError('fixture setup failure')
        with self.assertRaisesRegex(RuntimeError, 'fixture setup failure'):
            self.scope['main']()
        self.assert_not_completed()

    def test_main_continues_after_explicit_setup_success(self):
        self.checks.download_install_phpmyadmin.return_value = 1
        self.scope['main']()
        self.checks.setupCLI.assert_called_once_with()
        self.checks.startDeferredServices.assert_called_once_with()
        self.logs.writeToFile.assert_any_call('CyberPanel installation successfully completed!,80')

    def setup_method(self, peer_failure=None, failed_command=None, move_status=0):
        tree = ast.parse((ROOT / 'install/install.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'preFlightsChecks')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'download_install_phpmyadmin')
        commands = Mock(side_effect=lambda command, *args: not (failed_command and command.startswith(failed_command)))
        scope = dict(os=Mock(), subprocess=Mock(), logging=SimpleNamespace(InstallLog=Mock()),
                     preFlightsChecks=SimpleNamespace(call=commands),
                     install_utils=SimpleNamespace(generate_random_string=lambda count: 'fixture-only'))
        scope['subprocess'].call.return_value = move_status
        scope['open'] = Mock(side_effect=lambda *args: io.StringIO("$cfg['Servers'][$i]['auth_type'] = 'cookie';\n"))
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), 'setup-method', 'exec'), scope)
        provision = Mock(side_effect=peer_failure)
        with patch('install.proxy_identity.ensure_pma_peer_key', provision):
            result = scope['download_install_phpmyadmin'](SimpleNamespace(distro='ubuntu', remotemysql='OFF'))
        return result, commands, provision

    def test_real_key_preparation_failure_reaches_main_as_failure(self):
        result, commands, provision = self.setup_method(RuntimeError('fixture paired-key preparation failure'))
        self.assertEqual(0, result)
        provision.assert_called_once_with()
        self.assertFalse(any(call.args[0].startswith('cp ') for call in commands.call_args_list))
        self.checks.download_install_phpmyadmin.return_value = result
        with self.assertRaisesRegex(RuntimeError, 'phpMyAdmin'):
            self.scope['main']()
        self.assert_not_completed()

    def test_required_command_failure_prevents_success(self):
        for prefix in ('wget ', 'unzip ', 'rm ', 'chown ',
                       'cp /usr/local/CyberCP/plogical/phpmyadminsignin.php ',
                       'cp /usr/local/CyberCP/plogical/phpmyadminsession.php '):
            with self.subTest(command=prefix):
                result, commands, provision = self.setup_method(failed_command=prefix)
                self.assertEqual(0, result)
                self.assertTrue(commands.call_args.args[0].startswith(prefix))
                self.checks.reset_mock()
                self.logs.reset_mock()
                self.scope['open'].return_value = io.StringIO()
                self.checks.download_install_phpmyadmin.return_value = result
                with self.assertRaisesRegex(RuntimeError, 'phpMyAdmin'):
                    self.scope['main']()
                self.assert_not_completed()

    def test_extraction_move_failure_prevents_key_or_bridge_setup(self):
        result, commands, provision = self.setup_method(move_status=1)
        self.assertEqual(0, result)
        provision.assert_not_called()
        self.assertFalse(any(call.args[0].startswith('cp ') for call in commands.call_args_list))

    def test_real_setup_returns_explicit_success_after_both_bridges(self):
        result, commands, provision = self.setup_method()
        self.assertEqual(1, result)
        provision.assert_called_once_with()
        copies = [call.args[0] for call in commands.call_args_list if call.args[0].startswith('cp ')]
        self.assertEqual(2, len(copies))
        self.assertIn('phpmyadminsignin.php', copies[0])
        self.assertIn('phpmyadminsession.php', copies[1])

if __name__ == '__main__':
    unittest.main()
