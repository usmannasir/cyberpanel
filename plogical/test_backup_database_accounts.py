"""A backup records the accounts of a database itself, and a restore registers the database with its own user."""
import ast
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from xml.etree import ElementTree

from plogical import databaseAccounts as accounts
from plogical import mysqlUtilities as module
from plogical.backupMetadata import backup_includes_mail_domain
from plogical.mysqlUtilities import mysqlUtilities
from plogical.test_backup_restore_ssl import load_method
from plogical import test_backup_temp_metadata as lifetime
from plogical.test_database_restore_accounts import Cursor, Rows, applied, panel

HERE = Path(__file__).resolve().parent
HASH = '*94BDCEBE19083CE2A1F959FD02F964C7AF4CFC29'


def recorded(*names):
    """The panel's phpMyAdmin records, as the helpers read them."""
    return mock.patch.dict('sys.modules', {
        'databases.models': SimpleNamespace(GlobalUserDB=Rows({'username': name} for name in names))})


def server(administrator='root'):
    return mock.patch.object(accounts, 'administrative_account', return_value=administrator)


class RecordedAccountTests(unittest.TestCase):
    GRANTED = [('shop_user', '127.0.0.1'), ('cp-pma-5', 'localhost'), ('reseller', 'localhost'),
               ('shop_user', 'localhost'), ('shop_reader', '203.0.113.9')]

    def test_phpmyadmin_and_server_accounts_are_left_out(self):
        with server(), recorded('cp-pma-5', 'reseller'):
            kept = accounts.backed_up_accounts(self.GRANTED + [('root', 'localhost'), ('CP-PMA-9', 'localhost')],
                                               'shop_user')
        self.assertEqual([('shop_user', '127.0.0.1'), ('shop_user', 'localhost'), ('shop_reader', '203.0.113.9')],
                         kept)

    def test_administrative_account_of_a_remote_server_is_left_out(self):
        with server('doadmin'), recorded():
            self.assertEqual([('shop_user', '%')],
                             accounts.backed_up_accounts([('doadmin', '%'), ('shop_user', '%')], 'shop_user'))

    def test_registered_user_is_kept_even_when_a_panel_user_has_its_name(self):
        with server(), recorded('reseller'):
            self.assertEqual([('reseller', 'localhost')],
                             accounts.backed_up_accounts([('reseller', 'localhost')], 'reseller'))

    def test_record_is_matched_exactly(self):
        with server(), recorded('Reseller'):
            self.assertEqual([('reseller', 'localhost')],
                             accounts.backed_up_accounts([('reseller', 'localhost')], 'shop_user'))

    def test_registered_user_comes_first_at_each_of_its_hosts(self):
        granted = [('alice_reader', 'localhost'), ('shop_user', 'localhost'), ('alice_reader', '%'),
                   ('shop_user', '203.0.113.9')]
        with server(), recorded():
            self.assertEqual([('shop_user', 'localhost'), ('shop_user', '203.0.113.9'), ('alice_reader', 'localhost'),
                              ('alice_reader', '%')], accounts.backed_up_accounts(granted, 'shop_user'))


class BackupMetadataTests(unittest.TestCase):
    """prepareBackupMeta, with the harness of the metadata lifetime tests."""

    def setUp(self):
        lifetime.BackupTemporaryMetadataTests.setUp(self)
        self.website.databases_set = SimpleNamespace(
            all=lambda: [SimpleNamespace(dbName='shop_db', dbUser='shop_user')])
        users = SimpleNamespace(objects=SimpleNamespace(
            get=lambda user, host: SimpleNamespace(password='hash of %s@%s' % (user, host))))
        self.backup.prepareBackupMeta.__globals__.update(
            databaseAccounts=accounts, DBUsers=users,
            databaseGrants=SimpleNamespace(accounts_granted=lambda cursor, name: list(RecordedAccountTests.GRANTED)))

    def test_metadata_lists_the_accounts_of_the_database_only(self):
        with server(), recorded('cp-pma-5', 'reseller'):
            result = self.backup.prepareBackupMeta('fixture.invalid', 'fixture', self.scratch.name,
                                                   self.scratch.name, 0)
        self.assertEqual(1, result[0])
        document = Path(result[2]).read_text()
        listed = [(entry.findtext('dbUser'), entry.findtext('dbHost'), entry.findtext('password'))
                  for entry in ElementTree.parse(result[2]).findall('Databases/database/databaseUsers')]
        self.assertEqual([('shop_user', '127.0.0.1', 'hash of shop_user@127.0.0.1'),
                          ('shop_user', 'localhost', 'hash of shop_user@localhost'),
                          ('shop_reader', '203.0.113.9', 'hash of shop_reader@203.0.113.9')], listed)
        for name in ('cp-pma-5', 'reseller'):
            self.assertNotIn(name, document)

    def test_both_backup_formats_record_through_the_same_rule(self):
        for name in ('backupUtilities.py', 'Backupsv2.py'):
            source = (HERE / name).read_text()
            self.assertEqual(1, source.count('accounts_granted('), name)
            self.assertRegex(source, r'databaseAccounts\.backed_up_accounts\(\s*databaseGrants\.accounts_granted\(')


