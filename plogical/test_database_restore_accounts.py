"""A restore sets up the accounts registered for the database and leaves every other account as it is."""
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities


class Rows:
    """The few lookups of a model manager, over rows held in memory."""

    def __init__(self, rows):
        self.rows = [dict(row) for row in rows]

    @staticmethod
    def _matches(row, conditions):
        for key, wanted in conditions.items():
            field, _, test = key.partition('__')
            value = row.get(field)
            if hasattr(wanted, 'dbName'):
                wanted = wanted.dbName
            if test == 'in':
                if value not in wanted:
                    return False
            elif test == 'iexact':
                if str(value).lower() != str(wanted).lower():
                    return False
            elif value != wanted:
                return False
        return True

    @property
    def objects(self):
        return self

    def filter(self, **conditions):
        return Rows(row for row in self.rows if self._matches(row, conditions))

    def exclude(self, **conditions):
        return Rows(row for row in self.rows if not self._matches(row, conditions))

    def get(self, **conditions):
        found = self.filter(**conditions).rows
        if len(found) != 1:
            raise LookupError('no such row')
        return SimpleNamespace(**found[0])

    def first(self):
        return SimpleNamespace(**self.rows[0]) if self.rows else None

    def exists(self):
        return bool(self.rows)

    def values_list(self, field, flat=True):
        return [row[field] for row in self.rows]


def panel(databases=(('shop_db', 'shop_user'),), additional=(), phpmyadmin=()):
    """Patches for the panel's registrations: databases, their additional users, phpMyAdmin accounts."""
    return (mock.patch.object(module, 'Databases', Rows({'dbName': name, 'dbUser': user} for name, user in databases)),
            mock.patch('databases.models.DatabasesUsers',
                       Rows({'owner': owner, 'username': user} for owner, user in additional)),
            mock.patch('databases.models.GlobalUserDB', Rows({'username': user} for user in phpmyadmin)))


class Cursor:
    def __init__(self, granted):
        # granted: [(stored database, user, host, grant option)]
        self.granted = list(granted)
        self.statements = []
        self.rows = []

    def execute(self, query, args=None):
        self.statements.append((query, args))
        self.rows = []
        if query.startswith('SELECT User, Host FROM mysql.db WHERE Db IN'):
            self.rows = [(user, host) for stored, user, host, option in self.granted if stored in args]
        elif query.startswith('SELECT Db, Grant_priv FROM mysql.db'):
            self.rows = [(stored, 'Y' if option else 'N') for stored, user, host, option in self.granted
                         if (user, host) == tuple(args[:2]) and stored in args[2:]]
        elif query.startswith('SELECT User FROM mysql.user'):
            self.rows = [(args[0],)] if any((user, host) == tuple(args) for s, user, host, o in self.granted) else []
        elif query.startswith('SELECT Db FROM mysql.db WHERE User'):
            self.rows = [(stored,) for stored, user, host, option in self.granted if (user, host) == tuple(args)]

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def changes(self):
        return [(query, args) for query, args in self.statements if not query.startswith('SELECT')]


