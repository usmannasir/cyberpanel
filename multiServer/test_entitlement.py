"""The licence check: one feature, strict answers, short reuse, a bounded grace, and no free yes.

The stored answer is a stand-in here; multiServer/test_database.py runs the real
statements against MariaDB.
"""
import ast
import gzip
import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import types
import unittest
from unittest.mock import patch

from multiServer import entitlement

try:
    import requests  # noqa: F401
    HAVE_REQUESTS = True
except ImportError:
    HAVE_REQUESTS = False

ADDRESS = '203.0.113.20'
START = 1795000000
DOWN = None


class Stored:
    """The single row, with the meaning of the two real statements."""

    def __init__(self):
        self.row = None
        self.broken = False

    def load(self):
        if self.broken:
            raise RuntimeError('table is missing')
        return self.row

    def save_answer(self, address, granted, now):
        if self.broken:
            raise RuntimeError('table is missing')
        self.row = entitlement.State(address, granted, now, now)

    def claim(self, address, now):
        if self.broken:
            raise RuntimeError('table is missing')
        same = self.row is not None and self.row.server_ip == address
        if same and now - entitlement.RETRY_SECONDS < self.row.checked_at <= now:
            return False
        self.row = self.row._replace(checked_at=now) if same else entitlement.State(address, False, 0, now)
        return True


class Platform(unittest.TestCase):
    """allowed() against a scripted platform and a clock the test moves."""

    def setUp(self):
        self.stored = Stored()
        self.answer = DOWN
        self.asked = []
        self.now = START
        self.address = ADDRESS
        for patcher in (
                patch.object(entitlement, '_load', side_effect=lambda: self.stored.load()),
                patch.object(entitlement, '_save_answer', side_effect=lambda *a: self.stored.save_answer(*a)),
                patch.object(entitlement, '_claim', side_effect=lambda *a: self.stored.claim(*a)),
                patch.object(entitlement, 'ask', side_effect=self.ask),
                patch.object(entitlement, 'server_address', side_effect=lambda: self.address),
                patch.object(entitlement.time, 'time', side_effect=lambda: self.now + 0.5)):
            patcher.start()
            self.addCleanup(patcher.stop)

    def ask(self, address):
        self.asked.append((self.now - START, address))
        return self.answer

    def at(self, seconds, answer='unchanged'):
        self.now = START + seconds
        if answer != 'unchanged':
            self.answer = answer
        return entitlement.allowed()

    def times_asked(self):
        return [seconds for seconds, _ in self.asked]


class ReuseTests(Platform):
    def test_a_yes_is_reused_for_sixty_seconds(self):
        self.assertIs(True, self.at(0, True))
        self.assertIs(True, self.at(59, False))
        self.assertEqual([0], self.times_asked())
        self.assertIs(False, self.at(60))
        self.assertEqual([0, 60], self.times_asked())

    def test_a_no_is_reused_for_ten_seconds(self):
        self.assertIs(False, self.at(0, False))
        self.assertIs(False, self.at(9, True))
        self.assertEqual([0], self.times_asked())
        self.assertIs(True, self.at(10))
        self.assertEqual([0, 10], self.times_asked())

    def test_the_platform_is_asked_for_this_servers_address(self):
        self.at(0, True)
        self.assertEqual([(0, ADDRESS)], self.asked)

    def test_an_answer_for_another_address_is_not_used(self):
        self.assertIs(True, self.at(0, True))
        self.address = '203.0.113.21'
        self.assertIs(False, self.at(5, False))
        self.assertEqual([(0, ADDRESS), (5, '203.0.113.21')], self.asked)
        self.address = ADDRESS
        self.assertIs(False, self.at(6, DOWN), 'the old yes must not come back after the address was changed')

    def test_without_a_valid_address_the_answer_is_no_and_nobody_is_asked(self):
        self.address = None
        self.assertIs(False, self.at(0, True))
        self.assertEqual([], self.asked)


