"""Which database accounts the panel creates, changes or removes, and for whom.

A database server has three kinds of account next to each other:

  * accounts of the server and of the panel itself (root, mysql, cyberpanel,
    the administrative account of a remote database server, ...);
  * the account phpMyAdmin signs a panel user in with. It is named after the
    user's number (cp-pma-<id>): a customer's database user can never have
    that name, because such names are letters, numbers and underscores only;
  * the database users customers create for their websites.

Only the third kind is ever acted on for a customer, and only under the exact
name the panel registered. Names are compared in Python, because the panel's
own tables compare text without regard to case while the database server
tells `Shop_user` and `shop_user` apart.
"""
import json
import re

from plogical.databaseGrants import text
from plogical.securityUtils import is_safe_sql_identifier

PASSWORD_FILE = '/etc/cyberpanel/mysqlPassword'

PHPMYADMIN_PREFIX = 'cp-pma-'
_PHPMYADMIN_ACCOUNT = re.compile(r'cp-pma-[1-9][0-9]{0,17}')

# Accounts of the database server and of the panel, in lower case.
SYSTEM_ACCOUNTS = frozenset((
    'root', 'mysql', 'mariadb.sys', 'mysql.sys', 'mysql.session', 'mysql.infoschema',
    'debian-sys-maint', 'public', 'cyberpanel', 'rdsadmin',
))

_GLOBAL_USAGE = re.compile(r'GRANT USAGE ON \*\.\* TO ')
_DATABASE_GRANT = re.compile(r'GRANT [A-Z ,]+ ON `(?:[^`]|``)+`\.\* TO ')


def phpmyadmin_account(user_id):
    """The name of the account phpMyAdmin uses for the panel user with this number."""
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError('A phpMyAdmin account belongs to a saved panel user.')
    return PHPMYADMIN_PREFIX + str(user_id)


def is_phpmyadmin_account(name):
    return isinstance(name, str) and _PHPMYADMIN_ACCOUNT.fullmatch(name) is not None


def administrative_account(path=PASSWORD_FILE):
    """The account the panel itself signs in to the database server with."""
    try:
        with open(path) as stream:
            return str(json.load(stream)['mysqluser'])
    except Exception:
        return 'root'


def is_system_account(name):
    """True for a name of the server, of the panel, or in the phpMyAdmin namespace."""
    if not isinstance(name, str) or not name:
        return True
    lowered = name.lower()
    return lowered in SYSTEM_ACCOUNTS or lowered.startswith(PHPMYADMIN_PREFIX)


def is_reserved(name):
    """True for an account a customer's request must never create or change."""
    return is_system_account(name) or name.lower() == administrative_account().lower()


def _exists_ignoring_case(model, field, name):
    from django.db.models.functions import Lower
    return model.objects.annotate(lowered_name=Lower(field)).filter(lowered_name=name.lower()).exists()


def named_like_panel_user(name):
    """True when a panel user, or a phpMyAdmin record of one, has this name in any case."""
    from databases.models import GlobalUserDB
    from loginSystem.models import Administrator
    return (_exists_ignoring_case(Administrator, 'userName', name)
            or _exists_ignoring_case(GlobalUserDB, 'username', name))


def registered_as_database_user(name):
    """True when a database is registered with a user of this name in any case."""
    from databases.models import Databases, DatabasesUsers
    return (_exists_ignoring_case(Databases, 'dbUser', name)
            or _exists_ignoring_case(DatabasesUsers, 'username', name))


def account_refusal(name):
    """Why a customer's database user may not have this name; None when it may."""
    if not is_safe_sql_identifier(name):
        return 'A database user name may only contain letters, numbers and underscores.'
    if is_reserved(name):
        return 'This database user name is reserved for the server.'
    if named_like_panel_user(name):
        return 'This database user name is the name of a panel user. Choose another name.'
    return None


def registered_databases(name):
    """The databases registered with exactly this user name."""
    from databases.models import Databases
    if not isinstance(name, str) or not name:
        return []
    return [database for database in Databases.objects.filter(dbUser=name) if database.dbUser == name]


