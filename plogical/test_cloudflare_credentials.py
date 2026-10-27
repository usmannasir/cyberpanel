import json
import os
from pathlib import Path
import stat
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from plogical import cloudflareCredentials as cf
from plogical.test_interactive_premium_entitlements import actual
from plogical import test_interactive_premium_entitlements as _entitlements

TOKEN = 'synthetic_token_1234567890'
KEY = 'synthetic_global_key_1234567890'


class CredentialTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name).resolve() / 'account.conf'
        self.path.write_text("ACCOUNT_EMAIL='owner@example.test'\nPDNS_Token='leave-alone'\nSAVED_CF_Key='old-legacy-credential'\nSAVED_CF_Email='owner@example.test'\n")

    def test_switch_to_token_removes_stale_auth_preserves_other_providers(self):
        cf.save('token', TOKEN, path=self.path)
        self.assertEqual({'CF_Token': TOKEN}, cf.credentials(self.path))
        text = self.path.read_text()
        self.assertIn("PDNS_Token='leave-alone'", text)
        self.assertNotIn('CF_Key', text)
        self.assertNotIn('CF_Email', text)
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))
        self.assertEqual({'configured': True, 'mode': 'token'}, cf.metadata(self.path))
        self.assertNotIn(TOKEN, json.dumps(cf.metadata(self.path)))

    def test_switch_to_legacy_removes_token_and_zone_scope(self):
        self.path.write_text("CF_Token='old-token-123'\nSAVED_CF_Token='old-token-456'\nCF_Zone_ID='stale-zone'\nSAVED_CF_Account_ID='stale-account'\n")
        cf.save('global_key', KEY, 'owner@example.test', self.path)
        self.assertEqual({'CF_Key': KEY, 'CF_Email': 'owner@example.test'}, cf.credentials(self.path))
        self.assertNotIn('Token', self.path.read_text())
        self.assertNotIn('Zone_ID', self.path.read_text())

    def test_invalid_input_does_not_modify_credentials(self):
        old = self.path.read_bytes()
        for mode, secret, email in [('token', "bad'\n$(touch /tmp/x)", ''), ('token', 'abc', ''), ('global_key', KEY, 'bad'), ('unknown', TOKEN, '')]:
            with self.subTest(mode=mode, secret=secret):
                with self.assertRaises(ValueError):
                    cf.save(mode, secret, email, self.path)
                self.assertEqual(old, self.path.read_bytes())

    def test_failed_replace_preserves_previous_credentials(self):
        old = self.path.read_bytes()
        with patch.object(cf.os, 'replace', side_effect=OSError):
            with self.assertRaises(OSError):
                cf.save('token', TOKEN, path=self.path)
        self.assertEqual(old, self.path.read_bytes())
        self.assertEqual([], list(self.path.parent.glob('.cyberpanel-cloudflare-*')))

    def test_symlink_and_shared_parent_are_refused(self):
        alias = self.path.parent / 'alias'
        alias.symlink_to(self.path)
        with self.assertRaises(ValueError):
            cf.save('token', TOKEN, path=alias)
        os.chmod(self.path.parent, 0o777)
        with self.assertRaises(ValueError):
            cf.save('token', TOKEN, path=self.path)
        os.chmod(self.path.parent, 0o700)

    def test_shell_expressions_are_not_evaluated(self):
        marker = self.path.parent / 'executed'
        self.path.write_text("SAVED_CF_Token='$(touch %s)'\n" % marker)
        with self.assertRaises(ValueError):
            cf.credentials(self.path)
        self.assertFalse(marker.exists())

    def test_root_subprocess_receives_secret_only_through_stdin(self):
        result = SimpleNamespace(returncode=0, stdout=b'{"configured": true, "mode": "token"}')
        with patch.object(cf.os, 'geteuid', return_value=0), patch.object(cf.subprocess, 'run', return_value=result) as run:
            cf.request('save', {'mode': 'token', 'secret': TOKEN})
        args, kwargs = run.call_args
        self.assertIn('-I', args[0])
        self.assertIn('-S', args[0])
        self.assertNotIn(TOKEN, str(args))
        self.assertIn(TOKEN.encode(), kwargs['input'])
        self.assertNotIn('shell', kwargs)

    def test_web_uses_fixed_sudo_action_and_stdin(self):
        result = SimpleNamespace(returncode=0, stdout=b'{"configured": true, "mode": "token"}')
        with patch.object(cf.os, 'geteuid', return_value=1000), patch.object(cf.subprocess, 'run', return_value=result) as run:
            cf.request('save', {'mode': 'token', 'secret': TOKEN})
        args, kwargs = run.call_args
        self.assertEqual(['sudo', '-n', '--', '/usr/local/CyberPanel/bin/python', '-I', '-S',
                          '/usr/local/CyberCP/plogical/cloudflareCredentials.py', 'save'], args[0])
        self.assertNotIn(TOKEN, str(args))
        self.assertIn(TOKEN.encode(), kwargs['input'])
        self.assertNotIn('shell', kwargs)

    def test_unexpected_helper_output_is_rejected(self):
        result = SimpleNamespace(returncode=0, stdout=b'{"configured": true, "mode": "token", "secret": "do-not-return"}')
        with patch.object(cf.subprocess, 'run', return_value=result):
            with self.assertRaisesRegex(ValueError, 'could not be saved'):
                cf.request('metadata')

    def test_failed_subprocess_error_does_not_disclose_output(self):
        with patch.object(cf.subprocess, 'run', return_value=SimpleNamespace(returncode=1, stdout=TOKEN.encode(), stderr=KEY.encode())):
            with self.assertRaisesRegex(ValueError, 'could not be saved') as error:
                cf.request('save', {'secret': TOKEN})
        self.assertNotIn(TOKEN, str(error.exception))

    def test_token_zone_lookup_uses_bearer_and_no_origin_lookup(self):
        session = Mock()
        session.get.side_effect = [SimpleNamespace(status_code=200, json=lambda: {'success': True, 'result': []}),
            SimpleNamespace(status_code=200, json=lambda: {'success': True, 'result': [{'name': 'example.test', 'status': 'active'}]})]
        self.assertEqual((1, None), cf.find_zone('tunnel.example.test', {'CF_Token': TOKEN}, session))
        for call in session.get.call_args_list:
            self.assertEqual({'Authorization': 'Bearer ' + TOKEN}, call.kwargs['headers'])
            self.assertFalse(call.kwargs['allow_redirects'])
            self.assertEqual(10, call.kwargs['timeout'])
        self.assertEqual('example.test', session.get.call_args.kwargs['params']['name'])

    def test_legacy_zone_lookup_and_redacted_failure(self):
        session = Mock()
        session.get.return_value = SimpleNamespace(status_code=403, json=lambda: {'error': TOKEN})
        result = cf.find_zone('example.test', {'CF_Key': KEY, 'CF_Email': 'owner@example.test'}, session)
        self.assertEqual(0, result[0])
        self.assertNotIn(TOKEN, result[1])
        self.assertEqual({'X-Auth-Key': KEY, 'X-Auth-Email': 'owner@example.test'}, session.get.call_args.kwargs['headers'])


