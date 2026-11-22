#!/usr/local/CyberCP/bin/python
"""Save a website's mail in its backup repository, and bring it back.

The mail store belongs to the mail account and the repository to the
website's account, and neither account can read the other's files. So no
single program handles both. The mail is read, or written, by a process that
runs as the mail account; the repository is opened by the backup program
(restic for incremental backups, rustic for Backup V2) running as the
website's account, with that account's own settings; the two are joined by a
pipe that carries one tar archive.

This program is started with root privilege for one purpose: to start those
two processes under their accounts. It reads no mail, opens no repository and
reads no file of the website's itself.

The last line it prints is the outcome, for the backup job to read:

    [mail-archive] saved <snapshot id>
    [mail-archive] no-mail-folder <folder>
    [mail-archive] restored <what was written and what was left alone>
    [mail-archive] failed <reason>
"""
import argparse
import errno
import hashlib
import os
import pwd
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile

try:
    from .resticOutput import extract_snapshot_id
    from .IncBackupPath import IncBackupPath
except ImportError:  # started as a program
    from resticOutput import extract_snapshot_id
    from IncBackupPath import IncBackupPath

MAIL_ROOT = '/home/vmail'
MAIL_ACCOUNT = 'vmail'
PYTHON = '/usr/local/CyberCP/bin/python'
PROGRAM = os.path.abspath(__file__)
SEARCH_PATH = '/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin'

# Where the panel's own account keeps a secret for this program for a moment.
SECRET_FOLDER = '/home/cyberpanel'

OUTCOME_MARK = '[mail-archive]'
SAVED = 'saved'
NO_FOLDER = 'no-mail-folder'
RESTORED = 'restored'
FAILED = 'failed'

PRESENT = 'present'
ABSENT = 'absent'
LINK = 'link'
NOT_A_FOLDER = 'not-a-folder'
UNKNOWN = 'unknown'

# A restore may fill the disk up to a reserve: a twentieth of the file system,
# at least one and at most ten gigabytes. Every entry is counted as one block
# on top of its content.
RESERVE_SHARE = 0.05
LEAST_RESERVE = 1 << 30
MOST_RESERVE = 10 << 30
ENTRY_COST = 4096
MOST_ENTRIES = 10000000

RELINK = ('Mail behind a link that leaves the mail folder is not backed up, because such a link can lead to '
          'another website\'s mail. Mount the other location at that path instead of linking to it (a bind '
          'mount works), then run the backup again.')

_DOMAIN = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
_SNAPSHOT = re.compile(r'^[0-9a-f]{8,64}$')
_PLAN = re.compile(r'^(\d+):(\d+):([0-9a-f]{64})$')
_RUSTIC_SAVED = re.compile(r'"id"\s*:\s*"([0-9a-f]{64})"')


class Refused(Exception):
    """The request or the archive is not one this program acts on."""


# ---------------------------------------------------------------- names

def mail_folder(domain, mail_root=MAIL_ROOT):
    """The folder that holds every mailbox of a domain."""
    if not _DOMAIN.match(domain or '') or '..' in domain:
        raise Refused('%r is not a domain name.' % (domain,))
    return os.path.join(mail_root, domain)


def archive_name(domain):
    """The name a domain's mail archive has inside a snapshot."""
    return 'vmail-%s.tar' % domain


def archive_path(domain):
    """The path restic lists for a snapshot of a domain's mail."""
    return '/' + archive_name(domain)


def folder_state(folder):
    """Whether a mail folder is there, is missing, or cannot be told.

    Only a lookup that fails because the folder does not exist means ABSENT.
    A lookup that is refused says nothing about the folder, and is UNKNOWN.
    """
    try:
        mode = os.lstat(folder).st_mode
    except OSError as error:
        if error.errno in (errno.ENOENT, errno.ENOTDIR):
            return ABSENT
        return UNKNOWN
    if stat.S_ISLNK(mode):
        return LINK
    return PRESENT if stat.S_ISDIR(mode) else NOT_A_FOLDER


