"""Load a database dump into one database with an account that can reach nothing else.

A dump is text somebody else wrote: a customer's backup repository, an
uploaded archive, a cPanel account. It is therefore never run with the
panel's administrative database account. For each import a database account is
made that holds the grant on the target database alone (the exact grant of
databaseGrants), its credentials go into a private option file, and the
account is dropped when the import ends, whatever the outcome. A dump that
addresses another database is refused by the database server.

The command-line client is told to treat its input as data (`--binary-mode`,
and `--sandbox` where the client has it) and never to send a local file to the
server (`--local-infile=0`), so nothing in the dump can make the client run a
program or read a file. When the caller is root the client runs as an account
without privileges.

Views, triggers, routines and events carry a DEFINER. Only an administrative
account may name somebody else there, so the clause is left out while the dump
passes through and the objects are made in the name of the import account.
After the import they are handed to the database's own registered account,
which is the account the website uses. Where that cannot be done the import
account is not dropped, because what it made would stop working: it is locked,
keeps its one grant, and the panel log names the database.
"""
import os
import pwd
import re
import stat
import subprocess
import tempfile
import time

from plogical import CyberCPLogFileWriter as logging
from plogical import databaseGrants
from plogical import randomPassword

CLIENT = 'mysql'
ACCOUNT_PREFIX = 'cpimp_'

# What import_dump returns.
FAILED = 0
LOADED = 1
# All of the dump is loaded, but views, triggers, routines or events could not
# be handed to the database's own account; the locked import account owns them.
LOADED_OBJECTS_KEPT = 2

# What the panel grants a database user on a managed server whose
# administrative account may not grant every privilege (mysqlUtilities.createDatabase).
LIMITED_PRIVILEGES = 'INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE'
STALE_AFTER = 24 * 3600
UNPRIVILEGED = ('nobody',)
CHUNK = 65536

HOST = re.compile(r'[A-Za-z0-9.:_-]{1,255}')
ACCOUNT = re.compile(r'cpimp_([0-9a-f]{8})_[a-z0-9]{10}')

# The DEFINER clause where mysqldump, mariadb-dump and phpMyAdmin put it: at
# the start of a line, after nothing but keywords and version comments.
DEFINER = re.compile(
    br'^(?P<head>(?:/\*![0-9]+\s*)?(?:CREATE\b[A-Za-z0-9_=!/* \t]*?)?)'
    br'DEFINER\s*=\s*(?:`(?:[^`\n]|``)*`|\'[^\'\n]*\'|[A-Za-z0-9_$.-]+)'
    br'(?:\s*@\s*(?:`[^`\n]*`|\'[^\'\n]*\'|[A-Za-z0-9_.%:-]+)|\s*\(\s*\))?[ \t]?',
    re.IGNORECASE)

_options = {}


class ImportRefused(Exception):
    pass


def quote(name):
    """The name between backticks, as mysqlUtilities.quoteIdentifier writes it."""
    return '`' + str(name).replace('`', '``') + '`'


def _rows(cursor, query, args=None):
    cursor.execute(query, args)
    return [tuple(databaseGrants.text(value) for value in row) for row in cursor.fetchall()]


def client_options(client=CLIENT):
    """The options that make this client treat a dump as data, never as commands of its own."""
    if client not in _options:
        described = subprocess.check_output([client, '--no-defaults', '--help'], stderr=subprocess.DEVNULL)
        described = described.decode('utf-8', 'replace')
        if not re.search(r'^\s*--binary-mode\b', described, re.MULTILINE):
            raise ImportRefused('The installed database client cannot be told to ignore client commands in a dump.')
        # A statement in the dump must not make the client send a file of this machine either.
        options = ['--binary-mode', '--local-infile=0']
        if re.search(r'^\s*--sandbox\b', described, re.MULTILINE):
            options.append('--sandbox')
        _options[client] = options
    return list(_options[client])


