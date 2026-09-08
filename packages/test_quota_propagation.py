"""Package save regressions; ORM, entitlement and command boundaries are mocked."""
import json
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

from django.http import HttpResponse
from packages import packagesManager as module
from plogical import filesystemQuota as quota


class PackageQuotaPropagationTests(unittest.TestCase):
    def setUp(self):
        self.admin = NS(pk=1)
        self.package = NS(pk=3, admin=self.admin, enforceDiskLimits=1,
                          diskSpace=10, inodeLimit=20, save=Mock())
        self.data = {'packageName': 'owned', 'diskSpace': 50, 'bandwidth': 100,
                     'ftpAccounts': 1, 'dataBases': 1, 'emails': 1,
                     'allowedDomains': 1, 'enforceDiskLimits': 1, 'inodeLimit': 70}
        self.acl = Mock()
        self.acl.currentContextPermission.return_value = 1
        self.acl.loadErrorJson.return_value = HttpResponse('{"saveStatus":0}')
        self.preflight = Mock(return_value={'sites': ['owned']})
        self.apply = Mock(return_value={'ok': True})
        self.process = Mock(return_value='')
        for item in (
                patch.object(module, 'ACLManager', self.acl),
                patch.object(module.Administrator.objects, 'get', return_value=self.admin),
                patch.object(module.Package.objects, 'get', return_value=self.package),
                patch.object(module.PackagesManager, 'checkAddonAccess', return_value=True),
                patch.object(quota, 'prepare_package_quota', self.preflight),
                patch.object(quota, 'apply_quota_plan', self.apply),
                patch('plogical.processUtilities.ProcessUtilities.outputExecutioner', self.process)):
            item.start()
            self.addCleanup(item.stop)

    def save(self):
        request = NS(session={'userID': 1}, body=json.dumps(self.data).encode())
        return json.loads(module.PackagesManager(request).saveChanges().content)

    def test_enabled_save_prepares_saves_and_applies(self):
        calls = Mock()
        calls.attach_mock(self.preflight, 'prepare')
        calls.attach_mock(self.package.save, 'save')
        calls.attach_mock(self.apply, 'apply')
        response = self.save()
        self.assertEqual(1, response['saveStatus'])
        self.assertEqual(['prepare', 'save', 'apply'], [call[0] for call in calls.mock_calls])
        self.preflight.assert_called_once_with(self.package)
        self.apply.assert_called_once_with(self.preflight.return_value)

    def test_preflight_failure_does_not_save_or_run_scheduler(self):
        self.preflight.side_effect = quota.QuotaError('user quotas are off')
        response = self.save()
        self.assertEqual(0, response['saveStatus'])
        self.assertIn('No package settings were changed', response['error_message'])
        self.package.save.assert_not_called()
        self.apply.assert_not_called()
        self.process.assert_not_called()

    def test_saved_but_failed_application_is_truthful_and_retryable(self):
        self.apply.side_effect = [quota.QuotaError('one.test: failed'), {'ok': True}]
        first = self.save()
        self.assertEqual(0, first['saveStatus'])
        self.assertIn('settings were saved', first['error_message'])
        self.assertIn('one.test', first['error_message'])
        self.assertEqual(50, self.package.diskSpace)
        self.assertEqual(1, self.save()['saveStatus'])
        self.assertEqual(2, self.preflight.call_count)
        self.assertEqual(2, self.apply.call_count)

    def test_disabled_package_preserves_existing_no_quota_behavior(self):
        self.data['enforceDiskLimits'] = 0
        self.assertEqual(1, self.save()['saveStatus'])
        self.preflight.assert_not_called()
        self.apply.assert_not_called()

    def test_acl_and_ownership_denial_never_reach_quota(self):
        self.acl.currentContextPermission.return_value = 0
        self.assertEqual(0, self.save()['saveStatus'])
        self.acl.currentContextPermission.return_value = 1
        self.package.admin = NS(pk=2)
        self.assertEqual(0, self.save()['saveStatus'])
        self.package.save.assert_not_called()
        self.preflight.assert_not_called()
        self.apply.assert_not_called()

    def test_entitlement_denial_never_reaches_quota(self):
        with patch.object(module.PackagesManager, 'checkAddonAccess', return_value=False):
            self.assertEqual(0, self.save()['saveStatus'])
        self.package.save.assert_not_called()
        self.preflight.assert_not_called()

    def test_invalid_raw_limits_do_not_get_truncated_or_saved(self):
        for field, value in (('inodeLimit', -1), ('inodeLimit', 1.5),
                             ('inodeLimit', 'bad'), ('diskSpace', 1.5)):
            with self.subTest(field=field, value=value):
                self.data.update(diskSpace=50, inodeLimit=70)
                self.data[field] = value
                self.assertEqual(0, self.save()['saveStatus'])
                self.package.save.assert_not_called()
                self.preflight.assert_not_called()

