"""Creating a user checks the name first; a change of what a user may reach takes the phpMyAdmin account away."""
import json
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from userManagment import views


def post(payload, user=1):
    request = RequestFactory().post('/users/x', data=json.dumps(payload), content_type='application/json')
    request.session = {'userID': user}
    return request


class UserCreationTests(SimpleTestCase):
    def create(self, name, acl=None):
        payload = {'firstName': 'Site Owner', 'lastName': 'Account User', 'email': 'owner@example.com',
                   'userName': name, 'password': 'owner-password', 'websitesLimit': 1, 'selectedACL': 'user'}
        with mock.patch('validators.email', return_value=True), \
                mock.patch.object(views.ACLManager, 'CheckRegEx', return_value=1), \
                mock.patch.object(views.ACLManager, 'websitesLimitCheck', return_value=1), \
                mock.patch.object(views.ACLManager, 'isAdminACL', return_value=False), \
                mock.patch.object(views.ACLManager, 'loadedACL',
                                  return_value=acl or {'admin': 0, 'changeUserACL': 0, 'createNewUser': 1}), \
                mock.patch.object(views.ACL.objects, 'get', return_value=SimpleNamespace(name='user')), \
                mock.patch.object(views, 'Administrator') as users:
            users.objects.get.return_value = SimpleNamespace(pk=9)
            response = views.submitUserCreation(post(payload, 9))
        self.users = users
        return json.loads(response.content.decode())

    def test_plain_name_is_created(self):
        for acl in (None, {'admin': 1}, {'admin': 0, 'changeUserACL': 1, 'createNewUser': 1}):
            answer = self.create('john.doe', acl)
            self.assertEqual(1, answer['createStatus'])
            self.assertEqual('john.doe', self.users.call_args[1]['userName'])
            self.users.return_value.save.assert_called_once_with()

    def test_other_names_are_refused_for_every_role_before_anything_is_stored(self):
        for acl in (None, {'admin': 1}, {'admin': 0, 'changeUserACL': 1, 'createNewUser': 1}):
            for name in ('x /etc/shadow', 'x & id', "x' OR '1", 'a/../../b', ' x', 'x>y', '-rf', 'John Smith',
                         '', None, 7, ['x'], 'x' * 51, 'root', 'Root', 'mysql', 'cyberpanel', 'cp-pma-5'):
                answer = self.create(name, acl)
                self.assertEqual(0, answer['createStatus'], repr(name))
                self.assertTrue(answer['error_message'].startswith(('A user name starts with', 'This user name is reserved')),
                                answer['error_message'])
                self.users.assert_not_called()
                self.users.objects.get.assert_not_called()

    def test_command_line_example_uses_a_name_that_is_accepted(self):
        import os
        from plogical.panelUserNames import new_name_refusal
        path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(views.__file__))), 'cli', 'cyberPanel.py')
        with open(path) as stream:
            source = stream.read()
        example = source[source.index("completeCommandExample = 'cyberpanel createUser "):]
        name = example.split('--userName ')[1].split(' ')[0]
        self.assertIsNone(new_name_refusal(name), name)


