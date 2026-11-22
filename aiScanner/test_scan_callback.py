"""A scan ends once, with counts and a cost that are whole, decimal and never negative."""
import json
import time
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
                              cost_usd=None, issues_found=0, files_scanned=0, completed_at=None)
        self.owner.ai_scanner_settings = self.settings = mock.Mock(
            pk=5, admin=self.owner, api_key='cp_key_of_the_owner', balance=Decimal('10.0000'))
        self.updates = []

        def scan_get(scan_id):
            if scan_id != self.scan.scan_id:
                raise Missing()
            return self.scan

        def scan_filter(**query):
            self.assertEqual({'pk': 3, 'completed_at__isnull': True}, query)

            def exclude(**excluded):
                def update(**values):
                    # The database ends only a scan that has no result yet.
                    if self.scan.completed_at is not None or self.scan.status in excluded['status__in']:
                        return 0
                    self.scan.status = values['status']
                    self.scan.completed_at = values['completed_at']
                    return 1
                return SimpleNamespace(update=update)
            return SimpleNamespace(exclude=exclude)

        test = self

        class Atomic(object):
            """What a transaction does to the scan: everything, or nothing when it ends in an error."""

            def __enter__(self):
                test.transactions += 1
                self.before = (test.scan.status, test.scan.completed_at)

            def __exit__(self, kind, error, trace):
                if kind is not None:
                    test.scan.status, test.scan.completed_at = self.before
                return False

        self.transactions = 0

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
                ('aiScanner.api.transaction', SimpleNamespace(atomic=Atomic)),
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
        import datetime
        for ended, at in (('completed', datetime.datetime(2026, 1, 1)), ('failed', datetime.datetime(2026, 1, 1)),
                          ('cancelled', datetime.datetime(2026, 1, 1)), ('completed', None), ('cancelled', None)):
            self.scan.status, self.scan.completed_at = ended, at
            self.assertEqual('Callback already processed', self.callback(status='failed')[1]['message'])
            self.assertEqual('Callback already processed', self.callback()[1]['message'])
            self.assertEqual((ended, at), (self.scan.status, self.scan.completed_at))
        self.scan.save.assert_not_called()
        self.assertEqual([], self.updates)

    def test_a_result_ends_a_scan_this_panel_gave_up_on_at_the_start(self):
        # The platform took the scan but answered late: the panel marked it failed and stored no result.
        self.scan.status = 'failed'
        status, reply = self.callback()
        self.assertEqual((200, 'Callback received successfully'), (status, reply['message']))
        self.assertEqual(('completed', 2, 25, Decimal('0.045600')),
                         (self.scan.status, self.scan.issues_found, self.scan.files_scanned, self.scan.cost_usd))
        self.assertIsNotNone(self.scan.completed_at)
        self.scan.save.assert_called_once_with()
        self.assertEqual(1, len(self.updates))
        # And only once.
        self.assertEqual('Callback already processed', self.callback()[1]['message'])
        self.scan.save.assert_called_once_with()
        self.assertEqual(1, len(self.updates))

    def test_a_result_that_cannot_be_stored_does_not_end_the_scan(self):
        self.scan.save.side_effect = [RuntimeError('database went away'), None]
        status, reply = self.callback()
        self.assertEqual((500, 'Failed to update scan record'), (status, reply['message']))
        self.assertEqual(('running', None), (self.scan.status, self.scan.completed_at))
        self.assertEqual([], self.updates)
        self.status_updates.objects.get_or_create.assert_not_called()
        # The platform reports again and the result is stored.
        status, reply = self.callback()
        self.assertEqual((200, 'Callback received successfully'), (status, reply['message']))
        self.assertEqual(('completed', 2, 25), (self.scan.status, self.scan.issues_found, self.scan.files_scanned))
        self.assertEqual(1, len(self.updates))
        self.assertEqual(2, self.transactions)

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
        self.assertEqual(Decimal('0'), api.money('1e-3'))
        self.assertEqual(Decimal('0'), api.money('9' * 41))
        self.assertEqual(Decimal('0'), api.money(10 ** 400))
        self.assertEqual(Decimal('0'), api.money(float('inf')))
        self.assertEqual(Decimal('0'), api.money(True))
        self.assertEqual(Decimal('0'), api.money(['1']))
        self.assertEqual(Decimal('0'), api.money('10000'))
        self.assertEqual(Decimal('0.045600'), api.money(0.0456))
        self.assertEqual(Decimal('3.000000'), api.money(3))
        self.assertEqual(Decimal('0.000001'), api.money(' $0.000001 '))

    def test_a_count_is_a_number_or_a_few_digits_and_nothing_is_built_from_longer_text(self):
        for value, expected in ((12, 12), ('12', 12), (' 0042 ', 42), (0, 0), (-5, 0), (10 ** 30, 2147483647),
                                ('9999999999', 2147483647), ('12.9', 0), (12.9, 0), ('1e3', 0), ('1e1000000', 0),
                                ('1E1000000', 0), ('9' * 11, 0), ('9' * 5000000, 0), ('-3', 0), ('+3', 0),
                                ('٣', 0), ('', 0), (None, 0), (True, 0), ([3], 0), ({'a': 1}, 0),
                                (float('inf'), 0), (float('nan'), 0)):
            self.assertEqual(expected, api.whole_number(value), repr(value)[:40])
        started = time.time()
        self.callback(summary={'total_findings': '1e1000000', 'files_scanned': '1E999999999', 'cost': '1e1000000'})
        self.assertLess(time.time() - started, 2)
        self.assertEqual((0, 0, Decimal('0')), (self.scan.issues_found, self.scan.files_scanned, self.scan.cost_usd))

    def test_a_failed_scan_is_not_charged(self):
        self.callback(status='failed')
        self.assertEqual(('failed', Decimal('0')), (self.scan.status, self.scan.cost_usd))
        self.assertEqual([], self.updates)

    def test_only_the_key_of_the_scans_owner_is_accepted(self):
        self.assertEqual(403, self.callback(key='cp_another_key')[0])
        # A key with characters outside ASCII is a wrong key, not an error.
        self.assertEqual(403, self.callback(key='cp_key_of_the_owner\xe9')[0])
        self.assertEqual(403, self.callback(key='\xff\xfe')[0])
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
        for value in ('1e1000000', '9' * 11, '9' * 100000, '-4', '3.5', True, [1], 1e400):
            self.assertEqual(400, update(threats_found=value), repr(value)[:30])
        self.assertEqual(200, update(progress=45.7, files_scanned=' 12 ', threats_found=10 ** 30))
        defaults = self.status_updates.objects.update_or_create.call_args[1]['defaults']
        self.assertEqual((45, 12, 2147483647),
                         (defaults['progress'], defaults['files_scanned'], defaults['threats_found']))

    def test_a_status_update_with_a_key_outside_ascii_is_refused_as_a_wrong_key(self):
        request = RequestFactory().post(
            '/api/ai-scanner/status-webhook', data=json.dumps({'scan_id': self.scan.scan_id}),
            content_type='application/json', HTTP_X_API_KEY='cl\xe9')
        self.assertEqual(403, status_api.receive_status_update(request).status_code)