def shown(name):
    """A name out of the mail store or an archive, fit for one line of a message."""
    return ''.join(char if char.isprintable() else '?' for char in name)


def leaves(target):
    """Whether a link with this target points anywhere but further down from where it is."""
    return not target or target.startswith('/') or '..' in target.split('/')


# ------------------------------------------------- the backup job's side

def helper_command(action, domain, account, repository, program=None, password_file=None,
                   password_from=None, aws_key=None, snapshot=None):
    """The command line that runs this program for the backup job."""
    words = [PYTHON, PROGRAM, action, '--domain', domain, '--account', account, '--repository', repository]
    for option, value in (('--program', program), ('--password-file', password_file),
                          ('--password-from', password_from), ('--aws-key', aws_key), ('--snapshot', snapshot)):
        if value is not None:
            words += [option, str(value)]
    return ' '.join(shlex.quote(word) for word in words)


def keep_secret(value):
    """Put a secret in a file only the panel's account can read; returns the file's name.

    A command line can be read by every account on the server, so a secret
    never goes on one. This program is given the file's name instead.
    """
    descriptor, path = tempfile.mkstemp(prefix='repository-password-', dir=SECRET_FOLDER)
    with os.fdopen(descriptor, 'w') as handle:
        handle.write(value)
    return path


def forget_secret(path):
    if path:
        try:
            os.remove(path)
        except OSError:
            pass


def read_secret(path):
    """The secret the panel left for this program. Only a plain file of the panel's own folder is read."""
    if os.path.dirname(os.path.abspath(path)) != SECRET_FOLDER:
        raise Refused('The password file is not one of the panel\'s own.')
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise Refused('The password file is not a plain file.')
        return os.read(descriptor, 4096).decode('utf-8', 'replace').rstrip('\n')
    finally:
        os.close(descriptor)


def read_outcome(output):
    """(outcome, detail) from what this program printed.

    Output without an outcome line is a failure: the program did not finish.
    """
    lines = [line.strip() for line in (output or '').splitlines()]
    for line in reversed(lines):
        if line.startswith(OUTCOME_MARK):
            words = line[len(OUTCOME_MARK):].strip().split(' ', 1)
            if words[0] in (SAVED, NO_FOLDER, RESTORED, FAILED):
                return words[0], words[1].strip() if len(words) > 1 else ''
    said = ' | '.join(line for line in lines if line)
    return FAILED, 'The mail helper did not report a result%s' % (': ' + last_part(said) if said else '.')


def last_part(text, limit=1500):
    """The end of a program's messages, on one line."""
    line = ' | '.join(shown(part.strip()) for part in (text or '').splitlines() if part.strip())
    return line if len(line) <= limit else '... ' + line[-limit:]


# ------------------------------------------------------ the backup programs

class Restic(object):
    """An incremental backup repository."""

    def __init__(self, repository, password_file=None, environment=None):
        self.environment = dict(environment or {})
        self.words = ['restic', '-r', repository]
        if password_file:
            self.words += ['--password-file', password_file]

    def save(self, name):
        return self.words + ['backup', '--stdin', '--stdin-filename', name]

    def dump(self, snapshot, name):
        return self.words + ['dump', snapshot, '/' + name]

    def forget(self, snapshot):
        return self.words + ['forget', snapshot]

    def saved(self, output):
        try:
            return extract_snapshot_id(output)
        except ValueError:
            return None


class Rustic(object):
    """A Backup V2 repository. Its storage settings are the website account's own rclone settings."""

    environment = {}

    def __init__(self, repository):
        self.repository = repository

    def save(self, name):
        return ['rustic', '-r', self.repository, 'backup', '--stdin-filename', name, '-', '--password', '', '--json']

    def dump(self, snapshot, name):
        return ['rustic', '-r', self.repository, 'dump', '%s:%s' % (snapshot, name), '--password', '']

    def forget(self, snapshot):
        return ['rustic', '-r', self.repository, 'forget', snapshot, '--password', '']

    def saved(self, output):
        found = _RUSTIC_SAVED.findall(output or '')
        return found[-1] if found else None


