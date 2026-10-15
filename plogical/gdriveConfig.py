"""Append a new Drive remote atomically, as its website user, without shell secrets."""
import argparse
import configparser
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import stat
import sys
import tempfile


def validate_credentials(credentials):
    if not isinstance(credentials, dict):
        raise ValueError('Invalid credentials')
    if any(not isinstance(credentials.get(key), str) for key in
           ('token', 'refresh_token', 'client_id', 'client_secret', 'expiry')):
        raise ValueError('Invalid credentials')
    for key in ('token', 'refresh_token'):
        if not isinstance(credentials.get(key), str) or not re.fullmatch(r'[A-Za-z0-9._~+/=-]{1,8192}', credentials[key]):
            raise ValueError('Invalid credentials')
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,256}\.apps\.googleusercontent\.com', credentials.get('client_id', '')):
        raise ValueError('Invalid client')
    if not re.fullmatch(r'[A-Za-z0-9._~-]{1,512}', credentials.get('client_secret', '')):
        raise ValueError('Invalid client')
    expiry = datetime.fromisoformat(credentials['expiry'].replace('Z', '+00:00'))
    if expiry.tzinfo is None or not 0 < (expiry - datetime.now(timezone.utc)).total_seconds() <= 86400:
        raise ValueError('Invalid expiry')


def _owned_directory(path):
    info = path.lstat()
    if not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid():
        raise ValueError('Unsafe configuration directory')


def write_remote(home, account, credentials):
    validate_credentials(credentials)
    if not isinstance(account, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,63}', account):
        raise ValueError('Invalid account')
    home = Path(home)
    if not home.is_absolute() or any(path.is_symlink() for path in [home, *home.parents]):
        raise ValueError('Unsafe home directory')
    _owned_directory(home)
    directory = home
    for part in ('.config', 'rclone'):
        directory = directory / part
        try:
            directory.mkdir(mode=0o700)
        except FileExistsError:
            pass
        _owned_directory(directory)
        if directory.stat().st_mode & 0o022:
            raise ValueError('Configuration directory is writable by another user')
    lock = os.open(str(directory / '.gdrive-oauth.lock'), os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK, 0o600)
    temp = None
    try:
        info = os.fstat(lock)
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077 or info.st_nlink != 1:
            raise ValueError('Unsafe lock')
        fcntl.flock(lock, fcntl.LOCK_EX)
        config = directory / 'rclone.conf'
        old = b''
        original_info = None
        if config.exists() or config.is_symlink():
            descriptor = os.open(str(config), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                info = os.fstat(descriptor)
                original_info = info
                if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or
                        info.st_size > 4 * 1024 * 1024 or info.st_mode & 0o077 or info.st_nlink != 1):
                    raise ValueError('Unsafe existing config')
                with os.fdopen(descriptor, 'rb', closefd=False) as handle:
                    old = handle.read(4 * 1024 * 1024 + 1)
            finally:
                os.close(descriptor)
        parser = configparser.ConfigParser(interpolation=None, strict=True)
        parser.read_string(old.decode('utf-8'))
        if parser.has_section(account):
            raise ValueError('A destination with this name already exists')
        token = json.dumps({'access_token': credentials['token'], 'refresh_token': credentials['refresh_token'],
                            'token_type': 'Bearer', 'expiry': credentials['expiry']}, separators=(',', ':'))
        new = ('\n[' + account + ']\ntype = drive\nscope = drive.file\nclient_id = ' + credentials['client_id'] +
               '\nclient_secret = ' + credentials['client_secret'] + '\ntoken = ' + token + '\n').encode()
        descriptor, temp = tempfile.mkstemp(prefix='.gdrive-', dir=str(directory))
        with os.fdopen(descriptor, 'wb') as handle:
            handle.write(old + new)
            handle.flush()
            os.fsync(handle.fileno())
        # Native rclone does not honor this enrollment lock. Refuse an observed
        # concurrent edit rather than replacing newer credentials. This check is
        # not filesystem CAS: operators must serialize configuration changes.
        if original_info is None:
            if config.exists() or config.is_symlink():
                raise ValueError('Drive configuration changed concurrently')
        else:
            current_fd = os.open(str(config), os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                fingerprint = lambda value: (value.st_dev, value.st_ino, value.st_size,
                                             value.st_mtime_ns, value.st_ctime_ns)
                if fingerprint(os.fstat(current_fd)) != fingerprint(original_info):
                    raise ValueError('Drive configuration changed concurrently')
                with os.fdopen(current_fd, 'rb', closefd=False) as current:
                    if current.read(4 * 1024 * 1024 + 1) != old:
                        raise ValueError('Drive configuration changed concurrently')
                if fingerprint(config.lstat()) != fingerprint(original_info):
                    raise ValueError('Drive configuration changed concurrently')
            finally:
                os.close(current_fd)
        os.replace(temp, config)
        temp = None
        dir_descriptor = os.open(str(directory), os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(dir_descriptor)
        finally:
            os.close(dir_descriptor)
    finally:
        if temp:
            os.unlink(temp)
        os.close(lock)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--home', required=True)
    args = parser.parse_args()
    try:
        data = json.loads(sys.stdin.buffer.read(32769))
        write_remote(args.home, data['account'], data['credentials'])
    except Exception:
        print('Google Drive destination was not saved.', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
