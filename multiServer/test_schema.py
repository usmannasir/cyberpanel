"""The table statements and the check that refuses a table without its unique indexes.

A stand-in for MariaDB's information_schema is used here; multiServer/test_database.py
runs the same code against a real server.
"""
import ast
from pathlib import Path
import re
import sys
import types
import unittest
from unittest.mock import MagicMock, patch

from multiServer import schema

PLANNED = {'ms_nodes', 'ms_inventory_cache', 'ms_caps', 'ms_links', 'ms_pairing_codes', 'ms_nonces',
           'ms_sso_tickets', 'ms_sessions', 'ms_audit'}
NAME = re.compile(r'[a-z][a-z0-9_]*')
TYPE = re.compile(r'(varchar\((\d+)\)|bigint|int|smallint|tinyint\(1\)|mediumtext)( NOT NULL| DEFAULT NULL)'
                  r"( AUTO_INCREMENT| DEFAULT (0|''|'pending'))?")


class Database:
    """Answers the two information_schema questions for a set of tables."""

    def __init__(self, tables=schema.TABLES):
        self.columns = {table.name: [name for name, _ in table.columns] for table in tables}
        # (table, index name) -> (unique, [(column, prefix length), ...])
        self.indexes = {}
        for table in tables:
            self.indexes[(table.name, 'PRIMARY')] = (True, [(name, None) for name in table.primary])
            for name, columns in table.unique:
                self.indexes[(table.name, name)] = (True, [(column, None) for column in columns])
            for name, columns in table.indexes:
                self.indexes[(table.name, name)] = (False, [(column, None) for column in columns])
        self.executed = []
        self.commits = 0
        self.rows = []
        self.as_bytes = False

    def cursor(self):
        return self

    def commit(self):
        self.commits += 1

    def execute(self, statement):
        self.executed.append(statement)
        if 'information_schema.COLUMNS' in statement:
            self.rows = [(table, column) for table, columns in self.columns.items() for column in columns]
        elif 'information_schema.STATISTICS' in statement:
            assert 'NON_UNIQUE = 0' in statement
            self.rows = [(table, index, position, column, prefix)
                         for (table, index), (unique, members) in self.indexes.items() if unique
                         for position, (column, prefix) in enumerate(members, 1)]
        else:
            self.rows = []
        if self.as_bytes:
            self.rows = [tuple(value.encode() if isinstance(value, str) else value for value in row)
                         for row in self.rows]

    def fetchall(self):
        return self.rows


