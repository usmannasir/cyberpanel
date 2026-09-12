"""Actual mail views/cloud methods with inert models, files, workers and commands."""
import ast
import json
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from cloudAPI.test_wordpress_cloud_entitlements import load_cloud, Response

CONFIGS = ('saveRspamdConfigurations', 'savepostfixConfigurations',
           'saveRedisConfigurations', 'saveclamavConfigurations')
INTERACTIVE = ('installRspamd', 'fetchRspamdSettings', *CONFIGS,
               'FetchRspamdLog', 'RestartRspamd')
DEBUGGER = ('RunServerLevelEmailChecks', 'ResetEmailConfigurations',
            'ReadReport', 'debugEmailForSite', 'fixMailSSL')


class InertThread:
    def __init__(self):
        pass
    def start(self):
        raise AssertionError('No actual worker may start')


def load_email():
    ns, services, admin, output_file = load_cloud()
    for name in ('mailUtilities', 'EUsers', 'MailServerManager', 'httpProc',
                 'remove_stale_private_token_files', 'create_private_token_file',
                 'read_private_token_file'):
        services[name] = mock.Mock(name=name)
    ns.update(services)
    ns.update(multi=SimpleNamespace(Thread=InertThread),
              EMAIL_REPORT_DIRECTORY='/inert/reports', loadLoginPage='login',
              os=SimpleNamespace(path=SimpleNamespace(exists=mock.Mock(return_value=False))))
    ns['redirect'] = lambda url: SimpleNamespace(status_code=302, url=url)
    # The decorator's globals are the same inert namespace.
    services['ACLManager'].loadedACL.return_value = {'admin': 1}
    services['ACLManager'].currentContextPermission.return_value = 1
    services['ACLManager'].checkOwnership.return_value = 1
    services['ACLManager'].findAllSites.return_value = ['owned.example']
    services['ACLManager'].findChildDomains.return_value = []
    denied = Response('{"status":0,"saveStatus":0,"createStatus":0,"error_message":"ACL denied"}')
    services['ACLManager'].loadErrorJson.return_value = denied
    services['mailUtilities'].checkIfRspamdInstalled.return_value = 0
    services['mailUtilities'].RspamdInstallLogPath = '/inert/rspamd-install-log'
    services['EUsers'].objects.get.return_value = SimpleNamespace(
        emailOwner=SimpleNamespace(domainOwner=SimpleNamespace(domain='owned.example')))
    services['create_private_token_file'].return_value = ('inert-report-token', '/inert/report')
    services['read_private_token_file'].return_value = '{"MailSSL":1}'
    services['MailServerManager'].return_value.debugEmailForSite.return_value = (1, 'OK')
    services['MailServerManager'].return_value.fixMailSSL.return_value = Response('{"status":1}')
    services['httpProc'].return_value.render.return_value = Response('rendered')
    module = ast.parse((ROOT / 'emailPremium/views.py').read_text())
    module.body = [n for n in module.body if isinstance(n, ast.FunctionDef)]
    exec(compile(module, 'emailPremium/views.py', 'exec'), ns)
    module = ast.parse((ROOT / 'mailServer/mailserverManager.py').read_text())
    module.body = [n for n in module.body if isinstance(n, ast.ClassDef) and n.name == 'MailServerManager']
    native_ns = dict(ns)
    exec(compile(module, 'mailServer/mailserverManager.py', 'exec'), native_ns)
    return ns, native_ns['MailServerManager'], services, output_file


