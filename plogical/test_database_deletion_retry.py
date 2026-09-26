"""Retry real deletion methods with isolated SQL and website dependencies."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest import mock

import test_unix_account_deletion as website_tests

HERE = Path(__file__).resolve().parent


def database_helper(connection, cursor):
    tree = ast.parse((HERE / 'mysqlUtilities.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'mysqlUtilities')
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)
               and n.name in ('quoteIdentifier', 'deleteDatabase')]
    cls.body = methods
    scope = {'ProcessUtilities': NS(executioner=mock.Mock()),
             'logging': NS(CyberCPLogFileWriter=NS(writeToFile=mock.Mock()))}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(HERE / 'mysqlUtilities.py'), 'exec'), scope)
    helper = scope['mysqlUtilities']
    helper.setupConnection = lambda: (connection, cursor)
    return helper


class DatabaseDeletionTests(unittest.TestCase):
    def setUp(self):
        self.connection = mock.Mock()
        self.cursor = mock.Mock()
        self.cursor.fetchall.return_value = [('fixtureuser', 'localhost')]
        self.helper = database_helper(self.connection, self.cursor)

    def test_missing_database_is_idempotent_and_cleans_grants(self):
        self.assertEqual(1, self.helper.deleteDatabase('fixturedb', 'fixtureuser'))
        self.assertEqual([
            mock.call('DROP DATABASE IF EXISTS `fixturedb`'),
            mock.call('select user,host from mysql.db where db=%s', ('fixturedb',)),
            mock.call('DROP USER IF EXISTS %s@%s', ('fixtureuser', 'localhost')),
        ], self.cursor.execute.call_args_list)
        self.connection.close.assert_called_once()

    def test_database_identifiers_are_quoted(self):
        self.helper.deleteDatabase('fixture`db', 'fixtureuser')
        self.assertEqual('DROP DATABASE IF EXISTS `fixture``db`', self.cursor.execute.call_args_list[0].args[0])

    def test_real_database_errors_still_fail_and_close_connection(self):
        for failure in ('access denied', 'server disconnected', 'cannot remove directory'):
            with self.subTest(failure=failure):
                self.connection.reset_mock()
                self.cursor.execute.side_effect = RuntimeError(failure)
                self.assertEqual(failure, self.helper.deleteDatabase('fixturedb', 'fixtureuser'))
                self.connection.close.assert_called_once()

    def test_missing_connection_fails(self):
        helper = database_helper(0, None)
        self.assertEqual(0, helper.deleteDatabase('fixturedb', 'fixtureuser'))


class WebsiteDatabaseRetryTests(unittest.TestCase):
    setUp = website_tests.UnixAccountDeletionTests.setUp
    deletion = website_tests.UnixAccountDeletionTests.deletion

    def test_sql_cleanup_failure_retains_panel_row(self):
        self.scope['mysqlUtilities'].deleteDatabase = lambda *args: 'access denied'
        self.assertEqual(0, self.deletion())
        self.assertTrue(self.row_exists)
        self.assertNotIn('website-row-delete', self.events)

    def test_virtual_host_failure_does_not_delete_database_or_panel_row(self):
        self.vhost.deleteCoreConf = lambda *args: 0
        self.assertEqual(0, self.deletion())
        self.assertTrue(self.row_exists)
        self.assertNotIn('database-delete', self.events)

    def test_missing_database_retry_completes_worker(self):
        cursor = mock.Mock()
        cursor.fetchall.return_value = []
        self.scope['mysqlUtilities'] = database_helper(mock.Mock(), cursor)
        self.assertEqual(1, self.deletion())
        self.assertFalse(self.row_exists)
        self.assertIn('resource-limits', self.events)


class ResourceLimitsUserTests(unittest.TestCase):
    def test_resource_lookup_uses_website_unix_account(self):
        tree = ast.parse((HERE.parent / 'websiteFunctions/website.py').read_text())
        block = next(node for node in ast.walk(tree) if isinstance(node, ast.If)
                     and isinstance(node.test, ast.Call) and node.test.args
                     and isinstance(node.test.args[0], ast.Name)
                     and node.test.args[0].id == 'lscgctl_path')
        run = mock.Mock(return_value=NS(returncode=1))
        scope = {'website': NS(externalApp='fixtureunix'), 'lscgctl_path': '/fixture/lscgctl',
                 'subprocess': NS(run=run, PIPE=-1)}
        exec(compile(ast.Module(body=block.body, type_ignores=[]), 'resource-limits', 'exec'), scope)
        self.assertEqual(['/fixture/lscgctl', 'list-user', 'fixtureunix'], run.call_args.args[0])


@unittest.skipUnless(__import__('os').environ.get('CYBERPANEL_DELETE_DB_INTEGRATION') == '1',
                     'requires local MariaDB fixture access')
class MariaDBDeletionIntegrationTests(unittest.TestCase):
    def test_missing_database_with_retained_grants_can_be_retried(self):
        import MySQLdb
        import uuid
        name = 'cpdel_' + uuid.uuid4().hex[:16]
        control = MySQLdb.connect(read_default_file=__import__('os').path.expanduser('~/.my.cnf'),
                                    user='root', unix_socket='/run/mysqld/mysqld.sock')
        cursor = control.cursor()
        try:
            cursor.execute('CREATE DATABASE `' + name + '`')
            cursor.execute('CREATE USER %s@%s', (name, 'localhost'))
            cursor.execute('GRANT ALL ON `' + name + '`.* TO %s@%s', (name, 'localhost'))
            cursor.execute('DROP DATABASE `' + name + '`')
            with self.assertRaises(MySQLdb.OperationalError) as failure:
                cursor.execute('DROP DATABASE `' + name + '`')
            self.assertEqual(1008, failure.exception.args[0])
            for _ in range(2):
                connection = MySQLdb.connect(read_default_file=__import__('os').path.expanduser('~/.my.cnf'),
                                    user='root', unix_socket='/run/mysqld/mysqld.sock')
                helper = database_helper(connection, connection.cursor())
                self.assertEqual(1, helper.deleteDatabase(name, name))
            cursor.execute('SELECT COUNT(*) FROM mysql.user WHERE User=%s', (name,))
            self.assertEqual(0, cursor.fetchone()[0])
            cursor.execute('SELECT COUNT(*) FROM mysql.db WHERE Db=%s', (name,))
            self.assertEqual(0, cursor.fetchone()[0])
        finally:
            cursor.execute('DROP DATABASE IF EXISTS `' + name + '`')
            cursor.execute('DROP USER IF EXISTS %s@%s', (name, 'localhost'))
            control.close()
