"""Mail is in a backup when the job says so, and comes back from it without harm to the mail store."""
import ast
import errno
import fcntl
import io
import json
import os
import pwd
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from IncBackups import mailArchive
from IncBackups.jobStatus import DONE, FAILED, job_end

SOURCE = 'IncBackups/IncBackupsControl.py'
V2 = 'plogical/Backupsv2.py'
ROOT = Path(__file__).resolve().parents[1]
SAVED_BY_RESTIC = 'reading from stdin\nsnapshot 1a2b3c4d saved\n'
ROOMY = (1 << 40, 1000000)


def load_method(relative_path, class_name, method_name, namespace):
    """One method of a class, compiled on its own with the names it uses given by the test."""
    path = ROOT / relative_path
    cls = next(node for node in ast.parse(path.read_text()).body
               if isinstance(node, ast.ClassDef) and node.name == class_name)
    method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == method_name)
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[method_name]


def content(path):
    with open(path) as handle:
        return handle.read()


def account(name):
    try:
        entry = pwd.getpwnam(name)
    except KeyError:
        return None
    return name if entry.pw_uid != 0 else None


class TemporaryFolder(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.mkdtemp(prefix='mail-archive-test-')
        self.addCleanup(shutil.rmtree, self.base, True)

    def tree(self, folder, files):
        for name, text in files.items():
            path = os.path.join(folder, name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, 'w') as handle:
                handle.write(text)

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
        self.assertEqual((mailArchive.NO_FOLDER, os.path.join(self.base, 'example.com')),
                         mailArchive.look(os.path.join(self.base, 'example.com')))

    def test_folder_is_present_even_when_empty(self):
        os.mkdir(os.path.join(self.base, 'example.com'))
        self.assertEqual(mailArchive.PRESENT, mailArchive.folder_state(os.path.join(self.base, 'example.com')))
        self.assertEqual(mailArchive.PRESENT, mailArchive.look(os.path.join(self.base, 'example.com'))[0])

    def test_file_in_its_place_is_not_a_folder(self):
        self.tree(self.base, {'file.example': 'x'})
        self.assertEqual(mailArchive.NOT_A_FOLDER, mailArchive.folder_state(os.path.join(self.base, 'file.example')))
        self.assertEqual(mailArchive.FAILED, mailArchive.look(os.path.join(self.base, 'file.example'))[0])

    def test_link_in_its_place_is_named_with_what_to_do(self):
        os.mkdir(os.path.join(self.base, 'elsewhere'))
        link = os.path.join(self.base, 'link.example')
        os.symlink(os.path.join(self.base, 'elsewhere'), link)
        self.assertEqual(mailArchive.LINK, mailArchive.folder_state(link))
        outcome, detail = mailArchive.look(link)
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('%s is a link to %s' % (link, os.path.join(self.base, 'elsewhere')), detail)
        self.assertIn('Mount the other location at that path', detail)

    def test_refused_lookup_is_not_taken_for_a_missing_folder(self):
        # What an account that may not enter the mail store is told.
        with mock.patch('os.lstat', side_effect=OSError(errno.EACCES, 'Permission denied')):
            self.assertEqual(mailArchive.UNKNOWN, mailArchive.folder_state('/home/vmail/example.com'))
            outcome, detail = mailArchive.look('/home/vmail/example.com')
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('not a folder that can be read', detail)

    @unittest.skipIf(os.geteuid() == 0, 'root may enter every folder')
    def test_folder_behind_a_closed_folder_is_not_taken_for_a_missing_one(self):
        os.makedirs(os.path.join(self.base, 'vmail', 'example.com'))
        os.chmod(os.path.join(self.base, 'vmail'), 0)
        self.addCleanup(os.chmod, os.path.join(self.base, 'vmail'), 0o700)
        self.assertEqual(mailArchive.UNKNOWN,
                         mailArchive.folder_state(os.path.join(self.base, 'vmail', 'example.com')))

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
        self.assertEqual((mailArchive.RESTORED, '12 mail files written'),
                         mailArchive.read_outcome('[mail-archive] restored 12 mail files written\n'))
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
                                             password_from='/home/cyberpanel/repository-password-x y',
                                             aws_key='AKIA$(id)', snapshot='1a2b3c4d')
        words = shlex.split(command)
        self.assertEqual([mailArchive.PYTHON, mailArchive.PROGRAM, 'restore'], words[:3])
        self.assertEqual({'--domain': 'example.com', '--account': 'examp1234',
                          '--repository': 's3:s3.amazonaws.com/example.com',
                          '--password-from': '/home/cyberpanel/repository-password-x y',
                          '--aws-key': 'AKIA$(id)', '--snapshot': '1a2b3c4d'}, dict(zip(words[3::2], words[4::2])))
        # The privileged helper adds `sudo` itself to a command that has none; this one is one command.
        from plogical.commandShape import runs_one_command
        self.assertTrue(runs_one_command(command))

    def test_restored_words_say_what_was_left_alone(self):
        self.assertEqual('36 mail files written', mailArchive.restored_words(dict(written=36)))
        self.assertEqual('36 mail files written, 40 index, lock and compiled filter files left out (Dovecot makes '
                         'them again), 7 files of Dovecot left as they are on the server, '
                         '2 second names of files left out because their file was not restored',
                         mailArchive.restored_words(dict(written=36, rebuilt=40, kept=7, unlinked=2, mdbox=[])))
        words = mailArchive.mdbox_words(['imported', 'other'])
        self.assertIn('Not restored: imported, other.', words)
        self.assertIn('older storage files under a mailbox in use would lose the mail that arrived since', words)
        self.assertIn('Restore them into an empty mailbox folder, or ask support.', words)

    def test_output_is_printed_whatever_the_locale(self):
        raw = io.BytesIO()
        # What the program's output is under Python 3.6 with the C locale.
        plain = io.TextIOWrapper(raw, encoding='ascii')
        with mock.patch('sys.stdout', plain):
            mailArchive.say('[mail-archive] failed /home/vmail/example.com/b\u00fcro/Maildir: \u4e0d\udcff')
        self.assertEqual('[mail-archive] failed /home/vmail/example.com/b\u00fcro/Maildir: \u4e0d?\n',
                         raw.getvalue().decode('utf-8'))
        with self.assertRaises(UnicodeEncodeError):
            plain.write('b\u00fcro')
            plain.flush()
        with mock.patch('sys.stdout', io.StringIO()) as printed:
            mailArchive.say('plain')
        self.assertEqual('plain\n', printed.getvalue())


class SecretTests(TemporaryFolder):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(mailArchive, 'SECRET_FOLDER', self.base)
        patch.start()
        self.addCleanup(patch.stop)

    def test_secret_is_kept_in_a_private_file_and_never_on_a_command_line(self):
        path = mailArchive.keep_secret('typed pass word')
        self.assertEqual(self.base, os.path.dirname(path))
        self.assertEqual(0o600, stat.S_IMODE(os.stat(path).st_mode))
        self.assertEqual('typed pass word', mailArchive.read_secret(path))
        command = mailArchive.helper_command('restore', 'example.com', 'examp1234', 's3:s3.amazonaws.com/example.com',
                                             password_from=path, snapshot='1a2b3c4d')
        self.assertNotIn('typed', command)
        self.assertNotIn('--password ', command)
        mailArchive.forget_secret(path)
        self.assertFalse(os.path.exists(path))
        mailArchive.forget_secret(path)
        mailArchive.forget_secret(None)

    def test_password_that_is_not_text_leaves_no_file(self):
        for value in (None, '', 7, ['x'], {'a': 1}, b'bytes'):
            with self.assertRaises(mailArchive.Refused):
                mailArchive.keep_secret(value)
        self.assertEqual([], os.listdir(self.base))

    def test_only_a_plain_file_of_the_panel_s_own_folder_is_read(self):
        outside = tempfile.mkdtemp(prefix='mail-archive-test-')
        self.addCleanup(shutil.rmtree, outside, True)
        self.tree(outside, {'secret': 'root only'})
        os.symlink(os.path.join(outside, 'secret'), os.path.join(self.base, 'link'))
        os.mkdir(os.path.join(self.base, 'sub'))
        self.tree(self.base, {'sub/deeper': 'x'})
        for path in (os.path.join(outside, 'secret'), os.path.join(self.base, 'sub', 'deeper'),
                     os.path.join(self.base, '..', os.path.basename(outside), 'secret')):
            with self.assertRaises(mailArchive.Refused, msg=path):
                mailArchive.read_secret(path)
        with self.assertRaises(OSError):
            mailArchive.read_secret(os.path.join(self.base, 'link'))
        with self.assertRaises(mailArchive.Refused):
            mailArchive.read_secret(os.path.join(self.base, 'sub'))

    def test_program_takes_no_password_on_its_command_line(self):
        with mock.patch('sys.stderr', io.StringIO()), self.assertRaises(SystemExit):
            mailArchive.main(['restore', '--domain', 'example.com', '--password', 'typed'])
        store = mailArchive.store_of(SimpleNamespace(
            repository='s3:s3.amazonaws.com/example.com', program='restic', aws_key=None, password_file=None,
            password_from=mailArchive.keep_secret('typed pass word')))
        # restic is given the password in its own environment, and nothing in its words.
        self.assertEqual({'RESTIC_PASSWORD': 'typed pass word'}, store.environment)
        self.assertNotIn('typed pass word', ' '.join(store.dump('1a2b3c4d', 'vmail-example.com.tar')))


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
        for program in ('restic', 'rustic'):
            status, (outcome, detail) = self.run_program(
                'backup', '--domain', 'example.com', '--account', 'root', '--program', program,
                '--repository', '/home/example.com/incbackup')
            self.assertEqual((1, mailArchive.FAILED), (status, outcome))
            self.assertIn('not as root', detail)

    def test_request_that_names_no_account_repository_or_domain_is_refused(self):
        for words in (('backup', '--domain', 'example.com', '--repository', '/home/example.com/incbackup'),
                      ('backup', '--domain', 'example.com', '--account', 'nobody'),
                      ('backup', '--domain', 'example.com', '--account', 'nobody', '--repository=--help'),
                      ('restore', '--domain', '../etc', '--account', 'nobody', '--repository', '/x',
                       '--snapshot', '1a2b3c4d')):
            status, (outcome, detail) = self.run_program(*words)
            self.assertEqual((1, mailArchive.FAILED), (status, outcome), words)

    def test_stored_key_is_named_not_given_as_a_path(self):
        for key in ('../../etc/shadow', '/etc/shadow', 'a/b', '', '.', '..'):
            with self.assertRaises(mailArchive.Refused):
                mailArchive.aws_environment(key)

    def test_words_for_each_backup_program(self):
        restic = mailArchive.Restic('/home/example.com/incbackup', '/home/example.com/example.com')
        start = ['restic', '-r', '/home/example.com/incbackup', '--password-file', '/home/example.com/example.com']
        self.assertEqual(start + ['backup', '--stdin', '--stdin-filename', 'vmail-example.com.tar'],
                         restic.save('vmail-example.com.tar'))
        self.assertEqual(start + ['dump', '1a2b3c4d', '/vmail-example.com.tar'],
                         restic.dump('1a2b3c4d', 'vmail-example.com.tar'))
        self.assertEqual('1a2b3c4d', restic.saved(SAVED_BY_RESTIC))
        self.assertIsNone(restic.saved('Fatal: wrong password'))

        # The same words the database step of Backup V2 gives rustic.
        rustic = mailArchive.Rustic('rclone:offsite:example.com')
        self.assertEqual(['rustic', '-r', 'rclone:offsite:example.com', 'backup', '--stdin-filename',
                          'vmail-example.com.tar', '-', '--password', '', '--json'],
                         rustic.save('vmail-example.com.tar'))
        self.assertEqual(['rustic', '-r', 'rclone:offsite:example.com', 'dump',
                          '1a2b3c4d:vmail-example.com.tar', '--password', ''],
                         rustic.dump('1a2b3c4d', 'vmail-example.com.tar'))
        snapshot = 'ab' * 32
        self.assertEqual(snapshot, rustic.saved(
            '[INFO] using config\n{"time":"x","tree":"%s","paths":["vmail-example.com.tar"],"id":"%s"}\n' % (
                'cd' * 32, snapshot)))
        self.assertIsNone(rustic.saved('{"tree":"%s"}' % ('cd' * 32)))
        self.assertEqual({}, rustic.environment)


