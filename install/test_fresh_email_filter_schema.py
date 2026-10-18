"""Exercise the fresh installer path with its real unmanaged-mail DDL helper."""
import ast
import io
import os
from pathlib import Path
import re
import shlex
import types
import unittest
from unittest import mock

SOURCE = Path(__file__).with_name('install.py')
TABLES = ('e_catchall', 'e_plus_override', 'e_pattern_forwarding', 'e_server_settings')


def installer_class(namespace):
    tree = ast.parse(SOURCE.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == 'preFlightsChecks')
    cls.body = [node for node in cls.body if isinstance(node, ast.FunctionDef)
                and node.name in ('download_install_CyberPanel', 'initialize_email_filter_schema')]
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace['preFlightsChecks']


class SchemaConnection:
    def __init__(self, charset='utf8mb4', collation='utf8mb4_unicode_ci', fail_table=None):
        self.metadata = (charset, collation)
        self.fail_table = fail_table
        self.base_migrated = False
        self.tables = {}
        self.statements = []
        self.commits = 0

    def cursor(self):
        connection = self

        class Cursor:
            def __enter__(self): return self
            def __exit__(self, *args): pass
            def execute(self, sql):
                connection.statements.append(sql)
                if 'information_schema.COLUMNS' in sql:
                    if not connection.base_migrated:
                        raise RuntimeError('e_domains not migrated yet')
                elif sql.startswith('CREATE TABLE'):
                    table = re.search(r'CREATE TABLE IF NOT EXISTS `([^`]+)`', sql).group(1)
                    if table == connection.fail_table:
                        raise RuntimeError('injected CREATE denial')
                    connection.tables.setdefault(table, [])
                elif sql.startswith('SELECT 1 FROM'):
                    table = re.search(r'FROM `([^`]+)`', sql).group(1)
                    if table not in connection.tables:
                        raise RuntimeError('table missing after CREATE')
            def fetchone(self): return connection.metadata
        return Cursor()

    def commit(self): self.commits += 1


class FreshEmailFilterSchemaTests(unittest.TestCase):
    def run_installer(self, connection):
        events = []
        database = types.ModuleType('django.db'); database.connection = connection
        django = types.ModuleType('django'); django.__path__ = []
        env = types.ModuleType('env_generator')
        env.build_mysql_client_config = lambda *args, **kwargs: '[client]\n'
        namespace = {
            'os': types.SimpleNamespace(chdir=mock.Mock(), chmod=mock.Mock(), EX_OSERR=os.EX_OSERR,
                path=types.SimpleNamespace(join=os.path.join, exists=lambda path: True)),
            'sys': types.SimpleNamespace(path=[]), 'shlex': shlex, 'json': __import__('json'),
            'logging': types.SimpleNamespace(InstallLog=types.SimpleNamespace(writeToFile=mock.Mock())),
            'shutil': types.SimpleNamespace(move=mock.Mock()),
            'subprocess': types.SimpleNamespace(call=mock.Mock()),
            'open': lambda path, mode='r': io.StringIO('fixture-root-password\n' if mode == 'r' else ''),
            'VERSION': '3.0', 'BUILD': 8,
        }
        cls = installer_class(namespace)
        instance = object.__new__(cls)
        instance.path = '/usr/local'; instance.cyberPanelPath = '/usr/local/CyberCP'
        instance.distro = 1; instance.remotemysql = 'OFF'
        instance.generate_secure_env_file = lambda *args: events.append('environment')

        def call(command, distro, bracket, message, log=0, do_exit=0, code=0):
            argv = shlex.split(command); events.append(argv)
            if argv[-2:] == ['manage.py', 'migrate']:
                connection.base_migrated = True
            if 'shell' in argv and '-c' in argv:
                self.assertEqual((1, 1, os.EX_OSERR), (log, do_exit, code))
                try:
                    exec(argv[argv.index('-c') + 1], {})
                except Exception as error:
                    events.append(('schema-failure', str(error)))
                    return False  # Failed required child process, without terminating the test runner.
            return True
        cls.call = staticmethod(call)
        with mock.patch.dict('sys.modules', {'django': django, 'django.db': database, 'env_generator': env}):
            try:
                instance.download_install_CyberPanel('fixture-app-password', 'One')
            except RuntimeError:
                self.last_events = events
                raise
        self.last_events = events
        return instance, events

    def test_fresh_path_initializes_all_four_tables_after_migrate_before_static(self):
        for charset, collation in (('latin1', 'latin1_swedish_ci'),
                                   ('utf8mb3', 'utf8mb3_general_ci'),
                                   ('utf8mb4', 'utf8mb4_unicode_ci')):
            with self.subTest(charset=charset):
                connection = SchemaConnection(charset, collation)
                _, events = self.run_installer(connection)
                self.assertEqual(set(TABLES), set(connection.tables))
                self.assertEqual(1, connection.commits)
                schema_index = next(i for i, event in enumerate(events) if isinstance(event, list) and 'shell' in event)
                migrate_index = next(i for i, event in enumerate(events) if isinstance(event, list) and event[-2:] == ['manage.py', 'migrate'])
                static_index = next(i for i, event in enumerate(events) if isinstance(event, list) and 'collectstatic' in event)
                self.assertLess(migrate_index, schema_index)
                self.assertLess(schema_index, static_index)
                creates = [s for s in connection.statements if s.startswith('CREATE TABLE')]
                self.assertEqual(4, len(creates))
                self.assertTrue(all('DEFAULT CHARSET=%s COLLATE=%s' % (charset, collation) in sql for sql in creates))
                self.assertEqual(4, sum(s.startswith('SELECT 1 FROM') for s in connection.statements))

    def test_each_required_table_failure_stops_before_installation_continues(self):
        for table in TABLES:
            with self.subTest(table=table):
                connection = SchemaConnection(fail_table=table)
                with self.assertRaisesRegex(RuntimeError, 'Required email filter schema'):
                    self.run_installer(connection)
                self.assertEqual(0, connection.commits)
                self.assertFalse(any(isinstance(e, list) and 'collectstatic' in e for e in self.last_events))
                self.assertTrue(any(isinstance(e, tuple) and table in e[1] for e in self.last_events))

    def test_unknown_domain_charset_stops_before_creating_tables(self):
        connection = SchemaConnection(); connection.metadata = None
        with self.assertRaisesRegex(RuntimeError, 'Required email filter schema'):
            self.run_installer(connection)
        self.assertEqual({}, connection.tables)
        self.assertEqual(0, connection.commits)


if __name__ == '__main__':
    unittest.main()
