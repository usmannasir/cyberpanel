import sys
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
            if request.META['HTTP_AUTHORIZATION'] == self.admin.token:
                return 1, self.ajaxPre(1, None)
            else:
                return 0, self.ajaxPre(0, 'Invalid login information.')

        except BaseException as msg:
            return self.ajaxPre(0, str(msg))

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
            request.session['userID'] = self.admin.pk
            currentACL = ACLManager.loadedACL(self.admin.pk)

            if currentACL['admin'] == 0:
                return self.ajaxPre(0, 'Only administrators can see MySQL status.')

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
            execPath = execPath + " SubmitS3BackupRestore --backupDomain %s --backupFile '%s' --tempStoragePath %s --planName %s" % (
                self.data['domain'], self.data['backupFile'], tempStatusPath, self.data['planName'])
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

            command = 'wp core version --skip-plugins --skip-themes --path=%s' % (path)
            finalDic['version'] = str(ProcessUtilities.outputExecutioner(command, website.externalApp))

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
                finalDic['searchIndex'] = int(ProcessUtilities.outputExecutioner(command, website.externalApp).splitlines()[-1])
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

            command = 'wp user update cyberpanel --user_pass="%s" --path=%s --skip-plugins --skip-themes' % (password, path)
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
                command = "wp config set WP_AUTO_UPDATE_CORE false --skip-plugins --skip-themes --raw --path=%s" % (path)
                ProcessUtilities.executioner(command, website.externalApp)
            elif self.data['wpCore'] == 'Minor and Security Updates':
                command = "wp config set WP_AUTO_UPDATE_CORE minor --skip-plugins --skip-themes --allow-root --path=%s" % (path)
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

            command = 'wp core version --allow-root --skip-plugins --skip-themes --path=%s' % (path)
            result = ProcessUtilities.outputExecutioner(command)

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

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function %s --type %s" % ('DetachCluster', type)
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

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function SetupCluster --type %s" % (self.data['type'])
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

            ##

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            ##

            import CloudFlare
            cf = CloudFlare.CloudFlare(email=self.data['cfemail'], token=self.data['apikey'])

            zones = cf.zones.get(params = {'per_page':100})

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.6/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            command = 'chown cyberpanel:cyberpanel -R /usr/local/CyberCP/lib/python3.8/site-packages/tldextract/.suffix_cache'
            ProcessUtilities.executioner(command)

            for website in Websites.objects.all():
                import tldextract
                extractDomain = tldextract.extract(website.domain)
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

            from websiteFunctions.models import ChildDomains
            for website in ChildDomains.objects.all():

                import tldextract
                extractDomain = tldextract.extract(website.domain)
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

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/ClusterManager.py --function %s --type %s" % ('DebugCluster', type)
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
