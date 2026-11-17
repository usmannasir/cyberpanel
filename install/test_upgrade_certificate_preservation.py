"""Exercise upgrade certificate handling with real RSA/ECC certificate pairs."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'cyberpanel_upgrade.sh').read_text()
FUNCTIONS = SOURCE[SOURCE.index('Existing_Certificate_Pair_Valid() {'):SOURCE.index('\nRetry_Command() {')]
TRIGGERS = SOURCE[SOURCE.index('Tmp_Output=$(timeout 3 openssl s_client -connect 127.0.0.1:8090'):
                  SOURCE.index('\nif [[ ! -f /usr/bin/cyberpanel_utility')]


class UpgradeCertificatePreservationTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.panel = self.root / 'panel'
        self.admin = self.root / 'admin'
        self.source = self.root / 'source'
        for path in (self.panel, self.admin / 'cert', self.source):
            path.mkdir(parents=True)
        self.functions = FUNCTIONS.replace('/usr/local/lscp/conf', str(self.panel)).replace(
            '/usr/local/lsws/admin/conf', str(self.admin)).replace('/usr/local/CyberCP', str(self.source))

    def pair(self, cert, key, ecc=False, default=True):
        subject = '/CN=www.example.com/emailAddress=mail@example.com' if default else '/CN=operator.example'
        algorithm = ['ec', '-pkeyopt', 'ec_paramgen_curve:P-256'] if ecc else ['rsa:2048']
        subprocess.run(['openssl', 'req', '-x509', '-newkey', *algorithm, '-nodes', '-days', '2',
                        '-subj', subject, '-keyout', str(key), '-out', str(cert)],
                       check=True, capture_output=True)
        key.chmod(0o600)
        cert.chmod(0o644)

    def run_shell(self, command):
        return subprocess.run(['bash', '-c', self.functions + '\n' + command],
                              capture_output=True, text=True, timeout=15)

    def state(self):
        result = {}
        for path in self.root.rglob('*'):
            if path.is_file() or path.is_symlink():
                st = path.lstat()
                result[str(path)] = (path.read_bytes(), st.st_mode, st.st_uid, st.st_gid,
                                     st.st_ino, st.st_mtime_ns, st.st_ctime_ns,
                                     os.readlink(path) if path.is_symlink() else None)
        return result

    def valid(self, cert, key):
        command = 'Existing_Certificate_Pair_Valid %s %s' % (shlex.quote(str(cert)), shlex.quote(str(key)))
        return self.run_shell(command).returncode == 0

    def test_default_live_probe_retains_both_valid_pairs_across_repeated_upgrades(self):
        self.pair(self.panel / 'cert.pem', self.panel / 'key.pem')
        self.pair(self.admin / 'cert/admin.crt', self.admin / 'cert/admin.key')
        before = self.state()
        for _ in range(2):
            result = self.run_shell('timeout() { printf "subject=emailAddress=mail@example.com\\n"; }\n' + TRIGGERS)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.count('Preserving the existing certificate'), 2)
            self.assertEqual(self.state(), before)
        self.assertFalse((self.source / 'cert_conf').exists())

    def test_custom_ecc_pair_is_preserved(self):
        self.pair(self.panel / 'cert.pem', self.panel / 'key.pem', ecc=True, default=False)
        before = self.state()
        result = self.run_shell('Regenerate_Cert 8090')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.state(), before)

    def test_symlinked_valid_pair_preserves_links_targets_and_metadata(self):
        self.pair(self.root / 'actual.crt', self.root / 'actual.key')
        (self.panel / 'cert.pem').symlink_to(self.root / 'actual.crt')
        (self.panel / 'key.pem').symlink_to(self.root / 'actual.key')
        before = self.state()
        self.assertEqual(self.run_shell('Regenerate_Cert 8090').returncode, 0)
        self.assertEqual(self.state(), before)

    def test_legacy_webadmin_valid_pair_is_preserved(self):
        self.pair(self.admin / 'webadmin.crt', self.admin / 'webadmin.key')
        before = self.state()
        self.assertEqual(self.run_shell('Regenerate_Cert 7080').returncode, 0)
        self.assertEqual(self.state(), before)

    def test_mismatched_pair_is_not_mistaken_for_valid_identity(self):
        cert, key = self.panel / 'cert.pem', self.panel / 'key.pem'
        self.pair(cert, key)
        self.pair(self.root / 'other.crt', self.root / 'other.key')
        key.write_bytes((self.root / 'other.key').read_bytes())
        self.assertFalse(self.valid(cert, key))
        self.assertEqual(self.run_shell('Regenerate_Cert 8090').returncode, 0)
        self.assertTrue(self.valid(cert, key))

    def test_expired_pair_keeps_existing_repair_behavior(self):
        cert, key = self.panel / 'cert.pem', self.panel / 'key.pem'
        self.pair(cert, key)
        subprocess.run(['openssl', 'x509', '-in', str(cert), '-signkey', str(key), '-days', '-1',
                        '-out', str(self.root / 'expired.crt')], check=True, capture_output=True)
        cert.write_bytes((self.root / 'expired.crt').read_bytes())
        self.assertFalse(self.valid(cert, key))
        self.assertEqual(self.run_shell('Regenerate_Cert 8090').returncode, 0)
        self.assertTrue(self.valid(cert, key))

    def test_missing_or_corrupt_default_pair_keeps_existing_repair_behavior(self):
        cert, key = self.panel / 'cert.pem', self.panel / 'key.pem'
        for state in ('missing', 'corrupt'):
            with self.subTest(state=state):
                cert.unlink(missing_ok=True)
                key.unlink(missing_ok=True)
                if state == 'corrupt':
                    cert.write_text('not a certificate')
                    key.write_text('not a private key')
                self.assertFalse(self.valid(cert, key))
                self.assertEqual(self.run_shell('Regenerate_Cert 8090').returncode, 0)
                self.assertTrue(self.valid(cert, key))

    def test_nonregular_inputs_refuse_without_reading_fifo(self):
        cert, key = self.panel / 'cert.pem', self.panel / 'key.pem'
        self.pair(cert, key)
        cert.unlink()
        os.mkfifo(cert)
        self.assertFalse(self.valid(cert, key))


if __name__ == '__main__':
    unittest.main()
