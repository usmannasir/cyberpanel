"""Status events and exit statuses of the Python installer.

install.py and installCyberPanel.py are run through their real entry points
with what they install replaced; install_events is used as it is.
"""
import argparse
import ast
import importlib
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
from install.installer_test_harness import parse_as_python_36

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
                parse_as_python_36((ROOT / name).read_text())

    def test_python_36_parser_refuses_what_python_36_does_not_have(self):
        self.assertIsInstance(parse_as_python_36('value = "%s" % 1\n'), ast.Module)
        with self.assertRaises(SyntaxError):
            parse_as_python_36('value = (\n')
        if sys.version_info >= (3, 8):
            # Where the parser has the switch, newer syntax is refused as well.
            for newer in ('if (count := 1):\n    pass\n', 'def call(first, /):\n    pass\n'):
                with self.subTest(newer=newer):
                    with self.assertRaises(SyntaxError):
                        parse_as_python_36(newer)

    def test_interpreter_without_the_parser_switch_is_not_given_it(self):
        # ast.parse of Python 3.6 and 3.7 has no feature_version; passing it there is a TypeError.
        for interpreter in ((3, 6, 8), (3, 7, 0)):
            with self.subTest(interpreter=interpreter):
                with patch('ast.parse', side_effect=lambda source: 'parsed') as parse:
                    self.assertEqual('parsed', parse_as_python_36('value = 1\n', interpreter))
                parse.assert_called_once_with('value = 1\n')


