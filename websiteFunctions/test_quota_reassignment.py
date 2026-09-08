"""Reassignment checks preserve ACLs and precede PHP/model side effects."""
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from django.http import HttpResponse
from websiteFunctions import website as module
from plogical import filesystemQuota as quota


class WebsiteQuotaReassignmentTests(unittest.TestCase):
    def setUp(self):
        self.admin = NS(pk=1)
        self.site = NS(pk=1, domain='owned.test', externalApp='owned', save=Mock())
        self.package = NS(pk=3, diskSpace=50, inodeLimit=70, enforceDiskLimits=1)
        self.data = {'domain': 'owned.test', 'packForWeb': 'new', 'email': 'owner@example.test',
                     'phpVersion': 'PHP 8.3', 'admin': 'owner'}
        self.acl = Mock()
        for name in ('currentContextPermission', 'checkOwnership', 'checkUserOwnerShip'):
            getattr(self.acl, name).return_value = 1
        self.acl.loadErrorJson.return_value = HttpResponse('{"saveStatus":0}')
        self.prepare = Mock(return_value={'sites': ['owned']})
        self.apply = Mock(return_value={'ok': True})
        self.process = Mock()
        for item in (
                patch.object(module, 'ACLManager', self.acl),
                patch.object(module.Administrator.objects, 'get', return_value=self.admin),
                patch.object(module.Websites.objects, 'get', return_value=self.site),
                patch.object(module.Package.objects, 'get', return_value=self.package),
                patch.object(quota, 'prepare_package_quota', self.prepare),
                patch.object(quota, 'apply_quota_plan', self.apply),
                patch.object(module, 'ProcessUtilities', self.process)):
            item.start()
            self.addCleanup(item.stop)

    def save(self):
        return json.loads(module.WebsiteManager().saveWebsiteChanges(1, self.data).content)

    def test_reassignment_preflight_failure_precedes_php_and_model_changes(self):
        self.prepare.side_effect = quota.QuotaError('unsupported filesystem')
        response = self.save()
        self.assertEqual(0, response['saveStatus'])
        self.assertIn('No website settings were changed', response['error_message'])
        self.site.save.assert_not_called()
        self.assertEqual([], self.process.mock_calls)
        self.apply.assert_not_called()

    def test_success_preserves_order_and_uses_both_limit_helper(self):
        calls = Mock()
        for mock, name in ((self.prepare, 'prepare'), (self.process.popenExecutioner, 'php'),
                           (self.site.save, 'save'), (self.apply, 'apply')):
            calls.attach_mock(mock, name)
        self.assertEqual(1, self.save()['saveStatus'])
        self.assertEqual(['prepare', 'php', 'save', 'apply'], [c[0] for c in calls.mock_calls])
        self.prepare.assert_called_once_with(self.package, [self.site])
        self.process.executioner.assert_not_called()

    def test_application_failure_reports_saved_assignment(self):
        self.apply.side_effect = quota.QuotaError('owned.test: quota failed')
        response = self.save()
        self.assertEqual(0, response['saveStatus'])
        self.assertIn('Website settings were saved', response['error_message'])
        self.assertIn('owned.test', response['error_message'])
        self.site.save.assert_called_once()

    def test_disabled_package_does_not_clear_existing_quotas(self):
        self.package.enforceDiskLimits = 0
        self.assertEqual(1, self.save()['saveStatus'])
        self.prepare.assert_not_called()
        self.apply.assert_not_called()
        self.process.executioner.assert_not_called()

    def test_each_existing_authorization_denial_precedes_quota(self):
        for name in ('currentContextPermission', 'checkOwnership', 'checkUserOwnerShip'):
            with self.subTest(permission=name):
                getattr(self.acl, name).return_value = 0
                self.assertEqual(0, self.save()['saveStatus'])
                self.prepare.assert_not_called()
                self.site.save.assert_not_called()
                self.assertEqual([], self.process.mock_calls)
                getattr(self.acl, name).return_value = 1

