import json
from types import SimpleNamespace
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase

from plogical.clientIP import get_client_ip


class ClientIPTests(SimpleTestCase):

    def setUp(self):
        self.factory = RequestFactory()

    def client_ip(self, peer, forwarded, local_peer=None):
        meta = {'REMOTE_ADDR': peer, 'HTTP_CF_CONNECTING_IP': forwarded}
        if local_peer is not None:
            meta['HTTP_X_CYBERPANEL_PEER'] = local_peer
        return get_client_ip(self.factory.get('/', **meta))

    def test_spoofed_header_from_a_direct_client_is_ignored(self):
        self.assertEqual('203.0.113.5', self.client_ip('203.0.113.5', '8.8.8.8'))

    def test_header_from_cloudflare_is_used(self):
        self.assertEqual('198.51.100.7', self.client_ip('172.68.1.1', '198.51.100.7'))
        self.assertEqual('2001:db8::7', self.client_ip('2606:4700::1', '2001:db8::7'))

    def test_phpmyadmin_signin_passes_on_the_browser_address(self):
        # plogical/phpmyadminsignin.php validates panel sessions over loopback.
        self.assertEqual('203.0.113.5', self.client_ip('127.0.0.1', '', local_peer='203.0.113.5'))

    def test_phpmyadmin_signin_cannot_forward_a_spoofed_header(self):
        self.assertEqual('203.0.113.5', self.client_ip('127.0.0.1', '8.8.8.8', local_peer='203.0.113.5'))

    def test_phpmyadmin_signin_behind_cloudflare_uses_the_header(self):
        self.assertEqual('198.51.100.7', self.client_ip('::1', '198.51.100.7', local_peer='172.68.1.1'))

    def test_loopback_alone_does_not_make_the_header_trusted(self):
        self.assertEqual('127.0.0.1', self.client_ip('127.0.0.1', '8.8.8.8'))

    def test_only_loopback_callers_can_name_their_peer(self):
        self.assertEqual('203.0.113.5', self.client_ip('203.0.113.5', '198.51.100.7', local_peer='172.68.1.1'))

    def test_invalid_header_falls_back_to_the_peer(self):
        self.assertEqual('172.68.1.1', self.client_ip('172.68.1.1', '198.51.100.7, 10.0.0.1'))

    def test_request_without_header_uses_the_peer(self):
        self.assertEqual('203.0.113.5', get_client_ip(self.factory.get('/', REMOTE_ADDR='203.0.113.5')))

    @mock.patch('loginSystem.views.hashPassword.check_password', return_value=True)
    @mock.patch('loginSystem.views.Administrator.objects.get')
    def test_login_session_is_bound_to_the_real_peer(self, get, unused_check):
        from loginSystem.views import verifyLogin
        get.return_value = SimpleNamespace(pk=7, password='hash', state='ACTIVE', twoFA=0, secretKey='')
        request = self.factory.post(
            '/verifyLogin',
            data=json.dumps({'username': 'admin', 'password': 'secret'}),
            content_type='application/json',
            REMOTE_ADDR='203.0.113.5',
            HTTP_CF_CONNECTING_IP='8.8.8.8',
        )
        request.session = SessionStore()

        verifyLogin(request)

        self.assertEqual('203.0.113.5', request.session['ipAddr'])
