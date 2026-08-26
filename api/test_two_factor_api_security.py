import hashlib
import json
from types import SimpleNamespace
from unittest import mock

import pyotp
from django.core.cache import cache
from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase

from api.views import get_api_admin, loginAPI, verifyConn
from cloudAPI.cloudManager import CloudManager
from plogical import hashPassword
from plogical.securityUtils import (
    api_token_matches,
    api_two_factor_matches,
    ensure_api_token,
    generate_api_token,
    is_current_api_token,
    normalize_api_token,
)


class APITwoFactorSecurityTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def tearDown(self):
        cache.clear()

    @staticmethod
    def admin(two_factor=1):
        secret = pyotp.random_base32()
        token = generate_api_token()
        return SimpleNamespace(
            pk=7,
            api=1,
            state='ACTIVE',
            password='stored-password',
            token=token,
            twoFA=two_factor,
            secretKey=secret,
        )

    def test_password_derived_legacy_token_is_rejected_and_rotated(self):
        legacy = 'Basic ' + hashlib.sha256(b'admin:secret').hexdigest()
        account = SimpleNamespace(token=legacy, save=mock.Mock())

        self.assertFalse(is_current_api_token(legacy))
        self.assertFalse(api_token_matches(legacy, legacy))
        self.assertTrue(ensure_api_token(account))
        self.assertTrue(is_current_api_token(account.token))
        self.assertNotEqual(account.token, legacy)
        account.save.assert_called_once_with(update_fields=['token'])

    def test_generated_tokens_are_versioned_random_credentials(self):
        first = generate_api_token()
        second = generate_api_token()

        self.assertTrue(normalize_api_token(first).startswith('cp_api_v1_'))
        self.assertTrue(is_current_api_token(first))
        self.assertNotEqual(first, second)
        self.assertTrue(api_token_matches('Bearer ' + normalize_api_token(first), first))

    def test_hash_password_token_helper_no_longer_depends_on_password(self):
        first = hashPassword.generateToken('admin', 'same-password')
        second = hashPassword.generateToken('admin', 'same-password')

        self.assertNotEqual(first, second)
        self.assertTrue(is_current_api_token(first))
        self.assertTrue(is_current_api_token(second))

    def test_two_factor_helper_requires_current_code(self):
        admin = self.admin()
        missing = self.factory.post('/api/', data={})
        valid = self.factory.post(
            '/api/',
            data={},
            HTTP_X_CYBERPANEL_OTP=pyotp.TOTP(admin.secretKey).now(),
        )

        self.assertFalse(api_two_factor_matches(admin, missing, {}))
        self.assertTrue(api_two_factor_matches(admin, valid, {}))
        admin.twoFA = 0
        self.assertTrue(api_two_factor_matches(admin, missing, {}))

    def test_two_factor_helper_rate_limits_failed_codes(self):
        admin = self.admin()
        current_code = pyotp.TOTP(admin.secretKey).now()
        invalid_code = '000000' if current_code != '000000' else '000001'
        invalid = self.factory.post(
            '/api/',
            data={},
            HTTP_X_CYBERPANEL_OTP=invalid_code,
            REMOTE_ADDR='192.0.2.50',
        )
        valid = self.factory.post(
            '/api/',
            data={},
            HTTP_X_CYBERPANEL_OTP=current_code,
            REMOTE_ADDR='192.0.2.50',
        )

        for unused_attempt in range(10):
            self.assertFalse(api_two_factor_matches(admin, invalid, {}))
        self.assertFalse(api_two_factor_matches(admin, valid, {}))

        cache.clear()
        self.assertTrue(api_two_factor_matches(admin, valid, {}))

    @mock.patch('api.views.Administrator.objects.get')
    def test_get_api_admin_requires_token_and_otp(self, get_admin):
        admin = self.admin()
        get_admin.return_value = admin
        data = {'adminUser': 'admin'}

        request = self.factory.post(
            '/api/listPackage',
            HTTP_AUTHORIZATION=admin.token,
        )
        authenticated, response = get_api_admin(request, data)
        self.assertIsNone(authenticated)
        self.assertEqual(response.status_code, 401)

        request = self.factory.post(
            '/api/listPackage',
            HTTP_AUTHORIZATION=admin.token,
            HTTP_X_CYBERPANEL_OTP=pyotp.TOTP(admin.secretKey).now(),
        )
        authenticated, response = get_api_admin(request, data)
        self.assertIs(authenticated, admin)
        self.assertIsNone(response)

    @mock.patch('api.views.hashPassword.check_password', return_value=True)
    @mock.patch('api.views.Administrator.objects.get')
    def test_password_api_auth_also_requires_otp(self, get_admin, unused_password_check):
        admin = self.admin()
        get_admin.return_value = admin
        data = {'adminUser': 'admin', 'adminPass': 'correct-password'}

        authenticated, response = get_api_admin(self.factory.post('/api/'), data, allow_token=False)
        self.assertIsNone(authenticated)
        self.assertEqual(response.status_code, 401)

        request = self.factory.post(
            '/api/',
            HTTP_X_CYBERPANEL_OTP=pyotp.TOTP(admin.secretKey).now(),
        )
        authenticated, response = get_api_admin(request, data, allow_token=False)
        self.assertIs(authenticated, admin)
        self.assertIsNone(response)

    @mock.patch('api.views.hashPassword.check_password', return_value=True)
    @mock.patch('api.views.Administrator.objects.get')
    def test_verify_connection_requires_otp(self, get_admin, unused_password_check):
        admin = self.admin()
        get_admin.return_value = admin
        body = json.dumps({'adminUser': 'admin', 'adminPass': 'correct-password'})

        response = verifyConn(self.factory.post('/api/verifyConn', body, content_type='application/json'))
        self.assertEqual(response.status_code, 401)
        self.assertEqual(json.loads(response.content)['verifyConn'], 0)

        request = self.factory.post(
            '/api/verifyConn',
            body,
            content_type='application/json',
            HTTP_X_CYBERPANEL_OTP=pyotp.TOTP(admin.secretKey).now(),
        )
        response = verifyConn(request)
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.content)
        self.assertEqual(response_data['verifyConn'], 1)
        self.assertEqual(response_data['apiToken'], admin.token)
        self.assertEqual(response['Cache-Control'], 'no-store')

    @mock.patch('api.views.hashPassword.check_password', return_value=True)
    @mock.patch('api.views.Administrator.objects.get')
    def test_login_api_cannot_mint_session_without_otp(self, get_admin, unused_password_check):
        admin = self.admin()
        get_admin.return_value = admin
        request = self.factory.post('/api/login', {'username': 'admin', 'password': 'correct-password'})
        request.session = SessionStore()

        response = loginAPI(request)

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('userID', request.session)

    def test_cloud_router_auth_requires_otp(self):
        admin = self.admin()
        manager = CloudManager({'serverUserName': 'admin'}, admin)
        request = self.factory.post('/cloudAPI/', HTTP_AUTHORIZATION=admin.token)

        authenticated, response = manager.verifyLogin(request)
        self.assertEqual(authenticated, 0)
        self.assertEqual(json.loads(response.content)['status'], 0)

        request = self.factory.post(
            '/cloudAPI/',
            HTTP_AUTHORIZATION=admin.token,
            HTTP_X_CYBERPANEL_OTP=pyotp.TOTP(admin.secretKey).now(),
        )
        authenticated, response = manager.verifyLogin(request)
        self.assertEqual(authenticated, 1)
        self.assertEqual(json.loads(response.content)['status'], 1)
