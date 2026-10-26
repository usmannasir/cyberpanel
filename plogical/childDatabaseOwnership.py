"""Keep a converted WordPress child's database independent of its old parent."""
import json
import os
import shlex

from plogical.securityUtils import is_safe_sql_identifier, is_safe_system_user


def wordpress_identity(path, user, php, execute):
    """Read config constants with existing WP-CLI, under the site's Unix user."""
    if not is_safe_system_user(user) or user == 'root':
        raise ValueError('Cannot safely inspect the website configuration user.')
    config = os.path.join(path, 'wp-config.php')
    probe = (
        'if [ ! -x {root} ]; then exit 1; '
        'elif [ -L {config} ]; then exit 1; '
        'elif [ ! -e {config} ] && [ ! -d {root}/wp-includes ] && [ ! -e {root}/wp-load.php ]; then printf absent; '
        'elif [ -f {config} ] && [ -r {config} ]; then printf present; '
        'else exit 1; fi'
    ).format(root=shlex.quote(path), config=shlex.quote(config))
    ok, output = execute('/bin/sh -c ' + shlex.quote(probe), user, retRequired=True)
    if not ok or output.strip() not in ('present', 'absent'):
        raise ValueError('Cannot safely read a WordPress configuration. Fix its permissions before conversion.')
    if output.strip() == 'absent':
        return None
    values = {}
    for key in ('DB_NAME', 'DB_USER'):
        command = ' '.join(shlex.quote(part) for part in (
            '/usr/bin/timeout', '20', php, '-d', 'error_reporting=0', '/usr/bin/wp',
            'config', 'get', key, '--skip-plugins', '--skip-themes', '--path=' + path))
        ok, output = execute(command, user, retRequired=True)
        value = output.strip()
        if not ok or not is_safe_sql_identifier(value):
            raise ValueError('Cannot determine the WordPress database safely. Check WP-CLI/config constants before conversion.')
        values[key] = value
    return values


def _normal(path):
    return os.path.realpath(path).rstrip('/')


def assert_independent_accounts(database):
    from databases.models import Databases, DatabasesUsers
    from plogical.mysqlUtilities import mysqlUtilities

    accounts = {database.dbUser}
    accounts.update(DatabasesUsers.objects.filter(owner=database).values_list('username', flat=True))
    if (Databases.objects.filter(dbUser__in=accounts).exclude(pk=database.pk).exists() or
            DatabasesUsers.objects.filter(username__in=accounts).exclude(owner=database).exists()):
        raise ValueError('A database account is shared with another managed database. Use independent credentials before converting.')
    connection, cursor = mysqlUtilities.setupConnection()
    if connection == 0:
        raise ValueError('Cannot verify database account grants before conversion.')
    try:
        # Parent deletion drops every account granted on the database being removed.
        # Include manually added grants, which need not have panel model rows.
        cursor.execute('SELECT User FROM mysql.db WHERE Db IN (%s, %s)',
                       (database.dbName, database.dbName.replace('_', r'\_')))
        accounts.update(row[0] for row in cursor.fetchall())
        for account in accounts:
            cursor.execute('SELECT Db FROM mysql.db WHERE User = %s', (account,))
            if any(row[0].replace(r'\_', '_') != database.dbName for row in cursor.fetchall()):
                raise ValueError('A database account has grants on another database. Use independent credentials before converting.')
    finally:
        connection.close()


def child_metadata(master_id, child_path):
    from websiteFunctions.models import WPSites, WPStaging
    from cloudAPI.models import WPDeployments

    ids = []
    for site in WPSites.objects.filter(owner_id=master_id):
        if not isinstance(site.path, str) or not site.path:
            raise ValueError('Cannot determine a managed WordPress installation path.')
        if _normal(site.path) == child_path:
            ids.append(site.pk)
    if WPStaging.objects.filter(owner_id__in=ids).exists():
        raise ValueError('This WordPress site owns staging sites. Detach those staging relationships before converting.')
    from websiteFunctions.models import Websites
    master = Websites.objects.get(pk=master_id)
    paths = []
    for deployment in WPDeployments.objects.filter(owner_id=master_id):
        try:
            config = json.loads(deployment.config)
            relative = config.get('path', '')
            if not isinstance(relative, str):
                raise ValueError()
            path = os.path.join('/home/%s/public_html' % master.domain, relative)
        except (ValueError, TypeError, AttributeError):
            raise ValueError('Cannot determine another WordPress installation path. Conversion was stopped.') from None
        if _normal(path) == child_path:
            raise ValueError('This child has managed WordPress deployment settings. Remove or migrate those settings before converting.')
        paths.append(path)
    return sorted(ids), paths


