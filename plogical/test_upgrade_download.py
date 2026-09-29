"""Download failures cannot block browser upgrades or admit partial artifacts."""
import ast
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch


class UpgradeDownloadTests(unittest.TestCase):
    def setUp(self):
        tree = ast.parse(Path(__file__).with_name('upgrade.py').read_text())
        upgrade = next(node for node in tree.body
                       if isinstance(node, ast.ClassDef) and node.name == 'Upgrade')
        upgrade.body = [node for node in upgrade.body
                        if isinstance(node, ast.FunctionDef)
                        and node.name in ('downloadCustomBinary', 'verifyChecksum')]
        tree.body = [upgrade]
        namespace = dict(os=os, re=re, subprocess=subprocess)
        exec(compile(tree, 'upgrade.py', 'exec'), namespace)
        self.upgrade = namespace['Upgrade']
        self.messages = []
        self.upgrade.stdOut = lambda message, level: self.messages.append(message)
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.destination = str(self.root / 'candidate with spaces')
        self.url = 'https://example.invalid/binary?token=one&part=two'
        self.real_run = subprocess.run

    def fake_wget(self, exit_code=0, size=20000):
        wget = self.root / 'wget'
        wget.write_text('#!' + sys.executable + '\n' + '''
import os, sys
assert sys.argv[1:5] == ['-q', '--timeout=30', '--tries=3', '-O']
assert sys.argv[6:] == ['--', %r]
# More output than a pipe/socket buffer: neither stream may be inherited.
os.write(1, b'x' * 1048576)
os.write(2, b'x' * 1048576)
with open(sys.argv[5], 'wb') as target:
    target.write(b'a' * %d)
sys.exit(%d)
''' % (self.url, size, exit_code))
        wget.chmod(0o755)

    def download(self):
        def run(argv, stdout, stderr, timeout):
            self.assertEqual(subprocess.DEVNULL, stdout)
            self.assertEqual(subprocess.DEVNULL, stderr)
            self.assertEqual(600, timeout)
            # Test itself must not hang if a downloader regresses.
            return self.real_run(argv, stdout=stdout, stderr=stderr, timeout=5)
        with patch.dict(os.environ, {'PATH': str(self.root) + os.pathsep + os.environ['PATH']}), \
                patch.object(subprocess, 'run', side_effect=run):
            return self.upgrade.downloadCustomBinary(self.url, self.destination)

    def test_noisy_child_does_not_fill_browser_output_and_checksum_is_required(self):
        self.fake_wget()
        self.assertTrue(self.download())
        checksum = hashlib.sha256(b'a' * 20000).hexdigest()
        self.assertTrue(self.upgrade.verifyChecksum(self.destination, checksum))
        self.assertFalse(self.upgrade.verifyChecksum(self.destination, '0' * 64))
        self.assertFalse(self.upgrade.verifyChecksum(self.destination, None))

    def test_nonzero_exit_rejects_large_partial_download(self):
        self.fake_wget(exit_code=4)
        self.assertFalse(self.download())
        self.assertGreater(os.path.getsize(self.destination), 10240)
        self.assertTrue(any('wget exit 4' in message for message in self.messages))
        self.assertFalse(any('Downloaded successfully' in message for message in self.messages))

    def test_small_successful_response_is_rejected(self):
        self.fake_wget(size=10)
        self.assertFalse(self.download())

    def test_total_timeout_rejects_existing_large_partial_file(self):
        Path(self.destination).write_bytes(b'a' * 20000)
        with patch.object(subprocess, 'run', side_effect=subprocess.TimeoutExpired('wget', 600)):
            self.assertFalse(self.upgrade.downloadCustomBinary(self.url, self.destination))
        self.assertTrue(any('timed out' in message for message in self.messages))


if __name__ == '__main__':
    unittest.main()
