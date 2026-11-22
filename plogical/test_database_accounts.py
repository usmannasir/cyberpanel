"""Which database accounts are acted on for a customer, with the panel's tables and the server faked."""
import json
import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from plogical import databaseAccounts as accounts


class Cursor:
    """Records statements; answers the account and grant look-ups from what the test set up."""

    def __init__(self, hosts=None, grants=None, fail=None):
        self.hosts = dict(hosts or {})      # user -> [host, ...]
        self.grants = dict(grants or {})    # (user, host) -> [line, ...]
        self.fail = fail
        self.statements = []
        self.rows = []

    def execute(self, statement, arguments=None):
        self.statements.append((statement, arguments))
        if self.fail and statement.startswith(self.fail):
            raise RuntimeError('statement failed')
        if statement.startswith('SELECT User, Host FROM mysql.user'):
            # The server compares account names exactly; a case variant is returned to show it is not trusted.
            self.rows = [(user.encode(), host.encode()) for user, hosts in self.hosts.items()
                         for host in hosts if user.lower() == arguments[0].lower()]
        elif statement.startswith('SHOW GRANTS FOR'):
            self.rows = [(line,) for line in self.grants.get((arguments[0], arguments[1]), [])]
        else:
            self.rows = []

    def fetchall(self):
        rows, self.rows = self.rows, []
        return rows

    def ran(self, start):
        return [(statement, arguments) for statement, arguments in self.statements if statement.startswith(start)]


class NameTests(unittest.TestCase):
    def test_phpmyadmin_account_is_named_after_the_user_number(self):
        self.assertEqual('cp-pma-7', accounts.phpmyadmin_account(7))
        self.assertEqual('cp-pma-123456', accounts.phpmyadmin_account(123456))
        for value in (0, -1, None, '7', 7.0, True, "7' OR '1"):
            with self.assertRaises(ValueError):
                accounts.phpmyadmin_account(value)

    def test_only_such_names_are_phpmyadmin_accounts(self):
        self.assertTrue(accounts.is_phpmyadmin_account('cp-pma-7'))
        for name in ('root', 'admin', 'cp-pma-', 'cp-pma-07', 'cp-pma-7 ', 'cp-pma-7\n', 'CP-PMA-7', 'xcp-pma-7',
                     'cp-pma-7x', "cp-pma-7'", 'cp_pma_7', None, 7):
            self.assertFalse(accounts.is_phpmyadmin_account(name), repr(name))

    def test_a_customer_cannot_name_a_database_user_like_a_phpmyadmin_account(self):
        from plogical.securityUtils import is_safe_sql_identifier
        self.assertFalse(is_safe_sql_identifier(accounts.phpmyadmin_account(7)))

    def test_accounts_of_the_server_are_reserved_in_any_case(self):
        with mock.patch.object(accounts, 'administrative_account', return_value='root'):
            for name in ('root', 'Root', 'ROOT', 'mysql', 'mariadb.sys', 'mysql.sys', 'mysql.session',
                         'mysql.infoschema', 'debian-sys-maint', 'cyberpanel', 'CyberPanel', 'PUBLIC', 'rdsadmin',
                         'cp-pma-7', 'CP-PMA-9', '', None, 7):
                self.assertTrue(accounts.is_reserved(name), repr(name))
            for name in ('exam_user', 'wp_user', 'admin', 'rooty', 'my_root', 'cyberpanel2'):
                self.assertFalse(accounts.is_reserved(name), name)

    def test_administrative_account_of_a_remote_server_is_reserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'mysqlPassword')
            with open(path, 'w') as stream:
                json.dump({'mysqluser': 'doadmin', 'mysqlpassword': 'x', 'mysqlhost': 'db.example', 'mysqlport': 25060},
                          stream)
            self.assertEqual('doadmin', accounts.administrative_account(path))
            with open(path, 'w') as stream:
                stream.write('plain-root-password\n')
            self.assertEqual('root', accounts.administrative_account(path))
            self.assertEqual('root', accounts.administrative_account(os.path.join(directory, 'missing')))
        with mock.patch.object(accounts, 'administrative_account', return_value='doadmin'):
            self.assertTrue(accounts.is_reserved('doadmin'))
            self.assertTrue(accounts.is_reserved('DOADMIN'))
            self.assertFalse(accounts.is_system_account('doadmin'))


