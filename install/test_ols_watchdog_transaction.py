"""Run real Bash/legacy watchers, pidfd handoff and flock in a disposable PID namespace."""
import fcntl
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
import unittest
from unittest.mock import Mock, patch

REPO = Path(__file__).resolve().parent.parent
IMAGE = os.environ.get('CP_OLS_NATIVE_SERVICE_IMAGE')
LEGACY = os.environ.get('CP_OLS_NATIVE_LEGACY_WATCHDOG')


def wait_for(predicate):
    end = time.monotonic() + 6
    while time.monotonic() < end:
        try:
            result = predicate()
        except (FileNotFoundError, ProcessLookupError):
            result = False
        if result:
            return result
        time.sleep(.04)
    raise AssertionError('Timed out waiting for the watchdog fixture')


def wait_for_watchdog_snapshot(inspect, expected, live_identity, timeout=2):
    """Wait only for an exact read-only snapshot of this fixture's known owners."""
    expected = sorted(expected)
    deadline = time.monotonic() + timeout
    last_refusal = None
    while time.monotonic() < deadline:
        for pid, ticks, unused_kind in expected:
            if live_identity(pid) != ticks:
                raise RuntimeError('A known watchdog fixture identity changed')
        try:
            observed = inspect()
        except RuntimeError as error:
            # A /proc snapshot can cross a Bash child fork/exec boundary. The
            # production guard keeps refusing; no handoff or mutation is retried.
            last_refusal = error
            time.sleep(.04)
            continue
        if sorted(record[:3] for record in observed) != expected:
            raise AssertionError('Unexpected watchdog in the fixture snapshot')
        for pid, ticks, unused_kind in expected:
            if live_identity(pid) != ticks:
                raise RuntimeError('A known watchdog fixture identity changed')
        return observed
    raise RuntimeError('Watchdog fixture snapshot did not settle: ' + str(last_refusal))


