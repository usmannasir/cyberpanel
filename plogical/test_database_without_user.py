"""A database registered without a user of its own is backed up, restored and left without one."""
import ast
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock
from xml.dom import minidom
from xml.etree import ElementTree

from plogical import databaseAccounts as accounts
from plogical import mysqlUtilities as module
from plogical.databaseProvisioning import create_without_user
from plogical.mysqlUtilities import mysqlUtilities
from plogical.test_database_restore_accounts import Rows

ROOT = Path(__file__).resolve().parents[1]


def server():
    return mock.patch.object(accounts, 'administrative_account', return_value='root')


class Accounts:
    """mysql.user as the panel reads it for a backup."""

    def __init__(self, rows, fail=False):
        self.rows, self.fail, self.asked = rows, fail, []

    @property
    def objects(self):
        return self

    def filter(self, user):
        self.asked.append(user)
        if self.fail:
            raise RuntimeError('table cannot be read')
        # The table is not trusted to compare exactly: a case variant comes back too.
        return [SimpleNamespace(user=name, host=host, password=password)
                for name, host, password in self.rows if name.lower() == user.lower()]


class RecordedUserTests(unittest.TestCase):
    def recorded(self, registered, rows, found=1, fail=False):
        self.accounts = Accounts(rows, fail)
        database = SimpleNamespace(dbName='shop_db', dbUser=registered)
        with server(), mock.patch.object(module, 'DBUsers', self.accounts, create=True), \
                mock.patch.object(mysqlUtilities, 'fetchuser', return_value=found) as fetch, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            answer = mysqlUtilities.backupUserOf(database)
        self.fetch = fetch
        return answer

    def test_user_with_one_account(self):
        self.assertEqual(('shop_user', '*HASH'), self.recorded('shop_user', [('shop_user', 'localhost', '*HASH')]))
        self.fetch.assert_not_called()

    def test_user_with_an_account_at_several_hosts(self):
        rows = [('shop_user', '127.0.0.1', '*ONE'), ('shop_user', 'localhost', '*TWO'), ('Shop_User', '%', '*NOT')]
        self.assertEqual(('shop_user', '*ONE'), self.recorded('shop_user', rows, found='shop_user'))

    def test_database_without_a_user_is_recorded_without_one(self):
        self.assertEqual(('-', ''), self.recorded('-', [('other_user', 'localhost', '*HASH')]))
        self.assertEqual([], self.accounts.asked)

    def test_user_without_an_account_is_recorded_as_no_user(self):
        for found in (0, 1):
            self.assertEqual(('-', ''), self.recorded('shop_user', [], found=found))

    def test_registration_under_an_account_of_the_server_records_no_user_and_no_password(self):
        for name in ('root', 'Root', 'cyberpanel', 'cp-pma-5'):
            self.assertEqual(('-', ''), self.recorded(name, [(name, 'localhost', '*SERVER')]), name)
            self.assertEqual([], self.accounts.asked)
        # Also when the server names such an account as the one that holds the grant.
        self.assertEqual(('-', ''), self.recorded('root', [('root', 'localhost', '*SERVER')], found='root'))

    def test_user_found_on_the_server_is_recorded(self):
        self.assertEqual(('shop_wp', '*HASH'),
                         self.recorded('-', [('shop_wp', 'localhost', '*HASH')], found='shop_wp'))

    def test_unreadable_accounts_record_no_user_instead_of_stopping_the_backup(self):
        self.assertEqual(('-', ''), self.recorded('shop_user', [], fail=True))