class RefusalTests(unittest.TestCase):
    def refusal(self, name, panel_user=False):
        with mock.patch.object(accounts, 'administrative_account', return_value='root'), \
                mock.patch.object(accounts, 'named_like_panel_user', return_value=panel_user) as lookup:
            answer = accounts.account_refusal(name)
        self.lookup = lookup
        return answer

    def test_plain_name_is_accepted(self):
        self.assertIsNone(self.refusal('exam_user'))
        self.lookup.assert_called_once_with('exam_user')

    def test_reserved_name_is_refused_before_any_lookup(self):
        for name in ('root', 'ROOT', 'mysql', 'cyberpanel', 'public', 'rdsadmin'):
            self.assertIn('reserved', self.refusal(name), name)
            self.lookup.assert_not_called()

    def test_name_that_is_not_an_identifier_is_refused(self):
        for name in ('cp-pma-7', 'mariadb.sys', "x'y", 'a b', '', None, 7, 'x' * 65, '-'):
            self.assertIn('letters, numbers and underscores', self.refusal(name), repr(name))
            self.lookup.assert_not_called()

    def test_name_of_a_panel_user_is_refused(self):
        self.assertIn('panel user', self.refusal('reseller1', panel_user=True))

    def test_panel_user_lookup_ignores_case_in_both_tables(self):
        seen = []

        def exists(model, field, name):
            seen.append((model, field, name))
            return model == 'records' and name == 'Reseller1'

        fake = SimpleNamespace(Administrator='users', GlobalUserDB='records')
        with mock.patch.object(accounts, '_exists_ignoring_case', side_effect=exists), \
                mock.patch.dict('sys.modules', {'loginSystem.models': fake, 'databases.models': fake}):
            self.assertTrue(accounts.named_like_panel_user('Reseller1'))
            self.assertFalse(accounts.named_like_panel_user('other'))
        self.assertIn(('users', 'userName', 'Reseller1'), seen)
        self.assertIn(('records', 'username', 'Reseller1'), seen)

    def test_lookup_compares_lower_case_on_both_sides(self):
        model = mock.Mock()
        filtered = model.objects.annotate.return_value.filter
        filtered.return_value.exists.return_value = True
        self.assertTrue(accounts._exists_ignoring_case(model, 'userName', 'ReSeller1'))
        filtered.assert_called_once_with(lowered_name='reseller1')
        annotation = model.objects.annotate.call_args[1]['lowered_name']
        self.assertEqual('Lower', type(annotation).__name__)


class RegistrationTests(unittest.TestCase):
    def databases(self, rows):
        model = mock.Mock()
        model.objects.filter.return_value = rows
        return model

    def test_only_the_exact_name_is_registered(self):
        # The panel's table compares without regard to case and returns the variant.
        variant = SimpleNamespace(dbUser='Exam_User', dbName='exam_one')
        exact = SimpleNamespace(dbUser='exam_user', dbName='exam_two')
        model = self.databases([variant, exact])
        with mock.patch.dict('sys.modules', {'databases.models': SimpleNamespace(Databases=model)}):
            self.assertEqual([exact], accounts.registered_databases('exam_user'))
            self.assertEqual([variant], accounts.registered_databases('Exam_User'))
            self.assertEqual([], accounts.registered_databases('EXAM_USER'))
            for value in ('', None, 7, ['exam_user']):
                self.assertEqual([], accounts.registered_databases(value))


