"""The installer waits for apt and dpkg locks that another process holds.

apt-get gives up at once ("Could not get lock") while the daily apt update or
unattended upgrades hold a lock, and DPkg::Lock::Timeout covers only the dpkg
frontend lock. Everything here works on lock files in a temporary directory.
"""
import ast
import os
from pathlib import Path
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

# Tries to take the lock without waiting, as dpkg does, again and again.
TAKER = '''
import fcntl, os, sys, time
refused = 0
end = time.time() + float(sys.argv[2])
while time.time() < end:
    fd = os.open(sys.argv[1], os.O_RDWR)
    try:
        fcntl.lockf(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.lockf(fd, fcntl.LOCK_UN)
    except OSError:
        refused += 1
    os.close(fd)
print(refused)
'''


def hold(path, seconds):
    """Hold path's lock the way apt does, in another process, for seconds."""
    process = subprocess.Popen([sys.executable, '-c', HOLDER, str(path), str(seconds)],
                               stdout=subprocess.PIPE, universal_newlines=True)
    assert process.stdout.readline().strip() == 'held'
    process.stdout.close()
    return process


def lock_files(directory):
    paths = []
    for name in ('lock-frontend', 'lock', 'lists-lock', 'archives-lock'):
        path = os.path.join(directory, name)
        open(path, 'w').close()
        paths.append(path)
    return paths


class Budget(unittest.TestCase):
    def setUp(self):
        patcher = mock.patch.dict(os.environ)
        patcher.start()
        self.addCleanup(patcher.stop)
        os.environ.pop(install_utils.PACKAGE_LOCK_DEADLINE, None)


class Locks(Budget):
    def setUp(self):
        super().setUp()
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.paths = lock_files(directory.name)

    def test_free_locks_and_missing_files_are_not_busy(self):
        self.assertEqual([], install_utils.busy_package_locks(self.paths + ['/nonexistent/lock']))

    def test_a_lock_another_process_holds_is_busy_with_its_holder(self):
        holder = hold(self.paths[2], 5)
        try:
            busy = install_utils.busy_package_locks(self.paths)
        finally:
            holder.kill()
            holder.wait()
        self.assertEqual(['%s (process %d, python3)' % (self.paths[2], holder.pid)],
                         [entry.replace(os.path.basename(sys.executable), 'python3') for entry in busy])
        self.assertEqual([], install_utils.busy_package_locks(self.paths))

    def test_asking_takes_no_lock(self):
        # A process that takes the lock without waiting, as dpkg does, is never
        # refused while the installer keeps asking who holds it.
        taker = subprocess.Popen([sys.executable, '-c', TAKER, self.paths[1], '2'],
                                 stdout=subprocess.PIPE, universal_newlines=True)
        end = time.monotonic() + 2
        while time.monotonic() < end:
            install_utils.busy_package_locks(self.paths)
        self.assertEqual('0', taker.communicate()[0].strip())

    def test_the_wait_ends_when_the_other_process_lets_go(self):
        holder = hold(self.paths[3], 2)
        said = []
        started = time.monotonic()
        try:
            free = install_utils.wait_for_package_locks(poll=0.2, paths=self.paths, say=said.append)
        finally:
            holder.kill()
            holder.wait()
        self.assertTrue(free)
        self.assertGreaterEqual(time.monotonic() - started, 1.5)
        self.assertIn('it holds %s (process %d' % (self.paths[3], holder.pid), said[0])
        self.assertTrue(said[-1].startswith('The other package manager has finished'))

    def test_nothing_is_said_or_budgeted_when_the_locks_are_free(self):
        said = []
        self.assertTrue(install_utils.wait_for_package_locks(paths=self.paths, say=said.append))
        self.assertEqual([], said)
        self.assertNotIn(install_utils.PACKAGE_LOCK_DEADLINE, os.environ)


class OneBudget(Budget):
    def wait(self, now, said):
        return install_utils.wait_for_package_locks(
            timeout=120, poll=5, clock=lambda: now[0],
            sleep=lambda seconds: now.__setitem__(0, now[0] + seconds), say=said.append)

    def test_the_wait_is_bounded_and_says_once_a_minute(self):
        now, said = [1000.0], []
        with mock.patch.object(install_utils, 'busy_package_locks', return_value=['/var/lib/apt/lists/lock (x)']):
            self.assertFalse(self.wait(now, said))
        self.assertEqual(1120.0, now[0])
        self.assertEqual('1120', os.environ[install_utils.PACKAGE_LOCK_DEADLINE])
        self.assertTrue(said[-1].startswith('[WARNING] Another package manager still holds'))
        self.assertEqual(2, sum(1 for text in said if text.startswith('Waiting for another package manager')))

    def test_a_used_up_budget_is_not_spent_again(self):
        now, said = [1000.0], []
        with mock.patch.object(install_utils, 'busy_package_locks', return_value=['/var/lib/dpkg/lock (x)']):
            self.wait(now, said)
            spent = now[0]
            self.assertFalse(self.wait(now, said))
        self.assertEqual(spent, now[0])

    def test_the_budget_cyberpanel_sh_started_is_kept(self):
        os.environ[install_utils.PACKAGE_LOCK_DEADLINE] = '1030'
        now, said = [1000.0], []
        with mock.patch.object(install_utils, 'busy_package_locks', return_value=['/var/lib/dpkg/lock (x)']):
            self.assertFalse(self.wait(now, said))
        self.assertEqual(1030.0, now[0])

    def test_the_clock_is_the_time_since_boot(self):
        first = install_utils.seconds_since_boot()
        self.assertGreater(first, 0)
        self.assertLessEqual(first, install_utils.seconds_since_boot())


