"""Atomic isolated configuration tests; no shell, real credentials or customer files."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from plogical.gdriveConfig import write_remote


class ConfigTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name).resolve()
        self.credentials = {'token': 'SYNTHETIC-ACCESS', 'refresh_token': 'SYNTHETIC-REFRESH',
                            'client_id': 'synthetic.apps.googleusercontent.com',
                            'client_secret': 'SYNTHETIC-CLIENT',
                            'expiry': (datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}
        self.config = self.home / '.config/rclone/rclone.conf'

    def test_private_owned_config_preserves_existing_remote_verbatim(self):
        self.config.parent.mkdir(parents=True, mode=0o700)
        old = b'# preserve this comment\n[existing]\ntype = sftp\nhost = existing.example\n'
        self.config.write_bytes(old)
        self.config.chmod(0o600)
        write_remote(self.home, 'new-drive', self.credentials)
        data = self.config.read_bytes()
        self.assertTrue(data.startswith(old))
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o600)
        self.assertIn(b'scope = drive.file', data)
        token = json.loads(data.split(b'token = ')[1])
        self.assertEqual(token['expiry'], self.credentials['expiry'])

    def test_existing_account_is_not_overwritten(self):
        write_remote(self.home, 'drive', self.credentials)
        old = self.config.read_bytes()
        with self.assertRaises(ValueError):
            write_remote(self.home, 'drive', self.credentials)
        self.assertEqual(self.config.read_bytes(), old)

    def test_malformed_secrets_or_name_cannot_inject_config(self):
        for field in ('account', 'client_id', 'client_secret', 'token', 'refresh_token'):
            credentials = self.credentials.copy()
            account = 'drive'
            if field == 'account': account = 'name\n[another]'
            else: credentials[field] = 'secret\n[another]'
            with self.subTest(field=field), self.assertRaises(ValueError):
                write_remote(self.home, account, credentials)
        self.assertFalse(self.config.exists())

    def test_symlinked_config_is_not_followed(self):
        self.config.parent.mkdir(parents=True, mode=0o700)
        victim = self.home / 'must-remain'
        victim.write_text('unchanged')
        self.config.symlink_to(victim)
        with self.assertRaises(OSError):
            write_remote(self.home, 'drive', self.credentials)
        self.assertEqual(victim.read_text(), 'unchanged')

    def test_symlinked_directory_is_not_followed(self):
        victim = self.home / 'must-remain'
        victim.mkdir()
        (self.home / '.config').symlink_to(victim, target_is_directory=True)
        with self.assertRaises(ValueError):
            write_remote(self.home, 'drive', self.credentials)
        self.assertEqual(list(victim.iterdir()), [])

    def test_expired_token_does_not_create_configuration(self):
        self.credentials['expiry'] = '2024-04-08T21:53:00Z'
        with self.assertRaises(ValueError):
            write_remote(self.home, 'drive', self.credentials)
        self.assertFalse(self.config.exists())

    def test_atomic_replace_failure_preserves_existing_file(self):
        write_remote(self.home, 'drive', self.credentials)
        old = self.config.read_bytes()
        with mock.patch('plogical.gdriveConfig.os.replace', side_effect=OSError()), self.assertRaises(OSError):
            write_remote(self.home, 'second-drive', self.credentials)
        self.assertEqual(self.config.read_bytes(), old)
        self.assertEqual(list(self.config.parent.glob('.gdrive-*')), [self.config.parent / '.gdrive-oauth.lock'])

    def test_concurrent_native_replacement_is_not_overwritten(self):
        write_remote(self.home, 'drive', self.credentials)
        native = b'[native-update]\ntype = local\n'
        original_fsync = os.fsync
        def edit(fd):
            original_fsync(fd)
            replacement = self.config.with_name('native.conf')
            replacement.write_bytes(native)
            replacement.chmod(0o600)
            os.replace(replacement, self.config)
        with mock.patch('plogical.gdriveConfig.os.fsync', side_effect=edit), self.assertRaises(ValueError):
            write_remote(self.home, 'second-drive', self.credentials)
        self.assertEqual(self.config.read_bytes(), native)

    def test_new_config_created_concurrently_is_not_overwritten(self):
        native = b'[native-update]\ntype = local\n'
        original_fsync = os.fsync
        def edit(fd):
            original_fsync(fd)
            self.config.write_bytes(native)
            self.config.chmod(0o600)
        with mock.patch('plogical.gdriveConfig.os.fsync', side_effect=edit), self.assertRaises(ValueError):
            write_remote(self.home, 'drive', self.credentials)
        self.assertEqual(self.config.read_bytes(), native)


if __name__ == '__main__':
    unittest.main()
