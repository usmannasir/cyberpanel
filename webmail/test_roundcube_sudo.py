"""Root-free regression checks for install/upgrade Roundcube sudo provisioning."""
from contextlib import ExitStack
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from plogical import roundcubeSudo as sudo


class PolicyTests(unittest.TestCase):
    def test_exact_commands_and_safe_legacy_adoption(self):
        expected = {'/usr/local/CyberPanel/bin/python -I -S '
                    '/usr/local/CyberCP/plogical/roundcubeRuntime.py ' + action
                    for action in ('install', 'enable', 'disable')}
        self.assertTrue(sudo.matching_legacy_policy(sudo.policy()))
        commands = ', '.join(sorted(expected))
        legacy = '\n'.join(user + ' ALL=(root) NOPASSWD: ' + commands
                           for user in ('cyberpanel', 'lscpd'))
        self.assertTrue(sudo.matching_legacy_policy(legacy))
        for unsafe in (legacy.replace(' -I -S ', ' '), legacy + '\nDefaults !authenticate',
                       legacy.replace(' install', ' *'), legacy.replace('(root)', '(ALL)'),
                       legacy.replace('cyberpanel ALL', 'other ALL'), legacy.replace(' disable', ' remove')):
            self.assertFalse(sudo.matching_legacy_policy(unsafe), unsafe)

    def test_deployed_alias_policy_preserves_environment_restrictions(self):
        command = '/usr/local/CyberPanel/bin/python -I -S /usr/local/CyberCP/plogical/roundcubeRuntime.py '
        legacy = ('# Managed by CyberPanel: optional Roundcube lifecycle operations only.\n'
                  'Cmnd_Alias CYBERPANEL_ROUNDCUBE = ' + ', '.join(command + action for action in ('install', 'enable', 'disable')) + '\n'
                  'Defaults!CYBERPANEL_ROUNDCUBE env_reset, !setenv, secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
                  'lscpd ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_ROUNDCUBE\n'
                  'cyberpanel ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_ROUNDCUBE\n')
        self.assertTrue(sudo.matching_legacy_policy(legacy))
        self.assertEqual(legacy.splitlines()[1:], sudo.policy().splitlines()[1:])
        for unsafe in (legacy.replace('!setenv', 'setenv'), legacy.replace('NOSETENV:', 'SETENV:'),
                       legacy.replace(' -I -S ', ' '), legacy + 'other ALL=(root) NOPASSWD: ALL\n',
                       legacy.replace(command + 'disable', '/bin/sh'), legacy.replace('env_reset', '!env_reset')):
            self.assertFalse(sudo.matching_legacy_policy(unsafe), unsafe)

    def test_trusted_path_checks_ownership_modes_and_parents(self):
        for bad_uid, bad_mode in ((1000, 0o755), (0, 0o775), (0, 0o777)):
            def info(path):
                if str(path) == '/trusted':
                    return SimpleNamespace(st_uid=bad_uid, st_mode=stat.S_IFDIR | bad_mode)
                return SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o755)
            with patch.object(Path, 'lstat', info), self.assertRaises(RuntimeError):
                sudo.trusted_path('/trusted/helper.py')
        with patch.object(Path, 'lstat', return_value=SimpleNamespace(st_uid=0, st_mode=stat.S_IFREG | 0o755)):
            sudo.trusted_path('/trusted/helper.py')

    def test_trusted_path_checks_intermediate_symlink_targets(self):
        def info(path):
            if str(path) == '/trusted/python':
                return SimpleNamespace(st_uid=0, st_mode=stat.S_IFLNK | 0o777)
            if str(path) == '/untrusted/link':
                return SimpleNamespace(st_uid=1000, st_mode=stat.S_IFLNK | 0o777)
            return SimpleNamespace(st_uid=0, st_mode=stat.S_IFDIR | 0o755)
        with patch.object(Path, 'lstat', info), patch.object(Path, 'resolve', return_value=Path('/usr/bin/python3')), patch.object(os, 'readlink', return_value='/untrusted/link'), self.assertRaises(RuntimeError):
            sudo.trusted_path('/trusted/python')


class ProvisionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        root = Path(self.stack.enter_context(tempfile.TemporaryDirectory()))
        self.directory = root / 'sudoers.d'
        self.directory.mkdir()
        self.target = self.directory / 'cyberpanel-roundcube'
        self.main = root / 'sudoers'
        self.main.write_text('@includedir /etc/sudoers.d\n')
        for name, value in [('DIRECTORY', self.directory), ('TARGET', self.target), ('SUDOERS', self.main)]:
            self.stack.enter_context(patch.object(sudo, name, value))
        # Dependency fixtures are regular executables; path trust has dedicated tests.
        for name in ('PYTHON', 'HELPER', 'VISUDO'):
            fixture = root / name
            fixture.write_text('fixture')
            fixture.chmod(0o755)
            self.stack.enter_context(patch.object(sudo, name, fixture))
        self.stack.enter_context(patch.object(sudo.os, 'geteuid', return_value=0))
        self.stack.enter_context(patch.object(sudo.os, 'fchown'))
        self.trust = self.stack.enter_context(patch.object(sudo, 'trusted_path'))
        self.run = self.stack.enter_context(patch.object(sudo.subprocess, 'run'))

    def test_atomic_install_has_restricted_permissions_and_validation(self):
        observed = []
        def validate(argv, **kwargs):
            observed.append(argv)
            if len(observed) < 3:
                self.assertFalse(self.target.exists())
            if '-cf' in argv:
                candidate = Path(argv[-1])
                self.assertEqual(sudo.policy(), candidate.read_text())
                self.assertEqual(0o440, stat.S_IMODE(candidate.stat().st_mode))
        self.run.side_effect = validate
        sudo.provision()
        self.assertEqual(sudo.policy(), self.target.read_text())
        self.assertEqual(0o440, stat.S_IMODE(self.target.stat().st_mode))
        self.assertEqual(['-c', '-cf', '-c'], [argv[1] for argv in observed])
        self.assertEqual([self.target], list(self.directory.iterdir()))
        for dependency in (sudo.PYTHON, sudo.HELPER, sudo.VISUDO, sudo.SUDOERS, sudo.DIRECTORY):
            self.trust.assert_any_call(dependency)

    def test_invalid_candidate_preserves_previous_policy_and_removes_temp(self):
        previous = sudo.policy()
        self.target.write_text(previous)
        self.run.side_effect = [None, subprocess.CalledProcessError(1, 'visudo')]
        with self.assertRaises(subprocess.CalledProcessError):
            sudo.provision()
        self.assertEqual(previous, self.target.read_text())
        self.assertEqual([self.target], list(self.directory.iterdir()))

    def test_global_alias_conflict_rolls_back_policy(self):
        for existing in (False, True):
            with self.subTest(existing=existing):
                previous = sudo.policy().replace(sudo.MARKER, '# Legacy Roundcube rule\n')
                if existing:
                    self.target.write_text(previous)
                self.run.side_effect = [None, None, subprocess.CalledProcessError(1, 'visudo')]
                with self.assertRaises(subprocess.CalledProcessError):
                    sudo.provision()
                if existing:
                    self.assertEqual(previous, self.target.read_text())
                    self.assertEqual([self.target], list(self.directory.iterdir()))
                else:
                    self.assertEqual([], list(self.directory.iterdir()))

    def test_unmanaged_policy_and_symlinks_are_not_overwritten(self):
        self.target.write_text('other ALL=(ALL) NOPASSWD: ALL\n')
        with self.assertRaisesRegex(RuntimeError, 'unmanaged'):
            sudo.provision()
        self.assertEqual('other ALL=(ALL) NOPASSWD: ALL\n', self.target.read_text())
        self.target.unlink()
        self.target.symlink_to(self.main)
        with self.assertRaisesRegex(RuntimeError, 'regular file'):
            sudo.provision()
        self.assertEqual('@includedir /etc/sudoers.d\n', self.main.read_text())
        self.run.assert_not_called()

    def test_nonroot_and_missing_includedir_fail_without_policy(self):
        with patch.object(sudo.os, 'geteuid', return_value=1000), self.assertRaisesRegex(RuntimeError, 'as root'):
            sudo.provision()
        self.main.write_text('root ALL=(ALL) ALL\n')
        with self.assertRaisesRegex(RuntimeError, 'Enable /etc/sudoers.d'):
            sudo.provision()
        self.assertFalse(self.target.exists())
        self.run.assert_not_called()

    def test_matching_legacy_policy_is_adopted(self):
        self.target.write_text(sudo.policy().replace(sudo.MARKER, '# Legacy Roundcube rule\n'))
        sudo.provision()
        self.assertEqual(sudo.policy(), self.target.read_text())


if __name__ == '__main__':
    unittest.main()
