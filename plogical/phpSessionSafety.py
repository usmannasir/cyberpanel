#!/usr/bin/env python3
"""Retire the exact legacy CyberPanel session purge without touching sessions.

A PHP application's effective lifetime can differ from the global php.ini value.
Consequently a runtime-wide external file purge cannot safely infer expiry.
"""
import hashlib
import os
from pathlib import Path
import stat
import tempfile


CLEANER = Path('/usr/local/CyberCP/bin/cleansessions')
LEGACY_CLEANER = b'''#!/bin/bash
for version in $(ls /usr/local/lsws|grep lsphp); do echo ""; echo "PHP $version"; session_time=$(/usr/local/lsws/${version}/bin/php -i |grep -Ei 'session.gc_maxlifetime'| grep -Eo "[[:digit:]]+"|sort -u); find -O3 "/var/lib/lsphp/session/${version}" -ignore_readdir_race -depth -mindepth 1 -name 'sess_*' -type f -cmin 120 -delete; done
'''
RETIRED_CLEANER = b'''#!/bin/sh
# CyberPanel legacy global PHP session purge retired: application lifetimes vary.
# Retained as a no-op for existing cron entries. No session files are inspected.
# Configure application-specific cleanup and monitor session storage.
exit 0
'''


def _metadata(info):
    return (info.st_dev, info.st_ino, info.st_mode, info.st_uid, info.st_gid,
            info.st_size, info.st_mtime_ns, info.st_ctime_ns, info.st_nlink)


def _trusted_file(path):
    """Refuse links, aliases and writable/non-root installation paths."""
    for parent in reversed(path.parents):
        info = parent.lstat()
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != 0
                or info.st_mode & 0o022):
            raise RuntimeError('Untrusted session-cleaner directory: %s' % parent)
    info = path.lstat()
    if (not stat.S_ISREG(info.st_mode) or info.st_uid != 0
            or info.st_mode & 0o022 or info.st_nlink != 1):
        raise RuntimeError('Untrusted session-cleaner file: %s' % path)
    return info


def retire_legacy_cleaner(path=CLEANER):
    """Replace only the exact shipped helper; return an explicit disposition.

    The caller logs this result. Unknown/custom helpers remain untouched.
    No PHP configuration, crontab, session directory or service is accessed.
    """
    path = Path(path).absolute()
    if not path.exists() and not path.is_symlink():
        return 'absent'
    info = _trusted_file(path)
    original = path.read_bytes()
    if original == RETIRED_CLEANER:
        return 'already-retired'
    if original != LEGACY_CLEANER:
        return 'custom-preserved'

    digest = hashlib.sha256(original).hexdigest()
    backup = path.with_name(path.name + '.disabled-' + digest)
    if backup.exists() or backup.is_symlink():
        _trusted_file(backup)
        if backup.read_bytes() != original:
            raise RuntimeError('Existing session-cleaner backup differs')
    else:
        descriptor = os.open(str(backup), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(original)
            stream.flush()
            os.fsync(stream.fileno())

    descriptor, temporary = tempfile.mkstemp(prefix='.cleansessions-retire-', dir=str(path.parent))
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(RETIRED_CLEANER)
            stream.flush()
            os.fsync(stream.fileno())
        os.chown(temporary, info.st_uid, info.st_gid)
        os.chmod(temporary, stat.S_IMODE(info.st_mode))
        if (_metadata(_trusted_file(path)) != _metadata(info)
                or path.read_bytes() != original):
            raise RuntimeError('Session cleaner changed during retirement')
        os.replace(temporary, str(path))
        directory_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return 'retired'


def report_retirement(path=CLEANER, log=print):
    # Optional safety migration must not strand an otherwise valid upgrade.
    # A durability failure may happen after replacement, so do not claim that
    # the cleaner is unchanged or successfully retired when verification fails.
    try:
        result = retire_legacy_cleaner(path)
    except (OSError, RuntimeError) as error:
        log('WARNING: PHP session-cleaner retirement not verified; manual review required. The cleaner may have changed. Configure application-specific cleanup and monitor session storage. Detail: %s' % error)
        return 'unverified'
    if result == 'custom-preserved':
        log('WARNING: Unrecognized PHP session cleaner preserved; review its application-specific expiry policy manually.')
    elif result in ('retired', 'already-retired'):
        log('WARNING: CyberPanel legacy global PHP session purge is retired. Configure application-specific PHP GC/cleanup and monitor session storage; paths, lifetimes and session files were preserved.')
    else:
        log('PHP session defaults preserved. No CyberPanel global session purge installed; application-specific PHP GC/cleanup is required.')
    return result


if __name__ == '__main__':
    report_retirement()
