"""Mail is in an incremental backup when the job says so, and comes back from it."""
import errno
import io
import os
import shlex
import shutil
import stat
import subprocess
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from IncBackups import mailArchive
from plogical.test_child_domain_conversion import load_method

SOURCE = 'IncBackups/IncBackupsControl.py'
ROOT = Path(__file__).resolve().parents[1]
SAVED_BY_RESTIC = 'reading from stdin\nsnapshot 1a2b3c4d saved\n'


def content(path):
    with open(path) as handle:
        return handle.read()


class TemporaryFolder(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix='mail-archive-test-')
        self.addCleanup(shutil.rmtree, self.base, True)

    def tree(self, folder, files):
        for name, content in files.items():
            path = os.path.join(folder, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as handle:
                handle.write(content)

    def files_below(self, folder):
        found = {}
        for directory, _, names in os.walk(folder):
            for name in names:
                path = os.path.join(directory, name)
                if not os.path.islink(path):
                    found[os.path.relpath(path, folder)] = content(path)
        return found


class FolderStateTests(TemporaryFolder):
    def test_missing_folder_is_absent(self):
        self.assertEqual(mailArchive.ABSENT, mailArchive.folder_state(os.path.join(self.base, 'example.com')))
        self.assertEqual(mailArchive.ABSENT,
                         mailArchive.folder_state(os.path.join(self.base, 'missing', 'example.com')))

    def test_folder_is_present_even_when_empty(self):
        os.mkdir(os.path.join(self.base, 'example.com'))
        self.assertEqual(mailArchive.PRESENT, mailArchive.folder_state(os.path.join(self.base, 'example.com')))

    def test_file_or_link_in_its_place_is_not_a_folder(self):
        self.tree(self.base, {'file.example': 'x'})
        os.mkdir(os.path.join(self.base, 'real'))
        os.symlink(os.path.join(self.base, 'real'), os.path.join(self.base, 'link.example'))
        for name in ('file.example', 'link.example'):
            self.assertEqual(mailArchive.NOT_A_FOLDER, mailArchive.folder_state(os.path.join(self.base, name)))

    def test_refused_lookup_is_not_taken_for_a_missing_folder(self):
        # What an account that may not enter the mail store is told.
        with mock.patch('os.lstat', side_effect=OSError(errno.EACCES, 'Permission denied')):
            self.assertEqual(mailArchive.UNKNOWN, mailArchive.folder_state('/home/vmail/example.com'))

    @unittest.skipIf(os.geteuid() == 0, 'root may enter every folder')
    def test_folder_behind_a_closed_folder_is_not_taken_for_a_missing_one(self):
        os.makedirs(os.path.join(self.base, 'vmail', 'example.com'))
        os.chmod(os.path.join(self.base, 'vmail'), 0)
        self.addCleanup(os.chmod, os.path.join(self.base, 'vmail'), 0o700)
        self.assertEqual(mailArchive.UNKNOWN,
                         mailArchive.folder_state(os.path.join(self.base, 'vmail', 'example.com')))

    def test_look_tells_a_website_without_mail_from_one_with_mail(self):
        os.mkdir(os.path.join(self.base, 'example.com'))
        self.assertEqual((mailArchive.PRESENT, os.path.join(self.base, 'example.com')),
                         mailArchive.look('example.com', self.base))
        self.assertEqual((mailArchive.NO_FOLDER, os.path.join(self.base, 'other.example')),
                         mailArchive.look('other.example', self.base))
        with mock.patch('os.lstat', side_effect=OSError(errno.EACCES, 'Permission denied')):
            outcome, detail = mailArchive.look('example.com', self.base)
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('not a folder that can be read', detail)

    def test_only_a_domain_name_makes_a_mail_folder(self):
        self.assertEqual('/home/vmail/example.com', mailArchive.mail_folder('example.com'))
        for name in ('', None, '..', 'a/../b', '../etc', 'a/b', '.hidden', '-x', 'a b', 'a..b'):
            with self.assertRaises(mailArchive.Refused, msg=name):
                mailArchive.mail_folder(name)


class OutcomeTests(unittest.TestCase):
    def test_outcome_is_the_last_marked_line(self):
        self.assertEqual((mailArchive.SAVED, '1a2b3c4d'),
                         mailArchive.read_outcome('noise\n[mail-archive] saved 1a2b3c4d\n'))
        self.assertEqual((mailArchive.NO_FOLDER, '/home/vmail/example.com'),
                         mailArchive.read_outcome('[mail-archive] no-mail-folder /home/vmail/example.com'))
        self.assertEqual((mailArchive.RESTORED, '12'), mailArchive.read_outcome('[mail-archive] restored 12\n'))
        self.assertEqual((mailArchive.PRESENT, '/home/vmail/example.com'),
                         mailArchive.read_outcome('[mail-archive] present /home/vmail/example.com\n'))
        self.assertEqual((mailArchive.FAILED, 'tar: .: Cannot open: Permission denied'),
                         mailArchive.read_outcome('[mail-archive] failed tar: .: Cannot open: Permission denied\n'))

    def test_output_without_an_outcome_is_a_failure(self):
        for output in (None, '', 'Traceback (most recent call last):\n  boom\n', '[mail-archive] done\n',
                       'snapshot 1a2b3c4d saved\n'):
            outcome, detail = mailArchive.read_outcome(output)
            self.assertEqual(mailArchive.FAILED, outcome, output)
            self.assertIn('did not report a result', detail)

    def test_command_keeps_every_value_one_word(self):
        command = mailArchive.helper_command('restore', 'example.com', 'examp1234', 's3:s3.amazonaws.com/example.com',
                                             password='pass word; id', aws_key='AKIA$(id)', snapshot='1a2b3c4d')
        words = shlex.split(command)
        self.assertEqual([mailArchive.PYTHON, mailArchive.PROGRAM, 'restore'], words[:3])
        options = dict(zip(words[3::2], words[4::2]))
        self.assertEqual({'--domain': 'example.com', '--account': 'examp1234',
                          '--repository': 's3:s3.amazonaws.com/example.com', '--password': 'pass word; id',
                          '--aws-key': 'AKIA$(id)', '--snapshot': '1a2b3c4d'}, options)
        # The privileged helper adds `sudo` itself to a command that has none; this one is one command.
        from plogical.commandShape import runs_one_command
        self.assertTrue(runs_one_command(command))
        self.assertEqual([mailArchive.PYTHON, mailArchive.PROGRAM, 'look', '--domain', 'example.com'],
                         shlex.split(mailArchive.helper_command('look', 'example.com')))


class ProgramTests(unittest.TestCase):
    def run_program(self, *words):
        with mock.patch('sys.stdout', io.StringIO()) as printed, \
                mock.patch.object(mailArchive, 'run_joined') as joined:
            status = mailArchive.main(list(words))
        joined.assert_not_called()
        return status, mailArchive.read_outcome(printed.getvalue())

    def test_repository_is_never_opened_as_root(self):
        if os.geteuid() != 0:
            self.skipTest('needs root')
        status, (outcome, detail) = self.run_program('backup', '--domain', 'example.com', '--account', 'root',
                                                     '--repository', '/home/example.com/incbackup')
        self.assertEqual((1, mailArchive.FAILED), (status, outcome))
        self.assertIn('not as root', detail)

    def test_request_that_names_no_account_repository_or_domain_is_refused(self):
        for words in (('backup', '--domain', 'example.com', '--repository', '/home/example.com/incbackup'),
                      ('backup', '--domain', 'example.com', '--account', 'nobody'),
                      ('backup', '--domain', 'example.com', '--account', 'nobody', '--repository=--help'),
                      ('restore', '--domain', '../etc', '--account', 'nobody', '--repository', '/x',
                       '--snapshot', '1a2b3c4d'),
                      ('look', '--domain', 'a/b'), ('look',)):
            status, (outcome, detail) = self.run_program(*words)
            self.assertEqual((1, mailArchive.FAILED), (status, outcome), words)

    def test_stored_key_is_named_not_given_as_a_path(self):
        for key in ('../../etc/shadow', '/etc/shadow', 'a/b', '', '.', '..'):
            with self.assertRaises(mailArchive.Refused):
                mailArchive.aws_environment(key)


class JudgeTests(unittest.TestCase):
    FOLDER = '/home/vmail/example.com'

    def test_saved_snapshot_of_a_fully_read_folder_is_a_backup(self):
        self.assertEqual((mailArchive.SAVED, '1a2b3c4d', None),
                         mailArchive.judge_backup(self.FOLDER, 0, '', 0, SAVED_BY_RESTIC))

    def test_mail_that_changed_while_it_was_read_is_still_a_backup(self):
        errors = 'tar: ./qa/Maildir/new/1.host: File removed before we read it\n'
        self.assertEqual((mailArchive.SAVED, '1a2b3c4d', None),
                         mailArchive.judge_backup(self.FOLDER, 1, errors, 0, SAVED_BY_RESTIC))

    def test_folder_that_could_not_be_read_fails_and_its_snapshot_is_discarded(self):
        errors = 'tar: ./qa/Maildir: Cannot open: Permission denied\ntar: Exiting with failure status\n'
        for status in (2, -13, 141):
            outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, status, errors, 0, SAVED_BY_RESTIC)
            self.assertEqual(mailArchive.FAILED, outcome)
            self.assertIn('/home/vmail/example.com exists but could not be read in full', detail)
            self.assertIn('Permission denied', detail)
            self.assertEqual('1a2b3c4d', discard)

    def test_restic_that_fails_or_saves_nothing_fails(self):
        outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, -13, '', 1, 'Fatal: wrong password\n')
        self.assertEqual((mailArchive.FAILED, None), (outcome, discard))
        self.assertIn('wrong password', detail)
        outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, 0, '', 0, 'nothing was said\n')
        self.assertEqual((mailArchive.FAILED, None), (outcome, discard))
        outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, 0, '', 3, SAVED_BY_RESTIC)
        self.assertEqual((mailArchive.FAILED, '1a2b3c4d'), (outcome, discard))

    def test_no_message_of_a_failure_ends_the_job_as_done(self):
        # The job is over for its reader at the first `Completed` in the status file.
        for result in (mailArchive.judge_backup(self.FOLDER, 2, 'x', 0, SAVED_BY_RESTIC),
                       mailArchive.judge_backup(self.FOLDER, 0, '', 1, ''),
                       mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', 1, 'not found', 1, ''),
                       mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', 0, '', 1, '')):
            self.assertNotIn('Completed', result[1])

    def test_restore_is_done_only_when_both_ends_are(self):
        self.assertEqual((mailArchive.RESTORED, '7'),
                         mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', 0, '', 0, '7\n'))
        outcome, detail = mailArchive.judge_restore(
            self.FOLDER, '1a2b3c4d', 1, 'Fatal: cannot dump file: path "/vmail-example.com.tar" not found', 1,
            'empty file\n')
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('No mail archive could be read from snapshot 1a2b3c4d', detail)
        self.assertIn('before CyberPanel 3.0.13 hold no mail archive', detail)
        outcome, detail = mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', 0, '', 1, 'No space left on device\n')
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('stopped before it was done: No space left on device', detail)


def archive_of(*members):
    """A tar archive in memory. A member is (name, kind, value): a file's content or a link's target."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        for name, kind, value in members:
            entry = tarfile.TarInfo(name)
            entry.type = kind
            entry.mode = 0o700 if kind == tarfile.DIRTYPE else 0o600
            entry.mtime = 1700000000
            if kind == tarfile.REGTYPE:
                data = value.encode()
                entry.size = len(data)
                archive.addfile(entry, io.BytesIO(data))
            else:
                entry.linkname = value or ''
                archive.addfile(entry)
    stream.seek(0)
    return stream


class UnpackTests(TemporaryFolder):
    def setUp(self):
        super().setUp()
        self.folder = os.path.join(self.base, 'vmail', 'example.com')
        self.other = os.path.join(self.base, 'vmail', 'other.example')
        self.tree(self.other, {'user/Maildir/cur/1': 'private'})

    def test_mailboxes_come_back_with_their_modes_times_and_links(self):
        written = mailArchive.unpack(archive_of(
            ('.', tarfile.DIRTYPE, None),
            ('./qa', tarfile.DIRTYPE, None),
            ('./qa/Maildir/cur/1.host:2,S', tarfile.REGTYPE, 'first message'),
            ('./qa/Maildir/.Sent/cur/2.host:2,S', tarfile.REGTYPE, 'second message'),
            ('./qa/Maildir/.Archive/cur/1.host:2,S', tarfile.LNKTYPE, './qa/Maildir/cur/1.host:2,S'),
            ('./qa/sieve/managesieve.sieve', tarfile.REGTYPE, 'keep;'),
            ('./qa/.dovecot.sieve', tarfile.SYMTYPE, 'sieve/managesieve.sieve'),
        ), self.folder)
        self.assertEqual(4, written)
        self.assertEqual({'qa/Maildir/cur/1.host:2,S': 'first message',
                          'qa/Maildir/.Sent/cur/2.host:2,S': 'second message',
                          'qa/Maildir/.Archive/cur/1.host:2,S': 'first message',
                          'qa/sieve/managesieve.sieve': 'keep;'}, self.files_below(self.folder))
        message = os.stat(os.path.join(self.folder, 'qa/Maildir/cur/1.host:2,S'))
        self.assertEqual(0o600, stat.S_IMODE(message.st_mode))
        self.assertEqual(1700000000, int(message.st_mtime))
        self.assertEqual(2, message.st_nlink)
        self.assertEqual(0o700, stat.S_IMODE(os.stat(os.path.join(self.folder, 'qa')).st_mode))
        self.assertEqual('sieve/managesieve.sieve', os.readlink(os.path.join(self.folder, 'qa/.dovecot.sieve')))

    def test_newer_mail_stays_and_a_restored_file_replaces_the_one_there(self):
        self.tree(self.folder, {'qa/Maildir/cur/1': 'changed since', 'qa/Maildir/new/9': 'arrived later'})
        os.link(os.path.join(self.folder, 'qa/Maildir/cur/1'), os.path.join(self.base, 'second-name'))
        mailArchive.unpack(archive_of(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'as saved')), self.folder)
        self.assertEqual({'qa/Maildir/cur/1': 'as saved', 'qa/Maildir/new/9': 'arrived later'},
                         self.files_below(self.folder))
        # The file was replaced, not written into: its other name keeps what it had.
        self.assertEqual('changed since', content(os.path.join(self.base, 'second-name')))

    def refused(self, *members):
        before = self.files_below(self.base)
        with self.assertRaises(mailArchive.Refused):
            mailArchive.unpack(archive_of(*members), self.folder)
        return before

    def test_entry_that_leaves_the_folder_is_refused(self):
        for name in ('../other.example/user/Maildir/cur/evil', '/etc/cron.d/evil', 'qa/../../other.example/evil',
                     './..'):
            before = self.refused((name, tarfile.REGTYPE, 'evil'))
            self.assertEqual(before, self.files_below(self.base), name)

    def test_link_that_points_out_of_its_folder_is_refused(self):
        for target in (self.other + '/user/Maildir', '/etc', '../other.example/user/Maildir', 'a/../../x', ''):
            self.refused(('./thief/Maildir', tarfile.SYMTYPE, target))
            self.assertFalse(os.path.lexists(os.path.join(self.folder, 'thief/Maildir')), target)

    def test_second_name_for_a_file_outside_the_archive_is_refused(self):
        for target in ('../other.example/user/Maildir/cur/1', self.other + '/user/Maildir/cur/1', 'qa/absent'):
            self.refused(('./thief/Maildir/cur/1', tarfile.LNKTYPE, target))
            self.assertFalse(os.path.lexists(os.path.join(self.folder, 'thief/Maildir/cur/1')), target)

    def test_nothing_is_written_through_a_link_that_leads_out(self):
        os.makedirs(self.folder)
        os.symlink(self.other, os.path.join(self.folder, 'way-out'))
        before = self.refused(('./way-out/user/Maildir/cur/evil', tarfile.REGTYPE, 'evil'))
        self.assertEqual(before, self.files_below(self.base))
        self.refused(('./way-out', tarfile.DIRTYPE, None))

    def test_devices_and_pipes_are_refused(self):
        for kind in (tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            self.refused(('./qa/thing', kind, None))
            self.assertFalse(os.path.lexists(os.path.join(self.folder, 'qa/thing')))

    def test_writer_does_not_run_as_root(self):
        if os.geteuid() != 0:
            self.skipTest('needs root')
        with mock.patch('sys.stderr', io.StringIO()) as errors:
            self.assertEqual(1, mailArchive.main(['unpack', '--folder', self.folder]))
        self.assertIn('not by root', errors.getvalue())
        self.assertFalse(os.path.exists(self.folder))


@unittest.skipUnless(shutil.which('restic') and shutil.which('tar'), 'needs restic and tar')
class RepositoryTests(TemporaryFolder):
    """The whole way, with real programs, in a temporary folder.

    Started as root, the two ends run as another account, as they do on a
    server; otherwise they run as the account the tests run as.
    """

    def setUp(self):
        super().setUp()
        os.chmod(self.base, 0o755)
        self.account = 'nobody' if os.geteuid() == 0 else None
        self.mail_root = os.path.join(self.base, 'vmail')
        self.repository = os.path.join(self.base, 'incbackup')
        self.password_file = os.path.join(self.base, 'password')
        self.environment = {'RESTIC_CACHE_DIR': os.path.join(self.base, 'cache')}
        with open(self.password_file, 'w') as handle:
            handle.write('repository-password\n')
        os.makedirs(self.mail_root)
        os.makedirs(self.environment['RESTIC_CACHE_DIR'])
        self.give(self.base)
        self.restic('init')

        if os.geteuid() == 0:
            # The writing end is started from this file; the other account must be able to read it.
            program = os.path.join(self.base, 'program')
            os.mkdir(program)
            for name in ('mailArchive.py', 'resticOutput.py', 'IncBackupPath.py'):
                shutil.copy(str(ROOT / 'IncBackups' / name), program)
            patch = mock.patch.object(mailArchive, 'PROGRAM', os.path.join(program, 'mailArchive.py'))
            patch.start()
            self.addCleanup(patch.stop)

    def give(self, path):
        if self.account:
            subprocess.check_call(['chown', '-R', self.account, path])

    def restic(self, *words):
        options = mailArchive.process_options(self.account, self.environment)
        return subprocess.check_output(mailArchive.restic_words(self.repository, self.password_file) + list(words),
                                       stderr=subprocess.STDOUT, **options).decode()

    def back_up(self, domain='example.com'):
        return mailArchive.back_up(domain, self.account, self.repository, self.password_file, self.environment,
                                   mail_root=self.mail_root, mail_account=self.account)

    def restore(self, snapshot, mail_root, domain='example.com'):
        return mailArchive.restore(domain, self.account, self.repository, snapshot, self.password_file,
                                   self.environment, mail_root=mail_root, mail_account=self.account)

    def mailboxes(self):
        folder = os.path.join(self.mail_root, 'example.com')
        files = {'qa/Maildir/cur/1.host:2,S': 'first message\n' * 50,
                 'qa/Maildir/new/2.host': 'second message\n',
                 'second/Maildir/.Sent/cur/3.host:2,S': 'third message\n'}
        self.tree(folder, files)
        # A message copied to another folder is a second name of the same file,
        # and a mailbox's active filter is a link.
        os.makedirs(os.path.join(folder, 'qa/Maildir/.Archive/cur'))
        os.link(os.path.join(folder, 'qa/Maildir/cur/1.host:2,S'),
                os.path.join(folder, 'qa/Maildir/.Archive/cur/1.host:2,S'))
        files['qa/Maildir/.Archive/cur/1.host:2,S'] = files['qa/Maildir/cur/1.host:2,S']
        self.tree(folder, {'qa/sieve/managesieve.sieve': 'keep;'})
        files['qa/sieve/managesieve.sieve'] = 'keep;'
        os.symlink('sieve/managesieve.sieve', os.path.join(folder, 'qa/.dovecot.sieve'))
        os.utime(os.path.join(folder, 'qa/Maildir/new/2.host'), (1700000000, 1700000000))
        for directory, _, _ in os.walk(folder):
            os.chmod(directory, 0o700)
        self.give(folder)
        return files

    def test_mail_is_saved_and_comes_back(self):
        files = self.mailboxes()
        outcome, snapshot = self.back_up()
        self.assertEqual(mailArchive.SAVED, outcome, snapshot)
        self.assertIn(snapshot[:8], self.restic('snapshots'))
        self.assertIn('/vmail-example.com.tar', self.restic('ls', snapshot))

        elsewhere = os.path.join(self.base, 'restored')
        os.mkdir(elsewhere)
        self.give(elsewhere)
        outcome, count = self.restore(snapshot, elsewhere)
        self.assertEqual((mailArchive.RESTORED, '5'), (outcome, count))
        restored = os.path.join(elsewhere, 'example.com')
        self.assertEqual(files, self.files_below(restored))
        self.assertEqual(2, os.stat(os.path.join(restored, 'qa/Maildir/cur/1.host:2,S')).st_nlink)
        self.assertEqual('sieve/managesieve.sieve', os.readlink(os.path.join(restored, 'qa/.dovecot.sieve')))
        self.assertEqual(1700000000, int(os.stat(os.path.join(restored, 'qa/Maildir/new/2.host')).st_mtime))
        self.assertEqual(0o700, stat.S_IMODE(os.stat(os.path.join(restored, 'qa/Maildir')).st_mode))
        if self.account:
            import pwd
            self.assertEqual(pwd.getpwnam(self.account).pw_uid,
                             os.stat(os.path.join(elsewhere, 'example.com/qa/Maildir/new/2.host')).st_uid)

    def test_website_without_a_mail_folder_is_said_to_have_none(self):
        self.assertEqual((mailArchive.NO_FOLDER, os.path.join(self.mail_root, 'example.com')), self.back_up())
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

    def test_folder_that_cannot_be_read_fails_and_leaves_no_snapshot(self):
        self.mailboxes()
        closed = os.path.join(self.mail_root, 'example.com', 'qa', 'Maildir')
        if self.account:
            # A mailbox the mail account may not enter.
            subprocess.check_call(['chown', '-R', 'root', closed])
        else:
            os.chmod(closed, 0)
            self.addCleanup(os.chmod, closed, 0o700)
        outcome, detail = self.back_up()
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('exists but could not be read in full', detail)
        self.assertIn('Permission denied', detail)
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

    def test_snapshot_without_a_mail_archive_is_not_restored(self):
        plain = os.path.join(self.base, 'plain')
        self.tree(plain, {'file': 'x'})
        self.give(plain)
        snapshot = mailArchive.extract_snapshot_id(self.restic('backup', plain))
        outcome, detail = self.restore(snapshot, os.path.join(self.base, 'restored'))
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('No mail archive could be read from snapshot', detail)
        self.assertFalse(os.path.exists(os.path.join(self.base, 'restored', 'example.com', 'file')))

    def test_only_a_snapshot_id_is_asked_of_restic(self):
        for snapshot in ('latest', '--help', '', None, '1a2b3c4d --target /'):
            with self.assertRaises(mailArchive.Refused):
                self.restore(snapshot, self.mail_root)


class Runner:
    """The job's command runner: records each command with the account it runs as."""

    def __init__(self, output):
        self.output = output
        self.ran = []

    def outputExecutioner(self, command, user=None, shell=None, dir=None, retRequired=None):
        self.ran.append((command, user))
        return self.output


class JobStepTests(unittest.TestCase):
    def job(self, output, destination='local', **attributes):
        self.runner = Runner(output)
        self.status = []
        self.saved = []

        class Snapshots:
            def __init__(inner, **values):
                inner.values = values

            def save(inner):
                self.saved.append(inner.values)

        self.namespace = dict(
            mailArchive=mailArchive, ProcessUtilities=self.runner, JobSnapshots=Snapshots,
            logging=SimpleNamespace(statusWriter=lambda path, message, append=None: self.status.append(message)))
        job = SimpleNamespace(website=SimpleNamespace(domain='example.com'), externalApp='examp1234',
                              statusPath='/dev/null', backupDestinations=destination, jobid='job',
                              passwordFile='/home/example.com/example.com', reconstruct='local',
                              sftpFunction=mock.Mock(return_value=0), localFunction=mock.Mock(return_value=1),
                              awsFunction=mock.Mock(return_value=1))
        for name, value in attributes.items():
            setattr(job, name, value)
        repository = load_method(SOURCE, 'IncJobs', 'mailRepository', dict(self.namespace))
        job.mailRepository = lambda destination, domain: repository(job, destination, domain)
        return job

    def step(self, name, job):
        return load_method(SOURCE, 'IncJobs', name, dict(self.namespace))(job)

    def options(self):
        command, user = self.runner.ran[-1]
        # The helper is run with privilege, not as the website: it alone can see the mail store.
        self.assertIsNone(user)
        words = shlex.split(command)
        self.assertEqual([mailArchive.PYTHON, mailArchive.PROGRAM], words[:2])
        return words[2], dict(zip(words[3::2], words[4::2]))

    def test_saved_mail_is_recorded_and_reported(self):
        job = self.job('[mail-archive] saved 1a2b3c4d\n')
        self.assertEqual(1, self.step('emailBackup', job))
        self.assertEqual([dict(job='job', type='email:/home/vmail/example.com', snapshotid='1a2b3c4d',
                               destination='local')], self.saved)
        self.assertEqual('Emails for example.com backed to local.', self.status[-1])
        self.assertEqual(('backup', {'--domain': 'example.com', '--account': 'examp1234',
                                     '--repository': '/home/example.com/incbackup',
                                     '--password-file': '/home/example.com/example.com'}), self.options())
        # restic is not sent to read the mail store as the website's account.
        job.localFunction.assert_not_called()

    def test_website_without_mail_is_said_to_have_none_and_nothing_is_recorded(self):
        job = self.job('[mail-archive] no-mail-folder /home/vmail/example.com\n')
        self.assertEqual(1, self.step('emailBackup', job))
        self.assertEqual([], self.saved)
        self.assertEqual('No mail folder exists for example.com (/home/vmail/example.com): '
                         'there are no emails to back up.', self.status[-1])
        self.assertFalse([line for line in self.status if 'backed to' in line])

    def test_mail_that_was_not_saved_fails_the_job(self):
        for output in ('[mail-archive] failed /home/vmail/example.com exists but could not be read in full, '
                       'so its mail was not backed up: tar: .: Cannot open: Permission denied\n',
                       'Traceback (most recent call last):\n', '', None):
            job = self.job(output)
            self.assertEqual(0, self.step('emailBackup', job), output)
            self.assertEqual([], self.saved)
            self.assertIn('[5009]', self.status[-1])
            self.assertFalse([line for line in self.status if 'backed to' in line])
        job = self.job('[mail-archive] failed /home/vmail/example.com exists but could not be read in full\n')
        self.step('emailBackup', job)
        self.assertIn('/home/vmail/example.com exists but could not be read in full', self.status[-1])

    def test_bucket_is_opened_with_its_stored_key(self):
        job = self.job('[mail-archive] saved 1a2b3c4d\n', destination='s3:s3.amazonaws.com/AKIAEXAMPLE')
        self.assertEqual(1, self.step('emailBackup', job))
        action, options = self.options()
        self.assertEqual('s3:s3.amazonaws.com/example.com', options['--repository'])
        self.assertEqual('AKIAEXAMPLE', options['--aws-key'])
        self.assertEqual('s3:s3.amazonaws.com/AKIAEXAMPLE', self.saved[0]['destination'])

    def test_sftp_destination_ends_the_step_as_failed(self):
        job = self.job('[mail-archive] saved 1a2b3c4d\n', destination='sftp:backup@203.0.113.9')
        self.assertEqual(0, self.step('emailBackup', job))
        self.assertEqual([], self.runner.ran)
        self.assertEqual([], self.saved)

    def test_step_does_not_decide_by_looking_for_the_folder_itself(self):
        source = (ROOT / SOURCE).read_text()
        step = source[source.index('    def emailBackup(self):'):source.index('    def metaBackup(self):')]
        self.assertNotIn('os.path.exists', step)

    def test_recorded_snapshot_is_restored_by_the_helper(self):
        snapshot = SimpleNamespace(type='email:/home/vmail/example.com', destination='local', snapshotid='1a2b3c4d')
        job = self.job('[mail-archive] restored 6\n', website='example.com', jobid=snapshot)
        self.assertEqual(1, self.step('restoreEmail', job))
        self.assertEqual(('restore', {'--domain': 'example.com', '--account': 'examp1234',
                                      '--repository': '/home/example.com/incbackup',
                                      '--password-file': '/home/example.com/example.com',
                                      '--snapshot': '1a2b3c4d'}), self.options())
        self.assertEqual('6 mail files restored to /home/vmail/example.com.', self.status[-1])
        job.localFunction.assert_not_called()

    def test_remote_snapshot_is_restored_with_the_typed_password(self):
        job = self.job('[mail-archive] restored 6\n', website='example.com', jobid='1a2b3c4d', reconstruct='remote',
                       destination='s3:s3.amazonaws.com/AKIAEXAMPLE', passwordFile='typed password')
        self.assertEqual(1, self.step('restoreEmail', job))
        self.assertEqual(('restore', {'--domain': 'example.com', '--account': 'examp1234',
                                      '--repository': 's3:s3.amazonaws.com/example.com',
                                      '--password': 'typed password', '--aws-key': 'AKIAEXAMPLE',
                                      '--snapshot': '1a2b3c4d'}), self.options())
        job.awsFunction.assert_not_called()

    def test_restore_that_did_not_happen_fails(self):
        snapshot = SimpleNamespace(type='email:/home/vmail/example.com', destination='local', snapshotid='1a2b3c4d')
        for output in ('[mail-archive] failed No mail archive could be read from snapshot 1a2b3c4d\n', '', None,
                       '[mail-archive] saved 1a2b3c4d\n'):
            job = self.job(output, website='example.com', jobid=snapshot)
            self.assertEqual(0, self.step('restoreEmail', job), output)
            self.assertIn('[5009]', self.status[-1])


class V2StepTests(unittest.TestCase):
    """The V2 email step asks with privilege whether there is mail; it does not look for itself."""

    V2 = 'plogical/Backupsv2.py'

    def step(self, looked, saved='{"id": "abc", "summary": {"files_new": 3, "total_duration": 1}}\n'):
        ran = []

        def run(command, user=None, shell=None, dir=None, retRequired=None):
            ran.append((command, user))
            return looked if ' look ' in command else saved

        self.status = []
        import json
        namespace = dict(json=json, os=os, ProcessUtilities=SimpleNamespace(
            executioner=lambda *a, **k: 1, outputExecutioner=run),
            CPBackupsV2=SimpleNamespace(NO_MAIL_FOLDER=2, FAILED=3))
        step = load_method(self.V2, 'CPBackupsV2', 'BackupEmailsRustic', namespace)
        job = SimpleNamespace(website=SimpleNamespace(domain='example.com', externalApp='examp1234'), repo='repo',
                              snapshots=[], UpdateStatus=lambda message, state: self.status.append((message, state)))
        return step(job), job, ran

    def test_mail_is_saved_when_the_folder_is_there(self):
        result, job, ran = self.step('[mail-archive] present /home/vmail/example.com\n')
        self.assertEqual(1, result)
        self.assertEqual(['abc'], job.snapshots)
        self.assertEqual(shlex.split(mailArchive.helper_command('look', 'example.com')), shlex.split(ran[0][0]))
        self.assertIsNone(ran[0][1])
        self.assertIn('backup /home/vmail/example.com', ran[-1][0])

    def test_website_without_mail_saves_nothing_and_says_so(self):
        result, job, ran = self.step('[mail-archive] no-mail-folder /home/vmail/example.com\n')
        self.assertEqual(2, result)
        self.assertEqual([], job.snapshots)
        self.assertEqual(1, len(ran))
        source = (ROOT / self.V2).read_text()
        self.assertIn("elif emailsSaved == CPBackupsV2.NO_MAIL_FOLDER:\n"
                      "                            self.UpdateStatus('This website has no mail folder: "
                      "there are no emails to back up..,85',", source)
        self.assertEqual(2, self.constant('NO_MAIL_FOLDER'))

    def constant(self, name):
        import ast
        tree = ast.parse((ROOT / self.V2).read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'CPBackupsV2')
        return next(node.value.value for node in cls.body if isinstance(node, ast.Assign)
                    and node.targets[0].id == name)

    def test_answer_that_is_not_clear_fails_the_step(self):
        for looked in ('[mail-archive] failed /home/vmail/example.com is there but is not a folder\n', '', None):
            result, job, ran = self.step(looked)
            self.assertEqual(0, result, looked)
            self.assertEqual(1, len(ran))
            self.assertEqual(3, self.status[-1][1])

    def test_step_does_not_look_for_the_folder_itself(self):
        source = (ROOT / self.V2).read_text()
        step = source[source.index('    def BackupEmailsRustic(self):'):source.index('    #### Resote Functions')]
        self.assertNotIn('os.path.exists', step)


class JobEndTests(unittest.TestCase):
    """A job is reported as done only when every step it ran is."""

    def restore(self, kind, result):
        status = []
        snapshot = SimpleNamespace(type=kind, destination='local', snapshotid='1a2b3c4d')
        namespace = dict(
            mailArchive=mailArchive,
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda domain: SimpleNamespace(externalApp='examp1234'))),
            JobSnapshots=SimpleNamespace(objects=SimpleNamespace(get=lambda pk: snapshot)),
            logging=SimpleNamespace(statusWriter=lambda path, message, append=None: status.append(message)))
        run = load_method(SOURCE, 'IncJobs', 'restorePoint', namespace)
        job = SimpleNamespace(extraArgs=dict(tempPath='/dev/null', website='example.com', jobid=1, reconstruct='local'),
                              findRestorePath=mock.Mock())
        for step in ('restoreDatabase', 'restoreData', 'restoreEmail', 'reconstructWithMeta'):
            setattr(job, step, mock.Mock(return_value=result))
        run(job)
        return status

    def test_local_restore_is_done_only_when_its_step_is(self):
        for kind, said in (('database:shop_db', 'Database restored.'), ('data:/home/example.com', 'Data restored.'),
                           ('email:/home/vmail/example.com', 'Emails restored.'),
                           ('meta:/home/example.com/meta.xml', 'Reconstructed')):
            self.assertEqual([said, 'Completed'], self.restore(kind, 1)[-2:], kind)
            failed = self.restore(kind, 0)
            self.assertNotIn(said, failed, kind)
            self.assertNotIn('Completed', failed, kind)

    def remote(self, path):
        status = []
        namespace = dict(
            mailArchive=mailArchive,
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda domain: SimpleNamespace(externalApp='examp1234'))),
            logging=SimpleNamespace(statusWriter=lambda path, message, append=None: status.append(message)))
        run = load_method(SOURCE, 'IncJobs', 'restorePoint', namespace)
        job = SimpleNamespace(extraArgs=dict(tempPath='/dev/null', website='my.sqlsite.com', jobid='1a2b3c4d',
                                             reconstruct='remote', backupDestinations='s3:s3.amazonaws.com/KEY',
                                             password='typed', path=path), findRestorePath=mock.Mock())
        for step in ('restoreDatabase', 'restoreData', 'restoreEmail', 'reconstructWithMeta'):
            setattr(job, step, mock.Mock(return_value=1))
        run(job)
        return job

    def test_remote_snapshot_of_mail_is_known_by_its_path(self):
        for path in ('/vmail-my.sqlsite.com.tar', '/home/vmail/my.sqlsite.com'):
            job = self.remote(path)
            job.restoreEmail.assert_called_once_with()
            job.restoreDatabase.assert_not_called()
        # A database whose name has the mail account's in it is still a database.
        job = self.remote('/home/my.sqlsite.com/vmail_archive.sql')
        job.restoreDatabase.assert_called_once_with()
        job.restoreEmail.assert_not_called()

    def test_backup_without_its_meta_snapshot_is_not_reported_as_done(self):
        source = (ROOT / SOURCE).read_text()
        end = source[source.index('            ## Backup job done'):source.index('    ### Delete Snapshot')]
        self.assertIn('metaSaved = self.metaBackup()', end)
        self.assertLess(end.index('if metaSaved == 0:\n                return 0'), end.index("'Completed'"))

    def test_sftp_step_says_why_it_ends(self):
        status = []
        namespace = dict(logging=SimpleNamespace(
            statusWriter=lambda path, message, append=None: status.append(message)))
        step = load_method(SOURCE, 'IncJobs', 'sftpFunction', namespace)
        self.assertEqual(0, step(SimpleNamespace(statusPath='/dev/null'), '/home/example.com', 'data'))
        self.assertIn('[5009]', status[-1])
        self.assertIn('SFTP', status[-1])


if __name__ == '__main__':
    unittest.main()
