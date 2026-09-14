"""Exercise actual Apache manager/create bodies with inert process and DB services."""
import json
from types import SimpleNamespace
import unittest
from unittest import mock

from websiteFunctions.test_wordpress_entitlements import load_wordpress_manager, Response


TOOLS = ('ApacheManager', 'getSwitchStatus', 'switchServer', 'tuneSettings',
         'saveApacheConfigsToFile')


def website_data(**extra):
    return dict(domainName='owned.example', adminEmail='admin@example.test',
                phpSelection='PHP 8.3', package='Default', websiteOwner='admin',
                openBasedir=1, **extra)


def child_data(**extra):
    return dict(masterDomain='owned.example', domainName='child.owned.example',
                phpSelection='PHP 8.3', path='child', openBasedir=1, **extra)


class ApacheEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        self.acl = self.services['ACLManager']
        self.acl.CheckForPremFeature.return_value = 0

    def no_effects(self):
        for name, service in self.services.items():
            if name != 'ACLManager':
                self.assertEqual(service.mock_calls, [], name)

    def prepare_body(self, grant=1, ownership=1):
        self.acl.CheckForPremFeature.return_value = grant
        self.acl.loadedACL.return_value = {'admin': 1}
        self.acl.checkOwnership.return_value = ownership
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnerProtection.return_value = 1
        self.acl.loadErrorJson.return_value = Response(json.dumps({'status': 0, 'error_message': 'ACL denied'}))
        self.services['Administrator'].objects.get.return_value = SimpleNamespace(pk=7, userName='admin', defaultSite=1)
        self.services['Websites'].objects.get.side_effect = LookupError('No username collision')
        self.services['validators'].domain.return_value = True
        self.services['validators'].email.return_value = True
        self.services['virtualHostUtilities'].cyberPanel = '/usr/local/CyberCP'
        self.services['ApacheVhost'].configBasePath = '/etc/apache2/sites-enabled/'

    def test_unpaid_and_lookup_error_tools_stop_before_io(self):
        for failure in (False, True):
            for name in TOOLS:
                with self.subTest(failure=failure, method=name):
                    for service in self.services.values():
                        service.reset_mock()
                    self.acl.CheckForPremFeature.side_effect = RuntimeError('unavailable') if failure else None
                    response = getattr(self.manager('owned.example'), name)(userID=7, data={})
                    self.acl.CheckForPremFeature.assert_called_once_with('all')
                    self.assertEqual(self.acl.mock_calls, [mock.call.CheckForPremFeature('all')])
                    self.no_effects()
                    if name == 'ApacheManager':
                        self.assertEqual((response.status_code, response.url), (302, 'pricing'))
                    else:
                        payload = json.loads(response.content)
                        for key in ('status', 'saveStatus', 'configstatus', 'createWebSiteStatus', 'installStatus'):
                            self.assertEqual(payload[key], 0)

    def test_selected_backend_denies_before_website_or_child_work(self):
        for name in ('submitWebsiteCreation', 'submitDomainCreation'):
            for value in (1, '1', True, -1, '  +2 ', '01'):
                with self.subTest(method=name, value=value):
                    for service in self.services.values():
                        service.reset_mock()
                    response = getattr(self.manager(), name)(7, {'apacheBackend': value})
                    self.assertEqual(json.loads(response.content)['createWebSiteStatus'], 0)
                    self.acl.CheckForPremFeature.assert_called_once_with('all')
                    self.no_effects()

    def test_malformed_flags_fail_before_lookup_or_work(self):
        for value in ('false', '1 --mailDomain 0', 1.0, [], {}):
            for name in ('submitWebsiteCreation', 'submitDomainCreation'):
                with self.subTest(value=value, method=name):
                    response = getattr(self.manager(), name)(7, {'apacheBackend': value})
                    self.assertIn('Invalid Apache', json.loads(response.content)['error_message'])
                    self.acl.CheckForPremFeature.assert_not_called()
                    self.no_effects()

    def test_selected_backend_fails_closed_for_lookup_error_or_malformed_grant(self):
        for value in (True, '1', 1.0, None, {}, -1, RuntimeError('lookup failed')):
            with self.subTest(value=value):
                self.acl.CheckForPremFeature.side_effect = value if isinstance(value, Exception) else None
                self.acl.CheckForPremFeature.return_value = value
                response = self.manager().submitWebsiteCreation(7, {'apacheBackend': 1})
                self.assertEqual(json.loads(response.content)['createWebSiteStatus'], 0)
                self.no_effects()

    def test_no_backend_does_not_require_paid_entitlement_and_starts_original_create(self):
        self.prepare_body(grant=0)
        for value in (None, 0, '0', False, ''):
            for name, data in (('submitWebsiteCreation', website_data()), ('submitDomainCreation', child_data())):
                with self.subTest(value=value, method=name):
                    self.services['ProcessUtilities'].reset_mock()
                    result = getattr(self.manager(), name)(7, dict(data, apacheBackend=value))
                    self.assertEqual(json.loads(result.content)['createWebSiteStatus'], 1, result.content)
                    self.assertIn(' --apache 0', self.services['ProcessUtilities'].popenExecutioner.call_args.args[0])
                    self.services['ProcessUtilities'].popenExecutioner.assert_called_once()
        self.acl.CheckForPremFeature.assert_not_called()

    def test_paid_backend_creation_retains_real_command_and_acl(self):
        self.prepare_body()
        response = self.manager().submitWebsiteCreation(7, website_data(apacheBackend='  +1 '))
        self.assertEqual(json.loads(response.content)['createWebSiteStatus'], 1, response.content)
        self.assertIn(' --apache 1', self.services['ProcessUtilities'].popenExecutioner.call_args.args[0])
        self.acl.currentContextPermission.assert_called_once()
        self.acl.checkOwnerProtection.assert_called_once()
        self.acl.CheckForPremFeature.assert_called_once_with('all')

    def test_paid_child_backend_preserves_ownership_denial(self):
        self.prepare_body(ownership=0)
        result = self.manager().submitDomainCreation(7, child_data(apacheBackend=1))
        self.assertIs(result, self.acl.loadErrorJson.return_value)
        self.acl.checkOwnership.assert_called_once()
        self.services['ProcessUtilities'].popenExecutioner.assert_not_called()

    def test_alias_inherited_backend_is_checked_before_flag_or_worker_mutation(self):
        self.prepare_body(grant=0)
        self.services['os'].path.exists.return_value = True
        data = child_data(alias=1)
        result = self.manager().submitDomainCreation(7, data)
        self.assertEqual(json.loads(result.content)['createWebSiteStatus'], 0)
        self.assertNotIn('apacheBackend', data)
        self.acl.CheckForPremFeature.assert_called_once_with('all')
        self.services['ProcessUtilities'].popenExecutioner.assert_not_called()
        self.services['Websites'].objects.get.assert_not_called()

    def test_paid_alias_inherits_backend_and_ordinary_alias_stays_free(self):
        self.prepare_body()
        self.services['Websites'].objects.get.side_effect = None
        self.services['Websites'].objects.get.return_value = SimpleNamespace(phpSelection='PHP 8.3')
        for apache in (True, False):
            self.services['ProcessUtilities'].reset_mock()
            self.acl.CheckForPremFeature.reset_mock()
            self.acl.CheckForPremFeature.return_value = int(apache)
            self.services['os'].path.exists.return_value = apache
            data = child_data(alias=1)
            response = self.manager().submitDomainCreation(7, data)
            self.assertEqual(json.loads(response.content)['createWebSiteStatus'], 1, response.content)
            self.assertIn(' --apache %s' % int(apache), self.services['ProcessUtilities'].popenExecutioner.call_args.args[0])
            if apache:
                self.acl.CheckForPremFeature.assert_called_once_with('all')
            else:
                self.acl.CheckForPremFeature.assert_not_called()

    def test_paid_wordpress_without_apache_grant_cannot_start_apache_install(self):
        self.acl.CheckForPremFeature.side_effect = lambda feature: int(feature == 'wp-manager')
        result = self.manager().submitWorpressCreation(7, {'apacheBackend': 1})
        self.assertEqual(json.loads(result.content)['installStatus'], 0)
        self.assertEqual(self.acl.mock_calls, [mock.call.CheckForPremFeature('wp-manager'), mock.call.CheckForPremFeature('all')])
        self.no_effects()

    def test_paid_wordpress_without_apache_selection_starts_without_all_lookup(self):
        self.prepare_body()
        self.acl.CheckForPremFeature.side_effect = lambda feature: int(feature == 'wp-manager')
        response = self.manager().submitWorpressCreation(7, {
            'domain': 'owned.example', 'WPVersion': '7.0.2', 'title': 'Owned',
            'adminUser': 'admin', 'PasswordByPass': 'inert', 'Email': 'admin@example.test',
            'AutomaticUpdates': 0, 'Plugins': [], 'Themes': [], 'websiteOwner': 'admin',
            'package': 'Default', 'home': '1',
        })
        self.assertEqual(json.loads(response.content)['installStatus'], 1, response.content)
        self.services['ApplicationInstaller'].return_value.start.assert_called_once()
        self.assertEqual(self.services['ApplicationInstaller'].call_args.args[1]['apacheBackend'], 0)
        self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')

    def test_paid_apache_switch_retains_worker_and_ownership_gate(self):
        self.prepare_body()
        response = self.manager().switchServer(7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': 1})
        self.assertEqual(json.loads(response.content)['status'], 1)
        self.assertIn(' switchServer ', self.services['ProcessUtilities'].popenExecutioner.call_args.args[0])
        self.acl.checkOwnership.assert_called_once()
        self.services['ProcessUtilities'].reset_mock()
        self.acl.checkOwnership.return_value = 0
        self.manager().switchServer(7, {'domainName': 'owned.example', 'phpSelection': 'PHP 8.3', 'server': 1})
        self.services['ProcessUtilities'].popenExecutioner.assert_not_called()

    def test_paid_config_saving_keeps_admin_gate_and_success_output(self):
        self.prepare_body()
        self.services['ProcessUtilities'].outputExecutioner.return_value = '1,None'
        response = self.manager().saveApacheConfigsToFile(7, {'domainName': 'owned.example', 'configData': 'owned-config'})
        self.assertEqual(json.loads(response.content)['status'], 1)
        self.services['open'].return_value.write.assert_called_once_with('owned-config')
        self.services['open'].reset_mock()
        self.services['ProcessUtilities'].reset_mock()
        self.acl.loadedACL.return_value = {'admin': 0}
        self.manager().saveApacheConfigsToFile(7, {})
        self.services['open'].assert_not_called()
        self.services['ProcessUtilities'].outputExecutioner.assert_not_called()

    def test_generic_create_pages_remain_renderable_when_lookup_fails(self):
        self.prepare_body()
        self.acl.CheckForPremFeature.side_effect = RuntimeError('unavailable')
        self.services['Websites'].objects.get.side_effect = None
        self.services['Websites'].objects.get.return_value = SimpleNamespace(domain='owned.example')
        for name in ('createWebsite', 'CreateNewDomain'):
            with self.subTest(page=name):
                result = getattr(self.manager(), name)(userID=7)
                self.assertIs(result, self.services['httpProc'].return_value.render.return_value)
                self.assertEqual(self.services['httpProc'].call_args.args[2]['test_domain_data'], 0)


if __name__ == '__main__':
    unittest.main()
