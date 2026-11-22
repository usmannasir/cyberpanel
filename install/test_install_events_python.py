"""Status events and exit statuses of the Python installer.

install.py and installCyberPanel.py are run through their real entry points
with what they install replaced; install_events is used as it is.
"""
import argparse
import ast
import io
import os
from pathlib import Path
import re
import stat
import sys
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from install import install_events, install_utils

ROOT = Path(__file__).resolve().parents[1]

STEPS = ('preflight repositories system_update python_env download_panel web_server '
         'php database ftp dns email panel finishing hostname_ssl ready').split()
EVENT_LINE = re.compile(
    r'[0-9]{10} [0-9a-f]{32} ('
    r'install started [0-9a-z.]+|install complete|install failed [a-z0-9_]+|panel ready|'
    r'(%s) (running|done|skipped|warning [a-z0-9_]+|failed [a-z0-9_]+))' % '|'.join(STEPS))


class PythonEventWriterTests(unittest.TestCase):
    RUN = '0123456789abcdef0123456789abcdef'

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.file = Path(directory.name) / 'install_events.log'
        for name, replacement in (('EVENTS_FILE', str(self.file)), ('_running', 'web_server')):
            patcher = patch.object(install_events, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {install_events.RUN_ID_VARIABLE: self.RUN})
        environment.start()
        self.addCleanup(environment.stop)

    def events(self):
        return [' '.join(line.split()[2:]) for line in self.file.read_text().splitlines()]

    def test_steps_follow_the_one_the_shell_installer_started(self):
        for name in install_events.STEPS[1:]:
            install_events.step(name)
        install_events.finish()
        expected = ['web_server done']
        for name in install_events.STEPS[1:]:
            expected += [name + ' running', name + ' done']
        self.assertEqual(expected, self.events())
        for line in self.file.read_text().splitlines():
            self.assertRegex(line, '^%s$' % EVENT_LINE.pattern)
            self.assertEqual(self.RUN, line.split()[1])

    def test_steps_are_the_ones_cyberpanel_sh_expects_between_its_own(self):
        self.assertEqual(STEPS[STEPS.index('web_server'):STEPS.index('finishing')],
                         list(install_events.STEPS))

    def test_step_left_out_is_skipped_and_nothing_runs_until_the_next(self):
        install_events.step('php')
        install_events.step('database')
        install_events.step('ftp', False)
        install_events.step('dns', False)
        install_events.step('email', False)
        install_events.step('panel')
        install_events.step('panel')
        install_events.finish()
        install_events.finish()
        self.assertEqual(['web_server done', 'php running', 'php done', 'database running',
                          'database done', 'ftp skipped', 'dns skipped', 'email skipped',
                          'panel running', 'panel done'], self.events())

    def test_unknown_step_is_not_written(self):
        install_events.step('teapot')
        install_events.step('php\n1 x install complete')
        self.assertFalse(self.file.exists())

    def test_nothing_is_written_without_a_run_started_by_the_shell_installer(self):
        for value in (None, '', 'short', self.RUN.upper(), self.RUN + '\n', self.RUN + ' x'):
            with self.subTest(value=value):
                with patch.dict(os.environ):
                    os.environ.pop(install_events.RUN_ID_VARIABLE, None)
                    if value is not None:
                        os.environ[install_events.RUN_ID_VARIABLE] = value
                    with patch.object(install_events, '_running', 'web_server'):
                        install_events.step('php')
                        install_events.finish()
                self.assertFalse(self.file.exists())

    def test_file_is_created_for_root_only_and_only_added_to(self):
        self.file.write_text('1700000000 %s install started 3.0.11\n' % ('f' * 32))
        self.file.chmod(0o600)
        install_events.step('php')
        self.assertEqual('install started 3.0.11', self.events()[0])
        self.file.unlink()
        previous = os.umask(0)
        self.addCleanup(os.umask, previous)
        install_events.step('database')
        self.assertEqual(0o600, stat.S_IMODE(self.file.stat().st_mode))

    def test_file_that_cannot_be_written_does_not_stop_the_installer(self):
        with patch.object(install_events, 'EVENTS_FILE', str(self.file / 'not-a-directory' / 'x')):
            install_events.step('php')
            install_events.finish()

    def test_modules_run_on_python_36(self):
        for name in ('install/install_events.py', 'install/installLog.py', 'install/install_utils.py',
                     'install/install.py', 'install/installCyberPanel.py'):
            with self.subTest(name=name):
                ast.parse((ROOT / name).read_text(), feature_version=(3, 6))


