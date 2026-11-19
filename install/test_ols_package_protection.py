"""Persistent package protection for the CyberPanel OpenLiteSpeed overlay.

The helper is loaded by file path. Every path it touches lives in a temporary
directory and rpm, dpkg-query and apt-mark are fakes placed first on PATH.
The fakes are driven by files and log every invocation, so a test can prove
that nothing ran. No test may reach the real package tools of the machine
that runs it.
"""
import ast
import importlib.util
import inspect
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'plogical' / 'olsPackageProtection.py'
MARKER = b'cyberpanel_lsi_api_abi_v1'
TAG = '# cyberpanel-ols-package-protection'
FINE = ('not_applicable', 'already', 'applied', 'protected', 'released')
_LOADED = []

FAKES = {
    'rpm': r'''printf 'rpm LC_ALL=%s %s\n' "${LC_ALL:-}" "$*" >> "$OLS_FAKE/events"
if [ "$#" -ne 5 ] || [ "$1|$2|$3|$4" != '-q|--queryformat|%{NAME}\n|--file' ]; then
    echo 'rpm: unexpected arguments' >&2
    exit 97
fi
name=$(basename -- "$5")
if [ -f "$OLS_FAKE/rpm/$name.owner" ]; then
    cat "$OLS_FAKE/rpm/$name.owner"
    if [ -f "$OLS_FAKE/rpm/$name.rc" ]; then exit "$(cat "$OLS_FAKE/rpm/$name.rc")"; fi
    exit 0
fi
echo "file $5 is not owned by any package"
exit 1''',
    'dpkg-query': r'''printf 'dpkg-query LC_ALL=%s %s\n' "${LC_ALL:-}" "$*" >> "$OLS_FAKE/events"
if [ "$#" -ne 3 ] || [ "$1|$2" != '-W|-f=${Status}' ]; then
    echo 'dpkg-query: unexpected arguments' >&2
    exit 97
fi
if [ -f "$OLS_FAKE/dpkg/$3.status" ]; then
    printf '%s' "$(cat "$OLS_FAKE/dpkg/$3.status")"
    if [ -f "$OLS_FAKE/dpkg/$3.rc" ]; then exit "$(cat "$OLS_FAKE/dpkg/$3.rc")"; fi
    exit 0
fi
echo "dpkg-query: no packages found matching $3" >&2
exit 1''',
    'apt-mark': r'''printf 'apt-mark LC_ALL=%s %s\n' "${LC_ALL:-}" "$*" >> "$OLS_FAKE/events"
holds="$OLS_FAKE/holds"
action="$1"
shift
case "$action" in
showhold)
    if [ -f "$OLS_FAKE/showhold.rc" ]; then exit "$(cat "$OLS_FAKE/showhold.rc")"; fi
    cat "$holds" ;;
hold)
    if [ -f "$OLS_FAKE/hold.rc" ]; then exit "$(cat "$OLS_FAKE/hold.rc")"; fi
    for package in "$@"; do
        if grep -Fxq -- "$package" "$OLS_FAKE/hold.skip" 2>/dev/null; then continue; fi
        grep -Fxq -- "$package" "$holds" || echo "$package" >> "$holds"
        echo "$package set on hold."
    done ;;
unhold)
    if [ -f "$OLS_FAKE/unhold.rc" ]; then exit "$(cat "$OLS_FAKE/unhold.rc")"; fi
    for package in "$@"; do
        grep -Fxv -- "$package" "$holds" > "$holds.new"
        mv "$holds.new" "$holds"
        echo "Canceled hold on $package."
    done ;;
*) exit 99 ;;
esac''',
}

# A deliberately naive package manager: it replaces the custom core unless a
# line of its configuration excludes the owning package.
FAKE_DNF = r'''printf 'dnf %s\n' "$*" >> "$OLS_FAKE/events"
if ! grep -Eq '^exclude(pkgs)?[[:space:]]*[=:](.*[[:space:],])?openlitespeed([[:space:],]|$)' "$OLS_FAKE_DNF_CONF"; then
    printf 'stock-core' > "$OLS_FAKE_CORE"
fi'''


def load_helper():
    if not _LOADED:
        spec = importlib.util.spec_from_file_location('ols_package_protection_under_test', str(HELPER))
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _LOADED.append(module)
    return _LOADED[0]


def snapshot(path):
    info = os.stat(str(path))
    return (Path(str(path)).read_bytes(), info.st_ino, info.st_mtime_ns,
            stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid)


class Fixture(unittest.TestCase):
    distro = 'ubuntu'

    def setUp(self):
        self.mod = load_helper()
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.tmp = Path(holder.name)
        self.root = self.tmp / 'lsws'
        (self.root / 'bin').mkdir(parents=True)
        (self.root / 'modules').mkdir()
        self.core = self.root / 'bin' / 'openlitespeed'
        self.module = self.root / 'modules' / 'cyberpanel_ols.so'
        self.waf = self.root / 'modules' / 'mod_security.so'
        self.custom_core = b'\x7fELF custom core ' + MARKER + b'\x00 tail'
        self.core.write_bytes(self.custom_core)
        self.core.chmod(0o755)
        self.module.write_bytes(b'\x7fELF module ' + MARKER)
        self.os_release = self.tmp / 'os-release'
        self.etc = self.tmp / 'etc'
        (self.etc / 'dnf').mkdir(parents=True)
        self.dnf_conf = self.etc / 'dnf' / 'dnf.conf'
        self.yum_conf = self.etc / 'yum.conf'
        # The parent of the record is missing on purpose.
        self.record = self.tmp / 'cyberpanel' / 'ols-package-protection.json'
        self.fake = self.tmp / 'fake'
        (self.fake / 'rpm').mkdir(parents=True)
        (self.fake / 'dpkg').mkdir()
        self.events = self.fake / 'events'
        self.holds = self.fake / 'holds'
        self.holds.write_text('other-package\n')
        self.bin = self.tmp / 'bin'
        self.bin.mkdir()
        for name, body in FAKES.items():
            self.write_fake(name, body)
        environment = mock.patch.dict(os.environ, {
            'PATH': str(self.bin) + os.pathsep + os.environ.get('PATH', ''),
            'OLS_FAKE': str(self.fake),
            'OLS_FAKE_DNF_CONF': str(self.dnf_conf),
            'OLS_FAKE_CORE': str(self.core),
            'LC_ALL': 'C.UTF-8',
        })
        environment.start()
        self.addCleanup(environment.stop)
        for name in FAKES:
            self.assertEqual(shutil.which(name), str(self.bin / name),
                             'a real package tool is reachable from this test')
        self.set_distro(self.distro)
        self.set_dpkg('openlitespeed', 'install ok installed')
        self.set_owner(self.core, 'openlitespeed')
        self.protection = self.make()

    # -- fixture helpers ---------------------------------------------------
    def make(self, **overrides):
        paths = dict(root=str(self.root), os_release=str(self.os_release), record=str(self.record),
                     dnf_conf=str(self.dnf_conf), yum_conf=str(self.yum_conf))
        paths.update(overrides)
        return self.mod.Protection(**paths)

    def write_fake(self, name, body):
        path = self.bin / name
        path.write_text('#!/bin/bash\n' + body + '\n')
        path.chmod(0o755)

    def only_fakes_on_path(self):
        """Hide every real package tool, so a removed fake is really missing."""
        tools = self.tmp / 'tools'
        if not tools.exists():
            tools.mkdir()
            for name in ('cat', 'grep', 'basename', 'mv', 'sleep'):
                (tools / name).symlink_to(shutil.which(name))
        os.environ['PATH'] = str(self.bin) + os.pathsep + str(tools)
        for name in FAKES:
            self.assertIn(shutil.which(name), (None, str(self.bin / name)))

    def set_distro(self, distro):
        self.os_release.write_text('NAME="Test"\nID=%s\nVERSION_ID="1"\nID_LIKE="other"\n' % distro)

    def set_dpkg(self, package, status, rc=None):
        (self.fake / 'dpkg' / (package + '.status')).write_text(status)
        if rc is not None:
            (self.fake / 'dpkg' / (package + '.rc')).write_text(str(rc))

    def set_owner(self, path, owners, rc=None):
        name = os.path.basename(str(path))
        (self.fake / 'rpm' / (name + '.owner')).write_text(owners + '\n')
        if rc is not None:
            (self.fake / 'rpm' / (name + '.rc')).write_text(str(rc))

    def no_owner(self, path):
        (self.fake / 'rpm' / (os.path.basename(str(path)) + '.owner')).unlink()

    def ran(self):
        return self.events.read_text().splitlines() if self.events.exists() else []

    def changing_commands(self):
        return [line for line in self.ran()
                if ' hold ' in line or ' unhold ' in line or line.startswith('dnf ')]

    def held(self):
        return self.holds.read_text().split()

    def saved_record(self):
        return json.loads(self.record.read_text())

    def check(self, result, state, family=None, packages=None):
        for key in ('state', 'family', 'packages', 'reason'):
            self.assertIn(key, result)
        self.assertEqual(result['state'], state, result)
        self.assertIsInstance(result['packages'], list)
        if state in FINE:
            self.assertEqual(result['reason'], '', result)
        else:
            self.assertTrue(result['reason'].strip(), result)
        if family is not None:
            self.assertEqual(result['family'], family, result)
        if packages is not None:
            self.assertEqual(result['packages'], packages, result)
        return result


