import json
import os

import pyotp
import requests
from django.test import SimpleTestCase, tag


@tag('integration')
class TwoFactorAPIIntegrationTests(SimpleTestCase):
    def setUp(self):
        required = {
            'base_url': os.environ.get('CYBERPANEL_2FA_TEST_URL', '').rstrip('/'),
            'username': os.environ.get('CYBERPANEL_2FA_TEST_USERNAME', ''),
            'token': os.environ.get('CYBERPANEL_2FA_TEST_TOKEN', ''),
            'secret': os.environ.get('CYBERPANEL_2FA_TEST_SECRET', ''),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            self.skipTest('Missing integration settings: %s' % ', '.join(missing))
        self.config = required

    def cloud_request(self, otp=None):
        headers = {
            'Authorization': self.config['token'],
            'Content-Type': 'application/json',
        }
        if otp:
            headers['X-CyberPanel-OTP'] = otp
        return requests.post(
            self.config['base_url'] + '/cloudAPI/',
            headers=headers,
            data=json.dumps({
                'controller': 'verifyLogin',
                'serverUserName': self.config['username'],
            }),
            timeout=20,
        )

    def standard_api_request(self, otp=None):
        headers = {
            'Authorization': self.config['token'],
            'Content-Type': 'application/json',
        }
        if otp:
            headers['X-CyberPanel-OTP'] = otp
        return requests.post(
            self.config['base_url'] + '/api/listPackage',
            headers=headers,
            data=json.dumps({'adminUser': self.config['username']}),
            timeout=20,
        )

    def test_token_requires_two_factor_for_api_and_session_handoff(self):
        without_otp = self.cloud_request()
        self.assertEqual(without_otp.status_code, 200)
        self.assertEqual(without_otp.json()['status'], 0)

        otp = pyotp.TOTP(self.config['secret']).now()
        with_otp = self.cloud_request(otp)
        self.assertEqual(with_otp.status_code, 200)
        self.assertEqual(with_otp.json()['status'], 1)

        standard_without_otp = self.standard_api_request()
        self.assertEqual(standard_without_otp.status_code, 200)
        self.assertEqual(standard_without_otp.json()['existsStatus'], 0)

        standard_with_otp = self.standard_api_request(pyotp.TOTP(self.config['secret']).now())
        self.assertEqual(standard_with_otp.status_code, 200)
        self.assertIsInstance(standard_with_otp.json(), list)

        session = requests.Session()
        access_url = self.config['base_url'] + '/cloudAPI/access'
        params = {
            'serverUserName': self.config['username'],
            'token': self.config['token'],
        }
        denied = session.get(access_url, params=params, allow_redirects=False, timeout=20)
        self.assertEqual(denied.status_code, 401)
        self.assertNotIn('cyberpanel_sessionid', session.cookies)

        allowed = session.get(
            access_url,
            params=params,
            headers={'X-CyberPanel-OTP': pyotp.TOTP(self.config['secret']).now()},
            allow_redirects=False,
            timeout=20,
        )
        self.assertEqual(allowed.status_code, 302)
        self.assertIn('cyberpanel_sessionid', session.cookies)
