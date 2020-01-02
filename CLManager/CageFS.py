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

            command = 'yum install -y lvemanager'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'yum reinstall -y lvemanager lve-utils cagefs alt-python27-cllib'
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

def main():

    parser = argparse.ArgumentParser(description='CyberPanel CageFS Manager')
    parser.add_argument('--function', help='Function')


    args = vars(parser.parse_args())

    if args["function"] == "submitCageFSInstall":
        CageFS.submitCageFSInstall()





if __name__ == "__main__":
    main()