class ServerAccountTests(unittest.TestCase):
    def test_hosts_are_those_of_the_exact_user_name(self):
        cursor = Cursor(hosts={'exam_user': ['localhost', '127.0.0.1', '203.0.113.5'], 'Exam_User': ['localhost']})
        self.assertEqual(['localhost', '127.0.0.1', '203.0.113.5'], accounts.account_hosts(cursor, 'exam_user'))
        self.assertEqual(['localhost'], accounts.account_hosts(cursor, 'Exam_User'))
        self.assertEqual([], accounts.account_hosts(cursor, 'other'))
        self.assertEqual(('exam_user',), cursor.statements[0][1])

    def test_new_phpmyadmin_account_is_created_with_bound_values(self):
        cursor = Cursor()
        password = "p'w\" ;-- $x"
        with mock.patch.object(accounts, 'phpmyadmin_account_is_recorded', return_value=True):
            accounts.prepare_phpmyadmin_account(cursor, 'cp-pma-7', 'localhost', password)
        self.assertEqual([('CREATE USER %s@%s IDENTIFIED BY %s', ('cp-pma-7', 'localhost', password))],
                         cursor.ran('CREATE USER'))
        self.assertEqual([], cursor.ran('DROP'))
        self.assertEqual([], cursor.ran('ALTER'))
        for statement, unused in cursor.statements:
            self.assertNotIn(password, statement)

    def test_existing_phpmyadmin_account_gets_the_password_and_loses_its_grants(self):
        cursor = Cursor(hosts={'cp-pma-7': ['localhost']})
        with mock.patch.object(accounts, 'phpmyadmin_account_is_recorded', return_value=True):
            accounts.prepare_phpmyadmin_account(cursor, 'cp-pma-7', 'localhost', 'secret')
        self.assertEqual([('ALTER USER %s@%s IDENTIFIED BY %s', ('cp-pma-7', 'localhost', 'secret')),
                          ('REVOKE ALL PRIVILEGES, GRANT OPTION FROM %s@%s', ('cp-pma-7', 'localhost'))],
                         cursor.statements[1:])
        self.assertEqual([], cursor.ran('DROP'))
        self.assertEqual([], cursor.ran('CREATE'))

    def test_existing_account_without_a_record_is_left_alone(self):
        cursor = Cursor(hosts={'cp-pma-7': ['localhost']})
        with mock.patch.object(accounts, 'phpmyadmin_account_is_recorded', return_value=False):
            with self.assertRaises(ValueError):
                accounts.prepare_phpmyadmin_account(cursor, 'cp-pma-7', 'localhost', 'secret')
        self.assertEqual(1, len(cursor.statements))

    def test_no_other_account_is_ever_prepared(self):
        for name in ('root', 'cyberpanel', 'exam_user', 'reseller1', "x'@'%", 'cp-pma-0', 'CP-PMA-7', None):
            cursor = Cursor(hosts={'root': ['localhost'], 'exam_user': ['localhost']})
            with self.assertRaises(ValueError):
                accounts.prepare_phpmyadmin_account(cursor, name, 'localhost', 'secret')
            self.assertEqual([], cursor.statements, repr(name))

    def test_record_is_matched_exactly(self):
        records = mock.Mock()
        records.objects.filter.return_value = [SimpleNamespace(username='CP-PMA-7')]
        with mock.patch.dict('sys.modules', {'databases.models': SimpleNamespace(GlobalUserDB=records)}):
            self.assertFalse(accounts.phpmyadmin_account_is_recorded('cp-pma-7'))
            records.objects.filter.return_value = [SimpleNamespace(username='cp-pma-7')]
            self.assertTrue(accounts.phpmyadmin_account_is_recorded('cp-pma-7'))