class BackupListTests(unittest.TestCase):
    def test_database_without_a_user_is_dumped_and_listed(self):
        users = {'shop_db': ('shop_user', '*HASH'), 'imported_db': ('-', '')}
        utilities = mock.Mock()
        utilities.backupUserOf.side_effect = lambda row: users[row.dbName]
        utilities.createDatabaseBackup.return_value = 1
        namespace = dict(os=os, ProcessUtilities=mock.Mock(), logging=mock.MagicMock(),
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=utilities))
        backup = self.method('BackupDatabases', namespace)
        with tempfile.TemporaryDirectory() as scratch:
            job = SimpleNamespace(
                BackupPath=scratch, CheckIfSleepNeeded=lambda: None,
                website=SimpleNamespace(domain='example.test', databases_set=SimpleNamespace(
                    all=lambda: [SimpleNamespace(dbName=name) for name in ('shop_db', 'imported_db')])))
            self.assertEqual((1, None), backup(job))
            with open(os.path.join(scratch, 'databases.json')) as stream:
                listed = json.load(stream)['databases']
        self.assertEqual([{'databaseName': 'shop_db', 'databaseUser': 'shop_user', 'password': '*HASH'},
                          {'databaseName': 'imported_db', 'databaseUser': '-', 'password': ''}], listed)
        self.assertEqual(['shop_db', 'imported_db'],
                         [call[0][0] for call in utilities.createDatabaseBackup.call_args_list])

    @staticmethod
    def method(name, namespace, filename='plogical/backupUtilities.py'):
        tree = ast.parse((ROOT / filename).read_text())
        found = next(node for owner in tree.body if isinstance(owner, ast.ClassDef) for node in owner.body
                     if isinstance(node, ast.FunctionDef) and node.name == name)
        found.decorator_list = []
        exec(compile(ast.fix_missing_locations(ast.Module(body=[found], type_ignores=[])), filename, 'exec'),
             namespace)
        return namespace[name]

    def test_older_incremental_job_lists_it_and_goes_on(self):
        users = {'shop_db': ('shop_user', '*HASH'), 'imported_db': ('-', '')}
        utilities = mock.Mock()
        utilities.backupUserOf.side_effect = lambda row: users[row.dbName]
        written = {}

        class Recorder:
            def __init__(self, path, mode='r'):
                self.path = path

            def write(self, text):
                written[self.path] = text

            def close(self):
                pass

        from xml.etree.ElementTree import Element, SubElement
        namespace = dict(os=mock.Mock(), Element=Element, SubElement=SubElement, ElementTree=ElementTree,
                         minidom=minidom, randint=lambda low, high: 4321, open=Recorder,
                         logging=mock.MagicMock(), ProcessUtilities=mock.Mock(), DNS=mock.Mock(),
                         eDomains=mock.MagicMock(), backupUtilities=mock.Mock(),
                         build_dns_records_xml=lambda rows: Element('dnsrecords'),
                         build_email_accounts_xml=lambda rows: Element('emails'),
                         mysqlUtilities=SimpleNamespace(mysqlUtilities=utilities))
        namespace['backupUtilities'].getAliases.return_value = []
        namespace['eDomains'].objects.filter.return_value.first.return_value = None
        prepare = self.method('prepareBackupMeta', namespace, 'IncBackups/IncBackups.py')
        admin = SimpleNamespace(userName='owner', password='x', firstName='a', lastName='b', email='c@example.test')
        website = SimpleNamespace(
            domain='example.test', phpSelection='PHP 8.3', externalApp='example', admin=admin,
            childdomains_set=SimpleNamespace(all=lambda: []),
            databases_set=SimpleNamespace(all=lambda: [SimpleNamespace(dbName=name)
                                                       for name in ('imported_db', 'shop_db')]))
        self.assertEqual(1, prepare(SimpleNamespace(website=website, statusPath='status')))
        document = ElementTree.fromstring(written['/home/cyberpanel/4321'])
        self.assertEqual([('imported_db', '-', None), ('shop_db', 'shop_user', '*HASH')],
                         [(entry.findtext('dbName'), entry.findtext('dbUser'), entry.find('password').text)
                          for entry in document.findall('Databases/database')])


class CreationTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.website = SimpleNamespace(domain='fixture.example', pk=1)
        self.model = mock.Mock()
        self.model.objects.filter.return_value.exists.return_value = False
        self.utilities = mock.Mock()
        self.utilities.databaseExists.return_value = False
        self.utilities.createEmptyDatabase.side_effect = lambda name, progress: progress('database_created') or 1

    def create(self, name='imported_db'):
        return create_without_user(name, self.website, self.utilities, self.model, self.directory.name, None)

    def test_database_is_created_and_registered_without_a_user_and_no_account_is_made(self):
        self.assertEqual((1, 'None'), self.create())
        self.model.objects.create.assert_called_once_with(website=self.website, dbName='imported_db', dbUser='-')
        self.utilities.createEmptyDatabase.assert_called_once()
        self.utilities.createDatabase.assert_not_called()
        record, = [name for name in os.listdir(self.directory.name) if name.endswith('.json')]
        with open(os.path.join(self.directory.name, record)) as stream:
            data = json.load(stream)
        self.assertEqual(('completed', 'imported_db', None), (data['stage'], data['database'], data['username']))

    def test_existing_database_or_registration_is_never_adopted(self):
        self.utilities.databaseExists.return_value = True
        self.assertEqual(0, self.create()[0])
        self.utilities.createEmptyDatabase.assert_not_called()
        self.utilities.databaseExists.return_value = False
        self.model.objects.filter.return_value.exists.return_value = True
        self.assertEqual(0, self.create()[0])
        self.utilities.createEmptyDatabase.assert_not_called()
        self.model.objects.create.assert_not_called()

    def test_failed_creation_registers_nothing(self):
        self.utilities.createEmptyDatabase.side_effect = None
        self.utilities.createEmptyDatabase.return_value = 0
        self.assertEqual(0, self.create()[0])
        self.model.objects.create.assert_not_called()

    def test_name_that_is_not_a_database_name_touches_nothing(self):
        self.assertEqual(0, self.create('bad`name')[0])
        self.assertEqual([], os.listdir(self.directory.name))
        self.utilities.databaseExists.assert_not_called()

    def test_empty_database_is_made_with_one_statement_and_no_account(self):
        connection, cursor = mock.Mock(), mock.Mock()
        with mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)):
            self.assertEqual(1, mysqlUtilities.createEmptyDatabase('imported_db'))
        self.assertEqual([mock.call('CREATE DATABASE `imported_db`')], cursor.execute.call_args_list)
        connection.close.assert_called_once()


class RestoreTests(unittest.TestCase):
    def prepare(self, user, existing=None, website=1):
        rows = mock.Mock()
        rows.return_value.first.return_value = existing
        connection, cursor = mock.Mock(), mock.Mock()
        cursor.fetchall.return_value = [('imported_db',)]
        with mock.patch.object(module.Databases.objects, 'filter', rows), \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(connection, cursor)), \
                mock.patch.object(mysqlUtilities, 'createDatabaseWithoutUser', return_value=(1, 'None')) as without, \
                mock.patch.object(mysqlUtilities, 'createDatabaseAndRegister', return_value=(1, 'None')) as normal:
            answer = mysqlUtilities.prepareDatabaseForRestore('imported_db', user, SimpleNamespace(pk=website))
        self.without, self.normal = without, normal
        return answer

    def test_new_database_recorded_without_a_user_gets_none(self):
        self.assertEqual((1, 'None'), self.prepare('-'))
        self.without.assert_called_once()
        self.normal.assert_not_called()

    def test_new_database_with_a_user_is_created_as_before(self):
        self.assertEqual((1, 'None'), self.prepare('shop_user'))
        self.normal.assert_called_once()
        self.without.assert_not_called()

    def test_existing_database_without_a_user_keeps_its_registration(self):
        for recorded, here in (('-', '-'), ('shop_user', '-'), ('-', 'shop_user')):
            existing = SimpleNamespace(website_id=1, dbUser=here)
            self.assertEqual((1, 'None'), self.prepare(recorded, existing), (recorded, here))
            self.without.assert_not_called()
            self.normal.assert_not_called()

    def test_database_of_another_website_or_user_is_still_refused(self):
        self.assertEqual(0, self.prepare('-', SimpleNamespace(website_id=2, dbUser='-'))[0])
        self.assertEqual(0, self.prepare('shop_user', SimpleNamespace(website_id=1, dbUser='other_user'))[0])

    def test_dump_is_loaded_and_no_password_is_set_for_a_database_without_a_user(self):
        config = json.dumps({'mysqluser': 'root', 'mysqlpassword': 'x', 'mysqlport': 3306, 'mysqlhost': 'localhost'})
        with mock.patch('builtins.open', mock.mock_open(read_data=config)), \
                mock.patch.object(module.os.path, 'exists', return_value=True), \
                mock.patch.object(mysqlUtilities, 'detectBackupFormat', return_value={'compressed': False}), \
                mock.patch.object(module.databaseImport, 'import_dump', return_value=1) as load, \
                mock.patch.object(mysqlUtilities, 'registeredUser', return_value='-'), \
                mock.patch.object(mysqlUtilities, 'changePassword') as change, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            self.assertEqual(1, mysqlUtilities.restoreDatabaseBackup('imported_db', '/fixture', ''))
        load.assert_called_once()
        change.assert_not_called()

    def test_both_readers_of_the_database_list_restore_through_these_steps(self):
        source = (ROOT / 'plogical' / 'backupUtilities.py').read_text()
        self.assertEqual(2, source.count(
            "prepareDatabaseForRestore(db['databaseName'], db['databaseUser'], self.website)"))
        self.assertEqual(2, source.count(
            "restoreDatabaseBackup(db['databaseName'], self.databasesPath, db['password'])"))


