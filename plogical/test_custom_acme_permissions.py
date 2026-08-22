#!/usr/bin/env python3
"""Permission regression tests for CustomACME private material."""

import os
import pathlib
import stat
import tempfile
import unittest
from unittest import mock

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from plogical.customACME import CustomACME, _atomic_write


class AtomicCertificateWriteTests(unittest.TestCase):
    def test_private_file_replaces_a_permissive_file_as_0600(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'privkey.pem'
            path.write_bytes(b'old')
            path.chmod(0o644)

            _atomic_write(str(path), b'new-private-key', 0o600)

            self.assertEqual(b'new-private-key', path.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))

    def test_certificate_file_is_written_as_0644(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'fullchain.pem'
            _atomic_write(str(path), b'certificate', 0o644)
            self.assertEqual(0o644, stat.S_IMODE(path.stat().st_mode))


class AccountKeyPermissionTests(unittest.TestCase):
    def _acme(self, path):
        acme = object.__new__(CustomACME)
        acme.account_key_path = str(path)
        acme.account_key = rsa.generate_private_key(
            public_exponent=65537, key_size=2048,
            backend=default_backend())
        return acme

    def test_saved_account_key_is_0600_and_loadable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'account.key'
            acme = self._acme(path)
            with mock.patch(
                    'plogical.customACME.logging.CyberCPLogFileWriter.writeToFile'):
                self.assertTrue(acme._save_account_key())

            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))
            serialization.load_pem_private_key(
                path.read_bytes(), password=None, backend=default_backend())

    def test_loading_repairs_an_existing_account_key_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = pathlib.Path(directory) / 'account.key'
            acme = self._acme(path)
            key_data = acme.account_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption(),
            )
            path.write_bytes(key_data)
            path.chmod(0o644)
            acme.account_key = None
            with mock.patch(
                    'plogical.customACME.logging.CyberCPLogFileWriter.writeToFile'):
                self.assertTrue(acme._load_account_key())

            self.assertEqual(0o600, stat.S_IMODE(path.stat().st_mode))

    def test_loading_rejects_a_symbolic_link(self):
        with tempfile.TemporaryDirectory() as directory:
            target = pathlib.Path(directory) / 'target.key'
            target.write_bytes(b'not-a-key')
            link = pathlib.Path(directory) / 'account.key'
            link.symlink_to(target)
            acme = self._acme(link)
            with mock.patch(
                    'plogical.customACME.logging.CyberCPLogFileWriter.writeToFile'):
                self.assertFalse(acme._load_account_key())
            self.assertEqual(0o644, stat.S_IMODE(target.stat().st_mode))


if __name__ == '__main__':
    unittest.main()
