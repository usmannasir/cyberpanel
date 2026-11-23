"""The scanner page says what has to be set up before a scan, free or paid, can start.

The page offered the server's free scans to a panel account with no
connected CyberMail or scanner account, and Quick scan then answered with an
alert such as "Failed to authenticate VPS for free scans" that named no
cause and no next step. These tests read the wording module and the page's
template; they need neither Django nor the network.
"""
import re
import unittest
from pathlib import Path

from aiScanner import prerequisites as p

ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / 'aiScanner' / 'templates' / 'aiScanner' / 'scanner.html'
MANAGER = ROOT / 'aiScanner' / 'aiScannerManager.py'
SCANNER_KEY = {'X-API-Key': 'cp_' + 'a' * 30}
CYBERMAIL_KEY = {'X-CP-API-Key': 'cpk_example'}


class Reasons(unittest.TestCase):

    def test_without_a_connected_account_every_step_needs_the_account_first(self):
        for headers in ({}, None):
            self.assertEqual(p.reason(headers, free=True), p.ACCOUNT_REQUIRED)
            self.assertEqual(p.reason(headers, free=False), p.ACCOUNT_REQUIRED)

    def test_with_an_account_a_refused_free_key_and_a_missing_payment_are_told_apart(self):
        for headers in (SCANNER_KEY, CYBERMAIL_KEY):
            self.assertEqual(p.reason(headers, free=True), p.SERVER_NOT_VERIFIED)
            self.assertEqual(p.reason(headers, free=False), p.PAYMENT_REQUIRED)


class Messages(unittest.TestCase):

    def test_an_administrator_is_told_what_is_missing_and_where_to_connect_it(self):
        text = p.message(p.ACCOUNT_REQUIRED, may_connect=True, free=True)
        self.assertIn('No CyberMail or scanner account is connected to your panel account', text)
        self.assertIn("this server's free scans can only be used through one", text)
        self.assertIn('open Email Delivery, choose Get Started Free and connect a CyberMail account', text)
        self.assertTrue(text.endswith('No scan was started.'), text)

    def test_a_paid_step_without_an_account_names_the_account_and_then_payment(self):
        text = p.message(p.ACCOUNT_REQUIRED, may_connect=True, free=False)
        self.assertIn('scans and payment set-up go through one', text)
        self.assertIn('then set up payment on this page', text)

    def test_a_user_who_cannot_open_email_delivery_is_sent_to_the_administrator(self):
        text = p.message(p.ACCOUNT_REQUIRED, may_connect=False, free=True)
        self.assertIn('No CyberMail or scanner account is connected', text)
        self.assertIn('only an administrator can open: ask the server administrator.', text)
        self.assertNotIn('choose Get Started Free', text)

    def test_a_refused_free_key_names_the_server_and_both_possible_causes(self):
        text = p.message(p.SERVER_NOT_VERIFIED, may_connect=True, free=True, server_ip='203.0.113.10')
        self.assertIn('free-scan key of this server (203.0.113.10)', text)
        self.assertIn('the account that owns this VPS', text)
        self.assertIn('try again in a few minutes', text)
        other = p.message(p.SERVER_NOT_VERIFIED, may_connect=False, free=True, server_ip='203.0.113.10')
        self.assertIn('ask the server administrator', other)
        self.assertNotIn('Email Delivery', other)

    def test_a_missing_payment_method_is_said_as_such(self):
        text = p.message(p.PAYMENT_REQUIRED, may_connect=True)
        self.assertIn('needs a payment method, and none is set up', text)
        self.assertNotIn('account is connected', text)

    def test_every_cause_has_its_own_sentence(self):
        sentences = {p.message(why, True, free) for why, free in (
            (p.ACCOUNT_REQUIRED, True), (p.ACCOUNT_REQUIRED, False), (p.SERVER_NOT_VERIFIED, True),
            (p.PAYMENT_REQUIRED, False))}
        sentences.add(p.message(p.ACCOUNT_REQUIRED, False, True))
        self.assertEqual(len(sentences), 5)
        for old in ('Scanner not configured', 'Payment not configured', 'Failed to authenticate VPS'):
            self.assertFalse(any(old in sentence for sentence in sentences), old)

    def test_only_a_refused_scan_says_that_no_scan_started(self):
        self.assertNotIn(p.NOTHING_STARTED, p.message(p.ACCOUNT_REQUIRED, True, scan=False))
        self.assertIn(p.NOTHING_STARTED, p.message(p.PAYMENT_REQUIRED, True, scan=True))


class Refusals(unittest.TestCase):

    def test_the_refusal_keeps_the_shape_the_page_reads_and_adds_the_cause(self):
        body = p.refusal(p.ACCOUNT_REQUIRED, True, free=True, account_url='/emailDelivery/')
        self.assertIs(body['success'], False)
        self.assertEqual(body['error'], p.message(p.ACCOUNT_REQUIRED, True, True))
        self.assertEqual(body['reason'], p.ACCOUNT_REQUIRED)
        self.assertEqual(body['account_url'], '/emailDelivery/')

    def test_the_place_to_connect_an_account_is_given_only_to_who_may_open_it(self):
        self.assertNotIn('account_url', p.refusal(p.ACCOUNT_REQUIRED, False, True, account_url='/emailDelivery/'))
        self.assertNotIn('account_url', p.refusal(p.ACCOUNT_REQUIRED, True, True, account_url=''))
        self.assertNotIn('account_url', p.refusal(p.PAYMENT_REQUIRED, True, False, account_url='/emailDelivery/'))
        self.assertIn('account_url', p.refusal(p.SERVER_NOT_VERIFIED, True, True, account_url='/emailDelivery/'))


