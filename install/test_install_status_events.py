"""Status events and exit statuses of cyberpanel.sh.

Every test runs the real top level of the script in a temporary machine
(installer_test_harness), with what would install or configure replaced.
"""
import os
import re
import shutil
import signal
import socket
import stat
import subprocess
import time
import unittest
from unittest.mock import patch

from install.installer_test_harness import (
    CLI_FAILED, DEBIAN_12, REAL_FUNCTIONS, ROOT, SPECIAL_STUBS, STUBBED_PHASES,
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
    if name == 'hostname_ssl':
        COMPLETE_RUN += ['hostname_ssl running', 'hostname_ssl skipped']
    elif name == 'ready':
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
        self.assertIn('curl --silent --fail --insecure --noproxy * --max-time 15 --output /dev/null '
                      'https://127.0.0.1:8090/', machine.recorded(machine.calls))
        self.assertIn('Waiting for the panel to answer on port 8090 (3 minutes at most)...', result.stdout)
        self.assertEqual(
            ['Pre_Install_Setup_Repository', 'Pre_Install_Required_Components',
             'Pre_Install_Python_Environment', 'Pre_Install_Get_Panel_Source',
             'Pre_Install_System_Tweak', 'Main_Installation', 'Post_Install_Required_Components',
             'Post_Install_PHP_Session_Setup', 'Post_Install_PHP_TimezoneDB',
             'Post_Install_Regenerate_Cert', 'Post_Install_Start_Web_Terminal',
             'Post_Install_Regenerate_Webadmin_Console_Passwd',
             'Post_Install_Setup_Watchdog', 'Post_Install_Setup_Utility', 'Post_Install_Tweak'],
            machine.recorded(machine.phases))

    def test_a_web_terminal_that_does_not_start_is_no_failure_of_the_installation(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', fail_at='Post_Install_Start_Web_Terminal')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(COMPLETE_RUN, machine.events())
        self.assertIn('Post_Install_Start_Web_Terminal', machine.recorded(machine.phases))
        self.assertIn('CyberPanel Successfully Installed', result.stdout)

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

    def test_issued_hostname_certificate_is_a_finished_step(self):
        machine = Installer(self)
        machine.path('/usr/local/lsws/lsphp83/bin').mkdir(parents=True)
        runtime = machine.path('/usr/local/lsws/lsphp83/bin/lsphp')
        runtime.write_text('#!/bin/sh\n')
        runtime.chmod(0o755)
        result = machine.run('-v', 'ols', dns=True)
        self.assertEqual(0, result.returncode, result.stderr)
        events = machine.events()
        self.assertIn('hostname_ssl done', events)
        self.assertNotIn('hostname_ssl skipped', events)
        self.assertEqual(['cyberpanel createWebsite', 'cyberpanel hostNameSSL'],
                         [' '.join(call.split()[:2]) for call in machine.recorded(machine.calls)
                          if call.startswith('cyberpanel ')])

    def test_a_second_run_is_added_below_the_first(self):
        machine = Installer(self)
        machine.run('-v', 'ols')
        first = machine.event_lines()
        # The panel is there now, so the second run is refused; its lines follow
        # the first run's, which stay as they were.
        result = machine.run('-v', 'ols')
        self.assertEqual(1, result.returncode)
        lines = machine.event_lines()
        self.assertEqual(first, lines[:len(first)])
        self.assertEqual(['install started 3.0.11', 'preflight running', 'preflight failed already_installed',
                          'install failed already_installed'],
                         [' '.join(line.split()[2:]) for line in lines[len(first):]])
        self.assertNotEqual(first[0].split()[1], lines[-1].split()[1])

    def test_progress_log_lines_are_what_they_were(self):
        machine = Installer(self)
        machine.run('-v', 'ols')
        self.assertEqual(['Starting installation..,1', 'Initialization completed..,2', 'Completed [200]'],
                         [line for line in machine.install_log.read_text().splitlines() if line])


class NoRunTests(unittest.TestCase):
    """Help and a command line that cannot be read touch nothing."""

    def assert_untouched(self, machine):
        self.assertEqual([], machine.event_lines())
        self.assertEqual([], machine.recorded(machine.calls))
        self.assertEqual([], machine.recorded(machine.phases))
        self.assertFalse(machine.install_log.exists())

    def test_help_ends_with_status_zero_before_anything_is_checked(self):
        for arguments in (['help'], ['-h'], ['--help'], ['-v', 'ols', '--help'], ['-m', '-h']):
            with self.subTest(arguments=arguments):
                machine = Installer(self)
                result = machine.run(*arguments)
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertIn('CyberPanel Installer Script Help', result.stdout)
                self.assert_untouched(machine)

    def test_unreadable_command_line_ends_with_status_two(self):
        for arguments in (['--frobnicate'], ['-v', 'ols', 'extra'], ['-v'], ['-v', 'ols', '-x'],
                          ['-m', 'nginx']):
            with self.subTest(arguments=arguments):
                machine = Installer(self)
                result = machine.run(*arguments)
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn('CyberPanel Installer Script Help', result.stdout)
                self.assert_untouched(machine)

    def test_value_that_cannot_be_used_ends_with_status_two_before_anything_is_touched(self):
        # Before this was checked up front, a running Apache had been stopped and
        # masked by the time the value was looked at.
        for arguments, said in (
                (['-v', 'ols', '-p', 'short'], 'Password length less than 8'),
                (['-v', 'ols', '-b', 'junk'], 'Please input a valid format version number.'),
                (['-v', 'ols', '-b', '1.0.0'], 'You must use version number higher than 1.9.4'),
                (['-v', 'ols', '-b'], 'Please input a valid format version number.'),
                (['-v', 'not-a-license-key'], 'License key seems incorrect'),
                (['-b', '2.4.4', '-a', '-v', 'ABCD-EFGH-IJKL'], 'License key seems incorrect')):
            with self.subTest(arguments=arguments):
                machine = Installer(self)
                result = machine.run(*arguments, active_service='apache2')
                self.assertEqual(2, result.returncode, result.stdout + result.stderr)
                self.assertIn(said, result.stdout)
                self.assert_untouched(machine)

    def test_usage_check_and_argument_reader_agree(self):
        functions, _ = script_parts()
        reader = functions[functions.index('\nCheck_Usage() {'):functions.index('\nArgument_Mode() {')]
        helpers = ''.join(
            re.search(r'^%s\(\) \{\n.*?^\}\n' % name, functions, re.M | re.S).group(0)
            for name in ('Fail_Install', 'Leave_Install', 'Branch_Problem', 'License_Problem',
                         'Password_Problem', 'Branch_Check', 'Named_Components')
            if re.search(r'^%s\(\) \{' % name, functions, re.M))
        cases = {
            (): (0, 0), ('--debug',): (0, 0), ('default',): (0, 0), ('default', 'junk'): (0, 0),
            ('-v', 'ols'): (0, 0), ('--version', 'OLS', '--addons', '--mirror'): (0, 0),
            ('-v', 'ols', '-p', 'r'): (0, 0), ('-v', 'ols', '-p'): (0, 0),
            ('-v', 'ols', '-m', 'postfix', 'powerdns'): (0, 0),
            ('-v', 'ols', '-b', '2.4.4'): (0, 0), ('-b', ' 3.0.12 ', '-v', 'ols'): (0, 0),
            ('-v', 'ols', '-p', '12345678'): (0, 0), ('-v', 'ols', '-p', 'd'): (0, 0),
            ('-v', 'ols', '-p', 'random', '-a'): (0, 0),
            # The licence key is used by Argument_Mode, after the reader.
            ('-v', 'ABCD-EFGH-IJKL-MNOP'): (0, 0), ('-v', 'trial'): (0, 0), ('-v', 'TRIAL', '-a'): (0, 0),
            ('help',): ('help', 0), ('-h',): ('help', 0), ('-a', '--help'): ('help', 0),
            ('-v',): (2, 2), ('-x',): (2, 2), ('-v', 'ols', 'what'): (2, 2),
            # A value that cannot be used ends both, the check first.
            ('-v', 'ols', '-p', 'short'): (2, 2), ('-v', 'ols', '-b', 'junk'): (2, 2),
            ('-v', 'ols', '-b', '1.0.0'): (2, 2), ('-v', 'ols', '-b', '1.9.3'): (2, 2),
            ('-v', 'ols', '-b'): (2, 2),
            ('-v', 'not-a-license-key'): (2, 0), ('-v', 'ABCD-EFGH-IJKL'): (2, 0),
            ('-v', 'ABCD-EFGH-IJKL-MNOPQ'): (2, 0), ('-v', 'ABCDEFGHIJKLMNOPQRS'): (2, 0),
        }
        for arguments, (usage, reading) in cases.items():
            with self.subTest(arguments=arguments):
                script = ('Show_Help() { echo HELP; }\nlog_function_start() { :; }\nDebug_Log2() { :; }\n'
                          'Base_Number="1.9.3"\nAdmin_Pass_From_File=""\n'
                          'trap \'echo "REASON=$Install_Fail_Code"\' EXIT\n'
                          + helpers + reader)
                outcomes = []
                for function in ('Check_Usage', 'Check_Argument'):
                    result = subprocess.run(['bash', '-c', script + '\n%s "$@"\necho CONTINUES\n' % function,
                                             'bash'] + list(arguments),
                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                            universal_newlines=True, timeout=20)
                    self.assertEqual('', result.stderr)
                    if 'HELP' in result.stdout and result.returncode == 0:
                        self.assertNotIn('CONTINUES', result.stdout)
                        outcomes.append('help')
                    else:
                        self.assertEqual(result.returncode == 0, 'CONTINUES' in result.stdout)
                        outcomes.append(result.returncode)
                self.assertEqual(usage, outcomes[0])
                self.assertEqual('help' if usage == 'help' else reading, outcomes[1])


class FailedRunTests(unittest.TestCase):
    def failed(self, *arguments, status=1, reason, step='preflight', machine=None, **options):
        machine = machine or Installer(self)
        result = machine.run(*(arguments or ('-v', 'ols')), **options)
        self.assertEqual(status, result.returncode, result.stdout + result.stderr)
        self.assertEqual(up_to(step) + ['%s failed %s' % (step, reason), 'install failed ' + reason],
                         machine.events())
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)
        return machine, result

    def test_version_pointer_cannot_be_read(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', version='<html>busy</html>')
        self.assertEqual(1, result.returncode)
        self.assertEqual(['install started unknown', 'preflight running',
                          'preflight failed download_failed', 'install failed download_failed'],
                         machine.events())

    def test_not_root(self):
        self.failed(uid=1000, reason='not_root')
        self.failed(environment={'SUDO_USER': 'someone'}, reason='not_root')

    def test_no_public_address_is_reported_where_it_can_be_read(self):
        _, result = self.failed(ip='', reason='no_public_ip')
        self.assertIn('Can not detect IP', result.stdout)

    def test_unsupported_operating_system(self):
        machine = Installer(self)
        machine.os_release(DEBIAN_12)
        self.failed(machine=machine, reason='unsupported_os')
        machine = Installer(self)
        (machine.root / 'etc/os-release').unlink()
        self.failed(machine=machine, reason='unsupported_os')
        self.failed(environment={'XDG_CURRENT_DESKTOP': 'GNOME'}, reason='unsupported_os')

    def test_another_panel(self):
        for directory in ('/usr/local/cpanel', '/usr/local/directadmin', '/etc/apache2/plesk.conf.d',
                          '/usr/local/panel'):
            with self.subTest(directory=directory):
                machine = Installer(self)
                machine.path(directory).mkdir(parents=True)
                self.failed(machine=machine, reason='other_panel', active_service='apache2')
                self.assertEqual([], [call for call in machine.recorded(machine.calls)
                                      if call.startswith('systemctl')])

    def test_already_installed_is_found_before_a_service_is_stopped(self):
        machine = Installer(self)
        machine.path('/usr/local/CyberCP').mkdir(parents=True)
        _, result = self.failed(machine=machine, reason='already_installed', active_service='apache2')
        self.assertIn('CyberPanel already installed', result.stdout)
        self.assertEqual([], [call for call in machine.recorded(machine.calls)
                              if call.startswith('systemctl')])
        self.assertEqual([], machine.recorded(machine.phases))

    def test_a_running_web_server_is_still_stopped_on_a_fresh_server(self):
        machine = Installer(self)
        machine.run('-v', 'ols', active_service='apache2')
        self.assertEqual(['systemctl stop apache2', 'systemctl disable apache2', 'systemctl mask apache2'],
                         [call for call in machine.recorded(machine.calls)
                          if call.startswith('systemctl') and 'is-active' not in call])

    def test_answer_that_cannot_be_used(self):
        # Install, OpenLiteSpeed, full service, local MySQL, then the version question.
        _, result = self.failed('--debug', stdin='1\n1\n\n\njunk\n', status=2, reason='invalid_input')
        self.assertIn('Please input a valid format version number.', result.stdout)
        # LiteSpeed Enterprise with a serial number that is none.
        _, result = self.failed('--debug', stdin='1\n2\nnot-a-key\ny\n', status=2, reason='invalid_input')
        self.assertIn('License key seems incorrect', result.stdout)

    def test_wrong_answer_at_the_menu(self):
        self.failed('--debug', stdin='7\n', reason='invalid_input')

    def test_leaving_at_the_menu_is_not_an_error_and_not_an_installation(self):
        machine = Installer(self)
        result = machine.run('--debug', stdin='2\n')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['install started 3.0.11', 'preflight running', 'preflight failed cancelled',
                          'install failed cancelled'], machine.events())
        self.assertEqual([], machine.recorded(machine.phases))

    def test_each_step_before_the_installer_names_its_reason(self):
        for phase, step, status, reason in (
                ('Pre_Install_Setup_Repository', 'repositories', 1, 'package_manager'),
                ('Pre_Install_Required_Components', 'system_update', 1, 'package_manager'),
                ('Pre_Install_Python_Environment', 'python_env', 1, 'python_env'),
                ('Pre_Install_Get_Panel_Source', 'download_panel', 1, 'download_failed'),
                ('Pre_Install_System_Tweak', 'download_panel', 1, 'download_failed')):
            with self.subTest(phase=phase):
                self.failed(fail_at=phase, step=step, status=status, reason=reason)

    def test_command_that_fails_fifty_times_is_a_failed_run_like_any_other(self):
        # It used to end the script with status 2, which is what a command line
        # that cannot be read ends with.
        machine = Installer(self)
        harness = machine.harness()
        self.assertEqual(1, harness.count('Pre_Install_Get_Panel_Source() { phase'))
        harness = harness.replace('Pre_Install_Get_Panel_Source() { phase',
                                  'Pre_Install_Get_Panel_Source() { Retry_Command "note attempt; false"; phase')
        with patch.object(machine, 'harness', return_value=harness):
            result = machine.run('-v', 'ols')
        self.assertEqual(1, result.returncode, result.stderr)
        self.assertEqual(49, machine.recorded(machine.calls).count('attempt'))
        self.assertEqual(up_to('download_panel') + ['download_panel failed download_failed',
                                                    'install failed download_failed'], machine.events())
        self.assertIn('failed for 50 times', result.stdout)

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
        self.assertEqual(['hostname_ssl skipped', 'ready running', 'ready failed panel_setup',
                          'install failed panel_setup'], machine.events()[-4:])
        self.assertNotIn('panel ready', machine.events())
        self.assertIn('did not answer on port 8090 within 3 minutes', result.stdout)
        self.assertIn('Check it with: systemctl status lscpd\nPanel username: admin\n'
                      'Panel password: stored in %s\n' % machine.stored_password, result.stdout)
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)

    def probe_limits(self, machine):
        return [int(call.split('--max-time ')[1].split()[0])
                for call in machine.recorded(machine.calls) if '127.0.0.1:8090' in call]

    def test_wait_for_the_panel_ends_after_three_minutes_whatever_the_requests_do(self):
        # The harness's clock is the script's SECONDS: waiting moves it on, and
        # so does real time, by a second or two over a run. Hence the ranges.
        # Refused at once: asked every two seconds, 180 seconds long.
        machine = Installer(self)
        result = machine.run('-v', 'ols', panel_exit=7)
        self.assertEqual(1, result.returncode)
        limits = self.probe_limits(machine)
        self.assertIn(len(limits), range(85, 91))
        self.assertEqual([15] * 78, limits[:78])
        self.assertLessEqual(limits[-1], 3)
        # No answer at all: every request lasts as long as it may, and the last
        # one is given only what is left of the three minutes.
        machine = Installer(self)
        result = machine.run('-v', 'ols', panel_exit=28, panel_hangs=True)
        self.assertEqual(1, result.returncode)
        limits = self.probe_limits(machine)
        self.assertEqual([15] * 10, limits[:10])
        self.assertEqual(11, len(limits))
        self.assertLess(limits[-1], 15)
        self.assertIn(sum(limits) + 2 * (len(limits) - 1), range(175, 181))
        self.assertEqual(['ready failed panel_setup', 'install failed panel_setup'], machine.events()[-2:])

    def test_panel_that_answers_late_is_a_complete_installation(self):
        machine = Installer(self)
        harness = machine.harness()
        refused = '      return "$QA_PANEL_EXIT"\n'
        self.assertEqual(1, harness.count(refused))
        # Refused for the first two minutes, then answered.
        harness = harness.replace(refused, '      if (( SECONDS < 120 )); then return 7; fi\n      return 0\n')
        with patch.object(machine, 'harness', return_value=harness):
            result = machine.run('-v', 'ols')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(COMPLETE_RUN, machine.events())
        self.assertGreater(len(self.probe_limits(machine)), 50)

    def test_ending_by_a_signal_is_recorded_as_interrupted_and_keeps_the_signal(self):
        for name in ('TERM', 'INT', 'HUP'):
            with self.subTest(signal=name):
                machine = Installer(self)
                harness = machine.harness()
                self.assertEqual(1, harness.count('Pre_Install_Python_Environment() { phase'))
                harness = harness.replace('Pre_Install_Python_Environment() { phase',
                                          'Pre_Install_Python_Environment() { kill -%s $$; phase' % name)
                with patch.object(machine, 'harness', return_value=harness):
                    result = machine.run('-v', 'ols')
                self.assertEqual(-getattr(signal, 'SIG' + name), result.returncode)
                self.assertEqual(up_to('python_env') + ['python_env failed interrupted', 'install failed interrupted'],
                                 machine.events())
                # The step in which the signal came was not gone on with.
                self.assertNotIn('Pre_Install_Get_Panel_Source', machine.recorded(machine.phases))

    def test_ctrl_c_at_the_menu_is_an_interrupted_run(self):
        machine = Installer(self)
        process = machine.start('--debug')
        try:
            shown = ''
            while '2. Exit.' not in shown:
                line = process.stdout.readline()
                self.assertNotEqual('', line, 'the menu was not shown: ' + shown)
                shown += line
            process.send_signal(signal.SIGINT)
            process.communicate(timeout=60)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()
        self.assertEqual(-signal.SIGINT, process.returncode)
        self.assertEqual(['install started 3.0.11', 'preflight running', 'preflight failed interrupted',
                          'install failed interrupted'], machine.events())


