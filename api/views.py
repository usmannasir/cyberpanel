# -*- coding: utf-8 -*-

import json
from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical import hashPassword
from packages.models import Package
from baseTemplate.views import renderBase
from random import randint
from websiteFunctions.models import Websites
import os
from baseTemplate.models import version
from plogical.mailUtilities import mailUtilities
from websiteFunctions.website import WebsiteManager
from s3Backups.s3Backups import S3Backups
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities
from django.views.decorators.csrf import csrf_exempt
from userManagment.views import submitUserCreation as suc
# Create your views here.

@csrf_exempt
def verifyConn(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"verifyConn": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                data_ret = {"verifyConn": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"verifyConn": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'verifyConn': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def createWebsite(request):
    data = json.loads(request.body)
    adminUser = data['adminUser']
    admin = Administrator.objects.get(userName=adminUser)

    if admin.api == 0:
        data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                    'error_message': "API Access Disabled."}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    wm = WebsiteManager()
    return wm.createWebsiteAPI(json.loads(request.body))

@csrf_exempt
def getUserInfo(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']
            username = data['username']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                user = Administrator.objects.get(userName=username)
                data_ret = {'status': 1,
                            'firstName': user.firstName,
                            'lastName': user.lastName,
                            'email': user.email,
                            'adminStatus': user.acl.adminStatus,
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                data_ret = {'status': 0, 'error_message': "User does not exists."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def changeUserPassAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)


            websiteOwner = data['websiteOwner']
            ownerPassword = data['ownerPassword']

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"changeStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

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

    except BaseException as msg:
        data_ret = {'changeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def changePackageAPI(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            websiteName = data['websiteName']
            packageName = data['packageName']
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"changePackage": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

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

    except BaseException as msg:
        data_ret = {'changePackage': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def deleteWebsite(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"websiteDeleteStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            data['websiteName'] = data['domainName']

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"websiteDeleteStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            website = Websites.objects.get(domain=data['websiteName'])
            websiteOwner = website.admin

            try:
                if admin.websites_set.all().count() == 0:
                    websiteOwner.delete()
            except:
                pass

            ## Deleting master domain

            wm = WebsiteManager()
            return wm.submitWebsiteDeletion(admin.pk, data)

    except BaseException as msg:
        data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def submitWebsiteStatus(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"websiteStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"websiteStatus": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            wm = WebsiteManager()
            return wm.submitWebsiteStatus(admin.pk, json.loads(request.body))

    except BaseException as msg:
        data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def loginAPI(request):
    try:
        username = request.POST['username']
        password = request.POST['password']

        admin = Administrator.objects.get(userName=username)

        if admin.api == 0:
            data_ret = {"userID": 0, 'error_message': "API Access Disabled."}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        if hashPassword.check_password(admin.password, password):
            request.session['userID'] = admin.pk
            return redirect(renderBase)
        else:
            return HttpResponse("Invalid Credentials.")

    except BaseException as msg:
        data = {'userID': 0, 'loginStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

@csrf_exempt
def fetchSSHkey(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, password):

                pubKey = os.path.join("/root",".ssh",'cyberpanel.pub')
                execPath = "cat " + pubKey
                data = ProcessUtilities.outputExecutioner(execPath)

                data_ret = {
                            'status': 1,
                            'pubKeyStatus': 1,
                            'error_message': "None",
                            'pubKey':data
                            }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {
                            'status' : 0,
                            'pubKeyStatus': 0,
                            'error_message': "Could not authorize access to API."
                            }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data = {'status' : 0, 'pubKeyStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

@csrf_exempt
def remoteTransfer(request):
    try:
        if request.method == "POST":

            data = json.loads(request.body)
            username = data['username']
            password = data['password']


            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"transferStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ipAddress = data['ipAddress']
            accountsToTransfer = data['accountsToTransfer']

            if hashPassword.check_password(admin.password, password):
                dir = str(randint(1000, 9999))

                ##

                mailUtilities.checkHome()
                path = "/home/cyberpanel/accounts-" + str(randint(1000, 9999))
                writeToFile = open(path,'w')

                for items in accountsToTransfer:
                    writeToFile.writelines(items + "\n")
                writeToFile.close()

                ## Accounts to transfer is a path to file, containing accounts.

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
                execPath = execPath + " remoteTransfer --ipAddress " + ipAddress + " --dir " + dir + " --accountsToTransfer " + path
                ProcessUtilities.popenExecutioner(execPath)

                return HttpResponse(json.dumps({"transferStatus": 1, "dir": dir}))

                ##
            else:
                data_ret = {'transferStatus': 0, 'error_message': "Could not authorize access to API."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data = {'transferStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

@csrf_exempt
def fetchAccountsFromRemoteServer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"fetchStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

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

    except BaseException as msg:
        data = {'fetchStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

@csrf_exempt
def FetchRemoteTransferStatus(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"fetchStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            dir = "/home/backup/transfer-"+str(data['dir'])+"/backup_log"

            try:
                command = "cat "+ dir
                status = ProcessUtilities.outputExecutioner(command)


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



    except BaseException as msg:
        data = {'fetchStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

@csrf_exempt
def cancelRemoteTransfer(request):
    try:
        if request.method == "POST":
            data = json.loads(request.body)
            username = data['username']
            password = data['password']

            admin = Administrator.objects.get(userName=username)

            if admin.api == 0:
                data_ret = {"cancelStatus": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            dir = "/home/backup/transfer-"+str(data['dir'])



            if hashPassword.check_password(admin.password, password):

                path = dir + "/pid"

                command = "cat " + path
                pid = ProcessUtilities.outputExecutioner(command)

                command = "kill -KILL " + pid
                ProcessUtilities.executioner(command)

                command = "rm -rf " + dir
                ProcessUtilities.executioner(command)

                data = {'cancelStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data)
                return HttpResponse(json_data)

            else:
                data_ret = {'cancelStatus': 0, 'error_message': "Invalid Credentials"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except BaseException as msg:
        data = {'cancelStatus': 1, 'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)

@csrf_exempt
def cyberPanelVersion(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['username']
            adminPass = data['password']


            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"getVersion": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):

                Version = version.objects.get(pk=1)

                data_ret = {
                            "getVersion": 1,
                            'error_message': "none",
                            'currentVersion':Version.currentVersion,
                            'build':Version.build
                            }

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {
                            "getVersion": 0,
                            'error_message': "Could not authorize access to API."
                            }
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {
                    "getVersion": 0,
                    'error_message': str(msg)
                    }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

@csrf_exempt
def runAWSBackups(request):
    try:

        data = json.loads(request.body)
        randomFile = data['randomFile']

        if os.path.exists(randomFile):
            s3 = S3Backups(request, None, 'runAWSBackups')
            s3.start()
    except BaseException as msg:
        logging.writeToFile(str(msg) + ' [API.runAWSBackups]')


@csrf_exempt
def submitUserCreation(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']

            admin = Administrator.objects.get(userName=adminUser)

            if admin.api == 0:
                data_ret = {"status": 0, 'error_message': "API Access Disabled."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if hashPassword.check_password(admin.password, adminPass):
                request.session['userID'] = admin.pk
                return suc(request)
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'changeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)