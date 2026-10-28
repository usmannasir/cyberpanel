"""Opt-in native acceptance for the staged OLS helper and release archive.

Set CP_OLS_INTEGRATION_ARCHIVE to the checksum-pinned release archive. All
replacement and rollback operations run inside temporary directories.
"""
import ast
import hashlib
import os
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

import test_upgrade_staged_helpers as staging_helpers


@unittest.skipUnless(os.environ.get('CP_OLS_INTEGRATION_ARCHIVE'),
                     'requires the pinned native OLS security release archive')
class StagedAssetsNativeTests(unittest.TestCase):
    def setUp(self):
        # Reuse the real shell staging harness and its local release HTTP server.
        self.staging = staging_helpers.StagedUpgradeHelperTests(
            'test_invalid_selector_download_stops_staging')
        self.staging.setUp()
        self.addCleanup(self.staging.doCleanups)
        result = self.staging.stage_sources()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        stage = self.staging.stage
        tree = ast.parse((stage / 'upgrade.py').read_text())
        loader = next(n for n in tree.body if isinstance(n, ast.FunctionDef)
                      and n.name == 'load_ols_security_assets')
        namespace = {'os': os, '__file__': str(stage / 'upgrade.py')}
        exec(compile(ast.Module(body=[loader], type_ignores=[]),
                     str(stage / 'upgrade.py'), 'exec'), namespace)
        legacy = types.ModuleType('plogical.olsSecurityAssets')
        legacy.SecurityAssetsTransaction = lambda *a, **kw: self.fail('used installed helper')
        with patch.dict(sys.modules, {'plogical.olsSecurityAssets': legacy}):
            self.module = namespace['load_ols_security_assets']()
        self.assertEqual(Path(self.module.__file__), stage / 'olsSecurityAssets.py')
        self.archive = Path(os.environ['CP_OLS_INTEGRATION_ARCHIVE'])
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).hexdigest(),
                         self.module.SECURITY_ASSETS_SHA256)
        self.root = self.staging.root / 'lsws'
        for folder in ('conf', 'admin/conf', 'admin/fcgi-bin', 'admin/html', 'lsphp83/bin'):
            (self.root / folder).mkdir(parents=True, exist_ok=True)
        self.config = self.root / 'conf/httpd_config.conf'
        self.config.write_text('serverName staged-native-qa\ndisableWebAdmin 0\n')
        self.auth = self.root / 'admin/conf/htpasswd'
        self.auth.write_text('admin:preserve-existing-hash\n')
        self.website = self.root / 'lsphp83/bin/lsphp'
        self.website.write_bytes(b'website PHP must stay unchanged')
        self.runtime = self.root / 'admin/fcgi-bin/admin_php'
        self.runtime.symlink_to('../../lsphp83/bin/lsphp')
        self.html = self.root / 'admin/html/index.php'
        self.html.write_text('<?php echo "old webadmin"; ?>')
        self.before = {p: p.read_bytes() for p in
                       (self.config, self.auth, self.website, self.html)}
        self.before_paths = {str(p.relative_to(self.root)) for p in self.root.rglob('*')
                             if p.is_file() or p.is_symlink()}

    def apply_release(self):
        tx = self.module.SecurityAssetsTransaction(
            str(self.archive), self.module.SECURITY_ASSETS_SHA256, str(self.root))
        staged = tx.verify(staged=True)
        self.assertEqual(staged['version'], '8.3.36')
        tx.apply()
        applied = tx.verify()
        self.assertEqual(applied['version'], '8.3.36')
        self.assertFalse(self.runtime.is_symlink())
        self.assertTrue((self.root / 'admin/conf/enable_webadmin').is_file())
        for p in (self.config, self.auth, self.website):
            self.assertEqual(p.read_bytes(), self.before[p])
        self.assertNotEqual(self.html.read_bytes(), self.before[self.html])
        return tx

    def assert_restored(self):
        self.assertTrue(self.runtime.is_symlink())
        self.assertEqual(os.readlink(self.runtime), '../../lsphp83/bin/lsphp')
        for p, data in self.before.items():
            self.assertEqual(p.read_bytes(), data)
        self.assertFalse((self.root / 'admin/conf/enable_webadmin').exists())
        after_paths = {str(p.relative_to(self.root)) for p in self.root.rglob('*')
                       if (p.is_file() or p.is_symlink()) and
                       not p.relative_to(self.root).parts[0].startswith(
                           '.cyberpanel-security-backup-')}
        self.assertEqual(after_paths, self.before_paths)

    def test_staged_release_native_apply_and_rollback(self):
        tx = self.apply_release()
        tx.rollback()
        self.assert_restored()

    def test_staged_release_native_persisted_rollback(self):
        tx = self.apply_release()
        self.assertTrue(self.module.restore_security_assets(tx.backup_dir, str(self.root)))
        self.assert_restored()


if __name__ == '__main__':
    unittest.main()
