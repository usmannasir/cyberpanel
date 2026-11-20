"""Permission repair works on directories a customer controls: nothing privileged may follow a link."""
import grp
import json
import os
from pathlib import Path
import pwd
import shlex
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from filemanager.test_permission_feedback import load, response
from plogical.fileSystemSecurity import set_directory_owner

ROOT = Path(__file__).resolve().parents[1]
USER = pwd.getpwuid(os.getuid()).pw_name
GROUP = grp.getgrgid(os.getgid()).gr_name


class DirectoryOwnerTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name, 'home', 'example.com')
        self.home.mkdir(parents=True)
        self.outside = Path(holder.name, 'outside')
        self.outside.mkdir(mode=0o700)
        (self.outside / 'passwd').write_text('root:x:0:0\n')
        (self.outside / 'passwd').chmod(0o600)

    def mode(self, path):
        return stat.S_IMODE(os.stat(str(path), follow_symlinks=False).st_mode)

    def test_directory_receives_owner_group_and_mode(self):
        target = self.home / 'public_html'
        target.mkdir(mode=0o700)
        set_directory_owner(str(self.home), str(target), USER, GROUP, 0o750)
        self.assertEqual(0o750, self.mode(target))
        set_directory_owner(str(self.home.parent), str(self.home), USER, GROUP, None)

    def test_link_in_place_of_the_directory_is_refused_and_its_target_untouched(self):
        for target in (self.outside, self.outside / 'passwd'):
            link = self.home / 'public_html'
            os.symlink(str(target), str(link))
            before = self.mode(target)
            with self.assertRaises(OSError):
                set_directory_owner(str(self.home), str(link), USER, GROUP, 0o750)
            self.assertEqual(before, self.mode(target))
            link.unlink()

    def test_link_in_a_parent_directory_is_refused(self):
        (self.outside / 'docroot').mkdir(mode=0o700)
        os.symlink(str(self.outside), str(self.home / 'sites'))
        with self.assertRaises(OSError):
            set_directory_owner(str(self.home), str(self.home / 'sites' / 'docroot'), USER, GROUP, 0o750)
        self.assertEqual(0o700, self.mode(self.outside / 'docroot'))

    def test_file_and_paths_outside_the_home_are_refused(self):
        (self.home / 'public_html').write_text('a file')
        with self.assertRaises(OSError):
            set_directory_owner(str(self.home), str(self.home / 'public_html'), USER, GROUP, 0o750)
        for path in (str(self.outside), str(self.home / '..' / '..' / 'outside'), '/etc'):
            with self.assertRaises(ValueError):
                set_directory_owner(str(self.home), path, USER, GROUP, 0o750)
        self.assertEqual(0o700, self.mode(self.outside))

    def test_unknown_account_or_impossible_mode_changes_nothing(self):
        target = self.home / 'public_html'
        target.mkdir(mode=0o700)
        for arguments in (('no-such-user-zz', GROUP, 0o750), (USER, 'no-such-group-zz', 0o750),
                          (USER, GROUP, 0o4750), (USER, GROUP, '750')):
            with self.assertRaises((KeyError, ValueError)):
                set_directory_owner(str(self.home), str(target), *arguments)
        self.assertEqual(0o700, self.mode(target))

    def test_command_line_helper_applies_the_same_checks(self):
        target = self.home / 'public_html'
        target.mkdir(mode=0o700)
        script = str(ROOT / 'plogical' / 'secureDirectoryOwner.py')

        def run(directory):
            return subprocess.run([sys.executable, script, '--allowed-root', str(self.home), '--directory',
                                   directory, '--user', USER, '--group', GROUP, '--mode', '750'],
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30).returncode

        self.assertEqual(0, run(str(target)))
        self.assertEqual(0o750, self.mode(target))
        target.rmdir()
        os.symlink(str(self.outside), str(target))
        self.assertNotEqual(0, run(str(target)))
        self.assertEqual(0o700, self.mode(self.outside))

    @unittest.skipUnless(os.geteuid() == 0, 'needs root to change ownership')
    def test_recursive_ownership_does_not_follow_a_link_swapped_in_for_the_tree(self):
        os.symlink(str(self.outside), str(self.home / 'public_html'))
        subprocess.run(['chown', '-R', '-P', 'nobody', str(self.home / 'public_html')], check=True)
        self.assertEqual(0, os.stat(str(self.outside)).st_uid)
        self.assertEqual(0, os.stat(str(self.outside / 'passwd')).st_uid)


