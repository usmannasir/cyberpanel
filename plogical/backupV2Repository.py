import re
import shlex

from plogical.backupExcludes import SITE_BACKUP_DIRECTORIES


_DOMAIN_NAME = re.compile(
    r'^[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?$')
_BACKEND_NAME = re.compile(r'^[A-Za-z0-9][A-Za-z0-9 ._-]{0,127}$')
_CONFIG_SECTION = re.compile(r'^\s*\[([^\]\r\n]+)\]\s*$', re.MULTILINE)


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