class AccessRemovalTests(SimpleTestCase):
    def setUp(self):
        self.users = {
            'customer': SimpleNamespace(pk=7, userName='customer', owner=4, state='ACTIVE', acl=None, save=mock.Mock(),
                                        delete=mock.Mock(), initWebsitesLimit=1),
            'reseller1': SimpleNamespace(pk=4, userName='reseller1', owner=1, state='ACTIVE', save=mock.Mock()),
            'reseller2': SimpleNamespace(pk=5, userName='reseller2', owner=1, state='ACTIVE', save=mock.Mock()),
            'admin': SimpleNamespace(pk=1, userName='admin', owner=1, state='ACTIVE', save=mock.Mock()),
        }
        self.children = [SimpleNamespace(pk=8, userName='child', delete=mock.Mock())]

        def get(**kwargs):
            if 'userName' in kwargs:
                return self.users[kwargs['userName']]
            return [user for user in self.users.values() if user.pk == kwargs['pk']][0]

        def filtered(**kwargs):
            if 'owner' in kwargs:
                return self.children
            return [user for user in self.users.values() if user.pk == kwargs['pk']]

        patches = {
            'get': mock.patch.object(views.Administrator.objects, 'get', side_effect=get),
            'filter': mock.patch.object(views.Administrator.objects, 'filter', side_effect=filtered),
            'loaded': mock.patch.object(views.ACLManager, 'loadedACL', return_value={'admin': 1}),
            'owner': mock.patch.object(views.ACLManager, 'checkUserOwnerShip', return_value=1),
            'limit': mock.patch.object(views.ACLManager, 'websitesLimitCheck', return_value=1),
            'retire': mock.patch.object(views.phpmyadminAccess, 'retire', return_value=1),
        }
        for name, item in patches.items():
            setattr(self, name, item.start())
            self.addCleanup(item.stop)

    def answer(self, view, payload):
        return json.loads(view(post(payload)).content.decode())

    def test_suspended_user_loses_the_account_and_a_resumed_one_is_left_alone(self):
        with mock.patch('userManagment.userManager.UserManager'):
            self.assertEqual(1, self.answer(views.controlUserState,
                                            {'accountUsername': 'customer', 'state': 'SUSPEND'})['status'])
            self.retire.assert_called_once_with([self.users['customer']])
            self.assertEqual(1, self.answer(views.controlUserState,
                                            {'accountUsername': 'customer', 'state': 'ACTIVATE'})['status'])
        self.retire.assert_called_once_with([self.users['customer']])

    def test_deleted_user_and_the_users_below_lose_their_accounts_first(self):
        order = mock.Mock()
        order.attach_mock(self.retire, 'retire')
        order.attach_mock(self.users['customer'].delete, 'delete')
        self.assertEqual(1, self.answer(views.submitUserDeletion, {'accountUsername': 'customer'})['deleteStatus'])
        self.assertEqual([mock.call.retire([self.users['customer']] + self.children), mock.call.delete()],
                         order.mock_calls)

    def test_user_given_another_role_loses_the_account(self):
        role = SimpleNamespace(name='user')
        for acl in ({'admin': 1}, {'admin': 0, 'changeUserACL': 1}):
            self.retire.reset_mock()
            self.loaded.return_value = acl
            with mock.patch.object(views.ACL.objects, 'get', return_value=role), \
                    mock.patch.object(views.ACLManager, 'isAdminACL', return_value=False):
                self.assertEqual(1, self.answer(views.changeACLFunc,
                                                {'selectedUser': 'customer', 'selectedACL': 'user'})['status'])
            self.retire.assert_called_once_with([self.users['customer']])
            self.assertIs(role, self.users['customer'].acl)

    def test_users_of_a_changed_role_lose_their_accounts(self):
        members = [self.users['customer'], self.users['reseller1']]
        role = SimpleNamespace(save=mock.Mock(), administrator_set=SimpleNamespace(all=lambda: members))
        with mock.patch.object(views.ACL.objects, 'get', return_value=role):
            self.assertEqual(1, self.answer(views.submitACLModifications,
                                            {'aclToModify': 'user', 'adminStatus': 0, 'listDatabases': 0})['status'])
        self.retire.assert_called_once_with(members)

    def test_reseller_a_user_leaves_loses_the_account(self):
        payload = {'userToBeModified': 'customer', 'newOwner': 'reseller2', 'websitesLimit': 1}
        self.assertEqual(1, self.answer(views.saveResellerChanges, payload)['status'])
        self.retire.assert_called_once_with([self.users['reseller1']])
        self.assertEqual(5, self.users['customer'].owner)
        self.retire.reset_mock()
        self.assertEqual(1, self.answer(views.saveResellerChanges, payload)['status'])
        self.retire.assert_not_called()
