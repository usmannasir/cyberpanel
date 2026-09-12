"""Execute actual manager bodies with inert services, without panel bootstrap."""
import ast
from functools import wraps
import json
from pathlib import Path
import re
import shlex
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
PAGES = (
    'WPCreate', 'ListWPSites', 'WPHome', 'RestoreHome', 'RemoteBackupConfig',
    'BackupfileConfig', 'AddRemoteBackupsite', 'RestoreBackups', 'AutoLogin',
    'ConfigurePlugins', 'Addnewplugin', 'EidtPlugin', 'wordpressInstall',
)
ACTIONS = (
    'SearchOnkeyupPlugin', 'AddNewpluginAjax', 'deletesPlgin', 'Addplugineidt',
    'FetchWPdata', 'GetCurrentPlugins', 'GetCurrentThemes', 'fetchstaging',
    'fetchDatabase', 'SaveUpdateConfig', 'DeploytoProduction', 'WPCreateBackup',
    'RestoreWPbackupNow', 'SaveBackupConfig', 'SaveBackupSchedule',
    'AddWPsiteforRemoteBackup', 'UpdateRemoteschedules', 'ScanWordpressSite',
    'installwpcore', 'dataintegrity', 'UpdatePlugins', 'UpdateThemes',
    'DeletePlugins', 'DeleteThemes', 'ChangeStatus', 'ChangeStatusThemes',
    'CreateStagingNow', 'UpdateWPSettings', 'submitWorpressCreation',
    'installWordpress', 'fetchWPSitesForDomain', 'fetchWPBackups',
)


class Response:
    """Inert HTTP boundary; content and redirect target remain observable."""
    def __init__(self, content='', status=200, location=None):
        self.content = content.encode() if isinstance(content, str) else content
        self.status_code = status
        self.url = location


def load_wordpress_manager():
    # Whole original function/class ASTs run unchanged. Only module imports and
    # global Django/database bootstrap are excluded from this inert test loader.
    services = {name: mock.Mock(name=name) for name in (
        'ACLManager', 'Administrator', 'WPSites', 'WPStaging', 'WPSitesBackup',
        'RemoteBackupConfig', 'RemoteBackupSchedule', 'RemoteBackupsites',
        'wpplugins', 'Websites', 'ApplicationInstaller', 'mailUtilities',
        'ProcessUtilities', 'subprocess', 'os', 'time', 'requests', 'httpProc',
        'PHPManager', 'randomPassword', 'virtualHostUtilities', 'logging',
        'ApacheVhost', 'validators', 'open',
    )}
    namespace = {
        **services, 'wraps': wraps, 'json': json, 'HttpResponse': Response,
        'JsonResponse': lambda data: Response(json.dumps(data)),
        'redirect': lambda target: Response(status=302, location=target),
        'randint': lambda lower, upper: lower, 're': re, 'shlex': shlex,
    }
    premium = ast.parse((ROOT / 'plogical/premiumEntitlements.py').read_text())
    premium.body = [node for node in premium.body if isinstance(node, ast.FunctionDef)]
    exec(compile(premium, 'premiumEntitlements.py', 'exec'), namespace)
    helper = ast.parse((ROOT / 'websiteFunctions/wordpressEntitlements.py').read_text())
    helper.body = [node for node in helper.body if isinstance(node, ast.FunctionDef)]
    exec(compile(helper, 'wordpressEntitlements.py', 'exec'), namespace)
    apache = ast.parse((ROOT / 'websiteFunctions/apacheEntitlements.py').read_text())
    apache.body = [node for node in apache.body if isinstance(node, ast.FunctionDef)]
    exec(compile(apache, 'apacheEntitlements.py', 'exec'), namespace)
    version = ast.parse((ROOT / 'plogical/wordpressInstallerUtilities.py').read_text())
    version.body = [node for node in version.body
                    if isinstance(node, (ast.FunctionDef, ast.Assign))]
    exec(compile(version, 'wordpressInstallerUtilities.py', 'exec'), namespace)
    module = ast.parse((ROOT / 'websiteFunctions/website.py').read_text())
    module.body = [node for node in module.body if isinstance(node, ast.ClassDef)
                   and node.name == 'WebsiteManager']
    exec(compile(module, 'website.py', 'exec'), namespace)
    return namespace['WebsiteManager'], namespace, services


