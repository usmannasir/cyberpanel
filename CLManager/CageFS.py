#!/usr/local/CyberCP/bin/python
import sys
import os
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

django.setup()
import plogical.CyberCPLogFileWriter as logging
import argparse
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
from serverStatus.serverStatusUtil import ServerStatusUtil


class CageFS:
    packages = ['talksho']
    users = ['5001']

    @staticmethod
    def EnableCloudLinux():
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            confPath = '/usr/local/lsws/conf/httpd_config.conf'
            data = open(confPath, 'r').readlines()

            writeToFile = open(confPath, 'w')

            for items in data:
                if items.find('priority') > -1:
                    writeToFile.writelines(items)
                    writeToFile.writelines('enableLVE                 2\n')
                else:
                    writeToFile.writelines(items)

            writeToFile.close()
        else:
            confPath = '/usr/local/lsws/conf/httpd_config.xml'
            data = open(confPath, 'r').readlines()

            writeToFile = open(confPath, 'w')

            for items in data:
                if items.find('<enableChroot>') > -1:
                    writeToFile.writelines(items)
                    writeToFile.writelines('  <enableLVE>2</enableLVE>\n')
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

        ProcessUtilities.restartLitespeed()

    @staticmethod
    def submitCageFSInstall():
        try:

            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Checking if LVE Kernel is loaded ..\n", 1)

            if ProcessUtilities.outputExecutioner('uname -a').find('lve') > -1 or ProcessUtilities.outputExecutioner('lsmod').find('lve') > -1:
                pass
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "CloudLinux is installed but kernel is not loaded, please reboot your server to load appropriate kernel. [404]\n", 1)
                return 0

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "CloudLinux Kernel detected..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Enabling CloudLinux in web server ..\n", 1)

            CageFS.EnableCloudLinux()

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "CloudLinux enabled in server ..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Adding LVEManager port ..\n", 1)
            try:
                FirewallUtilities.addRule('tcp', '9000', '0.0.0.0/0')

                newFWRule = FirewallRules(name='lvemanager', proto='tcp', port='9000', ipAddress='0.0.0.0/0')
                newFWRule.save()
            except:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "LVEManager port added ..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Reinstalling important components ..\n", 1)

            command = 'yum install -y alt-python37-devel'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'yum reinstall -y cloudlinux-venv'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'yum reinstall -y lvemanager lve-utils cagefs'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'yum reinstall -y cloudlinux-venv'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'systemctl restart lvemanager'
            ServerStatusUtil.executioner(command, statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Important components reinstalled..\n", 1)

            activatedPath = '/home/cyberpanel/cloudlinux'

            writeToFile = open(activatedPath, 'a')
            writeToFile.write('CLInstalled')
            writeToFile.close()



            #### mount session save paths

            if os.path.exists('/etc/cagefs/cagefs.mp'):

                from managePHP.phpManager import PHPManager
                php_versions = PHPManager.findPHPVersions()

                for php in php_versions:
                    PHPVers = PHPManager.getPHPString(php)
                    line = f'@/var/lib/lsphp/session/lsphp{PHPVers},700\n'

                    WriteToFile = open('/etc/cagefs/cagefs.mp', 'a')
                    WriteToFile.write(line)
                    WriteToFile.close()

                command = 'cagefsctl --remount-all'
                ServerStatusUtil.executioner(command, statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    @staticmethod
    def submitinstallImunify(key):
        try:
            imunifyKeyPath = '/home/cyberpanel/imunifyKeyPath'

            writeToFile = open(imunifyKeyPath, 'w')
            writeToFile.write(key)
            writeToFile.close()

            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting Imunify360 Installation..\n", 1)

            # CRITICAL: Fix PHP-FPM pool configurations before installation
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Fixing PHP-FPM pool configurations for Imunify360 compatibility..\n", 1)
            
            # Import the upgrade module to access the fix function
            from plogical import upgrade
            fix_result = upgrade.Upgrade.CreateMissingPoolsforFPM()
            
            if fix_result == 0:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "PHP-FPM pool configurations fixed successfully..\n", 1)
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "Warning: PHP-FPM pool configuration fix had issues, continuing with installation..\n", 1)

            # Fix broken package installations that might prevent Imunify360 installation
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Fixing broken package installations..\n", 1)
            
            # Detect OS and fix packages accordingly
            if os.path.exists('/etc/redhat-release'):
                # CentOS/RHEL/CloudLinux
                command = 'yum-complete-transaction --cleanup-only 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)
                command = 'yum install -y --skip-broken 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)
            else:
                # Ubuntu/Debian
                command = 'dpkg --configure -a 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)
                command = 'apt --fix-broken install -y 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)

            command = 'mkdir -p /etc/sysconfig/imunify360/generic'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'touch /etc/sysconfig/imunify360/generic/modsec.conf'
            ServerStatusUtil.executioner(command, statusFile)

            integrationFile = '/etc/sysconfig/imunify360/integration.conf'

            content = """[paths]
ui_path =/usr/local/CyberCP/public/imunify
[web_server]
server_type = litespeed
graceful_restart_script = /usr/local/lsws/bin/lswsctrl restart
modsec_audit_log = /usr/local/lsws/logs/auditmodsec.log
modsec_audit_logdir = /usr/local/lsws/logs/

[malware]
basedir = /home
pattern_to_watch = ^/home/.+?/(public_html|public_ftp|private_html)(/.*)?$
"""

            writeToFile = open(integrationFile, 'w')
            writeToFile.write(content)
            writeToFile.close()

            ##

            ### address issue to create imunify dir - https://app.clickup.com/t/86engx249

            command = 'mkdir /usr/local/CyberCP/public/imunify'
            ProcessUtilities.executioner(command)

            command = 'pkill -f "bash i360deploy.sh"'
            ServerStatusUtil.executioner(command, statusFile)

            if not os.path.exists('i360deploy.sh'):
                command = 'wget https://repo.imunify360.cloudlinux.com/defence360/i360deploy.sh'
                ServerStatusUtil.executioner(command, statusFile)

            command = 'bash i360deploy.sh --uninstall --yes'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'bash i360deploy.sh --key %s --yes' % (key)
            ServerStatusUtil.executioner(command, statusFile)


            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Imunify reinstalled..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    @staticmethod
    def _ensure_imunifyav_assets(statusFile):
        try:
            commands = [
                'mkdir -p /etc/sysconfig/imunify360/generic',
                'mkdir -p /usr/local/CyberCP/public/imunifyav',
                'chown -R lscpd:lscpd /usr/local/CyberCP/public/imunifyav 2>/dev/null || true',
                'chmod 755 /usr/local/CyberCP/public/imunifyav 2>/dev/null || true',
                'chown -R lscpd:lscpd /etc/sysconfig/imunify360 2>/dev/null || true'
            ]

            for command in commands:
                ServerStatusUtil.executioner(command, statusFile)

            if os.path.exists('/etc/redhat-release'):
                pkg_cmd = 'yum install -y imunify-ui-generic imunify-antivirus || yum reinstall -y imunify-ui-generic'
            else:
                pkg_cmd = 'apt-get update -y >/dev/null 2>&1 && apt-get install -y imunify-antivirus || true'

            ServerStatusUtil.executioner(pkg_cmd, statusFile)
        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      f"ImunifyAV asset verification warning: {str(msg)}\n", 1)

    @staticmethod
    def submitinstallImunifyAV():
        try:
            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting ImunifyAV Installation..\n", 1)

            # CRITICAL: Fix PHP-FPM pool configurations before installation
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Fixing PHP-FPM pool configurations for ImunifyAV compatibility..\n", 1)
            
            # Import the upgrade module to access the fix function
            from plogical import upgrade
            fix_result = upgrade.Upgrade.CreateMissingPoolsforFPM()
            
            if fix_result == 0:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "PHP-FPM pool configurations fixed successfully..\n", 1)
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "Warning: PHP-FPM pool configuration fix had issues, continuing with installation..\n", 1)

            # Fix broken package installations that might prevent ImunifyAV installation
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Fixing broken package installations..\n", 1)
            
            # Detect OS and fix packages accordingly
            if os.path.exists('/etc/redhat-release'):
                # CentOS/RHEL/CloudLinux
                command = 'yum-complete-transaction --cleanup-only 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)
                command = 'yum install -y --skip-broken 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)
            else:
                # Ubuntu/Debian
                command = 'dpkg --configure -a 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)
                command = 'apt --fix-broken install -y 2>/dev/null || true'
                ServerStatusUtil.executioner(command, statusFile)

            command = 'mkdir -p /etc/sysconfig/imunify360'
            ServerStatusUtil.executioner(command, statusFile)


            integrationFile = '/etc/sysconfig/imunify360/integration.conf'

            content = """[paths]
ui_path = /usr/local/CyberCP/public/imunifyav
ui_path_owner = lscpd:lscpd
"""

            writeToFile = open(integrationFile, 'w')
            writeToFile.write(content)
            writeToFile.close()

            ##

            ### address issue to create imunify dir - https://app.clickup.com/t/86engx249

            command = 'pkill -f "bash imav-deploy.sh"'
            ServerStatusUtil.executioner(command, statusFile)

            if not os.path.exists('imav-deploy.sh'):
                command = 'wget https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh'
                ServerStatusUtil.executioner(command, statusFile)

            command = 'bash imav-deploy.sh --uninstall --yes'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'mkdir -p /usr/local/CyberCP/public/imunifyav'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'bash imav-deploy.sh --yes'
            ServerStatusUtil.executioner(command, statusFile)

            CageFS._ensure_imunifyav_assets(statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "ImunifyAV reinstalled..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel CageFS Manager')
    parser.add_argument('--function', help='Function')
    parser.add_argument('--key', help='Imunify Key')


    args = vars(parser.parse_args())

    if args["function"] == "submitCageFSInstall":
        CageFS.submitCageFSInstall()
    elif args["function"] == "submitinstallImunify":
        CageFS.submitinstallImunify(args["key"])
    elif args["function"] == "submitinstallImunifyAV":
        CageFS.submitinstallImunifyAV()

if __name__ == "__main__":
    main()

