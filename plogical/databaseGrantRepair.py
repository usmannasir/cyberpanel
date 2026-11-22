"""Give the grants made by earlier releases the exact form, during every upgrade.

Earlier releases granted a database user its database by the plain name. In
a grant `_` and `%` are wildcards (see databaseGrants), so the user of
`shop_db` could also use a database called `shopXdb`. For every database
registered in the panel, each account that holds a grant under the plain name
(the database's own user at every host, the phpMyAdmin account of a panel
user, an account added by hand) first gets the same privileges under the
escaped name and only then loses the plain grant, so nobody is without access
in between. A wildcard grant that is not the name of a registered database
was made by someone else: it is reported and left as it is.

Nothing here keeps state: a grant that is already exact is not touched, so the
repair can run at every upgrade and a run that was interrupted is finished by
the next one. It works on the server the panel creates its databases on, local
or remote, with the panel's administrative account; where that account may not
read or change grants the failure is reported and nothing else is affected.
"""
import re

from plogical import databaseGrants

# One line of SHOW GRANTS for a whole database, e.g.
#   GRANT ALL PRIVILEGES ON `shop_db`.* TO `shop_user`@`localhost` WITH GRANT OPTION
GRANT_LINE = re.compile(
    r'GRANT (?P<privileges>[A-Z][A-Z ,]*) ON `(?P<database>(?:[^`]|``)+)`\.\* TO .*?(?P<option> WITH GRANT OPTION)?')

COVERED_SHOWN = 12

# Schemas of the database server itself. A grant on one of them is the server's
# own (MySQL 8 gives `mysql.session` one on `performance_schema`), not a
# pattern somebody wrote, and is not reported at every upgrade.
SERVER_SCHEMAS = frozenset(('performance_schema', 'information_schema', 'mysql', 'sys'))


class RepairError(Exception):
    pass


def quote(name):
    """The name between backticks, as mysqlUtilities.quoteIdentifier writes it."""
    return '`' + str(name).replace('`', '``') + '`'


def _rows(cursor, query, args=None):
    cursor.execute(query, args)
    return [tuple(databaseGrants.text(value) for value in row) for row in cursor.fetchall()]


def _shown_grant(cursor, stored, user, host):
    """(privileges, with grant option) as the server itself writes this account's grant on `stored`."""
    holder, values = databaseGrants.holder(user, host)
    for (line,) in _rows(cursor, 'SHOW GRANTS FOR ' + holder, values):
        match = GRANT_LINE.fullmatch(line)
        if match and match.group('database').replace('``', '`') == stored:
            return match.group('privileges'), bool(match.group('option'))
    raise RepairError('the server does not show this grant')


def _held(cursor, stored, user, host):
    return bool(_rows(cursor, 'SELECT 1 FROM mysql.db WHERE Db = %s AND User = %s AND Host = %s',
                      (stored, user, host)))


def _move(cursor, stored, user, host):
    privileges, option = _shown_grant(cursor, stored, user, host)
    escaped = databaseGrants.escape_grant_name(stored)
    exact, plain = quote(escaped), quote(stored)
    holder, values = databaseGrants.holder(user, host)
    if _held(cursor, escaped, user, host):
        # The account already holds an exact grant, and the server uses that
        # one alone for this database. It is what the account keeps: the
        # privileges of the plain grant are not added to it.
        kept, kept_option = _shown_grant(cursor, escaped, user, host)
    else:
        kept, kept_option = privileges, option
        cursor.execute('GRANT %s ON %s.* TO %s%s' % (kept, exact, holder, ' WITH GRANT OPTION' if kept_option else ''),
                       values)
        if not _held(cursor, escaped, user, host):
            raise RepairError('the exact grant was not stored')
    cursor.execute('REVOKE %s ON %s.* FROM %s' % (privileges, plain, holder), values)
    if option:
        cursor.execute('REVOKE GRANT OPTION ON %s.* FROM %s' % (plain, holder), values)
    if _held(cursor, stored, user, host):
        raise RepairError('the plain grant is still there after the revoke')
    if not _held(cursor, escaped, user, host):
        # A server that read the revoke as a pattern took the exact grant with it: it is given again.
        cursor.execute('GRANT %s ON %s.* TO %s%s' % (kept, exact, holder, ' WITH GRANT OPTION' if kept_option else ''),
                       values)
        if not _held(cursor, escaped, user, host):
            raise RepairError('the exact grant did not stay after the revoke')


