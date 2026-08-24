import hashlib
import json
import os
import pathlib
import re
import stat
import tempfile
import time


HANDOFF_DIRECTORY = pathlib.Path(tempfile.gettempdir()) / 'cyberpanel-phpmyadmin-handoff'
HANDOFF_TTL = 120
_RECORD_NAME = re.compile(r'^[0-9a-f]{64}$')


def _prepare_directory(directory):
    directory = pathlib.Path(directory)
    try:
        directory.mkdir(mode=0o700)
    except FileExistsError:
        pass

    directory_stat = os.lstat(directory)
    if not stat.S_ISDIR(directory_stat.st_mode):
        raise PermissionError('phpMyAdmin handoff path is not a directory')
    if directory_stat.st_uid != os.geteuid():
        raise PermissionError('phpMyAdmin handoff directory has the wrong owner')
    if stat.S_IMODE(directory_stat.st_mode) != 0o700:
        raise PermissionError('phpMyAdmin handoff directory must use mode 0700')
    return directory


def _remove_expired_records(directory, now, ttl):
    cutoff = now - ttl
    for entry in os.scandir(directory):
        if not _RECORD_NAME.fullmatch(entry.name):
            continue
        try:
            entry_stat = entry.stat(follow_symlinks=False)
            if (
                stat.S_ISREG(entry_stat.st_mode)
                and entry_stat.st_uid == os.geteuid()
                and stat.S_IMODE(entry_stat.st_mode) == 0o600
                and entry_stat.st_nlink == 1
                and entry_stat.st_mtime < cutoff
            ):
                os.unlink(entry.path)
        except FileNotFoundError:
            continue


def create_handoff(username, token, directory=HANDOFF_DIRECTORY, now=None,
                   ttl=HANDOFF_TTL):
    if not isinstance(username, str) or not username or len(username) > 255:
        raise ValueError('Invalid phpMyAdmin handoff username')
    if not isinstance(token, str) or not token or len(token) > 512:
        raise ValueError('Invalid phpMyAdmin handoff token')
    if not isinstance(ttl, int) or ttl < 1 or ttl > 300:
        raise ValueError('Invalid phpMyAdmin handoff lifetime')

    now = int(time.time() if now is None else now)
    directory = _prepare_directory(directory)
    _remove_expired_records(directory, now, ttl)

    record_name = hashlib.sha256(token.encode('utf-8')).hexdigest()
    record_path = directory / record_name
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, 'O_NOFOLLOW'):
        flags |= os.O_NOFOLLOW

    descriptor = os.open(record_path, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        payload = json.dumps(
            {'username': username, 'expires': now + ttl},
            separators=(',', ':'),
        ).encode('utf-8')
        os.write(descriptor, payload)
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        try:
            os.unlink(record_path)
        except FileNotFoundError:
            pass
        raise
    else:
        os.close(descriptor)

    return record_path
