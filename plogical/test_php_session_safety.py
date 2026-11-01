"""Private-filesystem tests; never invoke a production session setup/cleaner."""
import ast
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import time
import unittest
from unittest import mock

from plogical import phpSessionSafety as safety


ROOT = Path(__file__).resolve().parents[1]
TEST_ROOT = os.environ.get('CP_SESSION_TEST_ROOT')
PHP = os.environ.get('CP_SESSION_TEST_PHP')


class IntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not hasattr(os, 'geteuid') or os.geteuid() != 0 or not TEST_ROOT:
            raise unittest.SkipTest('Requires root and an explicit trusted private CP_SESSION_TEST_ROOT')
        root = Path(TEST_ROOT)
        if not root.is_dir():
            raise RuntimeError('Explicit private test root must already exist')

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=TEST_ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.path = self.root / 'cleansessions'

    def legacy(self):
        self.path.write_bytes(safety.LEGACY_CLEANER)
        self.path.chmod(0o750)
        return self.path.stat()

    def backup(self):
        return self.path.with_name('cleansessions.disabled-' + hashlib.sha256(safety.LEGACY_CLEANER).hexdigest())

    def test_exact_legacy_replaced_with_private_backup_and_noop(self):
        before = self.legacy()
        self.assertEqual(safety.retire_legacy_cleaner(self.path), 'retired')
        self.assertEqual(self.backup().read_bytes(), safety.LEGACY_CLEANER)
        self.assertEqual(stat.S_IMODE(self.backup().stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.path.stat().st_mode), stat.S_IMODE(before.st_mode))
        self.assertEqual(self.path.stat().st_uid, before.st_uid)
        self.assertEqual(self.path.stat().st_gid, before.st_gid)
        self.assertEqual(self.path.read_bytes(), safety.RETIRED_CLEANER)
        subprocess.run([str(self.path)], check=True, timeout=5)

    def test_missing_helper_does_not_create_cleaner_or_cron(self):
        self.assertEqual(safety.retire_legacy_cleaner(self.path), 'absent')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_custom_helper_and_cron_unchanged(self):
        self.path.write_bytes(safety.LEGACY_CLEANER + b'# custom policy\n')
        self.path.chmod(0o700)
        cron = self.root / 'crontab'
        cron.write_text('09,39 * * * * /custom/application-cleaner\n')
        before = (self.path.read_bytes(), self.path.stat(), cron.read_bytes(), cron.stat())
        self.assertEqual(safety.retire_legacy_cleaner(self.path), 'custom-preserved')
        self.assertEqual((self.path.read_bytes(), self.path.stat(), cron.read_bytes(), cron.stat()), before)
        self.assertFalse(self.backup().exists())

    def test_second_run_preserves_inode_and_times(self):
        self.legacy()
        safety.retire_legacy_cleaner(self.path)
        before = self.path.stat()
        self.assertEqual(safety.retire_legacy_cleaner(self.path), 'already-retired')
        self.assertEqual(self.path.stat(), before)
        self.assertEqual(len(list(self.root.iterdir())), 2)

    def test_symlink_and_hardlink_refused(self):
        target = self.root / 'original'
        target.write_bytes(safety.LEGACY_CLEANER)
        self.path.symlink_to(target)
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(self.path)
        self.path.unlink()
        os.link(str(target), str(self.path))
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(self.path)
        self.assertEqual(target.read_bytes(), safety.LEGACY_CLEANER)

    def test_writable_and_nonroot_files_refused(self):
        self.legacy()
        self.path.chmod(0o777)
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(self.path)
        self.path.chmod(0o700)
        os.chown(str(self.path), 65534, 65534)
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(self.path)
        self.assertEqual(self.path.read_bytes(), safety.LEGACY_CLEANER)

    def test_symlink_or_writable_parent_refused(self):
        real = self.root / 'real'
        real.mkdir()
        nested = real / 'cleansessions'
        nested.write_bytes(safety.LEGACY_CLEANER)
        alias = self.root / 'alias'
        alias.symlink_to(real, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(alias / 'cleansessions')
        real.chmod(0o777)
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(nested)

    def test_backup_conflict_refused_without_replacing_cleaner(self):
        self.legacy()
        self.backup().write_bytes(b'foreign data')
        with self.assertRaises(RuntimeError):
            safety.retire_legacy_cleaner(self.path)
        self.assertEqual(self.path.read_bytes(), safety.LEGACY_CLEANER)

    def assert_unverified(self):
        messages = []
        self.assertEqual(safety.report_retirement(self.path, log=messages.append), 'unverified')
        self.assertEqual(len(messages), 1)
        self.assertIn('retirement not verified; manual review required', messages[0])
        self.assertIn('may have changed', messages[0])
        self.assertNotIn('were preserved', messages[0])

    def test_report_symlink_refusal_does_not_abort_upgrade(self):
        target = self.root / 'target'
        target.write_bytes(safety.LEGACY_CLEANER)
        self.path.symlink_to(target)
        self.assert_unverified()
        self.assertEqual(target.read_bytes(), safety.LEGACY_CLEANER)

    def test_report_backup_conflict_does_not_abort_upgrade(self):
        self.legacy()
        self.backup().write_bytes(b'foreign backup')
        self.assert_unverified()
        self.assertEqual(self.path.read_bytes(), safety.LEGACY_CLEANER)

    def test_report_backup_write_failure_does_not_abort_upgrade(self):
        self.legacy()
        with mock.patch.object(safety.os, 'open', side_effect=OSError('fixture backup write refused')):
            self.assert_unverified()
        self.assertEqual(self.path.read_bytes(), safety.LEGACY_CLEANER)

    def test_report_postreplace_fsync_failure_is_unverified_not_unchanged(self):
        self.legacy()
        real_fsync = safety.os.fsync
        calls = []

        def fail_directory_fsync(fd):
            calls.append(fd)
            if len(calls) == 3:
                raise OSError('fixture directory durability failure after replacement')
            return real_fsync(fd)

        with mock.patch.object(safety.os, 'fsync', side_effect=fail_directory_fsync):
            self.assert_unverified()
        self.assertEqual(self.path.read_bytes(), safety.RETIRED_CLEANER)
        self.assertEqual(self.backup().read_bytes(), safety.LEGACY_CLEANER)

    def test_concurrent_edit_preserved_and_temp_removed(self):
        self.legacy()
        real_trusted = safety._trusted_file
        calls = []

        def concurrent(path):
            if path == self.path:
                calls.append(path)
                if len(calls) == 2:
                    self.path.write_bytes(b'operator replacement\n')
            return real_trusted(path)

        with mock.patch.object(safety, '_trusted_file', side_effect=concurrent):
            with self.assertRaises(RuntimeError):
                safety.retire_legacy_cleaner(self.path)
        self.assertEqual(self.path.read_bytes(), b'operator replacement\n')
        self.assertFalse(list(self.root.glob('.cleansessions-retire-*')))

    def test_real_php_long_and_short_sessions_and_over_10000_files_survive(self):
        if not PHP or not Path(PHP).is_file():
            self.skipTest('Requires explicit CP_SESSION_TEST_PHP executable')
        sessions = self.root / 'application-sessions'
        sessions.mkdir(mode=0o700)
        ini = self.root / 'php.ini'
        ini.write_text('session.gc_maxlifetime=1440\nsession.save_path="%s"\n' % sessions)
        script = ("ini_set('session.gc_probability', '0');"
                  "ini_set('session.gc_maxlifetime', $argv[1]);"
                  "session_id($argv[2]); session_start();"
                  "$_SESSION['marker']='preserved-session'; session_write_close();")
        for lifetime, name in ((7200, 'longlifetimefixture'), (1440, 'shortlifetimefixture'),
                               (14400, 'extendedlifetimefixture')):
            subprocess.run([PHP, '-n', '-c', str(ini), '-r', script, '--', str(lifetime), name], check=True, timeout=10)
        for number in range(10001):
            (sessions / ('sess_other%05d' % number)).write_bytes(b'fixture')
        age = time.time() - 2000
        for path in sessions.iterdir():
            os.utime(str(path), (age, age))
        extended_age = time.time() - 10000
        os.utime(str(sessions / 'sess_extendedlifetimefixture'), (extended_age, extended_age))
        before = {p.name: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in sessions.iterdir()}
        ini_before = ini.read_bytes()
        self.legacy()
        safety.retire_legacy_cleaner(self.path)
        subprocess.run([str(self.path)], check=True, timeout=5)
        after = {p.name: (p.read_bytes(), p.stat().st_mode, p.stat().st_mtime_ns, p.stat().st_ctime_ns) for p in sessions.iterdir()}
        self.assertEqual(after, before)
        self.assertEqual(ini.read_bytes(), ini_before)
        read = ("ini_set('session.gc_probability','0'); ini_set('session.gc_maxlifetime','7200');"
                "session_id('longlifetimefixture');session_start();echo $_SESSION['marker'];session_write_close();")
        result = subprocess.run([PHP, '-n', '-c', str(ini), '-r', read], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, check=True, timeout=10)
        self.assertEqual(result.stdout, 'preserved-session')


class WiringTests(unittest.TestCase):
    def test_exact_fingerprint_is_generated_by_baseline_script(self):
        # Pinned from the actual shipped heredoc, not a private fixture file.
        self.assertEqual(hashlib.sha256(safety.LEGACY_CLEANER).hexdigest(),
                         '3292dd4fc7cc89267cfa1f0bb1d44130d0d2787dc17b5afe0cce0f752a562f20')

    def test_setup_generates_noop_and_other_behavior_is_unchanged(self):
        setup = (ROOT / 'CPScripts/setup_php_sessions.sh').read_text()
        generated = setup.split('<<"EOL"\n', 1)[1].split('\nEOL', 1)[0] + '\n'
        self.assertEqual(generated.encode(), safety.RETIRED_CLEANER)
        restored = setup.replace(safety.RETIRED_CLEANER.decode(), safety.LEGACY_CLEANER.decode())
        restored = restored.replace('echo "WARNING: No new global PHP session purge is provisioned. Review any existing cleaner; configure application-specific cleanup and monitor session storage."\n', '')
        # The complete original script's independently recorded source hash
        # proves initialization/restart/configuration behavior did not change.
        self.assertEqual(hashlib.sha256(restored.encode('utf-8')).hexdigest(),
                         '05a58d4eecc49874007922c60d2f46b6b7ad9c99bf79c37c2db11d009fcfc1d2')

    def test_upgrade_call_follows_successful_source_copy(self):
        source = (ROOT / 'plogical/upgrade.py').read_text(encoding='utf-8')
        module = ast.parse(source)
        upgrade = next(node for node in ast.walk(module) if isinstance(node, ast.FunctionDef) and node.name == 'upgrade')
        calls = [(node.lineno, ast.dump(node.func)) for node in ast.walk(upgrade) if isinstance(node, ast.Call)]
        download_line = next(line for line, func in calls if "attr='downloadAndUpgrade'" in func)
        safety_line = next(line for line, func in calls if "id='report_retirement'" in func)
        self.assertGreater(safety_line, download_line)
        self.assertIn('report_retirement(log=Upgrade.stdOut)', source)

    def test_explicit_warning_and_unknown_preservation(self):
        for result, term in (('retired', 'monitor session storage'), ('custom-preserved', 'preserved'), ('absent', 'No CyberPanel global session purge')):
            messages = []
            with mock.patch.object(safety, 'retire_legacy_cleaner', return_value=result):
                self.assertEqual(safety.report_retirement(log=messages.append), result)
            self.assertIn(term, messages[0])


if __name__ == '__main__':
    unittest.main()
