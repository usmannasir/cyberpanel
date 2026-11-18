"""The download guard against the system's real wget and a local throttled server."""
import hashlib
import http.server
import os
from pathlib import Path
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarded_download  # noqa: E402


class Handler(http.server.BaseHTTPRequestHandler):
    """Serves the payload the way the connection's plan entry says."""

    def do_GET(self):
        server = self.server
        with server.lock:
            index = len(server.requests)
            server.requests.append(self.headers.get('Range'))
        plan = server.plan[min(index, len(server.plan) - 1)]
        if plan.get('status', 200) != 200:
            self.send_error(plan['status'])
            return
        payload = server.payload
        self.send_response(200)
        self.send_header('Content-Type', 'application/octet-stream')
        self.send_header('Content-Length', str(len(payload)))
        self.end_headers()
        rate = plan.get('rate')                     # bytes per second, None = unthrottled
        stop = plan.get('close_after', len(payload))
        stall = plan.get('stall_after')             # then keep the connection open, silent
        sent = 0
        try:
            while sent < stop:
                if stall is not None and sent >= stall:
                    server.released.wait(120)
                    return
                step = 65536 if rate is None else max(1, int(rate * 0.05))
                step = min(step, stop - sent)
                if stall is not None:
                    step = min(step, stall - sent)
                self.wfile.write(payload[sent:sent + step])
                self.wfile.flush()
                sent += step
                if rate is not None:
                    time.sleep(0.05)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def log_message(self, *arguments):
        pass


class Server(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(self, address, payload, plan):
        self.payload = payload
        self.plan = plan
        self.requests = []
        self.lock = threading.Lock()
        self.released = threading.Event()
        http.server.HTTPServer.__init__(self, address, Handler)
        threading.Thread(target=self.serve_forever, kwargs={'poll_interval': 0.05},
                         daemon=True).start()

    def close(self):
        self.released.set()
        self.shutdown()
        self.server_close()


class Server6(Server):
    address_family = socket.AF_INET6


@unittest.skipUnless(shutil.which('wget'), 'wget is not installed')
class RealWgetTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.destination = os.path.join(temporary.name, 'candidate with spaces')
        # wget rejects /dev/null here; an empty file keeps the host's settings out.
        empty = os.path.join(temporary.name, 'wgetrc')
        open(empty, 'w').close()
        environment = patch.dict(os.environ, {'WGETRC': empty, 'SYSTEM_WGETRC': empty})
        environment.start()
        self.addCleanup(environment.stop)
        for name in ('http_proxy', 'https_proxy', 'HTTP_PROXY', 'HTTPS_PROXY', 'ALL_PROXY'):
            os.environ.pop(name, None)
        guarded_download._proven.clear()
        self.addCleanup(guarded_download._proven.clear)
        self.processes = []
        real = subprocess.Popen

        def recording(*arguments, **keywords):
            process = real(*arguments, **keywords)
            self.processes.append(process)
            return process

        popen = patch.object(guarded_download.subprocess, 'Popen', side_effect=recording)
        popen.start()
        self.addCleanup(popen.stop)
        self.messages = []
        self.policy = guarded_download.Policy(
            window=2.0, first_byte=2.0, stall=3.0, poll=0.1, pause=0.1, grace=2.0)

    def serve(self, size, *plan, **options):
        payload = os.urandom(size)
        server = options.get('kind', Server)((options.get('host', '127.0.0.1'),
                                               options.get('port', 0)), payload, list(plan))
        self.addCleanup(server.close)
        return server

    def fetch(self, server, host='127.0.0.1'):
        url = 'http://%s:%d/file?one=1&two=2' % (host, server.server_address[1])
        started = time.time()
        try:
            return guarded_download.fetch(url, self.destination, self.messages.append,
                                          self.policy)
        finally:
            self.elapsed = time.time() - started
            self.assertEqual([], [p.pid for p in self.processes if p.poll() is None])

    def assert_delivered(self, server):
        with open(self.destination, 'rb') as target:
            self.assertEqual(hashlib.sha256(server.payload).hexdigest(),
                             hashlib.sha256(target.read()).hexdigest())

    def test_healthy_download_is_one_request(self):
        server = self.serve(2 * 1024 * 1024, {})
        self.assertTrue(self.fetch(server), self.messages)
        self.assertEqual([None], server.requests)
        self.assert_delivered(server)

    def test_modest_but_adequate_rate_is_left_alone(self):
        # Also proves the file grows while wget runs, which the guard relies on:
        # a wget that buffered the body would look silent and be replaced.
        server = self.serve(500 * 1024, {'rate': 100 * 1024})
        self.assertTrue(self.fetch(server), self.messages)
        self.assertEqual([None], server.requests)
        self.assert_delivered(server)
        self.assertGreater(self.elapsed, 3)

    def test_trickling_connection_is_replaced_by_a_fresh_one(self):
        server = self.serve(300 * 1024, {'rate': 2048}, {})
        self.assertTrue(self.fetch(server), self.messages)
        # The second request starts over; nothing of the abandoned file is reused.
        self.assertEqual([None, None], server.requests)
        self.assert_delivered(server)
        self.assertLess(self.elapsed, 15)
        self.assertTrue(any('too slow' in message for message in self.messages), self.messages)

    def test_connection_that_always_stalls_fails_in_bounded_time(self):
        server = self.serve(300 * 1024, {'stall_after': 20000})
        self.assertFalse(self.fetch(server))
        self.assertEqual(3, len(server.requests))
        self.assertFalse(os.path.exists(self.destination))
        self.assertLess(self.elapsed, 30)

    def test_slow_link_still_completes_on_the_last_attempt(self):
        server = self.serve(40 * 1024, {'rate': 5 * 1024})
        self.assertTrue(self.fetch(server), self.messages)
        self.assertEqual(3, len(server.requests))
        self.assert_delivered(server)
        self.assertTrue(any('without a speed limit' in message for message in self.messages),
                        self.messages)

    def test_missing_file_fails_without_leaving_anything(self):
        server = self.serve(1024, {'status': 404})
        self.assertFalse(self.fetch(server))
        self.assertEqual(3, len(server.requests))
        self.assertFalse(os.path.exists(self.destination))
        self.assertTrue(any('exit code 8' in message for message in self.messages), self.messages)

    def test_truncated_response_is_not_accepted(self):
        server = self.serve(200 * 1024, {'close_after': 50000}, {})
        self.assertTrue(self.fetch(server), self.messages)
        self.assertEqual([None, None], server.requests)
        self.assert_delivered(server)

    def test_slow_ipv6_route_is_left_for_ipv4(self):
        if not socket.has_ipv6:
            self.skipTest('no IPv6 support')
        for _ in range(5):
            try:
                slow = self.serve(300 * 1024, {'rate': 2048}, kind=Server6, host='::1')
            except OSError:
                self.skipTest('no IPv6 loopback')
            try:
                fast = Server(('127.0.0.1', slow.server_address[1]), slow.payload, [{}])
            except OSError:
                continue
            self.addCleanup(fast.close)
            break
        else:
            self.skipTest('no port free on both loopback addresses')
        self.assertTrue(self.fetch(slow, host='localhost'), self.messages)
        if not slow.requests:
            self.skipTest('resolver offers IPv4 first for localhost')
        self.assertEqual([None], fast.requests)
        self.assert_delivered(fast)


if __name__ == '__main__':
    unittest.main()
