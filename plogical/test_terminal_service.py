import io
import itertools
import os
import pathlib
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock
from plogical import terminalService
from plogical.terminalService import (
    configure_terminal_service, plan_terminal_start, start_terminal_service)

ROOT = pathlib.Path(__file__).parents[1]
SERVICE = 'fastapi_ssh_server.service'
RESET = ['systemctl', 'reset-failed', SERVICE]
START = ['systemctl', 'start', SERVICE]


def properties(load, enabled, state):
    return 'LoadState=%s\nUnitFileState=%s\nActiveState=%s\n' % (load, enabled, state)


class TerminalServiceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.source = pathlib.Path(self.directory.name) / 'source.service'
        self.target = pathlib.Path(self.directory.name) / 'target.service'
        self.source.write_text('[Service]\nExecStart=/usr/bin/true\n')
        self.interpreter = pathlib.Path(self.directory.name) / 'python'

    def interpreter_exists(self):
        self.interpreter.write_text('#!/bin/sh\n')
        self.interpreter.chmod(0o700)

    def configure(self, load='loaded', active=False, fresh=False, enabled='enabled', state=None):
        state = state or ('active' if active else 'inactive')
        def run(command, **kwargs):
            if command[1] == 'show' and '--value' in command:return SimpleNamespace(stdout=load, returncode=0)
            if command[1] == 'show':return SimpleNamespace(stdout=properties('loaded', enabled, state), returncode=0)
            if command[1] == 'is-active':return SimpleNamespace(stdout='', returncode=0 if active else 3)
            return SimpleNamespace(stdout='', stderr='', returncode=0)
        with mock.patch('plogical.terminalService.subprocess.run', side_effect=run) as execute:
            result = configure_terminal_service(fresh_install=fresh, source=str(self.source), target=str(self.target),
                                                interpreter=str(self.interpreter))
        return result, [call[0][0] for call in execute.call_args_list]

    def test_fresh_install_enables_unit_and_leaves_start_until_interpreter_exists(self):
        result, commands = self.configure(load='not-found', fresh=True)
        self.assertEqual(result, 'enabled')
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertIn(['systemctl', 'enable', SERVICE], commands)
        self.assertFalse(any(command[1] in ('start', 'restart') or '--now' in command for command in commands))

    def test_fresh_install_starts_unit_when_interpreter_already_exists(self):
        self.interpreter_exists()
        result, commands = self.configure(load='not-found', fresh=True)
        self.assertEqual(result, 'enabled')
        self.assertLess(commands.index(['systemctl', 'enable', SERVICE]), commands.index(START))

    def test_upgrade_preserves_explicitly_removed_unit(self):
        result, commands = self.configure(load='not-found')
        self.assertEqual(result, 'absent')
        self.assertFalse(self.target.exists())
        self.assertEqual(len(commands), 1)

    def test_upgrade_and_repeat_install_preserve_stopped_unit(self):
        self.interpreter_exists()
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                self.target.write_text('previous unit')
                result, commands = self.configure(fresh=fresh)
                self.assertEqual(result, 'inactive')
                self.assertFalse(any(command[1] in ('start','restart','enable','reset-failed') for command in commands))

    def test_upgrade_starts_enabled_unit_left_failed(self):
        self.interpreter_exists()
        self.target.write_text('previous unit')
        result, commands = self.configure(state='failed')
        self.assertEqual(result, 'started')
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertEqual(commands[-2:], [RESET, START])
        self.assertLess(commands.index(['systemctl', 'daemon-reload']), commands.index(RESET))
        self.assertFalse(any(command[1] == 'enable' for command in commands))

    def test_upgrade_leaves_disabled_failed_unit_alone(self):
        self.interpreter_exists()
        self.target.write_text('previous unit')
        result, commands = self.configure(enabled='disabled', state='failed')
        self.assertEqual(result, 'inactive')
        self.assertFalse(any(command[1] in ('start','restart','enable','reset-failed') for command in commands))

    def test_masked_unit_is_never_replaced(self):
        self.target.symlink_to('/dev/null')
        result, commands = self.configure(load='masked', fresh=True)
        self.assertEqual(result, 'masked')
        self.assertEqual(os.readlink(str(self.target)), '/dev/null')
        self.assertEqual(len(commands), 1)

    def test_enabled_active_unit_is_refreshed_without_changing_enable_policy(self):
        self.target.write_text('previous unit')
        result, commands = self.configure(active=True)
        self.assertEqual(result, 'restarted')
        self.assertIn(['systemctl','restart','fastapi_ssh_server.service'], commands)
        self.assertFalse(any(command[1] == 'enable' for command in commands))

    def test_install_and_upgrade_use_distinct_lifecycle_policies(self):
        root = pathlib.Path(__file__).parents[1]
        self.assertIn('configure_terminal_service(fresh_install=True)',
                      (root / 'install/install.py').read_text())
        upgrade = (root / 'plogical/upgrade.py').read_text()
        self.assertIn('configure_terminal_service()', upgrade)
        self.assertNotIn('systemctl enable --now fastapi_ssh_server', upgrade)
        self.assertIn('systemctl is-active --quiet fastapi_ssh_server; then',
                      (root / 'cyberpanel_upgrade.sh').read_text())

    def test_unknown_service_state_fails_closed(self):
        with self.assertRaises(RuntimeError):self.configure(load='error')
        self.assertFalse(self.target.exists())

    def test_real_subprocess_supports_supported_python_runtimes(self):
        """Exercise Popen, since mocking run hides unsupported Python keywords."""
        executable = pathlib.Path(self.directory.name) / 'systemctl'
        journal = pathlib.Path(self.directory.name) / 'commands'
        executable.write_text('#!/bin/sh\n'
                              'echo "$*" >> "$CP_TEST_JOURNAL"\n'
                              'case "$1" in\n'
                              'show) case "$*" in\n'
                              '  *--value*) printf "%s\\n" "$CP_TEST_LOAD";;\n'
                              '  *) printf "LoadState=loaded\\nUnitFileState=enabled\\nActiveState=%s\\n" "$CP_TEST_STATE";;\n'
                              '  esac;;\n'
                              'is-active) [ "$CP_TEST_STATE" = active ];;\n'
                              '*) exit 0;;\n'
                              'esac\n')
        executable.chmod(0o700)
        self.interpreter_exists()
        for load, state, fresh, expected, last in (
                ('not-found', 'inactive', True, 'enabled', 'start ' + SERVICE),
                ('loaded', 'active', False, 'restarted', 'restart ' + SERVICE),
                ('loaded', 'inactive', False, 'inactive', None),
                ('loaded', 'failed', False, 'started', 'start ' + SERVICE)):
            with self.subTest(expected=expected):
                if self.target.exists():
                    self.target.unlink()
                journal.write_text('')
                environment = {'PATH': self.directory.name + os.pathsep + os.environ.get('PATH', ''),
                               'CP_TEST_LOAD': load, 'CP_TEST_STATE': state, 'CP_TEST_JOURNAL': str(journal)}
                with mock.patch.dict(os.environ, environment):
                    result = configure_terminal_service(fresh_install=fresh,
                                                        source=str(self.source), target=str(self.target),
                                                        interpreter=str(self.interpreter))
                self.assertEqual(result, expected)
                self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
                issued = journal.read_text().splitlines()
                if last:
                    self.assertEqual(issued[-1], last)
                else:
                    self.assertFalse(any(line.split()[0] in ('start', 'restart', 'reset-failed', 'enable')
                                         for line in issued))


