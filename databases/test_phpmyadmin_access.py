"""The key file, the record and the database account of a panel user's phpMyAdmin access."""
import os
import stat
import tempfile
import unittest
from types import SimpleNamespace
from unittest import mock

from databases import phpmyadminAccess as access
from plogical import databaseAccounts
from plogical.test_database_accounts import Cursor


class KeyFileTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.directory = os.path.join(holder.name, 'keys')

    def write(self, user_id, key):
        access.write_key(user_id, key, self.directory, None)

    def read(self, user_id):
        return access.read_key(user_id, self.directory, None)

    def test_key_is_kept_in_a_private_file_named_after_the_user_number(self):
        self.write(7, b'first-key')
        self.assertEqual(['7'], os.listdir(self.directory))
        self.assertEqual(0o700, stat.S_IMODE(os.stat(self.directory).st_mode))
        self.assertEqual(0o600, stat.S_IMODE(os.stat(os.path.join(self.directory, '7')).st_mode))
        self.assertEqual(b'first-key', self.read(7))

    def test_new_key_replaces_the_earlier_one(self):
        self.write(7, b'first-key')
        self.write(7, b'second-key')
        self.assertEqual(b'second-key', self.read(7))

    def test_key_is_never_written_through_a_link(self):
        os.makedirs(self.directory, 0o700)
        target = os.path.join(os.path.dirname(self.directory), 'elsewhere')
        with open(target, 'w') as stream:
            stream.write('untouched')
        os.symlink(target, os.path.join(self.directory, '7'))
        self.write(7, b'new-key')
        with open(target) as stream:
            self.assertEqual('untouched', stream.read())
        self.assertFalse(os.path.islink(os.path.join(self.directory, '7')))
        self.assertEqual(b'new-key', self.read(7))

    def test_key_is_not_read_through_a_link_or_from_a_shared_file(self):
        os.makedirs(self.directory, 0o700)
        target = os.path.join(os.path.dirname(self.directory), 'elsewhere')
        with open(target, 'w') as stream:
            stream.write('other-content')
        os.symlink(target, os.path.join(self.directory, '7'))
        with self.assertRaises(OSError):
            self.read(7)
        self.write(8, b'key')
        os.chmod(os.path.join(self.directory, '8'), 0o644)
        with self.assertRaises(OSError):
            self.read(8)
        self.write(9, b'key')
        os.link(os.path.join(self.directory, '9'), os.path.join(self.directory, 'second-name'))
        with self.assertRaises(OSError):
            self.read(9)
        with self.assertRaises(OSError):
            self.read(10)

    def test_only_a_user_number_names_a_key(self):
        for value in ('7', '../7', 'admin', "x; id", None, 0, -3, 7.0, True):
            with self.assertRaises(ValueError):
                self.write(value, b'key')
            with self.assertRaises(ValueError):
                self.read(value)
        self.assertFalse(os.path.exists(self.directory))

    def test_removed_key_is_gone_and_a_missing_one_is_no_error(self):
        access.remove_key(7, self.directory)
        self.assertFalse(os.path.exists(self.directory))
        self.write(7, b'key')
        access.remove_key(7, self.directory)
        self.assertEqual([], os.listdir(self.directory))
        access.remove_key(7, self.directory)

    def test_earlier_key_file_is_removed_only_under_a_plain_name(self):
        home = os.path.dirname(self.directory)
        for name in ('reseller1', 'john.doe', 'john@example.com'):
            path = os.path.join(home, 'phpmyadmin_' + name)
            with open(path, 'w') as stream:
                stream.write('key')
            access._remove_earlier_key(name, home)
            self.assertFalse(os.path.exists(path), name)
        os.makedirs(os.path.join(home, 'phpmyadmin_x'))
        victim = os.path.join(home, 'victim')
        with open(victim, 'w') as stream:
            stream.write('keep')
        for name in ('x/../victim', '../victim', 'John Smith', 'a/b', '', None, 7, 'x' * 51):
            access._remove_earlier_key(name, home)
        self.assertTrue(os.path.exists(victim))


class Record:
    def __init__(self, store, username, password='x'):
        self.store, self.username, self.password = store, username, password

    def delete(self):
        self.store.remove(self)


