"""User-detail loading must support keyword-only PyOTP provisioning APIs."""
import json
from types import SimpleNamespace
from unittest import mock
from urllib.parse import parse_qs, unquote, urlparse

import pyotp
from django.test import RequestFactory, SimpleTestCase

from userManagment.views import fetchUserDetails


class UserTOTPProvisioningTests(SimpleTestCase):
    secret = 'JBSWY3DPEHPK3PXPJBSWY3DPEHPK3PXP'

    def fetch(self, *, secret=None, twofa=False, actor=1, owner=99, admin=True, set_up=True):
        self.user = SimpleNamespace(
            id=2, pk=2, owner=owner, firstName='QA', lastName='User',
            email='qa+otp@example.invalid', initWebsitesLimit=10,
            secretKey=self.secret if secret is None else secret,
            acl=SimpleNamespace(name='user'), securityLevel=0,
            twoFA=twofa, save=mock.Mock())
        request = RequestFactory().post(
            '/users/fetchUserDetails',
            data=json.dumps(dict({'accountUsername': 'qa-user'}, **({'twofaSetup': True} if set_up else {}))),
            content_type='application/json')
        request.session = {'userID': actor}
        real_uri = pyotp.TOTP.provisioning_uri

        # New PyOTP accepts name only as a keyword. Exercise this contract even
        # when the test runner has an older (still supported) dependency.
        def keyword_uri(otp, *, name=None, issuer_name=None, **kwargs):
            return real_uri(otp, name=name, issuer_name=issuer_name, **kwargs)

        with mock.patch('userManagment.views.Administrator.objects.get',
                        side_effect=[self.user, SimpleNamespace(pk=actor)]), \
                mock.patch('userManagment.views.ACLManager.loadedACL',
                           return_value={'admin': int(admin)}), \
                mock.patch.object(pyotp.TOTP, 'provisioning_uri', keyword_uri):
            return json.loads(fetchUserDetails(request).content)

    def assert_uri(self, result):
        self.assertEqual(result['fetchStatus'], 1, result)
        uri = result['userDetails']['otpauth']
        parsed = urlparse(uri)
        self.assertEqual((parsed.scheme, parsed.netloc), ('otpauth', 'totp'))
        self.assertEqual(unquote(parsed.path), '/CyberPanel:qa+otp@example.invalid')
        self.assertEqual(parse_qs(parsed.query)['secret'], [self.user.secretKey])
        self.assertEqual(parse_qs(parsed.query)['issuer'], ['CyberPanel'])
        self.assertTrue(pyotp.parse_uri(uri).verify(pyotp.TOTP(self.user.secretKey).now()))

    def test_set_up_replaces_an_unconfirmed_secret(self):
        result = self.fetch()
        self.assert_uri(result)
        self.assertFalse(result['userDetails']['twofa'])
        self.assertNotEqual(self.user.secretKey, self.secret)
        self.user.save.assert_called_once_with()

    def test_existing_secret_and_enabled_twofa_are_preserved_and_not_sent(self):
        result = self.fetch(twofa=True)
        self.assertEqual(result['fetchStatus'], 1, result)
        self.assertNotIn('otpauth', result['userDetails'])
        self.assertNotIn(self.secret, json.dumps(result))
        self.assertTrue(result['userDetails']['twofa'])
        self.assertEqual(self.user.secretKey, self.secret)
        self.user.save.assert_not_called()

    def test_loading_without_set_up_sends_and_generates_no_secret(self):
        result = self.fetch(secret='None', set_up=False)
        self.assertEqual(result['fetchStatus'], 1, result)
        self.assertNotIn('otpauth', result['userDetails'])
        self.assertEqual(self.user.secretKey, 'None')
        self.user.save.assert_not_called()

    def test_initial_enrollment_generates_one_secret(self):
        result = self.fetch(secret='None')
        self.assert_uri(result)
        self.assertNotEqual(self.user.secretKey, 'None')
        self.user.save.assert_called_once_with()

    def test_account_owner_can_fetch(self):
        self.assert_uri(self.fetch(admin=False, owner=1))

    def test_self_can_fetch(self):
        self.assert_uri(self.fetch(admin=False, actor=2))

    def test_unrelated_user_cannot_fetch_or_generate_secret(self):
        result = self.fetch(admin=False, secret='None')
        self.assertEqual(result['fetchStatus'], 0)
        self.assertEqual(result['error_message'], 'Un-authorized access.')
        self.assertNotIn('userDetails', result)
        self.assertEqual(self.user.secretKey, 'None')
        self.user.save.assert_not_called()

    def test_missing_session_is_rejected(self):
        request = RequestFactory().post('/users/fetchUserDetails', data='{}',
                                        content_type='application/json')
        request.session = {}
        with mock.patch('userManagment.views.Administrator.objects.get') as get:
            result = json.loads(fetchUserDetails(request).content)
        self.assertEqual(result['fetchStatus'], 0)
        get.assert_not_called()