class TerminalStartDecisionTests(unittest.TestCase):
    """plan_terminal_start is the whole policy; these cover every combination."""

    LOADS = ('loaded', 'not-found', 'masked', 'error', 'bad-setting', '')
    ENABLED = ('enabled', 'enabled-runtime', 'disabled', 'masked', 'masked-runtime', 'static',
               'linked', 'indirect', 'bad', '')
    ACTIVE = ('active', 'reloading', 'activating', 'deactivating', 'inactive', 'failed', '')

    def test_enabled_failed_unit_is_cleared_and_started(self):
        for start_stopped in (False, True):
            self.assertEqual(plan_terminal_start('loaded', 'enabled', 'failed', True, start_stopped),
                             ('started', [RESET, START]))

    def test_stopped_unit_is_started_only_at_the_end_of_an_installation(self):
        self.assertEqual(plan_terminal_start('loaded', 'enabled', 'inactive', True), ('stopped', []))
        self.assertEqual(plan_terminal_start('loaded', 'enabled', 'inactive', True, True), ('started', [START]))

    def test_nothing_is_started_while_the_interpreter_is_missing(self):
        self.assertEqual(plan_terminal_start('loaded', 'enabled', 'failed', False), ('not-ready', []))
        self.assertEqual(plan_terminal_start('loaded', 'enabled', 'inactive', False, True), ('not-ready', []))

    def test_disabled_masked_or_missing_unit_is_left_alone(self):
        self.assertEqual(plan_terminal_start('loaded', 'disabled', 'failed', True, True), ('not-enabled', []))
        self.assertEqual(plan_terminal_start('loaded', 'disabled', 'inactive', True, True), ('not-enabled', []))
        self.assertEqual(plan_terminal_start('masked', 'masked', 'failed', True, True), ('masked', []))
        self.assertEqual(plan_terminal_start('loaded', 'masked-runtime', 'failed', True, True), ('masked', []))
        self.assertEqual(plan_terminal_start('not-found', '', 'inactive', True, True), ('not-loaded', []))

    def test_running_or_transitioning_unit_is_not_touched(self):
        for active in ('active', 'reloading', 'activating', 'deactivating'):
            self.assertEqual(plan_terminal_start('loaded', 'enabled', active, True, True), ('unchanged', []))

    def test_every_combination_only_starts_an_enabled_unit_with_its_interpreter(self):
        for load, enabled, active, ready, start_stopped in itertools.product(
                self.LOADS, self.ENABLED, self.ACTIVE, (False, True), (False, True)):
            outcome, commands = plan_terminal_start(load, enabled, active, ready, start_stopped)
            with self.subTest(load=load, enabled=enabled, active=active, ready=ready, start_stopped=start_stopped):
                self.assertEqual(bool(commands), outcome == 'started')
                for command in commands:
                    self.assertIn(command, (RESET, START))
                if commands:
                    self.assertEqual((load, enabled, ready), ('loaded', 'enabled', True))
                    self.assertIn(active, ('failed', 'inactive'))
                    self.assertEqual(commands[-1], START)
                    self.assertEqual(RESET in commands, active == 'failed')
                    self.assertTrue(active == 'failed' or start_stopped)


class TerminalStartCommandTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.interpreter = pathlib.Path(self.directory.name) / 'python'
        self.interpreter.write_text('#!/bin/sh\n')
        self.interpreter.chmod(0o700)

    def runner(self, shown=properties('loaded', 'enabled', 'failed'), status=0, failing=None):
        issued = []
        def run(command):
            issued.append(command)
            if command[1] == 'show':
                return SimpleNamespace(stdout=shown, stderr='bus unavailable', returncode=status)
            if command[1] == failing:
                return SimpleNamespace(stdout='', stderr='Unit not startable', returncode=1)
            return SimpleNamespace(stdout='', stderr='', returncode=0)
        return run, issued

    def start(self, run, **options):
        return start_terminal_service(interpreter=str(self.interpreter), run=run, **options)

    def test_reads_state_once_then_clears_and_starts_failed_unit(self):
        run, issued = self.runner()
        self.assertEqual(self.start(run), 'started')
        self.assertEqual(issued, [['systemctl', 'show', '--property=LoadState', '--property=UnitFileState',
                                   '--property=ActiveState', SERVICE], RESET, START])

    def test_disabled_failed_unit_gets_no_command(self):
        run, issued = self.runner(properties('loaded', 'disabled', 'failed'))
        self.assertEqual(self.start(run, start_stopped=True), 'not-enabled')
        self.assertEqual(len(issued), 1)

    def test_missing_or_unusable_interpreter_defers_the_start(self):
        for prepare in (self.interpreter.unlink, lambda: self.interpreter.write_text('') or self.interpreter.chmod(0o600)):
            prepare()
            run, issued = self.runner(properties('loaded', 'enabled', 'inactive'))
            self.assertEqual(self.start(run, start_stopped=True), 'not-ready')
            self.assertEqual(len(issued), 1)

    def test_unreadable_state_or_failed_command_is_reported(self):
        run, issued = self.runner(status=1)
        with self.assertRaisesRegex(RuntimeError, 'bus unavailable'):
            self.start(run)
        self.assertEqual(len(issued), 1)
        run, issued = self.runner(failing='start')
        with self.assertRaisesRegex(RuntimeError, 'Unit not startable'):
            self.start(run)
        run, issued = self.runner(shown='')
        self.assertEqual(self.start(run, start_stopped=True), 'not-loaded')
        self.assertEqual(len(issued), 1)

    def command_line(self, arguments, run):
        with mock.patch('sys.stdout', new_callable=io.StringIO) as out, \
                mock.patch('sys.stderr', new_callable=io.StringIO) as err:
            status = terminalService.main(arguments, interpreter=str(self.interpreter), run=run)
        return status, out.getvalue(), err.getvalue()

    def test_command_line_modes(self):
        run, issued = self.runner(properties('loaded', 'enabled', 'inactive'))
        self.assertEqual(self.command_line(['repair'], run), (0, 'Web Terminal service: stopped\n', ''))
        self.assertEqual(len(issued), 1)
        run, issued = self.runner(properties('loaded', 'enabled', 'inactive'))
        self.assertEqual(self.command_line(['start-installed'], run), (0, 'Web Terminal service: started\n', ''))
        self.assertEqual(issued[1:], [START])
        run, issued = self.runner(failing='start')
        status, out, err = self.command_line(['repair'], run)
        self.assertEqual((status, out), (1, ''))
        self.assertIn('Unit not startable', err)
        for arguments in ([], ['start'], ['repair', 'now']):
            run, issued = self.runner()
            self.assertEqual(self.command_line(arguments, run)[0], 2)
            self.assertEqual(issued, [])


