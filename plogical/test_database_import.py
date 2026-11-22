"""A dump is loaded by an account that may use one database, by a client that obeys no commands in it."""
import io
import os
import stat
import subprocess
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import databaseImport
from plogical import mysqlUtilities as module
from plogical.mysqlUtilities import mysqlUtilities

HELP_NEW = '  --binary-mode       Binary mode\n  --sandbox           Disallow commands\n'
HELP_OLD = '  -B, --batch\n  --binary-mode       Binary mode\n'


class Cursor:
    """Records statements and answers the few questions the import asks."""

    def __init__(self, answers=None, refuse=None):
        self.answers = dict(answers or {})
        self.refuse = refuse
        self.statements = []
        self.rows = []

    def execute(self, query, args=None):
        self.statements.append((query, args))
        self.rows = []
        if self.refuse and query.startswith(self.refuse):
            raise RuntimeError('refused by the server')
        for start, rows in self.answers.items():
            if query.startswith(start):
                self.rows = rows(args) if callable(rows) else list(rows)
                return

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def sent(self, start):
        return [(query, args) for query, args in self.statements if query.startswith(start)]


def filtered(data, sizes=(None,)):
    results = set()
    for size in sizes:
        sink = io.BytesIO()
        stream = databaseImport.DefinerFilter(sink)
        if size is None:
            stream.write(data)
        else:
            for start in range(0, len(data), size):
                stream.write(data[start:start + size])
        stream.close()
        results.add(sink.getvalue())
    assert len(results) == 1, 'the result depends on how the dump is cut into pieces'
    return results.pop()


class DefinerFilterTests(unittest.TestCase):
    SIZES = (None, 1, 2, 3, 7, 16, 64)

    def test_clauses_written_by_the_dump_programs_are_left_out(self):
        for line, expected in (
                (b"/*!50013 DEFINER=`shop_user`@`localhost` SQL SECURITY DEFINER */\n",
                 b"/*!50013 SQL SECURITY DEFINER */\n"),
                (b"/*!50003 CREATE*/ /*!50017 DEFINER=`root`@`localhost`*/ /*!50003 TRIGGER `t` BEFORE INSERT ON `a`\n",
                 b"/*!50003 CREATE*/ /*!50017 */ /*!50003 TRIGGER `t` BEFORE INSERT ON `a`\n"),
                (b"CREATE DEFINER=`shop_user`@`%` PROCEDURE `p`()\n", b"CREATE PROCEDURE `p`()\n"),
                (b"CREATE DEFINER='shop_user'@'10.0.0.%' FUNCTION `f`() RETURNS int\n",
                 b"CREATE FUNCTION `f`() RETURNS int\n"),
                (b"/*!50106 CREATE*/ /*!50117 DEFINER=`u`@`h`*/ /*!50106 EVENT `e` ON SCHEDULE EVERY 1 DAY\n",
                 b"/*!50106 CREATE*/ /*!50117 */ /*!50106 EVENT `e` ON SCHEDULE EVERY 1 DAY\n"),
                (b"CREATE ALGORITHM=UNDEFINED DEFINER=`u`@`localhost` SQL SECURITY DEFINER VIEW `v` AS select 1\n",
                 b"CREATE ALGORITHM=UNDEFINED SQL SECURITY DEFINER VIEW `v` AS select 1\n"),
                (b"CREATE OR REPLACE DEFINER = CURRENT_USER VIEW `v` AS select 1\n",
                 b"CREATE OR REPLACE VIEW `v` AS select 1\n"),
                (b"create definer=root@localhost trigger t before insert on a for each row set @x = 1\n",
                 b"create trigger t before insert on a for each row set @x = 1\n")):
            self.assertEqual(expected, filtered(line, self.SIZES), line)

    def test_table_data_and_other_statements_pass_unchanged(self):
        dump = (b"-- MariaDB dump\n/*M!999999\\- enable the sandbox mode */ \n"
                b"DROP TABLE IF EXISTS `notes`;\nCREATE TABLE `notes` (\n  `body` text COMMENT 'DEFINER=`a`@`b`'\n);\n"
                b"INSERT INTO `notes` VALUES ('CREATE DEFINER=`root`@`localhost` PROCEDURE p()'),"
                b"('/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */');\n"
                b"  DEFINER=`root`@`localhost` is text in the middle of a line\n"
                b"CREATE TABLE `definer` (`DEFINER` int);\n\xff\xfe\x00 binary\r\n")
        self.assertEqual(dump, filtered(dump, self.SIZES))

    def test_only_the_first_clause_of_a_line_is_left_out(self):
        line = b"CREATE DEFINER=`a`@`b` PROCEDURE p() SELECT 'DEFINER=`c`@`d`'\n"
        self.assertEqual(b"CREATE PROCEDURE p() SELECT 'DEFINER=`c`@`d`'\n", filtered(line, self.SIZES))

    def test_last_line_without_a_line_end_is_handled(self):
        self.assertEqual(b"CREATE PROCEDURE p() SELECT 1", filtered(b"CREATE DEFINER=`a`@`b` PROCEDURE p() SELECT 1",
                                                                     self.SIZES))

    def test_very_long_line_is_passed_on_in_pieces(self):
        sink = io.BytesIO()
        stream = databaseImport.DefinerFilter(sink)
        row = b"INSERT INTO `t` VALUES ('" + b'x' * (3 * databaseImport.CHUNK) + b"');\n"
        stream.write(row[:databaseImport.CHUNK])
        self.assertEqual(row[:databaseImport.CHUNK], sink.getvalue())  # nothing of a data line is held back
        stream.write(row[databaseImport.CHUNK:])
        stream.write(b"CREATE DEFINER=`a`@`b` PROCEDURE p() SELECT 1;\n")
        stream.close()
        self.assertEqual(row + b"CREATE PROCEDURE p() SELECT 1;\n", sink.getvalue())


