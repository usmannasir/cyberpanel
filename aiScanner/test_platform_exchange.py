"""What goes to the log and to the browser from the panel's exchange with the scanner platform."""
from unittest import mock

from django.test import SimpleTestCase

from aiScanner import aiScannerManager
from aiScanner.aiScannerManager import AIScannerManager

TOKEN = 'cp_file_token_SECRETSECRETSECRETSECRET'
KEY = 'cp_api_key_SECRETSECRETSECRETSECRETSEC'


def reply(payload, status=200):
    response = mock.Mock(status_code=status, text=str(payload))
    response.json.return_value = payload
    return response


class PlatformExchangeTests(SimpleTestCase):

    def setUp(self):
        self.manager = AIScannerManager()
        self.manager.logger = mock.Mock()
        patcher = mock.patch('aiScanner.aiScannerManager.requests')
        self.requests = patcher.start()
        self.addCleanup(patcher.stop)

    def logged(self):
        return ' '.join(str(call) for call in self.manager.logger.writeToFile.call_args_list)

    def test_no_token_key_or_reply_body_reaches_the_log(self):
        self.requests.post.return_value = reply({'success': True, 'scan_id': 'p1', 'echo': TOKEN})
        self.manager.submit_wordpress_scan(KEY, 'example.com', 'full', 'https://203.0.113.10:8090/api/ai-scanner/callback',
                                           TOKEN, 'https://203.0.113.10:8090/api/ai-scanner/', 'cp_1', '203.0.113.10')
        self.requests.get.return_value = reply({'success': True, 'balance_usd': 4321.75})
        self.assertEqual(4321.75, self.manager.get_account_balance(KEY))
        self.requests.post.return_value = reply({'success': True, 'setup_url': 'https://platform.cyberpersons.com/x',
                                                 'token': TOKEN})
        self.manager.setup_add_payment_method(KEY, 'owner@example.com', '203.0.113.10:8090')
        logged = self.logged()
        self.assertNotIn(TOKEN, logged)
        self.assertNotIn(KEY, logged)
        self.assertNotIn(KEY[:20], logged)
        self.assertNotIn('4321.75', logged)

    def test_the_browser_is_sent_only_to_https_pages_of_the_platform(self):
        from aiScanner.platform_auth import platform_page_url
        self.assertEqual('https://platform.cyberpersons.com/ai-scanner/cyberpanel/payment-setup/t/',
                         platform_page_url('https://platform.cyberpersons.com/ai-scanner/cyberpanel/payment-setup/t/'))
        self.assertEqual('https://platform.cyberpersons.com/a?b=c', platform_page_url('http://platform.cyberpersons.com/a?b=c'))
        for url in ('javascript:alert(1)', 'https://platform.cyberpersons.com.example.net/a', 'https://example.net/a',
                    'https://platform.cyberpersons.com@example.net/a', 'https://example.net\\@platform.cyberpersons.com/',
                    '//platform.cyberpersons.com/a', 'data:text/html,x', 'https://platform.cyberpersons.com:8443/a',
                    ' https://platform.cyberpersons.com/a', 'https://platform.cyberpersons.com/a\nb', '', None, 5):
            self.assertIsNone(platform_page_url(url), url)

    def test_an_address_outside_the_platform_is_not_handed_to_the_page(self):
        with mock.patch('aiScanner.aiScannerManager.scanner_payment_setup_request',
                        return_value=({'domain': 'x'}, {'X-API-Key': KEY})):
            self.requests.post.return_value = reply({'success': True, 'payment_url': 'javascript:alert(1)', 'token': 't'})
            self.assertIsNone(self.manager.setup_ai_scanner_payment('owner@example.com', '203.0.113.10:8090'))
            self.requests.post.return_value = reply({'success': True, 'payment_url': 'https://example.net/pay', 'token': 't'})
            self.assertIsNone(self.manager.setup_ai_scanner_payment('owner@example.com', '203.0.113.10:8090'))
            self.requests.post.return_value = reply({
                'success': True, 'payment_url': 'https://platform.cyberpersons.com/ai-scanner/pay/', 'token': 't'})
            self.assertEqual({'payment_url': 'https://platform.cyberpersons.com/ai-scanner/pay/', 'token': 't'},
                             self.manager.setup_ai_scanner_payment('owner@example.com', '203.0.113.10:8090'))
        self.requests.post.return_value = reply({'success': True, 'setup_url': 'https://example.net/card'})
        self.assertIsNone(self.manager.setup_add_payment_method(KEY, 'owner@example.com', '203.0.113.10:8090'))