class OutageTests(Platform):
    def test_the_last_yes_counts_for_twenty_four_hours_after_it_was_given(self):
        self.assertIs(True, self.at(0, True))
        day = 24 * 60 * 60
        self.assertIs(True, self.at(61, DOWN))
        self.assertIs(True, self.at(day - 1))
        self.assertIs(True, self.at(day))
        self.assertIs(False, self.at(day + 1))
        self.assertIs(False, self.at(day * 30))

    def test_the_grace_is_counted_from_the_last_yes_not_from_the_start_of_the_outage(self):
        self.assertIs(True, self.at(0, True))
        self.assertIs(True, self.at(3600, True))
        day = 24 * 60 * 60
        self.assertIs(True, self.at(3600 + day, DOWN))
        self.assertIs(False, self.at(3600 + day + 1))

    def test_an_unanswered_request_is_not_repeated_for_ten_seconds(self):
        self.at(0, True)
        for seconds in (60, 61, 65, 69, 70, 75, 79, 80):
            self.assertIs(True, self.at(seconds, DOWN))
        self.assertEqual([0, 60, 70, 80], self.times_asked())

    def test_without_an_earlier_yes_an_outage_means_no(self):
        self.assertIs(False, self.at(0, DOWN))
        self.assertIs(False, self.at(5))
        self.assertIs(False, self.at(10))
        self.assertEqual([0, 10], self.times_asked())

    def test_a_no_ends_the_grace_at_once(self):
        self.assertIs(True, self.at(0, True))
        self.assertIs(False, self.at(60, False))
        self.assertIs(False, self.at(70, DOWN))
        self.assertIs(False, self.at(3600))

    def test_the_platform_coming_back_is_noticed(self):
        self.at(0, True)
        self.assertIs(True, self.at(100, DOWN))
        self.assertIs(False, self.at(110, False))
        self.assertIs(True, self.at(120, True))

    def test_a_clock_set_back_does_not_extend_anything(self):
        self.assertIs(True, self.at(0, True))
        self.assertIs(False, self.at(-3600, DOWN), 'a yes dated in the future is not a yes')
        self.assertIs(True, self.at(-3590, True))
        self.assertEqual([0, -3600, -3590], self.times_asked())


class FailureTests(Platform):
    def test_an_answer_that_cannot_be_read_or_recorded_is_no(self):
        self.stored.broken = True
        self.assertIs(False, self.at(0, True))
        self.assertEqual([], self.asked, 'without the stored answer the platform would be asked on every request')
        self.stored.broken = False
        with patch.object(entitlement, '_save_answer', side_effect=RuntimeError('read-only')):
            self.assertIs(False, self.at(1, True))
        self.assertIs(False, self.at(2), 'the attempt was noted before asking, so nobody asks again at once')
        self.assertIs(True, self.at(1 + entitlement.RETRY_SECONDS))
        self.assertEqual([1, 1 + entitlement.RETRY_SECONDS], self.times_asked())

    def test_never_raises_and_answers_only_true_or_false(self):
        for broken in ('_load', '_save_answer', '_claim', 'ask', 'server_address'):
            for answer in (True, False, DOWN):
                self.stored.row = None
                with patch.object(entitlement, broken, side_effect=RuntimeError('unexpected')):
                    result = self.at(1000, answer)
                # Only a yes from the platform that was also recorded is a yes, and nobody asks
                # who could not first note that he is asking.
                self.assertIs(False, result, (broken, answer))
        with patch.object(entitlement, '_claim', side_effect=RuntimeError('read-only')):
            self.stored.row = None
            self.at(2000, True)
        self.assertNotIn(2000, self.times_asked())
        for strange in (1, 'yes', [True], 0, ''):
            self.stored.row = None
            self.assertIs(False, self.at(5000, strange), repr(strange))

    def test_a_stored_value_that_is_not_exactly_true_is_not_a_yes(self):
        self.stored.row = entitlement.State(ADDRESS, 1, START, START)
        self.assertIs(False, self.at(5, DOWN))


