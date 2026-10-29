"""Execute the production shell handoff against a failing installer."""
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class InstallerExitStatusTests(unittest.TestCase):
    def run_handoff(self, remote, status, marker):
        source = (ROOT / 'cyberpanel.sh').read_text()
        start = source.index('if [[ "$Remote_MySQL" = "On" ]] ; then\n  CP_INSTALL_MYSQL_PASSWORD=')
        end = source.index('\n}\n', start)
        fragment = source[start:end]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            stub = root / 'python-stub'
            stub.write_text('#!/bin/sh\nexit %s\n' % status)
            stub.chmod(0o755)
            log = root / 'installLogs.txt'
            log.write_text('CyberPanel installation successfully completed!,80\n' if marker else '')
            fragment = fragment.replace('/usr/local/CyberPanel/bin/python', str(stub))
            fragment = fragment.replace('/var/log/installLogs.txt', str(log))
            script = ('Remote_MySQL=%s\nMySQL_Password=test-only\nFinal_Flags=()\n'
                      'Debug_Log2() { :; }\n' % remote) + fragment + '\necho POST_INSTALL_REACHED\n'
            return subprocess.run(['bash'], input=script, text=True, capture_output=True)

    def test_failed_installer_cannot_use_stale_success_marker(self):
        for remote in ('On', 'Off'):
            with self.subTest(remote=remote):
                result = self.run_handoff(remote, 23, True)
                self.assertEqual(result.returncode, 23, result.stdout + result.stderr)
                self.assertNotIn('POST_INSTALL_REACHED', result.stdout)
                self.assertNotIn('sucessfully completed', result.stdout)

    def test_success_still_requires_completion_marker(self):
        for remote in ('On', 'Off'):
            with self.subTest(remote=remote):
                result = self.run_handoff(remote, 0, False)
                self.assertEqual(result.returncode, 1)
                self.assertNotIn('POST_INSTALL_REACHED', result.stdout)

    def test_successful_installer_can_continue(self):
        for remote in ('On', 'Off'):
            with self.subTest(remote=remote):
                result = self.run_handoff(remote, 0, True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('POST_INSTALL_REACHED', result.stdout)


if __name__ == '__main__':
    unittest.main()