class JudgeTests(unittest.TestCase):
    FOLDER = '/home/vmail/example.com'

    def test_saved_snapshot_of_a_fully_read_folder_is_a_backup(self):
        self.assertEqual((mailArchive.SAVED, '1a2b3c4d', None),
                         mailArchive.judge_backup(self.FOLDER, '1a2b3c4d', 0, '', 0, SAVED_BY_RESTIC))

    def test_mail_that_changed_while_it_was_read_is_still_a_backup(self):
        errors = 'tar: ./qa/Maildir/new/1.host: File removed before we read it\n'
        self.assertEqual((mailArchive.SAVED, '1a2b3c4d', None),
                         mailArchive.judge_backup(self.FOLDER, '1a2b3c4d', 1, errors, 0, SAVED_BY_RESTIC))

    def test_folder_that_could_not_be_read_fails_and_its_snapshot_is_discarded(self):
        errors = 'tar: ./qa/Maildir: Cannot open: Permission denied\ntar: Exiting with failure status\n'
        for status in (2, -13, 141):
            outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, '1a2b3c4d', status, errors, 0,
                                                                SAVED_BY_RESTIC)
            self.assertEqual(mailArchive.FAILED, outcome)
            self.assertIn('/home/vmail/example.com exists but could not be read in full', detail)
            self.assertIn('Permission denied', detail)
            self.assertEqual('1a2b3c4d', discard)

    def test_backup_program_that_fails_or_saves_nothing_fails(self):
        outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, None, -13, '', 1, 'Fatal: wrong password\n')
        self.assertEqual((mailArchive.FAILED, None), (outcome, discard))
        self.assertIn('wrong password', detail)
        outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, None, 0, '', 0, 'nothing was said\n')
        self.assertEqual((mailArchive.FAILED, None), (outcome, discard))
        outcome, detail, discard = mailArchive.judge_backup(self.FOLDER, '1a2b3c4d', 0, '', 3, SAVED_BY_RESTIC)
        self.assertEqual((mailArchive.FAILED, '1a2b3c4d'), (outcome, discard))

    def test_restore_pass_is_done_only_when_both_ends_are(self):
        self.assertEqual((mailArchive.RESTORED, '{"written": 7}'),
                         mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', 0, '', 0, 'a warning\n{"written": 7}\n'))
        outcome, detail = mailArchive.judge_restore(
            self.FOLDER, '1a2b3c4d', 1, 'Fatal: cannot dump file: path "/vmail-example.com.tar" not found',
            mailArchive.UNREADABLE, 'The archive could not be read: empty file\n')
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('No mail archive could be read from snapshot 1a2b3c4d', detail)
        self.assertIn('before CyberPanel 3.0.13 hold no mail archive', detail)
        # An archive that is damaged, from a backup program that ended well.
        self.assertEqual((mailArchive.FAILED, 'The archive could not be read: unexpected end of data'),
                         mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', 0, '', mailArchive.UNREADABLE,
                                                   'The archive could not be read: unexpected end of data\n'))

    def test_reason_the_restore_stopped_is_the_one_reported(self):
        # The backup program is cut off when the reading end stops, and fails with a broken pipe.
        for said in ('The archive does not fit: it needs more than 5 bytes or 9 entries, which is what the disk '
                     'has free less a reserve.', "The archive holds '../x', a name that leaves the mail folder.",
                     '[Errno 28] No space left on device', 'The archive needs more memory than a restore may use.'):
            for store_status, store_errors in ((1, 'Fatal: write /dev/stdout: broken pipe'), (-13, ''), (0, '')):
                self.assertEqual((mailArchive.FAILED, said), mailArchive.judge_restore(
                    self.FOLDER, '1a2b3c4d', store_status, store_errors, mailArchive.STOPPED, said + '\n'))
        outcome, detail = mailArchive.judge_restore(self.FOLDER, '1a2b3c4d', -13, '', -9, '')
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('ended by signal 9', detail)
        self.assertNotEqual(mailArchive.STOPPED, mailArchive.UNREADABLE)

    def test_search_for_links_does_not_fail_over_mail_that_moved_meanwhile(self):
        gone = ("find: '/home/vmail/example.com/qa/Maildir/new/1700.M1P2.host': No such file or directory\n"
                "find: '/home/vmail/example.com/qa/Maildir/tmp/x': No such file or directory\n")
        self.assertEqual('', mailArchive.search_trouble(0, ''))
        self.assertEqual('', mailArchive.search_trouble(1, gone))
        for errors in ("find: '/home/vmail/example.com/qa/Maildir': Permission denied\n",
                       gone + "find: '/home/vmail/example.com/qa': Permission denied\n",
                       "find: '/home/vmail/example.com/x': Input/output error\n", ''):
            trouble = mailArchive.search_trouble(1, errors)
            self.assertTrue(trouble, errors)
        self.assertIn('Permission denied', mailArchive.search_trouble(1, gone + "find: 'x': Permission denied\n"))


class JobEndTests(unittest.TestCase):
    """How a job ended is read from its failure mark and its last line."""

    def test_job_runs_until_its_last_line_says_completed(self):
        self.assertIsNone(job_end(''))
        self.assertIsNone(job_end(None))
        self.assertIsNone(job_end('Backing up data..\nData for example.com backed to local.\n'))
        self.assertEqual(DONE, job_end('Backing up data..\nMeta for example.com backed to local.\nCompleted\n'))
        self.assertEqual(DONE, job_end('Completed'))

    def test_failure_mark_ends_the_job_as_failed_whatever_else_the_file_says(self):
        self.assertEqual(FAILED, job_end('Backing up emails..\nx [IncJobs.emailBackup][5009]\n'))
        self.assertEqual(FAILED, job_end('x [5009]\nDatabase restored.\nCompleted\n'))

    def test_marker_words_in_names_decide_nothing(self):
        # A mail folder is named by its user; tar and the unpacker name it in what they say.
        tar = 'tar: ./qa/Maildir/.Completed: Cannot open: Permission denied\ntar: ./qa/Completed\n'
        outcome, detail, _ = mailArchive.judge_backup('/home/vmail/example.com', '1a2b3c4d', 2, tar, 0,
                                                      SAVED_BY_RESTIC)
        status = 'Backing up emails..\n%s [IncJobs.emailBackup][5009]\n' % detail
        self.assertIn('Completed', status)
        self.assertEqual(FAILED, job_end(status))
        # A line that only mentions the word is not the end of a job that is still running.
        self.assertIsNone(job_end('Backing up data..\nerror: open /home/example.com/Completed: denied\n'))
        self.assertIsNone(job_end('Completed\nMail restored to /home/vmail/example.com: 3 mail files written.\n'))
        # Text a program printed over several lines reaches the status as one line.
        self.assertEqual(1, len(mailArchive.last_part('tar: a\nCompleted\n[5009]\n').splitlines()))
        self.assertNotIn('\n', mailArchive.shown('folder\nCompleted'))

    def test_status_readers_use_it(self):
        view = (ROOT / 'IncBackups' / 'views.py').read_text()
        view = view[view.index('def get_backup_status(request):'):view.index('def delete_backup(request):')]
        scheduler = (ROOT / 'plogical' / 'IncScheduler.py').read_text()
        scheduler = scheduler[scheduler.index('    def startBackup(type):'):scheduler.index('    def git(type):')]
        for source in (view, scheduler):
            self.assertIn('ended = job_end(result)', source)
            self.assertIn('ended == DONE', source)
            self.assertIn('ended == FAILED', source)
            self.assertNotIn('find("Completed")', source)
            self.assertNotIn('find("[5009]")', source)


