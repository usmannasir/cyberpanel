"""Run only on an explicitly selected MySQL test host; use disposable databases."""
import os
import secrets
import shlex
import subprocess
import types
import unittest
from unittest import mock

from install.test_fresh_email_filter_schema import installer_class


class MySQLCursor:
    def __init__(self, database):
        self.database = database
        self.rows = []

    def execute(self, sql):
        result = subprocess.run(['mysql', '--batch', '--skip-column-names',
                                 '--database=' + self.database], input=sql,
                                text=True, capture_output=True, check=True)
        self.rows = [tuple(row.split('\t')) for row in result.stdout.splitlines()]

    def fetchone(self):
        return self.rows[0] if self.rows else None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass  # Each CLI invocation owns and closes its connection.


class Connection:
    def __init__(self, database):
        self.database = database

    def cursor(self):
        return MySQLCursor(self.database)

    def commit(self):
        pass  # DDL and the CLI use autocommit.


def initialize_from_installer(database):
    """Run the actual installer child payload against only this disposable DB."""
    connection = Connection(database)
    db_module = types.ModuleType('django.db'); db_module.connection = connection
    django_module = types.ModuleType('django'); django_module.__path__ = []
    cls = installer_class({'os': os, 'shlex': shlex})

    def child(command, distro, bracket, message, log, do_exit, code):
        argv = shlex.split(command)
        if argv[1:4] != ['manage.py', 'shell', '-c']:
            raise AssertionError('Unexpected installer schema command')
        with mock.patch.dict('sys.modules', {'django': django_module, 'django.db': db_module}):
            exec(argv[4], {})
        return True

    cls.call = staticmethod(child)
    cls.initialize_email_filter_schema(types.SimpleNamespace(distro=0))


@unittest.skipUnless(os.environ.get('CYBERPANEL_TEST_MYSQL') == '1',
                     'requires an explicitly selected MySQL test host')
class EmailSchemaIntegrationTests(unittest.TestCase):
    def test_legacy_charsets_creation_preservation_and_domain_cascade(self):
        for charset, collation in (('latin1', 'latin1_swedish_ci'),
                                   ('utf8mb3', 'utf8mb3_general_ci'),
                                   ('utf8mb4', 'utf8mb4_unicode_ci')):
            with self.subTest(charset=charset):
                database = 'cp_schema_gate_' + secrets.token_hex(8)
                subprocess.run(['mysql', '-e', 'CREATE DATABASE `%s` DEFAULT CHARACTER SET utf8mb4' % database],
                               check=True)
                try:
                    cursor = MySQLCursor(database)
                    cursor.execute('CREATE TABLE e_domains (domain varchar(50) PRIMARY KEY) '
                                   'ENGINE=InnoDB DEFAULT CHARSET=%s COLLATE=%s' % (charset, collation))
                    if charset != 'utf8mb4':
                        with self.assertRaises(subprocess.CalledProcessError):
                            cursor.execute('CREATE TABLE broken_original (domain_id varchar(50) PRIMARY KEY, '
                                           'FOREIGN KEY(domain_id) REFERENCES e_domains(domain)) '
                                           'ENGINE=InnoDB DEFAULT CHARSET=utf8mb4')
                    initialize_from_installer(database)
                    cursor.execute("INSERT INTO e_domains VALUES ('gate.example'); "
                                   "INSERT INTO e_catchall VALUES ('gate.example','mail@gate.example',1); "
                                   "INSERT INTO e_plus_override VALUES ('gate.example',1); "
                                   "INSERT INTO e_pattern_forwarding (domain_id,pattern,destination) "
                                   "VALUES ('gate.example','*','mail@gate.example'); "
                                   "INSERT INTO e_server_settings (id,plus_addressing_enabled) VALUES (1,1)")
                    initialize_from_installer(database)
                    cursor.execute('SELECT count(*) FROM e_catchall')
                    self.assertEqual(('1',), cursor.fetchone())
                    cursor.execute('SELECT plus_addressing_enabled FROM e_server_settings WHERE id=1')
                    self.assertEqual(('1',), cursor.fetchone())
                    cursor.execute("SELECT TABLE_NAME,CHARACTER_SET_NAME,COLLATION_NAME "
                                   "FROM information_schema.COLUMNS WHERE TABLE_SCHEMA=DATABASE() "
                                   "AND TABLE_NAME IN ('e_catchall','e_plus_override','e_pattern_forwarding') "
                                   "AND COLUMN_NAME='domain_id' ORDER BY TABLE_NAME")
                    self.assertEqual([(table, charset, collation) for table in
                                      ('e_catchall','e_pattern_forwarding','e_plus_override')], cursor.rows)
                    cursor.execute("DELETE FROM e_domains WHERE domain='gate.example'")
                    for table in ('e_catchall', 'e_plus_override', 'e_pattern_forwarding'):
                        cursor.execute('SELECT count(*) FROM ' + table)
                        self.assertEqual(('0',), cursor.fetchone())
                    cursor.execute('SELECT count(*) FROM e_server_settings')
                    self.assertEqual(('1',), cursor.fetchone())
                finally:
                    subprocess.run(['mysql', '-e', 'DROP DATABASE `%s`' % database], check=True)


if __name__ == '__main__':
    unittest.main()
