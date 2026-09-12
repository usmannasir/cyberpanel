"""Exercise real upgrade shell helpers with fake runtimes and no network access."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SOURCE = (ROOT / 'cyberpanel_upgrade.sh').read_text()


class UpgradeRuntimeRequirementsTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='upgrade-runtime-test-')
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.commands = self.root / 'commands'
        self.commands.mkdir()
        self.runtime = self.root / 'runtime/bin/python'
        self.system_runtime = self.root / 'system/python'
        self.requirements = self.root / 'requirements.txt'
        self.requirements.write_text('Django==4.2.14\ndocker==7.1.0\ncloudflare==2.20.0\n')
        self.trace = self.root / 'trace'
        self.trace.write_text('')
        self.log = self.root / 'upgrade.log'
        self.count = self.root / 'pip-count'
        self.environment = dict(os.environ, PATH=str(self.commands)+':/usr/bin:/bin',
                                PYTHONHOME='/wrong-runtime', PYTHONPATH='/wrong-packages',
                                AUDIT_TRACE=str(self.trace), AUDIT_COUNT=str(self.count),
                                CyberPanel_Python=str(self.system_runtime),
                                Server_OS_Version='26', Git_Content_URL='https://invalid.example',
                                Branch_Name='v3.0.6')
        fake_python = '''#!/bin/sh
printf '%s|%s|%s|%s\n' "$0" "$*" "${PYTHONHOME-unset}" "${PYTHONPATH-unset}" >> "$AUDIT_TRACE"
case "$*" in
  '-m pip --version') exit "${FAKE_PIP_MISSING:-0}" ;;
  '-m ensurepip --upgrade') exit "${FAKE_ENSUREPIP_EXIT:-0}" ;;
  *'install --upgrade'*) exit "${FAKE_BOOTSTRAP_EXIT:-0}" ;;
  *'--ignore-installed'*)
    count=0
    if [ -f "$AUDIT_COUNT" ]; then read count < "$AUDIT_COUNT"; fi
    count=$((count + 1)); printf '%s\n' "$count" > "$AUDIT_COUNT"
    if [ "${FAKE_FAIL_FIRST_INSTALL:-0}" = 1 ] && [ "$count" = 1 ]; then exit 41; fi
    exit "${FAKE_INSTALL_EXIT:-0}" ;;
  *'get_version()'*) printf '%s\n' "${FAKE_DJANGO:-4.2.14}"; exit "${FAKE_VERSION_EXIT:-0}" ;;
  *'import '*) exit "${FAKE_IMPORT_EXIT:-0}" ;;
  *'./configure.py'*) exit "${FAKE_CONFIGURE_EXIT:-0}" ;;
esac
exit 99
'''
        self.executable(self.runtime, fake_python)
        self.executable(self.system_runtime, fake_python)
        for name in ('python3', 'pip', 'pip3'):
            self.executable(self.commands/name, '#!/bin/sh\nprintf "WRONG-PATH-COMMAND\\n" >> "$AUDIT_TRACE"\nexit 99\n')
        self.executable(self.commands/'sleep', '#!/bin/sh\nexit 0\n')
        self.executable(self.commands/'curl', '#!/bin/sh\nprintf "%s" "${FAKE_HTTP_CODE:-200}"\n')
        self.executable(self.commands/'wget', '''#!/bin/sh
printf 'wget %s\n' "$*" >> "$AUDIT_TRACE"
output=''
while [ "$#" -gt 0 ]; do
  if [ "$1" = '-O' ]; then shift; output="$1"; fi
  shift
done
if [ "${FAKE_DOWNLOAD_INVALID:-0}" = 1 ]; then printf 'invalid response\n' > "$output";
else printf 'Django==4.2.14\n' > "$output"; fi
exit "${FAKE_DOWNLOAD_EXIT:-0}"
''')
        self.executable(self.commands/'tar', '''#!/bin/sh
if [ "${FAKE_TAR_EXIT:-0}" != 0 ]; then exit "$FAKE_TAR_EXIT"; fi
mkdir wsgi-lsapi-2.1
printf 'fixture\n' > wsgi-lsapi-2.1/configure.py
''')
        self.executable(self.commands/'make', '''#!/bin/sh
if [ "${FAKE_MAKE_EXIT:-0}" != 0 ]; then exit "$FAKE_MAKE_EXIT"; fi
if [ "${FAKE_EMPTY_BINARY:-0}" = 1 ]; then : > lswsgi;
else printf '#!/bin/sh\nexit 0\n' > lswsgi; fi
chmod 755 lswsgi
''')

    @staticmethod
    def executable(path, text):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        path.chmod(0o755)

    def function(self, name):
        start = SOURCE.index(name+'() {')
        end = SOURCE.index('\n}\n', start)+3
        result = SOURCE[start:end].replace('/var/log/cyberpanel_upgrade_debug.log', str(self.log))
        result = result.replace('/tmp/cyberpanel-lswsgi.XXXXXX', str(self.root/'build.XXXXXX'))
        return result

    def run_shell(self, code, **environment):
        definitions = '\n'.join(self.function(name) for name in (
            'Run_Upgrade_Command', 'Validate_Python_Requirements',
            'Install_Panel_Runtime_Requirements', 'Install_CyberCP_Runtime_Python_Requirements',
            'Download_Requirement', 'Build_Panel_LSWSGI'))
        env = dict(self.environment)
        env.update({key:str(value) for key,value in environment.items()})
        return subprocess.run(['/bin/bash', '-c', definitions+'\n'+code],
                              env=env, text=True, capture_output=True, timeout=15)

    def install_panel(self, **environment):
        return self.run_shell('Install_Panel_Runtime_Requirements %s %s' %
                              (shlex.quote(str(self.runtime)), shlex.quote(str(self.requirements))), **environment)

    def install_system(self, **environment):
        return self.run_shell('Install_CyberCP_Runtime_Python_Requirements '+shlex.quote(str(self.requirements)), **environment)

    def test_logged_command_keeps_failure_status_after_successful_tee(self):
        result = self.run_shell("Run_Upgrade_Command /bin/sh -c 'exit 37'")
        self.assertEqual(37, result.returncode)

    def test_log_write_failure_cannot_become_success(self):
        self.executable(self.commands/'tee', '#!/bin/sh\ncat >/dev/null\nexit 23\n')
        self.assertNotEqual(0, self.run_shell('Run_Upgrade_Command /bin/true').returncode)

    def test_panel_uses_its_interpreter_and_clears_ambient_python_environment(self):
        for operating_system in ('Ubuntu', 'CentOS', 'openEuler'):
            with self.subTest(operating_system=operating_system):
                self.assertEqual(0, self.install_panel(Server_OS=operating_system).returncode)
        lines = self.trace.read_text().splitlines()
        self.assertTrue(lines)
        self.assertTrue(all(line.startswith(str(self.runtime)+'|') for line in lines))
        self.assertTrue(all(line.endswith('|unset|unset') for line in lines))
        self.assertNotIn('WRONG-PATH-COMMAND', self.trace.read_text())

    def test_panel_install_failure_is_nonzero_after_bounded_retry(self):
        self.assertNotEqual(0, self.install_panel(FAKE_INSTALL_EXIT=41).returncode)
        self.assertEqual('2', self.count.read_text().strip())

    def test_panel_recovers_only_after_verified_retry(self):
        self.assertEqual(0, self.install_panel(FAKE_FAIL_FIRST_INSTALL=1).returncode)
        self.assertEqual('2', self.count.read_text().strip())

    def test_panel_bootstrap_version_and_import_failures_are_nonzero(self):
        for scenario in ({'FAKE_BOOTSTRAP_EXIT':11}, {'FAKE_DJANGO':'3.1.3'},
                         {'FAKE_IMPORT_EXIT':7}, {'FAKE_VERSION_EXIT':8}):
            with self.subTest(scenario=scenario):
                self.assertNotEqual(0, self.install_panel(**scenario).returncode)

    def test_missing_interpreter_or_requirements_precedes_any_pip_call(self):
        self.runtime.unlink()
        self.assertNotEqual(0, self.install_panel().returncode)
        self.assertEqual('', self.trace.read_text())
        self.requirements.unlink()
        self.assertNotEqual(0, self.install_system().returncode)
        self.assertEqual('', self.trace.read_text())

    def test_system_runtime_uses_selected_python_not_activated_path(self):
        self.assertEqual(0, self.install_system().returncode)
        lines = self.trace.read_text().splitlines()
        self.assertTrue(all(line.startswith(str(self.system_runtime)+'|') for line in lines))
        self.assertTrue(any(line.endswith('|/usr|') for line in lines))
        self.assertNotIn('WRONG-PATH-COMMAND', self.trace.read_text())

    def test_system_install_and_validation_failures_are_nonzero(self):
        for scenario in ({'FAKE_INSTALL_EXIT':29}, {'FAKE_IMPORT_EXIT':7},
                         {'FAKE_DJANGO':'3.1.3'}, {'FAKE_VERSION_EXIT':8}, {'FAKE_PIP_MISSING':1},
                         {'FAKE_PIP_MISSING':1,'FAKE_ENSUREPIP_EXIT':8},
                         {'FAKE_BOOTSTRAP_EXIT':9}):
            with self.subTest(scenario=scenario):
                self.assertNotEqual(0, self.install_system(**scenario).returncode)

    def test_system_pep_retry_preserves_final_status(self):
        self.assertEqual(0, self.install_system(FAKE_FAIL_FIRST_INSTALL=1).returncode)
        self.assertEqual('2', self.count.read_text().strip())
        self.assertIn('--break-system-packages -r', self.trace.read_text())

    def test_download_validates_exit_and_payload_and_preserves_existing_file(self):
        original=self.requirements.read_text()
        for scenario in ({'FAKE_DOWNLOAD_EXIT':18}, {'FAKE_DOWNLOAD_INVALID':1}):
            with self.subTest(scenario=scenario):
                result=self.run_shell('Download_Requirement '+shlex.quote(str(self.requirements)), **scenario)
                self.assertNotEqual(0,result.returncode)
                self.assertEqual(original,self.requirements.read_text())
                self.assertEqual([],list(self.root.glob('requirements.txt.download.*')))

    def test_download_uses_requested_branch_and_os_requirements(self):
        for version,name in (('26','requirments.txt'),('24','requirments.txt'),
                             ('9','requirments.txt'),('8','requirments-old.txt')):
            with self.subTest(version=version):
                self.trace.write_text('')
                result=self.run_shell('Download_Requirement '+shlex.quote(str(self.requirements)), Server_OS_Version=version)
                self.assertEqual(0,result.returncode)
                self.assertIn('https://invalid.example/v3.0.6/'+name,self.trace.read_text())
                self.assertEqual('Django==4.2.14\n',self.requirements.read_text())

    def test_failed_wsgi_stages_preserve_existing_binary(self):
        destination=self.root/'lswsgi'
        destination.write_bytes(b'existing binary')
        destination.chmod(0o755)
        for scenario in ({'FAKE_DOWNLOAD_EXIT':8},{'FAKE_TAR_EXIT':9},
                         {'FAKE_CONFIGURE_EXIT':10},{'FAKE_MAKE_EXIT':11},
                         {'FAKE_EMPTY_BINARY':1}):
            with self.subTest(scenario=scenario):
                result=self.run_shell('Build_Panel_LSWSGI %s %s' %
                    (shlex.quote(str(self.runtime)),shlex.quote(str(destination))),**scenario)
                self.assertNotEqual(0,result.returncode)
                self.assertEqual(b'existing binary',destination.read_bytes())
                self.assertEqual([],list(self.root.glob('lswsgi.upgrade.*')))
                self.assertEqual([],list(self.root.glob('build.*')))

    def test_successful_wsgi_build_installs_verified_nonempty_executable(self):
        destination=self.root/'lswsgi'
        destination.write_bytes(b'existing binary')
        result=self.run_shell('Build_Panel_LSWSGI %s %s' %
                             (shlex.quote(str(self.runtime)),shlex.quote(str(destination))))
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertTrue(destination.read_bytes().startswith(b'#!/bin/sh'))
        self.assertTrue(os.access(str(destination),os.X_OK))
        self.assertEqual([],list(self.root.glob('build.*')))

    def test_main_runtime_failures_survive_later_successful_repair_steps(self):
        main=self.function('Main_Upgrade')
        start=main.index('echo -e "[$(date',main.index('rm -f /usr/local/requirments.txt'))
        tail=main[start:]
        tail=tail.replace('/usr/local/CyberCP/bin/python',str(self.runtime)).replace('/usr/local/CyberCP/bin/lswsgi',str(self.root/'lswsgi')).replace('/usr/local/requirments.txt',str(self.requirements))
        self.executable(self.root/'lswsgi','#!/bin/sh\nexit 0\n')
        for stage in ('DOWNLOAD','INSTALL','BUILD','VALIDATE'):
            with self.subTest(stage=stage):
                code='''
Download_Requirement() { return "${FAIL_DOWNLOAD:-0}"; }
Install_Panel_Runtime_Requirements() { return "${FAIL_INSTALL:-0}"; }
Build_Panel_LSWSGI() { return "${FAIL_BUILD:-0}"; }
Validate_Python_Requirements() { return "${FAIL_VALIDATE:-0}"; }
Main_Upgrade() {
'''+tail+'\nUPGRADE_FAILED=0\nMain_Upgrade\n'
                result=self.run_shell(code,**{'FAIL_'+stage:1})
                self.assertNotEqual(0,result.returncode)
                self.assertNotIn('All components successfully installed',result.stdout)

    def test_failure_banner_cannot_claim_success_even_when_panel_answers(self):
        banner=self.function('Post_Install_Display_Final_Info')
        bind=self.root/'bind.conf';bind.write_text('8090\n')
        banner=banner.replace('/usr/local/lscp/conf/bind.conf',str(bind)).replace('/root/cyberpanel_upgrade_tmp',str(self.root/'unused-upgrade-temp'))
        for failed,http in ((1,200),(0,500)):
            with self.subTest(failed=failed,http=http):
                result=self.run_shell(banner+'\nUPGRADE_FAILED=%s\nPost_Install_Display_Final_Info\n'%failed,FAKE_HTTP_CODE=http)
                self.assertNotEqual(0,result.returncode)
                self.assertNotIn('CyberPanel Upgraded',result.stdout)
                self.assertNotIn('runtime was restored',result.stdout)

    def test_main_callers_preserve_failed_upgrade_or_system_restart(self):
        banner=self.function('Post_Install_Display_Final_Info')
        bind=self.root/'bind.conf';bind.write_text('8090\n')
        banner=banner.replace('/usr/local/lscp/conf/bind.conf',str(bind)).replace('/root/cyberpanel_upgrade_tmp',str(self.root/'unused-upgrade-temp'))
        tail=SOURCE[SOURCE.rindex('\nif ! Main_Upgrade; then'):]
        for main,system in ((1,0),(0,1),(0,0)):
            with self.subTest(main=main,system=system):
                code=banner+'''
Main_Upgrade() { return "$FAKE_MAIN_EXIT"; }
Post_Upgrade_System_Tweak() { return "$FAKE_SYSTEM_EXIT"; }
Restart_Web_Terminal() { :; }
UPGRADE_FAILED=0
'''+tail
                result=self.run_shell(code,FAKE_MAIN_EXIT=main,FAKE_SYSTEM_EXIT=system)
                self.assertEqual(bool(main or system),result.returncode != 0)
                self.assertEqual(not bool(main or system),'CyberPanel Upgraded' in result.stdout)

    def test_system_callers_reject_stale_requirements_and_preserve_failures(self):
        post=self.function('Post_Upgrade_System_Tweak')
        cache_start=post.index('mkdir -p /etc/cyberpanel\nlocal runtime_requirements_ready=0')
        cache_end=post.index('rm -f /usr/local/requirments.txt',cache_start)+len('rm -f /usr/local/requirments.txt')
        calls_start=post.index('if [[ "$Server_OS_Version" = "9" ]] || [[ "$Server_OS_Version" = "10" ]] || [[ "$Server_OS_Version" = "18" ]]')
        calls_end=post.index('# Keep private data from retired',calls_start)
        selected=post[cache_start:cache_end]+'\n'+post[calls_start:calls_end]
        cache_directory=self.root/'configuration'
        cache_directory.mkdir()
        cached=cache_directory/'cyberpanel-requirments-runtime.txt'
        python_environment=self.root/'pythonenv.conf'
        python_environment.write_text('PYTHONHOME=/usr\n')
        selected=selected.replace('/etc/cyberpanel',str(cache_directory)).replace('/usr/local/requirments.txt',str(self.requirements)).replace('/usr/local/lscp/conf/pythonenv.conf',str(python_environment))
        for scenario in ({'missing_current':True}, {'FAKE_SYSTEM_EXIT':12},
                         {'FAKE_ENVIRONMENT_EXIT':13},
                         {'Server_OS_Version':'26','FAKE_VALIDATE_EXIT':1,'FAKE_SYSTEM_EXIT':14}, {}):
            with self.subTest(scenario=scenario):
                cached.write_text('Django==3.1.3\n')
                self.trace.write_text('')
                if scenario.get('missing_current'):
                    self.requirements.unlink(missing_ok=True)
                else:
                    self.requirements.write_text('Django==4.2.14\n')
                code='''
Configure_LSCPD_Python_Environment() { return "${FAKE_ENVIRONMENT_EXIT:-0}"; }
Install_CyberCP_Runtime_Python_Requirements() {
  printf 'system-helper-called\n' >> "$AUDIT_TRACE"
  return "${FAKE_SYSTEM_EXIT:-0}"
}
Validate_Python_Requirements() { return "${FAKE_VALIDATE_EXIT:-0}"; }
Check_System_Runtime() {
'''+selected+'\n[[ "$UPGRADE_FAILED" -eq 0 ]]\n}\nUPGRADE_FAILED=0\nCheck_System_Runtime\n'
                overrides=dict(scenario)
                overrides.pop('missing_current',None)
                overrides.setdefault('Server_OS_Version','24')
                result=self.run_shell(code,**overrides)
                self.assertEqual(bool(scenario),result.returncode != 0)
                if scenario.get('missing_current'):
                    self.assertNotIn('system-helper-called',self.trace.read_text())
                    self.assertEqual('Django==3.1.3\n',cached.read_text())
                else:
                    self.assertEqual('Django==4.2.14\n',cached.read_text())


if __name__ == '__main__':
    unittest.main()
