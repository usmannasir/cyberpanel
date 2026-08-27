#!/usr/local/CyberCP/bin/python
import sys
import os
import django
sys.path.insert(0, '/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

django.setup()
import plogical.CyberCPLogFileWriter as logging
import argparse
from plogical.mailUtilities import mailUtilities
from plogical.processUtilities import ProcessUtilities
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
from serverStatus.serverStatusUtil import ServerStatusUtil
from plogical.imunify_integration import (
    IMUNIFY_360_UI,
    IMUNIFY_AV_UI,
    build_deploy_commands,
    build_imunify360_integration_conf,
    build_imunifyav_integration_conf,
    chmod_imunify_execute_files,
    ensure_clscripts_executable,
    ensure_install_status_file,
    run_deploy_commands,
    write_integration_conf,
)


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
            if key is None or not str(key).strip():
                raise ValueError('An Imunify360 license key is required.')
            key = str(key).strip()

            mailUtilities.checkHome()
            ensure_install_status_file()

            imunifyKeyPath = '/home/cyberpanel/imunifyKeyPath'
            keyFileDescriptor = os.open(
                imunifyKeyPath,
                os.O_WRONLY | os.O_CREAT | os.O_TRUNC,
                0o600,
            )
            with os.fdopen(keyFileDescriptor, 'w') as writeToFile:
                writeToFile.write(key)
            os.chmod(imunifyKeyPath, 0o600)

            with open(ServerStatusUtil.lswsInstallStatusPath, 'w') as statusFile:
                logging.CyberCPLogFileWriter.statusWriter(
                    ServerStatusUtil.lswsInstallStatusPath,
                    "Starting Imunify360 Installation..\n", 1)

                os.makedirs('/etc/sysconfig/imunify360/generic', exist_ok=True)
                with open('/etc/sysconfig/imunify360/generic/modsec.conf', 'a'):
                    pass
                os.makedirs(IMUNIFY_360_UI, exist_ok=True)

                write_integration_conf(build_imunify360_integration_conf())
                ensure_clscripts_executable()

                commands = build_deploy_commands('360', key=key)
                run_deploy_commands(commands, statusFile)
                write_integration_conf(build_imunify360_integration_conf())
                ensure_clscripts_executable()
                chmod_imunify_execute_files(IMUNIFY_360_UI)

                logging.CyberCPLogFileWriter.statusWriter(
                    ServerStatusUtil.lswsInstallStatusPath,
                    "Imunify360 reinstalled..\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    @staticmethod
    def submitinstallImunifyAV():
        try:
            mailUtilities.checkHome()
            ensure_install_status_file()

            with open(ServerStatusUtil.lswsInstallStatusPath, 'w') as statusFile:
                logging.CyberCPLogFileWriter.statusWriter(
                    ServerStatusUtil.lswsInstallStatusPath,
                    "Starting ImunifyAV Installation..\n", 1)

                os.makedirs('/etc/sysconfig/imunify360/generic', exist_ok=True)
                with open('/etc/sysconfig/imunify360/generic/modsec.conf', 'a'):
                    pass
                os.makedirs(IMUNIFY_AV_UI, exist_ok=True)

                write_integration_conf(build_imunifyav_integration_conf())
                ensure_clscripts_executable()

                commands = build_deploy_commands('av')
                run_deploy_commands(commands, statusFile)
                write_integration_conf(build_imunifyav_integration_conf())
                ensure_clscripts_executable()
                chmod_imunify_execute_files(IMUNIFY_AV_UI)

                logging.CyberCPLogFileWriter.statusWriter(
                    ServerStatusUtil.lswsInstallStatusPath,
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
