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

from plogical.databaseGrants import pattern_matches, text
from plogical.securityUtils import is_safe_sql_identifier

PASSWORD_FILE = '/etc/cyberpanel/mysqlPassword'

PHPMYADMIN_PREFIX = 'cp-pma-'
_PHPMYADMIN_ACCOUNT = re.compile(r'cp-pma-[1-9][0-9]{0,17}')

# What an imported database is registered with when it has no usable user of
# its own. It is not a valid account name, so nothing can be done with it.
NO_DATABASE_USER = '-'

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


def may_be_database_user(name):
    """True when a customer's database user may have this name on this server."""
    return account_refusal(name) is None


def may_register_user(name, website_id):
    """True when a database of this website may be registered with a user of this name.

    The name must be one a customer's database user may have, and no database
    of another website may be registered with it, in any case.
    """
    from databases.models import Databases, DatabasesUsers
    if not may_be_database_user(name):
        return False
    lowered = name.lower()
    for database in Databases.objects.filter(dbUser__iexact=name):
        if database.dbUser.lower() == lowered and database.website_id != website_id:
            return False
    for additional in DatabasesUsers.objects.filter(username__iexact=name).select_related('owner'):
        if additional.username.lower() == lowered and additional.owner.website_id != website_id:
            return False
    return True


def has_no_usable_user(name):
    """True for the mark of a database without a user and for a registration under an account of the server."""
    return name == NO_DATABASE_USER or is_reserved(name)


def backed_up_accounts(accounts, registered_user):
    """Of the (user, host) accounts granted a database, those a backup records for it.

    The account phpMyAdmin signs a panel user in with is granted every
    database the user manages and is built again on the user's next visit. It
    is not an account of the database, and neither is an account of the
    server. Earlier releases named that account after the panel user: such a
    name is left out as well, unless the database itself is registered with it.

    The registered user comes first, at each of its hosts: a restore registers
    the database with the first user listed.
    """
    from databases.models import GlobalUserDB
    recorded = set(GlobalUserDB.objects.values_list('username', flat=True))
    kept = [(user, host) for user, host in accounts
            if not is_reserved(user) and (user == registered_user or user not in recorded)]
    return ([account for account in kept if account[0] == registered_user]
            + [account for account in kept if account[0] != registered_user])


def restored_database_user(listed):
    """The user a restored database is registered with, out of the users its backup lists; None when there is none.

    Backups of earlier releases list every account that held a grant, in the
    order of the database server, so a phpMyAdmin account or an account named
    after a panel user can come first. The first user a customer's database
    user may be called is taken. When no listed user may, the first that is
    not an account of the server is returned, and creating the database with
    it says why it is refused.
    """
    names = []
    for name in listed:
        if isinstance(name, str) and not is_reserved(name) and name not in names:
            names.append(name)
    for name in names:
        if may_be_database_user(name):
            return name
    return names[0] if names else None


def registrations_needing_review():
    """(database, registered user, website, reason) of each database whose registered user the panel will not act on.

    Earlier releases registered an imported database under `root` when its
    user was not found, and let a database user carry the name of a panel
    user. Changing the password or the remote access of such a user is
    refused; an administrator has to give the database a user of its own.
    """
    from databases.models import Databases, GlobalUserDB
    from loginSystem.models import Administrator
    panel_names = set(name.lower() for name in Administrator.objects.values_list('userName', flat=True))
    panel_names.update(name.lower() for name in GlobalUserDB.objects.values_list('username', flat=True))
    found = []
    for database in Databases.objects.all().select_related('website'):
        user = database.dbUser
        if user == NO_DATABASE_USER:
            continue
        if is_reserved(user):
            found.append((database.dbName, user, database.website.domain, 'an account of the server'))
        elif user.lower() in panel_names:
            found.append((database.dbName, user, database.website.domain, 'the name of a panel user'))
    return found


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


_DUMP_GRANT = re.compile(
    r"GRANT (?!USAGE )[A-Z ,]+ ON `((?:[^`]|``)+)`\.\* TO ['`]([^'`]+)['`]@['`]localhost['`]")


def _has_wildcard(stored, wildcard):
    escaped = False
    for char in stored:
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == wildcard:
            return True
    return False


def users_granted_in_dump(lines, database):
    """The users a control-panel dump grants privileges on exactly this database at localhost, in order."""
    users = []
    for line in lines:
        found = _DUMP_GRANT.match(line.strip())
        if found is None:
            continue
        granted = found.group(1).replace('``', '`')
        # A grant on every database of a prefix names no database in particular.
        if _has_wildcard(granted, '%') or not pattern_matches(granted, database):
            continue
        if found.group(2) not in users:
            users.append(found.group(2))
    return users


def imported_database_user(cursor, candidate, website):
    """The user to register for a database imported from another control panel.

    The name comes from the archive. It is registered only when it is a name a
    customer could have created here, and when no account or registration
    outside this website already has it; otherwise the database is registered
    without a user.
    """
    from databases.models import Databases
    try:
        if account_refusal(candidate) is not None or len(candidate) > 50:
            return NO_DATABASE_USER
        registered = list(Databases.objects.filter(dbUser=candidate))
        if any(database.website_id != website.pk or database.dbUser != candidate for database in registered):
            return NO_DATABASE_USER
        if not registered and account_hosts(cursor, candidate):
            return NO_DATABASE_USER
        return candidate
    except Exception:
        return NO_DATABASE_USER


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
    local_hosts = (_panel_host(utilities), 'localhost', '127.0.0.1')
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


def _panel_host(utilities):
    """The host the panel's own accounts are made at, in lower case.

    With the database server on another machine that is this machine's
    address, which is known once a connection was made in this process.
    """
    try:
        connection, cursor = utilities.setupConnection()
        if connection != 0:
            connection.close()
    except Exception:
        pass
    return str(utilities.LOCALHOST).lower()


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