def archive_of(*members):
    """A tar archive in memory. A member is (name, kind, value[, mode]): a file's content or a link's target."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w') as archive:
        for member in members:
            name, kind, value = member[:3]
            entry = tarfile.TarInfo(name)
            entry.type = kind
            entry.mode = member[3] if len(member) > 3 else (0o700 if kind == tarfile.DIRTYPE else 0o600)
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

    def restore(self, *members, **options):
        """Both passes, as the program runs them."""
        plan = mailArchive.Unpacker(self.folder, options.get('limits', ROOMY)).check(archive_of(*members))
        self.counts = mailArchive.Unpacker(self.folder, options.get('limits', ROOMY)).write(
            archive_of(*members), plan)
        # written; Dovecot files never restored; Dovecot files kept as they are; second names left out
        return tuple(self.counts[name] for name in ('written', 'rebuilt', 'kept', 'unlinked'))

    def refused(self, *members, **options):
        """The first pass refuses the archive, and nothing at all is written."""
        before = self.files_below(self.base)
        existed = os.path.exists(self.folder)
        with self.assertRaises(mailArchive.Refused) as refusal:
            mailArchive.Unpacker(self.folder, options.get('limits', ROOMY)).check(archive_of(*members))
        self.assertEqual(before, self.files_below(self.base))
        self.assertEqual(existed, os.path.exists(self.folder))
        return str(refusal.exception)

    def test_mailboxes_come_back_with_their_times_and_links(self):
        written = self.restore(
            ('.', tarfile.DIRTYPE, None),
            ('./qa', tarfile.DIRTYPE, None),
            ('./qa/Maildir/cur/1.host:2,S', tarfile.REGTYPE, 'first message'),
            ('./qa/Maildir/.Sent/cur/2.host:2,S', tarfile.REGTYPE, 'second message'),
            ('./qa/Maildir/.Archive/cur/1.host:2,S', tarfile.LNKTYPE, './qa/Maildir/cur/1.host:2,S'),
            ('./qa/sieve/managesieve.sieve', tarfile.REGTYPE, 'keep;'),
            ('./qa/.dovecot.sieve', tarfile.SYMTYPE, 'sieve/managesieve.sieve'))
        self.assertEqual((4, 0, 0, 0), written)
        self.assertEqual([], self.counts['mdbox'])
        self.assertEqual({'qa/Maildir/cur/1.host:2,S': 'first message',
                          'qa/Maildir/.Sent/cur/2.host:2,S': 'second message',
                          'qa/Maildir/.Archive/cur/1.host:2,S': 'first message',
                          'qa/sieve/managesieve.sieve': 'keep;'}, self.files_below(self.folder))
        message = os.stat(os.path.join(self.folder, 'qa/Maildir/cur/1.host:2,S'))
        self.assertEqual(1700000000, int(message.st_mtime))
        self.assertEqual(2, message.st_nlink)
        self.assertEqual('sieve/managesieve.sieve', os.readlink(os.path.join(self.folder, 'qa/.dovecot.sieve')))

    def test_folders_and_files_are_for_the_mail_account_alone_whatever_the_archive_says(self):
        os.makedirs(os.path.join(self.folder, 'old'))
        os.chmod(os.path.join(self.folder, 'old'), 0o750)
        os.chmod(self.folder, 0o755)
        self.restore(
            ('.', tarfile.DIRTYPE, None, 0o777),
            ('./qa', tarfile.DIRTYPE, None, 0o777),
            ('./qa/Maildir', tarfile.DIRTYPE, None, 0o1777),
            ('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message', 0o666),
            ('./qa/Maildir/cur/2', tarfile.REGTYPE, 'message', 0o4755),
            ('./deep/er/Maildir/new/3', tarfile.REGTYPE, 'message', 0o644),
            ('./old', tarfile.DIRTYPE, None, 0o777),
            ('./old/4', tarfile.REGTYPE, 'message', 0o777))
        for directory, _, names in os.walk(self.folder):
            if directory not in (self.folder, os.path.join(self.folder, 'old')):
                self.assertEqual(0o700, stat.S_IMODE(os.stat(directory).st_mode), directory)
            for name in names:
                self.assertEqual(0o600, stat.S_IMODE(os.stat(os.path.join(directory, name)).st_mode), name)
        # A folder that was there keeps the mode its administrator gave it.
        self.assertEqual(0o750, stat.S_IMODE(os.stat(os.path.join(self.folder, 'old')).st_mode))
        self.assertEqual(0o755, stat.S_IMODE(os.stat(self.folder).st_mode))

    def test_newer_mail_stays_and_a_restored_file_replaces_the_one_there(self):
        self.tree(self.folder, {'qa/Maildir/cur/1': 'changed since', 'qa/Maildir/new/9': 'arrived later'})
        os.link(os.path.join(self.folder, 'qa/Maildir/cur/1'), os.path.join(self.base, 'second-name'))
        self.restore(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'as saved'))
        self.assertEqual({'qa/Maildir/cur/1': 'as saved', 'qa/Maildir/new/9': 'arrived later'},
                         self.files_below(self.folder))
        # The file was replaced, not written into: its other name keeps what it had.
        self.assertEqual('changed since', content(os.path.join(self.base, 'second-name')))
        self.assertEqual(['1'], os.listdir(os.path.join(self.folder, 'qa/Maildir/cur')))

    def test_nothing_is_written_before_the_whole_archive_is_checked(self):
        self.tree(self.folder, {'qa/Maildir/cur/1': 'as it is'})
        message = self.refused(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'overwritten'),
                               ('./qa/Maildir/cur/2', tarfile.REGTYPE, 'new'),
                               ('../other.example/user/Maildir/cur/evil', tarfile.REGTYPE, 'evil'))
        self.assertIn('leaves the mail folder', message)
        self.assertEqual({'qa/Maildir/cur/1': 'as it is'}, self.files_below(self.folder))
        with self.assertRaises(mailArchive.Refused):
            mailArchive.Unpacker(self.folder, ROOMY).write(
                archive_of(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'overwritten')), None)
        self.assertEqual({'qa/Maildir/cur/1': 'as it is'}, self.files_below(self.folder))

    def test_archive_that_is_not_the_one_checked_is_not_written_past_the_difference(self):
        checked = [('./qa/Maildir/cur/1', tarfile.REGTYPE, 'first')]
        plan = mailArchive.Unpacker(self.folder, ROOMY).check(archive_of(*checked))
        for other in ([('./qa/Maildir/cur/1', tarfile.REGTYPE, 'first'), ('./qa/Maildir/cur/2', tarfile.REGTYPE, 'x')],
                      [('./qa/Maildir/cur/1', tarfile.REGTYPE, 'longer than it was')],
                      [('./qa/Maildir/cur/9', tarfile.REGTYPE, 'first')]):
            with self.assertRaises(mailArchive.Refused) as refusal:
                mailArchive.Unpacker(self.folder, ROOMY).write(archive_of(*other), plan)
            self.assertIn('changed between its check and the restore', str(refusal.exception))
            self.assertFalse(os.path.exists(os.path.join(self.folder, 'qa/Maildir/cur/2')))

    def test_archive_larger_than_the_free_space_allows_is_refused_at_its_heading(self):
        message = self.refused(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'x' * 5000), limits=(8000, 100))
        self.assertIn('does not fit', message)
        self.refused(*[('./qa/Maildir/cur/%d' % number, tarfile.REGTYPE, '') for number in range(6)],
                     limits=(1 << 30, 5))
        # A member that claims a terabyte is refused when its heading is read; its content is not.
        heading = tarfile.TarInfo('./qa/Maildir/cur/huge')
        heading.size = 1 << 40
        before = self.files_below(self.base)
        with self.assertRaises(mailArchive.Refused):
            mailArchive.Unpacker(self.folder, (1 << 30, 100)).check(io.BytesIO(heading.tobuf()))
        self.assertEqual(before, self.files_below(self.base))

    def test_allowance_keeps_a_reserve_of_the_disk(self):
        space = os.statvfs(self.base)
        free = space.f_bavail * space.f_frsize
        allowed, entries = mailArchive.allowance(os.path.join(self.base, 'not', 'there', 'yet'))
        self.assertLessEqual(allowed, max(0, free - mailArchive.LEAST_RESERVE) + (1 << 24))
        self.assertLessEqual(entries, mailArchive.MOST_ENTRIES)
        with mock.patch('os.statvfs', return_value=SimpleNamespace(
                f_blocks=1000000, f_frsize=4096, f_bavail=500000, f_files=1000, f_favail=400)):
            # A 4 GB disk: the reserve is one gigabyte, and a twentieth of the entries.
            self.assertEqual((500000 * 4096 - (1 << 30), 350), mailArchive.allowance(self.base))
        with mock.patch('os.statvfs', return_value=SimpleNamespace(
                f_blocks=1000000000, f_frsize=4096, f_bavail=1000000, f_files=0, f_favail=0)):
            # A 4 TB disk with 4 GB free and no count of entries: less than the reserve of ten gigabytes is free.
            self.assertEqual((0, mailArchive.MOST_ENTRIES), mailArchive.allowance(self.base))

    @unittest.skipUnless(shutil.which('tar') and shutil.which('truncate'), 'needs tar and truncate')
    def test_file_with_holes_is_refused(self):
        source = os.path.join(self.base, 'source')
        os.makedirs(os.path.join(source, 'qa/Maildir/cur'))
        subprocess.check_call(['truncate', '-s', '64M', os.path.join(source, 'qa/Maildir/cur/holes')])
        data = subprocess.check_output(['tar', '--sparse', '--create', '--file=-', '--directory=' + source, '.'])
        self.assertLess(len(data), 1 << 20)
        before = self.files_below(self.base)
        with self.assertRaises(mailArchive.Refused) as refusal:
            mailArchive.Unpacker(self.folder, ROOMY).check(io.BytesIO(data))
        self.assertIn('holes', str(refusal.exception))
        self.assertEqual(before, self.files_below(self.base))

    def test_entry_that_leaves_the_folder_is_refused(self):
        for name in ('../other.example/user/Maildir/cur/evil', '/etc/cron.d/evil', 'qa/../../other.example/evil',
                     './..'):
            self.refused((name, tarfile.REGTYPE, 'evil'))

    def test_link_that_points_out_of_its_folder_is_refused(self):
        for target in (self.other + '/user/Maildir', '/etc', '../other.example/user/Maildir', 'a/../../x', ''):
            self.refused(('./thief/Maildir', tarfile.SYMTYPE, target))

    def test_second_name_for_a_file_outside_the_folder_is_refused(self):
        for target in ('../other.example/user/Maildir/cur/1', self.other + '/user/Maildir/cur/1', '.'):
            self.refused(('./thief/Maildir/cur/1', tarfile.LNKTYPE, target))

    def test_second_name_whose_file_is_not_there_is_left_out_and_counted(self):
        self.assertEqual((1, 0, 0, 1), self.restore(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message'),
                                                    ('./qa/Maildir/cur/2', tarfile.LNKTYPE, 'qa/absent')))
        self.assertEqual({'qa/Maildir/cur/1': 'message'}, self.files_below(self.folder))

    def test_nothing_is_written_through_a_link_that_leads_out(self):
        os.makedirs(self.folder)
        os.symlink(self.other, os.path.join(self.folder, 'way-out'))
        self.refused(('./way-out/user/Maildir/cur/evil', tarfile.REGTYPE, 'evil'))
        self.refused(('./way-out', tarfile.DIRTYPE, None))

    def test_devices_and_pipes_are_refused(self):
        for kind in (tarfile.CHRTYPE, tarfile.BLKTYPE, tarfile.FIFOTYPE):
            self.refused(('./qa/thing', kind, None))

    def test_file_where_a_folder_is_and_folder_where_a_file_is_are_refused_before_anything_is_written(self):
        self.tree(self.folder, {'qa/Maildir/cur/1': 'message'})
        self.refused(('./qa/Maildir/new/2', tarfile.REGTYPE, 'new'), ('./qa/Maildir/cur', tarfile.REGTYPE, 'x'))
        self.refused(('./qa/Maildir/cur/1', tarfile.DIRTYPE, None))

    # What Dovecot makes again and reads in the account that owns every website's mail.
    REBUILT = ('dovecot.index', 'dovecot.index.log', 'dovecot.index.log.2', 'dovecot.index.cache',
               'dovecot.list.index', 'dovecot.list.index.log', 'dovecot.mailbox.log', 'dovecot-uidlist.lock',
               '.temp.host.1234.0123456789abcdef')
    # What a mailbox folder gets only when it has none.
    OWN = ('dovecot-uidlist', 'dovecot-keywords', 'dovecot-uidvalidity', 'maildirsize')

    def test_files_are_told_apart_by_name(self):
        for name in self.REBUILT + ('.dovecot.svbin', 'managesieve.svbin', '.dovecot.lda-dupes',
                                    'dovecot.map.index', 'dovecot.index.cache.lock', 'maildirsize.lock'):
            self.assertEqual(mailArchive.REBUILT, mailArchive.dovecot_file(name), name)
        for name in self.OWN + ('dovecot-uidvalidity.5f3a1c2b', 'dovecot-acl'):
            self.assertEqual(mailArchive.OWN, mailArchive.dovecot_file(name), name)
        # Mail, the customer's filters and settings.
        for name in ('1700.M1P2.host:2,S', 'managesieve.sieve', '.dovecot.sieve', 'dovecot.sieve', 'subscriptions',
                     'vacation.sieve', 'notes.lock', 'x.temp.y', 'm.1'):
            self.assertIsNone(mailArchive.dovecot_file(name), name)

    def mailbox_archive(self):
        return ([('./qa/Maildir/%s' % name, tarfile.REGTYPE, 'old ' + name) for name in self.REBUILT + self.OWN]
                + [('./qa/Maildir/.Sent/%s' % name, tarfile.REGTYPE, 'old ' + name)
                   for name in ('dovecot-uidlist', 'dovecot.index')]
                + [('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message'),
                   ('./qa/Maildir/.Sent/cur/2', tarfile.REGTYPE, 'sent'),
                   ('./qa/Maildir/subscriptions', tarfile.REGTYPE, 'Sent\n'),
                   ('./qa/sieve/managesieve.sieve', tarfile.REGTYPE, 'keep;'),
                   ('./qa/sieve/managesieve.svbin', tarfile.REGTYPE, 'compiled'),
                   ('./qa/.dovecot.svbin', tarfile.REGTYPE, 'compiled'),
                   ('./qa/.dovecot.sieve', tarfile.SYMTYPE, 'sieve/managesieve.sieve')])

    def test_indexes_and_compiled_filters_are_never_restored_and_the_filter_itself_is(self):
        written, rebuilt, kept, unlinked = self.restore(*self.mailbox_archive())
        # Even into mailbox folders that have none of them.
        self.assertEqual((len(self.OWN) + 1 + 4, len(self.REBUILT) + 1 + 2, 0, 0), (written, rebuilt, kept, unlinked))
        restored = self.files_below(self.folder)
        self.assertEqual(sorted(['qa/Maildir/%s' % name for name in self.OWN]
                                + ['qa/Maildir/.Sent/dovecot-uidlist', 'qa/Maildir/cur/1', 'qa/Maildir/.Sent/cur/2',
                                   'qa/Maildir/subscriptions', 'qa/sieve/managesieve.sieve']), sorted(restored))
        self.assertEqual('keep;', restored['qa/sieve/managesieve.sieve'])
        self.assertEqual('sieve/managesieve.sieve', os.readlink(os.path.join(self.folder, 'qa/.dovecot.sieve')))
        self.assertEqual('old dovecot-uidlist', restored['qa/Maildir/dovecot-uidlist'])
        self.assertIn('%d index, lock and compiled filter files left out (Dovecot makes them again)' % rebuilt,
                      mailArchive.restored_words(self.counts))

    def test_uid_list_keywords_and_quota_count_are_left_alone_in_a_mailbox_that_has_them(self):
        self.tree(self.folder, {'qa/Maildir/dovecot-uidlist': 'current uidlist', 'qa/Maildir/cur/9': 'newer',
                                'qa/Maildir/dovecot.index.log': 'current log'})
        written, rebuilt, kept, unlinked = self.restore(*self.mailbox_archive())
        # INBOX keeps its own; the Sent folder had none and gets the saved UID list.
        self.assertEqual((1 + 4, len(self.REBUILT) + 1 + 2, len(self.OWN), 0), (written, rebuilt, kept, unlinked))
        restored = self.files_below(self.folder)
        self.assertEqual('current uidlist', restored['qa/Maildir/dovecot-uidlist'])
        self.assertEqual('current log', restored['qa/Maildir/dovecot.index.log'])
        for name in ('dovecot-keywords', 'dovecot-uidvalidity', 'maildirsize', 'dovecot.index'):
            self.assertNotIn('qa/Maildir/' + name, restored)
        self.assertEqual('old dovecot-uidlist', restored['qa/Maildir/.Sent/dovecot-uidlist'])
        self.assertEqual(('message', 'newer', 'sent', 'Sent\n'),
                         (restored['qa/Maildir/cur/1'], restored['qa/Maildir/cur/9'],
                          restored['qa/Maildir/.Sent/cur/2'], restored['qa/Maildir/subscriptions']))
        self.assertIn('%d files of Dovecot left as they are on the server' % len(self.OWN),
                      mailArchive.restored_words(self.counts))

    def test_restore_does_not_fail_over_one_of_dovecot_s_files(self):
        # A folder in the place of one, and one that cannot be put in place.
        os.makedirs(os.path.join(self.folder, 'box/Maildir/dovecot-keywords'))
        os.makedirs(os.path.join(self.folder, 'box/Maildir/dovecot.index.cache'))
        rename = os.rename

        def no_uidlist(source, target):
            if os.path.basename(target) == 'dovecot-uidlist':
                raise OSError(errno.EEXIST, 'recreated by Dovecot')
            return rename(source, target)

        with mock.patch('os.rename', side_effect=no_uidlist):
            written, rebuilt, kept, unlinked = self.restore(
                ('./box/Maildir/dovecot-keywords', tarfile.REGTYPE, 'old'),
                ('./box/Maildir/dovecot.index.cache', tarfile.REGTYPE, 'old'),
                ('./qa/Maildir/dovecot-uidlist', tarfile.REGTYPE, 'old'),
                ('./qa/Maildir/maildirsize', tarfile.SYMTYPE, 'dovecot-uidlist'),
                ('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message'))
        self.assertEqual((1, 1, 3, 0), (written, rebuilt, kept, unlinked))
        self.assertEqual({'qa/Maildir/cur/1': 'message'}, self.files_below(self.folder))
        self.assertEqual(['cur'], os.listdir(os.path.join(self.folder, 'qa/Maildir')))

    def test_lock_that_was_a_second_name_when_the_backup_ran_does_not_spoil_the_archive(self):
        # Dovecot makes a lock by giving a temporary file a second name; tar can catch that moment.
        written, rebuilt, kept, unlinked = self.restore(
            ('./qa/Maildir/.temp.host.1234.abcdef', tarfile.REGTYPE, '1 V1700000000 N2\n'),
            ('./qa/Maildir/dovecot-uidlist.lock', tarfile.LNKTYPE, './qa/Maildir/.temp.host.1234.abcdef'),
            ('./qa/Maildir/copy-of-the-list', tarfile.LNKTYPE, './qa/Maildir/dovecot-uidlist'),
            ('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message'))
        self.assertEqual((1, 3, 0, 0), (written, rebuilt, kept, unlinked))
        self.assertEqual({'qa/Maildir/cur/1': 'message'}, self.files_below(self.folder))
        # A mail folder may be called `temp.x`; only files are taken for temporary files.
        self.assertEqual((1, 0, 0, 0), self.restore(('./qa/Maildir/.temp.x', tarfile.DIRTYPE, None),
                                                    ('./qa/Maildir/.temp.x/cur/2', tarfile.REGTYPE, 'message')))

    MDBOX = [('./imported', tarfile.DIRTYPE, None),
             ('./imported/Mdbox/storage/m.1', tarfile.REGTYPE, 'older storage'),
             ('./imported/Mdbox/storage/dovecot.map.index', tarfile.REGTYPE, 'older map'),
             ('./imported/Mdbox/mailboxes/INBOX/dbox-Mails/dovecot.index', tarfile.REGTYPE, 'older index'),
             ('./imported/sieve/filter.sieve', tarfile.REGTYPE, 'keep;'),
             ('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message')]

    def test_mailbox_that_holds_mail_in_mdbox_files_is_not_restored_and_the_others_are(self):
        live = {'imported/Mdbox/storage/m.1': 'storage with newer mail',
                'imported/Mdbox/storage/dovecot.map.index': 'newer map',
                'imported/Mdbox/mailboxes/INBOX/dbox-Mails/dovecot.index': 'newer index'}
        self.tree(self.folder, live)
        self.assertTrue(mailArchive.holds_mdbox(os.path.join(self.folder, 'imported')))
        self.assertEqual((1, 0, 0, 0), self.restore(*self.MDBOX))
        self.assertEqual(['imported'], self.counts['mdbox'])
        self.assertEqual(dict(live, **{'qa/Maildir/cur/1': 'message'}), self.files_below(self.folder))
        words = mailArchive.mdbox_words(self.counts['mdbox'])
        self.assertIn('Not restored: imported.', words)

    def test_mdbox_mailbox_is_restored_into_an_empty_folder_without_its_indexes(self):
        os.makedirs(os.path.join(self.folder, 'imported', 'Mdbox', 'storage'))
        self.assertFalse(mailArchive.holds_mdbox(os.path.join(self.folder, 'imported')))
        self.assertFalse(mailArchive.holds_mdbox(os.path.join(self.folder, 'absent')))
        self.assertEqual((3, 2, 0, 0), self.restore(*self.MDBOX))
        self.assertEqual([], self.counts['mdbox'])
        self.assertEqual({'imported/Mdbox/storage/m.1': 'older storage', 'imported/sieve/filter.sieve': 'keep;',
                          'qa/Maildir/cur/1': 'message'}, self.files_below(self.folder))

    def long_name_record(self, kind, size):
        heading = tarfile.TarInfo('././@LongLink' if kind != tarfile.XHDTYPE else './PaxHeaders/x')
        heading.type = kind
        heading.size = size
        return heading.tobuf(tarfile.GNU_FORMAT)

    def test_record_of_names_larger_than_any_name_is_refused_before_it_is_read(self):
        class Counted(io.BytesIO):
            taken = 0

            def read(self, size=-1):
                data = super().read(size)
                Counted.taken += len(data)
                return data

        for kind in (tarfile.GNUTYPE_LONGNAME, tarfile.GNUTYPE_LONGLINK, tarfile.XHDTYPE, tarfile.XGLTYPE):
            # The record claims 40 GB; the stream behind it would go on for ever.
            stream = Counted(self.long_name_record(kind, 40 << 30) + b'\0' * (4 << 20))
            Counted.taken = 0
            before = self.files_below(self.base)
            with self.assertRaises(mailArchive.Refused) as refusal:
                mailArchive.Unpacker(self.folder, ROOMY).check(stream)
            self.assertIn('no name is that long', str(refusal.exception))
            self.assertLess(Counted.taken, 1 << 20)
            self.assertEqual(before, self.files_below(self.base))
            with self.assertRaises(mailArchive.Refused):
                mailArchive.Unpacker(self.folder, ROOMY).write(
                    io.BytesIO(self.long_name_record(kind, 40 << 30)), '1:1:' + '0' * 64)

    def test_long_names_of_real_length_are_read(self):
        name = './qa/Maildir/.' + 'Folder.' * 20 + 'End/cur/' + 'm' * 150
        for style in (tarfile.PAX_FORMAT, tarfile.GNU_FORMAT):
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w', format=style) as archive:
                entry = tarfile.TarInfo(name)
                entry.size = 7
                archive.addfile(entry, io.BytesIO(b'message'))
            plan = mailArchive.Unpacker(self.folder, ROOMY).check(io.BytesIO(stream.getvalue()))
            mailArchive.Unpacker(self.folder, ROOMY).write(io.BytesIO(stream.getvalue()), plan)
            self.assertEqual({name[2:]: 'message'}, self.files_below(self.folder))
            shutil.rmtree(self.folder)

    def test_folders_already_checked_are_not_remembered_without_end(self):
        members = [('./box%d/Maildir/cur/1' % number, tarfile.REGTYPE, 'message') for number in range(40)]
        with mock.patch.object(mailArchive, 'MOST_REMEMBERED', 5):
            plan_reader = mailArchive.Unpacker(self.folder, ROOMY)
            plan = plan_reader.check(archive_of(*members))
            writer = mailArchive.Unpacker(self.folder, ROOMY)
            counts = writer.write(archive_of(*members), plan)
        self.assertEqual(40, counts['written'])
        for unpacker in (plan_reader, writer):
            self.assertLessEqual(len(unpacker.inside), 5)
            self.assertLessEqual(len(unpacker.keeps), 5)
        self.assertEqual(40, len(self.files_below(self.folder)))

    def test_reading_end_limits_its_memory_and_says_when_an_archive_needs_more(self):
        limits = []
        with mock.patch('os.geteuid', return_value=5000), \
                mock.patch.object(mailArchive.resource, 'setrlimit', side_effect=lambda *how: limits.append(how)), \
                mock.patch.object(mailArchive, 'Unpacker', side_effect=MemoryError()), \
                mock.patch('os.umask'), mock.patch('sys.stdout', io.StringIO()) as printed:
            status = mailArchive.main(['unpack', '--folder', self.folder, '--check'])
        self.assertEqual(mailArchive.STOPPED, status)
        self.assertEqual([(mailArchive.resource.RLIMIT_AS, (mailArchive.MOST_MEMORY, mailArchive.MOST_MEMORY))],
                         limits)
        self.assertIn('needs more memory than a restore may use', printed.getvalue())

    def test_reading_end_tells_an_archive_it_cannot_read_from_one_it_refuses(self):
        def run(data):
            with mock.patch('os.geteuid', return_value=5000), mock.patch('os.umask'), \
                    mock.patch.object(mailArchive.resource, 'setrlimit'), \
                    mock.patch.object(mailArchive, 'allowance', return_value=ROOMY), \
                    mock.patch('sys.stdin', SimpleNamespace(buffer=io.BytesIO(data))), \
                    mock.patch('sys.stdout', io.StringIO()) as printed:
                return mailArchive.main(['unpack', '--folder', self.folder, '--check']), printed.getvalue()

        status, said = run(b'')
        self.assertEqual(mailArchive.UNREADABLE, status)
        self.assertIn('The archive could not be read', said)
        whole = archive_of(('./qa/Maildir/cur/1', tarfile.REGTYPE, 'message' * 400)).getvalue()
        self.assertEqual(mailArchive.UNREADABLE, run(whole[:1024])[0])
        status, said = run(archive_of(('../x', tarfile.REGTYPE, 'evil')).getvalue())
        self.assertEqual(mailArchive.STOPPED, status)
        self.assertIn('leaves the mail folder', said)
        status, said = run(whole)
        self.assertEqual(0, status)
        self.assertRegex(said.strip(), r'^1:\d+:[0-9a-f]{64}$')

    def test_names_with_the_job_s_marker_words_are_ordinary_names(self):
        self.assertEqual((2, 0, 0, 0), self.restore(('./qa/Maildir/.Completed/cur/1', tarfile.REGTYPE, 'message'),
                                                    ('./qa/Maildir/.[5009]/cur/2', tarfile.REGTYPE, 'message')))
        message = self.refused(('./qa/Maildir/.Completed/../../../Completed', tarfile.REGTYPE, 'evil'))
        status = 'Restoring email..\n%s Nothing was written. [IncJobs.restoreEmail][5009]\n' % mailArchive.last_part(
            message)
        self.assertEqual(FAILED, job_end(status))

    def test_writer_does_not_run_as_root(self):
        if os.geteuid() != 0:
            self.skipTest('needs root')
        for how in (['--check'], ['--expect', '1:1:' + '0' * 64]):
            with mock.patch('sys.stdout', io.StringIO()) as printed:
                self.assertEqual(mailArchive.STOPPED, mailArchive.main(['unpack', '--folder', self.folder] + how))
            self.assertIn('not by root', printed.getvalue())
        self.assertFalse(os.path.exists(self.folder))


FAKE_RUSTIC = '''#!%s
"""Stands in for rustic: takes the words the panel gives it and keeps archives in a folder."""
import hashlib, json, os, shutil, sys
words = sys.argv[1:]
assert words[0] == '-r', words
repository, action, rest = words[1], words[2], words[3:]
assert rest[-2:] == ['--password', ''] or rest[-3:] == ['--password', '', '--json'], words
sys.stderr.write('[INFO] repository %%s\\n' %% repository)
if action == 'backup':
    assert rest[0] == '--stdin-filename' and rest[2] == '-' and rest[-1] == '--json', words
    data = sys.stdin.buffer.read()
    snapshot = hashlib.sha256(data + os.urandom(8)).hexdigest()
    os.makedirs(os.path.join(repository, snapshot))
    with open(os.path.join(repository, snapshot, rest[1]), 'wb') as handle:
        handle.write(data)
    print(json.dumps({'tree': 'cd' * 32, 'paths': [rest[1]], 'id': snapshot, 'summary': {'files_new': 1}}))
elif action == 'dump':
    snapshot, name = rest[0].split(':', 1)
    path = os.path.join(repository, snapshot, name)
    if not os.path.isfile(path):
        sys.exit('error: path not found in snapshot')
    with open(path, 'rb') as handle:
        shutil.copyfileobj(handle, sys.stdout.buffer)
elif action == 'forget':
    shutil.rmtree(os.path.join(repository, rest[0]))
else:
    sys.exit('unknown ' + action)
'''


@unittest.skipUnless(shutil.which('tar') and shutil.which('find'), 'needs tar and find')
class RepositoryTests(TemporaryFolder):
    """The whole way, with real programs, in a temporary folder.

    Started as root, the mail is owned by one account and the repository by
    another, each closed to the other, as on a server. Otherwise both ends
    run as the account the tests run as.
    """

    def setUp(self):
        super().setUp()
        os.chmod(self.base, 0o755)
        root = os.geteuid() == 0
        self.mail_account = account('nobody') if root else None
        self.site_account = account('daemon') if root else None
        if root and not (self.mail_account and self.site_account):
            self.skipTest('needs the accounts nobody and daemon')
        self.mail_root = os.path.join(self.base, 'vmail')
        self.site = os.path.join(self.base, 'site')
        self.repository = os.path.join(self.site, 'incbackup')
        self.password_file = os.path.join(self.site, 'password')
        self.environment = {'RESTIC_CACHE_DIR': os.path.join(self.site, 'cache')}
        os.makedirs(self.mail_root)
        os.makedirs(self.environment['RESTIC_CACHE_DIR'])
        with open(self.password_file, 'w') as handle:
            handle.write('repository-password\n')
        os.chmod(self.mail_root, 0o700)
        os.chmod(self.site, 0o700)
        self.give(self.mail_root, self.mail_account)
        self.give(self.site, self.site_account)

        if root:
            # The writing end is started from this file; the mail account must be able to read it.
            program = os.path.join(self.base, 'program')
            os.mkdir(program)
            for name in ('mailArchive.py', 'resticOutput.py', 'IncBackupPath.py'):
                shutil.copy(str(ROOT / 'IncBackups' / name), program)
            patch = mock.patch.object(mailArchive, 'PROGRAM', os.path.join(program, 'mailArchive.py'))
            patch.start()
            self.addCleanup(patch.stop)

    def give(self, path, name):
        if name:
            subprocess.check_call(['chown', '-R', name, path])

    def restic(self, *words):
        return subprocess.check_output(self.store().words + list(words), stderr=subprocess.STDOUT,
                                       **mailArchive.process_options(self.site_account, self.environment)).decode()

    def store(self):
        return mailArchive.Restic(self.repository, self.password_file, self.environment)

    def back_up(self, store=None, **accounts):
        return mailArchive.back_up('example.com', accounts.get('site', self.site_account), store or self.store(),
                                   mail_root=self.mail_root, mail_account=accounts.get('mail', self.mail_account))

    def restore(self, snapshot, mail_root=None, store=None, wait=5):
        return mailArchive.restore('example.com', self.site_account, store or self.store(), snapshot,
                                   mail_root=mail_root or self.mail_root, mail_account=self.mail_account,
                                   lock=os.path.join(self.base, 'restore.lock'), wait=wait)

    def save_archive(self, *members):
        """A snapshot whose mail archive is one made by hand, as the website's account can make one."""
        saving = subprocess.Popen(self.store().save('vmail-example.com.tar'), stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  **mailArchive.process_options(self.site_account, self.environment))
        output = saving.communicate(archive_of(*members).getvalue())[0].decode()
        return mailArchive.extract_snapshot_id(output)

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
        self.give(folder, self.mail_account)
        return files

    def elsewhere(self):
        path = os.path.join(self.base, 'restored')
        os.mkdir(path)
        os.chmod(path, 0o700)
        self.give(path, self.mail_account)
        return path

    def close(self, path):
        """Make a file or folder of the mail store one the mail account may not open."""
        if self.mail_account:
            subprocess.check_call(['chown', 'root', path])
        os.chmod(path, 0)
        self.addCleanup(os.chmod, path, 0o700)

    def owner(self, path):
        return pwd.getpwuid(os.lstat(path).st_uid).pw_name

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_mail_is_saved_and_comes_back(self):
        self.restic('init')
        files = self.mailboxes()
        outcome, snapshot = self.back_up()
        self.assertEqual(mailArchive.SAVED, outcome, snapshot)
        self.assertIn(snapshot[:8], self.restic('snapshots'))
        self.assertIn('/vmail-example.com.tar', self.restic('ls', snapshot))

        outcome, said = self.restore(snapshot, self.elsewhere())
        self.assertEqual((mailArchive.RESTORED, '5 mail files written'), (outcome, said))
        restored = os.path.join(self.base, 'restored', 'example.com')
        self.assertEqual(files, self.files_below(restored))
        self.assertEqual(2, os.stat(os.path.join(restored, 'qa/Maildir/cur/1.host:2,S')).st_nlink)
        self.assertEqual('sieve/managesieve.sieve', os.readlink(os.path.join(restored, 'qa/.dovecot.sieve')))
        self.assertEqual(1700000000, int(os.stat(os.path.join(restored, 'qa/Maildir/new/2.host')).st_mtime))
        for directory, _, names in os.walk(restored):
            self.assertEqual(0o700, stat.S_IMODE(os.stat(directory).st_mode), directory)
            for name in names:
                if not os.path.islink(os.path.join(directory, name)):
                    self.assertEqual(0o600, stat.S_IMODE(os.stat(os.path.join(directory, name)).st_mode), name)
        self.assertFalse([name for _, _, names in os.walk(restored) for name in names
                          if name.startswith('.mail-restore.')])

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_mail_account_reads_the_mail_and_website_account_writes_the_repository(self):
        if not self.mail_account:
            self.skipTest('needs root, to run the two ends as two accounts')
        self.restic('init')
        self.mailboxes()
        # Each account's files are closed to the other: the mail to the website, the repository to the mail.
        self.assertEqual(0o700, stat.S_IMODE(os.stat(self.mail_root).st_mode))
        self.assertEqual(0o700, stat.S_IMODE(os.stat(self.site).st_mode))
        self.assertNotEqual(self.mail_account, self.site_account)

        # With the two ends swapped nothing can be saved.
        outcome, detail = self.back_up(mail=self.site_account, site=self.mail_account)
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

        outcome, snapshot = self.back_up()
        self.assertEqual(mailArchive.SAVED, outcome, snapshot)
        # What the backup added to the repository is the website account's.
        for directory, _, names in os.walk(self.repository):
            for name in names:
                self.assertEqual(self.site_account, self.owner(os.path.join(directory, name)))
        outcome, said = self.restore(snapshot, self.elsewhere())
        self.assertEqual(mailArchive.RESTORED, outcome, said)
        # What the restore wrote is the mail account's.
        restored = os.path.join(self.base, 'restored', 'example.com')
        for directory, folders, names in os.walk(restored):
            for name in folders + names:
                self.assertEqual(self.mail_account, self.owner(os.path.join(directory, name)))

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_website_without_a_mail_folder_is_said_to_have_none(self):
        self.restic('init')
        self.assertEqual((mailArchive.NO_FOLDER, os.path.join(self.mail_root, 'example.com')), self.back_up())
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_folder_that_cannot_be_read_fails_and_leaves_no_snapshot(self):
        self.restic('init')
        self.mailboxes()
        self.close(os.path.join(self.mail_root, 'example.com', 'qa', 'Maildir', 'new', '2.host'))
        outcome, detail = self.back_up()
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('exists but could not be read in full', detail)
        self.assertIn('Permission denied', detail)
        # restic had saved what tar could read; that snapshot is gone.
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

        # The same for a mailbox the mail account may not enter.
        self.close(os.path.join(self.mail_root, 'example.com', 'qa', 'Maildir'))
        outcome, detail = self.back_up()
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('exists but could not be read in full', detail)
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_mail_behind_a_link_is_not_reported_as_saved(self):
        self.restic('init')
        self.mailboxes()
        folder = os.path.join(self.mail_root, 'example.com')
        moved = os.path.join(self.base, 'other-disk')
        os.mkdir(moved)
        self.give(moved, self.mail_account)
        # A mailbox an administrator moved away and linked back, and one linked with a path that climbs.
        os.symlink(moved, os.path.join(folder, 'moved'))
        os.symlink('../other.example/user', os.path.join(folder, 'climbs'))
        outcome, detail = self.back_up()
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('%s is a link to %s' % (os.path.join(folder, 'moved'), moved), detail)
        self.assertIn('climbs is a link to ../other.example/user', detail)
        self.assertIn('Mount the other location at that path', detail)
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))

        # The same for the domain's folder itself.
        os.remove(os.path.join(folder, 'moved'))
        os.remove(os.path.join(folder, 'climbs'))
        os.rename(folder, os.path.join(moved, 'example.com'))
        os.symlink(os.path.join(moved, 'example.com'), folder)
        outcome, detail = self.back_up()
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('%s is a link to' % folder, detail)
        self.assertNotIn('vmail-example.com.tar', self.restic('snapshots'))
        outcome, detail = self.restore('1a2b3c4d')
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('not restored through a link', detail)

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_archive_the_restore_refuses_is_reported_with_the_restore_s_reason(self):
        self.restic('init')
        self.mailboxes()
        before = self.files_below(self.mail_root)
        # Enough content that restic is still writing when the reading end stops.
        snapshot = self.save_archive(('./qa/Maildir/cur/1.host:2,S', tarfile.REGTYPE, 'overwritten'),
                                     ('../other.example/user/Maildir/cur/evil', tarfile.REGTYPE, 'evil'),
                                     ('./qa/Maildir/cur/filler', tarfile.REGTYPE, 'x' * (8 << 20)))
        outcome, detail = self.restore(snapshot)
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('a name that leaves the mail folder', detail)
        self.assertIn('Nothing was written', detail)
        self.assertNotIn('No mail archive could be read', detail)
        self.assertNotIn('roken pipe', detail)
        self.assertEqual(before, self.files_below(self.mail_root))

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_mdbox_mailbox_in_use_is_left_alone_and_the_job_is_told(self):
        self.restic('init')
        self.mailboxes()
        folder = os.path.join(self.mail_root, 'example.com')
        self.tree(folder, {'imported/Mdbox/storage/m.1': 'storage at backup time',
                           'imported/Mdbox/storage/dovecot.map.index': 'map at backup time'})
        self.give(folder, self.mail_account)
        outcome, snapshot = self.back_up()
        self.assertEqual(mailArchive.SAVED, outcome, snapshot)
        self.tree(folder, {'imported/Mdbox/storage/m.1': 'storage with newer mail'})
        os.remove(os.path.join(folder, 'qa/Maildir/new/2.host'))
        self.give(folder, self.mail_account)

        outcome, detail = self.restore(snapshot)
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('Only part of the mail was restored: 5 mail files written', detail)
        self.assertIn('Not restored: imported.', detail)
        self.assertIn('Restore them into an empty mailbox folder, or ask support.', detail)
        self.assertEqual('storage with newer mail', content(os.path.join(folder, 'imported/Mdbox/storage/m.1')))
        self.assertEqual('second message\n', content(os.path.join(folder, 'qa/Maildir/new/2.host')))

    def test_one_restore_of_mail_runs_at_a_time(self):
        lock = os.path.join(self.base, 'restore.lock')
        first = mailArchive.restore_turn(lock, 0)
        self.assertIsNotNone(first)
        self.assertEqual(0o600, stat.S_IMODE(os.stat(lock).st_mode))
        try:
            self.assertIsNone(mailArchive.restore_turn(lock, 0))
            with mock.patch.object(mailArchive, 'run_joined') as joined:
                outcome, detail = self.restore('1a2b3c4d', wait=0.3)
            joined.assert_not_called()
            self.assertEqual(mailArchive.FAILED, outcome)
            self.assertIn('Another restore of mail is running on this server', detail)
            self.assertIn('Nothing was written', detail)
        finally:
            os.close(first)
        # The turn is free again, and a restore that ends gives it back.
        with mock.patch.object(mailArchive, 'run_joined', return_value=(0, '', mailArchive.STOPPED, 'no\n')):
            self.assertEqual(mailArchive.FAILED, self.restore('1a2b3c4d', wait=0)[0])
        second = mailArchive.restore_turn(lock, 0)
        self.assertIsNotNone(second)
        os.close(second)
        os.symlink(os.path.join(self.base, 'elsewhere'), os.path.join(self.base, 'link.lock'))
        with self.assertRaises(OSError):
            mailArchive.restore_turn(os.path.join(self.base, 'link.lock'), 0)
        self.assertFalse(os.path.exists(os.path.join(self.base, 'elsewhere')))
        self.assertEqual('/run/cyberpanel-mail-restore.lock', mailArchive.RESTORE_LOCK)

    @unittest.skipUnless(shutil.which('restic'), 'needs restic')
    def test_snapshot_without_a_mail_archive_is_not_restored(self):
        self.restic('init')
        plain = os.path.join(self.site, 'plain')
        self.tree(plain, {'file': 'x'})
        self.give(plain, self.site_account)
        snapshot = mailArchive.extract_snapshot_id(self.restic('backup', plain))
        outcome, detail = self.restore(snapshot, self.elsewhere())
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('No mail archive could be read from snapshot', detail)
        self.assertIn('Nothing was written', detail)
        self.assertEqual([], os.listdir(os.path.join(self.base, 'restored')))

    def test_only_a_snapshot_id_is_asked_of_the_backup_program(self):
        for snapshot in ('latest', '--help', '', None, '1a2b3c4d --target /'):
            with self.assertRaises(mailArchive.Refused):
                self.restore(snapshot)

    def test_backup_v2_repository_is_written_and_read_by_the_website_account(self):
        tools = os.path.join(self.base, 'bin')
        os.mkdir(tools)
        with open(os.path.join(tools, 'rustic'), 'w') as handle:
            handle.write(FAKE_RUSTIC % sys.executable)
        os.chmod(os.path.join(tools, 'rustic'), 0o755)
        patch = mock.patch.object(mailArchive, 'SEARCH_PATH', tools + ':' + mailArchive.SEARCH_PATH)
        patch.start()
        self.addCleanup(patch.stop)
        repository = os.path.join(self.site, 'incrementalbackups')
        os.mkdir(repository)
        self.give(repository, self.site_account)
        store = mailArchive.Rustic(repository)

        files = self.mailboxes()
        # A lock of Dovecot's, caught while it is the second name of its temporary file,
        # and a mail folder whose name ends the way a lock's does.
        folder = os.path.join(self.mail_root, 'example.com')
        self.tree(folder, {'qa/Maildir/.temp.host.99.abcdef': '1 V1 N2\n', 'qa/Maildir/.notes.lock/cur/4': 'kept\n'})
        os.link(os.path.join(folder, 'qa/Maildir/.temp.host.99.abcdef'),
                os.path.join(folder, 'qa/Maildir/dovecot-uidlist.lock'))
        self.tree(folder, {'qa/Maildir/.Sent/dovecot.index.log.lock': '', 'qa/Maildir/maildirsize.lock': ''})
        for directory, _, _ in os.walk(folder):
            os.chmod(directory, 0o700)
        self.give(folder, self.mail_account)
        files['qa/Maildir/.notes.lock/cur/4'] = 'kept\n'

        outcome, snapshot = self.back_up(store)
        self.assertEqual(mailArchive.SAVED, outcome, snapshot)
        self.assertEqual(['vmail-example.com.tar'], os.listdir(os.path.join(repository, snapshot)))
        with tarfile.open(os.path.join(repository, snapshot, 'vmail-example.com.tar')) as archive:
            names = archive.getnames()
        self.assertFalse([name for name in names if name.endswith('.lock') and '/.notes.lock' not in name], names)
        self.assertIn('./qa/Maildir/.notes.lock/cur/4', names)
        self.assertIn('./qa/Maildir/cur/1.host:2,S', names)
        if self.site_account:
            self.assertEqual(self.site_account, self.owner(os.path.join(repository, snapshot)))
        outcome, said = self.restore(snapshot, self.elsewhere(), store)
        self.assertEqual((mailArchive.RESTORED, '6 mail files written, 1 index, lock and compiled filter files '
                          'left out (Dovecot makes them again)'), (outcome, said))
        self.assertEqual(files, self.files_below(os.path.join(self.base, 'restored', 'example.com')))

        # A partial archive is forgotten there too.
        self.close(os.path.join(self.mail_root, 'example.com', 'qa', 'Maildir', 'new', '2.host'))
        outcome, detail = self.back_up(store)
        self.assertEqual(mailArchive.FAILED, outcome)
        self.assertIn('exists but could not be read in full', detail)
        self.assertEqual([snapshot], os.listdir(repository))