def drop_account(cursor, user, host):
    cursor.execute('DROP USER IF EXISTS %s@%s', (user, host))


def owns_objects(cursor, account):
    """True when a view, trigger, routine or event of any database has this account as its definer."""
    definer = '%s@%s' % account
    for table in ('VIEWS', 'TRIGGERS', 'ROUTINES', 'EVENTS'):
        if _rows(cursor, 'SELECT 1 FROM information_schema.%s WHERE DEFINER = %%s LIMIT 1' % table, (definer,)):
            return True
    return False


def lock_account(cursor, user, host):
    """Close the account for sign-in; what it owns keeps working. Returns how it was closed.

    MariaDB from 10.4.2 and MySQL from 5.7.6 can lock an account. An older
    server cannot: there the account gets a new password nobody knows.
    """
    try:
        cursor.execute('ALTER USER %s@%s ACCOUNT LOCK', (user, host))
        return 'locked'
    except BaseException:
        cursor.execute('ALTER USER %s@%s IDENTIFIED BY %s', (user, host, randomPassword.generate_pass(28) + '-aZ9'))
        return 'given a new password nobody knows'


def drop_stale_accounts(cursor, now=None):
    """Remove import accounts that a stopped import left behind a day or longer ago.

    An account that still owns views, triggers, routines or events is never
    removed: they would stop working. It is locked instead.
    """
    now = time.time() if now is None else now
    for user, host in _rows(cursor, 'SELECT User, Host FROM mysql.user WHERE User LIKE %s', ('cpimp\\_%',)):
        match = ACCOUNT.fullmatch(user)
        if match and now - int(match.group(1), 16) > STALE_AFTER:
            if owns_objects(cursor, (user, host)):
                lock_account(cursor, user, host)
            else:
                drop_account(cursor, user, host)


def create_account(cursor, database, native_password=False, now=None):
    """Make the account of one import; returns (user, host, password).

    The host is the one the database server sees this machine as, so the
    account is of use from here only.
    """
    host = _rows(cursor, "SELECT SUBSTRING_INDEX(USER(), '@', -1)")[0][0]
    if not isinstance(host, str) or not HOST.fullmatch(host):
        raise ImportRefused('Cannot tell which host the database server sees this machine as.')
    target = quote(databaseGrants.grant_name(cursor, database))
    user = '%s%08x_%s' % (ACCOUNT_PREFIX, int(time.time() if now is None else now),
                          randomPassword.generate_pass(10).lower())
    # Long and random; the ending satisfies a server that asks for every kind of character.
    password = randomPassword.generate_pass(28) + '-aZ9'
    if native_password:
        cursor.execute('CREATE USER %s@%s IDENTIFIED WITH mysql_native_password BY %s', (user, host, password))
    else:
        cursor.execute('CREATE USER %s@%s IDENTIFIED BY %s', (user, host, password))
    try:
        try:
            cursor.execute('GRANT ALL PRIVILEGES ON %s.* TO %%s@%%s' % target, (user, host))
        except BaseException:
            # A managed server whose administrative account may not grant every privilege.
            cursor.execute('GRANT %s ON %s.* TO %%s@%%s' % (LIMITED_PRIVILEGES, target), (user, host))
    except BaseException:
        drop_account(cursor, user, host)
        raise
    return user, host, password


def client_identity():
    """(uid, gid) the client runs as when the caller is root; None when the caller is not root."""
    if os.geteuid() != 0:
        return None
    for name in UNPRIVILEGED:
        try:
            entry = pwd.getpwnam(name)
        except KeyError:
            continue
        if entry.pw_uid != 0:
            return entry.pw_uid, entry.pw_gid
    raise ImportRefused('There is no account without privileges to run the database client as.')


