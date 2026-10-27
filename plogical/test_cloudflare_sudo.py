"""Fixed-action policy and fail-closed provisioning without host sudo edits."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from plogical import cloudflareSudo as cf
from plogical import gdriveSudo as shared


class CloudflarePolicyTests(unittest.TestCase):
    def test_policy_only_grants_the_two_exact_isolated_actions(self):
        text=cf.policy()
        prefix='/usr/local/CyberPanel/bin/python -I -S /usr/local/CyberCP/plogical/cloudflareCredentials.py'
        self.assertIn(' = '+prefix+' metadata, '+prefix+' save\n',text)
        self.assertNotIn('*',text)
        self.assertIn('env_reset, !setenv',text)
        self.assertIn('cyberpanel ALL=(root) NOPASSWD: NOSETENV:',text)
        self.assertIn('lscpd ALL=(root) NOPASSWD: NOSETENV:',text)
        for path in ('install/install.py','plogical/upgrade.py'):
            source=(Path(__file__).parents[1]/path).read_text()
            self.assertLess(source.index('provision_gdrive_sudo()'),source.index('provision_cloudflare_sudo()'))

    def test_gdrive_policy_bytes_unchanged(self):
        expected=('# Managed by CyberPanel: isolated Google Drive management.\n'
                  'Cmnd_Alias CYBERPANEL_GDRIVE = /usr/local/CyberPanel/bin/python -I -S /usr/local/CyberCP/plogical/gdriveConfig.py\n'
                  'Defaults!CYBERPANEL_GDRIVE env_reset, !setenv, secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"\n'
                  'lscpd ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_GDRIVE\n'
                  'cyberpanel ALL=(root) NOPASSWD: NOSETENV: CYBERPANEL_GDRIVE\n')
        self.assertEqual(shared.policy(),expected)

    def test_provisioning_calls_fixed_policy(self):
        with patch.object(cf,'provision_fixed') as provision:
            cf.provision()
        provision.assert_called_once_with(cf.PYTHON,cf.HELPER,cf.TARGET,cf.policy())

    def exercise(self,existing=None,fail_call=None):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);directory=root/'sudoers.d';directory.mkdir()
            sudoers=root/'sudoers';sudoers.write_text('@includedir /etc/sudoers.d\n')
            python=root/'python';python.write_text('python');python.chmod(0o755)
            helper=root/'helper';helper.write_text('helper')
            visudo=root/'visudo';visudo.write_text('visudo');visudo.chmod(0o755)
            target=directory/'fixture-policy';content=cf.policy()
            if existing is not None:target.write_text(existing)
            calls=[]
            def run(*args,**kwargs):
                calls.append(args)
                if len(calls)==fail_call:raise subprocess.CalledProcessError(1,args[0])
            with patch.object(shared,'DIRECTORY',directory),patch.object(shared,'SUDOERS',sudoers),patch.object(shared,'VISUDO',visudo),patch.object(shared,'trusted_path') as trusted,patch.object(shared.os,'geteuid',return_value=0),patch.object(shared.os,'fchown'),patch.object(shared.subprocess,'run',side_effect=run):
                if existing is not None and existing!=content:
                    with self.assertRaisesRegex(RuntimeError,'unmanaged'):shared.provision_fixed(python,helper,target,content)
                elif fail_call:
                    with self.assertRaises(subprocess.CalledProcessError):shared.provision_fixed(python,helper,target,content)
                else:
                    shared.provision_fixed(python,helper,target,content)
                    self.assertEqual(target.stat().st_mode & 0o777,0o440)
                    self.assertEqual(target.read_text(),content)
                for dependency in (python,helper,visudo,sudoers):self.assertIn(((dependency,),),[(call.args,) for call in trusted.call_args_list])
            if fail_call or (existing is not None and existing!=content):
                self.assertEqual(target.read_text() if target.exists() else None,existing)
            self.assertFalse(list(directory.glob('.*')))

    def test_success_and_idempotence(self):
        self.exercise();self.exercise(existing=cf.policy())

    def test_unmanaged_policy_refused(self):self.exercise(existing='# unrelated administrator policy\n')

    def test_failed_candidate_validation_preserves_existing(self):self.exercise(existing=cf.policy(),fail_call=2)

    def test_failed_global_validation_removes_new_policy(self):self.exercise(fail_call=3)

    def test_failed_global_validation_restores_existing(self):self.exercise(existing=cf.policy(),fail_call=3)

    def test_unprivileged_provisioning_refused(self):
        with patch.object(shared.os,'geteuid',return_value=1000),self.assertRaisesRegex(RuntimeError,'as root'):
            shared.provision_fixed(cf.PYTHON,cf.HELPER,cf.TARGET,cf.policy())

    def test_inactive_or_outside_target_refused(self):
        for target in ('/tmp/policy','/etc/sudoers.d/policy.bak','/etc/sudoers.d/policy~'):
            with self.assertRaises(RuntimeError):shared.provision_fixed(cf.PYTHON,cf.HELPER,target,cf.policy())

if __name__=='__main__':unittest.main()
