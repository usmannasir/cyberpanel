import os
import re
import shlex

from plogical.backupExcludes import SITE_BACKUP_DIRECTORIES


_DOMAIN_NAME = re.compile(
    r'^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$')
_BACKEND_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}$')
_CONFIG_SECTION = re.compile(r'^\s*\[([^\]\r\n]+)\]\s*$', re.MULTILINE)
_SNAPSHOT_ID = re.compile(r'[0-9a-f]{8,64}')
_DATABASE_NAME = re.compile(r'[A-Za-z0-9_]{1,64}')
_MAILBOX_NAME = re.compile(r'[^@\s]+')


def rustic_repository(backend_name, domain):
    if not _DOMAIN_NAME.fullmatch(domain or ''):
        raise ValueError('Invalid backup domain.')
    if backend_name == 'local':
        return '/home/%s/incrementalbackups' % domain
    if not _BACKEND_NAME.fullmatch(backend_name or ''):
        raise ValueError('Invalid backup repository name.')
    return shlex.quote('rclone:%s:%s' % (backend_name, domain))


def repository_names(config_content):
    repositories = ['local']
    for name in _CONFIG_SECTION.findall(config_content or ''):
        if name != 'local' and _BACKEND_NAME.fullmatch(name):
            repositories.append(name)
    return repositories


def website_exclude_arguments(source):
    prefix = '/home/'
    if not source.startswith(prefix):
        raise ValueError('Invalid website backup path.')
    domain = source[len(prefix):]
    if not _DOMAIN_NAME.fullmatch(domain):
        raise ValueError('Invalid website backup path.')
    return ' '.join(
        '--glob !%s/%s' % (source, directory)
        for directory in SITE_BACKUP_DIRECTORIES
    )


def database_name_from_snapshot_path(path):
    if not path or not path.endswith('.sql') or len(path) == 4:
        raise ValueError('Invalid database snapshot path.')
    return path[:-4]


def snapshot_id(value):
    """A snapshot is named by its hexadecimal identifier and nothing else."""
    if not isinstance(value, str) or _SNAPSHOT_ID.fullmatch(value) is None:
        raise ValueError('Invalid backup snapshot.')
    return value


def restore_target(path, domain):
    """Classify the path chosen for a restore, or raise ValueError.

    ('database', name)  a dump of one database, stored as <name>.sql
    ('mail', path)      this website's own mail directory, or a path below it
    ('files', path)     this website's own home, or a path below it

    The path comes from the browser. Only these three kinds exist, so a restore
    can never read from or write to another website's data.
    """
    if not isinstance(domain, str) or not _DOMAIN_NAME.fullmatch(domain) or '..' in domain:
        raise ValueError('Invalid backup domain.')
    if not isinstance(path, str) or not path or any(ord(char) < 32 or ord(char) == 127 for char in path):
        raise ValueError('Invalid restore path.')
    if '/' not in path and path.endswith('.sql'):
        name = path[:-len('.sql')]
        if _DATABASE_NAME.fullmatch(name) is None:
            raise ValueError('Invalid restore path.')
        return 'database', name
    if not path.startswith('/') or os.path.normpath(path) != path:
        raise ValueError('Invalid restore path.')
    if path == '/home/backup/%s/config.json' % domain:
        return 'files', path
    for kind, home in (('mail', '/home/vmail/' + domain), ('files', '/home/' + domain)):
        if path == home or path.startswith(home + '/'):
            return kind, path
    raise ValueError('Invalid restore path.')


def restore_command(repository, snapshot, path):
    """The rustic command restoring one checked path of one snapshot in place.

    `repository` is the value returned by rustic_repository().
    """
    return 'rustic -r %s restore %s %s --password ""  2>/dev/null' % (
        repository, shlex.quote('%s:%s' % (snapshot_id(snapshot), path)), shlex.quote(path))


def own_mailbox(email, domain):
    """Whether a mailbox named in a restored configuration is this website's own."""
    if not isinstance(email, str) or not isinstance(domain, str) or email.count('@') != 1:
        return False
    name, _, mail_domain = email.partition('@')
    return _MAILBOX_NAME.fullmatch(name) is not None and mail_domain.lower() == domain.lower()
