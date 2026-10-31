"""Exercise the real shell staging block against an older installed tree."""
import functools
import http.server
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


class StagedUpgradeHelperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='cp-staging-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / 'stage'
        self.stage.mkdir()
        self.release = self.root / 'http/v3.0.8'
        for name in ('plogical/upgrade.py', 'cyberpanel_version.py',
                     'cyberpanel_firewall_migration.py', 'lscpd_binary.py',
                     'plogical/olsSecurityAssets.py', 'plogical/olsParserRecovery.py'):
            target = self.release / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / name, target)
        self.server = http.server.ThreadingHTTPServer(
            ('127.0.0.1', 0),
            functools.partial(QuietHandler, directory=str(self.root / 'http')),
        )
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(self.server.server_close)
        self.addCleanup(self.server.shutdown)

    def stage_sources(self):
        source = (ROOT / 'cyberpanel_upgrade.sh').read_text()
        start = source.index('Download_Upgrade_Source() {')
        end = source.index('\nif [[ "$Server_Country"', start)
        block = source[start:end].replace(
            '/var/log/cyberpanel_upgrade_debug.log', str(self.root / 'debug.log'))
        env = dict(os.environ, Git_Content_URL='http://127.0.0.1:%s' % self.server.server_port,
                   Branch_Name='v3.0.8')
        # macOS developer hosts may not have wget; Linux QA uses its native wget.
        if not shutil.which('wget'):
            tools = self.root / 'tools'
            tools.mkdir(exist_ok=True)
            wget = tools / 'wget'
            wget.write_text('#!' + sys.executable + '\n'
                            'import sys, urllib.request\n'
                            'try:\n'
                            ' urllib.request.urlretrieve(sys.argv[-1], sys.argv[3])\n'
                            'except Exception:\n'
                            ' sys.exit(1)\n')
            wget.chmod(0o700)
            env['PATH'] = str(tools) + os.pathsep + env['PATH']
        return subprocess.run(['bash', '-c', 'sleep() { :; }\n' + block],
                              cwd=self.stage, env=env, capture_output=True, text=True)

    def test_staged_upgrader_imports_without_new_helper_in_installed_tree(self):
        result = self.stage_sources()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Stop before database recovery or any Upgrade methods. Execute the actual
        # startup imports, with an empty tree representing a pre-helper install.
        prefix = (self.stage / 'upgrade.py').read_text().split(
            'from contextlib import contextmanager', 1)[0]
        legacy = self.root / 'legacy-install'
        legacy.mkdir()
        prefix = prefix.replace("'/usr/local/CyberCP'", repr(str(legacy)))
        # The import-only fixture needs no MySQL connection or client library.
        runner = ('import sys, types; sys.path.insert(0, %r); '
                  'sys.modules["MySQLdb"] = types.ModuleType("MySQLdb"); '
                  'ns={"__name__":"staged_import_probe"}; '
                  'exec(compile(%r,"upgrade.py","exec"),ns); '
                  'print(ns["select_lscpd_binary"]("x86_64",(2,39)))'
                  % (str(self.stage), prefix))
        probe = subprocess.run([sys.executable, '-I', '-c', runner],
                               cwd=self.root, capture_output=True, text=True)
        self.assertEqual(probe.returncode, 0, probe.stdout + probe.stderr)
        self.assertEqual(probe.stdout.strip(), 'lscpd.0.4.0')

    def test_parser_diagnostic_helper_is_from_selected_release(self):
        result = self.stage_sources()
        self.assertEqual(0, result.returncode, result.stdout + result.stderr)
        self.assertEqual((self.stage / 'olsParserRecovery.py').read_bytes(),
                         (self.release / 'plogical/olsParserRecovery.py').read_bytes())

    def test_missing_parser_diagnostic_helper_stops_staging(self):
        (self.release / 'plogical/olsParserRecovery.py').unlink()
        result = self.stage_sources()
        self.assertNotEqual(0, result.returncode)
        self.assertIn('Failed to download olsParserRecovery.py', result.stdout)

    def test_missing_required_selector_stops_staging(self):
        (self.release / 'lscpd_binary.py').unlink()
        result = self.stage_sources()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Failed to download lscpd_binary.py', result.stdout)

    def test_security_helper_uses_selected_release_with_old_installed_package(self):
        result = self.stage_sources()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual((self.stage / 'olsSecurityAssets.py').read_bytes(),
                         (self.release / 'plogical/olsSecurityAssets.py').read_bytes())
        legacy = self.root / 'legacy-install/plogical'
        legacy.mkdir(parents=True)
        (legacy / '__init__.py').write_text('')
        # This old package must remain available; staging must not shadow it.
        (legacy / 'old_helper.py').write_text('value = "preserved"\n')
        (legacy / 'olsSecurityAssets.py').write_text('release = "old installed helper"\n')
        runner = '''import ast, os, sys
from pathlib import Path
sys.path.insert(0, %r)
import plogical.old_helper
import plogical.olsSecurityAssets
ns = {'os': os, '__file__': %r}
tree = ast.parse(Path(%r).read_text())
loader = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'load_ols_security_assets')
exec(compile(ast.Module(body=[loader], type_ignores=[]), 'upgrade.py', 'exec'), ns)
helper = ns['load_ols_security_assets']()
assert helper.__file__ == %r
assert callable(helper.SecurityAssetsTransaction)
assert plogical.old_helper.value == 'preserved'
assert plogical.olsSecurityAssets.release == 'old installed helper'
print('release helper loaded')
''' % (str(legacy.parent), str(self.stage / 'upgrade.py'),
       str(self.stage / 'upgrade.py'), str(self.stage / 'olsSecurityAssets.py'))
        probe = subprocess.run([sys.executable, '-I', '-c', runner],
                               cwd=self.root, capture_output=True, text=True)
        self.assertEqual(probe.returncode, 0, probe.stdout + probe.stderr)
        self.assertIn('release helper loaded', probe.stdout)

    def test_missing_security_helper_stops_staging_and_removes_stale_copy(self):
        (self.release / 'plogical/olsSecurityAssets.py').unlink()
        (self.stage / 'olsSecurityAssets.py').write_text('class SecurityAssetsTransaction: pass\n')
        result = self.stage_sources()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Failed to download olsSecurityAssets.py', result.stdout)
        self.assertNotIn('class SecurityAssetsTransaction',
                         (self.stage / 'olsSecurityAssets.py').read_text())

    def test_invalid_security_helper_stops_staging(self):
        (self.release / 'plogical/olsSecurityAssets.py').write_text('rate limit response\n')
        result = self.stage_sources()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Failed to download olsSecurityAssets.py', result.stdout)

    def test_older_upgrader_does_not_require_security_helper(self):
        source = self.release / 'plogical/upgrade.py'
        source.write_text(source.read_text().replace(
            'def load_ols_security_assets(', 'def older_unused_loader('))
        (self.release / 'plogical/olsSecurityAssets.py').unlink()
        result = self.stage_sources()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.stage / 'olsSecurityAssets.py').exists())

    def test_invalid_selector_download_stops_staging(self):
        (self.release / 'lscpd_binary.py').write_text('rate limit response\n')
        result = self.stage_sources()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Failed to download lscpd_binary.py', result.stdout)

    def test_older_upgrader_without_selector_does_not_require_it(self):
        source = self.release / 'plogical/upgrade.py'
        source.write_text(source.read_text().replace(
            'from lscpd_binary import select_lscpd_binary\n', ''))
        (self.release / 'lscpd_binary.py').unlink()
        result = self.stage_sources()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.stage / 'lscpd_binary.py').exists())


if __name__ == '__main__':
    unittest.main()
