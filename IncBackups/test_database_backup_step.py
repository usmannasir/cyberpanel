"""An incremental backup saves the dump it has just made, or fails."""
import os
import shlex
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical.test_child_domain_conversion import load_method

SOURCE = 'IncBackups/IncBackupsControl.py'
ROOT = Path(__file__).resolve().parents[1]
TEMPORARY = '/usr/local/CyberCP/tmp'


def dump_database_name(path):
    namespace = {}
    source = (ROOT / SOURCE).read_text()
    start = source.index('def dump_database_name(path):')
    exec(source[start:source.index('\n\n\n', start)], namespace)
    return namespace['dump_database_name'](path)


class Runner:
    """The command runner: records every command with the account it runs as."""

    debugPath = '/nonexistent-debug'

    def __init__(self, copy_fails=False):
        self.copy_fails = copy_fails
        self.ran = []

    def executioner(self, command, user=None, shell=False):
        self.ran.append((command, user))
        return 1

    def outputExecutioner(self, command, user=None, shell=None, dir=None, retRequired=None):
        self.ran.append((command, user))
        if command.startswith('cp ') and self.copy_fails:
            return 0, 'cp: cannot open the dump for reading: Permission denied\n'
        return (1, '') if retRequired else ''


class BackupStepTests(unittest.TestCase):
    def run_step(self, names=('shop_db',), copy_fails=False, snapshot=1, dump=1):
        self.runner = Runner(copy_fails)
        self.dump = mock.Mock(return_value=dump)
        self.status = mock.Mock()
        namespace = dict(os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: path == TEMPORARY)), shlex=shlex,
                         ProcessUtilities=self.runner,
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=SimpleNamespace(createDatabaseBackup=self.dump)),
                         logging=SimpleNamespace(statusWriter=self.status, writeToFile=mock.Mock()))
        remove = load_method(SOURCE, 'IncJobs', 'removeDump', dict(namespace))
        step = load_method(SOURCE, 'IncJobs', 'backupDatabases', namespace)

        def saved(path, kind):
            # What is in the website's directory at the moment the snapshot is made.
            self.runner.ran.append(('snapshot ' + path, 'restic'))
            return snapshot

        job = SimpleNamespace(
            website=SimpleNamespace(domain='example.com', databases_set=SimpleNamespace(
                all=lambda: [SimpleNamespace(dbName=name) for name in names])),
            externalApp='examp1234', statusPath='/dev/null', backupDestinations='local',
            localFunction=mock.Mock(side_effect=saved))
        job.removeDump = lambda path, user=None: remove(job, path, user)
        self.job = job
        return step(job)

    def commands(self):
        return [entry for entry in self.runner.ran if 'CyberCP/tmp' not in entry[0] or '.sql' in entry[0]]

    def test_fresh_dump_is_handed_to_the_website_copied_saved_and_removed(self):
        self.assertEqual(1, self.run_step())
        dump, copy = TEMPORARY + '/shop_db.sql', '/home/example.com/shop_db.sql'
        self.assertEqual([
            ('rm -f ' + copy, 'examp1234'),                    # nothing stale can be saved
            ('chown examp1234:examp1234 ' + dump, None),       # the private dump goes to the website's account
            ('cp %s %s' % (dump, copy), 'examp1234'),
            ('snapshot ' + copy, 'restic'),
            ('rm -f ' + dump, None),
            ('rm -f ' + copy, 'examp1234'),
        ], self.commands())
        self.dump.assert_called_once_with('shop_db', TEMPORARY, use_compression=False)

    def test_failed_copy_fails_the_job_and_saves_nothing(self):
        self.assertEqual(0, self.run_step(copy_fails=True))
        self.job.localFunction.assert_not_called()
        message = self.status.call_args[0][1]
        self.assertIn('shop_db', message)
        self.assertIn('Permission denied', message)
        self.assertIn('[5009]', message)
        # Neither file stays behind for a later run to save.
        self.assertEqual([('rm -f %s/shop_db.sql' % TEMPORARY, None), ('rm -f /home/example.com/shop_db.sql', 'examp1234')],
                         self.commands()[-2:])

    def test_copy_is_checked_by_its_exit_status(self):
        source = (ROOT / SOURCE).read_text()
        self.assertIn("copied, output = ProcessUtilities.outputExecutioner(\n"
                      "                        command, self.externalApp, shell=False, retRequired=True)", source)
        self.assertNotIn("command = 'cp %s %s' % (dbPath, dbPathNew)", source)

    def test_failed_dump_or_snapshot_fails_the_job_and_leaves_no_dump(self):
        self.assertEqual(0, self.run_step(dump=0))
        self.job.localFunction.assert_not_called()
        self.assertEqual(0, self.run_step(snapshot=0))
        self.assertEqual([('rm -f %s/shop_db.sql' % TEMPORARY, None), ('rm -f /home/example.com/shop_db.sql', 'examp1234')],
                         self.commands()[-2:])

    def test_every_database_of_the_website_is_saved(self):
        self.assertEqual(1, self.run_step(names=('shop_db', 'tools')))
        self.assertEqual(['/home/example.com/shop_db.sql', '/home/example.com/tools.sql'],
                         [call[0][0] for call in self.job.localFunction.call_args_list])

    def test_database_name_is_one_argument_of_every_command(self):
        name = 'shop db;x'
        self.assertEqual(1, self.run_step(names=(name,)))
        for command, user in self.commands():
            if user == 'restic':
                continue
            words = shlex.split(command)
            self.assertTrue(all(word.count(name) <= 1 for word in words), command)
            self.assertIn(words[-1], (TEMPORARY + '/' + name + '.sql', '/home/example.com/' + name + '.sql'), command)
            self.assertLessEqual(len(words), 3, command)