def write_defaults(user, password, host, port, identity=None):
    """A private option file for the client; returns (what the client is told to read, descriptor, path).

    The file has no name by the time the client starts: the client inherits
    the open descriptor and reads it as /dev/fd/N, so no other process finds
    the file and nothing is left behind when the import is stopped. `path` is
    None then. Only where the system has no /dev/fd the file keeps its name
    until the import ends.
    """
    descriptor, path = tempfile.mkstemp(prefix='.cpimport-', suffix='.cnf')
    try:
        os.fchmod(descriptor, 0o600)
        if identity is not None:
            os.fchown(descriptor, identity[0], identity[1])
        content = '[client]\nuser=%s\npassword=%s\nhost=%s\nport=%d\n' % (user, password, host, int(port))
        os.write(descriptor, content.encode('ascii'))
        if os.path.isdir('/dev/fd'):
            os.unlink(path)
            return '/dev/fd/%d' % descriptor, descriptor, None
    except BaseException:
        os.close(descriptor)
        try:
            os.unlink(path)
        except OSError:
            pass
        raise
    return path, descriptor, path


def _demote(identity):
    def change():
        os.setgroups([])
        os.setgid(identity[1])
        os.setuid(identity[0])
        os.umask(0o077)
    return change


class DefinerFilter(object):
    """Passes a dump on to `sink` without the DEFINER clause of the statements that create objects.

    Only the start of a line is looked at, and only when the line starts like
    such a statement, so table data passes through as it is and in pieces of
    any size.
    """

    def __init__(self, sink):
        self.sink = sink
        self.start = b''        # a line that has begun and may still be a statement of interest
        self.passing = False    # the rest of the current line goes through untouched

    @staticmethod
    def _of_interest(start):
        return start[:1] in (b'C', b'c', b'/')

    @staticmethod
    def _clean(line):
        if DefinerFilter._of_interest(line):
            return DEFINER.sub(lambda match: match.group('head'), line, 1)
        return line

    def write(self, data):
        out = []
        position = 0
        if not self.start and not self.passing:
            # Whole lines without the word go through in one piece.
            last = data.rfind(b'\n') + 1
            if last and b'DEFINER' not in data[:last].upper():
                out.append(data[:last])
                position = last
        while position < len(data):
            end = data.find(b'\n', position)
            piece = data[position:] if end == -1 else data[position:end + 1]
            position += len(piece)
            if self.passing:
                out.append(piece)
                self.passing = end == -1
            elif end != -1:
                out.append(self._clean(self.start + piece))
                self.start = b''
            else:
                self.start += piece
                if len(self.start) > CHUNK or not self._of_interest(self.start):
                    out.append(self._clean(self.start))
                    self.start = b''
                    self.passing = True
        if out:
            self.sink.write(b''.join(out))

    def close(self):
        if self.start:
            self.sink.write(self._clean(self.start))
            self.start = b''


def copy(source, sink):
    """Feed a readable binary stream into the import."""
    while True:
        data = source.read(CHUNK)
        if not data:
            return True
        sink.write(data)


def owner_account(cursor, database, user, preferred=()):
    """(user, host) of the database's registered account that may own the imported objects, or None.

    The account must hold its grant on this database and nothing on the
    server as a whole: objects that run in its name can then do no more than
    the website's own account already can.
    """
    if not isinstance(user, str) or not user:
        return None
    hosts = [row[0] for row in _rows(cursor, 'SELECT Host FROM mysql.user WHERE User = %s', (user,))]
    for host in sorted(hosts, key=lambda host: (host != 'localhost', host not in preferred, host)):
        if not databaseGrants.account_is_granted(cursor, database, user, host):
            continue
        grantee = "'%s'@'%s'" % (user.replace("'", "\\'"), host.replace("'", "\\'"))
        held = _rows(cursor, 'SELECT PRIVILEGE_TYPE FROM information_schema.USER_PRIVILEGES WHERE GRANTEE = %s',
                     (grantee,))
        if all(row[0] == 'USAGE' for row in held):
            return user, host
    return None