class ClientOptionTests(unittest.TestCase):
    def options(self, text):
        databaseImport._options.clear()
        self.addCleanup(databaseImport._options.clear)
        with mock.patch.object(databaseImport.subprocess, 'check_output', return_value=text.encode()) as described:
            result = databaseImport.client_options()
        self.assertEqual(['mysql', '--no-defaults', '--help'], described.call_args[0][0])
        return result

    def test_client_commands_are_switched_off_with_every_option_the_client_has(self):
        self.assertEqual(['--binary-mode', '--local-infile=0', '--sandbox'], self.options(HELP_NEW))
        self.assertEqual(['--binary-mode', '--local-infile=0'], self.options(HELP_OLD))

    def test_client_that_cannot_ignore_commands_is_not_used(self):
        with self.assertRaises(databaseImport.ImportRefused):
            self.options('  -B, --batch\n  mentions --binary-mode only in a sentence\n')


class AccountTests(unittest.TestCase):
    def test_account_gets_the_exact_grant_on_the_one_database(self):
        cursor = Cursor({'SELECT SUBSTRING_INDEX': [('localhost',)], 'SHOW VARIABLES': []})
        user, host, password = databaseImport.create_account(cursor, 'shop_db', now=0x65000000)
        self.assertRegex(user, r'^cpimp_65000000_[a-z0-9]{10}$')
        self.assertEqual('localhost', host)
        self.assertRegex(password, r'^[A-Za-z0-9]{28}-aZ9$')
        self.assertEqual([('CREATE USER %s@%s IDENTIFIED BY %s', (user, 'localhost', password))],
                         cursor.sent('CREATE USER'))
        self.assertEqual([('GRANT ALL PRIVILEGES ON `shop\\_db`.* TO %s@%s', (user, 'localhost'))],
                         cursor.sent('GRANT'))
        self.assertNotIn('*.*', ' '.join(query for query, args in cursor.statements))

    def test_two_imports_never_share_an_account_or_a_password(self):
        cursor = Cursor({'SELECT SUBSTRING_INDEX': [('localhost',)], 'SHOW VARIABLES': []})
        first = databaseImport.create_account(cursor, 'shop_db')
        second = databaseImport.create_account(cursor, 'shop_db')
        self.assertNotEqual(first[0], second[0])
        self.assertNotEqual(first[2], second[2])

    def test_account_is_made_for_the_host_the_server_sees(self):
        cursor = Cursor({'SELECT SUBSTRING_INDEX': [(b'10.0.0.7',)], 'SHOW VARIABLES': []})
        self.assertEqual('10.0.0.7', databaseImport.create_account(cursor, 'shop_db')[1])
        for host in ('%', '', "x' OR '1", None):
            cursor = Cursor({'SELECT SUBSTRING_INDEX': [(host,)], 'SHOW VARIABLES': []})
            with self.assertRaises(databaseImport.ImportRefused):
                databaseImport.create_account(cursor, 'shop_db')
            self.assertEqual([], cursor.sent('CREATE USER'))

    def test_account_does_not_stay_when_its_grant_fails(self):
        cursor = Cursor({'SELECT SUBSTRING_INDEX': [('localhost',)], 'SHOW VARIABLES': []}, refuse='GRANT')
        with self.assertRaises(RuntimeError):
            databaseImport.create_account(cursor, 'shop_db')
        (query, args), = cursor.sent('DROP USER')
        self.assertEqual('DROP USER IF EXISTS %s@%s', query)
        self.assertEqual(cursor.sent('CREATE USER')[0][1][:2], args)

    def test_accounts_left_by_a_stopped_import_are_removed_after_a_day(self):
        now = 0x65000000
        old, fresh = 'cpimp_%08x_abcdefghij' % (now - 90000), 'cpimp_%08x_abcdefghij' % (now - 3600)
        cursor = Cursor({'SELECT User, Host FROM mysql.user': [(old, 'localhost'), (fresh, 'localhost'),
                                                               ('cpimp_customer', 'localhost'),
                                                               ('cpimpXdeadbeef_abcdefghij', '%')]})
        databaseImport.drop_stale_accounts(cursor, now)
        self.assertEqual([('DROP USER IF EXISTS %s@%s', (old, 'localhost'))], cursor.sent('DROP USER'))
        self.assertEqual(('cpimp\\_%',), cursor.statements[0][1])

    def test_option_file_is_private_from_the_start(self):
        with mock.patch.object(databaseImport.os, 'fchown') as chown:
            path = databaseImport.write_defaults('cpimp_1', 'secret', 'localhost', '3306', (65534, 65534))
        self.addCleanup(os.unlink, path)
        self.assertEqual(0o600, stat.S_IMODE(os.stat(path).st_mode))
        with open(path) as stream:
            self.assertEqual('[client]\nuser=cpimp_1\npassword=secret\nhost=localhost\nport=3306\n', stream.read())
        self.assertEqual((65534, 65534), chown.call_args[0][1:])

    def test_root_never_runs_the_client_itself(self):
        entry = SimpleNamespace(pw_uid=65534, pw_gid=65533)
        with mock.patch.object(databaseImport.os, 'geteuid', return_value=0), \
                mock.patch.object(databaseImport.pwd, 'getpwnam', return_value=entry):
            self.assertEqual((65534, 65533), databaseImport.client_identity())
        with mock.patch.object(databaseImport.os, 'geteuid', return_value=0), \
                mock.patch.object(databaseImport.pwd, 'getpwnam', side_effect=KeyError('nobody')):
            with self.assertRaises(databaseImport.ImportRefused):
                databaseImport.client_identity()
        with mock.patch.object(databaseImport.os, 'geteuid', return_value=0), \
                mock.patch.object(databaseImport.pwd, 'getpwnam', return_value=SimpleNamespace(pw_uid=0, pw_gid=0)):
            with self.assertRaises(databaseImport.ImportRefused):
                databaseImport.client_identity()
        with mock.patch.object(databaseImport.os, 'geteuid', return_value=1001):
            self.assertIsNone(databaseImport.client_identity())