class SnapshotNameTests(unittest.TestCase):
    def test_only_the_ending_is_cut_from_the_file_name(self):
        for path, name in (('/home/example.com/orders.sql', 'orders'), ('/home/example.com/tools.sql', 'tools'),
                           ('/home/example.com/sql.sql', 'sql'), ('/home/example.com/sales_q.sql', 'sales_q'),
                           ('/home/example.com/mysql.sql', 'mysql'), ('x.sql.sql', 'x.sql'), ('plain', 'plain'),
                           ('/home/example.com/a.b.sql', 'a.b')):
            self.assertEqual(name, dump_database_name(path), path)

    def test_local_snapshot_is_recorded_under_the_whole_database_name(self):
        saved = []

        class Snapshots:
            def __init__(self, **values):
                self.values = values

            def save(self):
                saved.append(self.values)

        runner = Runner()
        runner.outputExecutioner = lambda command, user=None, **options: (
            runner.ran.append((command, user)) or 'snapshot 1a2b3c4d saved')
        namespace = dict(os=SimpleNamespace(path=SimpleNamespace(isfile=lambda path: False)), shlex=shlex,
                         ProcessUtilities=runner, JobSnapshots=Snapshots, dump_database_name=dump_database_name,
                         extract_snapshot_id=lambda output: '1a2b3c4d',
                         logging=SimpleNamespace(statusWriter=mock.Mock(), writeToFile=mock.Mock()))
        save = load_method(SOURCE, 'IncJobs', 'localFunction', namespace)
        job = SimpleNamespace(website=SimpleNamespace(domain='example.com'), repoPath='/home/example.com/incbackup',
                              passwordFile='/home/example.com/example.com', externalApp='examp1234', jobid='job',
                              backupDestinations='local', statusPath='/dev/null')
        for name in ('tools', 'sales_q', 'mysql', 'shop db'):
            self.assertEqual(1, save(job, '/home/example.com/%s.sql' % name, 'database'))
            self.assertEqual('database:' + name, saved[-1]['type'])
            command = runner.ran[-1][0]
            self.assertEqual('/home/example.com/%s.sql' % name, shlex.split(command)[4])

    def test_every_snapshot_is_named_through_the_same_function(self):
        source = (ROOT / SOURCE).read_text()
        self.assertNotIn("rstrip('.sql')", source)
        self.assertEqual(3, source.count("dump_database_name(backupPath)"))


class ArchiveBackupTests(unittest.TestCase):
    def test_archive_backup_moves_the_dump_with_quoted_names(self):
        source = (ROOT / 'plogical' / 'backupUtilities.py').read_text()
        self.assertNotIn("f'mv /home/cyberpanel/{dbName}", source)
        self.assertEqual(3, source.count("command = 'mv %s %s' % (shlex.quote(f'/home/cyberpanel/{dbName}."))


if __name__ == '__main__':
    unittest.main()