# ------------------------------------------------------------- judging

def judge_backup(folder, snapshot, reader_status, reader_errors, store_status, store_output):
    """(outcome, detail, snapshot to discard) for a finished backup.

    tar ends with status 1 when files changed or went away while it read
    them, which a mail store in use does all the time: that archive is good.
    Any other failure of the reader means mail is missing from the archive,
    and the snapshot made of it must not be kept.
    """
    if store_status != 0 or snapshot is None:
        said = last_part(store_output) or last_part(reader_errors) or 'the backup program gave no message'
        return FAILED, 'The mail in %s was not saved: %s' % (folder, said), snapshot
    if reader_status not in (0, 1):
        said = last_part(reader_errors) or 'the reader ended with status %s' % reader_status
        return FAILED, ('%s exists but could not be read in full, so its mail was not backed up: %s'
                        % (folder, said)), snapshot
    return SAVED, snapshot, None


def judge_restore(folder, snapshot, store_status, store_errors, writer_status, writer_output):
    """(outcome, what the writing end printed) for one pass of a restore."""
    if store_status != 0:
        said = last_part(store_errors) or 'the backup program ended with status %s' % store_status
        hint = ''
        if 'not found' in said.lower() or 'not exist' in said.lower():
            hint = ' Snapshots of mail made before CyberPanel 3.0.13 hold no mail archive.'
        return FAILED, 'No mail archive could be read from snapshot %s: %s.%s' % (snapshot, said, hint)
    if writer_status != 0:
        return FAILED, last_part(writer_output) or 'the writer ended with status %s' % writer_status
    lines = writer_output.strip().splitlines()
    return RESTORED, lines[-1].strip() if lines else ''


def restored_words(written, kept, unlinked):
    """What a restore did, for the job's status."""
    words = '%s mail files written' % written
    if kept:
        words += ', %s index files of Dovecot left as they are on the server' % kept
    if unlinked:
        words += ', %s second names of files left out because their file was not restored' % unlinked
    return words


# ---------------------------------------------------- running the two ends

def process_options(account, more_environment=None):
    """How subprocess starts a program as an account. None is the account this program runs as."""
    environment = {'PATH': SEARCH_PATH, 'LC_ALL': 'C'}
    switch = None
    if account is None:
        environment['HOME'] = os.environ.get('HOME', '/')
    else:
        entry = pwd.getpwnam(account)
        environment['HOME'] = entry.pw_dir

        def switch():
            os.initgroups(entry.pw_name, entry.pw_gid)
            os.setgid(entry.pw_gid)
            os.setuid(entry.pw_uid)
    environment.update(more_environment or {})
    return dict(preexec_fn=switch, env=environment, cwd='/', close_fds=True)


def run_joined(first, second):
    """Run two programs, the first writing into the second.

    Each is (words, options). Returns the first program's status and error
    messages, then the second program's status and everything it printed.
    """
    with tempfile.TemporaryFile() as errors:
        producer = subprocess.Popen(first[0], stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=errors, **first[1])
        try:
            consumer = subprocess.Popen(second[0], stdin=producer.stdout, stdout=subprocess.PIPE,
                                        stderr=subprocess.STDOUT, **second[1])
        except BaseException:
            producer.kill()
            producer.wait()
            raise
        finally:
            producer.stdout.close()
        output = consumer.communicate()[0]
        producer.wait()
        errors.seek(0)
        return (producer.returncode, errors.read().decode('utf-8', 'replace'),
                consumer.returncode, output.decode('utf-8', 'replace'))


