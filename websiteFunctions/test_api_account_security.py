import json
from types import SimpleNamespace
from unittest import mock

from django.http import HttpResponse
from django.test import SimpleTestCase

from plogical.securityUtils import api_token_matches
from websiteFunctions.website import WebsiteManager


class WebsiteAPIOwnerSecurityTests(SimpleTestCase):
    def payload(self, acl='user'):
        return {
            'adminUser': 'reseller',
            'adminPass': 'correct-password',
            'ownerEmail': 'owner@example.com',
            'websiteOwner': 'site-owner',
            'ownerPassword': 'owner-password',
            'packageName': 'Default',
            'domainName': 'example.com',
            'acl': acl,
        }

    @mock.patch('websiteFunctions.website.hashPassword.check_password', return_value=True)
    @mock.patch('websiteFunctions.website.ACLManager.loadedACL')
    @mock.patch('websiteFunctions.website.ACL.objects.get')
    @mock.patch('websiteFunctions.website.Administrator')
    def test_api_created_owner_receives_usable_random_token(
            self, administrator, get_acl, loaded_acl, unused_password_check):
        caller = SimpleNamespace(
            pk=9,
            password='stored-hash',
            acl=SimpleNamespace(adminStatus=1),
        )
        administrator.objects.get.return_value = caller
        get_acl.return_value = SimpleNamespace(name='user', adminStatus=0)
        loaded_acl.return_value = {'admin': 1}
        manager = WebsiteManager()
        manager.submitWebsiteCreation = mock.Mock(return_value=HttpResponse('{}'))

        manager.createWebsiteAPI(self.payload())

        created = administrator.call_args.kwargs
        self.assertEqual(created['api'], 1)
        self.assertTrue(api_token_matches(created['token'], created['token']))
        self.assertFalse(api_token_matches(created['token'], 'None'))
        manager.submitWebsiteCreation.assert_called_once()

    @mock.patch('websiteFunctions.website.hashPassword.check_password', return_value=True)
    @mock.patch('websiteFunctions.website.ACLManager.loadedACL')
    @mock.patch('websiteFunctions.website.ACL.objects.get')
    @mock.patch('websiteFunctions.website.Administrator')
    def test_non_admin_cannot_assign_admin_acl(
            self, administrator, get_acl, loaded_acl, unused_password_check):
        caller = SimpleNamespace(pk=9, password='stored-hash')
        administrator.objects.get.return_value = caller
        get_acl.return_value = SimpleNamespace(
            name='custom-admin',
            adminStatus=0,
            config='{"adminStatus": 1}',
        )
        loaded_acl.return_value = {
            'admin': 0,
            'createWebsite': 1,
            'changeUserACL': 1,
        }
        manager = WebsiteManager()
        manager.submitWebsiteCreation = mock.Mock(return_value=HttpResponse('{}'))

        response = manager.createWebsiteAPI(self.payload(acl='custom-admin'))
        body = json.loads(response.content.decode())

        self.assertEqual(body['createWebSiteStatus'], 0)
        self.assertIn('authorized', body['error_message'])
        self.assertEqual(administrator.call_count, 0)
        manager.submitWebsiteCreation.assert_not_called()
