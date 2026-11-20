"""A website's .ssh directory belongs to the customer: only its own user touches what is in it."""
import ast
import grp
import json
import os
from pathlib import Path
import pwd
import shlex
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

from plogical.fileSystemSecurity import set_file_owner
from plogical.test_child_domain_conversion import load_method

ROOT = Path(__file__).resolve().parents[1]
USER = pwd.getpwuid(os.getuid()).pw_name
GROUP = grp.getgrgid(os.getgid()).gr_name


class FileOwnerTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.home = Path(holder.name, 'home')
        (self.home / '.ssh').mkdir(parents=True)
        self.keys = self.home / '.ssh' / 'authorized_keys'
        self.outside = Path(holder.name, 'passwd')
        self.outside.write_text('root:x:0:0\n')

    def test_plain_key_file_is_accepted(self):
        self.keys.write_text('ssh-ed25519 AAAA key\n')
        set_file_owner(str(self.home), str(self.keys), USER, GROUP)

    def test_link_or_second_name_in_place_of_the_key_file_is_refused(self):
        os.symlink(str(self.outside), str(self.keys))
        with self.assertRaises(OSError):
            set_file_owner(str(self.home), str(self.keys), USER, GROUP)
        self.keys.unlink()
        os.link(str(self.outside), str(self.keys))
        with self.assertRaises(OSError):
            set_file_owner(str(self.home), str(self.keys), USER, GROUP)

    def test_link_in_place_of_the_directory_and_foreign_paths_are_refused(self):
        self.keys.write_text('key\n')
        (self.home / 'real').mkdir()
        (self.home / 'real' / 'authorized_keys').write_text('key\n')
        (self.home / '.ssh' / 'authorized_keys').unlink()
        (self.home / '.ssh').rmdir()
        os.symlink(str(self.home / 'real'), str(self.home / '.ssh'))
        with self.assertRaises(OSError):
            set_file_owner(str(self.home), str(self.keys), USER, GROUP)
        with self.assertRaises(ValueError):
            set_file_owner(str(self.home), str(self.outside), USER, GROUP)

    def test_command_line_helper_changes_a_file_only_as_a_file(self):
        self.keys.write_text('key\n')
        script = str(ROOT / 'plogical' / 'secureDirectoryOwner.py')

        def run(*target):
            return subprocess.run([sys.executable, script, '--allowed-root', str(self.home), '--user', USER,
                                   '--group', GROUP] + list(target), stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, timeout=30).returncode

        self.assertEqual(0, run('--file', str(self.keys)))
        self.assertNotEqual(0, run('--file', str(self.keys), '--mode', '644'))
        self.assertNotEqual(0, run('--file', str(self.home / '.ssh')))
        self.assertNotEqual(0, run('--file', str(self.keys), '--directory', str(self.home)))
        self.keys.unlink()
        os.symlink(str(self.outside), str(self.keys))
        self.assertNotEqual(0, run('--file', str(self.keys)))


