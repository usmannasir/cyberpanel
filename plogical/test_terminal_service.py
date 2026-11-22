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
    configure_terminal_service, main_process_not_executed, plan_terminal_start, start_terminal_service)

ROOT = pathlib.Path(__file__).parents[1]
SERVICE = 'fastapi_ssh_server.service'
RESET = ['systemctl', 'reset-failed', SERVICE]
START = ['systemctl', 'start', SERVICE]
SHOW = ['systemctl', 'show'] + ['--property=' + name for name in terminalService.PROPERTIES] + [SERVICE]

# How systemd reports the ways the unit can end up failed: (Result, ExecMainCode, ExecMainStatus).
NOT_EXECUTED = {'missing interpreter': ('exit-code', '1', '203'),
                'missing interpreter, start limit': ('start-limit-hit', '1', '203')}
OTHER_FAILURES = {'stop timed out': ('timeout', '2', '9'),
                  'killed by a signal': ('signal', '2', '15'),
                  'killed for memory': ('oom-kill', '2', '9'),
                  'crashed': ('exit-code', '1', '1'),
                  'crash loop': ('start-limit-hit', '1', '1'),
                  'core dump': ('core-dump', '3', '6'),
                  'watchdog': ('watchdog', '2', '6'),
                  'signal numbered 203': ('signal', '2', '203'),
                  'unknown': ('', '', '')}


def unit_state(active='inactive', failure=('success', '0', '0'), load='loaded', enabled='enabled', restarts='0'):
    return {'LoadState': load, 'UnitFileState': enabled, 'ActiveState': active, 'Result': failure[0],
            'ExecMainCode': failure[1], 'ExecMainStatus': failure[2], 'NRestarts': restarts}


class FakeSystemd(object):
    """Answers systemctl for one unit and records what was asked of it."""

    def __init__(self, state=None, before_install='loaded', stays_up=True, failing=None, unreadable=False):
        self.state = dict(state or unit_state())
        self.before_install, self.stays_up, self.failing, self.unreadable = before_install, stays_up, failing, unreadable
        self.issued = []

    def __call__(self, command, **options):
        self.issued.append(command)
        verb = command[1]
        if verb == 'show' and '--value' in command:
            return SimpleNamespace(stdout=self.before_install, stderr='', returncode=0)
        if verb == 'show':
            if self.unreadable:
                return SimpleNamespace(stdout='', stderr='bus unavailable', returncode=1)
            return SimpleNamespace(stdout=''.join('%s=%s\n' % item for item in sorted(self.state.items())),
                                   stderr='', returncode=0)
        if verb == 'is-active':
            return SimpleNamespace(stdout='', stderr='', returncode=0 if self.state['ActiveState'] == 'active' else 3)
        if verb == self.failing:
            return SimpleNamespace(stdout='', stderr='Unit not startable', returncode=1)
        if verb in ('start', 'restart'):
            if self.stays_up:
                self.state.update(unit_state('active'), UnitFileState=self.state['UnitFileState'])
            else:
                self.state.update(ActiveState='failed', Result='exit-code', ExecMainCode='1',
                                  ExecMainStatus='1', NRestarts='5')
        return SimpleNamespace(stdout='', stderr='', returncode=0)

    def changes(self):
        return [command for command in self.issued if command[1] not in ('show', 'is-active')]