def metadata(users):
    entries = ''.join('<databaseUsers><dbUser>%s</dbUser><dbHost>%s</dbHost><password>%s</password></databaseUsers>'
                      % (user, host, HASH) for user, host in users)
    return ('<metaFile><masterDomain>example.test</masterDomain><phpSelection>PHP 8.3</phpSelection>'
            '<externalApp>example</externalApp><VERSION>3.0</VERSION><BUILD>11</BUILD><userName>owner</userName>'
            '<Databases><database><dbName>shop_db</dbName>%s</database></Databases></metaFile>' % entries)


# A backup of an earlier release, in the order a database server without a
# loopback account lists the grants: a phpMyAdmin account, the account an
# earlier release named after the owner, then the database's user.
EARLIER = [('cp-pma-5', 'localhost'), ('owner', 'localhost'), ('shop_user', 'localhost'), ('shop_user', '203.0.113.9')]


class RestoreChoiceTests(unittest.TestCase):
    def choose(self, listed, panel_users=()):
        with server(), mock.patch.object(accounts, 'named_like_panel_user',
                                         side_effect=lambda name: name.lower() in panel_users):
            return accounts.restored_database_user(listed)

    def test_first_user_a_database_user_may_be_called(self):
        self.assertEqual('shop_user', self.choose(['cp-pma-5', 'root', 'shop_user', 'shop_reader']))
        self.assertEqual('shop_user', self.choose(['shop_user', 'shop_user', 'shop_reader']))
        self.assertEqual('shop_user', self.choose(['shop-user', 'shop_user']))
        self.assertEqual('exam_wp', self.choose(['alice', 'exam_wp'], panel_users=('alice',)))
        self.assertEqual('exam_wp', self.choose(['cp-pma-5', 'Alice', 'exam_wp'], panel_users=('alice',)))

    def test_user_whose_creation_will_say_why_it_is_refused(self):
        # No listed user may be a database user here: the first that is not an account of the server.
        self.assertEqual('owner', self.choose(['cp-pma-5', 'owner'], panel_users=('owner',)))
        self.assertEqual('shop-user', self.choose(['root', 'shop-user']))

    def test_no_usable_user(self):
        for listed in ([], ['cp-pma-5'], ['root', 'CP-PMA-7', 'cyberpanel'], [None, '']):
            self.assertIsNone(self.choose(listed), listed)

    def test_one_rule_names_a_database_user_for_registration_and_for_restoring(self):
        with server(), mock.patch.object(accounts, 'named_like_panel_user', side_effect=lambda name: name == 'owner'):
            self.assertTrue(accounts.may_be_database_user('shop_user'))
            for name in ('owner', 'root', 'cp-pma-5', 'shop-user', '-', '', None):
                self.assertFalse(accounts.may_be_database_user(name), repr(name))
        source = (HERE / 'mysqlUtilities.py').read_text()
        self.assertIn('databaseAccounts.may_be_database_user(dbUser)', source)

    def create_website(self, users, schema=True):
        user = SimpleNamespace(userName='owner', email='owner@example.test')
        website = object()
        hosts = mock.Mock()
        hosts.createVirtualHost.return_value = (1, 'None')
        self.databases = mock.Mock()
        self.databases.createDatabaseAndRegister.return_value = (1, 'None')
        namespace = dict(os=os, ElementTree=ElementTree, generate_pass=lambda length: 'starting-password',
                         Administrator=SimpleNamespace(objects=mock.Mock(get=mock.Mock(return_value=user))),
                         Websites=SimpleNamespace(objects=mock.Mock(get=mock.Mock(return_value=website))),
                         ChildDomains=SimpleNamespace(objects=mock.Mock()),
                         virtualHostUtilities=hosts, DNS=mock.Mock(), databaseAccounts=accounts,
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=self.databases),
                         backup_includes_mail_domain=backup_includes_mail_domain,
                         backup_uses_database_users_schema=lambda *args: schema)
        namespace['Websites'].objects.filter.return_value.count.return_value = 0
        namespace['ChildDomains'].objects.filter.return_value.count.return_value = 0
        create = load_method('backupUtilities.py', 'backupUtilities', 'createWebsiteFromBackup', namespace)
        with tempfile.TemporaryDirectory() as scratch:
            archive = Path(scratch) / 'fixture.tar.gz'
            archive.touch()
            (Path(scratch) / 'fixture').mkdir()
            (Path(scratch) / 'fixture' / 'meta.xml').write_text(metadata(users))
            with server(), mock.patch.object(accounts, 'named_like_panel_user',
                                             side_effect=lambda name: name == 'owner'):
                return create(str(archive), 'fixture')

    def test_archive_restore_registers_the_database_with_its_own_user(self):
        self.assertEqual((1, 'None'), self.create_website(EARLIER))
        self.databases.createDatabaseAndRegister.assert_called_once_with(
            'shop_db', 'shop_user', 'starting-password', mock.ANY)

    def test_archive_of_the_single_user_format_registers_its_user(self):
        text = metadata([]).replace('<dbName>shop_db</dbName>', '<dbName>shop_db</dbName><dbUser>shop_user</dbUser>')
        with mock.patch(__name__ + '.metadata', return_value=text):
            self.assertEqual((1, 'None'), self.create_website([], schema=False))
        self.databases.createDatabaseAndRegister.assert_called_once_with(
            'shop_db', 'shop_user', 'starting-password', mock.ANY)

    def test_archive_without_a_usable_user_stops_with_the_known_error(self):
        for users in ([], [('cp-pma-5', 'localhost')]):
            status, message = self.create_website(users)
            self.assertEqual(0, status)
            self.assertIn('no account metadata: shop_db', message)
            self.databases.createDatabaseAndRegister.assert_not_called()

    def restore_meta(self, users):
        method = load_method('restoreMeta.py', 'restoreMeta', 'startRestore', {})
        self.databases = mock.Mock()
        self.databases.prepareDatabaseForRestore.return_value = (1, 'None')
        self.databases.restoreDatabaseUser.return_value = 1
        method.__globals__.update(
            os=os, ElementTree=ElementTree, logging=mock.MagicMock(), Websites=mock.MagicMock(),
            virtualHostUtilities=mock.MagicMock(), mailUtilities=mock.MagicMock(), databaseAccounts=accounts,
            ProcessUtilities=SimpleNamespace(debugPath='/nonexistent-debug'),
            mysqlUtilities=SimpleNamespace(mysqlUtilities=self.databases))
        with tempfile.TemporaryDirectory() as scratch:
            path = os.path.join(scratch, 'meta.xml')
            with open(path, 'w') as stream:
                stream.write(metadata(users))
            with server(), mock.patch.object(accounts, 'named_like_panel_user',
                                             side_effect=lambda name: name == 'owner'):
                return method(path, os.path.join(scratch, 'status'))

    def test_metadata_restore_registers_the_database_with_its_own_user(self):
        self.assertEqual(1, self.restore_meta(EARLIER))
        self.databases.prepareDatabaseForRestore.assert_called_once_with('shop_db', 'shop_user', mock.ANY)
        self.assertEqual([entry[0] for entry in EARLIER],
                         [call[0][1] for call in self.databases.restoreDatabaseUser.call_args_list])

    def test_metadata_restore_without_a_usable_user_stops(self):
        self.assertEqual(0, self.restore_meta([('cp-pma-5', 'localhost')]))
        self.databases.prepareDatabaseForRestore.assert_not_called()
        self.databases.restoreDatabaseUser.assert_not_called()

    def test_repository_restore_chooses_the_same_way(self):
        source = (HERE / 'Backupsv2.py').read_text()
        self.assertIn("databaseAccounts.restored_database_user(\n"
                      "                        [databaseUser['user'] for databaseUser in databaseUsers])", source)
        self.assertIn('prepareDatabaseForRestore(dbName, registeredUser, self.website)', source)
        self.assertNotIn('prepareDatabaseForRestore(dbName, dbUser,', source)