def imported_objects(cursor, database, made_by):
    """[(kind, name, extra)] of the objects in the database whose definer is the import account."""
    definer = '%s@%s' % made_by
    found = []
    for (name,) in _rows(cursor, 'SELECT TABLE_NAME FROM information_schema.VIEWS '
                                 'WHERE TABLE_SCHEMA = %s AND DEFINER = %s', (database, definer)):
        found.append(('VIEW', name, None))
    for (name,) in _rows(cursor, 'SELECT TRIGGER_NAME FROM information_schema.TRIGGERS '
                                 'WHERE TRIGGER_SCHEMA = %s AND DEFINER = %s', (database, definer)):
        found.append(('TRIGGER', name, None))
    for kind, name in _rows(cursor, 'SELECT ROUTINE_TYPE, ROUTINE_NAME FROM information_schema.ROUTINES '
                                    'WHERE ROUTINE_SCHEMA = %s AND DEFINER = %s', (database, definer)):
        if kind in ('PROCEDURE', 'FUNCTION'):
            found.append((kind, name, None))
    for name, completion in _rows(cursor, 'SELECT EVENT_NAME, ON_COMPLETION FROM information_schema.EVENTS '
                                          'WHERE EVENT_SCHEMA = %s AND DEFINER = %s', (database, definer)):
        found.append(('EVENT', name, completion))
    return found


def reassign_definers(cursor, database, made_by, owner):
    """Hand the objects the import made to `owner`; returns how many were handed over.

    Each object is written again from the server's own description of it,
    with the owner in place of the import account. The description is read
    with names between backticks, whatever the server is set to; a trigger or
    routine is then made again under the sql_mode it was made with.
    """
    objects = imported_objects(cursor, database, made_by)
    if not objects:
        return 0
    old = 'DEFINER=%s@%s' % (quote(made_by[0]), quote(made_by[1]))
    new = 'DEFINER=%s@%s' % (quote(owner[0]), quote(owner[1]))
    replaces = 'MariaDB' in str(_rows(cursor, 'SELECT VERSION()')[0][0])
    schema = quote(database)
    databaseGrants.plain_session(cursor)
    plain = True
    cursor.execute('USE ' + schema)
    for kind, name, extra in objects:
        target = '%s.%s' % (schema, quote(name))
        if kind == 'EVENT':
            completion = 'ON COMPLETION PRESERVE' if extra == 'PRESERVE' else 'ON COMPLETION NOT PRESERVE'
            cursor.execute('ALTER %s EVENT %s %s' % (new, target, completion))
            continue
        if not plain:
            cursor.execute("SET SESSION sql_mode = ''")
            plain = True
        row = _rows(cursor, 'SHOW CREATE %s %s' % (kind, target))[0]
        original = row[1] if kind == 'VIEW' else row[2]
        if not isinstance(original, str) or not original.startswith('CREATE ') or original.count(old) < 1:
            raise ImportRefused('The %s %s is not described the way it was made.' % (kind.lower(), name))
        if kind != 'VIEW':
            cursor.execute('SET SESSION sql_mode = %s', (row[1],))
            plain = row[1] == ''
        statement = original.replace(old, new, 1)
        if kind == 'VIEW' or replaces:
            cursor.execute('CREATE OR REPLACE ' + statement[len('CREATE '):])
        else:
            cursor.execute('DROP %s %s' % (kind, target))
            try:
                cursor.execute(statement)
            except BaseException:
                # The server took the object and refused it under its new
                # owner: it is put back the way it was.
                cursor.execute(original)
                raise
    return len(objects)


def _note(message):
    logging.CyberCPLogFileWriter.writeToFile(message)


def _administrator(connect):
    if connect is None:
        from plogical.mysqlUtilities import mysqlUtilities
        connect = mysqlUtilities.setupConnection
    connection, cursor = connect()
    if connection == 0:
        raise ImportRefused('No administrative connection to the database server.')
    return connection, cursor


