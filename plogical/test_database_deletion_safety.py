"""Retry real deletion methods with isolated SQL and website dependencies."""
import ast
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest import mock


HERE = Path(__file__).resolve().parent


def database_helper(connection, cursor):
    tree = ast.parse((HERE / 'mysqlUtilities.py').read_text())
    cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'mysqlUtilities')
    methods = [n for n in cls.body if isinstance(n, ast.FunctionDef)
               and n.name in ('quoteIdentifier', 'deleteDatabase', 'submitDBDeletion')]
    cls.body = methods
    scope = {'ProcessUtilities': NS(executioner=mock.Mock()),
             'logging': NS(CyberCPLogFileWriter=NS(writeToFile=mock.Mock()))}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(HERE / 'mysqlUtilities.py'), 'exec'), scope)
    helper = scope['mysqlUtilities']
    helper.setupConnection = lambda: (connection, cursor)
    helper.test_scope = scope
    return helper


class DatabaseDeletionTests(unittest.TestCase):
    def setUp(self):
        self.connection = mock.Mock()
        self.cursor = mock.Mock()
        self.cursor.fetchall.return_value = [('fixtureuser', 'localhost')]
        self.helper = database_helper(self.connection, self.cursor)

    def test_database_names_never_reach_a_filesystem_command(self):
        # Leading whitespace previously split /var/lib/mysql/ into a separate
        # rm operand, destroying every local database before SQL was contacted.
        for name in (' leading_space', 'two words', '../escape', 'db;touch sentinel',
                     'db$(touch sentinel)', 'db`name'):
            with self.subTest(name=name):
                self.cursor.reset_mock()
                self.assertEqual(1, self.helper.deleteDatabase(name, 'fixtureuser'))
                self.helper.test_scope['ProcessUtilities'].executioner.assert_not_called()
                self.cursor.execute.assert_any_call(
                    'DROP DATABASE IF EXISTS ' + self.helper.quoteIdentifier(name))

    def test_sql_connection_failure_performs_no_filesystem_cleanup(self):
        helper = database_helper(0, None)
        self.assertEqual(0, helper.deleteDatabase(' leading_space', 'fixtureuser'))
        helper.test_scope['ProcessUtilities'].executioner.assert_not_called()

    def test_failed_sql_drop_retains_panel_registration_for_retry(self):
        row = mock.Mock(dbUser='fixtureuser')
        self.helper.test_scope['Databases'] = NS(objects=NS(get=mock.Mock(return_value=row)))
        self.cursor.execute.side_effect = RuntimeError('cannot remove directory')
        self.assertEqual((0, 'cannot remove directory'), self.helper.submitDBDeletion('fixturedb'))
        row.delete.assert_not_called()

    def test_successful_sql_drop_removes_panel_registration(self):
        row = mock.Mock(dbUser='fixtureuser')
        self.helper.test_scope['Databases'] = NS(objects=NS(get=mock.Mock(return_value=row)))
        self.assertEqual((1, 'None'), self.helper.submitDBDeletion('fixturedb'))
        row.delete.assert_called_once_with()

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


if __name__ == "__main__":
    unittest.main()