class DetectedUserTests(unittest.TestCase):
    """fetchuser registers a granted account only when it can be this website's database user."""

    def detect(self, registered, granted, allowed):
        database = SimpleNamespace(dbName='shop_db', dbUser=registered, website_id=7, save=mock.Mock())
        with mock.patch.object(module.Databases.objects, 'get', return_value=database), \
                mock.patch.object(mysqlUtilities, 'setupConnection', return_value=(mock.Mock(), mock.Mock())), \
                mock.patch.object(module.databaseGrants, 'accounts_granted',
                                  return_value=[(user, 'localhost') for user in granted]), \
                mock.patch.object(accounts, 'may_register_user',
                                  side_effect=lambda name, website: name in allowed) as asked, \
                mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'):
            answer = mysqlUtilities.fetchuser('shop_db')
        self.database, self.asked = database, asked
        return answer

    def test_registered_user_with_its_grant_stays(self):
        self.assertEqual('shop_user', self.detect('shop_user', ['other_user', 'shop_user'], ['other_user']))
        self.database.save.assert_not_called()

    def test_account_that_may_be_this_websites_user_is_registered(self):
        self.assertEqual('shop_wp', self.detect('-', ['reseller_one', 'shop_wp'], ['shop_wp']))
        self.assertEqual('shop_wp', self.database.dbUser)
        self.database.save.assert_called_once()
        self.asked.assert_any_call('shop_wp', 7)

    def test_account_that_may_not_leaves_the_registration_as_it_is(self):
        self.assertEqual(1, self.detect('-', ['reseller_one', 'other_site_user'], []))
        self.assertEqual('-', self.database.dbUser)
        self.database.save.assert_not_called()

    def rule(self, name, databases=(), additional=(), panel_user=False):
        models = SimpleNamespace(
            Databases=Rows({'dbUser': user, 'website_id': site} for user, site in databases),
            DatabasesUsers=SimpleNamespace(objects=SimpleNamespace(filter=lambda **conditions: SimpleNamespace(
                select_related=lambda field: [
                    SimpleNamespace(username=user, owner=SimpleNamespace(website_id=site))
                    for user, site in additional if user.lower() == conditions['username__iexact'].lower()]))))
        with server(), mock.patch.dict('sys.modules', {'databases.models': models}), \
                mock.patch.object(accounts, 'named_like_panel_user', return_value=panel_user):
            return accounts.may_register_user(name, 7)

    def test_rule_for_a_user_of_this_website(self):
        self.assertTrue(self.rule('shop_wp'))
        self.assertTrue(self.rule('shop_wp', databases=(('shop_wp', 7),), additional=(('shop_wp', 7),)))

    def test_rule_refuses_the_user_of_another_websites_database_in_any_case(self):
        self.assertFalse(self.rule('shop_wp', databases=(('Shop_WP', 8),)))
        self.assertFalse(self.rule('shop_wp', databases=(('shop_wp', 7), ('shop_wp', 8))))
        self.assertFalse(self.rule('shop_wp', additional=(('SHOP_wp', 8),)))

    def test_rule_refuses_names_no_database_user_may_have(self):
        self.assertFalse(self.rule('reseller_one', panel_user=True))
        for name in ('root', 'cp-pma-5', 'shop-wp', '-', None):
            self.assertFalse(self.rule(name), repr(name))


if __name__ == '__main__':
    unittest.main()
