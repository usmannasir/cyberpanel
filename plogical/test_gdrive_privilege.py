"""Privilege boundary tests use synthetic identities and never run a root write."""
import io
import json
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock
from plogical import gdriveConfig as config
from plogical import gdriveSudo as policy


class PrivilegeTests(unittest.TestCase):
    def setUp(self):
        self.data = {'user':'siteuser', 'home':'/home/site.example', 'account':'qa', 'credentials':{}}
        self.owner = SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/home/site.example')

    def invoke(self, data=None, owner=None, home_mode=0o40755, home_uid=1234):
        calls=[]
        info = lambda path: SimpleNamespace(st_mode=home_mode if str(path)==self.data['home'] else 0o40755,
                                           st_uid=home_uid if str(path)==self.data['home'] else 0)
        with mock.patch.object(config.pwd,'getpwnam',return_value=owner or self.owner), \
                mock.patch.object(Path,'lstat',info), \
                mock.patch.object(config.os,'getuid',side_effect=[0,1234]), \
                mock.patch.object(config.os,'geteuid',side_effect=[0,1234]), \
                mock.patch.object(config.os,'getgid',return_value=1234), \
                mock.patch.object(config.os,'getegid',return_value=1234), \
                mock.patch.object(config.os,'setgroups',side_effect=lambda v:calls.append(('groups',v))), \
                mock.patch.object(config.os,'setgid',side_effect=lambda v:calls.append(('gid',v))), \
                mock.patch.object(config.os,'setuid',side_effect=lambda v:calls.append(('uid',v))), \
                mock.patch.object(config,'write_remote',side_effect=lambda *v:calls.append(('write',v))):
            config.install_for_website(data or self.data)
        return calls

    def test_privilege_drop_precedes_writer(self):
        self.assertEqual([c[0] for c in self.invoke()],['groups','gid','uid','write'])

    def test_system_identity_and_home_mismatch_rejected(self):
        for user in ('root','cyberpanel','lscpd','nobody','bad/user'):
            with self.subTest(user=user), self.assertRaises(ValueError):
                self.invoke(dict(self.data,user=user))
        for owner in (SimpleNamespace(pw_uid=0,pw_gid=1234,pw_dir=self.owner.pw_dir),
                      SimpleNamespace(pw_uid=999,pw_gid=1234,pw_dir=self.owner.pw_dir),
                      SimpleNamespace(pw_uid=1234,pw_gid=0,pw_dir=self.owner.pw_dir),
                      SimpleNamespace(pw_uid=1234,pw_gid=1234,pw_dir='/root')):
            with self.assertRaises(ValueError): self.invoke(owner=owner)

    def test_unsafe_home_rejected(self):
        for home in ('/root','/home/mysql','/home/../root','/home/a.example/sub'):
            with self.subTest(home=home), self.assertRaises(ValueError): self.invoke(dict(self.data,home=home))
        for mode,uid in ((0o120777,1234),(0o40777,1234),(0o40755,0)):
            with self.assertRaises(ValueError): self.invoke(home_mode=mode,home_uid=uid)

    def test_cli_rejects_extra_args_oversize_duplicate_without_dispatch(self):
        for args, raw in ((['helper','--home','/root'],b'{}'), (['helper'],b'x'*32769),
                          (['helper'],b'{"user":"a","user":"b"}')):
            with mock.patch.object(config.sys,'argv',args), \
                 mock.patch.object(config.sys,'stdin',SimpleNamespace(buffer=io.BytesIO(raw))), \
                 mock.patch.object(config.sys,'stderr',io.StringIO()), \
                 mock.patch.object(config,'install_for_website') as dispatch:
                self.assertEqual(config.main(),1)
                dispatch.assert_not_called()

    def test_policy_is_exact_isolated_command(self):
        content=policy.policy()
        self.assertIn('CYBERPANEL_GDRIVE = /usr/local/CyberPanel/bin/python -I -S /usr/local/CyberCP/plogical/gdriveConfig.py\n',content)
        self.assertNotIn('*',content)
        self.assertIn('NOSETENV',content)
        for name in ('install/install.py','plogical/upgrade.py'):
            source=(Path(__file__).resolve().parents[1]/name).read_text()
            self.assertIn('provision_gdrive_sudo()',source)

if __name__=='__main__': unittest.main()
