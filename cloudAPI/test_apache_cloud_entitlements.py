"""Conditional paid Apache guard precedes optional cloud account mutation."""
import json
from pathlib import Path
import sys
from unittest import mock
import unittest
from types import SimpleNamespace

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from cloudAPI.test_wordpress_cloud_entitlements import load_cloud, Response


class ApacheCloudEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.ns,self.services,self.admin,self.output_file=load_cloud()
        self.acl=self.services['ACLManager']
        self.password=mock.Mock()
        self.ns['hashPassword']=self.password
        self.ns['ACL']=mock.Mock()
        self.data={'UserAccountName':'owned','UserPassword':'inert','FullName':'Owned',
                   'adminEmail':'owner@example.test','domainName':'owned.example','apacheBackend':1}
        self.cloud=self.ns['CloudManager'](self.data,self.admin)
        self.expected=Response('{"status":1,"createWebSiteStatus":1}')
        self.services['WebsiteManager'].return_value.submitWebsiteCreation.return_value=self.expected

    def no_work(self):
        self.password.assert_not_called()
        self.assertEqual(self.password.mock_calls,[])
        self.services['Administrator'].assert_not_called()
        self.services['Administrator'].return_value.save.assert_not_called()
        self.services['WebsiteManager'].assert_not_called()
        self.output_file.assert_not_called()

    def test_unpaid_apache_stops_before_cloud_account_creation(self):
        response=self.cloud.submitWebsiteCreation()
        self.assertEqual(json.loads(response.content)['createWebSiteStatus'],0)
        self.acl.CheckForPremFeature.assert_called_once_with('all')
        self.no_work()

    def test_lookup_failure_and_invalid_flag_stop_before_account_work(self):
        self.acl.CheckForPremFeature.side_effect=TimeoutError('unavailable')
        self.assertEqual(json.loads(self.cloud.submitWebsiteCreation().content)['status'],0)
        self.no_work()
        self.data['apacheBackend']='invalid'
        self.assertEqual(json.loads(self.cloud.submitWebsiteCreation().content)['status'],0)
        self.no_work()

    def test_authenticated_router_applies_guard_before_optional_account_creation(self):
        request=SimpleNamespace(body=json.dumps(dict(self.data,controller='submitWebsiteCreation',serverUserName='admin')).encode(),
                                META={'HTTP_AUTHORIZATION':'inert-token'},session={})
        self.assertEqual(json.loads(self.ns['router'](request).content)['status'],0)
        self.no_work()

    def test_non_apache_website_creation_remains_free(self):
        self.data['apacheBackend']=0
        self.assertIs(self.cloud.submitWebsiteCreation(),self.expected)
        self.acl.CheckForPremFeature.assert_not_called()
        self.services['Administrator'].return_value.save.assert_called_once_with()
        self.services['WebsiteManager'].return_value.submitWebsiteCreation.assert_called_once_with(7,self.data)

    def test_paid_apache_keeps_existing_account_and_website_delegation(self):
        self.acl.CheckForPremFeature.return_value=1
        self.assertIs(self.cloud.submitWebsiteCreation(),self.expected)
        self.services['Administrator'].return_value.save.assert_called_once_with()
        self.services['WebsiteManager'].return_value.submitWebsiteCreation.assert_called_once_with(7,self.data)


if __name__=='__main__':unittest.main()