class SingleFlightTests(Platform):
    """One worker asks; the time of the attempt is in the row before it does; nobody else waits."""

    def test_the_attempt_is_noted_before_the_platform_is_asked(self):
        noted = []

        def ask(address):
            noted.append(self.stored.row)
            return True

        with patch.object(entitlement, 'ask', side_effect=ask):
            self.assertIs(True, self.at(0))
            self.assertIs(True, self.at(60))
        self.assertEqual([entitlement.State(ADDRESS, False, 0, START),
                          entitlement.State(ADDRESS, True, START, START + 60)], noted)

    def test_requests_arriving_while_one_is_asking_are_answered_at_once_from_what_is_stored(self):
        self.assertIs(True, self.at(0, True))
        during = []

        def stalled(address):
            # What every other worker gets while this one waits for the platform.
            for _ in range(5):
                during.append(entitlement.allowed())
            self.asked.append((self.now - START, address))
            return DOWN

        with patch.object(entitlement, 'ask', side_effect=stalled):
            self.assertIs(True, self.at(60))
            for seconds in (61, 64, 69):
                self.assertIs(True, self.at(seconds))
        self.assertEqual([True] * 5, during, 'the last yes still counts, and nobody waited for it')
        self.assertEqual([0, 60], self.times_asked())

    def test_without_a_yes_to_fall_back_on_they_are_told_no_at_once(self):
        during = []

        def stalled(address):
            during.append(entitlement.allowed())
            self.asked.append((self.now - START, address))
            return True

        with patch.object(entitlement, 'ask', side_effect=stalled):
            self.assertIs(True, self.at(0))
        self.assertEqual([False], during, 'a yes that has not arrived is not a yes')
        self.assertEqual([0], self.times_asked())

    def test_a_worker_that_loses_the_claim_uses_the_answer_the_winner_just_stored(self):
        self.assertIs(True, self.at(0, True))
        def lost(address, now):
            # Between this worker's reading of the row and its claim, another asked and was told no.
            self.stored.save_answer(address, False, now)
            return False

        with patch.object(entitlement, '_claim', side_effect=lost):
            self.assertIs(False, self.at(60, True))
        self.assertEqual([0], self.times_asked())

    def test_a_stalled_platform_costs_one_request_in_ten_seconds_the_deadline_and_no_more(self):
        self.assertIs(True, self.at(0, True))
        waited = []
        with patch.object(entitlement, 'ask', side_effect=lambda address: waited.append(self.now - START)):
            for seconds in range(60, 121):
                self.assertIs(True, self.at(seconds))
        self.assertEqual([60, 70, 80, 90, 100, 110, 120], waited)


class DeadlineTests(unittest.TestCase):
    def test_the_caller_waits_no_longer_than_the_deadline_whatever_the_request_does(self):
        release = threading.Event()
        self.addCleanup(release.set)
        started = time.monotonic()
        with patch.object(entitlement, '_ask', side_effect=lambda address: release.wait(30) and True), \
                patch.object(entitlement, 'DEADLINE', 0.2):
            self.assertIsNone(entitlement.ask(ADDRESS))
        self.assertLess(time.monotonic() - started, 5)

    def test_an_answer_within_the_deadline_is_the_answer(self):
        for answer in (True, False, None):
            with patch.object(entitlement, '_ask', return_value=answer) as asked:
                self.assertIs(answer, entitlement.ask(ADDRESS))
            asked.assert_called_once_with(ADDRESS)

    def test_a_request_that_fails_is_no_answer(self):
        with patch.object(entitlement.threading, 'Thread', side_effect=RuntimeError('no more threads')):
            self.assertIsNone(entitlement.ask(ADDRESS))

    def test_the_parts_of_one_request_fit_inside_the_deadline(self):
        self.assertEqual(4, entitlement.DEADLINE)
        self.assertLessEqual(entitlement.CONNECT_SECONDS + entitlement.READ_SECONDS, entitlement.DEADLINE)
        self.assertLess(entitlement.DEADLINE, entitlement.RETRY_SECONDS)


class Reply:
    def __init__(self, status=200, body=b'{"status": 1, "error_message": null}'):
        self.status_code = status
        self.raw = types.SimpleNamespace(read=self.read)
        self.body = body
        self.closed = False
        self.read_with = None

    def read(self, amount, decode_content=False):
        self.read_with = (amount, decode_content)
        return self.body[:amount] if isinstance(self.body, bytes) else self.body

    def close(self):
        self.closed = True


