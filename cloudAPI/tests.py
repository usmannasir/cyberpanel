from types import SimpleNamespace
from unittest import mock

from django.core.cache import cache
from django.test import RequestFactory, SimpleTestCase
import pyotp

from cloudAPI.views import access
from plogical.securityUtils import generate_api_token, normalize_api_token


class Session(dict):
    def __init__(self):
        super().__init__()
        self.cycled = False
        self.saved = False
        self.expiry = None

    def cycle_key(self):
        self.cycled = True

    def set_expiry(self, expiry):
        self.expiry = expiry

    def save(self):
        self.saved = True


class CloudAccessSecurityTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.factory = RequestFactory()

    def tearDown(self):
        cache.clear()

    def request(self, username='owner', token='valid-token', remote_addr='192.0.2.10', otp=None):
        headers = {}
        if otp is not None:
            headers['HTTP_X_CYBERPANEL_OTP'] = otp
        request = self.factory.get(
            '/cloudAPI/access',
            {
                'serverUserName': username,
                'token': token,
                'redirect': '/websites/',
            },
            REMOTE_ADDR=remote_addr,
            HTTP_HOST='panel.example.com',
            **headers,
        )
        request.session = Session()
        return request

    @mock.patch('cloudAPI.views.Administrator.objects.get')
    def test_placeholder_token_cannot_create_session(self, get_admin):
        get_admin.return_value = SimpleNamespace(
            pk=7,
            api=1,
            state='ACTIVE',
            token='None',
        )
        request = self.request(token='None')

        response = access(request)

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('userID', request.session)
        self.assertEqual(response.content, b'Unauthorized access.')

    def test_unknown_disabled_and_invalid_accounts_have_same_response(self):
        cases = [
            mock.Mock(side_effect=Exception('missing account')),
            mock.Mock(return_value=SimpleNamespace(pk=7, api=0, state='ACTIVE', token='valid-token')),
            mock.Mock(return_value=SimpleNamespace(pk=7, api=1, state='ACTIVE', token='different-token')),
            mock.Mock(return_value=SimpleNamespace(pk=7, api=1, state='SUSPENDED', token='valid-token')),
        ]
        responses = []

        for index, get_admin in enumerate(cases):
            request = self.request(username='owner-%s' % index, remote_addr='192.0.2.%s' % (20 + index))
            with mock.patch('cloudAPI.views.Administrator.objects.get', get_admin):
                response = access(request)
            responses.append((response.status_code, response.content))

        self.assertEqual(len(set(responses)), 1)
        self.assertEqual(responses[0], (401, b'Unauthorized access.'))

    @mock.patch('cloudAPI.views.Administrator.objects.get')
    def test_successful_access_rotates_and_persists_session(self, get_admin):
        token = generate_api_token()
        get_admin.return_value = SimpleNamespace(
            pk=7,
            api=1,
            state='ACTIVE',
            token=token,
            twoFA=0,
            secretKey='None',
        )
        request = self.request(token='Bearer ' + normalize_api_token(token))

        response = access(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response['Location'], '/websites/')
        self.assertTrue(request.session.cycled)
        self.assertTrue(request.session.saved)
        self.assertEqual(request.session['userID'], 7)
        self.assertEqual(request.session['ipAddr'], '192.0.2.10')
        self.assertEqual(request.session.expiry, 43200)
        self.assertEqual(response['Cache-Control'], 'no-store')
        self.assertEqual(response['Referrer-Policy'], 'no-referrer')

    @mock.patch('cloudAPI.views.Administrator.objects.get')
    def test_two_factor_account_cannot_create_session_without_otp(self, get_admin):
        token = generate_api_token()
        get_admin.return_value = SimpleNamespace(
            pk=7,
            api=1,
            state='ACTIVE',
            token=token,
            twoFA=1,
            secretKey=pyotp.random_base32(),
        )

        request = self.request(token=token)
        response = access(request)

        self.assertEqual(response.status_code, 401)
        self.assertNotIn('userID', request.session)
        self.assertEqual(response.content, b'Two-factor authentication required.')

    @mock.patch('cloudAPI.views.Administrator.objects.get')
    def test_two_factor_account_accepts_token_and_current_otp(self, get_admin):
        token = generate_api_token()
        secret = pyotp.random_base32()
        get_admin.return_value = SimpleNamespace(
            pk=7,
            api=1,
            state='ACTIVE',
            token=token,
            twoFA=1,
            secretKey=secret,
        )

        request = self.request(token=token, otp=pyotp.TOTP(secret).now())
        response = access(request)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(request.session['userID'], 7)

    @mock.patch('cloudAPI.views.Administrator.objects.get')
    def test_repeated_failures_are_rate_limited(self, get_admin):
        get_admin.side_effect = Exception('missing account')

        for _ in range(10):
            response = access(self.request(username='missing'))
            self.assertEqual(response.status_code, 401)

        response = access(self.request(username='missing'))

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.content, b'Too many attempts. Try again later.')
        self.assertEqual(get_admin.call_count, 10)
