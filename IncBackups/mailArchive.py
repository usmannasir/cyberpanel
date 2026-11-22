#!/usr/local/CyberCP/bin/python
"""Save a website's mail in its incremental backup repository, and bring it back.

The mail store belongs to the mail account and the repository to the
website's account, and neither account can read the other's files. So no
single program handles both. The mail is read, or written, by a process that
runs as the mail account; the repository is opened by restic running as the
website's account; the two are joined by a pipe that carries one tar archive.

This program is started with root privilege for one purpose: to start those
two processes under their accounts. It reads no mail and opens no repository
itself, and nothing it is given is used with root privilege except the name
of the mail folder it looks for.

The last line it prints is the outcome, for the backup job to read:

    [mail-archive] saved <snapshot id>
    [mail-archive] no-mail-folder <folder>
    [mail-archive] restored <number of files>
    [mail-archive] present <folder>
    [mail-archive] failed <reason>

`present` answers the one question a job may ask without saving anything:
whether a domain has a mail folder. The panel's own process cannot enter the
mail store to find that out.
"""
import argparse
import errno
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

OUTCOME_MARK = '[mail-archive]'
SAVED = 'saved'
NO_FOLDER = 'no-mail-folder'
RESTORED = 'restored'
FAILED = 'failed'

PRESENT = 'present'
ABSENT = 'absent'
NOT_A_FOLDER = 'not-a-folder'
UNKNOWN = 'unknown'

_DOMAIN = re.compile(r'^[A-Za-z0-9_][A-Za-z0-9_.-]*$')
_SNAPSHOT = re.compile(r'^[0-9a-f]{8,64}$')


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
    return PRESENT if stat.S_ISDIR(mode) else NOT_A_FOLDER


# ------------------------------------------------- the backup job's side

def helper_command(action, domain, account=None, repository=None, password_file=None, password=None,
                   aws_key=None, snapshot=None):
    """The command line that runs this program for the backup job."""
    words = [PYTHON, PROGRAM, action, '--domain', domain]
    for option, value in (('--account', account), ('--repository', repository),
                          ('--password-file', password_file), ('--password', password),
                          ('--aws-key', aws_key), ('--snapshot', snapshot)):
        if value is not None:
            words += [option, str(value)]
    return ' '.join(shlex.quote(word) for word in words)


def read_outcome(output):
    """(outcome, detail) from what this program printed.

    Output without an outcome line is a failure: the program did not finish.
    """
    lines = [line.strip() for line in (output or '').splitlines()]
    for line in reversed(lines):
        if line.startswith(OUTCOME_MARK):
            words = line[len(OUTCOME_MARK):].strip().split(' ', 1)
            if words[0] in (SAVED, NO_FOLDER, RESTORED, PRESENT, FAILED):
                return words[0], words[1].strip() if len(words) > 1 else ''
    said = ' | '.join(line for line in lines if line)
    return FAILED, 'The mail helper did not report a result%s' % (': ' + last_part(said) if said else '.')


def last_part(text, limit=1500):
    """The end of a program's messages, on one line."""
    line = ' | '.join(part.strip() for part in (text or '').splitlines() if part.strip())
    return line if len(line) <= limit else '... ' + line[-limit:]


# ------------------------------------------------------------- judging

def judge_backup(folder, reader_status, reader_errors, restic_status, restic_output):
    """(outcome, detail, snapshot to discard) for a finished backup.

    tar ends with status 1 when files changed or went away while it read
    them, which a mail store in use does all the time: that archive is good.
    Any other failure of the reader means mail is missing from the archive,
    and the snapshot restic made of it must not be kept.
    """
    try:
        snapshot = extract_snapshot_id(restic_output)
    except ValueError:
        snapshot = None

    if restic_status != 0 or snapshot is None:
        said = last_part(restic_output) or last_part(reader_errors) or 'restic gave no message'
        return FAILED, 'The mail in %s was not saved: %s' % (folder, said), snapshot
    if reader_status not in (0, 1):
        said = last_part(reader_errors) or 'the reader ended with status %s' % reader_status
        return FAILED, ('%s exists but could not be read in full, so its mail was not backed up: %s'
                        % (folder, said)), snapshot
    return SAVED, snapshot, None