class Client:
    def __init__(self, code=0, broken=False):
        self.returncode = code
        self.received = io.BytesIO()
        self.stdin = mock.Mock()
        self.stdin.write.side_effect = self.write
        self.broken = broken

    def write(self, data):
        if self.broken:
            raise BrokenPipeError(32, 'Broken pipe')
        self.received.write(data)

    def wait(self):
        return self.returncode


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.cursor = Cursor({'SELECT SUBSTRING_INDEX': [('localhost',)], 'SHOW VARIABLES': []})
        self.connections = []
        self.launched = []
        self.files = []
        self.identity = None
        databaseImport._options.clear()
        self.addCleanup(databaseImport._options.clear)

    def connect(self):
        connection = mock.Mock()
        self.connections.append(connection)
        return connection, self.cursor

    def run_import(self, client, feed=None, owner=None, made=None, identity=None):
        def popen(command, **options):
            self.launched.append((command, options))
            path = command[1].split('=', 1)[1]
            with open(path) as stream:
                self.files.append((path, stream.read(), stat.S_IMODE(os.stat(path).st_mode)))
            return client

        feed = feed or (lambda sink: databaseImport.copy(io.BytesIO(b'CREATE TABLE t (i int);\n'), sink))
        with mock.patch.object(databaseImport.subprocess, 'check_output', return_value=HELP_NEW.encode()), \
                mock.patch.object(databaseImport.subprocess, 'Popen', side_effect=popen), \
                mock.patch.object(databaseImport, 'client_identity', return_value=identity), \
                mock.patch.object(databaseImport.os, 'fchown'), \
                mock.patch.object(databaseImport, '_native_password', return_value=False), \
                mock.patch.object(databaseImport, '_note') as note:
            result = databaseImport.import_dump('shop_db', feed, 'localhost', '3306', owner, self.connect, made)
        self.notes = [call[0][0] for call in note.call_args_list]
        return result

    def account(self):
        return self.cursor.sent('CREATE USER')[0][1][:2]

    def test_dump_is_loaded_by_the_import_account_with_client_commands_off(self):
        client = Client()
        self.assertEqual(1, self.run_import(client))
        (command, options), = self.launched
        path, content, mode = self.files[0]
        self.assertEqual(['mysql', '--defaults-file=' + path, '--binary-mode', '--local-infile=0', '--sandbox',
                          'shop_db'], command)
        user, host = self.account()
        self.assertIn('user=%s\n' % user, content)
        self.assertNotIn('root', content)
        self.assertEqual(0o600, mode)
        self.assertNotIn('/home/cyberpanel/.my.cnf', ' '.join(command))
        self.assertEqual(b'CREATE TABLE t (i int);\n', client.received.getvalue())
        self.assertEqual({'PATH', 'LC_ALL'}, set(options['env']))
        self.assertIsNone(options['preexec_fn'])

    def test_account_and_option_file_are_gone_after_a_good_import(self):
        self.assertEqual(1, self.run_import(Client()))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', self.account())], self.cursor.sent('DROP USER'))
        self.assertFalse(os.path.exists(self.files[0][0]))
        for connection in self.connections:
            connection.close.assert_called_once_with()

    def test_account_and_option_file_are_gone_when_the_client_reports_an_error(self):
        self.assertEqual(0, self.run_import(Client(code=1)))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', self.account())], self.cursor.sent('DROP USER'))
        self.assertFalse(os.path.exists(self.files[0][0]))
        self.assertTrue(self.notes[0].startswith('Database import into shop_db stopped'))

    def test_account_is_gone_when_the_client_stops_reading(self):
        self.assertEqual(0, self.run_import(Client(code=1, broken=True)))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', self.account())], self.cursor.sent('DROP USER'))

    def test_account_is_gone_when_reading_the_dump_fails(self):
        def feed(sink):
            raise RuntimeError('the repository went away')

        self.assertEqual(0, self.run_import(Client(), feed))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', self.account())], self.cursor.sent('DROP USER'))
        self.assertFalse(os.path.exists(self.files[0][0]))

    def test_source_that_ended_badly_is_a_failed_import(self):
        self.assertEqual(0, self.run_import(Client(), lambda sink: False))
        self.assertEqual(0, self.run_import(Client(), lambda sink: 0))

    def test_client_started_by_root_changes_to_an_account_without_privileges(self):
        self.assertEqual(1, self.run_import(Client(), identity=(65534, 65534)))
        self.assertTrue(callable(self.launched[0][1]['preexec_fn']))
        with mock.patch.object(databaseImport.os, 'setgroups') as groups, \
                mock.patch.object(databaseImport.os, 'setgid') as group, \
                mock.patch.object(databaseImport.os, 'setuid') as user, mock.patch.object(databaseImport.os, 'umask'):
            order = mock.Mock()
            order.attach_mock(groups, 'setgroups')
            order.attach_mock(group, 'setgid')
            order.attach_mock(user, 'setuid')
            self.launched[0][1]['preexec_fn']()
        self.assertEqual([mock.call.setgroups([]), mock.call.setgid(65534), mock.call.setuid(65534)],
                         order.mock_calls)

    def test_nothing_is_started_without_an_administrative_connection(self):
        self.connect = lambda: (0, 0)
        self.assertEqual(0, self.run_import(Client()))
        self.assertEqual([], self.launched)

    def test_definer_clauses_do_not_reach_the_client(self):
        client = Client()
        dump = b"/*!50013 DEFINER=`root`@`localhost` SQL SECURITY DEFINER */\nINSERT INTO t VALUES (1);\n"
        self.run_import(client, lambda sink: databaseImport.copy(io.BytesIO(dump), sink))
        self.assertEqual(b"/*!50013 SQL SECURITY DEFINER */\nINSERT INTO t VALUES (1);\n", client.received.getvalue())