class Runner:
    """The job's command runner: records each command with the account it runs as."""

    def __init__(self, output):
        self.output = output
        self.ran = []

    def outputExecutioner(self, command, user=None, shell=None, dir=None, retRequired=None):
        self.ran.append((command, user))
        return self.output(command) if callable(self.output) else self.output


class JobStepTests(TemporaryFolder):
    def setUp(self):
        super().setUp()
        patch = mock.patch.object(mailArchive, 'SECRET_FOLDER', self.base)
        patch.start()
        self.addCleanup(patch.stop)

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
                       'so its mail was not backed up: tar: ./qa/Maildir/.Completed: Cannot open: Permission denied\n',
                       '[mail-archive] failed The mail of example.com was not backed up: /home/vmail/example.com/qa '
                       'is a link to /mnt/disk2/qa.\n',
                       'Traceback (most recent call last):\n', '', None):
            job = self.job(output)
            self.assertEqual(0, self.step('emailBackup', job), output)
            self.assertEqual([], self.saved)
            self.assertIn('[5009]', self.status[-1])
            self.assertFalse([line for line in self.status if 'backed to' in line])
            self.assertEqual(FAILED, job_end('\n'.join(self.status)))

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

    def test_recorded_snapshot_is_restored_by_the_helper_and_the_status_says_what_was_left_alone(self):
        snapshot = SimpleNamespace(type='email:/home/vmail/example.com', destination='local', snapshotid='1a2b3c4d')
        job = self.job('[mail-archive] restored 6 mail files written, 7 index files of Dovecot left as they are '
                       'on the server\n', website='example.com', jobid=snapshot)
        self.assertEqual(1, self.step('restoreEmail', job))
        self.assertEqual(('restore', {'--domain': 'example.com', '--account': 'examp1234',
                                      '--repository': '/home/example.com/incbackup',
                                      '--password-file': '/home/example.com/example.com',
                                      '--snapshot': '1a2b3c4d'}), self.options())
        self.assertEqual('Mail restored to /home/vmail/example.com: 6 mail files written, 7 index files of Dovecot '
                         'left as they are on the server.', self.status[-1])
        job.localFunction.assert_not_called()
        self.assertEqual([], os.listdir(self.base))

    def test_typed_password_reaches_the_helper_in_a_private_file_that_is_then_removed(self):
        seen = []

        def helper(command):
            path = dict(zip(shlex.split(command)[3::2], shlex.split(command)[4::2]))['--password-from']
            seen.append((path, content(path), stat.S_IMODE(os.stat(path).st_mode)))
            return '[mail-archive] restored 6 mail files written\n'

        for output in (helper, lambda command: helper(command) and '[mail-archive] failed no\n'):
            job = self.job(output, website='example.com', jobid='1a2b3c4d', reconstruct='remote',
                           destination='s3:s3.amazonaws.com/AKIAEXAMPLE', passwordFile='typed pass word')
            self.step('restoreEmail', job)
            action, options = self.options()
            self.assertEqual({'--domain': 'example.com', '--account': 'examp1234',
                              '--repository': 's3:s3.amazonaws.com/example.com',
                              '--password-from': seen[-1][0], '--aws-key': 'AKIAEXAMPLE',
                              '--snapshot': '1a2b3c4d'}, options)
            self.assertEqual((os.path.dirname(seen[-1][0]), 'typed pass word', 0o600), (self.base,) + seen[-1][1:])
            self.assertNotIn('typed', self.runner.ran[-1][0])
            self.assertEqual([], os.listdir(self.base))
            job.awsFunction.assert_not_called()

    def test_restore_that_did_not_happen_fails(self):
        snapshot = SimpleNamespace(type='email:/home/vmail/example.com', destination='local', snapshotid='1a2b3c4d')
        for output in ('[mail-archive] failed No mail archive could be read from snapshot 1a2b3c4d\n', '', None,
                       '[mail-archive] saved 1a2b3c4d\n'):
            job = self.job(output, website='example.com', jobid=snapshot)
            self.assertEqual(0, self.step('restoreEmail', job), output)
            self.assertIn('[5009]', self.status[-1])


