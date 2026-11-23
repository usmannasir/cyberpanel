"""The SpamAssassin installer reports success only when the package manager installed it.

It used to count only an exit status of 1 as a failure. apt-get ends with
100 when it cannot install, for example while another package operation
holds its lock, so the page reported "SpamAssassin Installed" and went on to
configure Postfix for a filter that was not there.

The installer's function is taken from the source and run with stand-ins
for the package manager and the files; mailUtilities itself is not imported,
since importing it sets up Django.
"""
import ast
import os
import shutil
import subprocess
import tempfile
import types
import unittest
import warnings
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

APT_LOCK = ('E: Could not get lock /var/lib/dpkg/lock-frontend. It is held by process 41270 (apt-get)\n'
            'E: Unable to acquire the dpkg frontend lock (/var/lib/dpkg/lock-frontend), is another process using it?\n')


def installer(namespace):
    """The installSpamAssassin function of plogical/mailUtilities.py, defined in namespace."""
    with warnings.catch_warnings():
        # The rest of the file has escape sequences newer interpreters warn about.
        warnings.simplefilter('ignore', SyntaxWarning)
        tree = ast.parse((ROOT / 'plogical' / 'mailUtilities.py').read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'mailUtilities')
    function = next(node for node in cls.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'installSpamAssassin')
    function.decorator_list = []
    module = ast.Module(body=[function])
    module.type_ignores = []  # a field from Python 3.8 on; older versions ignore it
    exec(compile(module, 'mailUtilities.py', 'exec'), namespace)
    return namespace['installSpamAssassin']


class SpamAssassinInstall(unittest.TestCase):

    def setUp(self):
        self.folder = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.folder)
        self.log = os.path.join(self.folder, 'spamassassinInstallLogPath')
        self.logged = []

    def run_installer(self, status, output):
        calls = []

        def call(cmd, stdout=None, stderr=None):
            calls.append((cmd, stderr))
            stdout.write(output)
            stdout.flush()
            return status

        fake_subprocess = types.SimpleNamespace(call=call, STDOUT=subprocess.STDOUT)
        utilities = types.SimpleNamespace(spamassassinInstallLogPath=self.log)
        processes = types.SimpleNamespace(decideDistro=lambda: 'ubuntu', centos='centos', cent8='cent8')
        writer = types.SimpleNamespace(writeToFile=self.logged.append)
        namespace = {'os': os, 'shlex': __import__('shlex'), 'subprocess': fake_subprocess,
                     'mailUtilities': utilities, 'ProcessUtilities': processes,
                     'logging': types.SimpleNamespace(CyberCPLogFileWriter=writer)}
        result = installer(namespace)(None, None)
        with open(self.log) as handle:
            return result, handle.read(), calls

    def test_a_held_lock_is_reported_as_a_failure_with_its_reason(self):
        result, log, calls = self.run_installer(100, APT_LOCK)
        self.assertEqual(result, 0)
        self.assertNotIn('[200]', log)
        last = log.strip().splitlines()[-1]
        self.assertTrue(last.endswith('[404]'), last)
        self.assertIn('SpamAssassin was not installed.', last)
        self.assertIn('busy with another installation or update', last)
        self.assertIn('try again', last)

    def test_any_other_failing_status_is_a_failure_that_quotes_the_package_manager(self):
        result, log, calls = self.run_installer(1, 'Error: Unable to find a match: spamassassin\n')
        self.assertEqual(result, 0)
        self.assertNotIn('[200]', log)
        self.assertIn('The package manager reported: Error: Unable to find a match: spamassassin', log)

    def test_the_package_managers_errors_reach_the_log(self):
        calls = self.run_installer(100, APT_LOCK)[2]
        self.assertEqual(calls[0][1], subprocess.STDOUT)

    def test_a_successful_installation_still_reports_success(self):
        result, log, calls = self.run_installer(0, 'Setting up spamassassin (4.0.0-6) ...\n')
        self.assertEqual(result, 1)
        self.assertTrue(log.strip().endswith('SpamAssassin Installed.[200]'), log)
        self.assertNotIn('[404]', log)
        self.assertEqual(calls[0][0], ['sudo', 'apt-get', 'install', 'spamassassin', 'spamc', '-y'])


if __name__ == '__main__':
    unittest.main()
