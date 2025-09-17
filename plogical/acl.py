#!/usr/local/CyberCP/bin/python
import os,sys
import random
import string

from ApachController.ApacheVhosts import ApacheVhost
from manageServices.models import PDNSStatus
from .processUtilities import ProcessUtilities

sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from loginSystem.models import Administrator, ACL
from django.shortcuts import HttpResponse
from packages.models import Package
from websiteFunctions.models import Websites, ChildDomains, aliasDomains, DockerSites, WPSites
import json
from subprocess import call, CalledProcessError
from shlex import split
from .CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from dockerManager.models import Containers
from re import compile

class ACLManager:


    AdminACL = '{"adminStatus":1, "versionManagement": 1, "createNewUser": 1, "listUsers": 1, "deleteUser":1 , "resellerCenter": 1, ' \
               '"changeUserACL": 1, "createWebsite": 1, "modifyWebsite": 1, "suspendWebsite": 1, "deleteWebsite": 1, ' \
               '"createPackage": 1, "listPackages": 1, "deletePackage": 1, "modifyPackage": 1, "createDatabase": 1, "deleteDatabase": 1, ' \
               '"listDatabases": 1, "createNameServer": 1, "createDNSZone": 1, "deleteZone": 1, "addDeleteRecords": 1, ' \
               '"createEmail": 1, "listEmails": 1, "deleteEmail": 1, "emailForwarding": 1, "changeEmailPassword": 1, ' \
               '"dkimManager": 1, "createFTPAccount": 1, "deleteFTPAccount": 1, "listFTPAccounts": 1, "createBackup": 1,' \
               ' "restoreBackup": 1, "addDeleteDestinations": 1, "scheduleBackups": 1, "remoteBackups": 1, "googleDriveBackups": 1, "manageSSL": 1, ' \
               '"hostnameSSL": 1, "mailServerSSL": 1 }'

    ResellerACL = '{"adminStatus":0, "versionManagement": 1, "createNewUser": 1, "listUsers": 1, "deleteUser": 1 , "resellerCenter": 1, ' \
                  '"changeUserACL": 0, "createWebsite": 1, "modifyWebsite": 1, "suspendWebsite": 1, "deleteWebsite": 1, ' \
                  '"createPackage": 1, "listPackages": 1, "deletePackage": 1, "modifyPackage": 1, "createDatabase": 1, "deleteDatabase": 1, ' \
                  '"listDatabases": 1, "createNameServer": 1, "createDNSZone": 1, "deleteZone": 1, "addDeleteRecords": 1, ' \
                  '"createEmail": 1, "listEmails": 1, "deleteEmail": 1, "emailForwarding": 1, "changeEmailPassword": 1, ' \
                  '"dkimManager": 1, "createFTPAccount": 1, "deleteFTPAccount": 1, "listFTPAccounts": 1, "createBackup": 1,' \
                  ' "restoreBackup": 1, "addDeleteDestinations": 0, "scheduleBackups": 0, "remoteBackups": 0, "googleDriveBackups": 1, "manageSSL": 1, ' \
                  '"hostnameSSL": 0, "mailServerSSL": 0 }'

    UserACL = '{"adminStatus":0, "versionManagement": 1, "createNewUser": 0, "listUsers": 0, "deleteUser": 0 , "resellerCenter": 0, ' \
              '"changeUserACL": 0, "createWebsite": 0, "modifyWebsite": 0, "suspendWebsite": 0, "deleteWebsite": 0, ' \
              '"createPackage": 0, "listPackages": 0, "deletePackage": 0, "modifyPackage": 0, "createDatabase": 1, "deleteDatabase": 1, ' \
              '"listDatabases": 1, "createNameServer": 0, "createDNSZone": 1, "deleteZone": 1, "addDeleteRecords": 1, ' \
              '"createEmail": 1, "listEmails": 1, "deleteEmail": 1, "emailForwarding": 1, "changeEmailPassword": 1, ' \
              '"dkimManager": 1, "createFTPAccount": 1, "deleteFTPAccount": 1, "listFTPAccounts": 1, "createBackup": 1,' \
              ' "restoreBackup": 0, "addDeleteDestinations": 0, "scheduleBackups": 0, "remoteBackups": 0, "googleDriveBackups": 1, "manageSSL": 1, ' \
              '"hostnameSSL": 0, "mailServerSSL": 0 }'

    @staticmethod
    def VerifySMTPHost(currentACL, owner, user):
        if currentACL['admin'] == 1:
            return 1
        elif owner == user:
            return 1
        else:
            return 0

    @staticmethod
    def VerifyRecordOwner(currentACL, record, domain):
        if currentACL['admin'] == 1:
            return 1
        elif record.domainOwner.name == domain:
            return 1
        else:
            return 0


    @staticmethod
    def AliasDomainCheck(currentACL, aliasDomain, master):
        aliasOBJ = aliasDomains.objects.get(aliasDomain=aliasDomain)
        masterOBJ = Websites.objects.get(domain=master)
        if currentACL['admin'] == 1:
            return 1
        elif aliasOBJ.master == masterOBJ:
            return 1
        else:
            return 0

    @staticmethod
    def CheckPackageOwnership(package, admin, currentACL):
        if currentACL['admin'] == 1:
            return 1
        elif package.admin == admin:
            return 1
        else:
            return 0

    @staticmethod
    def CheckRegEx(RegexCheck, value):
        import re
        if re.match(RegexCheck, value):
            return 1
        else:
            return 0



    @staticmethod
    def FindIfChild():
        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            config = json.loads(open('/home/cyberpanel/cluster', 'r').read())
            if config['failoverServerIP'] == ipAddress:
                return 1
            else:
                return 0
        except:
            return 0


    @staticmethod
    def fetchIP():
        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            return ipData.split('\n', 1)[0]
        except BaseException:
            return "192.168.100.1"

    @staticmethod
    def validateInput(value, regex = None):
        if regex == None:
            verifier = compile(r'[\sa-zA-Z0-9_-]+')
        else:
            verifier = regex

        if verifier.fullmatch(value):
            return 1
        else:
            return 0

    @staticmethod
    def commandInjectionCheck(value):
        try:
            if value.find(';') > -1 or value.find('&&') > -1 or value.find('|') > -1 or value.find('...') > -1 \
                    or value.find("`") > -1 or value.find("$") > -1 or value.find("(") > -1 or value.find(")") > -1 \
                    or value.find("'") > -1 or value.find("[") > -1 or value.find("]") > -1 or value.find(
                "{") > -1 or value.find("}") > -1 \
                    or value.find(":") > -1 or value.find("<") > -1 or value.find(">") > -1 or value.find("&") > -1:
                return 1
            else:
                return 0
        except BaseException as msg:
            logging.writeToFile('%s. [32:commandInjectionCheck]' % (str(msg)))

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

        config = json.loads(admin.acl.config)

        if config['adminStatus']:
            finalResponse['admin'] = 1
        else:
            finalResponse['admin'] = 0
            finalResponse['versionManagement'] = config['versionManagement']

            ## User Management

            finalResponse['createNewUser'] = config['createNewUser']
            finalResponse['listUsers'] = config['listUsers']
            finalResponse['deleteUser'] = config['deleteUser']
            finalResponse['changeUserACL'] = config['changeUserACL']
            finalResponse['resellerCenter'] = config['resellerCenter']

            ## Website Management

            finalResponse['createWebsite'] = config['createWebsite']
            finalResponse['modifyWebsite'] = config['modifyWebsite']
            finalResponse['suspendWebsite'] = config['suspendWebsite']
            finalResponse['deleteWebsite'] = config['deleteWebsite']

            ## Package Management


            finalResponse['createPackage'] = config['createPackage']
            finalResponse['listPackages'] = config['listPackages']
            finalResponse['deletePackage'] = config['deletePackage']
            finalResponse['modifyPackage'] = config['modifyPackage']

            ## Database Management

            finalResponse['createDatabase'] = config['createDatabase']
            finalResponse['deleteDatabase'] = config['deleteDatabase']
            finalResponse['listDatabases'] = config['listDatabases']

            ## DNS Management

            finalResponse['createNameServer'] = config['createNameServer']
            finalResponse['createDNSZone'] = config['createDNSZone']
            finalResponse['deleteZone'] = config['deleteZone']
            finalResponse['addDeleteRecords'] = config['addDeleteRecords']

            ## Email Management

            finalResponse['createEmail'] = config['createEmail']
            finalResponse['listEmails'] = config['listEmails']
            finalResponse['deleteEmail'] = config['deleteEmail']
            finalResponse['emailForwarding'] = config['emailForwarding']
            finalResponse['changeEmailPassword'] = config['changeEmailPassword']
            finalResponse['dkimManager'] = config['dkimManager']

            ## FTP Management

            finalResponse['createFTPAccount'] = config['createFTPAccount']
            finalResponse['deleteFTPAccount'] = config['deleteFTPAccount']
            finalResponse['listFTPAccounts'] = config['listFTPAccounts']

            ## Backup Management

            finalResponse['createBackup'] = config['createBackup']
            finalResponse['googleDriveBackups'] = config['googleDriveBackups']
            finalResponse['restoreBackup'] = config['restoreBackup']
            finalResponse['addDeleteDestinations'] = config['addDeleteDestinations']
            finalResponse['scheduleBackups'] = config['scheduleBackups']
            finalResponse['remoteBackups'] = config['remoteBackups']

            ## SSL Management

            finalResponse['manageSSL'] = config['manageSSL']
            finalResponse['hostnameSSL'] = config['hostnameSSL']
            finalResponse['mailServerSSL'] = config['mailServerSSL']

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

            newACL = ACL(name='admin', adminStatus=1, config=ACLManager.AdminACL)
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
                         config=ACLManager.ResellerACL
                         )
            newACL.save()

            ## User ACL
            newACL = ACL(name='user', config=ACLManager.UserACL)
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
            return Administrator.objects.all().exclude(pk=userID).order_by('userName')
        else:
            admins = Administrator.objects.filter(owner=admin.pk).order_by('userName')
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
    def findAllSites(currentACL, userID, fetchChilds = 0):
        websiteNames = []

        if currentACL['admin'] == 1:
            allWebsites = Websites.objects.all().order_by('domain')

            for items in allWebsites:
                websiteNames.append(items.domain)

                if fetchChilds:
                    for child in items.childdomains_set.all().order_by('domain'):
                        websiteNames.append(child.domain)
        else:
            admin = Administrator.objects.get(pk=userID)

            websites = admin.websites_set.all().order_by('domain')
            admins = Administrator.objects.filter(owner=admin.pk)

            for items in websites:
                websiteNames.append(items.domain)

                if fetchChilds:
                    for child in items.childdomains_set.all().order_by('domain'):
                        websiteNames.append(child.domain)

            for items in admins:
                webs = items.websites_set.all().order_by('domain')
                for web in webs:
                    websiteNames.append(web.domain)

                    if fetchChilds:
                        for child in web.childdomains_set.all().order_by('domain'):
                            websiteNames.append(child.domain)


        return websiteNames

    @staticmethod
    def getPHPString(phpVersion):

        if phpVersion == "PHP 5.3":
            php = "53"
        elif phpVersion == "PHP 5.4":
            php = "54"
        elif phpVersion == "PHP 5.5":
            php = "55"
        elif phpVersion == "PHP 5.6":
            php = "56"
        elif phpVersion == "PHP 7.0":
            php = "70"
        elif phpVersion == "PHP 7.1":
            php = "71"
        elif phpVersion == "PHP 7.2":
            php = "72"
        elif phpVersion == "PHP 7.3":
            php = "73"
        elif phpVersion == "PHP 7.4":
            php = "74"
        elif phpVersion == "PHP 8.0":
            php = "80"
        elif phpVersion == "PHP 8.1":
            php = "81"
        elif phpVersion == "PHP 8.2":
            php = "82"
        elif phpVersion == "PHP 8.3":
            php = "83"
        elif phpVersion == "PHP 8.4":
            php = "84"

        return php

    @staticmethod
    def searchWebsiteObjects(currentACL, userID, searchTerm):
        if currentACL['admin'] == 1:
            # Get websites that match the search term
            websites = Websites.objects.filter(domain__istartswith=searchTerm)
            # Get WordPress sites that match the search term
            wp_sites = WPSites.objects.filter(title__icontains=searchTerm)
            # Add WordPress sites' parent websites to the results
            for wp in wp_sites:
                if wp.owner not in websites:
                    websites = websites | Websites.objects.filter(pk=wp.owner.pk)
            return websites
        else:
            websiteList = []
            admin = Administrator.objects.get(pk=userID)

            # Get websites that match the search term
            websites = admin.websites_set.filter(domain__istartswith=searchTerm)
            for items in websites:
                websiteList.append(items)

            # Get WordPress sites that match the search term
            wp_sites = WPSites.objects.filter(title__icontains=searchTerm)
            for wp in wp_sites:
                if wp.owner.admin == admin and wp.owner not in websiteList:
                    websiteList.append(wp.owner)

            admins = Administrator.objects.filter(owner=admin.pk)
            for items in admins:
                # Get websites that match the search term
                webs = items.websites_set.filter(domain__istartswith=searchTerm)
                for web in webs:
                    if web not in websiteList:
                        websiteList.append(web)
                
                # Get WordPress sites that match the search term
                wp_sites = WPSites.objects.filter(title__icontains=searchTerm)
                for wp in wp_sites:
                    if wp.owner.admin == items and wp.owner not in websiteList:
                        websiteList.append(wp.owner)

            return websiteList

    @staticmethod
    def findWebsiteObjects(currentACL, userID):
        if currentACL['admin'] == 1:
            return Websites.objects.all().order_by('domain')
        else:

            websiteList = []
            admin = Administrator.objects.get(pk=userID)

            websites = admin.websites_set.all().order_by('domain')

            for items in websites:
                websiteList.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                webs = items.websites_set.all().order_by('domain')
                for web in webs:
                    websiteList.append(web)

            return websiteList

    @staticmethod
    def findDockersiteObjects(currentACL, userID):
        if currentACL['admin'] == 1:
            return DockerSites.objects.all()
        else:

            DockersiteList = []
            admin = Administrator.objects.get(pk=userID)

            websites = admin.DockerSites_set.all()

            for items in websites:
                DockersiteList.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                webs = items.DockerSites_set.all()
                for web in webs:
                    DockersiteList.append(web)

            return DockersiteList

    @staticmethod
    def findAllDomains(currentACL, userID):
        domainsList = []

        if currentACL['admin'] == 1:
            domains = Websites.objects.all().order_by('domain')
            for items in domains:
                domainsList.append(items.domain)

                for childs in items.childdomains_set.all():
                    domainsList.append(childs.domain)

        else:
            admin = Administrator.objects.get(pk=userID)
            domains = admin.websites_set.all().order_by('domain')

            for items in domains:
                domainsList.append(items.domain)
                for childs in items.childdomains_set.all():
                    domainsList.append(childs.domain)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                doms = items.websites_set.all().order_by('domain')
                for dom in doms:
                    domainsList.append(dom.domain)
                    for childs in dom.childdomains_set.all():
                        domainsList.append(childs.domain)

        return domainsList

    @staticmethod
    def findAllWebsites(currentACL, userID):
        domainsList = []

        if currentACL['admin'] == 1:
            domains = Websites.objects.all().order_by('domain')
            for items in domains:
                domainsList.append(items.domain)
        else:
            admin = Administrator.objects.get(pk=userID)
            domains = admin.websites_set.all().order_by('domain')

            for items in domains:
                domainsList.append(items.domain)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                doms = items.websites_set.all().order_by('domain')
                for dom in doms:
                    domainsList.append(dom.domain)
        return domainsList

    @staticmethod
    def findAllDNSZones(currentACL, userID):
        from dns.models import Domains
        zonesList = []
        
        if currentACL['admin'] == 1:
            zones = Domains.objects.all().order_by('name')
            for zone in zones:
                zonesList.append(zone.name)
        else:
            admin = Administrator.objects.get(pk=userID)
            zones = Domains.objects.filter(admin=admin).order_by('name')
            
            for zone in zones:
                zonesList.append(zone.name)
            
            # Include zones from owned admins
            admins = Administrator.objects.filter(owner=admin.pk)
            for item in admins:
                owned_zones = Domains.objects.filter(admin=item).order_by('name')
                for zone in owned_zones:
                    zonesList.append(zone.name)
        
        return list(set(zonesList))  # Remove duplicates
    
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
    def checkGDriveOwnership(gD, admin, currentACL):

        try:
            if currentACL['admin'] == 1:
                return 1
            elif gD.owner == admin:
                return 1
            elif gD.owner.owner == admin.pk:
                    return 1

            return 0
        except:
            return 0

    @staticmethod
    def checkOwnershipZone(domain, admin, currentACL):
        # First check if user is admin
        if currentACL['admin'] == 1:
            return 1
            
        # Try to find domain in Websites table
        try:
            websiteDomain = Websites.objects.get(domain=domain)
            if websiteDomain.admin == admin or websiteDomain.admin.owner == admin.pk:
                return 1
        except:
            pass
            
        # Try to find domain in ChildDomains table
        try:
            childDomain = ChildDomains.objects.get(domain=domain)
            if childDomain.master.admin == admin or childDomain.master.admin.owner == admin.pk:
                return 1
        except:
            pass
            
        # Try to find domain in DNS Domains table (for standalone DNS zones)
        try:
            from dns.models import Domains
            dnsDomain = Domains.objects.get(name=domain)
            if dnsDomain.admin == admin:
                return 1
            # Check if the DNS zone is owned by a user owned by current admin
            if dnsDomain.admin.owner == admin.pk:
                return 1
        except:
            pass
            
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
            for childDomain in website.childdomains_set.all().order_by('domain'):
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

    @staticmethod
    def CheckDomainBlackList(domain):
        import socket

        BlackList = [ socket.gethostname(), 'hotmail.com', 'gmail.com', 'yandex.com', 'yahoo.com', 'localhost', 'aol.com', 'apple.com',
                     'cloudlinux.com', 'email.com', 'facebook.com', 'gmx.de', 'gmx.com', 'google.com',
                     'hushmail.com', 'icloud.com', 'inbox.com', 'imunify360.com', 'juno.com', 'live.com', 'localhost.localdomain',
                     'localhost4.localdomain4', 'localhost6.localdomain6','mail.com', 'mail.ru', 'me.com',
                     'microsoft.com', 'mxlogic.net', 'outlook.com', 'protonmail.com', 'twitter.com', 'yandex.ru']

        DotsCounter = domain.count('.')

        for black in BlackList:
            if DotsCounter == 1:
                if domain == black:
                    return 0
            else:
                if domain.endswith(black):
                    logging.writeToFile(black)
                    return 0

        return 1

    @staticmethod
    def CheckStatusFilleLoc(statusFile, domain=None):
        if statusFile.find('panel/') > -1:
            TemFilePath = statusFile.split('panel/')[1]
        else:
            TemFilePath = statusFile.split('tmp/')[1]

        try:
            value = int(TemFilePath)
            print(value)
        except:
            if domain != None:
                value = statusFile.split('cyberpanel/')[1]
                #logging.writeToFile(f'value of log file {value}')
                if value == f'{domain}_rustic_backup_log':
                    return 1
            return 0

        if (statusFile[:18] != "/home/cyberpanel/." or statusFile[:16] == "/home/cyberpanel" or statusFile[:4] == '/tmp' or statusFile[
                                                                                                                 :18] == '/usr/local/CyberCP') \
                and statusFile != '/usr/local/CyberCP/CyberCP/settings.py' and statusFile.find(
            '..') == -1 and statusFile != '/home/cyberpanel/.my.cnf' and statusFile != '/home/cyberpanel/.bashrc' and statusFile != '/home/cyberpanel/.bash_logout' and statusFile != '/home/cyberpanel/.profile':
            return 1
        else:
            return 0

    @staticmethod
    def FetchExternalApp(domain):
        try:
            childDomain = ChildDomains.objects.get(domain=domain)

            return childDomain.master.externalApp

        except:
            domainName = Websites.objects.get(domain=domain)
            return domainName.externalApp

    @staticmethod
    def CreateSecureDir():
        ### Check if upload path tmp dir is not available

        UploadPath = '/usr/local/CyberCP/tmp/'

        if not os.path.exists(UploadPath):
            command = 'mkdir %s' % (UploadPath)
            ProcessUtilities.executioner(command)

        command = 'chown cyberpanel:cyberpanel %s' % (UploadPath)
        ProcessUtilities.executioner(command)

        command = 'chmod 711 %s' % (UploadPath)
        ProcessUtilities.executioner(command)


    @staticmethod
    def GetServiceStatus(dic):
        if os.path.exists('/home/cyberpanel/postfix'):
            dic['emailAsWhole'] = 1
        else:
            dic['emailAsWhole'] = 0

        if os.path.exists('/home/cyberpanel/pureftpd'):
            dic['ftpAsWhole'] = 1
        else:
            dic['ftpAsWhole'] = 0

        try:
            pdns = PDNSStatus.objects.get(pk=1)
            dic['dnsAsWhole'] = pdns.serverStatus
        except:
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                pdnsPath = '/etc/powerdns'
            else:
                pdnsPath = '/etc/pdns'

            if os.path.exists(pdnsPath):
                PDNSStatus(serverStatus=1).save()
                dic['dnsAsWhole'] = 1
            else:
                dic['dnsAsWhole'] = 0

    @staticmethod
    def GetALLWPObjects(currentACL, userID):
        from websiteFunctions.models import WPSites

        wpsites = WPSites.objects.none()
        websites = ACLManager.findWebsiteObjects(currentACL, userID)

        for website in websites:
            wpsites |= website.wpsites_set.all()

        return wpsites

    @staticmethod
    def GetServerIP():
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        return ipData.split('\n', 1)[0]

    @staticmethod
    def CheckForPremFeature(feature):
        try:

            if ProcessUtilities.decideServer() == ProcessUtilities.ent:
                return 1

            url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
            data = {
                "name": feature,
                "IP": ACLManager.GetServerIP()
            }

            import requests
            response = requests.post(url, data=json.dumps(data))
            return response.json()['status']
        except:
            return 1

    @staticmethod
    def CheckIPBackupObjectOwner(currentACL, backupobj, user):
        if currentACL['admin'] == 1:
            return 1
        elif backupobj.owner == user:
            return 1
        else:
            return 0

    @staticmethod
    def CheckIPPluginObjectOwner(currentACL, backupobj, user):
        if currentACL['admin'] == 1:
            return 1
        elif backupobj.owner == user:
            return 1
        else:
            return 0

    @staticmethod
    def FetchCloudFlareAPIKeyFromAcme():
        try:

            command = 'grep SAVED_CF_Key= /root/.acme.sh/account.conf | cut -d= -f2 | tr -d "\'"'
            SAVED_CF_Key = ProcessUtilities.outputExecutioner(command).rstrip('\n')

            command = 'grep SAVED_CF_Email= /root/.acme.sh/account.conf | cut -d= -f2 | tr -d "\'"'
            SAVED_CF_Email = ProcessUtilities.outputExecutioner(command).rstrip('\n')

            if len(SAVED_CF_Key) > 3 and len(SAVED_CF_Email) > 3:
                return 1, SAVED_CF_Key, SAVED_CF_Email
            else:
                return 0, 'Key not defined', SAVED_CF_Email

        except BaseException as msg:
            return 0, str(msg), None


    @staticmethod
    def FindDocRootOfSite(vhostConf,domainName):
        try:
            if vhostConf == None:
                vhostConf = f'/usr/local/lsws/conf/vhosts/{domainName}/vhost.conf'

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "awk '/docRoot/ {print $2}' " + vhostConf
                docRoot = ProcessUtilities.outputExecutioner(command, 'root', True).rstrip('\n')
                #docRoot = docRoot.replace('$VH_ROOT', f'/home/{domainName}')
                return docRoot
            else:
                command = "awk '/DocumentRoot/ {print $2; exit}' " + vhostConf
                docRoot = ProcessUtilities.outputExecutioner(command, 'root', True).rstrip('\n')
                return docRoot
        except:
            pass

    @staticmethod
    def ReplaceDocRoot(vhostConf, domainName, NewDocRoot):
        try:
            if vhostConf == None:
                vhostConf = f'/usr/local/lsws/conf/vhosts/{domainName}/vhost.conf'

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                #command = f"sed -i 's/docRoot\s\s*.*/docRoot                   {NewDocRoot}/g " + vhostConf
                command = f"sed -i 's#docRoot\s\s*.*#docRoot                   {NewDocRoot}#g' " + vhostConf
                ProcessUtilities.executioner(command, 'root', True)
            else:
                command = f"sed -i 's#DocumentRoot\s\s*[^[:space:]]*#DocumentRoot {NewDocRoot}#g' " + vhostConf
                ProcessUtilities.executioner(command, 'root', True)
                
        except:
            pass

    @staticmethod
    def FindDocRootOfSiteApache(vhostConf, domainName):
        try:
            finalConfPath = ApacheVhost.configBasePath + domainName + '.conf'

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                if os.path.exists(finalConfPath):
                    command = "awk '/DocumentRoot/ {print $2; exit}' " + finalConfPath
                    docRoot = ProcessUtilities.outputExecutioner(command, 'root', True).rstrip('\n')
                    return docRoot
                else:
                    return None
            else:
                return None

        except:
            return None

    @staticmethod
    def ReplaceDocRootApache(vhostConf, domainName, NewDocRoot):
        try:
            finalConfPath = ApacheVhost.configBasePath + domainName + '.conf'

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = f"sed -i 's#DocumentRoot\s\s*[^[:space:]]*#DocumentRoot {NewDocRoot}#g' " + finalConfPath
                ProcessUtilities.executioner(command, 'root', True)
        except:
            pass


    @staticmethod
    def ISARM():

        command = 'uname -a'
        result = ProcessUtilities.outputExecutioner(command)

        if result.find('aarch64') > -1:
            return True
        else:
            return False

    #### if you update this function needs to update this function on plogical.acl.py as well
    @staticmethod
    def fixPermissions():
        try:

            try:
                def generate_pass(length=14):
                    chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
                    size = length
                    return ''.join(random.choice(chars) for x in range(size))

                content = """<?php
$_ENV['snappymail_INCLUDE_AS_API'] = true;
include '/usr/local/CyberCP/public/snappymail/index.php';

$oConfig = \snappymail\Api::Config();
$oConfig->SetPassword('%s');
echo $oConfig->Save() ? 'Done' : 'Error';

?>""" % (generate_pass())

                writeToFile = open('/usr/local/CyberCP/public/snappymail.php', 'w')
                writeToFile.write(content)
                writeToFile.close()

                command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/data"
                ProcessUtilities.executioner(command, 'root', True)

            except:
                pass


            command = "usermod -G lscpd,lsadm,nobody lscpd"
            ProcessUtilities.executioner(command, 'root', True)

            command = "usermod -G lscpd,lsadm,nogroup lscpd"
            ProcessUtilities.executioner(command, 'root', True)

            ###### fix Core CyberPanel permissions

            command = "find /usr/local/CyberCP -type d -exec chmod 0755 {} \;"
            ProcessUtilities.executioner(command, 'root', True)

            command = "find /usr/local/CyberCP -type f -exec chmod 0644 {} \;"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod -R 755 /usr/local/CyberCP/bin"
            ProcessUtilities.executioner(command, 'root', True)

            ## change owner

            command = "chown -R root:root /usr/local/CyberCP"
            ProcessUtilities.executioner(command, 'root', True)

            ########### Fix LSCPD

            command = "find /usr/local/lscp -type d -exec chmod 0755 {} \;"
            ProcessUtilities.executioner(command, 'root', True)

            command = "find /usr/local/lscp -type f -exec chmod 0644 {} \;"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod -R 755 /usr/local/lscp/bin"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod -R 755 /usr/local/lscp/fcgi-bin"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp"
            ProcessUtilities.executioner(command, 'root', True)

            ## change owner

            command = "chown -R root:root /usr/local/lscp"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod 700 /usr/local/CyberCP/cli/cyberPanel.py"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod 700 /usr/local/CyberCP/plogical/upgradeCritical.py"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod 755 /usr/local/CyberCP/postfixSenderPolicy/client.py"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chmod 640 /usr/local/CyberCP/CyberCP/settings.py"
            ProcessUtilities.executioner(command, 'root', True)

            command = "chown root:cyberpanel /usr/local/CyberCP/CyberCP/settings.py"
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
            ProcessUtilities.executioner(command, 'root', True)

            files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
                     '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                     '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                     '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
                     '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

            for items in files:
                command = 'chmod 644 %s' % (items)
                ProcessUtilities.executioner(command, 'root', True)

            impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                       '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                       '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
                       '/etc/powerdns/pdns.conf']

            for items in impFile:
                command = 'chmod 600 %s' % (items)
                ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 640 /etc/postfix/*.cf'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 640 /etc/dovecot/*.conf'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 640 /etc/dovecot/dovecot-sql.conf.ext'
            ProcessUtilities.executioner(command, 'root', True)

            fileM = ['/usr/local/lsws/FileManager/', '/usr/local/CyberCP/install/FileManager',
                     '/usr/local/CyberCP/serverStatus/litespeed/FileManager',
                     '/usr/local/lsws/Example/html/FileManager']

            import shutil
            for items in fileM:
                try:
                    shutil.rmtree(items)
                except:
                    pass

            command = 'chmod 755 /etc/pure-ftpd/'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 644 /etc/dovecot/dovecot.conf'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 644 /etc/postfix/main.cf'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 644 /etc/postfix/dynamicmaps.cf'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod +x /usr/local/CyberCP/plogical/renew.py'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
            ProcessUtilities.executioner(command, 'root', True)

            clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py'
                , '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
                         '/usr/local/CyberCP/CLScript/CloudLinuxDB.py', '/usr/local/CyberCP/CLScript/UserInfo.py']

            for items in clScripts:
                command = 'chmod +x %s' % (items)
                ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 600 /usr/local/CyberCP/plogical/adminPass.py'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 600 /etc/cagefs/exclude/cyberpanelexclude'
            ProcessUtilities.executioner(command, 'root', True)

            command = "find /usr/local/CyberCP/ -name '*.pyc' -delete"
            ProcessUtilities.executioner(command, 'root', True)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                command = 'chown root:pdns /etc/pdns/pdns.conf'
                ProcessUtilities.executioner(command, 'root', True)

                command = 'chmod 640 /etc/pdns/pdns.conf'
                ProcessUtilities.executioner(command, 'root', True)
            else:
                command = 'chown root:pdns /etc/powerdns/pdns.conf'
                ProcessUtilities.executioner(command, 'root', True)

                command = 'chmod 640 /etc/powerdns/pdns.conf'
                ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
            ProcessUtilities.executioner(command, 'root', True)

            command = '/usr/local/lsws/lsphp83/bin/php /usr/local/CyberCP/public/snappymail.php'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 600 /usr/local/CyberCP/public/snappymail.php'
            ProcessUtilities.executioner(command, 'root', True)

            ###

            WriteToFile = open('/etc/fstab', 'a')
            WriteToFile.write('proc    /proc        proc        defaults,hidepid=2    0 0\n')
            WriteToFile.close()

            command = 'mount -o remount,rw,hidepid=2 /proc'
            ProcessUtilities.executioner(command, 'root', True)

            ###

            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            if not os.path.exists(CentOSPath) or not os.path.exists(openEulerPath):
                group = 'nobody'
            else:
                group = 'nogroup'

            command = 'chown root:%s /usr/local/lsws/logs' % (group)
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 750 /usr/local/lsws/logs'
            ProcessUtilities.executioner(command, 'root', True)

            ## symlink protection

            writeToFile = open('/usr/lib/sysctl.d/50-default.conf', 'a')
            writeToFile.writelines('fs.protected_hardlinks = 1\n')
            writeToFile.writelines('fs.protected_symlinks = 1\n')
            writeToFile.close()

            command = 'sysctl --system'
            ProcessUtilities.executioner(command, 'root', True)

            command = 'chmod 700 %s' % ('/home/cyberpanel')
            ProcessUtilities.executioner(command, 'root', True)

            destPrivKey = "/usr/local/lscp/conf/key.pem"

            command = 'chmod 600 %s' % (destPrivKey)
            ProcessUtilities.executioner(command, 'root', True)



        except BaseException as msg:
            logging.writeToFile(str(msg) + " [fixPermissions]")




