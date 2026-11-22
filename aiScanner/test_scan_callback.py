"""A scan ends once, with counts and a cost that are whole, decimal and never negative."""
import json
from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import RequestFactory, SimpleTestCase

from aiScanner import api, status_api


class Missing(Exception):
    pass


class ScanCallbackTests(SimpleTestCase):

    def setUp(self):
        self.owner = SimpleNamespace(pk=7, userName='owner')
        self.scan = mock.Mock(pk=3, scan_id='cp_0123456789ab', admin=self.owner, status='running',
                              cost_usd=None, issues_found=0, files_scanned=0)
        self.owner.ai_scanner_settings = self.settings = mock.Mock(
            pk=5, admin=self.owner, api_key='cp_key_of_the_owner', balance=Decimal('10.0000'))
        self.updates = []

        def scan_get(scan_id):
            if scan_id != self.scan.scan_id:
                raise Missing()
            return self.scan

        def scan_filter(**query):
            def update(**values):
                # The database changes the state only of a scan that is still under way.
                if self.scan.status not in query.get('status__in', ()):
                    return 0
                self.scan.status = values['status']
                return 1
            return SimpleNamespace(update=update)

        def settings_filter(**query):
            def update(**values):
                self.updates.append((query, values))
                return 1 if self.settings.balance >= query['balance__gte'] else 0
            return SimpleNamespace(update=update)

        scans = SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(get=scan_get, filter=scan_filter))
        settings = SimpleNamespace(DoesNotExist=Missing, objects=SimpleNamespace(
            get=lambda admin: self.settings, filter=settings_filter))
        self.status_updates = mock.Mock()
        self.status_updates.objects.get_or_create.return_value = (mock.Mock(), True)
        self.status_updates.objects.update_or_create.return_value = (mock.Mock(phase='x', progress=1), True)
        for target, value in (
                ('aiScanner.api.ScanHistory', scans), ('aiScanner.status_api.ScanHistory', scans),
                ('aiScanner.api.AIScannerSettings', settings), ('aiScanner.status_api.AIScannerSettings', settings),
                ('aiScanner.api.FileAccessToken', mock.Mock()), ('aiScanner.models.FileAccessToken', mock.Mock()),
                ('aiScanner.status_models.ScanStatusUpdate', self.status_updates),
                ('aiScanner.status_api.ScanStatusUpdate', self.status_updates),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def callback(self, key='cp_key_of_the_owner', **payload):
        data = {'scan_id': self.scan.scan_id, 'status': 'completed',
                'summary': {'threat_level': 'LOW', 'total_findings': 2, 'files_scanned': 25, 'cost': '$0.0456'},
                'findings': [{'severity': 'CRITICAL', 'title': 'a'}, {'severity': 'high', 'title': 'b'}]}
        data.update(payload)
        request = RequestFactory().post('/api/ai-scanner/callback', data=json.dumps(data),
                                        content_type='application/json', HTTP_X_API_KEY=key)
        response = api.scan_callback(request)
        return response.status_code, json.loads(response.content.decode('utf-8'))

    def test_the_first_result_ends_the_scan_and_charges_once(self):
        status, reply = self.callback()
        self.assertEqual((200, 'success'), (status, reply['status']))
        self.assertEqual(('completed', 2, 25, Decimal('0.045600')),
                         (self.scan.status, self.scan.issues_found, self.scan.files_scanned, self.scan.cost_usd))
        self.scan.save.assert_called_once_with()
        self.assertEqual(1, len(self.updates))
        self.assertEqual({'pk': 5, 'balance__gte': Decimal('0.045600')}, self.updates[0][0])
        # The same result again changes nothing and charges nothing.
        status, reply = self.callback(summary={'total_findings': 99, 'files_scanned': 99, 'cost': '$5.00'})
        self.assertEqual((200, 'Callback already processed'), (status, reply['message']))
        self.assertEqual(('completed', 2, 25), (self.scan.status, self.scan.issues_found, self.scan.files_scanned))
        self.scan.save.assert_called_once_with()
        self.assertEqual(1, len(self.updates))

    def test_a_scan_that_has_ended_cannot_be_changed(self):
        for ended in ('completed', 'failed', 'cancelled'):
            self.scan.status = ended
            self.assertEqual('Callback already processed', self.callback(status='failed')[1]['message'])
            self.assertEqual(ended, self.scan.status)
        self.scan.save.assert_not_called()
        self.assertEqual([], self.updates)

    def test_only_an_end_state_is_accepted(self):
        for state in ('running', 'pending', 'paid', '', None, 7, ['completed']):
            self.assertEqual(400, self.callback(status=state)[0])
        self.assertEqual('running', self.scan.status)
        self.scan.save.assert_not_called()

    def test_counts_and_cost_are_never_negative_or_malformed(self):
        self.callback(summary={'total_findings': -5, 'files_scanned': 'many', 'cost': '-$3.00'},
                      findings='none')
        self.assertEqual((0, 0, Decimal('0')), (self.scan.issues_found, self.scan.files_scanned, self.scan.cost_usd))
        self.assertEqual([], self.updates)
        self.assertEqual(Decimal('0'), api.money('NaN'))
        self.assertEqual(Decimal('0'), api.money('1e9'))
        self.assertEqual(Decimal('0'), api.money(None))
        self.assertEqual(Decimal('1234.500000'), api.money('$1,234.50'))
        self.assertEqual(0, api.whole_number(True))
        self.assertEqual(12, api.whole_number('12.9'))

    def test_a_failed_scan_is_not_charged(self):
        self.callback(status='failed')
        self.assertEqual(('failed', Decimal('0')), (self.scan.status, self.scan.cost_usd))
        self.assertEqual([], self.updates)

    def test_only_the_key_of_the_scans_owner_is_accepted(self):
        self.assertEqual(403, self.callback(key='cp_another_key')[0])
        self.settings.api_key = None
        self.assertEqual(403, self.callback(key='None')[0])
        self.assertEqual('running', self.scan.status)

    def test_status_updates_hold_bounded_whole_numbers(self):
        def update(**payload):
            data = {'scan_id': self.scan.scan_id, 'phase': 'scanning_files', 'progress': 40}
            data.update(payload)
            request = RequestFactory().post('/api/ai-scanner/status-webhook', data=json.dumps(data),
                                            content_type='application/json', HTTP_X_API_KEY='cp_key_of_the_owner')
            return status_api.receive_status_update(request).status_code

        self.assertEqual(200, update(progress=250, files_scanned=-4, threats_found='3'))
        defaults = self.status_updates.objects.update_or_create.call_args[1]['defaults']
        self.assertEqual((100, 0, 3), (defaults['progress'], defaults['files_scanned'], defaults['threats_found']))
        self.assertEqual(400, update(files_scanned='many'))
        self.assertEqual(400, update(files_scanned=None))