class RepairPlanTests(unittest.TestCase):
    """Which account runs each repair command, and in which order."""

    def plan(self, children=()):
        calls = []

        def execute(command, user=None, shell=None, dir=None, retRequired=None):
            calls.append((command, user))
            return (1, '') if retRequired else ''

        process = Mock(centos=0, cent8=1)
        process.decideDistro.return_value = 2
        process.outputExecutioner.side_effect = execute
        website = Mock(externalApp='examp1234')
        website.childdomains_set.all.return_value = [SimpleNamespace(path=path) for path in children]
        websites = Mock()
        websites.objects.get.return_value = website
        repair = load('filemanager/filemanager.py', 'fixPermissions', dict(
            Websites=websites, ProcessUtilities=process, json=json, HttpResponse=response,
            logging=Mock(), shlex=shlex), 'FileManager')
        self.assertIsNone(repair(SimpleNamespace(returnPathEnclosed=shlex.quote), 'example.com'))
        return calls

    def test_no_privileged_command_changes_modes_or_follows_a_link(self):
        calls = self.plan(children=['/home/example.com/shop', "/home/example.com/it's here"])
        privileged = [command for command, user in calls if user is None]
        for command in privileged:
            words = shlex.split(command)
            self.assertNotIn('chmod', words, command)
            self.assertNotEqual('find', words[0], command)
            if words[0] == 'chown':
                self.assertEqual(['-R', '-P'], words[1:3], command)
        helper = [shlex.split(command) for command in privileged if 'secureDirectoryOwner.py' in command]
        self.assertEqual({'/home/example.com', '/home/example.com/public_html', '/home/example.com/shop',
                          "/home/example.com/it's here"},
                         {words[words.index('--directory') + 1] for words in helper})
        for words in helper:
            root = words[words.index('--allowed-root') + 1]
            self.assertIn(root, ('/home', '/home/example.com'))
            self.assertEqual('examp1234', words[words.index('--user') + 1])

    def test_modes_are_set_by_the_site_user_after_it_owns_the_tree(self):
        calls = self.plan(children=['/home/example.com/shop'])
        for tree in ('/home/example.com/public_html', '/home/example.com/shop'):
            own = calls.index(('chown -R -P examp1234:examp1234 %s' % tree, None))
            modes = [index for index, (command, user) in enumerate(calls)
                     if shlex.split(command)[-1 if command.startswith('chmod') else 1] == tree
                     and shlex.split(command)[0] in ('chmod', 'find')]
            self.assertEqual(3, len(modes), tree)
            for index in modes:
                self.assertGreater(index, own, tree)
                self.assertEqual('examp1234', calls[index][1], calls[index][0])
            final = next(index for index, (command, user) in enumerate(calls)
                         if 'secureDirectoryOwner.py' in command and '--directory %s ' % tree in command)
            self.assertGreater(final, max(modes))
            self.assertIn('--group nogroup --mode 750', calls[final][0])

    def test_document_root_keeps_its_restricted_mode(self):
        commands = [command for command, user in self.plan()]
        self.assertIn('chmod 750 /home/example.com/public_html', commands)
        self.assertIn('find /home/example.com/public_html -mindepth 1 -type d -exec chmod 0755 {} +', commands)
        self.assertIn('find /home/example.com/public_html -type f -exec chmod 0644 {} +', commands)


if __name__ == '__main__':
    unittest.main()