class V2StepTests(unittest.TestCase):
    """Backup V2 keeps mail the same way: nothing of it runs rustic or rclone with privilege."""

    def namespace(self, output):
        self.ran = []
        self.status = []

        def run(command, user=None, shell=None, dir=None, retRequired=None):
            self.ran.append((command, user))
            return output

        return dict(json=json, os=os, shlex=shlex,
                    ProcessUtilities=SimpleNamespace(executioner=lambda command, user=None, shell=None: self.ran.append(
                        (command, user)) or 1, outputExecutioner=run),
                    CPBackupsV2=SimpleNamespace(NO_MAIL_FOLDER=2, FAILED=3, RUNNING=1,
                                                StatusText=load_method(V2, 'CPBackupsV2', 'StatusText', {})))

    def backup(self, output):
        step = load_method(V2, 'CPBackupsV2', 'BackupEmailsRustic', self.namespace(output))
        job = SimpleNamespace(website=SimpleNamespace(domain='example.com', externalApp='examp1234'),
                              repo=shlex.quote('rclone:offsite:example.com'), snapshots=[],
                              UpdateStatus=lambda message, state: self.status.append((message, state)))
        return step(job), job

    def test_mail_is_saved_through_the_helper_as_the_two_accounts(self):
        snapshot = 'ab' * 32
        result, job = self.backup('[mail-archive] saved %s\n' % snapshot)
        self.assertEqual(1, result)
        self.assertEqual([snapshot], job.snapshots)
        command, user = self.ran[-1]
        self.assertIsNone(user)
        self.assertEqual(shlex.split(mailArchive.helper_command(
            'backup', 'example.com', 'examp1234', 'rclone:offsite:example.com', program='rustic')),
            shlex.split(command))
        # The only command with privilege is the helper; rustic itself is given to the website's account.
        for command, user in self.ran:
            if user is None:
                self.assertEqual(mailArchive.PYTHON, shlex.split(command)[0])
            else:
                self.assertEqual('examp1234', user)

    def test_website_without_mail_saves_nothing_and_says_so(self):
        result, job = self.backup('[mail-archive] no-mail-folder /home/vmail/example.com\n')
        self.assertEqual(2, result)
        self.assertEqual([], job.snapshots)
        source = (ROOT / V2).read_text()
        self.assertIn("elif emailsSaved == CPBackupsV2.NO_MAIL_FOLDER:\n"
                      "                            self.UpdateStatus('This website has no mail folder: "
                      "there are no emails to back up..,85',", source)

    def test_mail_that_was_not_saved_fails_the_step_with_the_reason(self):
        for output in ('[mail-archive] failed /home/vmail/example.com/qa/[200],x is a link to /mnt\n', '', None):
            result, job = self.backup(output)
            self.assertEqual(0, result, output)
            self.assertEqual([], job.snapshots)
            message, state = self.status[-1]
            self.assertEqual(3, state)
            # Nothing a mail folder is named can pass for the marks or the percentage of a status line.
            self.assertNotIn('[', message)
            self.assertNotIn(',', message)

    def test_no_step_runs_rustic_or_rclone_with_privilege_on_the_website_s_settings(self):
        source = (ROOT / V2).read_text()
        self.assertNotIn('export RCLONE_CONFIG', source)
        self.assertNotIn('RCLONE_CONFIG=/home/', source)
        # Commands are built in a variable first; each rustic command names the account it runs as.
        lines = source.splitlines()
        for number, line in enumerate(lines):
            if "command = f'rustic " in line or 'command = restore_command(' in line:
                following = ' '.join(lines[number + 1:number + 4])
                self.assertIn('self.website.externalApp', following, number + 1)

    def test_job_does_not_end_as_completed_after_a_step_that_failed(self):
        source = (ROOT / V2).read_text()
        end = source[source.index('### Finally change the backup rustic folder to the website user owner'):
                     source.index("self.UpdateStatus('Completed', CPBackupsV2.COMPLETED)")]
        self.assertIn('if not self.MergeSnapshotFlag:', end)
        self.assertLess(end.index('return 0'), end.index('self.MergeSnapshots()'))

    def restore(self, kind, value, output):
        from plogical import backupV2Repository
        self.assertEqual((kind, value), backupV2Repository.restore_target(value, 'example.com'))
        source = (ROOT / V2).read_text()
        start = source.index("                elif restoreKind == 'mail':")
        block = source[start:source.index("                self.UpdateStatus('Completed', CPBackupsV2.COMPLETED)", start)]
        program = ('def restore_step(self, restoreKind, restoreValue, snapshot):\n    if True:\n'
                   '                if False:\n                    pass\n' + block + '\n    return 1\n')
        namespace = self.namespace(output)
        namespace['restore_command'] = backupV2Repository.restore_command
        namespace['logging'] = SimpleNamespace(CyberCPLogFileWriter=SimpleNamespace(writeToFile=lambda text: None))
        namespace['ProcessUtilities'].debugPath = '/nonexistent-debug'
        namespace['ProcessUtilities'].outputExecutioner = lambda command, user=None, *more: (
            self.ran.append((command, user)) or (output if user is None else (1, '')))
        exec(program, namespace)
        job = SimpleNamespace(website=SimpleNamespace(domain='example.com', externalApp='examp1234'),
                              repo=shlex.quote('rclone:offsite:example.com'),
                              UpdateStatus=lambda message, state: self.status.append((message, state)))
        return namespace['restore_step'](job, kind, value, 'ab' * 32)

    def test_mail_archive_is_restored_through_the_helper(self):
        result = self.restore('mailarchive', 'vmail-example.com.tar',
                              '[mail-archive] restored 6 mail files written, 7 index files of Dovecot left\n')
        self.assertEqual(1, result)
        self.assertEqual([(mailArchive.helper_command('restore', 'example.com', 'examp1234',
                                                      'rclone:offsite:example.com', program='rustic',
                                                      snapshot='ab' * 32), None)], self.ran)
        self.assertEqual(('Mail restored: 6 mail files written; 7 index files of Dovecot left..,90', 1),
                         self.status[-1])
        self.assertEqual(0, self.restore('mailarchive', 'vmail-example.com.tar', '[mail-archive] failed no\n'))
        self.assertEqual(3, self.status[-1][1])

    def test_mail_saved_as_a_folder_tree_is_refused_and_nothing_runs(self):
        for path in ('/home/vmail/example.com', '/home/vmail/example.com/qa/Maildir'):
            self.assertEqual(0, self.restore('mail', path, 'unused'))
            self.assertEqual([], self.ran)
            message, state = self.status[-1]
            self.assertEqual(3, state)
            self.assertIn('does not restore mail in that form', message)

    def test_website_files_are_still_restored_as_the_website_account(self):
        self.assertEqual(1, self.restore('files', '/home/example.com/public_html', 'unused'))
        self.assertEqual(['examp1234'], [user for command, user in self.ran])

    def test_only_this_website_s_archive_is_a_mail_archive(self):
        from plogical import backupV2Repository
        self.assertEqual('vmail-example.com.tar', mailArchive.archive_name('example.com'))
        for path in ('vmail-other.example.tar', '/vmail-example.com.tar', 'vmail-example.com.tar/x'):
            with self.assertRaises(ValueError):
                backupV2Repository.restore_target(path, 'example.com')


