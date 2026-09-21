"""Run the real main-upgrade logging block against a disposable Python process."""
import os
from pathlib import Path
import selectors
import shlex
import subprocess
import sys
import tempfile
import time
import unittest


SOURCE = (Path(__file__).resolve().parents[1] / 'cyberpanel_upgrade.sh').read_text()


class UpgradeLiveOutputTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='upgrade-output-test-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.log = self.root / 'upgrade.log'
        start = SOURCE.index('Main_Upgrade() {')
        end = SOURCE.index('# Check if the command was successful', start)
        self.code = SOURCE[start:end] + '\nreturn "$RETURN_CODE"\n}\nMain_Upgrade\n'
        self.code = self.code.replace('/usr/local/CyberPanel/bin/python', shlex.quote(sys.executable))
        self.code = self.code.replace('/var/log/cyberpanel_upgrade_debug.log', shlex.quote(str(self.log)))
        self.code = self.code.replace('/tmp/cyberpanel-upgrade-output.XXXXXX', shlex.quote(str(self.root / 'output.XXXXXX')))
        self.env = dict(os.environ, Branch_Name='v3.0.6')

    def run_upgrade(self, source, **environment):
        (self.root / 'upgrade.py').write_text(source)
        return subprocess.run(['/bin/bash', '-c', self.code], cwd=self.root,
                              env=dict(self.env, **environment), capture_output=True,
                              text=True, timeout=10)

    def test_progress_reaches_console_and_log_while_upgrade_is_running(self):
        # No flush=True: the production invocation must disable Python buffering.
        (self.root / 'upgrade.py').write_text('''
import pathlib
import sys
import time
print('LIVE-UPGRADE-PROGRESS')
print('LIVE-UPGRADE-STDERR', file=sys.stderr)
while not pathlib.Path('release').exists():
    time.sleep(0.02)
print('UPGRADE-FINISHED')
''')
        process = subprocess.Popen(['/bin/bash', '-c', self.code], cwd=self.root,
                                   env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        output = b''
        try:
            with selectors.DefaultSelector() as selector:
                selector.register(process.stdout, selectors.EVENT_READ)
                deadline = time.monotonic() + 5
                while b'LIVE-UPGRADE-STDERR' not in output and time.monotonic() < deadline:
                    if selector.select(timeout=0.1):
                        chunk = os.read(process.stdout.fileno(), 65536)
                        if not chunk:
                            break
                        output += chunk
            self.assertIn(b'LIVE-UPGRADE-PROGRESS', output)
            self.assertIn(b'LIVE-UPGRADE-STDERR', output)
            self.assertIsNone(process.poll())
            self.assertIn('LIVE-UPGRADE-PROGRESS', self.log.read_text())
        finally:
            (self.root / 'release').touch()
            remaining, errors = process.communicate(timeout=10)
            process.stdout.close()
            process.stderr.close()
        self.assertEqual(0, process.returncode, errors)
        self.assertIn(b'UPGRADE-FINISHED', remaining)
        self.assertEqual([], list(self.root.glob('output.*')))

    def test_python_failure_survives_successful_tee(self):
        result = self.run_upgrade("print('failure detail')\nraise SystemExit(37)\n")
        self.assertEqual(37, result.returncode)
        self.assertIn('failure detail', self.log.read_text())
        self.assertEqual([], list(self.root.glob('output.*')))

    def test_legacy_completion_detection_uses_only_this_run(self):
        self.log.write_text('Upgrade Completed\n')
        error = "print('TypeError: expected string or bytes-like object')\n"
        self.assertEqual(37, self.run_upgrade(error + 'raise SystemExit(37)\n').returncode)
        self.assertEqual(0, self.run_upgrade(error + "print('Upgrade Completed')\nraise SystemExit(37)\n").returncode)

    def test_logging_failure_cannot_become_success(self):
        commands = self.root / 'commands'
        commands.mkdir()
        tee = commands / 'tee'
        tee.write_text('#!/bin/sh\ncat\nexit 23\n')
        tee.chmod(0o755)
        result = self.run_upgrade("print('completed')\n", PATH=str(commands) + ':' + os.environ['PATH'])
        self.assertEqual(23, result.returncode)


if __name__ == '__main__':
    unittest.main()
