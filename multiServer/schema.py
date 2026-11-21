"""The Multi-Server Manager tables.

They are created here with plain SQL, the way the panel creates its other late
tables, so one set of statements serves a new installation and an upgrade and
Django never alters them (the models are unmanaged). Replay protection and the
single use of pairing codes rest on the unique indexes declared below, so a
table that exists without one of them is reported instead of being used.

Times are whole Unix seconds in every table: they are compared with signed
timestamps and must not depend on a time zone setting.
"""
import collections

Table = collections.namedtuple('Table', 'name columns primary unique indexes foreign')

# Compared by code point, never by language rules: identifiers, hashes and
# nonces are equal only when identical (trailing spaces aside, which no stored
# value has). No unique key is longer than 64 characters, far below every
# InnoDB key limit.
SUFFIX = ' ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin'

LINK_ID = 'varchar(32) NOT NULL'
HASH = 'varchar(64) NOT NULL'
TIME = 'bigint NOT NULL'
LATER = 'bigint DEFAULT NULL'
COUNTER = 'bigint NOT NULL'

TABLES = (
    # Controller: one row per managed server. Address, keys and certificate pin
    # live only inside the sealed record.
    Table('ms_nodes', (
        ('link_id', LINK_ID),
        ('label', 'varchar(64) NOT NULL'),
        ('status', "varchar(16) NOT NULL DEFAULT 'pending'"),
        ('sealed', 'varchar(2048) NOT NULL'),
        ('panel_version', "varchar(32) NOT NULL DEFAULT ''"),
        ('created_at', TIME),
        ('updated_at', TIME),
        ('last_seen_at', LATER),
        ('last_error', "varchar(255) NOT NULL DEFAULT ''"),
        ('last_error_at', LATER),
    ), ('link_id',), (), (), ()),
    # Controller: the last validated inventory of each managed server.
    Table('ms_inventory_cache', (
        ('link_id', LINK_ID),
        ('snapshot', 'mediumtext NOT NULL'),
        ('fetched_at', LATER),
        ('error', "varchar(255) NOT NULL DEFAULT ''"),
        ('error_at', LATER),
    ), ('link_id',), (), (), (('ms_inventory_cache_link_fk', 'link_id', 'ms_nodes', 'link_id'),)),
    # Controller: capabilities that let one signed-in administrator's framed
    # view reach one managed server. Only the hash of a capability is kept.
    Table('ms_caps', (
        ('token_hash', HASH),
        ('link_id', LINK_ID),
        ('admin_id', 'int NOT NULL'),
        ('session_hash', HASH),
        ('created_at', TIME),
        ('expires_at', TIME),
    ), ('token_hash',), (), (('ms_caps_link', ('link_id',)), ('ms_caps_session', ('session_hash',)),
                             ('ms_caps_expiry', ('expires_at',))),
        (('ms_caps_link_fk', 'link_id', 'ms_nodes', 'link_id'),)),
    # Controller: the last licence answer, shared by every worker process.
    Table('ms_entitlement', (
        ('id', 'smallint NOT NULL'),
        ('server_ip', 'varchar(45) NOT NULL'),
        ('granted', 'tinyint(1) NOT NULL DEFAULT 0'),
        ('answered_at', 'bigint NOT NULL DEFAULT 0'),
        ('checked_at', 'bigint NOT NULL DEFAULT 0'),
    ), ('id',), (), (), ()),
    # Managed server: one row per controller allowed to manage it. Holds the
    # controller's public key only.
    Table('ms_links', (
        ('link_id', LINK_ID),
        ('controller_key', HASH),
        ('pairing_key', HASH),
        ('allowed_ips', 'varchar(1024) NOT NULL'),
        ('admin_id', 'int NOT NULL'),
        ('status', "varchar(16) NOT NULL DEFAULT 'pending'"),
        ('generation', COUNTER),
        ('created_at', TIME),
        ('updated_at', TIME),
        ('activated_at', LATER),
        ('expires_at', TIME),
        ('last_request_at', 'bigint NOT NULL DEFAULT 0'),
        ('failures', 'smallint NOT NULL DEFAULT 0'),
    ), ('link_id',), (('ms_links_pairing', ('pairing_key',)),), (('ms_links_status', ('status',)),), ()),
    # Managed server: pairing codes that are still open. The code itself is
    # never stored, only the public key derived from its seed.
    Table('ms_pairing_codes', (
        ('public_key', HASH),
        ('controller_ip', 'varchar(45) NOT NULL'),
        ('admin_id', 'int NOT NULL'),
        ('created_at', TIME),
        ('expires_at', TIME),
        ('failures', 'smallint NOT NULL DEFAULT 0'),
        ('consumed', 'tinyint(1) NOT NULL DEFAULT 0'),
    ), ('public_key',), (), (('ms_pairing_codes_expiry', ('expires_at',)),), ()),
    # Managed server: every nonce accepted on a link, until its time window
    # has passed.
    Table('ms_nonces', (
        ('id', 'bigint NOT NULL AUTO_INCREMENT'),
        ('link_id', LINK_ID),
        ('nonce', 'varchar(32) NOT NULL'),
        ('seen_at', TIME),
    ), ('id',), (('ms_nonces_link_nonce', ('link_id', 'nonce')),), (('ms_nonces_seen', ('seen_at',)),),
        (('ms_nonces_link_fk', 'link_id', 'ms_links', 'link_id'),)),
    # Managed server: one-click login tickets, by hash.
    Table('ms_sso_tickets', (
        ('ticket_hash', HASH),
        ('link_id', LINK_ID),
        ('admin_id', 'int NOT NULL'),
        ('actor', 'varchar(50) NOT NULL'),
        ('landing', 'varchar(255) NOT NULL'),
        ('created_at', TIME),
        ('expires_at', TIME),
        ('used', 'tinyint(1) NOT NULL DEFAULT 0'),
    ), ('ticket_hash',), (), (('ms_sso_tickets_link', ('link_id',)), ('ms_sso_tickets_expiry', ('expires_at',))),
        (('ms_sso_tickets_link_fk', 'link_id', 'ms_links', 'link_id'),)),
    # Managed server: panel sessions opened through a link, so pausing or
    # revoking the link can end them.
    Table('ms_sessions', (
        ('session_key', 'varchar(40) NOT NULL'),
        ('link_id', LINK_ID),
        ('created_at', TIME),
    ), ('session_key',), (), (('ms_sessions_link', ('link_id',)),),
        (('ms_sessions_link_fk', 'link_id', 'ms_links', 'link_id'),)),
    # Both: the audit trail. No column can hold a request or a reply.
    Table('ms_audit', (
        ('id', 'bigint NOT NULL AUTO_INCREMENT'),
        ('at', TIME),
        ('event', 'varchar(32) NOT NULL'),
        ('outcome', 'varchar(8) NOT NULL'),
        ('reason', "varchar(32) NOT NULL DEFAULT ''"),
        ('link_id', "varchar(32) NOT NULL DEFAULT ''"),
        ('actor', "varchar(50) NOT NULL DEFAULT ''"),
        ('source_ip', "varchar(45) NOT NULL DEFAULT ''"),
        ('method', "varchar(8) NOT NULL DEFAULT ''"),
        ('path', "varchar(255) NOT NULL DEFAULT ''"),
        ('status', 'smallint DEFAULT NULL'),
        ('size', LATER),
        ('dropped', 'smallint NOT NULL DEFAULT 0'),
    ), ('id',), (), (('ms_audit_at', ('at',)), ('ms_audit_link', ('link_id',))), ()),
)


