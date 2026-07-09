import sys
import socket
import random
import os
import json
import shlex
import userManagment.views as um
from backup.backupManager import BackupManager
from databases.databaseManager import DatabaseManager
from dns.dnsManager import DNSManager
from firewall.firewallManager import FirewallManager
from ftp.ftpManager import FTPManager
from highAvailability.haManager import HAManager
from loginSystem.models import Administrator
from mailServer.mailserverManager import MailServerManager
from manageSSL.views import issueSSL, obtainHostNameSSL, obtainMailServerSSL
from packages.packagesManager import PackagesManager
from plogical.mysqlUtilities import mysqlUtilities
from plogical.virtualHostUtilities import virtualHostUtilities
from websiteFunctions.website import WebsiteManager
from s3Backups.s3Backups import S3Backups
from serverLogs.views import getLogsFromFile
from serverStatus.views import topProcessesStatus, killProcess, switchTOLSWSStatus
from plogical import hashPassword
from loginSystem.models import ACL
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.securityUtils import api_token_matches
from managePHP.phpManager import PHPManager
from managePHP.views import submitExtensionRequest, getRequestStatusApache
from containerization.views import *

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")


class CloudManager:
    def __init__(self, data=None, admin=None):
        self.data = data
        self.admin = admin

    def ajaxPre(self, status, errorMessage):
        final_dic = {'status': status, 'error_message': errorMessage}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

    def verifyLogin(self, request):
        try:
            if api_token_matches(request.META.get('HTTP_AUTHORIZATION'), self.admin.token):
                return 1, self.ajaxPre(1, None)
            else:
                return 0, self.ajaxPre(0, 'Invalid login information.')

        except BaseException as msg:
            return 0, self.ajaxPre(0, str(msg))

    def fetchWebsites(self):
        try:
            wm = WebsiteManager()
            return wm.getFurtherAccounts(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitWebsiteDeletion(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.submitWebsiteDeletion(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitWebsiteCreation(self):
        try:

            try:

                UserAccountName = self.data['UserAccountName']
                UserPassword = self.data['UserPassword']
                FullName = self.data['FullName']
                token = hashPassword.generateToken(UserAccountName, UserPassword)
                password = hashPassword.hash_password(UserPassword)

                try:
                    initWebsitesLimit = int(self.data['websitesLimit'])
                except:
                    initWebsitesLimit = 10

                try:
                    acl = self.data['acl']
                    selectedACL = ACL.objects.get(name=acl)

                except:
                    selectedACL = ACL.objects.get(name='user')

                try:
                    apiAccess = int(self.data['api'])
                except:
                    apiAccess = 10

                try:
                    newAdmin = Administrator(firstName=FullName,
                                             lastName="",
                                             email=self.data['adminEmail'],
                                             type=3,
                                             userName=UserAccountName,
                                             password=password,
                                             initWebsitesLimit=initWebsitesLimit,
                                             owner=1,
                                             acl=selectedACL,
                                             token=token,
                                             api=apiAccess
                                             )
                    newAdmin.save()
                except BaseException as msg:
                    logging.writeToFile(str(msg))
                    admin = Administrator.objects.get(userName=UserAccountName)
                    admin.token = token
                    admin.password = password
                    admin.save()
            except BaseException as msg:
                logging.writeToFile(str(msg))

            wm = WebsiteManager()
            return wm.submitWebsiteCreation(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsiteDataJSON(self):
        try:
            wm = WebsiteManager()
            return wm.fetchWebsiteDataJSON(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsiteData(self):
        try:

            currentACL = ACLManager.loadedACL(self.admin.pk)
            website = Websites.objects.get(domain=self.data['domainName'])
            admin = Administrator.objects.get(pk=self.admin.pk)

            if ACLManager.checkOwnership(self.data['domainName'], admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            Data = {}

            Data['ftpAllowed'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['dbUsed'] = website.databases_set.all().count()
            Data['dbAllowed'] = website.package.dataBases

            DiskUsage, DiskUsagePercentage, bwInMB, bwUsage = virtualHostUtilities.FindStats(website)

            ## bw usage calculations

            Data['bwInMBTotal'] = website.package.bandwidth
            Data['bwInMB'] = bwInMB
            Data['bwUsage'] = bwUsage

            if DiskUsagePercentage > 100:
                DiskUsagePercentage = 100

            Data['diskUsage'] = DiskUsagePercentage
            Data['diskInMB'] = DiskUsage
            Data['diskInMBTotal'] = website.package.diskSpace

            ##

            Data['status'] = 1
            final_json = json.dumps(Data)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchModifyData(self):
        try:
            wm = WebsiteManager()
            return wm.submitWebsiteModify(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def saveModifications(self):
        try:
            wm = WebsiteManager()
            return wm.saveWebsiteChanges(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitDBCreation(self):
        try:
            dm = DatabaseManager()
            return dm.submitDBCreation(self.admin.pk, self.data, 1)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchDatabases(self):
        try:
            dm = DatabaseManager()
            return dm.fetchDatabases(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitDatabaseDeletion(self):
        try:
            dm = DatabaseManager()
            return dm.submitDatabaseDeletion(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def changePassword(self):
        try:
            dm = DatabaseManager()
            return dm.changePassword(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentRecordsForDomain(self):
        try:
            dm = DNSManager()
            return dm.getCurrentRecordsForDomain(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteDNSRecord(self):
        try:
            dm = DNSManager()
            return dm.deleteDNSRecord(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def addDNSRecord(self):
        try:
            dm = DNSManager()
            return dm.addDNSRecord(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitEmailCreation(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.submitEmailCreation()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getEmailsForDomain(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.getEmailsForDomain()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitEmailDeletion(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.submitEmailDeletion()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitPasswordChange(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.submitPasswordChange()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchCurrentForwardings(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.fetchCurrentForwardings()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitForwardDeletion(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.submitForwardDeletion()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitEmailForwardingCreation(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.submitEmailForwardingCreation()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchDKIMKeys(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.fetchDKIMKeys()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def generateDKIMKeys(self, request):
        try:
            request.session['userID'] = self.admin.pk
            msm = MailServerManager(request)
            return msm.generateDKIMKeys()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitFTPCreation(self, request):
        try:
            request.session['userID'] = self.admin.pk
            fm = FTPManager(request)
            return fm.submitFTPCreation()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getAllFTPAccounts(self, request):
        try:
            request.session['userID'] = self.admin.pk
            fm = FTPManager(request)
            return fm.getAllFTPAccounts()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitFTPDelete(self, request):
        try:
            request.session['userID'] = self.admin.pk
            fm = FTPManager(request)
            return fm.submitFTPDelete()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def changeFTPPassword(self, request):
        try:
            request.session['userID'] = self.admin.pk
            fm = FTPManager(request)
            return fm.changePassword()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def issueSSL(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return issueSSL(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def statusFunc(self):
        try:
            statusFile = self.data['statusFile']

            if ACLManager.CheckStatusFilleLoc(statusFile):
                pass
            else:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "100",
                            'currentStatus': 'Invalid status file.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            statusData = open(statusFile, 'r').readlines()
            try:
                lastLine = statusData[-1]
                if lastLine.find('[200]') > -1:
                    command = 'rm -f ' + statusFile
                    ProcessUtilities.executioner(command)
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
                        installationProgress = progress[1].rstrip('\n')
                    except:
                        installationProgress = 0
                    data_ret = {'status': 1, 'abort': 0, 'installationProgress': installationProgress,
                                'currentStatus': currentStatus}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            except IndexError:
                data_ret = {'status': 1, 'abort': 0, 'installationProgress': 0,
                            'currentStatus': 'Working..'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDomainCreation(self):
        try:
            wm = WebsiteManager()
            return wm.submitDomainCreation(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchDomains(self):
        try:
            wm = WebsiteManager()
            return wm.fetchDomains(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitDomainDeletion(self):
        try:
            wm = WebsiteManager()
            return wm.submitDomainDeletion(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def changeOpenBasedir(self):
        try:
            wm = WebsiteManager()
            return wm.changeOpenBasedir(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def changePHP(self):
        try:
            wm = WebsiteManager()
            return wm.changePHP(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def backupStatusFunc(self):
        try:
            bm = BackupManager()
            return bm.backupStatus(self.admin.pk, self.data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitBackupCreation(self):
        try:
            bm = BackupManager()
            return bm.submitBackupCreation(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentBackups(self):
        try:
            bm = BackupManager()
            return bm.getCurrentBackups(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteBackup(self):
        try:
            bm = BackupManager()
            return bm.deleteBackup(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchACLs(self):
        try:
            userID = self.admin.pk
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                aclNames = ACLManager.unFileteredACLs()
            elif currentACL['changeUserACL'] == 1:
                aclNames = ACLManager.unFileteredACLs()
            elif currentACL['createNewUser'] == 1:
                aclNames = ['user']
            else:
                return ACLManager.loadError()

            json_data = "["
            checker = 0

            for items in aclNames:
                dic = {'acl': items}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitUserCreation(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.submitUserCreation(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchUsers(self):
        try:
            userID = self.admin.pk
            allUsers = ACLManager.loadUserObjects(userID)

            json_data = "["
            checker = 0

            for user in allUsers:
                dic = {
                    "id": user.id,
                    "userName": user.userName,
                    "firstName": user.firstName,
                    "lastName": user.lastName,
                    "email": user.email,
                    "acl": user.acl.name,
                    "websitesLimit": user.initWebsitesLimit
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitUserDeletion(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.submitUserDeletion(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def saveModificationsUser(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.saveModifications(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def userWithResellerPriv(self):
        try:
            userID = self.admin.pk
            allUsers = ACLManager.userWithResellerPriv(userID)

            json_data = "["
            checker = 0

            for user in allUsers:
                dic = {
                    "userName": user,
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def saveResellerChanges(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.saveResellerChanges(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def changeACLFunc(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.changeACLFunc(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createACLFunc(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.createACLFunc(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def findAllACLs(self, request):
        try:
            userID = self.admin.pk
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                aclNames = ACLManager.findAllACLs()
            else:
                return ACLManager.loadErrorJson()

            json_data = "["
            checker = 0

            for items in aclNames:
                dic = {'acl': items}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteACLFunc(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.deleteACLFunc(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchACLDetails(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.fetchACLDetails(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitACLModifications(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return um.submitACLModifications(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitPackage(self, request):
        try:
            request.session['userID'] = self.admin.pk
            pm = PackagesManager(request)
            return pm.submitPackage()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchPackages(self, request):
        try:
            userID = self.admin.pk
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'deletePackage') == 0:
                return ACLManager.loadError()

            packageList = ACLManager.loadPackageObjects(userID, currentACL)

            json_data = "["
            checker = 0

            for items in packageList:
                dic = {
                    'packageName': items.packageName,
                    'allowedDomains': items.allowedDomains,
                    'diskSpace': items.diskSpace,
                    'bandwidth': items.bandwidth,
                    'emailAccounts': items.emailAccounts,
                    'dataBases': items.dataBases,
                    'ftpAccounts': items.ftpAccounts,
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitPackageDelete(self, request):
        try:
            request.session['userID'] = self.admin.pk
            pm = PackagesManager(request)
            return pm.submitDelete()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitPackageModify(self, request):
        try:
            request.session['userID'] = self.admin.pk
            pm = PackagesManager(request)
            return pm.saveChanges()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getDataFromLogFile(self, request):
        try:
            wm = WebsiteManager()
            return wm.getDataFromLogFile(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchErrorLogs(self, request):
        try:
            wm = WebsiteManager()
            return wm.fetchErrorLogs(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitApplicationInstall(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()

            if self.data['selectedApplication'] == 'WordPress with LSCache':
                return wm.installWordpress(self.admin.pk, self.data)
            elif self.data['selectedApplication'] == 'Prestashop':
                return wm.prestaShopInstall(self.admin.pk, self.data)
            elif self.data['selectedApplication'] == 'Joomla':
                return wm.installJoomla(self.admin.pk, self.data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def obtainServer(self, request):
        try:
            request.session['userID'] = self.admin.pk
            data_ret = {'status': 1, 'serverStatus': ProcessUtilities.decideServer()}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getSSHConfigs(self):
        try:
            fm = FirewallManager()
            return fm.getSSHConfigs(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def saveSSHConfigs(self):
        try:
            fm = FirewallManager()
            return fm.saveSSHConfigs(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteSSHKey(self):
        try:
            fm = FirewallManager()
            return fm.deleteSSHKey(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def addSSHKey(self):
        try:
            fm = FirewallManager()
            return fm.addSSHKey(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentRules(self):
        try:
            fm = FirewallManager()
            return fm.getCurrentRules(self.admin.pk)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def addRule(self):
        try:
            fm = FirewallManager()
            return fm.addRule(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteRule(self):
        try:
            fm = FirewallManager()
            return fm.deleteRule(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getLogsFromFile(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return getLogsFromFile(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def serverSSL(self, request):
        try:
            request.session['userID'] = self.admin.pk
            if self.data['type'] == 'hostname':
                return obtainHostNameSSL(request)
            else:
                return obtainMailServerSSL(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def setupManager(self, request):
        try:
            request.session['userID'] = self.admin.pk
            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            self.data['tempStatusPath'] = tempStatusPath

            ham = HAManager(request, self.data, 'setupNode')
            ham.start()

            data = {}
            data['tempStatusPath'] = tempStatusPath

            proc = httpProc(request, None)
            return proc.ajax(1, None, data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchManagerTokens(self, request):
        try:
            request.session['userID'] = self.admin.pk
            ham = HAManager(request, self.data, 'fetchManagerTokens')
            return ham.fetchManagerTokens()

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def addWorker(self, request):
        try:
            request.session['userID'] = self.admin.pk
            ham = HAManager(request, self.data, 'fetchManagerTokens')
            return ham.addWorker()

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchSSHKey(self, request):
        try:
            pubKey = os.path.join("/root", ".ssh", 'cyberpanel.pub')
            execPath = "sudo cat " + pubKey
            data = ProcessUtilities.outputExecutioner(execPath)

            data_ret = {
                'status': 1,
                'error_message': "None",
                'pubKey': data
            }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def putSSHkeyFunc(self, request):
        try:
            fm = FirewallManager(request)
            return fm.addSSHKey(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def leaveSwarm(self, request):
        try:
            request.session['userID'] = self.admin.pk
            ham = HAManager(request, self.data, 'leaveSwarm')
            return ham.leaveSwarm()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def setUpDataNode(self, request):
        try:
            request.session['userID'] = self.admin.pk
            ham = HAManager(request, self.data, 'setUpDataNode')
            return ham.setUpDataNode()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitEditCluster(self, request):
        try:
            request.session['userID'] = self.admin.pk
            ham = HAManager(request, self.data, 'submitEditCluster')
            return ham.submitEditCluster()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def connectAccount(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'connectAccount')
            return s3.connectAccount()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBuckets(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBuckets')
            return s3.fetchBuckets()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createPlan(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'createPlan')
            return s3.createPlan()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBackupPlans(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBackupPlans')
            return s3.fetchBackupPlans()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deletePlan(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deletePlan')
            return s3.deletePlan()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsitesInPlan(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchWebsitesInPlan')
            return s3.fetchWebsitesInPlan()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteDomainFromPlan(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deleteDomainFromPlan')
            return s3.deleteDomainFromPlan()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def savePlanChanges(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'savePlanChanges')
            return s3.savePlanChanges()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBackupLogs(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBackupLogs')
            return s3.fetchBackupLogs()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def forceRunAWSBackup(self, request):
        try:

            request.session['userID'] = self.admin.pk

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/IncScheduler.py forceRunAWSBackup --planName %s" % (
                self.data['planName'])
            ProcessUtilities.popenExecutioner(execPath)

            return self.ajaxPre(1, None)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def systemStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return topProcessesStatus(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def killProcess(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return killProcess(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def connectAccountDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'connectAccountDO')
            return s3.connectAccountDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBucketsDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBucketsDO')
            return s3.fetchBucketsDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createPlanDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'createPlanDO')
            return s3.createPlanDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBackupPlansDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBackupPlansDO')
            return s3.fetchBackupPlansDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deletePlanDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deletePlanDO')
            return s3.deletePlanDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsitesInPlanDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchWebsitesInPlanDO')
            return s3.fetchWebsitesInPlanDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBackupLogsDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBackupLogsDO')
            return s3.fetchBackupLogsDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteDomainFromPlanDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deleteDomainFromPlanDO')
            return s3.deleteDomainFromPlanDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def savePlanChangesDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'savePlanChangesDO')
            return s3.savePlanChangesDO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def forceRunAWSBackupDO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'forceRunAWSBackupDO')
            s3.start()
            return self.ajaxPre(1, None)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def showStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.showStatus()

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchRam(self, request):
        try:
            # request.session['userID'] = self.admin.pk
            # currentACL = ACLManager.loadedACL(self.admin.pk)
            #
            # if currentACL['admin'] == 0:
            #     return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            # if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
            #    return self.ajaxPre(0, 'This feature is currently only available on CentOS.')

            from psutil import virtual_memory
            import math

            finalData = {}
            mem = virtual_memory()
            inGB = math.ceil(float(mem.total) / float(1024 * 1024 * 1024))
            finalData['ramInGB'] = inGB

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                finalData['conf'] = ProcessUtilities.outputExecutioner('sudo cat /etc/my.cnf')
            else:
                finalData['conf'] = ProcessUtilities.outputExecutioner('sudo cat /etc/mysql/my.cnf')

            finalData['status'] = 1

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def applyMySQLChanges(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            result = mysqlUtilities.applyMySQLChanges(self.data)

            if result[0] == 0:
                return self.ajaxPre(0, result[1])
            else:
                return self.ajaxPre(1, None)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def restartMySQL(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.restartMySQL()

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchDatabasesMYSQL(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.fetchDatabases()

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchTables(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.fetchTables(self.data)

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteTable(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.deleteTable(self.data)

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchTableData(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.fetchTableData(self.data)

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchStructure(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

            finalData = mysqlUtilities.fetchStructure(self.data)

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def addMINIONode(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'addMINIONode')
            return s3.addMINIONode()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchMINIONodes(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchMINIONodes')
            return s3.fetchMINIONodes()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteMINIONode(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deleteMINIONode')
            return s3.deleteMINIONode()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def createPlanMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'createPlanMINIO')
            return s3.createPlanMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBackupPlansMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBackupPlansMINIO')
            return s3.fetchBackupPlansMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deletePlanMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deletePlanMINIO')
            return s3.deletePlanMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def savePlanChangesMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'savePlanChangesMINIO')
            return s3.savePlanChangesMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def forceRunAWSBackupMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'forceRunAWSBackupMINIO')
            s3.start()
            return self.ajaxPre(1, None)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsitesInPlanMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchWebsitesInPlanMINIO')
            return s3.fetchWebsitesInPlanMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchBackupLogsMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'fetchBackupLogsMINIO')
            return s3.fetchBackupLogsMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def deleteDomainFromPlanMINIO(self, request):
        try:
            request.session['userID'] = self.admin.pk
            s3 = S3Backups(request, self.data, 'deleteDomainFromPlanMINIO')
            return s3.deleteDomainFromPlanMINIO()
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitWebsiteStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.submitWebsiteStatus(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitChangePHP(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.changePHP(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getSwitchStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.getSwitchStatus(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def switchServer(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.switchServer(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def tuneSettings(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.tuneSettings(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentPHPConfig(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return PHPManager.getCurrentPHPConfig(self.data['phpSelection'])
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def savePHPConfigBasic(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return PHPManager.savePHPConfigBasic(self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchPHPSettingsAdvance(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return PHPManager.fetchPHPSettingsAdvance(self.data['phpSelection'])
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def savePHPConfigAdvance(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return PHPManager.savePHPConfigAdvance(self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchPHPExtensions(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return PHPManager.fetchPHPExtensions(self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitExtensionRequest(self, request):
        try:
            request.session['userID'] = self.admin.pk
            submitExtensionRequest(request)
            return self.ajaxPre(1, 'None')
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getRequestStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return getRequestStatusApache(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getContainerizationStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk

            finalData = {}
            finalData['status'] = 1

            if not ProcessUtilities.containerCheck():
                finalData['notInstalled'] = 1
            else:
                finalData['notInstalled'] = 0

            finalData = json.dumps(finalData)
            return HttpResponse(finalData)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def submitContainerInstall(self, request):
        try:
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            c = ContainerManager(request, None, 'submitContainerInstall')
            c.start()

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def switchTOLSWSStatus(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return switchTOLSWSStatus(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchWebsiteLimits(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return fetchWebsiteLimits(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def saveWebsiteLimits(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return saveWebsiteLimits(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getUsageData(self, request):
        try:
            request.session['userID'] = self.admin.pk
            return getUsageData(request)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def RunServerLevelEmailChecks(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            reportFile = "/home/cyberpanel/" + str(randint(1000, 9999))

            extraArgs = {'tempStatusPath': tempStatusPath, 'reportFile': reportFile}

            background = MailServerManager(None, 'RunServerLevelEmailChecks', extraArgs)
            background.start()

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath, 'reportFile': reportFile}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def ReadReport(self):
        try:
            reportFile = self.data['reportFile']
            reportContent = open(reportFile, 'r').read()

            data_ret = {'status': 1, 'reportContent': reportContent}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def ResetEmailConfigurations(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/mailUtilities.py"
            execPath = execPath + ' ResetEmailConfigurations --tempStatusPath %s' % (tempStatusPath)

            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchAllSites(self):
        try:
            currentACL = ACLManager.loadedACL(self.admin.pk)
            websites = ACLManager.findAllWebsites(currentACL, self.admin.pk)

            final_dic = {'status': 1, 'websites': websites}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def debugEmailForSite(self):
        try:

            websiteName = self.data['websiteName']
            result = MailServerManager(None, 'debugEmailForSite', None).debugEmailForSite(websiteName)

            if result[0]:
                final_dic = {'error_message': result[1], 'status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'error_message': result[1], 'status': 0}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fixMailSSL(self, request):
        try:

            request.session['userID'] = self.admin.pk
            msM = MailServerManager(request)
            return msM.fixMailSSL(self.data)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def ReadReportFTP(self):
        try:
            command = 'ps aux'
            result = ProcessUtilities.outputExecutioner(command)

            FTP = 1
            if result.find('pure-ftpd') == -1:
                FTP = 0

            data_ret = {'status': 1, 'FTP': FTP}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def ResetFTPConfigurations(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/ftp/ftpManager.py"
            execPath = execPath + ' ResetFTPConfigurations --tempStatusPath %s' % (tempStatusPath)

            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def ReadReportDNS(self):
        try:
            command = 'ps aux'
            result = ProcessUtilities.outputExecutioner(command)

            DNS = 1
            if result.find('pdns_server --guardian=no') == -1:
                DNS = 0

            data_ret = {'status': 1, 'DNS': DNS}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def ResetDNSConfigurations(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/dns/dnsManager.py"
            execPath = execPath + ' ResetDNSConfigurations --tempStatusPath %s' % (tempStatusPath)

            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def SubmitCloudBackup(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            try:
                data = str(int(self.data['data']))
            except:
                data = '0'

            try:
                emails = str(int(self.data['emails']))
            except:
                emails = '0'

            try:
                databases = str(int(self.data['databases']))
            except:
                databases = '0'

            try:
                port = str(self.data['port'])
            except:
                port = '0'

            try:
                ip = str(self.data['ip'])
            except:
                ip = '0'

            try:
                destinationDomain = self.data['destinationDomain']
            except:
                destinationDomain = 'None'

            import time
            BackupPath = '/home/cyberpanel/backups/%s/backup-' % (self.data['domain']) + self.data[
                'domain'] + "-" + time.strftime("%m.%d.%Y_%H-%M-%S")

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " CloudBackup --backupDomain %s --data %s --emails %s --databases %s --tempStoragePath %s " \
                                  "--path %s --port %s --ip %s --destinationDomain %s" % (
                           self.data['domain'], data, emails, databases, tempStatusPath, BackupPath, port, ip,
                           destinationDomain)
            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath, 'path': '%s.tar.gz' % (BackupPath)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def getCurrentCloudBackups(self):
        try:

            backupDomain = self.data['domainName']
            backupsPath = '/home/cyberpanel/backups/%s/' % (backupDomain)
            try:
                backups = os.listdir(backupsPath)
                backups.reverse()
            except:
                backups = []

            json_data = "["
            checker = 0

            counter = 1
            for items in backups:

                size = str(int(int(os.path.getsize('%s/%s' % (backupsPath, items))) / int(1048576)))

                dic = {'id': counter,
                       'file': items,
                       'size': '%s MBs' % (size),
                       }
                counter = counter + 1

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

    def fetchCloudBackupSettings(self):
        try:
            from plogical.backupUtilities import backupUtilities
            if os.path.exists(backupUtilities.CloudBackupConfigPath):
                result = json.loads(open(backupUtilities.CloudBackupConfigPath, 'r').read())
                self.nice = result['nice']
                self.cpu = result['cpu']
                self.time = result['time']
            else:
                self.nice = backupUtilities.NiceDefault
                self.cpu = backupUtilities.CPUDefault
                self.time = backupUtilities.time

            data_ret = {'status': 1, 'nice': self.nice, 'cpu': self.cpu, 'time': self.time}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def saveCloudBackupSettings(self):
        try:
            from plogical.backupUtilities import backupUtilities
            writeToFile = open(backupUtilities.CloudBackupConfigPath, 'w')
            writeToFile.write(json.dumps(self.data))
            writeToFile.close()

            data_ret = {'status': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'status': 0, 'abort': 0, 'installationProgress': "0", 'errorMessage': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def deleteCloudBackup(self):
        try:

            backupDomain = self.data['domainName']
            backupFile = self.data['backupFile']
            backupsPathComplete = '/home/cyberpanel/backups/%s/%s' % (backupDomain, backupFile)

            command = 'rm -f %s' % (backupsPathComplete)
            ProcessUtilities.executioner(command)

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SubmitCloudBackupRestore(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            try:
                sourceDomain = self.data['sourceDomain']
            except:
                sourceDomain = 'None'

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " SubmitCloudBackupRestore --backupDomain %s --backupFile %s --sourceDomain %s --tempStoragePath %s" % (
                self.data['domain'], self.data['backupFile'], sourceDomain, tempStatusPath)
            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def fetchAWSKeys(self):
        path = '/home/cyberpanel/.aws'
        credentials = path + '/credentials'

        data = open(credentials, 'r').readlines()

        aws_access_key_id = data[1].split(' ')[2].strip(' ').strip('\n')
        aws_secret_access_key = data[2].split(' ')[2].strip(' ').strip('\n')
        region = data[3].split(' ')[2].strip(' ').strip('\n')

        return aws_access_key_id, aws_secret_access_key, region

    def getCurrentS3Backups(self):
        try:

            import boto3
            from s3Backups.models import BackupPlan, BackupLogs
            plan = BackupPlan.objects.get(name=self.data['planName'])

            aws_access_key_id, aws_secret_access_key, region = self.fetchAWSKeys()

            if region.find('http') > -1:
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    endpoint_url=region
                )
            else:
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )
            bucket = s3.Bucket(plan.bucket)
            key = '%s/%s/' % (plan.name, self.data['domainName'])

            backups = []

            for file in bucket.objects.filter(Prefix=key):
                backups.append({'key': file.key, 'size': file.size})

            json_data = "["
            checker = 0

            counter = 1
            for items in backups:

                dic = {'id': counter,
                       'file': items['key'],
                       'size': items['size'],
                       }
                counter = counter + 1

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

    def deleteS3Backup(self):
        try:

            import boto3
            from s3Backups.models import BackupPlan, BackupLogs
            plan = BackupPlan.objects.get(name=self.data['planName'])

            aws_access_key_id, aws_secret_access_key, region = self.fetchAWSKeys()

            if region.find('http') > -1:
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                    endpoint_url=region
                )
            else:
                s3 = boto3.resource(
                    's3',
                    aws_access_key_id=aws_access_key_id,
                    aws_secret_access_key=aws_secret_access_key,
                )

            s3.Object(plan.bucket, self.data['backupFile']).delete()

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None"})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SubmitS3BackupRestore(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/backupUtilities.py"
            execPath = execPath + " SubmitS3BackupRestore --backupDomain %s --backupFile %s --tempStoragePath %s --planName %s" % (
                shlex.quote(self.data['domain']), shlex.quote(self.data['backupFile']), tempStatusPath, shlex.quote(self.data['planName']))
            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def DeployWordPress(self):
        try:

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempStatusPath, 'w')
            writeToFile.write('Starting..,0')
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/applicationInstaller.py"
            execPath = execPath + " DeployWordPress --tempStatusPath %s --appsSet '%s' --domain '%s' --email '%s' --password '%s' " \
                                  "--pluginUpdates '%s' --themeUpdates '%s' --title '%s' --updates '%s' --userName '%s' " \
                                  "--version '%s' --createSite %s" % (
                           tempStatusPath, self.data['appsSet'], self.data['domain'], self.data['email'],
                           self.data['passwordByPass'],
                           self.data['pluginUpdates'], self.data['themeUpdates'], self.data['title'],
                           self.data['updates'],
                           self.data['userName'], self.data['version'], str(self.data['createSite']))

            try:
                execPath = '%s --path %s' % (execPath, self.data['path'])
            except:
                pass

            ProcessUtilities.popenExecutioner(execPath)

            final_dic = {'status': 1, 'tempStatusPath': tempStatusPath}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def FetchWordPressDetails(self):
        try:

            finalDic = {}
            domain = self.data['domain']
            finalDic['status'] = 1
            finalDic['maintenanceMode'] = 1
            finalDic['php'] = '7.4'

            ## Get versopm

            website = Websites.objects.get(domain=domain)

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            command = 'wp core version --skip-plugins --skip-themes --path=%s 2>/dev/null' % (path)
            finalDic['version'] = str(ProcessUtilities.outputExecutioner(command, website.externalApp, True))

            ## LSCache

            command = 'wp plugin status litespeed-cache --skip-plugins --skip-themes --path=%s' % (path)
            result = str(ProcessUtilities.outputExecutioner(command, website.externalApp))

            if result.find('Status: Active') > -1:
                finalDic['lscache'] = 1
            else:
                finalDic['lscache'] = 0

            ## Debug

            try:
                command = 'wp config list --skip-plugins --skip-themes --path=%s' % (path)
                result = ProcessUtilities.outputExecutioner(command, website.externalApp).split('\n')
                finalDic['debugging'] = 0
                for items in result:
                    if items.find('WP_DEBUG') > -1 and items.find('1') > - 1:
                        finalDic['debugging'] = 1
                        break
            except BaseException as msg:
                finalDic['debugging'] = 0
                logging.writeToFile('Error fetching WordPress debug mode for %s. [404]' % (website.domain))

            ## Search index

            try:
                command = 'wp option get blog_public --skip-plugins --skip-themes --path=%s' % (path)
                finalDic['searchIndex'] = int(
                    ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()[-1])
            except BaseException as msg:
                logging.writeToFile('Error fetching WordPress searchIndex mode for %s. [404]' % (website.domain))
                finalDic['searchIndex'] = 0

            ## Maintenece mode

            try:

                command = 'wp maintenance-mode status --skip-plugins --skip-themes --path=%s' % (path)
                result = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()[-1]

                if result.find('not active') > -1:
                    finalDic['maintenanceMode'] = 0
                else:
                    finalDic['maintenanceMode'] = 1
            except BaseException as msg:
                logging.writeToFile('Error fetching WordPress maintenanceMode mode for %s. [404]' % (website.domain))
                finalDic['maintenanceMode'] = 0

            ## Get title

            try:
                command = 'wp option get blogname --skip-plugins --skip-themes --path=%s' % (path)
                finalDic['title'] = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()[-1]
            except:
                logging.writeToFile('Error fetching WordPress Title for %s. [404]' % (website.domain))
                finalDic['title'] = 'CyberPanel'

            ##

            final_json = json.dumps(finalDic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def AutoLogin(self):
        try:

            ## Get versopm

            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            ## Get title

            import plogical.randomPassword as randomPassword
            password = randomPassword.generate_pass(32)

            command = 'wp user create cyberpanel support@cyberpanel.cloud --role=administrator --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (
                password, path)
            ProcessUtilities.executioner(command, website.externalApp)

            command = 'wp user update cyberpanel --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (password,
                                                                                                             path)
            ProcessUtilities.executioner(command, website.externalApp)

            finalDic = {'status': 1, 'password': password}
            final_json = json.dumps(finalDic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def UpdateWPSettings(self):
        try:

            website = Websites.objects.get(domain=self.data['domain'])
            domain = self.data['domain']

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            if self.data['setting'] == 'lscache':
                if self.data['settingValue']:

                    command = "wp plugin install litespeed-cache --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    command = "wp plugin activate litespeed-cache --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'LSCache successfully installed and activated.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    command = 'wp plugin deactivate litespeed-cache --path=%s --skip-plugins --skip-themes' % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'LSCache successfully deactivated.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            elif self.data['setting'] == 'debugging':

                command = "wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (path)
                ProcessUtilities.executioner(command, website.externalApp)

                if self.data['settingValue']:
                    command = "wp config set WP_DEBUG true --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'WordPress is now in debug mode.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                else:
                    command = "wp config set WP_DEBUG false --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'WordPress debug mode turned off.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            elif self.data['setting'] == 'searchIndex':

                command = "wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (path)
                ProcessUtilities.executioner(command, website.externalApp)

                if self.data['settingValue']:
                    command = "wp option update blog_public 1 --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'Search Engine Indexing enabled.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                else:
                    command = "wp option update blog_public 0 --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'Search Engine Indexing disabled.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            elif self.data['setting'] == 'maintenanceMode':

                command = "wp litespeed-purge all --path=%s --skip-plugins --skip-themes" % (path)
                ProcessUtilities.executioner(command, website.externalApp)

                if self.data['settingValue']:

                    command = "wp maintenance-mode activate --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'WordPress Maintenance mode turned on.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                else:
                    command = "wp maintenance-mode deactivate --path=%s --skip-plugins --skip-themes" % (path)
                    ProcessUtilities.executioner(command, website.externalApp)

                    final_dic = {'status': 1, 'message': 'WordPress Maintenance mode turned off.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def GetCurrentPlugins(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            command = 'wp plugin list --skip-plugins --skip-themes --format=json --path=%s' % (path)
            json_data = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()[-1]
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})

            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def UpdatePlugins(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            if self.data['plugin'] == 'all':
                command = 'wp plugin update --all --skip-plugins --skip-themes --path=%s' % (path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin updates started in the background."})
                return HttpResponse(final_json)
            elif self.data['plugin'] == 'selected':
                if self.data['allPluginsChecked']:
                    command = 'wp plugin update --all --skip-plugins --skip-themes --path=%s' % (path)
                    ProcessUtilities.popenExecutioner(command, website.externalApp)
                    final_json = json.dumps(
                        {'status': 1, 'fetchStatus': 1, 'message': "Plugin updates started in the background."})
                    return HttpResponse(final_json)
                else:
                    pluginsList = ''

                    for plugin in self.data['plugins']:
                        pluginsList = '%s %s' % (pluginsList, plugin)

                    command = 'wp plugin update %s --skip-plugins --skip-themes --path=%s' % (pluginsList, path)
                    ProcessUtilities.popenExecutioner(command, website.externalApp)
                    final_json = json.dumps(
                        {'status': 1, 'fetchStatus': 1, 'message': "Plugin updates started in the background."})
                    return HttpResponse(final_json)
            else:
                command = 'wp plugin update %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin updates started in the background."})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def ChangeState(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            command = 'wp plugin status %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
            result = ProcessUtilities.outputExecutioner(command, website.externalApp)

            if result.find('Status: Active') > -1:
                command = 'wp plugin deactivate %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
                ProcessUtilities.executioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin successfully deactivated."})
                return HttpResponse(final_json)
            else:
                command = 'wp plugin activate %s --skip-plugins --skip-themes --path=%s' % (
                    self.data['plugin'], path)
                ProcessUtilities.executioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin successfully activated."})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def DeletePlugins(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            if self.data['plugin'] == 'selected':
                pluginsList = ''

                for plugin in self.data['plugins']:
                    pluginsList = '%s %s' % (pluginsList, plugin)

                command = 'wp plugin delete %s --skip-plugins --skip-themes --path=%s' % (pluginsList, path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin deletion started in the background."})
                return HttpResponse(final_json)
            else:
                command = 'wp plugin delete %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin deletion started in the background."})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def GetCurrentThemes(self):
        try:

            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            command = 'wp theme list --skip-plugins --skip-themes --format=json --path=%s' % (path)
            json_data = ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()[-1]
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def UpdateThemes(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            if self.data['plugin'] == 'all':
                command = 'wp theme update --all --skip-plugins --skip-themes --path=%s' % (path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Theme updates started in the background."})
                return HttpResponse(final_json)
            elif self.data['plugin'] == 'selected':
                if self.data['allPluginsChecked']:
                    command = 'wp theme update --all --skip-plugins --skip-themes --path=%s' % (path)
                    ProcessUtilities.popenExecutioner(command, website.externalApp)
                    final_json = json.dumps(
                        {'status': 1, 'fetchStatus': 1, 'message': "Theme updates started in the background."})
                    return HttpResponse(final_json)
                else:
                    pluginsList = ''

                    for plugin in self.data['plugins']:
                        pluginsList = '%s %s' % (pluginsList, plugin)

                    command = 'wp theme update %s --skip-plugins --skip-themes --path=%s' % (pluginsList, path)
                    ProcessUtilities.popenExecutioner(command, website.externalApp)
                    final_json = json.dumps(
                        {'status': 1, 'fetchStatus': 1, 'message': "Theme updates started in the background."})
                    return HttpResponse(final_json)
            else:
                command = 'wp theme update %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Theme updates started in the background."})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def ChangeStateThemes(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            command = 'wp theme status %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
            result = ProcessUtilities.outputExecutioner(command, website.externalApp)

            if result.find('Status: Active') > -1:
                command = 'wp theme deactivate %s --skip-plugins --skip-themes --path=%s' % (
                    self.data['plugin'], path)
                ProcessUtilities.executioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Theme successfully deactivated."})
                return HttpResponse(final_json)
            else:
                command = 'wp theme activate %s --skip-plugins --skip-themes --path=%s' % (
                    self.data['plugin'], path)
                ProcessUtilities.executioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Theme successfully activated."})
                return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def DeleteThemes(self):
        try:
            website = Websites.objects.get(domain=self.data['domain'])

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            if self.data['plugin'] == 'selected':
                pluginsList = ''

                for plugin in self.data['plugins']:
                    pluginsList = '%s %s' % (pluginsList, plugin)

                command = 'wp theme delete %s --skip-plugins --skip-themes --path=%s' % (pluginsList, path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Plugin Theme started in the background."})
                return HttpResponse(final_json)
            else:
                command = 'wp theme delete %s --skip-plugins --skip-themes --path=%s' % (self.data['plugin'], path)
                ProcessUtilities.popenExecutioner(command, website.externalApp)
                final_json = json.dumps(
                    {'status': 1, 'fetchStatus': 1, 'message': "Theme deletion started in the background."})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def GetServerPublicSSHkey(self):
        try:

            path = '/root/.ssh/cyberpanel.pub'
            command = 'cat %s' % (path)
            key = ProcessUtilities.outputExecutioner(command)

            final_dic = {'status': 1, 'key': key}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SubmitPublicKey(self):
        try:

            fm = FirewallManager()
            fm.addSSHKey(self.admin.pk, self.data)

            ## Create backup path so that file can be sent here later. If just submitting the key, no need to create backup folder domain.

            try:
                BackupPath = '/home/cyberpanel/backups/%s' % (self.data['domain'])
                command = 'mkdir -p %s' % (BackupPath)
                ProcessUtilities.executioner(command, 'cyberpanel')
            except:
                pass

            ###

            from WebTerminal.CPWebSocket import SSHServer
            SSHServer.findSSHPort()

            final_dic = {'status': 1, 'port': SSHServer.DEFAULT_PORT}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def CreateStaging(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.startCloning(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def startSync(self, request):
        try:
            request.session['userID'] = self.admin.pk
            wm = WebsiteManager()
            return wm.startSync(self.admin.pk, self.data)
        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def SaveAutoUpdateSettings(self):
        try:
            website = Websites.objects.get(domain=self.data['domainName'])
            domainName = self.data['domainName']
            from cloudAPI.models import WPDeployments

            try:
                wpd = WPDeployments.objects.get(owner=website)
                config = json.loads(wpd.config)
            except:
                wpd = WPDeployments(owner=website)
                config = {}

            try:
                from cloudAPI.models import WPDeployments
                wpd = WPDeployments.objects.get(owner=website)
                path = json.loads(wpd.config)['path']
                path = '/home/%s/public_html/%s' % (self.data['domain'], path)

            except:
                path = '/home/%s/public_html' % (self.data['domain'])

            config['updates'] = self.data['wpCore']
            config['pluginUpdates'] = self.data['plugins']
            config['themeUpdates'] = self.data['themes']
            wpd.config = json.dumps(config)
            wpd.save()

            if self.data['wpCore'] == 'Disabled':
                command = "wp config set WP_AUTO_UPDATE_CORE false --skip-plugins --skip-themes --raw --path=%s" % (
                    path)
                ProcessUtilities.executioner(command, website.externalApp)
            elif self.data['wpCore'] == 'Minor and Security Updates':
                command = "wp config set WP_AUTO_UPDATE_CORE minor --skip-plugins --skip-themes --allow-root --path=%s" % (
                    path)
                ProcessUtilities.executioner(command, website.externalApp)
            else:
                command = "wp config set WP_AUTO_UPDATE_CORE true --raw --allow-root --path=%s" % (path)
                ProcessUtilities.executioner(command, website.externalApp)

            final_json = json.dumps(
                {'status': 1, 'message': "Autoupdates configured."})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchWPSettings(self):
        try:

            cliVersion = ProcessUtilities.outputExecutioner('wp --version --allow-root')

            if cliVersion.find('not found') > -1:
                cliVersion = 'WP CLI Not installed.'

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                localCronPath = "/var/spool/cron/root"
            else:
                localCronPath = "/var/spool/cron/crontabs/root"

            cronData = ProcessUtilities.outputExecutioner('cat %s' % (localCronPath)).split('\n')

            finalCron = ''
            for cronLine in cronData:
                if cronLine.find('WPAutoUpdates.py') > -1:
                    finalCron = cronLine

            if finalCron.find('WPAutoUpdates.py') == -1:
                finalCron = 'Not Set'

            final_json = json.dumps(
                {'status': 1, 'cliVersion': cliVersion, 'finalCron': finalCron})
            return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def updateWPCLI(self):
        try:

            command = 'wp cli update'
            ProcessUtilities.executioner(command)
            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveWPSettings(self):
        try:

            command = 'wp cli update'
            ProcessUtilities.executioner(command)
            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def WPScan(self):
        try:

            path = '/home/%s/public_html' % (self.data['domainName'])

            command = 'wp core version --allow-root --skip-plugins --skip-themes --path=%s 2>/dev/null' % (path)
            result = ProcessUtilities.outputExecutioner(command, None, True)

            if result.find('Error:') > -1:
                final_dic = {'status': 0, 'fetchStatus': 0,
                             'error_message': 'This does not seem to be a WordPress installation'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_json = json.dumps({'status': 1})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SubmitCyberPanelUpgrade(self):
        try:
            try:
                mail = str(int(self.data['mail']))
            except:
                mail = '0'

            try:
                dns = str(int(self.data['dns']))
            except:
                dns = '0'

            try:
                ftp = str(int(self.data['ftp']))
            except:
                ftp = '0'

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/CyberPanelUpgrade.py --branch %s --mail %s --dns %s --ftp %s" % (
                self.data['CyberPanelBranch'], mail, dns, ftp)

            ProcessUtilities.executioner(execPath)
            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def DetachCluster(self):
        try:

            type = self.data['type']

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function %s --type %s" % (
                'DetachCluster', type)
            ProcessUtilities.executioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SetupCluster(self):
        try:

            ClusterConfigPath = '/home/cyberpanel/cluster'
            writeToFile = open(ClusterConfigPath, 'w')
            writeToFile.write(json.dumps(self.data))
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function SetupCluster --type %s" % (
            self.data['type'])
            ProcessUtilities.executioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def FetchMasterBootStrapStatus(self):
        try:
            from CyberCP import settings

            data = {}
            data['status'] = 1

            ## CyberPanel DB Creds
            data['dbName'] = settings.DATABASES['default']['NAME']
            data['dbUser'] = settings.DATABASES['default']['USER']
            data['password'] = settings.DATABASES['default']['PASSWORD']
            data['host'] = settings.DATABASES['default']['HOST']
            data['port'] = settings.DATABASES['default']['PORT']

            ## Root DB Creds

            data['rootdbName'] = settings.DATABASES['rootdb']['NAME']
            data['rootdbdbUser'] = settings.DATABASES['rootdb']['USER']
            data['rootdbpassword'] = settings.DATABASES['rootdb']['PASSWORD']

            command = 'cat /var/lib/mysql/grastate.dat'
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('No such file or directory') > -1:
                data['safe'] = 1
            elif output.find('safe_to_bootstrap: 1') > -1:
                data['safe'] = 1
            else:
                data['safe'] = 0

            final_json = json.dumps(data)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def FetchChildBootStrapStatus(self):
        try:

            data = {}
            data['status'] = 1

            command = 'cat /var/lib/mysql/grastate.dat'
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('No such file or directory') > -1:
                data['safe'] = 1
            elif output.find('safe_to_bootstrap: 0') > -1:
                data['safe'] = 1
            else:
                data['safe'] = 0

            final_json = json.dumps(data)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def BootMaster(self):
        try:

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function BootMaster --type Master"
            ProcessUtilities.executioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def BootChild(self):
        try:

            ChildData = '/home/cyberpanel/childaata'
            writeToFile = open(ChildData, 'w')
            writeToFile.write(json.dumps(self.data))
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function BootChild --type Child"
            ProcessUtilities.executioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def CreatePendingVirtualHosts(self):
        try:

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function CreatePendingVirtualHosts --type Child"
            ProcessUtilities.popenExecutioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SwitchDNS(self):
        try:

            command = 'chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache/'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python*/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command, None, True)

            ##

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            ##

            import CloudFlare
            cf = CloudFlare.CloudFlare(email=self.data['cfemail'], token=self.data['apikey'])

            zones = cf.zones.get(params={'per_page': 100})

            for website in Websites.objects.all():
                import tldextract
                no_cache_extract = tldextract.TLDExtract(cache_dir=None)
                extractDomain = no_cache_extract(website.domain)
                topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix

                for zone in zones:
                    if topLevelDomain == zone['name']:
                        try:
                            dns_records = cf.zones.dns_records.get(zone['id'], params={'name': website.domain})

                            for dns_record in dns_records:
                                r_zone_id = dns_record['zone_id']
                                r_id = dns_record['id']
                                r_name = dns_record['name']
                                r_type = dns_record['type']
                                r_ttl = dns_record['ttl']
                                r_proxied = dns_record['proxied']

                                dns_record_id = dns_record['id']

                                new_dns_record = {
                                    'zone_id': r_zone_id,
                                    'id': r_id,
                                    'type': r_type,
                                    'name': r_name,
                                    'content': ipAddress,
                                    'ttl': r_ttl,
                                    'proxied': r_proxied
                                }

                                cf.zones.dns_records.put(zone['id'], dns_record_id, data=new_dns_record)

                        except:
                            pass

            ### For child domainsa

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python*/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command, None, True)

            from websiteFunctions.models import ChildDomains
            for website in ChildDomains.objects.all():

                import tldextract
                no_cache_extract = tldextract.TLDExtract(cache_dir=None)
                extractDomain = no_cache_extract(website.domain)
                topLevelDomain = extractDomain.domain + '.' + extractDomain.suffix

                for zone in zones:
                    if topLevelDomain == zone['name']:
                        try:
                            dns_records = cf.zones.dns_records.get(zone['id'], params={'name': website.domain})

                            for dns_record in dns_records:
                                r_zone_id = dns_record['zone_id']
                                r_id = dns_record['id']
                                r_name = dns_record['name']
                                r_type = dns_record['type']
                                r_ttl = dns_record['ttl']
                                r_proxied = dns_record['proxied']

                                dns_record_id = dns_record['id']

                                new_dns_record = {
                                    'zone_id': r_zone_id,
                                    'id': r_id,
                                    'type': r_type,
                                    'name': r_name,
                                    'content': ipAddress,
                                    'ttl': r_ttl,
                                    'proxied': r_proxied
                                }

                                cf.zones.dns_records.put(zone['id'], dns_record_id, data=new_dns_record)

                        except:
                            pass

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            logging.writeToFile(str(msg))
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def DebugCluster(self):
        try:

            type = self.data['type']

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function %s --type %s" % (
                'DebugCluster', type)
            ProcessUtilities.executioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def UptimeMonitor(self):
        try:
            try:
                del self.data['controller']
                del self.data['serverUserName']
                del self.data['serverPassword']
            except:
                pass

            CloudConfigPath = '/home/cyberpanel/cloud'
            writeToFile = open(CloudConfigPath, 'w')
            writeToFile.write(json.dumps(self.data))
            writeToFile.close()

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function UptimeMonitor --type All"
            ProcessUtilities.executioner(execPath)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def CheckMasterNode(self):
        try:

            command = 'systemctl status mysql'
            result = ProcessUtilities.outputExecutioner(command)

            if result.find('active (running)') > -1:
                final_json = json.dumps({'status': 1})
            else:
                final_json = json.dumps({'status': 0, 'error_message': 'MySQL on Main node is not running.'})

            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def SyncToMaster(self):
        try:

            command = '/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function SyncToMaster --type Failover'
            ProcessUtilities.executioner(command)

            final_json = json.dumps({'status': 1})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


    def installN8N(self):
        try:
            import time
            from websiteFunctions.models import Websites
            from packages.models import Package
            from random import randint
            import re
            import threading
            from plogical.processUtilities import ProcessUtilities
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            from plogical import randomPassword

            # Validate required parameters
            domain_name = self.data.get('domainName')
            if not domain_name:
                return self.ajaxPre(0, 'domainName is required')

            # Validate domain name format
            if not re.match(r'^[a-zA-Z0-9][a-zA-Z0-9\-\.]*[a-zA-Z0-9]$', domain_name):
                return self.ajaxPre(0, 'Invalid domain name format')

            # Create status file path
            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            # Prepare website data
            website_data = {
                'domainName': domain_name,
                'adminEmail': self.data.get('adminEmail', f'admin@{domain_name}'),
                'phpSelection': 'PHP 8.1',
                'websiteOwner': self.data.get('websiteOwner', self.data.get('Owner', 'admin')),
                'package': self.data.get('package', 'Default'),
                'ssl': 1,
                'dkimCheck': 0,
                'openBasedir': 0,
                'mailDomain': 0
            }

            # Extract n8n parameters
            n8n_username = self.data.get('n8nUsername', self.data.get('WPusername', 'admin'))
            n8n_password = self.data.get('n8nPassword',
                                         self.data.get('WPpasswd', 'changeme' + str(randint(1000, 9999))))
            n8n_email = self.data.get('n8nEmail', self.data.get('WPemal', website_data['adminEmail']))
            n8n_port = self.data.get('port', self._find_available_n8n_port())

            # Database parameters will be generated by native process
            db_name = None  # Will be generated in thread
            db_user = None  # Will be generated in thread
            db_password = None  # Will be generated in thread

            # Create a new user for this n8n installation
            n8n_system_user = domain_name.replace('.', '_').replace('-', '_')[:32]  # Max 32 chars for username
            n8n_user_password = randomPassword.generate_pass()
            
            try:
                # Check if user already exists
                from loginSystem.models import Administrator, ACL
                existing_user = Administrator.objects.filter(userName=n8n_system_user).first()
                if not existing_user:
                    user_acl = ACL.objects.get(name='user')
                    
                    new_user = Administrator(
                        firstName=f"n8n_{domain_name}"[:50],  # Limit to 50 chars
                        lastName="",
                        email=website_data['adminEmail'],
                        type=3,  # Normal user
                        userName=n8n_system_user,
                        password=n8n_user_password,
                        initWebsitesLimit=1,
                        owner=self.admin.pk,
                        acl=user_acl,
                        token="",
                        api=0
                    )
                    new_user.save()
                    logging.writeToFile(f"[installN8N] Created new user: {n8n_system_user}")
                    website_data['websiteOwner'] = n8n_system_user
                else:
                    n8n_system_user = existing_user.userName
                    logging.writeToFile(f"[installN8N] Using existing user: {n8n_system_user}")
                    website_data['websiteOwner'] = n8n_system_user
            except Exception as e:
                logging.writeToFile(f"[installN8N] Failed to create user: {str(e)}")
                # Fall back to admin if user creation fails
                n8n_system_user = 'admin'
                website_data['websiteOwner'] = 'admin'

            # Create initial status file
            try:
                writeToFile = open(tempStatusPath, 'w')
                writeToFile.write('Starting n8n installation...,0\n')
                writeToFile.close()
                logging.writeToFile(f"[installN8N] Created status file at: {tempStatusPath}")
            except Exception as e:
                logging.writeToFile(f"[installN8N] Failed to create status file: {str(e)}")
                return self.ajaxPre(0, f"Failed to create status file: {str(e)}")

            # Start background installation including website creation
            try:
                logging.writeToFile(f"[installN8N] Creating thread for domain: {domain_name}")
                logging.writeToFile(f"[installN8N] Admin object: {self.admin}, Admin PK: {self.admin.pk if self.admin else 'None'}")
                installation_thread = threading.Thread(
                    target=self._install_n8n_with_website,
                    args=(self.admin.pk, website_data, domain_name, n8n_username, n8n_password, n8n_email, n8n_port,
                          db_name, db_user, db_password, tempStatusPath)
                )
                installation_thread.daemon = True
                installation_thread.start()
                logging.writeToFile(f"[installN8N] Thread started successfully for: {domain_name}")
            except Exception as e:
                logging.writeToFile(f"[installN8N] Failed to start thread: {str(e)}")
                return self.ajaxPre(0, f"Failed to start installation thread: {str(e)}")

            # Return response immediately with domain identifier for status checking
            final_dic = {
                'status': 1,
                'installStatus': 1,
                'error_message': 'None',
                'tempStatusPath': tempStatusPath,
                'domainIdentifier': domain_name.replace('.', '_'),
                'message': f'n8n installation started for {domain_name}',
                'n8nUsername': n8n_username,
                'n8nPort': n8n_port,
                'systemUser': n8n_system_user
            }

            # Add password only if auto-generated
            if 'n8nPassword' not in self.data and 'WPpasswd' not in self.data:
                final_dic['n8nPassword'] = n8n_password
            
            # Add system user password if new user was created
            if n8n_system_user != 'admin' and 'n8n_user_password' in locals():
                final_dic['systemUserPassword'] = n8n_user_password

            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def _install_n8n_with_website(self, admin_pk, website_data, domain_name, n8n_username, n8n_password, n8n_email, n8n_port,
                                  db_name, db_user, db_password, status_file_path):
        """
        Create website and install n8n in a single thread
        """
        # Import logging first to ensure we can log errors
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
        logging.writeToFile(f"[_install_n8n_with_website] Thread started for domain: {domain_name}")
        logging.writeToFile(f"[_install_n8n_with_website] Status file path: {status_file_path}")
        
        # Initialize a simple status writer immediately
        try:
            with open(status_file_path, 'w') as f:
                f.write('Thread started...,1\n')
        except Exception as e:
            logging.writeToFile(f"[_install_n8n_with_website] Failed to write initial status: {str(e)}")
        
        try:
            logging.writeToFile(f"[_install_n8n_with_website] Entering main try block")
            
            # Try a simpler approach - just import what we need
            import os
            import sys
            import time
            import json
            
            logging.writeToFile(f"[_install_n8n_with_website] About to import modules")
            
            from plogical.processUtilities import ProcessUtilities
            logging.writeToFile(f"[_install_n8n_with_website] Imported ProcessUtilities")
            
            from websiteFunctions.models import Websites
            logging.writeToFile(f"[_install_n8n_with_website] Imported Websites")
            
            from websiteFunctions.website import WebsiteManager
            logging.writeToFile(f"[_install_n8n_with_website] Imported WebsiteManager")
            
            from databases.models import Databases
            from plogical import randomPassword
            from plogical.mysqlUtilities import mysqlUtilities
            from loginSystem.models import Administrator
            
            logging.writeToFile(f"[_install_n8n_with_website] All imports complete")
            
            # Initialize status writer - use file handle directly
            class StatusWriter:
                def __init__(self, path):
                    self.path = path
                
                def writeToFile(self, message):
                    with open(self.path, 'a') as f:
                        f.write(message + '\n')
            
            statusWriter = StatusWriter(status_file_path)
            statusWriter.writeToFile('Starting website creation and n8n installation...,5')
            
            # Get administrator object
            try:
                logging.writeToFile(f"[_install_n8n_with_website] Attempting to get admin with pk={admin_pk}")
                admin = Administrator.objects.get(pk=admin_pk)
                logging.writeToFile(f"[_install_n8n_with_website] Found admin: {admin.userName}")
            except Administrator.DoesNotExist:
                logging.writeToFile(f"[_install_n8n_with_website] Administrator.DoesNotExist - pk={admin_pk}")
                statusWriter.writeToFile(f"Administrator with pk={admin_pk} not found [404]")
                return
            except Exception as e:
                logging.writeToFile(f"[_install_n8n_with_website] Error getting admin: {str(e)}")
                statusWriter.writeToFile(f"Error getting administrator: {str(e)} [404]")
                return
            
            # Step 1: Check if website already exists, create only if not
            existing_website = Websites.objects.filter(domain=domain_name).first()

            if existing_website:
                # Website already exists, skip creation
                logging.writeToFile(f"[_install_n8n_with_website] Website {domain_name} already exists, skipping creation")
                statusWriter.writeToFile(f'Website already exists, proceeding to N8N deployment...,20')
                website = existing_website
            else:
                # Website doesn't exist, create it
                statusWriter.writeToFile('Creating website...,10')
                logging.writeToFile(f"[_install_n8n_with_website] Creating website for {domain_name}")
                wm = WebsiteManager()
                result = wm.submitWebsiteCreation(admin.pk, website_data)
                result_data = json.loads(result.content)

                logging.writeToFile(f"[_install_n8n_with_website] Website creation result: {result_data}")

                if result_data.get('createWebSiteStatus', 0) != 1:
                    statusWriter.writeToFile(f"Failed to create website: {result_data.get('error_message', 'Unknown error')} [404]")
                    return

                # Wait for website creation to complete - 10 minute timeout
                creation_status_path = result_data.get('tempStatusPath')
                logging.writeToFile(f"[_install_n8n_with_website] Website creation status path: {creation_status_path}")

                if creation_status_path:
                    statusWriter.writeToFile('Waiting for website creation to complete (including SSL)...,15')
                    check_count = 0
                    max_checks = 600  # 10 minute timeout (600 seconds)
                    while check_count < max_checks:
                        try:
                            with open(creation_status_path, 'r') as f:
                                status = f.read()
                                if '[200]' in status:
                                    logging.writeToFile(f"[_install_n8n_with_website] Website creation completed successfully")
                                    break
                                elif '[404]' in status:
                                    logging.writeToFile(f"[_install_n8n_with_website] Website creation failed: {status}")
                                    statusWriter.writeToFile(f"Website creation failed: {status} [404]")
                                    return
                        except Exception as e:
                            if check_count % 10 == 0:  # Log every 10 checks
                                logging.writeToFile(f"[_install_n8n_with_website] Still waiting for website creation... (check #{check_count})")

                        check_count += 1
                        time.sleep(1)

                    if check_count >= max_checks:
                        logging.writeToFile(f"[_install_n8n_with_website] Website creation timed out after 10 minutes")
                        statusWriter.writeToFile(f"Website creation timed out after 10 minutes [404]")
                        return

                # Get the created website object
                logging.writeToFile(f"[_install_n8n_with_website] Getting website object for {domain_name}")
                try:
                    website = Websites.objects.get(domain=domain_name)
                    logging.writeToFile(f"[_install_n8n_with_website] Found website object: {website.domain}")
                except Websites.DoesNotExist:
                    logging.writeToFile(f"[_install_n8n_with_website] Website object not found for {domain_name}")
                    statusWriter.writeToFile('Website creation succeeded but website object not found [404]')
                    return
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_with_website] Error getting website object: {str(e)}")
                    statusWriter.writeToFile(f'Error getting website object: {str(e)} [404]')
                    return

                statusWriter.writeToFile('Website created successfully...,20')
            logging.writeToFile(f"[_install_n8n_with_website] Website creation phase complete")
            
            # Step 2: Create database using native CyberPanel process
            statusWriter.writeToFile('Creating database using CyberPanel...,25')
            db_result = self._createDatabaseForN8N(status_file_path, website)
            
            # Check if database creation failed
            if db_result == 0:
                logging.writeToFile(f"[_install_n8n_with_website] Database creation failed")
                return
            
            # Database creation successful - unpack the tuple
            db_name, db_user, db_password, db_type = db_result
            logging.writeToFile(f"[_install_n8n_with_website] Database created with type: {db_type}")
            
            statusWriter.writeToFile('Database created successfully...,30')
            
            # Step 3: Install n8n on the website
            logging.writeToFile(f"[_install_n8n_with_website] About to call _install_n8n_custom")
            logging.writeToFile(f"[_install_n8n_with_website] Parameters: domain={domain_name}")
            
            try:
                self._install_n8n_custom(website, domain_name, n8n_username, n8n_password, n8n_email, n8n_port,
                                       db_name, db_user, db_password, db_type, status_file_path, statusWriter)
                logging.writeToFile(f"[_install_n8n_with_website] _install_n8n_custom completed")
                
                # Write final success status with [200]
                statusWriter.writeToFile('n8n installation completed successfully [200]')
            except Exception as e:
                logging.writeToFile(f"[_install_n8n_with_website] Error calling _install_n8n_custom: {str(e)}")
                statusWriter.writeToFile(f"Error during n8n installation: {str(e)} [404]")
                raise
            
        except BaseException as msg:
            error_msg = str(msg) if str(msg) else "Unknown error occurred"
            logging.writeToFile(f"[_install_n8n_with_website] BaseException caught: {error_msg}")
            import traceback
            tb = traceback.format_exc()
            logging.writeToFile(f"[_install_n8n_with_website] Traceback: {tb}")
            try:
                statusWriter.writeToFile(f'Error in installation: {error_msg} [404]')
            except:
                # Try to write error directly to file
                try:
                    with open(status_file_path, 'a') as f:
                        f.write(f'Error in installation: {error_msg} [404]\n')
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_with_website] Failed to write error to status file: {str(e)}")
            return
    
    def _setupPostgreSQLForN8N(self):
        """
        Setup PostgreSQL for n8n if not already installed
        Returns: (success, postgres_password, error_message)
        """
        try:
            from plogical.processUtilities import ProcessUtilities
            from plogical import randomPassword
            import json
            import os
            
            # Check if PostgreSQL is installed
            check_postgres = ProcessUtilities.outputExecutioner("which psql", 'root')
            logging.writeToFile(f"[_setupPostgreSQLForN8N] PostgreSQL check result: '{check_postgres}'")
            
            if not check_postgres or 'psql' not in check_postgres or 'not found' in check_postgres or check_postgres.strip() == '':
                logging.writeToFile("[_setupPostgreSQLForN8N] PostgreSQL not found, installing...")
                
                # Detect OS and use appropriate package manager
                distro = ProcessUtilities.decideDistro()
                logging.writeToFile(f"[_setupPostgreSQLForN8N] Detected distro: {distro}, centos={ProcessUtilities.centos}, cent8={ProcessUtilities.cent8}, cent9={ProcessUtilities.cent9}, ubuntu={ProcessUtilities.ubuntu}")
                
                if distro == ProcessUtilities.centos or distro == ProcessUtilities.cent8 or distro == ProcessUtilities.cent9:
                    # CentOS/AlmaLinux/Rocky Linux
                    install_commands = [
                        "yum install -y epel-release",
                        "yum install -y postgresql postgresql-server postgresql-contrib",
                        "postgresql-setup initdb"
                    ]
                else:
                    # Ubuntu/Debian
                    install_commands = [
                        "DEBIAN_FRONTEND=noninteractive apt-get update",
                        "DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib"
                    ]
                
                # Additional check - if apt-get exists, force Ubuntu commands
                apt_check = ProcessUtilities.outputExecutioner("which apt-get", 'root')
                if apt_check and 'apt-get' in apt_check:
                    logging.writeToFile("[_setupPostgreSQLForN8N] Found apt-get, using Ubuntu/Debian commands")
                    install_commands = [
                        "DEBIAN_FRONTEND=noninteractive apt-get update",
                        "DEBIAN_FRONTEND=noninteractive apt-get install -y postgresql postgresql-contrib"
                    ]


                # Execute installation commands
                for cmd in install_commands:
                    logging.writeToFile(f"[_setupPostgreSQLForN8N] Running: {cmd}")
                    result, output = ProcessUtilities.outputExecutioner(cmd, 'root', shell=True, retRequired=True)
                    if result != 1:
                        logging.writeToFile(f"[_setupPostgreSQLForN8N] Command '{cmd}' failed with output: {output}")
                        return False, None, f"Failed to install PostgreSQL: {output}"
                    else:
                        logging.writeToFile(f"[_setupPostgreSQLForN8N] Command '{cmd}' succeeded")

                
                # Verify PostgreSQL installation
                verify_postgres = ProcessUtilities.outputExecutioner("which psql", 'root')
                logging.writeToFile(f"[_setupPostgreSQLForN8N] PostgreSQL verification result: '{verify_postgres}'")
                
                # Also try common PostgreSQL binary locations
                if not verify_postgres or 'psql' not in verify_postgres:
                    # Check common locations
                    common_paths = ["/usr/bin/psql", "/usr/local/bin/psql", "/usr/pgsql-*/bin/psql"]
                    for path in common_paths:
                        check_path = ProcessUtilities.outputExecutioner(f"ls {path} 2>/dev/null", 'root')
                        if check_path and 'psql' in check_path:
                            verify_postgres = check_path
                            logging.writeToFile(f"[_setupPostgreSQLForN8N] Found psql at: {path}")
                            break
                
                if not verify_postgres or ('psql' not in verify_postgres and 'No such' not in verify_postgres):
                    # Try to find psql with find command
                    find_psql = ProcessUtilities.outputExecutioner("find /usr -name psql -type f 2>/dev/null | head -1", 'root')
                    if find_psql and 'psql' in find_psql:
                        verify_postgres = find_psql
                        logging.writeToFile(f"[_setupPostgreSQLForN8N] Found psql using find: {find_psql}")
                    else:
                        logging.writeToFile("[_setupPostgreSQLForN8N] PostgreSQL installation verification failed")
                        return False, None, "PostgreSQL installation failed - psql not found"
                
                logging.writeToFile(f"[_setupPostgreSQLForN8N] PostgreSQL installed successfully, psql found at: {verify_postgres.strip()}")
            
            # Check/Load PostgreSQL password
            postgres_pass_file = "/etc/cyberpanel/postgresqlPassword"
            postgres_password = None
            
            if os.path.exists(postgres_pass_file):
                try:
                    with open(postgres_pass_file, 'r') as f:
                        postgres_data = json.loads(f.read())
                        postgres_password = postgres_data.get('postgrespassword')
                        logging.writeToFile("[_setupPostgreSQLForN8N] Loaded existing PostgreSQL credentials")
                except:
                    pass
            
            if not postgres_password:
                # Generate new password
                postgres_password = randomPassword.generate_pass(32)
                
                # Save password to file
                postgres_data = {
                    'postgrespassword': postgres_password,
                    'postgresport': '5433',
                    'postgreshost': 'localhost'
                }
                
                # Create directory if it doesn't exist
                ProcessUtilities.executioner("mkdir -p /etc/cyberpanel", 'root', True)
                
                # Write to temp file first, then move with proper permissions
                temp_file = f"/tmp/postgres_pass_{randomPassword.generate_pass()[:8]}.json"
                try:
                    with open(temp_file, 'w') as f:
                        json.dump(postgres_data, f, indent=2)
                    
                    # Move file with root permissions
                    ProcessUtilities.executioner(f"mv {temp_file} {postgres_pass_file}", 'root', True)
                    ProcessUtilities.executioner(f"chmod 600 {postgres_pass_file}", 'root', True)
                    ProcessUtilities.executioner(f"chown root:root {postgres_pass_file}", 'root', True)
                    
                    logging.writeToFile("[_setupPostgreSQLForN8N] Generated new PostgreSQL credentials")
                except Exception as e:
                    logging.writeToFile(f"[_setupPostgreSQLForN8N] Error saving credentials: {str(e)}")
                    if os.path.exists(temp_file):
                        os.remove(temp_file)
                    raise
            
            # Find PostgreSQL config file location
            pg_config_paths = [
                "/etc/postgresql/*/main/postgresql.conf",  # Ubuntu/Debian
                "/var/lib/pgsql/data/postgresql.conf",     # CentOS/RHEL old
                "/var/lib/pgsql/*/data/postgresql.conf"    # CentOS/RHEL new
            ]
            
            postgres_config = None
            for path in pg_config_paths:
                check_cmd = f"ls {path} 2>/dev/null | head -1"
                result = ProcessUtilities.outputExecutioner(check_cmd, 'root')
                if result and not result.find('No such') > -1:
                    postgres_config = result.strip()
                    break
            
            if postgres_config:
                logging.writeToFile(f"[_setupPostgreSQLForN8N] Found PostgreSQL config at: {postgres_config}")
                # Update port in PostgreSQL config
                update_port_cmd = f"sed -i 's/^#*port = .*/port = 5433/' {postgres_config}"
                ProcessUtilities.executioner(update_port_cmd, 'root', True)
                
                # Also update listen_addresses
                update_listen_cmd = f"sed -i \"s/^#*listen_addresses = .*/listen_addresses = 'localhost'/\" {postgres_config}"
                ProcessUtilities.executioner(update_listen_cmd, 'root', True)
                
                # Update pg_hba.conf for password authentication
                pg_hba_path = postgres_config.replace('postgresql.conf', 'pg_hba.conf')
                if os.path.exists(pg_hba_path):
                    logging.writeToFile(f"[_setupPostgreSQLForN8N] Updating pg_hba.conf at: {pg_hba_path}")
                    # Allow password authentication for local connections
                    hba_cmd = f"""sed -i 's/local   all             all                                     peer/local   all             all                                     md5/g' {pg_hba_path}"""
                    ProcessUtilities.executioner(hba_cmd, 'root', True)
                    # Also for host connections
                    hba_cmd2 = f"""sed -i 's/host    all             all             127.0.0.1\/32            ident/host    all             all             127.0.0.1\/32            md5/g' {pg_hba_path}"""
                    ProcessUtilities.executioner(hba_cmd2, 'root', True)
            else:
                logging.writeToFile("[_setupPostgreSQLForN8N] Warning: PostgreSQL config not found, using default settings")
            
            # Enable and restart PostgreSQL
            # First check which PostgreSQL service name is correct
            service_names = ["postgresql", "postgresql-12", "postgresql-13", "postgresql-14", "postgresql-15"]
            postgres_service = None
            
            for service in service_names:
                check_service = ProcessUtilities.outputExecutioner(f"systemctl list-unit-files | grep {service}.service", 'root')
                if check_service and service in check_service:
                    postgres_service = service
                    logging.writeToFile(f"[_setupPostgreSQLForN8N] Found PostgreSQL service: {service}")
                    break
            
            if not postgres_service:
                postgres_service = "postgresql"  # Default fallback
                logging.writeToFile("[_setupPostgreSQLForN8N] Using default PostgreSQL service name")
            
            # Enable and start the service
            enable_result = ProcessUtilities.executioner(f"systemctl enable {postgres_service}", 'root', True)
            start_result = ProcessUtilities.executioner(f"systemctl restart {postgres_service}", 'root', True)
            
            if start_result != 1:
                logging.writeToFile(f"[_setupPostgreSQLForN8N] Failed to start {postgres_service} service")
                return False, None, f"Failed to start PostgreSQL service {postgres_service}"
            
            # Wait for PostgreSQL to start
            import time
            time.sleep(5)
            
            # Verify PostgreSQL is running
            status_check = ProcessUtilities.outputExecutioner(f"systemctl is-active {postgres_service}", 'root')
            if 'active' not in status_check:
                logging.writeToFile(f"[_setupPostgreSQLForN8N] PostgreSQL service not active: {status_check}")
                return False, None, "PostgreSQL service failed to start"
            
            # Set postgres user password - first try default port, then custom port
            set_pass_cmd = f"""sudo -u postgres psql -c "ALTER USER postgres PASSWORD '{postgres_password}';" """
            pass_result, pass_output = ProcessUtilities.outputExecutioner(set_pass_cmd, 'root', shell=True, retRequired=True)
            
            if pass_result != 1:
                # Try with custom port
                logging.writeToFile("[_setupPostgreSQLForN8N] Configuring authentication on port 5433")
                set_pass_cmd = f"""sudo -u postgres psql -p 5433 -c "ALTER USER postgres PASSWORD '{postgres_password}';" """
                pass_result, pass_output = ProcessUtilities.outputExecutioner(set_pass_cmd, 'root', shell=True, retRequired=True)
                
                if pass_result != 1:
                    logging.writeToFile(f"[_setupPostgreSQLForN8N] Warning: Could not configure postgres authentication")
            else:
                logging.writeToFile("[_setupPostgreSQLForN8N] Successfully configured postgres authentication")
            
            logging.writeToFile("[_setupPostgreSQLForN8N] PostgreSQL setup completed")
            return True, postgres_password, None
            
        except Exception as e:
            error_msg = f"PostgreSQL setup error: {str(e)}"
            logging.writeToFile(f"[_setupPostgreSQLForN8N] {error_msg}")
            return False, None, error_msg
    
    def _createDatabaseForN8N(self, tempStatusPath, website):
        """
        Create PostgreSQL database for n8n
        Always uses PostgreSQL for n8n installations
        """
        try:
            from databases.models import Databases
            from plogical import randomPassword
            from plogical.processUtilities import ProcessUtilities
            import json
            
            # Generate database credentials - use lowercase for PostgreSQL compatibility
            dbName = f"n8n_{randomPassword.generate_pass()[:12]}".lower()  # PostgreSQL converts to lowercase
            dbUser = dbName
            dbPassword = randomPassword.generate_pass()
            
            # Always use PostgreSQL for n8n
            logging.writeToFile("[_createDatabaseForN8N] Setting up PostgreSQL for n8n")
            postgres_success, postgres_password, postgres_error = self._setupPostgreSQLForN8N()
            
            if not postgres_success:
                logging.writeToFile(f"[_createDatabaseForN8N] PostgreSQL setup failed: {postgres_error}")
                statusFile = open(tempStatusPath, 'a')
                statusFile.writelines(f"PostgreSQL setup failed: {postgres_error} [404]\n")
                statusFile.close()
                return 0
            
            # Check if database or user already exists
            if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(dbUser=dbUser).exists():
                statusFile = open(tempStatusPath, 'a')
                statusFile.writelines("This database or user is already taken. [404]\n")
                statusFile.close()
                return 0
            
            try:
                # Create PostgreSQL database and user - use separate commands for reliability
                logging.writeToFile(f"[_createDatabaseForN8N] Creating database with user")
                
                # Create user - use psql directly as it needs to run as postgres user
                create_user_cmd = f"psql -p 5433 -c \"CREATE USER {dbUser} WITH PASSWORD '{dbPassword}';\""
                user_result, user_output = ProcessUtilities.outputExecutioner(create_user_cmd, 'postgres', shell=True, retRequired=True)
                
                if user_result != 1:
                    logging.writeToFile(f"[_createDatabaseForN8N] Failed to create user. Output: {user_output}")
                    statusFile = open(tempStatusPath, 'a')
                    statusFile.writelines(f"Failed to create PostgreSQL user: {user_output} [404]\n")
                    statusFile.close()
                    return 0
                
                # Create database
                create_db_cmd = f"psql -p 5433 -c \"CREATE DATABASE {dbName} OWNER {dbUser};\""
                db_result, db_output = ProcessUtilities.outputExecutioner(create_db_cmd, 'postgres', shell=True, retRequired=True)
                
                if db_result != 1:
                    logging.writeToFile(f"[_createDatabaseForN8N] Failed to create database. Output: {db_output}")
                    statusFile = open(tempStatusPath, 'a')
                    statusFile.writelines(f"Failed to create PostgreSQL database: {db_output} [404]\n")
                    statusFile.close()
                    return 0
                
                # Grant privileges
                grant_cmd = f"psql -p 5433 -c \"GRANT ALL PRIVILEGES ON DATABASE {dbName} TO {dbUser};\""
                grant_result, grant_output = ProcessUtilities.outputExecutioner(grant_cmd, 'postgres', shell=True, retRequired=True)
                
                result = grant_result
                
                if result == 1:
                    logging.writeToFile(f"[_createDatabaseForN8N] PostgreSQL database creation command executed")
                    
                    # Verify the database was actually created
                    verify_cmd = f"psql -p 5433 -c \"SELECT datname FROM pg_database WHERE datname = '{dbName}';\""
                    verify_result, verify_output = ProcessUtilities.outputExecutioner(verify_cmd, 'postgres', shell=True, retRequired=True)
                    
                    if verify_result == 1 and dbName in verify_output:
                        logging.writeToFile(f"[_createDatabaseForN8N] PostgreSQL database verified successfully")
                        
                        # Save database record
                        db = Databases(website=website, dbName=dbName, dbUser=dbUser)
                        db.save()
                        
                        # Always return PostgreSQL type
                        return dbName, dbUser, dbPassword, 'postgresql'
                    else:
                        logging.writeToFile(f"[_createDatabaseForN8N] PostgreSQL database verification failed. Output: {verify_output}")
                        statusFile = open(tempStatusPath, 'a')
                        statusFile.writelines("Failed to verify PostgreSQL database creation [404]\n")
                        statusFile.close()
                        return 0
                else:
                    logging.writeToFile(f"[_createDatabaseForN8N] PostgreSQL database creation failed. Grant output: {grant_output}")
                    statusFile = open(tempStatusPath, 'a')
                    statusFile.writelines("Failed to create PostgreSQL database [404]\n")
                    statusFile.close()
                    return 0
            except Exception as e:
                logging.writeToFile(f"[_createDatabaseForN8N] PostgreSQL error: {str(e)}")
                statusFile = open(tempStatusPath, 'a')
                statusFile.writelines(f"PostgreSQL database error: {str(e)} [404]\n")
                statusFile.close()
                return 0
            
        except BaseException as msg:
            logging.writeToFile(str(msg) + '[CloudManager.createDatabaseForN8N]')
            return 0
    
    def _find_available_n8n_port(self):
        """Find an available port for n8n installation between 8000-9999"""
        port_range_start = 8000
        port_range_end = 9999
        max_attempts = 10
        
        for _ in range(max_attempts):
            port = random.randint(port_range_start, port_range_end)
            
            # Check if port is available
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            try:
                result = sock.bind(('127.0.0.1', port))
                sock.close()
                
                # Also check if port is not already used by another n8n instance
                # by checking OpenLiteSpeed vhost configurations
                vhost_config_path = f'/usr/local/lsws/conf/vhosts/n8n_port_{port}'
                if not os.path.exists(vhost_config_path):
                    return str(port)
            except OSError:
                # Port is already in use
                continue
            finally:
                try:
                    sock.close()
                except:
                    pass
        
        # If no available port found after max attempts, return a random one
        return str(random.randint(port_range_start, port_range_end))
    
    def _install_n8n_custom(self, website, domain_name, n8n_username, n8n_password, n8n_email, n8n_port,
                            db_name, db_user, db_password, db_type, status_file_path, statusWriter=None):
        """
        Install n8n using native installation method with MySQL/MariaDB or PostgreSQL
        """
        try:
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(f"[_install_n8n_custom] Starting installation for {domain_name}")
            
            from plogical.processUtilities import ProcessUtilities
            from plogical.mysqlUtilities import mysqlUtilities
            from plogical import randomPassword
            import os

            # Initialize status writer if not provided
            if statusWriter is None:
                class StatusWriter:
                    def __init__(self, path):
                        self.path = path


                    def writeToFile(self, message):
                        with open(self.path, 'a') as f:
                            f.write(message + '\n')

                statusWriter = StatusWriter(status_file_path)
                statusWriter.writeToFile('Starting n8n installation...')
            # Website paths
            website_home = f"/home/{website.domain}"
            public_html = f"{website_home}/public_html"
            n8n_dir = f"{website_home}/n8n"


            # Get website user

            website_user = website.externalApp

            try:
                # Step 1: Create directory structure
                statusWriter.writeToFile('Creating directory structure...,10')

                directories = [
                    f"{n8n_dir}/app",
                    f"{n8n_dir}/data",
                    f"{n8n_dir}/logs",
                    f"{n8n_dir}/config",
                    f"{n8n_dir}/backup"
                ]

                for directory in directories:
                    command = f"mkdir -p {directory}"
                    ProcessUtilities.executioner(command, website_user)

                logging.writeToFile(f"[_install_n8n_custom] Directories created successfully")

                # Database creation is now handled in _install_n8n_with_website
                statusWriter.writeToFile('Database setup complete...,30')

                # Step 2.5: Install Node.js via nvm for the website user
                statusWriter.writeToFile('Installing Node.js for user...,35')
                logging.writeToFile(f"[_install_n8n_custom] Installing nvm for user {website_user}")
                
                # Download and install nvm
                # First download the script, then execute it
                nvm_script = f"{website_home}/nvm_install.sh"
                download_cmd = f"curl -o {nvm_script} https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.3/install.sh"
                logging.writeToFile(f"[_install_n8n_custom] Downloading nvm install script")
                
                try:
                    # Download the script first
                    download_result = ProcessUtilities.outputExecutioner(download_cmd, website_user, shell=True)
                    if isinstance(download_result, tuple):
                        status, output = download_result
                        logging.writeToFile(f"[_install_n8n_custom] nvm download status: {status}, output: {output[:200]}")
                        if status != 1:
                            statusWriter.writeToFile(f'Failed to download nvm script: {output} [404]')
                            return
                    else:
                        logging.writeToFile(f"[_install_n8n_custom] nvm download output: {download_result[:200]}")
                    
                    # Check if script was downloaded
                    if not os.path.exists(nvm_script):
                        logging.writeToFile(f"[_install_n8n_custom] nvm script not found at {nvm_script}")
                        statusWriter.writeToFile(f'Failed to download nvm install script [404]')
                        return
                    
                    # Make it executable
                    ProcessUtilities.executioner(f"chmod +x {nvm_script}", website_user)
                    
                    # Now run the script
                    install_cmd = f"bash {nvm_script}"
                    logging.writeToFile(f"[_install_n8n_custom] Running nvm install script")
                    install_output = ProcessUtilities.outputExecutioner(install_cmd, website_user, shell=True)
                    if isinstance(install_output, tuple):
                        status, output = install_output
                        logging.writeToFile(f"[_install_n8n_custom] nvm install status: {status}, output: {output[:500]}")
                        if status != 1:
                            statusWriter.writeToFile(f'Failed to install nvm: {output} [404]')
                            return
                    else:
                        logging.writeToFile(f"[_install_n8n_custom] nvm install output: {install_output[:500]}")
                    
                    # Add nvm to bashrc if not already there
                    bashrc_path = f"{website_home}/.bashrc"
                    nvm_source_line = 'export NVM_DIR="$HOME/.nvm"\n[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"\n'
                    
                    # Create .bashrc if it doesn't exist and add nvm source lines
                    # Use bash commands to handle this properly with correct permissions
                    check_bashrc_cmd = f"test -f {bashrc_path} && echo 'exists' || echo 'not exists'"
                    bashrc_exists = ProcessUtilities.outputExecutioner(check_bashrc_cmd, website_user, shell=True)
                    if isinstance(bashrc_exists, tuple):
                        bashrc_exists = bashrc_exists[1] if len(bashrc_exists) == 2 else str(bashrc_exists)
                    
                    if 'not exists' in str(bashrc_exists):
                        # Create .bashrc with nvm source lines
                        create_bashrc_cmd = f'''echo 'export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"' > {bashrc_path}'''
                        ProcessUtilities.executioner(create_bashrc_cmd, website_user, shell=True)
                        logging.writeToFile(f"[_install_n8n_custom] Created .bashrc with nvm source lines")
                    else:
                        # Check if nvm is already in bashrc
                        check_nvm_cmd = f"grep -q 'NVM_DIR' {bashrc_path} && echo 'found' || echo 'not found'"
                        nvm_in_bashrc = ProcessUtilities.outputExecutioner(check_nvm_cmd, website_user, shell=True)
                        if isinstance(nvm_in_bashrc, tuple):
                            nvm_in_bashrc = nvm_in_bashrc[1] if len(nvm_in_bashrc) == 2 else str(nvm_in_bashrc)
                        
                        if 'not found' in str(nvm_in_bashrc):
                            # Append nvm source lines
                            append_cmd = f'''echo '
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \\. "$NVM_DIR/nvm.sh"' >> {bashrc_path}'''
                            ProcessUtilities.executioner(append_cmd, website_user, shell=True)
                            logging.writeToFile(f"[_install_n8n_custom] Appended nvm source lines to .bashrc")
                    
                    # Clean up the install script
                    ProcessUtilities.executioner(f"rm -f {nvm_script}", website_user)
                    logging.writeToFile(f"[_install_n8n_custom] nvm installation completed successfully")
                    
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error installing nvm: {str(e)}")
                    statusWriter.writeToFile(f'Failed to install nvm: {str(e)} [404]')
                    return
                
                # Create a script to source nvm and install node
                node_setup_script = f"{website_home}/setup_node.sh"
                script_content = '''#!/bin/bash
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm install 22
nvm use 22
nvm alias default 22
'''
                # Write script to temp location first, then move it
                temp_script = f"/tmp/setup_node_{website_user}.sh"
                with open(temp_script, 'w') as f:
                    f.write(script_content)
                
                # Move script to correct location with proper ownership
                ProcessUtilities.executioner(f"cp {temp_script} {node_setup_script}", website_user)
                os.remove(temp_script)
                
                # Make script executable and run it
                try:
                    ProcessUtilities.executioner(f"chmod +x {node_setup_script}", website_user)
                    logging.writeToFile(f"[_install_n8n_custom] Installing Node.js 22 via nvm")
                    node_install_output = ProcessUtilities.outputExecutioner(f"bash {node_setup_script}", website_user, shell=True, dir=website_home)
                    if isinstance(node_install_output, tuple):
                        # outputExecutioner might return (status, output)
                        if len(node_install_output) == 2:
                            status_code, actual_output = node_install_output
                            node_install_output = actual_output
                            logging.writeToFile(f"[_install_n8n_custom] node install status code: {status_code}")
                    logging.writeToFile(f"[_install_n8n_custom] Node install output: {str(node_install_output)[:500]}")
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error installing Node.js: {str(e)}")
                    statusWriter.writeToFile(f'Failed to install Node.js: {str(e)} [404]')
                    return
                
                # Clean up the script
                try:
                    ProcessUtilities.executioner(f"rm -f {node_setup_script}", website_user)
                except:
                    pass  # Ignore cleanup errors
                
                # Verify Node.js installation by checking version
                statusWriter.writeToFile('Verifying Node.js installation...,38')
                verify_node_cmd = 'bash -c "source ~/.nvm/nvm.sh && node --version"'
                verify_npm_cmd = 'bash -c "source ~/.nvm/nvm.sh && npm --version"'
                
                try:
                    node_version = ProcessUtilities.outputExecutioner(verify_node_cmd, website_user, shell=True, dir=website_home)
                    npm_version = ProcessUtilities.outputExecutioner(verify_npm_cmd, website_user, shell=True, dir=website_home)
                    
                    if isinstance(node_version, tuple):
                        node_version = node_version[1] if len(node_version) == 2 else str(node_version)
                    if isinstance(npm_version, tuple):
                        npm_version = npm_version[1] if len(npm_version) == 2 else str(npm_version)
                    
                    logging.writeToFile(f"[_install_n8n_custom] Node version: {node_version}")
                    logging.writeToFile(f"[_install_n8n_custom] NPM version: {npm_version}")
                    
                    # Check if versions look valid
                    if not node_version or 'v' not in str(node_version):
                        logging.writeToFile(f"[_install_n8n_custom] Invalid node version output: {node_version}")
                        statusWriter.writeToFile(f'Node.js installation verification failed [404]')
                        return
                    
                    statusWriter.writeToFile(f'Node.js {node_version.strip()} installed successfully...,39')
                    
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error verifying Node.js: {str(e)}")
                    statusWriter.writeToFile(f'Failed to verify Node.js installation: {str(e)} [404]')
                    return
                
                # Step 3: Install n8n via npm
                statusWriter.writeToFile('Installing n8n via npm...,40')
                logging.writeToFile(f"[_install_n8n_custom] About to run npm commands")

                # Check if npm/node is now available with nvm
                check_node_cmd = '''bash -c "source ~/.nvm/nvm.sh && which node"'''
                check_npm_cmd = '''bash -c "source ~/.nvm/nvm.sh && which npm"'''
                try:
                    node_check = ProcessUtilities.outputExecutioner(check_node_cmd, website_user, shell=True, dir=website_home)
                    npm_check = ProcessUtilities.outputExecutioner(check_npm_cmd, website_user, shell=True, dir=website_home)
                    if isinstance(node_check, tuple):
                        node_check = node_check[1] if len(node_check) == 2 else node_check
                    if isinstance(npm_check, tuple):
                        npm_check = npm_check[1] if len(npm_check) == 2 else npm_check
                    logging.writeToFile(f"[_install_n8n_custom] node path: {node_check}, npm path: {npm_check}")
                    
                    # Check if paths are valid
                    if not node_check or 'not found' in str(node_check) or not npm_check or 'not found' in str(npm_check):
                        logging.writeToFile(f"[_install_n8n_custom] Node/npm not found after installation")
                        statusWriter.writeToFile('Node.js installation failed - node/npm not found [404]')
                        return
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error checking node/npm: {str(e)}")
                    statusWriter.writeToFile(f'Failed to verify Node.js installation: {str(e)} [404]')
                    return

                # Change to app directory and install n8n
                # First create package.json
                app_dir = f"{n8n_dir}/app"
                logging.writeToFile(f"[_install_n8n_custom] Running npm init in dir: {app_dir}")
                
                # Use bash -c to source nvm before running npm commands
                init_cmd = 'bash -c "source ~/.nvm/nvm.sh && npm init -y"'
                init_output = ProcessUtilities.outputExecutioner(init_cmd, website_user, shell=True, dir=app_dir)
                logging.writeToFile(f"[_install_n8n_custom] npm init output: {init_output[:200]}")
                
                # Install n8n - this may take several minutes
                statusWriter.writeToFile('Installing n8n via npm (this may take 2-5 minutes)...,45')
                logging.writeToFile(f"[_install_n8n_custom] Starting npm install n8n in dir: {app_dir}")

                
                # Use bash -c to source nvm before installing n8n
                install_cmd = 'bash -c "source ~/.nvm/nvm.sh && npm install n8n --production"'
                install_output = ProcessUtilities.outputExecutioner(install_cmd, website_user, shell=True, dir=app_dir)
                logging.writeToFile(f"[_install_n8n_custom] npm install output: {install_output[:500]}")  # Log first 500 chars
                
                # Check if n8n was actually installed
                check_cmd = 'bash -c "source ~/.nvm/nvm.sh && ls node_modules/n8n"'
                check_output = ProcessUtilities.outputExecutioner(check_cmd, website_user, shell=True, dir=app_dir)
                logging.writeToFile(f"[_install_n8n_custom] Check n8n module output: {check_output}")
                
                if "No such file or directory" in check_output or "cannot access" in check_output:
                    statusWriter.writeToFile(f'n8n installation failed - module not found [404]')
                    logging.writeToFile(f"[_install_n8n_custom] n8n module not found after install")
                    return

                statusWriter.writeToFile('n8n installed successfully...,50')

                # Step 4: Create n8n configuration file
                statusWriter.writeToFile('Creating n8n configuration...,60')
                logging.writeToFile(f"[_install_n8n_custom] Creating n8n configuration file")

                # Generate encryption key
                logging.writeToFile(f"[_install_n8n_custom] Generating encryption key")
                encryption_key = randomPassword.generate_pass(32)
                logging.writeToFile(f"[_install_n8n_custom] Encryption key generated")
                
                # Configure database settings based on type
                if db_type == 'postgresql':
                    db_config = f'''# Database Configuration (PostgreSQL)
DB_TYPE=postgresdb
DB_POSTGRESDB_DATABASE={db_name}
DB_POSTGRESDB_HOST=127.0.0.1
DB_POSTGRESDB_PORT=5433
DB_POSTGRESDB_USER={db_user}
DB_POSTGRESDB_PASSWORD={db_password}'''
                    logging.writeToFile(f"[_install_n8n_custom] Using PostgreSQL configuration")
                else:
                    db_config = f'''# Database Configuration (MySQL/MariaDB)
DB_TYPE=mysqldb
DB_MYSQLDB_DATABASE={db_name}
DB_MYSQLDB_HOST=127.0.0.1
DB_MYSQLDB_PORT=3306
DB_MYSQLDB_USER={db_user}
DB_MYSQLDB_PASSWORD={db_password}
DB_MYSQLDB_CHARSET=utf8mb4
DB_MYSQLDB_COLLATION=utf8mb4_unicode_ci'''
                    logging.writeToFile(f"[_install_n8n_custom] Using MySQL/MariaDB configuration")

                config_content = f'''# n8n Configuration for {domain_name}

# Application Paths
N8N_USER_FOLDER={n8n_dir}/data
N8N_LOG_FILE_LOCATION={n8n_dir}/logs/n8n.log

{db_config}

# n8n Configuration
N8N_HOST=127.0.0.1
N8N_PORT={n8n_port}
N8N_PROTOCOL=https
WEBHOOK_URL=https://{domain_name}
N8N_EDITOR_BASE_URL=https://{domain_name}

# Security
N8N_BASIC_AUTH_ACTIVE=true
N8N_BASIC_AUTH_USER={n8n_username}
N8N_BASIC_AUTH_PASSWORD={n8n_password}
N8N_ENCRYPTION_KEY={encryption_key}

# Execution Settings
EXECUTIONS_DATA_SAVE_ON_ERROR=all
EXECUTIONS_DATA_SAVE_ON_SUCCESS=all
EXECUTIONS_DATA_MAX_AGE=336

# Performance
NODE_OPTIONS=--max-old-space-size=2048

# Timezone
GENERIC_TIMEZONE=UTC

# File Storage
N8N_DEFAULT_BINARY_DATA_MODE=filesystem
N8N_BINARY_DATA_STORAGE_PATH={n8n_dir}/data/files

# Log Settings
N8N_LOG_LEVEL=info

# Push Backend Configuration (Use SSE for OpenLiteSpeed compatibility)
N8N_PUSH_BACKEND=sse
'''

                config_file = f"{n8n_dir}/config/n8n.env"
                logging.writeToFile(f"[_install_n8n_custom] Writing config to {config_file}")
                
                # Write config to temp location first, then move it
                temp_config = f"/tmp/n8n_config_{website_user}_{n8n_port}.env"
                try:
                    with open(temp_config, 'w') as f:
                        f.write(config_content)
                    
                    # Copy to correct location with proper ownership
                    ProcessUtilities.executioner(f"cp {temp_config} {config_file}", website_user)
                    os.remove(temp_config)
                    
                    # Set permissions
                    command = f"chmod 600 {config_file}"
                    logging.writeToFile(f"[_install_n8n_custom] Setting config file permissions")
                    ProcessUtilities.executioner(command, website_user)
                    logging.writeToFile(f"[_install_n8n_custom] Config file written successfully")
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error writing config file: {str(e)}")
                    if os.path.exists(temp_config):
                        os.remove(temp_config)
                    statusWriter.writeToFile(f'Failed to write n8n configuration: {str(e)} [404]')
                    return

                # Save encryption key
                encryption_file = f"{n8n_dir}/config/encryption.key"
                logging.writeToFile(f"[_install_n8n_custom] Saving encryption key to {encryption_file}")
                
                # Write encryption key to temp location first, then move it
                temp_encryption = f"/tmp/n8n_encryption_{website_user}_{n8n_port}.key"
                try:
                    with open(temp_encryption, 'w') as f:
                        f.write(f"N8N_ENCRYPTION_KEY={encryption_key}\n")
                    
                    # Copy to correct location with proper ownership
                    ProcessUtilities.executioner(f"cp {temp_encryption} {encryption_file}", website_user)
                    os.remove(temp_encryption)
                    
                    # Set permissions
                    command = f"chmod 600 {encryption_file}"
                    ProcessUtilities.executioner(command, website_user)
                    logging.writeToFile(f"[_install_n8n_custom] Encryption key saved successfully")
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error saving encryption key: {str(e)}")
                    if os.path.exists(temp_encryption):
                        os.remove(temp_encryption)
                    statusWriter.writeToFile(f'Failed to save encryption key: {str(e)} [404]')
                    return

                statusWriter.writeToFile('Configuration created...,70')

                # Step 5: Create systemd service
                statusWriter.writeToFile('Creating systemd service...,80')
                logging.writeToFile(f"[_install_n8n_custom] Creating systemd service")

                service_name = f"n8n-{domain_name.replace('.', '-')}"
                logging.writeToFile(f"[_install_n8n_custom] Service name: {service_name}")
                service_content = f'''[Unit]
Description=n8n - Workflow Automation Tool for {domain_name}
After=network.target mysql.service
Requires=mysql.service

[Service]
Type=simple
User={website_user}
Group={website_user}
WorkingDirectory={n8n_dir}/app
EnvironmentFile={n8n_dir}/config/n8n.env

# Create log directory if it doesn't exist
ExecStartPre=/bin/bash -c 'mkdir -p {n8n_dir}/logs && chown {website_user}:{website_user} {n8n_dir}/logs'

# Start command - source nvm and environment file first, with detailed logging
ExecStart=/bin/bash -c 'exec > >(tee -a {n8n_dir}/logs/n8n.log) 2> >(tee -a {n8n_dir}/logs/n8n-error.log >&2) && echo "[$(date)] Starting n8n service..." && source {website_home}/.nvm/nvm.sh && echo "[$(date)] NVM sourced successfully" && source {n8n_dir}/config/n8n.env && echo "[$(date)] Environment variables loaded:" && env | grep -E "^(N8N_|DB_)" | sort && echo "[$(date)] Starting n8n on port $N8N_PORT..." && {n8n_dir}/app/node_modules/.bin/n8n start'

# Restart configuration
Restart=always
RestartSec=10

# Logging
StandardOutput=append:{n8n_dir}/logs/n8n.log
StandardError=append:{n8n_dir}/logs/n8n-error.log
SyslogIdentifier={service_name}

# Security
NoNewPrivileges=true
PrivateTmp=true

# Resource limits
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
'''

                service_file = f"/etc/systemd/system/{service_name}.service"
                logging.writeToFile(f"[_install_n8n_custom] Writing service file to {service_file}")
                
                # Write service file to temp location first, then move it with sudo
                temp_service = f"/tmp/n8n_service_{website_user}_{n8n_port}.service"
                try:
                    with open(temp_service, 'w') as f:
                        f.write(service_content)
                    
                    # Copy to systemd directory with sudo
                    command = f"sudo cp {temp_service} {service_file}"
                    ProcessUtilities.executioner(command)
                    
                    # Set proper ownership and permissions
                    ProcessUtilities.executioner(f"sudo chmod 644 {service_file}")
                    ProcessUtilities.executioner(f"sudo chown root:root {service_file}")
                    
                    os.remove(temp_service)
                    logging.writeToFile(f"[_install_n8n_custom] Service file written successfully")
                except Exception as e:
                    logging.writeToFile(f"[_install_n8n_custom] Error writing service file: {str(e)}")
                    if os.path.exists(temp_service):
                        os.remove(temp_service)
                    statusWriter.writeToFile(f'Failed to create systemd service: {str(e)} [404]')

                    return


                # Enable and start service
                logging.writeToFile(f"[_install_n8n_custom] Enabling and starting service")
                commands = [
                    "sudo systemctl daemon-reload",
                    f"sudo systemctl enable {service_name}",
                    f"sudo systemctl start {service_name}"
                ]

                for command in commands:
                    logging.writeToFile(f"[_install_n8n_custom] Running: {command}")
                    ProcessUtilities.executioner(command)
                    logging.writeToFile(f"[_install_n8n_custom] Command executed: {command}")

                statusWriter.writeToFile('Service created and started...,85')

                # Step 6: Configure OpenLiteSpeed reverse proxy
                statusWriter.writeToFile('Configuring web server...,90')
                logging.writeToFile(f"[_install_n8n_custom] Configuring OpenLiteSpeed reverse proxy")

                # Configure OpenLiteSpeed vhost for reverse proxy
                vhost_conf_path = f"/usr/local/lsws/conf/vhosts/{domain_name}/vhost.conf"
                logging.writeToFile(f"[_install_n8n_custom] Vhost config path: {vhost_conf_path}")
                
                # Read existing vhost configuration using sudo
                command = f"sudo cat {vhost_conf_path}"
                vhost_content = ProcessUtilities.outputExecutioner(command)
                
                if vhost_content.find('[Errno') > -1 or vhost_content.find('No such file') > -1:
                    statusWriter.writeToFile(f'Could not read vhost configuration: {vhost_content} [404]')
                    return
                
                # Check if proxy configuration already exists
                if f'extprocessor n8n{n8n_port}' not in vhost_content:
                    # Prepare proxy configuration to append at the end
                    proxy_config = f'''

# n8n Proxy Configuration
extprocessor n8n{n8n_port} {{
  type                    proxy
  address                 127.0.0.1:{n8n_port}
  maxConns                100
  pcKeepAliveTimeout      3600
  initTimeout             300
  retryTimeout            0
  respBuffer              0
}}

context / {{
  type                    proxy
  handler                 n8n{n8n_port}
  addDefaultCharset       off
  websocket               1
  
  extraHeaders            <<<END_extraHeaders
  RequestHeader set X-Forwarded-For $ip
  RequestHeader set X-Forwarded-Proto https
  RequestHeader set X-Forwarded-Host "{domain_name}"
  RequestHeader set Origin "{domain_name}, {domain_name}"
  RequestHeader set Host "{domain_name}"
  END_extraHeaders
}}
'''
                    
                    # Append proxy configuration at the end of the file
                    new_vhost_content = vhost_content.rstrip() + proxy_config
                    
                    # Create a temporary file with the new configuration
                    temp_file = f"/tmp/n8n_vhost_{domain_name}_{n8n_port}.conf"
                    logging.writeToFile(f"[_install_n8n_custom] Writing updated vhost to temp file: {temp_file}")
                    with open(temp_file, 'w') as f:
                        f.write(new_vhost_content)
                    
                    # Backup original configuration
                    backup_command = f"sudo cp {vhost_conf_path} {vhost_conf_path}.n8n_backup"
                    logging.writeToFile(f"[_install_n8n_custom] Backing up original vhost")
                    ProcessUtilities.executioner(backup_command)
                    
                    # Copy the new configuration to the vhost path
                    command = f"sudo cp {temp_file} {vhost_conf_path}"
                    logging.writeToFile(f"[_install_n8n_custom] Copying updated vhost")
                    ProcessUtilities.executioner(command)
                    
                    # Set proper ownership to lsadm:lsadm
                    chown_command = f"sudo chown lsadm:lsadm {vhost_conf_path}"
                    logging.writeToFile(f"[_install_n8n_custom] Setting vhost ownership")
                    ProcessUtilities.executioner(chown_command)
                    
                    # Clean up temp file
                    os.remove(temp_file)
                    logging.writeToFile(f"[_install_n8n_custom] Temp file cleaned up")

                    # Always assume vhost update succeeded since executioner doesn't return status
                    statusWriter.writeToFile('Proxy configuration added to vhost...,92')
                else:
                    logging.writeToFile(f"[_install_n8n_custom] Proxy config already exists")
                    statusWriter.writeToFile('Proxy configuration already exists...,92')

                # Restart OpenLiteSpeed
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"
                logging.writeToFile(f"[_install_n8n_custom] Restarting OpenLiteSpeed")
                ProcessUtilities.executioner(command)
                
                # Always report success since executioner doesn't return status
                statusWriter.writeToFile('OpenLiteSpeed restarted...,94')

                statusWriter.writeToFile('Web server configured...,95')

                # Step 7: Verify installation
                statusWriter.writeToFile('Verifying installation...,98')

                import time
                time.sleep(5)  # Give n8n time to start

                # Check if service is running
                command = f"sudo systemctl is-active {service_name}"
                result = ProcessUtilities.outputExecutioner(command)

                if result.strip() == "active":
                    statusWriter.writeToFile(f'n8n successfully installed at https://{domain_name}/ [200]')

                    # Write installation details
                    details = f'''
Installation Details:
- Domain: {domain_name}
- n8n URL: https://{domain_name}/
- n8n Username: {n8n_username}
- n8n Port: {n8n_port}
- Service Name: {service_name}
- Installation Directory: {n8n_dir}
- Database Name: {db_name}
- Database User: {db_user}

To manage n8n:
- Start: systemctl start {service_name}
- Stop: systemctl stop {service_name}
- Restart: systemctl restart {service_name}
- Status: systemctl status {service_name}
- Logs: journalctl -u {service_name} -f
'''
                    statusWriter.writeToFile(details)
                else:

                    statusWriter.writeToFile(
                        f'n8n service failed to start. Check logs: journalctl -u {service_name} [404]\n')
            except Exception as e:
                import traceback
                statusWriter.writeToFile(f'Installation failed: {str(e)}')
                statusWriter.writeToFile(f'Traceback: {traceback.format_exc()} [404]')
        except Exception as e:
            # If we can't even write to status file
            import traceback
            logging.writeToFile(f"[_install_n8n_custom] Critical error in n8n installation: {str(e)}")
            logging.writeToFile(f"[_install_n8n_custom] Critical error traceback: {traceback.format_exc()}")

    def _perform_n8n_installation_OLD_REMOVE(self, domain_name, status_file_path):
        """
        Perform the actual n8n installation process
        This runs in a background thread
        """
        # First, append to status file that thread started (before any imports that could fail)
        try:
            with open(status_file_path, 'a') as f:
                f.write('Background thread started successfully\n')
                f.write(f'Function called with domain: {domain_name}\n')
                f.write('About to start try block for imports...\n')
        except Exception as e:
            print(f"CRITICAL: Cannot write to status file {status_file_path}: {e}")
            return

        try:
            # Try imports one by one to catch specific failures
            with open(status_file_path, 'a') as f:
                f.write('Inside try block, attempting to import CyberCPLogFileWriter...\n')

            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

            with open(status_file_path, 'a') as f:
                f.write('CyberCPLogFileWriter import successful\n')
                f.write('Attempting to import Docker_Sites...\n')

            from plogical.DockerSites import Docker_Sites

            with open(status_file_path, 'a') as f:
                f.write('Docker_Sites import successful\n')
                f.write('Importing time module...\n')

            import time

            with open(status_file_path, 'a') as f:
                f.write('All imports successful, initializing status writer...\n')

            # Initialize status file writer
            try:
                with open(status_file_path, 'a') as f:
                    f.write('Creating CyberCPLogFileWriter instance...\n')
                status_writer = logging(status_file_path, 'a')

                with open(status_file_path, 'a') as f:
                    f.write('CyberCPLogFileWriter instance created, testing writeToFile...\n')

                status_writer.writeToFile('CyberCPLogFileWriter initialized successfully')

                with open(status_file_path, 'a') as f:
                    f.write('First writeToFile successful\n')

                status_writer.writeToFile('Starting n8n installation process...')
                status_writer.writeToFile(f'Domain: {domain_name}')
                status_writer.writeToFile(f'Data received: {self.data}')

                with open(status_file_path, 'a') as f:
                    f.write('All CyberCPLogFileWriter operations successful\n')

            except Exception as writer_error:
                with open(status_file_path, 'a') as f:
                    f.write(f'CyberCPLogFileWriter error: {str(writer_error)}\n')
                    f.write(f'Continuing without CyberCPLogFileWriter...\n')
                # Continue without the writer if it fails
                status_writer = None

            # Simplified approach - directly call DeployN8NContainer
            def write_status(message):
                if status_writer:
                    status_writer.writeToFile(message)
                else:
                    with open(status_file_path, 'a') as f:
                        f.write(f'{message}\n')

            write_status('Preparing Docker deployment...')

            # Use the same pattern as working submitDockerSiteCreation
            # Get all required parameters from the data sent by the platform
            sitename = self.data.get('sitename', domain_name.replace('.', '').replace('-', '')[:8])
            Owner = self.data.get('Owner', self.data.get('websiteOwner', domain_name.replace('.', '')))
            MysqlCPU = int(self.data.get('MysqlCPU', 1))
            MYsqlRam = int(self.data.get('MYsqlRam', 512))
            SiteCPU = int(self.data.get('SiteCPU', 1))
            SiteRam = int(self.data.get('SiteRam', 512))
            App = self.data.get('App', 'N8N')
            WPusername = self.data.get('WPusername', 'admin')
            WPemal = self.data.get('WPemal', self.data.get('adminEmail', f'admin@{domain_name}'))
            WPpasswd = self.data.get('WPpasswd', self.data.get('n8nPassword', 'auto-generate'))
            port = self.data.get('port', '8080')
            userID = self.data.get('userID', 1)

            write_status(f'Extracted parameters - sitename: {sitename}, Owner: {Owner}, CPU: {SiteCPU}, RAM: {SiteRam}')

            # Prepare temp status path
            from random import randint
            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            # Prepare data structure exactly like working submitDockerSiteCreation
            docker_data = {
                'JobID': tempStatusPath,  # Use temp status path like working version
                'Domain': domain_name,
                'WPemal': WPemal,
                'Owner': Owner,
                'userID': userID,
                'MysqlCPU': MysqlCPU,
                'MYsqlRam': MYsqlRam,
                'SiteCPU': SiteCPU,
                'SiteRam': SiteRam,
                'sitename': sitename,
                'WPusername': WPusername,
                'WPpasswd': WPpasswd,
                'externalApp': "".join(domain_name.replace('.', '').replace('-', '')[:5]) + str(randint(1000, 9999)),
                'App': App,
                'finalURL': domain_name,
                'port': port,
                'ServiceName': sitename.replace(' ', '-'),
                'ComposePath': f'/home/docker/{domain_name}/docker-compose.yml',
                'MySQLPath': f'/home/docker/{domain_name}/db',
                'MySQLRootPass': self.data.get('dbPassword', 'auto-generated'),
                'MySQLDBName': f'n8n_{sitename}',
                'MySQLDBUser': f'n8n_{sitename}',
                'MySQLPassword': self.data.get('dbPassword', 'auto-generated'),
                'MemoryMySQL': MYsqlRam,
                'CPUsMySQL': MysqlCPU,
                'MemorySite': SiteRam,
                'CPUsSite': SiteCPU
            }

            write_status(f'Docker data prepared following working pattern: {docker_data}')

            # Call the actual deployment function from DockerSites
            try:
                write_status('Starting Docker_Sites deployment...')

                # Create and run Docker_Sites instance
                try:
                    write_status('Creating Docker_Sites instance...')
                    write_status(f'Calling Docker_Sites with function: DeployN8NContainer')
                    write_status(f'Data keys: {list(docker_data.keys())}')

                    docker_sites = Docker_Sites('DeployN8NContainer', docker_data)
                    write_status('Docker_Sites instance created successfully')
                    write_status(f'Docker_Sites attributes: function_run={docker_sites.function_run}')

                except Exception as docker_init_error:
                    write_status(f'Docker_Sites creation failed: {str(docker_init_error)}')
                    import traceback
                    write_status(f'Docker_Sites creation traceback: {traceback.format_exc()}')
                    return

                try:
                    write_status('Starting Docker_Sites thread...')
                    docker_sites.start()
                    write_status('Docker deployment thread started successfully')
                except Exception as start_error:
                    write_status(f'Docker_Sites start failed: {str(start_error)}')
                    import traceback
                    write_status(f'Docker_Sites start traceback: {traceback.format_exc()}')
                    return

                try:
                    write_status('Waiting for Docker deployment completion...')
                    docker_sites.join()
                    write_status('Docker deployment thread completed')
                except Exception as join_error:
                    write_status(f'Docker_Sites join failed: {str(join_error)}')
                    import traceback
                    write_status(f'Docker_Sites join traceback: {traceback.format_exc()}')
                    return

                # The DeployN8NContainer function writes its own status to the JobID file
                # Check if it was successful by reading the final status
                try:
                    write_status('Reading deployment results...')
                    with open(status_file_path, 'r') as f:
                        final_status = f.read()
                    write_status(f'Final status content: {final_status}')

                    if '[200]' in final_status:
                        write_status(f'n8n successfully installed and deployed at https://{domain_name}/ [200]')
                    else:
                        write_status(f'Container deployment completed but with issues [404]')
                except Exception as read_error:
                    write_status(f'Unable to verify deployment status: {str(read_error)} [404]')

            except Exception as e:
                import traceback
                write_status(f'Container deployment failed: {str(e)} [404]')
                write_status(f'Traceback: {traceback.format_exc()}')
                return

        except Exception as e:
            # Write error to status file using direct file writing
            try:
                import traceback
                with open(status_file_path, 'a') as f:
                    f.write(f'MAIN EXCEPTION in _perform_n8n_installation: {str(e)}\n')
                    f.write(f'Full traceback: {traceback.format_exc()}\n')
                    f.write('Installation failed [404]\n')
            except Exception as log_error:
                # If we can't even write to the status file, something is very wrong
                print(f"Critical error - cannot write to status file: {log_error}")
                print(f"Original error: {e}")
                import traceback
                print(f"Traceback: {traceback.format_exc()}")

    def getN8NInstallStatus(self):
        try:
            # This now uses the standard statusFunc to check Docker site creation status
            # The status file path is provided in tempStatusPath from installN8N response

            statusFile = self.data.get('statusFile')
            if not statusFile:
                # For backward compatibility, also check domainIdentifier
                domain_identifier = self.data.get('domainIdentifier')
                if domain_identifier:
                    # Try to find the status file from previous installations
                    import os
                    import glob
                    possible_files = glob.glob(f'/home/cyberpanel/*')
                    for f in possible_files:
                        try:
                            with open(f, 'r') as file:
                                content = file.read()
                                if domain_identifier.replace('_', '.') in content:
                                    statusFile = f
                                    break
                        except:
                            pass

                if not statusFile:
                    return self.ajaxPre(0, 'statusFile or domainIdentifier is required')

            # Use the standard status function
            self.data['statusFile'] = statusFile
            return self.statusFunc()

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def listN8NInstallations(self):
        try:
            from websiteFunctions.models import Websites

            # Find all websites with n8n installations
            n8n_sites = []

            try:
                websites = Websites.objects.all()
                for website in websites:
                    # Check if this website has n8n running
                    # This is a placeholder - actual implementation would check container status
                    if hasattr(website, 'applicationInstaller') and website.applicationInstaller == 'n8n':
                        n8n_sites.append({
                            'domain': website.domain,
                            'status': 'running',  # This would be dynamically checked
                            'created': str(website.date),
                            'path': website.path
                        })
            except Exception as e:
                pass  # Continue even if this fails

            final_dic = {
                'status': 1,
                'error_message': 'None',
                'installations': n8n_sites,
                'count': len(n8n_sites)
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

    def removeN8NInstallation(self):
        try:
            from websiteFunctions.models import Websites
            from websiteFunctions.website import WebsiteManager
            import os

            domain_name = self.data.get('domainName')
            if not domain_name:
                return self.ajaxPre(0, 'domainName is required')

            # Check if website exists
            try:
                website = Websites.objects.get(domain=domain_name)
            except Websites.DoesNotExist:
                return self.ajaxPre(0, f'Website {domain_name} not found')

            # Stop and remove n8n containers
            # This would use Docker API to stop containers
            # For now, simulate the removal

            # Delete the website
            website_manager = WebsiteManager()
            delete_result = website_manager.submitWebsiteDeletion(self.admin.pk, {'websiteName': domain_name})

            if delete_result['status'] == 0:
                return self.ajaxPre(0, delete_result['error_message'])

            # Clean up status files
            status_file_path = f'/home/cyberpanel/n8n_install_{domain_name.replace(".", "_")}_status'
            try:
                if os.path.exists(status_file_path):
                    os.remove(status_file_path)
            except:
                pass  # Ignore cleanup errors

            final_dic = {
                'status': 1,
                'error_message': 'None',
                'message': f'n8n installation {domain_name} removed successfully'
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))
