"""The Multi-Server Manager tables in an upgrade: created when they can be, and never a reason to stop."""
import ast
from pathlib import Path
import sys
import unittest
from unittest.mock import MagicMock, patch

from multiServer import schema
from multiServer.test_schema import Database
from plogical import schemaMigration
from plogical.schemaMigration import ensure_multiserver_tables


class Connection(Database):
    """The tables as the fake database of the schema tests keeps them, with a connection's close()."""

    def __init__(self):
        Database.__init__(self)
        self.closed = 0
        self.denied = None

    def execute(self, statement):
        if self.denied and statement.startswith('CREATE TABLE'):
            raise RuntimeError(self.denied)
        Database.execute(self, statement)

    def close(self):
        self.closed += 1


class UpgradeTablesTests(unittest.TestCase):
    def setUp(self):
        self.database = Connection()
        self.opened = 0
        self.lines = []
        patcher = patch.object(schemaMigration.time, 'sleep')
        self.sleep = patcher.start()
        self.addCleanup(patcher.stop)

    def connect(self):
        self.opened += 1
        return self.database, self.database

    def run_step(self, connect=None):
        return ensure_multiserver_tables(connect or self.connect, self.lines.append)

    def assert_left_out(self, *reasons):
        (line,) = self.lines
        self.assertTrue(line.startswith('WARNING: The Multi-Server Manager tables were not created: '), line)
        for reason in reasons:
            self.assertIn(reason, line)
        self.assertIn('The upgrade continues without them and the feature stays off on this server', line)
        self.assertNotIn('\n', line)

    def test_usable_tables_are_created_at_once_and_nothing_is_said(self):
        self.assertIs(True, self.run_step())
        creates = [statement for statement in self.database.executed if statement.startswith('CREATE TABLE')]
        self.assertEqual([schema.create_statement(table) for table in schema.TABLES], creates)
        self.assertEqual((1, 1, 1), (self.opened, self.database.commits, self.database.closed))
        self.assertEqual([], self.lines)
        self.sleep.assert_not_called()

    def test_a_database_that_answers_a_moment_later_is_waited_for(self):
        answers = [RuntimeError("Can't connect to local server through socket"), (0, 0)]

        def connect():
            if answers:
                answer = answers.pop(0)
                if isinstance(answer, Exception):
                    raise answer
                return answer
            return self.connect()

        self.assertIs(True, self.run_step(connect))
        self.assertEqual([], self.lines)
        self.assertEqual([((5,),)] * 2, [call[:1] for call in self.sleep.call_args_list])

    def test_a_database_that_never_answers_is_one_line_and_no_failure(self):
        def connect():
            self.opened += 1
            raise RuntimeError("Can't connect to local server through socket")

        self.assertIs(False, self.run_step(connect))
        self.assertEqual(3, self.opened)
        self.assertEqual(2, self.sleep.call_count)
        self.assert_left_out("Can't connect to local server through socket")
        self.lines = []
        self.assertIs(False, self.run_step(lambda: (0, 0)))
        self.assert_left_out('the panel database could not be opened')

    def test_an_account_that_may_not_create_tables_is_one_line_and_no_failure(self):
        self.database.denied = "(1142, \"CREATE command denied to user 'cyberpanel'@'10.0.0.5' for table 'ms_nodes'\")"
        self.assertIs(False, self.run_step())
        self.assert_left_out('ms_nodes could not be created', 'CREATE command denied')
        self.assertEqual((3, 3, 0), (self.opened, self.database.closed, self.database.commits))

    def test_a_table_of_an_earlier_build_that_cannot_be_used_is_one_line_and_no_failure(self):
        self.database.columns['ms_links'].remove('pairing_key')
        del self.database.indexes[('ms_nonces', 'ms_nonces_link_nonce')]
        self.assertIs(False, self.run_step())
        self.assert_left_out('tables are not usable', 'ms_links: column pairing_key is missing',
                             'ms_nonces: no unique index on exactly (link_id, nonce)')
        self.assertFalse([statement for statement in self.database.executed
                          if statement.startswith(('DROP', 'ALTER', 'DELETE'))])

    def test_a_source_without_the_feature_is_one_line_and_no_failure(self):
        with patch.dict(sys.modules, {'multiServer.schema': None}):
            self.assertIs(False, self.run_step())
        self.assertEqual(0, self.opened)
        self.assert_left_out()

    def test_nothing_that_goes_wrong_is_raised(self):
        connection = MagicMock()
        connection.close.side_effect = RuntimeError('already gone')
        cursor = MagicMock()
        cursor.execute.side_effect = RuntimeError('server has gone away')

        def log(line):
            raise OSError('the log cannot be written')

        self.assertIs(False, ensure_multiserver_tables(lambda: (connection, cursor), log))
        self.assertEqual(3, connection.close.call_count)

    def test_a_new_installation_still_stops_when_its_tables_cannot_be_created(self):
        source = (Path(schemaMigration.__file__).parent.parent / 'install' / 'install.py').read_text()
        self.assertIn("'from plogical.schemaMigration import provision_multiserver; provision_multiserver()'", source)
        function = next(node for node in ast.parse(Path(schemaMigration.__file__).read_text()).body
                        if isinstance(node, ast.FunctionDef) and node.name == 'provision_multiserver')
        self.assertFalse([node for node in ast.walk(function) if isinstance(node, ast.Try)])

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_source_parses_as_python_3_6(self):
        ast.parse(Path(schemaMigration.__file__).read_text(), feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
