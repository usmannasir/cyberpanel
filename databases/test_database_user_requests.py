"""Password, remote access and deletion requests act on the registered name of a database the caller manages."""
import json
import unittest
from types import SimpleNamespace
from unittest import mock

from databases import databaseManager as module
from databases.databaseManager import DatabaseManager
from plogical import databaseAccounts


def site(domain):
    return SimpleNamespace(domain=domain)


def database(name, user, domain='mine.example'):
    return SimpleNamespace(pk=1, dbName=name, dbUser=user, website=site(domain))


class RequestTests(unittest.TestCase):
    def setUp(self):
        # What the panel's table returns for a user name: it compares without regard to case.
        self.registered = [database('exam_shop', 'exam_user')]
        self.owned = {'mine.example'}
        self.panel_users = set()
        self.accounts = [SimpleNamespace(user='exam_user', host='localhost', password='*HASH'),
                         SimpleNamespace(user='exam_user', host='127.0.0.1', password='*HASH')]
        self.meta = None
        databases = mock.Mock()
        databases.objects.filter.side_effect = lambda dbUser: [
            row for row in self.registered if row.dbUser.lower() == str(dbUser).lower()]
        databases.objects.get.side_effect = lambda dbName: [
            row for row in self.registered if row.dbName.lower() == str(dbName).lower()][0]

        def meta_get(**unused):
            if self.meta is None:
                raise LookupError('no remote access yet')
            return self.meta

        patches = {
            'loaded': mock.patch.object(module.ACLManager, 'loadedACL', return_value={'admin': 0}),
            'permission': mock.patch.object(module.ACLManager, 'currentContextPermission', return_value=1),
            'ownership': mock.patch.object(module.ACLManager, 'checkOwnership',
                                           side_effect=lambda domain, admin, acl: 1 if domain in self.owned else 0),
            'refused': mock.patch.object(module.ACLManager, 'loadErrorJson', return_value='refused'),
            'admin': mock.patch.object(module.Administrator.objects, 'get', return_value='admin-row'),
            'models': mock.patch.dict('sys.modules', {'databases.models': SimpleNamespace(Databases=databases)}),
            'databases': mock.patch.object(module, 'Databases', databases),
            'panel': mock.patch.object(databaseAccounts, 'named_like_panel_user',
                                       side_effect=lambda name: name.lower() in self.panel_users),
            'server': mock.patch.object(databaseAccounts, 'administrative_account', return_value='root'),
            'change': mock.patch.object(module.mysqlUtilities, 'changePassword', return_value=1),
            'create': mock.patch.object(module.mysqlUtilities, 'createDatabase', return_value=1),
            'enable': mock.patch.object(module.mysqlUtilities, 'allowRemoteAccess', return_value=1),
            'delete': mock.patch.object(module.mysqlUtilities, 'submitDBDeletion', return_value=(1, 'None')),
            'connect': mock.patch.object(module.mysqlUtilities, 'setupConnection', return_value=(0, 0)),
            'submit': mock.patch.object(module.mysqlUtilities, 'submitDBCreation', return_value=(1, 'None')),
            'server_accounts': mock.patch.object(module.DBUsers.objects, 'filter',
                                                 side_effect=lambda user: [a for a in self.accounts
                                                                           if a.user.lower() == user.lower()]),
            'meta_new': mock.patch.object(module, 'DBMeta'),
            'log': mock.patch.object(module.logging.CyberCPLogFileWriter, 'writeToFile'),
        }
        for name, item in patches.items():
            setattr(self, name, item.start())
            self.addCleanup(item.stop)
        self.meta_new.objects.get.side_effect = meta_get

    def answer(self, response):
        return response if response == 'refused' else json.loads(response.content.decode())


