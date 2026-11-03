import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from plogical import olsNativeValidation as native


class DiagnosticLedgerTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.runtime = self.root / 'runtime'
        self.runtime.mkdir()
        self.binary = self.root / 'core'
        for operation in (patch.object(native, 'RUNTIME', self.runtime),
                          patch.object(native, 'checked_mount'), patch.object(native, 'overlay')):
            operation.start()
            self.addCleanup(operation.stop)

    def probe(self, script):
        self.binary.write_text('#!/bin/sh\n' + script + '\n')
        self.binary.chmod(0o755)
        with patch.dict(os.environ, CP_TEST_LEDGER=str(self.runtime / 'testconf')):
            return native.private_test(self.binary, self.root, 'different-namespace')

    def test_native_consumption_preserves_original_status_and_output(self):
        code, message = self.probe('cat "$CP_TEST_LEDGER"; rm "$CP_TEST_LEDGER"; exit 1')
        self.assertEqual((code, message), (0, ''))
        code, message = self.probe('echo "[ERROR] broken" >>"$CP_TEST_LEDGER"; cat "$CP_TEST_LEDGER"; rm "$CP_TEST_LEDGER"; exit 2')
        self.assertEqual((code, message), (2, '[ERROR] broken\n'))

    def test_false_zero_and_unread_or_replaced_ledger_are_refused(self):
        for command in ('exit 0', 'rm "$CP_TEST_LEDGER"; exit 0',
                        'cat "$CP_TEST_LEDGER" >/dev/null; rm "$CP_TEST_LEDGER"; exit 0'):
            with self.subTest(command=command), self.assertRaisesRegex(RuntimeError, 'fresh diagnostic'):
                self.probe(command)
            ledger = self.runtime / 'testconf'
            if ledger.exists():
                ledger.unlink()

    def test_host_ledger_file_and_symlink_are_preserved(self):
        ledger = self.runtime / 'testconf'
        ledger.write_text('another test')
        with self.assertRaisesRegex(RuntimeError, 'existing OLS diagnostic'):
            native.check_runtime()
        self.assertEqual(ledger.read_text(), 'another test')
        ledger.unlink()
        ledger.symlink_to(self.root / 'unknown')
        with self.assertRaisesRegex(RuntimeError, 'existing OLS diagnostic'):
            native.check_runtime()
        self.assertTrue(ledger.is_symlink())
        ledger.unlink()
        self.runtime.rmdir()
        self.runtime.symlink_to(self.root)
        with self.assertRaisesRegex(RuntimeError, 'linked'):
            native.check_runtime()
