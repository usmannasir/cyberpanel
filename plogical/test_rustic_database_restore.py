"""A database is restored from a snapshot by the panel's own account without switching users itself."""
import io
import shlex
import subprocess
from types import SimpleNamespace
import unittest

from plogical import databaseImport
from plogical.test_child_domain_conversion import load_method


def restore(user, stream_result=1, import_result=1, dump_code=0):
    calls = SimpleNamespace(popen=[], stream=[], imports=[])

    def popen(command, **options):
        calls.popen.append((command, options))
        return SimpleNamespace(stdout=io.BytesIO(b'dump from the repository'), returncode=dump_code,
                               wait=lambda: dump_code)

    def stream(command, account, sink):
        calls.stream.append((command, account))
        sink.write(b'CREATE TABLE kept (id INT);\xff\xfe')
        return stream_result

    def import_dump(database, feed, host, port, owner):
        sink = io.BytesIO()
        fed = feed(sink)
        calls.imports.append(SimpleNamespace(database=database, host=host, port=port, owner=owner, fed=fed,
                                             received=sink.getvalue()))
        return import_result if fed and import_result else 0

    function = load_method('plogical/mysqlUtilities.py', 'mysqlUtilities', 'restoreRusticDatabase', dict(
        shlex=shlex, getpass=SimpleNamespace(getuser=lambda: user),
        subprocess=SimpleNamespace(Popen=popen, PIPE=subprocess.PIPE, DEVNULL=subprocess.DEVNULL),
        ProcessUtilities=SimpleNamespace(streamCommand=stream),
        databaseImport=SimpleNamespace(import_dump=import_dump, copy=databaseImport.copy,
                                       LOADED=databaseImport.LOADED,
                                       LOADED_OBJECTS_KEPT=databaseImport.LOADED_OBJECTS_KEPT),
        mysqlUtilities=SimpleNamespace(registeredUser=lambda name: 'site_user'),
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
        self.assertNotIn('sudo', shlex.split(command))
        self.assertEqual([], calls.popen)

    def test_dump_is_loaded_by_the_import_that_may_use_this_database_only(self):
        for user in ('cyberpanel', 'root'):
            result, calls = restore(user)
            job, = calls.imports
            self.assertEqual(('site_db', 'localhost', '3306', 'site_user'),
                             (job.database, job.host, job.port, job.owner))
            # No database client is started here: the administrative account never reads the dump.
            self.assertEqual([], [command for command, options in calls.popen if command[0] == 'mysql'])
        self.assertEqual(b'dump from the repository', job.received)
        self.assertEqual(b'CREATE TABLE kept (id INT);\xff\xfe', restore('cyberpanel')[1].imports[0].received)

    def test_failed_dump_or_failed_import_is_reported(self):
        self.assertEqual(0, restore('cyberpanel', stream_result=0)[0])
        self.assertEqual(0, restore('cyberpanel', import_result=0)[0])
        self.assertEqual(0, restore('root', dump_code=1)[0])
        self.assertEqual(0, restore('root', import_result=0)[0])

    def test_loaded_dump_whose_objects_stay_with_the_import_account_is_not_a_failure(self):
        for user in ('cyberpanel', 'root'):
            self.assertEqual(2, restore(user, import_result=2)[0])

    def test_root_callers_keep_the_direct_pipeline(self):
        result, calls = restore('root')
        self.assertEqual(1, result)
        self.assertEqual([], calls.stream)
        self.assertEqual(['sudo', '-u', 'examp1234', 'rustic'], calls.popen[0][0][:4])
        self.assertEqual(1, len(calls.popen))


class RefusalReportTests(unittest.TestCase):
    def test_refused_restore_can_be_reported_as_a_failure(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'plogical' / 'Backupsv2.py').read_text()
        routine = source[source.index('    def InitiateRestore(self):'):]
        self.assertLess(routine.index('self.FinalPathRuctic ='), routine.index('snapshot_id(self.data['))


if __name__ == '__main__':
    unittest.main()
