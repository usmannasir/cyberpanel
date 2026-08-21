import base64
import binascii
import fcntl
import hashlib
import os
import re
import shlex
import stat
import struct
import tempfile


SSH_KEY_TYPES = {
    'ssh-rsa',
    'ssh-dss',
    'ssh-ed25519',
    'ecdsa-sha2-nistp256',
    'ecdsa-sha2-nistp384',
    'ecdsa-sha2-nistp521',
    'sk-ssh-ed25519@openssh.com',
    'sk-ecdsa-sha2-nistp256@openssh.com',
    'ssh-rsa-cert-v01@openssh.com',
    'ssh-dss-cert-v01@openssh.com',
    'ssh-ed25519-cert-v01@openssh.com',
    'ecdsa-sha2-nistp256-cert-v01@openssh.com',
    'ecdsa-sha2-nistp384-cert-v01@openssh.com',
    'ecdsa-sha2-nistp521-cert-v01@openssh.com',
    'sk-ssh-ed25519-cert-v01@openssh.com',
    'sk-ecdsa-sha2-nistp256-cert-v01@openssh.com',
}

_KEY_DATA_RE = re.compile(r'^[A-Za-z0-9+/]+={0,2}$')
_KEY_ID_RE = re.compile(r'^[0-9a-f]{64}$')


def _decode_key_data(key_data):
    if not _KEY_DATA_RE.fullmatch(key_data):
        return None

    padded = key_data + ('=' * ((4 - len(key_data) % 4) % 4))
    try:
        return base64.b64decode(padded, validate=True)
    except (binascii.Error, ValueError):
        return None


def parse_authorized_key(line):
    """Return validated OpenSSH key data from an authorized_keys line."""
    if not line or line.lstrip().startswith('#'):
        return None

    try:
        fields = shlex.split(line, comments=False, posix=True)
    except ValueError:
        return None

    for index, key_type in enumerate(fields[:-1]):
        if key_type not in SSH_KEY_TYPES:
            continue

        key_data = fields[index + 1]
        decoded = _decode_key_data(key_data)
        if decoded is None or len(decoded) < 4:
            return None

        embedded_length = struct.unpack('>I', decoded[:4])[0]
        embedded_end = 4 + embedded_length
        if embedded_end > len(decoded):
            return None

        try:
            embedded_type = decoded[4:embedded_end].decode('ascii')
        except UnicodeDecodeError:
            return None
        if embedded_type != key_type:
            return None

        return {
            'keyType': key_type,
            'keyData': key_data,
            'comment': ' '.join(fields[index + 2:]),
            'keyId': hashlib.sha256(decoded).hexdigest(),
        }

    return None


def authorized_key_records(lines):
    records = []
    for line in lines:
        parsed = parse_authorized_key(line)
        if parsed is None:
            continue

        display_key = '%s %s' % (
            parsed['keyType'],
            parsed['keyData'][:50],
        )
        if parsed['comment']:
            display_key += '  ..  %s' % parsed['comment']

        records.append({
            'userName': parsed['comment'].split('@', 1)[0],
            'key': display_key,
            'keyId': parsed['keyId'],
        })

    return records


def delete_authorized_key(path, key_id):
    """Atomically remove only the key identified by its full decoded blob."""
    if not isinstance(key_id, str) or not _KEY_ID_RE.fullmatch(key_id):
        return False

    path = os.path.abspath(path)
    original_stat = os.lstat(path)
    if not stat.S_ISREG(original_stat.st_mode):
        raise ValueError('Authorized keys path must be a regular file.')
    if original_stat.st_nlink != 1:
        raise ValueError('Authorized keys file must not be hard linked.')

    with open(path, 'r', encoding='utf-8', errors='surrogateescape', newline='') as source:
        fcntl.flock(source.fileno(), fcntl.LOCK_EX)
        lines = source.readlines()

        retained = []
        deleted = False
        for line in lines:
            parsed = parse_authorized_key(line)
            if parsed is not None and parsed['keyId'] == key_id:
                deleted = True
                continue
            retained.append(line)

        if not deleted:
            return False

        current_stat = os.lstat(path)
        if (
            current_stat.st_dev != original_stat.st_dev
            or current_stat.st_ino != original_stat.st_ino
        ):
            raise ValueError('Authorized keys file changed during update.')

        directory = os.path.dirname(path)
        descriptor, temporary_path = tempfile.mkstemp(
            prefix='.authorized_keys.',
            dir=directory,
        )
        try:
            os.fchmod(descriptor, stat.S_IMODE(original_stat.st_mode))
            os.fchown(descriptor, original_stat.st_uid, original_stat.st_gid)
            with os.fdopen(
                descriptor,
                'w',
                encoding='utf-8',
                errors='surrogateescape',
                newline='',
            ) as destination:
                descriptor = None
                destination.writelines(retained)
                destination.flush()
                os.fsync(destination.fileno())

            os.replace(temporary_path, path)
            directory_descriptor = os.open(directory, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            if descriptor is not None:
                os.close(descriptor)
            if os.path.exists(temporary_path):
                os.unlink(temporary_path)

    return True
