"""The webmail image proxy: what it fetches and what it hands the browser."""
import socket
import threading
import unittest

from webmail.services import image_proxy
from webmail.services.image_proxy import ImageProxyError

PNG = b'\x89PNG\r\n\x1a\n' + b'\x00' * 32
SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><script>run()</script></svg>'


def resolver_for(table):
    """A getaddrinfo stand-in answering from {host: [address, ...]}."""
    calls = []

    def resolve(host, port, family=0, kind=0):
        calls.append(host)
        answers = []
        for address in table[host]:
            family = socket.AF_INET6 if ':' in address else socket.AF_INET
            answers.append((family, socket.SOCK_STREAM, 6, '', (address, port)))
        return answers

    resolve.calls = calls
    return resolve


class FakeResponse:
    def __init__(self, status, headers, body):
        self.status = status
        self.headers = headers
        self.body = body

    def getheader(self, name, default=None):
        return self.headers.get(name, default)

    def read(self, amount):
        chunk, self.body = self.body[:amount], self.body[amount:]
        return chunk


def connections_for(script):
    """Connection classes that answer from script and record every connect."""
    made = []

    class FakeConnection:
        def __init__(self, host, port, address, timeout):
            self.record = {'host': host, 'port': port, 'address': address}
            made.append(self.record)

        def request(self, method, target, headers):
            self.record['target'] = target
            if script and script[0] == 'unreachable':
                script.pop(0)
                raise ConnectionRefusedError()

        def getresponse(self):
            return FakeResponse(*script.pop(0))

        def close(self):
            pass

    return {'http': FakeConnection, 'https': FakeConnection}, made


class AddressTests(unittest.TestCase):

    def test_internal_and_special_addresses_are_not_public(self):
        for address in ('127.0.0.1', '10.1.2.3', '172.16.0.1', '192.168.1.1',
                        '169.254.169.254', '100.64.0.1', '0.0.0.0', '224.0.0.1',
                        '255.255.255.255', '::1', '::', 'fe80::1', 'fc00::1',
                        '::ffff:127.0.0.1', '::ffff:169.254.169.254',
                        '64:ff9b::7f00:1', '2002:7f00:1::1', 'not-an-address'):
            self.assertFalse(image_proxy.is_public_address(address), address)

    def test_public_addresses_are_allowed(self):
        for address in ('93.184.216.34', '1.1.1.1', '2606:4700:4700::1111'):
            self.assertTrue(image_proxy.is_public_address(address), address)

    def test_one_internal_answer_refuses_the_whole_name(self):
        resolve = resolver_for({'mixed.example': ['93.184.216.34', '127.0.0.1']})
        with self.assertRaises(ImageProxyError):
            image_proxy.resolve_public_addresses('mixed.example', 80, resolve)

    def test_ipv6_answers_are_checked(self):
        resolve = resolver_for({'six.example': ['fd00::5']})
        with self.assertRaises(ImageProxyError):
            image_proxy.resolve_public_addresses('six.example', 443, resolve)


class UrlTests(unittest.TestCase):

    def test_only_web_schemes_on_standard_ports(self):
        for url in ('ftp://images.example/a.png', 'file:///etc/passwd',
                    'https://images.example:8443/a.png', 'http://images.example:8090/a.png',
                    'http://user:pass@images.example/a.png', 'https:///a.png'):
            with self.assertRaises(ImageProxyError, msg=url):
                image_proxy.check_url(url)

    def test_request_target_is_quoted(self):
        scheme, host, port, target = image_proxy.check_url(
            'http://images.example/a b.png?q=1 2\r\nX: y')
        self.assertEqual(('http', 'images.example', 80), (scheme, host, port))
        # Newer Pythons drop CR/LF while splitting; older ones keep them.
        self.assertTrue(target.startswith('/a%20b.png?q=1%202'), target)
        for character in ' \r\n':
            self.assertNotIn(character, target)


class SniffTests(unittest.TestCase):

    def test_raster_formats_are_recognised_from_their_bytes(self):
        samples = {
            PNG: 'image/png',
            b'\xff\xd8\xff\xe0' + b'\x00' * 8: 'image/jpeg',
            b'GIF89a' + b'\x00' * 8: 'image/gif',
            b'RIFF\x00\x00\x00\x00WEBPVP8 ': 'image/webp',
            b'\x00\x00\x00\x1cftypavif': 'image/avif',
            b'BM' + b'\x00' * 12: 'image/bmp',
            b'\x00\x00\x01\x00' + b'\x00' * 8: 'image/x-icon',
        }
        for data, media_type in samples.items():
            self.assertEqual(media_type, image_proxy.sniff_image_type(data))

    def test_svg_and_pages_are_not_images(self):
        for data in (SVG, b'<?xml version="1.0"?>' + SVG, b'<html><script>run()</script>', b''):
            self.assertIsNone(image_proxy.sniff_image_type(data))


