"""A panel upgrade that hangs is stopped, GitHub outages are named, and skipped steps are reported."""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plogical import softUpgrade  # noqa: E402

JOB = 'b' * 32


class Fixture(unittest.TestCase):
    def setUp(self):
        self.base = tempfile.TemporaryDirectory()
        self.addCleanup(self.base.cleanup)
        patcher = mock.patch.object(softUpgrade, 'STATUS_ROOT', Path(self.base.name, 'status'))
        patcher.start()
        self.addCleanup(patcher.stop)
        softUpgrade.STATUS_ROOT.mkdir()
        self.output = Path(self.base.name, 'output')
        self.output.write_text('')

    def upgrader(self, script):
        """A stand-in upgrader in its own session, as run() starts the real one."""
        process = subprocess.Popen([sys.executable, '-c', script, str(self.output)],
                                   start_new_session=True)
        self.addCleanup(lambda: process.poll() is None and process.kill())
        return process

    def alive(self, pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        try:
            # A killed child of an exited parent is reaped by init; a zombie counts as gone.
            return Path('/proc/%d/stat' % pid).read_text().rsplit(')', 1)[-1].split()[0] != 'Z'
        except OSError:
            return False


HANGS = '''
import subprocess, sys, time
child = subprocess.Popen(['sleep', '300'])
open(sys.argv[1] + '.child', 'w').write(str(child.pid))
time.sleep(300)
'''

WRITES = '''
import sys, time
for _ in range(12):
    with open(sys.argv[1], 'a') as log:
        log.write('working\\n')
    time.sleep(0.25)
'''


class SupervisionTests(Fixture):
    def test_an_upgrader_that_writes_nothing_is_stopped_with_what_it_started(self):
        process = self.upgrader(HANGS)
        started = time.monotonic()
        with self.assertRaisesRegex(softUpgrade.Stopped, 'wrote nothing for 0 minutes and was stopped'):
            softUpgrade.supervise(process, [str(self.output)], pause=0.2, idle_limit=1.5)
        self.assertLess(time.monotonic() - started, 30)
        self.assertIsNotNone(process.poll())
        child = int(Path(str(self.output) + '.child').read_text())
        for _ in range(50):
            if not self.alive(child):
                break
            time.sleep(0.1)
        self.assertFalse(self.alive(child), 'the hung child of the upgrader is still running')

    def test_an_upgrader_that_keeps_writing_is_left_to_finish(self):
        process = self.upgrader(WRITES)
        self.assertEqual(0, softUpgrade.supervise(process, [str(self.output)], pause=0.1, idle_limit=1))

    def test_a_run_is_stopped_after_the_longest_time_even_while_writing(self):
        process = self.upgrader(WRITES.replace('range(12)', 'range(400)'))
        with self.assertRaisesRegex(softUpgrade.Stopped, 'still running after'):
            softUpgrade.supervise(process, [str(self.output)], pause=0.1, idle_limit=60, longest=1)

    def test_the_status_record_tells_the_page_how_long_the_run_wrote_nothing(self):
        softUpgrade.record_status(JOB, 'running')
        process = self.upgrader(HANGS)
        with self.assertRaises(softUpgrade.Stopped):
            softUpgrade.supervise(process, [str(self.output)], job=JOB, pause=0.2, idle_limit=1)
        record = json.loads(softUpgrade.status_path(JOB).read_text())
        self.assertEqual('running', record['state'])
        self.assertLessEqual(abs(record['active'] - time.time()), 5)

    def test_a_stop_request_ends_a_silent_run(self):
        process = self.upgrader(HANGS)
        softUpgrade.stop_path(JOB).write_text('')
        with self.assertRaisesRegex(softUpgrade.Stopped, 'stopped from the panel'):
            softUpgrade.supervise(process, [str(self.output)], job=JOB, pause=0.2, stop_after=0)
        self.assertFalse(softUpgrade.stop_path(JOB).exists())

    def test_a_stop_request_does_not_end_a_run_that_is_writing(self):
        process = self.upgrader(WRITES)
        softUpgrade.stop_path(JOB).write_text('')
        self.assertEqual(0, softUpgrade.supervise(process, [str(self.output)], job=JOB, pause=0.1,
                                                  stop_after=60))
        self.assertFalse(softUpgrade.stop_path(JOB).exists(), 'a declined request must not wait for later')


class StopRequestTests(Fixture):
    def running(self, active):
        softUpgrade.record_status(JOB, 'running', active=active)

    def test_only_a_run_that_wrote_nothing_for_five_minutes_can_be_stopped(self):
        now = time.time()
        self.running(now - 60)
        answer = softUpgrade.request_stop(JOB)
        self.assertEqual(0, answer['stopped'])
        self.assertIn('still writing', answer['message'])
        self.assertFalse(softUpgrade.stop_path(JOB).exists())
        status = softUpgrade.read_status(JOB)
        self.assertFalse(status['stoppable'])
        self.running(now - softUpgrade.STOP_AFTER - 5)
        self.assertTrue(softUpgrade.read_status(JOB)['stoppable'])
        self.assertEqual(1, softUpgrade.request_stop(JOB)['stopped'])
        self.assertTrue(softUpgrade.stop_path(JOB).exists())

    def test_a_run_that_ended_or_never_reported_activity_is_not_stopped(self):
        softUpgrade.record_status(JOB, 'complete')
        self.assertEqual(0, softUpgrade.request_stop(JOB)['stopped'])
        softUpgrade.record_status(JOB, 'running')
        self.assertEqual(0, softUpgrade.request_stop(JOB)['stopped'])
        self.assertNotIn('stoppable', softUpgrade.read_status(JOB))
        with self.assertRaises(ValueError):
            softUpgrade.request_stop('../x')

    def test_a_stop_file_placed_as_a_link_is_not_followed(self):
        target = Path(self.base.name, 'elsewhere')
        target.write_text('kept')
        os.symlink(str(target), str(softUpgrade.stop_path(JOB)))
        self.running(time.time() - softUpgrade.STOP_AFTER - 5)
        with self.assertRaises(OSError):
            softUpgrade.request_stop(JOB)
        self.assertEqual('kept', target.read_text())


class GitHubTests(unittest.TestCase):
    def call(self, *failures, attempts=3):
        calls = []

        def action():
            calls.append(1)
            if len(calls) <= len(failures):
                raise failures[len(calls) - 1]
            return 'answer'
        sleeps = []
        try:
            return softUpgrade.from_github(action, 'the release v3.0.19', attempts=attempts,
                                           sleep=sleeps.append), calls, sleeps
        except Exception as error:
            return error, calls, sleeps

    def test_a_short_outage_is_ridden_out(self):
        answer, calls, sleeps = self.call(URLError('timed out'), HTTPError('u', 503, 'x', {}, None))
        self.assertEqual('answer', answer)
        self.assertEqual(3, len(calls))
        self.assertEqual([10, 10], sleeps)

    def test_a_longer_outage_ends_with_a_message_that_says_nothing_changed(self):
        resolve = subprocess.CalledProcessError(128, ['git'], stderr="fatal: unable to access "
                                                "'https://github.com/usmannasir/cyberpanel.git/': "
                                                "Could not resolve host: github.com\n")
        error, calls, _ = self.call(resolve, resolve, resolve)
        self.assertIsInstance(error, RuntimeError)
        self.assertEqual(3, len(calls))
        self.assertIn('GitHub could not be reached for the release v3.0.19', str(error))
        self.assertIn('Could not resolve host: github.com', str(error))
        self.assertIn('Nothing was changed on this server', str(error))
        error, _, _ = self.call(*[subprocess.TimeoutExpired(['git'], 30)] * 3)
        self.assertIn('no answer within 30 seconds', str(error))

    def test_an_answer_from_github_is_not_taken_for_an_outage(self):
        missing = HTTPError('u', 404, 'Not Found', {}, None)
        error, calls, _ = self.call(missing)
        self.assertIs(missing, error)
        self.assertEqual(1, len(calls))
        refused = subprocess.CalledProcessError(128, ['git'], stderr='fatal: remote error: upload-pack: not our ref f\n')
        error, calls, _ = self.call(refused)
        self.assertIs(refused, error)
        self.assertEqual(1, len(calls))

    def test_git_is_told_to_give_up_on_a_stalled_transfer(self):
        seen = []

        def run(command, **options):
            seen.append(options['env'])
            return subprocess.CompletedProcess(command, 0, stdout='%s\trefs/heads/v3.0.18\n' % ('c' * 40))
        with mock.patch.object(softUpgrade.subprocess, 'run', run):
            self.assertEqual('c' * 40, softUpgrade.resolve_release('v3.0.18'))
        self.assertEqual('1000', seen[0]['GIT_HTTP_LOW_SPEED_LIMIT'])
        self.assertEqual('0', seen[0]['GIT_TERMINAL_PROMPT'])


class ReportTests(Fixture):
    def test_the_upgraders_list_of_steps_that_did_not_complete_is_read(self):
        report = Path(self.base.name, 'report.json')
        self.assertEqual([], softUpgrade.read_report(report))
        report.write_text(json.dumps({'incomplete': ['The panel web worker was not rebuilt: x'] + ['y' * 900] * 40}))
        steps = softUpgrade.read_report(report)
        self.assertEqual('The panel web worker was not rebuilt: x', steps[0])
        self.assertEqual(30, len(steps))
        self.assertEqual(600, len(steps[1]))
        for content in ('not json', '[]', '{"incomplete": "x"}'):
            report.write_text(content)
            self.assertEqual([], softUpgrade.read_report(report))

    def test_a_completed_run_records_its_incomplete_steps_for_the_page(self):
        with mock.patch.object(softUpgrade, 'run', return_value=['The automatic update timer was not refreshed: x']) as run, \
                mock.patch.object(softUpgrade, 'activate_panel_runtime', return_value={'http_status': 200}), \
                mock.patch.object(softUpgrade, 'kept_installations', return_value=set()):
            self.assertEqual(0, softUpgrade.run_panel_job('v3.0.18', JOB))
        self.assertEqual(JOB, run.call_args[1]['job'])
        record = json.loads(softUpgrade.status_path(JOB).read_text())
        self.assertEqual('complete', record['state'])
        self.assertEqual(['The automatic update timer was not refreshed: x'], record['incomplete'])

    def test_a_stopped_run_is_reported_as_failed_and_the_previous_version_put_back(self):
        with mock.patch.object(softUpgrade, 'run', side_effect=softUpgrade.Stopped('The upgrade wrote nothing for 30 minutes and was stopped.')), \
                mock.patch.object(softUpgrade, 'recover_from_failure',
                                  side_effect=lambda known, lock, error: str(error) + ' put back') as recover, \
                mock.patch.object(softUpgrade, 'kept_installations', return_value=set()):
            self.assertEqual(1, softUpgrade.run_panel_job('v3.0.18', JOB))
        recover.assert_called_once()
        record = json.loads(softUpgrade.status_path(JOB).read_text())
        self.assertEqual('failed', record['state'])
        self.assertEqual('The upgrade wrote nothing for 30 minutes and was stopped. put back', record['message'])


if __name__ == '__main__':
    unittest.main()
