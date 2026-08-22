import unittest
from unittest.mock import MagicMock, patch

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

    def execute(self, query, args=None):
        self.queries.append((query, args))
        if (self.fail_loopback_create and query.startswith("CREATE USER ")
                and args and args[1] == '127.0.0.1'):
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

        self.assertIn(
            ('CREATE USER %s@%s IDENTIFIED BY %s',
             ('site_user', 'localhost', 'secret')),
            cursor.queries,
        )
        self.assertIn(
            ('CREATE USER %s@%s IDENTIFIED BY %s',
             ('site_user', '127.0.0.1', 'secret')),
            cursor.queries,
        )
        self.assertIn(
            ('GRANT ALL PRIVILEGES ON `site_db`.* TO %s@%s',
             ('site_user', '127.0.0.1')),
            cursor.queries,
        )
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

        hosts = [args[1] for query, args in cursor.queries
                 if query.startswith('CREATE USER')]
        self.assertNotIn('127.0.0.1', hosts)

    def test_database_password_is_bound_and_never_logged_in_sql(self):
        connection = FakeConnection()
        cursor = FakeCursor()
        password = "p'ass $word;&|"
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(
                1,
                mysqlUtilities.createDatabase('site_db', 'site_user', password),
            )

        sql = '\n'.join(query for query, unused_args in cursor.queries)
        self.assertNotIn(password, sql)
        self.assertTrue(any(
            args and password in args for unused_query, args in cursor.queries
        ))

    def test_password_change_updates_loopback_account(self):
        connection = FakeConnection()
        cursor = FakeCursor()
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.changePassword('site_user', 'new-hash', encrypt=1))

        self.assertIn(
            ('SET PASSWORD FOR %s@%s = %s',
             ('site_user', 'localhost', 'new-hash')),
            cursor.queries,
        )
        self.assertIn(
            ('SET PASSWORD FOR %s@%s = %s',
             ('site_user', '127.0.0.1', 'new-hash')),
            cursor.queries,
        )

    def test_cleartext_password_change_is_bound(self):
        connection = FakeConnection()
        cursor = FakeCursor()
        password = "new $pass;'word"
        with patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(
                1,
                mysqlUtilities.changePassword('site_user', password),
            )

        self.assertIn(
            ('ALTER USER %s@%s IDENTIFIED BY %s',
             ('site_user', 'localhost', password)),
            cursor.queries,
        )
        sql = '\n'.join(query for query, unused_args in cursor.queries)
        self.assertNotIn(password, sql)


class RusticDatabaseRestoreTests(unittest.TestCase):

    @patch('plogical.mysqlUtilities.subprocess.Popen')
    def test_rustic_dump_is_piped_to_mysql_with_defaults_file(self, popen):
        dump_process = MagicMock(returncode=0)
        dump_process.stdout = MagicMock()
        import_process = MagicMock(returncode=0)
        popen.side_effect = [dump_process, import_process]

        result = mysqlUtilities.restoreRusticDatabase(
            'site_db', '/home/site/incrementalbackups', 'siteuser',
            'snapshot-id', 'root', 'localhost', '3306',
        )

        self.assertEqual(result, 1)
        dump_command = popen.call_args_list[0].args[0]
        import_command = popen.call_args_list[1].args[0]
        self.assertEqual(dump_command[:3], ['sudo', '-u', 'siteuser'])
        self.assertIn('snapshot-id:site_db.sql', dump_command)
        self.assertIn('--defaults-file=/home/cyberpanel/.my.cnf', import_command)
        self.assertNotIn('--defaults--file=/home/cyberpanel/.my.cnf', import_command)

    @patch('plogical.mysqlUtilities.subprocess.Popen')
    def test_failed_mysql_import_is_reported(self, popen):
        dump_process = MagicMock(returncode=0)
        dump_process.stdout = MagicMock()
        import_process = MagicMock(returncode=1)
        popen.side_effect = [dump_process, import_process]

        result = mysqlUtilities.restoreRusticDatabase(
            'site_db', '/home/site/incrementalbackups', 'siteuser',
            'snapshot-id', 'root', 'localhost', '3306',
        )

        self.assertEqual(result, 0)


if __name__ == '__main__':
    unittest.main()
