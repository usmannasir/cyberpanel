"""Restored private home files retain modes and become readable by the site UID."""
import os
from pathlib import Path
import pwd
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical.test_backup_restore_ssl import load_method


class RestoreHomeOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.root.chmod(0o755)
        self.domain = 'restore.example.test'
        self.home = self.root / self.domain
        self.home.mkdir(mode=0o750)
        self.private = self.home / 'private-db.php'
        self.private.write_text('private database fixture')
        self.private.chmod(0o600)
        public = self.home / 'public_html'
        public.mkdir(mode=0o750)
        (public / 'index.php').write_text('fixture')
        self.external = self.root / 'outside'
        self.external.mkdir(mode=0o700)
        self.external_file = self.external / 'untouched'
        self.external_file.write_text('outside fixture')
        self.external_file.chmod(0o600)
        (self.home / 'linked-file').symlink_to(self.external_file)
        (self.home / 'linked-directory').symlink_to(self.external, target_is_directory=True)
        self.owner = pwd.getpwnam('nobody') if os.geteuid() == 0 else pwd.getpwuid(os.getuid())
        self.websites = Mock()
        self.websites.objects.get.return_value = SimpleNamespace(externalApp=self.owner.pw_name)
        self.restore = load_method('backupUtilities.py', 'backupUtilities',
                                   'restoreWebsiteOwnership', dict(os=os, Websites=self.websites))

    def read_as_site_user(self):
        def change_user():
            os.setgid(self.owner.pw_gid)
            os.setuid(self.owner.pw_uid)
        return subprocess.run(
            [sys.executable, '-c', 'import pathlib,sys; print(pathlib.Path(sys.argv[1]).read_text())', str(self.private)],
            preexec_fn=change_user, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def test_whole_home_owner_changes_without_mode_changes_or_external_link_traversal(self):
        external_before = [(p.stat().st_uid, p.stat().st_gid, stat.S_IMODE(p.stat().st_mode))
                           for p in (self.external, self.external_file)]
        modes_before = {str(p): stat.S_IMODE(p.stat().st_mode)
                        for p in (self.home, self.private, self.home / 'public_html', self.home / 'public_html/index.php')}
        if os.geteuid() == 0:
            self.assertNotEqual(0, self.read_as_site_user().returncode)
        chown = os.chown
        calls = []
        def checked_chown(name, uid, gid, **kwargs):
            self.assertIs(False, kwargs.get('follow_symlinks'))
            self.assertIsInstance(kwargs.get('dir_fd'), int)
            calls.append(name)
            return chown(name, uid, gid, **kwargs)
        with patch.object(os, 'chown', side_effect=checked_chown):
            self.restore(self.domain, homeRoot=str(self.root))
        self.assertNotIn('untouched', calls)
        for path in modes_before:
            details = os.stat(path)
            self.assertEqual(self.owner.pw_uid, details.st_uid)
            self.assertEqual(self.owner.pw_gid, details.st_gid)
            self.assertEqual(modes_before[path], stat.S_IMODE(details.st_mode))
        self.assertEqual(0o600, stat.S_IMODE(self.private.stat().st_mode))
        self.assertEqual(external_before, [(p.stat().st_uid, p.stat().st_gid, stat.S_IMODE(p.stat().st_mode))
                                          for p in (self.external, self.external_file)])
        if os.geteuid() == 0:
            result = self.read_as_site_user()
            self.assertEqual(0, result.returncode, result.stderr)
            self.assertEqual('private database fixture', result.stdout.strip())

    def test_symlink_home_is_refused(self):
        link_domain = 'linked.example.test'
        (self.root / link_domain).symlink_to(self.external, target_is_directory=True)
        with self.assertRaises(OSError):
            self.restore(link_domain, homeRoot=str(self.root))

    def test_domain_path_traversal_is_refused_before_owner_lookup(self):
        for domain in ('', '.', '..', '../outside', 'site/../../outside'):
            with self.subTest(domain=domain), self.assertRaises(ValueError):
                self.restore(domain, homeRoot=str(self.root))
        self.websites.objects.get.assert_not_called()


if __name__ == '__main__':
    unittest.main()
