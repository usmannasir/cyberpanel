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


def _read(name, limit=128):
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
        return data.decode('ascii') if len(data) <= limit else None
    except Exception:
        return None


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


def generation():
    """Counter raised on every revocation; 0 when it cannot be read."""
    text = _read('generation', 18)
    return int(text) if text is not None and _NUMBER.fullmatch(text) else 0