class HostnameCertificateTests(unittest.TestCase):
    def machine(self):
        machine = Installer(self)
        machine.path('/usr/local/lsws/lsphp83/bin').mkdir(parents=True)
        runtime = machine.path('/usr/local/lsws/lsphp83/bin/lsphp')
        runtime.write_text('#!/bin/sh\n')
        runtime.chmod(0o755)
        return machine

    def test_failed_certificate_is_a_warning_on_a_panel_that_is_ready(self):
        machine = self.machine()
        result = machine.run('-v', 'ols', '-p', 'Hunter2-secret', dns=True, tls_output=CLI_FAILED)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(up_to('hostname_ssl') + ['hostname_ssl warning hostname_ssl', 'panel ready',
                                                  'install failed hostname_ssl'], machine.events())
        self.assertIn('Hostname SSL', result.stderr)
        self.assertIn('Visit: https://192.0.2.10:8090', result.stdout)
        self.assertIn('Panel username: admin', result.stdout)
        self.assertIn('stored in %s' % machine.path('/etc/cyberpanel/adminPass'), result.stdout)
        after_notice = result.stdout.split('could not be issued', 1)[1]
        self.assertNotIn('Hunter2-secret', after_notice)
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)

    def test_failed_certificate_on_a_panel_that_does_not_answer(self):
        machine = self.machine()
        result = machine.run('-v', 'ols', dns=True, tls_output=CLI_FAILED, panel_exit=7)
        self.assertEqual(1, result.returncode)
        self.assertEqual(['hostname_ssl warning hostname_ssl', 'install failed hostname_ssl'],
                         machine.events()[-2:])

    def test_signal_during_the_certificate_request_is_an_interrupted_run_and_nothing_else(self):
        # No notice about a certificate (the request had not failed), the panel
        # is not asked for the password and gets no request.
        machine = self.machine()
        result = machine.run('-v', 'ols', dns=True, tls_signal='TERM')
        self.assertEqual(-signal.SIGTERM, result.returncode)
        self.assertEqual(up_to('hostname_ssl') + ['hostname_ssl failed interrupted', 'install failed interrupted'],
                         machine.events())
        self.assertNotIn('Visit: https://', result.stdout)
        self.assertNotIn('could not be issued', result.stdout)
        calls = machine.recorded(machine.calls)
        self.assertEqual([], [call for call in calls if '127.0.0.1:8090' in call or call == 'password-check'])

    def test_certificate_counts_as_failed_only_once_its_request_has_failed(self):
        machine = self.machine()
        machine.run('-v', 'ols', dns=True, tls_output=CLI_FAILED)
        self.assertIn('result-during-the-certificate-request=failed', machine.recorded(machine.calls))
        self.assertIn('hostname_ssl warning hostname_ssl', machine.events())

    def test_notice_about_the_certificate_does_not_need_the_events_file(self):
        # A directory where the file belongs: nothing can be written or read there.
        machine = self.machine()
        machine.events_file.parent.mkdir(parents=True)
        machine.events_file.mkdir()
        result = machine.run('-v', 'ols', dns=True, tls_output=CLI_FAILED)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertIn('a certificate for the hostname of this server could not be issued', result.stdout)
        self.assertIn('Visit: https://192.0.2.10:8090', result.stdout)
        self.assertTrue(machine.events_file.is_dir())
        # A run that completes is not troubled by it either.
        machine = Installer(self)
        machine.events_file.parent.mkdir(parents=True)
        machine.events_file.mkdir()
        result = machine.run('-v', 'ols')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertIn('CyberPanel Successfully Installed', result.stdout)
        # A failure is still one, with the status it had, when it cannot be recorded.
        machine = Installer(self)
        machine.events_file.parent.mkdir(parents=True)
        machine.events_file.mkdir()
        self.assertEqual(1, machine.run('-v', 'ols', fail_at='Pre_Install_Python_Environment').returncode)

    def test_website_that_could_not_be_created_is_a_failure_without_access_details(self):
        machine = self.machine()
        result = machine.run('-v', 'ols', dns=True, create_output=CLI_FAILED)
        self.assertEqual(1, result.returncode)
        self.assertEqual(up_to('hostname_ssl') + ['hostname_ssl failed panel_setup', 'panel ready',
                                                  'install failed panel_setup'], machine.events())
        self.assertNotIn('Visit: https://', result.stdout)

    def test_no_runtime_for_the_hostname_website_is_a_failure(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', dns=True, panel_exit=7)
        self.assertEqual(1, result.returncode)
        self.assertEqual(['hostname_ssl failed panel_setup', 'install failed panel_setup'],
                         machine.events()[-2:])


@unittest.skipUnless(shutil.which('curl'), 'curl is needed')
class ReadinessProbeTests(unittest.TestCase):
    """Panel_Answers as it is, with the real curl."""

    def setUp(self):
        functions, _ = script_parts()
        start = functions.index('\nPanel_Answers() {\n') + 1
        self.function = functions[start:functions.index('\n}\n', start) + 3]
        # Stands in for a proxy: it only lets itself be connected to.
        self.proxy = socket.socket()
        self.addCleanup(self.proxy.close)
        self.proxy.bind(('127.0.0.1', 0))
        self.proxy.listen(8)
        self.proxy.settimeout(0.3)
        # A port of this machine on which nothing listens.
        unused = socket.socket()
        unused.bind(('127.0.0.1', 0))
        self.port = unused.getsockname()[1]
        unused.close()

    def asked_of_the_proxy(self):
        count = 0
        while True:
            try:
                connection, _ = self.proxy.accept()
            except socket.timeout:
                return count
            connection.close()
            count += 1

    def probe(self, function, seconds):
        address = 'https://127.0.0.1:8090/'
        self.assertEqual(1, function.count(address))
        environment = {'PATH': os.environ['PATH']}
        for name in ('http_proxy', 'https_proxy', 'HTTPS_PROXY', 'all_proxy', 'ALL_PROXY'):
            environment[name] = 'http://127.0.0.1:%d' % self.proxy.getsockname()[1]
        script = function.replace(address, 'https://127.0.0.1:%d/' % self.port) + '\nPanel_Answers %d\n' % seconds
        return subprocess.run(['bash', '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, env=environment, timeout=120)

    def test_proxy_named_in_the_environment_is_not_asked(self):
        result = self.probe(self.function, 1)
        self.assertEqual((1, '', ''), (result.returncode, result.stdout, result.stderr))
        self.assertEqual(0, self.asked_of_the_proxy())
        # The same request without the option goes to the proxy: this test would see it.
        option = " --noproxy '*'"
        self.assertEqual(1, self.function.count(option))
        self.probe(self.function.replace(option, ''), 1)
        self.assertGreater(self.asked_of_the_proxy(), 0)

    def test_wait_ends_when_its_time_is_over(self):
        started = time.time()
        result = self.probe(self.function, 3)
        waited = time.time() - started
        self.assertEqual(1, result.returncode)
        self.assertGreater(waited, 2)
        self.assertLess(waited, 12)


if __name__ == '__main__':
    unittest.main()
