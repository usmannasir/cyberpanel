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
list="${ACTIVE_SERVICES:-}"
[ "$1" = "is-failed" ] && list="${FAILED_SERVICES:-}"
for service in $list; do
  [ "$service" = "$3" ] && exit 0
done
exit 3
''',
            'doveconf': '''#!/bin/sh
printf 'validated\n' >> "$CONFIG_TRACE"
conf="${DOVECOT_CONF:-}"
[ "$1" = "-c" ] && conf="$2"
if [ -n "${BAD_MARKER:-}" ]; then grep -q -- "$BAD_MARKER" "$conf" && exit 89; exit 0; fi
case " $* " in *" -x "*) exit "${CONFIG_EXIT:-0}" ;; esac
exit 0
''',
        }.items():
            path = self.root/name
            path.write_text(code)
            path.chmod(0o755)
        self.trace = self.root/'trace'
        # Never the server's own mail configuration, also when the suite runs on a panel host.
        self.conf = self.root/'dovecot.conf'
        self.certs = self.root/'certs'
        self.env = dict(os.environ, PATH=str(self.root)+':/usr/bin:/bin',
                        CONFIG_TRACE=str(self.trace), DOVECOT_CONF=str(self.conf),
                        DOVECOT_SNI_ROOT=str(self.certs))
    def run_shell(self, code, **env):
        definitions = '\n'.join(function(name) for name in (
            'Repair_Dovecot_Missing_SNI', 'Check_Upgrade_Services', 'Verify_Upgrade_Services'))
        return subprocess.run(['/bin/bash','-c',definitions+'\n'+code],
                              env=dict(self.env,**env),stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                              universal_newlines=True,timeout=10)
    def test_running_mail_with_invalid_config_stops_before_upgrade_work(self):
        marker=self.root/'upgrade-started'
        result=self.run_shell('Check_Upgrade_Services || exit 1\ntouch '+shlex.quote(str(marker)),
                              ACTIVE_SERVICES='lscpd dovecot',CONFIG_EXIT='89')
        self.assertNotEqual(0,result.returncode)
        self.assertFalse(marker.exists())
        self.assertIn('mail has not been restarted',result.stderr)
    # dovecot.conf as releases before 3.0.8 left it after websites were created without SSL.
    HEAD = 'protocols = imap pop3\nssl = required\n'
    NOCERT_24 = ('local_name nocert.example {\n        ssl_server_cert_file = /etc/letsencrypt/live/nocert.example/fullchain.pem\n'
                 '        ssl_server_key_file = /etc/letsencrypt/live/nocert.example/privkey.pem\n}\n')
    NOCERT_23 = ('\nlocal_name mail.nocert.example {\n        ssl_cert = </etc/letsencrypt/live/mail.nocert.example/fullchain.pem\n'
                 '        ssl_key = </etc/letsencrypt/live/mail.nocert.example/privkey.pem\n}\n\n')
    HASCERT = ('local_name hascert.example {\n        ssl_cert = </etc/letsencrypt/live/hascert.example/fullchain.pem\n'
               '        ssl_key = </etc/letsencrypt/live/hascert.example/privkey.pem\n}\n')
    OWN = ('local_name own.example {\n  ssl_cert = </etc/ssl/own/fullchain.pem\n  ssl_key = </etc/ssl/own/privkey.pem\n}\n'
           'local_name extra.example {\n        ssl_cert = </etc/letsencrypt/live/extra.example/fullchain.pem\n'
           '        ssl_key = </etc/letsencrypt/live/extra.example/privkey.pem\n        ssl_min_protocol = TLSv1.2\n}\n')
    KEYLESS = ('local_name keyless.example {\n        ssl_cert = </etc/letsencrypt/live/keyless.example/fullchain.pem\n'
               '        ssl_key = </etc/letsencrypt/live/keyless.example/privkey.pem\n}\n')
    def certificate(self, name, files=('fullchain.pem', 'privkey.pem')):
        live = self.certs/'etc/letsencrypt/live'/name
        live.mkdir(parents=True, exist_ok=True)
        for item in files:
            (live/item).write_text('pem\n')
    def write_conf(self, text):
        self.conf.write_text(text)
        self.conf.chmod(0o640)
        return self.conf.read_bytes()
    def backups(self):
        return sorted(self.root.glob('dovecot.conf.cyberpanel-*.before-tls-repair'))
    def test_blocks_of_websites_without_certificate_are_removed_and_upgrade_continues(self):
        self.certificate('hascert.example')
        self.certificate('keyless.example', files=('fullchain.pem',))
        original = self.write_conf(self.HEAD+self.NOCERT_24+self.HASCERT+self.NOCERT_23+self.OWN+self.KEYLESS)
        marker = self.root/'upgrade-started'
        result = self.run_shell('Check_Upgrade_Services || exit 1\ntouch '+shlex.quote(str(marker)),
                                ACTIVE_SERVICES='lscpd dovecot', BAD_MARKER='nocert.example/')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertTrue(marker.exists())
        self.assertEqual(self.HEAD+self.HASCERT+'\n\n'+self.OWN, self.conf.read_text())
        self.assertEqual(0o640, self.conf.stat().st_mode & 0o777)
        [backup] = self.backups()
        self.assertEqual(original, backup.read_bytes())
        self.assertIn('keyless.example mail.nocert.example nocert.example', result.stdout)
        self.assertIn(str(backup), result.stdout)
    def test_file_is_put_back_when_dovecot_still_refuses_it(self):
        original = self.write_conf(self.HEAD+self.NOCERT_24)
        marker = self.root/'upgrade-started'
        result = self.run_shell('Check_Upgrade_Services || exit 1\ntouch '+shlex.quote(str(marker)),
                                ACTIVE_SERVICES='dovecot', CONFIG_EXIT='89')
        self.assertNotEqual(0, result.returncode)
        self.assertFalse(marker.exists())
        self.assertEqual(original, self.conf.read_bytes())
        self.assertEqual([], self.backups())
        self.assertIn('mail has not been restarted', result.stderr)
    def test_other_errors_and_blocks_that_are_not_ours_or_usable_are_left_alone(self):
        self.certificate('hascert.example')
        for text in (self.HEAD, self.HEAD+self.HASCERT+self.OWN):
            with self.subTest(text=text[-40:]):
                original = self.write_conf(text)
                result = self.run_shell('Check_Upgrade_Services', ACTIVE_SERVICES='dovecot', CONFIG_EXIT='89')
                self.assertNotEqual(0, result.returncode)
                self.assertEqual(original, self.conf.read_bytes())
                self.assertEqual([], self.backups())
    def test_linked_configuration_is_not_rewritten(self):
        target = self.root/'elsewhere.conf'
        target.write_text(self.HEAD+self.NOCERT_24)
        self.conf.symlink_to(target)
        result = self.run_shell('Check_Upgrade_Services', ACTIVE_SERVICES='dovecot', BAD_MARKER='nocert.example/')
        self.assertNotEqual(0, result.returncode)
        self.assertEqual(self.HEAD+self.NOCERT_24, target.read_text())
    def test_failed_mail_left_by_these_blocks_is_repaired_and_not_required(self):
        original = self.write_conf(self.HEAD+self.NOCERT_23)
        result = self.run_shell('Check_Upgrade_Services || exit 1\necho "required: ${UPGRADE_ACTIVE_SERVICES[*]}"',
                                ACTIVE_SERVICES='lscpd', FAILED_SERVICES='dovecot', BAD_MARKER='nocert.example/')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual(self.HEAD+'\n\n', self.conf.read_text())
        [backup] = self.backups()
        self.assertEqual(original, backup.read_bytes())
        self.assertIn('required: lscpd\n', result.stdout)
    def test_failed_mail_with_another_error_does_not_stop_the_upgrade(self):
        original = self.write_conf(self.HEAD+self.NOCERT_24)
        result = self.run_shell('Check_Upgrade_Services || exit 1\necho continued',
                                ACTIVE_SERVICES='lscpd', FAILED_SERVICES='dovecot', CONFIG_EXIT='89')
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn('continued', result.stdout)
        self.assertEqual(original, self.conf.read_bytes())
        self.assertEqual([], self.backups())
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
