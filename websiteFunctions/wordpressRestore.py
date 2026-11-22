"""Decide what a WordPress restore may do before it creates or changes anything."""
import os
import re


def validate_restore_path(root, relative):
    if not isinstance(relative, str) or len(relative) > 200:
        raise ValueError('Invalid restore path.')
    if relative.startswith('/') or '\\' in relative or '..' in relative:
        raise ValueError('Restore path must stay inside the new website document root.')
    relative = relative.rstrip('/')
    if relative:
        parts = relative.split('/')
        if any(part in ('', '.') or not re.fullmatch(r'[A-Za-z0-9_.-]+', part) for part in parts):
            raise ValueError('Use only letters, numbers, dots, hyphens and underscores in restore path segments.')
    canonical_root = os.path.realpath(root)
    target = os.path.realpath(os.path.join(root, relative))
    if (canonical_root != os.path.abspath(root) or
            os.path.commonpath((canonical_root, target)) != canonical_root):
        raise ValueError('Restore path must stay inside the new website document root.')
    return relative, '0' if relative else '1'


# The kinds of backup WordPress Manager makes, as their descriptions name them.
# A description without one of these names is a backup of files and database.
BACKUP_KINDS = {'DataBase Backup': 'database', 'Website Backup': 'files'}


def restore_plan(backup_type, destination_site_id, domain):
    """What a restore request asks for: (kind of backup, 'existing' or 'new' destination).

    kind is 'database', 'files' or 'both'. A request names either an existing
    WordPress site or a new domain, never both and never neither. A database
    alone cannot become a site, so it only goes into an existing one. Every
    other combination raises ValueError before anything is downloaded,
    created or changed.
    """
    kind = BACKUP_KINDS.get(backup_type, 'both')
    try:
        site = int(destination_site_id)
    except (TypeError, ValueError):
        raise ValueError('Select exactly one restore destination.')
    domain = domain if isinstance(domain, str) else ''
    existing = domain == '' and site != -1
    new = domain != '' and site == -1
    if existing == new:
        raise ValueError('Select exactly one restore destination.')
    if new and kind == 'database':
        raise ValueError('A database backup can only be restored to an existing WordPress site.')
    return kind, 'new' if new else 'existing'


def backup_parts(kind, extracted, random_path, dump_file):
    """Where a backup keeps what its kind promises, inside the folder it was unpacked to.

    Returns (directory of the site's files or None, database dump or None).
    A backup is an archive of the folder it was assembled in, so its content
    lies under that folder's full path.
    """
    root = '%s/ab/usr/local/CyberCP/tmp/%s' % (extracted, random_path)
    files = '%s/public_html' % root if kind in ('files', 'both') else None
    dump = '%s/%s' % (root, dump_file) if kind in ('database', 'both') else None
    return files, dump


def restored_site_address(domain, path):
    """The address WordPress Manager records for a site: its domain, and its folder when it has one."""
    return domain if not path else '%s/%s' % (domain, path)
