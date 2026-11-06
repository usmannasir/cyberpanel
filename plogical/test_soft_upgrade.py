"""Exercise the actual soft-upgrade launcher against a local Git ref and HTTP payload."""
import ast
import fcntl
import functools
import json
import os
import hashlib
import http.server
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch
from urllib.error import HTTPError

from plogical import softUpgrade


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class PanelUpgradeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        repo = self.root / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'v3.0.8', str(repo)], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.email=test@example.invalid',
                        '-c', 'user.name=test', 'commit', '--allow-empty', '-qm', 'fixture'], check=True)
        revision = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        self.release = self.root / 'http' / revision / 'plogical'
        self.release.mkdir(parents=True)
        self.receipt = self.root / 'receipt'
        helper = Path(__file__).with_name('olsSecurityAssets.py').read_bytes()
        (self.release / 'olsSecurityAssets.py').write_bytes(helper)
        self.expected = hashlib.sha256(helper).hexdigest()
        # The child runs out-of-process using the same staging mode as the
        # installed launcher. Use the actual upgrader's selected helper loader.
        source = Path(__file__).with_name('upgrade.py').read_text()
        loader = source[source.index('def load_ols_security_assets('):source.index('class OLSUpgradeFailure')]
        (self.release / 'upgrade.py').write_text(
            'import os, hashlib, sys\nfrom pathlib import Path\n' + loader +
            'class Upgrade: pass\nhelper=load_ols_security_assets()\n'
            'Path(%r).write_text(sys.argv[1] + " " + hashlib.sha256(Path(helper.__file__).read_bytes()).hexdigest())\n'
            % str(self.receipt))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0),
            functools.partial(QuietHandler, directory=str(self.root / 'http')))
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        patcher = patch.multiple(softUpgrade, STATUS_ROOT=self.root / 'status', REPOSITORY=str(repo),
                                 RAW='http://127.0.0.1:%d' % server.server_port)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_release_helpers_work_without_installed_helper(self):
        self.assertEqual(softUpgrade.run('v3.0.8'), 0)
        self.assertEqual(self.receipt.read_text(), 'SoftUpgrade,v3.0.8 ' + self.expected)

    def test_stages_watchdog_from_service_helpers_selected_revision(self):
        # This target declares its dependency in the controller, not in the entry script.
        source = self.release / 'upgrade.py'
        source.write_text(source.read_text() + "\ncontroller = 'olsServiceControl.py'\n")
        root = Path(__file__).resolve().parents[1]
        for name in ('plogical/olsServiceControl.py', 'plogical/olsWatchdog.py', 'CPScripts/watchdog.sh'):
            destination = self.release.parent / name
            destination.parent.mkdir(exist_ok=True)
            destination.write_bytes((root / name).read_bytes())
        revision = softUpgrade.resolve_release('v3.0.8')
        stage = self.root / 'stage'
        stage.mkdir()
        softUpgrade.stage_release(stage, revision)
        self.assertEqual((stage / 'olsWatchdog.py').read_bytes(), (root / 'plogical/olsWatchdog.py').read_bytes())
        self.assertEqual((stage / 'watchdog.sh').read_bytes(), (root / 'CPScripts/watchdog.sh').read_bytes())
        program = """import hashlib, importlib.util, sys
from pathlib import Path
stage = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location('isolated_service', str(stage / 'olsServiceControl.py'))
service = importlib.util.module_from_spec(spec)
spec.loader.exec_module(service)
assert Path(service.watchdog.__file__).parent == stage
assert hashlib.sha256((stage / 'watchdog.sh').read_bytes()).hexdigest() == service.watchdog.COOPERATIVE
"""
        result = subprocess.run([sys.executable, '-I', '-B', '-c', program, str(stage)],
                                cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(0, result.returncode, result.stderr.decode())
        (stage / 'olsWatchdog.py').unlink()
        missing = subprocess.run([sys.executable, '-I', '-B', '-c', program, str(stage)],
                                 cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertNotEqual(0, missing.returncode)
        self.assertIn(b'olsWatchdog.py', missing.stderr)
        (self.release / 'olsWatchdog.py').unlink()
        refused = self.root / 'refused-stage'
        refused.mkdir()
        with self.assertRaises(HTTPError) as failure:
            softUpgrade.stage_release(refused, revision)
        self.assertEqual(failure.exception.code, 404)

    def poll_job(self, job, admin=1, transport=True):
        path = Path(__file__).resolve().parents[1] / 'baseTemplate/views.py'
        view = next(node for node in ast.parse(path.read_text()).body
                    if isinstance(node, ast.FunctionDef) and node.name == 'upgradeStatus')
        process = Mock()
        def output(command, retRequired, shell):
            self.assertTrue(retRequired)
            self.assertFalse(shell)
            self.assertEqual(command.split()[:4], ['/usr/local/CyberPanel/bin/python', '-I',
                             '/usr/local/CyberCP/plogical/softUpgrade.py', '--status'])
            if not transport:
                return 0, ''
            return 1, json.dumps(softUpgrade.read_status(command.split()[4]))
        process.outputExecutioner.side_effect = output
        acl = Mock()
        acl.loadedACL.return_value = {'admin': admin}
        acl.loadErrorJson.return_value = {'access': 'denied'}
        namespace = dict(ProcessUtilities=process, json=json, HttpResponse=lambda data, status=200: dict(json.loads(data), http_status=status),
                         ACLManager=acl, os=os)
        exec(compile(ast.Module(body=[view], type_ignores=[]), str(path), 'exec'), namespace)
        request = SimpleNamespace(method='POST', session={'userID': 4, 'softUpgradeRun': job, 'softUpgradeStarted': 0})
        return namespace['upgradeStatus'](request)

    def test_status_transport_failure_is_retryable_even_for_an_old_running_job(self):
        job = 'a' * 32
        softUpgrade.record_status(job, 'running')
        self.assertEqual(self.poll_job(job, transport=False)['http_status'], 503)
        self.assertEqual(self.poll_job(job)['upgradeStatus'], 1)
        self.assertEqual(self.poll_job(job)['finished'], 0)

    def test_poll_refuses_nonadmin_and_invalid_run_identifiers(self):
        self.assertEqual(self.poll_job('x', admin=0), {'access': 'denied'})
        response = self.poll_job('../../secret')
        self.assertEqual(response['upgradeStatus'], 0)
        self.assertIn('Invalid upgrade run identifier', response['error_message'])

    def test_poll_detects_launcher_death_or_pid_reuse(self):
        job = '4' * 32
        softUpgrade.record_status(job, 'running')
        path = softUpgrade.status_path(job)
        status = json.loads(path.read_text())
        status['start_ticks'] = 'changed'
        path.write_text(json.dumps(status))
        result = self.poll_job(job)
        self.assertEqual((result['finished'], result['upgradeStatus']), (1, 0))
        self.assertIn('before reporting completion', result['error_message'])

    def test_panel_worker_and_poll_report_completed_release(self):
        job = '1' * 32
        with patch.object(softUpgrade, 'activate_panel_runtime', return_value={'fresh': True}) as activation:
            self.assertEqual(softUpgrade.run_panel_job('v3.0.8', job), 0)
        activation.assert_called_once()
        self.assertEqual(softUpgrade.read_status(job)['activation'], {'fresh': True})
        self.assertEqual(self.receipt.read_text(), 'SoftUpgrade,v3.0.8 ' + self.expected)
        self.assertEqual(softUpgrade.status_path(job).stat().st_mode & 0o777, 0o600)
        response = self.poll_job(job)
        self.assertEqual((response['finished'], response['upgradeStatus']), (1, 1))

    def test_panel_worker_and_poll_report_failed_staging(self):
        job = '2' * 32
        (self.release / 'olsSecurityAssets.py').unlink()
        with patch.object(sys, 'stderr'):
            self.assertNotEqual(softUpgrade.run_panel_job('v3.0.8', job), 0)
        response = self.poll_job(job)
        self.assertEqual((response['finished'], response['upgradeStatus']), (1, 0))
        self.assertIn('404', response['error_message'])
        self.assertFalse(self.receipt.exists())

    def test_surviving_upgrade_child_keeps_the_lock_after_its_launcher_exits(self):
        started = self.root / 'child-started'
        release = self.root / 'let-child-exit'
        finished = self.root / 'child-finished'
        duplicate = self.root / 'duplicate'
        (self.release / 'upgrade.py').write_text("""import os, time
from pathlib import Path
class Upgrade: pass
started, release, finished, duplicate = map(Path, %r)
if started.exists():
    duplicate.touch()
    raise SystemExit(0)
started.write_text(str(os.getpid()))
deadline = time.monotonic() + 15
while not release.exists() and time.monotonic() < deadline:
    time.sleep(.02)
finished.touch()
""" % ([str(path) for path in (started, release, finished, duplicate)],))
        # Only this disposable launcher exits abruptly. Its own staged child
        # remains alive and bounded by a deadline even if the test fails.
        launcher = """import os, sys, threading, time
from pathlib import Path
sys.path.insert(0, %r)
from plogical import softUpgrade as app
app.STATUS_ROOT, app.REPOSITORY, app.RAW = Path(%r), %r, %r
def disappear_after_start():
    while not Path(%r).exists():
        time.sleep(.01)
    os._exit(73)
threading.Thread(target=disappear_after_start, daemon=True).start()
sys.exit(app.run_panel_job('v3.0.8', 'a' * 32))
""" % (str(Path(__file__).resolve().parents[1]), str(softUpgrade.STATUS_ROOT),
       softUpgrade.REPOSITORY, softUpgrade.RAW, str(started))
        try:
            result = subprocess.run([sys.executable, '-B', '-c', launcher], cwd=self.root,
                                    env=dict(os.environ, TMPDIR=str(self.root)),
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            self.assertEqual(result.returncode, 73)
            child_stat = Path('/proc/%s/stat' % started.read_text()).read_text()
            self.assertIsNotNone(softUpgrade.live_start_ticks(child_stat))
            with patch.object(sys, 'stderr'):
                self.assertNotEqual(softUpgrade.run_panel_job('v3.0.8', 'b' * 32), 0)
            self.assertIn('Another panel upgrade', softUpgrade.read_status('b' * 32)['message'])
            self.assertFalse(duplicate.exists())
        finally:
            release.touch()
            deadline = time.monotonic() + 5
            while started.exists() and not finished.exists() and time.monotonic() < deadline:
                time.sleep(.02)
        self.assertTrue(finished.exists())
        with (softUpgrade.STATUS_ROOT / '.lock').open('a') as lock:
            deadline = time.monotonic() + 3
            while True:
                try:
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    break
                except BlockingIOError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(.02)

    def test_panel_worker_forwards_actual_upgrade_failure(self):
        job = '3' * 32
        with (self.release / 'upgrade.py').open('a') as child:
            child.write("print('unrecognized native OLS error', file=sys.stderr)\nraise SystemExit(78)\n")
        with patch.object(sys, 'stderr'):
            self.assertNotEqual(softUpgrade.run_panel_job('v3.0.8', job), 0)
        response = self.poll_job(job)
        self.assertEqual((response['finished'], response['upgradeStatus']), (1, 0))
        self.assertIn('unrecognized native OLS error', response['error_message'])

    def test_missing_release_helper_prevents_execution(self):
        (self.release / 'olsSecurityAssets.py').unlink()
        with self.assertRaises(OSError):
            softUpgrade.run('v3.0.8')
        self.assertFalse(self.receipt.exists())

    def test_rejects_ref_path_or_option_injection_before_fetch(self):
        for branch in ('../../master', '--upload-pack=evil', 'v3.0.8;cmd'):
            with self.subTest(branch=branch), self.assertRaises(ValueError):
                softUpgrade.run(branch)
        self.assertFalse(self.receipt.exists())
