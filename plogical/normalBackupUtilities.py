import os
import posixpath
import shutil


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


def move_local_backup_archive(archive_path, run_path):
    if not os.path.isfile(archive_path) or os.path.getsize(archive_path) <= 0:
        raise FileNotFoundError('Completed backup archive is missing or empty: %s' % archive_path)
    if not os.path.isdir(run_path):
        raise FileNotFoundError('Backup destination directory does not exist: %s' % run_path)
    return shutil.move(archive_path, run_path)