class FetchTests(unittest.TestCase):

    def fetch(self, url, table, script):
        connections, made = connections_for(script)
        resolve = resolver_for(table)
        result = image_proxy.fetch_image(url, resolver=resolve, connections=connections)
        return result, made, resolve

    def test_svg_is_refused_even_when_labelled_as_an_image(self):
        with self.assertRaises(ImageProxyError):
            self.fetch('https://images.example/x.svg',
                       {'images.example': ['93.184.216.34']},
                       [(200, {'Content-Type': 'image/svg+xml'}, SVG)])
        with self.assertRaises(ImageProxyError):
            self.fetch('https://images.example/x.png',
                       {'images.example': ['93.184.216.34']},
                       [(200, {'Content-Type': 'image/png'}, SVG)])

    def test_media_type_comes_from_the_bytes(self):
        (data, media_type), made, unused = self.fetch(
            'https://images.example/x', {'images.example': ['93.184.216.34']},
            [(200, {'Content-Type': 'text/html'}, PNG)])
        self.assertEqual((PNG, 'image/png'), (data, media_type))

    def test_connection_goes_to_the_checked_address(self):
        unused, made, resolve = self.fetch(
            'https://images.example/x.png', {'images.example': ['93.184.216.34']},
            [(200, {}, PNG)])
        self.assertEqual([{'host': 'images.example', 'port': 443,
                           'address': '93.184.216.34', 'target': '/x.png'}], made)
        self.assertEqual(['images.example'], resolve.calls)

    def test_redirect_to_an_internal_address_is_refused(self):
        for location in ('http://127.0.0.1:80/', 'http://169.254.169.254/latest/meta-data/',
                         'http://internal.example/', 'http://[::1]/'):
            script = [(302, {'Location': location}, b'')]
            with self.assertRaises(ImageProxyError, msg=location):
                self.fetch('https://images.example/x.png',
                           {'images.example': ['93.184.216.34'],
                            'internal.example': ['10.0.0.8'],
                            '127.0.0.1': ['127.0.0.1'],
                            '169.254.169.254': ['169.254.169.254'],
                            '::1': ['::1']},
                           script)

    def test_redirect_to_another_port_is_refused(self):
        with self.assertRaises(ImageProxyError):
            self.fetch('https://images.example/x.png', {'images.example': ['93.184.216.34']},
                       [(301, {'Location': 'https://images.example:8090/'}, b'')])

    def test_public_redirect_is_followed_and_checked_again(self):
        (data, unused), made, resolve = self.fetch(
            'https://images.example/x.png',
            {'images.example': ['93.184.216.34'], 'cdn.example': ['93.184.216.35']},
            [(302, {'Location': '//cdn.example/y.png'}, b''), (200, {}, PNG)])
        self.assertEqual(PNG, data)
        self.assertEqual(['images.example', 'cdn.example'], resolve.calls)
        self.assertEqual('93.184.216.35', made[1]['address'])

    def test_redirect_loops_stop(self):
        script = [(302, {'Location': '/again'}, b'')] * (image_proxy.MAX_REDIRECTS + 1)
        with self.assertRaises(ImageProxyError):
            self.fetch('https://images.example/x.png', {'images.example': ['93.184.216.34']},
                       list(script))

    def test_next_checked_address_is_tried_when_one_is_unreachable(self):
        (data, unused), made, resolve = self.fetch(
            'https://images.example/x.png',
            {'images.example': ['2606:4700::6810:1', '93.184.216.34']},
            ['unreachable', (200, {}, PNG)])
        self.assertEqual(PNG, data)
        self.assertEqual(['2606:4700::6810:1', '93.184.216.34'], [m['address'] for m in made])
        self.assertEqual(['images.example'], resolve.calls)

    def test_slow_answers_stop_at_the_deadline(self):
        from unittest import mock
        clock = iter(range(0, 1000, 20))
        with mock.patch('webmail.services.image_proxy.time.monotonic', lambda: next(clock)):
            with self.assertRaises(ImageProxyError):
                self.fetch('https://images.example/x.png',
                           {'images.example': ['93.184.216.34']},
                           [(200, {}, PNG * 100000)])

    def test_oversized_and_failed_answers_are_refused(self):
        big = PNG + b'\x00' * image_proxy.MAX_BYTES
        for answer in ((200, {}, big), (200, {'Content-Length': str(image_proxy.MAX_BYTES + 1)}, PNG),
                       (404, {}, PNG), (500, {}, b'')):
            with self.assertRaises(ImageProxyError):
                self.fetch('https://images.example/x.png',
                           {'images.example': ['93.184.216.34']}, [answer])


class PinnedConnectionTests(unittest.TestCase):

    def test_http_connection_uses_the_pinned_address_and_keeps_the_name(self):
        server = socket.socket()
        server.bind(('127.0.0.1', 0))
        server.listen(1)
        port = server.getsockname()[1]
        seen = []

        def answer():
            client, unused = server.accept()
            data = b''
            while b'\r\n\r\n' not in data:
                data += client.recv(4096)
            seen.append(data)
            client.sendall(b'HTTP/1.0 200 OK\r\nContent-Length: 2\r\n\r\nok')
            client.close()

        worker = threading.Thread(target=answer)
        worker.start()
        try:
            # "images.invalid" never resolves: only the pinned address is used.
            connection = image_proxy.CONNECTIONS['http']('images.invalid', port, '127.0.0.1', 5)
            connection.request('GET', '/x.png')
            self.assertEqual(200, connection.getresponse().status)
            connection.close()
        finally:
            worker.join(5)
            server.close()
        self.assertIn(b'Host: images.invalid:%d' % port, seen[0])


if __name__ == '__main__':
    unittest.main()