class RetireTests(unittest.TestCase):
    def setUp(self):
        self.records = []
        self.cursor = Cursor()
        self.connection = mock.Mock()
        model = mock.Mock()
        # The panel's table compares without regard to case.
        model.objects.filter.side_effect = lambda username: [
            record for record in list(self.records) if record.username.lower() == username.lower()]
        utilities = SimpleNamespace(LOCALHOST='localhost',
                                    setupConnection=mock.Mock(return_value=(self.connection, self.cursor)))
        self.utilities = utilities
        for item in (mock.patch.dict('sys.modules', {
                         'databases.models': SimpleNamespace(GlobalUserDB=model),
                         'plogical.mysqlUtilities': SimpleNamespace(mysqlUtilities=utilities)}),
                     mock.patch.object(databaseAccounts, 'administrative_account', return_value='root'),
                     mock.patch.object(databaseAccounts, 'registered_as_database_user', return_value=False),
                     mock.patch.object(access, 'remove_key'),
                     mock.patch.object(access, '_remove_earlier_key'),
                     mock.patch.object(access.logging, 'writeToFile')):
            self.log = item.start()
            self.addCleanup(item.stop)

    def record(self, username, password='x'):
        record = Record(self.records, username, password)
        self.records.append(record)
        return record

    def earlier(self, name, grants=None):
        """What an earlier release left for a user who is not an administrator."""
        self.record(name, 'gAAAAABencrypted')
        self.cursor.hosts[name] = ['localhost']
        self.cursor.grants[(name, 'localhost')] = grants or [
            "GRANT USAGE ON *.* TO `%s`@`localhost` IDENTIFIED BY PASSWORD '*X'" % name,
            'GRANT ALL PRIVILEGES ON `exam\\_shop`.* TO `%s`@`localhost`' % name]

    def user(self, pk=7, name='reseller1'):
        return SimpleNamespace(pk=pk, userName=name, owner=1)

    def dropped(self):
        return [arguments for unused, arguments in self.cursor.ran('DROP USER IF EXISTS')]

    def test_account_and_record_of_the_user_number_are_removed(self):
        self.record('cp-pma-7')
        other = self.record('cp-pma-8')
        self.assertEqual(1, access.retire([self.user()]))
        self.assertEqual([('cp-pma-7', 'localhost')], self.dropped())
        self.assertEqual([other], self.records)
        access.remove_key.assert_called_once_with(7)
        self.connection.close.assert_called_once_with()

    def test_account_an_earlier_release_named_after_the_user_is_removed_too(self):
        self.earlier('reseller1')
        self.assertEqual(1, access.retire([self.user()]))
        self.assertEqual([('reseller1', 'localhost'), ('cp-pma-7', 'localhost')], self.dropped())
        self.assertEqual([], self.records)
        access._remove_earlier_key.assert_called_once_with('reseller1')

    def test_first_visit_after_the_upgrade_removes_the_earlier_account_only(self):
        self.earlier('reseller1')
        current = self.record('cp-pma-7')
        self.assertEqual(1, access.retire_earlier(self.user()))
        self.assertEqual([('reseller1', 'localhost')], self.dropped())
        self.assertEqual([current], self.records)

    def test_same_name_without_an_earlier_record_is_never_dropped(self):
        # An account that only happens to carry the name of a panel user.
        self.cursor.hosts['reseller1'] = ['localhost']
        self.cursor.grants[('reseller1', 'localhost')] = ["GRANT USAGE ON *.* TO `reseller1`@`localhost`"]
        self.assertEqual(1, access.retire([self.user()]))
        self.assertEqual([('cp-pma-7', 'localhost')], self.dropped())

    def test_record_of_an_administrator_proves_no_account(self):
        self.record('boss', 'Xk3PlainRandom1')
        self.cursor.hosts['boss'] = ['localhost']
        self.cursor.grants[('boss', 'localhost')] = ["GRANT USAGE ON *.* TO `boss`@`localhost`"]
        self.assertEqual(1, access.retire([self.user(3, 'boss')]))
        self.assertEqual([('cp-pma-3', 'localhost')], self.dropped())
        self.assertEqual([], self.records)

    def test_earlier_account_of_the_server_or_of_a_database_is_kept_and_reported(self):
        for name in ('root', 'cyberpanel', 'mysql'):
            self.earlier(name)
            self.assertEqual(1, access.retire_earlier(self.user(9, name)))
        self.assertEqual([], self.dropped())
        self.assertEqual(3, self.log.call_count)
        self.assertIn('left in place', self.log.call_args[0][0])
        self.assertEqual([], self.records)
        self.earlier('exam_user')
        databaseAccounts.registered_as_database_user.return_value = True
        self.assertEqual(1, access.retire_earlier(self.user(9, 'exam_user')))
        self.assertEqual([], self.dropped())

    def test_earlier_account_with_wider_privileges_is_kept(self):
        self.earlier('reseller1', ["GRANT ALL PRIVILEGES ON *.* TO `reseller1`@`localhost` WITH GRANT OPTION"])
        self.assertEqual(1, access.retire_earlier(self.user()))
        self.assertEqual([], self.dropped())

    def test_record_of_another_user_is_never_taken_for_an_earlier_one(self):
        # A user created long ago under a name of the new kind.
        kept = self.record('cp-pma-8')
        self.assertEqual(1, access.retire_earlier(self.user(7, 'cp-pma-8')))
        self.assertEqual([kept], self.records)
        variant = self.record('RESELLER1', 'gAAAAABencrypted')
        self.assertEqual(1, access.retire_earlier(self.user()))
        self.assertEqual([kept, variant], self.records)
        self.assertEqual([], self.dropped())

    def test_every_user_is_handled_over_one_connection(self):
        self.assertEqual(1, access.retire([self.user(7), self.user(8, 'other'), None]))
        self.assertEqual([('cp-pma-7', 'localhost'), ('cp-pma-8', 'localhost')], self.dropped())
        self.utilities.setupConnection.assert_called_once_with()

    def test_account_uses_the_host_the_panel_connects_from(self):
        self.utilities.LOCALHOST = '192.0.2.10'
        self.assertEqual(1, access.retire([self.user()]))
        self.assertEqual([('cp-pma-7', '192.0.2.10')], self.dropped())

    def test_failure_is_reported_and_never_raised(self):
        self.cursor.fail = 'DROP USER'
        self.assertEqual(0, access.retire([self.user(), self.user(8, 'other')]))
        self.assertEqual(2, len(self.dropped()))
        self.connection.close.assert_called_once_with()
        self.utilities.setupConnection.return_value = (0, 0)
        self.assertEqual(0, access.retire([self.user()]))
        self.utilities.setupConnection.side_effect = RuntimeError('server away')
        self.assertEqual(0, access.retire([self.user()]))
        self.assertEqual(1, access.retire([]))

    def test_account_that_cannot_be_dropped_keeps_its_record_and_key_for_the_next_attempt(self):
        record = self.record('cp-pma-7')
        self.cursor.fail = 'DROP USER'
        self.assertEqual(0, access.retire([self.user()]))
        self.assertEqual([record], self.records)
        access.remove_key.assert_not_called()
        # The next removal finds the record and finishes the work.
        self.cursor.fail = None
        self.assertEqual(1, access.retire([self.user()]))
        self.assertEqual([], self.records)
        access.remove_key.assert_called_once_with(7)

    def test_website_leaving_an_owner_retires_the_owner_and_the_reseller_above(self):
        owner = SimpleNamespace(pk=7, userName='customer', owner=4)
        reseller = SimpleNamespace(pk=4, userName='reseller1', owner=1)
        users = mock.Mock()
        users.objects.filter.return_value.exclude.return_value = [reseller]
        with mock.patch.dict('sys.modules', {'loginSystem.models': SimpleNamespace(Administrator=users)}):
            self.assertEqual(1, access.retire_for_website(owner))
        users.objects.filter.assert_called_once_with(pk=4)
        self.assertEqual([('cp-pma-7', 'localhost'), ('cp-pma-4', 'localhost')], self.dropped())


if __name__ == '__main__':
    unittest.main()
