"""Fresh install: the PHP build packages of the timezone step go only to the PHP versions that are installed.

On AlmaLinux 10 the step installed lsphp??-mysqlnd and lsphp??-devel. The
wildcard also named PHP 8.6, which the installer never installs; the
packages made /usr/local/lsws/lsphp86 without PHP itself, and the command
line accepted that folder as PHP 8.6 for new websites.
"""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


def shell_function(source, name):
    match = re.search(r'^' + re.escape(name) + r'\(\) \{\n.*?^\}', source, re.M | re.S)
    if match is None:
        raise AssertionError('%s is not in cyberpanel.sh' % name)
    return match.group(0)


class InstalledPHPBuildPackagesTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.root = Path(folder.name)
        self.calls = self.root / 'calls'
        self.source = (ROOT / 'cyberpanel.sh').read_text()

    def lsphp(self, digits, php=True, executable=True):
        folder = self.root / ('lsphp' + digits) / 'bin'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / 'php-config').write_text('#!/bin/sh\n')
        if php:
            (folder / 'php').write_text('#!/bin/sh\n')
            (folder / 'php').chmod(0o755 if executable else 0o644)

    def bash(self, script, **environment):
        # universal_newlines and the two pipes: AlmaLinux 8 runs the panel on Python 3.6.
        return subprocess.run(['bash'], input=script, universal_newlines=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, timeout=20,
                              env=dict(os.environ, LSWS_ROOT=str(self.root), QA_CALLS=str(self.calls),
                                       **environment))

    def recorded(self):
        return self.calls.read_text().splitlines() if self.calls.exists() else []

    def test_only_folders_with_their_php_count_as_installed(self):
        for digits in ('81', '83', '85'):
            self.lsphp(digits)
        self.lsphp('84', executable=False)
        self.lsphp('86', php=False)  # what the extension packages left on AlmaLinux 10
        (self.root / 'lsphp74.bak' / 'bin').mkdir(parents=True)
        result = self.bash(shell_function(self.source, 'installed_lsphp_versions') + '\ninstalled_lsphp_versions\n')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['81', '83', '85'], result.stdout.split())

    def test_no_version_prints_nothing_and_succeeds(self):
        result = self.bash(shell_function(self.source, 'installed_lsphp_versions') + '\ninstalled_lsphp_versions\n')
        self.assertEqual((0, ''), (result.returncode, result.stdout))

    def timezone_step(self, server_os):
        """Run the real timezone step with every command that would touch the server recorded instead."""
        stubs = '''
log_function_start() { :; }
log_info() { :; }
Debug_Log2() { :; }
install_package() { printf 'install %s\\n' "$1" >> "$QA_CALLS"; }
yum() { printf 'yum %s\\n' "$*" >> "$QA_CALLS"; }
configure_php_timezone() { printf 'configure %s\\n' "$1" >> "$QA_CALLS"; }
rm() { :; }
mkdir() { :; }
cd() { :; }
wget() { :; }
tar() { :; }
'''
        script = (stubs + shell_function(self.source, 'installed_lsphp_versions') + '\n'
                  + shell_function(self.source, 'Post_Install_PHP_TimezoneDB') + '\nPost_Install_PHP_TimezoneDB\n')
        result = self.bash(script, Server_OS=server_os)
        self.assertEqual(0, result.returncode, result.stderr)
        return [line for line in self.recorded() if not line.startswith('configure ')]

    def test_almalinux_installs_build_packages_for_the_installed_versions_only(self):
        for digits in ('81', '82', '83', '84', '85'):
            self.lsphp(digits)
        calls = self.timezone_step('CentOS')
        self.assertEqual(['install make gcc glibc-devel libmemcached-devel zlib-devel']
                         + ['install lsphp%s-mysqlnd lsphp%s-devel' % (digits, digits)
                            for digits in ('81', '82', '83', '84', '85')]
                         + ['yum remove -y lsphp??-mysql'], calls)
        self.assertFalse([call for call in calls if '86' in call or '??-devel' in call or '??-mysqlnd' in call])

    def test_a_folder_left_without_php_gets_no_packages(self):
        self.lsphp('85')
        self.lsphp('86', php=False)
        calls = self.timezone_step('CentOS')
        self.assertIn('install lsphp85-mysqlnd lsphp85-devel', calls)
        self.assertFalse([call for call in calls if 'lsphp86' in call])

    def test_ubuntu_keeps_its_packages(self):
        # On Ubuntu 26.04 PHP 8.6 arrives complete in the PHP step: apt reads
        # lsphp80* as a regular expression that names every lsphp8x package.
        # This branch is unchanged.
        self.lsphp('85')
        self.assertEqual(['install libmagickwand-dev pkg-config build-essential lsphp*-dev'],
                         self.timezone_step('Ubuntu'))


if __name__ == '__main__':
    unittest.main()
