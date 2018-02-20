# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import json
from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical import hashPassword
from plogical.installUtilities import installUtilities
from packages.models import Package
import shutil
from plogical.mysqlUtilities import mysqlUtilities
from databases.models import Databases
from baseTemplate.views import renderBase
from random import randint
from websiteFunctions.models import Websites,ChildDomains
import os
import signal
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from shutil import rmtree
from baseTemplate.models import version
import subprocess
import shlex
import re
from dns.models import Domains,Records
# Create your views here.


def verifyConn(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            adminUser = data['adminUser']
            adminPass = data['adminPass']


            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                data_ret = {"verifyConn": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"verifyConn": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'verifyConn': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def createWebsite(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']
            domain = data['domainName']
            adminEmail = data['ownerEmail']
            packageName = data['packageName']
            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']
            externalApp = "".join(re.findall("[a-zA-Z]+", domain))[:7]


            try:
                website = Websites.objects.get(domain=domain)
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                            'error_message': "Website Already Exists"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                pass

            try:
                website = ChildDomains.objects.get(domain=domain)
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                            'error_message': "Website Already Exists"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                pass

            phpSelection = "PHP 7.0"

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if adminEmail is None:
                adminEmail = "usman@cyberpersons.com"

            try:
                websiteOwn = Administrator(userName=websiteOwner, password=hashPassword.hash_password(ownerPassword),
                                           email=adminEmail, type=3, owner=admin.pk,
                                           initWebsitesLimit=1)
                websiteOwn.save()
            except BaseException,msg:
                pass

            ## Create Configurations

            numberOfWebsites = str(Websites.objects.count() + ChildDomains.objects.count())
            sslpath = "/home/" + domain + "/public_html"

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " createVirtualHost --virtualHostName " + domain + " --administratorEmail " + adminEmail + " --phpVersion '" + phpSelection + "' --virtualHostUser " + externalApp + " --numberOfSites " + numberOfWebsites + " --ssl " + str(
                '0') + " --sslPath " + sslpath

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                pass
            else:
                data_ret = {'createWebSiteStatus': 0, 'error_message': output, "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ## Create Configurations ends here


            selectedPackage = Package.objects.get(packageName=packageName)

            websiteOwn = Administrator.objects.get(userName=websiteOwner)

            website = Websites(admin=websiteOwn, package=selectedPackage, domain=domain, adminEmail=adminEmail,
                               phpSelection=phpSelection, ssl=0,externalApp=externalApp)

            website.save()

            data_ret = {'createWebSiteStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg), "existsStatus": 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def changeUserPassAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)


            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"changeStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


            websiteOwn = Administrator.objects.get(userName=websiteOwner)
            websiteOwn.password = hashPassword.hash_password(ownerPassword)
            websiteOwn.save()



            data_ret = {'changeStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'changeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def changePackageAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            websiteName = data['websiteName']
            packageName = data['packageName']
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"changePackage": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


            website = Websites.objects.get(domain=websiteName)
            pack = Package.objects.get(packageName=packageName)

            website.package = pack
            website.save()



            data_ret = {'changePackage': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'changePackage': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def deleteWebsite(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            websiteName = data['domainName']
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"websiteDeleteStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            numberOfWebsites = str(Websites.objects.count() + ChildDomains.objects.count())

            ## Deleting master domain

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

            execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + websiteName + " --numberOfSites " + numberOfWebsites

            subprocess.check_output(shlex.split(execPath))

            delWebsite = Websites.objects.get(domain=websiteName)
            databases = Databases.objects.filter(website=delWebsite)

            childDomains = delWebsite.childdomains_set.all()

            ## Deleting child domains

            for items in childDomains:
                numberOfWebsites = str(Websites.objects.count() + ChildDomains.objects.count())
                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " deleteVirtualHostConfigurations --virtualHostName " + items.domain + " --numberOfSites " + numberOfWebsites

                subprocess.check_output(shlex.split(execPath))

            for items in databases:
                mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

            delWebsite.delete()

            try:
                delZone = Domains.objects.get(name=websiteName)
                delZone.delete()
            except:
                pass

            installUtilities.reStartLiteSpeed()

            data_ret = {'websiteDeleteStatus': 1, 'error_message': "None"}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def submitWebsiteStatus(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            websiteName = data['websiteName']
            state = data['state']
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"websiteStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            website = Websites.objects.get(domain=websiteName)

            if state == "Suspend":
                virtualHostUtilities.suspendVirtualHost(websiteName)
                installUtilities.reStartLiteSpeed()
                website.state = 0
            else:
                virtualHostUtilities.UnsuspendVirtualHost(websiteName)
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

def loginAPI(request):
    try:
        if request.method == "POST":

            username = request.POST['username']
            password = request.POST['password']

            admin = Administrator.objects.get(userName=username)

            if hashPassword.check_password(admin.password, password):
                request.session['userID'] = admin.pk
                return redirect(renderBase)
            else:
                return HttpResponse("Invalid Credentials.")


    except BaseException, msg:
        data = {'userID': 0, 'loginStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


def fetchSSHkey(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if hashPassword.check_password(admin.password, password):

                keyPath = os.path.join("/root",".ssh")
                pubKey = keyPath + "/cyberpanel.pub"

                execPath = "sudo cat " + pubKey

                data = subprocess.check_output(shlex.split(execPath))

                data_ret = {'pubKeyStatus': 1, 'error_message': "None", "pubKey":data}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'pubKeyStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except BaseException, msg:
        data = {'pubKeyStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

def remoteTransfer(request):
    try:
        if request.method == "POST":

            data = json.loads(request.body)
            username = data['username']
            password = data['password']
            ipAddress = data['ipAddress']
            accountsToTransfer = data['accountsToTransfer']

            admin = Administrator.objects.get(userName=username)

            if hashPassword.check_password(admin.password, password):
                dir = str(randint(1000, 9999))

                ##

                accountsToTransfer = ','.join(accountsToTransfer)

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"

                execPath = execPath + " remoteTransfer --ipAddress " + ipAddress + " --dir " + dir + " --accountsToTransfer " + accountsToTransfer

                subprocess.Popen(shlex.split(execPath))

                return HttpResponse(json.dumps({"transferStatus": 1, "dir": dir}))

                ##
            else:
                data_ret = {'transferStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)




    except BaseException, msg:
        data = {'transferStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

def fetchAccountsFromRemoteServer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)
            if hashPassword.check_password(admin.password, password):

                records = Websites.objects.all()

                json_data = "["
                checker = 0

                for items in records:
                    dic = {
                           'website': items.domain,
                           'php': items.phpSelection,
                           'package': items.package.packageName,
                           'email': items.adminEmail,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})

                return HttpResponse(final_json)
            else:
                data_ret = {'fetchStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException, msg:
        data = {'fetchStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


def FetchRemoteTransferStatus(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']
            dir = "/home/backup/transfer-"+str(data['dir'])+"/backup_log"

            try:
                command = "sudo cat "+ dir
                status = subprocess.check_output(shlex.split(command))

                admin = Administrator.objects.get(userName=username)
                if hashPassword.check_password(admin.password, password):

                    final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "status": status})
                    return HttpResponse(final_json)
                else:
                    data_ret = {'fetchStatus': 0, 'error_message': "Invalid Credentials"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            except:
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "status": "Just started.."})
                return HttpResponse(final_json)



    except BaseException, msg:
        data = {'fetchStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

def cancelRemoteTransfer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']
            dir = "/home/backup/transfer-"+str(data['dir'])

            admin = Administrator.objects.get(userName=username)

            if hashPassword.check_password(admin.password, password):

                if os.path.exists(dir):

                    path = dir+"/pid"

                    pid = open(path, "r").readlines()[0]

                    try:
                        os.kill(int(pid), signal.SIGKILL)
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [cancelRemoteTransfer]")

                    rmtree(dir)

                    data = {'cancelStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)

                else:
                    data = {'cancelStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data)
                    return HttpResponse(json_data)
            else:
                data_ret = {'cancelStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except BaseException, msg:
        data = {'cancelStatus': 1, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)


def cyberPanelVersion(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['username']
            adminPass = data['password']


            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):

                Version = version.objects.get(pk=1)

                data_ret = {"getVersion": 1,
                            'error_message': "Could not authorize access to API",
                            'currentVersion':Version.currentVersion,
                            'build':Version.build}

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"getVersion": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {"getVersion": 0,
                    'error_message': "Could not authorize access to API"}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def putSSHkey(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['username']
            adminPass = data['password']
            pubKey = data['putSSHKey']


            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                keyPath = "/home/cyberpanel/.ssh"

                if not os.path.exists(keyPath):
                    os.makedirs(keyPath)


                ## writeKey

                authorized_keys = keyPath+"/authorized_keys"
                presenseCheck = 0
                try:
                    data = open(authorized_keys, "r").readlines()
                    for items in data:
                        if items.find(pubKey) > -1:
                            presenseCheck = 1
                except:
                    pass

                if presenseCheck == 0:
                    writeToFile = open(authorized_keys, 'a')
                    writeToFile.writelines("#Added by CyberPanel\n")
                    writeToFile.writelines("\n")
                    writeToFile.writelines(pubKey)
                    writeToFile.writelines("\n")
                    writeToFile.close()

                ##

                command = "sudo chmod g-w /home/cyberpanel"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                os.chmod(keyPath,0700)
                os.chmod(authorized_keys, 0600)


                data_ret = {"putSSHKey": 1,
                            'error_message': "None",}

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"putSSHKey": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {"putSSHKey": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def changeAdminPassword(request):
    try:

        data = json.loads(request.body)

        adminPass = data['password']
        randomFile = data['randomFile']

        if os.path.exists(randomFile):
            os.remove(randomFile)
            admin = Administrator.objects.get(userName="admin")
            admin.password = hashPassword.hash_password(adminPass)
            admin.save()
            data_ret = {"changed": 1,
                        'error_message': "None"}

            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        else:
            data_ret = {"changed": 0,
                        'error_message': "Failed to authorize access to change password!"}

            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)



    except BaseException, msg:
        data_ret = {"changed": 0,
                    'error_message': "Failed to authorize access to change password!"}

        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


