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


def registered_as_database_user(name):
    """True when a database is registered with a user of this name in any case."""
    from databases.models import Databases, DatabasesUsers
    return (_exists_ignoring_case(Databases, 'dbUser', name)
            or _exists_ignoring_case(DatabasesUsers, 'username', name))


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