def install_data():
    return {
        'domain': 'owned.example', 'home': '1', 'blogTitle': 'Owned site',
        'adminUser': 'wpadmin', 'passwordByPass': 'inert-password',
        'adminEmail': 'admin@example.test',
    }


class WordPressEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.ns, self.services = load_wordpress_manager()
        self.acl = self.services['ACLManager']
        self.acl.CheckForPremFeature.return_value = 0

    def assert_denied_without_effects(self, name, page, **kwargs):
        for service in self.services.values():
            service.reset_mock()
        result = getattr(self.manager(), name)(userID=7, **kwargs)
        self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')
        self.assertEqual(self.acl.mock_calls, [mock.call.CheckForPremFeature('wp-manager')])
        for service_name, service in self.services.items():
            if service_name != 'ACLManager':
                self.assertEqual(service.mock_calls, [], service_name)
        if page:
            self.assertEqual((result.status_code, result.url), (302, 'pricing'))
        else:
            payload = json.loads(result.content)
            for key in ('status', 'installStatus', 'createWebSiteStatus', 'fetchStatus'):
                self.assertEqual(payload[key], 0)
            self.assertIn('entitlement', payload['error_message'])
            self.assertNotIn('tempStatusPath', payload)

    def test_unpaid_manager_routes_stop_before_models_workers_or_commands(self):
        for name in PAGES + ACTIONS:
            with self.subTest(method=name):
                self.assert_denied_without_effects(name, name in PAGES)

    def test_lookup_failure_denies_every_entry_without_effects(self):
        self.acl.CheckForPremFeature.side_effect = RuntimeError('lookup unavailable')
        for name in PAGES + ACTIONS:
            with self.subTest(method=name):
                self.assert_denied_without_effects(name, name in PAGES)

    def test_malformed_grants_do_not_start_installation(self):
        for value in (True, '1', 1.0, None, {}, -1):
            with self.subTest(value=value):
                self.acl.CheckForPremFeature.return_value = value
                self.assert_denied_without_effects('installWordpress', False)

    def test_unpaid_page_deletion_arguments_do_not_remove_records_or_start_cleanup(self):
        cases = {
            'RemoteBackupConfig': {'DeleteID': 9},
            'BackupfileConfig': {'RemoteConfigID': 9, 'DeleteID': 9},
            'AddRemoteBackupsite': {'RemoteScheduleID': 9, 'DeleteSiteID': 9},
            'ListWPSites': {'DeleteID': 9},
            'RestoreBackups': {'DeleteID': 9},
            'WPHome': {'WPid': 9, 'request': SimpleNamespace(GET={'DeleteID': '9'})},
        }
        for name, kwargs in cases.items():
            with self.subTest(page=name):
                self.assert_denied_without_effects(name, True, **kwargs)

    def prepare_paid(self, ownership=1):
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.loadedACL.return_value = {'admin': 1}
        self.acl.checkOwnership.return_value = ownership
        self.services['Administrator'].objects.get.return_value = SimpleNamespace(pk=7)
        self.services['requests'].RequestException = RuntimeError
        version = mock.Mock()
        version.json.return_value = {'offers': [{'current': '7.0.2'}]}
        self.services['requests'].get.return_value = version

    def test_paid_existing_site_install_reaches_original_worker_and_owner_check(self):
        self.prepare_paid()
        result = self.manager().installWordpress(7, install_data())
        self.assertEqual(json.loads(result.content)['installStatus'], 1)
        self.acl.checkOwnership.assert_called_once()
        installer = self.services['ApplicationInstaller']
        self.assertEqual(installer.call_args.args[0], 'wordpress')
        self.assertEqual(installer.call_args.args[1]['WPVersion'], '7.0.2')
        installer.return_value.start.assert_called_once_with()
        self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')

    def test_paid_does_not_bypass_existing_site_ownership(self):
        self.prepare_paid(ownership=0)
        denied = Response(json.dumps({'installStatus': 0, 'error_message': 'Not owned'}))
        self.acl.loadErrorJson.return_value = denied
        self.assertIs(self.manager().installWordpress(7, install_data()), denied)
        self.services['ApplicationInstaller'].assert_not_called()
        self.services['mailUtilities'].checkHome.assert_not_called()

    def test_paid_plugin_bucket_creation_still_saves_requested_owner_data(self):
        self.prepare_paid()
        result = self.manager().AddNewpluginAjax(7, {'Name': 'Owned', 'config': ['one']})
        self.assertEqual(json.loads(result.content)['status'], 1)
        self.services['wpplugins'].return_value.save.assert_called_once_with()
        self.assertEqual(self.services['wpplugins'].call_args.kwargs['Name'], 'Owned')

    def test_paid_wp_home_preserves_owner_check_and_renders_after_one_lookup(self):
        self.prepare_paid()
        site = SimpleNamespace(owner=SimpleNamespace(domain='owned.example'))
        self.services['WPSites'].objects.get.return_value = site
        self.services['randomPassword'].generate_pass.return_value = 'inert'
        expected = Response('wp-home')
        self.services['httpProc'].return_value.render.return_value = expected
        result = self.manager().WPHome(SimpleNamespace(GET={}), 7, WPid=9)
        self.assertIs(result, expected)
        self.acl.checkOwnership.assert_called_once()
        self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')
        self.services['requests'].post.assert_not_called()
        self.assertEqual(self.services['httpProc'].call_args.args[1], 'websiteFunctions/WPsiteHome.html')

    def test_cloud_api_installer_uses_manager_denial(self):
        source = ast.parse((ROOT / 'cloudAPI/cloudManager.py').read_text())
        method = next(node for node in ast.walk(source) if isinstance(node, ast.FunctionDef)
                      and node.name == 'submitApplicationInstall')
        exec(compile(ast.Module(body=[method], type_ignores=[]), 'cloudManager.py', 'exec'), self.ns)
        cloud = SimpleNamespace(admin=SimpleNamespace(pk=7), data={
            **install_data(), 'selectedApplication': 'WordPress with LSCache'})
        result = self.ns['submitApplicationInstall'](cloud, SimpleNamespace(session={}))
        self.assertEqual(json.loads(result.content)['installStatus'], 0)
        self.services['ApplicationInstaller'].assert_not_called()
        self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')

    def test_pricing_page_does_not_require_paid_access(self):
        expected = Response('pricing')
        self.services['httpProc'].return_value.render.return_value = expected
        self.assertIs(self.manager().WordpressPricing(userID=7), expected)
        self.acl.CheckForPremFeature.assert_not_called()

    def test_shared_polling_does_not_require_wordpress_entitlement(self):
        self.acl.CheckStatusFilleLoc.return_value = False
        result = self.manager().installWordpressStatus(7, {'statusFile': '/invalid'})
        self.assertEqual(json.loads(result.content)['currentStatus'], 'Invalid status file.')
        self.acl.CheckForPremFeature.assert_not_called()

    def test_free_joomla_installer_still_starts_original_worker(self):
        self.prepare_paid()
        self.acl.CheckForPremFeature.return_value = 0
        result = self.manager().installJoomla(7, {
            'domain': 'owned.example', 'home': '1', 'siteName': 'Owned',
            'passwordByPass': 'inert', 'prefix': 'x_',
        })
        self.assertEqual(json.loads(result.content)['installStatus'], 1)
        self.services['ApplicationInstaller'].return_value.start.assert_called_once_with()
        self.assertEqual(self.services['ApplicationInstaller'].call_args.args[0], 'joomla')
        self.acl.CheckForPremFeature.assert_not_called()


if __name__ == '__main__':
    unittest.main()
