"""Provision the Multi-Server Manager key directory, role and keys (run as root).

    /etc/cyberpanel/multiserver/        root:cyberpanel 0750
        role          off | controller | node     (off after install and upgrade)
        identity.key  a node's Ed25519 identity key
        generation    raised on every revocation
        master.key    a controller's key for sealing its link records

Files are root-owned and group-readable by the panel only. Nothing here is ever
replaced once it exists, so repeated installs, upgrades and rollbacks keep it.
"""
import base64
import grp
import os
import re
import secrets
import stat
import sys
import tempfile

KEY_DIRECTORY = '/etc/cyberpanel/multiserver'
OWNER = 0
ROLES = ('off', 'controller', 'node')


def _gid(group):
    return group if isinstance(group, int) else grp.getgrnam(group).gr_gid


def _ensure_file(name, content, gid):
    """Create a private file with this content, or keep and re-protect the existing one."""
    path = os.path.join(KEY_DIRECTORY, name)
    try:
        try:
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
            created = True
        except FileExistsError:
            descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            created = False
    except OSError as error:
        raise RuntimeError('Unsafe Multi-Server Manager file %s: %s' % (path, error))
    try:
        details = os.fstat(descriptor)
        if not stat.S_ISREG(details.st_mode) or details.st_uid != OWNER or details.st_nlink != 1:
            raise RuntimeError('Unsafe Multi-Server Manager file %s; refusing to use it' % path)
        if created:
            data = content.encode('ascii')
            if os.write(descriptor, data) != len(data):
                raise RuntimeError('Incomplete write of %s' % path)
            os.fsync(descriptor)
        os.fchown(descriptor, OWNER, gid)
        os.fchmod(descriptor, 0o640)
    finally:
        os.close(descriptor)


def _replace_file(name, content, gid):
    descriptor, temporary = tempfile.mkstemp(dir=KEY_DIRECTORY, prefix='.' + name + '.')
    try:
        os.write(descriptor, content.encode('ascii'))
        os.fsync(descriptor)
        os.fchown(descriptor, OWNER, gid)
        os.fchmod(descriptor, 0o640)
    except BaseException:
        os.close(descriptor)
        os.unlink(temporary)
        raise
    os.close(descriptor)
    os.rename(temporary, os.path.join(KEY_DIRECTORY, name))


def ensure_key_directory(group='cyberpanel'):
    """Create the directory and the role file ('off'); keep whatever already exists."""
    gid = _gid(group)
    try:
        os.mkdir(KEY_DIRECTORY, 0o750)
    except FileExistsError:
        pass
    try:
        descriptor = os.open(KEY_DIRECTORY, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    except OSError as error:
        raise RuntimeError('Unsafe Multi-Server Manager directory %s: %s' % (KEY_DIRECTORY, error))
    try:
        if os.fstat(descriptor).st_uid != OWNER:
            raise RuntimeError('Multi-Server Manager directory %s has the wrong owner' % KEY_DIRECTORY)
        os.fchown(descriptor, OWNER, gid)
        os.fchmod(descriptor, 0o750)
    finally:
        os.close(descriptor)
    # Only this child directory is writable by the panel. A per-link marker
    # survives database rollback without invalidating other controllers.
    revoked = os.path.join(KEY_DIRECTORY, 'revoked')
    try:
        os.mkdir(revoked, 0o700)
    except FileExistsError:
        pass
    descriptor = os.open(revoked, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if os.fstat(descriptor).st_uid != OWNER:
            raise RuntimeError('Unsafe Multi-Server revocation directory')
        os.fchown(descriptor, OWNER, gid)
        os.fchmod(descriptor, 0o770)
    finally:
        os.close(descriptor)
    _ensure_file('role', 'off\n', gid)


def set_role(role, group='cyberpanel'):
    """Switch this server to one role and make sure that role's key exists."""
    if not isinstance(role, str) or role not in ROLES:
        raise ValueError('The role is one of: %s' % ', '.join(ROLES))
    gid = _gid(group)
    ensure_key_directory(gid)
    if role == 'node':
        _ensure_file('identity.key', secrets.token_hex(32), gid)
        _ensure_file('generation', '1', gid)
    elif role == 'controller':
        _ensure_file('master.key', base64.urlsafe_b64encode(os.urandom(32)).decode('ascii'), gid)
    _replace_file('role', role + '\n', gid)


def bump_generation(group='cyberpanel'):
    """Raise the revocation counter; links recorded under an older value stop working."""
    gid = _gid(group)
    _ensure_file('generation', '1', gid)
    with open(os.path.join(KEY_DIRECTORY, 'generation')) as source:
        text = source.read(32)
    current = int(text) if re.fullmatch(r'[0-9]{1,18}', text) else 0
    _replace_file('generation', str(current + 1), gid)
    return current + 1


if __name__ == '__main__':
    # install/multiserver_identity.py            provision (installer and upgrader)
    # install/multiserver_identity.py ROLE       switch role
    if len(sys.argv) == 1:
        ensure_key_directory()
    elif len(sys.argv) == 2:
        set_role(sys.argv[1])
    else:
        sys.exit('usage: multiserver_identity.py [off|controller|node]')