class JobOrderTests(unittest.TestCase):
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
            done = self.restore(kind, 1)
            self.assertEqual([said, 'Completed'], done[-2:], kind)
            self.assertEqual(DONE, job_end('\n'.join(done)))
            failed = self.restore(kind, 0)
            self.assertNotIn(said, failed, kind)
            self.assertNotIn('Completed', failed, kind)

    def remote(self, path):
        namespace = dict(
            mailArchive=mailArchive,
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda domain: SimpleNamespace(externalApp='examp1234'))),
            logging=SimpleNamespace(statusWriter=lambda path, message, append=None: None))
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

    def test_meta_snapshot_is_saved_before_the_mail_and_a_failure_of_either_fails_the_job(self):
        source = (ROOT / SOURCE).read_text()
        job = source[source.index('            if self.prepareBackupMeta() == 0:'):source.index('    ### Delete Snapshot')]
        order = [job.index(step) for step in ('self.backupData()', 'self.backupDatabases()',
                                              'metaSaved = self.metaBackup()', "command = 'rm -f %s' % (metaPathNew)",
                                              'if metaSaved == 0:\n                return 0',
                                              'if self.emailBackup() == 0:\n                    return 0',
                                              "logging.statusWriter(self.statusPath, 'Completed', 1)")]
        self.assertEqual(sorted(order), order)

    def test_sftp_step_says_why_it_ends(self):
        status = []
        namespace = dict(logging=SimpleNamespace(
            statusWriter=lambda path, message, append=None: status.append(message)))
        step = load_method(SOURCE, 'IncJobs', 'sftpFunction', namespace)
        self.assertEqual(0, step(SimpleNamespace(statusPath='/dev/null'), '/home/example.com', 'data'))
        self.assertEqual(FAILED, job_end(status[-1]))
        self.assertIn('SFTP', status[-1])


if __name__ == '__main__':
    unittest.main()
