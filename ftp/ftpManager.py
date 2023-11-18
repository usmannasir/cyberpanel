#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django

from plogical.httpProc import httpProc

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from django.shortcuts import redirect
from django.http import HttpResponse
try:
    from .models import Users
    from loginSystem.models import Administrator
except:
    pass
import plogical.CyberCPLogFileWriter as logging
try:
    from loginSystem.views import loadLoginPage
    from websiteFunctions.models import Websites
    from plogical.ftpUtilities import FTPUtilities
    from plogical.acl import ACLManager
except:
    pass
import os

from plogical.processUtilities import ProcessUtilities
import argparse

class FTPManager:
    def __init__(self, request, extraArgs = None):
        self.request = request
        self.extraArgs = extraArgs

    def loadFTPHome(self):
        proc = httpProc(self.request, 'ftp/index.html',
                        None, 'createFTPAccount')
        return proc.render()

    def createFTPAccount(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        admin = Administrator.objects.get(pk=userID)

        if not os.path.exists('/home/cyberpanel/pureftpd'):
            proc = httpProc(self.request, 'ftp/createFTPAccount.html',
                            {"status": 0}, 'createFTPAccount')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        proc = httpProc(self.request, 'ftp/createFTPAccount.html',
                        {'websiteList': websitesName, 'OwnerFTP': admin.userName, "status": 1}, 'createFTPAccount')
        return proc.render()

    def submitFTPCreation(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'createFTPAccount') == 0:
                return ACLManager.loadErrorJson('creatFTPStatus', 0)

            data = json.loads(self.request.body)
            userName = data['ftpUserName']
            password = data['passwordByPass']

            domainName = data['ftpDomain']

            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(domainName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            try:
                api = data['api']
            except:
                api = '0'

            admin = Administrator.objects.get(id=userID)

            try:
                path = data['path']
                if len(path) > 0:
                    pass
                else:
                    path = 'None'
            except:
                path = 'None'


            result = FTPUtilities.submitFTPCreation(domainName, userName, password, path, admin.userName, api)

            if result[0] == 1:
                data_ret = {'status': 1, 'creatFTPStatus': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'creatFTPStatus': 0, 'error_message': result[1]}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'creatFTPStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteFTPAccount(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/pureftpd'):
            proc = httpProc(self.request, 'ftp/deleteFTPAccount.html',
                            {"status": 0}, 'deleteFTPAccount')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        proc = httpProc(self.request, 'ftp/deleteFTPAccount.html',
                        {'websiteList': websitesName, "status": 1}, 'deleteFTPAccount')
        return proc.render()

    def fetchFTPAccounts(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteFTPAccount') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            domain = data['ftpDomain']

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            website = Websites.objects.get(domain=domain)

            ftpAccounts = website.users_set.all()

            json_data = "["
            checker = 0

            for items in ftpAccounts:
                dic = {"userName": items.user}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitFTPDelete(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deleteFTPAccount') == 0:
                return ACLManager.loadErrorJson('deleteStatus', 0)

            data = json.loads(self.request.body)
            ftpUserName = data['ftpUsername']

            admin = Administrator.objects.get(pk=userID)
            ftp = Users.objects.get(user=ftpUserName)

            if ACLManager.checkOwnership(ftp.domain.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            FTPUtilities.submitFTPDeletion(ftpUserName)

            final_json = json.dumps({'status': 1, 'deleteStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException as msg:
            data_ret = {'status': 0, 'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def listFTPAccounts(self):
        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if not os.path.exists('/home/cyberpanel/pureftpd'):
            proc = httpProc(self.request, 'ftp/listFTPAccounts.html',
                            {"status": 0}, 'listFTPAccounts')
            return proc.render()

        websitesName = ACLManager.findAllSites(currentACL, userID)
        proc = httpProc(self.request, 'ftp/listFTPAccounts.html',
                        {'websiteList': websitesName, "status": 1}, 'listFTPAccounts')
        return proc.render()

    def getAllFTPAccounts(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listFTPAccounts') == 0:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            data = json.loads(self.request.body)
            selectedDomain = data['selectedDomain']

            domain = Websites.objects.get(domain=selectedDomain)

            admin = Administrator.objects.get(pk=userID)
            if ACLManager.checkOwnership(selectedDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            records = Users.objects.filter(domain=domain)

            json_data = "["
            checker = 0

            for items in records:
                dic = {'id': items.id,
                       'user': items.user,
                       'dir': items.dir,
                       'quotasize': str(items.quotasize) + "MB",
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def changePassword(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'listFTPAccounts') == 0:
                return ACLManager.loadErrorJson('changePasswordStatus', 0)

            data = json.loads(self.request.body)
            userName = data['ftpUserName']
            password = data['passwordByPass']

            admin = Administrator.objects.get(pk=userID)
            ftp = Users.objects.get(user=userName)

            if currentACL['admin'] == 1:
                pass
            elif ftp.domain.admin != admin:
                return ACLManager.loadErrorJson()

            FTPUtilities.changeFTPPassword(userName, password)

            data_ret = {'status': 1, 'changePasswordStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            data_ret = {'status': 0, 'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installPureFTPD(self):
        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:

            command = 'DEBIAN_FRONTEND=noninteractive apt remove pure-ftp* -y'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt install pure-ftpd-mysql -y'
            os.system(command)

            command = 'DEBIAN_FRONTEND=noninteractive apt install pure-ftpd-mysql -y'
            os.system(command)

            if ProcessUtilities.decideDistro() != ProcessUtilities.ubuntu20:
                command = 'wget https://rep.cyberpanel.net/pure-ftpd-common_1.0.47-3_all.deb'
                ProcessUtilities.executioner(command)

                command = 'wget https://rep.cyberpanel.net/pure-ftpd-mysql_1.0.47-3_amd64.deb'
                ProcessUtilities.executioner(command)

                command = 'dpkg --install --force-confold pure-ftpd-common_1.0.47-3_all.deb'
                ProcessUtilities.executioner(command)

                command = 'dpkg --install --force-confold pure-ftpd-mysql_1.0.47-3_amd64.deb'
                ProcessUtilities.executioner(command)

        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos:

            command = 'yum remove pure-ftp* -y'
            os.system(command)

            command = "yum install -y pure-ftpd"
            ProcessUtilities.executioner(command)
        elif ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

            command = 'yum remove pure-ftp* -y'
            os.system(command)

            command = 'dnf install pure-ftpd -y'
            ProcessUtilities.executioner(command)

        ####### Install pureftpd to system startup

        def pureFTPDServiceName():
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                return 'pure-ftpd-mysql'
            return 'pure-ftpd'

        command = "systemctl enable " + pureFTPDServiceName()
        ProcessUtilities.executioner(command)

        ###### FTP Groups and user settings settings

        command = 'groupadd -g 2001 ftpgroup'
        ProcessUtilities.executioner(command)

        command = 'useradd -u 2001 -s /bin/false -d /bin/null -c "pureftpd user" -g ftpgroup ftpuser'
        ProcessUtilities.executioner(command)

        return 1

    def startPureFTPD(self):
        ############## Start pureftpd ######################
        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
            command = 'systemctl start pure-ftpd-mysql'
        else:
            command = 'systemctl start pure-ftpd'
        ProcessUtilities.executioner(command)

        return 1

    def installPureFTPDConfigurations(self, mysqlPassword):
        try:
            ## setup ssl for ftp

            try:
                os.mkdir("/etc/ssl/private")
            except:
                pass

            if (ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8) or (
                    ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20 and ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu):
                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'
            else:
                command = 'openssl req -x509 -nodes -days 7300 -newkey rsa:2048 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/ssl/private/pure-ftpd.pem -out /etc/ssl/private/pure-ftpd.pem'

            ProcessUtilities.executioner(command)

            import shutil

            ftpdPath = "/etc/pure-ftpd"

            if os.path.exists(ftpdPath):
                shutil.rmtree(ftpdPath)
                shutil.copytree("/usr/local/CyberCP/install/pure-ftpd-one", ftpdPath)

            else:
                shutil.copytree("/usr/local/CyberCP/install/pure-ftpd-one", ftpdPath)


            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                try:
                    os.mkdir('/etc/pure-ftpd/conf')
                    os.mkdir('/etc/pure-ftpd/auth')
                    os.mkdir('/etc/pure-ftpd/db')
                except OSError as err:
                    pass

            data = open(ftpdPath + "/pureftpd-mysql.conf", "r").readlines()

            writeDataToFile = open(ftpdPath + "/pureftpd-mysql.conf", "w")

            dataWritten = "MYSQLPassword " + mysqlPassword + '\n'
            for items in data:
                if items.find("MYSQLPassword") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            writeDataToFile.close()

            ftpConfPath = '/etc/pure-ftpd/pureftpd-mysql.conf'

            if self.remotemysql == 'ON':
                command = "sed -i 's|localhost|%s|g' %s" % (self.mysqlhost, ftpConfPath)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|3306|%s|g' %s" % (self.mysqlport, ftpConfPath)
                ProcessUtilities.executioner(command)

                command = "sed -i 's|MYSQLSocket /var/lib/mysql/mysql.sock||g' %s" % (ftpConfPath)
                ProcessUtilities.executioner(command)

            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:

                if os.path.exists('/etc/pure-ftpd/db/mysql.conf'):
                    os.remove('/etc/pure-ftpd/db/mysql.conf')
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')
                else:
                    shutil.copy(ftpdPath + "/pureftpd-mysql.conf", '/etc/pure-ftpd/db/mysql.conf')

                import subprocess
                command = 'echo 1 > /etc/pure-ftpd/conf/TLS'
                subprocess.call(command, shell=True)

                command = 'echo %s > /etc/pure-ftpd/conf/ForcePassiveIP' % (self.publicip)
                subprocess.call(command, shell=True)

                command = 'echo "40110 40210" > /etc/pure-ftpd/conf/PassivePortRange'
                subprocess.call(command, shell=True)

                command = 'echo "no" > /etc/pure-ftpd/conf/UnixAuthentication'
                subprocess.call(command, shell=True)

                command = 'echo "/etc/pure-ftpd/db/mysql.conf" > /etc/pure-ftpd/conf/MySQLConfigFile'
                subprocess.call(command, shell=True)

                command = 'ln -s /etc/pure-ftpd/conf/MySQLConfigFile /etc/pure-ftpd/auth/30mysql'
                ProcessUtilities.executioner(command)

                command = 'ln -s /etc/pure-ftpd/conf/UnixAuthentication /etc/pure-ftpd/auth/65unix'
                ProcessUtilities.executioner(command)

                command = 'systemctl restart pure-ftpd-mysql.service'
                ProcessUtilities.executioner(command)

            return 1

        except IOError as msg:
            return 0

    def ResetFTPConfigurations(self):
        try:
            ### Check if remote or local mysql

            passFile = "/etc/cyberpanel/mysqlPassword"

            try:
                jsonData = json.loads(ProcessUtilities.outputExecutioner('cat %s' % (passFile)))

                self.mysqluser = jsonData['mysqluser']
                self.mysqlpassword = jsonData['mysqlpassword']
                self.mysqlport = jsonData['mysqlport']
                self.mysqlhost = jsonData['mysqlhost']
                self.remotemysql = 'ON'

                if self.mysqlhost.find('rds.amazon') > -1:
                    self.RDS = 1

                ## Also set localhost to this server

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddressLocal = ipData.split('\n', 1)[0]

                self.LOCALHOST = ipAddressLocal
            except BaseException as msg:
                self.remotemysql = 'OFF'

                if os.path.exists(ProcessUtilities.debugPath):
                    logging.CyberCPLogFileWriter.writeToFile('%s. [setupConnection:75]' % (str(msg)))

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Removing and re-installing FTP..,5')

            if self.installPureFTPD() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'installPureFTPD failed. [404].')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Resetting configurations..,40')

            import sys
            sys.path.append('/usr/local/CyberCP')
            os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
            from CyberCP import settings

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Configurations reset..,70')

            if self.installPureFTPDConfigurations(settings.DATABASES['default']['PASSWORD']) == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'installPureFTPDConfigurations failed. [404].')
                return 0

            if self.startPureFTPD() == 0:
                logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'],
                                                          'startPureFTPD failed. [404].')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Fixing permissions..,90')

            from mailServer.mailserverManager import MailServerManager
            MailServerManager(None, None, None).fixCyberPanelPermissions()
            logging.CyberCPLogFileWriter.statusWriter(self.extraArgs['tempStatusPath'], 'Completed [200].')

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

def main():

    parser = argparse.ArgumentParser(description='CyberPanel')
    parser.add_argument('function', help='Specify a function to call!')
    parser.add_argument('--tempStatusPath', help='Path of temporary status file.')

    args = parser.parse_args()

    if args.function == "ResetFTPConfigurations":
        extraArgs = {'tempStatusPath': args.tempStatusPath}
        ftp = FTPManager(None, extraArgs)
        ftp.ResetFTPConfigurations()

if __name__ == "__main__":
    main()