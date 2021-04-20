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

            if ProcessUtilities.outputExecutioner('uname -a').find('lve') == -1:
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

            command = 'yum reinstall -y lvemanager lve-utils cagefs'
            ServerStatusUtil.executioner(command, statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Important components reinstalled..\n", 1)

            activatedPath = '/home/cyberpanel/cloudlinux'

            writeToFile = open(activatedPath, 'a')
            writeToFile.write('CLInstalled')
            writeToFile.close()

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    @staticmethod
    def submitinstallImunify(key):
        try:

            imunifyKeyPath = '/home/cyberpanel/imunifyKeyPath'

            ##

            writeToFile = open(imunifyKeyPath, 'w')
            writeToFile.write(key)
            writeToFile.close()

            ##

            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting Imunify Installation..\n", 1)

            ##

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

            if not os.path.exists('i360deploy.sh'):
                command = 'wget https://repo.imunify360.cloudlinux.com/defence360/i360deploy.sh'
                ServerStatusUtil.executioner(command, statusFile)

            command = 'bash i360deploy.sh --key %s --beta' % (key)
            ServerStatusUtil.executioner(command, statusFile)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Imunify reinstalled..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    @staticmethod
    def submitinstallImunifyAV():
        try:


            mailUtilities.checkHome()

            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Starting ImunifyAV Installation..\n", 1)

            ##

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

            if not os.path.exists('imav-deploy.sh'):
                command = 'wget https://repo.imunify360.cloudlinux.com/defence360/imav-deploy.sh'
                ServerStatusUtil.executioner(command, statusFile)

            command = 'bash imav-deploy.sh'
            ServerStatusUtil.executioner(command, statusFile)

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