class PremiumEmailTests(unittest.TestCase):
    def setUp(self):
        self.ns, self.mail_class, self.services, self.output_file = load_email()
        self.acl = self.services['ACLManager']
        self.req = SimpleNamespace(session={'userID': 7}, method='POST', body=json.dumps({
            'source':'owned@owned.example','numberofEmails':50,'duration':'1h',
            'websiteName':'owned.example','reportFile':'inert-token'}).encode())

    def assert_no_work(self):
        self.output_file.assert_not_called()
        for name in ('ProcessUtilities', 'mailUtilities', 'EUsers', 'MailServerManager',
                     'remove_stale_private_token_files', 'create_private_token_file',
                     'read_private_token_file', 'httpProc'):
            self.assertEqual(self.services[name].mock_calls, [], name)

    def assert_denied(self, response, flags=()):
        self.assertEqual(response.status_code, 200)
        body = json.loads(response.content)
        self.assertEqual(body['status'], 0)
        self.assertIn('entitlement', body['error_message'])
        for flag in flags: self.assertEqual(body[flag], 0)
        self.assertNotIn('tempStatusPath', body)
        self.assert_no_work()

    def test_unpaid_interactive_mail_handlers_have_compatible_denials(self):
        for name in INTERACTIVE:
            with self.subTest(name=name):
                self.acl.reset_mock()
                flags = ('saveStatus',) if name in CONFIGS else (
                    ('fetchStatus',) if name == 'fetchRspamdSettings' else (
                        ('logstatus',) if name == 'FetchRspamdLog' else ()))
                self.assert_denied(self.ns[name](self.req), flags)
                self.acl.CheckForPremFeature.assert_called_once_with('email-debugger')

    def test_unpaid_email_limits_stop_before_mailbox_read_or_install(self):
        self.assert_denied(self.mail_class(self.req).SaveEmailLimitsNew(), ('createStatus',))
        self.acl.CheckForPremFeature.assert_called_once_with('all')

    def test_lookup_exception_and_malformed_grants_deny_before_mail_work(self):
        for value in (True, '1', 1.0, None):
            with self.subTest(value=value):
                self.acl.CheckForPremFeature.return_value = value
                self.assert_denied(self.ns['installRspamd'](self.req))
                self.assert_denied(self.mail_class(self.req).SaveEmailLimitsNew(), ('createStatus',))
        self.acl.CheckForPremFeature.side_effect = TimeoutError('unavailable')
        for name in INTERACTIVE:
            self.assert_denied(self.ns[name](self.req))
        self.assert_denied(self.mail_class(self.req).SaveEmailLimitsNew())

    def test_paid_pages_deny_without_config_or_ip_reads(self):
        for call in (lambda:self.ns['Rspamd'](self.req),lambda:self.ns['EmailDebugger'](self.req),
                     lambda:self.mail_class(self.req).EmailLimits()):
            self.assertEqual(call().url, 'https://cyberpanel.net/cyberpanel-addons')
            self.assert_no_work()
        self.acl.CheckForPremFeature.side_effect = TimeoutError('unavailable')
        self.assertEqual(self.mail_class(self.req).EmailLimits().status_code, 302)
        self.assert_no_work()

    def test_authenticated_cloud_debugger_routes_deny_before_worker_or_report(self):
        for name in DEBUGGER:
            with self.subTest(name=name):
                self.acl.reset_mock()
                request = SimpleNamespace(body=json.dumps(dict(json.loads(self.req.body), controller=name, serverUserName='admin')).encode(),
                                          META={'HTTP_AUTHORIZATION':'inert-token'}, session={})
                self.assert_denied(self.ns['router'](request))
                self.acl.CheckForPremFeature.assert_called_once_with('email-debugger')

    def test_debugger_view_reuses_authoritative_cloud_denial_once(self):
        for name in DEBUGGER:
            with self.subTest(name=name):
                self.acl.reset_mock()
                self.assert_denied(self.ns[name](self.req))
                self.acl.CheckForPremFeature.assert_called_once_with('email-debugger')
                self.acl.GetServerIP.assert_not_called()

    def test_paid_rspamd_actions_preserve_original_commands_and_response(self):
        self.acl.CheckForPremFeature.return_value = 1
        for name in CONFIGS:
            with self.subTest(name=name):
                self.assertEqual(json.loads(self.ns[name](self.req).content)['saveStatus'], 1)
        self.assertEqual(self.output_file.call_count, 4)
        self.assertEqual(self.services['ProcessUtilities'].outputExecutioner.call_count, 4)
        self.assertEqual(json.loads(self.ns['installRspamd'](self.req).content)['status'], 1)
        self.services['ProcessUtilities'].popenExecutioner.assert_called_once_with(
            '/usr/local/CyberCP/bin/python /inert/CyberCP/plogical/mailUtilities.py installRspamd')
        result = json.loads(self.ns['fetchRspamdSettings'](self.req).content)
        self.assertEqual((result['fetchStatus'], result['installed']), (1,0))
        self.assertEqual(json.loads(self.ns['FetchRspamdLog'](self.req).content)['logstatus'], 1)
        self.assertEqual(json.loads(self.ns['RestartRspamd'](self.req).content)['status'], 1)
        self.services['ProcessUtilities'].executioner.assert_any_call('systemctl restart rspamd')

    def test_paid_does_not_bypass_existing_admin_checks(self):
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.loadedACL.return_value = {'admin':0}
        for name in INTERACTIVE + DEBUGGER:
            with self.subTest(name=name):
                result = json.loads(self.ns[name](self.req).content)
                self.assertEqual(result['error_message'], 'ACL denied')
                self.assert_no_work()

    def test_email_limits_still_require_permission_and_exact_site_ownership(self):
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.currentContextPermission.return_value = 0
        self.assertIn('ACL denied', self.mail_class(self.req).SaveEmailLimitsNew().content.decode())
        self.services['EUsers'].objects.get.assert_not_called()
        self.acl.currentContextPermission.return_value = 1
        self.acl.checkOwnership.return_value = 0
        self.assertIn('ACL denied', self.mail_class(self.req).SaveEmailLimitsNew().content.decode())
        self.acl.checkOwnership.assert_called_once()
        self.services['mailUtilities'].assert_not_called()
        self.services['ProcessUtilities'].executioner.assert_not_called()
        self.output_file.assert_not_called()

    def test_paid_email_limits_reach_original_install_and_configuration(self):
        self.acl.CheckForPremFeature.return_value = 1
        self.services['ProcessUtilities'].outputExecutioner.return_value = '1,None'
        response = self.mail_class(self.req).SaveEmailLimitsNew()
        self.assertEqual(json.loads(response.content)['status'], 1)
        self.acl.CheckForPremFeature.assert_called_once_with('all')
        self.assertEqual(self.acl.checkOwnership.call_args.args[0], 'owned.example')
        self.services['ProcessUtilities'].executioner.assert_any_call(
            '/usr/local/CyberCP/bin/python /inert/CyberCP/plogical/mailUtilities.py SetupEmailLimits')
        self.output_file().write.assert_called_once_with('owned@owned.example 50/1h\n')

    def test_paid_debugger_views_reach_workers_without_duplicate_lookup(self):
        self.acl.CheckForPremFeature.return_value = 1
        for name in ('RunServerLevelEmailChecks','ResetEmailConfigurations','debugEmailForSite','fixMailSSL'):
            with self.subTest(name=name):
                self.acl.reset_mock()
                self.assertEqual(json.loads(self.ns[name](self.req).content)['status'], 1)
                self.acl.CheckForPremFeature.assert_called_once_with('email-debugger')
        self.services['create_private_token_file'].assert_called_once_with('/inert/reports')
        self.services['MailServerManager'].return_value.start.assert_called_once_with()

    def test_core_mail_page_and_existing_job_status_remain_available(self):
        expected = self.services['httpProc'].return_value.render.return_value
        self.assertIs(self.mail_class(self.req).loadEmailHome(), expected)
        self.assertIs(self.ns['emailPolicyServer'](self.req), expected)
        self.services['ProcessUtilities'].outputExecutioner.return_value = 'working'
        result = json.loads(self.ns['installStatusRspamd'](self.req).content)
        self.assertEqual(result['abort'], 0)
        self.acl.CheckForPremFeature.assert_not_called()

    def test_mail_import_preserves_setup_before_entitlement_models(self):
        source = (ROOT / 'mailServer/mailserverManager.py').read_text()
        self.assertTrue(source.startswith('#!/usr/local/CyberCP/bin/python\n# coding=utf-8\n'))
        self.assertLess(source.index('django.setup()'), source.index(
            'from plogical.premiumEntitlements import premium_entitlement_required'))


if __name__ == '__main__':
    unittest.main()