class ViewTests(unittest.TestCase):
    def setUp(self):
        _entitlements.EntitlementTests.setUp(self)
        actual('manageSSL/views.py', ['v2ManageSSL'], self.env)
        self.acl.CheckForPremFeature.return_value = 1
        self.helper = patch.object(cf, 'request', return_value={'configured': True, 'mode': 'token'}).start()
        self.addCleanup(patch.stopall)

    def test_non_admin_get_never_reads_credentials(self):
        self.acl.loadedACL.return_value = {'admin': 0, 'manageSSL': 1}
        result = self.env['v2ManageSSL'](SimpleNamespace(session={'userID': 7}, method='GET'))
        self.assertFalse(result[2]['CanConfigureDNS'])
        self.helper.assert_not_called()

    def test_non_admin_post_cannot_change_server_provider(self):
        self.acl.loadedACL.return_value = {'admin': 0, 'manageSSL': 1}
        result = self.env['v2ManageSSL'](SimpleNamespace(session={'userID': 7}, method='POST'))
        self.assertEqual({'ownership_denied': True}, result)
        self.helper.assert_not_called()

    def test_admin_get_reads_only_redacted_metadata(self):
        result = self.env['v2ManageSSL'](SimpleNamespace(session={'userID': 7}, method='GET'))
        self.helper.assert_called_once_with('metadata')
        self.assertNotIn('SAVED_CF_Key', result[2])
        self.assertTrue(result[2]['CFConfigured'])

    def test_admin_save_preserves_mode_and_reports_success(self):
        request = SimpleNamespace(session={'userID': 7}, method='POST', POST={'CF_Mode': 'token', 'SAVED_CF_Key': TOKEN})
        result = self.env['v2ManageSSL'](request)
        self.helper.assert_any_call('save', {'mode': 'token', 'secret': TOKEN, 'email': ''})
        self.assertEqual(1, result[2]['SaveSuccess'])
        self.assertNotIn(TOKEN, str(result[2]))

    def test_failed_save_is_not_success(self):
        self.helper.side_effect = ValueError(cf.ERROR)
        request = SimpleNamespace(session={'userID': 7}, method='POST', POST={'CF_Mode': 'token', 'SAVED_CF_Key': TOKEN})
        result = self.env['v2ManageSSL'](request)
        self.assertNotIn('SaveSuccess', result[2])
        self.assertEqual(cf.ERROR, result[2]['SaveError'])

    def test_unpaid_or_malformed_entitlement_cannot_save(self):
        for grant in (0, '1', True, None, 1.0):
            with self.subTest(grant=grant):
                self.acl.CheckForPremFeature.return_value = grant
                result = self.env['v2ManageSSL'](SimpleNamespace(session={'userID': 7}, method='POST'))
                self.assertEqual(0, result[2]['PremStat'])
                self.helper.assert_not_called()



if __name__ == '__main__':
    unittest.main()
