"""Durable creation intent for nontransactional SQL provisioning."""
import fcntl
import hashlib
import json
import os
import secrets
import stat
import time
from contextlib import ExitStack

from plogical.securityUtils import _open_private_directory, _owner_ids, is_safe_sql_identifier

JOURNAL_DIRECTORY = '/home/cyberpanel/.database-provisioning'


class ProvisioningError(Exception):
    pass


class ProvisioningJournal:
    def __init__(self, database, username, website, directory=JOURNAL_DIRECTORY, owner_user='cyberpanel'):
        if not is_safe_sql_identifier(database) or not is_safe_sql_identifier(username):
            raise ProvisioningError('Invalid database name or username.')
        self.database, self.username, self.website = database, username, str(website)
        self.directory, self.owner_user = directory, owner_user
        self.name = hashlib.sha256(('database:' + database).encode()).hexdigest()
        self.data = None

    def _open(self, name, flags):
        descriptor = os.open(name, flags | os.O_CLOEXEC | os.O_NOFOLLOW, 0o600, dir_fd=self.directory_fd)
        try:
            info = os.fstat(descriptor)
            if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or info.st_mode & 0o077:
                raise ProvisioningError('Provisioning record must be a private regular file.')
            owner = _owner_ids(self.owner_user)
            if owner and os.geteuid() == 0:
                os.fchown(descriptor, *owner)
            return descriptor
        except BaseException:
            os.close(descriptor)
            raise

    def __enter__(self):
        self.resources = ExitStack()
        try:
            self.directory_fd = _open_private_directory(self.directory, self.owner_user)
            self.resources.callback(os.close, self.directory_fd)
            names = [self.name, hashlib.sha256(('user:' + self.username).encode()).hexdigest()]
            for name in sorted(names):
                descriptor = self._open(name + '.lock', os.O_RDWR | os.O_CREAT)
                self.resources.callback(os.close, descriptor)
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    raise ProvisioningError('A database creation using this name or user is already running.')
            try:
                descriptor = self._open(self.name + '.json', os.O_RDONLY)
            except FileNotFoundError:
                pass
            else:
                with os.fdopen(descriptor, 'r') as stream:
                    content = stream.read(16385)
                if len(content) > 16384:
                    raise ProvisioningError('Provisioning record is too large.')
                self.data = json.loads(content)
                if self.data.get('database') != self.database:
                    raise ProvisioningError('Provisioning record does not match the database.')
            return self
        except BaseException:
            self.resources.close()
            raise

    def begin(self):
        previous = self.data.get('attempt') if self.data else None
        self.data = {'version': 1, 'attempt': secrets.token_hex(16), 'previous_attempt': previous,
                     'database': self.database, 'username': self.username, 'website': self.website,
                     'stage': 'reserved', 'updated': int(time.time())}
        self.record('reserved')

    def record(self, stage):
        self.data['stage'] = stage
        self.data['updated'] = int(time.time())
        temporary = self.name + '.' + secrets.token_hex(8) + '.tmp'
        descriptor = self._open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
        try:
            with os.fdopen(descriptor, 'w') as stream:
                json.dump(self.data, stream, sort_keys=True)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.name + '.json', src_dir_fd=self.directory_fd, dst_dir_fd=self.directory_fd)
            os.fsync(self.directory_fd)
        finally:
            try:
                os.unlink(temporary, dir_fd=self.directory_fd)
            except FileNotFoundError:
                pass

    def __exit__(self, *args):
        self.resources.close()


def create_and_register(database, username, password, website, utilities, database_model,
                        directory=JOURNAL_DIRECTORY, owner_user='cyberpanel'):
    """Never adopt or drop an existing SQL namespace after a partial failure."""
    try:
        with ProvisioningJournal(database, username, website.domain, directory, owner_user) as journal:
            if (database_model.objects.filter(dbName=database).exists()
                    or database_model.objects.filter(dbUser=username).exists()):
                raise ProvisioningError('This database or user is already registered.')
            # An old journal is evidence of an attempt, never proof of current ownership.
            # Only independently empty SQL and panel namespaces permit delete/recreate.
            if utilities.databaseNamesExist(database, username):
                raise ProvisioningError('An SQL database or account already uses this name. Existing data was preserved; administrator review is required.')
            journal.begin()
            if utilities.createDatabase(database, username, password, progress=journal.record) != 1:
                raise ProvisioningError('Database creation stopped at %s. Existing data and the provisioning record were preserved for administrator review.' % journal.data['stage'])
            journal.record('registering_panel')
            database_model.objects.create(website=website, dbName=database, dbUser=username)
            journal.record('completed')
            return 1, 'None'
    except ProvisioningError as error:
        return 0, str(error)
    except Exception:
        # Driver errors can contain credentials; retain the stage, not the exception text.
        return 0, 'Database creation could not complete. Existing data and any provisioning record were preserved for administrator review.'
