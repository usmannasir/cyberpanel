"""checkedExecutioner reports how a command really ended, also when the web
panel runs it through the privileged helper; sendCommand without status=True
sends and answers exactly as before.

The stand-in helper does what lscpd does: it hands the command line to sh,
answers with everything the shell printed, and ends with one byte that is 0
for every command that ends normally, whatever its exit status.
"""
import os
import shlex
import subprocess
import time
from types import SimpleNamespace
import unittest

from plogical import commandStatus
from plogical.commandShape import runs_one_command
from plogical.test_child_domain_conversion import load_method

TOKEN = 'T' * 32


def helper_reply(request, last=b'\x00'):
    """Run a request the way lscpd does and return its reply."""
    line = request.decode('utf-8')[len(TOKEN):]
    cwd = None
    while line.startswith(('-u ', '-d ')):
        flag, value, line = line.split(' ', 2)
        if flag == '-d':
            cwd = value
    # sudo is a no-op here: the stand-in already "is" the account it runs as.
    process = subprocess.Popen(['sh', '-c', 'sudo() { "$@"; }; ' + line], cwd=cwd,
                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    return process.communicate()[0] + last


class Runner(object):
    """ProcessUtilities' three methods, loaded from the source, talking to the stand-in."""

    def __init__(self, reply=helper_reply):
        self.sent = []
        self.logged = []
        sent = self.sent

        class Socket(object):
            def sendall(self, data):
                sent.append(data)
                self.data = reply(data)

            def recv(self, size):
                chunk, self.data = self.data[:7], self.data[7:]
                return chunk

            def close(self):
                pass

        self.utilities = SimpleNamespace(token=TOKEN, debugPath='/nonexistent/debug',
                                         setupUDSConnection=lambda: [Socket(), 'None'])
        namespace = dict(ProcessUtilities=self.utilities, os=os, time=time, subprocess=subprocess, shlex=shlex,
                         logging=SimpleNamespace(writeToFile=self.logged.append),
                         commandStatus=commandStatus, runs_one_command=runs_one_command,
                         getpass=SimpleNamespace(getuser=lambda: 'cyberpanel'))
        for name in ('sendCommand', 'checkedExecutioner', 'normalExecutioner'):
            setattr(self.utilities, name, load_method('plogical/processUtilities.py', 'ProcessUtilities',
                                                      name, dict(namespace)))

    def status(self, command, user=None, dir=None):
        return self.utilities.sendCommand(command, user, dir, status=True)

    def run(self, command, user=None):
        return self.utilities.checkedExecutioner(command, user)


class ExitStatusTests(unittest.TestCase):

    def test_failed_commands_are_failures(self):
        runner = Runner()
        for command in ('false', "sh -c 'exit 3'", 'ls /nonexistent-cyberpanel-test',
                        'no-such-program-cyberpanel-test'):
            self.assertEqual(0, runner.run(command), command)
            self.assertNotEqual(0, runner.status(command)[0], command)

    def test_successful_commands_succeed_with_their_output_unchanged(self):
        runner = Runner()
        self.assertEqual((0, 'a\nb'), runner.status("printf 'a\\nb'"))
        self.assertEqual(1, runner.run('true'))

    def test_the_real_exit_status_is_reported(self):
        self.assertEqual(3, Runner().status("sh -c 'exit 3'")[0])

    def test_the_request_carries_the_status_trailer(self):
        runner = Runner()
        runner.status('id -u', user='examp1234')
        request = runner.sent[0].decode()
        self.assertTrue(request.startswith(TOKEN + "-u examp1234 (eval 'id -u');printf '\\n"), request)

    def test_a_command_of_the_panel_runs_through_sudo(self):
        runner = Runner()
        runner.run('true')
        self.assertIn("(eval 'sudo true')", runner.sent[0].decode())

    def test_the_directory_is_kept(self):
        self.assertEqual((0, '/tmp\n'), Runner().status('pwd', dir='/tmp'))

    def test_a_reply_without_the_trailer_is_a_failure(self):
        # The shell was killed, or the helper answered with nothing but its byte.
        runner = Runner(reply=lambda request: b'partial output\x00')
        self.assertEqual((None, 'partial output'), runner.status('true'))
        self.assertEqual(0, runner.run('true'))
        self.assertEqual(0, Runner(reply=lambda request: b'').run('true'))

    def test_a_command_too_long_for_the_trailer_is_sent_and_read_as_before(self):
        runner = Runner()
        command = 'true ' + 'x' * (commandStatus.REQUEST_LIMIT - len(TOKEN) - 40)
        self.assertEqual(1, runner.run(command))
        self.assertNotIn(b'(eval', runner.sent[0])
        self.assertLessEqual(len(runner.sent[0]), commandStatus.REQUEST_LIMIT)

    def test_a_refused_command_is_a_failure(self):
        status, output = Runner().status('sudo -u examp1234 true; id')
        self.assertIsNone(status)
        self.assertIn('refused', output)

    def test_without_status_the_request_and_the_reply_are_as_before(self):
        runner = Runner()
        reply = runner.utilities.sendCommand('false')
        self.assertEqual([(TOKEN + 'sudo false').encode()], runner.sent)
        self.assertEqual('\x00', reply)
        runner.utilities.sendCommand('pwd', 'examp1234', '/tmp')
        self.assertEqual((TOKEN + '-u examp1234 -d /tmp pwd').encode(), runner.sent[1])

    def test_as_root_the_status_of_the_command_decides(self):
        runner = Runner()
        runner.utilities.checkedExecutioner.__globals__['getpass'] = SimpleNamespace(getuser=lambda: 'root')
        self.assertEqual(1, runner.run('true'))
        self.assertEqual(0, runner.run('false'))
        self.assertEqual([], runner.sent)


if __name__ == '__main__':
    unittest.main()
