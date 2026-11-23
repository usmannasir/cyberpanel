"""The installer waits for apt and dpkg locks that another process holds.

apt-get gives up at once ("Could not get lock") while the daily apt update or
unattended upgrades hold a lock, and DPkg::Lock::Timeout covers only the dpkg
frontend lock. Everything here works on lock files in a temporary directory.
"""
import ast
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import install_utils  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]

HOLDER = '''
import fcntl, sys, time
f = open(sys.argv[1], 'w')
fcntl.lockf(f, fcntl.LOCK_EX)
print('held', flush=True)
time.sleep(float(sys.argv[2]))
'''


def hold(path, seconds):
    """Hold path's lock the way apt does, in another process, for seconds."""
    process = subprocess.Popen([sys.executable, '-c', HOLDER, str(path), str(seconds)],
                               stdout=subprocess.PIPE, universal_newlines=True)
    assert process.stdout.readline().strip() == 'held'
    return process


class Locks(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = []
        for name in ('lock-frontend', 'lock', 'lists-lock', 'archives-lock'):
            path = Path(directory.name) / name
            path.write_text('')
            self.paths.append(str(path))

    def test_free_locks_and_missing_files_are_not_busy(self):
        self.assertEqual([], install_utils.busy_package_locks(self.paths + ['/nonexistent/lock']))

    def test_a_lock_another_process_holds_is_busy_and_is_left_alone(self):
        holder = hold(self.paths[2], 5)
        try:
            self.assertEqual([self.paths[2]], install_utils.busy_package_locks(self.paths))
            self.assertEqual([self.paths[2]], install_utils.busy_package_locks(self.paths))
        finally:
            holder.kill()
            holder.wait()
        self.assertEqual([], install_utils.busy_package_locks(self.paths))

    def test_the_wait_ends_when_the_other_process_lets_go(self):
        holder = hold(self.paths[2], 2)
        said = []
        started = time.monotonic()
        try:
            free = install_utils.wait_for_package_locks(timeout=60, poll=0.2, paths=self.paths, say=said.append)
        finally:
            holder.kill()
            holder.wait()
        self.assertTrue(free)
        self.assertGreaterEqual(time.monotonic() - started, 1.5)
        self.assertIn(self.paths[2], said[0])
        self.assertTrue(said[-1].startswith('The other package manager has finished'))

    def test_the_wait_is_bounded(self):
        now = [0.0]
        said = []
        with mock.patch.object(install_utils, 'busy_package_locks', return_value=['/var/lib/apt/lists/lock']):
            free = install_utils.wait_for_package_locks(
                timeout=120, poll=5, clock=lambda: now[0],
                sleep=lambda seconds: now.__setitem__(0, now[0] + seconds), say=said.append)
        self.assertFalse(free)
        self.assertEqual(120.0, now[0])
        self.assertTrue(said[-1].startswith('[WARNING] Another package manager still holds'))
        # One message a minute while waiting (at 0 and 60 s), not one per poll.
        self.assertEqual(2, sum(1 for text in said if text.startswith('Waiting for another package manager')))

    def test_nothing_is_said_when_the_locks_are_free(self):
        said = []
        self.assertTrue(install_utils.wait_for_package_locks(paths=self.paths, say=said.append))
        self.assertEqual([], said)


class AptCommands(unittest.TestCase):
    def test_apt_and_dpkg_commands_on_ubuntu(self):
        for command in ('apt-get update', 'DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server',
                        'env DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp83 lsphp83-*',
                        'apt update -y', 'apt install quota -y', 'dpkg -i x.deb',
                        'sudo apt install linux-image-extra-virtual -y', 'true && apt-get update'):
            self.assertTrue(install_utils.uses_apt(command, install_utils.ubuntu), command)

    def test_other_commands_and_other_systems(self):
        for command in ('systemctl enable pdns', 'apt-key add key.gpg', 'cp aptfile /tmp/x',
                        'echo capture', 'dnf install -y pdns'):
            self.assertFalse(install_utils.uses_apt(command, install_utils.ubuntu), command)
        self.assertFalse(install_utils.uses_apt('apt-get update', install_utils.cent8))

    def test_call_waits_before_every_attempt_of_an_apt_command(self):
        with mock.patch.object(install_utils, 'wait_for_package_locks') as wait, \
                mock.patch.object(install_utils.subprocess, 'call', side_effect=[100, 0]) as run, \
                mock.patch.object(install_utils, 'stdOut'):
            self.assertTrue(install_utils.call('DEBIAN_FRONTEND=noninteractive apt-get update', install_utils.ubuntu,
                                               'x', 'apt-get update', 1, 1, os.EX_OSERR, True))
        self.assertEqual(2, wait.call_count)
        self.assertEqual(2, run.call_count)

    def test_call_does_not_wait_for_other_commands(self):
        with mock.patch.object(install_utils, 'wait_for_package_locks') as wait, \
                mock.patch.object(install_utils.subprocess, 'call', return_value=0), \
                mock.patch.object(install_utils, 'stdOut'):
            install_utils.call('systemctl enable pdns', install_utils.ubuntu, 'x', 'enable', 1, 1)
            install_utils.call('dnf install -y pdns', install_utils.cent8, 'x', 'install', 1, 1)
        wait.assert_not_called()


class ShellScript(unittest.TestCase):
    """cyberpanel.sh waits the same way before its own apt and apt-get."""

    def setUp(self):
        self.script = (ROOT / 'cyberpanel.sh').read_text()
        start = self.script.index("python3 - <<'WAIT'\n") + len("python3 - <<'WAIT'\n")
        self.waiter = self.script[start:self.script.index('\nWAIT\n', start)]

    def test_apt_and_apt_get_of_the_script_wait_first(self):
        self.assertIn('\napt() { Wait_For_Package_Locks; command apt "$@"; }\n', self.script)
        self.assertIn('\napt-get() { Wait_For_Package_Locks; command apt-get "$@"; }\n', self.script)
        # Defined before the first function that runs apt.
        self.assertLess(self.script.index('\napt-get() {'), self.script.index('\nPre_Install_Required_Components() {'))

    def test_the_script_waits_for_the_same_locks(self):
        tree = ast.parse(self.waiter)
        locks = next(node.value for node in tree.body if isinstance(node, ast.Assign)
                     and node.targets[0].id == 'LOCKS')
        self.assertEqual(install_utils.APT_LOCKS, ast.literal_eval(locks))

    def test_the_script_waits_until_the_lock_is_free(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = []
            for name in ('lock-frontend', 'lock', 'lists-lock', 'archives-lock'):
                path = os.path.join(directory, name)
                open(path, 'w').close()
                paths.append(path)
            waiter = self.waiter
            for real, temporary in zip(install_utils.APT_LOCKS, paths):
                waiter = waiter.replace(repr(real), repr(temporary))
            self.assertNotIn('/var/lib', waiter)
            holder = hold(paths[3], 2)
            started = time.monotonic()
            try:
                result = subprocess.run([sys.executable, '-c', waiter], stdout=subprocess.PIPE,
                                        universal_newlines=True, timeout=60)
            finally:
                holder.kill()
                holder.wait()
            self.assertEqual(0, result.returncode)
            self.assertGreaterEqual(time.monotonic() - started, 1.5)
            self.assertIn('Waiting for another package manager to finish (it holds %s)' % paths[3], result.stdout)
            self.assertIn('The other package manager has finished; continuing.', result.stdout)


if __name__ == '__main__':
    unittest.main()
