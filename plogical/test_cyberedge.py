import io
import hashlib
import os
from types import SimpleNamespace
from unittest import TestCase, mock

from plogical import cyberedge


class Response(io.BytesIO):
    headers = {}


class CyberEdgeIntegrationTests(TestCase):
    def test_verified_plugin_download_accepts_pinned_checksum(self):
        payload = b'a valid test archive'
        with mock.patch.object(cyberedge, 'PLUGIN_SHA256', hashlib.sha256(payload).hexdigest()):
            path = cyberedge.download_verified_plugin(lambda *args, **kwargs: Response(payload))
        try:
            with open(path, 'rb') as archive:
                self.assertEqual(archive.read(), payload)
            self.assertEqual(os.stat(path).st_mode & 0o777, 0o644)
        finally:
            os.unlink(path)

    def test_verified_plugin_download_rejects_wrong_archive(self):
        with self.assertRaisesRegex(ValueError, 'checksum'):
            cyberedge.download_verified_plugin(lambda *args, **kwargs: Response(b'not-the-release'))

    def test_public_status_requires_edge_identity_headers(self):
        resolver = lambda *args, **kwargs: [(None, None, None, None, ('8.8.8.8', 443))]
        runner = mock.Mock(return_value=SimpleNamespace(
            returncode=0, stdout='HTTP/2 200\r\nx-cyberedge-cache: hit\r\nx-cyberedge-node: edge-one\r\n'))
        status = cyberedge.public_edge_status('https://example.com/', resolver=resolver, runner=runner)
        self.assertEqual(status, {'state': 'active', 'cache': 'hit', 'node': 'edge-one', 'reason': ''})
        self.assertIn('--resolve', runner.call_args.args[0])

    def test_public_status_refuses_private_dns(self):
        resolver = lambda *args, **kwargs: [(None, None, None, None, ('127.0.0.1', 443))]
        runner = mock.Mock()
        self.assertEqual(cyberedge.public_edge_status('https://example.com/', resolver=resolver, runner=runner), {'state': 'unavailable'})
        runner.assert_not_called()

    def test_wordpress_redirect_is_strictly_allow_listed(self):
        self.assertEqual(
            cyberedge.wordpress_admin_redirect('cyberedge'),
            '/wp-admin/tools.php?page=cyberedge-cache')
        self.assertEqual(cyberedge.wordpress_admin_redirect('https://attacker.test'), '/wp-admin')
