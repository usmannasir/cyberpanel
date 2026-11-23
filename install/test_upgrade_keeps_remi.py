"""The upgrade puts back the Remi repository that removing epel-release takes with it.

remi-release requires epel-release, and Pre_Upgrade_Setup_Repository removes
epel-release on RPM systems, so every upgrade removed Remi; LiteSpeed's PHP
packages for EL9 need libicu78, which only Remi provides. The real shell
functions run here with rpm and yum replaced by recorders.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'cyberpanel_upgrade.sh').read_text()


def functions():
    start = SOURCE.index('Remember_Remi_Release() {')
    return SOURCE[start:SOURCE.index('\nPre_Upgrade_Setup_Repository() {', start)]


class RemiRelease(unittest.TestCase):
    def run_upgrade_steps(self, version, before, after, install_works=True):
        """Remember, remove EPEL (and Remi with it), restore. before/after:
        whether remi-release is installed before the removal / after EPEL is back."""
        with tempfile.TemporaryDirectory() as directory:
            tools = Path(directory, 'bin')
            tools.mkdir()
            calls = Path(directory, 'calls')
            state = Path(directory, 'remi-installed')
            if before:
                state.write_text('')
            (tools / 'rpm').write_text('#!/bin/bash\necho "rpm $*" >> %s\n[[ -e %s ]]\n' % (calls, state))
            (tools / 'yum').write_text('#!/bin/bash\necho "yum $*" >> %s\n%s\n' % (
                calls, ('touch %s' % state) if install_works else 'exit 1'))
            for tool in ('rpm', 'yum'):
                (tools / tool).chmod(0o755)
            script = functions().replace('/var/log/cyberpanel_upgrade_debug.log', str(Path(directory, 'debug.log')))
            removal = '' if after else 'rm -f %s' % state
            result = subprocess.run(
                ['bash', '-c', '%s\nRemember_Remi_Release\n%s\nRestore_Remi_Release\n' % (script, removal)],
                env=dict(os.environ, PATH='%s:/usr/bin:/bin' % tools, Server_OS_Version=version),
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
            self.assertEqual(0, result.returncode, result.stdout)
            installs = [line for line in (calls.read_text().splitlines() if calls.exists() else [])
                        if line.startswith('yum')]
            log = Path(directory, 'debug.log')
            return installs, (log.read_text() if log.exists() else '')

    def test_remi_removed_with_epel_comes_back(self):
        for version in ('8', '9', '10'):
            installs, log = self.run_upgrade_steps(version, before=True, after=False)
            self.assertEqual(['yum install -y https://rpms.remirepo.net/enterprise/remi-release-%s.rpm' % version],
                             installs)
            self.assertIn('Remi repository installed again', log)

    def test_on_9_and_10_remi_lost_in_an_earlier_upgrade_comes_back(self):
        for version in ('9', '10'):
            installs, _ = self.run_upgrade_steps(version, before=False, after=False)
            self.assertEqual(['yum install -y https://rpms.remirepo.net/enterprise/remi-release-%s.rpm' % version],
                             installs)

    def test_on_8_a_server_without_remi_is_left_without_it(self):
        self.assertEqual([], self.run_upgrade_steps('8', before=False, after=False)[0])

    def test_nothing_is_installed_when_remi_is_still_there(self):
        for version in ('8', '9', '10'):
            self.assertEqual([], self.run_upgrade_steps(version, before=True, after=True)[0])

    def test_a_failed_install_is_reported_and_does_not_stop_the_upgrade(self):
        installs, log = self.run_upgrade_steps('9', before=True, after=False, install_works=False)
        self.assertEqual(1, len(installs))
        self.assertIn('WARNING: the Remi repository was removed with EPEL and could not be installed again', log)

    def test_the_steps_surround_every_removal_and_reinstall_of_epel(self):
        start = SOURCE.index('\nPre_Upgrade_Setup_Repository() {')
        body = SOURCE[start:SOURCE.index('\nelif [[ "$Server_OS" = "Ubuntu" ]] ; then', start)]
        self.assertLess(body.index('Remember_Remi_Release'), body.index('yum autoremove epel-release -y'))
        self.assertEqual(1, body.count('Remember_Remi_Release'))
        self.assertEqual(body.count('install epel-release -y'), body.count('Restore_Remi_Release'))
        for line in body.splitlines():
            if 'install epel-release -y' in line:
                following = body[body.index(line) + len(line):].lstrip().splitlines()[0]
                self.assertEqual('Restore_Remi_Release', following.strip(), line)


if __name__ == '__main__':
    unittest.main()