def owned_server(objects, hosts=('localhost',), granted=('shop\\_db',), global_privileges=('USAGE',),
                 version='10.11.20-MariaDB', statements=None):
    """A cursor of a server on which the import account made `objects` in shop_db."""
    made = dict((kind, [name for k, name in objects if k == kind]) for kind in ('VIEW', 'TRIGGER', 'PROCEDURE', 'EVENT'))
    statements = statements or {}
    answers = {
        'SELECT TABLE_NAME FROM information_schema.VIEWS': [(name,) for name in made['VIEW']],
        'SELECT TRIGGER_NAME FROM information_schema.TRIGGERS': [(name,) for name in made['TRIGGER']],
        'SELECT ROUTINE_TYPE, ROUTINE_NAME': [('PROCEDURE', name) for name in made['PROCEDURE']],
        'SELECT EVENT_NAME, ON_COMPLETION': [(name, 'NOT PRESERVE') for name in made['EVENT']],
        'SELECT Host FROM mysql.user': [(host,) for host in hosts],
        'SELECT Db FROM mysql.db': [(name,) for name in granted],
        'SELECT PRIVILEGE_TYPE': [(name,) for name in global_privileges],
        'SELECT VERSION()': [(version,)],
        'SHOW CREATE VIEW': [('v', "CREATE ALGORITHM=UNDEFINED DEFINER=`cpimp_1`@`localhost` SQL SECURITY DEFINER "
                                   "VIEW `v` AS select 100 % 7 AS `x`", 'utf8mb4', 'utf8mb4_general_ci')],
        'SHOW CREATE TRIGGER': [('trg', 'STRICT_TRANS_TABLES', "CREATE DEFINER=`cpimp_1`@`localhost` TRIGGER trg "
                                        "BEFORE INSERT ON t FOR EACH ROW SET NEW.note = 'DEFINER=`cpimp_1`@`localhost`'",
                                 'utf8mb4', 'utf8mb4_general_ci', 'utf8mb4_general_ci')],
        'SHOW CREATE PROCEDURE': [('p', '', "CREATE DEFINER=`cpimp_1`@`localhost` PROCEDURE `p`()\nSELECT 1",
                                   'utf8mb4', 'utf8mb4_general_ci', 'utf8mb4_general_ci')],
    }
    answers.update(statements)
    return Cursor(answers)


