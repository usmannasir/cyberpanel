"""The admin password given in a file stays out of sight, and -p out of the logs."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import shutil
import signal
import stat
import string
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from install.installer_test_harness import (
    CLI_FAILED, ROOT, STUBBED_PHASES, Installer, parse_as_python_36, script_parts, stand_in_interpreter,
    with_stand_ins,
)

SECRET = 'Tr0ub4dor&3 -e \\n $HOME `id` "quoted"'
# What is done to the panel's service: held when install.py has returned, and
# enabled and started once the panel has confirmed the admin password.
HELD = ['systemctl disable lscpd', 'systemctl stop lscpd']
COMPLETING = HELD + ['password-check', 'systemctl enable lscpd', 'systemctl restart lscpd']
# A run that reaches its end also asks whether the panel starts at boot.
COMPLETE_RUN = COMPLETING + ['systemctl is-enabled lscpd']
AS_ROOT = unittest.skipUnless(os.geteuid() == 0, 'a file owned by root is needed')


def function(name):
    functions, _ = script_parts()
    start = functions.index('\n%s() {\n' % name) + 1
    return functions[start:functions.index('\n}\n', start) + 3]


def password_file(directory, content=SECRET + '\n', mode=0o600):
    path = Path(directory) / 'panel-password'
    path.write_text(content, encoding='utf-8')
    path.chmod(mode)
    return path


CANNOT_BE_READ = 'The file named in CP_ADMIN_PASSWORD_FILE cannot be read.'
NOT_A_FILE = 'CP_ADMIN_PASSWORD_FILE does not name a regular file.'
NOT_ROOT_ONLY = 'must belong to root and be readable by root only (chmod 600).'
TOO_SHORT = 'has less than 8 characters.'
TOO_LONG = 'The password in the file named in CP_ADMIN_PASSWORD_FILE has more than 1024 characters.'


class PasswordFileReaderTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name

    def read(self, path, search_path=None, seconds=20):
        script = function('Read_Admin_Password_File') + (
            'Read_Admin_Password_File\nstatus=$?\nprintf "%s" "$Admin_Pass_From_File"\n'
            'printf "%s" "$Admin_Pass_File_Problem" >&2\nexit $status\n')
        environment = {'PATH': search_path or os.environ['PATH']}
        if path is not None:
            environment['CP_ADMIN_PASSWORD_FILE'] = str(path)
        return subprocess.run(['bash', '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              encoding='utf-8', env=environment, timeout=seconds)

    def assert_refused(self, path, saying, *secrets, **options):
        result = self.read(path, **options)
        self.assertEqual(1, result.returncode)
        self.assertEqual('', result.stdout)
        self.assertIn(saying, result.stderr)
        for secret in secrets:
            self.assertNotIn(secret, result.stderr)

    def test_no_file_named_changes_nothing(self):
        for path in (None, ''):
            result = self.read(path)
            self.assertEqual((0, '', ''), (result.returncode, result.stdout, result.stderr))

    def test_file_that_is_not_there_cannot_be_read(self):
        self.assert_refused(Path(self.directory) / 'missing', CANNOT_BE_READ)
        self.assert_refused(Path(self.directory) / 'missing' / 'deeper', CANNOT_BE_READ)

    def test_directory_is_no_file(self):
        self.assert_refused(self.directory, NOT_A_FILE)

    @AS_ROOT
    def test_password_is_taken_as_it_is_written(self):
        for content in (SECRET + '\n', SECRET, SECRET + '\nsecond line\n', '  spaced out  \n'):
            with self.subTest(content=content):
                result = self.read(password_file(self.directory, content))
                self.assertEqual((0, ''), (result.returncode, result.stderr))
                self.assertEqual(content.split('\n')[0], result.stdout)

    @AS_ROOT
    def test_line_ending_of_another_system_is_no_part_of_the_password(self):
        result = self.read(password_file(self.directory, SECRET + '\r\n'))
        self.assertEqual((0, SECRET, ''), (result.returncode, result.stdout, result.stderr))
        # Seven characters and a carriage return are seven characters.
        self.assert_refused(password_file(self.directory, 'short7!\r\n'), TOO_SHORT, 'short7!')

    @AS_ROOT
    def test_modes_that_only_root_can_read_are_accepted(self):
        for mode in (0o600, 0o400):
            with self.subTest(mode=oct(mode)):
                self.assertEqual(0, self.read(password_file(self.directory, mode=mode)).returncode)

    @AS_ROOT
    def test_file_that_others_can_read_is_refused(self):
        for mode in (0o644, 0o640, 0o604, 0o660, 0o666):
            with self.subTest(mode=oct(mode)):
                self.assert_refused(password_file(self.directory, mode=mode), NOT_ROOT_ONLY, SECRET)

    @AS_ROOT
    def test_file_of_another_account_is_refused(self):
        path = password_file(self.directory)
        os.chown(str(path), 65534, 0)
        self.assert_refused(path, NOT_ROOT_ONLY, SECRET)

    @AS_ROOT
    def test_link_is_judged_by_the_file_it_leads_to(self):
        link = Path(self.directory) / 'link'
        link.symlink_to(password_file(self.directory))
        result = self.read(link)
        self.assertEqual((0, SECRET, ''), (result.returncode, result.stdout, result.stderr))
        password_file(self.directory, mode=0o644)
        self.assert_refused(link, NOT_ROOT_ONLY, SECRET)

    @AS_ROOT
    def test_short_or_empty_password_is_refused_without_being_shown(self):
        for content in ('', '\n', 'short7!\n', '\n' + SECRET + '\n'):
            with self.subTest(content=content):
                self.assert_refused(password_file(self.directory, content), TOO_SHORT, 'short7!')

    def test_name_is_followed_to_refuse_and_then_once_to_open(self):
        source = function('Read_Admin_Password_File')
        # Twice in tests that can only refuse, before anything is opened.
        refusals = source[:source.index('\n{\n')]
        self.assertEqual(2, refusals.count('"$CP_ADMIN_PASSWORD_FILE"'))
        for test in ('if [[ ! -r "$CP_ADMIN_PASSWORD_FILE" ]]; then\n  Admin_Pass_File_Problem=',
                     'if [[ ! -f "$CP_ADMIN_PASSWORD_FILE" ]]; then\n  Admin_Pass_File_Problem='):
            self.assertEqual(1, refusals.count(test))
            after = refusals[refusals.index(test):].splitlines()
            self.assertEqual(['  return 1', 'fi'], after[2:4])
        # Once in the open. What is judged and read is the opened file.
        self.assertEqual(3, source.count('$CP_ADMIN_PASSWORD_FILE'))
        closing = '\n} 2>/dev/null < "$CP_ADMIN_PASSWORD_FILE"\n'
        self.assertEqual(1, source.count(closing))
        opened = source[source.index('\n{\n'):source.index(closing)]
        self.assertIn("details=$(stat -L -c '%u %a %F' /dev/stdin)", opened)
        self.assertEqual(1, opened.count('IFS= read -r -n 1026 first_line'))
        self.assertNotIn('$CP_ADMIN_PASSWORD_FILE', opened)
        # Nothing is read before kind, owner and mode were judged.
        self.assertLess(opened.index('regular'), opened.index('IFS= read'))
        self.assertLess(opened.index('8#77'), opened.index('IFS= read'))
        self.assertEqual(1, source.count('IFS= read'))

    def test_device_without_an_end_is_refused_at_once(self):
        for device in ('/dev/zero', '/dev/urandom', '/dev/null'):
            with self.subTest(device=device):
                self.assert_refused(device, NOT_A_FILE, seconds=5)

    def test_pipe_without_a_writer_is_refused_at_once(self):
        pipe = Path(self.directory) / 'pipe'
        os.mkfifo(str(pipe), 0o600)
        self.assert_refused(pipe, NOT_A_FILE, seconds=5)
        link = Path(self.directory) / 'link-to-pipe'
        link.symlink_to(pipe)
        self.assert_refused(link, NOT_A_FILE, seconds=5)

    def test_link_that_leads_nowhere_cannot_be_read(self):
        link = Path(self.directory) / 'dangling'
        link.symlink_to(Path(self.directory) / 'missing')
        self.assert_refused(link, CANNOT_BE_READ)

    @AS_ROOT
    def test_line_without_an_end_is_not_read_whole(self):
        megabyte = 'x' * (1024 * 1024)
        self.assert_refused(password_file(self.directory, megabyte), TOO_LONG, 'xxxxxxxx', seconds=5)
        self.assert_refused(password_file(self.directory, megabyte + '\n'), TOO_LONG, 'xxxxxxxx', seconds=5)

    @AS_ROOT
    def test_longest_password_has_1024_characters(self):
        longest = 'p' * 1024
        for content in (longest, longest + '\n', longest + '\r\n', longest + '\r'):
            with self.subTest(content=content[-3:]):
                result = self.read(password_file(self.directory, content))
                self.assertEqual((0, longest, ''), (result.returncode, result.stdout, result.stderr))
        for content in (longest + 'p', longest + 'p\n', longest + 'p\r\n', longest + '\rp', longest + '\r\r\n',
                        'p\u00e4' * 513 + '\n'):
            with self.subTest(content=content[-3:]):
                self.assert_refused(password_file(self.directory, content), TOO_LONG, 'pppppppp')

    @AS_ROOT
    def test_file_that_was_opened_is_the_one_checked_and_read(self):
        # The name is a link. While the file is being checked the link is turned
        # to a file that others can read and that holds another password: the
        # checks and the password must still be those of the file that was opened.
        opened = password_file(self.directory)
        other = Path(self.directory) / 'other'
        other.write_text('another-Secret-9\n')
        other.chmod(0o644)
        link = Path(self.directory) / 'link'
        link.symlink_to(opened)
        tools = Path(self.directory) / 'tools'
        tools.mkdir()
        (tools / 'stat').write_text('#!/bin/sh\nln -sfn "%s" "%s"\nexec "%s" "$@"\n'
                                    % (other, link, shutil.which('stat')))
        (tools / 'stat').chmod(0o755)
        result = self.read(link, search_path='%s:%s' % (tools, os.environ['PATH']))
        self.assertEqual(str(other), os.readlink(str(link)))
        self.assertEqual((0, SECRET, ''), (result.returncode, result.stdout, result.stderr))


class UnusableFileWholeScriptTests(unittest.TestCase):
    """The whole script with a name that is no password file: help is still
    answered, a run is refused before it starts, and neither waits for a file
    that has no end or no writer."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.pipe = Path(directory.name) / 'pipe'
        os.mkfifo(str(self.pipe), 0o600)
        self.endless = Path(directory.name) / 'endless'
        self.endless.write_text('x' * (1024 * 1024))
        self.endless.chmod(0o600)

    def finished(self, machine, *arguments, **options):
        process = machine.start(*arguments, **options)
        try:
            output, errors = process.communicate('', timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            self.fail('the installer waited for the file')
        return process.returncode, output, errors

    def names(self):
        return ('/dev/zero', str(self.pipe), str(self.endless))

    def test_help_is_answered(self):
        for name in self.names():
            for arguments in (('--help',), ('-v', 'ols', '-h')):
                with self.subTest(name=name, arguments=arguments):
                    machine = Installer(self)
                    status, output, errors = self.finished(
                        machine, *arguments, environment={'CP_ADMIN_PASSWORD_FILE': name})
                    self.assertEqual((0, ''), (status, errors))
                    self.assertIn('will do minimal install', output)
                    self.assertEqual([], machine.events())

    def test_run_is_refused_before_it_starts(self):
        for name in self.names():
            with self.subTest(name=name):
                machine = Installer(self)
                status, output, errors = self.finished(
                    machine, '-v', 'ols', environment={'CP_ADMIN_PASSWORD_FILE': name})
                self.assertEqual(2, status)
                if name == str(self.endless) and os.geteuid() == 0:
                    self.assertIn(TOO_LONG, errors)
                elif name == str(self.endless):
                    self.assertIn(NOT_ROOT_ONLY, errors)
                else:
                    self.assertIn(NOT_A_FILE, errors)
                self.assertEqual([], machine.events())
                self.assertEqual([], machine.recorded(machine.phases))


class RootOnlyTestsAreMarkedTests(unittest.TestCase):
    """A test of the reader that makes a password file needs root: for another
    account every such file is refused for its owner, and a test that expects
    a refusal would pass without having tested what it names."""

    def test_every_reader_test_that_makes_a_password_file_is_skipped_without_root(self):
        tree = ast.parse(Path(__file__).read_text(encoding='utf-8'))
        checked = []
        for cls in tree.body:
            if not isinstance(cls, ast.ClassDef) or cls.name not in ('PasswordFileReaderTests', 'InstallationTests'):
                continue
            for method in cls.body:
                if not isinstance(method, ast.FunctionDef) or not method.name.startswith('test_'):
                    continue
                makes_file = any(isinstance(node, ast.Call) and getattr(node.func, 'id', '') == 'password_file'
                                 for node in ast.walk(method))
                marked = any(getattr(decorator, 'id', '') == 'AS_ROOT' for decorator in method.decorator_list)
                if makes_file:
                    checked.append(method.name)
                    self.assertTrue(marked, '%s.%s makes a password file and is not marked AS_ROOT'
                                    % (cls.name, method.name))
        self.assertGreater(len(checked), 8)


class MaskedArgumentTests(unittest.TestCase):
    def masked(self, *arguments):
        script = function('Mask_Arguments') + ('Mask_Arguments "$@"\n'
                                               'for argument in "${Logged_Arguments[@]}"; do printf "%s\\n" "$argument"; done\n')
        result = subprocess.run(['bash', '-c', script, 'bash'] + list(arguments), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding='utf-8', timeout=20)
        self.assertEqual('', result.stderr)
        return result.stdout.splitlines()

    def test_value_of_the_password_option_is_replaced(self):
        self.assertEqual(['-v', 'ols', '-p', '*****', '-a'], self.masked('-v', 'ols', '-p', SECRET, '-a'))
        self.assertEqual(['--password', '*****', '-v', 'ols'], self.masked('--password', 'hunter2hunter2', '-v', 'ols'))
        self.assertEqual(['-p', '*****', '-p', '*****'], self.masked('-p', 'one-secret', '-p', 'two-secret'))

    def test_other_arguments_are_kept(self):
        self.assertEqual(['-v', 'ols', '-m', 'postfix', '--debug'], self.masked('-v', 'ols', '-m', 'postfix', '--debug'))
        self.assertEqual(['-v', 'ols', '-p'], self.masked('-v', 'ols', '-p'))
        self.assertEqual([], self.masked())


class InstallationTests(unittest.TestCase):
    """Whole runs of the installer's top level (installer_test_harness)."""

    @AS_ROOT
    def test_password_from_a_file_is_in_no_output_and_no_log(self):
        for arguments in (['-v', 'ols'], ['-v', 'ols', '-p', 'another-Secret-9'], ['--debug', '-v', 'ols']):
            with self.subTest(arguments=arguments):
                machine = Installer(self)
                path = password_file(str(machine.root / 'home'))
                result = machine.run(*arguments, environment={'CP_ADMIN_PASSWORD_FILE': str(path)})
                self.assertEqual(0, result.returncode, result.stderr)
                path.unlink()
                written = machine.everything_written()
                for secret in (SECRET, 'another-Secret-9'):
                    self.assertNotIn(secret, result.stdout)
                    self.assertNotIn(secret, result.stderr)
                    self.assertNotIn(secret, written)
                self.assertIn('Admin password is read from the file named in CP_ADMIN_PASSWORD_FILE', result.stdout)
                self.assertIn('Panel password: *****', result.stdout)
                self.assertIn('CyberPanel Successfully Installed', result.stdout)
                self.assertEqual('install complete', machine.events()[-1])

    @AS_ROOT
    def test_password_from_a_file_is_used_at_the_menu_too(self):
        machine = Installer(self)
        path = password_file(str(machine.root / 'home'))
        answers = '1\n1\n\n\n\n\n\n\n\n\n'
        result = machine.run(stdin=answers, environment={'CP_ADMIN_PASSWORD_FILE': str(path)})
        self.assertEqual(0, result.returncode, result.stdout[-2000:] + result.stderr)
        path.unlink()
        self.assertNotIn(SECRET, result.stdout + result.stderr + machine.everything_written())
        self.assertIn('Panel password: *****', result.stdout)

    def test_file_that_cannot_be_used_stops_before_anything_is_touched(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', environment={'CP_ADMIN_PASSWORD_FILE': str(machine.root / 'missing')})
        self.assertEqual(2, result.returncode)
        self.assertIn('CP_ADMIN_PASSWORD_FILE', result.stderr)
        self.assertEqual([], machine.event_lines())
        self.assertEqual([], machine.recorded(machine.calls))
        self.assertEqual([], machine.recorded(machine.phases))

    def test_help_is_given_whatever_the_file_is(self):
        machine = Installer(self)
        result = machine.run('--help', environment={'CP_ADMIN_PASSWORD_FILE': str(machine.root / 'missing')})
        self.assertEqual((0, ''), (result.returncode, result.stderr))
        self.assertIn('CyberPanel Installer Script Help', result.stdout)

    @AS_ROOT
    def test_value_of_the_password_option_is_not_looked_at_when_the_file_is_used(self):
        # "short" would end the run with status 2 without the file.
        machine = Installer(self)
        path = password_file(str(machine.root / 'home'))
        result = machine.run('-v', 'ols', '-p', 'short', environment={'CP_ADMIN_PASSWORD_FILE': str(path)})
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('install complete', machine.events()[-1])
        self.assertEqual(SECRET + '\n', machine.stored_password.read_text())
        self.assertIn('The password option is not used', result.stdout)
        self.assertEqual(2, Installer(self).run('-v', 'ols', '-p', 'short').returncode)

    def test_password_on_the_command_line_is_masked_in_both_logs(self):
        for option in ('-p', '--password'):
            with self.subTest(option=option):
                machine = Installer(self)
                result = machine.run('-v', 'ols', option, 'command-Line-Secret-1', '-a')
                self.assertEqual(0, result.returncode, result.stderr)
                logs = sorted(machine.path('/var/log/cyberpanel').glob('cyberpanel_install_*.log'))
                self.assertEqual(2, len(logs))
                text = ''.join(log.read_text() for log in logs)
                self.assertNotIn('command-Line-Secret-1', text)
                self.assertNotIn('command-Line-Secret-1', machine.everything_written())
                self.assertIn('Script arguments: -v ols %s ***** -a' % option, text)
                self.assertIn('Starting: Check_Argument with args: -v ols %s ***** -a' % option, text)
                # Shown to the person who typed it, as before.
                self.assertIn('Panel password: command-Line-Secret-1', result.stdout)

    def test_help_names_the_file(self):
        machine = Installer(self)
        self.assertIn('CP_ADMIN_PASSWORD_FILE', machine.run('--help').stdout)


class PanelAccountTests(unittest.TestCase):
    """Set_Admin_Password: the password is stored for root and given to the tree's adminPass.py."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.stored = self.root / 'adminPass'
        self.tool = self.root / 'adminPass.py'
        self.python = self.root / 'python'
        self.python.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$0.arguments"\n'
                               'stat -c %a "$QA_STORED" > "$0.mode"\nexit "$QA_STATUS"\n')
        self.python.chmod(0o755)

    def set_password(self, password, tree='new', umask='022', status=0):
        if tree == 'missing':
            if self.tool.exists():
                self.tool.unlink()
        else:
            self.tool.write_text("parser.add_argument('--password', help='New Password')\n"
                                 + ("parser.add_argument('--password-file')\n" if tree == 'new' else ''))
        source = with_stand_ins(function('Set_Admin_Password'), (
            ('/etc/cyberpanel/adminPass', self.stored),
            ('/usr/local/CyberPanel/bin/python', self.python),
            ('/usr/local/CyberCP/plogical/adminPass.py', self.tool)))
        self.assertNotIn('/etc/', source)
        self.assertNotIn('/usr/local/', source)
        result = subprocess.run(['bash', '-c', 'umask %s\n%s\nSet_Admin_Password' % (umask, source)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, encoding='utf-8', timeout=20,
                                env={'PATH': os.environ['PATH'], 'Admin_Pass': password,
                                     'QA_STORED': str(self.stored), 'QA_STATUS': str(status)})
        self.assertEqual(('', ''), (result.stdout, result.stderr))
        return result.returncode, (self.root / 'python.arguments').read_text().splitlines(), \
            (self.root / 'python.mode').read_text().strip()

    def test_tree_that_can_read_a_file_never_gets_the_password_on_its_command_line(self):
        for password in (SECRET, '-eEnnEEnn', '1234567'):
            with self.subTest(password=password):
                status, arguments, mode_when_read = self.set_password(password)
                self.assertEqual(0, status)
                self.assertEqual(password + '\n', self.stored.read_text())
                self.assertEqual([str(self.tool), '--password-file', str(self.stored)], arguments)
                self.assertEqual('600', mode_when_read)
                self.assertEqual(0o600, stat.S_IMODE(self.stored.stat().st_mode))

    def test_older_tree_gets_the_password_the_way_it_takes_it(self):
        # adminPass.py of 3.0.12 and before knows --password only; given the new
        # option it ends with status 2 and sets nothing.
        # One argument, so that a password that begins with "-" is no option.
        for password in (SECRET, '-starts-with-a-dash', '--password-file'):
            with self.subTest(password=password):
                status, arguments, mode_when_read = self.set_password(password, tree='old')
                self.assertEqual(0, status)
                self.assertEqual([str(self.tool), '--password=' + password], arguments)
                self.assertEqual(password + '\n', self.stored.read_text())
                self.assertEqual('600', mode_when_read)

    def test_tool_that_is_not_there_is_called_the_old_way_and_its_failure_is_the_status(self):
        # Nothing is printed for the missing file; the interpreter's failure to
        # run it is what ends the run.
        status, arguments, _ = self.set_password(SECRET, tree='missing', status=2)
        self.assertEqual(2, status)
        self.assertEqual([str(self.tool), '--password=' + SECRET], arguments)

    def test_status_is_that_of_the_tool(self):
        for tree in ('new', 'old'):
            for status in (0, 1, 2):
                with self.subTest(tree=tree, status=status):
                    self.assertEqual(status, self.set_password(SECRET, tree=tree, status=status)[0])

    def test_stored_password_is_never_readable_by_others(self):
        self.assertEqual(1, function('Set_Admin_Password').count('umask 077'))
        _, _, mode_when_read = self.set_password(SECRET, umask='000')
        self.assertEqual('600', mode_when_read)

    def test_the_password_is_part_of_one_command_only_and_only_for_an_older_tree(self):
        source = (ROOT / 'cyberpanel.sh').read_text(encoding='utf-8')
        carrying = [line.strip() for line in source.splitlines()
                    if 'Admin_Pass' in line and re.match(r'\s*(/|python|cyberpanel |curl|wget)', line)]
        self.assertEqual(['/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py '
                          '--password="$Admin_Pass"'], carrying)
        fallback = function('Set_Admin_Password')
        self.assertLess(fallback.index("grep -q -- '--password-file'"), fallback.index('--password-file /etc'))
        self.assertLess(fallback.index('\nelse\n'), fallback.index('--password="$Admin_Pass"'))


# The password is written in ASCII, so that it can be part of a command line in any locale.
LEGACY_HASH = 'import hashlib\nprint(hashlib.sha256(b"salt" + %a.encode("utf-8")).hexdigest() + ":salt")\n'


class AdminPasswordCheckTests(unittest.TestCase):
    """Admin_Password_Is_Set: the real check, run by a stand-in for the panel's tree.

    The tree has the panel's real plogical/hashPassword.py, the same file in
    3.0.12 and now; Django, the administrator table and bcrypt are stand-ins.
    QA_DATABASE_FAILURES is the number of questions the table does not answer.
    """

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.tree = self.root / 'CyberCP'
        for package in ('django', 'loginSystem', 'plogical', 'CyberCP'):
            (self.tree / package).mkdir(parents=True)
            (self.tree / package / '__init__.py').write_text('')
        (self.tree / 'django/__init__.py').write_text('def setup():\n    pass\n')
        (self.tree / 'django/db.py').write_text(
            'import os\n\n\n'
            'class Connection:\n    def close(self):\n'
            '        with open(os.environ["QA_RECORD"], "a") as record:\n'
            '            record.write("closed\\n")\n\n\n'
            'connection = Connection()\n')
        (self.tree / 'CyberCP/settings.py').write_text('')
        (self.tree / 'bcrypt.py').write_text('')
        (self.tree / 'plogical/hashPassword.py').write_text(
            (ROOT / 'plogical/hashPassword.py').read_text(encoding='utf-8'), encoding='utf-8')
        (self.tree / 'loginSystem/models.py').write_text(
            'import json\nimport os\n\n\n'
            'class OperationalError(Exception):\n    pass\n\n\n'
            'class Row:\n    def __init__(self, password):\n        self.password = password\n\n\n'
            'class Rows(list):\n    def first(self):\n        return self[0] if self else None\n\n\n'
            'class Manager:\n    def filter(self, userName):\n'
            '        with open(os.environ["QA_RECORD"], "a") as record:\n'
            '            record.write("asked\\n")\n'
            '        with open(os.environ["QA_RECORD"]) as record:\n'
            '            asked = record.read().count("asked")\n'
            '        if asked <= int(os.environ["QA_DATABASE_FAILURES"]):\n'
            '            raise OperationalError("(2002, \\"Can\'t connect to local server\\nthrough socket\\")")\n'
            '        with open(os.environ["QA_ADMINISTRATORS"]) as source:\n'
            '            stored = json.load(source)\n'
            '        return Rows([Row(stored[userName])] if userName in stored else [])\n\n\n'
            'class Administrator:\n    objects = Manager()\n')
        self.stored = self.root / 'adminPass'
        self.administrators = self.root / 'administrators.json'
        self.record = self.root / 'record'

    def stored_hash(self, password):
        return subprocess.run([sys.executable, '-c', LEGACY_HASH % password], stdout=subprocess.PIPE,
                              encoding='utf-8', check=True).stdout.strip()

    def check(self, administrators, stored='absent', database_failures=0):
        self.administrators.write_text(json.dumps(administrators))
        if stored != 'absent':
            self.stored.write_text(stored, encoding='utf-8')
        elif self.stored.exists():
            self.stored.unlink()
        if self.record.exists():
            self.record.unlink()
        source = function('Admin_Password_Is_Set')
        self.assertNotIn('Admin_Pass"', source)
        # Asked five times, three seconds apart; the tests do not wait that long.
        self.assertEqual(1, source.count('for attempt in range(5):'))
        self.assertEqual(1, source.count('        time.sleep(3)\n'))
        source = source.replace('        time.sleep(3)\n', '        time.sleep(0.01)\n')
        # The interpreter is a file of the temporary directory: these tests are
        # also run by the panel's own interpreter, whose path the script names.
        source = with_stand_ins(source, (
            ('/usr/local/CyberPanel/bin/python', stand_in_interpreter(self.root / 'installer-python')),
            ('/usr/local/CyberCP', self.tree),
            ('/etc/cyberpanel/adminPass', self.stored)))
        self.assertNotIn('/etc/', source)
        self.assertNotIn('/usr/local/', source)
        result = subprocess.run(['bash', '-c', source + '\nAdmin_Password_Is_Set'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding='utf-8', timeout=60,
                                env={'PATH': os.environ['PATH'], 'QA_ADMINISTRATORS': str(self.administrators),
                                     'QA_RECORD': str(self.record), 'QA_DATABASE_FAILURES': str(database_failures)})
        self.assertEqual('', result.stdout)
        return result

    def recorded(self):
        return self.record.read_text().split() if self.record.exists() else []

    def assert_could_not_run(self, result, reason):
        self.assertEqual(12, result.returncode)
        self.assertEqual('The check could not run: %s\n' % reason, result.stderr)

    def test_check_runs_when_the_tests_are_run_by_the_panels_interpreter(self):
        # On a server that has a panel the tests are run by its interpreter,
        # /usr/local/CyberCP/bin/python: a path that holds the names the check
        # is given stand-ins for.
        interpreter = self.root / 'server/usr/local/CyberCP/bin/python'
        interpreter.parent.mkdir(parents=True)
        interpreter.symlink_to(sys.executable)
        with patch.object(sys, 'executable', str(interpreter)):
            result = self.check({'admin': self.stored_hash(SECRET)}, SECRET + '\n')
            self.assertEqual((0, ''), (result.returncode, result.stderr))
            self.assertEqual(11, self.check({'admin': self.stored_hash('1234567')}, SECRET + '\n').returncode)

    def test_check_is_run_by_the_interpreter_that_ran_adminpass(self):
        source = function('Admin_Password_Is_Set')
        self.assertIn("( cd /usr/local/CyberCP && /usr/local/CyberPanel/bin/python - <<'VERIFY'\n", source)
        self.assertNotIn('/usr/local/CyberCP/bin/python', source)
        self.assertIn('/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py',
                      function('Set_Admin_Password'))

    def test_administrator_with_the_stored_password(self):
        for password in (SECRET, 'p\u00e4ssw\u00f6rd-1234', '1234567', '-starts-with-a-dash'):
            for ending in ('\n', '', '\r\n'):
                with self.subTest(password=password, ending=ending):
                    result = self.check({'admin': self.stored_hash(password)}, password + ending)
                    self.assertEqual((0, ''), (result.returncode, result.stderr))
                    self.assertEqual(['asked'], self.recorded())

    def test_administrator_with_another_password(self):
        # What a panel has that created its administrator itself on a first request.
        result = self.check({'admin': self.stored_hash('1234567')}, SECRET + '\n')
        self.assertEqual((11, ''), (result.returncode, result.stderr))

    def test_no_administrator(self):
        result = self.check({}, SECRET + '\n')
        self.assertEqual((10, ''), (result.returncode, result.stderr))
        result = self.check({'someone': self.stored_hash(SECRET)}, SECRET + '\n')
        self.assertEqual((10, ''), (result.returncode, result.stderr))

    def test_nothing_stored_is_a_check_that_could_not_run(self):
        result = self.check({'admin': self.stored_hash('')}, '')
        self.assert_could_not_run(result, 'ValueError: no password is stored in %s' % self.stored)
        result = self.check({'admin': self.stored_hash(SECRET)})
        self.assertEqual(12, result.returncode)
        self.assertEqual(1, len(result.stderr.splitlines()))
        self.assertTrue(result.stderr.startswith('The check could not run: FileNotFoundError: '), result.stderr)
        self.assertEqual([], self.recorded())

    def test_tree_that_cannot_be_set_up_is_a_check_that_could_not_run(self):
        (self.tree / 'loginSystem/models.py').write_text('raise RuntimeError("fixture: no\\nsettings")\n')
        result = self.check({'admin': self.stored_hash(SECRET)}, SECRET + '\n')
        self.assert_could_not_run(result, 'RuntimeError: fixture: no settings')
        (self.tree / 'loginSystem/models.py').unlink()
        result = self.check({'admin': self.stored_hash(SECRET)}, SECRET + '\n')
        self.assertEqual(12, result.returncode)
        self.assertRegex(result.stderr, r"^The check could not run: (ModuleNotFoundError|ImportError): [^\n]+\n$")

    def test_database_that_answers_late_is_asked_again(self):
        for failures in (1, 4):
            with self.subTest(failures=failures):
                result = self.check({'admin': self.stored_hash(SECRET)}, SECRET + '\n', database_failures=failures)
                self.assertEqual((0, ''), (result.returncode, result.stderr))
                # The connection is closed after every question that failed.
                self.assertEqual(['asked', 'closed'] * failures + ['asked'], self.recorded())
        result = self.check({'admin': self.stored_hash('1234567')}, SECRET + '\n', database_failures=2)
        self.assertEqual((11, ''), (result.returncode, result.stderr))
        result = self.check({}, SECRET + '\n', database_failures=2)
        self.assertEqual((10, ''), (result.returncode, result.stderr))

    def test_database_that_does_not_answer_is_a_check_that_could_not_run(self):
        result = self.check({'admin': self.stored_hash(SECRET)}, SECRET + '\n', database_failures=5)
        self.assert_could_not_run(
            result, "OperationalError: (2002, \"Can't connect to local server through socket\")")
        self.assertEqual(['asked', 'closed'] * 5, self.recorded())

    def test_check_is_valid_for_the_panel_interpreter_of_almalinux_8(self):
        source = function('Admin_Password_Is_Set')
        code = source[source.index("<<'VERIFY'\n") + len("<<'VERIFY'\n"):source.index('\nVERIFY\n')]
        parse_as_python_36(code)


class PasswordOutcomeTests(unittest.TestCase):
    """Whole runs: no installation ends complete with another password than the one given."""

    def probes(self, machine):
        return [call for call in machine.recorded(machine.calls) if '127.0.0.1:8090' in call]

    def assert_panel_held(self, machine, result, checked):
        # Left running or enabled, it would let anyone in: see Hold_Panel. Held
        # when install.py had returned, and again by the end of the run.
        self.assertEqual(HELD + (['password-check'] if checked else []) + HELD, machine.panel_service_calls())
        self.assertIn('The panel is stopped and is not started when the server boots', result.stdout)
        self.assertIn("starts the panel and makes it start at boot: adminPass 'a new password'", result.stdout)
        # Said once, where the reason is known.
        self.assertNotIn('will not start by itself', result.stdout)

    def test_tree_that_can_read_a_file_gets_the_file(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', '-p', 'Typed-Secret-99')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('install complete', machine.events()[-1])
        call = machine.recorded(machine.adminpass_call)
        self.assertEqual([str(machine.path('/usr/local/CyberCP/plogical/adminPass.py')), '--password-file',
                          str(machine.stored_password)], call)
        self.assertEqual('Typed-Secret-99\n', machine.stored_password.read_text())
        self.assertEqual(0o600, stat.S_IMODE(machine.stored_password.stat().st_mode))
        self.assertEqual(COMPLETE_RUN, machine.panel_service_calls())

    def test_older_tree_gets_the_password_and_the_run_completes(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', '-p', 'Typed-Secret-99', tree='old')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('install complete', machine.events()[-1])
        self.assertEqual([str(machine.path('/usr/local/CyberCP/plogical/adminPass.py')),
                          '--password=Typed-Secret-99'], machine.recorded(machine.adminpass_call))

    def test_the_panel_is_asked_for_the_password_before_it_gets_its_first_request(self):
        machine = Installer(self)
        machine.run('-v', 'ols')
        calls = machine.recorded(machine.calls)
        self.assertEqual(1, calls.count('password-check'))
        self.assertEqual(1, len(self.probes(machine)))
        self.assertLess(calls.index('password-check'), calls.index(self.probes(machine)[0]))
        check = machine.password_check.read_text()
        self.assertIn('hashPassword.check_password(admin.password, password)', check)
        self.assertIn(str(machine.stored_password), check)

    def test_password_that_could_not_be_set_fails_the_run(self):
        # Status 2 is what an adminPass.py answers that does not know an option.
        for tree, status in (('new', 2), ('old', 2), ('new', 1)):
            with self.subTest(tree=tree, status=status):
                machine = Installer(self)
                result = machine.run('-v', 'ols', tree=tree, adminpass_exit=status)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                events = machine.events()
                self.assertEqual(['finishing failed panel_setup', 'install failed panel_setup'], events[-2:])
                self.assertNotIn('install complete', events)
                self.assertNotIn('panel ready', events)
                self.assertEqual([], self.probes(machine))
                self.assertIn('The admin password could not be set in the panel', result.stdout)
                self.assertNotIn('CyberPanel Successfully Installed', result.stdout)
                self.assert_panel_held(machine, result, checked=False)

    WRONG = 'CyberPanel was installed, but its administrator does not have the password of this installation.'
    UNCHECKED = ('CyberPanel was installed, but it could not be checked that its administrator has the password '
                 'of this installation.')

    def test_administrator_without_the_given_password_fails_the_run(self):
        # 10: no administrator, 11: another password. Everything else, also a
        # status the check does not give itself, is a check that could not run.
        for status, said, unsaid in ((10, self.WRONG, self.UNCHECKED), (11, self.WRONG, self.UNCHECKED),
                                     (12, self.UNCHECKED, self.WRONG), (1, self.UNCHECKED, self.WRONG),
                                     (127, self.UNCHECKED, self.WRONG)):
            with self.subTest(status=status):
                machine = Installer(self)
                result = machine.run('-v', 'ols', dns=True, password_check_exit=status)
                self.assertEqual(1, result.returncode, result.stdout + result.stderr)
                events = machine.events()
                # Found right after the password was set: the hostname step is not reached.
                self.assertEqual(['finishing failed panel_setup', 'install failed panel_setup'], events[-2:])
                self.assertNotIn('install complete', events)
                self.assertNotIn('panel ready', events)
                self.assertEqual([], self.probes(machine))
                self.assertEqual([], [call for call in machine.recorded(machine.calls)
                                      if call.startswith('cyberpanel ')])
                self.assertIn(said, result.stdout)
                self.assertNotIn(unsaid, result.stdout)
                self.assertNotIn('CyberPanel Successfully Installed', result.stdout)
                self.assertNotIn('Visit: https://', result.stdout)
                self.assert_panel_held(machine, result, checked=True)

    def test_failed_certificate_with_a_confirmed_password_leaves_the_panel_running(self):
        machine = Installer(self)
        machine.path('/usr/local/lsws/lsphp83/bin').mkdir(parents=True)
        runtime = machine.path('/usr/local/lsws/lsphp83/bin/lsphp')
        runtime.write_text('#!/bin/sh\n')
        runtime.chmod(0o755)
        result = machine.run('-v', 'ols', dns=True, tls_output=CLI_FAILED)
        self.assertEqual(1, result.returncode)
        self.assertEqual(['hostname_ssl warning hostname_ssl', 'panel ready', 'install failed hostname_ssl'],
                         machine.events()[-3:])
        self.assertEqual(COMPLETING, machine.panel_service_calls())
        self.assertIn('Visit: https://', result.stdout)
        self.assertNotIn('The panel is stopped', result.stdout)

    def test_run_that_reaches_its_end_without_a_confirmed_password_fails_and_holds_the_panel(self):
        # Cannot happen as the script is; the guards are tried by taking the
        # confirmation out of it.
        machine = Installer(self)
        harness = machine.harness()
        confirmation = '  0) Panel_Password_Confirmed="Yes" ;;\n'
        # Once in the real function and once in what the harness runs of it.
        self.assertEqual(2, harness.count(confirmation))
        with patch.object(machine, 'harness', return_value=harness.replace(confirmation, '  0) : ;;\n')):
            result = machine.run('-v', 'ols')
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(['ready running', 'ready failed panel_setup', 'install failed panel_setup'],
                         machine.events()[-3:])
        self.assertEqual([], self.probes(machine))
        # Start_Panel did nothing, and the end of the run held the panel again.
        self.assertEqual(HELD + ['password-check'] + HELD, machine.panel_service_calls())
        self.assertEqual(1, result.stdout.count('The panel is stopped and will not start by itself: the installation '
                                                "ended before the panel's administrator had a confirmed password."))
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)


class PanelHoldTests(unittest.TestCase):
    """The panel's service is enabled and started only for a confirmed password.

    From the call of install.py on, a run that fails or is interrupted before
    the confirmation leaves the service disabled and stopped. A run that fails
    before install.py was called does nothing to the service: the server may
    have a panel of its own.
    """

    AFTER_THE_INSTALLER = ('Post_Install_Required_Components', 'Post_Install_PHP_Session_Setup',
                           'Post_Install_PHP_TimezoneDB', 'Post_Install_Regenerate_Cert',
                           'Post_Install_Regenerate_Webadmin_Console_Passwd', 'Post_Install_Setup_Watchdog',
                           'Post_Install_Setup_Utility')
    BEFORE_THE_INSTALLER = ('Pre_Install_Setup_Repository', 'Pre_Install_Required_Components',
                            'Pre_Install_Python_Environment', 'Pre_Install_Get_Panel_Source',
                            'Pre_Install_System_Tweak')

    def assert_held_without_a_start(self, machine, holds):
        # Held when install.py had returned, if it did, and by the end of the run.
        self.assertEqual(HELD * holds, machine.panel_service_calls())
        self.assertEqual([], [call for call in machine.recorded(machine.calls) if '127.0.0.1:8090' in call])
        self.assertNotIn('install complete', machine.events())

    def test_every_phase_is_covered(self):
        phases = [name for name in STUBBED_PHASES if name.startswith('Post_Install')]
        self.assertEqual(sorted(self.AFTER_THE_INSTALLER + ('Post_Install_Addon_Memcached', 'Post_Install_Addon_Redis',
                                                            'Post_Install_Start_Web_Terminal')), sorted(phases))
        self.assertEqual(sorted(self.BEFORE_THE_INSTALLER),
                         sorted(name for name in STUBBED_PHASES if name.startswith('Pre_Install')))

    def test_failure_after_the_installer_and_before_the_confirmation_holds_the_panel(self):
        for phase in self.AFTER_THE_INSTALLER + ('Post_Install_Addon_Memcached', 'Post_Install_Addon_Redis'):
            with self.subTest(phase=phase):
                machine = Installer(self)
                result = machine.run('-v', 'ols', '-a', fail_at=phase)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual('install failed panel_setup', machine.events()[-1])
                self.assert_held_without_a_start(machine, holds=2)
                self.assertEqual(1, result.stdout.count('The panel is stopped and will not start by itself'))

    def test_failure_inside_the_installer_holds_the_panel(self):
        for options in ({'python_steps': 'step:php step:database exit:1'}, {'fail_at': 'No_Completion_Marker'}):
            with self.subTest(options=options):
                machine = Installer(self)
                result = machine.run('-v', 'ols', **options)
                self.assertEqual(1, result.returncode)
                self.assertEqual(HELD, machine.panel_service_calls())
                self.assertEqual(1, result.stdout.count('The panel is stopped and will not start by itself'))

    def test_signal_after_the_installer_and_before_the_confirmation_holds_the_panel(self):
        for phase in ('Main_Installation',) + self.AFTER_THE_INSTALLER + ('Post_Install_Tweak',):
            for name in ('TERM', 'INT', 'HUP'):
                with self.subTest(phase=phase, signal=name):
                    machine = Installer(self)
                    result = machine.run('-v', 'ols', signal_at=phase, signal=name)
                    self.assertEqual(-getattr(signal, 'SIG' + name), result.returncode)
                    self.assertEqual('install failed interrupted', machine.events()[-1])
                    self.assert_held_without_a_start(machine, holds=1 if phase == 'Main_Installation' else 2)
                    # A run that was interrupted says nothing more.
                    self.assertNotIn('The panel is stopped', result.stdout)

    def test_failure_before_the_installer_does_not_touch_the_panel_of_the_server(self):
        cases = [{'fail_at': phase} for phase in self.BEFORE_THE_INSTALLER]
        cases += [{'uid': 1000}, {'ip': ''}, {'version': '<html>busy</html>'},
                  {'signal_at': 'Pre_Install_Required_Components'},
                  {'signal_at': 'Pre_Install_System_Tweak', 'signal': 'INT'}]
        for options in cases:
            with self.subTest(options=options):
                machine = Installer(self)
                result = machine.run('-v', 'ols', **options)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual([], machine.panel_service_calls())
                self.assertNotIn('The panel is stopped', result.stdout)

    def test_server_that_has_a_panel_keeps_its_service(self):
        machine = Installer(self)
        machine.path('/usr/local/CyberCP').mkdir(parents=True)
        result = machine.run('-v', 'ols')
        self.assertEqual(1, result.returncode)
        self.assertEqual('install failed already_installed', machine.events()[-1])
        self.assertEqual([], [call for call in machine.recorded(machine.calls) if call.startswith('systemctl')])
        self.assertNotIn('The panel is stopped', result.stdout)

    def test_completing_run_starts_the_panel_only_after_the_confirmation(self):
        for tree in ('new', 'old'):
            with self.subTest(tree=tree):
                machine = Installer(self)
                result = machine.run('-v', 'ols', tree=tree)
                self.assertEqual(0, result.returncode, result.stdout + result.stderr)
                self.assertEqual(COMPLETE_RUN, machine.panel_service_calls())
                self.assertNotIn('The panel is stopped', result.stdout)

    STOPPED_THOUGH_CONFIRMED = ('The panel is stopped and is not started when the server boots, because the '
                                'installation ended before the panel was started.')

    def test_failure_after_the_confirmation_and_before_the_start_says_how_to_start_the_panel(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', fail_at='Configure_Default_PHP_CLI')
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(['finishing failed panel_setup', 'install failed panel_setup'], machine.events()[-2:])
        # Held when install.py had returned and confirmed after that: the end
        # of the run neither starts the panel nor holds it again.
        self.assertEqual(HELD + ['password-check'], machine.panel_service_calls())
        self.assertEqual([], [call for call in machine.recorded(machine.calls) if '127.0.0.1:8090' in call])
        self.assertEqual(1, result.stdout.count(self.STOPPED_THOUGH_CONFIRMED))
        self.assertIn('Its administrator has the password of this installation. These two commands start the panel:\n'
                      'systemctl enable lscpd\nsystemctl start lscpd\n', result.stdout)
        self.assertNotIn('will not start by itself', result.stdout)
        self.assertNotIn('a password that is not yours', result.stdout)

    def test_signal_after_the_confirmation_and_before_the_start_says_nothing(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', signal_at='Configure_Default_PHP_CLI')
        self.assertEqual(-signal.SIGTERM, result.returncode)
        self.assertEqual('install failed interrupted', machine.events()[-1])
        self.assertEqual(HELD + ['password-check'], machine.panel_service_calls())
        self.assertNotIn('The panel is stopped', result.stdout)

    def test_panel_that_was_started_is_not_called_stopped(self):
        # A run that completes, and one that fails after the panel was started
        # (the website for the hostname could not be made).
        for options, status in (({}, 0), ({'dns': True, 'create_output': CLI_FAILED}, 1)):
            with self.subTest(options=options):
                machine = Installer(self)
                machine.path('/usr/local/lsws/lsphp83/bin').mkdir(parents=True)
                runtime = machine.path('/usr/local/lsws/lsphp83/bin/lsphp')
                runtime.write_text('#!/bin/sh\n')
                runtime.chmod(0o755)
                result = machine.run('-v', 'ols', **options)
                self.assertEqual(status, result.returncode, result.stdout + result.stderr)
                self.assertEqual(COMPLETE_RUN if status == 0 else COMPLETING, machine.panel_service_calls())
                self.assertNotIn('The panel is stopped', result.stdout)

    def test_run_ends_complete_only_when_the_panel_starts_at_boot(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual(COMPLETE_RUN, machine.panel_service_calls())

    def test_panel_enabled_on_the_second_try_completes_the_run(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', panel_enabled='second')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('install complete', machine.events()[-1])
        self.assertEqual(COMPLETE_RUN + ['systemctl enable lscpd', 'systemctl is-enabled lscpd'],
                         machine.panel_service_calls())

    def test_panel_that_cannot_be_enabled_fails_the_run_before_it_is_called_complete(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', panel_enabled='no')
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        self.assertEqual(['ready failed panel_setup', 'install failed panel_setup'], machine.events()[-2:])
        self.assertNotIn('install complete', machine.events())
        self.assertNotIn('panel ready', machine.events())
        self.assertIn("but the panel's service could not be set to start when the server boots.\n"
                      'Set it with: systemctl enable lscpd\n', result.stdout)
        # The panel was started with a confirmed password: it is not held, and
        # not called stopped.
        self.assertEqual(COMPLETE_RUN + ['systemctl enable lscpd', 'systemctl is-enabled lscpd'],
                         machine.panel_service_calls())
        self.assertNotIn('The panel is stopped', result.stdout)
        # Nothing waited for the panel to answer.
        self.assertEqual([], [call for call in machine.recorded(machine.calls) if '127.0.0.1:8090' in call])

    def test_only_two_places_enable_or_start_the_panel(self):
        functions, top_level = script_parts()
        source = functions + top_level
        # Commands only: a message that tells the person installing how to
        # start the panel names the commands without running them.
        starts = [line.strip() for line in source.splitlines()
                  if re.search(r'systemctl\s+(enable|start|restart|reenable|unmask)\b.*\blscpd\b', line)
                  and not line.strip().startswith('echo')]
        self.assertEqual(['systemctl enable lscpd >/dev/null 2>&1', 'systemctl restart lscpd >/dev/null 2>&1',
                          'systemctl enable lscpd >/dev/null 2>&1',
                          'systemctl enable lscpd >/dev/null 2>&1', 'systemctl restart lscpd'], starts)
        # The third is the second try of Panel_Starts_At_Boot, which only the
        # end of a run with a confirmed password calls.
        self.assertIn('systemctl enable lscpd >/dev/null 2>&1', function('Panel_Starts_At_Boot'))
        self.assertEqual(1, source.count('if ! Panel_Starts_At_Boot; then'))
        finish = function('Install_Run_Finish')
        self.assertLess(finish.index('if [[ "$Panel_Password_Confirmed" != "Yes" ]]; then'),
                        finish.index('if ! Panel_Starts_At_Boot; then'))
        start_panel = function('Start_Panel')
        self.assertIn('if [[ "$Panel_Password_Confirmed" != "Yes" ]]; then\n  return 1\nfi\nsystemctl enable lscpd',
                      start_panel)
        self.assertEqual(1, source.count('\nPanel_Installing="Yes"\nMain_Installation\n'))
        self.assertEqual(1, source.count('Panel_Password_Confirmed="Yes"'))
        # systemd 219 (CentOS 7) has no "disable --now".
        self.assertEqual(['systemctl disable lscpd >/dev/null 2>&1', 'systemctl stop lscpd >/dev/null 2>&1'],
                         [line for line in function('Hold_Panel').splitlines() if line.startswith('systemctl')])


class AdminPassCommandTests(unittest.TestCase):
    """/usr/bin/adminPass as the installer writes it, run by sh with stand-ins."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        tweak = function('Post_Install_Tweak')
        opening = "cat > /usr/bin/adminPass <<'ADMINPASS'\n"
        self.assertEqual(1, tweak.count(opening))
        body = tweak[tweak.index(opening) + len(opening):tweak.index('\nADMINPASS\n') + 1]
        self.stored = self.root / 'adminPass'
        self.python = self.root / 'python'
        self.python.write_text('#!/bin/sh\nprintf "%s\\n" "$@" > "$0.arguments"\nexit "$QA_STATUS"\n')
        self.python.chmod(0o755)
        tools = self.root / 'tools'
        tools.mkdir()
        (tools / 'systemctl').write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "$QA_SERVICE_CALLS"\n')
        (tools / 'systemctl').chmod(0o755)
        self.command = self.root / 'adminPass-command'
        self.command.write_text(with_stand_ins(body, (
            ('/usr/local/CyberPanel/bin/python', self.python),
            ('/usr/local/CyberCP/plogical/adminPass.py', 'adminPass.py'),
            ('/etc/cyberpanel/adminPass', self.stored))), encoding='utf-8')
        self.assertNotIn('/usr/local/', self.command.read_text(encoding='utf-8'))
        self.assertNotIn('/etc/', self.command.read_text(encoding='utf-8'))
        self.service_calls = self.root / 'service-calls'

    def run_command(self, *arguments, status=0, shell='sh'):
        result = subprocess.run([shell, str(self.command)] + list(arguments), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, encoding='utf-8', timeout=20,
                                env={'PATH': '%s:%s' % (self.root / 'tools', os.environ['PATH']),
                                     'QA_STATUS': str(status), 'QA_SERVICE_CALLS': str(self.service_calls)})
        calls = self.service_calls.read_text().splitlines() if self.service_calls.exists() else []
        return result, calls

    def test_password_the_panel_took_is_stored_and_the_panel_started(self):
        for shell in ('sh', 'bash'):
            for password in ('New-Secret-1234', SECRET, '-e'):
                with self.subTest(shell=shell, password=password):
                    for leftover in (self.stored, self.service_calls):
                        if leftover.exists():
                            leftover.unlink()
                    result, calls = self.run_command(password, shell=shell)
                    self.assertEqual((0, '', ''), (result.returncode, result.stdout, result.stderr))
                    self.assertEqual(['adminPass.py', '--password', password],
                                     (self.root / 'python.arguments').read_text().splitlines())
                    self.assertEqual(password + '\n', self.stored.read_text())
                    self.assertEqual(0o600, stat.S_IMODE(self.stored.stat().st_mode))
                    self.assertEqual(['enable lscpd', 'restart lscpd'], calls)

    def test_password_the_panel_did_not_take_changes_nothing(self):
        self.stored.write_text('the-password-before\n')
        for status in (1, 2, 3):
            with self.subTest(status=status):
                result, calls = self.run_command('New-Secret-1234', status=status)
                self.assertEqual(1, result.returncode)
                self.assertEqual('The password was not set, and the panel was left as it was.\n', result.stdout)
                self.assertEqual('the-password-before\n', self.stored.read_text())
                self.assertEqual([], calls)

    def test_command_is_written_whole_and_for_root_only(self):
        tweak = function('Post_Install_Tweak')
        self.assertIn("\nADMINPASS\nchmod 700 /usr/bin/adminPass\n", tweak)
        self.assertNotIn('>> /usr/bin/adminPass', tweak)


class AdminPassScriptTests(unittest.TestCase):
    def setUp(self):
        self.tree = parse_as_python_36((ROOT / 'plogical/adminPass.py').read_text(encoding='utf-8'))
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name

    def functions(self, scope):
        body = [node for node in self.tree.body if isinstance(node, ast.FunctionDef)]
        exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), 'adminPass', 'exec'), scope)
        return scope

    def test_first_line_is_the_password(self):
        read = self.functions({})['password_from_file']
        for content, expected in ((SECRET + '\n', SECRET), (SECRET, SECRET), (SECRET + '\r\n', SECRET),
                                  (' padded \nsecond\n', ' padded '), ('', ''),
                                  ('p\u00e4ssw\u00f6rd-1234\n', 'p\u00e4ssw\u00f6rd-1234')):
            with self.subTest(content=content):
                self.assertEqual(expected, read(str(password_file(self.directory, content))))

    def change(self, *arguments):
        hashing = Mock()
        administrators = Mock()
        administrators.objects.count.return_value = 1
        self.forget = Mock()
        scope = self.functions(dict(argparse=argparse, Administrator=administrators, hashPassword=hashing,
                                    print=Mock(), forget_generated_password_notice=self.forget))
        with patch.object(sys, 'argv', ['adminPass.py'] + list(arguments)):
            scope['main']()
        return hashing

    def test_a_password_that_is_set_ends_the_notice_of_a_generated_one(self):
        self.change('--password', 'typed-by-hand')
        self.forget.assert_called_once_with()

    def test_password_file_sets_the_admin_password(self):
        hashing = self.change('--password-file', str(password_file(self.directory)))
        hashing.hash_password.assert_called_once_with(SECRET)
        hashing.generateToken.assert_called_once_with('admin', SECRET)

    def test_password_option_still_works(self):
        hashing = self.change('--password', 'typed-by-hand')
        hashing.hash_password.assert_called_once_with('typed-by-hand')

    def test_password_that_begins_with_a_dash_needs_the_form_with_the_equals_sign(self):
        # The way the installer gives the password to a tree that cannot read a file.
        for password in ('-starts-with-a-dash', '--password-file', '-p', '--api'):
            with self.subTest(password=password):
                hashing = self.change('--password=' + password)
                hashing.hash_password.assert_called_once_with(password)
        with patch('sys.stderr'), self.assertRaises(SystemExit) as stopped:
            self.change('--password', '-starts-with-a-dash')
        self.assertEqual(2, stopped.exception.code)

    def test_parser_of_the_older_tree_takes_the_form_with_the_equals_sign(self):
        # The options of adminPass.py as 3.0.12 has them.
        parser = argparse.ArgumentParser(description='Reset admin user password!')
        parser.add_argument('--password', help='New Password')
        parser.add_argument('--api', help='Enable/Disable API')
        parser.add_argument('--api-token', help='Set a pre-generated versioned API token while enabling API access')
        for password in ('-starts-with-a-dash', '--api', SECRET):
            with self.subTest(password=password):
                self.assertEqual(password, parser.parse_args(['--password=' + password]).password)
        with patch('sys.stderr'), self.assertRaises(SystemExit):
            parser.parse_args(['--password', '-starts-with-a-dash'])

    def test_file_without_a_password_is_refused(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit) as stopped:
            self.change('--password-file', str(password_file(self.directory, '\n')))
        self.assertEqual(2, stopped.exception.code)


