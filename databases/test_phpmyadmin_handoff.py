import hashlib
import json
import os
import pathlib
import stat
import tempfile
import unittest

from databases.phpmyadmin_handoff import create_handoff


class PhpMyAdminHandoffTests(unittest.TestCase):
    def test_creates_private_short_lived_token_record(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff_dir = pathlib.Path(directory) / 'handoff'
            path = create_handoff(
                'admin', 'unpredictable-token', directory=handoff_dir,
                now=1_000, ttl=120,
            )

            self.assertEqual(
                hashlib.sha256(b'unpredictable-token').hexdigest(),
                path.name,
            )
            self.assertEqual(0o700, handoff_dir.stat().st_mode & 0o777)
            self.assertEqual(0o600, path.stat().st_mode & 0o777)
            self.assertEqual(
                {'username': 'admin', 'expires': 1_120},
                json.loads(path.read_text(encoding='utf-8')),
            )

    def test_rejects_insecure_existing_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff_dir = pathlib.Path(directory) / 'handoff'
            handoff_dir.mkdir(mode=0o755)
            handoff_dir.chmod(0o755)

            with self.assertRaises(PermissionError):
                create_handoff(
                    'admin', 'token', directory=handoff_dir, now=1_000,
                )

    def test_refuses_to_replace_existing_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff_dir = pathlib.Path(directory) / 'handoff'
            create_handoff(
                'admin', 'same-token', directory=handoff_dir, now=1_000,
            )

            with self.assertRaises(FileExistsError):
                create_handoff(
                    'admin', 'same-token', directory=handoff_dir, now=1_001,
                )

    def test_removes_only_expired_private_regular_records(self):
        with tempfile.TemporaryDirectory() as directory:
            handoff_dir = pathlib.Path(directory) / 'handoff'
            expired = create_handoff(
                'admin', 'old-token', directory=handoff_dir,
                now=1_000, ttl=10,
            )
            os.utime(expired, (1_000, 1_000))
            unrelated = handoff_dir / 'not-a-token'
            unrelated.write_text('keep', encoding='utf-8')
            unrelated.chmod(0o600)

            create_handoff(
                'admin', 'new-token', directory=handoff_dir,
                now=2_000, ttl=120,
            )

            self.assertFalse(expired.exists())
            self.assertTrue(unrelated.exists())


if __name__ == '__main__':
    unittest.main()
