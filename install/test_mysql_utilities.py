#!/usr/bin/env python3
"""
Tests for the installer's database preparation.

The behaviour these pin down was found by installing against a real remote
MySQL server: when the administrative connection was unusable,
createDatabase() created nothing, said nothing, and returned a value the
caller ignored. The installation continued and failed several steps later at
`manage.py migrate` against an application account that had never been
created, which points the installer at the wrong credential entirely.

No server is contacted; the client library is stubbed.

    python3 -m unittest install.test_mysql_utilities -v
"""

import json
import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import mysqlUtilities as mu  # noqa: E402
from mysqlUtilities import MySQLSetupError, mysqlUtilities  # noqa: E402


class FakeCursor(object):
    def __init__(self, fail_on=None):
        self.statements = []
        self._fail_on = fail_on

    def execute(self, sql, args=None):
        self.statements.append((sql, args))
        if self._fail_on and self._fail_on in sql:
            raise RuntimeError('statement rejected by the server')

    def close(self):
        pass


class FakeConnection(object):
    def __init__(self, cursor):
        self._cursor = cursor
        self.committed = False
        self.closed = False

    def cursor(self):
        return self._cursor

    def commit(self):
        self.committed = True

    def close(self):
        self.closed = True


class CreateDatabaseTests(unittest.TestCase):
    def setUp(self):
        self.reported = []
        patcher = mock.patch.object(mysqlUtilities, '_report',
                                    side_effect=self.reported.append)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _with_connection(self, cursor, params=None, remote=1):
        conn = FakeConnection(cursor)
        params = params or {'host': 'db.example.com', 'port': 3307,
                            'user': 'admin', 'passwd': 'secret'}
        c1 = mock.patch.object(mysqlUtilities, '_load_admin_connection',
                               return_value=(params, remote))
        c2 = mock.patch.object(mysqlUtilities, '_connect', return_value=conn)
        c1.start(); c2.start()
        self.addCleanup(c1.stop); self.addCleanup(c2.stop)
        return conn

    def _sql(self, cursor):
        return ' | '.join(s for s, _ in cursor.statements)

    # --- the regression -------------------------------------------------

    def test_unreachable_admin_connection_fails_and_explains_itself(self):
        c1 = mock.patch.object(
            mysqlUtilities, '_load_admin_connection',
            return_value=({'host': 'db.example.com', 'port': 3306,
                           'user': 'admin', 'passwd': 'x'}, 1))
        c2 = mock.patch.object(
            mysqlUtilities, '_connect',
            side_effect=MySQLSetupError(
                "Cannot connect to MySQL at db.example.com:3306 as 'admin': "
                "Access denied"))
        c1.start(); c2.start()
        self.addCleanup(c1.stop); self.addCleanup(c2.stop)

        result = mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel',
                                               'pw', '203.0.113.4')

        self.assertEqual(result, 0, 'an unusable admin connection must fail')
        self.assertTrue(self.reported, 'the reason must be reported')
        self.assertIn('Cannot connect', self.reported[0])
        self.assertIn('db.example.com', self.reported[0])

    def test_statement_failure_is_reported_not_swallowed(self):
        cursor = FakeCursor(fail_on='CREATE USER')
        self._with_connection(cursor)
        result = mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel',
                                               'pw', '203.0.113.4')
        self.assertEqual(result, 0)
        self.assertTrue(self.reported)

    # --- credential handling --------------------------------------------

    def test_password_is_bound_never_interpolated(self):
        cursor = FakeCursor()
        self._with_connection(cursor)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel',
                                      "p'w#1 $x", '203.0.113.4')
        for sql, args in cursor.statements:
            self.assertNotIn("p'w#1 $x", sql,
                             'the password must never be part of the SQL text')
        bound = [a for _, a in cursor.statements if a and "p'w#1 $x" in a]
        self.assertTrue(bound, 'the password must be passed as a bound value')

    def test_no_shell_and_no_password_in_argv(self):
        cursor = FakeCursor()
        self._with_connection(cursor)
        with mock.patch.object(mu.subprocess, 'call') as call, \
                mock.patch.object(mu.subprocess, 'Popen') as popen:
            mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                          '203.0.113.4')
        call.assert_not_called()
        popen.assert_not_called()

    # --- identifiers -----------------------------------------------------

    def test_unsafe_identifiers_are_refused(self):
        for name, user in (('cyber panel', 'cyberpanel'),
                           ('cyberpanel', 'user`; DROP'),
                           ('cyber`panel', 'cyberpanel'),
                           ('', 'cyberpanel')):
            self.reported[:] = []
            result = mysqlUtilities.createDatabase(name, user, 'pw',
                                                   '203.0.113.4')
            self.assertEqual(result, 0, 'refused: %r/%r' % (name, user))
            self.assertTrue(self.reported)

    # --- account host ----------------------------------------------------

    def test_remote_account_is_scoped_to_the_panel_address(self):
        cursor = FakeCursor()
        self._with_connection(cursor, remote=1)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                      '203.0.113.4')
        hosts = {a[1] for _, a in cursor.statements if a and len(a) > 1}
        self.assertIn('203.0.113.4', hosts)
        self.assertNotIn('localhost', hosts)

    def test_local_account_stays_on_localhost(self):
        cursor = FakeCursor()
        self._with_connection(cursor, params={'host': 'localhost', 'port': 3306,
                                              'user': 'root', 'passwd': 'x'},
                              remote=0)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                      '203.0.113.4')
        hosts = {a[1] for _, a in cursor.statements if a and len(a) > 1}
        self.assertEqual(hosts, {'localhost'})

    # --- provider quirks preserved ---------------------------------------

    def test_digitalocean_gets_native_password(self):
        cursor = FakeCursor()
        self._with_connection(cursor, params={'host': 'db.ondigitalocean.com',
                                              'port': 25060, 'user': 'doadmin',
                                              'passwd': 'x'}, remote=1)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                      '203.0.113.4')
        self.assertIn('mysql_native_password', self._sql(cursor))

    def test_rds_gets_the_restricted_grant(self):
        cursor = FakeCursor()
        self._with_connection(cursor, params={'host': 'x.rds.amazonaws.com',
                                              'port': 3306, 'user': 'admin',
                                              'passwd': 'x'}, remote=1)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                      '203.0.113.4')
        sql = self._sql(cursor)
        self.assertIn('GRANT INDEX, DROP, UPDATE', sql)
        self.assertNotIn('GRANT ALL PRIVILEGES', sql)

    def test_ordinary_remote_gets_all_privileges(self):
        cursor = FakeCursor()
        self._with_connection(cursor, remote=1)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                      '203.0.113.4')
        self.assertIn('GRANT ALL PRIVILEGES', self._sql(cursor))

    # --- success ---------------------------------------------------------

    def test_success_creates_database_user_and_grant_then_commits(self):
        cursor = FakeCursor()
        conn = self._with_connection(cursor)
        result = mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel',
                                               'pw', '203.0.113.4')
        sql = self._sql(cursor)
        self.assertEqual(result, 1)
        self.assertIn('CREATE DATABASE', sql)
        self.assertIn('CREATE USER', sql)
        self.assertIn('GRANT', sql)
        self.assertIn('FLUSH PRIVILEGES', sql)
        self.assertTrue(conn.committed)
        self.assertTrue(conn.closed)
        self.assertFalse(self.reported)

    def test_rerun_is_tolerated(self):
        """A retried installation must not fail because the database or the
        account already exists."""
        cursor = FakeCursor()
        self._with_connection(cursor)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel', 'pw',
                                      '203.0.113.4')
        sql = self._sql(cursor)
        self.assertIn('CREATE DATABASE IF NOT EXISTS', sql)
        self.assertIn('CREATE USER IF NOT EXISTS', sql)

    def test_rerun_refreshes_the_existing_application_password(self):
        """The generated password changes on a retry, so an existing account
        must be updated to match the newly generated .env value."""
        cursor = FakeCursor()
        self._with_connection(cursor)
        mysqlUtilities.createDatabase('cyberpanel', 'cyberpanel',
                                      'NewAppPw456', '203.0.113.4')
        changes = [
            args for sql, args in cursor.statements
            if sql.startswith('ALTER USER')
        ]
        self.assertIn(
            ('cyberpanel', '203.0.113.4', 'NewAppPw456'), changes)