def repair(cursor, registered):
    """Move the plain grants of registered databases to the exact form; list other wildcard grants.

    `registered` holds the database names known to the panel.
    """
    result = {'literal': False, 'moved': [], 'failed': [], 'patterns': [], 'too_long': []}
    if databaseGrants.names_are_literal(cursor):
        # This server reads the name of a grant literally: nothing was ever a wildcard.
        result['literal'] = True
        return result
    # The grants are read from what the server writes: it has to write them one way.
    databaseGrants.plain_session(cursor)
    # A server that folds database names to lower case stores them that way in its grants.
    folds = _rows(cursor, 'SELECT @@lower_case_table_names')[0][0] not in (0, '0')
    known = set(name.lower() if folds else name for name in registered)
    schemas = None
    for stored, user, host in _rows(cursor, 'SELECT Db, User, Host FROM mysql.db ORDER BY Db, User, Host'):
        if not databaseGrants.is_pattern(stored):
            continue
        if stored.lower() in SERVER_SCHEMAS and stored not in known:
            continue
        if stored in known and not databaseGrants.exact_name_fits(stored):
            # The server accepts no exact grant for this name; said once per database.
            if stored not in result['too_long']:
                result['too_long'].append(stored)
            continue
        if stored in known:
            try:
                _move(cursor, stored, user, host)
                result['moved'].append([stored, user, host])
            except Exception as error:
                result['failed'].append([stored, user, host, type(error).__name__ + ': ' + str(error)])
            continue
        if schemas is None:
            schemas = [row[0] for row in _rows(cursor, 'SELECT SCHEMA_NAME FROM information_schema.SCHEMATA')]
        covered = sorted(name for name in known.union(schemas) if databaseGrants.pattern_matches(stored, name))
        result['patterns'].append([stored, user, host, covered])
    return result


def describe(result, log):
    """Tell the administrator what was done and what needs a look."""
    if result['literal']:
        log('Database grants: this server reads database names in grants literally; nothing to change.')
        return
    if result['moved']:
        log('Database grants: %d grant(s) of earlier releases now name their own database only.'
            % len(result['moved']))
    for stored, user, host, reason in result['failed']:
        log('WARNING: The grant on `%s` for %s@%s still covers similarly named databases (%s).'
            % (stored, user or "''", host, reason))
    for stored in result.get('too_long', ()):
        log('NOTICE: The grants on `%s` were left as they are. The name of this database is too long for a grant '
            'that covers it alone: each `_` and `%%` counts twice and the server accepts %d characters. Its users '
            'can also reach databases whose names differ only where this name has `_` or `%%`.'
            % (stored, databaseGrants.NAME_LENGTH))
    for stored, user, host, covered in result['patterns']:
        names = ', '.join(covered[:COVERED_SHOWN]) or 'no database at the moment'
        if len(covered) > COVERED_SHOWN:
            names += ' and %d more' % (len(covered) - COVERED_SHOWN)
        log('NOTICE: The grant on `%s` for %s@%s is a pattern that is not the name of a database made in the '
            'panel. It was left as it is. It covers: %s.' % (stored, user or "''", host, names))


def panel_database():
    """The name of the panel's own database, where it registers the databases it makes."""
    try:
        from CyberCP import settings
        return str(settings.DATABASES['default']['NAME'])
    except Exception:
        return 'cyberpanel'


def registered_databases(cursor, database):
    """Names of the databases made in the panel, read with the administrative connection."""
    return [row[0] for row in _rows(cursor, 'SELECT dbName FROM %s.databases_databases' % quote(database))]


def run(connect=None, log=print):
    """Entry point for the upgrader; `connect` returns (connection, cursor) or (0, 0)."""
    if connect is None:
        from plogical.mysqlUtilities import mysqlUtilities
        connect = mysqlUtilities.setupConnection

    connection, cursor = connect()
    if connection == 0:
        log('WARNING: Database grants were not checked: no connection to the database server.')
        return 'no connection'
    try:
        result = repair(cursor, registered_databases(cursor, panel_database()))
    finally:
        connection.close()
    describe(result, log)
    if result['failed']:
        return 'incomplete'
    if result['moved']:
        return 'repaired'
    return 'nothing to change'
