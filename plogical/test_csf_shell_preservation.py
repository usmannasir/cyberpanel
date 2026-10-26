"""Exercise shell preservation failure paths without firewall commands."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def functions():
    source = (ROOT / 'cyberpanel_upgrade.sh').read_text()
    return source[source.index('Check_CSF_Migration() {'):source.index('Set_Default_Variables() {')]


class PreservationShellTests(unittest.TestCase):
    def run_shell(self, tail, extra=None):
        env = dict(os.environ, CYBERPANEL_CSF_STATE='/untrusted-test-state')
        env.update(extra or {})
        return subprocess.run(['bash', '-c', functions() + '\n' + tail],
                              env=env, capture_output=True, text=True, timeout=10)

    def test_exit_failure_preserves_original_code(self):
        result = self.run_shell('Verify_CSF_Preservation() { return 0; }; trap CSF_Preservation_Exit EXIT; exit 17')
        self.assertEqual(17, result.returncode)

    def test_exit_verification_failure_overrides_success(self):
        result = self.run_shell('Verify_CSF_Preservation() { return 1; }; trap CSF_Preservation_Exit EXIT; exit 0')
        self.assertEqual(1, result.returncode)
        self.assertIn('no automatic firewall reset', result.stderr)

    def test_unsupported_target_is_rejected_before_python(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_shell('''
Branch_Name=v3.0.7
curl() { while [[ "$1" != "-o" ]]; do shift; done; shift; echo '# old guard' > "$1"; }
python3() { echo SHOULD_NOT_EXECUTE; }
Check_CSF_Target_Support
''', {'CYBERPANEL_CSF_STATE': temporary})
            self.assertEqual(1, result.returncode)
            self.assertNotIn('SHOULD_NOT_EXECUTE', result.stdout)

    def test_supported_target_verifies_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as temporary:
            result = self.run_shell('''
Branch_Name=v3.0.8
curl() { while [[ "$1" != "-o" ]]; do shift; done; shift; echo 'CSF_PRESERVATION_VERSION = 1' > "$1"; }
python3() { [[ "$2" = verify && "$3" = "$CYBERPANEL_CSF_STATE" ]]; }
Check_CSF_Target_Support
''', {'CYBERPANEL_CSF_STATE': temporary})
            self.assertEqual(0, result.returncode, result.stderr)

    def test_no_snapshot_verification_is_noop(self):
        result = self.run_shell('unset CYBERPANEL_CSF_STATE; Verify_CSF_Preservation')
        self.assertEqual(0, result.returncode)


if __name__ == '__main__':
    unittest.main()
