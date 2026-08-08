import unittest
from unittest.mock import patch

from plogical.mysqlUtilities import mysqlUtilities


class FakeConnection:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class FakeCursor:
    def __init__(self, fail_loopback_create=False):
        self.queries = []
        self.fail_loopback_create = fail_loopback_create

    def execute(self, query):
        self.queries.append(query)
        if self.fail_loopback_create and query.startswith("CREATE USER '") and "@'127.0.0.1'" in query:
            raise RuntimeError('loopback account already exists')


class MySQLLoopbackUserTests(unittest.TestCase):

    def setUp(self):
        self.original_localhost = mysqlUtilities.LOCALHOST
        self.original_remotehost = mysqlUtilities.REMOTEHOST
        self.original_rds = mysqlUtilities.RDS
        mysqlUtilities.LOCALHOST = 'localhost'
        mysqlUtilities.REMOTEHOST = ''
        mysqlUtilities.RDS = 0

    def tearDown(self):
        mysqlUtilities.LOCALHOST = self.original_localhost
        mysqlUtilities.REMOTEHOST = self.original_remotehost
        mysqlUtilities.RDS = self.original_rds

    def test_local_database_user_is_created_for_socket_and_loopback(self):
        connection = FakeConnection()
        cursor = FakeCursor()
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.createDatabase('site_db', 'site_user', 'secret'))

        sql = '\n'.join(cursor.queries)
        self.assertIn("CREATE USER 'site_user'@'localhost'", sql)
        self.assertIn("CREATE USER 'site_user'@'127.0.0.1'", sql)
        self.assertIn("GRANT ALL PRIVILEGES ON site_db.* TO 'site_user'@'127.0.0.1'", sql)
        self.assertTrue(connection.closed)

    def test_loopback_account_failure_does_not_undo_primary_account(self):
        connection = FakeConnection()
        cursor = FakeCursor(fail_loopback_create=True)
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.createDatabase('site_db', 'site_user', 'secret'))
        self.assertTrue(connection.closed)

    def test_remote_database_does_not_receive_loopback_account(self):
        mysqlUtilities.LOCALHOST = '10.0.0.20'
        mysqlUtilities.REMOTEHOST = 'database.example'
        connection = FakeConnection()
        cursor = FakeCursor()
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.createDatabase('site_db', 'site_user', 'secret'))

        self.assertNotIn("@'127.0.0.1'", '\n'.join(cursor.queries))

    def test_password_change_updates_loopback_account(self):
        connection = FakeConnection()
        cursor = FakeCursor()
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.changePassword('site_user', 'new-hash', encrypt=1))

        sql = '\n'.join(cursor.queries)
        self.assertIn("SET PASSWORD FOR 'site_user'@'localhost'", sql)
        self.assertIn("SET PASSWORD FOR 'site_user'@'127.0.0.1'", sql)


if __name__ == '__main__':
    unittest.main()