class EarlierAccountTests(unittest.TestCase):
    USAGE = "GRANT USAGE ON *.* TO `reseller1`@`localhost` IDENTIFIED BY PASSWORD '*2470C0C06DEE42FD1618BB99005ADCA2EC9D1E19'"
    OWN = 'GRANT ALL PRIVILEGES ON `exam\\_shop`.* TO `reseller1`@`localhost`'

    def refusal(self, user='reseller1', lines=None, hosts=None, registered=False):
        cursor = Cursor(hosts={user: ['localhost']} if hosts is None else hosts,
                        grants={(user, 'localhost'): [self.USAGE, self.OWN] if lines is None else lines})
        with mock.patch.object(accounts, 'administrative_account', return_value='root'), \
                mock.patch.object(accounts, 'registered_as_database_user', return_value=registered):
            answer = accounts.earlier_phpmyadmin_account_refusal(cursor, user, 'localhost')
        self.cursor = cursor
        return answer

    def test_account_with_database_privileges_only_can_go(self):
        self.assertIsNone(self.refusal())
        self.assertIsNone(self.refusal(lines=[self.USAGE]))
        self.assertIsNone(self.refusal(lines=["GRANT USAGE ON *.* TO 'reseller1'@'localhost'",
                                              "GRANT SELECT, INSERT, CREATE TEMPORARY TABLES ON `a``b`.* TO 'reseller1'@'localhost'"]))

    def test_account_of_the_server_is_kept_without_a_question_to_the_server(self):
        for name in ('root', 'Root', 'mysql', 'cyberpanel', 'mariadb.sys', 'cp-pma-3', '', None):
            self.assertIsNotNone(self.refusal(user=name), repr(name))
            self.assertEqual([], self.cursor.statements)

    def test_registered_database_user_is_kept(self):
        self.assertIn('registered', self.refusal(registered=True))
        self.assertEqual([], self.cursor.statements)

    def test_missing_account_is_reported_as_such(self):
        self.assertEqual('there is no such account', self.refusal(hosts={}))
        self.assertEqual('there is no such account', self.refusal(hosts={'reseller1': ['127.0.0.1']}))
        self.assertEqual('there is no such account', self.refusal(hosts={'Reseller1': ['localhost']}))

    def test_account_holding_anything_else_is_kept(self):
        for extra in ("GRANT ALL PRIVILEGES ON *.* TO `reseller1`@`localhost` WITH GRANT OPTION",
                      'GRANT ALL PRIVILEGES ON *.* TO `reseller1`@`localhost`',
                      'GRANT SELECT ON *.* TO `reseller1`@`localhost`',
                      'GRANT SELECT ON `mysql`.`user` TO `reseller1`@`localhost`',
                      'GRANT ALL PRIVILEGES ON `exam\\_shop`.* TO `reseller1`@`localhost` WITH GRANT OPTION',
                      'GRANT `dba` TO `reseller1`@`localhost`',
                      "GRANT PROXY ON ''@'%' TO 'reseller1'@'localhost'",
                      'GRANT EXECUTE ON PROCEDURE `exam`.`p` TO `reseller1`@`localhost`',
                      'something unexpected'):
            self.assertIn('privileges', self.refusal(lines=[self.USAGE, self.OWN, extra]), extra)
        self.assertIn('privileges', self.refusal(lines=[]))


