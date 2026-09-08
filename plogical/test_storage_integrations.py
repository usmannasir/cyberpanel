"""Storage policy integration checks with isolated model and command boundaries."""
import ast
import contextlib
import datetime
import io
import json
from pathlib import Path
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch


ROOT = Path(__file__).resolve().parents[1]


def method(path, class_name, name, namespace):
    tree = ast.parse((ROOT / path).read_text())
    owner = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == class_name)
    selected = next(node for node in owner.body if isinstance(node, ast.FunctionDef) and node.name == name)
    selected.decorator_list = []
    code = ast.fix_missing_locations(ast.Module(body=[selected], type_ignores=[]))
    exec(compile(code, str(ROOT / path), 'exec'), namespace)
    return namespace[name]


class ProjectPolicyIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.admin = NS(pk=1)
        self.package = NS(pk=3, admin=self.admin, enforceDiskLimits=1, diskSpace=10,
                          inodeLimit=20, save=Mock())
        self.site = NS(pk=4, domain='owned.test', package=self.package, save=Mock())
        self.package.websites_set = NS(all=Mock(return_value=[self.site]))
        self.project = NS(prepare_policy=Mock(return_value={'site_id': 4}), apply_policy=Mock())
        self.legacy = NS(limit=lambda value: value, prepare_package_quota=Mock(return_value={'legacy': 1}),
                         apply_quota_plan=Mock())
        self.process = NS(outputExecutioner=Mock(), popenExecutioner=Mock())
        self.acl = Mock()
        for name in ('currentContextPermission', 'checkOwnership', 'checkUserOwnerShip'):
            getattr(self.acl, name).return_value = 1
        self.acl.loadErrorJson.return_value = NS(content='{"saveStatus": 0}')
        self.namespace = {
            'json': json, 'HttpResponse': lambda text: NS(content=text),
            'ACLManager': self.acl, 'filesystemQuota': self.legacy, 'storageQuota': self.project,
            'Administrator': NS(objects=NS(get=Mock(return_value=self.admin))),
            'Package': NS(objects=NS(get=Mock(return_value=self.package))),
            'Websites': NS(objects=NS(get=Mock(return_value=self.site))),
            'ProcessUtilities': self.process,
            'virtualHostUtilities': NS(Server_root='/server', cyberPanel='/panel'),
            'shlex': __import__('shlex'),
        }
        self.package_data = {'packageName': 'owned', 'diskSpace': 50, 'bandwidth': 100,
                             'ftpAccounts': 1, 'dataBases': 1, 'emails': 1, 'allowedDomains': 1,
                             'enforceDiskLimits': 1, 'inodeLimit': 70}
        patches = [
            patch('plogical.storageQuota', self.project, create=True),
            patch.dict('sys.modules', {'plogical.processUtilities': NS(ProcessUtilities=self.process),
                                      'plogical.filesystemQuota': self.legacy,
                                      'plogical.storageQuota': self.project}),
            patch('plogical.filesystemQuota', self.legacy, create=True),
        ]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)

    def package_save(self):
        request = NS(session={'userID': 1}, body=json.dumps(self.package_data))
        manager = NS(request=request, checkAddonAccess=lambda: True)
        function = method('packages/packagesManager.py', 'PackagesManager', 'saveChanges', self.namespace)
        return json.loads(function(manager).content)

    def website_save(self):
        data = {'domain': 'owned.test', 'packForWeb': 'owned', 'email': 'owner@example.test',
                'phpVersion': 'PHP 8.3', 'admin': 'owner'}
        function = method('websiteFunctions/website.py', 'WebsiteManager', 'saveWebsiteChanges', self.namespace)
        return json.loads(function(NS(), 1, data).content)

    def test_package_project_preflight_failure_prevents_database_save(self):
        self.project.prepare_policy.side_effect = ValueError('project enrollment is pending')
        result = self.package_save()
        self.assertEqual(0, result['saveStatus'])
        self.assertIn('No package settings were changed', result['error_message'])
        self.package.save.assert_not_called()
        self.legacy.apply_quota_plan.assert_not_called()
        self.project.apply_policy.assert_not_called()

    def test_reassignment_prepares_explicit_prospective_policy_before_php(self):
        self.project.prepare_policy.side_effect = ValueError('project enrollment is pending')
        result = self.website_save()
        self.assertEqual(0, result['saveStatus'])
        self.site.save.assert_not_called()
        self.process.popenExecutioner.assert_not_called()

    def test_all_package_sites_are_prepared_before_any_settings_or_limits_change(self):
        second_site = NS(pk=5, domain='second.test', package=self.package)
        self.package.websites_set.all.return_value = [self.site, second_site]
        self.project.prepare_policy.side_effect = [{'site_id': 4}, ValueError('Second site is pending')]
        result = self.package_save()
        self.assertEqual(0, result['saveStatus'])
        self.package.save.assert_not_called()
        self.project.apply_policy.assert_not_called()
        self.legacy.apply_quota_plan.assert_not_called()

    def test_registered_disabled_policy_is_applied_after_save_without_clearing_legacy_quota(self):
        self.package_data['enforceDiskLimits'] = 0
        order = Mock()
        for child, name in ((self.project.prepare_policy, 'prepare'), (self.package.save, 'save'),
                            (self.project.apply_policy, 'apply')):
            order.attach_mock(child, name)
        result = self.package_save()
        self.assertEqual(1, result['saveStatus'])
        self.project.prepare_policy.assert_called_once_with(self.site, 50, 70, enforce=False)
        self.assertEqual(['prepare', 'save', 'apply'], [call[0] for call in order.mock_calls])
        self.legacy.apply_quota_plan.assert_not_called()

    def test_package_application_failure_reports_saved_state_and_failed_site(self):
        self.project.apply_policy.side_effect = ValueError('Readback failed')
        result = self.package_save()
        self.assertEqual(0, result['saveStatus'])
        self.assertIn('Package settings were saved', result['error_message'])
        self.assertIn('owned.test', result['error_message'])
        self.package.save.assert_called_once()

    def test_website_application_failure_keeps_saved_assignment_and_says_so(self):
        self.project.apply_policy.side_effect = ValueError('Readback failed')
        result = self.website_save()
        self.assertEqual(0, result['saveStatus'])
        self.assertIn('Website settings were saved', result['error_message'])
        self.site.save.assert_called_once()

    def test_no_enrollment_keeps_legacy_apply_behavior(self):
        self.project.prepare_policy.return_value = None
        self.assertEqual(1, self.package_save()['saveStatus'])
        self.legacy.apply_quota_plan.assert_called_once()
        self.project.apply_policy.assert_not_called()


class MailActivationIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.website = NS(pk=4, package=NS(emailAccounts=0))
        self.domain = NS(domain='owned.test')
        self.email = NS(save=Mock())
        self.users = Mock(return_value=self.email)
        self.users.objects.filter.return_value.exists.return_value = False
        self.domains = Mock()
        self.domains.objects.filter.return_value.exists.return_value = True
        self.domains.objects.get.return_value = self.domain
        self.ensure = Mock(side_effect=ValueError('storage enrollment failed'))
        self.project = NS(ensure_mail_domain=self.ensure)
        self.namespace = {
            'EUsers': self.users, 'Domains': self.domains,
            'Websites': NS(objects=NS(get=Mock(return_value=self.website))),
            'ChildDomains': NS(objects=NS(get=Mock())),
            'DomainLimits': Mock(), 'EmailLimits': Mock(),
            'os': NS(path=NS(exists=Mock(return_value=False))),
            'bcrypt': NS(hashpw=Mock(return_value=b'hash'), gensalt=Mock()),
            'ProcessUtilities': NS(executioner=Mock()),
            'logging': NS(CyberCPLogFileWriter=NS(writeToFile=Mock())),
        }
        for item in (patch('plogical.storageQuota', self.project, create=True),
                     patch.dict('sys.modules', {'plogical.storageQuota': self.project})):
            item.start()
            self.addCleanup(item.stop)

    def test_mail_domain_guard_runs_before_any_mailbox_activation(self):
        function = method('plogical/mailUtilities.py', 'mailUtilities', 'createEmailAccount', self.namespace)
        with contextlib.redirect_stdout(io.StringIO()):
            result = function('owned.test', 'hello', 'test-password')
        self.assertEqual(0, result[0])
        self.ensure.assert_called_once_with(self.domain, self.website)
        self.users.assert_not_called()
        self.email.save.assert_not_called()

    def test_child_mail_domain_uses_master_website_before_activation(self):
        self.namespace['Websites'].objects.get.side_effect = ValueError('Not a parent domain')
        self.namespace['ChildDomains'].objects.get.return_value = NS(master=self.website)
        function = method('plogical/mailUtilities.py', 'mailUtilities', 'createEmailAccount', self.namespace)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(0, function('owned.test', 'hello', 'test-password')[0])
        self.ensure.assert_called_once_with(self.domain, self.website)
        self.email.save.assert_not_called()

    def test_successful_guard_precedes_mailbox_save_for_new_mail(self):
        self.ensure.side_effect = None
        order = Mock()
        order.attach_mock(self.ensure, 'ensure')
        order.attach_mock(self.email.save, 'save')
        function = method('plogical/mailUtilities.py', 'mailUtilities', 'createEmailAccount', self.namespace)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(1, function('owned.test', 'hello', 'test-password')[0])
        self.assertEqual(['ensure', 'save'], [call[0] for call in order.mock_calls])
        self.assertEqual('maildir:/home/vmail/owned.test/hello/Maildir', self.email.mail)


class StorageCardContextTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse((ROOT / 'websiteFunctions/website.py').read_text())
        selected = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name == 'storage_card_context')
        namespace = {'json': json}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[selected], type_ignores=[])),
                     'websiteFunctions/website.py', 'exec'), namespace)
        self.context = namespace['storage_card_context']
        self.now = datetime.datetime(2026, 9, 9, 1, tzinfo=datetime.timezone.utc)
        self.package = NS(diskSpace=200, inodeLimit=400, enforceDiskLimits=1)
        self.cached = {'DiskUsage': 110, 'storageUsageStatus': 'available',
                       'storageUsageCheckedAt': self.now.isoformat(),
                       'storageQuotaStatus': {'state': 'active', 'enforced': True,
                                              'scope': 'website_and_owned_mail',
                                              'checked_at': self.now.isoformat(),
                                              'policy': {'disk_space': 200, 'inode_limit': 400, 'enforce': True}}}

    def card(self):
        return self.context(NS(config=json.dumps(self.cached), package=self.package), self.now)

    def test_recent_verified_total_and_policy_are_shown(self):
        card = self.card()
        self.assertTrue(card['storageUsageAvailable'])
        self.assertEqual(110, card['diskInMB'])
        self.assertEqual(55, card['diskUsage'])
        self.assertEqual('active', card['storageQuotaState'])

    def test_old_unmarked_or_failed_stats_are_unavailable_not_a_false_zero(self):
        for status in (None, 'unavailable'):
            with self.subTest(status=status):
                self.cached['storageUsageStatus'] = status
                card = self.card()
                self.assertFalse(card['storageUsageAvailable'])
                self.assertIsNone(card['diskInMB'])
                self.assertEqual(0, card['diskUsage'])

    def test_stale_future_and_missing_timestamp_cannot_claim_current_measurement_or_quota(self):
        for value in (None, 'invalid', '2026-09-09T01:00:00',
                      (self.now - datetime.timedelta(hours=37)).isoformat(),
                      (self.now + datetime.timedelta(hours=1)).isoformat()):
            with self.subTest(value=value):
                self.cached['storageUsageCheckedAt'] = value
                self.cached['storageQuotaStatus']['checked_at'] = value
                card = self.card()
                self.assertFalse(card['storageUsageAvailable'])
                self.assertEqual('unavailable', card['storageQuotaState'])

    def test_saved_package_change_invalidates_cached_active_quota(self):
        self.package.diskSpace = 250
        self.assertEqual('pending', self.card()['storageQuotaState'])
        self.assertEqual(44, self.card()['diskUsage'])

    def test_active_without_verified_policy_scope_or_enforcement_is_not_presented_as_configured(self):
        for field, value in (('enforced', False), ('policy', None), ('scope', 'website_only')):
            with self.subTest(field=field):
                previous = self.cached['storageQuotaStatus'][field]
                self.cached['storageQuotaStatus'][field] = value
                self.assertNotEqual('active', self.card()['storageQuotaState'])
                self.cached['storageQuotaStatus'][field] = previous

    def test_zero_allowance_remains_unlimited_with_zero_percentage(self):
        self.package.diskSpace = 0
        card = self.card()
        self.assertTrue(card['storageUsageAvailable'])
        self.assertEqual(110, card['diskInMB'])
        self.assertEqual(0, card['diskInMBTotal'])
        self.assertEqual(0, card['diskUsage'])

    def test_unconfigured_pending_and_unsupported_statuses_remain_distinct(self):
        for state in ('unconfigured', 'pending', 'unsupported'):
            self.cached['storageQuotaStatus'].update(state=state, reason='<private-path>')
            card = self.card()
            self.assertEqual(state, card['storageQuotaState'])
            self.assertNotIn('<private-path>', str(card))


if __name__ == '__main__':
    unittest.main()