class AskTests(unittest.TestCase):
    """What is sent to the platform and which replies count."""

    def setUp(self):
        self.calls = []
        self.reply = Reply()
        requests = types.ModuleType('requests')
        requests.post = self.post
        patcher = patch.dict(sys.modules, {'requests': requests})
        patcher.start()
        self.addCleanup(patcher.stop)

    def post(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        if isinstance(self.reply, Exception):
            raise self.reply
        return self.reply

    def test_the_request_is_the_add_on_check_for_exactly_multi_server(self):
        self.assertIs(True, entitlement.ask(ADDRESS))
        (args, kwargs), = self.calls
        self.assertEqual(('https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission',), args)
        self.assertEqual({'name': 'multi-server', 'IP': ADDRESS}, json.loads(kwargs.pop('data')))
        self.assertEqual({'headers': {'Accept-Encoding': 'identity'}, 'timeout': (2, 2),
                          'allow_redirects': False, 'stream': True}, kwargs)
        self.assertEqual((entitlement.MAX_REPLY + 1, True), self.reply.read_with)
        self.assertTrue(self.reply.closed)

    def test_only_the_integer_one_is_a_yes_and_only_the_integer_zero_is_a_no(self):
        for body, expected in (
                (b'{"status": 1}', True), (b'{"status": 0}', False),
                (b'{"status": 0, "error_message": "No Multi-Server Manager licence for this IP"}', False),
                (b'{"status": true}', None), (b'{"status": false}', None), (b'{"status": "1"}', None),
                (b'{"status": 1.0}', None), (b'{"status": 2}', None), (b'{"status": -1}', None),
                (b'{"status": null}', None), (b'{"status": [1]}', None), (b'{"Status": 1}', None),
                (b'{}', None), (b'[1]', None), (b'1', None), (b'"status"', None), (b'', None),
                (b'{"status": 1', None), (b'<html>status 1</html>', None), (b'\xff\xfe{"status": 1}', None),
                (b'{"status": 1, "status": 0}', None), (b'{"status": 0, "status": 1}', None),
                (b'{"data": {"status": 1}}', None), ('{"status": 1}', None), (None, None),
                (b'{"status": 1, "pad": "' + b'x' * entitlement.MAX_REPLY + b'"}', None),
                (b'{"status": 1}' + b' ' * entitlement.MAX_REPLY, None),
                (b'{"status": 1}' + b' ' * (entitlement.MAX_REPLY - 13), True)):
            self.reply = Reply(body=body)
            self.assertIs(expected, entitlement.ask(ADDRESS), body)
            self.assertTrue(self.reply.closed)

    def test_any_status_but_200_is_no_answer_whatever_the_body_says(self):
        for status in (201, 204, 301, 302, 400, 403, 404, 429, 500, 502, 503, '200', None, True):
            self.reply = Reply(status=status, body=b'{"status": 1}')
            self.assertIsNone(entitlement.ask(ADDRESS), status)
            self.assertIsNone(self.reply.read_with, 'the body of such a reply is not even read')
            self.assertTrue(self.reply.closed)

    def test_an_unreachable_platform_is_no_answer_and_never_an_error(self):
        for failure in (ConnectionError('refused'), TimeoutError('timed out'), OSError('no route'),
                        ValueError('bad url'), RuntimeError('anything')):
            self.reply = failure
            self.assertIsNone(entitlement.ask(ADDRESS))
        with patch.dict(sys.modules, {'requests': None}):
            self.assertIsNone(entitlement.ask(ADDRESS))


@unittest.skipUnless(HAVE_REQUESTS, 'the requests library is not installed here')
class AskOverHttpTests(unittest.TestCase):
    """ask() with the real HTTP library against a stand-in platform on this machine's loopback."""

    def setUp(self):
        test = self
        self.received = []
        self.reply = (200, {'Content-Type': 'application/json'}, b'{"status": 1, "error_message": null}')

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get('Content-Length', '0'))
                test.received.append((self.path, dict(self.headers.items()), self.rfile.read(length)))
                status, headers, body = test.reply if self.path == '/ask' else (200, {}, b'{"status": 1}')
                self.send_response(status)
                for name, value in headers.items():
                    self.send_header(name, value)
                self.send_header('Content-Length', str(len(body)))
                self.end_headers()
                try:
                    self.wfile.write(body)
                except OSError:
                    pass    # the client stopped reading, as it should for an oversized reply

            do_GET = do_POST

            def log_message(self, *arguments):
                pass

        self.server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        self.base = 'http://127.0.0.1:%d' % self.server.server_address[1]
        thread = threading.Thread(target=self.server.serve_forever)
        thread.daemon = True
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)
        # No proxy from the environment may stand between the test and its own server.
        for patcher in (patch.object(entitlement, 'URL', self.base + '/ask'),
                        patch.dict(os.environ, {'NO_PROXY': '127.0.0.1', 'no_proxy': '127.0.0.1'})):
            patcher.start()
            self.addCleanup(patcher.stop)

    def test_one_post_with_the_feature_and_the_address_and_the_answer_is_read(self):
        self.assertIs(True, entitlement.ask(ADDRESS))
        (path, headers, body), = self.received
        self.assertEqual('/ask', path)
        self.assertEqual({'name': 'multi-server', 'IP': ADDRESS}, json.loads(body.decode()))
        self.assertEqual('identity', headers['Accept-Encoding'])
        self.reply = (200, {}, b'{"status": 0, "error_message": "No Multi-Server Manager licence for this IP"}')
        self.assertIs(False, entitlement.ask(ADDRESS))

    def test_a_redirect_is_not_followed(self):
        for status in (301, 302, 303, 307, 308):
            self.reply = (status, {'Location': self.base + '/elsewhere'}, b'{"status": 1}')
            self.assertIsNone(entitlement.ask(ADDRESS), status)
        self.assertEqual(['/ask'] * 5, [path for path, _, _ in self.received])

    def test_an_error_status_is_no_answer_even_with_a_yes_in_its_body(self):
        for status in (201, 400, 403, 404, 500, 502, 503):
            self.reply = (status, {}, b'{"status": 1}')
            self.assertIsNone(entitlement.ask(ADDRESS), status)

    def test_a_reply_that_is_too_long_or_not_the_expected_json_is_no_answer(self):
        for body in (b'{"status": 1, "pad": "' + b'x' * (4 * 1024 * 1024) + b'"}',
                     b'{"status": 1}' + b' ' * entitlement.MAX_REPLY, b'<html>status 1</html>', b'',
                     b'{"status": true}', b'{"status": "1"}', b'{"status": 1, "status": 0}'):
            self.reply = (200, {}, body)
            self.assertIsNone(entitlement.ask(ADDRESS), body[:40])

    def test_a_compressed_reply_is_read_as_what_it_says(self):
        self.reply = (200, {'Content-Encoding': 'gzip'}, gzip.compress(b'{"status": 1}'))
        self.assertIs(True, entitlement.ask(ADDRESS))
        self.reply = (200, {'Content-Encoding': 'gzip'}, gzip.compress(b'{"status": 1}' + b' ' * 10 ** 6))
        self.assertIsNone(entitlement.ask(ADDRESS))

    def test_nothing_listening_is_no_answer(self):
        self.server.shutdown()
        self.server.server_close()
        self.assertIsNone(entitlement.ask(ADDRESS))