def guest():
    from olsWatchdog import (ALIAS, COOPERATIVE, LEGACY as LEGACY_HASH, SCRIPT, hash_file,
                             inspect_watchdog, prepare_watchdog, process_fields, sleep_child)
    root = Path('/usr/local/lsws')
    root.mkdir(exist_ok=True)
    SCRIPT.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy('/legacy', SCRIPT)
    SCRIPT.chmod(0o700)
    ALIAS.parent.mkdir(parents=True, exist_ok=True)
    ALIAS.symlink_to(SCRIPT)
    assert hash_file(SCRIPT) == LEGACY_HASH
    # Record manager requests locally. The container has no host PID namespace,
    # socket or network. The PHP-kill branch must not execute while locked.
    stub = ALIAS.parent / 'systemctl'
    stub.write_text('#!/bin/sh\necho "$@" >>/tmp/controller\nexit 0\n')
    stub.chmod(0o755)
    service_env = dict(os.environ, PATH='/usr/local/bin:/usr/bin:/bin')
    def launch(args):
        code = ('import subprocess; p=subprocess.Popen(%r, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL);'
                'print(p.pid)' % args)
        return int(subprocess.check_output([sys.executable, '-c', code], env=service_env))
    old = launch(['/bin/bash', str(ALIAS), 'lsws'])
    maria = launch(['/bin/bash', str(ALIAS), 'mariadb'])
    def idle(pid):
        entry = Path('/proc') / str(pid)
        children = (entry / ('task/%d/children' % pid)).read_text().split()
        return len(children) == 1 and sleep_child(Path('/proc') / children[0])
    wait_for(lambda: idle(old) and idle(maria))
    maria_ticks = process_fields(Path('/proc') / str(maria))[19]
    lockfile = root / '.ols-bundle-install.lock'
    with lockfile.open('w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        original = inspect_watchdog(root, allow_legacy=True)
        assert len(original) == 1 and original[0][0] == old
        for attempt in ('stopped', 'ambiguous'):
            ambiguous = None
            if attempt == 'ambiguous':
                ambiguous = launch(['/bin/bash', '-x', str(ALIAS), 'web'])
                wait_for(lambda: idle(ambiguous))
            try:
                prepare_watchdog(root, attempt != 'stopped', script='/candidate')
            except RuntimeError:
                pass
            else:
                raise AssertionError('Did not refuse ' + attempt)
            assert hash_file(SCRIPT) == LEGACY_HASH and idle(old)
            if ambiguous:
                # This is the PID returned by our own bounded disposable process.
                os.kill(ambiguous, 15)
                wait_for(lambda: not (Path('/proc') / str(ambiguous)).exists())
        # A blocked/ignored signal must be refused before touching the active
        # monitor or its installed script. Override only this test's /proc read.
        status_path = Path('/proc') / str(old) / 'status'
        original_read = Path.read_text
        def ignoring_term(path, *args, **kwargs):
            text = original_read(path, *args, **kwargs)
            if path == status_path:
                lines = text.splitlines()
                lines = [('SigIgn:\t0000000000004000' if line.startswith('SigIgn:') else line) for line in lines]
                return '\n'.join(lines)
            return text
        with patch.object(Path, 'read_text', ignoring_term):
            try:
                prepare_watchdog(root, True, script='/candidate')
            except RuntimeError as error:
                assert 'normal termination' in str(error)
            else:
                raise AssertionError('Ignored TERM did not refuse')
        assert hash_file(SCRIPT) == LEGACY_HASH and inspect_watchdog(root, allow_legacy=True) == original
        before = Path('/tmp/controller').read_text()
        # Crash boundary between successor acknowledgement and retiring the
        # original. The retry must adopt that waiter, not launch a duplicate.
        successors = []
        original_popen = subprocess.Popen
        def start_successor(*args, **kwargs):
            process = original_popen(*args, **kwargs)
            fields = process_fields(Path('/proc') / str(process.pid))
            successors.append((process.pid, fields[19], 'cooperative'))
            return process
        with patch('olsWatchdog.subprocess.Popen', side_effect=start_successor), \
                patch('olsWatchdog._pidfd_send_signal', side_effect=RuntimeError('injected interruption')):
            try:
                prepare_watchdog(root, True, script='/candidate')
            except RuntimeError as error:
                assert 'injected interruption' in str(error)
            else:
                raise AssertionError('Missing interrupted handoff')
        assert len(successors) == 1
        def live_identity(pid):
            fields = process_fields(Path('/proc') / str(pid))
            return fields[19] if fields[0] not in ('X', 'Z') else None
        waiting = wait_for_watchdog_snapshot(
            lambda: inspect_watchdog(root, allow_legacy=True),
            [original[0][:3], successors[0]], live_identity)
        assert len(waiting) == 2 and hash_file(SCRIPT) == COOPERATIVE and idle(old)
        waiter = next(r[0] for r in waiting if r[2] == 'cooperative')
        prepare_watchdog(root, True, script='/candidate')
        current = inspect_watchdog(root)
        assert len(current) == 1 and current[0][0] == waiter and waiter != old and current[0][2] == 'cooperative'
        assert hash_file(SCRIPT) == COOPERATIVE and not (Path('/proc') / str(old)).exists()
        time.sleep(1.3)
        assert Path('/tmp/controller').read_text() == before
        prepare_watchdog(root, True, script='/candidate')
        assert inspect_watchdog(root)[0][:3] == current[0][:3]
    assert process_fields(Path('/proc') / str(maria))[19] == maria_ticks
    assert idle(maria)
    # Start a new cooperative iteration without waiting for the live watcher's
    # usual minute-long sleep. Its manager child must see the shared lock held,
    # and must not inherit the lock descriptor itself.
    stub.write_text('#!/bin/sh\nif flock -xn /usr/local/lsws/.ols-bundle-install.lock -c true; then exit 2; fi\n'
                    'for f in /proc/self/fd/*; do [ "$(readlink "$f")" != /usr/local/lsws/.ols-bundle-install.lock ] || exit 3; done\n'
                    'echo "$@" >>/tmp/locked-check\nexit 0\n')
    launch(['/bin/bash', str(SCRIPT), 'lsws'])
    wait_for(lambda: Path('/tmp/locked-check').is_file())
    print('positive handoff; stopped/ambiguous refusal; shared-lock exclusion; no inherited lock; MariaDB preserved')


class WatchdogSnapshotReadinessTests(unittest.TestCase):
    def setUp(self):
        self.expected = [(12, '100', 'legacy'), (34, '200', 'cooperative')]
        self.observed = [entry + (1, ['lsws']) for entry in self.expected]
        self.identities = {12: '100', 34: '200'}

    def test_transient_refusal_requires_a_fresh_exact_snapshot(self):
        inspect = Mock(side_effect=[RuntimeError('missing executing descriptor'), self.observed])
        with patch.object(time, 'sleep'):
            self.assertEqual(wait_for_watchdog_snapshot(
                inspect, self.expected, self.identities.get), self.observed)
        self.assertEqual(inspect.call_count, 2)

    def test_persistent_foreign_candidate_refusal_is_not_accepted(self):
        inspect = Mock(side_effect=RuntimeError('unverified foreign candidate'))
        with patch.object(time, 'monotonic', side_effect=[0, 0, .04, .08, .12]), \
                patch.object(time, 'sleep'):
            with self.assertRaisesRegex(RuntimeError, 'did not settle.*foreign candidate'):
                wait_for_watchdog_snapshot(inspect, self.expected, self.identities.get, timeout=.1)
        self.assertEqual(inspect.call_count, 3)

    def test_unknown_watcher_in_a_complete_snapshot_is_immediately_rejected(self):
        inspect = Mock(return_value=self.observed + [(56, '300', 'cooperative', 1, ['lsws'])])
        with self.assertRaisesRegex(AssertionError, 'Unexpected watchdog'):
            wait_for_watchdog_snapshot(inspect, self.expected, self.identities.get)
        inspect.assert_called_once()

    def test_changed_known_identity_is_rejected_before_snapshot(self):
        inspect = Mock()
        self.identities[34] = 'reused-pid'
        with self.assertRaisesRegex(RuntimeError, 'identity changed'):
            wait_for_watchdog_snapshot(inspect, self.expected, self.identities.get)
        inspect.assert_not_called()

    def test_known_identity_must_survive_the_snapshot(self):
        def inspect():
            self.identities[34] = 'reused-pid'
            return self.observed
        with self.assertRaisesRegex(RuntimeError, 'identity changed'):
            wait_for_watchdog_snapshot(inspect, self.expected, self.identities.get)


class WatchdogTransactionTests(unittest.TestCase):
    @unittest.skipUnless(IMAGE and LEGACY, 'native watchdog fixture not configured')
    def test_real_legacy_watchdog_migrates_under_the_transaction_lock(self):
        command = ['docker', 'run', '--rm', '--init', '--network=none',
                   '-v', str(REPO / 'plogical') + ':/src:ro',
                   '-v', str(REPO / 'CPScripts/watchdog.sh') + ':/candidate:ro',
                   '-v', str(Path(LEGACY).resolve()) + ':/legacy:ro',
                   '-v', str(Path(__file__).resolve()) + ':/guest.py:ro',
                   '-e', 'PYTHONPATH=/src', IMAGE, 'python3', '-B', '/guest.py', 'guest']
        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=35)
        self.assertEqual(0, result.returncode, result.stdout.decode())


if __name__ == '__main__' and sys.argv[-1:] == ['guest']:
    guest()