def look(folder):
    """Whether a domain's mail folder can be backed up. Returns (PRESENT, NO_FOLDER or FAILED, detail)."""
    state = folder_state(folder)
    if state == ABSENT:
        return NO_FOLDER, folder
    if state == LINK:
        return FAILED, '%s is a link to %s, so its mail was not backed up. %s' % (
            folder, shown(os.readlink(folder)), RELINK)
    if state != PRESENT:
        return FAILED, '%s is there but is not a folder that can be read, so its mail was not backed up.' % folder
    return PRESENT, folder


def links_out(folder, mail_account):
    """(links below folder that lead out of it, what went wrong while looking), found as the mail account.

    tar saves a link as a link. The mail behind a link that leads elsewhere
    would be missing from an archive that is then reported as saved.
    """
    finder = subprocess.Popen(['find', folder, '-type', 'l', '-printf', '%P\\0%l\\0'],
                              stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                              **process_options(mail_account))
    output, errors = finder.communicate()
    fields = output.decode('utf-8', 'replace').split('\0')
    found = [(name, target) for name, target in zip(fields[0::2], fields[1::2]) if leaves(target)]
    return found, (last_part(errors.decode('utf-8', 'replace')) or 'find ended with status %s' % finder.returncode
                   ) if finder.returncode != 0 else ''


def back_up(domain, account, store, mail_root=MAIL_ROOT, mail_account=MAIL_ACCOUNT):
    """Save the mail of a domain as one snapshot. Returns (outcome, detail)."""
    folder = mail_folder(domain, mail_root)
    outcome, detail = look(folder)
    if outcome != PRESENT:
        return outcome, detail

    outward, unread = links_out(folder, mail_account)
    if unread:
        return FAILED, '%s exists but could not be read in full, so its mail was not backed up: %s' % (folder, unread)
    if outward:
        named = '; '.join('%s is a link to %s' % (shown(os.path.join(folder, name)), shown(target))
                          for name, target in outward[:3])
        more = ' (and %s more)' % (len(outward) - 3) if len(outward) > 3 else ''
        return FAILED, 'The mail of %s was not backed up: %s%s. %s' % (domain, named, more, RELINK)

    reader = (['tar', '--create', '--file=-', '--directory=' + folder, '.'], process_options(mail_account))
    writer = (store.save(archive_name(domain)), process_options(account, store.environment))
    reader_status, reader_errors, store_status, store_output = run_joined(reader, writer)
    outcome, detail, discard = judge_backup(folder, store.saved(store_output), reader_status, reader_errors,
                                            store_status, store_output)
    if discard:
        # An archive that lacks mail is not left where a restore could pick it.
        subprocess.call(store.forget(discard), stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL, **process_options(account, store.environment))
    return outcome, detail


def restore(domain, account, store, snapshot, mail_root=MAIL_ROOT, mail_account=MAIL_ACCOUNT):
    """Unpack the mail archive of a snapshot over the domain's mail folder. Returns (outcome, detail).

    The archive is read twice. The first time every entry is checked and
    nothing is written, so an archive that is refused leaves the mail as it
    was. The second time it is written, and it has to be the archive that
    was checked.
    """
    folder = mail_folder(domain, mail_root)
    if not _SNAPSHOT.match(snapshot or ''):
        raise Refused('%r is not a snapshot id.' % (snapshot,))
    state = folder_state(folder)
    if state == LINK:
        return FAILED, '%s is a link to %s; mail is not restored through a link. Nothing was written.' % (
            folder, shown(os.readlink(folder)))
    if state not in (ABSENT, PRESENT):
        return FAILED, '%s is in the way: it is not a folder. Nothing was written.' % folder

    def read_into(*how):
        reader = (store.dump(snapshot, archive_name(domain)), process_options(account, store.environment))
        writer = ([sys.executable, PROGRAM, 'unpack', '--folder', folder] + list(how),
                  process_options(mail_account))
        return judge_restore(folder, snapshot, *run_joined(reader, writer))

    outcome, plan = read_into('--check')
    if outcome != RESTORED:
        return FAILED, '%s Nothing was written.' % plan.rstrip()
    if not _PLAN.match(plan):
        return FAILED, 'The check of the mail archive gave no result: %s. Nothing was written.' % last_part(plan)

    outcome, counts = read_into('--expect', plan)
    if outcome != RESTORED:
        return FAILED, 'The restore into %s stopped before it was done: %s' % (folder, counts)
    try:
        written, kept, unlinked = (int(count) for count in counts.split())
    except ValueError:
        return FAILED, 'The restore into %s gave no result: %s' % (folder, last_part(counts))
    return RESTORED, restored_words(written, kept, unlinked)


