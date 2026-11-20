"""Reserve, check and read the status files polled by the panel.

A status path arrives from the browser, so it is only ever accepted when it is
exactly one of the files the panel creates, and it is only ever read when it is
a plain file: never a link, a pipe or a directory.
"""
import errno
import os
import re
import secrets
import shlex
import stat
import sys

STATUS_DIRECTORIES = ('/home/cyberpanel', '/tmp', '/usr/local/CyberCP/tmp')
BACKUP_LOG_DIRECTORY = '/home/cyberpanel'
BACKUP_LOG_SUFFIX = '_rustic_backup_log'
MAX_STATUS_BYTES = 1024 * 1024
REFUSED = '[status file refused]'
# -I: the root reader imports the standard library only, never a file that
# happens to sit beside this one or in the caller's environment.
ROOT_READER = '/usr/local/CyberCP/bin/python -I /usr/local/CyberCP/plogical/statusUtilities.py read '

RESTORE_DIRECTORY = '/home/backup'

_STATUS_NAME = re.compile(r'[0-9]{1,64}')
_DOMAIN = re.compile(r'[A-Za-z0-9](?:[A-Za-z0-9._-]{0,251}[A-Za-z0-9])?')
_ARCHIVE_NAME = re.compile(r'[^/\x00-\x1f\x7f]{1,255}')
_TRANSFER_ID = re.compile(r'[0-9]{1,12}')


def create_status_file(directory='/home/cyberpanel'):
    # Four-digit random names can reuse an old root-owned success file, or
    # collide with another active worker. Reserve each path before launch.
    while True:
        path = os.path.join(directory, str(secrets.randbits(128)))
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError:
            continue
        with os.fdopen(fd, 'w') as status:
            status.write('Starting..,0')
        return path


def valid_status_path(path, domain=None):
    """True only for a status file the panel itself creates."""
    if not isinstance(path, str):
        return False
    directory, separator, name = path.rpartition('/')
    if separator and directory in STATUS_DIRECTORIES and _STATUS_NAME.fullmatch(name):
        return True
    if isinstance(domain, str) and _DOMAIN.fullmatch(domain) and '..' not in domain:
        return path == '%s/%s%s' % (BACKUP_LOG_DIRECTORY, domain, BACKUP_LOG_SUFFIX)
    return False


def _archive_name(name):
    return isinstance(name, str) and _ARCHIVE_NAME.fullmatch(name) is not None and '..' not in name \
        and name != '.'


def valid_restore_status_path(path):
    """True only for <backups>/<archive>/status or <backups>/transfer-<id>/<archive>/status."""
    if not isinstance(path, str):
        return False
    directory, separator, name = path.rpartition('/')
    if not separator or name != 'status':
        return False
    parent, separator, archive = directory.rpartition('/')
    if not separator or not _archive_name(archive):
        return False
    if parent == RESTORE_DIRECTORY:
        return True
    backups, separator, transfer = parent.rpartition('/')
    return backups == RESTORE_DIRECTORY and transfer.startswith('transfer-') \
        and _TRANSFER_ID.fullmatch(transfer[len('transfer-'):]) is not None


def restore_work_directory(backup_file, transfer_id=None):
    """The directory a restore of this archive works in, or '' for any other value.

    The archive name comes from the browser, so it may only be a file name.
    """
    if not _archive_name(backup_file):
        return ''
    archive = backup_file[:-len('.tar.gz')] if backup_file.endswith('.tar.gz') else backup_file
    if not _archive_name(archive):
        return ''
    if os.path.lexists(os.path.join(RESTORE_DIRECTORY, backup_file)):
        return os.path.join(RESTORE_DIRECTORY, archive)
    if isinstance(transfer_id, bool) or not isinstance(transfer_id, (str, int)):
        return ''
    if not _TRANSFER_ID.fullmatch(str(transfer_id)):
        return ''
    return '%s/transfer-%s/%s' % (RESTORE_DIRECTORY, transfer_id, archive)


def _read_plain_file(path):
    flags = os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | getattr(os, 'O_CLOEXEC', 0)
    descriptor = os.open(path, flags)
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            raise OSError(errno.EINVAL, 'Not a plain status file.')
        if details.st_size > MAX_STATUS_BYTES:
            os.lseek(descriptor, details.st_size - MAX_STATUS_BYTES, os.SEEK_SET)
        parts = []
        remaining = MAX_STATUS_BYTES
        while remaining > 0:
            part = os.read(descriptor, min(65536, remaining))
            if not part:
                break
            parts.append(part)
            remaining -= len(part)
        return b''.join(parts).decode('utf-8', 'replace')
    finally:
        os.close(descriptor)


def read_status_file(path, domain=None):
    """Return a status file's text, or '' while it has not been written.

    Raises ValueError for anything that is not a plain status file.
    """
    if not valid_status_path(path, domain):
        raise ValueError('Invalid status file.')
    return _read_checked(path)


def read_restore_status(directory):
    """Return the progress text of the restore working in this directory.

    Raises ValueError unless it is a restore working directory holding a plain
    status file; '' while the status has not been written.
    """
    path = '%s/status' % (directory,)
    if not valid_restore_status_path(path):
        raise ValueError('Invalid status file.')
    return _read_checked(path)


def _read_checked(path):
    try:
        return _read_plain_file(path)
    except FileNotFoundError:
        return ''
    except PermissionError:
        # Written by a root worker with a private mode: ask the root reader,
        # which applies the same checks before it opens anything.
        return _read_as_root(path)
    except OSError:
        raise ValueError('Invalid status file.')


def _read_as_root(path):
    from plogical.processUtilities import ProcessUtilities
    result = ProcessUtilities.outputExecutioner(ROOT_READER + shlex.quote(path), retRequired=True)
    if not (isinstance(result, tuple) and len(result) == 2 and isinstance(result[1], str)):
        return ''
    succeeded, output = result
    if output.startswith(REFUSED):
        raise ValueError('Invalid status file.')
    return output if succeeded else ''


def main(arguments):
    """Root reader: `statusUtilities.py read PATH` prints one status file."""
    try:
        if len(arguments) != 2 or arguments[0] != 'read':
            raise ValueError('Invalid status file.')
        path = arguments[1]
        domain = None
        if isinstance(path, str) and path.endswith(BACKUP_LOG_SUFFIX):
            domain = path.rpartition('/')[2][:-len(BACKUP_LOG_SUFFIX)]
        if not (valid_status_path(path, domain) or valid_restore_status_path(path)):
            raise ValueError('Invalid status file.')
        try:
            text = _read_plain_file(path)
        except FileNotFoundError:
            text = ''
        sys.stdout.write(text)
        return 0
    except BaseException:
        sys.stdout.write(REFUSED + '\n')
        return 3


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
