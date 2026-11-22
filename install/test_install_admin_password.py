"""The admin password given in a file stays out of sight, and -p out of the logs."""
import argparse
import ast
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch

from install.installer_test_harness import CLI_FAILED, ROOT, Installer, parse_as_python_36, script_parts

SECRET = 'Tr0ub4dor&3 -e \\n $HOME `id` "quoted"'
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


class PasswordFileReaderTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.directory = directory.name

    def read(self, path):
        script = function('Read_Admin_Password_File') + (
            'Read_Admin_Password_File\nstatus=$?\nprintf "%s" "$Admin_Pass_From_File"\n'
            'printf "%s" "$Admin_Pass_File_Problem" >&2\nexit $status\n')
        environment = {'PATH': os.environ['PATH']}
        if path is not None:
            environment['CP_ADMIN_PASSWORD_FILE'] = str(path)
        return subprocess.run(['bash', '-c', script], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              universal_newlines=True, env=environment, timeout=20)

    def assert_refused(self, path, *secrets):
        result = self.read(path)
        self.assertEqual(1, result.returncode)
        self.assertEqual('', result.stdout)
        self.assertIn('CP_ADMIN_PASSWORD_FILE', result.stderr)
        for secret in secrets:
            self.assertNotIn(secret, result.stderr)

    def test_no_file_named_changes_nothing(self):
        for path in (None, ''):
            result = self.read(path)
            self.assertEqual((0, '', ''), (result.returncode, result.stdout, result.stderr))

    @AS_ROOT
    def test_password_is_taken_as_it_is_written(self):
        for content in (SECRET + '\n', SECRET, SECRET + '\nsecond line\n', '  spaced out  \n'):
            with self.subTest(content=content):
                result = self.read(password_file(self.directory, content))
                self.assertEqual((0, ''), (result.returncode, result.stderr))
                self.assertEqual(content.split('\n')[0], result.stdout)

    @AS_ROOT
    def test_modes_that_only_root_can_read_are_accepted(self):
        for mode in (0o600, 0o400):
            with self.subTest(mode=oct(mode)):
                self.assertEqual(0, self.read(password_file(self.directory, mode=mode)).returncode)

    @AS_ROOT
    def test_file_that_others_can_read_is_refused(self):
        for mode in (0o644, 0o640, 0o604, 0o660, 0o666):
            with self.subTest(mode=oct(mode)):
                self.assert_refused(password_file(self.directory, mode=mode), SECRET)

    @AS_ROOT
    def test_file_of_another_account_is_refused(self):
        path = password_file(self.directory)
        os.chown(str(path), 65534, 0)
        self.assert_refused(path, SECRET)

    def test_missing_file_directory_and_link_are_refused(self):
        self.assert_refused(Path(self.directory) / 'missing')
        self.assert_refused(self.directory)
        link = Path(self.directory) / 'link'
        link.symlink_to(password_file(self.directory))
        self.assert_refused(link, SECRET)

    @AS_ROOT
    def test_short_or_empty_password_is_refused_without_being_shown(self):
        for content in ('', '\n', 'short7!\n', '\n' + SECRET + '\n'):
            with self.subTest(content=content):
                self.assert_refused(password_file(self.directory, content), 'short7!')