class AptCommands(Budget):
    def test_apt_and_dpkg_commands_on_ubuntu(self):
        for command in ('apt-get update', 'DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server',
                        'env DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp83 lsphp83-*',
                        'apt update -y', 'apt install quota -y', 'dpkg -i x.deb',
                        'add-apt-repository -y ppa:x/y', 'true && apt-get update'):
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
    """cyberpanel.sh waits the same way before its own apt commands."""

    def setUp(self):
        self.script = (ROOT / 'cyberpanel.sh').read_text()
        opening = 'deadline=$(python3 -I - "${CP_PACKAGE_LOCK_DEADLINE:-}" <<\'WAIT\'\n'
        start = self.script.index(opening) + len(opening)
        self.waiter = self.script[start:self.script.index('\nWAIT\n', start)]

    def test_apt_and_retried_apt_get_wait_first(self):
        self.assertIn('\napt() { Wait_For_Package_Locks; command apt "$@"; }\n', self.script)
        retry = self.script[self.script.index('\nRetry_Command() {\n'):]
        retry = retry[:retry.index('\n}\n')]
        self.assertIn('(apt|apt-get|add-apt-repository)[[:space:]] ]]; then\n      Wait_For_Package_Locks', retry)
        # No function name that bash refuses in POSIX mode (sh cyberpanel.sh on RPM systems).
        self.assertNotIn('\napt-get()', self.script)
        result = subprocess.run(['bash', '--posix', '-n', str(ROOT / 'cyberpanel.sh')],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        self.assertEqual(0, result.returncode, result.stderr)

    def test_the_script_asks_about_the_same_locks_the_same_way(self):
        tree = ast.parse(self.waiter)
        values = {node.targets[0].id: ast.literal_eval(node.value) for node in tree.body
                  if isinstance(node, ast.Assign) and isinstance(node.targets[0], ast.Name)
                  and node.targets[0].id in ('LOCKS', 'FLOCK', 'WAIT_SECONDS')}
        self.assertEqual({'LOCKS': install_utils.APT_LOCKS, 'FLOCK': install_utils._FLOCK,
                          'WAIT_SECONDS': install_utils.PACKAGE_LOCK_WAIT_SECONDS}, values)
        self.assertIn('fcntl.F_GETLK', self.waiter)
        self.assertNotIn('LOCK_NB', self.waiter)

    def run_waiter(self, paths, *arguments):
        waiter = self.waiter
        for real, temporary in zip(install_utils.APT_LOCKS, paths):
            waiter = waiter.replace(repr(real), repr(temporary))
        self.assertNotIn('/var/lib', waiter)
        return subprocess.run([sys.executable, '-I', '-c', waiter] + list(arguments), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, universal_newlines=True, timeout=60)

    def test_the_script_waits_until_the_lock_is_free_and_hands_on_its_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = lock_files(directory)
            holder = hold(paths[2], 2)
            started = time.monotonic()
            try:
                result = self.run_waiter(paths, '')
            finally:
                holder.kill()
                holder.wait()
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertGreaterEqual(time.monotonic() - started, 1.5)
            self.assertIn('it holds %s (process %d' % (paths[2], holder.pid), result.stderr)
            self.assertIn('The other package manager has finished; continuing.', result.stderr)
            deadline = float(result.stdout.strip())
            self.assertAlmostEqual(install_utils.seconds_since_boot() + 1800, deadline, delta=30)

            # Free locks: no wait, nothing said, no budget started.
            result = self.run_waiter(paths, '')
            self.assertEqual(('', ''), (result.stdout, result.stderr))

    def test_the_script_does_not_wait_past_the_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            paths = lock_files(directory)
            holder = hold(paths[0], 30)
            try:
                started = time.monotonic()
                result = self.run_waiter(paths, '%.0f' % (install_utils.seconds_since_boot() - 1))
            finally:
                holder.kill()
                holder.wait()
            self.assertLess(time.monotonic() - started, 5)
            self.assertIn('trying anyway', result.stderr)


if __name__ == '__main__':
    unittest.main()
