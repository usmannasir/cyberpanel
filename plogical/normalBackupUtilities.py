import os
import posixpath
import re
import shutil
import time


BACKUP_RUN_NAME = re.compile(r'^\d{2}\.\d{2}\.\d{4}_\d{2}-\d{2}-\d{2}$')


def normalize_local_backup_path(path):
    if not isinstance(path, str):
        raise ValueError('Local backup path is required.')

    candidate = path.strip()
    if not candidate:
        raise ValueError('Local backup path is required.')
    if '\x00' in candidate:
        raise ValueError('Local backup path contains an invalid character.')
    if not posixpath.isabs(candidate):
        raise ValueError('Local backup path must be an absolute path, such as /home/backup.')
    if '..' in candidate.split('/'):
        raise ValueError('Local backup path cannot contain parent-directory components.')

    normalized = posixpath.normpath(candidate)
    if normalized == '/':
        raise ValueError('The filesystem root cannot be used as a backup destination.')
    return normalized


def prepare_local_backup_run(destination_path, run_name):
    destination = normalize_local_backup_path(destination_path)
    if not run_name or '/' in run_name or run_name in ('.', '..'):
        raise ValueError('Invalid backup run name.')

    run_path = os.path.join(destination, run_name)
    os.makedirs(run_path, exist_ok=True)
    return run_path


def prune_expired_local_backup_runs(destination_path, retention_days, now=None):
    destination = normalize_local_backup_path(destination_path)
    try:
        retention_days = int(retention_days)
    except (TypeError, ValueError):
        raise ValueError('Backup retention must be a non-negative number of days.')
    if retention_days < 0:
        raise ValueError('Backup retention must be a non-negative number of days.')
    if retention_days == 0 or not os.path.isdir(destination):
        return []

    cutoff = (time.time() if now is None else now) - (retention_days * 86400)
    removed = []
    for entry in os.scandir(destination):
        if not BACKUP_RUN_NAME.fullmatch(entry.name):
            continue
        if not entry.is_dir(follow_symlinks=False):
            continue
        if entry.stat(follow_symlinks=False).st_mtime >= cutoff:
            continue
        shutil.rmtree(entry.path)
        removed.append(entry.path)
    return removed


def move_local_backup_archive(archive_path, run_path):
    if not os.path.isfile(archive_path) or os.path.getsize(archive_path) <= 0:
        raise FileNotFoundError('Completed backup archive is missing or empty: %s' % archive_path)
    if not os.path.isdir(run_path):
        raise FileNotFoundError('Backup destination directory does not exist: %s' % run_path)
    return shutil.move(archive_path, run_path)