class TerminalStartOrderTests(unittest.TestCase):
    """The unit is started only after what its ExecStart names has been created."""

    def test_unit_runs_the_interpreter_the_start_waits_for(self):
        unit = (ROOT / 'fastapi_ssh_server.service').read_text()
        self.assertIn('\nExecStart=%s -m uvicorn ' % terminalService.INTERPRETER, unit)
        self.assertEqual(terminalService.SERVICE, 'fastapi_ssh_server.service')

    def test_module_never_enables_and_starts_in_one_step(self):
        self.assertNotIn('--now', (ROOT / 'plogical/terminalService.py').read_text())

    def test_installer_starts_the_unit_after_interpreter_and_key_pair(self):
        script = (ROOT / 'cyberpanel.sh').read_text()
        steps = script[script.rindex('\nMain_Installation\n'):]
        order = [steps.index('\n%s\n' % step) for step in (
            'Main_Installation', 'Post_Install_Required_Components', 'Post_Install_Regenerate_Cert',
            'Post_Install_Start_Web_Terminal')]
        self.assertEqual(order, sorted(order))
        self.assertLess(order[-1], steps.index('\nPost_Install_Tweak '))
        body = script.split('\nPost_Install_Start_Web_Terminal() {', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('/usr/local/CyberCP/plogical/terminalService.py start-installed', body)
        self.assertNotIn('systemctl enable', body)
        creation = script.split('\nPost_Install_Required_Components() {', 1)[1].split('\n}\n', 1)[0]
        self.assertIn('-m venv /usr/local/CyberCP', creation)

    def test_upgrade_script_repairs_a_unit_that_is_not_running(self):
        script = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        body = script.split('\nRestart_Web_Terminal() {', 1)[1].split('\n}\n', 1)[0]
        active, repair = body.split('\n  elif ', 1)
        self.assertIn('if systemctl is-active --quiet fastapi_ssh_server; then', active)
        self.assertIn('systemctl restart fastapi_ssh_server', active)
        self.assertIn('/usr/local/CyberCP/plogical/terminalService.py repair', repair)
        for forbidden in ('systemctl enable', 'systemctl unmask', 'systemctl start', 'systemctl restart'):
            self.assertNotIn(forbidden, repair)


if __name__ == '__main__':unittest.main()
