"""Repair only the standard root-owned database credential used by the panel.

No credential is read or replaced. Custom ownership/modes and unsafe paths fail
closed so an upgrade cannot silently grant access to an unrelated secret.
"""
import errno
import grp
import os
import stat

PASSWORD_FILE = '/etc/cyberpanel/mysqlPassword'


def _reject_acl(fd):
    # chmod changes the POSIX ACL mask too, potentially enabling named readers.
    # Query the verified descriptor; never inspect a pathname then reopen it.
    try:
        os.getxattr(fd, 'system.posix_acl_access')
    except OSError as error:
        if error.errno in (errno.ENODATA, errno.ENOTSUP):
            return
        raise
    raise PermissionError('Custom MySQL credential access ACL; review manually')


def _check_parent(fd, gid):
    _reject_acl(fd)
    current = os.fstat(fd)
    mode = stat.S_IMODE(current.st_mode)
    if current.st_uid != 0 or mode & 0o022:
        raise PermissionError('Unsafe MySQL credential parent directory')
    if not (mode & 0o001 or (current.st_gid == gid and mode & 0o010)):
        raise PermissionError('Panel cannot traverse MySQL credential parent directory; review manually')


def repair(path=None):
    """Return whether a standard 0600/0640 file needed root:cyberpanel 0640.

    Walk trusted directories by descriptor, refusing symlinks and writable or
    non-root parents. Operate on the verified file descriptor, never a re-opened
    path. Only the panel's existing group receives read access.
    """
    if os.geteuid() != 0:
        raise PermissionError('MySQL credential permission repair requires root')
    if path is None:
        path = PASSWORD_FILE
    if not os.path.isabs(path) or os.path.normpath(path) != path:
        raise ValueError('Unsafe MySQL credential path')
    gid = grp.getgrnam('cyberpanel').gr_gid
    if gid == 0:
        raise ValueError('Unsafe panel service group')
    directory_flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | os.O_CLOEXEC
    parent_fd = os.open('/', directory_flags)
    file_fd = None
    try:
        components = path.split('/')[1:]
        for component in components[:-1]:
            _check_parent(parent_fd, gid)
            next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = next_fd
        _check_parent(parent_fd, gid)
        file_fd = os.open(components[-1], os.O_RDONLY | os.O_NOFOLLOW |
                          os.O_NONBLOCK | os.O_CLOEXEC, dir_fd=parent_fd)
        _reject_acl(file_fd)
        current = os.fstat(file_fd)
        if (not stat.S_ISREG(current.st_mode) or current.st_nlink != 1 or
                current.st_uid != 0 or current.st_gid not in (0, gid) or
                stat.S_IMODE(current.st_mode) not in (0o600, 0o640)):
            raise PermissionError('Nonstandard MySQL credential ownership, type or mode; review manually')
        changed = current.st_gid != gid or stat.S_IMODE(current.st_mode) != 0o640
        if changed:
            if current.st_gid != gid:
                os.fchown(file_fd, -1, gid)
            os.fchmod(file_fd, 0o640)
            verified = os.fstat(file_fd)
            if (verified.st_uid, verified.st_gid, stat.S_IMODE(verified.st_mode)) != (0, gid, 0o640):
                raise PermissionError('MySQL credential permission repair did not take effect')
        return changed
    finally:
        if file_fd is not None:
            os.close(file_fd)
        os.close(parent_fd)
