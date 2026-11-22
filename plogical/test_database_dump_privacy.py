"""Database dumps and the dump program's option file are private; names in command lines are single arguments."""
import json
import os
import shlex
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities

CREDENTIALS = json.dumps({'mysqluser': 'root', 'mysqlpassword': 'fixture', 'mysqlport': 3306,
                          'mysqlhost': 'localhost'})


class OptionFileTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = os.path.join(self.directory.name, '.my.cnf')
        previous = os.umask(0o022)
        self.addCleanup(os.umask, previous)

    def write(self):
        with mock.patch.object(module.os, 'fchown'):
            mysqlUtilities.writeClientDefaults(self.path, 'fixture-password')

    def test_file_made_by_root_goes_to_the_panel_account(self):
        entry = SimpleNamespace(pw_uid=1001, pw_gid=1002)
        with mock.patch.object(module.os, 'geteuid', return_value=0), \
                mock.patch.object(module.pwd, 'getpwnam', return_value=entry), \
                mock.patch.object(module.os, 'fchown') as chown:
            mysqlUtilities.writeClientDefaults(self.path, 'fixture-password')
        self.assertEqual((1001, 1002), chown.call_args[0][1:])

    def test_file_is_private_whatever_the_umask_is(self):
        self.write()
        self.assertEqual(0o600, stat.S_IMODE(os.stat(self.path).st_mode))
        with open(self.path) as stream:
            content = stream.read()
        self.assertIn('[mysqldump]\nuser=root\npassword=fixture-password\n', content)

    def test_existing_file_or_link_is_never_written_into(self):
        target = os.path.join(self.directory.name, 'elsewhere')
        os.symlink(target, self.path)
        with self.assertRaises(OSError):
            self.write()
        self.assertFalse(os.path.exists(target))
        os.unlink(self.path)
        with open(self.path, 'w') as stream:
            stream.write('kept')
        with self.assertRaises(OSError):
            self.write()
        with open(self.path) as stream:
            self.assertEqual('kept', stream.read())

    def test_no_caller_writes_the_file_first_and_closes_it_afterwards(self):
        from pathlib import Path
        root = Path(__file__).resolve().parents[1]
        for name in ('plogical/mysqlUtilities.py', 'plogical/cPanelImporter.py'):
            source = (root / name).read_text()
            self.assertNotIn("open(cnfPath, 'w')", source, name)


class DumpTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        previous = os.umask(0o022)
        self.addCleanup(os.umask, previous)
        self.commands = []

    def backup(self, name, compressed=False, rustic=0, remove=True):
        def executioner(command, user=None, shell=False):
            self.commands.append(command)
            if remove and command.startswith('rm -f '):
                for path in shlex.split(command)[2:]:
                    try:
                        os.unlink(path)
                    except OSError:
                        pass
            return 1

        def run(command, stdout=None, **options):
            self.commands.append(command)
            stdout.write('-- dump\n')
            return SimpleNamespace(returncode=0, stderr=b'')

        def output(command, user=None, shell=None):
            self.commands.append(command)
            return json.dumps({'id': 'abc', 'summary': {'files_new': 1, 'total_duration': 1}}) + '\n'

        with mock.patch('builtins.open', mock.mock_open(read_data=CREDENTIALS)), \
                mock.patch.object(module.os.path, 'exists', return_value=True), \
                mock.patch.object(module.os.path, 'getsize', return_value=10), \
                mock.patch.object(mysqlUtilities, 'saveBackupMetadata'), \
                mock.patch.object(module.ProcessUtilities, 'executioner', side_effect=executioner), \
                mock.patch.object(module.ProcessUtilities, 'outputExecutioner', side_effect=output), \
                mock.patch.object(module.subprocess, 'run', side_effect=run), \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            return mysqlUtilities.createDatabaseBackup(name, self.directory.name, rustic, "'repo of site'", 'siteuser',
                                                       use_compression=compressed, use_new_features=False)

    def test_dump_file_is_private_whatever_the_umask_is(self):
        self.assertEqual(1, self.backup('shop_db'))
        path = os.path.join(self.directory.name, 'shop_db.sql')
        self.assertEqual(0o600, stat.S_IMODE(os.stat(path).st_mode))

    def test_dump_is_never_written_into_a_file_that_is_already_there(self):
        path = os.path.join(self.directory.name, 'shop_db.sql')
        with open(path, 'w') as stream:
            stream.write('somebody else put this here')
        self.assertEqual(0, self.backup('shop_db', remove=False))
        with open(path) as stream:
            self.assertEqual('somebody else put this here', stream.read())

    def test_compressed_dump_is_made_private_by_the_shell_that_writes_it(self):
        self.assertEqual(1, self.backup('shop_db', compressed=True))
        command, owner = self.commands[-2:]
        self.assertTrue(command.startswith('umask 077; mysqldump '), command)
        self.assertEqual(['chown', 'cyberpanel:cyberpanel', os.path.join(self.directory.name, 'shop_db.sql.gz')],
                         shlex.split(owner))

    def test_dump_made_by_root_goes_to_the_panel_account(self):
        entry = SimpleNamespace(pw_uid=1001, pw_gid=1002)
        with mock.patch.object(module.os, 'geteuid', return_value=0), \
                mock.patch.object(module.pwd, 'getpwnam', return_value=entry) as lookup, \
                mock.patch.object(module.os, 'fchown') as chown:
            self.assertEqual(1, self.backup('shop_db'))
        lookup.assert_called_once_with('cyberpanel')
        self.assertEqual((1001, 1002), chown.call_args[0][1:])
        with mock.patch.object(module.os, 'geteuid', return_value=1001), mock.patch.object(module.os, 'fchown') as chown:
            self.assertEqual(1, self.backup('shop_db'))
        chown.assert_not_called()

    def test_unusual_name_is_one_argument_in_every_command_line(self):
        name = 'shop db;id>x'
        self.assertEqual(1, self.backup(name))
        remove, dump = self.commands
        self.assertEqual(['rm', '-f', os.path.join(self.directory.name, name + '.sql')], shlex.split(remove))
        self.assertEqual(name, dump[-1])

        self.commands = []
        self.assertEqual(1, self.backup(name, compressed=True))
        pipeline = self.commands[-2]
        self.assertEqual(os.path.join(self.directory.name, name + '.sql.gz'), shlex.split(self.commands[-1])[-1])
        dump_part, _, file_part = pipeline.partition(' | gzip -c > ')
        self.assertEqual(name, shlex.split(dump_part)[-1])
        self.assertEqual([os.path.join(self.directory.name, name + '.sql.gz')], shlex.split(file_part))

        self.commands = []
        self.assertEqual((1, 'abc'), self.backup(name, rustic=1))
        dump_part, _, rustic_part = self.commands[-1].partition(' | ')
        self.assertEqual(name, shlex.split(dump_part.replace(' 2>/dev/null', ''))[-1])
        words = shlex.split(rustic_part.replace(' 2>/dev/null', ''))
        self.assertEqual(name + '.sql', words[words.index('--stdin-filename') + 1])

    def test_name_is_one_argument_of_the_dump_command(self):
        command = mysqlUtilities.buildMysqldumpCommand('root', 'localhost', 3306, 'shop db;id', False, False)
        self.assertEqual('shop db;id', shlex.split(command)[-1])
        self.assertEqual('shop_db', shlex.split(
            mysqlUtilities.buildMysqldumpCommand('root', 'localhost', 3306, 'shop_db', False, False))[-1])

    def test_name_that_is_an_option_or_a_path_is_not_backed_up(self):
        for name in ('-rf', '--result-file=/etc/passwd', '../../etc/cron.d/x', 'a/b', '', '.', '..', 'a\nb', 'a\x00b',
                     None, 'x' * 65):
            self.commands = []
            self.assertEqual(0, self.backup(name), repr(name))
            self.assertEqual([], self.commands)


class DirectoryTests(unittest.TestCase):
    def test_directories_that_hold_dumps_stay_closed_to_other_accounts(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'IncBackups' / 'IncBackupsControl.py').read_text()
        self.assertNotIn('chmod 755 /home/cyberpanel', source)
        self.assertIn("command = 'chmod 700 /home/cyberpanel'", source)
        self.assertNotIn("'chmod 711 %s' % (UploadPath)", source)
        self.assertIn("'chmod 700 %s' % (UploadPath)", source)


if __name__ == '__main__':
    unittest.main()
