"""The folder a WordPress backup or restore works in, and what earlier releases left of such folders.

A job assembles a site's files, its database dump and a wp-config.php with
the database password in a folder of its own under STAGING_ROOT, named with
32 hex characters. The folder is the job's alone and goes when the job
ends. Releases up to 3.0.12 left the folder of every backup of files and
database behind, readable by every local account; the upgrade removes those.
"""
import os
import re
import shutil
import time


STAGING_ROOT = '/usr/local/CyberCP/tmp'
JOB_FOLDER_NAME = re.compile(r'[0-9a-f]{32}')
# A folder younger than this may belong to a job that is still running.
STALE_AFTER = 24 * 60 * 60


def is_job_folder(path, root=STAGING_ROOT):
    """Whether a path is a job's own folder: directly under the staging root, named with 32 hex characters.

    Asked before a job's folder is removed, so that a path that is anything
    else (empty, the root itself, a path with further parts) is never
    handed to `rm -rf`.
    """
    if not isinstance(path, str) or not isinstance(root, str) or not root.startswith('/'):
        return False
    name = os.path.basename(path)
    return JOB_FOLDER_NAME.fullmatch(name) is not None and path == '%s/%s' % (root.rstrip('/'), name)


def looks_like_backup_staging(path):
    """Whether a folder holds what a backup assembles: a public_html folder or a database dump at its top."""
    try:
        entries = list(os.scandir(path))
    except OSError:
        return False
    for entry in entries:
        if entry.name == 'public_html' and entry.is_dir(follow_symlinks=False):
            return True
        if entry.name.endswith('.sql') and entry.is_file(follow_symlinks=False):
            return True
    return False


def stale_staging_folders(root=STAGING_ROOT, now=None, stale_after=STALE_AFTER):
    """The folders under the staging root that an earlier release's backup left behind.

    Only a real folder (not a link) directly under the root, named as a
    job's folder is, last changed more than a day ago and holding what a
    backup assembles. Anything else under the root is not this function's
    to judge and is left out.
    """
    now = time.time() if now is None else now
    found = []
    try:
        entries = sorted(os.scandir(root), key=lambda entry: entry.name)
    except OSError:
        return found
    for entry in entries:
        try:
            if not entry.is_dir(follow_symlinks=False) or not is_job_folder(entry.path, root):
                continue
            if now - entry.stat(follow_symlinks=False).st_mtime <= stale_after:
                continue
        except OSError:
            continue
        if looks_like_backup_staging(entry.path):
            found.append(entry.path)
    return found


def folder_size(path):
    """The bytes the files below a folder hold; links are counted as links, not followed."""
    total = 0
    for folder, folders, files in os.walk(path, onerror=lambda error: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(folder, name)).st_size
            except OSError:
                pass
    return total


def remove_stale_staging(root=STAGING_ROOT, log=print, now=None, remove=shutil.rmtree):
    """Remove the staging folders earlier releases left behind and say how many and how much.

    Returns (folders removed, bytes they held). A folder that cannot be
    removed is named and does not stop the others.
    """
    removed = 0
    freed = 0
    for path in stale_staging_folders(root, now):
        size = folder_size(path)
        try:
            remove(path)
        except OSError as error:
            log('WARNING: The backup work folder %s was not removed: %s' % (path, error))
            continue
        removed += 1
        freed += size
    log('Backup work folders left by earlier releases: %d removed, %.1f MB freed.' % (
        removed, freed / (1024.0 * 1024.0)))
    return removed, freed