class HandOverTests(unittest.TestCase):
    ACCOUNT = ('cpimp_1', 'localhost')

    def hand_over(self, cursor, owner='shop_user'):
        with mock.patch.object(databaseImport, '_note') as note:
            result = databaseImport.hand_over(cursor, 'shop_db', self.ACCOUNT, owner)
        self.notes = [call[0][0] for call in note.call_args_list]
        return result

    def changes(self, cursor):
        return [query for query, args in cursor.statements
                if query.split()[0] in ('CREATE', 'DROP', 'ALTER', 'USE', 'SET')]

    def test_objects_made_by_the_import_go_to_the_registered_account(self):
        cursor = owned_server([('VIEW', 'v'), ('TRIGGER', 'trg'), ('PROCEDURE', 'p'), ('EVENT', 'e')])
        self.assertTrue(self.hand_over(cursor))
        self.assertEqual([
            'USE `shop_db`',
            "CREATE OR REPLACE ALGORITHM=UNDEFINED DEFINER=`shop_user`@`localhost` SQL SECURITY DEFINER "
            "VIEW `v` AS select 100 % 7 AS `x`",
            'SET SESSION sql_mode = %s',
            "CREATE OR REPLACE DEFINER=`shop_user`@`localhost` TRIGGER trg BEFORE INSERT ON t FOR EACH ROW "
            "SET NEW.note = 'DEFINER=`cpimp_1`@`localhost`'",
            'SET SESSION sql_mode = %s',
            "CREATE OR REPLACE DEFINER=`shop_user`@`localhost` PROCEDURE `p`()\nSELECT 1",
            'ALTER DEFINER=`shop_user`@`localhost` EVENT `shop_db`.`e` ON COMPLETION NOT PRESERVE',
        ], self.changes(cursor))
        # A statement of the server's own goes back as it is, never through value substitution.
        self.assertIsNone(cursor.sent('CREATE OR REPLACE ALGORITHM')[0][1])
        self.assertEqual(('STRICT_TRANS_TABLES',), cursor.sent('SET SESSION sql_mode')[0][1])
        self.assertEqual(('cpimp_1@localhost',), cursor.sent('SELECT TABLE_NAME')[0][1][1:])

    def test_server_without_replace_drops_and_makes_triggers_and_routines_again(self):
        cursor = owned_server([('TRIGGER', 'trg'), ('PROCEDURE', 'p')], version='8.0.36')
        self.assertTrue(self.hand_over(cursor))
        self.assertEqual(['USE `shop_db`', 'SET SESSION sql_mode = %s', 'DROP TRIGGER `shop_db`.`trg`',
                          "CREATE DEFINER=`shop_user`@`localhost` TRIGGER trg BEFORE INSERT ON t FOR EACH ROW "
                          "SET NEW.note = 'DEFINER=`cpimp_1`@`localhost`'",
                          'SET SESSION sql_mode = %s', 'DROP PROCEDURE `shop_db`.`p`',
                          "CREATE DEFINER=`shop_user`@`localhost` PROCEDURE `p`()\nSELECT 1"], self.changes(cursor))

    def test_nothing_is_asked_or_changed_when_the_import_made_no_such_object(self):
        cursor = owned_server([])
        self.assertTrue(self.hand_over(cursor))
        self.assertEqual([], self.changes(cursor))
        self.assertEqual([], cursor.sent('SELECT Host FROM mysql.user'))

    def test_account_with_rights_on_the_whole_server_never_becomes_the_owner(self):
        cursor = owned_server([('VIEW', 'v')], global_privileges=('SELECT', 'SUPER'))
        self.assertFalse(self.hand_over(cursor, 'root'))
        self.assertEqual([], self.changes(cursor))
        self.assertIn('have no owner', self.notes[0])

    def test_account_without_the_grant_on_this_database_never_becomes_the_owner(self):
        cursor = owned_server([('VIEW', 'v')], granted=('other\\_db',))
        self.assertFalse(self.hand_over(cursor))
        self.assertEqual([], self.changes(cursor))

    def test_database_without_a_registered_account_keeps_no_owner(self):
        for owner in (None, ''):
            cursor = owned_server([('VIEW', 'v')])
            self.assertFalse(self.hand_over(cursor, owner))
            self.assertEqual([], self.changes(cursor))
        cursor = owned_server([('VIEW', 'v')], hosts=())
        self.assertFalse(self.hand_over(cursor))

    def test_local_account_is_preferred_as_owner(self):
        cursor = owned_server([('VIEW', 'v')], hosts=('203.0.113.9', '127.0.0.1', 'localhost'))
        self.assertEqual(('shop_user', 'localhost'),
                         databaseImport.owner_account(cursor, 'shop_db', 'shop_user'))
        cursor = owned_server([('VIEW', 'v')], hosts=('203.0.113.9', '10.0.0.7'))
        self.assertEqual(('shop_user', '203.0.113.9'),
                         databaseImport.owner_account(cursor, 'shop_db', 'shop_user', ('203.0.113.9',)))

    def test_object_that_is_not_described_as_it_was_made_stops_the_hand_over(self):
        cursor = owned_server([('VIEW', 'v')], statements={
            'SHOW CREATE VIEW': [('v', "CREATE ALGORITHM=UNDEFINED DEFINER=`root`@`localhost` VIEW `v` AS select 1")]})
        with self.assertRaises(databaseImport.ImportRefused):
            self.hand_over(cursor)
        self.assertEqual(['USE `shop_db`'], self.changes(cursor))

    def test_import_hands_over_before_it_drops_its_account(self):
        cursor = owned_server([('VIEW', 'v')], statements={'SELECT SUBSTRING_INDEX': [('localhost',)],
                                                           'SHOW VARIABLES': []})
        # The server describes the view with the import account as its definer.
        cursor.answers['SHOW CREATE VIEW'] = lambda args: [(
            'v', "CREATE ALGORITHM=UNDEFINED DEFINER=`%s`@`localhost` SQL SECURITY DEFINER VIEW `v` AS select 1"
            % cursor.sent('CREATE USER')[0][1][0])]
        case = ImportTests('test_account_and_option_file_are_gone_after_a_good_import')
        case.setUp()
        case.cursor = cursor
        self.assertEqual(1, case.run_import(Client(), owner='shop_user'))
        self.assertEqual(["CREATE OR REPLACE ALGORITHM=UNDEFINED DEFINER=`shop_user`@`localhost` SQL SECURITY DEFINER "
                          "VIEW `v` AS select 1"], [query for query, args in cursor.sent('CREATE OR REPLACE')])
        order = [query.split(' ')[0] + ' ' + query.split(' ')[1] for query, args in cursor.statements
                 if query.startswith(('CREATE OR REPLACE', 'DROP USER'))]
        self.assertEqual(['CREATE OR', 'DROP USER'], order)
        case.doCleanups()

    def test_import_that_leaves_objects_without_an_owner_is_not_a_success(self):
        cursor = owned_server([('VIEW', 'v')], global_privileges=('SUPER',),
                              statements={'SELECT SUBSTRING_INDEX': [('localhost',)], 'SHOW VARIABLES': []})
        case = ImportTests('test_account_and_option_file_are_gone_after_a_good_import')
        case.setUp()
        case.cursor = cursor
        self.assertEqual(0, case.run_import(Client(), owner='root'))
        self.assertEqual(1, len(cursor.sent('DROP USER')))
        case.doCleanups()

    def test_caller_that_hands_over_later_gets_the_account_of_the_import(self):
        cursor = owned_server([('VIEW', 'v')], statements={'SELECT SUBSTRING_INDEX': [('localhost',)],
                                                           'SHOW VARIABLES': []})
        case = ImportTests('test_account_and_option_file_are_gone_after_a_good_import')
        case.setUp()
        case.cursor = cursor
        made = []
        self.assertEqual(1, case.run_import(Client(), made=made))
        self.assertEqual([('shop_db', case.account())], made)
        self.assertEqual([], cursor.sent('CREATE OR REPLACE'))
        self.assertEqual(1, len(cursor.sent('DROP USER')))
        case.doCleanups()


