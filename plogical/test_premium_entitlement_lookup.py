"""Run the actual entitlement method with inert platform/HTTP dependencies."""
import ast
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock


def load_lookup():
    source = Path(__file__).with_name('acl.py').read_text()
    tree = ast.parse(source)
    owner = next(node for node in tree.body
                 if isinstance(node, ast.ClassDef) and node.name == 'ACLManager')
    method = next(node for node in owner.body
                  if isinstance(node, ast.FunctionDef)
                  and node.name == 'CheckForPremFeature')
    owner.body = [method]
    module = ast.Module(body=[owner], type_ignores=[])
    runtime = SimpleNamespace(ent=1, OLS=0, decideServer=mock.Mock(return_value=0))
    namespace = {'ProcessUtilities': runtime, 'json': json}
    exec(compile(module, str(Path(__file__).with_name('acl.py')), 'exec'), namespace)
    manager = namespace['ACLManager']
    manager.GetServerIP = mock.Mock(return_value='192.0.2.10')
    return manager, runtime


class PremiumEntitlementLookupTests(unittest.TestCase):
    def setUp(self):
        self.manager, self.runtime = load_lookup()
        self.requests = ModuleType('requests')
        self.response = SimpleNamespace(
            status_code=200, json=mock.Mock(return_value={'status': 1}))
        self.requests.post = mock.Mock(return_value=self.response)
        patcher = mock.patch.dict(sys.modules, {'requests': self.requests})
        patcher.start()
        self.addCleanup(patcher.stop)

    def lookup(self, feature='all'):
        return self.manager.CheckForPremFeature(feature)

    def test_integer_grant_uses_exact_feature_and_bounded_request(self):
        for feature in ('all', 'wp-manager', 'email-debugger'):
            with self.subTest(feature=feature):
                self.requests.post.reset_mock()
                self.assertEqual(1, self.lookup(feature))
                self.requests.post.assert_called_once_with(
                    'https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission',
                    data=json.dumps({'name': feature, 'IP': '192.0.2.10'}),
                    timeout=(3.05, 10), allow_redirects=False)

    def test_explicit_denial_returns_integer_zero(self):
        self.response.json.return_value = {'status': 0}
        result = self.lookup()
        self.assertIs(type(result), int)
        self.assertEqual(0, result)

    def test_truthy_or_wrong_type_status_does_not_grant(self):
        for status in ('1', '0', True, False, 1.0, 0.0, None, 2, -1, [1], {'all': 1}):
            with self.subTest(status=status):
                self.response.json.return_value = {'status': status}
                result = self.lookup()
                self.assertIs(type(result), int)
                self.assertEqual(0, result)

    def test_missing_status_and_nonobject_payloads_deny(self):
        for payload in ({}, [], [1], '1', 1, True, None):
            with self.subTest(payload=payload):
                self.response.json.return_value = payload
                self.assertEqual(0, self.lookup())

    def test_non_success_http_cannot_grant_even_with_positive_body(self):
        for code in (204, 301, 302, 307, 400, 401, 403, 429, 500, 503):
            with self.subTest(code=code):
                self.response.status_code = code
                self.response.json.reset_mock()
                self.assertEqual(0, self.lookup())
                self.response.json.assert_not_called()

    def test_malformed_json_denies(self):
        self.response.json.side_effect = ValueError('invalid JSON')
        self.assertEqual(0, self.lookup())

    def test_request_timeout_or_connection_error_denies_without_retry(self):
        for error in (TimeoutError('timeout'), ConnectionError('unavailable')):
            with self.subTest(error=type(error).__name__):
                self.requests.post.reset_mock()
                self.requests.post.side_effect = error
                self.assertEqual(0, self.lookup())
                self.requests.post.assert_called_once()

    def test_machine_ip_failure_denies_before_request(self):
        self.manager.GetServerIP.side_effect = OSError('missing machine IP')
        self.assertEqual(0, self.lookup())
        self.requests.post.assert_not_called()

    def test_server_detection_failure_denies_before_request(self):
        self.runtime.decideServer.side_effect = OSError('unavailable')
        self.assertEqual(0, self.lookup())
        self.requests.post.assert_not_called()

    def test_enterprise_grant_is_preserved_without_ip_or_network_lookup(self):
        self.runtime.decideServer.return_value = self.runtime.ent
        self.manager.GetServerIP.side_effect = AssertionError('must not read')
        self.requests.post.side_effect = AssertionError('must not call')
        self.assertEqual(1, self.lookup())
        self.manager.GetServerIP.assert_not_called()
        self.requests.post.assert_not_called()

    def test_previous_grant_is_not_reused_after_subsequent_failure(self):
        self.assertEqual(1, self.lookup())
        self.requests.post.side_effect = TimeoutError('timeout')
        self.assertEqual(0, self.lookup())
        self.assertEqual(2, self.requests.post.call_count)


if __name__ == '__main__':
    unittest.main()
