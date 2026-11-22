"""Status events and exit statuses of cyberpanel.sh.

Every test runs the real top level of the script in a temporary machine
(installer_test_harness), with what would install or configure replaced.
"""
import os
import re
import signal
import stat
import unittest
from unittest.mock import patch

from install.installer_test_harness import (
    CLI_FAILED, REAL_FUNCTIONS, ROOT, SPECIAL_STUBS, STUBBED_PHASES,
    Installer, script_parts, top_level_functions,
)

STEPS = ('preflight repositories system_update python_env download_panel web_server '
         'php database ftp dns email panel finishing hostname_ssl ready').split()
EVENT_LINE = re.compile(
    r'[0-9]{10} [0-9a-f]{32} ('
    r'install started [0-9a-z.]+|install complete|install failed [a-z0-9_]+|panel ready|'
    r'(%s) (running|done|skipped|warning [a-z0-9_]+|failed [a-z0-9_]+))' % '|'.join(STEPS))

COMPLETE_RUN = ['install started 3.0.11']
for name in STEPS:
    if name == 'ready':
        COMPLETE_RUN += ['ready running', 'panel ready', 'ready done']
    else:
        COMPLETE_RUN += [name + ' running', name + ' done']
COMPLETE_RUN.append('install complete')


def up_to(step):
    """The events of a run until this step started."""
    return COMPLETE_RUN[:COMPLETE_RUN.index(step + ' running') + 1]


class HarnessSafetyTests(unittest.TestCase):
    def test_every_function_the_top_level_calls_is_known_to_the_harness(self):
        _, top_level = script_parts()
        called = set(top_level_functions(top_level))
        self.assertIn('Post_Install_Tweak', called)
        known = set(REAL_FUNCTIONS) | set(STUBBED_PHASES) | set(SPECIAL_STUBS)
        self.assertEqual(set(), called - known)

    def test_no_tool_that_changes_a_system_can_be_found(self):
        machine = Installer(self)
        for tool in ('systemctl', 'apt', 'apt-get', 'yum', 'dnf', 'rpm', 'pip', 'git', 'wget',
                     'curl', 'reboot', 'swapon', 'sysctl', 'ln', 'cp', 'mv', 'rm'):
            self.assertFalse((machine.root / 'bin' / tool).exists(), tool)

    def test_nothing_that_runs_names_a_path_outside_the_temporary_machine(self):
        outside = re.compile(r'(?<![\w./])/(etc|var|usr|root|home|tmp|opt|sys|boot|bin|sbin|lib|lib64|run|srv|mnt)/')
        for arguments, options in (
                (['-v', 'ols', '-a', '--debug'], {}),
                (['-v', 'ols', '-m', 'postfix'], {'dns': True, 'tls_output': CLI_FAILED}),
                (['-v', 'ols'], {'fail_at': 'Pre_Install_Required_Components'}),
                (['--debug'], {'stdin': '1\n1\n\n\n\n\n\n\n\n\n'})):
            with self.subTest(arguments=arguments):
                machine = Installer(self)
                machine.path('/usr/local/lsws/lsphp83/bin').mkdir(parents=True)
                runtime = machine.path('/usr/local/lsws/lsphp83/bin/lsphp')
                runtime.write_text('#!/bin/sh\n')
                runtime.chmod(0o755)
                result = machine.run(*arguments, trace=True, **options)
                # The script's check for sudo takes and prints the shell's own
                # variables; those two lines name paths without using them.
                trace = [line for line in result.stderr.splitlines() if line.startswith('+')
                         and not re.match(r"\++ (Sudo_Test=|echo )'BASH=", line)]
                self.assertGreater(len(trace), 200)
                for line in trace:
                    line = line.replace(str(machine.root), 'MACHINE').replace(str(ROOT), 'REPOSITORY')
                    self.assertIsNone(outside.search(line), line)