class RestoredEntryTests(unittest.TestCase):
    """Every entry of a backup goes through the choice of the registered user and the restore of accounts."""

    def restore_all(self, users, panel_users=('owner',), existing=()):
        """Register the database as a restore does, then restore each listed entry in order."""
        with server(), mock.patch.object(accounts, 'named_like_panel_user',
                                         side_effect=lambda name: name.lower() in panel_users):
            self.registered = accounts.restored_database_user([user for user, host in users])
        # The registered user has its account at the panel's own host from the creation of the database.
        self.cursor = Cursor([('shop\\_db', self.registered, 'localhost', False)] + list(existing))
        made = []

        def create(name, user, password, create_database, host):
            made.append((name, user, create_database, host))
            self.cursor.granted.append(('shop\\_db', user, host, False))
            return 1

        with applied(panel(databases=(('shop_db', self.registered),), panel_users=panel_users)), \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(mock.Mock(), self.cursor)), \
                mock.patch.object(mysqlUtilities, 'createDatabase', side_effect=create), \
                mock.patch.object(mysqlUtilities, 'changePassword', return_value=1) as change, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile') as log:
            results = [mysqlUtilities.restoreDatabaseUser('shop_db', user, HASH, host) for user, host in users]
        self.made, self.change, self.log = made, change, log
        return results

    def passwords_set(self):
        return [(call[0][0], call[0][3]) for call in self.change.call_args_list]

    def test_earlier_backup_restores_the_user_at_both_hosts_and_nothing_else(self):
        self.assertEqual([1, 1, 1, 1], self.restore_all(EARLIER))
        self.assertEqual('shop_user', self.registered)
        self.assertEqual([('shop_user', 'localhost'), ('shop_user', '203.0.113.9')], self.passwords_set())
        # Only the user's account at the remote host is new.
        self.assertEqual([('shop_db', 'shop_user', 0, '203.0.113.9')], self.made)
        self.assertEqual([], self.cursor.changes())

    def test_user_listed_after_the_owners_account_is_the_registered_one(self):
        self.assertEqual([1, 1], self.restore_all([('owner', 'localhost'), ('exam_wp', 'localhost')]))
        self.assertEqual('exam_wp', self.registered)
        self.assertEqual([('exam_wp', 'localhost')], self.passwords_set())
        self.assertEqual([], self.made)

    def test_user_listed_after_an_account_nobody_here_is_named_like_is_restored_as_well(self):
        # The account an earlier release named after a reseller who is not on this server.
        users = [('alice', 'localhost'), ('exam_wp', 'localhost'), ('exam_wp', '203.0.113.9')]
        self.assertEqual([1, 1, 1], self.restore_all(users))
        self.assertEqual('alice', self.registered)
        self.assertEqual(users, self.passwords_set())
        self.assertEqual([('shop_db', 'exam_wp', 0, 'localhost'), ('shop_db', 'exam_wp', 0, '203.0.113.9')], self.made)

    def test_user_listed_after_a_phpmyadmin_account_is_the_registered_one(self):
        self.assertEqual([1, 1], self.restore_all([('cp-pma-5', 'localhost'), ('exam_wp', 'localhost')]))
        self.assertEqual('exam_wp', self.registered)
        self.assertEqual([('exam_wp', 'localhost')], self.passwords_set())

    def test_account_that_exists_on_this_server_is_never_given_the_password_from_a_backup(self):
        existing = [('other\\_db', 'other_user', 'localhost', False)]
        users = [('shop_user', 'localhost'), ('other_user', 'localhost'), ('other_user', '%')]
        self.assertEqual([1, 1, 1], self.restore_all(users, existing=existing))
        self.assertEqual([('shop_user', 'localhost')], self.passwords_set())
        self.assertEqual([], self.made)

    def test_role_and_entry_with_an_invalid_host_do_not_stop_the_restore(self):
        users = [('shop_user', 'localhost'), ('reporting', ''), ('shop_user', "x' y"), ('shop_user', '203.0.113.9')]
        self.assertEqual([1, 1, 1, 1], self.restore_all(users))
        self.assertEqual([('shop_user', 'localhost'), ('shop_user', '203.0.113.9')], self.passwords_set())

    def test_phpmyadmin_account_is_skipped_before_the_server_is_asked(self):
        self.assertEqual([1], self.restore_all([('cp-pma-5', 'localhost')]))
        self.assertIsNone(self.registered)
        self.assertEqual([], self.cursor.statements)
        self.assertEqual([], self.made)
        self.change.assert_not_called()
        self.assertIn('was not restored', self.log.call_args[0][0])

    def test_account_of_the_server_is_skipped(self):
        self.assertEqual([1, 1, 1], self.restore_all([('root', 'localhost'), ('Mysql', '%'), ('shop_user', '%')]))
        self.assertEqual([('shop_user', '%')], self.passwords_set())
        self.assertEqual([('shop_db', 'shop_user', 0, '%')], self.made)

    def test_repository_format_lists_users_the_same_way(self):
        # Backup V2 keeps the same entries as a list of user, host and password.
        entries = [{'user': user, 'host': host, 'password': HASH} for user, host in EARLIER]
        with server(), mock.patch.object(accounts, 'named_like_panel_user', side_effect=lambda name: name == 'owner'):
            self.assertEqual('shop_user', accounts.restored_database_user([entry['user'] for entry in entries]))


if __name__ == '__main__':
    unittest.main()
