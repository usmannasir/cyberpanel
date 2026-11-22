"""A restore asked for through the panel names only this website's own data."""
import ast
import json
from pathlib import Path
import shlex
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import MagicMock, patch

from IncBackups import mailArchive
from plogical.backupV2Repository import (
    own_mailbox,
    restore_command,
    restore_target,
    snapshot_id,
)

ROOT = Path(__file__).resolve().parents[1]
SNAPSHOT = 'a3f1c9d2' * 8
DOMAIN = 'example.com'


class SnapshotIdTests(unittest.TestCase):
    def test_full_and_short_identifiers_are_accepted(self):
        for value in (SNAPSHOT, SNAPSHOT[:8], SNAPSHOT[:16]):
            self.assertEqual(value, snapshot_id(value))

    def test_anything_else_is_refused(self):
        for value in ('latest', SNAPSHOT[:7], SNAPSHOT + 'a', SNAPSHOT.upper(), SNAPSHOT + ' --delete',
                      SNAPSHOT + '\n', SNAPSHOT[:8] + ';id', '-r', '', None, 12345678, [SNAPSHOT]):
            with self.assertRaises(ValueError, msg=repr(value)):
                snapshot_id(value)


class RestoreTargetTests(unittest.TestCase):
    def test_the_sites_own_files_mail_and_databases_are_classified(self):
        for path, expected in (
                ('/home/example.com', ('files', '/home/example.com')),
                ('/home/example.com/public_html/wp-content', ('files', '/home/example.com/public_html/wp-content')),
                ('/home/example.com/public_html/My Photos', ('files', '/home/example.com/public_html/My Photos')),
                ('/home/backup/example.com/config.json', ('files', '/home/backup/example.com/config.json')),
                # Mail as it is stored now: one archive, named after the website.
                ('vmail-example.com.tar', ('mailarchive', 'vmail-example.com.tar')),
                # Mail as earlier versions stored it. It is recognised so that
                # the restore can say why it is not done.
                ('/home/vmail/example.com', ('mail', '/home/vmail/example.com')),
                ('/home/vmail/example.com/info/Maildir', ('mail', '/home/vmail/example.com/info/Maildir')),
                ('exam_wp.sql', ('database', 'exam_wp'))):
            self.assertEqual(expected, restore_target(path, DOMAIN), path)
        self.assertEqual('vmail-example.com.tar', mailArchive.archive_name(DOMAIN))

    def test_paths_outside_the_site_are_refused(self):
        for path in ('/home/other.com', '/home/example.com.evil', '/home/example.comx/public_html',
                     '/home/vmail/other.com', '/home/vmail', '/home/vmail/example.com.evil/x',
                     '/home/example.com/../other.com', '/home/example.com/public_html/..',
                     '/home/example.com//public_html', '/home/example.com/./x', '/home/example.com/',
                     'home/example.com', '/etc', '/', '/home', '/home/backup/example.com',
                     '/home/backup/other.com/config.json', '/home/backup/example.com/other.json',
                     '/home/example.com/x\n/etc', '/home/example.com/x\ty', '/home/example.com/\x00',
                     'vmail-other.com.tar', 'vmail-example.com.evil.tar', '/vmail-example.com.tar',
                     'vmail-example.com.tar/x', 'vmail-example.com.tar/../x', './vmail-example.com.tar',
                     'vmail-.tar', 'vmail-example.com.tar\n',
                     '', None, 7, ['/home/example.com']):
            with self.assertRaises(ValueError, msg=repr(path)):
                restore_target(path, DOMAIN)

    def test_mail_is_recognised_only_as_the_sites_own_mail_directory(self):
        # A directory merely named like the mail store, inside the site, is site data.
        self.assertEqual('files', restore_target('/home/example.com/home/vmail', DOMAIN)[0])
        self.assertEqual('files', restore_target('/home/example.com/x/home/vmail/example.com', DOMAIN)[0])

    def test_database_names_are_plain_identifiers(self):
        for path in ('mysql; drop.sql', '--init-command=x.sql', '-x.sql', 'a/b.sql', '../x.sql', '.sql',
                     'a b.sql', 'a.sql.sql', 'x' * 65 + '.sql', "a'b.sql", 'a`b.sql'):
            with self.assertRaises(ValueError, msg=path):
                restore_target(path, DOMAIN)

    def test_domain_that_is_not_a_domain_name_selects_nothing(self):
        for domain in ('', '..', 'a/b', 'a b', None):
            with self.assertRaises(ValueError, msg=repr(domain)):
                restore_target('/home/x', domain)


