"""Database-level grants that name one database and nothing else.

MariaDB and MySQL read `_` and `%` in the database part of a GRANT or REVOKE
as wildcards, between backticks as well: a grant on `shop_db` also covers a
database called `shopXdb`. A backslash before the character makes it literal,
and that escaped form is what the server then keeps in mysql.db. MySQL 8 with
partial_revokes enabled reads the name literally instead, so nothing may be
escaped there.

Statements are built by the callers with mysqlUtilities.quoteIdentifier around
the name returned here; reading mysql.db goes through accounts_granted so that
both stored forms are found.
"""


def text(value):
    """A value read from a system table, as str."""
    if isinstance(value, (bytes, bytearray)):
        return bytes(value).decode('utf-8', 'surrogateescape')
    return value


def escape_grant_name(name):
    """The database name with every wildcard character made literal."""
    return name.replace('\\', '\\\\').replace('_', '\\_').replace('%', '\\%')


def names_are_literal(cursor):
    """True where the server reads the database name of a grant literally.

    MariaDB and older MySQL have no such variable and return no row.
    """
    cursor.execute("SHOW VARIABLES LIKE 'partial_revokes'")
    rows = cursor.fetchall()
    return bool(rows and len(rows[0]) > 1 and str(text(rows[0][1])).upper() in ('ON', '1'))


def grant_name(cursor, name):
    """What to write as the database of a GRANT or REVOKE so that it means `name` alone."""
    if not isinstance(name, str) or not name:
        raise ValueError('A grant needs a database name.')
    if names_are_literal(cursor):
        return name
    return escape_grant_name(name)


def stored_names(name):
    """Every value mysql.db may hold for a grant on exactly this database.

    The plain name is what earlier releases wrote (a pattern, where the name
    has wildcard characters). The escaped forms are what this release and
    phpMyAdmin write.
    """
    forms = [name, escape_grant_name(name), name.replace('_', '\\_')]
    return tuple(sorted(set(forms), key=forms.index))


def is_pattern(stored):
    """True when a stored database value can match more than one database name."""
    escaped = False
    for char in stored:
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char in '_%':
            return True
    return False


def pattern_matches(stored, database):
    """True when the stored database value of a grant covers this database name."""
    # Positions in `database` that the pattern read so far can end at.
    ends = {0}
    index = 0
    while index < len(stored) and ends:
        char = stored[index]
        if char == '%':
            ends = set(range(min(ends), len(database) + 1))
        elif char == '_':
            ends = {end + 1 for end in ends if end < len(database)}
        else:
            if char == '\\' and index + 1 < len(stored):
                index += 1
                char = stored[index]
            ends = {end + 1 for end in ends if database[end:end + 1] == char}
        index += 1
    return len(database) in ends


def accounts_granted(cursor, name):
    """(user, host) of each account with a grant stored for exactly this database, in server order."""
    forms = stored_names(name)
    cursor.execute('SELECT User, Host FROM mysql.db WHERE Db IN (%s)' % ', '.join(['%s'] * len(forms)), forms)
    accounts = []
    for row in cursor.fetchall():
        account = (text(row[0]), text(row[1]))
        if account not in accounts:
            accounts.append(account)
    return accounts


def account_is_granted(cursor, name, user, host):
    """True when this account has a grant stored for exactly this database."""
    cursor.execute('SELECT Db FROM mysql.db WHERE User = %s AND Host = %s', (user, host))
    held = set(text(row[0]) for row in cursor.fetchall())
    return bool(held.intersection(stored_names(name)))
