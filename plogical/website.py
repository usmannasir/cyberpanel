#!/usr/local/CyberCP/bin/python2
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from acl import ACLManager
import CyberCPLogFileWriter as logging
from websiteFunctions.models import Websites, ChildDomains
from virtualHostUtilities import virtualHostUtilities
import subprocess
import shlex
from installUtilities import installUtilities
from django.shortcuts import HttpResponse, render
from loginSystem.models import Administrator, ACL
from packages.models import Package
from mailUtilities import mailUtilities
from random import randint
import time
import re
from childDomain import ChildDomainManager
from math import ceil
from plogical.alias import AliasManager
from plogical.applicationInstaller import ApplicationInstaller
from databases.models import Databases
import randomPassword as randomPassword
import hashlib
from mysqlUtilities import mysqlUtilities
from plogical import hashPassword
from emailMarketing.emACL import emACL
from processUtilities import ProcessUtilities
from managePHP.phpManager import PHPManager

class WebsiteManager:
    def __init__(self, domain = None, childDomain = None):
        self.domain = domain
        self.childDomain = childDomain

    def createWebsite(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createWebsite') == 0:
                return ACLManager.loadError()

            adminNames = ACLManager.loadAllUsers(userID)
            packagesName = ACLManager.loadPackages(userID, currentACL)
            phps = PHPManager.findPHPVersions()

            Data = {'packageList': packagesName, "owernList": adminNames, 'phps': phps}
            return render(request, 'websiteFunctions/createWebsite.html', Data)

        except BaseException, msg:
            return HttpResponse(str(msg))

    def modifyWebsite(self, request = None, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'modifyWebsite') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)
            phps = PHPManager.findPHPVersions()

            return render(request, 'websiteFunctions/modifyWebsite.html', {'websiteList': websitesName, 'phps': phps})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def deleteWebsite(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteWebsite') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)


            return render(request, 'websiteFunctions/deleteWebsite.html', {'websiteList': websitesName})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def siteState(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if ACLManager.currentContextPermission(currentACL, 'suspendWebsite') == 0:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'websiteFunctions/suspendWebsite.html', {'websiteList': websitesName})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def listWebsites(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pagination = self.websitePagination(currentACL, userID)

            return render(request, 'websiteFunctions/listWebsites.html', {"pagination": pagination})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def listCron(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            websitesName = ACLManager.findAllSites(currentACL, userID)
            return render(request, 'websiteFunctions/listCron.html', {'websiteList': websitesName})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def domainAlias(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            aliasManager = AliasManager(self.domain)
            noAlias, finalAlisList = aliasManager.fetchAlisForDomains()

            path = "/home/" + self.domain + "/public_html"

            return render(request, 'websiteFunctions/domainAlias.html', {
                'masterDomain': self.domain,
                'aliases': finalAlisList,
                'path': path,
                'noAlias': noAlias
            })
        except BaseException, msg:
            return HttpResponse(str(msg))

    def submitWebsiteCreation(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createWebsite') == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            domain = data['domainName']
            #logging.CyberCPLogFileWriter.writeToFile(domain)
            adminEmail = data['adminEmail']
            phpSelection = data['phpSelection']
            packageName = data['package']
            websiteOwner = data['websiteOwner']
            try:
                HA = data['HA']
                externalApp = 'nobody'
            except:
                externalApp = "".join(re.findall("[a-zA-Z]+", domain))[:7]

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            ## Create Configurations

            execPath = "sudo /usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " createVirtualHost --virtualHostName " + domain + \
                       " --administratorEmail " + adminEmail + " --phpVersion '" + phpSelection + \
                       "' --virtualHostUser " + externalApp + " --ssl " + str(data['ssl']) + " --dkimCheck " \
                       + str(data['dkimCheck']) + " --openBasedir " + str(data['openBasedir']) + \
                       ' --websiteOwner ' + websiteOwner + ' --package ' + packageName + ' --tempStatusPath ' + tempStatusPath

            subprocess.Popen(shlex.split(execPath))
            time.sleep(2)

            data_ret = {'status': 1, 'createWebSiteStatus': 1, 'error_message': "None", 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException, msg:
            data_ret = {'status': 0, 'createWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDomainCreation(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            masterDomain = data['masterDomain']
            domain = data['domainName']
            phpSelection = data['phpSelection']
            path = data['path']
            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            if ACLManager.checkOwnership(masterDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            if currentACL['admin'] != 1:
                data['openBasedir'] = 1


            if len(path) > 0:
                path = path.lstrip("/")
                path = "/home/" + masterDomain + "/public_html/" + path
            else:
                path = "/home/" + masterDomain + "/public_html/" + domain

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createDomain --masterDomain " + masterDomain + " --virtualHostName " + domain + \
                       " --phpVersion '" + phpSelection + "' --ssl " + str(data['ssl']) + " --dkimCheck " + str(
                data['dkimCheck']) \
                       + " --openBasedir " + str(data['openBasedir']) + ' --path ' + path + ' --websiteOwner ' \
                       + admin.userName + ' --tempStatusPath ' + tempStatusPath

            subprocess.Popen(shlex.split(execPath))
            time.sleep(2)

            data_ret = {'status': 1, 'createWebSiteStatus': 1, 'error_message': "None", 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0,'createWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def fetchDomains(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            masterDomain = data['masterDomain']

            if ACLManager.checkOwnership(masterDomain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            cdManager = ChildDomainManager(masterDomain)
            json_data = cdManager.findChildDomainsJson()

            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def searchWebsites(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            try:
                json_data = self.searchWebsitesJson(currentACL, userID, data['patternAdded'])
            except BaseException, msg:
                tempData = {}
                tempData['page'] = 1
                return self.getFurtherAccounts(userID, tempData)

            pagination = self.websitePagination(currentACL, userID)
            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data, 'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException, msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def getFurtherAccounts(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            pageNumber = int(data['page'])
            json_data = self.findWebsitesJson(currentACL, userID, pageNumber)
            pagination = self.websitePagination(currentACL, userID)
            final_dic = {'status': 1, 'listWebSiteStatus': 1, 'error_message': "None", "data": json_data, 'pagination': pagination}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
        except BaseException, msg:
            dic = {'status': 1, 'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def submitWebsiteDeletion(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'deleteWebsite') == 0:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            websiteName = data['websiteName']

            ## Deleting master domain

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + websiteName
            subprocess.check_output(shlex.split(execPath))

            data_ret = {'status': 1, 'websiteDeleteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'websiteDeleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitDomainDeletion(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            websiteName = data['websiteName']

            if ACLManager.checkOwnership(websiteName, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('websiteDeleteStatus', 0)

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
            execPath = execPath + " deleteDomain --virtualHostName " + websiteName
            subprocess.check_output(shlex.split(execPath))

            data_ret = {'status': 1, 'websiteDeleteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'websiteDeleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitWebsiteStatus(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'suspendWebsite') == 0:
                return ACLManager.loadErrorJson('websiteStatus', 0)

            websiteName = data['websiteName']
            state = data['state']

            website = Websites.objects.get(domain=websiteName)

            if state == "Suspend":
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + websiteName
                command = "sudo mv " + confPath + " " + confPath + "-suspended"
                subprocess.call(shlex.split(command))
                installUtilities.reStartLiteSpeed()
                website.state = 0
            else:
                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + websiteName

                command = "sudo mv " + confPath + "-suspended" + " " + confPath
                subprocess.call(shlex.split(command))

                command = "chown -R " + "lsadm" + ":" + "lsadm" + " " + confPath
                cmd = shlex.split(command)
                subprocess.call(cmd)

                installUtilities.reStartLiteSpeed()
                website.state = 1

            website.save()

            data_ret = {'websiteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:

            data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def submitWebsiteModify(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'modifyWebsite') == 0:
                return ACLManager.loadErrorJson('modifyStatus', 0)

            packs = ACLManager.loadPackages(userID, currentACL)
            admins = ACLManager.loadAllUsers(userID)

            ## Get packs name

            json_data = "["
            checker = 0

            for items in packs:
                dic = {"pack": items}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            ### Get admin names

            admin_data = "["
            checker = 0

            for items in admins:
                dic = {"adminNames": items}

                if checker == 0:
                    admin_data = admin_data + json.dumps(dic)
                    checker = 1
                else:
                    admin_data = admin_data + ',' + json.dumps(dic)

            admin_data = admin_data + ']'

            websiteToBeModified = data['websiteToBeModified']

            modifyWeb = Websites.objects.get(domain=websiteToBeModified)

            email = modifyWeb.adminEmail
            currentPack = modifyWeb.package.packageName
            owner = modifyWeb.admin.userName

            data_ret = {'status': 1, 'modifyStatus': 1, 'error_message': "None", "adminEmail": email,
                        "packages": json_data, "current_pack": currentPack, "adminNames": admin_data,
                        'currentAdmin': owner}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)

        except BaseException, msg:
            dic = {'status': 0, 'modifyStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def fetchWebsiteDataJSON(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'createWebsite') == 0:
                return ACLManager.loadErrorJson('createWebSiteStatus', 0)

            packs = ACLManager.loadPackages(userID, currentACL)
            admins = ACLManager.loadAllUsers(userID)

            ## Get packs name

            json_data = "["
            checker = 0

            for items in packs:
                dic = {"pack": items}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            ### Get admin names

            admin_data = "["
            checker = 0

            for items in admins:
                dic = {"adminNames": items}

                if checker == 0:
                    admin_data = admin_data + json.dumps(dic)
                    checker = 1
                else:
                    admin_data = admin_data + ',' + json.dumps(dic)

            admin_data = admin_data + ']'

            data_ret = {'status': 1, 'error_message': "None",
                        "packages": json_data, "adminNames": admin_data}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)

        except BaseException, msg:
            dic = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def saveWebsiteChanges(self, userID = None, data = None):
        try:
            domain = data['domain']
            package = data['packForWeb']
            email = data['email']
            phpVersion = data['phpVersion']
            newUser = data['admin']

            currentACL = ACLManager.loadedACL(userID)
            if ACLManager.currentContextPermission(currentACL, 'modifyWebsite') == 0:
                return ACLManager.loadErrorJson('saveStatus', 0)

            confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domain
            completePathToConfigFile = confPath + "/vhost.conf"

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'status': 0, 'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

                ## php changes ends

            newOwner = Administrator.objects.get(userName=newUser)

            modifyWeb = Websites.objects.get(domain=domain)
            webpack = Package.objects.get(packageName=package)

            modifyWeb.package = webpack
            modifyWeb.adminEmail = email
            modifyWeb.phpSelection = phpVersion
            modifyWeb.admin = newOwner

            modifyWeb.save()

            data_ret = {'status': 1, 'saveStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0, 'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def loadDomainHome(self, request = None, userID = None, data = None):

        if Websites.objects.filter(domain=self.domain).exists():

            currentACL = ACLManager.loadedACL(userID)
            website = Websites.objects.get(domain=self.domain)
            admin = Administrator.objects.get(pk=userID)


            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            Data = {}

            marketingStatus = emACL.checkIfEMEnabled(admin.userName)

            Data['marketingStatus'] = marketingStatus
            Data['ftpTotal'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['databasesUsed'] = website.databases_set.all().count()
            Data['databasesTotal'] = website.package.dataBases

            Data['domain'] = self.domain

            diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + self.domain, website.package.diskSpace)

            ## bw usage calculation

            try:
                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " findDomainBW --virtualHostName " + self.domain + " --bandwidth " + str(
                    website.package.bandwidth)

                output = subprocess.check_output(shlex.split(execPath))
                bwData = output.split(",")
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg))
                bwData = [0, 0]

            ## bw usage calculations

            Data['bwInMBTotal'] = website.package.bandwidth
            Data['bwInMB'] = bwData[0]
            Data['bwUsage'] = bwData[1]

            if diskUsageDetails != None:
                if diskUsageDetails[1] > 100:
                    diskUsageDetails[1] = 100

                Data['diskUsage'] = diskUsageDetails[1]
                Data['diskInMB'] = diskUsageDetails[0]
                Data['diskInMBTotal'] = website.package.diskSpace
            else:
                Data['diskUsage'] = 0
                Data['diskInMB'] = 0
                Data['diskInMBTotal'] = website.package.diskSpace

            Data['phps'] = PHPManager.findPHPVersions()

            return render(request, 'websiteFunctions/website.html', Data)

        else:
            return render(request, 'websiteFunctions/website.html',
                          {"error": 1, "domain": "This domain does not exists."})

    def launchChild(self, request = None, userID = None, data = None):

        if ChildDomains.objects.filter(domain=self.childDomain).exists():
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            website = Websites.objects.get(domain=self.domain)

            Data = {}

            Data['ftpTotal'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['databasesUsed'] = website.databases_set.all().count()
            Data['databasesTotal'] = website.package.dataBases

            Data['domain'] = self.domain
            Data['childDomain'] = self.childDomain

            diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + self.domain, website.package.diskSpace)

            ## bw usage calculation

            try:
                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " findDomainBW --virtualHostName " + self.domain + " --bandwidth " + str(
                    website.package.bandwidth)

                output = subprocess.check_output(shlex.split(execPath))
                bwData = output.split(",")
            except BaseException, msg:
                logging.CyberCPLogFileWriter.writeToFile(str(msg))
                bwData = [0, 0]

            ## bw usage calculations

            Data['bwInMBTotal'] = website.package.bandwidth
            Data['bwInMB'] = bwData[0]
            Data['bwUsage'] = bwData[1]

            if diskUsageDetails != None:
                if diskUsageDetails[1] > 100:
                    diskUsageDetails[1] = 100

                Data['diskUsage'] = diskUsageDetails[1]
                Data['diskInMB'] = diskUsageDetails[0]
                Data['diskInMBTotal'] = website.package.diskSpace
            else:
                Data['diskUsage'] = 0
                Data['diskInMB'] = 0
                Data['diskInMBTotal'] = website.package.diskSpace

            Data['phps'] = PHPManager.findPHPVersions()

            return render(request, 'websiteFunctions/launchChild.html', Data)
        else:
            return render(request, 'websiteFunctions/launchChild.html', {"error":1,"domain": "This child domain does not exists"})

    def getDataFromLogFile(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        logType = data['logType']
        self.domain = data['virtualHost']
        page = data['page']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('logstatus', 0)


        if logType == 1:
            fileName = "/home/" + self.domain + "/logs/" + self.domain + ".access_log"
        else:
            fileName = "/home/" + self.domain + "/logs/" + self.domain + ".error_log"

        ## get Logs

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " getAccessLogs --path " + fileName + " --page " + str(page)

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            final_json = json.dumps(
                {'status': 0,'logstatus': 0, 'error_message': "Not able to fetch logs, see CyberPanel main log file!"})
            return HttpResponse(final_json)

        ## get log ends here.


        data = output.split("\n")

        json_data = "["
        checker = 0

        for items in reversed(data):
            if len(items) > 10:
                logData = items.split(" ")
                domain = logData[0].strip('"')
                ipAddress = logData[1]
                time = (logData[4]).strip("[").strip("]")
                resource = logData[7].strip('"')
                size = logData[10].replace('"', '')

                dic = {'domain': domain,
                       'ipAddress': ipAddress,
                       'time': time,
                       'resource': resource,
                       'size': size,
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'
        final_json = json.dumps({'status': 1, 'logstatus': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)

    def fetchErrorLogs(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        self.domain = data['virtualHost']
        page = data['page']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('logstatus', 0)

        fileName = "/home/" + self.domain + "/logs/" + self.domain + ".error_log"

        ## get Logs

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " getErrorLogs --path " + fileName + " --page " + str(page)

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            final_json = json.dumps(
                {'status': 0, 'logstatus': 0, 'error_message': "Not able to fetch logs, see CyberPanel main log file!"})
            return HttpResponse(final_json)

        ## get log ends here.

        final_json = json.dumps({'status': 1, 'logstatus': 1, 'error_message': "None", "data": output})
        return HttpResponse(final_json)

    def getDataFromConfigFile(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('configstatus', 0)

        filePath = installUtilities.Server_root_path + "/conf/vhosts/" + self.domain + "/vhost.conf"

        command = 'sudo cat ' + filePath
        configData = subprocess.check_output(shlex.split(command))

        if len(configData) == 0:
            status = {'status': 0, "configstatus": 0, "error_message": "Configuration file is currently empty!"}

            final_json = json.dumps(status)
            return HttpResponse(final_json)

        status = {'status': 1, "configstatus": 1, "configData": configData}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

    def saveConfigsToFile(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('configstatus', 0)

        configData = data['configData']
        self.domain = data['virtualHost']

        mailUtilities.checkHome()

        tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        vhost = open(tempPath, "w")

        vhost.write(configData)

        vhost.close()

        ## writing data temporary to file

        filePath = installUtilities.Server_root_path + "/conf/vhosts/" + self.domain + "/vhost.conf"

        ## save configuration data

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " saveVHostConfigs --path " + filePath + " --tempPath " + tempPath

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            status = {"configstatus": 1}

            final_json = json.dumps(status)
            return HttpResponse(final_json)
        else:
            data_ret = {'configstatus': 0, 'error_message': output}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        ## save configuration data ends

    def getRewriteRules(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('rewriteStatus', 0)

        try:
            childDom = ChildDomains.objects.get(domain=self.domain)
            filePath = childDom.path + '/.htaccess'
        except:
            filePath = "/home/" + self.domain + "/public_html/.htaccess"

        try:
            rewriteRules = open(filePath, "r").read()

            if len(rewriteRules) == 0:
                status = {"rewriteStatus": 1, "error_message": "Rules file is currently empty"}
                final_json = json.dumps(status)
                return HttpResponse(final_json)

            status = {"rewriteStatus": 1, "rewriteRules": rewriteRules}

            final_json = json.dumps(status)
            return HttpResponse(final_json)

        except IOError:
            status = {"rewriteStatus": 1, "error_message": "none", "rewriteRules": ""}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

    def saveRewriteRules(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']
        rewriteRules = data['rewriteRules']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('rewriteStatus', 0)

        ## writing data temporary to file

        mailUtilities.checkHome()
        tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
        vhost = open(tempPath, "w")
        vhost.write(rewriteRules)
        vhost.close()

        ## writing data temporary to file

        try:
            childDomain = ChildDomains.objects.get(domain=self.domain)
            filePath = childDomain.path + '/.htaccess'
        except:
            filePath = "/home/" + self.domain + "/public_html/.htaccess"

        ## save configuration data

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " saveRewriteRules --virtualHostName " + self.domain + " --path " + filePath + " --tempPath " + tempPath

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            status = {"rewriteStatus": 1, 'error_message': output}
            final_json = json.dumps(status)
            return HttpResponse(final_json)
        else:
            data_ret = {'rewriteStatus': 0, 'error_message': output}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def saveSSL(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['virtualHost']
        key = data['key']
        cert = data['cert']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('sslStatus', 0)

        mailUtilities.checkHome()

        ## writing data temporary to file


        tempKeyPath = "/home/cyberpanel/" + str(randint(1000, 9999))
        vhost = open(tempKeyPath, "w")
        vhost.write(key)
        vhost.close()

        tempCertPath = "/home/cyberpanel/" + str(randint(1000, 9999))
        vhost = open(tempCertPath, "w")
        vhost.write(cert)
        vhost.close()

        ## writing data temporary to file

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " saveSSL --virtualHostName " + self.domain + " --tempKeyPath " + tempKeyPath + " --tempCertPath " + tempCertPath

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            data_ret = {'sslStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        else:
            logging.CyberCPLogFileWriter.writeToFile(
                output)
            data_ret = {'sslStatus': 0, 'error_message': output}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changePHP(self, userID = None, data = None):

        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        self.domain = data['childDomain']
        phpVersion = data['phpSelection']

        if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadErrorJson('changePHP', 0)


        confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + self.domain
        completePathToConfigFile = confPath + "/vhost.conf"

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            pass
        else:
            data_ret = {'status': 1, 'changePHP': 0, 'error_message': output}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        data_ret = {'status': 1, 'changePHP': 1, 'error_message': "None"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    def getWebsiteCron(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)
            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('getWebsiteCron', 0)

            website = Websites.objects.get(domain=self.domain)

            if Websites.objects.filter(domain=self.domain).exists():
                pass
            else:
                dic = {'getWebsiteCron': 0, 'error_message': 'You do not own this domain'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                cronPath = "/var/spool/cron/" + website.externalApp
            else:
                cronPath = "/var/spool/cron/crontabs/" + website.externalApp

            cmd = 'sudo test -e ' + cronPath + ' && echo Exists'
            output = os.popen(cmd).read()

            if "Exists" not in output:
                data_ret = {'getWebsiteCron': 1, "user": website.externalApp, "crons": {}}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            crons = []

            try:
                # f = subprocess.check_output(["sudo", "cat", cronPath])
                f = subprocess.check_output(["sudo", "crontab", "-u", website.externalApp, "-l"])
            except subprocess.CalledProcessError as error:
                dic = {'getWebsiteCron': 0, 'error_message': 'Unable to access Cron file'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)
            counter = 0
            for line in f.split("\n"):
                if line:
                    split = line.split(" ", 5)
                    if len(split) == 6:
                        counter += 1
                        crons.append({"line": counter,
                                      "minute": split[0],
                                      "hour": split[1],
                                      "monthday": split[2],
                                      "month": split[3],
                                      "weekday": split[4],
                                      "command": split[5]})

            data_ret = {'getWebsiteCron': 1, "user": website.externalApp, "crons": crons}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException, msg:
            print msg
            dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def getCronbyLine(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            line = data['line']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('getWebsiteCron', 0)

            if Websites.objects.filter(domain=self.domain).exists():
                pass
            else:
                dic = {'getWebsiteCron': 0, 'error_message': 'You do not own this domain'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            line -= 1
            website = Websites.objects.get(domain=self.domain)

            cronPath = "/var/spool/cron/" + website.externalApp
            crons = []

            try:
                # f = subprocess.check_output(["sudo", "cat", cronPath])
                f = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", website.externalApp, "-l"])
                print f
            except subprocess.CalledProcessError as error:
                dic = {'getWebsiteCron': 0, 'error_message': 'Unable to access Cron file'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            f = f.split("\n")
            cron = f[line]

            if not cron:
                dic = {'getWebsiteCron': 0, 'error_message': 'Cron line empty'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            cron = cron.split(" ", 5)
            if len(cron) != 6:
                dic = {'getWebsiteCron': 0, 'error_message': 'Cron line incorrect'}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

            data_ret = {"getWebsiteCron": 1,
                        "user": website.externalApp,
                        "cron": {
                            "minute": cron[0],
                            "hour": cron[1],
                            "monthday": cron[2],
                            "month": cron[3],
                            "weekday": cron[4],
                            "command": cron[5],
                        },
                        "line": line}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException, msg:
            print msg
            dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def saveCronChanges(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            line = data['line']

            minute = data['minute']
            hour = data['hour']
            monthday = data['monthday']
            month = data['month']
            weekday = data['weekday']
            command = data['command']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('getWebsiteCron', 0)

            website = Websites.objects.get(domain=self.domain)

            tempPath = "/home/cyberpanel/" + website.externalApp + str(randint(10000, 99999)) + ".cron.tmp"

            finalCron = "%s %s %s %s %s %s" % (minute, hour, monthday, month, weekday, command)

            output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", website.externalApp, "-l"])

            if "no crontab for" in output:
                data_ret = {'addNewCron': 0, 'error_message': 'crontab file does not exists for user'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            with open(tempPath, "w+") as file:
                file.write(output)

            # Confirming that directory is read/writable
            o = subprocess.call(['sudo', 'chown', 'cyberpanel:cyberpanel', tempPath])
            if o is not 0:
                data_ret = {'addNewCron': 0, 'error_message': 'Error Changing Permissions'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            with open(tempPath, 'r') as file:
                data = file.readlines()

            data[line] = finalCron + '\n'

            with open(tempPath, 'w') as file:
                file.writelines(data)

            output = subprocess.call(["sudo", "/usr/bin/crontab", "-u", website.externalApp, tempPath])

            os.remove(tempPath)
            if output != 0:
                data_ret = {'addNewCron': 0, 'error_message': 'Incorrect Syntax cannot be accepted.'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            data_ret = {"getWebsiteCron": 1,
                        "user": website.externalApp,
                        "cron": finalCron,
                        "line": line}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException, msg:
            print msg
            dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def remCronbyLine(self, userID=None, data=None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            line = data['line']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('addNewCron', 0)

            line -= 1
            website = Websites.objects.get(domain=self.domain)

            output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", website.externalApp, "-l"])

            if "no crontab for" in output:
                data_ret = {'addNewCron': 0, 'error_message': 'No Cron exists for this user'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            tempPath = "/home/cyberpanel/" + website.externalApp + str(randint(10000, 99999)) + ".cron.tmp"

            with open(tempPath, "w+") as file:
                file.write(output)

            # Confirming that directory is read/writable
            o = subprocess.call(['sudo', 'chown', 'cyberpanel:cyberpanel', tempPath])
            if o is not 0:
                data_ret = {'addNewCron': 0, 'error_message': 'Error Changing Permissions'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            with open(tempPath, 'r') as file:
                data = file.readlines()

            removedLine = data.pop(line)

            with open(tempPath, 'w') as file:
                file.writelines(data)

            output = subprocess.call(["sudo", "/usr/bin/crontab", "-u", website.externalApp, tempPath])

            os.remove(tempPath)
            if output != 0:
                data_ret = {'addNewCron': 0, 'error_message': 'Incorrect Syntax cannot be accepted'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            data_ret = {"remCronbyLine": 1,
                        "user": website.externalApp,
                        "removeLine": removedLine,
                        "line": line}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException, msg:
            print msg
            dic = {'remCronbyLine': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def addNewCron(self, userID=None, data=None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']
            minute = data['minute']
            hour = data['hour']
            monthday = data['monthday']
            month = data['month']
            weekday = data['weekday']
            command = data['command']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('addNewCron', 0)

            website = Websites.objects.get(domain=self.domain)

            try:
                output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", website.externalApp, "-l"])
            except:
                try:
                    subprocess.call(('sudo', 'crontab', '-u', website.externalApp, '-'))
                except:
                    data_ret = {'addNewCron': 0, 'error_message': 'Unable to initialise crontab file for user'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

            output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", website.externalApp, "-l"])

            if "no crontab for" in output:
                echo = subprocess.Popen((['cat', '/dev/null']), stdout=subprocess.PIPE)
                subprocess.call(('sudo', 'crontab', '-u', website.externalApp, '-'), stdin=echo.stdout)
                echo.wait()
                echo.stdout.close()
                output = subprocess.check_output(["sudo", "/usr/bin/crontab", "-u", website.externalApp, "-l"])
                if "no crontab for" in output:
                    data_ret = {'addNewCron': 0, 'error_message': 'Unable to initialise crontab file for user'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

            tempPath = "/home/cyberpanel/" + website.externalApp + str(randint(10000, 99999)) + ".cron.tmp"

            finalCron = "%s %s %s %s %s %s" % (minute, hour, monthday, month, weekday, command)

            with open(tempPath, "a") as file:
                file.write(output + finalCron + "\n")

            output = subprocess.call(["sudo", "/usr/bin/crontab", "-u", website.externalApp, tempPath])

            os.remove(tempPath)
            if output != 0:
                data_ret = {'addNewCron': 0, 'error_message': 'Incorrect Syntax cannot be accepted'}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)

            data_ret = {"addNewCron": 1,
                        "user": website.externalApp,
                        "cron": finalCron}
            final_json = json.dumps(data_ret)
            return HttpResponse(final_json)
        except BaseException, msg:
            print msg
            dic = {'addNewCron': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)

    def submitAliasCreation(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']
            aliasDomain = data['aliasDomain']
            ssl = data['ssl']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('createAliasStatus', 0)

            sslpath = "/home/" + self.domain + "/public_html"

            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createAlias --masterDomain " + self.domain + " --aliasDomain " + aliasDomain + " --ssl " + str(
                ssl) + " --sslPath " + sslpath + " --administratorEmail " + admin.email + ' --websiteOwner ' + admin.userName

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'createAliasStatus': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ## Create Configurations ends here

            data_ret = {'createAliasStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)



        except BaseException, msg:
            data_ret = {'createAliasStatus': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def issueAliasSSL(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']
            aliasDomain = data['aliasDomain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('sslStatus', 0)


            sslpath = "/home/" + self.domain + "/public_html"

            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " issueAliasSSL --masterDomain " + self.domain + " --aliasDomain " + aliasDomain + " --sslPath " + sslpath + " --administratorEmail " + admin.email

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                data_ret = {'sslStatus': 1, 'error_message': "None", "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'sslStatus': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'sslStatus': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def delateAlias(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['masterDomain']
            aliasDomain = data['aliasDomain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('deleteAlias', 0)

            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " deleteAlias --masterDomain " + self.domain + " --aliasDomain " + aliasDomain

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                data_ret = {'deleteAlias': 1, 'error_message': "None", "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'deleteAlias': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


        except BaseException, msg:
            data_ret = {'deleteAlias': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeOpenBasedir(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            self.domain = data['domainName']
            openBasedirValue = data['openBasedirValue']

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('changeOpenBasedir', 0)

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " changeOpenBasedir --virtualHostName '" + self.domain + "' --openBasedirValue " + openBasedirValue

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'status': 0, 'changeOpenBasedir': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data_ret = {'status': 1, 'changeOpenBasedir': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'status': 0,'changeOpenBasedir': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def wordpressInstall(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'websiteFunctions/installWordPress.html', {'domainName': self.domain})

        except BaseException, msg:
            return HttpResponse(str(msg))

    def installWordpress(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)


            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['blogTitle'] = data['blogTitle']
            extraArgs['adminUser'] = data['adminUser']
            extraArgs['adminPassword'] = data['adminPassword']
            extraArgs['adminEmail'] = data['adminEmail']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            background = ApplicationInstaller('wordpress', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException, msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installWordpressStatus(self, userID = None, data = None):
        try:
            statusFile = data['statusFile']

            statusData = open(statusFile, 'r').readlines()

            lastLine = statusData[-1]

            if lastLine.find('[200]') > -1:
                command = 'sudo rm -f ' + statusFile
                subprocess.call(shlex.split(command))
                data_ret = {'abort': 1, 'installStatus': 1, 'installationProgress': "100",
                            'currentStatus': 'Successfully Installed.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            elif lastLine.find('[404]') > -1:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0",
                            'error_message': lastLine}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                progress = lastLine.split(',')
                currentStatus = progress[0]
                try:
                    installationProgress = progress[1]
                except:
                    installationProgress = 0
                data_ret = {'abort': 0, 'installStatus': 0, 'installationProgress': installationProgress,
                            'currentStatus': currentStatus}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0", 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def joomlaInstall(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'websiteFunctions/installJoomla.html', {'domainName': self.domain})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def installJoomla(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            domainName = data['domain']
            home = data['home']

            sitename = data['sitename']
            username = data['username']
            password = data['password']
            prefix = data['prefix']

            mailUtilities.checkHome()

            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Setting up paths,0')
            statusFile.close()

            finalPath = ""

            admin = Administrator.objects.get(pk=userID)

            ## DB Creation

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Creating database..,10')
            statusFile.close()

            dbName = randomPassword.generate_pass()
            dbUser = dbName
            dbPassword = randomPassword.generate_pass()

            if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(
                    dbUser=dbUser).exists():
                data_ret = {'status': 0, 'installStatus': 0,
                            'error_message': "0,This database or user is already taken."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            result = mysqlUtilities.createDatabase(dbName, dbUser, dbPassword)

            if result == 1:
                pass
            else:
                data_ret = {'status': 0, 'installStatus': 0,
                            'error_message': "0,Not able to create database."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ##



            try:
                website = ChildDomains.objects.get(domain=domainName)
                externalApp = website.master.externalApp

                if website.master.package.dataBases > website.master.databases_set.all().count():
                    pass
                else:
                    data_ret = {'status': 0, 'installStatus': 0,
                                'error_message': "0,Maximum database limit reached for this website."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if home == '0':
                    path = data['path']
                    finalPath = website.path.rstrip('/') + "/" + path + "/"
                else:
                    finalPath = website.path + "/"

                db = Databases(website=website.master, dbName=dbName, dbUser=dbUser)
                db.save()

            except:
                website = Websites.objects.get(domain=domainName)
                externalApp = website.externalApp

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    data_ret = {'status': 0, 'installStatus': 0,
                                'error_message': "0,Maximum database limit reached for this website."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if home == '0':
                    path = data['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"

                db = Databases(website=website, dbName=dbName, dbUser=dbUser)
                db.save()

            if finalPath.find("..") > -1:
                data_ret = {'status': 0, 'installStatus': 0,
                            'error_message': "Specified path must be inside virtual host home!"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ## Installation
            salt = randomPassword.generate_pass(32)
            # return salt
            password_hash = hashlib.md5(password + salt).hexdigest()
            password = password_hash + ":" + salt

            statusFile = open(tempStatusPath, 'w')
            statusFile.writelines('Downloading Joomla Core..,20')
            statusFile.close()

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " installJoomla --virtualHostName " + domainName + \
                       " --virtualHostUser " + externalApp + " --path " + finalPath + " --dbName " + dbName + \
                       " --dbUser " + dbUser + " --dbPassword " + dbPassword + " --username " + username + \
                       " --password " + password + " --prefix " + prefix + " --sitename '" + sitename + "'" \
                       + " --tempStatusPath " + tempStatusPath

            # return execPath


            output = subprocess.Popen(shlex.split(execPath))

            data_ret = {'status': 1, "installStatus": 1, 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


            ## Installation ends

        except BaseException, msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def setupGit(self, request = None, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            path = '/home/cyberpanel/' + self.domain + '.git'

            if os.path.exists(path):
                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddress = ipData.split('\n', 1)[0]

                webhookURL = 'https://' + ipAddress + ':8090/websites/' + self.domain + '/gitNotify'

                return render(request, 'websiteFunctions/setupGit.html',
                              {'domainName': self.domain, 'installed': 1, 'webhookURL': webhookURL})
            else:

                command = "sudo ssh-keygen -f /root/.ssh/git -t rsa -N ''"
                ProcessUtilities.executioner(command)

                ###

                configContent = """Host github.com
    IdentityFile /root/.ssh/git
Host gitlab.com
    IdentityFile /root/.ssh/git
"""

                path = "/home/cyberpanel/config"
                writeToFile = open(path, 'w')
                writeToFile.writelines(configContent)
                writeToFile.close()

                command = 'sudo mv ' + path + ' /root/.ssh/config'
                ProcessUtilities.executioner(command)

                command = 'sudo chown root:root /root/.ssh/config'
                ProcessUtilities.executioner(command)

                command = 'sudo cat /root/.ssh/git.pub'
                deploymentKey = subprocess.check_output(shlex.split(command)).strip('\n')

            return render(request, 'websiteFunctions/setupGit.html',
                          {'domainName': self.domain, 'deploymentKey': deploymentKey, 'installed': 0})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def setupGitRepo(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['username'] = data['username']
            extraArgs['reponame'] = data['reponame']
            extraArgs['branch'] = data['branch']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))
            extraArgs['defaultProvider'] = data['defaultProvider']

            background = ApplicationInstaller('git', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException, msg:
            data_ret = {'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def gitNotify(self, userID = None, data = None):
        try:

            extraArgs = {}
            extraArgs['domain'] = self.domain

            background = ApplicationInstaller('pull', extraArgs)
            background.start()

            data_ret = {'pulled': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            data_ret = {'pulled': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def detachRepo(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['domainName'] = data['domain']
            extraArgs['admin'] = admin

            background = ApplicationInstaller('detach', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException, msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def changeBranch(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['domainName'] = data['domain']
            extraArgs['githubBranch'] = data['githubBranch']
            extraArgs['admin'] = admin

            background = ApplicationInstaller('changeBranch', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException, msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def installPrestaShop(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'websiteFunctions/installPrestaShop.html', {'domainName': self.domain})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def prestaShopInstall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            self.domain = data['domain']

            if ACLManager.checkOwnership(self.domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            mailUtilities.checkHome()

            extraArgs = {}
            extraArgs['admin'] = admin
            extraArgs['domainName'] = data['domain']
            extraArgs['home'] = data['home']
            extraArgs['shopName'] = data['shopName']
            extraArgs['firstName'] = data['firstName']
            extraArgs['lastName'] = data['lastName']
            extraArgs['databasePrefix'] = data['databasePrefix']
            extraArgs['email'] = data['email']
            extraArgs['password'] = data['password']
            extraArgs['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            if data['home'] == '0':
                extraArgs['path'] = data['path']

            background = ApplicationInstaller('prestashop', extraArgs)
            background.start()

            time.sleep(2)

            data_ret = {'status': 1, 'installStatus': 1, 'error_message': 'None',
                        'tempStatusPath': extraArgs['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

            ## Installation ends

        except BaseException, msg:
            data_ret = {'status': 0, 'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def createWebsiteAPI(self, data = None):
        try:

            adminUser = data['adminUser']
            adminPass = data['adminPass']
            adminEmail = data['ownerEmail']
            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']
            data['ssl'] = 0
            data['dkimCheck'] = 0
            data['openBasedir'] = 1
            data['adminEmail'] = data['ownerEmail']
            data['phpSelection'] = "PHP 7.0"
            data['package'] = data['packageName']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):

                if adminEmail is None:
                    data['adminEmail'] = "usman@cyberpersons.com"

                try:
                    acl = ACL.objects.get(name='user')
                    websiteOwn = Administrator(userName=websiteOwner,
                                               password=hashPassword.hash_password(ownerPassword),
                                               email=adminEmail, type=3, owner=admin.pk,
                                               initWebsitesLimit=1, acl=acl)
                    websiteOwn.save()
                except BaseException:
                    pass

            else:
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            return self.submitWebsiteCreation(admin.pk, data)

        except BaseException, msg:
            data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg), "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def searchWebsitesJson(self, currentlACL, userID, searchTerm):

        websites = ACLManager.searchWebsiteObjects(currentlACL, userID, searchTerm)

        json_data = "["
        checker = 0

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        for items in websites:
            if items.state == 0:
                state = "Suspended"
            else:
                state = "Active"
            dic = {'domain': items.domain, 'adminEmail': items.adminEmail, 'ipAddress': ipAddress,
                   'admin': items.admin.userName, 'package': items.package.packageName, 'state': state}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def findWebsitesJson(self, currentACL, userID, pageNumber):
        finalPageNumber = ((pageNumber * 10)) - 10
        endPageNumber = finalPageNumber + 10
        websites = ACLManager.findWebsiteObjects(currentACL, userID)[finalPageNumber:endPageNumber]

        json_data = "["
        checker = 0

        try:
            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to read machine IP, error:" + str(msg))
            ipAddress = "192.168.100.1"

        for items in websites:
            if items.state == 0:
                state = "Suspended"
            else:
                state = "Active"
            dic = {'domain': items.domain, 'adminEmail': items.adminEmail, 'ipAddress': ipAddress,
                   'admin': items.admin.userName, 'package': items.package.packageName, 'state': state}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    def websitePagination(self, currentACL, userID):
        websites = ACLManager.findAllSites(currentACL, userID)

        pages = float(len(websites)) / float(10)
        pagination = []

        if pages <= 1.0:
            pages = 1
            pagination.append('<li><a href="\#"></a></li>')
        else:
            pages = ceil(pages)
            finalPages = int(pages) + 1

            for i in range(1, finalPages):
                pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

        return pagination