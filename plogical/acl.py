#!/usr/local/CyberCP/bin/python
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from loginSystem.models import Administrator, ACL
from django.shortcuts import HttpResponse
from packages.models import Package
from websiteFunctions.models import Websites, ChildDomains
from dns.models import Domains
import json
from subprocess import call, CalledProcessError
from shlex import split
from .CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from dockerManager.models import Containers

class ACLManager:

    @staticmethod
    def commandInjectionCheck(value):
        if value.find(';') > -1 or value.find('&&') > -1 or value.find('|') > -1 or value.find('...') > -1 \
                or value.find("`") > -1 or value.find("$") > -1 or value.find("(") > -1 or value.find(")") > -1 \
                or value.find("'") > -1 or value.find("[") > -1 or value.find("]") > -1 or value.find(
            "{") > -1 or value.find("}") > -1 \
                or value.find(":") > -1 or value.find("<") > -1 or value.find(">") > -1:
            return 1
        else:
            return 0

    @staticmethod
    def loadedACL(val):

        admin = Administrator.objects.get(pk=val)
        finalResponse = {}
        finalResponse['firstName'] = admin.firstName
        finalResponse['lastName'] = admin.lastName

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            serverIPAddress = ipData.split('\n', 1)[0]
        except BaseException as msg:
            serverIPAddress = "192.168.100.1"

        finalResponse['serverIPAddress'] = serverIPAddress
        finalResponse['adminName'] = admin.firstName

        if admin.acl.adminStatus == 1:
            finalResponse['admin'] = 1
        else:
            finalResponse['admin'] = 0

            acl = ACL.objects.get(name=admin.acl.name)
            finalResponse['versionManagement'] = acl.versionManagement

            ## User Management

            finalResponse['createNewUser'] = acl.createNewUser
            finalResponse['listUsers'] = acl.listUsers
            finalResponse['deleteUser'] = acl.deleteUser
            finalResponse['changeUserACL'] = acl.changeUserACL
            finalResponse['resellerCenter'] = acl.resellerCenter

            ## Website Management

            finalResponse['createWebsite'] = acl.createWebsite
            finalResponse['modifyWebsite'] = acl.modifyWebsite
            finalResponse['suspendWebsite'] = acl.suspendWebsite
            finalResponse['deleteWebsite'] = acl.deleteWebsite

            ## Package Management


            finalResponse['createPackage'] = acl.createPackage
            finalResponse['listPackages'] = acl.listPackages
            finalResponse['deletePackage'] = acl.deletePackage
            finalResponse['modifyPackage'] = acl.modifyPackage

            ## Database Management

            finalResponse['createDatabase'] = acl.createDatabase
            finalResponse['deleteDatabase'] = acl.deleteDatabase
            finalResponse['listDatabases'] = acl.listDatabases

            ## DNS Management

            finalResponse['createNameServer'] = acl.createNameServer
            finalResponse['createDNSZone'] = acl.createDNSZone
            finalResponse['deleteZone'] = acl.deleteZone
            finalResponse['addDeleteRecords'] = acl.addDeleteRecords

            ## Email Management

            finalResponse['createEmail'] = acl.createEmail
            finalResponse['listEmails'] = acl.listEmails
            finalResponse['deleteEmail'] = acl.deleteEmail
            finalResponse['emailForwarding'] = acl.emailForwarding
            finalResponse['changeEmailPassword'] = acl.changeEmailPassword
            finalResponse['dkimManager'] = acl.dkimManager

            ## FTP Management

            finalResponse['createFTPAccount'] = acl.createFTPAccount
            finalResponse['deleteFTPAccount'] = acl.deleteFTPAccount
            finalResponse['listFTPAccounts'] = acl.listFTPAccounts

            ## Backup Management

            finalResponse['createBackup'] = acl.createBackup
            finalResponse['restoreBackup'] = acl.restoreBackup
            finalResponse['addDeleteDestinations'] = acl.addDeleteDestinations
            finalResponse['scheDuleBackups'] = acl.scheDuleBackups
            finalResponse['remoteBackups'] = acl.remoteBackups

            ## SSL Management

            finalResponse['manageSSL'] = acl.manageSSL
            finalResponse['hostnameSSL'] = acl.hostnameSSL
            finalResponse['mailServerSSL'] = acl.mailServerSSL

        return finalResponse

    @staticmethod
    def checkUserOwnerShip(currentACL, owner, user):
        if currentACL['admin'] == 1:
            return 1
        elif owner == user:
            return 1
        elif owner.pk == user.owner:
            return 1
        else:
            return 0

    @staticmethod
    def currentContextPermission(currentACL, context):
        try:
            if currentACL['admin'] == 1:
                return 1
            elif currentACL[context] == 1:
                return 1
            else:
                return 0
        except:
            pass

    @staticmethod
    def createDefaultACLs():
        try:

            ## Admin ACL

            newACL = ACL(name='admin', adminStatus=1)
            newACL.save()

            ## Reseller ACL

            newACL = ACL(name='reseller',
                         createNewUser=1,
                         deleteUser=1,
                         createWebsite=1,
                         resellerCenter=1,
                         modifyWebsite=1,
                         suspendWebsite=1,
                         deleteWebsite=1,
                         createPackage=1,
                         deletePackage=1,
                         modifyPackage=1,
                         createNameServer=1,
                         restoreBackup=1,
                         )
            newACL.save()

            ## User ACL
            newACL = ACL(name='user')
            newACL.save()
        except:
            pass

    @staticmethod
    def loadError():
        try:
            return HttpResponse('You are not authorized to access this resource.')
        except:
            pass

    @staticmethod
    def loadErrorJson(additionalParameter = None, additionalParameterValue = None):
        try:
            if additionalParameter == None:
                finalJson = {"status": 0, "errorMessage": 'You are not authorized to access this resource.',
                        'error_message': 'You are not authorized to access this resource.',
                        }
            else:
                finalJson = {"status": 0, "errorMessage": 'You are not authorized to access this resource.',
                        'error_message': 'You are not authorized to access this resource.',
                        additionalParameter: additionalParameterValue
                        }

            json_data = json.dumps(finalJson)
            return HttpResponse(json_data)
        except:
            pass

    @staticmethod
    def findAllUsers():
        userNames = []
        allUsers = Administrator.objects.all()
        for items in allUsers:
            if items.userName == 'admin':
                continue
            userNames.append(items.userName)
        return userNames

    @staticmethod
    def findAllACLs():
        aclNames = []
        allACLs = ACL.objects.all()

        for items in allACLs:
            if items.name == 'admin' or items.name == 'reseller' or items.name == 'user':
                continue
            else:
                aclNames.append(items.name)
        return aclNames

    @staticmethod
    def unFileteredACLs():
        aclNames = []
        allACLs = ACL.objects.all()

        for items in allACLs:
            aclNames.append(items.name)

        return aclNames

    @staticmethod
    def loadAllUsers(userID):
        admin = Administrator.objects.get(pk=userID)
        adminNames = []

        finalResponse = ACLManager.loadedACL(userID)

        if finalResponse['admin'] == 1:
            admins = Administrator.objects.all()
            for items in admins:
                if items.userName == admin.userName:
                    continue
                adminNames.append(items.userName)
        else:
            admins = Administrator.objects.filter(owner=admin.pk)
            for items in admins:
                adminNames.append(items.userName)

        adminNames.append(admin.userName)
        return adminNames

    @staticmethod
    def loadUserObjects(userID):
        admin = Administrator.objects.get(pk=userID)
        adminObjects = []

        finalResponse = ACLManager.loadedACL(userID)

        if finalResponse['admin'] == 1:
            return Administrator.objects.all()
        else:
            admins = Administrator.objects.filter(owner=admin.pk)
            for items in admins:
                adminObjects.append(items)

                adminObjects.append(admin)

        return adminObjects

    @staticmethod
    def fetchTableUserObjects(userID):
        admin = Administrator.objects.get(pk=userID)
        adminObjects = []

        finalResponse = ACLManager.loadedACL(userID)

        if finalResponse['admin'] == 1:
            return Administrator.objects.all().exclude(pk=userID)
        else:
            admins = Administrator.objects.filter(owner=admin.pk)
            for items in admins:
                adminObjects.append(items)

        return adminObjects

    @staticmethod
    def loadDeletionUsers(userID, finalResponse):
        admin = Administrator.objects.get(pk=userID)
        adminNames = []

        if finalResponse['admin'] == 1:
            admins = Administrator.objects.all()
            for items in admins:
                if items.userName == admin.userName:
                    continue
                adminNames.append(items.userName)
        else:
            admins = Administrator.objects.filter(owner=admin.pk)
            for items in admins:
                adminNames.append(items.userName)

        return adminNames

    @staticmethod
    def userWithResellerPriv(userID):
        admin = Administrator.objects.get(pk=userID)
        adminNames = []

        finalResponse = ACLManager.loadedACL(userID)

        if finalResponse['admin'] == 1:
            admins = Administrator.objects.all()
            for items in admins:
                if items.acl.resellerCenter == 1:
                    if items.userName == admin.userName:
                        continue
                    adminNames.append(items.userName)
        else:
            admins = Administrator.objects.filter(owner=admin.pk)
            for items in admins:
                if items.acl.resellerCenter == 1:
                    adminNames.append(items.userName)

        adminNames.append(admin.userName)
        return adminNames

    @staticmethod
    def websitesLimitCheck(currentAdmin, websitesLimit, userToBeModified = None):
        if currentAdmin.acl.adminStatus != 1:

            if currentAdmin.initWebsitesLimit != 0:
                webLimits = 0
                allUsers = Administrator.objects.filter(owner=currentAdmin.pk)
                for items in allUsers:
                    webLimits = webLimits + items.initWebsitesLimit

                if userToBeModified != None:
                    webLimits = webLimits - userToBeModified.initWebsitesLimit

                webLimits = webLimits + websitesLimit + currentAdmin.websites_set.all().count()

                if webLimits <= currentAdmin.initWebsitesLimit:
                    return 1
                else:
                    return 0
            else:
                return 1
        else:
            return 1

    @staticmethod
    def loadPackages(userID, finalResponse):
        admin = Administrator.objects.get(pk=userID)
        packNames = []

        if finalResponse['admin'] == 1:
            packs = Package.objects.all()
            for items in packs:
                packNames.append(items.packageName)
        else:
            packs = admin.package_set.all()
            for items in packs:
                packNames.append(items.packageName)

        return packNames

    @staticmethod
    def loadPackageObjects(userID, finalResponse):
        admin = Administrator.objects.get(pk=userID)

        if finalResponse['admin'] == 1:
            return Package.objects.all()
        else:
            return admin.package_set.all()

    @staticmethod
    def findAllSites(currentACL, userID):
        websiteNames = []

        if currentACL['admin'] == 1:
            allWebsites = Websites.objects.all()
            for items in allWebsites:
                websiteNames.append(items.domain)
        else:
            admin = Administrator.objects.get(pk=userID)

            websites = admin.websites_set.all()
            admins = Administrator.objects.filter(owner=admin.pk)

            for items in websites:
                websiteNames.append(items.domain)

            for items in admins:
                webs = items.websites_set.all()
                for web in webs:
                    websiteNames.append(web.domain)


        return websiteNames

    @staticmethod
    def searchWebsiteObjects(currentACL, userID, searchTerm):
        if currentACL['admin'] == 1:
            return Websites.objects.filter(domain__istartswith=searchTerm)
        else:
            websiteList = []
            admin = Administrator.objects.get(pk=userID)

            websites = admin.websites_set.filter(domain__istartswith=searchTerm)

            for items in websites:
                websiteList.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                webs = items.websites_set.filter(domain__istartswith=searchTerm)
                for web in webs:
                    websiteList.append(web)

            return websiteList

    @staticmethod
    def findWebsiteObjects(currentACL, userID):
        if currentACL['admin'] == 1:
            return Websites.objects.all()
        else:

            websiteList = []
            admin = Administrator.objects.get(pk=userID)

            websites = admin.websites_set.all()

            for items in websites:
                websiteList.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                webs = items.websites_set.all()
                for web in webs:
                    websiteList.append(web)

            return websiteList

    @staticmethod
    def findAllDomains(currentACL, userID):
        domainsList = []

        if currentACL['admin'] == 1:
            domains = Websites.objects.all()
            for items in domains:
                domainsList.append(items.domain)
        else:
            admin = Administrator.objects.get(pk=userID)
            domains = admin.websites_set.all()

            for items in domains:
                domainsList.append(items.domain)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                doms = items.websites_set.all()
                for dom in doms:
                    domainsList.append(dom.domain)

        return domainsList

    @staticmethod
    def findAllWebsites(currentACL, userID):
        domainsList = []

        if currentACL['admin'] == 1:
            domains = Websites.objects.order_by('domain').all()
            for items in domains:
                domainsList.append(items.domain)
        else:
            admin = Administrator.objects.get(pk=userID)
            domains = admin.websites_set.all()

            for items in domains:
                domainsList.append(items.domain)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                doms = items.websites_set.all()
                for dom in doms:
                    domainsList.append(dom.domain)
        return domainsList

    @staticmethod
    def checkOwnership(domain, admin, currentACL):

        try:
            childDomain = ChildDomains.objects.get(domain=domain)

            if currentACL['admin'] == 1:
                return 1
            elif childDomain.master.admin == admin:
                return 1
            else:
                if childDomain.master.admin.owner == admin.pk:
                    return 1

        except:
            domainName = Websites.objects.get(domain=domain)

            if currentACL['admin'] == 1:
                return 1
            elif  domainName.admin == admin:
                return 1
            else:
                if domainName.admin.owner == admin.pk:
                    return 1
                else:
                    return 0

    @staticmethod
    def checkOwnershipZone(domain, admin, currentACL):
        domain = Domains.objects.get(name=domain)

        if currentACL['admin'] == 1:
            return 1
        elif domain.admin == admin:
            return 1
        elif domain.admin.owner == admin.pk:
            return 1
        else:
            return 0

    @staticmethod
    def executeCall(command):
        try:
            result = call(split(command))
            if result == 1:
                return 0, 'Something bad happened'
            else:
                return 1, 'None'
        except CalledProcessError as msg:
            logging.writeToFile(str(msg) + ' [ACLManager.executeCall]')
            return 0, str(msg)

    @staticmethod
    def checkContainerOwnership(name, userID):
        try:
            container = Containers.objects.get(name=name)
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if currentACL['admin'] == 1:
                return 1
            elif container.admin == admin:
                return 1
            else:
                return 0
        except:
            return 0

    @staticmethod
    def findAllContainers(currentACL, userID):
        containerName = []

        if currentACL['admin'] == 1:
            allContainers = Containers.objects.all()
            for items in allContainers:
                containerName.append(items.name)
        else:
            admin = Administrator.objects.get(pk=userID)

            containers = admin.containers_set.all()
            admins = Administrator.objects.filter(owner=admin.pk)

            for items in containers:
                containerName.append(items.name)

            for items in admins:
                cons = items.containers_set.all()
                for con in cons:
                    containerName.append(con.name)


        return containerName

    @staticmethod
    def findContainersObjects(currentACL, userID):

        if currentACL['admin'] == 1:
            return Containers.objects.all()
        else:

            containerList = []
            admin = Administrator.objects.get(pk=userID)

            containers = admin.containers_set.all()

            for items in containers:
                containerList.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                cons = items.containers_set.all()
                for con in cons:
                    containerList.append(con)

            return containerList

    @staticmethod
    def findChildDomains(websiteNames):
        childDomains = []

        for items in websiteNames:
            website = Websites.objects.get(domain = items)
            for childDomain in website.childdomains_set.all():
                childDomains.append(childDomain.domain)

        return childDomains

    @staticmethod
    def checkOwnerProtection(currentACL, owner, child):
        if currentACL['admin'] == 1:
            return 1
        elif child.owner == owner.pk:
            return 1
        elif child == owner:
            return 1
        else:
            return 0


