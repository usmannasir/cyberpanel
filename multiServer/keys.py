"""Read the Multi-Server Manager role and keys.

The files are written by root (install/multiserver_identity.py) and read here by
the panel. Anything unexpected about them — missing, a link, wrong owner, readable
by others, wrong content — means the feature is off or the key is absent.
"""
import os
import re
import stat

KEY_DIRECTORY = '/etc/cyberpanel/multiserver'
OWNER = 0
OFF, CONTROLLER, NODE = 'off', 'controller', 'node'

_ROLE = re.compile(r'(off|controller|node)\n?')
_HEX_KEY = re.compile(r'[0-9a-f]{64}')
_FERNET_KEY = re.compile(r'[A-Za-z0-9_-]{43}=')
_NUMBER = re.compile(r'[0-9]{1,18}')


def _read(name, limit=128, versioned=False):
    """The text of one private file in the key directory, or None."""
    try:
        directory = os.lstat(KEY_DIRECTORY)
        if not stat.S_ISDIR(directory.st_mode) or directory.st_uid != OWNER or directory.st_mode & 0o022:
            return None
        descriptor = os.open(os.path.join(KEY_DIRECTORY, name),
                             os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
        try:
            details = os.fstat(descriptor)
            if (not stat.S_ISREG(details.st_mode) or details.st_uid != OWNER
                    or details.st_nlink != 1 or details.st_mode & 0o027):
                return None
            data = os.read(descriptor, limit + 1)
        finally:
            os.close(descriptor)
        if len(data) > limit:
            return None
        text = data.decode('ascii')
        if versioned:
            return text, (details.st_dev, details.st_ino, details.st_ctime_ns)
        return text
    except Exception:
        return None


def role_revision(expected):
    """Bind short-lived logins to this installation of the root-owned role file.

    set_role replaces the file. A switch away and back also invalidates a browser
    that did not make any request during the interval. The text and revision come
    from the same checked descriptor.
    """
    value = _read('role', 16, versioned=True)
    if not value or value[0].rstrip('\n') != expected or not _ROLE.fullmatch(value[0]):
        raise ValueError('Multi-Server role changed.')
    return value[1]


def role():
    """'controller', 'node' or 'off'; never raises."""
    text = _read('role', 16)
    matched = _ROLE.fullmatch(text) if text is not None else None
    return matched.group(1) if matched else OFF


def identity_key():
    """This node's Ed25519 identity key (32 bytes), or None."""
    text = _read('identity.key')
    return bytes.fromhex(text) if text is not None and _HEX_KEY.fullmatch(text) else None


def master_key():
    """The controller's key for sealing its link records, or None."""
    text = _read('master.key')
    return text.encode('ascii') if text is not None and _FERNET_KEY.fullmatch(text) else None


def revoked(link_id):
    """A marker survives restoring an older database. Errors other than absence stop the gateway."""
    if not re.fullmatch(r'[0-9a-f]{32}', link_id):
        raise ValueError('Invalid link id')
    try:
        os.lstat(os.path.join(KEY_DIRECTORY, 'revoked', link_id))
    except FileNotFoundError:
        return False
    return True


def mark_revoked(link_id):
    """Persist before acknowledging, including a retry after the first reply was lost."""
    if not re.fullmatch(r'[0-9a-f]{32}', link_id):
        raise ValueError('Invalid link id')
    directory = os.open(os.path.join(KEY_DIRECTORY, 'revoked'), os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        try:
            fd = os.open(link_id, os.O_WRONLY | os.O_NOFOLLOW | os.O_CREAT | os.O_EXCL, 0o600,
                         dir_fd=directory)
        except FileExistsError:
            pass
        else:
            os.close(fd)
        os.fsync(directory)
    finally:
        os.close(directory)


def generation():
    """Counter raised on every revocation; 0 when it cannot be read."""
    text = _read('generation', 18)
    return int(text) if text is not None and _NUMBER.fullmatch(text) else 0
