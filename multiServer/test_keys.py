"""The role switch and the key files: off unless everything about them is right."""
import ast
import sys
import os
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch

from install import multiserver_identity as provision
from multiServer import keys

ME = os.getuid()
MY_GROUP = os.getgid()


class Directory(unittest.TestCase):
    """A key directory owned by the test's own user stands in for root's."""

    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.directory = Path(holder.name, 'multiserver')
        for target in (keys, provision):
            for name, value in (('KEY_DIRECTORY', str(self.directory)), ('OWNER', ME)):
                patcher = patch.object(target, name, value)
                patcher.start()
                self.addCleanup(patcher.stop)

    def provision(self):
        provision.ensure_key_directory(group=MY_GROUP)

    def write(self, name, text, mode=0o640):
        path = self.directory / name
        path.write_text(text)
        path.chmod(mode)
        return path


class ProvisioningTests(Directory):
    def test_first_run_creates_a_private_directory_with_the_feature_off(self):
        self.provision()
        details = self.directory.stat()
        self.assertEqual((0o750, ME, MY_GROUP),
                         (stat.S_IMODE(details.st_mode), details.st_uid, details.st_gid))
        role = (self.directory / 'role').stat()
        self.assertEqual(0o640, stat.S_IMODE(role.st_mode))
        self.assertEqual('off\n', (self.directory / 'role').read_text())
        self.assertEqual('off', keys.role())

    def test_repeat_run_keeps_the_role_and_every_key(self):
        self.provision()
        self.write('role', 'node\n')
        self.write('identity.key', 'ab' * 32)
        self.provision()
        self.assertEqual('node\n', (self.directory / 'role').read_text())
        self.assertEqual('ab' * 32, (self.directory / 'identity.key').read_text())

    def test_directory_that_is_a_link_or_a_file_is_refused(self):
        elsewhere = self.directory.parent / 'elsewhere'
        elsewhere.mkdir()
        os.symlink(str(elsewhere), str(self.directory))
        with self.assertRaises(RuntimeError):
            self.provision()
        self.assertEqual([], list(elsewhere.iterdir()))
        os.unlink(str(self.directory))
        self.directory.write_text('not a directory')
        with self.assertRaises(RuntimeError):
            self.provision()

    def test_role_file_that_is_a_link_is_refused(self):
        self.provision()
        target = self.directory.parent / 'target'
        target.write_text('controller\n')
        (self.directory / 'role').unlink()
        os.symlink(str(target), str(self.directory / 'role'))
        with self.assertRaises(RuntimeError):
            self.provision()
        self.assertEqual('off', keys.role())

    def test_set_role_writes_only_known_roles_and_creates_that_roles_key(self):
        self.provision()
        provision.set_role('node', group=MY_GROUP)
        self.assertEqual('node', keys.role())
        identity = (self.directory / 'identity.key').read_text()
        self.assertRegex(identity, r'\A[0-9a-f]{64}\Z')
        self.assertEqual('1', (self.directory / 'generation').read_text())
        self.assertFalse((self.directory / 'master.key').exists())
        provision.set_role('node', group=MY_GROUP)
        self.assertEqual(identity, (self.directory / 'identity.key').read_text())
        provision.set_role('off', group=MY_GROUP)
        self.assertEqual('off', keys.role())
        self.assertEqual(identity, (self.directory / 'identity.key').read_text())
        provision.set_role('controller', group=MY_GROUP)
        self.assertEqual('controller', keys.role())
        self.assertRegex((self.directory / 'master.key').read_text(), r'\A[A-Za-z0-9_-]{43}=\Z')
        for unknown in ('both', 'Controller', '', 'node\n', None):
            with self.assertRaises(ValueError):
                provision.set_role(unknown, group=MY_GROUP)
        self.assertEqual('controller', keys.role())

    def test_generation_only_ever_increases(self):
        self.provision()
        provision.set_role('node', group=MY_GROUP)
        self.assertEqual(2, provision.bump_generation(group=MY_GROUP))
        self.assertEqual(3, provision.bump_generation(group=MY_GROUP))
        self.assertEqual(3, keys.generation())


