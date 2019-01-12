#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import subprocess
import shlex
import argparse
import shutil
import plogical.CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from websiteFunctions.models import Websites, ChildDomains, aliasDomains
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.sslUtilities import sslUtilities
from plogical.vhost import vhost



class ServerStatusUtil:
    lswsInstallStatusPath = '/home/cyberpanel/switchLSWSStatus'
    serverRootPath = '/usr/local/lsws/'

    @staticmethod
    def executioner(command, statusFile):
        try:
            res = subprocess.call(shlex.split(command), stdout=statusFile, stderr=statusFile)
            if res == 1:
                return 0
            else:
                return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def installLiteSpeed(licenseKey, statusFile):
        try:

            cwd = os.getcwd()
            try:

                command = 'groupadd nobody'
                ServerStatusUtil.executioner(command, statusFile)

            except:
                pass

            try:
                command = 'usermod -a -G nobody nobody'
                ServerStatusUtil.executioner(command, statusFile)
            except:
                pass
            try:
                command = 'systemctl stop lsws'
                ServerStatusUtil.executioner(command, statusFile)
            except:
                pass

            command = 'wget https://www.litespeedtech.com/packages/5.0/lsws-5.3.5-ent-x86_64-linux.tar.gz'
            if ServerStatusUtil.executioner(command, statusFile) == 0:
                return 0

            command = 'tar zxf lsws-5.3.5-ent-x86_64-linux.tar.gz'
            if ServerStatusUtil.executioner(command, statusFile) == 0:
                return 0

            writeSerial = open('lsws-5.3.5/serial.no', 'w')
            writeSerial.writelines(licenseKey)
            writeSerial.close()

            shutil.copy('/usr/local/CyberCP/serverStatus/litespeed/install.sh', 'lsws-5.3.5/')
            shutil.copy('/usr/local/CyberCP/serverStatus/litespeed/functions.sh', 'lsws-5.3.5/')

            os.chdir('lsws-5.3.5')

            command = 'chmod +x install.sh'
            if ServerStatusUtil.executioner(command, statusFile) == 0:
                return 0

            command = 'chmod +x functions.sh'
            if ServerStatusUtil.executioner(command, statusFile) == 0:
                return 0

            command = './install.sh'
            if ServerStatusUtil.executioner(command, statusFile) == 0:
                return 0

            os.chdir(cwd)
            confPath = '/usr/local/lsws/conf/'
            shutil.copy('/usr/local/CyberCP/serverStatus/litespeed/httpd_config.xml', confPath)
            shutil.copy('/usr/local/CyberCP/serverStatus/litespeed/modsec.conf', confPath)
            shutil.copy('/usr/local/CyberCP/serverStatus/litespeed/httpd.conf', confPath)

            try:
                command = 'chown -R lsadm:lsadm ' + confPath
                subprocess.call(shlex.split(command))
            except:
                pass

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def setupFileManager(statusFile):
        try:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, "Setting up Filemanager files..\n")

            fileManagerPath = ServerStatusUtil.serverRootPath+"FileManager"
            if os.path.exists(fileManagerPath):
                shutil.rmtree(fileManagerPath)
            shutil.copytree("/usr/local/CyberCP/serverStatus/litespeed/FileManager",fileManagerPath)

            ## remove unnecessary files

            command = 'chmod -R 777 ' + fileManagerPath
            if ServerStatusUtil.executioner(command, statusFile) == 0:
                return 0

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,"Filemanager files are set!\n")

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def recover():
        FNULL = open(os.devnull, 'w')

        if os.path.exists('/usr/local/lsws'):
            shutil.rmtree('/usr/local/lsws')

        command = 'tar -zxvf /usr/local/olsBackup.tar.gz -C /usr/local/'
        ServerStatusUtil.executioner(command, FNULL)

        command = 'mv /usr/local/usr/local/lsws /usr/local'
        ServerStatusUtil.executioner(command, FNULL)

        if os.path.exists('/usr/local/usr'):
            shutil.rmtree('/usr/local/usr')

    @staticmethod
    def createWebsite(website):
        try:
            virtualHostName = website.domain

            confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
            FNULL = open(os.devnull, 'w')
            if not os.path.exists(confPath):
                command = 'mkdir -p ' + confPath
                ServerStatusUtil.executioner(command, FNULL)

            completePathToConfigFile = confPath + "/vhost.conf"

            if vhost.perHostVirtualConf(completePathToConfigFile, website.adminEmail , website.externalApp, website.phpSelection,
                                        virtualHostName, 1) == 1:
                pass
            else:
                return 0

            retValues = vhost.createConfigInMainVirtualHostFile(virtualHostName)
            if retValues[0] == 0:
                return 0

            if os.path.exists('/etc/letsencrypt/live/' + virtualHostName):
                sslUtilities.installSSLForDomain(virtualHostName, website.adminEmail)

            vhostPath = vhost.Server_root + "/conf/vhosts"
            FNULL = open(os.devnull, 'w')
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def createDomain(website):
        try:
            virtualHostName = website.domain

            confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
            completePathToConfigFile = confPath + "/vhost.conf"

            confPath = vhost.Server_root + "/conf/vhosts/" + virtualHostName
            FNULL = open(os.devnull, 'w')
            if not os.path.exists(confPath):
                command = 'mkdir -p ' + confPath
                ServerStatusUtil.executioner(command, FNULL)

            if vhost.perHostDomainConf(website.path, website.master.domain, virtualHostName, completePathToConfigFile, website.master.adminEmail, website.phpSelection, website.master.externalApp, 1) == 1:
                pass
            else:
                return 0

            retValues = vhost.createConfigInMainDomainHostFile(virtualHostName, website.master.domain)

            if retValues[0] == 0:
                return 0

            if os.path.exists('/etc/letsencrypt/live/' + virtualHostName):
                sslUtilities.installSSLForDomain(virtualHostName, website.master.adminEmail)

            vhostPath = vhost.Server_root + "/conf/vhosts"
            FNULL = open(os.devnull, 'w')
            command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + vhostPath
            cmd = shlex.split(command)
            subprocess.call(cmd, stdout=FNULL, stderr=subprocess.STDOUT)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
        return 0

    @staticmethod
    def rebuildvConf():
        try:
            allWebsites = Websites.objects.all()
            for website in allWebsites:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "Building vhost conf for: " + website.domain + ".\n", 1)
                if ServerStatusUtil.createWebsite(website) == 0:
                    return 0

                childs = website.childdomains_set.all()

                for child in childs:
                    try:
                        if ServerStatusUtil.createDomain(child) == 0:
                            logging.CyberCPLogFileWriter.writeToFile(
                                'Error while creating child domain: ' + child.domain)
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(
                            'Error while creating child domain: ' + child.domain + ' . Exact message: ' + str(
                                msg))

                aliases = website.aliasdomains_set.all()

                for alias in aliases:
                    try:
                        aliasDomain = alias.aliasDomain
                        alias.delete()
                        virtualHostUtilities.createAlias(website.domain, aliasDomain, 0, '/home', website.adminEmail, website.admin)
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(
                            'Error while creating alais domain: ' + aliasDomain + ' . Exact message: ' + str(
                                msg))

                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          "vhost conf successfully built for: " + website.domain + ".\n", 1)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    @staticmethod
    def switchTOLSWS(licenseKey):
        try:
            statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')
            FNULL = open(os.devnull, 'w')

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,"Starting conversion process..\n")
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Removing OpenLiteSpeed..\n", 1)

            ## Try to stop current LiteSpeed Process

            ProcessUtilities.killLiteSpeed()

            if os.path.exists('/usr/local/lsws'):
                command = 'tar -zcvf /usr/local/olsBackup.tar.gz /usr/local/lsws'
                if ServerStatusUtil.executioner(command, FNULL) == 0:
                    logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, "Failed to create backup of current LSWS. [404]", 1)
                    ServerStatusUtil.recover()
                    return 0

                dirs = os.listdir('/usr/local/lsws')
                for dir in dirs:
                    if dir.find('lsphp') > -1:
                        continue
                    finalDir = '/usr/local/lsws/' + dir
                    try:
                        shutil.rmtree(finalDir)
                    except:
                        pass

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "OpenLiteSpeed removed.\n", 1)

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Installing LiteSpeed Enterprise Web Server ..\n", 1)


            if ServerStatusUtil.installLiteSpeed(licenseKey, statusFile) == 0:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, "Failed to install LiteSpeed. [404]", 1)
                ServerStatusUtil.recover()
                return 0

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "LiteSpeed Enterprise Web Server installed.\n", 1)


            if ServerStatusUtil.setupFileManager(statusFile) == 0:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, "Failed to set up File Manager. [404]", 1)
                ServerStatusUtil.recover()
                return 0

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Rebuilding vhost conf..\n", 1)

            ServerStatusUtil.rebuildvConf()

            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "vhost conf successfully built.\n", 1)

            ProcessUtilities.stopLitespeed()
            ProcessUtilities.restartLitespeed()


            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,"Successfully switched to LITESPEED ENTERPRISE WEB SERVER. [200]\n", 1)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            ServerStatusUtil.recover()

def main():

    parser = argparse.ArgumentParser(description='Server Status Util.')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--licenseKey', help='LITESPEED ENTERPRISE WEB SERVER License Key')

    args = parser.parse_args()

    if args.function == "switchTOLSWS":
        ServerStatusUtil.switchTOLSWS(args.licenseKey)


if __name__ == "__main__":
    main()