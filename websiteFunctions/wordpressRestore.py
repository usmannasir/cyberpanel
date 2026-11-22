"""Decide what a WordPress restore may do before it creates or changes anything."""
import os
import re
from urllib.parse import urlsplit


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


# A backup is an archive of the folder it was assembled in, so everything in
# it lies under that folder's full path: this prefix and the folder's name.
BACKUP_FOLDER = 'usr/local/CyberCP/tmp'
BACKUP_FOLDER_NAME = re.compile(r'[A-Za-z0-9]{1,64}')
# Where the site's files lie under that folder. A site whose stored path has
# no slash at its end (a staging site) was copied one folder deeper.
SITE_FOLDERS = ('public_html', 'public_html/public_html')
# One of these in a folder makes it a WordPress site's folder.
SITE_MARKERS = ('wp-config.php', 'wp-includes/version.php')


def backup_listing_filter(random_path):
    """The pattern (grep -E) for the few names in an archive's listing that tell how the backup is laid out.

    The folder name comes from the backup's description; it is checked here,
    so nothing else can reach the pattern.
    """
    if not isinstance(random_path, str) or BACKUP_FOLDER_NAME.fullmatch(random_path) is None:
        raise ValueError('The backup names a work folder that no backup of this panel has.')
    return (r'^/?%s/%s/(public_html/(public_html/)?(wp-config\.php|wp-includes/version\.php)|[^/]+\.sql)$'
            % (BACKUP_FOLDER, random_path))


def backup_layout(kind, listing, random_path, dump_file):
    """Where a backup keeps what its kind promises, read from the listing of the archive itself.

    listing is the output of `tar -t`, whole or filtered with
    backup_listing_filter. Returns a dict of archive member names, written
    as the archive stores them:
      files   the folder that holds the site's files, or None
      config  the wp-config.php in that folder, or None when it has none
      strip   how many leading folders to drop so that the files land in
              the destination itself
      dump    the database dump, or None
      root    how many leading folders make up the path of the folder the
              backup was assembled in
    A backup that lacks what its kind promises raises ValueError with the
    reason, before anything is created or changed.
    """
    if not isinstance(random_path, str) or BACKUP_FOLDER_NAME.fullmatch(random_path) is None:
        raise ValueError('The backup names a work folder that no backup of this panel has.')
    root = '%s/%s' % (BACKUP_FOLDER, random_path)
    stored = {}
    for line in str(listing or '').splitlines():
        name = line.strip()
        plain = name.lstrip('/')
        if plain.startswith(root + '/'):
            # The archive may store names with or without the leading slash.
            stored[plain[len(root) + 1:]] = name[:len(name) - len(plain)]
    layout = {'files': None, 'config': None, 'strip': 0, 'dump': None, 'root': len(root.split('/'))}
    if kind in ('files', 'both'):
        folder = next((folder for folder in SITE_FOLDERS
                       if any('%s/%s' % (folder, marker) in stored for marker in SITE_MARKERS)), None)
        if folder is None:
            raise ValueError('The backup file could not be read or holds no WordPress files '
                             '(neither wp-config.php nor wp-includes was found in it)')
        marker = next(marker for marker in SITE_MARKERS if '%s/%s' % (folder, marker) in stored)
        slash = stored['%s/%s' % (folder, marker)]
        layout['files'] = '%s%s/%s' % (slash, root, folder)
        layout['strip'] = len(root.split('/')) + len(folder.split('/'))
        if '%s/wp-config.php' % folder in stored:
            layout['config'] = '%s/wp-config.php' % layout['files']
    if kind in ('database', 'both'):
        if not isinstance(dump_file, str) or dump_file not in stored:
            raise ValueError('The backup file could not be read or holds no database dump')
        layout['dump'] = '%s%s/%s' % (stored[dump_file], root, dump_file)
    return layout


# The constants in wp-config.php that tie a site to one address, or make it a network of sites.
ADDRESS_CONSTANTS = ('WP_HOME', 'WP_SITEURL')
NETWORK_CONSTANTS = ('MULTISITE', 'SUBDOMAIN_INSTALL', 'DOMAIN_CURRENT_SITE')
CONFIG_DEFINITION = re.compile(r'^\s*define\s*\(\s*[\'"]([A-Z_]+)[\'"]\s*,\s*(.*)$')
ADDRESS_FILTER = '|'.join(ADDRESS_CONSTANTS + NETWORK_CONSTANTS)


def other_domain_refusal(config_lines):
    """Why a backup cannot become a site under another domain, or None when nothing in its wp-config.php forbids it.

    config_lines are the lines of the backup's wp-config.php that mention
    one of the constants above. A line that is commented out does not count.
    """
    defined = {}
    for line in str(config_lines or '').splitlines():
        found = CONFIG_DEFINITION.match(line)
        if found is not None:
            defined[found.group(1)] = found.group(2).strip().lower()
    if any(name in defined for name in ADDRESS_CONSTANTS):
        return ('The wp-config.php in this backup fixes the address of the site (WP_HOME or WP_SITEURL), so the '
                'copy would still answer under the old domain. Restore it to its own site, or remove those lines '
                'on the site, make a new backup and restore that one')
    network = defined.get('MULTISITE', '')
    if (network.startswith(('true', '1', "'1'", '"1"')) or 'SUBDOMAIN_INSTALL' in defined
            or 'DOMAIN_CURRENT_SITE' in defined):
        return ('This backup is of a WordPress network (multisite), which is tied to its domain in wp-config.php '
                'and in its database. It can only be restored to its own site')
    return None


def address_is_on(address, domain):
    """Whether a site address (its siteurl) is on exactly this domain, with or without www."""
    text = str(address or '').strip()
    if '://' not in text:
        text = '//' + text
    try:
        host = (urlsplit(text).hostname or '').lower()
    except ValueError:
        return False
    domain = str(domain or '').lower()
    return bool(domain) and host in (domain, 'www.' + domain)


def restored_site_address(domain, path):
    """The address WordPress Manager records for a site: its domain, and its folder when it has one."""
    return domain if not path else '%s/%s' % (domain, path)