class FirstAdministratorTests(unittest.TestCase):
    """adminPass.py --first-administrator: the panel's first administrator, with
    a password nobody chose, readable by root only, made at most once."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        (self.root / 'etc').mkdir()
        (self.root / 'home').mkdir()
        self.stored = self.root / 'etc' / 'adminPass'
        self.lock = self.root / 'etc' / 'adminPass.lock'
        self.marker = self.root / 'home' / 'adminPassGenerated'
        self.events = []
        self.administrators = Mock()
        self.administrators.objects.exists.side_effect = lambda: self.events.append('count') or self.existing
        self.existing = False
        self.created = []
        self.printed = []
        tree = parse_as_python_36((ROOT / 'plogical/adminPass.py').read_text(encoding='utf-8'))
        body = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
        import fcntl
        flock = fcntl.flock

        def flock_recorded(descriptor, operation):
            self.events.append('lock')
            return flock(descriptor, operation)

        self.scope = dict(
            argparse=argparse, os=os, sys=sys, tempfile=tempfile, secrets=__import__('secrets'),
            fcntl=SimpleNamespace(flock=flock_recorded, LOCK_EX=fcntl.LOCK_EX),
            Administrator=self.administrators, create_first_administrator=self.create,
            forget_generated_password_notice=Mock(), hashPassword=Mock(),
            PASSWORD_FILE=str(self.stored), PASSWORD_LOCK=str(self.lock), GENERATED_LENGTH=20,
            GENERATED_ALPHABET=string.ascii_letters + string.digits,
            GENERATED_PASSWORD_MARKER=str(self.marker),
            print=lambda *values: self.printed.append(' '.join(str(value) for value in values)))
        exec(compile(ast.fix_missing_locations(ast.Module(body=body, type_ignores=[])), 'adminPass', 'exec'),
             self.scope)

    def create(self, password):
        # What the panel's own function does with the database is not what is
        # tested here: only that it gets the password, before it is stored.
        self.created.append((password, self.stored.exists()))
        if self.fail_create:
            raise RuntimeError('fixture: the database refused the row')

    fail_create = False

    def leftovers(self):
        return sorted(path.name for path in (self.root / 'etc').iterdir()
                      if path.name not in ('adminPass', 'adminPass.lock'))

    def test_a_panel_without_an_administrator_gets_one_with_a_generated_password(self):
        self.assertEqual(0, self.scope['make_first_administrator']())
        self.assertEqual(1, len(self.created))
        password, stored_before = self.created[0]
        self.assertFalse(stored_before, 'the password was in place before the administrator existed')
        self.assertRegex(password, r'^[A-Za-z0-9]{20}$')
        self.assertEqual(password + '\n', self.stored.read_text(encoding='utf-8'))
        self.assertEqual(0o600, stat.S_IMODE(self.stored.stat().st_mode))
        self.assertEqual(0o600, stat.S_IMODE(self.lock.stat().st_mode))
        self.assertEqual([], self.leftovers())
        self.assertTrue(self.marker.is_file())
        self.assertEqual('', self.marker.read_text())
        self.assertTrue(self.printed)
        self.assertNotIn(password, ' '.join(self.printed))
        self.assertIn(str(self.stored), ' '.join(self.printed))

    def test_a_panel_with_an_administrator_is_left_as_it_is(self):
        self.stored.write_text('kept\n')
        self.existing = True
        self.assertEqual(0, self.scope['make_first_administrator']())
        self.assertEqual([], self.created)
        self.assertEqual('kept\n', self.stored.read_text())
        self.assertFalse(self.marker.exists())
        self.assertEqual([], self.leftovers())

    def test_the_count_is_taken_under_the_lock(self):
        self.scope['make_first_administrator']()
        self.assertEqual(['lock', 'count'], self.events)

    def test_an_administrator_that_cannot_be_saved_leaves_nothing_behind(self):
        self.stored.write_text('kept\n')
        self.fail_create = True
        with self.assertRaises(RuntimeError):
            self.scope['make_first_administrator']()
        self.assertEqual('kept\n', self.stored.read_text())
        self.assertEqual([], self.leftovers())
        self.assertFalse(self.marker.exists())

    def test_generated_passwords_are_letters_and_digits_and_differ(self):
        passwords = {self.scope['generated_password']() for _ in range(200)}
        self.assertEqual(200, len(passwords))
        for password in passwords:
            self.assertRegex(password, r'^[A-Za-z0-9]{20}$')

    def test_the_marker_does_not_follow_a_link(self):
        target = self.root / 'etc' / 'elsewhere'
        target.write_text('untouched\n')
        self.marker.symlink_to(target)
        self.scope['note_generated_password']()
        self.assertTrue(self.marker.is_symlink())
        self.assertEqual('untouched\n', target.read_text())

    def test_the_option_runs_alone_and_its_status_is_the_exit_status(self):
        with patch.object(sys, 'argv', ['adminPass.py', '--first-administrator']):
            with self.assertRaises(SystemExit) as stopped:
                self.scope['main']()
        self.assertEqual(0, stopped.exception.code)
        self.assertEqual(1, len(self.created))
        for others in (['--password', 'typed-by-hand'], ['--password-file', '/dev/null'], ['--api', '1']):
            with self.subTest(others=others):
                with patch.object(sys, 'argv', ['adminPass.py', '--first-administrator'] + others), \
                        patch('sys.stderr'), self.assertRaises(SystemExit) as stopped:
                    self.scope['main']()
                self.assertEqual(2, stopped.exception.code)

    def test_a_failure_is_status_1_and_names_only_its_kind(self):
        self.fail_create = True
        with patch.object(sys, 'argv', ['adminPass.py', '--first-administrator']):
            with self.assertRaises(SystemExit) as stopped:
                self.scope['main']()
        self.assertEqual(1, stopped.exception.code)
        self.assertEqual(['The first administrator could not be made: RuntimeError'], self.printed)

    def test_the_first_administrator_of_a_typed_password_is_made_the_same_way(self):
        source = (ROOT / 'plogical/adminPass.py').read_text(encoding='utf-8')
        self.assertEqual(2, source.count('create_first_administrator('))
        self.assertNotIn('Administrator(userName=', source)
        self.assertNotIn('1234567', source)


if __name__ == '__main__':
    unittest.main()
