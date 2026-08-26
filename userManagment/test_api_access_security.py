import json
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from plogical.securityUtils import generate_api_token, is_current_api_token
from userManagment.views import saveChangesAPIAccess


class APIAccessKeyManagementTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def request(self, access):
        request = self.factory.post(
            '/users/saveChangesAPIAccess',
            data=json.dumps({'accountUsername': 'admin', 'access': access}),
            content_type='application/json',
        )
        request.session = {'userID': 1}
        return request

    @mock.patch('userManagment.views.ACLManager.loadedACL', return_value={'admin': 1})
    @mock.patch('userManagment.views.Administrator.objects.get')
    def test_enabling_rotates_legacy_key_and_returns_current_key(self, get_admin, unused_acl):
        account = SimpleNamespace(
            token='Basic ' + ('a' * 64),
            api=0,
            save=mock.Mock(),
        )
        get_admin.return_value = account

        response = saveChangesAPIAccess(self.request('Enable'))
        body = json.loads(response.content)

        self.assertEqual(body['status'], 1)
        self.assertTrue(is_current_api_token(body['apiToken']))
        self.assertEqual(body['apiToken'], account.token)
        self.assertEqual(account.api, 1)

    @mock.patch('userManagment.views.ACLManager.loadedACL', return_value={'admin': 1})
    @mock.patch('userManagment.views.Administrator.objects.get')
    def test_regenerate_replaces_current_key(self, get_admin, unused_acl):
        old_token = generate_api_token()
        account = SimpleNamespace(token=old_token, api=1, save=mock.Mock())
        get_admin.return_value = account

        response = saveChangesAPIAccess(self.request('Regenerate'))
        body = json.loads(response.content)

        self.assertEqual(body['status'], 1)
        self.assertTrue(is_current_api_token(body['apiToken']))
        self.assertNotEqual(body['apiToken'], old_token)
        self.assertEqual(account.api, 1)

    @mock.patch('userManagment.views.ACLManager.loadedACL', return_value={'admin': 1})
    @mock.patch('userManagment.views.Administrator.objects.get')
    def test_disabling_revokes_stored_key(self, get_admin, unused_acl):
        account = SimpleNamespace(token=generate_api_token(), api=1, save=mock.Mock())
        get_admin.return_value = account

        response = saveChangesAPIAccess(self.request('Disable'))
        body = json.loads(response.content)

        self.assertEqual(body, {'status': 1})
        self.assertEqual(account.api, 0)
        self.assertEqual(account.token, '')