class AddressTests(unittest.TestCase):
    def read(self, text):
        with tempfile.NamedTemporaryFile('w', suffix='machineIP') as file:
            file.write(text)
            file.flush()
            with patch.object(entitlement, 'ADDRESS_FILE', file.name):
                return entitlement.server_address()

    def test_the_first_line_of_the_panels_address_file(self):
        self.assertEqual('203.0.113.20', self.read('203.0.113.20'))
        self.assertEqual('203.0.113.20', self.read('203.0.113.20\n'))
        self.assertEqual('203.0.113.20', self.read(' 203.0.113.20 \nsecond line\n'))
        self.assertEqual('2001:db8::20', self.read('2001:db8::20\n'))

    def test_anything_that_is_not_one_address_is_none(self):
        for text in ('', '\n203.0.113.20', 'example.com', '203.0.113.20, 10.0.0.1', '203.0.113.0/24',
                     'fe80::1%eth0', '203.0.113.20"}', 'x' * 500):
            self.assertIsNone(self.read(text), text)
        with patch.object(entitlement, 'ADDRESS_FILE', '/nonexistent/machineIP'):
            self.assertIsNone(entitlement.server_address())


class IndependenceTests(unittest.TestCase):
    """The panel's general add-on check answers yes on LiteSpeed Enterprise; this one must not."""
    SOURCE = Path(entitlement.__file__).read_text()

    def test_the_kind_of_web_server_is_never_looked_at(self):
        for name in ('decideServer', 'ProcessUtilities', 'CheckForPremFeature', 'plogical', 'lsws'):
            self.assertNotIn(name, self.SOURCE)

    def test_the_documented_periods(self):
        self.assertEqual((60, 10, 10, 86400), (entitlement.YES_SECONDS, entitlement.NO_SECONDS,
                                               entitlement.RETRY_SECONDS, entitlement.GRACE_SECONDS))
        self.assertEqual('multi-server', entitlement.FEATURE)

    @unittest.skipUnless(sys.version_info >= (3, 8), 'ast cannot check an older grammar before Python 3.8')
    def test_source_parses_as_python_3_6(self):
        ast.parse(self.SOURCE, feature_version=(3, 6))


if __name__ == '__main__':
    unittest.main()