class RoleReadingTests(Directory):
    def test_missing_directory_or_file_means_off(self):
        self.assertEqual('off', keys.role())
        self.provision()
        (self.directory / 'role').unlink()
        self.assertEqual('off', keys.role())

    def test_only_an_exact_known_role_is_accepted(self):
        self.provision()
        for text, expected in (('controller\n', 'controller'), ('node\n', 'node'), ('node', 'node'),
                               ('off\n', 'off'), ('Controller\n', 'off'), ('node controller\n', 'off'),
                               ('controller\nnode\n', 'off'), ('', 'off'), ('x' * 4000, 'off'),
                               (' node\n', 'off')):
            self.write('role', text)
            self.assertEqual(expected, keys.role(), repr(text))

    def test_exposed_or_substituted_role_file_means_off(self):
        self.provision()
        self.write('role', 'controller\n', mode=0o644)
        self.assertEqual('off', keys.role())
        self.write('role', 'controller\n', mode=0o660)
        self.assertEqual('off', keys.role())
        self.write('role', 'controller\n')
        self.assertEqual('controller', keys.role())
        os.link(str(self.directory / 'role'), str(self.directory / 'copy'))
        self.assertEqual('off', keys.role())
        (self.directory / 'copy').unlink()
        with patch.object(keys, 'OWNER', ME + 1):
            self.assertEqual('off', keys.role())

    def test_role_never_raises(self):
        with patch.object(keys.os, 'open', side_effect=RuntimeError('unexpected')):
            self.assertEqual('off', keys.role())


class KeyReadingTests(Directory):
    def test_identity_and_master_keys_are_returned_only_in_their_exact_form(self):
        self.provision()
        self.assertIsNone(keys.identity_key())
        self.assertIsNone(keys.master_key())
        provision.set_role('node', group=MY_GROUP)
        self.assertEqual(32, len(keys.identity_key()))
        self.assertEqual((self.directory / 'identity.key').read_text(), keys.identity_key().hex())
        provision.set_role('controller', group=MY_GROUP)
        self.assertEqual((self.directory / 'master.key').read_text().encode(), keys.master_key())
        for name, reader, bad in (('identity.key', keys.identity_key, 'ab' * 31),
                                  ('identity.key', keys.identity_key, 'AB' * 32),
                                  ('identity.key', keys.identity_key, 'ab' * 32 + '\n'),
                                  ('master.key', keys.master_key, 'short')):
            (self.directory / name).unlink()
            self.write(name, bad)
            self.assertIsNone(reader(), (name, bad))

    def test_world_readable_or_linked_key_is_not_used(self):
        self.provision()
        provision.set_role('node', group=MY_GROUP)
        path = self.directory / 'identity.key'
        path.chmod(0o644)
        self.assertIsNone(keys.identity_key())
        path.chmod(0o640)
        self.assertIsNotNone(keys.identity_key())
        secret = self.directory.parent / 'other'
        secret.write_text('cd' * 32)
        path.unlink()
        os.symlink(str(secret), str(path))
        self.assertIsNone(keys.identity_key())

    def test_generation_defaults_to_zero_when_unreadable(self):
        self.assertEqual(0, keys.generation())
        self.provision()
        self.write('generation', 'many')
        self.assertEqual(0, keys.generation())


class CompatibilityTests(unittest.TestCase):
    def test_sources_parse_as_python_3_6(self):
        root = Path(__file__).resolve().parents[1]
        for relative in ('multiServer/keys.py', 'install/multiserver_identity.py'):
            options = {'feature_version': (3, 6)} if sys.version_info >= (3, 8) else {}
            ast.parse((root / relative).read_text(), **options)


if __name__ == '__main__':
    unittest.main()
