import hashlib
import io
import json
import os
from pathlib import Path
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from plogical.olsSecurityAssets import SecurityAssetsTransaction, _allowed, restore_security_assets


class SecurityAssetsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'lsws'
        self.root.mkdir()
        (self.root / 'admin/fcgi-bin').mkdir(parents=True)
        (self.root / 'conf').mkdir()
        (self.root / 'conf/httpd_config.conf').write_text('serverName test\ndisableWebAdmin 0\n')
        (self.root / 'admin/conf').mkdir()
        (self.root / 'admin/conf/htpasswd').write_text('admin:unchanged-hash\n')
        (self.root / 'lsphp83/bin').mkdir(parents=True)
        self.website = self.root / 'lsphp83/bin/lsphp'
        self.website.write_bytes(b'website-runtime')
        self.runtime = self.root / 'admin/fcgi-bin/admin_php'
        self.runtime.symlink_to('../../lsphp83/bin/lsphp')
        self.files = {
            'admin/fcgi-bin/admin_php': b'fixed-standalone-runtime',
            'admin/cyberpanel-php/etc/php.ini': b'session.upload_progress.enabled=0\n',
            'admin/html/index.php': b'<?php echo "fixed"; ?>',
            'add-ons/webcachemgr/VERSION': b'new-optional-version',
        }

    def archive(self, extra=None, mutate=None):
        manifest = {'release': '2.5.7', 'files': []}
        for name, data in self.files.items():
            manifest['files'].append({'path': name, 'mode': 0o755 if name.endswith('admin_php') else 0o644,
                'sha256': hashlib.sha256(data).hexdigest(), 'existing_only': name.startswith('add-ons/')})
        if mutate:
            mutate(manifest)
        target = Path(self.temp.name) / 'assets.tar.gz'
        with tarfile.open(target, 'w:gz') as archive:
            entries = {'manifest.json': json.dumps(manifest).encode()}
            entries.update({'payload/' + k: v for k, v in self.files.items()})
            entries.update(extra or {})
            for name, data in entries.items():
                info = tarfile.TarInfo(name)
                info.size = len(data)
                archive.addfile(info, io.BytesIO(data))
        return str(target), hashlib.sha256(target.read_bytes()).hexdigest()

    def prepare(self, fresh=False):
        archive, digest = self.archive()
        with patch.object(SecurityAssetsTransaction, 'verify', return_value={}):
            return SecurityAssetsTransaction(archive, digest, str(self.root), fresh_install=fresh)

    def test_apply_and_rollback_preserve_symlink_website_auth_and_config(self):
        tx = self.prepare()
        with patch.object(tx, 'verify', return_value={}):
            tx.apply()
        self.assertFalse(self.runtime.is_symlink())
        self.assertTrue((self.root / 'admin/conf/enable_webadmin').exists())
        self.assertEqual(self.runtime.read_bytes(), b'fixed-standalone-runtime')
        self.assertEqual(self.website.read_bytes(), b'website-runtime')
        self.assertFalse((self.root / 'add-ons').exists())
        self.assertIn('disableWebAdmin 0', (self.root / 'conf/httpd_config.conf').read_text())
        self.assertEqual((self.root / 'admin/conf/htpasswd').read_text(), 'admin:unchanged-hash\n')
        tx.rollback()
        self.assertTrue(self.runtime.is_symlink())
        self.assertEqual(os.readlink(self.runtime), '../../lsphp83/bin/lsphp')
        self.assertFalse((self.root / 'admin/cyberpanel-php').exists())
        self.assertFalse((self.root / 'admin/html').exists())

    def test_installed_optional_component_receives_new_source_files(self):
        component = self.root / 'add-ons/webcachemgr'
        component.mkdir(parents=True)
        tx = self.prepare()
        with patch.object(tx, 'verify', return_value={}):
            tx.apply()
        self.assertEqual((component / 'VERSION').read_bytes(), b'new-optional-version')
        tx.rollback()
        self.assertFalse((component / 'VERSION').exists())
        self.assertTrue(component.is_dir())

    def test_fresh_install_disables_webadmin_and_rollback_restores_bytes(self):
        config = self.root / 'conf/httpd_config.conf'
        previous = config.read_bytes()
        tx = self.prepare(fresh=True)
        with patch.object(tx, 'verify', return_value={}):
            tx.apply()
        self.assertIn('disableWebAdmin 1', config.read_text())
        self.assertFalse((self.root / 'admin/conf/enable_webadmin').exists())
        tx.rollback()
        self.assertEqual(config.read_bytes(), previous)

    def test_failed_post_apply_probe_rolls_back(self):
        tx = self.prepare()
        with patch.object(tx, 'verify', side_effect=RuntimeError('runtime failed')):
            with self.assertRaisesRegex(RuntimeError, 'runtime failed'):
                tx.apply()
        self.assertTrue(self.runtime.is_symlink())
        self.assertEqual(self.website.read_bytes(), b'website-runtime')
        self.assertFalse((self.root / 'admin/html').exists())

    def test_html_open_symlink_supported_and_restored(self):
        (self.root / 'admin/html.open').mkdir()
        (self.root / 'admin/html.open/index.php').write_bytes(b'old')
        (self.root / 'admin/html').symlink_to('html.open')
        tx = self.prepare()
        with patch.object(tx, 'verify', return_value={}):
            tx.apply()
        self.assertTrue((self.root / 'admin/html').is_symlink())
        tx.rollback()
        self.assertEqual((self.root / 'admin/html.open/index.php').read_bytes(), b'old')

    def test_unrecognized_html_link_rejected_before_mutation(self):
        (self.root / 'admin/html').symlink_to('/tmp')
        with self.assertRaisesRegex(RuntimeError, 'document-root link'):
            self.prepare()
        self.assertTrue(self.runtime.is_symlink())

    def test_linked_parent_rejected(self):
        (self.root / 'admin/cyberpanel-php').symlink_to('/tmp')
        with self.assertRaisesRegex(RuntimeError, 'Unsafe OLS asset parent'):
            self.prepare()

    def test_checksum_mismatch_rejected(self):
        archive, _ = self.archive()
        with self.assertRaisesRegex(RuntimeError, 'checksum mismatch'):
            SecurityAssetsTransaction(archive, '0' * 64, str(self.root))
        self.assertTrue(self.runtime.is_symlink())

    def test_unlisted_archive_path_rejected(self):
        archive, digest = self.archive({'payload/../../etc/passwd': b'forbidden'})
        with self.assertRaisesRegex(RuntimeError, 'Unlisted'):
            SecurityAssetsTransaction(archive, digest, str(self.root))

    def test_unapproved_manifest_path_rejected(self):
        self.files['admin/conf/htpasswd'] = b'forbidden'
        archive, digest = self.archive()
        with self.assertRaisesRegex(RuntimeError, 'Unapproved'):
            SecurityAssetsTransaction(archive, digest, str(self.root))

    def test_bad_member_hash_rejected(self):
        archive, digest = self.archive(mutate=lambda m: m['files'][0].update(sha256='0' * 64))
        with self.assertRaisesRegex(RuntimeError, 'asset checksum mismatch'):
            SecurityAssetsTransaction(archive, digest, str(self.root))

    def test_failed_prevalidation_leaves_no_backup_or_mutation(self):
        archive, digest = self.archive()
        with patch.object(SecurityAssetsTransaction, 'verify', side_effect=RuntimeError('bad PHP')):
            with self.assertRaisesRegex(RuntimeError, 'bad PHP'):
                SecurityAssetsTransaction(archive, digest, str(self.root))
        self.assertFalse(list(self.root.glob('.cyberpanel-security-backup-*')))
        self.assertTrue(self.runtime.is_symlink())

    def test_persisted_rollback_restores_prior_bundle_and_symlink(self):
        config = self.root / 'conf/httpd_config.conf'
        previous = config.read_bytes()
        tx = self.prepare(fresh=True)
        with patch.object(tx, 'verify', return_value={}):
            tx.apply()
        self.assertTrue(restore_security_assets(tx.backup_dir, str(self.root)))
        self.assertTrue(self.runtime.is_symlink())
        self.assertEqual(config.read_bytes(), previous)
        self.assertEqual(self.website.read_bytes(), b'website-runtime')

    def test_persisted_rollback_rejects_tampered_target_before_changes(self):
        tx = self.prepare()
        with patch.object(tx, 'verify', return_value={}):
            tx.apply()
        manifest = Path(tx.backup_dir) / 'rollback.json'
        data = json.loads(manifest.read_text())
        data['entries'][0]['target'] = '/etc/passwd'
        manifest.write_text(json.dumps(data))
        with self.assertRaisesRegex(RuntimeError, 'Unapproved'):
            restore_security_assets(tx.backup_dir, str(self.root))
        self.assertFalse(self.runtime.is_symlink())

    def test_path_policy_rejects_traversal_and_auth(self):
        for name in ('../VERSION', '/VERSION', 'admin/html/../conf/htpasswd',
                     'admin/html/.user.ini', 'admin/conf/htpasswd', 'conf/httpd_config.conf',
                     'admin//html/test.php', 'admin/html/x\\y.php'):
            self.assertFalse(_allowed(name), name)

if __name__ == '__main__':
    unittest.main()
