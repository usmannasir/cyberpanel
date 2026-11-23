"""A refused scan or payment set-up says its cause, and the page knows whether an account is connected.

These tests run the scanner's views with stand-ins for the database, the
platform and the server's address. They need the panel's Django settings,
so they run with the panel's test runner on a QA server.
"""
import json
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from aiScanner.aiScannerManager import AIScannerManager

FREE_SCANS = {'success': True, 'is_vps': True, 'has_free_scans': True, 'free_scans_available': 10}


class Missing(Exception):
    pass


class ScanPrerequisiteTests(SimpleTestCase):

    def setUp(self):
        self.admin = SimpleNamespace(pk=7, userName='owner', email='owner@example.com')
        self.acl = {'admin': 1}
        self.headers = {}
        self.settings = SimpleNamespace(is_payment_configured=False, api_key='', balance=0)
        for target, value in (
                ('plogical.acl.ACLManager.loadedACL', lambda userID: self.acl),
                ('plogical.acl.ACLManager.fetchIP', lambda: '203.0.113.10'),
                ('plogical.acl.ACLManager.findWebsiteObjects', lambda acl, userID: []),
                ('aiScanner.aiScannerManager.saved_scanner_auth_headers', lambda admin: self.headers),
                ('aiScanner.aiScannerManager.reverse', lambda name: '/emailDelivery/'),
        ):
            patcher = mock.patch(target, side_effect=value, create=True)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, value in (
                ('aiScanner.aiScannerManager.Administrator',
                 SimpleNamespace(objects=SimpleNamespace(get=lambda pk: self.admin))),
                ('aiScanner.aiScannerManager.AIScannerSettings', SimpleNamespace(
                    DoesNotExist=Missing, objects=SimpleNamespace(
                        get=lambda admin: self.settings,
                        get_or_create=lambda admin, defaults: (self.settings, False)))),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch('aiScanner.aiScannerManager.ScanHistory')
        self.scans = patcher.start()
        self.addCleanup(patcher.stop)
        self.scans.SCAN_TYPE_CHOICES = [('full', 'Full Scan'), ('quick', 'Quick Scan')]

    def start_scan(self, vps_info, vps_key=None):
        manager = AIScannerManager()
        request = RequestFactory().post('/aiscanner/start-scan/',
                                        data=json.dumps({'domain': 'shop.example.org', 'scan_type': 'quick'}),
                                        content_type='application/json')
        request.session = {'userID': 7}
        with mock.patch.object(manager, 'check_vps_free_scans', return_value=vps_info), \
                mock.patch.object(manager, 'get_or_create_vps_api_key', return_value=vps_key), \
                mock.patch.object(manager, 'submit_wordpress_scan') as submit:
            body = json.loads(manager.startScan(request, 7).content.decode('utf-8'))
        submit.assert_not_called()
        self.scans.objects.create.assert_not_called()
        return body

    def test_a_free_scan_without_an_account_says_so_and_where_to_connect_it(self):
        body = self.start_scan(FREE_SCANS)
        self.assertIs(body['success'], False)
        self.assertEqual(body['reason'], 'account_required')
        self.assertIn('No CyberMail or scanner account is connected to your panel account', body['error'])
        self.assertIn('Get Started Free', body['error'])
        self.assertIn('No scan was started.', body['error'])
        self.assertEqual(body['account_url'], '/emailDelivery/')

    def test_a_user_who_is_no_administrator_is_sent_to_the_administrator(self):
        self.acl = {'admin': 0}
        body = self.start_scan(FREE_SCANS)
        self.assertEqual(body['reason'], 'account_required')
        self.assertIn('ask the server administrator', body['error'])
        self.assertNotIn('account_url', body)

    def test_a_free_key_the_platform_refused_to_a_connected_account_names_the_server(self):
        self.headers = {'X-CP-API-Key': 'cpk_example'}
        body = self.start_scan(FREE_SCANS)
        self.assertEqual(body['reason'], 'server_not_verified')
        self.assertIn('203.0.113.10', body['error'])

    def test_a_paid_scan_without_an_account_or_without_payment_is_told_apart(self):
        body = self.start_scan({'success': False})
        self.assertEqual(body['reason'], 'account_required')
        self.headers = {'X-CP-API-Key': 'cpk_example'}
        body = self.start_scan({'success': False})
        self.assertEqual(body['reason'], 'payment_required')
        self.assertIn('needs a payment method', body['error'])

    def test_payment_set_up_without_an_account_says_so(self):
        manager = AIScannerManager()
        request = RequestFactory().post('/aiscanner/setup-payment/', HTTP_HOST='panel.example.net:8090')
        request.session = {'userID': 7}
        with mock.patch.object(manager, 'setup_ai_scanner_payment', return_value=None):
            body = json.loads(manager.setupPayment(request, 7).content.decode('utf-8'))
        self.assertEqual(body['reason'], 'account_required')
        self.assertNotIn('No scan was started.', body['error'])

    def test_a_payment_set_up_that_failed_for_another_cause_keeps_its_message(self):
        self.headers = {'X-API-Key': 'cp_' + 'a' * 30}
        manager = AIScannerManager()
        request = RequestFactory().post('/aiscanner/setup-payment/', HTTP_HOST='panel.example.net:8090')
        request.session = {'userID': 7}
        with mock.patch.object(manager, 'setup_ai_scanner_payment', return_value=None):
            body = json.loads(manager.setupPayment(request, 7).content.decode('utf-8'))
        self.assertEqual(body, {'success': False, 'error': 'Failed to setup payment. Please check the logs and try again.'})

    def test_the_page_is_told_whether_an_account_is_connected(self):
        manager = AIScannerManager()
        request = RequestFactory().get('/aiscanner/')
        request.session = {'userID': 7}
        seen = {}

        def render(request, template, context):
            seen.update(context)
            return 'page'

        with mock.patch('aiScanner.aiScannerManager.render', side_effect=render), \
                mock.patch.object(manager, 'get_ai_scanner_pricing', return_value=None), \
                mock.patch.object(manager, 'check_vps_free_scans', return_value=FREE_SCANS):
            manager.scannerHome(request, 7)
            self.assertIs(seen['account_missing'], True)
            self.assertEqual(seen['account_setup_url'], '/emailDelivery/')
            self.headers = {'X-CP-API-Key': 'cpk_example'}
            manager.scannerHome(request, 7)
            self.assertIs(seen['account_missing'], False)
            self.assertEqual(seen['account_setup_url'], '')
