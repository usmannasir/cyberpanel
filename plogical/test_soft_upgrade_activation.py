"""Check durable GUI job activation and the independent worker boundary."""
import fcntl
import hashlib
import http.server
import json
import os
from pathlib import Path
import subprocess
import ssl
import sys
import tempfile
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from plogical import softUpgrade as app


class ActivationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        patcher = patch.object(app, 'STATUS_ROOT', self.root / 'status')
        patcher.start()
        self.addCleanup(patcher.stop)
        self.job = 'a' * 32

    def test_legacy_two_argument_launcher_selects_independent_scope(self):
        def run(argv, **kwargs):
            self.assertEqual(argv[:3], [app.SYSTEMD_RUN, '--scope', '--quiet'])
            self.assertIn('--unit=cyberpanel-soft-upgrade-' + self.job, argv)
            self.assertEqual(argv[-3:], ['--worker', 'v3.0.8', self.job])
            self.assertTrue(kwargs['start_new_session'])
            self.assertEqual(kwargs['stdin'], subprocess.DEVNULL)
            self.assertEqual(kwargs['stdout'], subprocess.DEVNULL)
            self.assertEqual(app.read_status(self.job)['state'], 'starting')
            app.record_status(self.job, 'complete', activation={'checked': True})
            return SimpleNamespace(returncode=0, stderr='')
        with patch.object(app.subprocess, 'run', side_effect=run):
            self.assertEqual(app.launch_panel_job('v3.0.8', self.job), 0)
        self.assertEqual(app.read_status(self.job)['activation'], {'checked': True})

    def test_invalid_job_or_branch_never_launches_a_scope(self):
        with patch.object(app.subprocess, 'run') as run:
            for branch, job in [('v3.0.8;id', self.job), ('v3.0.8', '../escape')]:
                with self.assertRaises(ValueError):
                    app.launch_panel_job(branch, job)
            run.assert_not_called()

    def test_failed_scope_admission_is_terminal_failure(self):
        with patch.object(app.subprocess, 'run', side_effect=OSError('systemd unavailable')):
            self.assertEqual(app.launch_panel_job('v3.0.8', self.job), 1)
        self.assertEqual(app.read_status(self.job)['state'], 'failed')
        self.assertIn('independent upgrade worker', app.read_status(self.job)['message'])

    def test_scope_exit_without_worker_result_cannot_report_complete(self):
        with patch.object(app.subprocess, 'run', return_value=SimpleNamespace(returncode=1)):
            self.assertEqual(app.launch_panel_job('v3.0.8', self.job), 1)
        self.assertEqual(app.read_status(self.job)['state'], 'failed')

    def test_upgrade_failure_does_not_restart_panel(self):
        with patch.object(app, 'run', side_effect=RuntimeError('native refused')), \
                patch.object(app, 'activate_panel_runtime') as activation, patch.object(app.sys, 'stderr'):
            self.assertEqual(app.run_panel_job('v3.0.8', self.job), 1)
        activation.assert_not_called()
        self.assertEqual(app.read_status(self.job)['state'], 'failed')

    def test_activation_failure_is_terminal_failure_after_successful_upgrade(self):
        with patch.object(app, 'run', return_value=0), \
                patch.object(app, 'activate_panel_runtime', side_effect=RuntimeError('panel still stale')), \
                patch.object(app.sys, 'stderr'):
            self.assertEqual(app.run_panel_job('v3.0.8', self.job), 1)
        self.assertEqual(app.read_status(self.job)['state'], 'failed')
        self.assertIn('panel still stale', app.read_status(self.job)['message'])

    def test_lock_and_running_status_remain_owned_during_activation(self):
        def activate(fd):
            self.assertEqual(app.read_status(self.job)['state'], 'running')
            with (app.STATUS_ROOT / '.lock').open('a') as lock:
                with self.assertRaises(BlockingIOError):
                    fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            os.fstat(fd)
            return {'fresh': True}
        with patch.object(app, 'run', return_value=0), \
                patch.object(app, 'activate_panel_runtime', side_effect=activate):
            self.assertEqual(app.run_panel_job('v3.0.8', self.job), 0)
        self.assertEqual(app.read_status(self.job)['activation'], {'fresh': True})

    def test_activation_requires_retirement_new_master_and_fresh_worker(self):
        old = {'pid': 10, 'start_ticks': '1'}
        old_worker = {'pid': 11, 'start_ticks': '2', 'ppid': 10}
        new = {'pid': 20, 'start_ticks': '3'}
        worker = {'pid': 21, 'start_ticks': '4', 'ppid': 20}
        before = {'active': True, 'master': old, 'workers': [old_worker]}
        after = {'active': True, 'master': new, 'workers': [worker]}
        with patch.object(app, 'panel_state', side_effect=[before, after, after]), \
                patch.object(app, 'process_identity', return_value=None), \
                patch.object(app, 'probe_panel', return_value={'http_status': 200}), \
                patch.object(app, 'worker_belongs_to_master', return_value=True), \
                patch.object(app.subprocess, 'run') as run:
            result = app.activate_panel_runtime(7)
        self.assertEqual(result['master'], new)
        self.assertTrue(result['previous_runtime_retired'])
        self.assertEqual(run.call_args[1]['pass_fds'], (7,))

    def test_old_worker_survival_and_wrong_worker_ancestry_fail_closed(self):
        before = {'active': True, 'master': {'pid': 10, 'start_ticks': '1'}, 'workers': []}
        after = {'active': True, 'master': {'pid': 20, 'start_ticks': '3'},
                 'workers': [{'pid': 21, 'start_ticks': '4', 'ppid': 1}]}
        for identity, belongs in [(before['master'], True), (None, False)]:
            with self.subTest(identity=identity), patch.object(app, 'panel_state', side_effect=[before, after, after]), \
                    patch.object(app, 'process_identity', return_value=identity), \
                    patch.object(app, 'probe_panel', return_value={'http_status': 200}), \
                    patch.object(app, 'worker_belongs_to_master', return_value=belongs), \
                    patch.object(app.subprocess, 'run'), \
                    patch.object(app.time, 'monotonic', side_effect=[0, 0, 2]), \
                    patch.object(app.time, 'sleep'):
                with self.assertRaisesRegex(RuntimeError, 'activation failed'):
                    app.activate_panel_runtime(7, timeout=1)

    def test_restart_failure_cannot_be_swallowed(self):
        with patch.object(app, 'panel_state', return_value={'master': None, 'workers': []}), \
                patch.object(app.subprocess, 'run', side_effect=subprocess.CalledProcessError(1, 'systemctl')):
            with self.assertRaises(subprocess.CalledProcessError):
                app.activate_panel_runtime(7)

    def test_default_and_custom_panel_ports_are_respected(self):
        path = self.root / 'bind.conf'
        for binding, expected in [('', ('127.0.0.1', 8090)), ('*:8443', ('127.0.0.1', 8443)),
                                  ('[::]:9443', ('::1', 9443))]:
            path.write_text(binding)
            self.assertEqual(app.panel_endpoint(self.root), expected)
        for binding in ['*:0', '*:99999', 'https://evil:8090', '*:8090\n*:8443']:
            path.write_text(binding)
            with self.assertRaises(RuntimeError):
                app.panel_endpoint(self.root)

    def test_scope_must_be_outside_the_panel_control_group(self):
        expected = '/cyberpanel-soft-upgrade-' + self.job + '.scope'
        for value, accepted in [('0::/system.slice' + expected, True),
                                ('0::/system.slice/lscpd.service', False),
                                ('0::/system.slice/lscpd.service' + expected, False)]:
            with self.subTest(value=value), patch.object(app, 'Path') as path:
                path.return_value.read_text.return_value = value
                if accepted:
                    app.require_job_scope(self.job)
                else:
                    with self.assertRaises(RuntimeError):
                        app.require_job_scope(self.job)

    def test_worker_stdout_stderr_and_stdin_are_independent_of_parent_pipes(self):
        script = ('import sys\nfrom pathlib import Path\n'
                  'sys.path.insert(0, %r)\nfrom plogical import softUpgrade as app\n'
                  'app.STATUS_ROOT=Path(%r)\napp.worker_io(%r)\n'
                  'assert sys.stdin.read()==""\nprint("worker-output")\n'
                  'print("worker-error",file=sys.stderr)\n') % (
                      str(Path(__file__).resolve().parents[1]), str(app.STATUS_ROOT), self.job)
        result = subprocess.run([sys.executable, '-I', '-c', script],
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((result.stdout, result.stderr), (b'', b''))
        log = Path(str(app.status_path(self.job)) + '.launcher.log')
        self.assertEqual(log.stat().st_mode & 0o777, 0o600)
        self.assertIn('worker-output', log.read_text())
        self.assertIn('worker-error', log.read_text())

    def test_real_tls_readiness_accepts_exact_installed_pin_and_refuses_another(self):
        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b'<html>panel login</html>')
            def log_message(self, *unused):
                pass
        key = self.root / 'key.pem'
        cert = self.root / 'cert.pem'
        other = self.root / 'other.pem'
        for destination in (cert, other):
            subprocess.run(['openssl', 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
                            '-days', '1', '-subj', '/CN=localhost', '-keyout', str(key),
                            '-out', str(destination)], check=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if destination == cert:
                server_key = self.root / 'server-key.pem'
                server_key.write_bytes(key.read_bytes())
        server = http.server.HTTPServer(('127.0.0.1', 0), Handler)
        context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        context.load_cert_chain(str(cert), str(server_key))
        server.socket = context.wrap_socket(server.socket, server_side=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        self.addCleanup(server.server_close)
        self.addCleanup(server.shutdown)
        (self.root / 'bind.conf').write_text('*:' + str(server.server_port))
        result = app.probe_panel(self.root)
        self.assertEqual(result['http_status'], 200)
        self.assertEqual(result['certificate_sha256'], hashlib.sha256(
            ssl.PEM_cert_to_DER_cert(cert.read_text())).hexdigest())
        cert.write_bytes(other.read_bytes())
        with self.assertRaisesRegex(RuntimeError, 'certificate does not match'):
            app.probe_panel(self.root)


if __name__ == '__main__':
    unittest.main()