def judge_restore(folder, snapshot, restic_status, restic_errors, writer_status, writer_output):
    """(outcome, detail) for a finished restore."""
    if restic_status != 0:
        said = last_part(restic_errors) or 'restic ended with status %s' % restic_status
        hint = ''
        if 'not found' in said.lower() or 'not exist' in said.lower():
            hint = ' Snapshots of mail made before CyberPanel 3.0.13 hold no mail archive.'
        return FAILED, 'No mail archive could be read from snapshot %s: %s.%s' % (snapshot, said, hint)
    if writer_status != 0:
        said = last_part(writer_output) or 'the writer ended with status %s' % writer_status
        return FAILED, 'The restore into %s stopped before it was done: %s' % (folder, said)
    return RESTORED, last_part(writer_output).split(' ')[-1]


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


def restic_words(repository, password_file):
    words = ['restic', '-r', repository]
    if password_file:
        words += ['--password-file', password_file]
    return words


def look(domain, mail_root=MAIL_ROOT):
    """Whether a domain has a mail folder. Returns (outcome, detail)."""
    folder = mail_folder(domain, mail_root)
    state = folder_state(folder)
    if state == ABSENT:
        return NO_FOLDER, folder
    if state != PRESENT:
        return FAILED, '%s is there but is not a folder that can be read, so its mail was not backed up.' % folder
    return PRESENT, folder


