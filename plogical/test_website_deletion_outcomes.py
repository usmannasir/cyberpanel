import json
import threading
import unittest
from unittest import mock
from plogical.websiteDeletion import RESULT_PREFIX, wait_for_deletion


class DeletionOutcomeTests(unittest.TestCase):
    def result(self, completed=True):
        return RESULT_PREFIX + json.dumps({'completed': completed})

    def test_worker_completion_is_confirmed(self):
        execute = mock.Mock(return_value=(1, self.result()))
        self.assertEqual('completed', wait_for_deletion('fixture', execute, mock.Mock()))
        execute.assert_called_once_with('fixture', retRequired=True)

    def test_worker_failure_is_not_success(self):
        for result in ((0, self.result()), (1, self.result(False)), (1, 'unrelated output'), None, (1, RESULT_PREFIX + '{}')):
            with self.subTest(result=result):
                self.assertEqual('failed', wait_for_deletion('fixture', mock.Mock(return_value=result), mock.Mock()))

    def test_exception_is_reported(self):
        log = mock.Mock()
        self.assertEqual('failed', wait_for_deletion('fixture', mock.Mock(side_effect=OSError('launch failed')), log))
        log.assert_called_once()

    def test_timeout_does_not_cancel_running_worker(self):
        release = threading.Event()
        done = threading.Event()
        def execute(*args, **kwargs):
            release.wait(2)
            done.set()
            return 1, self.result()
        try:
            self.assertEqual('pending', wait_for_deletion('fixture', execute, mock.Mock(), timeout=0.01))
            self.assertFalse(done.is_set())
        finally:
            release.set()
        self.assertTrue(done.wait(1))

    def test_thread_launch_failure_is_reported(self):
        with mock.patch('plogical.websiteDeletion.threading.Thread.start', side_effect=RuntimeError('no worker')):
            self.assertEqual('failed', wait_for_deletion('fixture', mock.Mock(), mock.Mock()))

    def test_late_failure_is_logged(self):
        release = threading.Event()
        logged = threading.Event()
        def execute(*args, **kwargs):
            release.wait(2)
            return 0, ''
        try:
            self.assertEqual('pending', wait_for_deletion('fixture', execute, lambda text: logged.set(), timeout=0.01))
        finally:
            release.set()
        self.assertTrue(logged.wait(1))
