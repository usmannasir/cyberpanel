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


class PasswordChangeTests(StatementTests):
    def test_every_account_of_the_user_gets_the_new_password(self):
        self.cursor.hosts = {'exam_user': ['localhost', '127.0.0.1', '198.51.100.7', '203.0.113.5']}
        self.assertEqual(1, mysqlUtilities.changePassword('exam_user', "n'ew $pass"))
        self.assertEqual([('ALTER USER %s@%s IDENTIFIED BY %s', ('exam_user', host, "n'ew $pass"))
                          for host in ('localhost', '127.0.0.1', '198.51.100.7', '203.0.113.5')],
                         self.cursor.ran('ALTER USER'))
        self.assertEqual(1, self.connection.closed)

    def test_accounts_of_a_name_in_another_case_are_not_touched(self):
        self.cursor.hosts = {'exam_user': ['localhost'], 'Exam_User': ['localhost', '%']}
        self.assertEqual(1, mysqlUtilities.changePassword('exam_user', 'new'))
        self.assertEqual([('ALTER USER %s@%s IDENTIFIED BY %s', ('exam_user', 'localhost', 'new'))],
                         self.cursor.ran('ALTER USER'))

    def test_user_without_an_account_is_reported_as_failure(self):
        self.assertEqual(0, mysqlUtilities.changePassword('exam_user', 'new'))
        self.assertEqual([], self.cursor.ran('ALTER USER'))
        self.assertEqual(1, self.connection.closed)

    def test_one_failed_account_fails_the_change(self):
        self.cursor.hosts = {'exam_user': ['localhost', '127.0.0.1']}
        self.cursor.fail = 'ALTER USER'
        self.assertEqual(0, mysqlUtilities.changePassword('exam_user', 'new'))
        self.assertEqual(1, self.connection.closed)

    def test_accounts_of_the_server_are_refused_before_connecting(self):
        self.cursor.hosts = {'root': ['localhost'], 'cyberpanel': ['localhost'], 'cp-pma-7': ['localhost']}
        for name in ('root', 'Root', 'mysql', 'mariadb.sys', 'cyberpanel', 'debian-sys-maint', 'cp-pma-7', '', None):
            self.assertEqual(0, mysqlUtilities.changePassword(name, 'new'), repr(name))
            self.assertEqual(0, mysqlUtilities.changePassword(name, '*HASH', 1, 'localhost'), repr(name))
        self.assertEqual([], self.cursor.statements)
        self.assertEqual(0, self.connection.closed)

    def test_administrative_account_of_a_remote_server_is_refused(self):
        with mock.patch.object(databaseAccounts, 'administrative_account', return_value='doadmin'):
            self.assertEqual(0, mysqlUtilities.changePassword('doadmin', 'new'))
        self.assertEqual([], self.cursor.statements)

    def test_stored_password_for_one_host_is_set_there_and_on_loopback(self):
        self.assertEqual(1, mysqlUtilities.changePassword('exam_user', '*HASH', 1, '203.0.113.5'))
        self.assertEqual([('SET PASSWORD FOR %s@%s = %s', ('exam_user', '203.0.113.5', '*HASH')),
                          ('SET PASSWORD FOR %s@%s = %s', ('exam_user', '127.0.0.1', '*HASH'))],
                         self.cursor.ran('SET PASSWORD'))
        self.assertEqual([], self.cursor.ran('SELECT'))


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
