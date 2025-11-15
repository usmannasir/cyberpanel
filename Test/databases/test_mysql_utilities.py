import sys
import types
import unittest
from unittest import mock

# Provide minimal stubs when running tests outside the target servers.
if 'django' not in sys.modules:
    django_stub = types.ModuleType("django")
    django_stub.setup = lambda: None
    sys.modules['django'] = django_stub

if 'MySQLdb' not in sys.modules:
    mysql_stub = types.ModuleType("MySQLdb")
    mysql_stub.connect = lambda *args, **kwargs: None
    cursors_stub = types.SimpleNamespace(SSCursor=object)
    mysql_stub.cursors = cursors_stub
    sys.modules['MySQLdb'] = mysql_stub
    sys.modules['MySQLdb.cursors'] = types.ModuleType("MySQLdb.cursors")
    sys.modules['MySQLdb.cursors'].SSCursor = object

from plogical import mysqlUtilities


class DummyConnection:
    def __init__(self, literal_side_effect=None):
        self.literal_calls = []
        self.literal_side_effect = literal_side_effect
        self.closed = False

    def literal(self, value):
        if self.literal_side_effect:
            raise self.literal_side_effect
        self.literal_calls.append(value)
        return f"'{value}'"

    def close(self):
        self.closed = True


class DummyCursor:
    def __init__(self):
        self.executed = []
        self.fetchone_value = None

    def execute(self, query, params=None):
        self.executed.append((query, params))

    def fetchone(self):
        return self.fetchone_value


class MysqlUtilitiesChangePasswordTests(unittest.TestCase):
    def test_numeric_password_is_coerced_and_sanitized(self):
        connection = DummyConnection()
        cursor = DummyCursor()

        with mock.patch.object(mysqlUtilities.mysqlUtilities, 'setupConnection', return_value=(connection, cursor)), \
                mock.patch.object(mysqlUtilities.mysqlUtilities, 'resolve_mysql_username', return_value='demo_user'), \
                mock.patch('plogical.mysqlUtilities.os.path.exists', return_value=False):
            result = mysqlUtilities.mysqlUtilities.changePassword('demo_user', 987654321)

        self.assertEqual(result, 1)
        self.assertIn('987654321', connection.literal_calls)
        self.assertEqual(len(cursor.executed), 2)  # USE mysql + password update
        self.assertIn("PASSWORD('987654321')", cursor.executed[-1][0])

    def test_logs_error_when_literal_fails(self):
        connection = DummyConnection(literal_side_effect=ValueError("boom"))
        cursor = DummyCursor()

        with mock.patch.object(mysqlUtilities.mysqlUtilities, 'setupConnection', return_value=(connection, cursor)), \
                mock.patch.object(mysqlUtilities.mysqlUtilities, 'resolve_mysql_username', return_value='demo_user'), \
                mock.patch('plogical.mysqlUtilities.os.path.exists', return_value=False), \
                mock.patch('plogical.mysqlUtilities.logging.CyberCPLogFileWriter.writeToFile') as log_mock:
            result = mysqlUtilities.mysqlUtilities.changePassword('demo_user', 'secret')

        self.assertEqual(result, 0)
        log_calls = [call.args[0] for call in log_mock.call_args_list]
        self.assertTrue(any('[mysqlUtilities.changePassword.literal]' in msg for msg in log_calls))


class MysqlUtilitiesResolveUserTests(unittest.TestCase):
    def test_resolves_username_when_orm_missing(self):
        class _StubManager:
            def get(self, *args, **kwargs):
                raise Exception("not found")

        dbusers_stub = types.SimpleNamespace(objects=_StubManager())
        databases_stub = types.SimpleNamespace(objects=_StubManager())

        cursor = DummyCursor()
        cursor.fetchone_value = None

        with mock.patch('plogical.mysqlUtilities.DBUsers', dbusers_stub, create=True), \
                mock.patch('plogical.mysqlUtilities.Databases', databases_stub, create=True):
            resolved = mysqlUtilities.mysqlUtilities.resolve_mysql_username('mystery_user', cursor)

        self.assertEqual(resolved, 'mystery_user')


if __name__ == "__main__":
    unittest.main()