# ----------------------------------------------------- unpacking an archive

def member_parts(name):
    """The parts of a name inside the archive; it may not leave the folder it is unpacked into."""
    parts = [part for part in name.split('/') if part not in ('', '.')]
    if name.startswith('/') or '..' in parts:
        raise Refused('The archive holds %r, a name that leaves the mail folder.' % (name,))
    return parts


def is_bookkeeping(name):
    """Whether a file is one Dovecot keeps about a mailbox: its indexes, UID list, keywords and quota count."""
    return name == 'maildirsize' or name.startswith('dovecot.') or name.startswith('dovecot-')


def allowance(folder):
    """(bytes, entries) a restore may add to the file system that holds folder."""
    path = folder
    while not os.path.isdir(path):
        path = os.path.dirname(path)
    space = os.statvfs(path)
    size = space.f_blocks * space.f_frsize
    reserve = min(max(LEAST_RESERVE, int(size * RESERVE_SHARE)), MOST_RESERVE)
    entries = MOST_ENTRIES
    if space.f_files:
        entries = min(entries, space.f_favail - int(space.f_files * RESERVE_SHARE))
    return max(0, space.f_bavail * space.f_frsize - reserve), max(0, entries)


class Unpacker(object):
    """Checks a tar archive of mail, and writes it below a folder.

    The archive comes out of a repository that the website's account can
    write, and it is unpacked as the mail account, which owns the mail of
    every domain on the server. So nothing in it is trusted. Every entry
    must land inside the folder; a link may only point further down from
    where it is; only files, folders and links are created; folders are made
    for the mail account alone and files likewise, whatever the archive says;
    and the whole of it has to fit in the free space, less a reserve.
    """

    FOLDER, FILE, LINK, SECOND = 'folder', 'file', 'link', 'second name'

    def __init__(self, folder, limits=None):
        self.folder = folder
        self.top = os.path.realpath(folder)
        self.most_bytes, self.most_entries = limits if limits is not None else allowance(folder)
        self.inside = set()
        self.keeps = {}
        self.entries = 0
        self.size = 0
        self.digest = hashlib.sha256()
        self.serial = 0

    # -- what both passes do

    def place(self, parts, name):
        """Where an entry goes, after making sure the folder it goes into really is inside."""
        target = os.path.join(self.top, *parts)
        parent = os.path.dirname(target)
        if parent not in self.inside:
            real = os.path.realpath(parent)
            if real != self.top and not real.startswith(self.top + os.sep):
                raise Refused('The archive holds %r, which would be written outside the mail folder.' % (name,))
            self.inside.add(parent)
        return target

    def examine(self, member):
        """(kind, where it goes, the file a second name stands for). Refuses what may not be restored."""
        parts = member_parts(member.name)
        source = None
        if member.isdir():
            kind = self.FOLDER
        elif member.issym():
            kind = self.LINK
            if leaves(member.linkname):
                raise Refused('The archive holds the link %r to %r, which is not below it.' % (
                    member.name, member.linkname))
        elif member.islnk():
            kind = self.SECOND
            source_parts = member_parts(member.linkname)
            if not source_parts or is_bookkeeping(source_parts[-1]):
                raise Refused('The archive holds %r, a second name for %r, which is not a mail file.' % (
                    member.name, member.linkname))
            source = self.place(source_parts, member.linkname)
        elif member.isreg():
            kind = self.FILE
            if member.issparse() or member.size < 0:
                raise Refused('The archive holds %r as a file with holes; mail files have none.' % (member.name,))
            self.size += member.size
        else:
            raise Refused('The archive holds %r, which is not a file, a folder or a link.' % (member.name,))

        self.entries += 1
        self.size += ENTRY_COST
        if self.size > self.most_bytes or self.entries > self.most_entries:
            raise Refused('The archive does not fit: it needs more than %s bytes or %s entries, which is what the '
                          'disk has free less a reserve.' % (self.most_bytes, self.most_entries))
        self.digest.update(repr((member.name, member.type, member.size, member.linkname,
                                 int(member.mtime))).encode('utf-8', 'backslashreplace'))

        if not parts:
            if kind != self.FOLDER:
                raise Refused('The archive holds %r, which is not a name.' % (member.name,))
            return kind, None, None

        target = self.place(parts, member.name)
        if kind != self.FOLDER and is_bookkeeping(parts[-1]):
            # Whatever is in the place of one of Dovecot's own files stays there.
            return kind, target, source
        try:
            there = os.lstat(target).st_mode
        except OSError:
            there = None
        if there is not None and (kind == self.FOLDER) != stat.S_ISDIR(there):
            raise Refused('The archive holds %r as a %s, and the mail folder has %s there.' % (
                member.name, kind, 'a folder' if stat.S_ISDIR(there) else 'something that is not a folder'))
        return kind, target, source

    def plan(self):
        return '%d:%d:%s' % (self.entries, self.size, self.digest.hexdigest())

    # -- the first pass

    def check(self, stream):
        """Read the whole archive and write nothing. Returns what the archive is, for the second pass."""
        for member in tarfile.open(fileobj=stream, mode='r|'):
            self.examine(member)
        return self.plan()

    # -- the second pass

    def make_folder(self, path):
        """Make a folder and those above it, each for the mail account alone."""
        missing = []
        while not os.path.isdir(path):
            missing.append(path)
            path = os.path.dirname(path)
        for folder in reversed(missing):
            try:
                os.mkdir(folder, 0o700)
            except FileExistsError:
                pass

    def keeps_its_own(self, folder):
        """Whether a folder already has Dovecot's files; decided once, before any is written into it."""
        if folder not in self.keeps:
            try:
                self.keeps[folder] = any(is_bookkeeping(name) for name in os.listdir(folder))
            except OSError:
                self.keeps[folder] = False
        return self.keeps[folder]

    def put(self, target, make):
        """Create an entry beside its place and move it there, so that it is whole when it appears.

        Dovecot does not take a name that starts with a dot for a message.
        """
        self.serial += 1
        beside = os.path.join(os.path.dirname(target), '.mail-restore.%d.%d' % (os.getpid(), self.serial))
        try:
            make(beside)
            os.rename(beside, target)
        finally:
            if os.path.lexists(beside):
                os.remove(beside)

    def write(self, stream, plan):
        """Write the archive that was checked. Returns (files written, index files kept, second names left out)."""
        expected = _PLAN.match(plan or '')
        if not expected:
            raise Refused('The archive was not checked before it is written.')
        changed = Refused('The archive changed between its check and the restore.')
        written = kept = unlinked = 0
        self.make_folder(self.top)

        archive = tarfile.open(fileobj=stream, mode='r|')
        for member in archive:
            kind, target, source = self.examine(member)
            if self.entries > int(expected.group(1)) or self.size > int(expected.group(2)):
                raise changed
            if target is None:
                continue
            if kind == self.FOLDER:
                self.make_folder(target)
                continue

            self.make_folder(os.path.dirname(target))
            bookkeeping = is_bookkeeping(os.path.basename(target))
            if bookkeeping and (kind != self.FILE or self.keeps_its_own(os.path.dirname(target))):
                # Old indexes over newer mail would hand out message numbers a
                # mail client has already seen for other messages.
                kept += 1
                continue

            if kind == self.FILE:
                def make(path, member=member):
                    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
                    with os.fdopen(descriptor, 'wb') as output:
                        shutil.copyfileobj(archive.extractfile(member), output)
                    os.utime(path, (member.mtime, member.mtime))
            elif kind == self.LINK:
                def make(path, member=member):
                    os.symlink(member.linkname, path)
            else:
                if not os.path.isfile(source) or os.path.islink(source):
                    unlinked += 1
                    continue

                def make(path, source=source):
                    os.link(source, path)

            try:
                self.put(target, make)
            except OSError:
                if not bookkeeping:
                    raise
                # A restore never fails over an index file: Dovecot makes its own.
                kept += 1
                continue
            if kind != self.LINK:
                written += 1

        if self.plan() != plan:
            raise changed
        return written, kept, unlinked


