"""Fail-closed settings for operator-provisioned Google Drive installations.

Only fixed, root-owned private JSON files are read. No HTTP request, environment
variable, callback hostname or OAuth credential can add an installation here.
"""
import ipaddress
import json
import logging
import os
from pathlib import PurePosixPath
import re
import stat
from urllib.parse import urlsplit

CONFIG_PATHS = {
    'panel': '/etc/cyberpanel/gdrive-handoff.json',
    'platform': '/etc/cyberhosting/gdrive-handoff.json',
}
CALLBACK_PATHS = ('/backup/gDriveSetup', '/IncrementalBackups/ConfigureV2BackupSetup')
KEY = re.compile(r'[A-Za-z0-9_-]{32,256}\Z')
MAX_BYTES = 65536


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('Duplicate field')
        result[key] = value
    return result


def _reject_constant(value):
    raise ValueError('Invalid JSON constant')


def _absolute_path(value):
    if (not isinstance(value, str) or not value.startswith('/') or
            any(ord(c) < 32 or ord(c) >= 127 for c in value) or
            str(PurePosixPath(value)) != value or '..' in value.split('/') or value == '/'):
        raise ValueError('Invalid absolute path')
    return value


def _read_private_json(path):
    """Walk trusted directories using dirfds; reject links and writable ancestry."""
    parts = _absolute_path(path).split('/')[1:]
    directory = os.open('/', os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
            info = os.fstat(directory)
            if info.st_uid != 0 or stat.S_IMODE(info.st_mode) & 0o022:
                raise ValueError('Untrusted configuration directory')
        fd = os.open(parts[-1], os.O_RDONLY | os.O_NONBLOCK | os.O_NOFOLLOW, dir_fd=directory)
        try:
            info = os.fstat(fd)
            if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0 or info.st_nlink != 1
                    or stat.S_IMODE(info.st_mode) & 0o7137 or info.st_size > MAX_BYTES):
                # Permit root 0600 or root + a service read-group 0640 only.
                raise ValueError('Untrusted configuration file')
            chunks = []
            length = 0
            while True:
                chunk = os.read(fd, min(8192, MAX_BYTES + 1 - length))
                if not chunk:
                    break
                chunks.append(chunk)
                length += len(chunk)
                if length > MAX_BYTES:
                    raise ValueError('Configuration too large')
            after = os.fstat(fd)
            if (info.st_size, info.st_mtime_ns, info.st_ctime_ns) != (
                    after.st_size, after.st_mtime_ns, after.st_ctime_ns):
                raise ValueError('Configuration changed during read')
            return json.loads(b''.join(chunks).decode('utf-8'),
                              object_pairs_hook=_unique_object, parse_constant=_reject_constant)
        finally:
            os.close(fd)
    finally:
        os.close(directory)


def _origin(value):
    if (not isinstance(value, str) or not value or
            any(ord(c) <= 32 or ord(c) >= 127 for c in value) or '\\' in value):
        raise ValueError('Invalid HTTPS origin')
    url = urlsplit(value)
    if (url.scheme != 'https' or not url.hostname or url.username or url.password
            or url.query or url.fragment or url.path or value.endswith(('?', '#'))):
        raise ValueError('Invalid HTTPS origin')
    host = url.hostname
    try:
        address = ipaddress.ip_address(host)
        canonical_host = '[' + host + ']' if address.version == 6 else host
    except ValueError:
        if (len(host) > 253 or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label)
                                 for label in host.split('.'))):
            raise ValueError('Invalid hostname')
        canonical_host = host
    port = url.port
    if port is not None and not 1 <= port <= 65535:
        raise ValueError('Invalid port')
    expected = 'https://' + canonical_host + (':' + str(port) if port is not None else '')
    if expected != value:
        raise ValueError('Use the exact canonical browser origin')
    return value


def _key(value):
    if not isinstance(value, str) or not KEY.fullmatch(value):
        raise ValueError('Invalid installation key')
    return value


def _disabled(role):
    result = {'GDRIVE_HANDOFF_ENABLED': False}
    if role == 'panel':
        result.update(GDRIVE_PLATFORM_BASE_URL='https://platform.cyberpersons.com',
                      GDRIVE_HANDOFF_REGISTRATION_KEY='')
    else:
        result.update(GDRIVE_HANDOFF_BASE_URL='', GDRIVE_HANDOFF_DB='',
                      GDRIVE_HANDOFF_CALLBACKS=[], GDRIVE_HANDOFF_CLIENT_KEYS={})
    return result


def _validate(data, role):
    if role not in CONFIG_PATHS:
        raise ValueError('Unknown configuration role')
    allowed = {'version', 'enabled', 'platform_origin'}
    allowed |= {'installation_key'} if role == 'panel' else {'database', 'installations'}
    if (not isinstance(data, dict) or set(data) - allowed or type(data.get('version')) is not int
            or data['version'] != 1 or type(data.get('enabled')) is not bool):
        raise ValueError('Invalid configuration schema')
    if data['enabled'] is False:
        return _disabled(role)
    if set(data) != allowed:
        raise ValueError('Incomplete configuration')
    origin = _origin(data['platform_origin'])
    if role == 'panel':
        return {'GDRIVE_HANDOFF_ENABLED': True, 'GDRIVE_PLATFORM_BASE_URL': origin,
                'GDRIVE_HANDOFF_REGISTRATION_KEY': _key(data['installation_key'])}
    installations = data['installations']
    if not isinstance(installations, list) or not 1 <= len(installations) <= 256:
        raise ValueError('Installations required')
    callbacks, keys, origins, used_keys = [], {}, set(), set()
    for installation in installations:
        if not isinstance(installation, dict) or set(installation) != {'origin', 'key'}:
            raise ValueError('Invalid installation')
        callback_origin = _origin(installation['origin'])
        key = _key(installation['key'])
        if callback_origin in origins or key in used_keys:
            raise ValueError('Duplicate installation or reused key')
        origins.add(callback_origin)
        used_keys.add(key)
        for path in CALLBACK_PATHS:
            callback = callback_origin + path
            callbacks.append(callback)
            keys[callback] = key
    return {'GDRIVE_HANDOFF_ENABLED': True, 'GDRIVE_HANDOFF_BASE_URL': origin,
            'GDRIVE_HANDOFF_DB': _absolute_path(data['database']),
            'GDRIVE_HANDOFF_CALLBACKS': callbacks, 'GDRIVE_HANDOFF_CLIENT_KEYS': keys}


def load_gdrive_settings(role, path=None):
    """Invalid/missing configuration disables enrollment without breaking the app.

    The optional path is for isolated tests; settings always use the fixed path.
    """
    if role not in CONFIG_PATHS:
        raise ValueError('Unknown configuration role')
    try:
        return _validate(_read_private_json(path or CONFIG_PATHS[role]), role)
    except FileNotFoundError:
        return _disabled(role)
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        # Never log configuration values, installation keys or raw exceptions.
        logging.getLogger(__name__).warning(
            'Google Drive handoff configuration rejected; enrollment remains disabled.')
        return _disabled(role)
