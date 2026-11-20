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


SCHEDULE_FREQUENCIES = ('30 Minutes', '1 Hour', '6 Hours', '12 Hours', '1 Day', '3 Days', '1 Week')
_RETENTION = re.compile(r'[0-9]{1,4}')
_FORGET_SELECTION = re.compile(r'--keep-daily [0-9]{1,4}|[0-9a-f]{8,64}')


def retention_days(value):
    """How many daily snapshots a schedule keeps: a whole number from 1 to 3650."""
    if isinstance(value, bool) or not isinstance(value, (int, str)):
        raise ValueError('Invalid backup retention.')
    if isinstance(value, str) and _RETENTION.fullmatch(value) is None:
        raise ValueError('Invalid backup retention.')
    days = int(value)
    if not 1 <= days <= 3650:
        raise ValueError('Invalid backup retention.')
    return days


def forget_selection(value):
    """What a forget run removes: one snapshot, or all but a number of daily ones.

    The text goes on a command line that the scheduled job runs as root.
    """
    if not isinstance(value, str) or _FORGET_SELECTION.fullmatch(value) is None:
        raise ValueError('Invalid snapshot selection.')
    return value


def schedule_entry(repo, frequency, retention, website_data, website_databases, website_emails):
    """One entry of a website's backup schedule, built only from checked values.

    The scheduled job reads the entry back as root, so nothing is stored that
    it could not put on a command line.
    """
    if repo != 'local':
        backend_name(repo)
    if not isinstance(frequency, str) or frequency not in SCHEDULE_FREQUENCIES:
        raise ValueError('Invalid backup frequency.')
    return {"repo": repo, "retention": str(retention_days(retention)), "frequency": frequency,
            "websiteData": website_data is True, "websiteEmails": website_emails is True,
            "websiteDatabases": website_databases is True, "lastRun": ""}


def backend_name(value):
    """The name of a storage backend as it appears in rclone.conf, or raise ValueError."""
    if not isinstance(value, str) or not _BACKEND_NAME.fullmatch(value):
        raise ValueError('Invalid backup repository name.')
    return value


def rclone_section(name, settings):
    """The text of one rclone.conf section.

    Names and values come from the browser. Each value stays on its own line,
    so it can never start another section or add another setting.
    """
    lines = ['', '[%s]' % backend_name(name)]
    for key, value in settings:
        if isinstance(value, bool) or not isinstance(value, (str, int)):
            raise ValueError('Invalid backup repository setting.')
        value = str(value)
        if any(ord(char) < 32 or ord(char) == 127 for char in value):
            raise ValueError('Invalid backup repository setting.')
        lines.append('%s = %s' % (key, value))
    return '\n'.join(lines) + '\n'


def remove_section_command(name, config_path):
    """The sed command that removes one backend's section from an rclone.conf."""
    pattern = backend_name(name).replace('.', '\\.')
    return "sed -i '/\\[%s\\]/,/^$/d' %s" % (pattern, shlex.quote(config_path))
