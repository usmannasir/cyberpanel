"""A stalled or trickling bundle download is replaced, never accepted or left hanging."""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time
import types
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guarded_download  # noqa: E402


ROOT = Path(__file__).resolve().parents[1]

# Each invocation appends its arguments to "calls" and follows the matching
# entry of "script" (the last entry repeats).
FAKE_WGET = r'''
import json, os, signal, sys, time
state = os.environ['FAKE_WGET_STATE']
with open(os.path.join(state, 'calls'), 'a') as calls:
    calls.write(json.dumps({'argv': sys.argv[1:], 'pid': os.getpid()}) + '\n')
with open(os.path.join(state, 'calls')) as calls:
    index = len(calls.read().splitlines()) - 1
with open(os.path.join(state, 'script')) as script:
    steps = json.load(script)
step = steps[min(index, len(steps) - 1)]
if step.get('ignore_term'):
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
if step.get('create', True):
    target = open(sys.argv[sys.argv.index('-O') + 1], 'wb', buffering=0)
    target.write(b'a' * step.get('burst', 0))
    deadline = time.time() + step.get('seconds', 0)
    while time.time() < deadline:
        target.write(b'a' * step.get('chunk', 0))
        time.sleep(0.05)
    target.close()
else:
    time.sleep(step.get('seconds', 0))
sys.exit(step.get('exit', 0))
'''

FAST = {'burst': 50000}
TRICKLE = {'burst': 100, 'chunk': 10, 'seconds': 30}
GUARDED = ['-q', '--show-progress', '--tries=1', '--timeout=30']
GUARDED_IPV4 = GUARDED + ['--inet4-only']
UNHURRIED = ['-q', '--show-progress', '--timeout=60']


def alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


class LadderTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        wget = self.root / 'wget'
        wget.write_text('#!' + sys.executable + '\n' + FAKE_WGET)
        wget.chmod(0o755)
        environment = patch.dict(os.environ, {
            'PATH': str(self.root) + os.pathsep + os.environ['PATH'],
            'FAKE_WGET_STATE': str(self.root)})
        environment.start()
        self.addCleanup(environment.stop)
        guarded_download._proven.clear()
        self.addCleanup(guarded_download._proven.clear)
        self.destination = str(self.root / 'candidate with spaces')
        self.url = 'https://example.invalid/binary?token=one&part=two'
        self.messages = []
        self.policy = guarded_download.Policy(
            window=0.6, first_byte=0.6, stall=0.8, poll=0.05, pause=0, grace=1.0)

    def script(self, *steps):
        (self.root / 'script').write_text(json.dumps(list(steps)))

    def calls(self):
        path = self.root / 'calls'
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text().splitlines()]

    def flags(self):
        """Arguments of every call without the trailing -O DEST -- URL."""
        for call in self.calls():
            self.assertEqual(['-O', self.destination, '--', self.url], call['argv'][-4:])
        return [call['argv'][:-4] for call in self.calls()]

    def fetch(self, url=None):
        started = time.time()
        try:
            return guarded_download.fetch(url or self.url, self.destination,
                                          self.messages.append, self.policy)
        finally:
            self.elapsed = time.time() - started

    def assert_no_child_left(self):
        self.assertEqual([], [call['pid'] for call in self.calls() if alive(call['pid'])])

    def test_healthy_download_runs_once_without_delay(self):
        self.script(FAST)
        self.assertTrue(self.fetch())
        self.assertEqual([GUARDED], self.flags())
        self.assertEqual(50000, os.path.getsize(self.destination))
        self.assertLess(self.elapsed, 2)

    def test_trickle_is_dropped_and_retried_over_ipv4(self):
        self.script(TRICKLE, FAST)
        self.assertTrue(self.fetch())
        self.assertEqual([GUARDED, GUARDED_IPV4], self.flags())
        self.assertEqual(50000, os.path.getsize(self.destination))
        self.assert_no_child_left()
        self.assertLess(self.elapsed, 5)
        self.assertTrue(any('too slow' in message for message in self.messages), self.messages)

    def test_failed_transfer_is_never_accepted_and_leaves_no_partial(self):
        # A partial larger than the caller's 10 KB size check must not survive.
        self.script({'burst': 30000, 'exit': 4}, {'create': False, 'exit': 4})
        self.assertFalse(self.fetch())
        self.assertEqual([GUARDED, GUARDED_IPV4, UNHURRIED], self.flags())
        self.assertFalse(os.path.exists(self.destination))
        self.assertTrue(any('exit code 4' in message for message in self.messages), self.messages)

    def test_every_partial_is_removed_after_the_last_attempt(self):
        self.script({'burst': 30000, 'exit': 4})
        self.assertFalse(self.fetch())
        self.assertEqual(3, len(self.calls()))
        self.assertFalse(os.path.exists(self.destination))

    def test_slow_but_moving_last_attempt_is_allowed_to_finish(self):
        self.script(TRICKLE, TRICKLE, {'burst': 100, 'chunk': 200, 'seconds': 1.5})
        self.assertTrue(self.fetch())
        self.assertEqual([GUARDED, GUARDED_IPV4, UNHURRIED], self.flags())
        self.assertGreater(os.path.getsize(self.destination), 100)
        self.assert_no_child_left()
        self.assertTrue(any('without a speed limit' in message for message in self.messages),
                        self.messages)

    def test_stalled_last_attempt_fails_in_bounded_time(self):
        self.script(TRICKLE, TRICKLE, {'burst': 3000, 'seconds': 30})
        self.assertFalse(self.fetch())
        self.assertEqual(3, len(self.calls()))
        self.assert_no_child_left()
        self.assertFalse(os.path.exists(self.destination))
        self.assertLess(self.elapsed, 8)

    def test_connection_that_never_delivers_data_is_replaced(self):
        for silent in ({'seconds': 30}, {'create': False, 'seconds': 30}):
            with self.subTest(silent=silent):
                (self.root / 'calls').write_text('')
                guarded_download._proven.clear()
                self.script(silent, FAST)
                self.assertTrue(self.fetch())
                self.assertEqual([GUARDED, GUARDED_IPV4], self.flags())
                self.assert_no_child_left()

    def test_small_file_finishing_inside_the_window_is_not_judged(self):
        self.script({'burst': 10, 'chunk': 10, 'seconds': 0.3})
        self.assertTrue(self.fetch())
        self.assertEqual([GUARDED], self.flags())

    def test_child_ignoring_term_is_killed(self):
        self.policy.grace = 0.3
        self.script(dict(TRICKLE, ignore_term=True), FAST)
        self.assertTrue(self.fetch())
        self.assertEqual(2, len(self.calls()))
        self.assert_no_child_left()

    def test_interrupt_does_not_leave_wget_running(self):
        self.script(TRICKLE)
        with patch.object(guarded_download._Watch, 'verdict', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.fetch()
        self.assertEqual(1, len(self.calls()))
        self.assert_no_child_left()

    def test_step_that_worked_is_where_the_next_file_starts(self):
        self.script(TRICKLE, FAST)
        self.assertTrue(self.fetch())
        self.assertTrue(self.fetch())
        self.assertEqual([GUARDED, GUARDED_IPV4, GUARDED_IPV4], self.flags())
        # Another host has proven nothing yet.
        other = 'https://other.invalid/file'
        self.assertTrue(guarded_download.fetch(other, self.destination,
                                               self.messages.append, self.policy))
        self.assertEqual(GUARDED + ['-O', self.destination, '--', other],
                         self.calls()[-1]['argv'])

    def test_download_that_completes_while_being_stopped_counts(self):
        class Finishing(object):
            returncode = None

            def wait(self, timeout=None):
                if self.returncode is None:
                    raise subprocess.TimeoutExpired('wget', timeout)
                return self.returncode

            def poll(self):
                return self.returncode

            def terminate(self):
                self.returncode = 0

            kill = terminate

        with patch.object(guarded_download.subprocess, 'Popen', return_value=Finishing()) as popen:
            self.assertTrue(self.fetch())
        self.assertEqual(1, popen.call_count)


class WatchTests(unittest.TestCase):
    """Verdicts from synthetic (time, size) observations; no process involved."""

    def setUp(self):
        self.policy = guarded_download.Policy(floor=1000, window=60, first_byte=45, stall=300)

    def watch(self, guarded=True):
        return guarded_download._Watch(guarded, self.policy, 0)

    def test_no_data_is_reported_only_after_the_first_byte_allowance(self):
        watch = self.watch()
        self.assertIsNone(watch.verdict(44.9, 0))
        self.assertEqual('silent', watch.verdict(45, 0)[0])

    def test_rate_is_judged_only_over_a_full_window_from_the_first_byte(self):
        watch = self.watch()
        self.assertIsNone(watch.verdict(30, 1))
        for second in range(31, 90):
            self.assertIsNone(watch.verdict(second, 1), second)
        reason, rate = watch.verdict(90, 1)
        self.assertEqual('slow', reason)
        self.assertEqual(0, rate)

    def test_floor_is_a_strict_lower_bound(self):
        at_floor = self.watch()
        at_floor.verdict(0, 1)
        self.assertIsNone(at_floor.verdict(60, 1 + 60 * 1000))
        below = self.watch()
        below.verdict(0, 1)
        self.assertEqual(('slow', 999.0), below.verdict(60, 1 + 60 * 999))

    def test_trickle_after_a_fast_start_is_caught_once_the_burst_leaves_the_window(self):
        watch = self.watch()
        size = 0
        for second in range(0, 6):
            size += 300000
            self.assertIsNone(watch.verdict(second, size))
        verdicts = {}
        for second in range(6, 80):
            size += 10
            verdicts[second] = watch.verdict(second, size)
        self.assertIsNone(verdicts[60])
        first = min(second for second, verdict in verdicts.items() if verdict)
        self.assertEqual(65, first)
        self.assertEqual(('slow', 10.0), verdicts[first])

    def test_healthy_transfer_is_never_judged_slow(self):
        watch = self.watch()
        for second in range(0, 600):
            self.assertIsNone(watch.verdict(second, 1 + second * 1000))

    def test_unreadable_size_gives_no_verdict(self):
        watch = self.watch()
        watch.verdict(0, 1)
        self.assertIsNone(watch.verdict(500, None))

    def test_unhurried_attempt_only_stops_when_nothing_changes(self):
        watch = self.watch(guarded=False)
        self.assertIsNone(watch.verdict(299, 0))
        self.assertIsNone(watch.verdict(299.5, 1))
        self.assertIsNone(watch.verdict(599, 1))
        # wget may restart the file on an internal retry; that is activity.
        self.assertIsNone(watch.verdict(599.25, 0))
        self.assertIsNone(watch.verdict(899, 0))
        self.assertEqual('stalled', watch.verdict(899.25, 0)[0])


class AdapterTests(unittest.TestCase):
    """InstallCyberPanel.downloadCustomBinary on top of the guarded fetch."""

    def setUp(self):
        path = ROOT / 'install/installCyberPanel.py'
        self.source = path.read_text(encoding='utf-8')
        tree = ast.parse(self.source)
        cls = next(node for node in tree.body
                   if isinstance(node, ast.ClassDef) and node.name == 'InstallCyberPanel')
        cls.body = [node for node in cls.body
                    if isinstance(node, ast.FunctionDef) and node.name == 'downloadCustomBinary']
        self.method = ast.get_source_segment(self.source, cls.body[0]) \
            if hasattr(ast, 'get_source_segment') else ''
        tree.body = [cls]
        self.log = Mock()
        self.subprocess = Mock()
        namespace = dict(os=os, subprocess=self.subprocess,
                         logging=types.SimpleNamespace(InstallLog=self.log))
        exec(compile(tree, str(path), 'exec'), namespace)
        klass = namespace['InstallCyberPanel']
        self.messages = []
        klass.stdOut = staticmethod(lambda message, *arguments: self.messages.append(message))
        self.installer = klass()
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.destination = os.path.join(temporary.name, 'binary')
        self.url = 'https://example.invalid/binary'
        self.module = types.ModuleType('guarded_download')
        self.module.fetch = Mock()
        modules = patch.dict(sys.modules, {'guarded_download': self.module})
        modules.start()
        self.addCleanup(modules.stop)

    def fetched(self, size, result=True):
        """The guarded fetch left SIZE bytes behind and reported RESULT."""
        def effect(*arguments):
            with open(self.destination, 'wb') as target:
                target.write(b'a' * size)
            return result
        self.module.fetch.side_effect = effect

    def download(self):
        return self.installer.downloadCustomBinary(self.url, self.destination)

    def test_verified_exit_and_reasonable_size_are_both_required(self):
        self.fetched(20000)
        self.assertTrue(self.download())
        (url, destination, notify), _ = self.module.fetch.call_args
        self.assertEqual((self.url, self.destination), (url, destination))
        notify('progress note')
        self.assertIn('progress note', self.messages)
        self.subprocess.call.assert_not_called()

        self.fetched(10)
        self.assertFalse(self.download())

    def test_failed_fetch_is_not_rescued_by_a_large_partial(self):
        self.fetched(20000, result=False)
        self.assertFalse(self.download())
        self.assertFalse(any('Downloaded successfully' in message for message in self.messages))
        self.assertEqual(1, self.log.writeToFile.call_count)
        # installLog treats text after a comma as the progress percentage.
        self.assertNotIn(',', self.log.writeToFile.call_args[0][0])

    def test_defect_in_the_guard_falls_back_to_plain_wget_with_its_exit_checked(self):
        self.module.fetch.side_effect = RuntimeError('guard defect')
        for exit_code, expected in ((0, True), (4, False)):
            with self.subTest(exit_code=exit_code):
                def call(argv):
                    with open(self.destination, 'wb') as target:
                        target.write(b'a' * 20000)
                    return exit_code
                self.subprocess.call.side_effect = call
                self.assertEqual(expected, self.download())
                self.subprocess.call.assert_called_with(
                    ['wget', '-q', '--show-progress', '-O', self.destination, '--', self.url])

    def test_download_no_longer_goes_through_the_unchecked_command_runner(self):
        if not self.method:
            self.skipTest('needs ast.get_source_segment')
        self.assertNotIn('install_utils.call', self.method)


class CompatibilityTests(unittest.TestCase):
    def test_guard_parses_on_the_el8_system_interpreter(self):
        if sys.version_info < (3, 8):
            self.skipTest('this interpreter already proved it by importing the module')
        source = (ROOT / 'install/guarded_download.py').read_text(encoding='utf-8')
        ast.parse(source, feature_version=(3, 6))
        self.assertIsNone(re.search(r'\b(capture_output|text)\s*=', source))


if __name__ == '__main__':
    unittest.main()
