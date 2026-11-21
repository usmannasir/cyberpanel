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
        # The installed layout: the classifier locates the module and the
        # configuration from the core's own directory.
        self.lsws = self.root / 'lsws'
        for name in ('bin', 'modules', 'conf', 'admin/conf'):
            (self.lsws / name).mkdir(parents=True)
        self.core = self.lsws / 'bin/openlitespeed'
        self.core.write_text('#!/bin/bash\n# cyberpanel_lsi_api_abi_v1\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        self.core.chmod(0o755)
        self.module = self.lsws / 'modules/cyberpanel_ols.so'
        self.module.write_text('ELF cyberpanel_lsi_api_abi_v1')
        self.waf = self.lsws / 'modules/mod_security.so'
        self.waf.write_text('paired custom WAF')
        self.policy = self.root / '.cyberpanel-stock-recovery-policy'
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
            'sha256sum': '''case "${@: -1}" in
 "$CORE") digest="${LEGACY_CORE_HASH:-}" ;;
 "$MODULE") digest="${LEGACY_MODULE_HASH:-}" ;;
esac
if [ -n "${digest:-}" ] && [ -f "${@: -1}" ]; then
    printf '%s  %s\\n' "$digest" "${@: -1}"
else
    exec /usr/bin/sha256sum "$@"
fi''',
            'dpkg-query': '''if [ "${@: -1}" = ols-modsecurity ]; then
printf "%s" "${WAF_PACKAGE_STATUS-install ok installed}"; exit "${WAF_QUERY_STATUS:-0}"
fi
printf "%s" "${PACKAGE_STATUS:-install ok installed}"''',
            'apt-mark': '''echo "apt-mark $*" >> "$EVENTS"
case "$1" in
showhold) [ "${SHOWHOLD_FAIL:-0}" = 0 ] || exit 1; cat "$HOLDS";;
hold) [ "${HOLD_FAIL:-0}" = 0 ] && [ "${HOLD_FAIL_PACKAGE:-}" != "$2" ] || exit 1; [ "${HOLD_NOOP:-0}" = 1 ] || [ "${HOLD_NOOP_PACKAGE:-}" = "$2" ] || echo "$2" >> "$HOLDS";;
unhold) shift; for package in "$@"; do grep -Fxv "$package" "$HOLDS" > "$HOLDS.new"; mv "$HOLDS.new" "$HOLDS"; done;;
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
        self.guard = GUARD.replace('/usr/local/CyberCP/plogical', str(ROOT / 'plogical')).replace('/etc/os-release', str(self.release)).replace('/usr/local/lsws/.cyberpanel-stock-recovery-policy', str(self.policy)).replace(
            '/usr/local/lsws/bin/openlitespeed', str(self.core)).replace(
            '/usr/local/lsws/modules/cyberpanel_ols.so', str(self.module)).replace(
            '/usr/local/lsws/modules/mod_security.so', str(self.waf))
        self.guard += '\nOLS_Custom_Config_Test() { timeout 30 "$1" -t; }\n'

    def run_upgrade(self, command=None, **env):
        environment = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                           CORE=str(self.core), MODULE=str(self.module), WAF=str(self.waf),
                           WAF_PACKAGE_STATUS="install ok installed",
                           HOLDS=str(self.holds), EVENTS=str(self.events))
        environment.update(env)
        return subprocess.run(['bash', '-c', self.guard + '\nProtect_Custom_OLS_From_Packages || exit 1\n' +
                               (command or UPGRADES[0])], env=environment, capture_output=True, text=True, timeout=10)

    def assert_no_apt(self):
        events = self.events.read_text() if self.events.exists() else ''
        self.assertNotRegex(events, r'(?m)^apt(?:-get)? ')

    def test_recovery_policy_rejects_unsupported_core_before_native_or_package_work(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="22.04"\n')
        self.core.write_text('#!/bin/bash\n# cyberpanel_lsi_api_abi_v1\necho native-validation >> "$EVENTS"\nexit 0\n')
        for symlink in (False, True):
            with self.subTest(symlink=symlink):
                if symlink:
                    self.policy.symlink_to(self.root / 'missing-policy')
                else:
                    self.policy.write_bytes(b'CYBERPANEL_STOCK_RECOVERY_V1\nAUTO_SSL=disabled\n')
                result = self.run_upgrade()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('cannot enforce the stock recovery policy', result.stdout)
                self.assert_no_apt()
                self.assertNotIn('native-validation', self.events.read_text() if self.events.exists() else '')
                self.policy.unlink()

    def test_recovery_policy_refuses_fifo_and_symlink_core_without_hashing(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="22.04"\n')
        self.policy.write_bytes(b'CYBERPANEL_STOCK_RECOVERY_V1\nAUTO_SSL=disabled\n')
        self.core.unlink()
        for shape in ('symlink', 'fifo'):
            with self.subTest(shape=shape):
                if shape == 'symlink': self.core.symlink_to(self.module)
                else: os.mkfifo(self.core, 0o600)
                result = self.run_upgrade()
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('requires a regular verified core', result.stdout)
                self.assert_no_apt()
                self.core.unlink()

    def test_policy_aware_jammy_core_keeps_policy_and_package_holds(self):
        from plogical.olsServiceControl import RECOVERED_JAMMY_BUNDLE
        self.release.write_text('ID=ubuntu\nVERSION_ID="22.04"\n')
        self.policy.write_bytes(b'CYBERPANEL_STOCK_RECOVERY_V1\nAUTO_SSL=disabled\n')
        self.policy.chmod(0o600)
        before = self.policy.read_bytes(), self.policy.stat()
        result = self.run_upgrade(LEGACY_CORE_HASH=RECOVERED_JAMMY_BUNDLE[0])
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('openlitespeed\n', self.holds.read_text())
        self.assertIn('ols-modsecurity\n', self.holds.read_text())
        self.assertEqual(self.policy.read_bytes(), before[0])
        self.assertEqual(self.policy.stat().st_ino, before[1].st_ino)
        self.assertEqual(self.policy.stat().st_mode, before[1].st_mode)

    def test_recovery_policy_core_is_restricted_to_jammy(self):
        self.policy.write_bytes(b'CYBERPANEL_STOCK_RECOVERY_V1\nAUTO_SSL=disabled\n')
        self.release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        result = self.run_upgrade()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires the verified Jammy core', result.stdout)
        self.assert_no_apt()

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

    SITE_ERRORS = ("2026-11-21 19:54:31.349049 [ERROR] [191712] [config:server:vhosts:vhost:mail.example.com:epsr:mail.655340] "
                   "invalid path - /usr/local/lsws/lsphp73/bin/lsphp, it cannot be started by Web server!\n"
                   "2026-11-21 19:54:31.351614 [ERROR] [191712] [PlainConf] [virtualHostConfig:] parseline found more '}' "
                   "in /usr/local/lsws/conf/vhosts/shop.example.com/vhost.conf:110")

    def stock_core(self):
        self.module.unlink()
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')

    def test_errors_in_single_websites_do_not_stop_a_stock_upgrade(self):
        self.stock_core()
        result = self.run_upgrade(VALIDATION_STATUS='2', VALIDATION_OUTPUT=self.SITE_ERRORS)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('upgrade -y', self.events.read_text())
        self.assertEqual(self.holds.read_text(), 'other-package\n')

    def test_errors_in_single_websites_do_not_stop_a_custom_upgrade(self):
        result = self.run_upgrade(VALIDATION_STATUS='2', VALIDATION_OUTPUT=self.SITE_ERRORS)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('openlitespeed', self.holds.read_text())
        self.assertIn('upgrade -y', self.events.read_text())

    def test_errors_in_single_websites_do_not_stop_a_stock_core_beside_our_module(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="20.04"\n')
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        result = self.run_upgrade(VALIDATION_STATUS='2', VALIDATION_OUTPUT=self.SITE_ERRORS)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('upgrade -y', self.events.read_text())

    def test_invalid_stock_configuration_stops_before_package_changes(self):
        listener = '[ERROR] [config:server:listener:SSL] failed to load the certificate'
        for env in ({'VALIDATION_STATUS': '2'}, {'VALIDATION_OUTPUT': '[FATAL] invalid core'},
                    {'VALIDATION_STATUS': '2', 'VALIDATION_OUTPUT': self.SITE_ERRORS + '\n' + listener},
                    {'VALIDATION_STATUS': '3', 'VALIDATION_OUTPUT': self.SITE_ERRORS},
                    {'VALIDATION_STATUS': '2', 'VALIDATION_OUTPUT': '[WARN] harmless'},
                    {'SIMULATE_TIMEOUT': '1'}):
            with self.subTest(env=env):
                self.stock_core()
                original = self.core.read_bytes()
                result = self.run_upgrade(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('no package changes attempted', result.stdout)
                self.assert_no_apt()
                self.assertEqual(self.core.read_bytes(), original)
                self.module.write_text('restored for the next case')
        self.stock_core()
        result = self.run_upgrade(VALIDATION_STATUS='2', VALIDATION_OUTPUT=self.SITE_ERRORS + '\n' + listener)
        self.assertIn(listener, result.stdout)
        self.assertNotIn('lsphp73', result.stdout)

    def test_a_refusal_shows_the_error_to_correct_and_not_the_website_errors(self):
        wide = '[ERROR] [config:server:epsr:shared] invalid path - /nonexistent/bin/lsphp, it cannot be started by Web server!'
        result = self.run_upgrade(VALIDATION_STATUS='2', VALIDATION_OUTPUT=self.SITE_ERRORS + '\n' + wide)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Custom OLS configuration failed validation; no package changes attempted', result.stdout)
        self.assertIn(wide, result.stdout)
        self.assertNotIn('lsphp73', result.stdout)
        self.assert_no_apt()

    def test_valid_stock_configuration_keeps_the_normal_package_upgrade(self):
        self.stock_core()
        result = self.run_upgrade(VALIDATION_STATUS='1', VALIDATION_OUTPUT='[WARN] harmless')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('upgrade -y', self.events.read_text())
        self.assertEqual(self.holds.read_text(), 'other-package\n')
        self.assertEqual(self.core.read_text(), 'stock replacement')

    def test_unmarked_legacy_ubuntu_pair_requires_both_verified_files(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        self.module.write_text('legacy module without ABI marker')
        original = self.core.read_bytes()
        core_hash = '2a836d4bf17fe5152d15dd60fd3817c1d3c294b48b35f12b776fa2efb7771422'
        module_hash = 'f1c1ab881625fa6fe6545e45283220e86245a1e3c96e29c4d86af9ab15fd6c2b'

        for reported_module_hash in ('', module_hash):
            with self.subTest(module_verified=bool(reported_module_hash)):
                self.holds.write_text('other-package\n')
                self.events.write_text('')
                result = self.run_upgrade(
                    LEGACY_CORE_HASH=core_hash, LEGACY_MODULE_HASH=reported_module_hash,
                    WAF_PACKAGE_STATUS='', WAF_QUERY_STATUS='1',
                    VALIDATION_STATUS='1', VALIDATION_OUTPUT='[WARN] License validation failed',
                )
                self.assertEqual(self.core.read_bytes(), original)
                if reported_module_hash:
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    self.assertIn('openlitespeed\n', self.holds.read_text())
                else:
                    self.assertNotEqual(result.returncode, 0)
                    self.assert_no_apt()

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

    def test_stock_core_with_module_and_other_faults_aborts_before_packages(self):
        self.release.write_text('ID=ubuntu\nVERSION_ID="24.04"\n')
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-0}"\n')
        original = self.core.read_bytes()
        for env in ({'VALIDATION_OUTPUT': '[ERROR] missing CRS file'},
                    {'SIMULATE_TIMEOUT': '1'}):
            with self.subTest(env=env):
                result = self.run_upgrade(**env)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('recover the verified paired bundle', result.stdout)
                self.assertEqual(self.core.read_bytes(), original)
                self.assertEqual(self.holds.read_text(), 'other-package\n')
                self.assert_no_apt()

    ABI = ('[cyberpanel_ols] Module v2.7.7 DISABLED: incompatible OpenLiteSpeed '
           'core ABI (expected CyberPanel OLS 2.5.2)')

    def vendor_core(self, release='ID=ubuntu\nVERSION_ID="24.04"\n'):
        """A package update replaced the core and left the CyberPanel module."""
        self.release.write_text(release)
        self.core.write_text('#!/bin/bash\necho "$VALIDATION_OUTPUT"\nexit "${VALIDATION_STATUS:-1}"\n')
        self.httpd = self.lsws / 'conf/httpd_config.conf'
        self.httpd.write_text('serverName x\nautoSSL                   1\nacmeEmail admin@cyberpanel.net\n')
        self.admin = self.lsws / 'admin/conf/admin_config.conf'
        self.admin.write_text('enableCoreDump 1\nthrottleEnabled 1\nthrottleMaxFailures 5\n')
        stamp = '2026-11-19 14:41:43.122363 '
        self.default = '\n'.join([
            self.ABI,
            stamp + '[WARN] [PlainConf] [httpServerConfig:] Not support [autossl 1] in file %s:2' % self.httpd,
            stamp + '[WARN] [PlainConf] [httpServerConfig:] Not support [acmeemail admin@cyberpanel.net] in file %s:3' % self.httpd,
            stamp + '[WARN] [1579] [config:server:vhosts:vhost:Example] Uid of /x/Example/html/ is 0, smaller than minimum requirement 11, use server uid!'])
        self.webadmin = '\n'.join(
            stamp + '[ERROR] [1579] [PlainConf] [adminConfig:] Not support [%s] in file %s:%d' % (text, self.admin, number)
            for number, text in ((2, 'throttleenabled 1'), (3, 'throttlemaxfailures 5')))
        return self.core.read_bytes()

    def test_vendor_core_beside_our_module_is_protected_before_packages_and_left_to_the_transaction(self):
        original = self.vendor_core()
        for env in ({'VALIDATION_OUTPUT': None}, {'VALIDATION_OUTPUT': 'webadmin', 'VALIDATION_STATUS': '2'}):
            with self.subTest(env=env):
                self.core.write_bytes(original)
                self.events.write_text('')
                self.holds.write_text('other-package\n')
                env['VALIDATION_OUTPUT'] = self.default + ('\n' + self.webadmin if env['VALIDATION_OUTPUT'] else '')
                # The bundle transaction of the same run restores the CyberPanel core.
                result = self.run_upgrade(UPGRADES[0] + '\nprintf "\\n# cyberpanel_lsi_api_abi_v1\\n" >> "$CORE"', **env)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('This upgrade restores the CyberPanel OpenLiteSpeed bundle', result.stdout)
                self.assertNotIn('recover the verified paired bundle', result.stdout)
                events = self.events.read_text()
                self.assertLess(events.index('apt-mark hold ols-modsecurity'),
                                re.search(r'(?m)^apt(?:-get)? ', events).start())
                self.assertTrue(self.core.read_bytes().startswith(original))
                self.assertEqual(self.holds.read_text(), 'other-package\nopenlitespeed\nols-modsecurity\n')
                self.assertNotIn('apt-mark unhold', events)

    def test_holds_set_for_a_vendor_core_are_released_when_the_run_ends_on_the_vendor_core(self):
        original = self.vendor_core()
        for ending, status in (('exit 78', 78), ('true', 0)):
            with self.subTest(ending=ending):
                self.events.write_text('')
                self.holds.write_text('other-package\nols-modsecurity\n')
                result = self.run_upgrade(UPGRADES[0] + '\n' + ending, VALIDATION_OUTPUT=self.default)
                self.assertEqual(result.returncode, status, result.stdout + result.stderr)
                self.assertEqual(self.core.read_bytes(), original)
                # Only the hold this run added is released; the administrator's stays.
                self.assertEqual(self.holds.read_text(), 'other-package\nols-modsecurity\n')
                self.assertIn('apt-mark unhold openlitespeed\n', self.events.read_text())

    def test_vendor_core_with_faults_of_its_own_aborts_before_packages_showing_the_whole_line(self):
        original = self.vendor_core()
        fault = '[ERROR] [config:server:listener:SSL] ' + 'y' * 2500 + ' missing certificate'
        forged = '[ERROR] [PlainConf] [adminConfig:] Not support [throttleenabled 1] in file %s:1' % self.admin
        for output in (self.default + '\n' + fault, self.default + '\n' + forged):
            with self.subTest(output=output[-60:]):
                result = self.run_upgrade(VALIDATION_OUTPUT=output, VALIDATION_STATUS='2')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('cannot restore the CyberPanel bundle', result.stdout)
                self.assertIn(output.splitlines()[-1], result.stdout)
                self.assertEqual(self.core.read_bytes(), original)
                self.assertEqual(self.holds.read_text(), 'other-package\n')
                self.assert_no_apt()
        result = self.run_upgrade(VALIDATION_OUTPUT='incompatible OpenLiteSpeed core ABI')
        self.assertNotEqual(result.returncode, 0)
        self.assert_no_apt()

    def test_vendor_core_is_accepted_on_every_bundle_platform_and_refused_elsewhere(self):
        for release in ('ID="almalinux"\nVERSION_ID="9.9"\n', 'ID="almalinux"\nVERSION_ID="8.10"\n',
                        'ID="almalinux"\nVERSION_ID="10.2"\n', 'ID="rocky"\nVERSION_ID="9.7"\n'):
            with self.subTest(release=release):
                original = self.vendor_core(release), self.waf.read_bytes()
                self.events.write_text('')
                result = self.run_upgrade(self.rpm_updates()[0], VALIDATION_OUTPUT=self.default)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertIn('yum update -y --exclude=openlitespeed --exclude=ols-modsecurity', self.events.read_text())
                self.assertEqual((self.core.read_bytes(), self.waf.read_bytes()), original)
                self.assertEqual(self.holds.read_text(), 'other-package\n')
        original = self.vendor_core('ID=ubuntu\nVERSION_ID="20.04"\n')
        result = self.run_upgrade(VALIDATION_OUTPUT=self.default)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('no CyberPanel OpenLiteSpeed bundle exists', result.stdout)
        self.assertEqual(self.holds.read_text(), 'other-package\n')
        self.assert_no_apt()

    def test_vendor_core_beside_an_existing_recovery_policy_is_repaired_on_jammy_only(self):
        policy = b'CYBERPANEL_STOCK_RECOVERY_V1\nAUTO_SSL=disabled\n'
        original = self.vendor_core('ID=ubuntu\nVERSION_ID="22.04"\n')
        self.policy.write_bytes(policy)
        # A package update replaced the policy-aware core after an earlier repair.
        result = self.run_upgrade(UPGRADES[0] + '\nprintf "\\n# cyberpanel_lsi_api_abi_v1\\n" >> "$CORE"',
                                  VALIDATION_OUTPUT=self.default)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('This upgrade restores the CyberPanel OpenLiteSpeed bundle', result.stdout)
        self.assertEqual(self.policy.read_bytes(), policy)
        self.assertIn('openlitespeed\n', self.holds.read_text())
        # Without our module there is nothing to repair: the policy still refuses.
        self.core.write_bytes(original)
        self.holds.write_text('other-package\n')
        self.events.write_text('')
        self.module.write_text('ELF vendor module without the marker')
        for output in ('', self.default):
            with self.subTest(output=output[:20]):
                result = self.run_upgrade(VALIDATION_OUTPUT=output)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('cannot enforce the stock recovery policy', result.stdout)
                self.assert_no_apt()
        # The policy belongs to the Jammy core alone.
        self.vendor_core('ID=ubuntu\nVERSION_ID="24.04"\n')
        self.module.write_text('ELF cyberpanel_lsi_api_abi_v1')
        result = self.run_upgrade(VALIDATION_OUTPUT=self.default)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('requires the verified Jammy core', result.stdout)
        self.assert_no_apt()

    def test_classifier_pin_matches_the_published_helper(self):
        import hashlib
        helper = ROOT / 'plogical/olsStockClassifier.py'
        pin = re.search(r'OLS_Split_State\(\) \(\n.*\n  local pin=(\S+)\n  local blob=(\S+)\n', SOURCE)
        self.assertEqual(pin.group(1), hashlib.sha256(helper.read_bytes()).hexdigest())
        data = helper.read_bytes()
        self.assertEqual(pin.group(2), hashlib.sha1(b'blob %d\0' % len(data) + data).hexdigest())

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