def capture_child_database(child):
    from databases.models import Databases
    from websiteFunctions.models import ChildDomains, WPSites
    from cloudAPI.models import WPDeployments
    from managePHP.phpManager import PHPManager
    from plogical.processUtilities import ProcessUtilities

    master = child.master
    php_version = PHPManager.getPHPString(master.phpSelection)
    if not str(php_version).isdigit():
        raise ValueError('Invalid PHP selection for database inspection.')
    php = '/usr/local/lsws/lsphp%s/bin/php' % php_version
    read = lambda path: wordpress_identity(path, master.externalApp, php, ProcessUtilities.outputExecutioner)
    site_ids, deployment_paths = child_metadata(master.pk, _normal(child.path))
    identity = read(child.path)
    if identity is None:
        if site_ids:
            raise ValueError('A managed WordPress site has no local configuration. Conversion was stopped.')
        return None
    database = Databases.objects.filter(dbName=identity['DB_NAME']).first()
    if database is None:
        return None  # Unregistered databases do not participate in parent deletion.
    if database.website_id != master.pk or database.dbUser != identity['DB_USER']:
        raise ValueError('The WordPress database does not belong exclusively to this parent website. Conversion was stopped.')

    assert_independent_accounts(database)
    paths = {'/home/%s/public_html' % master.domain}
    paths.update(ChildDomains.objects.filter(master=master).exclude(pk=child.pk).values_list('path', flat=True))
    paths.update(WPSites.objects.filter(owner=master).values_list('path', flat=True))
    paths.update(deployment_paths)
    child_path = _normal(child.path)
    for path in sorted(paths):
        if not isinstance(path, str) or not path:
            raise ValueError('Cannot determine another WordPress installation path. Conversion was stopped.')
        if _normal(path) == child_path:
            continue
        other = read(path)
        if other is not None and other['DB_NAME'] == database.dbName:
            raise ValueError('This database is shared with another WordPress installation. Use a separate database before converting.')
    return dict(database_id=database.pk, master_id=master.pk, domain=child.domain,
                source_path=child.path, db_name=database.dbName, db_user=database.dbUser, site_ids=site_ids)


def transfer_child_database(snapshot, destination):
    if snapshot is None:
        return
    from django.db import transaction
    from databases.models import Databases
    from websiteFunctions.models import Websites, WPSites, WPStaging
    from managePHP.phpManager import PHPManager
    from plogical.processUtilities import ProcessUtilities

    target = Websites.objects.get(domain=snapshot['domain'])
    if target.pk == snapshot['master_id']:
        raise ValueError('The converted website must be independent of its original parent.')
    php_version = PHPManager.getPHPString(target.phpSelection)
    if not str(php_version).isdigit():
        raise ValueError('Invalid PHP selection for database inspection.')
    identity = wordpress_identity(destination, target.externalApp,
        '/usr/local/lsws/lsphp%s/bin/php' % php_version, ProcessUtilities.outputExecutioner)
    if identity != {'DB_NAME': snapshot['db_name'], 'DB_USER': snapshot['db_user']}:
        raise ValueError('WordPress database settings changed during conversion; ownership was not transferred.')
    with transaction.atomic():
        database = Databases.objects.select_for_update().get(pk=snapshot['database_id'])
        if (database.website_id != snapshot['master_id'] or
                database.dbName != snapshot['db_name'] or database.dbUser != snapshot['db_user']):
            raise ValueError('Database ownership changed during conversion; refusing to overwrite it.')
        assert_independent_accounts(database)
        ids, unused = child_metadata(snapshot['master_id'], _normal(snapshot['source_path']))
        if ids != snapshot['site_ids']:
            raise ValueError('WordPress metadata changed during conversion; refusing to overwrite it.')
        database.website = target
        database.save(update_fields=['website'])
        sites = WPSites.objects.select_for_update().filter(owner_id=snapshot['master_id'],
            pk__in=ids)
        ids = list(sites.values_list('pk', flat=True))
        sites.update(owner=target, path=destination)
        WPStaging.objects.filter(wpsite_id__in=ids).delete()