def account_hosts(cursor, user):
    """The hosts of every account the server has under exactly this user name."""
    cursor.execute('SELECT User, Host FROM mysql.user WHERE User = %s', (user,))
    return [text(row[1]) for row in cursor.fetchall() if text(row[0]) == user]


def drop_account(cursor, user, host):
    cursor.execute('DROP USER IF EXISTS %s@%s', (user, host))


def phpmyadmin_account_is_recorded(account):
    """True when the panel recorded this phpMyAdmin account for its user."""
    from databases.models import GlobalUserDB
    return any(record.username == account for record in GlobalUserDB.objects.filter(username=account))


def prepare_phpmyadmin_account(cursor, account, host, password):
    """Leave the phpMyAdmin account existing with this password and without privileges.

    The grants for the user's databases are added by the caller afterwards, so
    a database the user no longer manages is not carried over.
    """
    if not is_phpmyadmin_account(account):
        raise ValueError('Not a phpMyAdmin account.')
    if host in account_hosts(cursor, account):
        if not phpmyadmin_account_is_recorded(account):
            raise ValueError('The phpMyAdmin account exists without a record of its user.')
        cursor.execute('ALTER USER %s@%s IDENTIFIED BY %s', (account, host, password))
        cursor.execute('REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@%s', (account, host))
    else:
        cursor.execute('CREATE USER %s@%s IDENTIFIED BY %s', (account, host, password))


def holds_database_privileges_only(cursor, user, host):
    """True when the account holds nothing but privileges on named databases."""
    cursor.execute('SHOW GRANTS FOR %s@%s', (user, host))
    lines = [text(row[0]) for row in cursor.fetchall()]
    if not lines:
        return False
    for line in lines:
        if 'WITH GRANT OPTION' in line:
            return False
        if _GLOBAL_USAGE.match(line) is None and _DATABASE_GRANT.match(line) is None:
            return False
    return True


def earlier_phpmyadmin_account_refusal(cursor, user, host):
    """Why the account an earlier release named after a panel user is kept; None when it can go.

    Earlier releases signed a panel user in to phpMyAdmin with an account
    carrying the user's own name. It is removed only while nothing else can be
    meant by that name: not a system account, not a registered database user,
    and holding only what the panel gave such an account.
    """
    if not isinstance(user, str) or is_reserved(user):
        return 'the name belongs to the server'
    if registered_as_database_user(user):
        return 'a database is registered with a user of this name'
    if host not in account_hosts(cursor, user):
        return 'there is no such account'
    if not holds_database_privileges_only(cursor, user, host):
        return 'it holds privileges a phpMyAdmin account was never given'
    return None


def open_remote_access(utilities, passwords, database, user, host, previous_host=None):
    """Give a database user an account at `host` with the password of its local account.

    `passwords` maps each host the user already has an account at to its stored
    password hash. A new account starts with a random password and is removed
    again when it cannot be given the user's own. The account of the remote
    host used before is removed. Returns (1, None) or (0, reason).
    """
    from plogical import randomPassword
    # The server keeps host names in lower case.
    host = host.lower()
    passwords = dict((known.lower(), stored) for known, stored in passwords.items())
    local_hosts = (str(utilities.LOCALHOST).lower(), 'localhost', '127.0.0.1')
    local_hash = None
    for local in local_hosts:
        if passwords.get(local):
            local_hash = passwords[local]
            break
    if local_hash is None:
        return 0, 'The local account of this database user was not found.'

    created = host not in passwords
    if created and utilities.createDatabase(database, user, randomPassword.generate_pass(32), 0, host) != 1:
        _drop(utilities, user, host)
        return 0, 'The remote account could not be created.'
    if utilities.changePassword(user, local_hash, 1, host) != 1:
        if created:
            _drop(utilities, user, host)
        return 0, 'The remote account could not be given the password of this database user.'
    previous_host = previous_host.lower() if isinstance(previous_host, str) else None
    if previous_host and previous_host != host and previous_host not in local_hosts and previous_host in passwords:
        _drop(utilities, user, previous_host)
    return 1, None


def _drop(utilities, user, host):
    connection, cursor = utilities.setupConnection()
    if connection == 0:
        return 0
    try:
        drop_account(cursor, user, host)
        return 1
    except Exception:
        return 0
    finally:
        connection.close()
