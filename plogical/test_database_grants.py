"""A grant on a database names that database only, and readers find it in either stored form."""
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from plogical import databaseGrants
from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities

ROOT = Path(__file__).resolve().parents[1]
ASK = "SHOW VARIABLES LIKE 'partial_revokes'"


class Cursor:
    """Records every statement; answers a statement by its first words."""

    def __init__(self, answers=None):
        self.queries = []
        self.answers = answers or {}
        self.rows = []

    def execute(self, query, args=None):
        self.queries.append((query, args))
        self.rows = []
        for start, rows in self.answers.items():
            if query.startswith(start):
                self.rows = list(rows)

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def statements(self, start):
        return [(query, args) for query, args in self.queries if query.startswith(start)]


class Connection:
    closed = False

    def close(self):
        self.closed = True


class GrantNameTests(unittest.TestCase):
    def test_wildcard_characters_are_made_literal(self):
        self.assertEqual('shop\\_db', databaseGrants.escape_grant_name('shop_db'))
        self.assertEqual('a\\%b', databaseGrants.escape_grant_name('a%b'))
        self.assertEqual('a\\\\b', databaseGrants.escape_grant_name('a\\b'))
        self.assertEqual('a\\\\\\_b', databaseGrants.escape_grant_name('a\\_b'))
        self.assertEqual('plain', databaseGrants.escape_grant_name('plain'))

    def test_server_without_the_setting_gets_the_escaped_name(self):
        cursor = Cursor()
        self.assertEqual('shop\\_db', databaseGrants.grant_name(cursor, 'shop_db'))
        self.assertEqual([(ASK, None)], cursor.queries)

    def test_setting_off_gets_the_escaped_name(self):
        for value in ('OFF', 'off', '0', b'OFF'):
            cursor = Cursor({'SHOW VARIABLES': [('partial_revokes', value)]})
            self.assertEqual('shop\\_db', databaseGrants.grant_name(cursor, 'shop_db'))

    def test_server_that_reads_names_literally_gets_the_plain_name(self):
        for value in ('ON', 'on', '1', b'ON'):
            cursor = Cursor({'SHOW VARIABLES': [('partial_revokes', value)]})
            self.assertEqual('shop_db', databaseGrants.grant_name(cursor, 'shop_db'))

    def test_a_grant_without_a_database_is_refused(self):
        for name in (None, '', 5):
            with self.assertRaises(ValueError):
                databaseGrants.grant_name(Cursor(), name)

    def test_stored_forms_of_a_name(self):
        self.assertEqual(('plain',), databaseGrants.stored_names('plain'))
        self.assertEqual(('shop_db', 'shop\\_db'), databaseGrants.stored_names('shop_db'))
        self.assertEqual(('a_%', 'a\\_\\%', 'a\\_%'), databaseGrants.stored_names('a_%'))

    def test_pattern_is_told_from_an_exact_name(self):
        self.assertTrue(databaseGrants.is_pattern('shop_db'))
        self.assertTrue(databaseGrants.is_pattern('shop%'))
        self.assertTrue(databaseGrants.is_pattern('shop\\_db_'))
        self.assertFalse(databaseGrants.is_pattern('shop\\_db'))
        self.assertFalse(databaseGrants.is_pattern('shop\\%'))
        self.assertFalse(databaseGrants.is_pattern('plain'))

    def test_what_a_stored_value_covers(self):
        self.assertTrue(databaseGrants.pattern_matches('shop_db', 'shopXdb'))
        self.assertTrue(databaseGrants.pattern_matches('__________', 'cyberpanel'))
        self.assertFalse(databaseGrants.pattern_matches('__________', 'mysql'))
        self.assertTrue(databaseGrants.pattern_matches('shop%', 'shop'))
        self.assertTrue(databaseGrants.pattern_matches('%', 'anything'))
        self.assertTrue(databaseGrants.pattern_matches('a%c_e', 'abbcde'))
        self.assertFalse(databaseGrants.pattern_matches('a%c_e', 'abbcd'))
        self.assertTrue(databaseGrants.pattern_matches('shop\\_db', 'shop_db'))
        self.assertFalse(databaseGrants.pattern_matches('shop\\_db', 'shopXdb'))
        self.assertFalse(databaseGrants.pattern_matches('\\_\\_', 'ab'))

    def test_accounts_are_read_under_both_forms_once_each(self):
        cursor = Cursor({'SELECT User, Host': [('shop_user', '127.0.0.1'), (b'shop_user', b'localhost'),
                                                ('shop_user', '127.0.0.1')]})
        self.assertEqual([('shop_user', '127.0.0.1'), ('shop_user', 'localhost')],
                         databaseGrants.accounts_granted(cursor, 'shop_db'))
        self.assertEqual([('SELECT User, Host FROM mysql.db WHERE Db IN (%s, %s)', ('shop_db', 'shop\\_db'))],
                         cursor.queries)

    def test_account_grant_is_found_in_either_form(self):
        for held, expected in ((['shop_db'], True), (['shop\\_db'], True), (['other', b'shop\\_db'], True),
                               (['shopXdb'], False), (['shop\\_d_'], False), ([], False)):
            cursor = Cursor({'SELECT Db': [(value,) for value in held]})
            self.assertEqual(expected, databaseGrants.account_is_granted(cursor, 'shop_db', 'shop_user', 'localhost'))
            self.assertEqual([('SELECT Db FROM mysql.db WHERE User = %s AND Host = %s', ('shop_user', 'localhost'))],
                             cursor.queries)