# ------------------------------------------------------------ the program

def aws_environment(key):
    """The credentials restic needs for a bucket, from the panel's own store of them."""
    if not key or os.path.basename(key) != key or key in ('.', '..'):
        raise Refused('%r is not the name of a stored AWS key.' % (key,))
    with open(os.path.join(IncBackupPath.AWS.value, key)) as stored:
        return {'AWS_ACCESS_KEY_ID': key, 'AWS_SECRET_ACCESS_KEY': stored.read().strip()}


def repository_account(account):
    """The account the backup program runs as. It is never root: the repository is the website's."""
    if not account:
        raise Refused('No website account was named.')
    if pwd.getpwnam(account).pw_uid == 0:
        raise Refused('The repository is opened as the website account, not as root.')
    return account


def store_of(args):
    """The backup program and repository a request names."""
    if not args.repository or args.repository.startswith('-'):
        raise Refused('No repository was named.')
    if args.program == 'rustic':
        return Rustic(args.repository)
    environment = aws_environment(args.aws_key) if args.aws_key else {}
    if args.password_from:
        # Given to restic alone, in its environment.
        environment['RESTIC_PASSWORD'] = read_secret(args.password_from)
    return Restic(args.repository, args.password_file, environment)


def main(arguments=None):
    parser = argparse.ArgumentParser(description='Mail in website backups', allow_abbrev=False)
    parser.add_argument('action', choices=('backup', 'restore', 'unpack'))
    parser.add_argument('--domain')
    parser.add_argument('--account')
    parser.add_argument('--repository')
    parser.add_argument('--program', choices=('restic', 'rustic'), default='restic')
    parser.add_argument('--password-file')
    parser.add_argument('--password-from')
    parser.add_argument('--aws-key')
    parser.add_argument('--snapshot')
    parser.add_argument('--folder')
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--expect')
    args = parser.parse_args(arguments)

    if args.action == 'unpack':
        # The end of a restore that reads the archive; it runs as the mail account.
        try:
            if os.geteuid() == 0:
                raise Refused('Mail is written by the mail account, not by root.')
            os.umask(0o077)
            unpacker = Unpacker(args.folder)
            if args.check:
                print(unpacker.check(sys.stdin.buffer))
            else:
                print('%d %d %d' % unpacker.write(sys.stdin.buffer, args.expect))
            return 0
        except BaseException as error:
            sys.stdout.write('%s\n' % shown(str(error)))
            return 1

    try:
        if os.geteuid() != 0:
            raise Refused('This program needs root privilege to start the mail reader and the backup program '
                          'under their own accounts.')
        store = store_of(args)
        account = repository_account(args.account)
        if args.action == 'backup':
            outcome, detail = back_up(args.domain, account, store)
        else:
            outcome, detail = restore(args.domain, account, store, args.snapshot)
    except BaseException as error:
        outcome, detail = FAILED, str(error) if isinstance(error, Refused) else '%s: %s' % (
            type(error).__name__, error)

    print('%s %s %s' % (OUTCOME_MARK, outcome, last_part(detail)))
    return 0 if outcome != FAILED else 1


if __name__ == '__main__':
    sys.exit(main())