class InstallLogStepTests(unittest.TestCase):
    """installLog as install.py loads it: its steps are written to the status file."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.file = Path(directory.name) / 'install_events.log'
        self.progress = Path(directory.name) / 'installLogs.txt'
        # install.py runs in its own directory, where installLog finds
        # install_events beside it. requests is what posts the progress lines.
        self.requests = ModuleType('requests')
        self.requests.post = Mock()
        modules = patch.dict(sys.modules, {'requests': self.requests})
        modules.start()
        self.addCleanup(modules.stop)
        for name in ('installLog', 'install_events'):
            sys.modules.pop(name, None)
        sys.path.insert(0, str(ROOT / 'install'))
        self.addCleanup(sys.path.remove, str(ROOT / 'install'))
        self.module = importlib.import_module('installLog')
        writer = self.module.install_events
        self.assertEqual(str(ROOT / 'install/install_events.py'), writer.__file__)
        for target, name, replacement in ((writer, 'EVENTS_FILE', str(self.file)), (writer, '_running', 'web_server'),
                                          (self.module.InstallLog, 'fileName', str(self.progress))):
            patcher = patch.object(target, name, replacement)
            patcher.start()
            self.addCleanup(patcher.stop)
        environment = patch.dict(os.environ, {writer.RUN_ID_VARIABLE: 'b' * 32})
        environment.start()
        self.addCleanup(environment.stop)

    def test_steps_of_the_install_log_reach_the_status_file(self):
        log = self.module.InstallLog
        log.step('php')
        log.step('database')
        log.step('ftp', False)
        log.step('dns')
        log.step('email', enabled=False)
        log.step('panel')
        log.stepsFinished()
        lines = self.file.read_text().splitlines()
        self.assertEqual(['web_server done', 'php running', 'php done', 'database running', 'database done',
                          'ftp skipped', 'dns running', 'dns done', 'email skipped', 'panel running', 'panel done'],
                         [' '.join(line.split()[2:]) for line in lines])
        for line in lines:
            self.assertRegex(line, '^%s$' % EVENT_LINE.pattern)
            self.assertEqual('b' * 32, line.split()[1])
        self.assertEqual(0o600, stat.S_IMODE(self.file.stat().st_mode))

    def test_progress_lines_are_written_and_posted_as_before(self):
        log = self.module.InstallLog
        log.step('database')
        log.writeToFile('Installing MySQL,60')
        self.assertRegex(self.progress.read_text(), r'^\[[0-9._-]+\] Installing MySQL,60\n$')
        self.requests.post.assert_called_once()
        self.assertEqual(log.LogURL, self.requests.post.call_args[0][0])
        self.assertIn('Installing MySQL,60', self.requests.post.call_args[1]['data'])
        # A step is no progress line: it is not written there and not posted.
        self.assertNotIn('database', self.progress.read_text())


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
                        # Sieve comes with the mail server and not without it.
                        self.assertEqual(email == 'ON', 'sieve' in self.work)
                        self.assertEqual(email == 'ON',
                                         'Installing Sieve for email filtering..,55' in self.work)
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

    def test_no_exit_of_the_installer_reports_success_outright(self):
        files = installer_files()
        # The installer itself, its own modules and what it imports of the panel.
        for name in ('install/install.py', 'install/installCyberPanel.py', 'install/install_utils.py',
                     'install/installLog.py', 'install/install_events.py', 'install/mysqlUtilities.py',
                     'install/env_generator.py', 'plogical/terminalService.py', 'cyberpanel_version.py'):
            self.assertIn(ROOT / name, files)
        self.assertGreater(len(files), 20)
        for path in files:
            with self.subTest(file=str(path.relative_to(ROOT))):
                self.assertEqual([], exits(path.read_text(), successful=True))
        # The exits are seen, with the statuses they have now.
        self.assertEqual(4, len(exits((ROOT / 'install/install.py').read_text(), successful=False)))

    def test_exit_scan_sees_every_way_to_end_with_status_zero(self):
        # Proof that the scan above is not blind, on Python 3.6 as on newer ones.
        source = ('import os\nimport sys\n'
                  'os._exit(0)\nsys.exit()\nsys.exit(0)\nexit(0)\nsys.exit(os.EX_OK)\nsys.exit(None)\n'
                  'sys.exit(1)\nos._exit(os.EX_SOFTWARE)\nsys.exit("usage")\nsys.exit(0 if done else 1)\n'
                  'sys.exit(code or os.EX_SOFTWARE)\nmain.exit(0)\n')
        self.assertEqual([3, 4, 5, 6, 7, 8], exits(source, successful=True))
        self.assertEqual([9, 10, 11, 12, 13], exits(source, successful=False))


def imported_files(path):
    """The files of this repository that a Python file imports, wherever in it."""
    found = set()
    for node in ast.walk(ast.parse(path.read_text())):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules = [node.module]
        else:
            continue
        for module in modules:
            # install.py is run from its own directory, with the tree behind it.
            for base in (ROOT / 'install', ROOT):
                candidate = base / (module.replace('.', '/') + '.py')
                if candidate.exists():
                    found.add(candidate)
                    break
    return found


def installer_files():
    """Every Python file that a fresh installation runs code of: install.py,
    the installer's own modules as far as their imports lead, and the files of
    the panel that those import."""
    files = {ROOT / 'install/install.py'}
    queue = [ROOT / 'install/install.py']
    while queue:
        for found in imported_files(queue.pop()):
            if found not in files:
                files.add(found)
                if found.parent == ROOT / 'install':
                    queue.append(found)
    return sorted(files)


def dotted_name(node):
    parts = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        return '.'.join(reversed(parts + [node.id]))
    return ''


def exits(source, successful):
    """Line numbers of the calls that end the process: the ones that report
    success whatever happened (no status, 0, None, os.EX_OK), or the others.
    Written without ast.unparse, which Python 3.6 does not have."""
    lines = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call) or dotted_name(node.func) not in ('os._exit', 'sys.exit', 'exit', 'quit'):
            continue
        if not node.args:
            success = True
        else:
            try:
                value = ast.literal_eval(node.args[0])
                success = value is None or value is False or value == 0
            except ValueError:
                success = dotted_name(node.args[0]) == 'os.EX_OK'
        if success == successful:
            lines.append(node.lineno)
    return sorted(lines)


if __name__ == '__main__':
    unittest.main()