def _native_password():
    from plogical.mysqlUtilities import mysqlUtilities
    return mysqlUtilities.REMOTEHOST.find('ondigitalocean') > -1


def _usable_name(database):
    from plogical.mysqlUtilities import mysqlUtilities
    return mysqlUtilities.usableInCommands(database)


TRUST_SETTING = 'log_bin_trust_function_creators'


def allow_function_creators(cursor):
    """Let the import account make triggers and functions on a server that writes a binary log.

    Such a server refuses them from an account without the SUPER privilege
    unless log_bin_trust_function_creators is on, half-way through a dump.
    The setting is switched on for the time of the import. Returns True when
    it was switched on here and has to be put back.
    """
    try:
        rows = _rows(cursor, 'SELECT @@GLOBAL.log_bin, @@GLOBAL.' + TRUST_SETTING)
    except BaseException:
        return False
    if not rows or str(rows[0][0]).upper() in ('0', 'OFF') or str(rows[0][1]).upper() in ('1', 'ON'):
        return False
    try:
        cursor.execute('SET GLOBAL %s = 1' % TRUST_SETTING)
        return True
    except BaseException as error:
        _note('This server writes a binary log and %s is off; the panel may not switch it on (%s). '
              'A dump with triggers or functions will stop at the first of them.' % (TRUST_SETTING, error))
        return False


def restore_function_creators(cursor):
    try:
        cursor.execute('SET GLOBAL %s = 0' % TRUST_SETTING)
    except BaseException as error:
        _note('%s was switched on for an import and could not be switched off again: %s' % (TRUST_SETTING, error))


def import_dump(database, feed, host='localhost', port=3306, owner=None, connect=None, made=None):
    """Load a dump into `database`.

    Returns LOADED (1) when all of it was loaded, FAILED (0) when it was not,
    and LOADED_OBJECTS_KEPT (2) when all of it was loaded but views, triggers,
    routines or events could not be handed to the database's own account and
    stay with the locked import account.

    `feed(sink)` writes the dump into `sink` and returns a true value when its
    source ended well. `owner` is the user name of the database's registered
    account. `made`, a list, receives (database, (user, host)) of the import
    account when the caller hands the imported objects over itself, later,
    with `settle`; the account lives until then.
    """
    account = None
    path = None
    descriptor = None
    loaded = False
    trusted = False
    try:
        # The name is the last argument of the client: it must not read as an option or a path.
        if not _usable_name(database):
            raise ImportRefused('A database with this name cannot be imported into.')
        options = client_options()
        connection, cursor = _administrator(connect)
        try:
            try:
                drop_stale_accounts(cursor)
            except BaseException as error:
                # Looking for what a stopped import left behind never stops an import.
                _note('Accounts left by earlier imports were not looked for: %s' % error)
            user, account_host, password = create_account(cursor, database, _native_password())
            account = (user, account_host)
            trusted = allow_function_creators(cursor)
        finally:
            connection.close()

        identity = client_identity()
        defaults, descriptor, path = write_defaults(user, password, host, port, identity)
        with tempfile.TemporaryFile() as errors:
            client = subprocess.Popen(
                [CLIENT, '--defaults-file=' + defaults] + options + [database],
                stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=errors, cwd='/',
                env={'PATH': os.environ.get('PATH', '/usr/local/bin:/usr/bin:/bin'), 'LC_ALL': 'C'},
                pass_fds=(descriptor,) if path is None else (),
                preexec_fn=_demote(identity) if identity is not None else None)
            fed = False
            try:
                sink = DefinerFilter(client.stdin)
                fed = feed(sink)
                sink.close()
            except (OSError, ValueError):
                # The client stopped reading: its exit status tells why.
                fed = False
            finally:
                try:
                    client.stdin.close()
                except OSError:
                    pass
                client.wait()
            loaded = bool(fed) and client.returncode == 0
            if not loaded:
                # The client names the error on the last lines it writes.
                errors.seek(max(0, errors.seek(0, os.SEEK_END) - 2000))
                said = [line for line in errors.read().decode('utf-8', 'replace').splitlines()
                        if line.startswith('ERROR')]
                reason = said[-1][:300] if said else 'the dump could not be read to its end'
                if 'ERROR 1419' in reason:
                    reason += (' The server writes a binary log and does not let this account make triggers '
                               'or functions: set %s=1 on the database server and import again.' % TRUST_SETTING)
                _note('Database import into %s stopped: %s' % (database, reason))
    except BaseException as error:
        loaded = False
        _note('Database import into %s failed: %s' % (database, error))
    finally:
        if descriptor is not None:
            try:
                os.close(descriptor)
            except OSError:
                pass
        if path is not None:
            try:
                os.unlink(path)
            except OSError:
                pass
        result = FAILED
        if account is not None:
            try:
                result = _finish(database, account, owner, connect, made, loaded, trusted)
            except BaseException as error:
                result = FAILED
                _note('Database import into %s could not be finished: %s' % (database, error))
    return result


