"""A database is restored from a snapshot by the panel's own account without switching users itself."""
import io
import shlex
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.test_child_domain_conversion import load_method


class Sink(io.BytesIO):
    def close(self):
        self.closed_by_caller = True


def restore(user, stream_result=1, import_code=0, dump_code=0):
    calls = SimpleNamespace(popen=[], stream=[])

    def popen(command, **options):
        calls.popen.append((command, options))
        if command[0] == 'mysql':
            return SimpleNamespace(stdin=Sink(), returncode=import_code, wait=lambda: import_code,
                                   communicate=lambda: (None, None))
        return SimpleNamespace(stdout=Mock(), returncode=dump_code, wait=lambda: dump_code)

    def stream(command, account, sink):
        calls.stream.append((command, account))
        sink.write(b'CREATE TABLE kept (id INT);\xff\xfe')
        return stream_result

    function = load_method('plogical/mysqlUtilities.py', 'mysqlUtilities', 'restoreRusticDatabase', dict(
        shlex=shlex, getpass=SimpleNamespace(getuser=lambda: user),
        subprocess=SimpleNamespace(Popen=popen, PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL),
        ProcessUtilities=SimpleNamespace(streamCommand=stream),
        logging=SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=lambda *a: None))))
    result = function('site_db', "'rclone:team drive:example.com'", 'examp1234', 'abcdef0123456789',
                      'root', 'localhost', '3306')
    return result, calls


class PanelAccountTests(unittest.TestCase):
    def test_dump_runs_as_the_website_account_through_the_helper(self):
        result, calls = restore('cyberpanel')
        self.assertEqual(1, result)
        (command, account), = calls.stream
        self.assertEqual('examp1234', account)
        self.assertEqual(['rustic', '-r', 'rclone:team drive:example.com', 'dump',
                          'abcdef0123456789:site_db.sql', '--password', '', '2>/dev/null'], shlex.split(command))
        (mysql, options), = calls.popen
        self.assertEqual(['mysql', '--defaults-file=/home/cyberpanel/.my.cnf'], mysql[:2])
        self.assertEqual('site_db', mysql[-1])
        self.assertNotIn('sudo', mysql + shlex.split(command))

    def test_failed_dump_or_failed_import_is_reported(self):
        self.assertEqual(0, restore('cyberpanel', stream_result=0)[0])
        self.assertEqual(0, restore('cyberpanel', import_code=1)[0])

    def test_root_callers_keep_the_direct_pipeline(self):
        result, calls = restore('root')
        self.assertEqual(1, result)
        self.assertEqual([], calls.stream)
        self.assertEqual(['sudo', '-u', 'examp1234', 'rustic'], calls.popen[0][0][:4])


class RefusalReportTests(unittest.TestCase):
    def test_refused_restore_can_be_reported_as_a_failure(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'plogical' / 'Backupsv2.py').read_text()
        routine = source[source.index('    def InitiateRestore(self):'):]
        self.assertLess(routine.index('self.FinalPathRuctic ='), routine.index('snapshot_id(self.data['))


class StreamTests(unittest.TestCase):
    def stream(self, chunks):
        sent = []

        class Socket:
            def sendall(self, data):
                sent.append(data)

            def recv(self, size):
                return chunks.pop(0) if chunks else b''

            def close(self):
                pass

        helper = SimpleNamespace(setupUDSConnection=lambda: [Socket(), 'None'], token='TOKEN')
        function = load_method('plogical/processUtilities.py', 'ProcessUtilities', 'streamCommand', dict(
            ProcessUtilities=helper, logging=SimpleNamespace(writeToFile=lambda *a: None), os=__import__('os')))
        sink = io.BytesIO()
        return function('rustic dump x', 'examp1234', sink), sink.getvalue(), sent

    def test_output_is_passed_on_as_bytes_and_the_last_byte_is_the_exit_status(self):
        result, written, sent = self.stream([b'ab\xff', b'\xfec', b'd\x00'])
        self.assertEqual((1, b'ab\xff\xfecd'), (result, written))
        self.assertEqual([b'TOKEN-u examp1234 rustic dump x'], sent)

    def test_exit_status_alone_and_split_across_reads(self):
        self.assertEqual((1, b''), self.stream([b'\x00'])[:2])
        self.assertEqual((1, b'abc'), self.stream([b'abc', b'\x00'])[:2])
        self.assertEqual((0, b'abc\x00'), self.stream([b'abc\x00', b'\x01'])[:2])

    def test_failure_and_no_reply_are_reported(self):
        self.assertEqual(0, self.stream([b'partial', b'\x02'])[0])
        self.assertEqual(0, self.stream([])[0])


if __name__ == '__main__':
    unittest.main()