class RestoreCommandTests(unittest.TestCase):
    def test_snapshot_and_path_reach_the_command_as_single_arguments(self):
        path = '/home/example.com/public_html/My Photos; $(id) `id` "x" \'y\''
        command = restore_command("'rclone:team drive:example.com'", SNAPSHOT, path)
        arguments = shlex.split(command.replace(' 2>/dev/null', ''))
        self.assertEqual(['rustic', '-r', 'rclone:team drive:example.com', 'restore',
                          SNAPSHOT + ':' + path, path, '--password', ''], arguments)
        self.assertTrue(command.endswith(' 2>/dev/null'))

    def test_unchecked_snapshot_is_not_formatted(self):
        with self.assertRaises(ValueError):
            restore_command('/home/example.com/incrementalbackups', 'latest; id', '/home/example.com')


class MailboxTests(unittest.TestCase):
    def test_only_mailboxes_of_the_sites_own_domain_are_restored(self):
        self.assertTrue(own_mailbox('info@example.com', DOMAIN))
        self.assertTrue(own_mailbox('Info@EXAMPLE.com', DOMAIN))
        for email in ('ceo@victim.com', 'info@example.com.evil', 'info@sub.example.com', 'info@',
                      '@example.com', 'info', 'a@b@example.com', 'in fo@example.com', '', None, 7):
            self.assertFalse(own_mailbox(email, DOMAIN), repr(email))