class RestoreCallerTests(unittest.TestCase):
    """The restore functions of the panel hand every dump to the import above."""

    def restore(self, compressed=False, result=1, registered='shop_user', password_check=1, changed=1):
        self.fed = []
        self.importer = mock.Mock(return_value=result)

        def import_dump(database, feed, host, port, owner=None, connect=None, made=None):
            sink = io.BytesIO()
            self.fed.append((feed(sink), sink.getvalue()))
            return self.importer(database, host, port, owner)

        decompress = mock.Mock(returncode=0)
        decompress.stdout = io.BytesIO(b'unpacked dump')
        with mock.patch('builtins.open', mock.mock_open(read_data=b'plain dump')), \
                mock.patch.object(module.json, 'loads', return_value={
                    'mysqluser': 'root', 'mysqlpassword': 'fixture', 'mysqlport': 3307, 'mysqlhost': 'db.internal'}), \
                mock.patch.object(module.os.path, 'exists', return_value=True), \
                mock.patch.object(mysqlUtilities, 'detectBackupFormat', return_value={'compressed': compressed}), \
                mock.patch.object(module.subprocess, 'Popen', return_value=decompress) as popen, \
                mock.patch.object(module.subprocess, 'call') as call, \
                mock.patch.object(module.databaseImport, 'import_dump', side_effect=import_dump), \
                mock.patch.object(mysqlUtilities, 'registeredUser', return_value=registered), \
                mock.patch.object(mysqlUtilities, 'changePassword', return_value=changed) as change, \
                mock.patch.object(mysqlUtilities, 'setupConnection') as connect:
            outcome = mysqlUtilities.restoreDatabaseBackup('shop_db', '/fixture', '*HASH', passwordCheck=password_check)
        self.popen, self.call, self.change, self.connect = popen, call, change, connect
        return outcome

    def test_archive_dump_goes_through_the_restricted_import(self):
        self.assertEqual(1, self.restore())
        self.importer.assert_called_once_with('shop_db', 'db.internal', 3307, 'shop_user')
        self.assertEqual([(True, b'plain dump')], self.fed)
        # No client is started here any more, and the administrative option file is not used.
        self.call.assert_not_called()
        self.popen.assert_not_called()
        self.connect.assert_not_called()

    def test_compressed_dump_is_unpacked_into_the_same_import(self):
        self.assertEqual(1, self.restore(compressed=True))
        self.assertEqual([(True, b'unpacked dump')], self.fed)
        self.assertEqual(['gunzip', '-c', '/fixture/shop_db.sql.gz'], self.popen.call_args[0][0])

    def test_failed_import_is_a_failed_restore(self):
        self.assertEqual(0, self.restore(result=0))

    def test_old_archive_sets_the_password_of_the_registered_user_only(self):
        self.assertEqual(1, self.restore(password_check=None))
        self.change.assert_called_once_with('shop_user', '*HASH', 1)
        # Not with a statement put together from the archive's values.
        self.connect.assert_not_called()

    def test_old_archive_for_a_database_without_registered_user_changes_no_password(self):
        self.assertEqual(0, self.restore(password_check=None, registered=None))
        self.change.assert_not_called()
        self.assertEqual(0, self.restore(password_check=None, changed=0))

    def test_registered_user_comes_from_the_panel(self):
        with mock.patch.object(module.Databases.objects, 'get', return_value=SimpleNamespace(dbUser='shop_user')) as get:
            self.assertEqual('shop_user', mysqlUtilities.registeredUser('shop_db'))
        get.assert_called_once_with(dbName='shop_db')
        with mock.patch.object(module.Databases.objects, 'get', side_effect=RuntimeError('no row')):
            self.assertIsNone(mysqlUtilities.registeredUser('shop_db'))


if __name__ == '__main__':
    unittest.main()