class WithoutWaiting(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch('plogical.terminalService.time.sleep')
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.interpreter = pathlib.Path(self.directory.name) / 'python'

    def interpreter_exists(self):
        self.interpreter.write_text('#!/bin/sh\n')
        self.interpreter.chmod(0o700)


class TerminalServiceTests(WithoutWaiting):
    def setUp(self):
        super(TerminalServiceTests, self).setUp()
        self.source = pathlib.Path(self.directory.name) / 'source.service'
        self.target = pathlib.Path(self.directory.name) / 'target.service'
        self.source.write_text('[Service]\nExecStart=/usr/bin/true\n')

    def configure(self, systemd=None, fresh=False):
        systemd = systemd or FakeSystemd()
        with mock.patch('plogical.terminalService.subprocess.run', side_effect=systemd):
            result = configure_terminal_service(fresh_install=fresh, source=str(self.source), target=str(self.target),
                                                interpreter=str(self.interpreter))
        return result, systemd

    def test_fresh_install_enables_unit_and_leaves_start_until_interpreter_exists(self):
        result, systemd = self.configure(FakeSystemd(before_install='not-found'), fresh=True)
        self.assertEqual(result, ('enabled', ''))
        self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
        self.assertEqual(systemd.changes(), [['systemctl', 'daemon-reload'], ['systemctl', 'enable', SERVICE]])

    def test_fresh_install_starts_unit_when_interpreter_already_exists(self):
        self.interpreter_exists()
        result, systemd = self.configure(FakeSystemd(before_install='not-found'), fresh=True)
        self.assertEqual(result, ('enabled', ''))
        self.assertEqual(systemd.changes()[-2:], [['systemctl', 'enable', SERVICE], START])

    def test_fresh_install_reports_a_unit_that_does_not_stay_up(self):
        self.interpreter_exists()
        result, systemd = self.configure(FakeSystemd(before_install='not-found', stays_up=False), fresh=True)
        self.assertEqual(result[0], 'enabled')
        self.assertIn('did not stay running', result[1])

    def test_upgrade_preserves_explicitly_removed_unit(self):
        result, systemd = self.configure(FakeSystemd(before_install='not-found'))
        self.assertEqual(result, ('absent', ''))
        self.assertFalse(self.target.exists())
        self.assertEqual(len(systemd.issued), 1)

    def test_upgrade_and_repeat_install_preserve_stopped_unit(self):
        self.interpreter_exists()
        for fresh in (False, True):
            with self.subTest(fresh=fresh):
                self.target.write_text('previous unit')
                result, systemd = self.configure(fresh=fresh)
                self.assertEqual(result, ('inactive', ''))
                self.assertEqual(systemd.changes(), [['systemctl', 'daemon-reload']])

    def test_upgrade_starts_enabled_unit_whose_main_process_could_not_be_executed(self):
        self.interpreter_exists()
        for name, failure in NOT_EXECUTED.items():
            with self.subTest(failure=name):
                self.target.write_text('previous unit')
                result, systemd = self.configure(FakeSystemd(unit_state('failed', failure)))
                self.assertEqual(result, ('started', ''))
                self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
                self.assertEqual(systemd.changes(), [['systemctl', 'daemon-reload'], RESET, START])

    def test_upgrade_leaves_and_names_any_other_failed_unit(self):
        self.interpreter_exists()
        for name, failure in OTHER_FAILURES.items():
            with self.subTest(failure=name):
                self.target.write_text('previous unit')
                result, systemd = self.configure(FakeSystemd(unit_state('failed', failure)))
                self.assertEqual(result[0], 'failed')
                self.assertIn('Result=%s, ExecMainCode=%s, ExecMainStatus=%s' % failure, result[1])
                self.assertIn('left as it is', result[1])
                self.assertEqual(systemd.changes(), [['systemctl', 'daemon-reload']])

    def test_upgrade_reports_a_repaired_unit_that_does_not_stay_up(self):
        self.interpreter_exists()
        self.target.write_text('previous unit')
        result, systemd = self.configure(FakeSystemd(unit_state('failed', NOT_EXECUTED['missing interpreter']),
                                                     stays_up=False))
        self.assertEqual(result[0], 'not-running')
        self.assertIn('ActiveState=failed', result[1])

    def test_upgrade_leaves_disabled_failed_unit_alone(self):
        self.interpreter_exists()
        self.target.write_text('previous unit')
        for failure in list(NOT_EXECUTED.values()) + list(OTHER_FAILURES.values()):
            result, systemd = self.configure(FakeSystemd(unit_state('failed', failure, enabled='disabled')))
            self.assertEqual(result, ('inactive', ''))
            self.assertEqual(systemd.changes(), [['systemctl', 'daemon-reload']])

    def test_masked_unit_is_never_replaced(self):
        self.target.symlink_to('/dev/null')
        result, systemd = self.configure(FakeSystemd(before_install='masked'), fresh=True)
        self.assertEqual(result, ('masked', ''))
        self.assertEqual(os.readlink(str(self.target)), '/dev/null')
        self.assertEqual(len(systemd.issued), 1)

    def test_enabled_active_unit_is_refreshed_without_changing_enable_policy(self):
        self.target.write_text('previous unit')
        result, systemd = self.configure(FakeSystemd(unit_state('active')))
        self.assertEqual(result, ('restarted', ''))
        self.assertEqual(systemd.changes(), [['systemctl', 'daemon-reload'], ['systemctl', 'restart', SERVICE]])

    def test_install_and_upgrade_use_distinct_lifecycle_policies(self):
        root = pathlib.Path(__file__).parents[1]
        self.assertIn('configure_terminal_service(fresh_install=True)',
                      (root / 'install/install.py').read_text())
        upgrade = (root / 'plogical/upgrade.py').read_text()
        self.assertIn('configure_terminal_service()', upgrade)
        self.assertNotIn('systemctl enable --now fastapi_ssh_server', upgrade)
        self.assertIn('systemctl is-active --quiet fastapi_ssh_server; then',
                      (root / 'cyberpanel_upgrade.sh').read_text())

    def test_upgrader_prints_the_note_about_a_unit_it_left_alone(self):
        upgrade = (ROOT / 'plogical/upgrade.py').read_text()
        call = upgrade.split('terminal_outcome, terminal_note = configure_terminal_service()\n', 1)[1]
        self.assertEqual([line.strip() for line in call.splitlines()[:2]],
                         ['if terminal_note:', 'Upgrade.stdOut(terminal_note)'])

    def test_unknown_service_state_fails_closed(self):
        with self.assertRaises(RuntimeError):self.configure(FakeSystemd(before_install='error'))
        self.assertFalse(self.target.exists())

    def test_real_subprocess_supports_supported_python_runtimes(self):
        """Exercise Popen, since mocking run hides unsupported Python keywords."""
        executable = pathlib.Path(self.directory.name) / 'systemctl'
        journal = pathlib.Path(self.directory.name) / 'commands'
        active = pathlib.Path(self.directory.name) / 'active'
        executable.write_text('#!/bin/sh\n'
                              'echo "$*" >> "$CP_TEST_JOURNAL"\n'
                              'read state < "$CP_TEST_ACTIVE"\n'
                              'case "$1" in\n'
                              'show) case "$*" in\n'
                              '  *--value*) printf "%s\\n" "$CP_TEST_LOAD";;\n'
                              '  *) printf "LoadState=loaded\\nUnitFileState=enabled\\nActiveState=%s\\n" "$state"\n'
                              '     printf "Result=%s\\nExecMainCode=%s\\nExecMainStatus=%s\\nNRestarts=0\\n" $CP_TEST_FAILURE;;\n'
                              '  esac;;\n'
                              'is-active) [ "$state" = active ];;\n'
                              'start|restart) echo "$CP_TEST_STARTS_AS" > "$CP_TEST_ACTIVE";;\n'
                              '*) exit 0;;\n'
                              'esac\n')
        executable.chmod(0o700)
        self.interpreter_exists()
        for load, state, failure, starts_as, fresh, expected, last in (
                ('not-found', 'inactive', 'success 0 0', 'active', True, 'enabled', 'start ' + SERVICE),
                ('loaded', 'active', 'success 0 0', 'active', False, 'restarted', 'restart ' + SERVICE),
                ('loaded', 'inactive', 'success 0 0', 'active', False, 'inactive', None),
                ('loaded', 'failed', 'exit-code 1 203', 'active', False, 'started', 'start ' + SERVICE),
                ('loaded', 'failed', 'exit-code 1 203', 'failed', False, 'not-running', 'start ' + SERVICE),
                ('loaded', 'failed', 'timeout 2 9', 'active', False, 'failed', None)):
            with self.subTest(expected=expected):
                if self.target.exists():
                    self.target.unlink()
                journal.write_text('')
                active.write_text(state + '\n')
                environment = {'PATH': self.directory.name + os.pathsep + os.environ.get('PATH', ''),
                               'CP_TEST_LOAD': load, 'CP_TEST_ACTIVE': str(active), 'CP_TEST_FAILURE': failure,
                               'CP_TEST_STARTS_AS': starts_as, 'CP_TEST_JOURNAL': str(journal)}
                with mock.patch.dict(os.environ, environment):
                    result, note = configure_terminal_service(fresh_install=fresh,
                                                              source=str(self.source), target=str(self.target),
                                                              interpreter=str(self.interpreter))
                self.assertEqual(result, expected)
                self.assertEqual(bool(note), expected in ('not-running', 'failed'))
                self.assertEqual(self.source.read_bytes(), self.target.read_bytes())
                issued = [line for line in journal.read_text().splitlines()
                          if line.split()[0] in ('start', 'restart', 'reset-failed', 'enable')]
                self.assertEqual(issued[-1] if issued else None, last)


class TerminalStartDecisionTests(unittest.TestCase):
    """plan_terminal_start is the whole policy; these cover every combination."""

    LOADS = ('loaded', 'not-found', 'masked', 'error', 'bad-setting', '')
    ENABLED = ('enabled', 'enabled-runtime', 'disabled', 'masked', 'masked-runtime', 'static',
               'linked', 'indirect', 'bad', '')
    ACTIVE = ('active', 'reloading', 'activating', 'deactivating', 'inactive', 'failed', '')

    def test_only_an_exited_main_process_with_status_203_counts_as_not_executed(self):
        for name, failure in NOT_EXECUTED.items():
            self.assertTrue(main_process_not_executed(unit_state('failed', failure)), name)
        for name, failure in OTHER_FAILURES.items():
            self.assertFalse(main_process_not_executed(unit_state('failed', failure)), name)
        self.assertFalse(main_process_not_executed({}))
        self.assertFalse(main_process_not_executed(unit_state('failed', ('success', '1', '203'))))

    def test_upgrade_starts_a_failed_unit_only_if_its_main_process_could_not_be_executed(self):
        for failure in NOT_EXECUTED.values():
            self.assertEqual(plan_terminal_start(unit_state('failed', failure), True), ('started', [RESET, START]))
        for name, failure in OTHER_FAILURES.items():
            self.assertEqual(plan_terminal_start(unit_state('failed', failure), True), ('failed', []), name)
        self.assertEqual(plan_terminal_start({'LoadState': 'loaded', 'UnitFileState': 'enabled',
                                              'ActiveState': 'failed'}, True), ('failed', []))

    def test_end_of_installation_starts_a_failed_unit_whatever_the_failure(self):
        for failure in list(NOT_EXECUTED.values()) + list(OTHER_FAILURES.values()):
            self.assertEqual(plan_terminal_start(unit_state('failed', failure), True, True),
                             ('started', [RESET, START]))

    def test_stopped_unit_is_started_only_at_the_end_of_an_installation(self):
        self.assertEqual(plan_terminal_start(unit_state('inactive'), True), ('stopped', []))
        self.assertEqual(plan_terminal_start(unit_state('inactive'), True, True), ('started', [START]))
        # a stop that ended cleanly after an earlier failed start is still a stop
        stopped = unit_state('inactive', NOT_EXECUTED['missing interpreter'])
        self.assertEqual(plan_terminal_start(stopped, True), ('stopped', []))

    def test_nothing_is_started_while_the_interpreter_is_missing(self):
        failed = unit_state('failed', NOT_EXECUTED['missing interpreter'])
        self.assertEqual(plan_terminal_start(failed, False), ('not-ready', []))
        self.assertEqual(plan_terminal_start(failed, False, True), ('not-ready', []))
        self.assertEqual(plan_terminal_start(unit_state('inactive'), False, True), ('not-ready', []))

    def test_disabled_masked_or_missing_unit_is_left_alone(self):
        failure = NOT_EXECUTED['missing interpreter']
        for state, outcome in ((unit_state('failed', failure, enabled='disabled'), 'not-enabled'),
                               (unit_state('inactive', enabled='disabled'), 'not-enabled'),
                               (unit_state('failed', failure, load='masked', enabled='masked'), 'masked'),
                               (unit_state('failed', failure, enabled='masked-runtime'), 'masked'),
                               (unit_state('inactive', load='not-found', enabled=''), 'not-loaded'),
                               ({}, 'not-loaded')):
            self.assertEqual(plan_terminal_start(state, True, True), (outcome, []))

    def test_running_or_transitioning_unit_is_not_touched(self):
        for active in ('active', 'reloading', 'activating', 'deactivating'):
            self.assertEqual(plan_terminal_start(unit_state(active), True, True), ('unchanged', []))

    def test_every_combination_only_starts_an_enabled_unit_with_its_interpreter(self):
        failures = list(NOT_EXECUTED.values()) + list(OTHER_FAILURES.values()) + [('success', '0', '0')]
        for load, enabled, active, failure, ready, start_stopped in itertools.product(
                self.LOADS, self.ENABLED, self.ACTIVE, failures, (False, True), (False, True)):
            outcome, commands = plan_terminal_start(unit_state(active, failure, load, enabled), ready, start_stopped)
            with self.subTest(load=load, enabled=enabled, active=active, failure=failure, ready=ready,
                              start_stopped=start_stopped):
                self.assertEqual(bool(commands), outcome == 'started')
                for command in commands:
                    self.assertIn(command, (RESET, START))
                if commands:
                    self.assertEqual((load, enabled, ready), ('loaded', 'enabled', True))
                    self.assertIn(active, ('failed', 'inactive'))
                    self.assertEqual(commands[-1], START)
                    self.assertEqual(RESET in commands, active == 'failed')
                    self.assertTrue(start_stopped or (active == 'failed' and failure in NOT_EXECUTED.values()))


class TerminalStartCommandTests(WithoutWaiting):
    def setUp(self):
        super(TerminalStartCommandTests, self).setUp()
        self.interpreter_exists()
        self.not_executed = unit_state('failed', NOT_EXECUTED['missing interpreter'])

    def start(self, systemd, **options):
        return start_terminal_service(interpreter=str(self.interpreter), run=systemd, **options)

    def test_clears_and_starts_then_watches_the_unit_stay_up(self):
        systemd = FakeSystemd(self.not_executed)
        self.assertEqual(self.start(systemd), ('started', ''))
        self.assertEqual(systemd.issued, [SHOW, RESET, START] + [SHOW] * terminalService.SETTLE_CHECKS)
        self.assertEqual(self.sleep.call_args_list, [mock.call(1)] * terminalService.SETTLE_CHECKS)

    def test_start_that_does_not_stay_active_is_reported_as_not_running(self):
        for start_stopped, state in ((False, self.not_executed), (True, unit_state('inactive'))):
            systemd = FakeSystemd(state, stays_up=False)
            outcome, note = self.start(systemd, start_stopped=start_stopped)
            self.assertEqual(outcome, 'not-running')
            self.assertIn('ActiveState=failed, Result=exit-code, ExecMainCode=1, ExecMainStatus=1, NRestarts=5', note)
            self.assertIn('journalctl -u ' + SERVICE, note)
            self.assertEqual(systemd.issued[-1], SHOW)

    def test_unit_that_dies_and_is_restarted_by_systemd_is_not_running(self):
        systemd = FakeSystemd(unit_state('inactive'))
        def dying(command, **options):
            if command == SHOW and systemd.issued.count(SHOW) == 2:  # the second look after the start
                systemd.state.update(NRestarts='1')
            return systemd(command, **options)
        outcome, note = self.start(dying, start_stopped=True)
        self.assertEqual(outcome, 'not-running')
        self.assertIn('ActiveState=active', note)
        self.assertIn('NRestarts=1', note)
        self.assertEqual(self.sleep.call_count, 2)

    def test_other_failed_states_get_no_command_and_are_named(self):
        for name, failure in OTHER_FAILURES.items():
            with self.subTest(failure=name):
                systemd = FakeSystemd(unit_state('failed', failure))
                outcome, note = self.start(systemd)
                self.assertEqual(outcome, 'failed')
                self.assertIn('Result=%s, ExecMainCode=%s, ExecMainStatus=%s' % failure, note)
                self.assertIn('systemctl disable ' + SERVICE, note)
                self.assertEqual(systemd.issued, [SHOW])
                self.sleep.assert_not_called()

    def test_disabled_failed_unit_gets_no_command(self):
        systemd = FakeSystemd(unit_state('failed', NOT_EXECUTED['missing interpreter'], enabled='disabled'))
        self.assertEqual(self.start(systemd, start_stopped=True), ('not-enabled', ''))
        self.assertEqual(systemd.issued, [SHOW])

    def test_missing_or_unusable_interpreter_defers_the_start(self):
        for prepare in (self.interpreter.unlink, lambda: self.interpreter.write_text('') or self.interpreter.chmod(0o600)):
            prepare()
            systemd = FakeSystemd(unit_state('inactive'))
            self.assertEqual(self.start(systemd, start_stopped=True), ('not-ready', ''))
            self.assertEqual(systemd.issued, [SHOW])

    def test_unreadable_state_or_failed_command_is_reported(self):
        systemd = FakeSystemd(unreadable=True)
        with self.assertRaisesRegex(RuntimeError, 'bus unavailable'):
            self.start(systemd)
        self.assertEqual(len(systemd.issued), 1)
        systemd = FakeSystemd(self.not_executed, failing='start')
        with self.assertRaisesRegex(RuntimeError, 'Unit not startable'):
            self.start(systemd)
        self.assertEqual(systemd.issued, [SHOW, RESET, START])

    def command_line(self, arguments, systemd):
        with mock.patch('sys.stdout', new_callable=io.StringIO) as out, \
                mock.patch('sys.stderr', new_callable=io.StringIO) as err:
            status = terminalService.main(arguments, interpreter=str(self.interpreter), run=systemd)
        return status, out.getvalue(), err.getvalue()

    def test_command_line_modes(self):
        systemd = FakeSystemd(unit_state('inactive'))
        self.assertEqual(self.command_line(['repair'], systemd), (0, 'Web Terminal service: stopped\n', ''))
        self.assertEqual(systemd.issued, [SHOW])
        systemd = FakeSystemd(unit_state('inactive'))
        self.assertEqual(self.command_line(['start-installed'], systemd), (0, 'Web Terminal service: started\n', ''))
        self.assertEqual(systemd.changes(), [START])
        systemd = FakeSystemd(self.not_executed)
        self.assertEqual(self.command_line(['repair'], systemd), (0, 'Web Terminal service: started\n', ''))
        systemd = FakeSystemd(self.not_executed, failing='start')
        status, out, err = self.command_line(['repair'], systemd)
        self.assertEqual((status, out), (1, ''))
        self.assertIn('Unit not startable', err)
        for arguments in ([], ['start'], ['repair', 'now']):
            systemd = FakeSystemd()
            self.assertEqual(self.command_line(arguments, systemd)[0], 2)
            self.assertEqual(systemd.issued, [])

    def test_command_line_reports_the_real_state(self):
        systemd = FakeSystemd(unit_state('inactive'), stays_up=False)
        status, out, err = self.command_line(['start-installed'], systemd)
        self.assertEqual((status, err), (1, ''))
        self.assertEqual(out.splitlines()[0], 'Web Terminal service: not-running')
        self.assertIn('did not stay running', out.splitlines()[1])
        systemd = FakeSystemd(unit_state('failed', OTHER_FAILURES['stop timed out']))
        status, out, err = self.command_line(['repair'], systemd)
        self.assertEqual((status, err), (0, ''))
        self.assertEqual(out.splitlines()[0], 'Web Terminal service: failed')
        self.assertIn('Result=timeout', out.splitlines()[1])
        self.assertEqual(systemd.changes(), [])


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
        self.assertIn('| tee -a /var/log/cyberpanel_upgrade_debug.log', repair)
        for forbidden in ('systemctl enable', 'systemctl unmask', 'systemctl start', 'systemctl restart'):
            self.assertNotIn(forbidden, repair)


if __name__ == '__main__':unittest.main()
