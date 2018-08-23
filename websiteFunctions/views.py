# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from packages.models import Package
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
from .models import Websites,ChildDomains
import json
from math import ceil
from plogical.mysqlUtilities import mysqlUtilities
import os
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.installUtilities import installUtilities
import plogical.randomPassword as randomPassword
import subprocess
import shlex
from databases.models import Databases
import re
from random import randint
import hashlib
from plogical.mailUtilities import mailUtilities
from plogical.applicationInstaller import ApplicationInstaller
import time
from plogical.acl import ACLManager
from plogical.alias import AliasManager
# Create your views here.

def loadWebsitesHome(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        return render(request,'websiteFunctions/index.html',{"type":admin.type})
    except KeyError:
        return redirect(loadLoginPage)

def createWebsite(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['createWebsite'] == 1:
                pass
            else:
                return ACLManager.loadError()

            adminNames = ACLManager.loadAllUsers(userID)
            packagesName = ACLManager.loadPackages(userID, currentACL)

            Data = {'packageList': packagesName, "owernList":adminNames}
            return render(request, 'websiteFunctions/createWebsite.html', Data)

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def modifyWebsite(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['modifyWebsite'] == 1:
                pass
            else:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'websiteFunctions/modifyWebsite.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def deleteWebsite(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['deleteWebsite'] == 1:
                pass
            else:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'websiteFunctions/deleteWebsite.html', {'websiteList' : websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def siteState(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            elif currentACL['suspendWebsite'] == 1:
                pass
            else:
                return ACLManager.loadError()

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'websiteFunctions/suspendWebsite.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def submitWebsiteCreation(request):
    try:
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)
        if currentACL['admin'] == 1:
            pass
        elif currentACL['createWebsite'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('createWebSiteStatus', 0)

        if request.method == 'POST':

            data = json.loads(request.body)

            domain = data['domainName']
            adminEmail = data['adminEmail']
            phpSelection = data['phpSelection']
            packageName = data['package']
            websiteOwner = data['websiteOwner']
            externalApp = "".join(re.findall("[a-zA-Z]+", domain))[:7]
            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))


            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createVirtualHost --virtualHostName " + domain + \
                       " --administratorEmail " + adminEmail + " --phpVersion '" + phpSelection + \
                       "' --virtualHostUser " + externalApp + " --ssl " + str(data['ssl']) + " --dkimCheck " \
                       + str(data['dkimCheck']) + " --openBasedir " + str(data['openBasedir']) + \
                       ' --websiteOwner ' + websiteOwner + ' --package ' + packageName + ' --tempStatusPath ' + tempStatusPath

            subprocess.Popen(shlex.split(execPath))
            time.sleep(2)

            data_ret = {'createWebSiteStatus': 1, 'error_message': "None", 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


    except BaseException, msg:
        data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitDomainCreation(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            masterDomain = data['masterDomain']
            domain = data['domainName']
            phpSelection = data['phpSelection']
            path = data['path']
            tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            userID = request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            admin = Administrator.objects.get(pk=userID)

            if currentACL['admin'] != 1:
                data['openBasedir'] = 1

            if len(path) > 0:
                path = path.lstrip("/")
                path = "/home/" + masterDomain + "/public_html/" + path
            else:
                path = "/home/" + masterDomain + "/public_html/" + domain


            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createDomain --masterDomain " + masterDomain + " --virtualHostName " + domain + \
                       " --phpVersion '" + phpSelection + "' --ssl " + str(data['ssl']) + " --dkimCheck " + str(data['dkimCheck']) \
                       + " --openBasedir " + str(data['openBasedir']) + ' --path ' + path + ' --websiteOwner ' \
                       + admin.userName + ' --tempStatusPath ' + tempStatusPath

            subprocess.Popen(shlex.split(execPath))
            time.sleep(2)

            data_ret = {'createWebSiteStatus': 1, 'error_message': "None", 'tempStatusPath': tempStatusPath}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def fetchDomains(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                masterDomain = data['masterDomain']

                master = Websites.objects.get(domain=masterDomain)

                childDomains = master.childdomains_set.all()

                json_data = "["
                checker = 0

                for items in childDomains:
                    dic = {
                        'childDomain': items.domain,
                        'path': items.path,
                        'childLunch': '/websites/' + masterDomain + '/' + items.domain
                    }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def listWebsites(request):
    try:
        userID = request.session['userID']
        try:

            currentACL = ACLManager.loadedACL(userID)
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


            return render(request,'websiteFunctions/listWebsites.html',{"pagination":pagination})

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def getFurtherAccounts(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    status = data['page']
                    pageNumber = int(status)

                except BaseException, msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [getFurtherAccounts]')

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
                dic = {'domain': items.domain, 'adminEmail': items.adminEmail,'ipAddress':ipAddress,'admin': items.admin.userName,'package': items.package.packageName,'state':state}

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data +',' + json.dumps(dic)

            json_data = json_data + ']'
            final_dic = {'listWebSiteStatus': 1, 'error_message': "None", "data": json_data}
            final_json = json.dumps(final_dic)


            return HttpResponse(final_json)

        except BaseException,msg:
            dic = {'listWebSiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)


    except KeyError,msg:
        dic = {'listWebSiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(dic)
        return HttpResponse(json_data)

def submitWebsiteDeletion(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                websiteName = data['websiteName']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['deleteWebsite'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('websiteDeleteStatus', 0)


                numberOfWebsites = str(Websites.objects.count() + ChildDomains.objects.count())

                ## Deleting master domain

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + websiteName + \
                           " --numberOfSites " + numberOfWebsites

                subprocess.check_output(shlex.split(execPath))

                data_ret = {'websiteDeleteStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitDomainDeletion(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                websiteName = data['websiteName']

                childDomain = ChildDomains.objects.get(domain=websiteName)
                admin = Administrator.objects.get(pk=val)

                if childDomain.master.admin == admin:
                    execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                    execPath = execPath + " deleteDomain --virtualHostName " + websiteName

                    subprocess.check_output(shlex.split(execPath))

                    data_ret = {'websiteDeleteStatus': 1,'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'websiteDeleteStatus': 0, 'error_message': "You can not delete this child domain, as master domain is not owned by logged in user."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitWebsiteStatus(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                websiteName = data['websiteName']
                state = data['state']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['suspendWebsite'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('websiteStatus', 0)

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

        except BaseException,msg:


            data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitWebsiteModify(request):
    try:
        userID = request.session['userID']
        try:

            if request.method == 'POST':

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['modifyWebsite'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('modifyStatus', 0)

                packs = ACLManager.loadPackages(userID, currentACL)
                admins = ACLManager.loadAllUsers(userID)

                ## Get packs name

                json_data = "["
                checker = 0


                for items in packs:
                    dic = {"pack":items}

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


                data = json.loads(request.body)
                websiteToBeModified = data['websiteToBeModified']

                modifyWeb = Websites.objects.get(domain=websiteToBeModified)


                email = modifyWeb.adminEmail
                currentPack = modifyWeb.package.packageName
                owner = modifyWeb.admin.userName

                data_ret = {'modifyStatus': 1,'error_message': "None","adminEmail":email,
                            "packages":json_data,"current_pack":currentPack,"adminNames":admin_data,'currentAdmin':owner}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)
        except BaseException,msg:
            dic = {'modifyStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(dic)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'modifyStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def saveWebsiteChanges(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['domain']
                package = data['packForWeb']
                email = data['email']
                phpVersion = data['phpVersion']
                newUser = data['admin']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['modifyWebsite'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('saveStatus', 0)


                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domain
                completePathToConfigFile = confPath + "/vhost.conf"

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    pass
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
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

                data_ret = {'saveStatus': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        data_ret = {'saveStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def domain(request, domain):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if Websites.objects.filter(domain=domain).exists():
            currentACL = ACLManager.loadedACL(userID)
            website = Websites.objects.get(domain=domain)

            Data = {}

            Data['ftpTotal'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['databasesUsed'] = website.databases_set.all().count()
            Data['databasesTotal'] = website.package.dataBases

            Data['domain'] = domain

            diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + domain, website.package.diskSpace)

            ## bw usage calculation

            try:
                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " findDomainBW --virtualHostName " + domain + " --bandwidth " + str(
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

            return render(request, 'websiteFunctions/website.html', Data)

        else:
            return render(request, 'websiteFunctions/website.html', {"error":1,"domain": "This domain does not exists."})
    except KeyError:
        return redirect(loadLoginPage)

def launchChild(request, domain, childDomain):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)

        if ChildDomains.objects.filter(domain=childDomain).exists():
            currentACL = ACLManager.loadedACL(userID)
            website = Websites.objects.get(domain=domain)

            Data = {}

            Data['ftpTotal'] = website.package.ftpAccounts
            Data['ftpUsed'] = website.users_set.all().count()

            Data['databasesUsed'] = website.databases_set.all().count()
            Data['databasesTotal'] = website.package.dataBases

            Data['domain'] = domain
            Data['childDomain'] = childDomain

            diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + domain, website.package.diskSpace)

            ## bw usage calculation

            try:
                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " findDomainBW --virtualHostName " + domain + " --bandwidth " + str(
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

            return render(request, 'websiteFunctions/launchChild.html', Data)
        else:
            return render(request, 'websiteFunctions/launchChild.html', {"error":1,"domain": "This child domain does not exists"})
    except KeyError:
        return redirect(loadLoginPage)

def getDataFromLogFile(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        logType = data['logType']
        virtualHost = data['virtualHost']
        page = data['page']


        if logType == 1:
            fileName = "/home/" + virtualHost + "/logs/" + virtualHost + ".access_log"
        else:
            fileName = "/home/" + virtualHost + "/logs/" + virtualHost + ".error_log"

        ## get Logs

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " getAccessLogs --path " + fileName + " --page " + str(page)

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            final_json = json.dumps(
                {'logstatus': 0, 'error_message': "Not able to fetch logs, see CyberPanel main log file!"})
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
        final_json = json.dumps({'logstatus': 1, 'error_message': "None", "data": json_data})
        return HttpResponse(final_json)

        ##

    except KeyError,msg:
        data_ret = {'logstatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def fetchErrorLogs(request):
    try:
        userID = request.session['userID']

        data = json.loads(request.body)
        virtualHost = data['virtualHost']
        page = data['page']

        fileName = "/home/" + virtualHost + "/logs/" + virtualHost + ".error_log"

        ## get Logs

        execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

        execPath = execPath + " getErrorLogs --path " + fileName + " --page " + str(page)

        output = subprocess.check_output(shlex.split(execPath))

        if output.find("1,None") > -1:
            final_json = json.dumps(
                {'logstatus': 0, 'error_message': "Not able to fetch logs, see CyberPanel main log file!"})
            return HttpResponse(final_json)

        ## get log ends here.

        final_json = json.dumps({'logstatus': 1, 'error_message': "None", "data": output})
        return HttpResponse(final_json)

    except BaseException,msg:
        final_json = json.dumps({'logstatus': 0, 'error_message': str(msg)})
        return HttpResponse(final_json)

def getDataFromConfigFile(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                filePath = installUtilities.Server_root_path + "/conf/vhosts/" + virtualHost + "/vhost.conf"

                command = 'sudo cat ' + filePath
                configData = subprocess.check_output(shlex.split(command))

                if len(configData) == 0:
                    status = {"configstatus": 0, "error_message": "Configuration file is currently empty!"}

                    final_json = json.dumps(status)
                    return HttpResponse(final_json)

                status = {"configstatus": 1, "configData": configData}
                final_json = json.dumps(status)
                return HttpResponse(final_json)

            except BaseException, msg:
                data_ret = {'configstatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except KeyError, msg:
        status = {"configstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getDataFromConfigFile]")
        return HttpResponse("Not Logged in as admin")

def saveConfigsToFile(request):
    try:
        userID = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] != 1:
                    return ACLManager.loadErrorJson('configstatus', 0)


                ## writing data temporary to file

                mailUtilities.checkHome()

                tempPath = "/home/cyberpanel/"+str(randint(1000, 9999))

                vhost = open(tempPath, "w")

                vhost.write(data['configData'])

                vhost.close()

                ## writing data temporary to file

                filePath = installUtilities.Server_root_path + "/conf/vhosts/"+virtualHost+"/vhost.conf"

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


            except BaseException, msg:
                data_ret = {'configstatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



    except KeyError, msg:
        status = {"configstatus":0,"error":"Could not save, see CyberPanel main log file."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[saveConfigsToFile]")
        return HttpResponse("Not Logged in as admin")

def getRewriteRules(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                try:
                    childDom = ChildDomains.objects.get(domain=virtualHost)
                    filePath = childDom.path + '/.htaccess'

                except:
                    website = Websites.objects.get(domain=virtualHost)
                    filePath = "/home/" + virtualHost + "/public_html/.htaccess"

                try:
                    rewriteRules = open(filePath,"r").read()

                    if len(rewriteRules) == 0:

                        status = {"rewriteStatus": 1, "error_message": "Rules file is currently empty"}
                        final_json = json.dumps(status)
                        return HttpResponse(final_json)

                    status = {"rewriteStatus": 1, "rewriteRules": rewriteRules}

                    final_json = json.dumps(status)
                    return HttpResponse(final_json)
                except IOError:
                    status = {"rewriteStatus": 1, "error_message": "none","rewriteRules":""}
                    final_json = json.dumps(status)
                    return HttpResponse(final_json)

            except BaseException, msg:
                data_ret = {'rewriteStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getDataFromConfigFile]")
        return HttpResponse("Not Logged in as admin")

def saveRewriteRules(request):
    try:
        userID = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                ## writing data temporary to file

                mailUtilities.checkHome()
                tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
                vhost = open(tempPath, "w")
                vhost.write(data['rewriteRules'])
                vhost.close()

                ## writing data temporary to file

                admin = Administrator.objects.get(pk=userID)
                currentACL = ACLManager.loadedACL(userID)

                try:
                    childDomain = ChildDomains.objects.get(domain=virtualHost)
                    filePath = childDomain.path + '/.htaccess'
                except:
                    filePath = "/home/" + virtualHost + "/public_html/.htaccess"

                ## save configuration data

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " saveRewriteRules --virtualHostName "+ virtualHost + " --path " + filePath + " --tempPath " + tempPath

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    status = {"rewriteStatus": 1, 'error_message': output}
                    final_json = json.dumps(status)
                    return HttpResponse(final_json)
                else:
                    data_ret = {'rewriteStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                    ## save configuration data ends

            except BaseException, msg:
                data_ret = {'rewriteStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except KeyError, msg:
        status = {"rewriteStatus":0,"error":"Could not save, see main log file."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[saveConfigsToFile]")
        return HttpResponse("Not Logged in as admin")

def saveSSL(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['virtualHost']

                mailUtilities.checkHome()

                ## writing data temporary to file


                tempKeyPath = "/home/cyberpanel/" + str(randint(1000, 9999))
                vhost = open(tempKeyPath, "w")
                vhost.write(data['key'])
                vhost.close()

                tempCertPath = "/home/cyberpanel/" + str(randint(1000, 9999))
                vhost = open(tempCertPath, "w")
                vhost.write(data['cert'])
                vhost.close()

                ## writing data temporary to file

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " saveSSL --virtualHostName " + domain + " --tempKeyPath " + tempKeyPath + " --tempCertPath " + tempCertPath

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

                ## save configuration data ends


        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Can not create directory to stroe SSL [saveSSL]]")
            data_ret = {'sslStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Can not create directory to stroe SSL [saveSSL]]")
        data_ret = {'sslStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def changePHP(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                childDomain = data['childDomain']
                phpVersion = data['phpSelection']

                admin = Administrator.objects.get(pk=userID)
                currentACL = ACLManager.loadedACL(userID)

                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + childDomain
                completePathToConfigFile = confPath + "/vhost.conf"

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " changePHP --phpVersion '" + phpVersion + "' --path " + completePathToConfigFile

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    pass
                else:
                    data_ret = {'changePHP': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                data_ret = {'changePHP': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'changePHP': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        data_ret = {'changePHP': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def listCron(request):
    try:
        userID = request.session['userID']
        try:
            currentACL = ACLManager.loadedACL(userID)

            websitesName = ACLManager.findAllSites(currentACL, userID)

            return render(request, 'websiteFunctions/listCron.html', {'websiteList': websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))
    except KeyError:
        return redirect(loadLoginPage)

def getWebsiteCron(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                currentACL = ACLManager.loadedACL(userID)

                data = json.loads(request.body)
                domain = data['domain']

                admin = Administrator.objects.get(pk=request.session['userID'])
                website = Websites.objects.get(domain=domain)

                if Websites.objects.filter(domain=domain).exists():
                    pass
                else:
                    dic = {'getWebsiteCron': 0, 'error_message': 'You do not own this domain'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                cronPath = "/var/spool/cron/" + website.externalApp
                cmd = 'sudo test -e ' + cronPath + ' && echo Exists'
                output = os.popen(cmd).read()

                if "Exists" not in output:
                    data_ret = {'getWebsiteCron': 1, "user": website.externalApp, "crons": {}}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                cronPath = "/var/spool/cron/" + website.externalApp
                crons = []

                try:
                    f = subprocess.check_output(["sudo", "cat", cronPath])
                    print f
                except subprocess.CalledProcessError as error:
                    dic = {'getWebsiteCron': 0, 'error_message': 'Unable to access Cron file'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)
                counter = 0
                for line in f.split("\n"):
                    if line:
                        split = line.split(" ", 5)
                        print line
                        print split
                        if len(split) == 6:
                            counter += 1
                            crons.append({"line": counter,
                                          "minute": split[0],
                                          "hour": split[1],
                                          "monthday": split[2],
                                          "month": split[3],
                                          "weekday": split[4],
                                          "command": split[5]})

                print json.dumps(crons)

                data_ret = {'getWebsiteCron': 1, "user": website.externalApp, "crons": crons}
                final_json = json.dumps(data_ret)
                return HttpResponse(final_json)
            except BaseException, msg:
                print msg
                dic = {'getWebsiteCron': 0, 'error_message': str(msg)}
                json_data = json.dumps(dic)
                return HttpResponse(json_data)

    except KeyError, msg:
        status = {"getWebsiteCron": 0, "error": "Not Logged in as admin"}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

def getCronbyLine(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                currentACL = ACLManager.loadedACL(userID)
                data = json.loads(request.body)
                domain = data['domain']
                line = data['line']

                line -= 1
                admin = Administrator.objects.get(pk=request.session['userID'])
                website = Websites.objects.get(domain=domain)

                if Websites.objects.filter(domain=domain).exists():
                    pass
                else:
                    dic = {'getWebsiteCron': 0, 'error_message': 'You do not own this domain'}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                cronPath = "/var/spool/cron/" + website.externalApp
                crons = []

                try:
                    f = subprocess.check_output(["sudo", "cat", cronPath])
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

    except KeyError, msg:
        status = {"getWebsiteCron": 0, "error": "Not Logged in"}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

def saveCronChanges(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                currentACL = ACLManager.loadedACL(userID)
                data = json.loads(request.body)
                domain = data['domain']
                line = data['line']

                minute = data['minute']
                hour = data['hour']
                monthday = data['monthday']
                month = data['month']
                weekday = data['weekday']
                command = data['command']

                website = Websites.objects.get(domain=domain)

                cronPath = "/var/spool/cron/" + website.externalApp
                tempPath = "/home/cyberpanel/" + website.externalApp + str(randint(10000, 99999)) + ".cron.tmp"

                finalCron = "%s %s %s %s %s %s" % (minute, hour, monthday, month, weekday, command)

                o = subprocess.call(['sudo', 'cp', cronPath, tempPath])
                if o is not 0:
                    data_ret = {'addNewCron': 0, 'error_message': 'Unable to copy to temporary files'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

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
                print 'test'

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

    except KeyError, msg:
        status = {"getWebsiteCron": 0, "error": "Not Logged in"}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

def remCronbyLine(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                domain = data['domain']
                line = data['line']

                line -= 1

                website = Websites.objects.get(domain=domain)

                cronPath = "/var/spool/cron/" + website.externalApp
                cmd = 'sudo test -e ' + cronPath + ' && echo Exists'
                output = os.popen(cmd).read()

                if "Exists" not in output:
                    data_ret = {'remCronbyLine': 0, 'error_message': 'No Cron exists for this user'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                cronPath = "/var/spool/cron/" + website.externalApp
                tempPath = "/home/cyberpanel/" + website.externalApp + str(randint(10000, 99999)) + ".cron.tmp"

                o = subprocess.call(['sudo', 'cp', cronPath, tempPath])
                if o is not 0:
                    data_ret = {'addNewCron': 0, 'error_message': 'Unable to copy to temporary files'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

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

    except KeyError, msg:
        status = {"remCronbyLine": 0, "error": "Not Logged in"}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

def addNewCron(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            try:
                currentACL = ACLManager.loadedACL(userID)
                data = json.loads(request.body)
                domain = data['domain']

                minute = data['minute']
                hour = data['hour']
                monthday = data['monthday']
                month = data['month']
                weekday = data['weekday']
                command = data['command']

                website = Websites.objects.get(domain=domain)

                cronPath = "/var/spool/cron/" + website.externalApp
                cmd = 'sudo test -e ' + cronPath + ' && echo Exists'
                output = os.popen(cmd).read()

                if "Exists" not in output:
                    echo = subprocess.Popen(('echo'), stdout=subprocess.PIPE)
                    output = subprocess.call(('sudo', 'crontab', '-u', website.externalApp, '-'), stdin=echo.stdout)
                    echo.wait()
                    echo.stdout.close()
                    # Confirmation
                    o = subprocess.call(["sudo", "cp", "/dev/null", cronPath])

                cronPath = "/var/spool/cron/" + website.externalApp
                tempPath = "/home/cyberpanel/" + website.externalApp + str(randint(10000, 99999)) + ".cron.tmp"

                finalCron = "%s %s %s %s %s %s" % (minute, hour, monthday, month, weekday, command)

                o = subprocess.call(['sudo', 'cp', cronPath, tempPath])
                if o is not 0:
                    data_ret = {'addNewCron': 0, 'error_message': 'Unable to copy to temporary files'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                # Confirming that directory is read/writable
                o = subprocess.call(['sudo', 'chown', 'cyberpanel:cyberpanel', tempPath])
                if o is not 0:
                    data_ret = {'addNewCron': 0, 'error_message': 'Error Changing Permissions'}
                    final_json = json.dumps(data_ret)
                    return HttpResponse(final_json)

                with open(tempPath, "a") as file:
                    file.write(finalCron + "\n")

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

    except KeyError, msg:
        status = {"addNewCron": 0, "error": "Not Logged in"}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

def domainAlias(request, domain):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)
        try:

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()


            aliasManager = AliasManager(domain)
            noAlias, finalAlisList = aliasManager.fetchAlisForDomains()

            path = "/home/" + domain + "/public_html"

            return render(request, 'websiteFunctions/domainAlias.html', {
                                                                           'masterDomain': domain,
                                                                           'aliases':finalAlisList,
                                                                           'path':path,
                                                                           'noAlias':noAlias
                                                                        })
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))
    except KeyError:
        return redirect(loadLoginPage)

def submitAliasCreation(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if request.method == 'POST':

            if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
                pass
            else:
                return ACLManager.loadError()


            data = json.loads(request.body)

            masterDomain = data['masterDomain']
            aliasDomain = data['aliasDomain']
            ssl = data['ssl']

            sslpath = "/home/" + masterDomain + "/public_html"

            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createAlias --masterDomain " + masterDomain + " --aliasDomain " + aliasDomain + " --ssl " + str(
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

def issueAliasSSL(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            currentACL = ACLManager.loadedACL(userID)
            data = json.loads(request.body)

            masterDomain = data['masterDomain']
            aliasDomain = data['aliasDomain']

            admin = Administrator.objects.get(pk=userID)

            sslpath = "/home/" + masterDomain + "/public_html"

            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " issueAliasSSL --masterDomain " + masterDomain + " --aliasDomain " + aliasDomain + " --sslPath " + sslpath + " --administratorEmail " + admin.email

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'sslStatus': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ## Create Configurations ends here



            data_ret = {'sslStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)



    except BaseException, msg:
        data_ret = {'sslStatus': 0, 'error_message': str(msg), "existsStatus": 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def delateAlias(request):
    try:
        userID = request.session['userID']
        if request.method == 'POST':
            data = json.loads(request.body)

            masterDomain = data['masterDomain']
            aliasDomain = data['aliasDomain']

            ## Create Configurations

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " deleteAlias --masterDomain " + masterDomain + " --aliasDomain " + aliasDomain

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'deleteAlias': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ## Create Configurations ends here

            data_ret = {'deleteAlias': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)



    except BaseException, msg:
        data_ret = {'deleteAlias': 0, 'error_message': str(msg), "existsStatus": 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def changeOpenBasedir(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domainName = data['domainName']
                openBasedirValue = data['openBasedirValue']

                currentACL = ACLManager.loadedACL(userID)
                if currentACL['admin'] != 1:
                    return ACLManager.loadErrorJson('changeOpenBasedir', 0)


                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " changeOpenBasedir --virtualHostName '" + domainName + "' --openBasedirValue " + openBasedirValue


                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    pass
                else:
                    data_ret = {'changeOpenBasedir': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)



                data_ret = {'changeOpenBasedir': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'changeOpenBasedir': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        data_ret = {'changeOpenBasedir': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def applicationInstaller(request):
    try:
        userID = request.session['userID']
        try:
            return render(request, 'websiteFunctions/applicationInstaller.html')
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))
    except KeyError:
        return redirect(loadLoginPage)

def wordpressInstall(request, domain):
    try:
        userID = request.session['userID']
        return render(request, 'websiteFunctions/installWordPress.html', {'domainName' : domain})
    except KeyError:
        return redirect(loadLoginPage)

def installWordpress(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if request.method == 'POST':
            try:
                data = json.loads(request.body)

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

                data_ret = {'installStatus': 1, 'error_message': 'None', 'tempStatusPath': extraArgs['tempStatusPath']}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


            except BaseException, msg:
                data_ret = {'installStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except KeyError, msg:
        status = {"installStatus":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installWordpress]")
        return HttpResponse("Not Logged in as admin")

def installWordpressStatus(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                statusFile = data['statusFile']

                statusData = open(statusFile, 'r').readlines()

                lastLine = statusData[-1]

                if lastLine.find('[200]') > -1:
                    data_ret = { 'abort':1, 'installStatus': 1, 'installationProgress': "100", 'currentStatus': 'Successfully Installed.' }
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                elif lastLine.find('[404]') > -1:
                    data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0", 'error_message': lastLine}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    progress = lastLine.split(',')
                    currentStatus = progress[0]
                    installationProgress = progress[1]
                    data_ret = {'abort': 0, 'installStatus': 0, 'installationProgress': installationProgress, 'currentStatus': currentStatus}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            except BaseException, msg:
                data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0", 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except KeyError, msg:
        data_ret = {'abort': 1, 'installStatus': 0, 'installationProgress': "0", 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def joomlaInstall(request, domain):
    try:
        userID = request.session['userID']
        return render(request, 'websiteFunctions/installJoomla.html', {'domainName' : domain})
    except KeyError:
        return redirect(loadLoginPage)

def installJoomla(request):
    try:
        val = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
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

                admin = Administrator.objects.get(pk=val)

                ## DB Creation

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Creating database..,10')
                statusFile.close()

                dbName = randomPassword.generate_pass()
                dbUser = dbName
                dbPassword = randomPassword.generate_pass()

                if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(
                        dbUser=dbUser).exists():
                    data_ret = {'installStatus': 0,
                                'error_message': "0,This database or user is already taken."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                result = mysqlUtilities.createDatabase(dbName, dbUser, dbPassword)

                if result == 1:
                    pass
                else:
                    data_ret = {'installStatus': 0,
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
                        data_ret = {'installStatus': 0,
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
                        data_ret = {'installStatus': 0,
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
                    data_ret = {'installStatus': 0,
                                'error_message': "Specified path must be inside virtual host home!"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                ## Installation
                salt = randomPassword.generate_pass(32)
                #return salt
                password_hash = hashlib.md5(password + salt).hexdigest()
                password = password_hash + ":" + salt

                statusFile = open(tempStatusPath, 'w')
                statusFile.writelines('Downloading Joomla Core..,20')
                statusFile.close()


                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " installJoomla --virtualHostName " + domainName + \
                           " --virtualHostUser " + externalApp + " --path " + finalPath + " --dbName " + dbName + \
                           " --dbUser " + dbUser + " --dbPassword " + dbPassword + " --username " + username + \
                           " --password " + password +" --prefix " + prefix + " --sitename '" + sitename + "'" \
                           + " --tempStatusPath " + tempStatusPath

                #return execPath


                output = subprocess.Popen(shlex.split(execPath))

                data_ret = {"installStatus": 1, 'tempStatusPath': tempStatusPath}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



                ## Installation ends

            except BaseException, msg:
                data_ret = {'installStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except KeyError, msg:
        status = {"installStatus":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installJoomla]")
        return HttpResponse("Not Logged in as admin")

def setupGit(request, domain):
    try:
        userID = request.session['userID']
        try:
            path = '/home/cyberpanel/' + domain + '.git'

            if os.path.exists(path):

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                ipAddress = ipData.split('\n', 1)[0]

                webhookURL = 'https://' + ipAddress + ':8090/websites/' + domain + '/gitNotify'

                return render(request, 'websiteFunctions/setupGit.html',
                              {'domainName': domain, 'installed': 1, 'webhookURL': webhookURL})
            else:
                command = 'sudo cat /root/.ssh/cyberpanel.pub'
                deploymentKey = subprocess.check_output(shlex.split(command)).strip('\n')

            return render(request, 'websiteFunctions/setupGit.html', {'domainName' : domain, 'deploymentKey': deploymentKey, 'installed': 0})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))
    except KeyError:
        return redirect(loadLoginPage)

def setupGitRepo(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if request.method == 'POST':
            try:
                data = json.loads(request.body)

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

                data_ret = {'installStatus': 1, 'error_message': 'None', 'tempStatusPath': extraArgs['tempStatusPath']}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


            except BaseException, msg:
                data_ret = {'installStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except KeyError, msg:
        status = {"installStatus":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installWordpress]")
        return HttpResponse("Not Logged in as admin")

def gitNotify(request, domain):
    try:
        if request.method == 'POST':
            try:

                extraArgs = {}
                extraArgs['domain'] = domain

                background = ApplicationInstaller('pull', extraArgs)
                background.start()

                data_ret = {'pulled': 1, 'error_message': 'None'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            except BaseException, msg:
                data_ret = {'pulled': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except KeyError, msg:
        data_ret = {"pulled":0,"error":str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def detachRepo(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if request.method == 'POST':
            try:
                data = json.loads(request.body)

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


    except KeyError, msg:
        status = {"status":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installWordpress]")
        return HttpResponse("Not Logged in as admin")

def changeBranch(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if request.method == 'POST':
            try:
                data = json.loads(request.body)

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


    except KeyError, msg:
        status = {"status":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installWordpress]")
        return HttpResponse("Not Logged in as admin")

def installPrestaShop(request, domain):
    try:
        userID = request.session['userID']

        return render(request, 'websiteFunctions/installPrestaShop.html', {'domainName' : domain})

    except KeyError:
        return redirect(loadLoginPage)

def prestaShopInstall(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(id=val)
        if request.method == 'POST':
            try:
                data = json.loads(request.body)

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

                data_ret = {'installStatus': 1, 'error_message': 'None', 'tempStatusPath': extraArgs['tempStatusPath']}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

                ## Installation ends

            except BaseException, msg:
                data_ret = {'installStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except KeyError, msg:
        status = {"installStatus":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installJoomla]")
        return HttpResponse("Not Logged in as admin")