class RemoteAccessTests(unittest.TestCase):
    def setUp(self):
        self.cursor = Cursor()
        self.connection = mock.Mock()
        self.utilities = mock.Mock()
        self.utilities.LOCALHOST = 'localhost'
        self.utilities.setupConnection.return_value = (self.connection, self.cursor)
        self.utilities.createDatabase.return_value = 1
        self.utilities.changePassword.return_value = 1
        self.passwords = {'localhost': '*HASH', '127.0.0.1': '*HASH'}

    def open(self, host='203.0.113.5', previous=None):
        return accounts.open_remote_access(self.utilities, self.passwords, 'exam_shop', 'exam_user', host, previous)

    def test_new_remote_account_starts_with_a_random_password_and_gets_the_users_own(self):
        self.assertEqual((1, None), self.open())
        (database, user, temporary, create, host), unused = self.utilities.createDatabase.call_args
        self.assertEqual(('exam_shop', 'exam_user', 0, '203.0.113.5'), (database, user, create, host))
        self.assertNotEqual('cyberpanel', temporary)
        self.assertEqual(32, len(temporary))
        self.open()
        self.assertNotEqual(temporary, self.utilities.createDatabase.call_args[0][2])
        self.utilities.changePassword.assert_called_with('exam_user', '*HASH', 1, '203.0.113.5')
        self.assertEqual([], self.cursor.ran('DROP'))

    def test_account_is_removed_again_when_it_cannot_get_the_users_password(self):
        self.utilities.changePassword.return_value = 0
        self.assertEqual(0, self.open()[0])
        self.assertEqual([('DROP USER IF EXISTS %s@%s', ('exam_user', '203.0.113.5'))], self.cursor.ran('DROP'))
        self.connection.close.assert_called_once_with()

    def test_account_left_half_made_is_removed(self):
        self.utilities.createDatabase.return_value = 0
        self.assertEqual(0, self.open()[0])
        self.utilities.changePassword.assert_not_called()
        self.assertEqual([('DROP USER IF EXISTS %s@%s', ('exam_user', '203.0.113.5'))], self.cursor.ran('DROP'))

    def test_nothing_is_created_without_a_local_account_to_copy_from(self):
        for passwords in ({}, {'203.0.113.9': '*HASH'}, {'localhost': ''}, {'localhost': None}):
            self.passwords = passwords
            self.assertEqual(0, self.open()[0])
        self.utilities.createDatabase.assert_not_called()
        self.utilities.changePassword.assert_not_called()
        self.utilities.setupConnection.assert_not_called()

    def test_existing_account_is_neither_created_nor_removed(self):
        self.passwords['203.0.113.5'] = '*OLD'
        self.utilities.changePassword.return_value = 0
        self.assertEqual(0, self.open()[0])
        self.utilities.createDatabase.assert_not_called()
        self.assertEqual([], self.cursor.ran('DROP'))
        self.passwords = {'localhost': '*HASH', 'db.example.com': '*OLD'}
        self.assertEqual(0, self.open(host='DB.Example.com')[0])
        self.utilities.createDatabase.assert_not_called()
        self.assertEqual([], self.cursor.ran('DROP'))

    def test_account_of_the_previous_remote_host_is_removed(self):
        self.passwords['198.51.100.7'] = '*HASH'
        self.assertEqual((1, None), self.open(previous='198.51.100.7'))
        self.assertEqual([('DROP USER IF EXISTS %s@%s', ('exam_user', '198.51.100.7'))], self.cursor.ran('DROP'))

    def test_local_accounts_and_the_same_host_are_never_removed(self):
        for previous in ('localhost', '127.0.0.1', 'LOCALHOST', '203.0.113.5', None, '', '198.51.100.99'):
            self.assertEqual((1, None), self.open(previous=previous))
        self.assertEqual([], self.cursor.ran('DROP'))
        self.utilities.LOCALHOST = '192.0.2.10'
        self.passwords = {'192.0.2.10': '*HASH'}
        self.assertEqual((1, None), self.open(previous='192.0.2.10'))
        self.assertEqual([], self.cursor.ran('DROP'))

    def test_going_back_to_local_access_removes_the_remote_account(self):
        self.passwords['203.0.113.5'] = '*HASH'
        self.assertEqual((1, None), self.open(host='localhost', previous='203.0.113.5'))
        self.utilities.createDatabase.assert_not_called()
        self.assertEqual([('DROP USER IF EXISTS %s@%s', ('exam_user', '203.0.113.5'))], self.cursor.ran('DROP'))


if __name__ == '__main__':
    unittest.main()
