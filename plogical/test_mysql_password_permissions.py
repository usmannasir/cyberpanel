"""Regression coverage for the upgrader's narrow MySQL credential mode repair."""
import ast
import errno
import grp
import os
from pathlib import Path
import stat
import struct
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]

@unittest.skipUnless(os.geteuid() == 0, 'requires root for real credential isolation')
class MySQLPasswordPermissionTests(unittest.TestCase):
    def setUp(self):
        self.gid = grp.getgrnam('cyberpanel').gr_gid
        self.temp = tempfile.TemporaryDirectory(prefix='.cp-mysql-mode-test-', dir='/var/lib')
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.directory.chmod(0o755)
        self.path = self.directory / 'mysqlPassword'
        self.original = b'{"mysqluser":"custom_user","mysqlpassword":"fixture-only","mysqlport":4406}\n'
        self.path.write_bytes(self.original)
        os.chown(str(self.path), 0, self.gid)
        self.path.chmod(0o600)

    def can_read(self, uid=65533, gid=None):
        child = os.fork()
        if child == 0:
            try:
                os.setgroups([])
                os.setgid(self.gid if gid is None else gid)
                os.setuid(uid)
                with self.path.open('rb') as stream:
                    data = stream.read()
                os._exit(0 if data == self.original else 2)
            except OSError:
                os._exit(1)
        _, status = os.waitpid(child, 0)
        return os.WIFEXITED(status) and os.WEXITSTATUS(status) == 0

    def repair(self):
        from plogical.mysqlPasswordPermissions import repair
        return repair(str(self.path))

    def test_upgrade_repairs_actual_service_read_without_exposing_to_other_users(self):
        self.assertFalse(self.can_read())
        tree = ast.parse((ROOT / 'plogical/upgrade.py').read_text())
        body = next(node.body for node in ast.walk(tree)
                    if isinstance(node, ast.FunctionDef) and node.name == 'upgrade')
        begin = next(i for i, node in enumerate(body) if isinstance(node, ast.Expr)
                     and isinstance(node.value, ast.Call)
                     and isinstance(node.value.func, ast.Attribute)
                     and node.value.func.attr == 'fixPermissions') + 1
        end = next(i for i, node in enumerate(body) if isinstance(node, ast.ImportFrom)
                   and node.module == 'plogical.roundcubeSudo')
        statements = body[begin:end]
        # Execute only the production repair hook; never the surrounding upgrader.
        import sys
        if 'plogical.mysqlPasswordPermissions' in sys.modules or (ROOT / 'plogical/mysqlPasswordPermissions.py').exists():
            from plogical import mysqlPasswordPermissions
            with patch.object(mysqlPasswordPermissions, 'PASSWORD_FILE', str(self.path)):
                exec(compile(ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[])), 'upgrade-hook', 'exec'), {})
        else:
            exec(compile(ast.fix_missing_locations(ast.Module(body=statements, type_ignores=[])), 'upgrade-hook', 'exec'), {})
        self.assertTrue(self.can_read(), 'upgrader left the panel service unable to read its credential')
        self.assertFalse(self.can_read(gid=65534))
        self.assertEqual(self.original, self.path.read_bytes())

    def test_root_group_repair_is_idempotent_and_preserves_inode_and_bytes(self):
        os.chown(str(self.path), 0, 0)
        before = self.path.stat()
        self.assertTrue(self.repair())
        self.assertFalse(self.repair())
        after = self.path.stat()
        self.assertEqual((0, self.gid, 0o640), (after.st_uid, after.st_gid, stat.S_IMODE(after.st_mode)))
        self.assertEqual((before.st_ino, before.st_size, before.st_mtime_ns), (after.st_ino, after.st_size, after.st_mtime_ns))
        self.assertEqual(self.original, self.path.read_bytes())

    def test_symlink_file_is_rejected_without_changing_target(self):
        target = self.directory / 'custom'
        self.path.rename(target)
        self.path.symlink_to(target)
        with self.assertRaises((OSError, ValueError)):
            self.repair()
        self.assertEqual(0o600, stat.S_IMODE(target.stat().st_mode))

    def test_symlink_parent_is_rejected(self):
        parent = self.directory / 'actual'
        parent.mkdir()
        self.path.rename(parent / 'mysqlPassword')
        link = self.directory / 'linked'
        link.symlink_to(parent, target_is_directory=True)
        self.path = link / 'mysqlPassword'
        with self.assertRaises((OSError, ValueError)):
            self.repair()
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))

    def test_hardlink_rejected(self):
        os.link(str(self.path), str(self.directory / 'alias'))
        with self.assertRaises((OSError, ValueError)):
            self.repair()
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))

    def test_nonregular_rejected_without_blocking(self):
        self.path.unlink()
        os.mkfifo(str(self.path), 0o600)
        with self.assertRaises((OSError, ValueError)):
            self.repair()

    def test_custom_owner_group_and_mode_are_not_rewritten(self):
        for uid, gid, mode in ((65534, self.gid, 0o600), (0, 65534, 0o600), (0, self.gid, 0o400), (0, self.gid, 0o644)):
            with self.subTest(uid=uid, gid=gid, mode=mode):
                os.chown(str(self.path), uid, gid)
                self.path.chmod(mode)
                with self.assertRaises((OSError, ValueError)):
                    self.repair()
                current = self.path.stat()
                self.assertEqual((uid, gid, mode), (current.st_uid, current.st_gid, stat.S_IMODE(current.st_mode)))

    def test_unsafe_parent_is_not_repaired(self):
        for uid, mode in ((0, 0o777), (65534, 0o755), (0, 0o700)):
            with self.subTest(uid=uid, mode=mode):
                os.chown(str(self.directory), uid, 0)
                self.directory.chmod(mode)
                with self.assertRaises((OSError, ValueError)):
                    self.repair()
                self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))
        os.chown(str(self.directory), 0, 0)

    def test_masked_named_user_acl_is_rejected_without_activating_access(self):
        # Real Linux POSIX ACL: named user can read, but its mask is initially0.
        acl = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', tag, perm, identity)
            for tag, perm, identity in ((1, 6, 0xffffffff), (2, 4, 65534),
                (4, 0, 0xffffffff), (16, 0, 0xffffffff), (32, 0, 0xffffffff)))
        os.setxattr(str(self.path), 'system.posix_acl_access', acl)
        self.assertFalse(self.can_read(uid=65534, gid=65534))
        self.path.chmod(0o640)
        self.assertTrue(self.can_read(uid=65534, gid=65534), 'fixture must reproduce ACL mask activation')
        self.path.chmod(0o600)
        before = os.getxattr(str(self.path), 'system.posix_acl_access')
        with self.assertRaises(PermissionError):
            self.repair()
        self.assertFalse(self.can_read(uid=65534, gid=65534))
        self.assertEqual(before, os.getxattr(str(self.path), 'system.posix_acl_access'))
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))

    def test_parent_access_acl_is_preserved_and_rejected(self):
        acl = struct.pack('<I', 2) + b''.join(struct.pack('<HHI', tag, perm, identity)
            for tag, perm, identity in ((1, 7, 0xffffffff), (2, 1, 65534),
                (4, 5, 0xffffffff), (16, 5, 0xffffffff), (32, 5, 0xffffffff)))
        os.setxattr(str(self.directory), 'system.posix_acl_access', acl)
        before = os.getxattr(str(self.directory), 'system.posix_acl_access')
        with self.assertRaises(PermissionError):
            self.repair()
        self.assertEqual(before, os.getxattr(str(self.directory), 'system.posix_acl_access'))
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))
        self.assertEqual(self.original, self.path.read_bytes())

    def test_filesystem_without_acl_support_can_repair_standard_file(self):
        with patch('os.getxattr', side_effect=OSError(errno.ENOTSUP, 'fixture unsupported')):
            self.assertTrue(self.repair())
        self.assertTrue(self.can_read())
        self.assertFalse(self.can_read(gid=65534))

    def test_acl_lookup_failure_is_not_treated_as_no_acl(self):
        with patch('os.getxattr', side_effect=PermissionError('fixture xattr denial')):
            with self.assertRaises(PermissionError):
                self.repair()
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))

    def test_missing_file_not_created(self):
        self.path.unlink()
        with self.assertRaises(OSError):
            self.repair()
        self.assertFalse(self.path.exists())

    def test_missing_group_and_nonroot_are_fail_closed(self):
        with patch('grp.getgrnam', side_effect=KeyError('fixture')):
            with self.assertRaises((OSError, ValueError, KeyError)):
                self.repair()
        with patch('os.geteuid', return_value=65534):
            with self.assertRaises((OSError, ValueError)):
                self.repair()
        self.assertEqual(0o600, stat.S_IMODE(self.path.stat().st_mode))

if __name__ == '__main__':
    unittest.main()