class Commands:
    def __init__(self):
        self.calls = []

    def outputExecutioner(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        return '1,None'

    def executioner(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        return 1


class KeyHandlerTests(unittest.TestCase):
    def handler(self, name):
        self.commands = Commands()
        self.written = {}
        self.removed = []
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)

        def fake_open(path, flags, mode=0o777):
            self.written['path'], self.written['flags'], self.written['mode'] = path, flags, mode
            return os.open(os.path.join(holder.name, 'key'), os.O_WRONLY | os.O_CREAT, 0o600)

        fake_os = SimpleNamespace(open=fake_open, fdopen=os.fdopen, chmod=lambda path, mode: None,
                                  remove=self.removed.append, O_WRONLY=os.O_WRONLY, O_CREAT=os.O_CREAT,
                                  O_EXCL=os.O_EXCL, O_NOFOLLOW=os.O_NOFOLLOW, path=os.path)
        website = SimpleNamespace(externalApp='examp1234')
        acl = Mock()
        acl.checkOwnership.return_value = 1
        return load_method('websiteFunctions/website.py', 'WebsiteManager', name, dict(
            ACLManager=acl, Administrator=Mock(), ProcessUtilities=self.commands, json=json, shlex=shlex,
            os=fake_os, Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: website)),
            virtualHostUtilities=SimpleNamespace(cyberPanel='/usr/local/CyberCP'),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode())))

    def test_key_is_added_by_the_site_user_through_a_private_temporary_file(self):
        add = self.handler('addSSHKey')
        result = json.loads(add(None, userID=7, data={'domain': 'example.com',
                                                      'key': 'ssh-ed25519 AAAA me@host'}).content)
        self.assertEqual(1, result['add_status'])
        self.assertEqual([('mkdir -p /home/example.com/.ssh', 'examp1234')], self.commands.calls[:1])
        self.assertRegex(self.written['path'], r'\A/usr/local/CyberCP/tmp/[0-9a-f]{32}\Z')
        self.assertTrue(self.written['flags'] & os.O_EXCL and self.written['flags'] & os.O_NOFOLLOW)
        command, user = self.commands.calls[1]
        self.assertEqual('examp1234', user)
        self.assertEqual(['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/firewallUtilities.py',
                          'addSSHKey', '--tempPath', self.written['path'], '--path',
                          '/home/example.com/.ssh/authorized_keys'], shlex.split(command))
        self.assertEqual([self.written['path']], self.removed)
        self.assertEqual(2, len(self.commands.calls))

    def test_no_command_under_the_sites_home_runs_with_privilege(self):
        add = self.handler('addSSHKey')
        add(None, userID=7, data={'domain': 'example.com', 'key': 'ssh-ed25519 AAAA me@host'})
        for command, user in self.commands.calls:
            self.assertEqual('examp1234', user, command)

    def test_old_root_owned_key_file_is_handed_over_only_as_a_plain_file(self):
        delete = self.handler('deleteSSHKey')
        delete(None, userID=7, data={'domain': 'example.com', 'key': 'ssh-ed25519 AAAA me@host'})
        privileged = [shlex.split(command) for command, user in self.commands.calls if user is None]
        self.assertEqual(1, len(privileged))
        self.assertEqual(['/usr/local/CyberCP/bin/python', '/usr/local/CyberCP/plogical/secureDirectoryOwner.py',
                          '--allowed-root', '/home/example.com', '--file',
                          '/home/example.com/.ssh/authorized_keys', '--user', 'examp1234', '--group',
                          'examp1234'], privileged[0])
        self.assertFalse(any(command.startswith('chown') for command, user in self.commands.calls))


class GitSetupSourceTests(unittest.TestCase):
    def test_git_setup_writes_its_configuration_as_the_site_user(self):
        tree = ast.parse((ROOT / 'websiteFunctions/website.py').read_text())
        cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'WebsiteManager')
        method = next(node for node in cls.body if isinstance(node, ast.FunctionDef) and node.name == 'setupGit')
        source = ast.get_source_segment((ROOT / 'websiteFunctions/website.py').read_text(), method)
        self.assertNotIn("'mv %s /home/%s/.ssh/config'", source)
        self.assertNotIn("/home/cyberpanel/config", source)
        self.assertNotIn("chown %s:%s /home/%s/.ssh/config", source)
        self.assertIn("'cp %s %s' % (shlex.quote(path), shlex.quote('/home/%s/.ssh/config' % self.domain))", source)
        # every command helper call in the routine names the site user
        calls = [node for node in ast.walk(method) if isinstance(node, ast.Call)
                 and isinstance(node.func, ast.Attribute)
                 and node.func.attr in ('executioner', 'outputExecutioner')]
        self.assertTrue(calls)
        for call in calls:
            self.assertEqual(2, len(call.args), ast.dump(call)[:120])

    def test_worker_tolerates_a_temporary_file_it_cannot_remove(self):
        source = (ROOT / 'plogical/firewallUtilities.py').read_text()
        self.assertIn("""                try:
                    os.remove(tempPath)
                except OSError:""", source)


if __name__ == '__main__':
    unittest.main()
