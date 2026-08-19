import json
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from userManagment.views import submitUserCreation


class UserACLAssignmentSecurityTests(SimpleTestCase):
    @mock.patch('validators.email', return_value=True)
    @mock.patch('userManagment.views.ACLManager.CheckRegEx', return_value=1)
    @mock.patch('userManagment.views.ACLManager.websitesLimitCheck', return_value=1)
    @mock.patch('userManagment.views.ACLManager.loadedACL')
    @mock.patch('userManagment.views.ACL.objects.get')
    @mock.patch('userManagment.views.Administrator')
    def test_non_admin_cannot_create_user_with_custom_admin_acl(
            self, administrator, get_acl, loaded_acl, unused_limit_check,
            unused_regex_check, unused_email_check):
        loaded_acl.return_value = {
            'admin': 0,
            'changeUserACL': 1,
            'createNewUser': 1,
        }
        get_acl.return_value = SimpleNamespace(
            name='custom-admin',
            adminStatus=0,
            config='{"adminStatus": 1}',
        )
        administrator.objects.get.return_value = SimpleNamespace(pk=9)
        request = RequestFactory().post(
            '/users/submitUserCreation',
            data=json.dumps({
                'firstName': 'Site Owner',
                'lastName': 'Account User',
                'email': 'owner@example.com',
                'userName': 'site-owner',
                'password': 'owner-password',
                'websitesLimit': 1,
                'selectedACL': 'custom-admin',
                'securityLevel': 'HIGH',
            }),
            content_type='application/json',
        )
        request.session = {'userID': 9}

        response = submitUserCreation(request)
        body = json.loads(response.content.decode())

        self.assertEqual(body['createStatus'], 0)
        self.assertIn('authorized', body['error_message'])
        self.assertEqual(administrator.call_count, 0)