class PanelStatementTests(unittest.TestCase):
    def setUp(self):
        self.saved = (mysqlUtilities.LOCALHOST, mysqlUtilities.REMOTEHOST, mysqlUtilities.RDS)
        mysqlUtilities.LOCALHOST, mysqlUtilities.REMOTEHOST, mysqlUtilities.RDS = 'localhost', '', 0
        self.connection = Connection()

    def tearDown(self):
        mysqlUtilities.LOCALHOST, mysqlUtilities.REMOTEHOST, mysqlUtilities.RDS = self.saved

    def run_with(self, cursor, function, *args):
        with mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(self.connection, cursor)), \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            return function(*args)

    def test_new_database_is_granted_by_its_exact_name(self):
        cursor = Cursor()
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.createDatabase, 'shop_db', 'shop_user', 'secret'))
        self.assertEqual([('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ('shop_user', 'localhost')),
                          ('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ('shop_user', '127.0.0.1'))],
                         cursor.statements('GRANT'))
        self.assertEqual([('CREATE DATABASE `shop_db`', None)], cursor.statements('CREATE DATABASE'))
        self.assertLess(cursor.queries.index((ASK, None)), cursor.queries.index(('CREATE DATABASE `shop_db`', None)))

    def test_name_made_of_wildcards_is_granted_as_itself(self):
        cursor = Cursor()
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.createDatabase, '__________', 'some_user', 'secret'))
        expected = 'GRANT ALL PRIVILEGES ON `' + '\\_' * 10 + '`.* TO %s@%s'
        self.assertEqual({expected}, {query for query, args in cursor.statements('GRANT')})
        stored = '\\_' * 10
        self.assertFalse(databaseGrants.pattern_matches(stored, 'cyberpanel'))
        self.assertTrue(databaseGrants.pattern_matches(stored, '__________'))

    def test_limited_privileges_for_rds_use_the_exact_name_too(self):
        mysqlUtilities.RDS = 1
        cursor = Cursor()
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.createDatabase, 'shop_db', 'shop_user', 'secret'))
        self.assertIn(('GRANT INDEX, DROP, UPDATE, ALTER, CREATE, SELECT, INSERT, DELETE ON `shop\\_db`.* TO %s@%s',
                       ('shop_user', 'localhost')), cursor.queries)

    def test_server_that_reads_names_literally_gets_the_plain_name(self):
        cursor = Cursor({'SHOW VARIABLES': [('partial_revokes', 'ON')]})
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.createDatabase, 'shop_db', 'shop_user', 'secret'))
        self.assertIn(('GRANT ALL PRIVILEGES ON `shop_db`.* TO %s@%s', ('shop_user', 'localhost')), cursor.queries)

    def test_remote_host_account_is_granted_by_exact_name(self):
        cursor = Cursor()
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.createDatabase, 'shop_db', 'shop_user', 'secret',
                                          0, '203.0.113.9'))
        self.assertEqual([('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ('shop_user', '203.0.113.9'))],
                         cursor.statements('GRANT'))
        self.assertEqual([], cursor.statements('CREATE DATABASE'))

    def test_failed_setting_lookup_creates_nothing(self):
        cursor = Cursor()
        cursor.fetchall = mock.Mock(side_effect=RuntimeError('lost connection'))
        self.assertEqual(0, self.run_with(cursor, mysqlUtilities.createDatabase, 'shop_db', 'shop_user', 'secret'))
        self.assertEqual([(ASK, None)], cursor.queries)
        self.assertTrue(self.connection.closed)

    def test_phpmyadmin_account_is_granted_by_exact_name_with_bound_account(self):
        cursor = Cursor()
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.addUserToDB, 'shop_db', "o'brien", 'secret', 0))
        self.assertEqual([(ASK, None),
                          ('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ("o'brien", 'localhost'))],
                         cursor.queries)

    def test_phpmyadmin_grant_quotes_the_database_name(self):
        cursor = Cursor()
        self.run_with(cursor, mysqlUtilities.addUserToDB, 'shop`.* TO x; --', 'paneluser', 'secret', 0)
        self.assertEqual([('GRANT ALL PRIVILEGES ON `shop``.* TO x; --`.* TO %s@%s', ('paneluser', 'localhost'))],
                         cursor.statements('GRANT'))

    def test_global_user_grant_is_exact_and_bound(self):
        cursor = Cursor()
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.allowGlobalUserAccess, 'paneluser', 'shop_db'))
        self.assertEqual([('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', ('paneluser', 'localhost'))],
                         cursor.statements('GRANT'))

    def test_deleting_a_database_drops_accounts_stored_under_either_form(self):
        cursor = Cursor({'SELECT User, Host': [('shop_user', 'localhost'), ('shop_user', '127.0.0.1')]})
        self.assertEqual(1, self.run_with(cursor, mysqlUtilities.deleteDatabase, 'shop_db', 'shop_user'))
        self.assertEqual([('DROP DATABASE IF EXISTS `shop_db`', None),
                          ('SELECT User, Host FROM mysql.db WHERE Db IN (%s, %s)', ('shop_db', 'shop\\_db')),
                          ('DROP USER IF EXISTS %s@%s', ('shop_user', 'localhost')),
                          ('DROP USER IF EXISTS %s@%s', ('shop_user', '127.0.0.1'))], cursor.queries)

    def restore_user(self, held):
        cursor = Cursor({'SELECT User FROM mysql.user': [('shop_user',)], 'SELECT Db': [(value,) for value in held]})
        with mock.patch.object(mysqlUtilities, 'changePassword', return_value=1) as password, \
                mock.patch.object(mysqlUtilities, 'createDatabase') as create:
            result = self.run_with(cursor, mysqlUtilities.restoreDatabaseUser, 'shop_db', 'shop_user', 'hash', 'localhost')
        create.assert_not_called()
        return result, password

    def test_restore_accepts_an_account_whose_grant_is_stored_escaped(self):
        for held in (['shop\\_db'], ['shop_db'], ['other\\_db', 'shop\\_db']):
            result, password = self.restore_user(held)
            self.assertEqual(1, result)
            password.assert_called_once_with('shop_user', 'hash', 1, 'localhost')

    def test_restore_refuses_an_account_granted_on_another_database_only(self):
        for held in (['shopXdb'], ['other\\_db'], []):
            result, password = self.restore_user(held)
            self.assertEqual(0, result)
            password.assert_not_called()

    def fetch_user(self, registered, accounts):
        row = mock.Mock(dbUser=registered)
        cursor = Cursor({'SELECT User, Host': accounts})
        with mock.patch.object(module.Databases.objects, 'get', return_value=row):
            return self.run_with(cursor, mysqlUtilities.fetchuser, 'shop_db'), row, cursor

    def test_registered_user_with_its_grant_stays_the_database_user(self):
        result, row, cursor = self.fetch_user('shop_user', [('panel_reseller', 'localhost'), ('shop_user', 'localhost')])
        self.assertEqual('shop_user', result)
        row.save.assert_not_called()
        self.assertEqual('shop_user', row.dbUser)
        self.assertEqual([('SELECT User, Host FROM mysql.db WHERE Db IN (%s, %s)', ('shop_db', 'shop\\_db'))],
                         cursor.queries)
        self.assertTrue(self.connection.closed)

    def test_database_user_is_detected_only_when_the_registered_one_has_no_grant(self):
        result, row, cursor = self.fetch_user('gone', [('plain', 'localhost'), ('shop_user', 'localhost')])
        self.assertEqual('shop_user', result)
        self.assertEqual('shop_user', row.dbUser)
        row.save.assert_called_once_with()

    def test_database_without_accounts_reports_none(self):
        result, row, cursor = self.fetch_user('gone', [])
        self.assertEqual(1, result)
        row.save.assert_not_called()


class BackupReaderTests(unittest.TestCase):
    def test_backups_read_database_accounts_under_both_forms(self):
        for name in ('backupUtilities.py', 'Backupsv2.py'):
            source = (ROOT / 'plogical' / name).read_text()
            self.assertEqual(1, source.count('databaseGrants.accounts_granted(cursor, '), name)
            self.assertNotIn('mysql.db where db=', source.lower(), name)
            self.assertIn('from plogical import databaseGrants', source, name)

    def test_backup_v2_keeps_host_then_user_order(self):
        cursor = Cursor({'SELECT User, Host': [('shop_user', 'localhost')]})
        db = SimpleNamespace(dbName='shop_db')
        accounts = [(host, user) for user, host in databaseGrants.accounts_granted(cursor, db.dbName)]
        self.assertEqual([('localhost', 'shop_user')], accounts)
        source = (ROOT / 'plogical' / 'Backupsv2.py').read_text()
        self.assertIn('DBUsers = [(host, user) for user, host in', source)


if __name__ == '__main__':
    unittest.main()