def back_up(domain, account, repository, password_file, environment=None,
            mail_root=MAIL_ROOT, mail_account=MAIL_ACCOUNT):
    """Save the mail of a domain as one snapshot. Returns (outcome, detail)."""
    outcome, folder = look(domain, mail_root)
    if outcome != PRESENT:
        return outcome, folder

    reader = (['tar', '--create', '--file=-', '--directory=' + folder, '.'], process_options(mail_account))
    restic = (restic_words(repository, password_file) + ['backup', '--stdin', '--stdin-filename',
                                                         archive_name(domain)],
              process_options(account, environment))
    outcome, detail, discard = judge_backup(folder, *run_joined(reader, restic))

    if discard:
        # An archive that lacks mail is not left where a restore could pick it.
        options = process_options(account, environment)
        subprocess.call(restic_words(repository, password_file) + ['forget', discard],
                        stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
    return outcome, detail


def restore(domain, account, repository, snapshot, password_file=None, environment=None,
            mail_root=MAIL_ROOT, mail_account=MAIL_ACCOUNT):
    """Unpack the mail archive of a snapshot over the domain's mail folder. Returns (outcome, detail)."""
    folder = mail_folder(domain, mail_root)
    if not _SNAPSHOT.match(snapshot or ''):
        raise Refused('%r is not a snapshot id.' % (snapshot,))
    if folder_state(folder) not in (ABSENT, PRESENT):
        return FAILED, '%s is in the way: it is not a folder.' % folder

    restic = (restic_words(repository, password_file) + ['dump', snapshot, archive_path(domain)],
              process_options(account, environment))
    writer = ([sys.executable, PROGRAM, 'unpack', '--folder', folder], process_options(mail_account))
    return judge_restore(folder, snapshot, *run_joined(restic, writer))


# ----------------------------------------------------- unpacking an archive

def member_parts(name):
    """The parts of a name inside the archive; it may not leave the folder it is unpacked into."""
    parts = [part for part in name.split('/') if part not in ('', '.')]
    if name.startswith('/') or '..' in parts:
        raise Refused('The archive holds %r, a name that leaves the mail folder.' % (name,))
    return parts


def unpack(stream, folder):
    """Write the files of a tar archive below folder. Returns the number of files written.

    The archive comes out of a repository that the website's account can
    write, and it is unpacked as the mail account, which owns the mail of
    every domain on the server. So nothing in it is trusted: every entry
    must land inside the folder, a link may only point further down from
    where it is, and only files, folders and links are created.
    """
    os.makedirs(folder, 0o700, exist_ok=True)
    top = os.path.realpath(folder)
    checked = set()

    def below(path):
        return path == top or path.startswith(top + os.sep)

    def place(parts, name):
        """Where an entry goes, after making sure its folder really is inside."""
        target = os.path.join(top, *parts)
        parent = os.path.dirname(target)
        if parent not in checked:
            if not below(os.path.realpath(parent)):
                raise Refused('The archive holds %r, which would be written outside the mail folder.' % (name,))
            os.makedirs(parent, 0o700, exist_ok=True)
            checked.add(parent)
        return target

    def clear(target):
        if os.path.lexists(target):
            os.remove(target)

    written = 0
    archive = tarfile.open(fileobj=stream, mode='r|')
    for member in archive:
        parts = member_parts(member.name)
        mode = member.mode & 0o777
        if not parts:
            if member.isdir():
                os.chmod(top, mode | 0o700)
            continue
        target = place(parts, member.name)

        if member.isdir():
            if os.path.islink(target):
                raise Refused('The archive holds the folder %r where a link is.' % (member.name,))
            os.makedirs(target, 0o700, exist_ok=True)
            os.chmod(target, mode | 0o700)
        elif member.isreg():
            clear(target)
            descriptor = os.open(target, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            with os.fdopen(descriptor, 'wb') as output:
                shutil.copyfileobj(archive.extractfile(member), output)
                os.fchmod(output.fileno(), mode)
            os.utime(target, (member.mtime, member.mtime))
            written += 1
        elif member.issym():
            link = member.linkname
            if not link or link.startswith('/') or '..' in link.split('/'):
                raise Refused('The archive holds the link %r to %r, which is not below it.' % (member.name, link))
            clear(target)
            os.symlink(link, target)
        elif member.islnk():
            source = place(member_parts(member.linkname), member.linkname)
            if not os.path.isfile(source) or os.path.islink(source):
                raise Refused('The archive holds %r, a second name for a file it does not hold.' % (member.name,))
            clear(target)
            os.link(source, target)
            written += 1
        else:
            raise Refused('The archive holds %r, which is not a file, a folder or a link.' % (member.name,))
    return written


# ------------------------------------------------------------ the program

def aws_environment(key):
    """The credentials restic needs for a bucket, from the panel's own store of them."""
    if not key or os.path.basename(key) != key or key in ('.', '..'):
        raise Refused('%r is not the name of a stored AWS key.' % (key,))
    with open(os.path.join(IncBackupPath.AWS.value, key)) as stored:
        return {'AWS_ACCESS_KEY_ID': key, 'AWS_SECRET_ACCESS_KEY': stored.read().strip()}


def repository_account(account):
    """The account restic runs as. It is never root: the repository is the website's."""
    if not account:
        raise Refused('No website account was named.')
    if pwd.getpwnam(account).pw_uid == 0:
        raise Refused('The repository is opened as the website account, not as root.')
    return account


def main(arguments=None):
    parser = argparse.ArgumentParser(description='Mail in incremental backups')
    parser.add_argument('action', choices=('backup', 'restore', 'look', 'unpack'))
    parser.add_argument('--domain')
    parser.add_argument('--account')
    parser.add_argument('--repository')
    parser.add_argument('--password-file')
    parser.add_argument('--password')
    parser.add_argument('--aws-key')
    parser.add_argument('--snapshot')
    parser.add_argument('--folder')
    args = parser.parse_args(arguments)

    try:
        if args.action == 'unpack':
            # The end of a restore that writes the mail; it runs as the mail account.
            if os.geteuid() == 0:
                raise Refused('Mail is written by the mail account, not by root.')
            print(unpack(sys.stdin.buffer, args.folder))
            return 0

        if args.action == 'look':
            outcome, detail = look(args.domain)
        else:
            if os.geteuid() != 0:
                raise Refused('This program needs root privilege to start the mail reader and restic '
                              'under their own accounts.')
            if not args.repository or args.repository.startswith('-'):
                raise Refused('No repository was named.')
            environment = aws_environment(args.aws_key) if args.aws_key else {}
            if args.password is not None:
                environment['RESTIC_PASSWORD'] = args.password
            account = repository_account(args.account)

            if args.action == 'backup':
                outcome, detail = back_up(args.domain, account, args.repository, args.password_file, environment)
            else:
                outcome, detail = restore(args.domain, account, args.repository, args.snapshot,
                                          args.password_file, environment)
    except BaseException as error:
        if args.action == 'unpack':
            sys.stderr.write('%s\n' % (error,))
            return 1
        outcome, detail = FAILED, str(error) if isinstance(error, Refused) else '%s: %s' % (
            type(error).__name__, error)

    print('%s %s %s' % (OUTCOME_MARK, outcome, last_part(detail)))
    return 0 if outcome != FAILED else 1


if __name__ == '__main__':
    sys.exit(main())