class StatementTests(unittest.TestCase):
    def test_every_planned_table_is_created_only_if_missing_as_innodb_with_exact_comparison(self):
        names = [table.name for table in schema.TABLES]
        self.assertEqual(len(names), len(set(names)))
        self.assertEqual(PLANNED | {'ms_entitlement'}, set(names))
        for table in schema.TABLES:
            statement = schema.create_statement(table)
            self.assertTrue(statement.startswith('CREATE TABLE IF NOT EXISTS `%s` (' % table.name), statement)
            self.assertTrue(statement.endswith(') ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin'))
            self.assertEqual(1, statement.count('PRIMARY KEY'))
            self.assertNotIn(';', statement)

    def test_every_name_is_a_plain_identifier(self):
        for table in schema.TABLES:
            names = [table.name] + [name for name, _ in table.columns] + list(table.primary)
            for name, columns in table.unique + table.indexes:
                names += [name] + list(columns)
            for constraint in table.foreign:
                names += list(constraint)
            for name in names:
                self.assertTrue(NAME.fullmatch(name), (table.name, name))

    def test_every_column_has_a_bounded_type(self):
        unbounded = []
        for table in schema.TABLES:
            for name, definition in table.columns:
                matched = TYPE.fullmatch(definition)
                self.assertTrue(matched, (table.name, name, definition))
                if matched.group(2) is not None:
                    self.assertLessEqual(int(matched.group(2)), 2048, (table.name, name))
                if matched.group(1) == 'mediumtext':
                    unbounded.append((table.name, name))
        # The one column that is not a varchar: a validated inventory, capped by its writer.
        self.assertEqual([('ms_inventory_cache', 'snapshot')], unbounded)

    def test_keys_name_existing_columns_and_parents_are_created_first(self):
        created = {}
        index_names = set()
        for table in schema.TABLES:
            columns = dict(table.columns)
            for group in (table.primary,) + tuple(members for _, members in table.unique + table.indexes):
                self.assertTrue(group and set(group) <= set(columns), (table.name, group))
            for name, _ in table.unique + table.indexes:
                self.assertNotIn(name, index_names)
                index_names.add(name)
            for name, column, parent, parent_column in table.foreign:
                self.assertNotIn(name, index_names)
                index_names.add(name)
                self.assertIn(parent, created, 'a parent table must be created before its children')
                self.assertEqual((parent_column,), created[parent].primary)
                self.assertEqual(dict(created[parent].columns)[parent_column], columns[column])
            created[table.name] = table

    def test_the_unique_indexes_the_design_rests_on_are_required(self):
        required = {table.name: schema.required_unique(table) for table in schema.TABLES}
        self.assertIn(('link_id', 'nonce'), required['ms_nonces'])
        self.assertIn(('pairing_key',), required['ms_links'])
        for name, key in (('ms_nodes', 'link_id'), ('ms_links', 'link_id'), ('ms_pairing_codes', 'public_key'),
                          ('ms_sso_tickets', 'ticket_hash'), ('ms_caps', 'token_hash'),
                          ('ms_sessions', 'session_key'), ('ms_inventory_cache', 'link_id'),
                          ('ms_entitlement', 'id'), ('ms_audit', 'id'), ('ms_nonces', 'id')):
            self.assertEqual((key,), required[name][0])
        for table in schema.TABLES:
            statement = schema.create_statement(table)
            for columns in schema.required_unique(table)[1:]:
                self.assertIn('UNIQUE KEY', statement)
                self.assertIn('(%s)' % ', '.join('`%s`' % column for column in columns), statement)

    def test_the_audit_table_has_no_column_for_a_body_or_a_secret(self):
        audit = next(table for table in schema.TABLES if table.name == 'ms_audit')
        self.assertEqual(('id', 'at', 'event', 'outcome', 'reason', 'link_id', 'actor', 'source_ip', 'method',
                          'path', 'status', 'size', 'dropped'), tuple(name for name, _ in audit.columns))
        for name, definition in audit.columns:
            width = TYPE.fullmatch(definition).group(2)
            self.assertLessEqual(int(width or 0), 255, name)

    def test_secrets_of_other_parties_are_stored_only_as_hashes_or_public_keys(self):
        names = {name for table in schema.TABLES for name, _ in table.columns}
        for forbidden in ('code', 'seed', 'ticket', 'token', 'capability', 'private_key', 'password', 'secret',
                          'signature', 'body'):
            self.assertNotIn(forbidden, names)


class CheckTests(unittest.TestCase):
    def test_tables_as_created_have_no_problems(self):
        database = Database()
        self.assertEqual([], schema.problems(database))
        database.as_bytes = True
        self.assertEqual([], schema.problems(database))

    def test_a_missing_table_is_reported_once(self):
        database = Database()
        del database.columns['ms_nonces']
        self.assertEqual(['ms_nonces: the table is missing'], schema.problems(database))

    def test_all_tables_missing_are_all_reported(self):
        database = Database(tables=())
        self.assertEqual(['%s: the table is missing' % table.name for table in schema.TABLES],
                         schema.problems(database))

    def test_a_missing_column_is_reported(self):
        database = Database()
        database.columns['ms_links'].remove('generation')
        self.assertEqual(['ms_links: column generation is missing'], schema.problems(database))

    def test_a_table_without_a_required_unique_index_is_reported(self):
        for table, index, columns in (('ms_nonces', 'ms_nonces_link_nonce', 'link_id, nonce'),
                                      ('ms_links', 'ms_links_pairing', 'pairing_key'),
                                      ('ms_pairing_codes', 'PRIMARY', 'public_key')):
            database = Database()
            del database.indexes[(table, index)]
            self.assertEqual(['%s: no unique index on exactly (%s)' % (table, columns)], schema.problems(database))

    def test_an_index_that_does_not_enforce_the_same_rule_is_not_accepted(self):
        weaker = (
            (False, [('link_id', None), ('nonce', None)]),                      # not unique
            (True, [('link_id', None), ('nonce', None), ('seen_at', None)]),    # unique only with a third column
            (True, [('nonce', None), ('link_id', None)]),                       # another order is another index
            (True, [('link_id', None)]),                                        # would allow one nonce per link
            (True, [('link_id', None), ('nonce', 8)]),                          # only the first characters
        )
        for replacement in weaker:
            database = Database()
            database.indexes[('ms_nonces', 'ms_nonces_link_nonce')] = replacement
            self.assertEqual(['ms_nonces: no unique index on exactly (link_id, nonce)'],
                             schema.problems(database), replacement)

    def test_a_unique_index_under_another_name_is_accepted(self):
        database = Database()
        database.indexes[('ms_nonces', 'renamed')] = database.indexes.pop(('ms_nonces', 'ms_nonces_link_nonce'))
        self.assertEqual([], schema.problems(database))


