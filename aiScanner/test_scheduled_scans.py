"""Scheduled scans store only checked values, are shown escaped, and need the scanner to be allowed."""
import json
import os
import re
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from aiScanner import scheduled_views, views

TEMPLATE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates', 'aiScanner', 'scanner.html')


class ScheduledScanTests(SimpleTestCase):

    def setUp(self):
        self.acl = {'admin': 0}
        self.admin = SimpleNamespace(pk=7)
        self.created = []
        self.scan_model = mock.Mock()
        self.scan_model.FREQUENCY_CHOICES = [('daily', 'Daily'), ('weekly', 'Weekly'), ('monthly', 'Monthly'),
                                             ('quarterly', 'Quarterly')]
        self.scan_model.SCAN_TYPE_CHOICES = [('full', 'Full Scan'), ('quick', 'Quick Scan'), ('custom', 'Custom Scan')]

        def new_scan(**fields):
            scan = mock.Mock(id=31, **fields)
            self.created.append((fields, scan))
            return scan

        self.scan_model.side_effect = new_scan
        websites = SimpleNamespace(objects=SimpleNamespace(filter=lambda admin: SimpleNamespace(
            values_list=lambda name, flat: ['example.com', 'example.org'])))
        for target, value in (
                ('aiScanner.models.ScheduledScan', self.scan_model),
                ('loginSystem.models.Administrator', SimpleNamespace(objects=SimpleNamespace(get=lambda pk: self.admin))),
                ('websiteFunctions.models.Websites', websites),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        patcher = mock.patch('plogical.acl.ACLManager.loadedACL', side_effect=lambda userID: self.acl)
        patcher.start()
        self.addCleanup(patcher.stop)

    def valid(self, **changes):
        data = {'name': 'Nightly check', 'domains': ['example.com'], 'frequency': 'weekly', 'scan_type': 'full',
                'time_of_day': '02:30', 'day_of_week': '3', 'day_of_month': '1',
                'notification_emails': ['owner@example.com'], 'email_notifications': True}
        data.update(changes)
        return data

    def create(self, data, session=None):
        request = RequestFactory().post('/aiscanner/scheduled-scans/', data=json.dumps(data),
                                        content_type='application/json')
        request.session = {'userID': 7} if session is None else session
        response = scheduled_views.scheduledScans(request)
        return response.status_code, json.loads(response.content.decode('utf-8'))

    def test_a_valid_scheduled_scan_is_stored(self):
        self.assertEqual((200, {'success': True, 'id': 31}), self.create(self.valid()))
        fields, scan = self.created[0]
        self.assertEqual(('Nightly check', 'weekly', 'full', 3, None),
                         (fields['name'], fields['frequency'], fields['scan_type'], fields['day_of_week'],
                          fields['day_of_month']))
        scan.set_domains.assert_called_once_with(['example.com'])
        scan.set_notification_emails.assert_called_once_with(['owner@example.com'])
        scan.save.assert_called_once_with()

    def test_values_outside_what_the_model_allows_are_refused(self):
        for changes in (
                {'name': '<img src=x onerror=alert(1)>'}, {'name': 'a"b'}, {'name': 'x' * 201}, {'name': ['x']},
                {'name': 'line\nbreak'},
                {'frequency': 'hourly'}, {'frequency': ['weekly']}, {'scan_type': 'deep'},
                {'domains': 'example.com'}, {'domains': [5]}, {'domains': ['example.com'] * 201},
                {'time_of_day': '25:00'}, {'time_of_day': 230},
                {'day_of_week': '7'}, {'day_of_week': '-1'}, {'day_of_week': None}, {'day_of_week': '1; drop'},
                {'frequency': 'monthly', 'day_of_month': '32'}, {'frequency': 'monthly', 'day_of_month': '0'},
                {'notification_emails': ['not an address']}, {'notification_emails': 'owner@example.com'},
                {'notification_emails': ['owner@example.com\nBcc: other@example.net']},
                {'notification_emails': ['a%d@example.com' % number for number in range(11)]},
        ):
            status, reply = self.create(self.valid(**changes))
            self.assertFalse(reply['success'], changes)
        self.assertEqual([], self.created)

    def test_a_domain_of_another_user_is_refused(self):
        status, reply = self.create(self.valid(domains=['example.com', 'other.example.net']))
        self.assertFalse(reply['success'])
        self.assertEqual([], self.created)

    def test_a_failure_shows_no_internal_text(self):
        self.scan_model.side_effect = RuntimeError('table ai_scanner_scheduled_scans is locked by 10.0.0.5')
        status, reply = self.create(self.valid())
        self.assertEqual({'success': False, 'error': 'Internal server error'}, reply)

    def test_scheduled_scans_need_a_session_and_the_scanner_switch(self):
        self.assertEqual((401, {'success': False, 'error': 'Not authenticated'}), self.create(self.valid(), session={}))
        self.acl = {'admin': 0, 'aiScannerAccess': 0}
        self.assertEqual((403, {'success': False, 'error': 'Access denied'}), self.create(self.valid()))
        self.assertEqual([], self.created)
        for view in (scheduled_views.scheduledScanDetail, scheduled_views.toggleScheduledScan,
                     scheduled_views.scheduledScanExecutions):
            request = RequestFactory().get('/aiscanner/scheduled-scans/1/')
            request.session = {'userID': 7}
            self.assertEqual(403, view(request, 1).status_code)

    def test_every_scanner_view_checks_the_scanner_switch(self):
        self.acl = {'admin': 0, 'aiScannerAccess': 0}
        for view, arguments in ((views.aiScannerHome, ()), (views.setupPayment, ()), (views.setupComplete, ()),
                                (views.startScan, ()), (views.refreshBalance, ()), (views.addPaymentMethod, ()),
                                (views.paymentMethodComplete, ()), (views.getScanHistory, ()),
                                (views.getScanDetails, ('cp_1',)), (views.getPlatformMonitorUrl, ('cp_1',)),
                                (views.getPlatformScanStatus, ('cp_1',))):
            request = RequestFactory().get('/aiscanner/')
            request.session = {'userID': 7}
            response = view(request, *arguments)
            self.assertTrue(response.status_code == 403 or b'not authorized' in response.content, view.__name__)

    def test_an_acl_made_before_the_switch_existed_keeps_access(self):
        from aiScanner.access import scanner_allowed
        self.assertTrue(scanner_allowed({'admin': 0}))
        self.assertTrue(scanner_allowed({'admin': 0, 'aiScannerAccess': 1}))
        self.assertTrue(scanner_allowed({'admin': 1, 'aiScannerAccess': 0}))
        self.assertFalse(scanner_allowed({'admin': 0, 'aiScannerAccess': 0}))

    def test_pausing_a_scheduled_scan_needs_the_csrf_token(self):
        self.assertFalse(getattr(scheduled_views.toggleScheduledScan, 'csrf_exempt', False))

    def test_the_page_escapes_what_users_typed(self):
        with open(TEMPLATE, encoding='utf-8') as handle:
            page = handle.read()
        start = page.index('function displayScheduledScans(scans)')
        block = page[start:page.index('function saveScheduledScan()', start)]
        raw = [value for value in re.findall(r'\$\{([^}]*)\}', block)
               if 'scan.' in value and not value.startswith('escapeHtml(') and "'" not in value]
        self.assertEqual([], raw)
        for field in ('scan.name', 'scan.status', 'scan.frequency', 'scan.scan_type'):
            self.assertIn('${escapeHtml(%s)}' % field, block)
        self.assertIn("escapeHtml((scan.domains || []).join(', '))", block)
        self.assertNotIn('${scan.id}', block)
        self.assertNotIn('[value="${domain}"]', page)
