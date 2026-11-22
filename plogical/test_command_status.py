"""A command run through the privileged helper reports how it really ended."""
import io
import os
import shlex
import subprocess
from types import SimpleNamespace
import unittest

from plogical import commandStatus
from plogical.test_child_domain_conversion import load_method

MARKER = 'a' * 32
OTHER = 'b' * 32
TRAILER = b'\n' + MARKER.encode() + b' '


def stream(chunks=None, command='rustic dump x', shell=False, last=b'\x00', token='TOKEN'):
    """Run streamCommand against a stand-in for the helper.

    With chunks the helper answers with exactly those reads. With shell it
    does what the real one does: it hands the command line to sh, answers
    with everything the shell printed, and ends with a byte that says nothing
    about the exit status.
    """
    sent = []
    logged = []

    class Socket(object):
        def __init__(self):
            self.reads = list(chunks or [])
            self.closed = False

        def sendall(self, data):
            sent.append(data)
            if shell:
                line = data.decode('utf-8').split(' ', 2)[2]
                process = subprocess.Popen(['sh', '-c', line], stdin=subprocess.DEVNULL,
                                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                reply = process.communicate()[0] + last
                self.reads = [reply[index:index + 7] for index in range(0, len(reply), 7)]

        def recv(self, size):
            return self.reads.pop(0) if self.reads else b''

        def close(self):
            self.closed = True

    sockets = []

    def connect():
        sockets.append(Socket())
        return [sockets[-1], 'None']

    helper = SimpleNamespace(setupUDSConnection=connect, token=token)
    function = load_method('plogical/processUtilities.py', 'ProcessUtilities', 'streamCommand', dict(
        ProcessUtilities=helper, logging=SimpleNamespace(writeToFile=logged.append), os=os,
        commandStatus=SimpleNamespace(
            new_marker=lambda: MARKER, helper_request=commandStatus.helper_request,
            StatusReader=commandStatus.StatusReader)))
    sink = io.BytesIO()
    result = function(command, 'examp1234', sink)
    return SimpleNamespace(result=result, written=sink.getvalue(), sent=sent, sockets=sockets, logged=logged)


class TrailerTests(unittest.TestCase):

    def test_the_command_runs_in_a_subshell_and_the_shell_reports_its_status(self):
        done = stream([b'ab\xff', b'\xfec', b'd' + TRAILER + b'0\x00'])
        self.assertEqual((1, b'ab\xff\xfecd'), (done.result, done.written))
        self.assertEqual(
            [b"TOKEN-u examp1234 (eval 'rustic dump x');printf '\\n" + MARKER.encode() + b" %d' $?"],
            done.sent)
        self.assertTrue(done.sockets[0].closed)

    def test_the_helper_s_last_byte_alone_is_not_taken_for_success(self):
        # What the helper really sends when a command fails: its output and a zero byte.
        done = stream([b'partial', b'\x00'])
        self.assertEqual((0, b'partial'), (done.result, done.written))
        self.assertEqual(0, stream([b'\x00']).result)
        self.assertEqual(0, stream([]).result)
        for status in (b'1', b'3', b'127', b'137', b'255'):
            done = stream([b'output' + TRAILER + status + b'\x00'])
            self.assertEqual((0, b'output'), (done.result, done.written), status)

    def test_a_trailer_split_across_reads_is_found_and_never_passed_on(self):
        reply = b'x' * 100 + TRAILER + b'0\x00'
        for size in (1, 2, 5, 37, 38, 39, 64, 200):
            done = stream([reply[index:index + size] for index in range(0, len(reply), size)])
            self.assertEqual((1, b'x' * 100), (done.result, done.written), size)
        done = stream([TRAILER + b'0\x00'])
        self.assertEqual((1, b''), (done.result, done.written))

    def test_output_that_looks_like_a_trailer_stays_output(self):
        another = b'\n' + OTHER.encode() + b' 0\x00'
        done = stream([b'data' + another + TRAILER + b'0\x00'])
        self.assertEqual((1, b'data' + another), (done.result, done.written))
        # The marker of another call at the very end reports nothing for this one.
        done = stream([b'data' + another])
        self.assertEqual((0, b'data' + another[:-1]), (done.result, done.written))
        # This call's own marker in the output, followed by the real trailer of a failure.
        done = stream([b'data' + TRAILER + b'0\x00' + TRAILER + b'1\x00'])
        self.assertEqual((0, b'data' + TRAILER + b'0\x00'), (done.result, done.written))

    def test_a_shell_that_was_killed_reports_nothing(self):
        # The helper's last byte is not zero when the shell did not end by itself.
        self.assertEqual(0, stream([b'out' + TRAILER + b'0\x09']).result)
        self.assertEqual(0, stream([b'out' + TRAILER + b'0']).result)
        self.assertEqual(0, stream([b'out' + TRAILER + b'0\x00more']).result)
        self.assertEqual(0, stream([b'out' + TRAILER + b'\x00']).result)
        self.assertEqual(0, stream([b'out' + TRAILER + b'0000\x00']).result)

    def test_a_command_longer_than_the_helper_takes_is_not_sent(self):
        fixed = len(stream([TRAILER + b'0\x00'], command='x').sent[0]) - 1
        fits = stream([TRAILER + b'0\x00'], command='x' * (commandStatus.REQUEST_LIMIT - fixed))
        self.assertEqual((1, commandStatus.REQUEST_LIMIT), (fits.result, len(fits.sent[0])))
        for command in ('x' * (commandStatus.REQUEST_LIMIT - fixed + 1),
                        # Counted in bytes, and with what quoting adds.
                        'é' * ((commandStatus.REQUEST_LIMIT - fixed) // 2 + 1),
                        "'" * ((commandStatus.REQUEST_LIMIT - fixed) // 5 + 1)):
            refused = stream([TRAILER + b'0\x00'], command=command)
            self.assertEqual((0, [], []), (refused.result, refused.sent, refused.sockets))
            self.assertEqual(1, len(refused.logged))
        self.assertEqual(1023, commandStatus.REQUEST_LIMIT)

    def test_request_fits_measures_what_would_be_sent(self):
        fixed = len(commandStatus.helper_request('t' * 32, 'examp1234', 'x', MARKER)) - 1
        self.assertTrue(commandStatus.request_fits('examp1234', 'x' * (1023 - fixed)))
        self.assertFalse(commandStatus.request_fits('examp1234', 'x' * (1024 - fixed)))
        self.assertFalse(commandStatus.request_fits('examp1234', 'a\x00b'))
        self.assertFalse(commandStatus.request_fits('examp1234', None))

    def test_a_command_that_is_no_text_is_not_sent(self):
        for command in (None, b'true', 'a\x00b', '\udcff'):
            refused = stream([TRAILER + b'0\x00'], command=command)
            self.assertEqual((0, []), (refused.result, refused.sent), command)


class ShellTests(unittest.TestCase):
    """The same through a real shell that answers like the helper: output, then a zero byte."""

    def run_command(self, command, last=b'\x00'):
        done = stream(command=command, shell=True, last=last)
        return done.result, done.written

    def test_the_status_of_the_command_decides(self):
        self.assertEqual((1, b''), self.run_command('true'))
        self.assertEqual((0, b''), self.run_command('false'))
        self.assertEqual((0, b''), self.run_command('exit 3'))
        self.assertEqual((1, b'kept\n'), self.run_command('echo kept; exit 0'))
        self.assertEqual((0, b'kept\n'), self.run_command('echo kept; false'))
        self.assertEqual(0, self.run_command('/nonexistent/program')[0])
        self.assertEqual(0, self.run_command('/nonexistent/program 2>/dev/null')[0])
        self.assertEqual(0, self.run_command('kill -9 $$ 2>/dev/null; sh -c \'kill -9 $PPID\'')[0])

    def test_the_text_of_the_command_cannot_end_the_subshell_or_hide_the_trailer(self):
        self.assertEqual((1, b'a\n'), self.run_command('echo a # a comment'))
        self.assertEqual((0, b''), self.run_command('false # a comment'))
        self.assertEqual(0, self.run_command('echo ( 2>/dev/null')[0])
        self.assertEqual(0, self.run_command("echo 'open")[0])
        # Text that would close the subshell early is no command at all: nothing of it runs.
        result, written = self.run_command('echo a); (true')
        self.assertEqual((0, False), (result, written.startswith(b'a\n')))
        self.assertEqual((0, b''), self.run_command('false; exit'))
        self.assertEqual((1, b'one\ntwo\n'), self.run_command('echo one\necho two'))

    def test_quotes_pipes_and_redirections_of_the_command_keep_their_meaning(self):
        self.assertEqual((1, b"it's \"x\" $HOME `id` \\ ; & | < > * ? ( ) { } [ ] ! # ~\n"), self.run_command(
            "printf '%s\\n' " + shlex.quote("it's \"x\" $HOME `id` \\ ; & | < > * ? ( ) { } [ ] ! # ~")))
        self.assertEqual((1, b'B\n'), self.run_command('echo b 2>/dev/null | tr b B'))
        self.assertEqual((0, b''), self.run_command('echo b | grep -q c'))
        self.assertEqual((1, b''), self.run_command('ls /nonexistent-directory 2>/dev/null; true'))
        self.assertEqual((1, b'--\n'), self.run_command('echo "-$(printf "")-" 2>/dev/null'))
        self.assertEqual((1, b''), self.run_command('rustic --help >/dev/null 2>&1; true --password ""'))

    def test_binary_output_of_any_length_arrives_unchanged(self):
        ending = b'\n' + OTHER.encode() + b' 0\x00'
        result, written = self.run_command(
            'head -c 300000 /dev/zero; printf \'\\377\\376\\n%s 0\\000\' %s' % ('%s', OTHER))
        self.assertEqual(1, result)
        self.assertEqual(300000 + len(b'\xff\xfe') + len(ending), len(written))
        self.assertEqual(b'\x00\x00\xff\xfe' + ending, written[-(4 + len(ending)):])
        self.assertEqual((1, b''), self.run_command(':'))

    def test_error_output_arrives_before_the_trailer(self):
        result, written = self.run_command('echo out; echo err 1>&2; exit 4')
        self.assertEqual((0, b'out\nerr\n'), (result, written))


if __name__ == '__main__':
    unittest.main()
