"""Run actual token and WebSocket methods with inert identity/file/SSH boundaries."""
import ast
import asyncio
import json
import logging
from pathlib import Path
from types import ModuleType, SimpleNamespace
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class JWTError(Exception):
    pass


class WebSocketDisconnect(Exception):
    pass


def compile_method(path, name, env):
    source = ast.parse((ROOT / path).read_text())
    method = next(node for node in source.body
                  if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    method.decorator_list = []
    exec(compile(ast.Module(body=[method], type_ignores=[]), path, 'exec'), env)
    return env[name]


class TerminalEntitlementTests(unittest.TestCase):
    def setUp(self):
        self.acl = mock.Mock()
        self.acl.CheckForPremFeature.return_value = 0
        self.acl.loadedACL.return_value = {'admin': 1}
        self.acl.checkOwnership.return_value = 1
        self.sites = mock.Mock()
        self.sites.DoesNotExist = type('MissingSite', (Exception,), {})
        self.sites.objects.get.return_value = SimpleNamespace(externalApp='owneduser')
        self.admins = mock.Mock()
        self.encoder = mock.Mock()
        self.encoder.encode.return_value = 'inert-signed-token'
        modules = {}
        for name, attrs in {
            'websiteFunctions.models': {'Websites': self.sites},
            'plogical.acl': {'ACLManager': self.acl},
            'loginSystem.models': {'Administrator': self.admins},
            'jwt': {'encode': self.encoder.encode},
        }.items():
            module = ModuleType(name)
            vars(module).update(attrs)
            modules[name] = module
        self.imports = mock.patch.dict('sys.modules', modules)
        self.imports.start()
        self.addCleanup(self.imports.stop)
        self.env = {'json': json, 'JsonResponse': lambda value: value,
                    'get_terminal_jwt_secret': mock.Mock(return_value='inert-secret'),
                    'create_terminal_request': mock.Mock(return_value='owned-jti'),
                    'TERMINAL_JWT_ISSUER': 'cyberpanel-web-terminal',
                    'TERMINAL_JWT_AUDIENCE': 'cyberpanel-web-terminal'}
        self.issue = compile_method('websiteFunctions/views.py', 'get_terminal_jwt', self.env)
        self.request = SimpleNamespace(body=json.dumps({'domain': 'owned.example'}), session={'userID': 7})

    def assert_no_token_effects(self):
        self.env['get_terminal_jwt_secret'].assert_not_called()
        self.env['create_terminal_request'].assert_not_called()
        self.encoder.encode.assert_not_called()

    def test_unpaid_or_lookup_failure_cannot_create_request_file_secret_or_jwt(self):
        for value in (0, True, '1', 1.0, None, {}, -1, RuntimeError('lookup unavailable')):
            with self.subTest(value=value):
                self.acl.CheckForPremFeature.side_effect = value if isinstance(value, Exception) else None
                self.acl.CheckForPremFeature.return_value = value
                result = self.issue(self.request)
                self.assertEqual(result['status'], 0)
                self.assertIn('Add-ons', result['error_message'])
                self.assertNotIn('token', result)
                self.assert_no_token_effects()
                self.admins.objects.get.assert_not_called()
                self.sites.objects.get.assert_not_called()
                self.acl.loadedACL.assert_not_called()

    def test_authentication_still_precedes_paid_lookup(self):
        self.request.session = {}
        self.assertEqual(self.issue(self.request)['error_message'], 'Not authenticated')
        self.acl.CheckForPremFeature.assert_not_called()
        self.assert_no_token_effects()

    def test_paid_grant_cannot_override_ownership_or_missing_site(self):
        self.acl.CheckForPremFeature.return_value = 1
        self.acl.checkOwnership.return_value = 0
        self.assertEqual(self.issue(self.request)['error_message'], 'Not authorized')
        self.assert_no_token_effects()
        self.sites.objects.get.assert_not_called()
        self.acl.checkOwnership.return_value = 1
        self.sites.objects.get.side_effect = self.sites.DoesNotExist()
        self.assertEqual(self.issue(self.request)['error_message'], 'Website not found')
        self.assert_no_token_effects()

    def test_paid_issuer_binds_grant_to_existing_identity_and_ten_minute_token(self):
        self.acl.CheckForPremFeature.return_value = 1
        result = self.issue(self.request)
        self.assertEqual(result, {'status': 1, 'token': 'inert-signed-token', 'ssh_user': 'owneduser'})
        self.acl.CheckForPremFeature.assert_called_once_with('all')
        self.acl.checkOwnership.assert_called_once_with('owned.example', self.admins.objects.get.return_value, {'admin': 1})
        self.env['create_terminal_request'].assert_called_once_with(7, 'owneduser')
        payload = self.encoder.encode.call_args.args[0]
        self.assertIs(payload['web_terminal'], True)
        self.assertEqual(payload['sub'], '7')
        self.assertEqual(payload['ssh_user'], 'owneduser')
        self.assertEqual(payload['jti'], 'owned-jti')
        self.assertEqual((payload['exp'] - payload['iat']).total_seconds(), 600)
        self.assertEqual(self.encoder.encode.call_args.kwargs, {'algorithm': 'HS256'})

    def server(self, grant=True):
        payload = {'iat': 100, 'exp': 700, 'jti': 'owned-jti', 'sub': '7',
                   'ssh_user': 'owneduser', 'web_terminal': grant}
        env = {'jwt': mock.Mock(), 'JWTError': JWTError, 'JWT_SECRET': 'inert-secret', 'JWT_ALGORITHM': 'HS256',
               'TERMINAL_JWT_AUDIENCE': 'expected-audience', 'TERMINAL_JWT_ISSUER': 'expected-issuer',
               'MAX_TOKEN_LIFETIME_SECONDS': 900, 'consume_terminal_request': mock.Mock(return_value=True),
               'WebSocket': object, 'Query': lambda value: value, 'WebSocketDisconnect': WebSocketDisconnect,
               'pwd': mock.Mock(), 'open_authorized_keys': mock.Mock(return_value=37),
               'generate_ssh_keypair': mock.Mock(return_value=('private-inert', 'public-inert')),
               'add_ephemeral_key': mock.Mock(), 'remove_ephemeral_key': mock.Mock(),
               'os': mock.Mock(), 'tempfile': mock.Mock(), 'logging': logging, 'asyncio': asyncio,
               'asyncssh': SimpleNamespace(connect=mock.AsyncMock())}
        env['jwt'].decode.return_value = payload
        env['os'].urandom.return_value = b'inert123'
        env['tempfile'].NamedTemporaryFile.return_value = mock.MagicMock()
        env['tempfile'].NamedTemporaryFile.return_value.__enter__.return_value.name = '/inert/private-key'
        env['pwd'].getpwnam.return_value = SimpleNamespace(pw_uid=1007)
        conn = env['asyncssh'].connect.return_value
        process = mock.Mock()
        process.stdout.at_eof.return_value = True
        conn.create_process = mock.AsyncMock(return_value=process)
        conn.close = mock.Mock()
        decode = compile_method('fastapi_ssh_server.py', 'decode_terminal_token', env)
        endpoint = compile_method('fastapi_ssh_server.py', 'websocket_endpoint', env)
        env['SSH_PORT'] = 22
        return env, decode, endpoint

    def test_missing_or_malformed_signed_grant_rejects_before_one_time_request_consumption(self):
        for value in (None, False, 0, 1, 'true', [], {}):
            with self.subTest(value=value):
                env, decode, unused = self.server(value)
                with self.assertRaises(JWTError):
                    decode('inert-token')
                env['consume_terminal_request'].assert_not_called()

    def test_paid_grant_preserves_signature_options_and_one_use_authorization(self):
        env, decode, unused = self.server()
        self.assertEqual(decode('inert-token')['ssh_user'], 'owneduser')
        args = env['jwt'].decode.call_args
        self.assertEqual(args.kwargs['algorithms'], ['HS256'])
        self.assertEqual(args.kwargs['audience'], 'expected-audience')
        self.assertEqual(args.kwargs['issuer'], 'expected-issuer')
        for key, value in args.kwargs['options'].items():
            self.assertTrue(value, key)
        env['consume_terminal_request'].assert_called_once_with('owned-jti', '7', 'owneduser')
        env['consume_terminal_request'].return_value = False
        with self.assertRaises(JWTError):
            decode('same-inert-token')

    def test_grant_does_not_override_lifetime_or_signature_failure(self):
        env, decode, unused = self.server()
        env['jwt'].decode.return_value['exp'] = 3700
        with self.assertRaises(JWTError):
            decode('inert-token')
        env['consume_terminal_request'].assert_not_called()
        env['jwt'].decode.side_effect = JWTError('bad signature')
        with self.assertRaises(JWTError):
            decode('inert-token')
        env['consume_terminal_request'].assert_not_called()

    def test_legacy_token_websocket_closes_before_account_file_or_ssh_effects(self):
        env, unused, endpoint = self.server(None)
        ws = mock.AsyncMock()
        asyncio.run(endpoint(ws, token='legacy-token', ssh_user='owneduser'))
        ws.close.assert_awaited_once_with(code=4403)
        ws.accept.assert_not_awaited()
        env['pwd'].getpwnam.assert_not_called()
        env['open_authorized_keys'].assert_not_called()
        env['generate_ssh_keypair'].assert_not_called()
        env['asyncssh'].connect.assert_not_awaited()

    def test_paid_websocket_preserves_account_identity_and_root_rejections(self):
        for mismatched in (True, False):
            env, unused, endpoint = self.server()
            if not mismatched:
                env['pwd'].getpwnam.return_value.pw_uid = 0
            ws = mock.AsyncMock()
            asyncio.run(endpoint(ws, token='paid-token', ssh_user='someoneelse' if mismatched else 'owneduser'))
            ws.close.assert_awaited_once_with(code=4403)
            ws.accept.assert_not_awaited()
            env['open_authorized_keys'].assert_not_called()

    def test_paid_websocket_runs_existing_owned_flow_and_cleanup(self):
        env, unused, endpoint = self.server()
        ws = mock.AsyncMock()
        ws.receive_bytes.side_effect = WebSocketDisconnect()
        asyncio.run(endpoint(ws, token='paid-token', ssh_user='owneduser'))
        ws.accept.assert_awaited_once()
        env['asyncssh'].connect.assert_awaited_once_with('127.0.0.1', port=22, username='owneduser',
            client_keys=['/inert/private-key'], known_hosts=None)
        env['asyncssh'].connect.return_value.create_process.assert_awaited_once_with(term_type='xterm')
        env['add_ephemeral_key'].assert_called_once()
        env['remove_ephemeral_key'].assert_called_once_with(37, mock.ANY)
        env['os'].close.assert_called_once_with(37)
        env['os'].unlink.assert_called_once_with('/inert/private-key')


if __name__ == '__main__':
    unittest.main()
