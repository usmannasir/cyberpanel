"""Filesystem acceptance checks for pre-activation phpMyAdmin peer identity."""
import grp
import json
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from install.proxy_identity import ensure_pma_peer_key, prepare_staged_phpmyadmin


@unittest.skipUnless(os.geteuid() == 0, 'root is required to test service ownership boundaries')
class ProxyIdentityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='pma-peer-test-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.root.chmod(0o755)
        self.panel_user = pwd.getpwnam('daemon')
        self.php_user = pwd.getpwnam('nobody')
        self.panel_group = grp.getgrgid(self.panel_user.pw_gid).gr_name
        self.php_group = grp.getgrgid(self.php_user.pw_gid).gr_name
        self.panel_key = self.root / 'panel-key'
        self.php_key = self.root / 'php-key'
        self.staged = self.root / 'staged'
        self.staged.mkdir()
        self.pma = self.staged / 'public' / 'phpmyadmin'
        self.pma.mkdir(parents=True)
        (self.pma / 'config.inc.php').write_text('retained configuration')
        self.source = self.staged / 'plogical'
        self.source.mkdir()
        self.signer = self.source / 'phpmyadminsignin.php'
        self.signer.write_text("<?php\n// new authenticated signer\n        $_SESSION['PMA_single_signon_host'] = 'localhost';\n        $_SESSION['PMA_single_signon_port'] = 3306;\n")
        (self.source / 'phpmyadminsession.php').write_text('<?php // new session helper\n')
        self.config = self.root / 'database-config'
        self.config.write_text('fixture-local-password')
        self.kwargs = dict(path=str(self.panel_key), php_path=str(self.php_key),
                           group=self.panel_group, php_group=self.php_group)

    def ensure(self):
        ensure_pma_peer_key(**self.kwargs)

    def stage(self):
        return prepare_staged_phpmyadmin(str(self.staged), config_path=str(self.config), **self.kwargs)

    def read_as(self, path, user):
        def demote():
            os.setgroups([])
            os.setgid(user.pw_gid)
            os.setuid(user.pw_uid)
        return subprocess.run([sys.executable, '-c', 'import sys;open(sys.argv[1],"rb").read()', str(path)],
                              preexec_fn=demote, capture_output=True).returncode

    def test_default_keys_are_outside_recursive_lscp_and_source_repairs(self):
        from install.proxy_identity import PMA_PEER_KEY, PMA_PHP_PEER_KEY
        self.assertEqual('/etc/cyberpanel/pmaPeerKey', PMA_PEER_KEY)
        self.assertEqual('/etc/cyberpanel/pmaPeerKeyPHP', PMA_PHP_PEER_KEY)

    def test_real_service_groups_can_read_only_their_copy(self):
        self.ensure()
        self.assertEqual(self.panel_key.read_bytes(), self.php_key.read_bytes())
        self.assertRegex(self.panel_key.read_text(), '^[a-f0-9]{64}$')
        for path, owner, other in ((self.panel_key, self.panel_user, self.php_user),
                                   (self.php_key, self.php_user, self.panel_user)):
            self.assertEqual((0, owner.pw_gid, 0o640),
                             (path.stat().st_uid, path.stat().st_gid, stat.S_IMODE(path.stat().st_mode)))
            self.assertEqual(0, self.read_as(path, owner))
            self.assertNotEqual(0, self.read_as(path, other))

    def test_repeat_provisioning_preserves_keys(self):
        self.ensure()
        before = self.panel_key.read_bytes()
        self.ensure()
        self.assertEqual(before, self.panel_key.read_bytes())
        self.assertEqual(before, self.php_key.read_bytes())

    def test_exposed_or_group_writable_keys_are_refused(self):
        self.ensure()
        for path in (self.panel_key, self.php_key):
            for mode in (0o644, 0o660, 0o646):
                with self.subTest(path=path.name, mode=oct(mode)):
                    path.chmod(mode)
                    with self.assertRaises(RuntimeError):
                        self.ensure()
                    path.chmod(0o640)

    def test_key_owner_must_be_root(self):
        self.ensure()
        os.chown(self.panel_key, self.panel_user.pw_uid, self.panel_user.pw_gid)
        with self.assertRaises(RuntimeError):
            self.ensure()

    def test_symlink_key_is_refused_without_changing_target(self):
        target = self.root / 'target'
        target.write_text('a' * 64)
        target.chmod(0o600)
        self.panel_key.symlink_to(target)
        with self.assertRaises(OSError):
            self.ensure()
        self.assertEqual('a' * 64, target.read_text())
        self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))

    def test_hardlinked_key_is_refused(self):
        self.ensure()
        os.link(self.php_key, self.root / 'link')
        with self.assertRaises(RuntimeError):
            self.ensure()

    def test_mismatched_copies_are_refused_and_preserved(self):
        self.ensure()
        original = self.panel_key.read_bytes()
        self.php_key.write_text('b' * 64)
        with self.assertRaises(RuntimeError):
            self.ensure()
        self.assertEqual(original, self.panel_key.read_bytes())
        self.assertEqual('b' * 64, self.php_key.read_text())

    def test_fifo_key_is_refused_without_waiting_for_a_writer(self):
        os.mkfifo(self.panel_key, 0o600)
        with self.assertRaises(RuntimeError):
            self.ensure()

    def test_malformed_key_is_refused(self):
        self.panel_key.write_text('not-a-key')
        self.panel_key.chmod(0o600)
        with self.assertRaises(RuntimeError):
            self.ensure()

    def test_local_staging_replaces_both_helpers_and_preserves_config(self):
        (self.pma / 'phpmyadminsignin.php').write_text('old untrusted signer')
        self.assertTrue(self.stage())
        self.assertEqual(self.signer.read_text(), (self.pma / 'phpmyadminsignin.php').read_text())
        self.assertEqual((self.source / 'phpmyadminsession.php').read_text(),
                         (self.pma / 'phpmyadminsession.php').read_text())
        self.assertEqual('retained configuration', (self.pma / 'config.inc.php').read_text())
        for name in ('phpmyadminsignin.php', 'phpmyadminsession.php'):
            info = (self.pma / name).stat()
            self.assertEqual((0, self.php_user.pw_gid, 0o640),
                             (info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode)))

    def test_remote_host_and_nondefault_port_are_preserved_with_php_escaping(self):
        self.config.write_text(json.dumps({'mysqlhost': "db'host\\path", 'mysqlport': '3307'}))
        self.stage()
        content = (self.pma / 'phpmyadminsignin.php').read_text()
        self.assertIn("'db\\'host\\\\path'", content)
        self.assertIn("['PMA_single_signon_port'] = 3307;", content)

    def test_missing_source_fails_before_any_helper_is_replaced(self):
        (self.pma / 'phpmyadminsignin.php').write_text('old fixture')
        (self.source / 'phpmyadminsession.php').unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage()
        self.assertEqual('old fixture', (self.pma / 'phpmyadminsignin.php').read_text())
        self.assertFalse(self.panel_key.exists())

    def test_invalid_remote_config_cannot_fall_back_to_localhost(self):
        values = ('{broken', '[]', '{}', '{"mysqlhost":null,"mysqlport":3306}',
                  '{"mysqlhost":"db"}', '{"mysqlhost":"db","mysqlport":0}',
                  '{"mysqlhost":"db","mysqlport":"wrong"}',
                  '{"mysqlhost":"","mysqlport":3306}')
        for value in values:
            with self.subTest(config=value):
                self.config.write_text(value)
                with self.assertRaises((RuntimeError, ValueError)):
                    self.stage()
                self.assertFalse(self.panel_key.exists())
                self.assertFalse((self.pma / 'phpmyadminsignin.php').exists())

    def test_missing_or_empty_database_config_is_refused(self):
        self.config.unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage()
        self.config.write_text('')
        with self.assertRaises(RuntimeError):
            self.stage()

    def test_symlink_staging_directory_is_refused(self):
        real = self.staged / 'retained'
        self.pma.rename(real)
        self.pma.symlink_to(real, target_is_directory=True)
        with self.assertRaises(RuntimeError):
            self.stage()
        self.assertFalse((real / 'phpmyadminsignin.php').exists())

    def test_symlink_source_is_refused(self):
        self.signer.unlink()
        self.signer.symlink_to(self.config)
        with self.assertRaises(OSError):
            self.stage()

    def test_absent_phpmyadmin_only_provisions_keys(self):
        import shutil
        shutil.rmtree(self.staged / 'public')
        self.config.unlink()
        self.assertFalse(self.stage())
        self.assertTrue(self.panel_key.is_file())
        self.assertFalse((self.staged / 'public').exists())

    def test_copy_error_propagates_and_temporary_files_are_removed(self):
        with mock.patch('install.proxy_identity.os.replace', side_effect=OSError('copy failure')):
            with self.assertRaises(OSError):
                self.stage()
        self.assertEqual([], list(self.pma.glob('.pma-peer-*')))
        self.assertFalse((self.pma / 'phpmyadminsignin.php').exists())

    def make_current(self):
        self.current = self.root / 'current'
        self.current_pma = self.current / 'public' / 'phpmyadmin'
        self.current_pma.mkdir(parents=True)
        (self.current_pma / 'index.php').write_text('<?php // existing framework')
        (self.current_pma / 'config.inc.php').write_text('retained configuration')
        (self.current_pma / 'phpmyadminsignin.php').write_text('old untrusted signer')
        (self.current_pma / 'phpmyadminsession.php').write_text('old untrusted session helper')
        library = self.current_pma / 'libraries'
        library.mkdir()
        self.library_file = library / 'fixture.php'
        self.library_file.write_text('retained app library')
        os.chown(self.library_file, self.php_user.pw_uid, self.php_user.pw_gid)
        self.library_file.chmod(0o600)

    def stage_current(self):
        return prepare_staged_phpmyadmin(str(self.staged), config_path=str(self.config),
                                         current_root=str(self.current), **self.kwargs)

    def test_complete_retained_app_is_available_before_source_activation(self):
        self.make_current()
        original = {str(path.relative_to(self.current_pma)): path.read_bytes()
                    for path in self.current_pma.rglob('*') if path.is_file()}
        self.stage_current()
        self.assertEqual('<?php // existing framework', (self.pma / 'index.php').read_text())
        library = self.pma / 'libraries' / 'fixture.php'
        self.assertEqual('retained app library', library.read_text())
        self.assertEqual((self.php_user.pw_uid, self.php_user.pw_gid, 0o600),
                         (library.stat().st_uid, library.stat().st_gid, stat.S_IMODE(library.stat().st_mode)))
        self.assertEqual(0, self.read_as(library, self.php_user))
        self.assertNotIn('old untrusted', (self.pma / 'phpmyadminsignin.php').read_text())
        self.assertNotIn('old untrusted', (self.pma / 'phpmyadminsession.php').read_text())
        self.assertEqual(original, {str(path.relative_to(self.current_pma)): path.read_bytes()
                                  for path in self.current_pma.rglob('*') if path.is_file()})

    def test_retained_tree_symlink_is_refused_without_reading_external_file(self):
        self.make_current()
        target = self.root / 'outside'
        target.write_text('must never be copied')
        (self.current_pma / 'linked').symlink_to(target)
        with self.assertRaises(OSError):
            self.stage_current()
        self.assertFalse((self.pma / 'linked').exists())
        self.assertFalse(self.panel_key.exists())

    def test_special_file_in_retained_tree_is_refused_without_hanging(self):
        self.make_current()
        os.mkfifo(self.current_pma / 'pipe', 0o600)
        with self.assertRaises(RuntimeError):
            self.stage_current()

    def test_retained_config_without_framework_cannot_activate(self):
        self.make_current()
        (self.current_pma / 'index.php').unlink()
        with self.assertRaises(FileNotFoundError):
            self.stage_current()
        self.assertFalse(self.panel_key.exists())

    def test_current_and_staged_trees_must_be_separate(self):
        with self.assertRaises(RuntimeError):
            prepare_staged_phpmyadmin(str(self.staged), current_root=str(self.staged), **self.kwargs)

    def test_both_absent_apps_only_provision_keys(self):
        import shutil
        self.current = self.root / 'current'
        self.current.mkdir()
        shutil.rmtree(self.staged / 'public')
        self.assertFalse(self.stage_current())
        self.assertTrue(self.panel_key.exists())

    def test_repository_helpers_stage_and_keep_remote_endpoint(self):
        source = Path(__file__).resolve().parents[1] / 'plogical'
        for name in ('phpmyadminsignin.php', 'phpmyadminsession.php'):
            (self.source / name).write_bytes((source / name).read_bytes())
        self.config.write_text(json.dumps({'mysqlhost': '2001:db8::20', 'mysqlport': 3308}))
        self.stage()
        content = (self.pma / 'phpmyadminsignin.php').read_text()
        self.assertIn('X-CyberPanel-Peer-Signature', content)
        self.assertIn("['PMA_single_signon_host'] = '2001:db8::20';", content)
        self.assertIn("['PMA_single_signon_port'] = 3308;", content)


if __name__ == '__main__':
    unittest.main()