class RestoredAccountTests(unittest.TestCase):
    HASH = '*94BDCEBE19083CE2A1F959FD02F964C7AF4CFC29'

    def restore(self, user, host='localhost', granted=(('shop\\_db', 'shop_user', 'localhost', False),), **registered):
        self.cursor = Cursor(granted)
        connection = mock.Mock()
        patches = panel(**registered)
        with patches[0], patches[1], patches[2], \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, self.cursor)) as connect, \
                mock.patch.object(mysqlUtilities, 'createDatabase', return_value=1) as create, \
                mock.patch.object(mysqlUtilities, 'changePassword', return_value=1) as change, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile') as log:
            result = mysqlUtilities.restoreDatabaseUser('shop_db', user, self.HASH, host)
        self.connect, self.create, self.change, self.log = connect, create, change, log
        return result

    def test_registered_user_gets_the_password_from_the_backup(self):
        self.assertEqual(1, self.restore('shop_user'))
        self.change.assert_called_once_with('shop_user', self.HASH, 1, 'localhost')
        self.create.assert_not_called()

    def test_account_that_is_not_registered_for_the_database_is_left_as_it_is(self):
        # Another account with a grant on the database, as a backup lists it.
        granted = (('shop\\_db', 'shop_user', 'localhost', False), ('shop\\_db', 'reseller', 'localhost', False))
        self.assertEqual(1, self.restore('reseller', granted=granted))
        self.change.assert_not_called()
        self.create.assert_not_called()
        self.connect.assert_not_called()
        self.assertIn('not a registered user', self.log.call_args[0][0])

    def test_account_of_another_database_is_left_as_it_is(self):
        self.assertEqual(1, self.restore('other_user', databases=(('shop_db', 'shop_user'), ('other_db', 'other_user'))))
        self.change.assert_not_called()
        self.create.assert_not_called()

    def test_phpmyadmin_account_is_never_restored_even_under_a_registered_name(self):
        granted = (('shop\\_db', 'reseller', 'localhost', False),)
        self.assertEqual(1, self.restore('reseller', granted=granted, databases=(('shop_db', 'reseller'),),
                                         phpmyadmin=('Reseller',)))
        self.change.assert_not_called()
        self.connect.assert_not_called()

    def test_additional_registered_user_is_restored(self):
        granted = (('shop\\_db', 'shop_reader', 'localhost', False),)
        self.assertEqual(1, self.restore('shop_reader', granted=granted, additional=(('shop_db', 'shop_reader'),)))
        self.change.assert_called_once_with('shop_reader', self.HASH, 1, 'localhost')

    def test_database_that_is_not_registered_restores_no_account(self):
        self.assertEqual(1, self.restore('shop_user', databases=()))
        self.change.assert_not_called()
        self.connect.assert_not_called()

    def test_host_must_be_an_address_a_name_or_a_pattern(self):
        for host in ("localhost' OR '1'='1", 'two words', '', 'line\nbreak', 'localhost\n', "a'b", None, 5):
            self.assertEqual(0, self.restore('shop_user', host), repr(host))
            self.change.assert_not_called()
            self.create.assert_not_called()
            self.connect.assert_not_called()
        for host in ('%', '10.0.0.%', 'db.example.com', '2001:db8::1', '192.168.1.0/255.255.255.0'):
            self.assertEqual(1, self.restore('shop_user', host), host)

    def test_new_account_of_the_registered_user_starts_with_a_password_nobody_knows(self):
        self.assertEqual(1, self.restore('shop_user', '203.0.113.9'))
        (name, user, password, create, host), = [call[0] for call in self.create.call_args_list]
        self.assertEqual(('shop_db', 'shop_user', 0, '203.0.113.9'), (name, user, create, host))
        self.assertRegex(password, r'^[A-Za-z0-9]{32}$')
        self.assertNotEqual(self.HASH, password)
        self.change.assert_called_once_with('shop_user', self.HASH, 1, '203.0.113.9')

    def test_existing_registered_account_without_the_grant_is_refused(self):
        self.assertEqual(0, self.restore('shop_user', granted=(('other\\_db', 'shop_user', 'localhost', False),)))
        self.change.assert_not_called()


class StartingPasswordTests(unittest.TestCase):
    def test_archive_restore_creates_the_user_with_a_password_nobody_knows(self):
        from pathlib import Path
        source = (Path(__file__).resolve().parents[1] / 'plogical' / 'backupUtilities.py').read_text()
        self.assertNotIn("createDatabaseAndRegister(dbName, dbUser, 'cyberpanel'", source)
        self.assertIn('createDatabaseAndRegister(dbName, dbUser, generate_pass(32), website)', source)

    def test_restore_into_a_new_database_does_the_same(self):
        with mock.patch.object(module, 'Databases', Rows([])), \
                mock.patch.object(mysqlUtilities, 'createDatabaseAndRegister', return_value=(1, 'None')) as create:
            mysqlUtilities.prepareDatabaseForRestore('shop_db', 'shop_user', SimpleNamespace(pk=1))
            mysqlUtilities.prepareDatabaseForRestore('shop_db', 'shop_user', SimpleNamespace(pk=1))
        first, second = [call[0][2] for call in create.call_args_list]
        self.assertRegex(first, r'^[A-Za-z0-9]{32}$')
        self.assertNotEqual(first, second)


if __name__ == '__main__':
    unittest.main()
