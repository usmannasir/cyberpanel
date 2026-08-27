import json
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase, override_settings

from loginSystem.twoFactor import (
    PENDING_CREATED_KEY,
    RECOVERY_CODES_KEY,
    confirm_recovery_codes,
    consume_recovery_code,
    prepare_recovery_codes,
)


@override_settings(
    PASSWORD_HASHERS=['django.contrib.auth.hashers.MD5PasswordHasher']
)
class RecoveryCodeTests(SimpleTestCase):

    @staticmethod
    def account():
        return SimpleNamespace(pk=7, config='{}', save=mock.Mock())

    def test_prepared_codes_are_hashed_and_require_confirmation(self):
        account = self.account()

        codes = prepare_recovery_codes(account)
        pendingConfig = json.loads(account.config)

        self.assertEqual(10, len(codes))
        self.assertEqual(10, len(set(codes)))
        self.assertNotIn(codes[0], account.config)
        self.assertTrue(confirm_recovery_codes(account))
        confirmedConfig = json.loads(account.config)
        self.assertEqual(10, len(confirmedConfig[RECOVERY_CODES_KEY]))
        self.assertNotIn(PENDING_CREATED_KEY, confirmedConfig)
        self.assertNotEqual(pendingConfig, confirmedConfig)

    @mock.patch('loginSystem.twoFactor.time.time', return_value=2000)
    def test_expired_pending_codes_cannot_be_confirmed(self, unused_time):
        account = self.account()
        account.config = json.dumps({
            'pendingTwoFARecoveryCodes': ['hash'] * 10,
            PENDING_CREATED_KEY: 1000,
        })

        self.assertFalse(confirm_recovery_codes(account))

    @mock.patch('loginSystem.twoFactor.time.time', return_value=1000)
    def test_future_dated_pending_codes_cannot_be_confirmed(self, unused_time):
        account = self.account()
        account.config = json.dumps({
            'pendingTwoFARecoveryCodes': ['hash'] * 10,
            PENDING_CREATED_KEY: 2000,
        })

        self.assertFalse(confirm_recovery_codes(account))

    @mock.patch('loginSystem.twoFactor.transaction.atomic', return_value=nullcontext())
    @mock.patch('loginSystem.twoFactor.Administrator.objects.select_for_update')
    def test_recovery_code_can_only_be_consumed_once(self, select_for_update, unused_atomic):
        account = self.account()
        codes = prepare_recovery_codes(account)
        self.assertTrue(confirm_recovery_codes(account))
        select_for_update.return_value.get.return_value = account

        self.assertTrue(consume_recovery_code(account.pk, codes[0]))
        self.assertFalse(consume_recovery_code(account.pk, codes[0]))


class RecoveryCodeLoginTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def request(self, data):
        request = self.factory.post(
            '/verifyLogin',
            data=json.dumps(data),
            content_type='application/json',
        )
        request.session = SessionStore()
        return request

    @staticmethod
    def admin():
        return SimpleNamespace(
            pk=7,
            password='stored-password-hash',
            state='ACTIVE',
            twoFA=1,
            secretKey='JBSWY3DPEHPK3PXP',
        )

    @mock.patch('loginSystem.views.consume_recovery_code', return_value=True)
    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_unused_recovery_code_can_complete_login(
        self, administrator_get, unused_password_check, consume_code
    ):
        from loginSystem.views import verifyLogin
        administrator_get.return_value = self.admin()
        request = self.request({
            'username': 'admin',
            'password': 'secret',
            'twofa': 'ABCDE-FGHIJ',
        })

        response = verifyLogin(request)

        self.assertEqual(1, json.loads(response.content)['loginStatus'])
        self.assertEqual(7, request.session['userID'])
        consume_code.assert_called_once_with(7, 'ABCDE-FGHIJ')

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=False)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_password_is_checked_before_two_factor_prompt(
        self, administrator_get, unused_password_check
    ):
        from loginSystem.views import verifyLogin
        administrator_get.return_value = self.admin()

        response = verifyLogin(self.request({
            'username': 'admin',
            'password': 'wrong',
        }))

        self.assertEqual(0, json.loads(response.content)['loginStatus'])
