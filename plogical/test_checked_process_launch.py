import unittest
from unittest import mock
from plogical.processUtilities import ProcessUtilities


class CheckedProcessLaunchTests(unittest.TestCase):
    def test_checked_launch_propagates_thread_start_failure(self):
        with mock.patch.object(ProcessUtilities, 'start', side_effect=RuntimeError('thread unavailable')), \
                mock.patch('plogical.processUtilities.logging.writeToFile'):
            with self.assertRaisesRegex(RuntimeError, 'thread unavailable'):
                ProcessUtilities.popenExecutioner('ignored', raise_errors=True)

    def test_existing_callers_keep_best_effort_behavior(self):
        with mock.patch.object(ProcessUtilities, 'start', side_effect=RuntimeError('thread unavailable')), \
                mock.patch('plogical.processUtilities.logging.writeToFile'):
            self.assertIsNone(ProcessUtilities.popenExecutioner('ignored'))


if __name__ == '__main__':
    unittest.main()
