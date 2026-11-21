"""A self-updating server trusts only a release file signed by CyberPanel."""
import ast
import base64
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import releaseManifest  # noqa: E402

from cryptography.hazmat.primitives import serialization  # noqa: E402
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey  # noqa: E402

RELEASE = {'schema': 1, 'sequence': 7, 'version': '3.0', 'build': 10, 'branch': 'v3.0.10',
           'commit': 'a' * 40, 'published': '2026-11-21T09:30:05Z', 'soak_hours': 24,
           'spread_hours': 48, 'hold': False}


def public_text(key):
    return base64.b64encode(key.public_key().public_bytes(
        encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)).decode()


def document(release, key, text=None, prefix=releaseManifest.PREFIX):
    text = json.dumps(release, sort_keys=True, separators=(',', ':')) if text is None else text
    identity = releaseManifest.key_id(base64.b64decode(public_text(key)))
    signature = base64.b64encode(key.sign(prefix + text.encode())).decode()
    return json.dumps({'release': text, 'signatures': [{'key': identity, 'signature': signature}]}).encode()


class VerificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.key, cls.spare, cls.stranger = (Ed25519PrivateKey.generate() for unused in range(3))
        cls.publishers = (public_text(cls.key), public_text(cls.spare))

    def verified(self, data):
        return releaseManifest.verified(data, self.publishers)

    def test_release_signed_by_either_publisher_key_is_accepted(self):
        self.assertEqual(RELEASE, self.verified(document(RELEASE, self.key)))
        self.assertEqual(RELEASE, self.verified(document(RELEASE, self.spare)))

    def test_release_signed_by_anyone_else_is_refused(self):
        with self.assertRaisesRegex(releaseManifest.Unverified, 'not signed by CyberPanel'):
            self.verified(document(RELEASE, self.stranger))
        # A stranger claiming a publisher's key name gains nothing.
        forged = json.loads(document(RELEASE, self.stranger).decode())
        forged['signatures'][0]['key'] = releaseManifest.key_id(base64.b64decode(self.publishers[0]))
        with self.assertRaises(releaseManifest.Unverified):
            self.verified(json.dumps(forged).encode())

    def test_any_change_to_the_signed_text_is_refused(self):
        good = json.loads(document(RELEASE, self.key).decode())
        for changed in (good['release'].replace('a' * 40, 'b' * 40),
                        good['release'].replace('"hold":false', '"hold":true'),
                        good['release'] + ' '):
            with self.subTest(changed), self.assertRaises(releaseManifest.Unverified):
                self.verified(json.dumps(dict(good, release=changed)).encode())

    def test_signature_made_for_another_purpose_is_refused(self):
        with self.assertRaises(releaseManifest.Unverified):
            self.verified(document(RELEASE, self.key, prefix=b'another-purpose\n'))

    def test_signed_release_with_unexpected_content_is_refused(self):
        changes = (
            {'schema': 2}, {'schema': True}, {'sequence': 0}, {'sequence': '7'}, {'version': '3'},
            {'version': '3.0;id'}, {'build': '10'}, {'build': -1}, {'branch': 'stable'},
            {'branch': 'v3.0.11'}, {'commit': 'A' * 40}, {'commit': 'a' * 39}, {'commit': None},
            {'published': '2026-11-21 09:30:05'}, {'published': '2026-13-41T09:30:05Z'},
            {'soak_hours': 337}, {'soak_hours': 1.5}, {'spread_hours': -1}, {'hold': 0},
            {'extra': 1},
        )
        for change in changes:
            with self.subTest(change), self.assertRaises(releaseManifest.Unverified):
                self.verified(document(dict(RELEASE, **change), self.key))
        missing = dict(RELEASE)
        del missing['hold']
        for text in (None, '[]', '"text"', 'not json'):
            with self.subTest(text), self.assertRaises(releaseManifest.Unverified):
                self.verified(document(missing, self.key, text=text))

    def test_files_that_are_not_release_files_are_refused(self):
        oversized = document(RELEASE, self.key) + b' ' * releaseManifest.LIMIT
        junk = (b'', b'{}', b'[]', b'null', b'\xff\xfe', b'{"release": 1, "signatures": []}',
                b'{"release": "{}", "signatures": {}}', b'{"release": "{}", "signatures": [1]}',
                b'{"release": "{}", "signatures": [{"key": "x", "signature": "!"}]}', oversized, 'text')
        for data in junk:
            with self.subTest(data[:40]), self.assertRaises(releaseManifest.Unverified):
                self.verified(data)

    def test_many_signature_entries_are_not_tried(self):
        good = json.loads(document(RELEASE, self.key).decode())
        good['signatures'] = [{'key': 'x', 'signature': 'eA=='}] * 4 + good['signatures']
        with self.assertRaises(releaseManifest.Unverified):
            self.verified(json.dumps(good).encode())

    def test_a_system_that_cannot_check_signatures_trusts_nothing(self):
        def broken(*arguments):
            raise releaseManifest.Unavailable('Release signatures cannot be checked here.')
        with mock.patch.object(releaseManifest, '_signed_by', broken):
            with self.assertRaises(releaseManifest.Unavailable):
                self.verified(document(RELEASE, self.key))


class ModuleTests(unittest.TestCase):
    def test_built_in_keys_are_two_different_ed25519_keys(self):
        keys = [base64.b64decode(key, validate=True) for key in releaseManifest.PUBLISHERS]
        self.assertEqual([32, 32], [len(key) for key in keys])
        self.assertNotEqual(keys[0], keys[1])

    def test_release_time_and_order(self):
        self.assertEqual(1795253405, releaseManifest.published_time(RELEASE))
        self.assertLess(releaseManifest.order('3.0', 9), releaseManifest.order('3.0', 10))
        self.assertLess(releaseManifest.order('3.0', 10), releaseManifest.order('3.1', 0))
        self.assertLess(releaseManifest.order('2.4', 9), releaseManifest.order('3.0', 1))

    def test_release_file_is_fetched_over_https_from_cyberpanel(self):
        self.assertEqual('https://cyberpanel.net/release.json', releaseManifest.URL)
        with mock.patch('plogical.panelWorkerBuild.download', return_value=b'data') as download:
            self.assertEqual(b'data', releaseManifest.fetch())
        download.assert_called_once_with(releaseManifest.URL, limit=releaseManifest.LIMIT, timeout=30)

    def test_module_runs_on_the_oldest_supported_python(self):
        options = {'feature_version': (3, 6)} if sys.version_info >= (3, 8) else {}
        ast.parse((ROOT / 'plogical' / 'releaseManifest.py').read_text(), **options)


if __name__ == '__main__':
    unittest.main()
