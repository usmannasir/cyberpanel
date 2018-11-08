from plogical import hashPassword
from loginSystem.models import Administrator
from django.shortcuts import HttpResponse
import json
from plogical.website import WebsiteManager
from plogical.acl import  ACLManager
from plogical.virtualHostUtilities import virtualHostUtilities
from websiteFunctions.models import  Websites
import subprocess, shlex
from databases.databaseManager import DatabaseManager
from dns.dnsManager import DNSManager
from mailServer.mailserverManager import MailServerManager
from ftp.ftpManager import FTPManager
from manageSSL.views import issueSSL
from plogical.backupManager import BackupManager

class CloudManager:

    def __init__(self, data = None):
        self.data = data

    def ajaxPre(self, status, errorMessage):
        final_dic = {'status': status, 'error_message': errorMessage}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    def verifyLogin(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                return self.ajaxPre(1, None)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsites(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.getFurtherAccounts(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitWebsiteDeletion(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.submitWebsiteDeletion(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitWebsiteCreation(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.submitWebsiteCreation(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsiteDataJSON(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.fetchWebsiteDataJSON(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsiteData(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                currentACL = ACLManager.loadedACL(admin.pk)
                website = Websites.objects.get(domain=self.data['domainName'])
                admin = Administrator.objects.get(pk=admin.pk)

                if ACLManager.checkOwnership(self.data['domainName'], admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                Data = {}

                Data['ftpAllowed'] = website.package.ftpAccounts
                Data['ftpUsed'] = website.users_set.all().count()

                Data['dbUsed'] = website.databases_set.all().count()
                Data['dbAllowed'] = website.package.dataBases

                diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + self.data['domainName'], website.package.diskSpace)

                ## bw usage calculation

                try:
                    execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                    execPath = execPath + " findDomainBW --virtualHostName " + self.data['domainName'] + " --bandwidth " + str(
                        website.package.bandwidth)

                    output = subprocess.check_output(shlex.split(execPath))
                    bwData = output.split(",")
                except BaseException:
                    bwData = [0, 0]

                ## bw usage calculations

                Data['bwAllowed'] = website.package.bandwidth
                Data['bwUsed'] = bwData[0]
                Data['bwUsage'] = bwData[1]

                if diskUsageDetails != None:
                    if diskUsageDetails[1] > 100:
                        diskUsageDetails[1] = 100

                    Data['diskUsage'] = diskUsageDetails[1]
                    Data['diskUsed'] = diskUsageDetails[0]
                    Data['diskAllowed'] = website.package.diskSpace
                else:
                    Data['diskUsed'] = 0
                    Data['diskUsage'] = 0
                    Data['diskInMBTotal'] = website.package.diskSpace

                Data['status'] = 1
                final_json = json.dumps(Data)
                return HttpResponse(final_json)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchModifyData(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.submitWebsiteModify(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def saveModifications(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.saveWebsiteChanges(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitDBCreation(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DatabaseManager()
                return dm.submitDBCreation(admin.pk, self.data, 1)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchDatabases(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DatabaseManager()
                return dm.fetchDatabases(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitDatabaseDeletion(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DatabaseManager()
                return dm.submitDatabaseDeletion(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def changePassword(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DatabaseManager()
                return dm.changePassword(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentRecordsForDomain(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DNSManager()
                return dm.getCurrentRecordsForDomain(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def deleteDNSRecord(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DNSManager()
                return dm.deleteDNSRecord(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def addDNSRecord(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['password']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                dm = DNSManager()
                return dm.addDNSRecord(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitEmailCreation(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.submitEmailCreation()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def getEmailsForDomain(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.getEmailsForDomain()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitEmailDeletion(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.submitEmailDeletion()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitPasswordChange(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.submitPasswordChange()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchCurrentForwardings(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.fetchCurrentForwardings()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitForwardDeletion(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.submitForwardDeletion()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitEmailForwardingCreation(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.submitEmailForwardingCreation()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchDKIMKeys(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.fetchDKIMKeys()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def generateDKIMKeys(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                msm = MailServerManager(request)
                return msm.generateDKIMKeys()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitFTPCreation(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                fm = FTPManager(request)
                return fm.submitFTPCreation()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def getAllFTPAccounts(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                fm = FTPManager(request)
                return fm.getAllFTPAccounts()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitFTPDelete(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                fm = FTPManager(request)
                return fm.submitFTPDelete()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def changeFTPPassword(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                fm = FTPManager(request)
                return fm.changePassword()
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def issueSSL(self, request):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)
            request.session['userID'] = admin.pk

            if hashPassword.check_password(admin.password, adminPass):
                return issueSSL(request)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def statusFunc(self):
        try:
            statusFile = self.data['statusFile']
            statusData = open(statusFile, 'r').readlines()
            lastLine = statusData[-1]

            if lastLine.find('[200]') > -1:
                command = 'sudo rm -f ' + statusFile
                subprocess.call(shlex.split(command))
                data_ret = {'status': 1, 'abort': 1, 'installationProgress': "100", 'currentStatus': lastLine}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            elif lastLine.find('[404]') > -1:
                data_ret = {'status': 0, 'abort': 1, 'installationProgress': "0", 'error_message': lastLine}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                progress = lastLine.split(',')
                currentStatus = progress[0]
                try:
                    installationProgress = progress[1]
                except:
                    installationProgress = 0
                data_ret = {'status': 1, 'abort': 0, 'installationProgress': installationProgress, 'currentStatus': currentStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0,'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDomainCreation(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.submitDomainCreation(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def fetchDomains(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.fetchDomains(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def submitDomainDeletion(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.submitDomainDeletion(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def changeOpenBasedir(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.changeOpenBasedir(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def changePHP(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                wm = WebsiteManager()
                return wm.changePHP(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def backupStatusFunc(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                bm = BackupManager()
                return bm.backupStatus(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            data_ret = {'status': 0,'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitBackupCreation(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                bm = BackupManager()
                return bm.submitBackupCreation(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentBackups(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                bm = BackupManager()
                return bm.getCurrentBackups(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))

    def deleteBackup(self):
        try:
            adminUser = self.data['userName']
            adminPass = self.data['serverPassword']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                bm = BackupManager()
                return bm.deleteBackup(admin.pk, self.data)
            else:
                return self.ajaxPre(0, 'Invalid login information.')

        except BaseException, msg:
            return self.ajaxPre(0, str(msg))