class LoadAdminConnectionTests(unittest.TestCase):
    def _write(self, content):
        tmp = tempfile.NamedTemporaryFile('w', suffix='.json', delete=False)
        tmp.write(content)
        tmp.close()
        self.addCleanup(os.unlink, tmp.name)
        return tmp.name

    def test_remote_json_is_read_as_the_remote_endpoint(self):
        path = self._write(json.dumps({
            'mysqlhost': 'db.example.com', 'mysqlport': '3307',
            'mysqluser': 'cpadmin', 'mysqlpassword': 'secret'}))
        with open(path) as handle:
            content = handle.read()
        with mock.patch.object(mu, 'open', mock.mock_open(read_data=content),
                               create=True):
            params, remote = mysqlUtilities._load_admin_connection()
        self.assertEqual(remote, 1)
        self.assertEqual(params['host'], 'db.example.com')
        self.assertEqual(params['port'], 3307)
        self.assertEqual(params['user'], 'cpadmin')

    def test_local_plaintext_is_read_as_root_on_localhost(self):
        with mock.patch.object(mu, 'open', mock.mock_open(
                read_data='rootpassword\nignored\n'), create=True):
            params, remote = mysqlUtilities._load_admin_connection()
        self.assertEqual(remote, 0)
        self.assertEqual(params['host'], 'localhost')
        self.assertEqual(params['user'], 'root')
        self.assertEqual(params['passwd'], 'rootpassword')

    def test_local_password_that_looks_like_json_stays_local(self):
        with mock.patch.object(mu, 'open', mock.mock_open(read_data='123\n'),
                               create=True):
            params, remote = mysqlUtilities._load_admin_connection()
        self.assertEqual(remote, 0)
        self.assertEqual(params['passwd'], '123')

    def test_malformed_remote_json_is_not_treated_as_a_local_password(self):
        content = '{"mysqlhost": "db.example.com", "mysqlport": "bad"}'
        with mock.patch.object(mu, 'open', mock.mock_open(read_data=content),
                               create=True):
            with self.assertRaises(MySQLSetupError):
                mysqlUtilities._load_admin_connection()


if __name__ == '__main__':
    unittest.main()
