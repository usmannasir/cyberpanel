"""Run the real guard before destructive fake APT upgrade commands."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'cyberpanel_upgrade.sh').read_text()
GUARD = SOURCE[SOURCE.index('OLS_Pinned_Helper() {'):SOURCE.index('\nCheck_OS() {')]
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
        self.waf = self.root / 'waf'
        self.waf.write_text('paired custom WAF')
        self.release = self.root / 'os-release'
        self.release.write_text('ID=ubuntu\nVERSION_ID="26.04"\n')
        self.holds = self.root / 'holds'
        self.holds.write_text('other-package\n')
        self.events = self.root / 'events'
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        for name, body in {
            'rpm': '''echo "rpm query ${@: -1}" >> "$EVENTS"
case "${@: -1}" in
 "$CORE") printf '%s\n' "${RPM_CORE_OWNER:-openlitespeed}"; exit "${RPM_STATUS:-0}" ;;
 "$WAF") printf '%s\n' "${RPM_WAF_OWNER:-ols-modsecurity}"; exit "${RPM_STATUS:-0}" ;;
 *) echo "file ${@: -1} is not owned by any package"; exit 1 ;;
esac''',
            'yum': '''echo "yum $*" >>"$EVENTS"
case " $* " in *" --exclude=openlitespeed "*) ;; *) printf stock-core >"$CORE" ;; esac
case " $* " in *" --exclude=ols-modsecurity "*) ;; *) printf stock-waf >"$WAF" ;; esac''',
            'timeout': '[ "$1" = 30 ] || exit 99; shift; [ "${SIMULATE_TIMEOUT:-0}" = 0 ] || exit 124; exec "$@"',
            'dpkg-query': '''if [ "${@: -1}" = ols-modsecurity ]; then
printf "%s" "${WAF_PACKAGE_STATUS-install ok installed}"; exit "${WAF_QUERY_STATUS:-0}"
fi
printf "%s" "${PACKAGE_STATUS:-install ok installed}"''',
            'apt-mark': '''echo "apt-mark $*" >> "$EVENTS"
case "$1" in
showhold) [ "${SHOWHOLD_FAIL:-0}" = 0 ] || exit 1; cat "$HOLDS";;
hold) [ "${HOLD_FAIL:-0}" = 0 ] && [ "${HOLD_FAIL_PACKAGE:-}" != "$2" ] || exit 1; [ "${HOLD_NOOP:-0}" = 1 ] || [ "${HOLD_NOOP_PACKAGE:-}" = "$2" ] || echo "$2" >> "$HOLDS";;
*) exit 99;;
esac''',
            'apt': '''echo "apt $*" >> "$EVENTS"
if ! grep -Fxq openlitespeed "$HOLDS"; then printf 'stock replacement' > "$CORE"; fi
if [ "$WAF_PACKAGE_STATUS" = "install ok installed" ] && ! grep -Fxq ols-modsecurity "$HOLDS"; then printf 'stock WAF replacement' > "$WAF"; fi''',
            'apt-get': '''echo "apt-get $*" >> "$EVENTS"
if ! grep -Fxq openlitespeed "$HOLDS"; then printf 'stock replacement' > "$CORE"; fi
if [ "$WAF_PACKAGE_STATUS" = "install ok installed" ] && ! grep -Fxq ols-modsecurity "$HOLDS"; then printf 'stock WAF replacement' > "$WAF"; fi''',
        }.items():
            path = self.bin / name
            path.write_text('#!/bin/bash\n' + body + '\n')
            path.chmod(0o755)
        # Package sequencing uses executable fixture stubs. The native ledger
        # itself is exercised against actual OLS in the opt-in Docker suite.
        self.guard = GUARD.replace('/usr/local/CyberCP/plogical', str(ROOT / 'plogical')).replace('/etc/os-release', str(self.release)).replace(
            '/usr/local/lsws/bin/openlitespeed', str(self.core)).replace(
            '/usr/local/lsws/modules/cyberpanel_ols.so', str(self.module)).replace(
            '/usr/local/lsws/modules/mod_security.so', str(self.waf))
        self.guard += '\nOLS_Custom_Config_Test() { timeout 30 "$1" -t; }\n'

    def run_upgrade(self, command=None, **env):
        environment = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                           CORE=str(self.core), WAF=str(self.waf), WAF_PACKAGE_STATUS="install ok installed",
                           HOLDS=str(self.holds), EVENTS=str(self.events))
        environment.update(env)
        return subprocess.run(['bash', '-c', self.guard + '\nProtect_Custom_OLS_From_Packages || exit 1\n' +
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
                self.assertEqual(self.waf.read_text(), 'paired custom WAF')
                events = self.events.read_text()
                self.assertLess(events.index('apt-mark hold openlitespeed'),
                                re.search(r'(?m)^apt(?:-get)? ', events).start())
                self.assertLess(events.index('apt-mark hold ols-modsecurity'),
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
        self.holds.write_text('other-package\nopenlitespeed\nols-modsecurity\n')
        self.assertEqual(self.run_upgrade(PACKAGE_STATUS='hold ok installed').returncode, 0)
        self.assertEqual(self.holds.read_text(), 'other-package\nopenlitespeed\nols-modsecurity\n')
        self.assertNotIn('apt-mark hold ', self.events.read_text())

    def test_stock_ubuntu20_with_leftover_module_is_not_held(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="20.04"\n')
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        self.assertEqual(self.run_upgrade().returncode, 0)
        self.assertEqual(self.holds.read_text(), 'other-package\n')
        self.assertEqual(self.core.read_text(), 'stock replacement')

    def test_installed_waf_hold_failure_or_ineffective_hold_aborts(self):
        for env in ({'HOLD_FAIL_PACKAGE': 'ols-modsecurity'},
                    {'HOLD_NOOP_PACKAGE': 'ols-modsecurity'}):
            with self.subTest(env=env):
                self.holds.write_text('other-package\n')
                self.events.write_text('')
                self.assertNotEqual(self.run_upgrade(**env).returncode, 0)
                self.assertEqual(self.waf.read_text(), 'paired custom WAF')
                self.assert_no_apt()

    def test_absent_waf_package_is_not_installed_or_held(self):
        for status, rc in (('', '1'), ('unknown ok not-installed', '0'),
                           ('deinstall ok config-files', '0'), ('purge ok not-installed', '0')):
            with self.subTest(status=status, rc=rc):
                self.holds.write_text('other-package\n')
                result = self.run_upgrade(WAF_PACKAGE_STATUS=status, WAF_QUERY_STATUS=rc)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual(self.holds.read_text(), 'other-package\nopenlitespeed\n')
                self.assertEqual(self.waf.read_text(), 'paired custom WAF')

    def test_uncertain_waf_package_state_aborts(self):
        for status, rc in (('', '2'), ('install ok unpacked', '0'),
                           ('install reinstreq half-installed', '0'), ('install ok installed', '1')):
            with self.subTest(status=status, rc=rc):
                self.assertNotEqual(self.run_upgrade(WAF_PACKAGE_STATUS=status, WAF_QUERY_STATUS=rc).returncode, 0)
                self.assert_no_apt()

    def test_existing_waf_hold_supported(self):
        self.holds.write_text('other-package\nols-modsecurity\n')
        self.assertEqual(self.run_upgrade(WAF_PACKAGE_STATUS='hold ok installed').returncode, 0)
        self.assertNotIn('apt-mark hold ols-modsecurity', self.events.read_text())
        self.assertIn('ols-modsecurity\n', self.holds.read_text())

    def test_split_stock_core_custom_module_aborts_before_packages(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        original = self.core.read_bytes()
        for env in ({'VALIDATION_OUTPUT': 'incompatible OpenLiteSpeed core ABI'},
                    {'VALIDATION_OUTPUT': '[ERROR] missing CRS file'},
                    {'SIMULATE_TIMEOUT': '1'}):
            with self.subTest(env=env):
                result = self.run_upgrade(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('recover the verified paired bundle', result.stdout)
                self.assertEqual(self.core.read_bytes(), original)
                self.assertEqual(self.holds.read_text(), 'other-package\n')
                self.assert_no_apt()

    def test_custom_core_missing_paired_module_aborts(self):
        self.module.unlink()
        self.assertNotEqual(self.run_upgrade().returncode, 0)
        self.assert_no_apt()

    def test_invalid_configuration_aborts_before_packages(self):
        for env in ({'VALIDATION_STATUS': '2'}, {'VALIDATION_OUTPUT': '[FATAL] invalid core'}, {'VALIDATION_OUTPUT': '[ERROR] invalid PHP path'},
                    {'VALIDATION_OUTPUT': 'incompatible OpenLiteSpeed core ABI'}):
            with self.subTest(env=env):
                self.assertNotEqual(self.run_upgrade(**env).returncode, 0)
                self.assert_no_apt()

    def test_warning_only_configuration_is_accepted(self):
        self.assertEqual(self.run_upgrade(VALIDATION_STATUS='1', VALIDATION_OUTPUT='[WARN] harmless').returncode, 0)

    def test_validation_timeout_aborts_before_apt(self):
        self.assertNotEqual(self.run_upgrade(SIMULATE_TIMEOUT='1').returncode, 0)
        self.assert_no_apt()

    def test_short_failure_diagnostic_is_printed(self):
        result = self.run_upgrade(VALIDATION_STATUS='2', VALIDATION_OUTPUT='[FATAL] broken listener')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('[FATAL] broken listener', result.stdout)

    def test_validation_failure_preserves_bounded_actionable_diagnostic(self):
        result = self.run_upgrade(VALIDATION_OUTPUT='x' * 3000 + '[ERROR] invalid PHP path')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('[ERROR] invalid PHP path', result.stdout)
        self.assertLess(len(result.stdout), 2200)
        self.assert_no_apt()

    def test_unknown_package_owner_aborts(self):
        self.assertNotEqual(self.run_upgrade(PACKAGE_STATUS='unknown ok not-installed').returncode, 0)
        self.assert_no_apt()

    def test_rpm_updates_preserve_only_verified_owners_and_other_package_updates(self):
        self.release.write_text('ID=almalinux\n')
        original = self.core.read_bytes(), self.waf.read_bytes()
        for command in self.rpm_updates():
            result = self.run_upgrade(command, RPM_WAF_OWNER='openlitespeed\nols-modsecurity')
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual((self.core.read_bytes(), self.waf.read_bytes()), original)
            self.assertIn('yum update -y --exclude=openlitespeed --exclude=ols-modsecurity', self.events.read_text())
            self.assertNotIn('--exclude=lsphp', self.events.read_text())
            self.assertEqual(self.holds.read_text(), 'other-package\n')

    def rpm_updates(self):
        commands = re.findall(r'then (yum update -y [^;]+?) \|\| return 1; fi', SOURCE)
        self.assertEqual(len(commands), 3)
        return commands

    def test_rpm_preflight_failures_stop_before_any_package_transaction(self):
        self.release.write_text('ID=almalinux\n')
        for env in ({'VALIDATION_OUTPUT': '[FATAL] bad listener'},
                    {'VALIDATION_STATUS': '2'}, {'RPM_STATUS': '1'},
                    {'RPM_CORE_OWNER': 'lsphp83'}, {'RPM_WAF_OWNER': '--exclude=*'},
                    {'RPM_WAF_OWNER': 'openlitespeed\nother-owner'}):
            with self.subTest(env=env):
                self.events.write_text('')
                result = self.run_upgrade(self.rpm_updates()[0], **env)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('yum update', self.events.read_text())
                if 'VALIDATION_STATUS' in env or 'VALIDATION_OUTPUT' in env:
                    self.assertNotIn('rpm query', self.events.read_text())

    def test_enterprise_installation_keeps_normal_rpm_update(self):
        self.release.write_text('ID=almalinux\n')
        self.core.unlink()
        result = self.run_upgrade(self.rpm_updates()[0])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('yum update -y', self.events.read_text())
        self.assertNotIn('--exclude', self.events.read_text())
        self.assertNotIn('rpm query', self.events.read_text())

    def test_entrypoint_protects_even_check_os_package_installations(self):
        entrypoint = SOURCE[SOURCE.rindex('\nCheck_Root\n'):]
        guard = entrypoint.index('Protect_Custom_OLS_From_Packages || exit 1')
        self.assertLess(guard, entrypoint.index('\nCheck_OS\n'))
        self.assertLess(guard, entrypoint.index('\nPre_Upgrade_Setup_Repository || exit 1'))
        self.assertLess(guard, entrypoint.index('\nPre_Upgrade_Required_Components\n'))


if __name__ == '__main__':
    unittest.main()