class MaskedArgumentTests(unittest.TestCase):
    def masked(self, *arguments):
        script = function('Mask_Arguments') + ('Mask_Arguments "$@"\n'
                                               'for argument in "${Logged_Arguments[@]}"; do printf "%s\\n" "$argument"; done\n')
        result = subprocess.run(['bash', '-c', script, 'bash'] + list(arguments), stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=20)
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
        source = function('Set_Admin_Password')
        for real, stand_in in (('/etc/cyberpanel/adminPass', self.stored),
                               ('/usr/local/CyberPanel/bin/python', self.python),
                               ('/usr/local/CyberCP/plogical/adminPass.py', self.tool)):
            self.assertIn(real, source)
            source = source.replace(real, str(stand_in))
        self.assertNotIn('/etc/', source)
        self.assertNotIn('/usr/local/', source)
        result = subprocess.run(['bash', '-c', 'umask %s\n%s\nSet_Admin_Password' % (umask, source)],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=20,
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
        status, arguments, mode_when_read = self.set_password(SECRET, tree='old')
        self.assertEqual(0, status)
        self.assertEqual([str(self.tool), '--password', SECRET], arguments)
        self.assertEqual(SECRET + '\n', self.stored.read_text())
        self.assertEqual('600', mode_when_read)

    def test_tool_that_is_not_there_is_called_the_old_way_and_its_failure_is_the_status(self):
        # Nothing is printed for the missing file; the interpreter's failure to
        # run it is what ends the run.
        status, arguments, _ = self.set_password(SECRET, tree='missing', status=2)
        self.assertEqual(2, status)
        self.assertEqual([str(self.tool), '--password', SECRET], arguments)

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
        source = (ROOT / 'cyberpanel.sh').read_text()
        carrying = [line.strip() for line in source.splitlines()
                    if 'Admin_Pass' in line and re.match(r'\s*(/|python|cyberpanel |curl|wget)', line)]
        self.assertEqual(['/usr/local/CyberPanel/bin/python /usr/local/CyberCP/plogical/adminPass.py '
                          '--password "$Admin_Pass"'], carrying)
        fallback = function('Set_Admin_Password')
        self.assertLess(fallback.index("grep -q -- '--password-file'"), fallback.index('--password-file /etc'))
        self.assertLess(fallback.index('\nelse\n'), fallback.index('--password "$Admin_Pass"'))


LEGACY_HASH = 'import hashlib\nprint(hashlib.sha256(b"salt" + %r.encode()).hexdigest() + ":salt")\n'


class AdminPasswordCheckTests(unittest.TestCase):
    """Admin_Password_Is_Set: the real check, run by a stand-in for the panel's tree.

    The tree has the panel's real plogical/hashPassword.py, the same file in
    3.0.12 and now; Django, the administrator table and bcrypt are stand-ins.
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
        (self.tree / 'CyberCP/settings.py').write_text('')
        (self.tree / 'bcrypt.py').write_text('')
        (self.tree / 'plogical/hashPassword.py').write_text((ROOT / 'plogical/hashPassword.py').read_text())
        (self.tree / 'loginSystem/models.py').write_text(
            'import json\nimport os\n\n\n'
            'class Row:\n    def __init__(self, password):\n        self.password = password\n\n\n'
            'class Rows(list):\n    def first(self):\n        return self[0] if self else None\n\n\n'
            'class Manager:\n    def filter(self, userName):\n'
            '        with open(os.environ["QA_ADMINISTRATORS"]) as source:\n'
            '            stored = json.load(source)\n'
            '        return Rows([Row(stored[userName])] if userName in stored else [])\n\n\n'
            'class Administrator:\n    objects = Manager()\n')
        self.stored = self.root / 'adminPass'
        self.administrators = self.root / 'administrators.json'

    def stored_hash(self, password):
        return subprocess.run([sys.executable, '-c', LEGACY_HASH % password], stdout=subprocess.PIPE,
                              universal_newlines=True, check=True).stdout.strip()

    def check(self, administrators, stored='absent'):
        self.administrators.write_text(json.dumps(administrators))
        if stored != 'absent':
            self.stored.write_text(stored, encoding='utf-8')
        elif self.stored.exists():
            self.stored.unlink()
        source = function('Admin_Password_Is_Set')
        self.assertNotIn('Admin_Pass"', source)
        for real, stand_in in (('/usr/local/CyberCP/bin/python', sys.executable),
                               ('/usr/local/CyberCP', self.tree),
                               ('/etc/cyberpanel/adminPass', self.stored)):
            self.assertIn(real, source)
            source = source.replace(real, str(stand_in))
        self.assertNotIn('/etc/', source)
        self.assertNotIn('/usr/local/', source)
        result = subprocess.run(['bash', '-c', source + '\nAdmin_Password_Is_Set'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, universal_newlines=True, timeout=60,
                                env={'PATH': os.environ['PATH'], 'QA_ADMINISTRATORS': str(self.administrators)})
        self.assertEqual('', result.stdout)
        return result

    def test_administrator_with_the_stored_password(self):
        for password in (SECRET, 'p\u00e4ssw\u00f6rd-1234', '1234567'):
            for ending in ('\n', '', '\r\n'):
                with self.subTest(password=password, ending=ending):
                    result = self.check({'admin': self.stored_hash(password)}, password + ending)
                    self.assertEqual((0, ''), (result.returncode, result.stderr))

    def test_administrator_with_another_password(self):
        # What a panel has that created its administrator itself on a first request.
        result = self.check({'admin': self.stored_hash('1234567')}, SECRET + '\n')
        self.assertEqual((1, ''), (result.returncode, result.stderr))

    def test_no_administrator(self):
        result = self.check({}, SECRET + '\n')
        self.assertEqual((1, ''), (result.returncode, result.stderr))
        result = self.check({'someone': self.stored_hash(SECRET)}, SECRET + '\n')
        self.assertEqual(1, result.returncode)

    def test_nothing_stored_is_no_password(self):
        result = self.check({'admin': self.stored_hash('')}, '')
        self.assertEqual(1, result.returncode)
        result = self.check({'admin': self.stored_hash(SECRET)})
        self.assertNotEqual(0, result.returncode)
        self.assertIn('adminPass', result.stderr)

    def test_check_that_cannot_run_is_a_failed_check(self):
        (self.tree / 'loginSystem/models.py').write_text('raise RuntimeError("fixture: no database")\n')
        result = self.check({'admin': self.stored_hash(SECRET)}, SECRET + '\n')
        self.assertNotEqual(0, result.returncode)
        self.assertIn('fixture: no database', result.stderr)

    def test_check_is_valid_for_the_panel_interpreter_of_almalinux_8(self):
        source = function('Admin_Password_Is_Set')
        code = source[source.index("<<'VERIFY'\n") + len("<<'VERIFY'\n"):source.index('\nVERIFY\n')]
        parse_as_python_36(code)


class PasswordOutcomeTests(unittest.TestCase):
    """Whole runs: no installation ends complete with another password than the one given."""

    def probes(self, machine):
        return [call for call in machine.recorded(machine.calls) if '127.0.0.1:8090' in call]

    def assert_panel_stopped(self, machine, result):
        # Left running, it would let anyone in: see Stop_Panel_Without_Password.
        self.assertIn('systemctl stop lscpd', machine.recorded(machine.calls))
        self.assertIn('The panel has been stopped', result.stdout)
        self.assertIn("adminPass 'a new password'", result.stdout)

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
        self.assertNotIn('systemctl stop lscpd', machine.recorded(machine.calls))

    def test_older_tree_gets_the_password_and_the_run_completes(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', '-p', 'Typed-Secret-99', tree='old')
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual('install complete', machine.events()[-1])
        self.assertEqual([str(machine.path('/usr/local/CyberCP/plogical/adminPass.py')), '--password',
                          'Typed-Secret-99'], machine.recorded(machine.adminpass_call))

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
                self.assert_panel_stopped(machine, result)

    def test_administrator_without_the_given_password_fails_the_run(self):
        machine = Installer(self)
        result = machine.run('-v', 'ols', password_check_exit=1)
        self.assertEqual(1, result.returncode, result.stdout + result.stderr)
        events = machine.events()
        self.assertEqual(['ready running', 'ready failed panel_setup', 'install failed panel_setup'], events[-3:])
        self.assertNotIn('install complete', events)
        self.assertNotIn('panel ready', events)
        self.assertEqual([], self.probes(machine))
        self.assertIn('its administrator does not have the password of this installation', result.stdout)
        self.assertNotIn('CyberPanel Successfully Installed', result.stdout)
        self.assert_panel_stopped(machine, result)

    def test_failed_certificate_is_no_working_panel_without_the_given_password(self):
        machine = Installer(self)
        machine.path('/usr/local/lsws/lsphp83/bin').mkdir(parents=True)
        runtime = machine.path('/usr/local/lsws/lsphp83/bin/lsphp')
        runtime.write_text('#!/bin/sh\n')
        runtime.chmod(0o755)
        result = machine.run('-v', 'ols', dns=True, tls_output=CLI_FAILED, password_check_exit=1)
        self.assertEqual(1, result.returncode)
        events = machine.events()
        self.assertEqual(['hostname_ssl failed panel_setup', 'install failed panel_setup'], events[-2:])
        self.assertNotIn('panel ready', events)
        self.assertEqual([], self.probes(machine))
        self.assertNotIn('Visit: https://', result.stdout)


class AdminPassScriptTests(unittest.TestCase):
    def setUp(self):
        self.tree = parse_as_python_36((ROOT / 'plogical/adminPass.py').read_text())
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
        scope = self.functions(dict(argparse=argparse, Administrator=administrators, hashPassword=hashing,
                                    print=Mock()))
        with patch.object(sys, 'argv', ['adminPass.py'] + list(arguments)):
            scope['main']()
        return hashing

    def test_password_file_sets_the_admin_password(self):
        hashing = self.change('--password-file', str(password_file(self.directory)))
        hashing.hash_password.assert_called_once_with(SECRET)
        hashing.generateToken.assert_called_once_with('admin', SECRET)

    def test_password_option_still_works(self):
        hashing = self.change('--password', 'typed-by-hand')
        hashing.hash_password.assert_called_once_with('typed-by-hand')

    def test_file_without_a_password_is_refused(self):
        with patch('sys.stderr'), self.assertRaises(SystemExit) as stopped:
            self.change('--password-file', str(password_file(self.directory, '\n')))
        self.assertEqual(2, stopped.exception.code)


if __name__ == '__main__':
    unittest.main()
