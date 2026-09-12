"""Exercise actual cloud methods, helper and router with inert service boundaries."""
import ast
import builtins
from functools import wraps
import json
import re
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
ACTIONS = (
    'DeployWordPress', 'FetchWordPressDetails', 'AutoLogin', 'UpdateWPSettings',
    'GetCurrentPlugins', 'UpdatePlugins', 'ChangeState', 'DeletePlugins',
    'GetCurrentThemes', 'UpdateThemes', 'ChangeStateThemes', 'DeleteThemes',
    'SaveAutoUpdateSettings', 'fetchWPSettings', 'updateWPCLI', 'saveWPSettings',
    'WPScan',
)


class Response:
    def __init__(self, content='', status=200):
        self.content = content.encode() if isinstance(content, str) else content
        self.status_code = status


def load_cloud():
    services = {name: mock.Mock(name=name) for name in (
        'ACLManager', 'ProcessUtilities', 'Websites', 'WPDeployments',
        'WebsiteManager', 'Administrator', 'logging', 'randomPassword',
    )}
    services['ACLManager'].CheckForPremFeature.return_value = 0
    services['ProcessUtilities'].outputExecutioner.return_value = '1'
    services['ProcessUtilities'].decideDistro.return_value = 'ubuntu'
    services['ProcessUtilities'].centos = 'centos'
    services['ProcessUtilities'].cent8 = 'cent8'
    services['Websites'].objects.get.return_value = SimpleNamespace(
        externalApp='ownedapp', domain='owned.example')
    services['WPDeployments'].objects.get.return_value = SimpleNamespace(
        config='{"path":""}', save=mock.Mock())
    services['randomPassword'].generate_pass.return_value = 'inert-password'
    admin = SimpleNamespace(pk=7, api=1, state='ACTIVE', token='inert-token')
    services['Administrator'].objects.get.return_value = admin
    output_file = mock.mock_open()
    safe_os = SimpleNamespace(path=SimpleNamespace(exists=mock.Mock(return_value=False)))
    allowed_imports = {
        'os': safe_os,
        'plogical.CyberCPLogFileWriter': SimpleNamespace(CyberCPLogFileWriter=services['logging']),
        'plogical.processUtilities': SimpleNamespace(ProcessUtilities=services['ProcessUtilities']),
        'cloudAPI.models': SimpleNamespace(WPDeployments=services['WPDeployments']),
        'plogical.randomPassword': services['randomPassword'],
    }
    def inert_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name not in allowed_imports:
            raise AssertionError('Unexpected import: ' + name)
        if name == 'plogical.randomPassword' and not fromlist:
            return SimpleNamespace(randomPassword=services['randomPassword'])
        return allowed_imports[name]
    namespace = {
        **services, '__builtins__': {**vars(builtins), '__import__': inert_import},
        'wraps': wraps, 'json': json, 're': re, 'HttpResponse': Response,
        'JsonResponse': lambda data: Response(json.dumps(data)),
        'redirect': mock.Mock(), 'open': output_file, 'randint': lambda a, b: a,
        'virtualHostUtilities': SimpleNamespace(cyberPanel='/inert/CyberCP'),
        'api_token_matches': mock.Mock(return_value=True),
        'api_two_factor_matches': mock.Mock(return_value=True),
        'csrf_exempt': lambda method: method,
    }
    for filename in ('plogical/premiumEntitlements.py', 'websiteFunctions/wordpressEntitlements.py',
                     'websiteFunctions/apacheEntitlements.py'):
        helper = ast.parse((ROOT / filename).read_text())
        helper.body = [node for node in helper.body if isinstance(node, ast.FunctionDef)]
        exec(compile(helper, filename, 'exec'), namespace)
    module = ast.parse((ROOT / 'cloudAPI/cloudManager.py').read_text())
    module.body = [node for node in module.body if isinstance(node, ast.ClassDef)
                   and node.name == 'CloudManager']
    exec(compile(module, 'cloudManager.py', 'exec'), namespace)
    views = ast.parse((ROOT / 'cloudAPI/views.py').read_text())
    views.body = [node for node in views.body if isinstance(node, ast.FunctionDef)
                  and node.name == 'router']
    exec(compile(views, 'cloudAPI/views.py', 'exec'), namespace)
    return namespace, services, admin, output_file


def data():
    return dict(domain='owned.example', domainName='owned.example', appsSet='none',
                email='owner@example.test', passwordByPass='inert', pluginUpdates='Disabled',
                themeUpdates='Disabled', title='Owned', updates='Disabled', userName='wpuser',
                version='7.0.2', createSite=0, setting='lscache', settingValue=False,
                plugin='one', plugins=['one'], wpCore='Disabled', themes='Disabled')


class CloudWordPressEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.ns, self.services, self.admin, self.output_file = load_cloud()
        self.acl = self.services['ACLManager']
        self.cloud = self.ns['CloudManager'](data(), self.admin)

    def assert_denied(self, response):
        result = json.loads(response.content)
        self.assertEqual(response.status_code, 200)
        for key in ('status', 'installStatus', 'createWebSiteStatus', 'fetchStatus'):
            self.assertEqual(result[key], 0)
        self.assertIn('entitlement', result['error_message'])
        self.assertNotIn('tempStatusPath', result)
        for name in ('ProcessUtilities', 'Websites', 'WPDeployments', 'randomPassword'):
            self.assertEqual(self.services[name].mock_calls, [], name)
        self.output_file.assert_not_called()

    def test_unpaid_all_direct_methods_stop_before_files_models_and_commands(self):
        for name in ACTIONS:
            with self.subTest(method=name):
                self.acl.reset_mock()
                self.assert_denied(getattr(self.cloud, name)())
                self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')

    def test_lookup_exception_denies_every_direct_method(self):
        self.acl.CheckForPremFeature.side_effect = TimeoutError('unavailable')
        for name in ACTIONS:
            with self.subTest(method=name):
                self.assert_denied(getattr(self.cloud, name)())

    def test_truthy_malformed_grants_cannot_launch_cloud_installer(self):
        for status in (True, '1', 1.0, None, [], 2):
            with self.subTest(status=status):
                self.acl.CheckForPremFeature.return_value = status
                self.assert_denied(self.cloud.DeployWordPress())

    def request(self, action, **overrides):
        payload = dict(data(), controller=action, serverUserName='admin')
        payload.update(overrides)
        return SimpleNamespace(body=json.dumps(payload).encode(), META={
            'HTTP_AUTHORIZATION': 'inert-token'}, session={})

    def test_authenticated_router_reaches_each_gate(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                self.acl.reset_mock()
                result = self.ns['router'](self.request(action))
                self.assert_denied(result)
                self.acl.CheckForPremFeature.assert_called_once_with('wp-manager')
                self.ns['api_token_matches'].assert_called_with('inert-token', 'inert-token')
                self.ns['api_two_factor_matches'].assert_called()

    def test_subscription_does_not_bypass_existing_cloud_authentication(self):
        self.acl.CheckForPremFeature.return_value = 1
        cases = ('non_admin', 'disabled_api', 'inactive', 'token', 'two_factor')
        for case in cases:
            with self.subTest(case=case):
                self.admin.api = 1
                self.admin.state = 'ACTIVE'
                self.ns['api_token_matches'].return_value = case != 'token'
                self.ns['api_two_factor_matches'].return_value = case != 'two_factor'
                if case == 'disabled_api': self.admin.api = 0
                if case == 'inactive': self.admin.state = 'SUSPENDED'
                request = self.request('DeployWordPress', serverUserName=(
                    'other' if case == 'non_admin' else 'admin'))
                result = json.loads(self.ns['router'](request).content)
                self.assertEqual(result['status'], 0)
                self.acl.CheckForPremFeature.assert_not_called()
                self.output_file.assert_not_called()
                self.services['ProcessUtilities'].popenExecutioner.assert_not_called()

    def test_paid_deployment_keeps_worker_and_status_response(self):
        self.acl.CheckForPremFeature.return_value = 1
        result = json.loads(self.ns['router'](self.request('DeployWordPress')).content)
        self.assertEqual(result['status'], 1)
        self.assertEqual(result['tempStatusPath'], '/home/cyberpanel/1000')
        self.output_file.assert_called_once_with(result['tempStatusPath'], 'w')
        command = self.services['ProcessUtilities'].popenExecutioner.call_args.args[0]
        self.assertIn('applicationInstaller.py DeployWordPress', command)
        self.assertIn("--domain 'owned.example'", command)

    def test_paid_details_and_settings_keep_original_cli_path(self):
        self.acl.CheckForPremFeature.return_value = 1
        result = json.loads(self.cloud.FetchWordPressDetails().content)
        self.assertEqual(result['status'], 1)
        self.assertEqual(result['version'], '1')
        self.services['ProcessUtilities'].outputExecutioner.assert_any_call(
            'wp core version --skip-plugins --skip-themes --path=/home/owned.example/public_html/ 2>/dev/null',
            'ownedapp', True)
        result = json.loads(self.cloud.UpdateWPSettings().content)
        self.assertEqual(result['status'], 1)
        self.services['ProcessUtilities'].executioner.assert_called_once_with(
            'wp plugin deactivate litespeed-cache --path=/home/owned.example/public_html/ --skip-plugins --skip-themes',
            'ownedapp')

    def test_paid_plugin_theme_and_admin_management_bodies_still_run(self):
        self.acl.CheckForPremFeature.return_value = 1
        for name in ACTIONS[4:] + ('AutoLogin',):
            with self.subTest(method=name):
                result = json.loads(getattr(self.cloud, name)().content)
                self.assertEqual(result['status'], 1, result)
        self.services['WPDeployments'].objects.get.return_value.save.assert_called_once_with()
        self.services['randomPassword'].generate_pass.assert_called_once_with(32)

    def test_free_website_inventory_does_not_require_wordpress(self):
        expected = Response('{"status":1,"data":[]}')
        self.services['WebsiteManager'].return_value.getFurtherAccounts.return_value = expected
        self.assertIs(self.ns['router'](self.request('fetchWebsites')), expected)
        self.acl.CheckForPremFeature.assert_not_called()
        self.services['WebsiteManager'].return_value.getFurtherAccounts.assert_called_once()


if __name__ == '__main__':
    unittest.main()