class NotApplicableTests(Fixture):
    def untouched(self, result):
        self.check(result, 'not_applicable', packages=[])
        self.assertEqual(self.ran(), [])
        self.assertFalse(self.record.exists())
        self.assertFalse(self.record.parent.exists())
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\ngpgcheck=1\n')
        self.assertEqual(self.held(), ['other-package'])

    def each_family(self, *actions):
        for distro in ('ubuntu', 'almalinux'):
            with self.subTest(distro=distro):
                self.set_distro(distro)
                self.dnf_conf.write_bytes(b'[main]\ngpgcheck=1\n')
                for action in actions:
                    self.untouched(action())

    def test_stock_core_with_leftover_marker_module(self):
        self.core.write_bytes(b'\x7fELF stock core')
        self.each_family(self.protection.protect, self.protection.status)

    def test_missing_core_as_on_litespeed_enterprise(self):
        self.core.unlink()
        self.each_family(self.protection.protect, self.protection.status)

    def test_custom_core_without_marker_module(self):
        self.module.write_bytes(b'\x7fELF other module')
        self.each_family(self.protection.protect, self.protection.status)
        self.module.unlink()
        self.each_family(self.protection.protect, self.protection.status)

    def test_core_that_is_a_symlink(self):
        real = self.root / 'bin' / 'openlitespeed.real'
        self.core.rename(real)
        self.core.symlink_to(real)
        self.each_family(self.protection.protect, self.protection.status)

    def test_module_that_is_a_symlink(self):
        real = self.root / 'modules' / 'cyberpanel_ols.real'
        self.module.rename(real)
        self.module.symlink_to(real)
        self.each_family(self.protection.protect, self.protection.status)

    def test_core_that_is_not_a_regular_file(self):
        self.core.unlink()
        os.mkfifo(str(self.core))
        self.each_family(self.protection.protect, self.protection.status)

    def test_unknown_distribution(self):
        self.dnf_conf.write_bytes(b'[main]\ngpgcheck=1\n')
        for distro in ('debian', 'fedora', 'ubuntu-core', ''):
            with self.subTest(distro=distro):
                self.set_distro(distro)
                self.untouched(self.protection.protect())
                self.untouched(self.protection.status())

    def test_missing_os_release(self):
        self.dnf_conf.write_bytes(b'[main]\ngpgcheck=1\n')
        self.os_release.unlink()
        self.untouched(self.protection.protect())

    def test_explains_itself_without_using_reason(self):
        self.core.write_bytes(b'\x7fELF stock core')
        result = self.protection.protect()
        self.assertEqual(result['reason'], '')
        self.assertTrue(result['detail'].strip())


class FamilyTests(Fixture):
    def test_families_follow_the_shell_guard(self):
        self.dnf_conf.write_bytes(b'[main]\n')
        expected = {'ubuntu': 'apt'}
        for distro in ('almalinux', 'rhel', 'centos', 'rocky', 'cloudlinux', 'ol', 'openeuler'):
            expected[distro] = 'rpm'
        for distro, family in sorted(expected.items()):
            with self.subTest(distro=distro):
                self.set_distro(distro)
                self.assertEqual(self.protection.status()['family'], family)

    def test_quoted_and_mixed_case_id(self):
        self.dnf_conf.write_bytes(b'[main]\n')
        for line, family in (('ID="almalinux"', 'rpm'), ("ID='rocky'", 'rpm'),
                             ('ID=Ubuntu', 'apt'), ('ID="CentOS"', 'rpm')):
            with self.subTest(line=line):
                self.os_release.write_text('NAME=x\n%s\nID_LIKE="rhel fedora"\n' % line)
                self.assertEqual(self.protection.status()['family'], family)

    def test_marker_is_found_across_read_boundaries(self):
        for offset in (65536 - 10, 1048576 - 10, 2 * 1048576 - 3):
            with self.subTest(offset=offset):
                blob = bytearray(b'\x00' * (offset + 4096))
                blob[offset:offset + len(MARKER)] = MARKER
                self.core.write_bytes(bytes(blob))
                self.assertEqual(self.protection.status()['state'], 'unprotected')


