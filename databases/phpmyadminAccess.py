"""The phpMyAdmin access of a panel user: its key file, its record and its database account.

A user who is not an administrator signs in to phpMyAdmin with an account of
their own, named after the user's number and granted the databases the user
manages at that moment. Its password is stored encrypted; the key is kept in
a private file named after the user's number as well.

The account is taken away whenever what the user may manage changes (the
user is suspended or deleted, gets another role, a website moves to another
owner). The next visit to phpMyAdmin builds it again from what the user
manages then.
"""
import os
import re
import stat

from plogical import databaseAccounts
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.securityUtils import _open_private_directory, _owner_ids

KEY_DIRECTORY = '/home/cyberpanel/.phpmyadmin-keys'
KEY_OWNER = 'cyberpanel'
EARLIER_KEY_DIRECTORY = '/home/cyberpanel'
_EARLIER_KEY_NAME = re.compile(r'[A-Za-z0-9._@-]{1,50}')
_KEY_LIMIT = 256


def _key_name(user_id):
    if isinstance(user_id, bool) or not isinstance(user_id, int) or user_id < 1:
        raise ValueError('A phpMyAdmin key belongs to a saved panel user.')
    return str(user_id)


def write_key(user_id, key, directory=KEY_DIRECTORY, owner=KEY_OWNER):
    """Store the key of this user's phpMyAdmin password, replacing an earlier one."""
    name = _key_name(user_id)
    directory_fd = _open_private_directory(directory, owner)
    try:
        try:
            os.unlink(name, dir_fd=directory_fd)
        except FileNotFoundError:
            pass
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_CLOEXEC | os.O_NOFOLLOW
        descriptor = os.open(name, flags, 0o600, dir_fd=directory_fd)
        with os.fdopen(descriptor, 'wb') as stream:
            if owner is not None and os.geteuid() == 0:
                os.fchown(stream.fileno(), *_owner_ids(owner))
            stream.write(key)
    finally:
        os.close(directory_fd)


def read_key(user_id, directory=KEY_DIRECTORY, owner=KEY_OWNER):
    name = _key_name(user_id)
    directory_fd = _open_private_directory(directory, owner)
    try:
        descriptor = os.open(name, os.O_RDONLY | os.O_CLOEXEC | os.O_NOFOLLOW, dir_fd=directory_fd)
        with os.fdopen(descriptor, 'rb') as stream:
            status = os.fstat(stream.fileno())
            if (not stat.S_ISREG(status.st_mode) or status.st_nlink != 1 or status.st_mode & 0o077
                    or status.st_uid != os.geteuid()):
                raise OSError('The phpMyAdmin key must be a private file of the panel.')
            key = stream.read(_KEY_LIMIT + 1)
        if not key or len(key) > _KEY_LIMIT:
            raise OSError('The phpMyAdmin key is not usable.')
        return key.strip()
    finally:
        os.close(directory_fd)


def remove_key(user_id, directory=KEY_DIRECTORY):
    try:
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError:
        return
    try:
        os.unlink(_key_name(user_id), dir_fd=directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def _remove_earlier_key(user_name, directory=EARLIER_KEY_DIRECTORY):
    # Earlier releases named the key file after the user. Only a name that is
    # a plain file name is looked for.
    if not isinstance(user_name, str) or _EARLIER_KEY_NAME.fullmatch(user_name) is None:
        return
    try:
        directory_fd = os.open(directory, os.O_RDONLY | os.O_DIRECTORY | os.O_CLOEXEC | os.O_NOFOLLOW)
    except OSError:
        return
    try:
        os.unlink('phpmyadmin_' + user_name, dir_fd=directory_fd)
    except OSError:
        pass
    finally:
        os.close(directory_fd)


def _earlier_records(user_name):
    from databases.models import GlobalUserDB
    if not isinstance(user_name, str) or not user_name or databaseAccounts.is_phpmyadmin_account(user_name):
        return []
    return [record for record in GlobalUserDB.objects.filter(username=user_name) if record.username == user_name]


def _retire_earlier(cursor, host, user):
    """Remove what an earlier release kept for this user under the user's own name."""
    records = _earlier_records(user.userName)
    # The stored password of an account is an encrypted token; an administrator's record never was one.
    if any(str(record.password).startswith('gAAAAA') for record in records):
        refusal = databaseAccounts.earlier_phpmyadmin_account_refusal(cursor, user.userName, host)
        if refusal is None:
            databaseAccounts.drop_account(cursor, user.userName, host)
        elif refusal != 'there is no such account':
            logging.writeToFile(
                'The database account named after panel user number %d was left in place: %s. '
                'Review it by hand. [phpMyAdmin access]' % (user.pk, refusal))
    for record in records:
        record.delete()
    _remove_earlier_key(user.userName)


def _retire_current(cursor, host, user):
    from databases.models import GlobalUserDB
    account = databaseAccounts.phpmyadmin_account(user.pk)
    # The account goes first. While it cannot be dropped its record and key
    # stay, so that the next removal or the user's next visit finishes the work.
    databaseAccounts.drop_account(cursor, account, host)
    for record in GlobalUserDB.objects.filter(username=account):
        if record.username == account:
            record.delete()
    remove_key(user.pk)


def _each(users, steps):
    """Run the steps for every user over one connection. Never raises: the caller's own work goes on."""
    users = [user for user in users if user is not None and getattr(user, 'pk', None)]
    if not users:
        return 1
    connection = None
    done = 1
    try:
        from plogical.mysqlUtilities import mysqlUtilities
        connection, cursor = mysqlUtilities.setupConnection()
        if connection == 0:
            connection = None
            raise RuntimeError('no connection to the database server')
        for user in users:
            for step in steps:
                try:
                    step(cursor, mysqlUtilities.LOCALHOST, user)
                except Exception as error:
                    done = 0
                    logging.writeToFile('phpMyAdmin access of panel user number %s was not fully removed (%s). '
                                        '[phpMyAdmin access]' % (user.pk, type(error).__name__))
    except Exception as error:
        done = 0
        logging.writeToFile('phpMyAdmin access was not removed (%s). [phpMyAdmin access]' % type(error).__name__)
    finally:
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass
    return done


def retire_earlier(user):
    """Before new access is built: remove what an earlier release kept under the user's name."""
    return _each([user], (_retire_earlier,))


def retire(users):
    """Take phpMyAdmin access away from these users; it is built again on their next visit."""
    return _each(users, (_retire_earlier, _retire_current))


def retire_for_website(owner):
    """A website left this owner: the owner and the reseller above lose the account that reached its databases."""
    try:
        from loginSystem.models import Administrator
        users = [owner] + list(Administrator.objects.filter(pk=owner.owner).exclude(pk=owner.pk))
    except Exception:
        users = [owner]
    return retire(users)
