"""A scanner key from the payment return address is stored only for the session that started the set-up."""
import time
from types import SimpleNamespace
from unittest import mock

from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase

from aiScanner import aiScannerManager
from aiScanner.aiScannerManager import AIScannerManager

KEY = 'cp_' + 'A1b2C3d4_-' * 4 + 'xyz'


class SetupCompleteTests(SimpleTestCase):

    def setUp(self):
        self.admin = SimpleNamespace(pk=7, userName='owner', email='owner@example.com')
        self.acl = {'admin': 0}
        self.settings = mock.Mock()
        self.settings.objects.get_or_create.return_value = (mock.Mock(), True)
        self.balance = 12.5
        for target, value in (
                ('aiScanner.aiScannerManager.Administrator',
                 SimpleNamespace(objects=SimpleNamespace(get=lambda pk: self.admin))),
                ('aiScanner.aiScannerManager.AIScannerSettings', self.settings),
                ('aiScanner.aiScannerManager.messages', mock.Mock()),
                ('aiScanner.aiScannerManager.redirect', lambda name: HttpResponse(name)),
        ):
            patcher = mock.patch(target, value)
            patcher.start()
            self.addCleanup(patcher.stop)
        for target, value in (
                ('plogical.acl.ACLManager.loadedACL', lambda userID: self.acl),
                ('plogical.acl.ACLManager.fetchIP', lambda: '203.0.113.10'),
                ('aiScanner.aiScannerManager.AIScannerManager.get_account_balance', lambda key: self.balance),
        ):
            patcher = mock.patch(target, side_effect=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.messages = aiScannerManager.messages

    def complete(self, session, **query):
        request = RequestFactory().get('/aiscanner/setup-complete/', query)
        request.session = session
        response = AIScannerManager().setupComplete(request, 7)
        return response

    def stored(self):
        calls = self.settings.objects.update_or_create.call_args_list + self.settings.objects.get_or_create.call_args_list
        return [call[1] for call in calls]

    def test_a_key_is_refused_when_this_session_started_no_set_up(self):
        self.complete({}, status='success', api_key=KEY, balance='999')
        self.complete({}, status='partial_success', api_key=KEY)
        self.assertEqual([], self.stored())
        self.assertEqual(2, self.messages.error.call_count)
        self.messages.success.assert_not_called()

    def test_the_session_that_started_the_set_up_gets_its_key_once(self):
        session = {'aiScannerSetupStarted': int(time.time()) - 60}
        self.complete(session, status='success', api_key=KEY, balance='999', charged='true', amount='10')
        self.assertEqual([{'admin': self.admin,
                           'defaults': {'api_key': KEY, 'is_payment_configured': True, 'balance': 12.5}}],
                         self.stored())
        self.assertNotIn('aiScannerSetupStarted', session)
        self.messages.success.assert_called_once()
        # The same return address a second time stores nothing.
        self.complete(session, status='success', api_key='cp_' + 'B' * 43)
        self.assertEqual(1, len(self.stored()))

    def test_the_balance_in_the_address_is_never_stored(self):
        self.balance = None
        self.complete({'aiScannerSetupStarted': int(time.time())}, status='success', api_key=KEY, balance='999')
        self.assertEqual([{'admin': self.admin, 'defaults': {'api_key': KEY, 'is_payment_configured': True}}],
                         self.stored())

    def test_a_set_up_started_too_long_ago_is_refused(self):
        self.complete({'aiScannerSetupStarted': int(time.time()) - 3601}, status='success', api_key=KEY)
        self.complete({'aiScannerSetupStarted': int(time.time()) + 600}, status='success', api_key=KEY)
        self.complete({'aiScannerSetupStarted': 'yes'}, status='success', api_key=KEY)
        self.assertEqual([], self.stored())

    def test_something_that_is_no_scanner_key_is_refused(self):
        for key in ('', 'not-a-key', 'cp_short', 'cp_' + 'a' * 43 + '<script>', 'cp_' + 'a' * 300):
            self.complete({'aiScannerSetupStarted': int(time.time())}, status='success', api_key=key)
        self.assertEqual([], self.stored())

    def test_a_failed_set_up_uses_the_marker_up_and_shows_no_text_from_the_address(self):
        session = {'aiScannerSetupStarted': int(time.time())}
        self.complete(session, status='failed', error='<b>call 555-0100</b>')
        self.assertNotIn('aiScannerSetupStarted', session)
        self.assertEqual('Payment setup failed or was cancelled.', self.messages.error.call_args[0][1])
        self.assertEqual([], self.stored())

    def test_a_user_whose_acl_switches_the_scanner_off_stores_nothing(self):
        self.acl = {'admin': 0, 'aiScannerAccess': 0}
        session = {'aiScannerSetupStarted': int(time.time())}
        self.complete(session, status='success', api_key=KEY)
        self.assertEqual([], self.stored())

    def test_starting_the_set_up_marks_the_session(self):
        request = RequestFactory().post('/aiscanner/setup-payment/', HTTP_HOST='203.0.113.10:8090')
        request.session = {}
        with mock.patch.object(AIScannerManager, 'setup_ai_scanner_payment',
                               return_value={'payment_url': 'https://platform.cyberpersons.com/pay', 'token': 't'}) as setup:
            before = int(time.time())
            AIScannerManager().setupPayment(request, 7)
        self.assertGreaterEqual(request.session['aiScannerSetupStarted'], before)
        # The browser comes back to the address it used: that is where its session is.
        self.assertEqual('203.0.113.10:8090', setup.call_args[0][1])
