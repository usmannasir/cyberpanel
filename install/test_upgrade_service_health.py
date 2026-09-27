"""Exercise service preflight and final health checks without touching services."""
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

SOURCE = (Path(__file__).resolve().parents[1]/'cyberpanel_upgrade.sh').read_text()

def function(name):
    start = SOURCE.index(name+'() {')
    return SOURCE[start:SOURCE.index('\n}\n', start)+3]

class UpgradeServiceHealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for name, code in {
            'systemctl': '''#!/bin/sh
for service in ${ACTIVE_SERVICES:-}; do
  [ "$service" = "$3" ] && exit 0
done
exit 3
''',
            'doveconf': '''#!/bin/sh
printf 'validated\n' >> "$CONFIG_TRACE"
case " $* " in *" -x "*) exit "${CONFIG_EXIT:-0}" ;; esac
exit 0
''',
        }.items():
            path = self.root/name
            path.write_text(code)
            path.chmod(0o755)
        self.trace = self.root/'trace'
        self.env = dict(os.environ, PATH=str(self.root)+':/usr/bin:/bin',
                        CONFIG_TRACE=str(self.trace))
    def run_shell(self, code, **env):
        definitions = function('Check_Upgrade_Services')+'\n'+function('Verify_Upgrade_Services')
        return subprocess.run(['/bin/bash','-c',definitions+'\n'+code],
                              env=dict(self.env,**env),capture_output=True,text=True,timeout=10)
    def test_running_mail_with_invalid_config_stops_before_upgrade_work(self):
        marker=self.root/'upgrade-started'
        result=self.run_shell('Check_Upgrade_Services || exit 1\ntouch '+shlex.quote(str(marker)),
                              ACTIVE_SERVICES='lscpd dovecot',CONFIG_EXIT='89')
        self.assertNotEqual(0,result.returncode)
        self.assertFalse(marker.exists())
        self.assertIn('mail has not been restarted',result.stderr)
    def test_optional_inactive_mail_does_not_require_valid_config(self):
        result=self.run_shell('Check_Upgrade_Services && Verify_Upgrade_Services',
                              ACTIVE_SERVICES='lscpd',CONFIG_EXIT='89')
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertFalse(self.trace.exists())
    def test_active_services_remaining_up_pass(self):
        result=self.run_shell('Check_Upgrade_Services && Verify_Upgrade_Services',
                              ACTIVE_SERVICES='lscpd lshttpd mariadb postfix dovecot pdns pure-ftpd')
        self.assertEqual(0,result.returncode,result.stderr)
        self.assertEqual('validated\n',self.trace.read_text())
    def test_loss_of_each_previously_running_service_is_failure(self):
        for service in ('lscpd','lshttpd','lsws','openlitespeed','mariadb','mysql','mysqld','postfix','dovecot','pdns','powerdns','pure-ftpd','pure-ftpd-mysql'):
            with self.subTest(service=service):
                result=self.run_shell('Check_Upgrade_Services || exit 1\nexport ACTIVE_SERVICES=""\nVerify_Upgrade_Services',
                                      ACTIVE_SERVICES=service)
                self.assertNotEqual(0,result.returncode)
                self.assertIn(service+' was running',result.stderr)
    def test_preflight_precedes_mutating_upgrade_setup(self):
        # Extract and run the real entry-point sequence up to server inspection.
        tail=SOURCE[SOURCE.rindex('\nCheck_Root\n'):]
        tail=tail[:tail.index('\nCheck_Server_IP')]
        marker=self.root/'setup-started'
        result=self.run_shell('Check_Root() { :; }\nSet_Default_Variables() { touch '+shlex.quote(str(marker))+'; }\n'+tail,
                              ACTIVE_SERVICES='dovecot',CONFIG_EXIT='89')
        self.assertNotEqual(0,result.returncode)
        self.assertFalse(marker.exists())
    def test_final_service_failure_cannot_emit_upgrade_success(self):
        tail=SOURCE[SOURCE.rindex('\nRestart_Web_Terminal\n'):]
        result=self.run_shell('''
Restart_Web_Terminal() { :; }
Post_Install_Display_Final_Info() { test "$UPGRADE_FAILED" -eq 0; }
UPGRADE_ACTIVE_SERVICES=(dovecot)
UPGRADE_FAILED=0
'''+tail,ACTIVE_SERVICES='')
        self.assertNotEqual(0,result.returncode)

if __name__ == '__main__':
    unittest.main()