class SuccessfulRunTests(unittest.TestCase):
    def test_every_step_is_recorded_in_order_and_the_run_ends_complete(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(COMPLETE_RUN, machine.events())
        self.assertIn('CyberPanel Successfully Installed', result.stdout)
        # An error page is not an answer.
        self.assertIn('curl --silent --fail --insecure --max-time 5 --output /dev/null https://127.0.0.1:8090/',
                      machine.recorded(machine.calls))
        self.assertEqual(
            ['Pre_Install_Setup_Repository', 'Pre_Install_Required_Components',
             'Pre_Install_Python_Environment', 'Pre_Install_Get_Panel_Source',
             'Pre_Install_System_Tweak', 'Main_Installation', 'Post_Install_Required_Components',
             'Post_Install_PHP_Session_Setup', 'Post_Install_PHP_TimezoneDB',
             'Post_Install_Regenerate_Cert', 'Post_Install_Regenerate_Webadmin_Console_Passwd',
             'Post_Install_Setup_Watchdog', 'Post_Install_Setup_Utility', 'Post_Install_Tweak'],
            machine.recorded(machine.phases))

    def test_lines_have_the_agreed_form_and_one_run_name(self):
        machine = Installer(self)
        machine.run('-v', 'ols')
        lines = machine.event_lines()
        for line in lines:
            self.assertRegex(line, '^%s$' % EVENT_LINE.pattern)
        self.assertEqual(1, len({line.split()[1] for line in lines}))
        times = [int(line.split()[0]) for line in lines]
        self.assertEqual(sorted(times), times)

    def test_file_is_for_root_only(self):
        machine = Installer(self)
        os.umask(os.umask(0o022))
        machine.run('-v', 'ols')
        self.assertEqual(0o600, stat.S_IMODE(machine.events_file.stat().st_mode))

    def test_components_left_out_are_skipped(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', python_steps='step:php step:database skip:ftp skip:dns '
                                                          'skip:email step:panel finish')
        self.assertEqual(0, result.returncode, result.stderr)
        events = machine.events()
        for name in ('ftp', 'dns', 'email'):
            self.assertIn(name + ' skipped', events)
            self.assertNotIn(name + ' running', events)
        self.assertEqual('install complete', events[-1])
        self.assertEqual([step for step in STEPS if step not in ('ftp', 'dns', 'email')],
                         [event.split()[0] for event in events if event.endswith(' running')])

    def test_a_second_run_is_added_below_the_first(self):
        machine = Installer(self)
        machine.run('-v', 'ols')
        first = machine.event_lines()
        machine.run('-v', 'ols')
        lines = machine.event_lines()
        self.assertEqual(first, lines[:len(first)])
        self.assertEqual(COMPLETE_RUN, [' '.join(line.split()[2:]) for line in lines[len(first):]])
        self.assertNotEqual(first[0].split()[1], lines[-1].split()[1])

    def test_progress_log_lines_are_what_they_were(self):
        machine = Installer(self)
        machine.run('-v', 'ols')
        self.assertEqual(['Starting installation..,1', 'Initialization completed..,2', 'Completed [200]'],
                         [line for line in machine.install_log.read_text().splitlines() if line])


class FailedRunTests(unittest.TestCase):
    def failed(self, *arguments, status=1, reason, step='preflight', machine=None, **options):
        machine = machine or Installer(self)
        result = machine.run(*(arguments or ('-v', 'ols')), **options)
        self.assertEqual(status, result.returncode, result.stdout + result.stderr)
        self.assertEqual(up_to(step) + ['%s failed %s' % (step, reason), 'install failed ' + reason],
                         machine.events())
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)
        return machine, result

    def test_each_step_before_the_installer_names_its_reason(self):
        for phase, step, status, reason in (
                ('Pre_Install_Setup_Repository', 'repositories', 1, 'package_manager'),
                ('Pre_Install_Required_Components', 'system_update', 1, 'package_manager'),
                ('Pre_Install_Python_Environment', 'python_env', 1, 'python_env'),
                ('Pre_Install_Get_Panel_Source', 'download_panel', 1, 'download_failed'),
                ('Pre_Install_System_Tweak', 'download_panel', 1, 'download_failed')):
            with self.subTest(phase=phase):
                self.failed(fail_at=phase, step=step, status=status, reason=reason)

    def test_installer_failure_keeps_its_status_and_names_the_step(self):
        self.failed(python_steps='exit:23', step='web_server', status=23, reason='panel_setup')
        self.failed(python_steps='step:php step:database exit:70', step='database', status=70,
                    reason='panel_setup')
        machine = Installer(self)
        result = machine.run('-v', 'ols', python_steps='step:php step:database skip:ftp skip:dns '
                                                          'step:email exit:9')
        self.assertEqual(9, result.returncode)
        self.assertEqual(['dns skipped', 'email running', 'email failed panel_setup',
                          'install failed panel_setup'], machine.events()[-4:])

    def test_installer_that_ends_without_its_completion_marker(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', fail_at='No_Completion_Marker')
        self.assertEqual(1, result.returncode)
        self.assertEqual(['panel done', 'install failed internal'], machine.events()[-2:])

    def test_each_finishing_part_fails_the_run(self):
        for phase in ('Post_Install_Required_Components', 'Post_Install_PHP_Session_Setup',
                      'Post_Install_PHP_TimezoneDB', 'Post_Install_Setup_Utility'):
            with self.subTest(phase=phase):
                self.failed(fail_at=phase, step='finishing', reason='panel_setup')

    def test_exit_without_a_status_in_the_middle_of_a_run_is_a_failure(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', python_steps='step:php exit:0', fail_at='No_Completion_Marker')
        self.assertEqual(1, result.returncode)
        self.assertEqual(['php failed panel_setup', 'install failed panel_setup'], machine.events()[-2:])
        # The same for a line that ends the script with status 0 outright.
        machine = Installer(self)
        harness = machine.harness()
        self.assertEqual(1, harness.count('Pre_Install_System_Tweak() { phase'))
        harness = harness.replace('Pre_Install_System_Tweak() { phase',
                                  'Pre_Install_System_Tweak() { exit 0; phase')
        with patch.object(machine, 'harness', return_value=harness):
            result = machine.run('-v', 'ols')
        self.assertEqual(1, result.returncode)
        self.assertEqual(['download_panel failed download_failed', 'install failed download_failed'],
                         machine.events()[-2:])

    def test_panel_that_does_not_answer(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', panel_exit=7)
        self.assertEqual(1, result.returncode)
        self.assertEqual(['hostname_ssl done', 'ready running', 'ready failed panel_setup',
                          'install failed panel_setup'], machine.events()[-4:])
        self.assertNotIn('panel ready', machine.events())
        self.assertIn('does not answer on port 8090', result.stdout)
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)

    def test_ending_by_a_signal_is_recorded(self):
        machine = Installer(self)
        harness = machine.harness()
        self.assertEqual(1, harness.count('Pre_Install_Python_Environment() { phase'))
        harness = harness.replace('Pre_Install_Python_Environment() { phase',
                                  'Pre_Install_Python_Environment() { kill -TERM $$; phase')
        with patch.object(machine, 'harness', return_value=harness):
            result = machine.run('-v', 'ols')
        self.assertEqual(-signal.SIGTERM, result.returncode)
        self.assertEqual(['python_env failed python_env', 'install failed python_env'], machine.events()[-2:])


if __name__ == '__main__':
    unittest.main()
