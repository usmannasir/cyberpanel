"""A website's .ssh directory belongs to the customer: only its own user touches what is in it."""
import ast
import base64
import grp
import json
import os
from pathlib import Path
import pwd
import shlex
import struct
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from plogical.fileSystemSecurity import set_file_owner
from plogical.sshKeyUtilities import parse_authorized_key, with_authorized_key, without_authorized_key
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


def key_line(seed=1, comment='qa@probe'):
    """A well-formed ed25519 public key line."""
    blob = struct.pack('>I', 11) + b'ssh-ed25519' + struct.pack('>I', 32) + bytes([seed]) * 32
    return 'ssh-ed25519 %s %s' % (base64.b64encode(blob).decode(), comment)


class KeyContentTests(unittest.TestCase):
    def test_new_key_is_appended_once(self):
        addition = with_authorized_key('', key_line())
        self.assertEqual('#Created by CyberPanel\n#Added by CyberPanel\n%s\n' % key_line(), addition)
        self.assertEqual('', with_authorized_key(addition, key_line()))
        self.assertEqual('', with_authorized_key(addition, key_line(comment='other@host')))
        more = with_authorized_key(addition.rstrip('\n'), key_line(seed=2))
        self.assertEqual('\n#Added by CyberPanel\n%s\n' % key_line(seed=2), more)

    def test_only_one_well_formed_key_on_one_line_is_accepted(self):
        for value in ('not a key', 'ssh-ed25519 AAAA me@host', key_line() + '\n' + key_line(seed=2),
                      key_line() + '\rcommand="x" ' + key_line(seed=2), '', None, 7, ['ssh-ed25519']):
            self.assertIsNone(with_authorized_key('', value), repr(value))

    def test_one_key_is_removed_by_its_identifier_and_the_rest_kept(self):
        first, second = key_line(), key_line(seed=2, comment='other@host')
        content = '#Created by CyberPanel\n%s\n#note\n%s\n' % (first, second)
        identifier = parse_authorized_key(first)['keyId']
        self.assertEqual('#Created by CyberPanel\n#note\n%s\n' % second,
                         without_authorized_key(content, identifier))
        self.assertIsNone(without_authorized_key('#Created by CyberPanel\n%s\n' % second, identifier))
        for value in ('', 'latest', identifier.upper(), identifier + 'a', None, 7):
            self.assertIsNone(without_authorized_key(content, value), repr(value))


class SiteAccount:
    """Stands in for the command helper: a key file that only the site user changes."""

    def __init__(self, content=None):
        self.content = content
        self.calls = []

    def outputExecutioner(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        words = shlex.split(command)
        if words[0] == 'cat':
            return self.content if self.content is not None else 'cat: %s: No such file or directory' % words[1]
        return ''

    def executioner(self, command, user=None, *arguments, **options):
        self.calls.append((command, user))
        words = shlex.split(command)
        if user == 'examp1234' and words[0] == 'dd':
            self.content = (self.content or '') + Path(words[1][len('if='):]).read_text()
        if user == 'examp1234' and words[0] == 'cp':
            self.content = Path(words[1]).read_text()
        return 1


class KeyHandlerTests(unittest.TestCase):
    def setUp(self):
        holder = tempfile.TemporaryDirectory()
        self.addCleanup(holder.cleanup)
        self.temporary = Path(holder.name)
        shared = patch('plogical.fileSystemSecurity.SHARED_TEMP_DIRECTORY', holder.name)
        shared.start()
        self.addCleanup(shared.stop)

    def manager(self, account):
        website = SimpleNamespace(externalApp='examp1234')
        acl = Mock()
        acl.checkOwnership.return_value = 1
        namespace = dict(
            ACLManager=acl, Administrator=Mock(), ProcessUtilities=account, json=json, shlex=shlex, os=os,
            Websites=SimpleNamespace(objects=SimpleNamespace(get=lambda **kwargs: website)),
            HttpResponse=lambda content: SimpleNamespace(content=content.encode()))
        methods = {name: load_method('websiteFunctions/website.py', 'WebsiteManager', name, namespace)
                   for name in ('addSSHKey', 'deleteSSHKey', 'handOverSiteKeyFile', 'readSiteKeyFile')}
        manager = SimpleNamespace()
        manager.handOverSiteKeyFile = lambda domain, user: methods['handOverSiteKeyFile'](manager, domain, user)
        manager.readSiteKeyFile = lambda path, user: methods['readSiteKeyFile'](manager, path, user)
        manager.add = lambda key: json.loads(methods['addSSHKey'](
            manager, userID=7, data={'domain': 'example.com', 'key': key}).content)
        manager.delete = lambda key: json.loads(methods['deleteSSHKey'](
            manager, userID=7, data={'domain': 'example.com', 'key': key}).content)
        return manager

    def test_key_is_added_by_the_site_user_and_listed_once(self):
        account = SiteAccount()
        manager = self.manager(account)
        self.assertEqual(1, manager.add(key_line())['add_status'])
        self.assertEqual('#Created by CyberPanel\n#Added by CyberPanel\n%s\n' % key_line(), account.content)
        self.assertEqual(1, manager.add(key_line())['add_status'])
        self.assertEqual(1, account.content.count(key_line()))
        self.assertEqual([], list(self.temporary.iterdir()))

    def test_value_that_is_not_a_public_key_is_refused_and_writes_nothing(self):
        account = SiteAccount(content='existing\n')
        result = self.manager(account).add('command="x" not a key')
        self.assertEqual(0, result['add_status'])
        self.assertEqual('existing\n', account.content)
        self.assertFalse(any(command.startswith(('dd ', 'cp ')) for command, user in account.calls))

    def test_key_is_deleted_by_the_site_user_and_other_keys_stay(self):
        other = key_line(seed=2, comment='other@host')
        account = SiteAccount(content='%s\n%s\n' % (key_line(), other))
        manager = self.manager(account)
        identifier = parse_authorized_key(key_line())['keyId']
        self.assertEqual(1, manager.delete(identifier)['delete_status'])
        self.assertEqual(other + '\n', account.content)
        self.assertEqual(0, manager.delete(identifier)['delete_status'])
        self.assertEqual([], list(self.temporary.iterdir()))

    def test_change_that_did_not_reach_the_file_is_not_reported_as_done(self):
        account = SiteAccount()
        account.executioner = lambda command, user=None, *a, **k: account.calls.append((command, user)) or 0
        self.assertEqual(0, self.manager(account).add(key_line())['add_status'])

    def test_only_the_checked_handover_runs_with_privilege(self):
        account = SiteAccount(content=key_line() + '\n')
        manager = self.manager(account)
        manager.add(key_line(seed=3))
        manager.delete(parse_authorized_key(key_line())['keyId'])
        privileged = {command for command, user in account.calls if user is None}
        self.assertEqual({'/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/secureDirectoryOwner.py'
                          ' --allowed-root /home/example.com --file /home/example.com/.ssh/authorized_keys'
                          ' --user examp1234 --group examp1234'}, privileged)
        for command, user in account.calls:
            if user is not None:
                self.assertEqual('examp1234', user)
            self.assertNotIn('firewallUtilities.py', command)


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
