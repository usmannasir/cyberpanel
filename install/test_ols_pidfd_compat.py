"""PID descriptor compatibility: never substitute a numerical-PID signal."""
import ctypes
import errno
import json
import os
from pathlib import Path
import platform
import select
import signal
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'plogical'))
import olsWatchdog as watchdog

PROOFS = []

class PidfdCompatibilityTests(unittest.TestCase):
    def test_standard_open_api_is_preferred(self):
        with patch.object(watchdog.os, 'pidfd_open', return_value=77, create=True) as native, patch.object(watchdog.ctypes, 'CDLL') as libc:
            self.assertEqual(watchdog._pidfd_open(321), 77)
        native.assert_called_once_with(321)
        libc.assert_not_called()

    def test_standard_signal_api_is_preferred(self):
        with patch.object(watchdog.signal, 'pidfd_send_signal', return_value=None, create=True) as native, patch.object(watchdog.ctypes, 'CDLL') as libc:
            self.assertIsNone(watchdog._pidfd_send_signal(77, signal.SIGTERM))
        native.assert_called_once_with(77, signal.SIGTERM)
        libc.assert_not_called()

    def test_existing_api_errors_never_fall_back(self):
        for code in (errno.EPERM, errno.ENOSYS):
            for owner, name, invoke in ((watchdog.os, 'pidfd_open', lambda: watchdog._pidfd_open(321)), (watchdog.signal, 'pidfd_send_signal', lambda: watchdog._pidfd_send_signal(77, 0))):
                with self.subTest(code=code, name=name), patch.object(owner, name, side_effect=OSError(code, 'refused'), create=True), patch.object(watchdog.ctypes, 'CDLL') as libc, patch.object(watchdog.os, 'kill') as kill:
                    with self.assertRaises(OSError) as caught:
                        invoke()
                    self.assertEqual(caught.exception.errno, code)
                    libc.assert_not_called()
                    kill.assert_not_called()

    def test_raw_syscall_error_is_fatal_and_preserves_errno(self):
        for code in (errno.EPERM, errno.ENOSYS):
            for invoke, number in ((lambda: watchdog._pidfd_open(321), 434), (lambda: watchdog._pidfd_send_signal(77, 15), 424)):
                def refused(*args):
                    ctypes.set_errno(code)
                    return -1
                libc = Mock()
                libc.syscall.side_effect = refused
                with self.subTest(code=code, syscall=number), patch.object(watchdog.os, 'pidfd_open', None, create=True), patch.object(watchdog.signal, 'pidfd_send_signal', None, create=True), patch.object(watchdog.ctypes, 'CDLL', return_value=libc), patch.object(watchdog.os, 'kill') as kill:
                    with self.assertRaises(OSError) as caught:
                        invoke()
                    self.assertEqual(caught.exception.errno, code)
                    self.assertEqual(libc.syscall.call_args[0][0].value, number)
                    kill.assert_not_called()

    def test_unsupported_architecture_refuses_without_syscall(self):
        with patch.object(watchdog.os, 'pidfd_open', None, create=True), patch.object(watchdog.signal, 'pidfd_send_signal', None, create=True), patch.object(watchdog.platform, 'machine', return_value='aarch64'), patch.object(watchdog.ctypes, 'CDLL') as libc:
            for invoke in (lambda: watchdog._pidfd_open(1), lambda: watchdog._pidfd_send_signal(4, 0)):
                with self.assertRaises(OSError) as caught:
                    invoke()
                self.assertEqual(caught.exception.errno, errno.ENOSYS)
            libc.assert_not_called()

    def test_32bit_process_refuses_without_syscall(self):
        with patch.object(watchdog.os, 'pidfd_open', None, create=True), patch.object(watchdog.signal, 'pidfd_send_signal', None, create=True), patch.object(watchdog.ctypes, 'sizeof', return_value=4), patch.object(watchdog.ctypes, 'CDLL') as libc:
            for invoke in (lambda: watchdog._pidfd_open(1), lambda: watchdog._pidfd_send_signal(4, 0)):
                with self.assertRaises(OSError) as caught:
                    invoke()
                self.assertEqual(caught.exception.errno, errno.ENOSYS)
            libc.assert_not_called()

    def test_nonlinux_refuses_without_syscall(self):
        with patch.object(watchdog.os, 'pidfd_open', None, create=True), patch.object(watchdog.signal, 'pidfd_send_signal', None, create=True), patch.object(watchdog.sys, 'platform', 'darwin'), patch.object(watchdog.ctypes, 'CDLL') as libc:
            for invoke in (lambda: watchdog._pidfd_open(1), lambda: watchdog._pidfd_send_signal(4, 0)):
                with self.assertRaises(OSError) as caught:
                    invoke()
                self.assertEqual(caught.exception.errno, errno.ENOSYS)
            libc.assert_not_called()

    def test_arguments_cannot_be_truncated_to_another_pid_or_fd(self):
        with patch.object(watchdog.os, 'pidfd_open', None, create=True), patch.object(watchdog.signal, 'pidfd_send_signal', None, create=True), patch.object(watchdog.ctypes, 'CDLL') as libc:
            for value in (-1, 2 ** 32 + 1):
                for invoke in (lambda: watchdog._pidfd_open(value), lambda: watchdog._pidfd_send_signal(value, 0), lambda: watchdog._pidfd_send_signal(4, value)):
                    with self.assertRaises(OverflowError):
                        invoke()
            with self.assertRaises(TypeError):
                watchdog._pidfd_open(1.1)
            libc.assert_not_called()

    def real_child_proof(self, forced):
        target = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        unrelated = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'])
        opened = []
        proof = {'forced_missing_apis': forced, 'target_pid': target.pid, 'unrelated_pid': unrelated.pid}
        try:
            fd = watchdog._pidfd_open(target.pid)
            otherfd = watchdog._pidfd_open(unrelated.pid)
            opened.extend([fd, otherfd])
            proof['target_fdinfo'] = Path('/proc/self/fdinfo/%s' % fd).read_text()
            proof['target_fdlink'] = os.readlink('/proc/self/fd/%s' % fd)
            self.assertEqual(proof['target_fdlink'], 'anon_inode:[pidfd]')
            fields = dict(line.split(':', 1) for line in proof['target_fdinfo'].splitlines())
            self.assertEqual(int(fields['Pid']), target.pid)
            self.assertFalse(os.get_inheritable(fd))
            self.assertFalse(select.select([fd], [], [], 0)[0])
            with patch.object(watchdog.os, 'kill', side_effect=AssertionError('numerical PID signal forbidden')):
                watchdog._pidfd_send_signal(fd, 0)
                watchdog._pidfd_send_signal(fd, signal.SIGTERM)
                self.assertEqual(select.select([fd], [], [], 5)[0], [fd])
                self.assertEqual(target.wait(timeout=5), -signal.SIGTERM)
                self.assertIsNone(unrelated.poll())
                with self.assertRaises(OSError) as caught:
                    watchdog._pidfd_send_signal(fd, 0)
                self.assertEqual(caught.exception.errno, errno.ESRCH)
                os.close(fd)
                opened.remove(fd)
                with self.assertRaises(OSError) as caught:
                    watchdog._pidfd_send_signal(fd, signal.SIGTERM)
                self.assertEqual(caught.exception.errno, errno.EBADF)
                reused = os.open('/dev/null', os.O_RDONLY)
                try:
                    if reused != fd:
                        os.dup2(reused, fd)
                        opened.append(fd)
                    with self.assertRaises(OSError) as caught:
                        watchdog._pidfd_send_signal(fd, signal.SIGTERM)
                    self.assertEqual(caught.exception.errno, errno.EBADF)
                    self.assertIsNone(unrelated.poll())
                finally:
                    os.close(reused)
                watchdog._pidfd_send_signal(otherfd, signal.SIGTERM)
                self.assertEqual(unrelated.wait(timeout=5), -signal.SIGTERM)
            proof['checks'] = ['exact_pid_fdinfo', 'close_on_exec', 'live_not_ready', 'signal_zero', 'target_only_SIGTERM', 'exit_readiness', 'dead_target_ESRCH', 'closed_fd_EBADF', 'reused_devnull_fd_EBADF', 'unrelated_alive_until_own_cleanup']
            PROOFS.append(proof)
        finally:
            for fd in opened:
                os.close(fd)
            for process in (target, unrelated):
                if process.poll() is None:
                    # Cleanup only our still-owned unreaped child; never product fallback.
                    process.terminate()
                    process.wait(timeout=5)

    def test_native_runtime_child_pidfd_identity_and_signal(self):
        self.real_child_proof(False)

    def test_missing_apis_real_raw_syscall_child_identity_and_signal(self):
        with patch.object(watchdog.os, 'pidfd_open', None, create=True), patch.object(watchdog.signal, 'pidfd_send_signal', None, create=True):
            self.real_child_proof(True)

if __name__ == '__main__':
    result = unittest.main(verbosity=2, exit=False).result
    if os.environ.get('PIDFD_RECEIPT'):
        Path(os.environ['PIDFD_RECEIPT']).write_text(json.dumps({'python': sys.version, 'kernel': platform.release(), 'machine': platform.machine(), 'stdlib_pidfd_open': hasattr(os, 'pidfd_open'), 'stdlib_pidfd_send_signal': hasattr(signal, 'pidfd_send_signal'), 'tests': result.testsRun, 'failures': len(result.failures), 'errors': len(result.errors), 'skipped': len(result.skipped), 'proofs': PROOFS}, indent=2) + '\n')
    sys.exit(not result.wasSuccessful())
