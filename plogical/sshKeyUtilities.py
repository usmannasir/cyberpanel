# -*- coding: utf-8 -*-
"""Helpers for parsing OpenSSH ``authorized_keys`` entries.

CyberPanel historically recognised only ``ssh-rsa`` keys when listing or
deleting authorized keys.  As a result ed25519/ecdsa keys (now the OpenSSH
default) were invisible in the SSH Access UI and could not be removed.  These
helpers recognise every key type OpenSSH emits so the UI stays correct
regardless of the algorithm the user generated their key with.
"""

# Key types that may appear as the key-type token of an authorized_keys entry.
# Covers RSA, DSA, ECDSA, Ed25519 and the FIDO/U2F security-key variants.
SSH_KEY_TYPES = (
    'ssh-rsa',
    'ssh-dss',
    'ssh-ed25519',
    'ecdsa-sha2-nistp256',
    'ecdsa-sha2-nistp384',
    'ecdsa-sha2-nistp521',
    'sk-ssh-ed25519@openssh.com',
    'sk-ecdsa-sha2-nistp256@openssh.com',
)


def parse_authorized_key(line):
    """Parse a single ``authorized_keys`` line.

    Returns a dict ``{'keyType', 'keyData', 'comment'}`` or ``None`` when the
    line is blank, a comment, or contains no recognised key type.

    The key type is located by scanning the whitespace-separated fields rather
    than assuming it is the first one, because an entry may be prefixed with
    options (e.g. ``no-pty,no-X11-forwarding ssh-ed25519 AAAA... user@host``).
    """
    if not line or line.lstrip().startswith('#'):
        return None

    fields = line.split()

    for index, field in enumerate(fields):
        if field in SSH_KEY_TYPES:
            keyData = fields[index + 1] if index + 1 < len(fields) else ''
            if not keyData:
                return None
            comment = fields[index + 2] if index + 2 < len(fields) else ''
            return {'keyType': field, 'keyData': keyData, 'comment': comment}

    return None
