"""The statements sent for a password change, for a phpMyAdmin account and for table data, with the server faked."""
import unittest
from unittest import mock

from plogical import databaseAccounts
from plogical.mysqlUtilities import mysqlUtilities
from plogical.test_database_accounts import Cursor


class Connection:
    def __init__(self):
        self.closed = 0

    def close(self):
        self.closed += 1


class StatementTests(unittest.TestCase):
    def setUp(self):
        self.saved = (mysqlUtilities.LOCALHOST, mysqlUtilities.REMOTEHOST, mysqlUtilities.RDS)
        mysqlUtilities.LOCALHOST, mysqlUtilities.REMOTEHOST, mysqlUtilities.RDS = 'localhost', '', 0
        self.connection = Connection()
        self.cursor = Cursor()
        for item in (mock.patch.object(mysqlUtilities, 'setupConnection',
                                       side_effect=lambda: (self.connection, self.cursor)),
                     mock.patch.object(databaseAccounts, 'administrative_account', return_value='root'),
                     mock.patch('plogical.mysqlUtilities.logging.CyberCPLogFileWriter.writeToFile')):
            self.log = item.start()
            self.addCleanup(item.stop)

    def tearDown(self):
        mysqlUtilities.LOCALHOST, mysqlUtilities.REMOTEHOST, mysqlUtilities.RDS = self.saved

    def logged(self):
        return ' '.join(str(call[0][0]) for call in self.log.call_args_list)


class PhpMyAdminAccountTests(StatementTests):
    def test_account_is_created_with_bound_values(self):
        with mock.patch.object(databaseAccounts, 'phpmyadmin_account_is_recorded', return_value=True):
            self.assertEqual(1, mysqlUtilities.addUserToDB(None, 'cp-pma-7', "p'w", 1))
        self.assertEqual([('CREATE USER %s@%s IDENTIFIED BY %s', ('cp-pma-7', 'localhost', "p'w"))],
                         self.cursor.ran('CREATE USER'))
        self.assertEqual(1, self.connection.closed)

    def test_existing_account_is_not_dropped(self):
        self.cursor.hosts = {'cp-pma-7': ['localhost']}
        with mock.patch.object(databaseAccounts, 'phpmyadmin_account_is_recorded', return_value=True):
            self.assertEqual(1, mysqlUtilities.addUserToDB(None, 'cp-pma-7', 'secret', 1))
        self.assertEqual([], self.cursor.ran('DROP'))
        self.assertEqual([], self.cursor.ran('CREATE'))
        self.assertEqual(1, len(self.cursor.ran('ALTER USER')))
        self.assertEqual(1, len(self.cursor.ran('REVOKE ALL PRIVILEGES, GRANT OPTION FROM')))

    def test_name_of_a_panel_user_or_of_another_account_reaches_no_statement(self):
        self.cursor.hosts = {'root': ['localhost'], 'cyberpanel': ['localhost'], 'exam_user': ['localhost']}
        for name in ('root', 'cyberpanel', 'exam_user', 'reseller1', "x'@'localhost' IDENTIFIED BY 'y", 'a b',
                     'CP-PMA-7', 'cp-pma-0', None, 7):
            self.assertEqual(0, mysqlUtilities.addUserToDB(None, name, 'secret', 1), repr(name))
            self.assertEqual(0, mysqlUtilities.addUserToDB('exam_shop', name, 'secret', 0), repr(name))
        self.assertEqual([], self.cursor.statements)
        self.assertEqual(0, self.connection.closed)

    def test_failed_creation_is_reported_without_the_password_in_the_log(self):
        self.cursor.fail = 'CREATE USER'
        self.assertEqual(0, mysqlUtilities.addUserToDB(None, 'cp-pma-7', 'VERY-SECRET', 1))
        self.assertNotIn('VERY-SECRET', self.logged())
        self.assertEqual(1, self.connection.closed)

    def test_grant_names_the_database_alone_and_binds_the_account(self):
        self.assertEqual(1, mysqlUtilities.addUserToDB('exam_shop', 'cp-pma-7', 'secret', 0))
        self.assertEqual([('GRANT ALL PRIVILEGES ON `exam\\_shop`.* TO %s@%s', ('cp-pma-7', 'localhost'))],
                         self.cursor.ran('GRANT'))
        self.assertEqual(1, self.connection.closed)

    def test_failed_grant_is_reported(self):
        self.cursor.fail = 'GRANT'
        self.assertEqual(0, mysqlUtilities.addUserToDB('exam_shop', 'cp-pma-7', 'secret', 0))
        self.assertEqual(1, self.connection.closed)


if __name__ == '__main__':
    unittest.main()