class PasswordTests(RequestTests):
    def ask(self, user='exam_user', password='new-password'):
        return self.answer(DatabaseManager().changePassword(5, {'dbUserName': user, 'dbPassword': password}))

    def test_password_of_an_own_database_user_is_changed_on_every_host(self):
        self.assertEqual(1, self.ask()['changePasswordStatus'])
        self.change.assert_called_once_with('exam_user', 'new-password')

    def test_name_in_another_case_than_the_registration_is_refused(self):
        # The caller owns a registration that differs from the typed name by case only.
        self.registered = [database('exam_shop', 'Root'), database('exam_blog', 'Reseller1'),
                           database('exam_wiki', 'Other_User')]
        for typed in ('root', 'ROOT', 'reseller1', 'other_user', 'OTHER_USER'):
            self.assertEqual('refused', self.ask(typed), typed)
        self.change.assert_not_called()

    def test_registered_name_is_what_reaches_the_server(self):
        self.registered = [database('exam_one', 'Exam_User'), database('exam_two', 'exam_user')]
        self.assertEqual(1, self.ask('exam_user')['changePasswordStatus'])
        self.change.assert_called_once_with('exam_user', 'new-password')

    def test_user_of_a_database_of_somebody_else_is_refused(self):
        self.registered = [database('other_shop', 'other_user', 'theirs.example')]
        self.assertEqual('refused', self.ask('other_user'))
        self.change.assert_not_called()

    def test_user_shared_with_a_website_of_somebody_else_is_refused(self):
        self.registered = [database('exam_shop', 'shared_user'), database('other_shop', 'shared_user', 'theirs.example')]
        self.assertEqual('refused', self.ask('shared_user'))
        self.registered.reverse()
        self.assertEqual('refused', self.ask('shared_user'))
        self.change.assert_not_called()

    def test_unknown_user_is_refused(self):
        self.assertEqual('refused', self.ask('nobody'))
        self.change.assert_not_called()

    def test_registration_under_an_account_of_the_server_is_refused_and_reported(self):
        for name in ('root', 'mysql', 'cyberpanel', 'public', 'rdsadmin'):
            self.registered = [database('imported_db', name)]
            answer = self.ask(name)
            self.assertEqual(0, answer['changePasswordStatus'], name)
            self.assertIn('does not change', answer['error_message'])
        self.change.assert_not_called()
        self.assertEqual(5, self.log.call_count)
        self.assertIn('imported_db', self.log.call_args[0][0])

    def test_registration_under_the_name_of_a_panel_user_is_refused(self):
        self.panel_users = {'reseller1'}
        self.registered = [database('exam_shop', 'reseller1')]
        self.assertEqual(0, self.ask('reseller1')['changePasswordStatus'])
        self.registered = [database('exam_shop', 'Reseller1')]
        self.assertEqual(0, self.ask('Reseller1')['changePasswordStatus'])
        self.change.assert_not_called()

    def test_password_must_be_a_text_that_is_not_empty(self):
        for password in ('', None, 7, ['x'], {'a': 1}, True):
            self.assertEqual(0, self.ask(password=password)['changePasswordStatus'], repr(password))
        self.change.assert_not_called()

    def test_failure_of_the_server_is_reported(self):
        self.change.return_value = 0
        self.assertEqual(0, self.ask()['changePasswordStatus'])

    def test_new_database_needs_a_password_that_is_a_text(self):
        for password in ('', None, 7, ['x'], {'a': 1}):
            response = DatabaseManager().submitDBCreation(5, {
                'databaseWebsite': 'mine.example', 'dbName': 'shop', 'dbUsername': 'user', 'dbPassword': password})
            self.assertEqual(0, self.answer(response)['createDBStatus'], repr(password))
        self.submit.assert_not_called()