class AptTests(Fixture):
    distro = 'ubuntu'

    def test_holds_the_core_package(self):
        result = self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed'])
        self.assertEqual(result['added'], ['openlitespeed'])
        self.assertEqual(self.held(), ['other-package', 'openlitespeed'])
        self.assertIn('apt-mark LC_ALL=C hold openlitespeed', self.ran())
        saved = self.saved_record()
        self.assertEqual(saved['family'], 'apt')
        self.assertEqual(saved['added'], ['openlitespeed'])
        self.assertEqual(saved['version'], 1)
        self.assertEqual(stat.S_IMODE(os.stat(str(self.record)).st_mode), 0o644)
        self.assertEqual(stat.S_IMODE(os.stat(str(self.record.parent)).st_mode), 0o755)
        self.assertEqual(sorted(os.listdir(str(self.record.parent))), [self.record.name])

    def test_every_command_runs_in_the_c_locale(self):
        self.protection.protect()
        self.assertTrue(self.ran())
        for line in self.ran():
            self.assertIn(' LC_ALL=C ', line)

    def test_holds_the_core_and_an_installed_waf_package(self):
        for status in ('install ok installed', 'hold ok installed'):
            with self.subTest(status=status):
                self.holds.write_text('other-package\n')
                self.events.write_text('')
                self.set_dpkg('ols-modsecurity', status)
                self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed', 'ols-modsecurity'])
                self.assertEqual(self.held(), ['other-package', 'openlitespeed', 'ols-modsecurity'])
                self.assertEqual(self.changing_commands(),
                                 ['apt-mark LC_ALL=C hold openlitespeed ols-modsecurity'])
                self.assertEqual(self.saved_record()['added'], ['openlitespeed', 'ols-modsecurity'])
                self.record.unlink()

    def test_core_package_already_marked_hold_by_dpkg(self):
        self.set_dpkg('openlitespeed', 'hold ok installed')
        self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed'])

    def test_absent_waf_package_is_not_held(self):
        for status, rc in (('', 1), ('unknown ok not-installed', 0),
                           ('deinstall ok config-files', 0), ('purge ok not-installed', 0)):
            with self.subTest(status=status, rc=rc):
                self.holds.write_text('other-package\n')
                self.set_dpkg('ols-modsecurity', status, rc)
                self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed'])
                self.assertEqual(self.held(), ['other-package', 'openlitespeed'])
                self.record.unlink()

    def test_unknown_waf_package_is_not_held(self):
        # No status file: the fake answers like dpkg-query for an unknown name.
        self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed'])
        self.assertNotIn('ols-modsecurity', self.held())

    def test_uncertain_waf_state_is_refused_without_a_hold(self):
        for status, rc in (('', 2), ('install ok unpacked', 0),
                           ('install reinstreq half-installed', 0), ('install ok installed', 1)):
            with self.subTest(status=status, rc=rc):
                self.set_dpkg('ols-modsecurity', status, rc)
                result = self.check(self.protection.protect(), 'refused', 'apt')
                self.assertIn('ols-modsecurity', result['reason'])
                self.assertEqual(self.changing_commands(), [])
                self.assertEqual(self.held(), ['other-package'])
                self.assertFalse(self.record.exists())
                self.check(self.protection.status(), 'refused', 'apt')

    def test_uncertain_core_package_state_is_refused(self):
        for status, rc in (('unknown ok not-installed', 0), ('deinstall ok config-files', 0),
                           ('install ok half-configured', 0), ('', 1)):
            with self.subTest(status=status, rc=rc):
                self.set_dpkg('openlitespeed', status, rc)
                self.check(self.protection.protect(), 'refused', 'apt')
                self.assertEqual(self.changing_commands(), [])
                self.assertFalse(self.record.exists())

    def test_hold_that_silently_does_nothing_fails(self):
        (self.fake / 'hold.skip').write_text('openlitespeed\n')
        result = self.check(self.protection.protect(), 'failed', 'apt')
        self.assertIn('openlitespeed', result['reason'])
        self.assertEqual(self.held(), ['other-package'])
        self.assertFalse(self.record.exists())

    def test_partial_hold_fails_and_records_only_what_was_held(self):
        self.set_dpkg('ols-modsecurity', 'install ok installed')
        (self.fake / 'hold.skip').write_text('ols-modsecurity\n')
        result = self.check(self.protection.protect(), 'failed', 'apt')
        self.assertIn('ols-modsecurity', result['reason'])
        self.assertEqual(result['missing'], ['ols-modsecurity'])
        self.assertEqual(self.saved_record()['added'], ['openlitespeed'])

    def test_hold_command_failure_fails(self):
        (self.fake / 'hold.rc').write_text('100')
        self.check(self.protection.protect(), 'failed', 'apt')
        self.assertEqual(self.held(), ['other-package'])
        self.assertFalse(self.record.exists())

    def test_unreadable_holds_fail_before_any_hold(self):
        (self.fake / 'showhold.rc').write_text('1')
        self.check(self.protection.protect(), 'failed', 'apt')
        self.assertEqual(self.changing_commands(), [])
        self.check(self.protection.status(), 'unprotected', 'apt')

    def test_everything_already_held_changes_and_records_nothing(self):
        self.set_dpkg('ols-modsecurity', 'hold ok installed')
        self.holds.write_text('other-package\nopenlitespeed\nols-modsecurity\n')
        before = snapshot(self.holds)
        result = self.check(self.protection.protect(), 'already', 'apt', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(result['added'], [])
        self.assertEqual(self.changing_commands(), [])
        self.assertEqual(snapshot(self.holds), before)
        self.assertFalse(self.record.exists())
        self.assertFalse(self.record.parent.exists())

    def test_only_the_unheld_package_is_held_and_recorded(self):
        self.set_dpkg('ols-modsecurity', 'install ok installed')
        self.holds.write_text('other-package\nopenlitespeed\n')
        result = self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(result['added'], ['ols-modsecurity'])
        self.assertEqual(self.changing_commands(), ['apt-mark LC_ALL=C hold ols-modsecurity'])
        self.assertEqual(self.saved_record()['added'], ['ols-modsecurity'])

    def test_second_run_is_already(self):
        self.check(self.protection.protect(), 'applied')
        record = snapshot(self.record)
        self.events.write_text('')
        self.check(self.protection.protect(), 'already', 'apt', ['openlitespeed'])
        self.assertEqual(self.changing_commands(), [])
        self.assertEqual(snapshot(self.record), record)

    def test_missing_commands_fail_without_raising(self):
        for name in ('dpkg-query', 'apt-mark'):
            with self.subTest(missing=name):
                for fake, body in FAKES.items():
                    self.write_fake(fake, body)
                (self.bin / name).unlink()
                self.only_fakes_on_path()
                result = self.check(self.protection.protect(), 'failed', 'apt')
                self.assertIn(name, result['reason'])
                self.assertFalse(self.record.exists())

    def test_command_that_hangs_fails_at_the_timeout(self):
        self.write_fake('dpkg-query', 'exec sleep 30')
        started = time.time()
        result = self.check(self.make(timeout=0.3).protect(), 'failed', 'apt')
        self.assertLess(time.time() - started, 15)
        self.assertIn('dpkg-query', result['reason'])

    def test_unwritable_record_is_reported(self):
        blocker = self.tmp / 'blocker'
        blocker.write_text('a file where the record directory should be')
        result = self.check(self.make(record=str(blocker / 'record.json')).protect(), 'failed', 'apt')
        # The hold itself is real and is said to be so.
        self.assertIn('openlitespeed', self.held())
        self.assertIn('record', result['reason'].lower())

    def test_status_reports_and_changes_nothing(self):
        self.set_dpkg('ols-modsecurity', 'install ok installed')
        self.holds.write_text('other-package\nopenlitespeed\n')
        before = snapshot(self.holds)
        result = self.check(self.protection.status(), 'unprotected', 'apt', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(result['missing'], ['ols-modsecurity'])
        self.assertIn('ols-modsecurity', result['reason'])
        self.assertEqual(self.changing_commands(), [])
        self.assertEqual(snapshot(self.holds), before)
        self.assertFalse(self.record.exists())
        self.protection.protect()
        result = self.check(self.protection.status(), 'protected', 'apt', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(result['missing'], [])


class RpmFixture(Fixture):
    distro = 'almalinux'
    names = 'openlitespeed'

    def conf(self, data, path=None):
        path = path or self.dnf_conf
        path.write_bytes(data)
        return path

    def apply(self, data, state='applied'):
        self.conf(data)
        self.check(self.protection.protect(), state, 'rpm')
        return self.dnf_conf.read_bytes()

    def tagged(self, eol=b'\n'):
        return TAG.encode() + eol + b'exclude=' + self.names.encode() + eol

    def key_lines(self, data):
        return [line for line in data.splitlines()
                if line.startswith((b'exclude', b'excludepkgs'))]


class RpmConfigTests(RpmFixture):
    def test_key_created_before_the_sections_that_follow_main(self):
        after = self.apply(b'[main]\ngpgcheck=1\ninstallonly_limit=3\n\n[other]\nname=x\n')
        self.assertEqual(after, b'[main]\ngpgcheck=1\ninstallonly_limit=3\n' + self.tagged() +
                         b'\n[other]\nname=x\n')
        saved = self.saved_record()
        self.assertEqual(saved['family'], 'rpm')
        self.assertEqual(saved['path'], os.path.realpath(str(self.dnf_conf)))
        self.assertEqual(saved['added'], ['openlitespeed'])
        self.assertIs(saved['created_key'], True)
        self.assertEqual(saved['version'], 1)

    def test_key_created_when_main_is_the_last_section(self):
        after = self.apply(b'[other]\nname=x\n[main]\ngpgcheck=1\n')
        self.assertEqual(after, b'[other]\nname=x\n[main]\ngpgcheck=1\n' + self.tagged())

    def test_key_created_in_a_file_without_trailing_newline(self):
        after = self.apply(b'[main]\ngpgcheck=1')
        self.assertEqual(after, b'[main]\ngpgcheck=1\n' + self.tagged())

    def test_key_created_in_an_empty_main_section(self):
        self.assertEqual(self.apply(b'[main]\n'), b'[main]\n' + self.tagged())
        self.record.unlink()
        self.assertEqual(self.apply(b'[main]'), b'[main]\n' + self.tagged())

    def test_key_created_above_trailing_blank_and_comment_lines(self):
        after = self.apply(b'[main]\ngpgcheck=1\n\n# the repository below\n[other]\nname=x\n')
        self.assertEqual(after, b'[main]\ngpgcheck=1\n' + self.tagged() +
                         b'\n# the repository below\n[other]\nname=x\n')

    def test_key_created_after_a_continued_value(self):
        after = self.apply(b'[main]\ninstallonlypkgs=kernel\n    kernel-core\n\n[other]\n')
        self.assertEqual(after, b'[main]\ninstallonlypkgs=kernel\n    kernel-core\n' + self.tagged() +
                         b'\n[other]\n')

    def test_tag_line_is_invisible_to_the_panel_package_lock(self):
        # The panel rewrites every line that contains this word.
        self.assertNotIn('exclude', TAG)
        after = self.apply(b'[main]\ngpgcheck=1\n')
        self.assertIn(TAG.encode() + b'\n', after)
        self.assertEqual([line for line in after.splitlines() if b'exclude' in line],
                         [b'exclude=openlitespeed'])

    def test_merges_into_the_customer_line(self):
        cases = (
            (b'[main]\nexclude=kernel*\ngpgcheck=1\n', b'[main]\nexclude=kernel* openlitespeed\ngpgcheck=1\n'),
            # An indented comment is not a value line: names never go into it and
            # a package named in it is not covered.
            (b'[main]\nexclude=foo\n    # note about packages\ngpgcheck=1\n',
             b'[main]\nexclude=foo openlitespeed\n    # note about packages\ngpgcheck=1\n'),
            (b'[main]\nexclude=foo\n    bar\n    ; trailing note\n',
             b'[main]\nexclude=foo\n    bar openlitespeed\n    ; trailing note\n'),
            (b'[main]\nexclude=foo\n    # openlitespeed is updated by CyberPanel\n    bar\n',
             b'[main]\nexclude=foo\n    # openlitespeed is updated by CyberPanel\n    bar openlitespeed\n'),
            (b'[main]\nexcludepkgs = foo, bar\n', b'[main]\nexcludepkgs = foo, bar openlitespeed\n'),
            (b'[main]\nexclude=foo\n    bar\n\tbaz\ngpgcheck=1\n',
             b'[main]\nexclude=foo\n    bar\n\tbaz openlitespeed\ngpgcheck=1\n'),
            (b'[main]\nexclude:foo\n', b'[main]\nexclude:foo openlitespeed\n'),
            (b'[main]\nexclude=\ngpgcheck=1\n', b'[main]\nexclude=openlitespeed\ngpgcheck=1\n'),
            (b'[main]\nexclude = \n', b'[main]\nexclude = openlitespeed\n'),
            (b'[main]\nexclude=kernel*  \n', b'[main]\nexclude=kernel* openlitespeed  \n'),
            (b'[main]\nexclude=OpenLiteSpeed*\n', b'[main]\nexclude=OpenLiteSpeed* openlitespeed\n'),
            (b'[main]\nexclude=openlitespeed-devel\n', b'[main]\nexclude=openlitespeed-devel openlitespeed\n'),
            (b'[main]\n# caf\xe9\nexclude=kernel*\n', b'[main]\n# caf\xe9\nexclude=kernel* openlitespeed\n'),
        )
        for before, expected in cases:
            with self.subTest(before=before):
                if self.record.exists():
                    self.record.unlink()
                self.assertEqual(self.apply(before), expected)
                self.assertNotIn(TAG.encode(), expected)
                saved = self.saved_record()
                self.assertEqual(saved['added'], ['openlitespeed'])
                self.assertIs(saved['created_key'], False)

    def test_last_line_of_the_file_gains_a_newline(self):
        # A later ">>" append must not be glued to the protected names.
        self.assertEqual(self.apply(b'[main]\nexclude=kernel*'), b'[main]\nexclude=kernel* openlitespeed\n')

    def test_names_go_before_an_inline_comment(self):
        # yum reads " ;" as a comment, dnf reads it as more names.
        after = self.apply(b'[main]\nexclude=kernel* ; keep kernels\n')
        self.assertEqual(after, b'[main]\nexclude=kernel* openlitespeed ; keep kernels\n')
        self.record.unlink()
        after = self.apply(b'[main]\nexclude=kernel* ; openlitespeed was here\n')
        self.assertEqual(after, b'[main]\nexclude=kernel* openlitespeed ; openlitespeed was here\n')

    def test_already_covered_writes_nothing(self):
        cases = (
            b'[main]\nexclude=openlitespeed\n',
            b'[main]\nexclude=kernel* openlitespeed*\n',
            b'[main]\nexcludepkgs=*\n',
            b'[main]\nexclude=foo,openlitespeed,bar\n',
            b'[main]\nexclude = foo ,\topenlitespeed\n',
            b'[main]\nexclude=foo\n    open?itespeed\n',
            b'[main]\nexclude:open[l]itespeed\n',
            b'[main]\nexclude=openlitespeed',
            b'[main]\r\nexclude=openlitespeed\r\n',
        )
        for data in cases:
            with self.subTest(data=data):
                self.conf(data)
                before = snapshot(self.dnf_conf)
                listing = sorted(os.listdir(str(self.dnf_conf.parent)))
                result = self.check(self.protection.protect(), 'already', 'rpm', ['openlitespeed'])
                self.assertEqual(result['added'], [])
                self.assertEqual(snapshot(self.dnf_conf), before)
                self.assertEqual(sorted(os.listdir(str(self.dnf_conf.parent))), listing)
                self.assertFalse(self.record.exists())
                self.check(self.protection.status(), 'protected', 'rpm', ['openlitespeed'])

    def test_second_run_is_byte_identical(self):
        self.apply(b'[main]\ngpgcheck=1\n\n[other]\nname=x\n')
        before = snapshot(self.dnf_conf)
        record = snapshot(self.record)
        self.check(self.protection.protect(), 'already', 'rpm', ['openlitespeed'])
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertEqual(snapshot(self.record), record)

    def test_yum_conf_symlink_survives_and_its_target_is_updated(self):
        target = self.conf(b'[main]\ngpgcheck=1\n')
        self.yum_conf.symlink_to('dnf/dnf.conf')
        protection = self.make(dnf_conf=str(self.etc / 'absent' / 'dnf.conf'))
        self.check(protection.protect(), 'applied', 'rpm')
        self.assertTrue(os.path.islink(str(self.yum_conf)))
        self.assertEqual(os.readlink(str(self.yum_conf)), 'dnf/dnf.conf')
        self.assertFalse(os.path.islink(str(target)))
        self.assertEqual(target.read_bytes(), b'[main]\ngpgcheck=1\n' + self.tagged())
        self.assertEqual(self.yum_conf.read_bytes(), target.read_bytes())
        self.assertEqual(self.saved_record()['path'], os.path.realpath(str(target)))
        self.assertEqual(sorted(os.listdir(str(self.etc))), ['dnf', 'yum.conf'])

    def test_dnf_conf_is_preferred_over_a_separate_yum_conf(self):
        self.conf(b'[main]\n')
        self.conf(b'[main]\nkeepcache=0\n', self.yum_conf)
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\n' + self.tagged())
        self.assertEqual(self.yum_conf.read_bytes(), b'[main]\nkeepcache=0\n')

    def test_yum_conf_is_used_when_there_is_no_dnf_conf(self):
        self.conf(b'[main]\nkeepcache=0\n', self.yum_conf)
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.assertEqual(self.yum_conf.read_bytes(), b'[main]\nkeepcache=0\n' + self.tagged())
        self.assertFalse(self.dnf_conf.exists())

    def test_last_of_two_keys_is_extended_and_no_third_appears(self):
        after = self.apply(b'[main]\nexclude=a\ngpgcheck=1\nexcludepkgs=b\nkeepcache=0\n')
        self.assertEqual(after, b'[main]\nexclude=a\ngpgcheck=1\nexcludepkgs=b openlitespeed\nkeepcache=0\n')
        self.assertEqual(len(self.key_lines(after)), 2)

    def test_only_the_last_key_decides_coverage(self):
        after = self.apply(b'[main]\nexclude=openlitespeed\nexclude=kernel*\n')
        self.assertEqual(after, b'[main]\nexclude=openlitespeed\nexclude=kernel* openlitespeed\n')

    def test_other_section_with_its_own_key_is_left_alone(self):
        after = self.apply(b'[main]\ngpgcheck=1\n\n[epel]\nexclude=openlitespeed*\nexcludepkgs=x\n')
        self.assertEqual(after, b'[main]\ngpgcheck=1\n' + self.tagged() +
                         b'\n[epel]\nexclude=openlitespeed*\nexcludepkgs=x\n')
        self.record.unlink()
        after = self.apply(b'[epel]\nexclude=kernel*\n[main]\nexclude=kernel*\n')
        self.assertEqual(after, b'[epel]\nexclude=kernel*\n[main]\nexclude=kernel* openlitespeed\n')

    def test_missing_main_section_fails_with_the_file_intact(self):
        for data in (b'gpgcheck=1\nexclude=foo\n', b'[Main]\ngpgcheck=1\n', b'[other]\nexclude=foo\n', b''):
            with self.subTest(data=data):
                self.conf(data)
                before = snapshot(self.dnf_conf)
                result = self.check(self.protection.protect(), 'failed', 'rpm')
                self.assertIn('[main]', result['reason'])
                self.assertEqual(snapshot(self.dnf_conf), before)
                self.assertFalse(self.record.exists())
                self.check(self.protection.status(), 'unprotected', 'rpm')

    def test_missing_configuration_is_never_created(self):
        self.check(self.protection.protect(), 'failed', 'rpm')
        self.assertFalse(self.dnf_conf.exists())
        self.assertFalse(self.yum_conf.exists())
        self.assertFalse(self.record.exists())
        self.check(self.protection.status(), 'unprotected', 'rpm')

    def test_configuration_that_is_not_a_regular_file_fails(self):
        self.dnf_conf.mkdir()
        self.check(self.protection.protect(), 'failed', 'rpm')
        self.assertEqual(os.listdir(str(self.dnf_conf)), [])

    def simulated_write_error(self, target, **patch):
        self.conf(b'[main]\ngpgcheck=1\nexclude=kernel*\n')
        before = snapshot(self.dnf_conf)
        with mock.patch.object(target, **patch):
            result = self.check(self.protection.protect(), 'failed', 'rpm')
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertEqual(os.listdir(str(self.dnf_conf.parent)), ['dnf.conf'])
        self.assertFalse(self.record.exists())
        return result

    def test_failed_replace_leaves_the_original_and_no_temp_file(self):
        self.simulated_write_error(self.mod.os, attribute='replace', side_effect=OSError(30, 'Read-only file system'))

    def test_failed_fsync_leaves_the_original_and_no_temp_file(self):
        self.simulated_write_error(self.mod.os, attribute='fsync', side_effect=OSError(5, 'Input/output error'))

    def test_failed_temp_file_leaves_the_original(self):
        self.simulated_write_error(self.mod.tempfile, attribute='mkstemp',
                                   side_effect=PermissionError(13, 'Permission denied'))

    def test_write_that_does_not_take_effect_fails(self):
        self.conf(b'[main]\ngpgcheck=1\n')
        with mock.patch.object(self.mod.os, 'replace', side_effect=lambda source, target: os.unlink(source)):
            self.check(self.protection.protect(), 'failed', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\ngpgcheck=1\n')
        self.assertFalse(self.record.exists())

    @unittest.skipIf(os.geteuid() == 0, 'root can write to any directory')
    def test_unwritable_directory_leaves_the_original(self):
        self.conf(b'[main]\ngpgcheck=1\n')
        before = snapshot(self.dnf_conf)
        self.dnf_conf.parent.chmod(0o555)
        self.addCleanup(self.dnf_conf.parent.chmod, 0o755)
        self.check(self.protection.protect(), 'failed', 'rpm')
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertEqual(os.listdir(str(self.dnf_conf.parent)), ['dnf.conf'])

    def test_mode_and_owner_are_preserved(self):
        self.conf(b'[main]\ngpgcheck=1\n')
        self.dnf_conf.chmod(0o640)
        if os.geteuid() == 0:
            os.chown(str(self.dnf_conf), 4242, 4343)
        before = snapshot(self.dnf_conf)
        self.check(self.protection.protect(), 'applied', 'rpm')
        after = snapshot(self.dnf_conf)
        self.assertNotEqual(after[0], before[0])
        self.assertEqual(after[3:], before[3:])
        self.assertEqual(after[3], 0o640)

    def test_crlf_file_stays_crlf(self):
        after = self.apply(b'[main]\r\ngpgcheck=1\r\n\r\n[other]\r\nname=x\r\n')
        self.assertEqual(after, b'[main]\r\ngpgcheck=1\r\n' + self.tagged(b'\r\n') + b'\r\n[other]\r\nname=x\r\n')
        self.record.unlink()
        after = self.apply(b'[main]\r\nexclude=kernel*\r\ngpgcheck=1\r\n')
        self.assertEqual(after, b'[main]\r\nexclude=kernel* openlitespeed\r\ngpgcheck=1\r\n')
        self.record.unlink()
        after = self.apply(b'[main]\r\ngpgcheck=1')
        self.assertEqual(after, b'[main]\r\ngpgcheck=1\r\n' + self.tagged(b'\r\n'))
        self.assertEqual(after.count(b'\n'), after.count(b'\r\n'))

    def test_status_reports_and_changes_nothing(self):
        self.conf(b'[main]\nexclude=kernel*\n')
        before = snapshot(self.dnf_conf)
        result = self.check(self.protection.status(), 'unprotected', 'rpm', ['openlitespeed'])
        self.assertEqual(result['missing'], ['openlitespeed'])
        self.assertIn('openlitespeed', result['reason'])
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertFalse(self.record.exists())
        self.protection.protect()
        result = self.check(self.protection.status(), 'protected', 'rpm', ['openlitespeed'])
        self.assertEqual(result['missing'], [])

    def test_fake_update_replaces_the_core_before_and_not_after(self):
        self.write_fake('dnf', FAKE_DNF)
        self.conf(b'[main]\ngpgcheck=1\ninstallonly_limit=3\n\n[other]\nname=x\n')
        self.assertEqual(subprocess.call(['dnf', 'update', '-y']), 0)
        self.assertEqual(self.core.read_bytes(), b'stock-core')

        self.core.write_bytes(self.custom_core)
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed'])
        self.assertEqual(subprocess.call(['dnf', 'update', '-y']), 0)
        self.assertEqual(self.core.read_bytes(), self.custom_core)

        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(subprocess.call(['dnf', 'update', '-y']), 0)
        self.assertEqual(self.core.read_bytes(), b'stock-core')


class RpmOwnershipTests(RpmFixture):
    def setUp(self):
        super(RpmOwnershipTests, self).setUp()
        self.original = b'[main]\ngpgcheck=1\n'
        self.conf(self.original)

    def refused(self):
        before = snapshot(self.dnf_conf)
        result = self.check(self.protection.protect(), 'refused', 'rpm')
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertFalse(self.record.exists())
        self.check(self.protection.status(), 'refused', 'rpm')
        return result

    def queried(self):
        return [line.rsplit(' ', 1)[1] for line in self.ran() if line.startswith('rpm ')]

    def test_query_matches_the_shell_guard(self):
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed'])
        self.assertEqual(self.ran()[0], 'rpm LC_ALL=C -q --queryformat %{NAME}\\n --file ' + str(self.core))

    def test_unowned_module_and_absent_waf_are_skipped(self):
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed'])
        self.assertEqual(self.queried(), [str(self.core), str(self.module)])
        self.assertEqual(self.dnf_conf.read_bytes(), self.original + self.tagged())

    def test_unowned_waf_is_skipped(self):
        self.waf.write_bytes(b'custom WAF')
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed'])
        self.assertEqual(self.queried(), [str(self.core), str(self.module), str(self.waf)])

    def test_waf_owned_by_its_own_package_adds_that_package(self):
        self.waf.write_bytes(b'custom WAF')
        self.set_owner(self.waf, 'ols-modsecurity')
        self.names = 'openlitespeed ols-modsecurity'
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(self.dnf_conf.read_bytes(), self.original + self.tagged())
        self.assertEqual(self.saved_record()['added'], ['openlitespeed', 'ols-modsecurity'])

    def test_only_the_missing_name_is_added(self):
        self.waf.write_bytes(b'custom WAF')
        self.set_owner(self.waf, 'openlitespeed\nols-modsecurity')
        self.conf(b'[main]\nexclude=ols-modsecurity\n')
        result = self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(result['added'], ['openlitespeed'])
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\nexclude=ols-modsecurity openlitespeed\n')
        self.assertEqual(self.saved_record()['added'], ['openlitespeed'])

    def test_glob_that_covers_both_names_is_already(self):
        self.waf.write_bytes(b'custom WAF')
        self.set_owner(self.waf, 'ols-modsecurity')
        self.conf(b'[main]\nexclude=o*\n')
        self.check(self.protection.protect(), 'already', 'rpm', ['openlitespeed', 'ols-modsecurity'])

    def test_module_owned_by_the_core_package_is_accepted(self):
        self.set_owner(self.module, 'openlitespeed')
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed'])

    def test_unexpected_owner_is_refused(self):
        self.waf.write_bytes(b'custom WAF')
        for target, owners in ((self.core, 'lsphp83'), (self.core, 'ols-modsecurity'),
                               (self.module, 'ols-modsecurity'), (self.module, 'other-owner'),
                               (self.waf, '--exclude=*'), (self.waf, 'openlitespeed\nother-owner')):
            with self.subTest(target=target.name, owners=owners):
                self.set_owner(self.core, 'openlitespeed')
                for path in (self.module, self.waf):
                    owner = self.fake / 'rpm' / (path.name + '.owner')
                    if owner.exists():
                        owner.unlink()
                self.set_owner(target, owners)
                result = self.refused()
                self.assertIn(str(target), result['reason'])

    def test_rpm_error_is_refused(self):
        self.waf.write_bytes(b'custom WAF')
        for target, text, rc in ((self.core, 'error: rpmdb open failed', 1), (self.core, 'openlitespeed', 2),
                                 (self.waf, 'ols-modsecurity', 1),
                                 (self.waf, 'error: cannot open Packages database', 1),
                                 (self.module, '', 0)):
            with self.subTest(target=target.name, text=text, rc=rc):
                for path in (self.core, self.module, self.waf):
                    for suffix in ('.owner', '.rc'):
                        leftover = self.fake / 'rpm' / (path.name + suffix)
                        if leftover.exists():
                            leftover.unlink()
                self.set_owner(self.core, 'openlitespeed')
                self.set_owner(target, text, rc)
                self.refused()

    def test_core_not_owned_by_any_package_is_refused(self):
        self.no_owner(self.core)
        result = self.refused()
        self.assertIn(str(self.core), result['reason'])

    def test_missing_rpm_fails_without_raising(self):
        (self.bin / 'rpm').unlink()
        self.only_fakes_on_path()
        result = self.check(self.protection.protect(), 'failed', 'rpm')
        self.assertIn('rpm', result['reason'])
        self.assertEqual(self.dnf_conf.read_bytes(), self.original)


class ReleaseTests(Fixture):
    def rpm(self, data):
        self.set_distro('almalinux')
        self.dnf_conf.write_bytes(data)

    def test_without_a_record_nothing_happens(self):
        for distro in ('ubuntu', 'almalinux'):
            with self.subTest(distro=distro):
                self.rpm(b'[main]\nexclude=openlitespeed\n')
                self.set_distro(distro)
                self.holds.write_text('other-package\nopenlitespeed\n')
                self.check(self.protection.release(), 'not_applicable', packages=[])
                self.assertEqual(self.ran(), [])
                self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\nexclude=openlitespeed\n')
                self.assertEqual(self.held(), ['other-package', 'openlitespeed'])

    def test_created_key_disappears_with_its_tag_line(self):
        for original in (b'[main]\ngpgcheck=1\n\n[other]\nname=x\n', b'[main]\ngpgcheck=1\n',
                         b'[main]\r\ngpgcheck=1\r\n'):
            with self.subTest(original=original):
                self.rpm(original)
                self.check(self.protection.protect(), 'applied', 'rpm')
                self.assertIn(TAG.encode(), self.dnf_conf.read_bytes())
                result = self.check(self.protection.release(), 'released', 'rpm', ['openlitespeed'])
                self.assertEqual(result['added'], [])
                self.assertEqual(self.dnf_conf.read_bytes(), original)
                self.assertFalse(self.record.exists())
                self.assertEqual(os.listdir(str(self.dnf_conf.parent)), ['dnf.conf'])

    def test_existing_key_keeps_exactly_its_original_tokens(self):
        for original in (b'[main]\nexclude=kernel*\ngpgcheck=1\n', b'[main]\nexcludepkgs = foo, bar\n',
                         b'[main]\nexclude=foo\n    bar\n', b'[main]\nexclude=\n', b'[main]\nexclude = \n',
                         b'[main]\nexclude=kernel* ; keep kernels\n', b'[main]\nexclude:foo  \n',
                         b'[main]\nexclude=kernel*,\n', b'[main]\nexcludepkgs = ,\n',
                         b'[main]\nexclude=a\nexclude=b , \n', b'[main]\r\nexclude=kernel*\r\n'):
            for owners in ('openlitespeed', 'openlitespeed\nols-modsecurity'):
                with self.subTest(original=original, owners=owners):
                    self.rpm(original)
                    self.waf.write_bytes(b'custom WAF')
                    self.set_owner(self.waf, owners)
                    self.check(self.protection.protect(), 'applied', 'rpm', owners.split())
                    self.assertNotEqual(self.dnf_conf.read_bytes(), original)
                    self.check(self.protection.release(), 'released', 'rpm', owners.split())
                    self.assertEqual(self.dnf_conf.read_bytes(), original)
                    self.assertFalse(self.record.exists())

    def test_customer_tokens_added_to_our_key_stay(self):
        self.rpm(b'[main]\ngpgcheck=1\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.dnf_conf.write_bytes(b'[main]\ngpgcheck=1\n' + TAG.encode() + b'\nexclude=openlitespeed kernel*\n')
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\ngpgcheck=1\nexclude=kernel*\n')

    def test_only_recorded_names_are_removed(self):
        self.rpm(b'[main]\nexclude=ols-modsecurity\n')
        self.waf.write_bytes(b'custom WAF')
        self.set_owner(self.waf, 'ols-modsecurity')
        self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed', 'ols-modsecurity'])
        self.check(self.protection.release(), 'released', 'rpm', ['openlitespeed'])
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\nexclude=ols-modsecurity\n')

    def test_names_are_removed_wherever_the_administrator_moved_them(self):
        self.rpm(b'[main]\nexclude=kernel*\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.dnf_conf.write_bytes(b'[main]\nexclude=kernel*,openlitespeed,foo\n    openlitespeed\nexclude=bar\n')
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\nexclude=kernel*,foo\nexclude=bar\n')

    def test_other_sections_are_not_touched(self):
        original = b'[main]\ngpgcheck=1\n[epel]\nexclude=openlitespeed\n'
        self.rpm(original)
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), original)

    def test_release_when_the_configuration_was_already_cleaned(self):
        self.rpm(b'[main]\ngpgcheck=1\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.dnf_conf.write_bytes(b'[main]\ngpgcheck=1\n')
        before = snapshot(self.dnf_conf)
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertFalse(self.record.exists())
        self.dnf_conf.unlink()
        self.check(self.protection.protect(), 'failed', 'rpm')

    def test_release_with_the_configuration_gone(self):
        self.rpm(b'[main]\ngpgcheck=1\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.dnf_conf.unlink()
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertFalse(self.dnf_conf.exists())
        self.assertFalse(self.record.exists())

    def test_failed_release_write_keeps_the_record(self):
        self.rpm(b'[main]\ngpgcheck=1\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        before = snapshot(self.dnf_conf)
        with mock.patch.object(self.mod.os, 'replace', side_effect=OSError(30, 'Read-only file system')):
            self.check(self.protection.release(), 'failed', 'rpm')
        self.assertEqual(snapshot(self.dnf_conf), before)
        self.assertTrue(self.record.exists())
        self.assertEqual(os.listdir(str(self.dnf_conf.parent)), ['dnf.conf'])

    def test_unholds_only_recorded_apt_packages(self):
        self.set_dpkg('ols-modsecurity', 'hold ok installed')
        self.holds.write_text('other-package\nols-modsecurity\n')
        self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed', 'ols-modsecurity'])
        self.events.write_text('')
        self.check(self.protection.release(), 'released', 'apt', ['openlitespeed'])
        self.assertEqual(self.changing_commands(), ['apt-mark LC_ALL=C unhold openlitespeed'])
        self.assertEqual(self.held(), ['other-package', 'ols-modsecurity'])
        self.assertFalse(self.record.exists())
        self.check(self.protection.release(), 'not_applicable')

    def test_apt_release_skips_a_hold_that_is_already_gone(self):
        self.check(self.protection.protect(), 'applied', 'apt')
        self.holds.write_text('other-package\n')
        self.events.write_text('')
        self.check(self.protection.release(), 'released', 'apt')
        self.assertEqual(self.changing_commands(), [])
        self.assertFalse(self.record.exists())

    def test_failed_unhold_keeps_the_record(self):
        self.check(self.protection.protect(), 'applied', 'apt')
        (self.fake / 'unhold.rc').write_text('100')
        result = self.check(self.protection.release(), 'failed', 'apt')
        self.assertIn('openlitespeed', result['reason'])
        self.assertTrue(self.record.exists())
        self.assertIn('openlitespeed', self.held())

    def test_release_works_when_the_core_is_no_longer_custom(self):
        for distro in ('ubuntu', 'almalinux'):
            with self.subTest(distro=distro):
                self.core.write_bytes(self.custom_core)
                self.rpm(b'[main]\nexclude=kernel*\n')
                self.set_distro(distro)
                self.holds.write_text('other-package\n')
                self.check(self.protection.protect(), 'applied')
                self.core.write_bytes(b'stock-core')
                self.check(self.protection.status(), 'not_applicable')
                self.check(self.protection.release(), 'released')
                self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\nexclude=kernel*\n')
                self.assertEqual(self.held(), ['other-package'])
                self.assertFalse(self.record.exists())

    def test_unreadable_record_is_not_guessed_at(self):
        self.record.parent.mkdir()
        self.record.write_text('{not json')
        self.check(self.protection.release(), 'failed')
        self.assertEqual(self.record.read_text(), '{not json')
        self.assertEqual(self.changing_commands(), [])
        # A fresh protection run replaces it with a true record.
        self.check(self.protection.protect(), 'applied', 'apt')
        self.assertEqual(self.saved_record()['added'], ['openlitespeed'])

    def test_protect_after_manual_apt_removal_applies_again(self):
        self.check(self.protection.protect(), 'applied', 'apt')
        self.holds.write_text('other-package\n')
        self.check(self.protection.status(), 'unprotected', 'apt')
        result = self.check(self.protection.protect(), 'applied', 'apt', ['openlitespeed'])
        self.assertEqual(result['added'], ['openlitespeed'])
        self.assertEqual(self.held(), ['other-package', 'openlitespeed'])
        self.assertEqual(self.saved_record()['added'], ['openlitespeed'])

    def test_protect_after_manual_rpm_removal_applies_again(self):
        original = b'[main]\ngpgcheck=1\n'
        self.rpm(original)
        self.check(self.protection.protect(), 'applied', 'rpm')
        protected = self.dnf_conf.read_bytes()
        self.dnf_conf.write_bytes(original)
        self.check(self.protection.status(), 'unprotected', 'rpm')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), protected)
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), original)

    def test_record_is_merged_after_partial_manual_removal(self):
        original = b'[main]\ngpgcheck=1\n'
        self.rpm(original)
        self.waf.write_bytes(b'custom WAF')
        self.set_owner(self.waf, 'ols-modsecurity')
        self.check(self.protection.protect(), 'applied', 'rpm')
        tagged = original + TAG.encode() + b'\nexclude=openlitespeed'
        self.assertEqual(self.dnf_conf.read_bytes(), tagged + b' ols-modsecurity\n')
        self.dnf_conf.write_bytes(tagged + b'\n')
        result = self.check(self.protection.protect(), 'applied', 'rpm', ['openlitespeed', 'ols-modsecurity'])
        self.assertEqual(result['added'], ['ols-modsecurity'])
        self.assertEqual(self.dnf_conf.read_bytes(), tagged + b' ols-modsecurity\n')
        saved = self.saved_record()
        self.assertEqual(saved['added'], ['openlitespeed', 'ols-modsecurity'])
        self.assertIs(saved['created_key'], True)
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), original)

    def test_key_the_administrator_wrote_after_deleting_ours_is_kept(self):
        self.rpm(b'[main]\ngpgcheck=1\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.dnf_conf.write_bytes(b'[main]\ngpgcheck=1\nexclude=\n')
        self.check(self.protection.protect(), 'applied', 'rpm')
        self.assertIs(self.saved_record()['created_key'], False)
        self.check(self.protection.release(), 'released', 'rpm')
        self.assertEqual(self.dnf_conf.read_bytes(), b'[main]\ngpgcheck=1\nexclude=\n')


class CommandLineTests(Fixture):
    def cli(self, *arguments):
        command = [sys.executable, '-IB', str(HELPER)] + list(arguments) + [
            '--root', str(self.root), '--os-release', str(self.os_release), '--record', str(self.record),
            '--dnf-conf', str(self.dnf_conf), '--yum-conf', str(self.yum_conf)]
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   universal_newlines=True, env=dict(os.environ))
        output, errors = process.communicate(timeout=60)
        return process.returncode, output, errors

    def one_object(self, *arguments):
        status, output, errors = self.cli(*arguments)
        self.assertEqual(output.count('\n'), 1, output + errors)
        return status, json.loads(output)

    def test_apt_round_trip(self):
        self.assertEqual(self.one_object('--status'), (1, mock.ANY))
        status, result = self.one_object('--status')
        self.assertEqual((status, result['state'], result['family']), (1, 'unprotected', 'apt'))
        status, result = self.one_object('--apply')
        self.assertEqual((status, result['state'], result['packages']), (0, 'applied', ['openlitespeed']))
        self.assertEqual(self.held(), ['other-package', 'openlitespeed'])
        status, result = self.one_object('--apply')
        self.assertEqual((status, result['state']), (0, 'already'))
        status, result = self.one_object('--status')
        self.assertEqual((status, result['state']), (0, 'protected'))
        status, result = self.one_object('--release')
        self.assertEqual((status, result['state']), (0, 'released'))
        self.assertEqual(self.held(), ['other-package'])
        status, result = self.one_object('--release')
        self.assertEqual((status, result['state']), (0, 'not_applicable'))

    def test_rpm_round_trip(self):
        self.set_distro('rocky')
        original = b'[main]\ngpgcheck=1\n'
        self.dnf_conf.write_bytes(original)
        status, result = self.one_object('--apply')
        self.assertEqual((status, result['state'], result['family']), (0, 'applied', 'rpm'))
        self.assertIn(b'exclude=openlitespeed\n', self.dnf_conf.read_bytes())
        status, result = self.one_object('--status')
        self.assertEqual((status, result['state']), (0, 'protected'))
        status, result = self.one_object('--release')
        self.assertEqual((status, result['state']), (0, 'released'))
        self.assertEqual(self.dnf_conf.read_bytes(), original)

    def test_refused_and_failed_exit_one(self):
        self.set_dpkg('ols-modsecurity', 'install ok unpacked')
        status, result = self.one_object('--apply')
        self.assertEqual((status, result['state']), (1, 'refused'))
        self.assertTrue(result['reason'])
        self.set_dpkg('ols-modsecurity', 'install ok installed')
        (self.fake / 'hold.skip').write_text('openlitespeed\nols-modsecurity\n')
        status, result = self.one_object('--apply')
        self.assertEqual((status, result['state']), (1, 'failed'))

    def test_not_applicable_exits_zero(self):
        self.core.write_bytes(b'stock-core')
        for mode in ('--apply', '--status', '--release'):
            with self.subTest(mode=mode):
                status, result = self.one_object(mode)
                self.assertEqual((status, result['state']), (0, 'not_applicable'))
        self.assertEqual(self.ran(), [])

    def test_exactly_one_mode_is_required(self):
        for arguments in ((), ('--apply', '--status'), ('--release', '--apply')):
            with self.subTest(arguments=arguments):
                status, output, _ = self.cli(*arguments)
                self.assertEqual(status, 2)
                self.assertEqual(output, '')
        self.assertEqual(self.ran(), [])


class ModuleContractTests(Fixture):
    def test_defaults_are_the_production_paths(self):
        defaults = dict((name, parameter.default) for name, parameter in
                        inspect.signature(self.mod.Protection.__init__).parameters.items()
                        if parameter.default is not inspect.Parameter.empty)
        expected = dict(root='/usr/local/lsws', os_release='/etc/os-release',
                        record='/etc/cyberpanel/ols-package-protection.json',
                        dnf_conf='/etc/dnf/dnf.conf', yum_conf='/etc/yum.conf')
        for name, value in expected.items():
            self.assertEqual(defaults.get(name), value, name)

    def test_module_level_functions_use_the_same_rules(self):
        paths = dict(root=str(self.root), os_release=str(self.os_release), record=str(self.record),
                     dnf_conf=str(self.dnf_conf), yum_conf=str(self.yum_conf))
        self.check(self.mod.status(**paths), 'unprotected', 'apt', ['openlitespeed'])
        self.check(self.mod.protect(**paths), 'applied', 'apt', ['openlitespeed'])
        self.check(self.mod.status(**paths), 'protected', 'apt', ['openlitespeed'])
        self.check(self.mod.release(**paths), 'released', 'apt', ['openlitespeed'])

    def test_unexpected_errors_are_returned_not_raised(self):
        with mock.patch.object(self.mod.subprocess, 'Popen', side_effect=RuntimeError('boom')):
            for action in (self.protection.protect, self.protection.status):
                result = action()
                self.assertNotIn(result['state'], FINE)
                self.assertIn('boom', result['reason'])

    def test_source_runs_on_python_36(self):
        source = HELPER.read_text(encoding='utf-8')
        if sys.version_info >= (3, 8):
            try:
                ast.parse(source, filename=str(HELPER), feature_version=(3, 6))
            except ValueError:  # newer interpreters no longer accept 3.6
                ast.parse(source, filename=str(HELPER), feature_version=(3, 7))
        else:
            ast.parse(source, filename=str(HELPER))
        for forbidden in ('capture_output=', 'text=True', 'from __future__ import annotations',
                          'dataclass', ':=', 'removeprefix', 'removesuffix'):
            self.assertNotIn(forbidden, source)

    def test_source_imports_only_the_standard_library(self):
        tree = ast.parse(HELPER.read_text(encoding='utf-8'))
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split('.')[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                self.assertEqual(node.level, 0)
                imported.add((node.module or '').split('.')[0])
        allowed = set(('argparse', 'errno', 'fnmatch', 'json', 'os', 're', 'signal', 'stat',
                       'subprocess', 'sys', 'tempfile'))
        self.assertEqual(imported - allowed, set())


if __name__ == '__main__':
    unittest.main()
