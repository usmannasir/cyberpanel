import json
import os
import shutil
import tempfile
from types import SimpleNamespace
from unittest import mock

from django.contrib.sessions.backends.signed_cookies import SessionStore
from django.test import RequestFactory, SimpleTestCase

from plogical import clientIP
from plogical.clientIP import get_client_ip


class CloudflareFileTestCase(SimpleTestCase):
    """Points CLOUDFLARE_IPS_FILE at a temporary directory."""

    def setUp(self):
        self.factory = RequestFactory()
        self.tempdir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tempdir)
        self.path = os.path.join(self.tempdir, 'cloudflare-ips.txt')
        patcher = mock.patch.object(clientIP, 'CLOUDFLARE_IPS_FILE', self.path)
        patcher.start()
        self.addCleanup(patcher.stop)
        clientIP._saved.update(mtime=None, networks=clientIP.BUILTIN_CLOUDFLARE_NETWORKS)

    def write(self, text):
        with open(self.path, 'w') as handle:
            handle.write(text)


class ClientIPTests(CloudflareFileTestCase):

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


PUBLISHED = '\n'.join('192.0.%d.0/24' % index for index in range(12)) + '\n'


class CloudflareIPsFileTests(CloudflareFileTestCase):

    def test_saved_list_replaces_the_builtin_one(self):
        self.write(PUBLISHED)

        self.assertTrue(clientIP.is_cloudflare_ip('192.0.5.9'))
        self.assertFalse(clientIP.is_cloudflare_ip('172.68.1.1'))

    def test_missing_or_invalid_file_falls_back_to_the_builtin_list(self):
        self.assertTrue(clientIP.is_cloudflare_ip('172.68.1.1'))

        for text in ('<html>error</html>\n', '192.0.2.0/24\n', ''):
            with self.subTest(text=text):
                self.write(text)
                os.utime(self.path, (1, len(text) + 1))
                self.assertTrue(clientIP.is_cloudflare_ip('172.68.1.1'))
                self.assertFalse(clientIP.is_cloudflare_ip('192.0.2.9'))

    def test_refresh_saves_both_published_lists(self):
        responses = {
            clientIP.CLOUDFLARE_IPS_URLS[0]: mock.Mock(text='\n'.join(PUBLISHED.splitlines()[:10])),
            clientIP.CLOUDFLARE_IPS_URLS[1]: mock.Mock(text='2606:4700::/32\n2400:cb00::/32'),
        }

        with mock.patch('requests.get', side_effect=lambda url, timeout: responses[url]):
            self.assertEqual(12, clientIP.refresh_cloudflare_ips())

        self.assertTrue(clientIP.is_cloudflare_ip('2606:4700::1'))
        self.assertTrue(clientIP.is_cloudflare_ip('192.0.9.1'))
        self.assertEqual(['cloudflare-ips.txt'], os.listdir(self.tempdir))
        if os.name == 'posix':
            self.assertEqual(0o644, os.stat(self.path).st_mode & 0o777)

    def test_bad_download_keeps_the_previous_list(self):
        self.write(PUBLISHED)

        with mock.patch('requests.get', return_value=mock.Mock(text='<html>maintenance</html>')):
            with self.assertRaises(ValueError):
                clientIP.refresh_cloudflare_ips()

        self.assertEqual(PUBLISHED, open(self.path).read())
        self.assertEqual(['cloudflare-ips.txt'], os.listdir(self.tempdir))
