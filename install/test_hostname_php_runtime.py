"""Execute the real fresh installer's hostname block with isolated command spies."""
import os
import ast
import contextlib
import io
import json
from pathlib import Path
import re
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class HostnamePHPRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.calls = self.root / 'calls'
        source = Path(os.environ.get('HOSTNAME_TEST_SHELL', str(ROOT / 'cyberpanel.sh'))).read_text()
        self.top_level = source[source.rindex('\nPost_Install_Tweak'):].strip()
        marker = '# If valid hostname is set that resolves externally'
        self.block = source.split(marker, 1)[1].split('\n}', 1)[0]
        self.block = self.block.split('\n', 1)[1]
        helpers = []
        for name in ('CyberPanel_CLI_Succeeded', 'Setup_Hostname_SSL'):
            match = re.search(r'^' + name + r'\(\) \{\n.*?^\}', source, re.M | re.S)
            if match: helpers.append(match.group(0))
        self.helper = '\n'.join(helpers)

    def runtime(self, version, executable=True, binary='lsphp'):
        path = self.root / ('lsphp' + version.replace('.', '')) / 'bin' / binary
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('#!/bin/sh\nexit 0\n')
        path.chmod(0o755 if executable else 0o644)

    def status_output(self, success, message=None):
        tree = ast.parse((ROOT / 'cli/cyberPanel.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'cyberPanel')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'printStatus')
        scope = {'json': json}
        exec(compile(ast.fix_missing_locations(ast.Module(body=[method], type_ignores=[])), 'actual-cli-status', 'exec'), scope)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            scope['printStatus'](None, success, message if message is not None else ('None' if success else 'Website already exists'))
        return output.getvalue()

    def run_block(self, dns=True, existing=False, top_level=False, output=None, process_exit=0, tls_output=None, tls_exit=0):
        stubs = '''
hostname() { printf '%s\\n' 'qa.example.test'; }
dig() { if [ "$QA_DNS" = 1 ]; then printf '%s\\n' '192.0.2.1'; fi; }
log_info() { :; }
log_error() { printf '%s\\n' "$*" >&2; }
cyberpanel() {
  printf '%s\\n' "$*" >> "$QA_CALLS"
  if [ "$1" = createWebsite ]; then
    printf '%s\\n' "$QA_CREATE_OUTPUT"
    return "$QA_CREATE_EXIT"
  fi
  if [ "$1" = hostNameSSL ]; then
    printf '%s\\n' "$QA_TLS_OUTPUT"
    return "$QA_TLS_EXIT"
  fi
}
'''
        caller = self.top_level if top_level else 'Post_Install_Tweak'
        script = stubs + self.helper + '\nPost_Install_Tweak() {\n' + self.block + '\n}\nPost_Install_Display_Final_Info() { printf FINAL_SUCCESS; }\n' + caller
        result = subprocess.run(['bash'], input=script,
            text=True, capture_output=True, timeout=10,
            env=dict(os.environ, LSWS_ROOT=str(self.root), QA_CALLS=str(self.calls),
                     QA_DNS=str(int(dns)), QA_CREATE_EXIT=str(process_exit),
                     QA_CREATE_OUTPUT=self.status_output(0 if existing else 1) if output is None else output,
                     QA_TLS_OUTPUT=self.status_output(1) if tls_output is None else tls_output, QA_TLS_EXIT=str(tls_exit)))
        calls = [shlex.split(line) for line in self.calls.read_text().splitlines()] if self.calls.exists() else []
        return result, calls

    def selected(self, calls):
        create = next(call for call in calls if call[0] == 'createWebsite')
        return create[create.index('--php') + 1]

    def test_fresh_ubuntu_alma_with_only_php83_never_requests_missing_php74(self):
        self.runtime('8.3')
        result, calls = self.run_block()
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('8.3', self.selected(calls))
        self.assertEqual(['createWebsite', 'hostNameSSL'], [call[0] for call in calls])

    def test_non_executable_runtime_is_skipped(self):
        self.runtime('8.3', executable=False)
        self.runtime('8.2')
        _, calls = self.run_block()
        self.assertEqual('8.2', self.selected(calls))

    def test_php_cli_alone_cannot_back_an_lsapi_website(self):
        self.runtime('8.3', binary='php')
        result, calls = self.run_block()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], calls)

    def test_no_installed_runtime_creates_no_site_or_certificate(self):
        result, calls = self.run_block()
        self.assertNotEqual(0, result.returncode)
        self.assertEqual([], calls)

    def test_php83_is_preferred_for_new_hostname(self):
        self.runtime('8.0')
        self.runtime('8.3')
        _, calls = self.run_block()
        self.assertEqual('8.3', self.selected(calls))

    def test_legacy_installed_php74_remains_usable(self):
        self.runtime('7.4')
        _, calls = self.run_block()
        self.assertEqual('7.4', self.selected(calls))

    def test_unresolved_hostname_has_no_site_side_effects(self):
        self.runtime('8.3')
        _, calls = self.run_block(dns=False)
        self.assertEqual([], calls)

    def test_existing_site_json_failure_never_changes_php_or_runs_tls(self):
        self.runtime('8.3')
        result, calls = self.run_block(existing=True)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(['createWebsite'], [call[0] for call in calls])


    def test_real_top_level_stops_before_success_when_no_runtime_exists(self):
        result, calls = self.run_block(top_level=True)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('FINAL_SUCCESS', result.stdout)
        self.assertEqual([], calls)

    def test_real_top_level_stops_on_cli_json_failure_with_zero_exit(self):
        self.runtime('8.3')
        result, calls = self.run_block(existing=True, top_level=True)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('FINAL_SUCCESS', result.stdout)
        self.assertEqual(['createWebsite'], [call[0] for call in calls])

    def test_successful_cli_json_allows_real_top_level_completion(self):
        self.runtime('8.3')
        result, calls = self.run_block(top_level=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('FINAL_SUCCESS', result.stdout)
        self.assertEqual(['createWebsite', 'hostNameSSL'], [call[0] for call in calls])

    def test_progress_lines_do_not_hide_single_real_cli_success_status(self):
        self.runtime('8.3')
        result, calls = self.run_block(output='Creating website...\n' + self.status_output(1))
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(['createWebsite', 'hostNameSSL'], [call[0] for call in calls])

    def test_malformed_or_ambiguous_cli_status_does_not_issue_tls(self):
        self.runtime('8.3')
        for output in ('not JSON', self.status_output(0) + self.status_output(1)):
            with self.subTest(output=output):
                if self.calls.exists(): self.calls.unlink()
                result, calls = self.run_block(output=output)
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(['createWebsite'], [call[0] for call in calls])

    def test_create_process_failure_does_not_issue_tls(self):
        self.runtime('8.3')
        result, calls = self.run_block(process_exit=1)
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(['createWebsite'], [call[0] for call in calls])


    def test_hostname_ssl_json_failure_stops_real_top_level(self):
        self.runtime('8.3')
        result, calls = self.run_block(top_level=True, tls_output=self.status_output(0, 'TLS failed'))
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('FINAL_SUCCESS', result.stdout)
        self.assertIn('Hostname SSL', result.stderr)

    def test_hostname_ssl_legacy_success_one_with_error_is_not_success(self):
        self.runtime('8.3')
        result, calls = self.run_block(top_level=True, tls_output=self.status_output(1, 'Certificate request failed'))
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('FINAL_SUCCESS', result.stdout)
        self.assertIn('Hostname SSL', result.stderr)

    def test_hostname_ssl_process_failure_stops_real_top_level(self):
        self.runtime('8.3')
        result, calls = self.run_block(top_level=True, tls_exit=1)
        self.assertNotEqual(0, result.returncode)
        self.assertNotIn('FINAL_SUCCESS', result.stdout)
        self.assertIn('Hostname SSL', result.stderr)


if __name__ == '__main__':
    unittest.main()
