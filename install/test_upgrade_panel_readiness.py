"""Run the real final upgrade check against controlled HTTP startup responses."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class PanelReadinessTests(unittest.TestCase):
    def run_check(self, responses, failed=0):
        source = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        function = source.split('Post_Install_Display_Final_Info() {', 1)[1].split('\nRestart_Web_Terminal() {', 1)[0]
        function = 'Post_Install_Display_Final_Info() {' + function
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'bind.conf').write_text('*:8090')
            (root / 'responses').write_text('\n'.join(responses) + '\n')
            for name, content in {
                'curl': '''echo "$*" >> "$EVENTS"
n=$(cat "$COUNT" 2>/dev/null || echo 0); n=$((n+1)); echo "$n" > "$COUNT"
line=$(sed -n "${n}p" "$RESPONSES"); [ -n "$line" ] || line=503
if [ "$line" = timeout ]; then printf 000; exit 28; fi
printf '%s' "$line"
''',
                'sleep': 'echo sleep >> "$SLEEPS"\n',
                'rm': 'exit 0\n',
            }.items():
                p = root / name
                p.write_text('#!/bin/bash\n' + content)
                p.chmod(0o755)
            function = function.replace('/usr/local/lscp/conf/bind.conf', str(root / 'bind.conf'))
            env = dict(os.environ, PATH=str(root) + os.pathsep + os.environ['PATH'],
                       EVENTS=str(root / 'events'), COUNT=str(root / 'count'),
                       RESPONSES=str(root / 'responses'), SLEEPS=str(root / 'sleeps'))
            result = subprocess.run(['bash', '-c', function + '\nUPGRADE_FAILED=%s\nPost_Install_Display_Final_Info' % failed],
                                    env=env, text=True, capture_output=True, timeout=5)
            calls = (root / 'events').read_text().splitlines() if (root / 'events').exists() else []
            sleeps = (root / 'sleeps').read_text().splitlines() if (root / 'sleeps').exists() else []
            return result, calls, sleeps

    def test_503_then_200_waits_for_startup(self):
        result, calls, sleeps = self.run_check(['503', '200'])
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(sleeps), 1)
        self.assertIn('CyberPanel Upgraded', result.stdout)

    def test_transport_timeout_then_ready(self):
        result, calls, _ = self.run_check(['timeout', '200'])
        self.assertEqual(result.returncode, 0)
        self.assertEqual(len(calls), 2)

    def test_persistent_failure_is_bounded_and_nonzero(self):
        for response in ('503', 'timeout'):
            with self.subTest(response=response):
                result, calls, sleeps = self.run_check([response] * 20)
                self.assertEqual(result.returncode, 1)
                self.assertEqual(len(calls), 10)
                self.assertEqual(len(sleeps), 9)
                self.assertNotIn('CyberPanel Upgraded', result.stdout)
                for call in calls:
                    self.assertIn('--connect-timeout 2', call)
                    self.assertIn('--max-time 5', call)

    def test_prior_required_stage_failure_cannot_be_masked(self):
        result, calls, _ = self.run_check(['200'], failed=1)
        self.assertEqual(result.returncode, 1)
        self.assertNotIn('CyberPanel Upgraded', result.stdout)
        self.assertEqual(calls, [])

    def test_existing_ready_statuses_still_succeed_immediately(self):
        for status in ('200', '302', '401', '403'):
            with self.subTest(status=status):
                result, calls, sleeps = self.run_check([status])
                self.assertEqual(result.returncode, 0)
                self.assertEqual(len(calls), 1)
                self.assertEqual(sleeps, [])


if __name__ == '__main__':
    unittest.main()