class InstallerEntryPointTests(unittest.TestCase):
    """The real main() of install.py and Main() of installCyberPanel.py."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.file = Path(directory.name) / 'install_events.log'
        for name, replacement in (('EVENTS_FILE', str(self.file)), ('_running', 'web_server')):
            patcher = patch.object(install_events, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {install_events.RUN_ID_VARIABLE: 'a' * 32})
        environment.start()
        self.addCleanup(environment.stop)
        self.work = []
        log = SimpleNamespace(
            writeToFile=lambda message: self.work.append(message),
            step=install_events.step, stepsFinished=install_events.finish, ServerIP='')
        self.logging = SimpleNamespace(InstallLog=log)

    def function(self, path, name):
        tree = ast.parse((ROOT / path).read_text())
        node = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == name)
        return ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[]))

    def events(self):
        return [' '.join(line.split()[2:]) for line in self.file.read_text().splitlines()]

    def server_installer(self):
        """installCyberPanel.Main with every installation method recorded."""
        installer = Mock()
        installer.installSieve.side_effect = lambda: self.work.append('sieve')
        installer.installPureFTPD.side_effect = lambda: self.work.append('ftp')
        installer.installPowerDNS.side_effect = lambda: self.work.append('dns')
        cls = Mock(return_value=installer)
        database = Mock()
        database.createDatabase.return_value = 1
        scope = dict(
            os=Mock(), time=Mock(), open=Mock(return_value=io.StringIO('fixture')),
            logging=self.logging, install=Mock(), install_utils=Mock(), mysqlUtilities=database,
            InstallCyberPanel=cls, centos=1, ubuntu=0, cent8=2, openeuler=3,
            build_database_config=Mock(return_value={'db_name': 'cyberpanel', 'db_user': 'cyberpanel'}),
            require_fresh_application_installation=Mock())
        exec(compile(self.function('install/installCyberPanel.py', 'Main'), 'Main', 'exec'), scope)
        return scope['Main']

    def run_main(self, *flags):
        checks = Mock()
        checks.install_postfix_dovecot.side_effect = lambda: self.work.append('email')
        factory = Mock(return_value=checks)
        factory.debug = False
        scope = dict(argparse=argparse, os=Mock(), subprocess=Mock(), open=Mock(return_value=io.StringIO()),
                     logging=self.logging, preFlightsChecks=factory, get_distro=lambda: 0, ubuntu=0,
                     configure_jwt_secret=Mock())
        exec(compile(self.function('install/install.py', 'main'), 'main', 'exec'), scope)
        modules = {}
        server = ModuleType('installCyberPanel')
        server.Main = self.server_installer()
        server.InstallCyberPanel = SimpleNamespace(mysqlPassword='fixture-only', setupWebmail=Mock())
        modules['installCyberPanel'] = server
        for name in ('roundcubeSudo', 'gdriveSudo', 'cloudflareSudo'):
            module = ModuleType('plogical.' + name)
            module.provision = Mock()
            modules['plogical.' + name] = module
        terminal = ModuleType('plogical.terminalService')
        terminal.configure_terminal_service = Mock()
        modules['plogical.terminalService'] = terminal
        with patch.dict(sys.modules, modules), \
                patch.object(sys, 'argv', ['install.py', '192.0.2.10', '--remotemysql', 'OFF'] + list(flags)):
            scope['main']()
        return checks

    def test_default_installation_goes_through_every_step(self):
        self.run_main()
        expected = ['web_server done']
        for name in install_events.STEPS[1:]:
            expected += [name + ' running', name + ' done']
        self.assertEqual(expected, self.events())
        self.assertEqual('CyberPanel installation successfully completed!,80', self.work[-1])

    def test_every_choice_of_components_skips_exactly_the_ones_left_out(self):
        for email in ('ON', 'OFF'):
            for dns in ('ON', 'OFF'):
                for ftp in ('ON', 'OFF'):
                    with self.subTest(email=email, dns=dns, ftp=ftp):
                        if self.file.exists():
                            self.file.unlink()
                        del self.work[:]
                        with patch.object(install_events, '_running', 'web_server'):
                            self.run_main('--postfix', email, '--powerdns', dns, '--ftp', ftp)
                        events = self.events()
                        chosen = {'ftp': ftp, 'dns': dns, 'email': email}
                        for name, choice in chosen.items():
                            self.assertEqual(choice == 'ON', name in self.work)
                            self.assertEqual(choice == 'ON', name + ' running' in events)
                            self.assertEqual(choice == 'ON', name + ' done' in events)
                            self.assertEqual(choice == 'OFF', name + ' skipped' in events)
                        self.assertEqual(
                            [name for name in install_events.STEPS if chosen.get(name) != 'OFF'],
                            ['web_server'] + [event.split()[0] for event in events
                                              if event.endswith(' running')])
                        self.assertEqual(list(install_events.STEPS)[1:],
                                         [event.split()[0] for event in events
                                          if event.split()[1] in ('running', 'skipped')])
                        self.assertEqual('panel done', events[-1])

    def test_step_is_left_running_when_the_installer_stops(self):
        main = self.server_installer()
        database = Mock(side_effect=RuntimeError('fixture database failure'))
        installer = Mock()
        installer.installMySQL = database
        with patch.dict(main.__globals__, {'InstallCyberPanel': Mock(return_value=installer)}):
            with self.assertRaisesRegex(RuntimeError, 'fixture database failure'):
                main('/root', 'One', 0, 0, None, '8090', 'ON', 'ON', '192.0.2.10', 'OFF')
        self.assertEqual(['web_server done', 'php running', 'php done', 'database running'], self.events())


class PythonExitStatusTests(unittest.TestCase):
    def test_exit_asked_for_with_a_message_is_never_a_success(self):
        for arguments in ((), (os.EX_OK,)):
            with self.subTest(arguments=arguments):
                with patch('builtins.print'), self.assertRaises(SystemExit) as stopped:
                    install_utils.stdOut('fixture failure', 0, 1, *arguments)
                self.assertEqual(os.EX_SOFTWARE, stopped.exception.code)
        with patch('builtins.print'), self.assertRaises(SystemExit) as stopped:
            install_utils.stdOut('fixture failure', 0, 1, os.EX_OSERR)
        self.assertEqual(os.EX_OSERR, stopped.exception.code)

    def test_failed_command_with_exit_asked_for_is_never_a_success(self):
        with patch('builtins.print'), patch.object(install_utils.subprocess, 'call', return_value=1), \
                self.assertRaises(SystemExit) as stopped:
            install_utils.call('false', install_utils.ubuntu, '', 'fixture', 0, 1)
        self.assertEqual(os.EX_SOFTWARE, stopped.exception.code)

    def test_no_failure_path_of_the_installer_ends_with_status_zero(self):
        for name in ('install/install.py', 'install/installCyberPanel.py', 'install/install_utils.py'):
            tree = ast.parse((ROOT / name).read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                target = ast.unparse(node.func) if hasattr(ast, 'unparse') else ''
                if target in ('os._exit', 'sys.exit', 'exit'):
                    argument = ast.unparse(node.args[0]) if node.args else ''
                    self.assertNotIn(argument, ('', '0', 'os.EX_OK'), '%s:%s' % (name, node.lineno))


if __name__ == '__main__':
    unittest.main()
