"""The admin password given in a file stays out of sight, and -p out of the logs."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from install.installer_test_harness import Installer, script_parts

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
            'Read_Admin_Password_File\nstatus=$?\nprintf "%s" "$Admin_Pass_From_File"\nexit $status\n')
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


if __name__ == '__main__':
    unittest.main()
