"""Ubuntu 20 must select a complete, separately pinned compatible release."""
import builtins
import ast
import os
import unittest
from pathlib import Path
from unittest import mock

from install.test_custom_ols_platforms import binary_configs, load_method


ROOT = Path(__file__).resolve().parents[1]
CASES = ((ROOT/'install/installCyberPanel.py', 'InstallCyberPanel', False),
         (ROOT/'plogical/upgrade.py', 'Upgrade', True))


class Ubuntu20ReleaseTests(unittest.TestCase):
    def select(self, path, name, static, version):
        detect = load_method(path, name, 'detectPlatform')
        release = 'DISTRIB_ID=Ubuntu\nDISTRIB_RELEASE='+version+'\n'
        with mock.patch.object(os.path, 'exists', side_effect=lambda p:p=='/etc/lsb-release'), \
             mock.patch.object(builtins, 'open', mock.mock_open(read_data=release)):
            return detect() if static else detect(type('Target', (), {})())

    def test_focal_uses_its_own_explicit_platform(self):
        for path,name,static in CASES:
            with self.subTest(entrypoint=name):
                self.assertEqual(self.select(path,name,static,'20.04'),'ubuntu20')

    def test_older_ubuntu_is_not_silently_admitted(self):
        for path,name,static in CASES:
            with self.subTest(entrypoint=name):
                self.assertEqual(self.select(path,name,static,'18.04'),'skip')

    def test_newer_ubuntu_routing_is_preserved(self):
        for path,name,static in CASES:
            for version,expected in [('22.04','ubuntu'),('24.04','ubuntu'),('26.04','ubuntu26')]:
                with self.subTest(entrypoint=name,version=version):
                    self.assertEqual(self.select(path,name,static,version),expected)

    def test_both_entrypoints_pin_the_same_complete_focal_tuple(self):
        installed=[]
        for path,name,_ in CASES:
            with self.subTest(entrypoint=name):
                config=binary_configs(path,name)['ubuntu20']
                expected={'url':'openlitespeed-2.5.7-x86_64-ubuntu20',
                          'module_url':'cyberpanel_ols-2.7.7-x86_64-ubuntu20.so',
                          'modsec_url':'mod_security-2.5.6-x86_64-ubuntu20.so'}
                for key,filename in expected.items():
                    self.assertEqual(config[key],'https://cyberpanel.net/'+filename)
                self.assertEqual(set(config['sha256']),{'binary','module','modsec'})
                for digest in config['sha256'].values():self.assertRegex(digest,r'^[0-9a-f]{64}$')
                self.assertNotEqual(config,binary_configs(path,name)['ubuntu'])
                installed.append(config)
        self.assertEqual(len(installed),2)
        self.assertEqual(installed[0],installed[1])

    def test_modsecurity_management_keeps_the_same_focal_core_and_module(self):
        path=ROOT/'plogical/modSec.py'
        detect=load_method(path,'modSec','detectPlatform')
        for version,expected in [('20.04','ubuntu20'),('18.04',None),('20.10',None)]:
            with mock.patch.object(builtins,'open',mock.mock_open(read_data='ID=ubuntu\nVERSION_ID='+version+'\n')):
                self.assertEqual(detect(),expected)
        klass=next(n for n in ast.parse(path.read_text(encoding='utf-8')).body if isinstance(n,ast.ClassDef) and n.name=='modSec')
        assignment=next(n for n in klass.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='MODSEC_COMPATIBLE' for t in n.targets))
        module=ast.literal_eval(assignment.value)['ubuntu20']
        core=binary_configs(CASES[0][0],CASES[0][1])['ubuntu20']
        self.assertEqual(module['url'],core['modsec_url'])
        self.assertEqual(module['sha256'],core['sha256']['modsec'])
        self.assertEqual(module['core_sha256'],core['sha256']['binary'])


if __name__=='__main__':unittest.main()