class EnsureTests(unittest.TestCase):
    def test_creates_each_table_in_order_commits_once_and_checks(self):
        database = Database()
        schema.ensure_tables(database, database)
        creates = [statement for statement in database.executed if statement.startswith('CREATE TABLE')]
        self.assertEqual([schema.create_statement(table) for table in schema.TABLES], creates)
        self.assertEqual(creates, database.executed[:len(creates)])
        self.assertEqual(2, len(database.executed) - len(creates))
        self.assertEqual(1, database.commits)

    def test_stops_when_an_existing_table_lacks_a_unique_index(self):
        database = Database()
        del database.indexes[('ms_nonces', 'ms_nonces_link_nonce')]
        with self.assertRaisesRegex(RuntimeError,
                                    r'not usable: ms_nonces: no unique index on exactly \(link_id, nonce\)'):
            schema.ensure_tables(database, database)

    def test_a_failed_statement_names_its_table_and_nothing_is_committed(self):
        connection, cursor = MagicMock(), MagicMock()
        cursor.execute.side_effect = [None, RuntimeError('errno 150')]
        with self.assertRaisesRegex(RuntimeError, 'ms_inventory_cache could not be created: errno 150'):
            schema.ensure_tables(connection, cursor)
        connection.commit.assert_not_called()


class ReadyTests(unittest.TestCase):
    """ready() is asked on every request once a role is set, with Django's own connection."""

    def setUp(self):
        self.database = Database()
        django = types.ModuleType('django')
        django.db = types.ModuleType('django.db')
        django.db.connection = MagicMock()
        django.db.connection.cursor.return_value.__enter__.return_value = self.database
        self.connection = django.db.connection
        self.clock = MagicMock(return_value=1000.0)
        for patcher in (patch.dict(sys.modules, {'django': django, 'django.db': django.db}),
                        patch.object(schema, '_READY', False), patch.object(schema, '_RECHECK_AT', 0),
                        patch.object(schema.time, 'monotonic', self.clock)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_true_for_usable_tables_and_then_not_asked_again(self):
        self.assertIs(True, schema.ready())
        self.clock.return_value += 86400
        self.assertIs(True, schema.ready())
        self.assertEqual(1, self.connection.cursor.call_count)

    def test_false_is_remembered_for_thirty_seconds_and_no_longer(self):
        index = self.database.indexes.pop(('ms_nonces', 'ms_nonces_link_nonce'))
        self.assertIs(False, schema.ready())
        for _ in range(50):
            self.assertIs(False, schema.ready())
        self.assertEqual(1, self.connection.cursor.call_count, 'a failed check is not repeated for every request')
        self.database.indexes[('ms_nonces', 'ms_nonces_link_nonce')] = index
        self.clock.return_value += schema.RECHECK_SECONDS - 0.5
        self.assertIs(False, schema.ready())
        self.assertEqual(1, self.connection.cursor.call_count)
        self.clock.return_value += 0.5
        self.assertIs(True, schema.ready(), 'tables repaired or created meanwhile are noticed without a restart')
        self.assertEqual(2, self.connection.cursor.call_count)
        self.assertEqual(30, schema.RECHECK_SECONDS)

    def test_tables_that_stay_unusable_are_looked_at_once_in_each_period(self):
        del self.database.indexes[('ms_nonces', 'ms_nonces_link_nonce')]
        for second in range(95):
            self.assertIs(False, schema.ready())
            self.clock.return_value += 1
        self.assertEqual(4, self.connection.cursor.call_count)

    def test_never_raises_and_creates_nothing(self):
        self.connection.cursor.side_effect = RuntimeError('database is down')
        self.assertIs(False, schema.ready())
        self.assertIs(False, schema.ready())
        self.assertEqual(1, self.connection.cursor.call_count, 'a database that is down is not asked again at once')
        self.connection.cursor.side_effect = None
        self.clock.return_value += schema.RECHECK_SECONDS
        self.assertIs(True, schema.ready())
        self.assertFalse([statement for statement in self.database.executed if not statement.startswith('SELECT')])


class CompatibilityTests(unittest.TestCase):
    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_source_parses_as_python_3_6(self):
        ast.parse(Path(schema.__file__).read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
