"""Creating a user checks the name first."""
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
