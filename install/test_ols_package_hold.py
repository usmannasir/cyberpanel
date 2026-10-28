"""Run the real guard before destructive fake APT upgrade commands."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'cyberpanel_upgrade.sh').read_text()
GUARD = SOURCE.split('Protect_Custom_OLS_From_APT() {', 1)[1].split('\nCheck_OS() {', 1)[0]
GUARD = 'Protect_Custom_OLS_From_APT() {' + GUARD
UPGRADES = [line.strip() for line in SOURCE.splitlines()
            if re.match(r'^\s*(?:DEBIAN_[A-Z_]+=\S+\s+)*(?:apt|apt-get)\s.*\bupgrade -y', line)]


class PackageHoldTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.core = self.root / 'core'
        self.core.write_text('#!/bin/bash\n# cyberpanel_lsi_api_abi_v1\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        self.core.chmod(0o755)
        self.module = self.root / 'module'
        self.module.write_text('ELF cyberpanel_lsi_api_abi_v1')
        self.release = self.root / 'os-release'
        self.release.write_text('ID=ubuntu\nVERSION_ID="26.04"\n')
        self.holds = self.root / 'holds'
        self.holds.write_text('other-package\n')
        self.events = self.root / 'events'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name, body in {
            'timeout': '[ "$1" = 30 ] || exit 99; shift; [ "${SIMULATE_TIMEOUT:-0}" = 0 ] || exit 124; exec "$@"',
            'dpkg-query': 'printf "%s" "${PACKAGE_STATUS:-install ok installed}"',
            'apt-mark': '''echo "apt-mark $*" >> "$EVENTS"
case "$1" in
showhold) [ "${SHOWHOLD_FAIL:-0}" = 0 ] || exit 1; cat "$HOLDS";;
hold) [ "${HOLD_FAIL:-0}" = 0 ] || exit 1; [ "${HOLD_NOOP:-0}" = 1 ] || echo "$2" >> "$HOLDS";;
*) exit 99;;
esac''',
            'apt': '''echo "apt $*" >> "$EVENTS"
if ! grep -Fxq openlitespeed "$HOLDS"; then printf 'stock replacement' > "$CORE"; fi''',
            'apt-get': '''echo "apt-get $*" >> "$EVENTS"
if ! grep -Fxq openlitespeed "$HOLDS"; then printf 'stock replacement' > "$CORE"; fi''',
        }.items():
            path = self.bin / name
            path.write_text('#!/bin/bash\n' + body + '\n')
            path.chmod(0o755)
        self.guard = GUARD.replace('/etc/os-release', str(self.release)).replace(
            '/usr/local/lsws/bin/openlitespeed', str(self.core)).replace(
            '/usr/local/lsws/modules/cyberpanel_ols.so', str(self.module))

    def run_upgrade(self, command=None, **env):
        environment = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                           CORE=str(self.core), HOLDS=str(self.holds), EVENTS=str(self.events))
        environment.update(env)
        return subprocess.run(['bash', '-c', self.guard + '\nProtect_Custom_OLS_From_APT || exit 1\n' +
                               (command or UPGRADES[0])], env=environment, capture_output=True, text=True)

    def assert_no_apt(self):
        events = self.events.read_text() if self.events.exists() else ''
        self.assertNotRegex(events, r'(?m)^apt(?:-get)? ')

    def test_every_real_apt_upgrade_path_preserves_custom_bytes(self):
        self.assertEqual(len(UPGRADES), 2)
        original = self.core.read_bytes()
        for command in UPGRADES:
            with self.subTest(command=command):
                self.holds.write_text('other-package\n')
                self.events.write_text('')
                result = self.run_upgrade(command)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.core.read_bytes(), original)
                events = self.events.read_text()
                self.assertLess(events.index('apt-mark hold openlitespeed'),
                                re.search(r'(?m)^apt(?:-get)? ', events).start())

    def test_hold_failure_aborts_before_destructive_upgrade(self):
        original = self.core.read_bytes()
        self.assertNotEqual(self.run_upgrade(HOLD_FAIL='1').returncode, 0)
        self.assertEqual(self.core.read_bytes(), original)
        self.assert_no_apt()

    def test_success_without_effective_hold_aborts(self):
        self.assertNotEqual(self.run_upgrade(HOLD_NOOP='1').returncode, 0)
        self.assert_no_apt()

    def test_cannot_read_holds_aborts(self):
        self.assertNotEqual(self.run_upgrade(SHOWHOLD_FAIL='1').returncode, 0)
        self.assert_no_apt()

    def test_existing_hold_is_preserved_without_rewriting(self):
        self.holds.write_text('other-package\nopenlitespeed\n')
        self.assertEqual(self.run_upgrade(PACKAGE_STATUS='hold ok installed').returncode, 0)
        self.assertEqual(self.holds.read_text(), 'other-package\nopenlitespeed\n')
        self.assertNotIn('apt-mark hold ', self.events.read_text())

    def test_stock_ubuntu20_with_leftover_module_is_not_held(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="20.04"\n')
        self.core.write_text('stock core')
        self.assertEqual(self.run_upgrade().returncode, 0)
        self.assertEqual(self.holds.read_text(), 'other-package\n')
        self.assertEqual(self.core.read_text(), 'stock replacement')

    def test_custom_core_missing_paired_module_aborts(self):
        self.module.unlink()
        self.assertNotEqual(self.run_upgrade().returncode, 0)
        self.assert_no_apt()

    def test_invalid_configuration_aborts_before_packages(self):
        for env in ({'VALIDATION_STATUS': '2'}, {'VALIDATION_OUTPUT': '[ERROR] invalid PHP path'},
                    {'VALIDATION_OUTPUT': 'incompatible OpenLiteSpeed core ABI'}):
            with self.subTest(env=env):
                self.assertNotEqual(self.run_upgrade(**env).returncode, 0)
                self.assert_no_apt()

    def test_warning_only_configuration_is_accepted(self):
        self.assertEqual(self.run_upgrade(VALIDATION_STATUS='1', VALIDATION_OUTPUT='[WARN] harmless').returncode, 0)

    def test_validation_timeout_aborts_before_apt(self):
        self.assertNotEqual(self.run_upgrade(SIMULATE_TIMEOUT='1').returncode, 0)
        self.assert_no_apt()

    def test_validation_failure_preserves_bounded_actionable_diagnostic(self):
        result = self.run_upgrade(VALIDATION_OUTPUT='x' * 3000 + '[ERROR] invalid PHP path')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('[ERROR] invalid PHP path', result.stdout)
        self.assertLess(len(result.stdout), 2200)
        self.assert_no_apt()

    def test_unknown_package_owner_aborts(self):
        self.assertNotEqual(self.run_upgrade(PACKAGE_STATUS='unknown ok not-installed').returncode, 0)
        self.assert_no_apt()

    def test_non_ubuntu_does_not_create_hold(self):
        self.release.write_text('ID=almalinux\n')
        self.assertEqual(self.run_upgrade().returncode, 0)
        self.assertEqual(self.holds.read_text(), 'other-package\n')

    def test_entrypoint_protects_even_check_os_package_installations(self):
        entrypoint = SOURCE[SOURCE.rindex('\nCheck_Root\n'):]
        guard = entrypoint.index('Protect_Custom_OLS_From_APT || exit 1')
        self.assertLess(guard, entrypoint.index('\nCheck_OS\n'))
        self.assertLess(guard, entrypoint.index('\nPre_Upgrade_Setup_Repository\n'))
        self.assertLess(guard, entrypoint.index('\nPre_Upgrade_Required_Components\n'))


if __name__ == '__main__':
    unittest.main()