def _finish(database, account, owner, connect, made, loaded, trusted):
    """Settle the import account once the client has ended; returns what import_dump returns."""
    connection, cursor = _administrator(connect)
    try:
        try:
            if made is not None:
                # The caller hands the objects over when the database's users
                # exist, and settles the account then.
                made.append((database, account))
                return LOADED if loaded else FAILED
            complete = settle(cursor, database, account, owner, connection)
            if not loaded:
                return FAILED
            return LOADED if complete else LOADED_OBJECTS_KEPT
        finally:
            if trusted:
                restore_function_creators(cursor)
    finally:
        connection.close()


def settle(cursor, database, account, owner, connection=None):
    """Give what the import account made in `database` to the registered account `owner` and remove the import account.

    Returns True when nothing is left with the import account. When objects
    cannot be handed over, the account is not dropped, because they would stop
    working: it is locked, keeps its grant on this database alone, and one
    line in the panel log names the database. Returns False then.
    """
    reason = 'the database has no registered account of its own that could own them'
    complete = False
    try:
        complete = hand_over(cursor, database, account, owner, connection)
    except BaseException as error:
        reason = str(error)
    try:
        if not complete and imported_objects(cursor, database, account):
            closed = lock_account(cursor, account[0], account[1])
            _note('Views, triggers, routines or events imported into %s still belong to the import account '
                  '%s@%s: %s. The account was %s and keeps its grant on this database alone, so they keep '
                  'working. Give them a definer by hand, then drop the account.'
                  % (database, account[0], account[1], reason, closed))
            return False
        drop_account(cursor, account[0], account[1])
        return True
    except BaseException as error:
        _note('The import account %s@%s of %s could not be settled: %s' % (account[0], account[1], database, error))
        return False


def hand_over(cursor, database, account, owner, connection=None):
    """Give what the import account made in `database` to the registered account `owner`; True when none is left."""
    if not imported_objects(cursor, database, account):
        return True
    holder = owner_account(cursor, database, owner, (account[1],))
    if holder is None:
        return False
    if connection is not None:
        try:
            connection.set_character_set('utf8mb4')
        except BaseException:
            pass
    handed = reassign_definers(cursor, database, account, holder)
    _note('%d imported view(s), trigger(s), routine(s) or event(s) in %s now belong to %s@%s.'
          % (handed, database, holder[0], holder[1]))
    return True


def open_dump(path):
    """Open a dump file for reading, only when the name is that of a regular file itself.

    A dump can lie in a directory another account writes to. A name that was
    made a link there is not followed.
    """
    descriptor = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK | os.O_CLOEXEC)
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise ImportRefused('The dump is not a regular file.')
        return os.fdopen(descriptor, 'rb')
    except BaseException:
        os.close(descriptor)
        raise
