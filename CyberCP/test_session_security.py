import json
from types import SimpleNamespace
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from CyberCP.secMiddleware import secMiddleware
from CyberCP.sessionSecurity import session_ip_key, session_ip_matches
from loginSystem.views import verifyLogin


class SessionIPTests(SimpleTestCase):
    def test_canonical_ipv6_prefix_and_privacy_addresses(self):
        self.assertEqual(session_ip_key('2001:0DB8:0000:12::1'),
                         session_ip_key('2001:db8:0:ffff::2'))
        self.assertTrue(session_ip_matches('2001:db8:0', '2001:db8::3'))
        self.assertFalse(session_ip_matches('2001:db8:0', '2001:db8:1::3'))

    def test_mapped_ipv4_matches_native_ipv4(self):
        self.assertEqual('192.0.2.1', session_ip_key('::ffff:192.0.2.1'))
        self.assertEqual('192.0.2.1', session_ip_key('::ffff:c000:201'))
        self.assertTrue(session_ip_matches('192.0.2.1', '::ffff:c000:201'))
        self.assertFalse(session_ip_matches('192.0.2.1', '::ffff:192.0.2.2'))

    def test_missing_invalid_and_ambiguous_legacy_bindings_do_not_match(self):
        for stored, address in ((None, '192.0.2.1'), ('192.0.2.1', None),
                                ('', ''), ('::ffff', '::ffff:192.0.2.1'),
                                ('2001::', '2001::1'), ('bad', 'bad')):
            self.assertFalse(session_ip_matches(stored, address))

    def request(self, path, address, session, method='get', data=None):
        factory = RequestFactory()
        if method == 'post':
            request = factory.post(path, json.dumps(data or {}),
                                   content_type='application/json', REMOTE_ADDR=address)
        else:
            request = factory.get(path, REMOTE_ADDR=address)
        request.session = session
        return request

    @mock.patch('CyberCP.secMiddleware.Administrator.objects.get')
    def test_high_rejects_changed_address_low_allows_it(self, get_admin):
        middleware = secMiddleware(lambda request: HttpResponse('ok'))
        for level, expected in ((secMiddleware.HIGH, 302), (secMiddleware.LOW, 200)):
            get_admin.return_value = SimpleNamespace(securityLevel=level)
            session = SessionStore()
            session.update({'userID': 7, 'ipAddr': '192.0.2.1'})
            response = middleware(self.request('/base/', '198.51.100.2', session))
            self.assertEqual(expected, response.status_code)
            if level == secMiddleware.HIGH:
                self.assertEqual('/', response['Location'])
                self.assertNotIn('userID', session)
            else:
                self.assertEqual(7, session['userID'])

    @mock.patch('CyberCP.secMiddleware.Administrator.objects.get')
    def test_changed_ip_post_returns_actionable_error(self, get_admin):
        get_admin.return_value = SimpleNamespace(securityLevel=secMiddleware.HIGH)
        session = SessionStore()
        session.update({'userID': 7, 'ipAddr': '192.0.2.1'})
        response = secMiddleware(lambda request: HttpResponse('must-not-run'))(
            self.request('/websites/action', '198.51.100.2', session, 'post'))
        payload = json.loads(response.content)
        self.assertTrue(payload['sessionExpired'])
        self.assertIn('LOW Security Level', payload['error_message'])
        self.assertNotIn('userID', session)

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('CyberCP.secMiddleware.Administrator.objects.get')
    def test_login_then_dashboard_accepts_equivalent_address_forms(self, get_admin, check):
        get_admin.return_value = SimpleNamespace(pk=7, password='hash', state='ACTIVE',
            twoFA=False, securityLevel=secMiddleware.HIGH)
        for login_ip, dashboard_ip in (
            ('::ffff:192.0.2.1', '192.0.2.1'),
            ('2001:0DB8:0000:12::1', '2001:db8::2'),
        ):
            session = SessionStore()
            response = secMiddleware(verifyLogin)(self.request('/verifyLogin', login_ip,
                session, 'post', {'username': 'admin', 'password': 'test'}))
            self.assertEqual(1, json.loads(response.content)['loginStatus'])
            response = secMiddleware(lambda request: HttpResponse('dashboard'))(
                self.request('/base/', dashboard_ip, session))
            self.assertEqual(b'dashboard', response.content)

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('CyberCP.secMiddleware.Administrator.objects.get')
    def test_stale_session_allows_same_login_attempt(self, get_admin, check):
        get_admin.return_value = SimpleNamespace(pk=7, password='hash', state='ACTIVE',
            twoFA=False, securityLevel=secMiddleware.HIGH)
        session = SessionStore()
        session.update({'userID': 99, 'ipAddr': '192.0.2.1'})
        response = secMiddleware(verifyLogin)(self.request('/verifyLogin', '198.51.100.2',
            session, 'post', {'username': 'admin', 'password': 'test'}))
        self.assertEqual(1, json.loads(response.content)['loginStatus'])
        self.assertEqual(7, session['userID'])
        self.assertEqual('198.51.100.2', session['ipAddr'])
        check.assert_called_once()

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=False)
    @mock.patch('CyberCP.secMiddleware.Administrator.objects.get')
    def test_stale_session_cannot_bypass_password_validation(self, get_admin, check):
        get_admin.return_value = SimpleNamespace(pk=7, password='hash', state='ACTIVE',
            twoFA=False, securityLevel=secMiddleware.HIGH)
        session = SessionStore()
        session.update({'userID': 99, 'ipAddr': '192.0.2.1'})
        response = secMiddleware(verifyLogin)(self.request('/verifyLogin', '198.51.100.2',
            session, 'post', {'username': 'admin', 'password': 'wrong'}))
        self.assertEqual(0, json.loads(response.content)['loginStatus'])
        self.assertNotIn('userID', session)