def create_statement(table):
    """The CREATE TABLE IF NOT EXISTS statement for one table."""
    parts = ['`%s` %s' % column for column in table.columns]
    parts.append('PRIMARY KEY (%s)' % _columns(table.primary))
    parts.extend('UNIQUE KEY `%s` (%s)' % (name, _columns(columns)) for name, columns in table.unique)
    parts.extend('KEY `%s` (%s)' % (name, _columns(columns)) for name, columns in table.indexes)
    parts.extend('CONSTRAINT `%s` FOREIGN KEY (`%s`) REFERENCES `%s` (`%s`) ON DELETE CASCADE' % constraint
                 for constraint in table.foreign)
    return 'CREATE TABLE IF NOT EXISTS `%s` (%s)%s' % (table.name, ', '.join(parts), SUFFIX)


def required_unique(table):
    """The column lists that must each be exactly one unique index of the table."""
    return (tuple(table.primary),) + tuple(tuple(columns) for _, columns in table.unique)


def problems(cursor):
    """What is wrong with the tables as they exist now; an empty list when they are usable."""
    names = ', '.join("'%s'" % table.name for table in TABLES)
    cursor.execute('SELECT TABLE_NAME, COLUMN_NAME FROM information_schema.COLUMNS '
                   'WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME IN (%s)' % names)
    present = collections.defaultdict(set)
    for table_name, column in cursor.fetchall():
        present[_text(table_name)].add(_text(column))
    cursor.execute('SELECT TABLE_NAME, INDEX_NAME, SEQ_IN_INDEX, COLUMN_NAME, SUB_PART '
                   'FROM information_schema.STATISTICS WHERE TABLE_SCHEMA = DATABASE() '
                   'AND NON_UNIQUE = 0 AND TABLE_NAME IN (%s)' % names)
    indexes = collections.defaultdict(dict)
    for table_name, index, position, column, prefix in cursor.fetchall():
        # An index on the first characters of a column is not the index required.
        indexes[(_text(table_name), _text(index))][int(position)] = None if prefix is not None else _text(column)
    unique = collections.defaultdict(set)
    for (table_name, _), members in indexes.items():
        unique[table_name].add(tuple(members[position] for position in sorted(members)))
    found = []
    for table in TABLES:
        if table.name not in present:
            found.append('%s: the table is missing' % table.name)
            continue
        for column, _ in table.columns:
            if column not in present[table.name]:
                found.append('%s: column %s is missing' % (table.name, column))
        for columns in required_unique(table):
            if columns not in unique[table.name]:
                found.append('%s: no unique index on exactly (%s)' % (table.name, ', '.join(columns)))
    return found


def ensure_tables(connection, cursor):
    """Create the missing tables, then refuse to go on unless every table is usable."""
    for table in TABLES:
        try:
            cursor.execute(create_statement(table))
        except Exception as error:
            raise RuntimeError('Multi-Server Manager table %s could not be created: %s'
                               % (table.name, error)) from error
    connection.commit()
    found = problems(cursor)
    if found:
        raise RuntimeError('Multi-Server Manager tables are not usable: ' + '; '.join(found))


_READY = False


def ready():
    """Whether the tables exist with their unique indexes; never raises, never creates."""
    global _READY
    if _READY:
        return True
    try:
        from django.db import connection
        with connection.cursor() as cursor:
            usable = not problems(cursor)
    except Exception:
        return False
    # Only success is remembered: tables created by an upgrade are noticed by
    # running workers, and tables do not lose an index while the panel runs.
    _READY = usable
    return usable


def _columns(names):
    return ', '.join('`%s`' % name for name in names)


def _text(value):
    return value.decode('utf-8') if isinstance(value, bytes) else value