class RemoteAccessTests(RequestTests):
    def ask(self, user='exam_user', host='203.0.113.5'):
        return self.answer(DatabaseManager().allowRemoteIP(5, {'dbUserName': user, 'remoteIP': host}))

    def test_remote_account_is_opened_for_the_registered_user(self):
        self.assertEqual({'status': 1}, self.ask())
        (name, user, temporary, create, host), unused = self.create.call_args
        self.assertEqual(('exam_shop', 'exam_user', 0, '203.0.113.5'), (name, user, create, host))
        self.assertNotEqual('cyberpanel', temporary)
        self.assertEqual(32, len(temporary))
        self.change.assert_called_once_with('exam_user', '*HASH', 1, '203.0.113.5')
        unused, saved = self.meta_new.call_args
        self.assertEqual({'remoteIP': '203.0.113.5'}, json.loads(saved['value']))

    def test_nothing_is_created_when_the_local_account_cannot_be_read(self):
        self.accounts = []
        answer = self.ask()
        self.assertEqual(0, answer['status'])
        self.create.assert_not_called()
        self.change.assert_not_called()
        self.meta_new.assert_not_called()

    def test_account_that_cannot_get_the_users_password_is_removed_and_not_recorded(self):
        self.change.return_value = 0
        cursor = mock.Mock()
        connection = mock.Mock()
        self.connect.return_value = (connection, cursor)
        self.assertEqual(0, self.ask()['status'])
        cursor.execute.assert_called_once_with('DROP USER IF EXISTS %s@%s', ('exam_user', '203.0.113.5'))
        connection.close.assert_called_once_with()
        self.meta_new.assert_not_called()

    def test_new_remote_host_replaces_the_previous_one(self):
        self.accounts.append(SimpleNamespace(user='exam_user', host='198.51.100.7', password='*HASH'))
        self.meta = mock.Mock(value=json.dumps({'remoteIP': '198.51.100.7'}))
        cursor = mock.Mock()
        self.connect.return_value = (mock.Mock(), cursor)
        self.assertEqual({'status': 1}, self.ask())
        cursor.execute.assert_called_once_with('DROP USER IF EXISTS %s@%s', ('exam_user', '198.51.100.7'))
        self.assertEqual({'remoteIP': '203.0.113.5'}, json.loads(self.meta.value))
        self.meta.save.assert_called_once_with()

    def test_name_in_another_case_than_the_registration_is_refused(self):
        self.registered = [database('exam_shop', 'Root'), database('exam_blog', 'Other_User')]
        for typed in ('root', 'other_user'):
            self.assertEqual('refused', self.ask(typed), typed)
        self.create.assert_not_called()
        self.change.assert_not_called()

    def test_account_of_the_server_or_named_like_a_panel_user_is_refused(self):
        self.panel_users = {'reseller1'}
        for name in ('root', 'cyberpanel', 'reseller1'):
            self.registered = [database('imported_db', name)]
            self.assertEqual(0, self.ask(name)['status'], name)
        self.create.assert_not_called()
        self.enable.assert_not_called()

    def test_user_of_a_database_of_somebody_else_is_refused(self):
        self.registered = [database('other_shop', 'other_user', 'theirs.example')]
        self.assertEqual('refused', self.ask('other_user'))
        self.create.assert_not_called()

    def test_host_is_matched_as_a_whole(self):
        for host in ('203.0.113.5\n', "x' OR '1", 'a b', '', None, 7, ['%'], 'x' * 256, "%'@'localhost"):
            self.assertEqual('refused', self.ask(host=host), repr(host))
        self.create.assert_not_called()
        self.enable.assert_not_called()

    def test_reading_the_remote_host_needs_the_registered_name(self):
        manager = DatabaseManager()
        self.assertEqual({'status': 1, 'dbHost': 'localhost'},
                         self.answer(manager.remoteAccess(5, {'dbUserName': 'exam_user'})))
        self.assertEqual('refused', self.answer(manager.remoteAccess(5, {'dbUserName': 'EXAM_USER'})))
        self.registered = [database('other_shop', 'other_user', 'theirs.example')]
        self.assertEqual('refused', self.answer(manager.remoteAccess(5, {'dbUserName': 'other_user'})))


class DeletionTests(RequestTests):
    def ask(self, name):
        return self.answer(DatabaseManager().submitDatabaseDeletion(5, {'dbName': name}))

    def test_registered_database_is_deleted_under_its_registered_name(self):
        self.assertEqual(1, self.ask('exam_shop')['deleteStatus'])
        self.delete.assert_called_once_with('exam_shop')

    def test_name_in_another_case_removes_nothing(self):
        for name in ('Exam_Shop', 'EXAM_SHOP'):
            self.assertEqual(0, self.ask(name)['deleteStatus'], name)
        self.delete.assert_not_called()


if __name__ == '__main__':
    unittest.main()