class PageState(unittest.TestCase):

    def test_the_page_asks_for_an_account_only_when_none_is_connected(self):
        self.assertEqual(p.page_state({}, True, '/emailDelivery/'),
                         {'account_missing': True, 'account_setup_url': '/emailDelivery/'})
        self.assertEqual(p.page_state({}, False, '/emailDelivery/'),
                         {'account_missing': True, 'account_setup_url': ''})
        for headers in (SCANNER_KEY, CYBERMAIL_KEY):
            self.assertEqual(p.page_state(headers, True, '/emailDelivery/'),
                             {'account_missing': False, 'account_setup_url': ''})


class Page(unittest.TestCase):
    """The template offers the free scans, the scan and payment set-up as usable only with an account."""

    @classmethod
    def setUpClass(cls):
        cls.page = TEMPLATE.read_text()

    def block(self, start, end):
        first = self.page.index(start)
        return self.page[first:self.page.index(end, first)]

    def test_the_account_notice_names_what_is_missing_and_links_to_the_set_up(self):
        notice = self.block('{% if account_missing %}\n        <div class="scanner-section" id="scannerAccountRequired">',
                            '<!-- Payment Setup Section -->')
        self.assertIn('{% trans "Connect an account first" %}', notice)
        self.assertIn('no scan can start', notice)
        self.assertIn('{% if account_setup_url %}', notice)
        self.assertIn('href="{{ account_setup_url }}"', notice)
        self.assertIn('{% trans "Open Email Delivery" %}', notice)
        self.assertIn('ask the server administrator', notice)

    def test_the_scan_button_is_locked_until_an_account_is_connected(self):
        form = self.block('<form id="scanForm">', '</form>')
        locked = form.split('{% if account_missing %}')[1].split('{% elif')[0]
        self.assertIn('disabled', locked)
        self.assertIn('Connect an account first', locked)
        self.assertNotIn('type="submit"', locked)
        # The submit button follows only in the branches for a connected account.
        self.assertLess(form.index('{% if account_missing %}'), form.index('type="submit"'))

    def test_the_free_scan_offer_says_it_needs_the_account(self):
        offer = self.block('<h4>VPS Free Scans Available</h4>', '{% elif vps_info.is_vps')
        self.assertIn('{% if account_missing %}', offer)
        self.assertIn('They can be used once an account is connected', offer)

    def test_payment_set_up_is_offered_only_with_an_account(self):
        setup = self.block('<!-- Payment Setup Section -->', '<!-- VPS Free Scans Notice -->')
        locked = setup.split('{% if account_missing %}')[1].split('{% else %}')[0]
        self.assertIn('disabled', locked)
        self.assertNotIn('setupPayment()', locked)
        self.assertIn('onclick="setupPayment()"', setup.split('{% if account_missing %}')[1].split('{% else %}')[1])

    def test_the_script_shows_each_refusal_and_offers_the_set_up_page(self):
        helper = self.block('function showScannerRefusal(data)', 'function setupPayment()')
        self.assertIn('data.error', helper)
        self.assertIn("typeof data.account_url === 'string'", helper)
        self.assertIn(r'/^\/[A-Za-z0-9]/.test(data.account_url)', helper)
        self.assertIn('confirm(', helper)
        for start, end in (('function setupPayment()', "const scanForm"),
                           ("fetch('/aiscanner/start-scan/'", 'function refreshScanHistory()'),
                           ('function addPaymentMethod()', '// Auto-refresh scan history')):
            body = self.block(start, end)
            self.assertIn('showScannerRefusal(data);', body, start)
            self.assertNotIn("alert('Error: ' + data.error)", body, start)


class Manager(unittest.TestCase):
    """The refusals are worded where they were decided; no check is added, removed or moved."""

    @classmethod
    def setUpClass(cls):
        cls.source = MANAGER.read_text()

    def method(self, name):
        return self.source.split('    def %s(' % name)[1].split('\n    def ')[0]

    def test_each_former_vague_refusal_now_has_its_cause(self):
        start = self.method('startScan')
        self.assertIn("self.prerequisite_refusal(admin, currentACL, free=True, server_ip=server_ip) or\n"
                      "                        {'success': False, 'error': 'Failed to authenticate VPS for free scans'}",
                      start)
        self.assertEqual(start.count('self.prerequisite_refusal(admin, currentACL, free=False) or'), 2)
        self.assertIn('account_only=True', self.method('setupPayment'))
        self.assertEqual(self.method('addPaymentMethod').count('self.prerequisite_refusal('), 4)

    def test_the_wording_runs_only_after_a_refusal_was_decided(self):
        start = self.method('startScan')
        # The account is read for the wording only inside the branches that refuse.
        self.assertNotIn('saved_scanner_auth_headers', start)
        for line in start.splitlines():
            if 'prerequisite_refusal' in line:
                self.assertTrue(line.strip().startswith('return JsonResponse(') or line.strip().startswith('self.'),
                                line)

    def test_the_page_receives_the_account_state(self):
        self.assertIn('context.update(self.account_state(admin, currentACL))', self.method('scannerHome'))

    def test_only_an_administrator_is_sent_to_email_delivery(self):
        self.assertIn("return currentACL.get('admin') == 1", self.method('may_connect_account'))
        self.assertIn("reverse('emailDeliveryHome')", self.method('account_setup_url'))


if __name__ == '__main__':
    unittest.main()