class RestoreRoutineTests(unittest.TestCase):
    """The restore routine itself: what it runs for a hostile request and for a config file."""

    def setUp(self):
        tree = ast.parse((ROOT / 'plogical/Backupsv2.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CPBackupsV2')
        self.methods = {node.name: node for node in cls.body if isinstance(node, ast.FunctionDef)}
        self.root = MagicMock()
        self.root.debugPath = '/does-not-exist'
        self.mysql = MagicMock()
        self.databases = MagicMock()
        self.mail = MagicMock()
        self.website = SimpleNamespace(domain=DOMAIN, externalApp='examp1234', BackupLock=0, save=lambda: None)
        websites = SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: self.website))
        self.modules = {
            'websiteFunctions.models': SimpleNamespace(Websites=websites),
            'plogical.mysqlUtilities': SimpleNamespace(mysqlUtilities=self.mysql),
            'databases.models': SimpleNamespace(Databases=self.databases, DatabasesUsers=MagicMock()),
            'dns.models': SimpleNamespace(Domains=MagicMock()),
            'plogical.dnsUtilities': SimpleNamespace(DNS=MagicMock()),
            'plogical.mailUtilities': SimpleNamespace(mailUtilities=self.mail),
        }
        self.statuses = []

    def function(self, name):
        """A method of the class as a plain function."""
        method = self.methods[name]
        method.decorator_list = []
        namespace = {}
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'Backupsv2.py', 'exec'), namespace)
        return namespace[name]

    def routine(self, name, data):
        status = type('CPBackupsV2', (), {'FAILED': 0, 'RUNNING': 3, 'COMPLETED': 1,
                                          'FetchCurrentTimeStamp': staticmethod(lambda: '0'),
                                          'StatusText': staticmethod(self.function('StatusText'))})
        namespace = dict(os=SimpleNamespace(path=SimpleNamespace(exists=lambda path: True)), json=json,
                         time=MagicMock(), logging=MagicMock(), ProcessUtilities=self.root,
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=self.mysql,
                                                        restoreDatabaseBackup=self.mysql.restoreDatabaseBackup),
                         CPBackupsV2=status, shlex=shlex, snapshot_id=snapshot_id,
                         restore_target=restore_target, restore_command=restore_command,
                         own_mailbox=own_mailbox)
        exec(compile(ast.Module(body=[self.methods[name]], type_ignores=[]), 'Backupsv2.py', 'exec'), namespace)
        instance = SimpleNamespace(
            data=dict(domain=DOMAIN, BasePath='/home/backup', **data), website=self.website,
            repo='/home/example.com/incrementalbackups',
            UpdateStatus=lambda message, state: self.statuses.append((message, state)))
        instance.RestoreConfig = lambda: (1, None)
        with patch.dict(sys.modules, self.modules):
            return namespace[name](instance)

    def commands(self):
        calls = self.root.outputExecutioner.call_args_list + self.root.executioner.call_args_list
        return [call[0][0] for call in calls]

    def test_hostile_snapshot_or_path_stops_before_any_command(self):
        for data in (dict(snapshotid=SNAPSHOT + ' --delete', path='/home/example.com'),
                     dict(snapshotid=SNAPSHOT, path='/home/vmail/other.com'),
                     dict(snapshotid=SNAPSHOT, path='/home/vmail/example.com/../other.com'),
                     dict(snapshotid=SNAPSHOT, path='/home/example.com/x\n/home/vmail'),
                     dict(snapshotid=SNAPSHOT, path='/home/vmail; id'),
                     dict(snapshotid=SNAPSHOT, path='mysql; x.sql'),
                     dict(snapshotid='latest', path='exam_wp.sql')):
            self.root.reset_mock()
            self.assertEqual(0, self.routine('InitiateRestore', data), data)
            self.assertEqual([], self.commands(), data)
            self.mysql.restoreDatabaseBackup.assert_not_called()

    def test_site_files_are_restored_as_the_sites_own_user(self):
        self.root.outputExecutioner.side_effect = ['10\n', '5000\n', (1, 'restored')]
        self.assertEqual(1, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT,
                                                                path='/home/example.com/public_html')))
        command, user = self.root.outputExecutioner.call_args_list[-1][0][:2]
        self.assertEqual('examp1234', user)
        self.assertEqual(restore_command('/home/example.com/incrementalbackups', SNAPSHOT,
                                         '/home/example.com/public_html'), command)

    def restores(self):
        """The commands that restore something, apart from the questions about disk space and the working folder."""
        return [command for command in self.commands()
                if 'rustic' in command or 'rclone' in command or mailArchive.PROGRAM in command]

    def test_mail_archive_is_restored_by_the_helper_under_the_two_accounts(self):
        self.root.outputExecutioner.side_effect = [
            '10\n', '5000\n',
            '[mail-archive] restored 4 mail files written, 32 index files of Dovecot left as they are on the server\n']
        self.assertEqual(1, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT, path='vmail-example.com.tar')))

        call = self.root.outputExecutioner.call_args_list[-1]
        # The helper is started with privilege, to start the two ends and for nothing else.
        self.assertEqual(1, len(call[0]))
        self.assertEqual({}, call[1])
        command = call[0][0]
        self.assertEqual(mailArchive.helper_command('restore', DOMAIN, 'examp1234',
                                                    '/home/example.com/incrementalbackups', program='rustic',
                                                    snapshot=SNAPSHOT), command)
        self.assertEqual([command], self.restores())
        words = shlex.split(command)
        self.assertEqual([mailArchive.PYTHON, mailArchive.PROGRAM, 'restore'], words[:3])
        options = dict(zip(words[3::2], words[4::2]))
        # rustic reads the repository as the website's account, with that
        # account's own storage settings; the mail account writes the mail.
        self.assertEqual({'--domain': DOMAIN, '--account': 'examp1234', '--program': 'rustic',
                          '--repository': '/home/example.com/incrementalbackups', '--snapshot': SNAPSHOT}, options)
        self.assertEqual('vmail', mailArchive.MAIL_ACCOUNT)
        self.assertNotIn('RCLONE_CONFIG', command)
        # What is unpacked is named by the website, not by the request.
        self.assertNotIn('vmail-example.com.tar', command)

        self.assertEqual(('Mail restored: 4 mail files written; 32 index files of Dovecot left as they are on the '
                          'server..,90', 3), self.statuses[-2])
        self.assertEqual(('Completed', 1), self.statuses[-1])

    def test_mail_archive_that_is_not_restored_fails_the_restore(self):
        for said in ('[mail-archive] failed No mail archive could be read from snapshot [200], x. '
                     'Nothing was written.\n', 'Traceback (most recent call last):\n', '', None):
            self.root.reset_mock()
            self.statuses = []
            self.root.outputExecutioner.side_effect = ['10\n', '5000\n', said]
            self.assertEqual(0, self.routine('InitiateRestore',
                                             dict(snapshotid=SNAPSHOT, path='vmail-example.com.tar')), said)
            message, state = self.statuses[-1]
            self.assertEqual(0, state)
            self.assertNotEqual('Completed', message)
            # Nothing a program printed can pass for the marks or the percentage of a status line.
            self.assertNotIn('[', message)
            self.assertNotIn(',', message)

    def test_mail_stored_as_a_folder_tree_is_refused_and_nothing_is_run_for_it(self):
        # Such a tree could only be written back by rustic running with
        # privilege on storage settings the website's account controls.
        for path in ('/home/vmail/example.com', '/home/vmail/example.com/info',
                     '/home/vmail/example.com/info/Maildir/cur'):
            self.root.reset_mock()
            self.statuses = []
            self.root.outputExecutioner.side_effect = ['10\n', '5000\n', (1, 'restored')]
            self.assertEqual(0, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT, path=path)), path)
            # Only the two questions about disk space were asked; nothing was restored, as any account.
            self.assertEqual(2, self.root.outputExecutioner.call_count, path)
            self.assertEqual([], self.restores(), path)
            message, state = self.statuses[-1]
            self.assertEqual(0, state)
            self.assertIn('does not restore mail in that form', message)
            self.assertIn('Take a new backup', message)

    def test_nothing_but_the_sites_own_mail_archive_reaches_the_privileged_helper(self):
        # Another website's archive, or a path made to look like this one's, selects nothing at all.
        for path in ('vmail-other.com.tar', 'vmail-example.com.evil.tar', '/vmail-example.com.tar',
                     'vmail-example.com.tar/../vmail-other.com.tar', '/home/vmail/other.com',
                     '/home/vmail/example.com/../other.com', '/home/vmail'):
            self.root.reset_mock()
            self.assertEqual(0, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT, path=path)), path)
            self.assertEqual([], self.commands(), path)

        # A directory merely named like the mail store, inside the site, is site
        # data: it is restored by rustic as the website's own account.
        self.root.reset_mock()
        self.root.outputExecutioner.side_effect = ['10\n', '5000\n', (1, 'restored')]
        self.assertEqual(1, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT,
                                                                path='/home/example.com/home/vmail')))
        command, user = self.root.outputExecutioner.call_args_list[-1][0][:2]
        self.assertEqual('examp1234', user)
        self.assertEqual(restore_command('/home/example.com/incrementalbackups', SNAPSHOT,
                                         '/home/example.com/home/vmail'), command)

    def test_no_restore_runs_rustic_with_privilege(self):
        # Every command that names rustic is given to the website's account,
        # whatever is restored; the routine sets no storage settings for it.
        for path, answer in (('/home/example.com/public_html', (1, 'restored')),
                             ('vmail-example.com.tar', '[mail-archive] restored 1 mail files written\n'),
                             ('/home/vmail/example.com/info', (1, 'restored'))):
            self.root.reset_mock()
            self.root.outputExecutioner.side_effect = ['10\n', '5000\n', answer]
            self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT, path=path))
            for call in self.root.outputExecutioner.call_args_list + self.root.executioner.call_args_list:
                command = call[0][0]
                self.assertNotIn('RCLONE_CONFIG', command, path)
                if command.startswith('rustic ') or ' rustic -r ' in command:
                    self.assertEqual('examp1234', call[0][1], path)

    def test_database_is_restored_only_when_it_belongs_to_the_website(self):
        self.root.outputExecutioner.side_effect = ['10\n', '5000\n']
        self.databases.objects.filter.return_value.exists.return_value = False
        self.assertEqual(0, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT, path='other_db.sql')))
        self.mysql.restoreDatabaseBackup.assert_not_called()
        self.databases.objects.filter.assert_called_with(dbName='other_db', website=self.website)

        self.root.outputExecutioner.side_effect = ['10\n', '5000\n']
        self.databases.objects.filter.return_value.exists.return_value = True
        self.mysql.restoreDatabaseBackup.return_value = 1
        self.assertEqual(1, self.routine('InitiateRestore', dict(snapshotid=SNAPSHOT, path='exam_wp.sql')))
        arguments = self.mysql.restoreDatabaseBackup.call_args[0]
        self.assertEqual(('exam_wp', 'examp1234', SNAPSHOT), (arguments[0], arguments[7], arguments[8]))

    def test_config_is_read_as_the_site_user_and_foreign_mailboxes_are_left_alone(self):
        config = {'DNSRecords': [], 'databases': [], 'EmailAddresses': [
            {'email': 'info@example.com', 'password': 'hash-1'},
            {'email': 'ceo@victim.com', 'password': 'hash-2'}]}
        self.root.outputExecutioner.side_effect = ['restored', json.dumps(config) + '\n']
        self.mail.createEmailAccount.return_value = (0, 'exists')
        self.mail.changeEmailPassword.return_value = (1, 'None')
        self.assertEqual((1, None), self.routine('RestoreConfig', dict(snapshotid=SNAPSHOT, path='x')))
        restore, read = self.root.outputExecutioner.call_args_list
        self.assertEqual('examp1234', restore[0][1])
        self.assertIn(' %s:/home/backup/example.com/config.json ' % SNAPSHOT, restore[0][0])
        self.assertEqual(('cat /home/example.com/config.json', 'examp1234'), read[0][:2])
        self.mail.createEmailAccount.assert_called_once_with(DOMAIN, 'info', 'hash-1')
        self.mail.changeEmailPassword.assert_called_once_with('info@example.com', 'hash-1', 1)

    def test_config_restore_refuses_an_unchecked_snapshot(self):
        result = self.routine('RestoreConfig', dict(snapshotid=SNAPSHOT + ';id', path='x'))
        self.assertEqual(0, result[0])
        self.assertEqual([], self.commands())


if __name__ == '__main__':
    unittest.main()
