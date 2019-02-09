# -*- coding: utf-8 -*-
from __future__ import unicode_literals
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
import subprocess
import shlex
from plogical.mailUtilities import mailUtilities
from plogical.website import WebsiteManager
from loginSystem.models import ACL
from plogical.acl import ACLManager
from firewall.models import FirewallRules
from s3Backups.s3Backups import S3Backups
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
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
    wm = WebsiteManager()
    return wm.createWebsiteAPI(json.loads(request.body))

def getUserInfo(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)

            adminUser = data['adminUser']
            adminPass = data['adminPass']
            username = data['username']

            admin = Administrator.objects.get(userName=adminUser)

            if hashPassword.check_password(admin.password, adminPass):
                pass
            else:
                data_ret = {"status": 0,
                            'error_message': "Could not authorize access to API"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            try:
                user = Administrator.objects.get(userName=username)
                data_ret = {'status': 0,
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

    except BaseException, msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
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
            data['websiteName'] = data['domainName']
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

            website = Websites.objects.get(domain=data['websiteName'])
            websiteOwner = website.admin

            if admin.websites_set.all().count() == 0:
                websiteOwner.delete()

            ## Deleting master domain

            wm = WebsiteManager()
            return wm.submitWebsiteDeletion(admin.pk, data)

    except BaseException, msg:
        data_ret = {'websiteDeleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitWebsiteStatus(request):
    try:
        if request.method == 'POST':
            data = json.loads(request.body)
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

            wm = WebsiteManager()
            return wm.submitWebsiteStatus(admin.pk, json.loads(request.body))

    except BaseException, msg:
        data_ret = {'websiteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def loginAPI(request):
    try:
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

                pubKey = os.path.join("/root",".ssh",'cyberpanel.pub')
                execPath = "sudo cat " + pubKey
                data = subprocess.check_output(shlex.split(execPath))

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

    except BaseException, msg:
        data = {'status' : 0, 'pubKeyStatus': 0,'error_message': str(msg)}
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

                mailUtilities.checkHome()
                path = "/home/cyberpanel/accounts-" + str(randint(1000, 9999))
                writeToFile = open(path,'w')

                for items in accountsToTransfer:
                    writeToFile.writelines(items + "\n")
                writeToFile.close()

                ## Accounts to transfer is a path to file, containing accounts.

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/remoteTransferUtilities.py"
                execPath = execPath + " remoteTransfer --ipAddress " + ipAddress + " --dir " + dir + " --accountsToTransfer " + path
                subprocess.Popen(shlex.split(execPath))

                return HttpResponse(json.dumps({"transferStatus": 1, "dir": dir}))

                ##
            else:
                data_ret = {'transferStatus': 0, 'error_message': "Could not authorize access to API."}
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

                path = dir + "/pid"

                command = "sudo cat " + path
                pid = subprocess.check_output(shlex.split(command))

                command = "sudo kill -KILL " + pid
                subprocess.call(shlex.split(command))

                command = "sudo rm -rf " + dir
                subprocess.call(shlex.split(command))

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

    except BaseException, msg:
        data_ret = {
                    "getVersion": 0,
                    'error_message': str(msg)
                    }
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
            numberOfAdministrator = Administrator.objects.count()
            if numberOfAdministrator == 0:
                ACLManager.createDefaultACLs()
                acl = ACL.objects.get(name='admin')
                token = hashPassword.generateToken('admin', '1234567')

                email = 'usman@cyberpersons.com'
                admin = Administrator(userName="admin", password=hashPassword.hash_password(adminPass), type=1, email=email,
                                      firstName="Cyber", lastName="Panel", acl=acl, token=token)
                admin.save()

                vers = version(currentVersion="1.8", build=1)
                vers.save()

                package = Package(admin=admin, packageName="Default", diskSpace=1000,
                                  bandwidth=1000, ftpAccounts=1000, dataBases=1000,
                                  emailAccounts=1000, allowedDomains=20)
                package.save()

                newFWRule = FirewallRules(name="panel", proto="tcp", port="8090")
                newFWRule.save()

                newFWRule = FirewallRules(name="http", proto="tcp", port="80")
                newFWRule.save()

                newFWRule = FirewallRules(name="https", proto="tcp", port="443")
                newFWRule.save()

                newFWRule = FirewallRules(name="ftp", proto="tcp", port="21")
                newFWRule.save()

                newFWRule = FirewallRules(name="smtp", proto="tcp", port="25")
                newFWRule.save()

                newFWRule = FirewallRules(name="smtps", proto="tcp", port="587")
                newFWRule.save()

                newFWRule = FirewallRules(name="ssmtp", proto="tcp", port="465")
                newFWRule.save()

                newFWRule = FirewallRules(name="pop3", proto="tcp", port="110")
                newFWRule.save()

                newFWRule = FirewallRules(name="imap", proto="tcp", port="143")
                newFWRule.save()

                newFWRule = FirewallRules(name="simap", proto="tcp", port="993")
                newFWRule.save()

                newFWRule = FirewallRules(name="dns", proto="udp", port="53")
                newFWRule.save()

                newFWRule = FirewallRules(name="dnstcp", proto="tcp", port="53")
                newFWRule.save()

                newFWRule = FirewallRules(name="ftptls", proto="tcp", port="40110-40210")
                newFWRule.save()

                data_ret = {"changed": 1,
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            os.remove(randomFile)
            token = hashPassword.generateToken('admin', adminPass)
            admin = Administrator.objects.get(userName="admin")
            admin.password = hashPassword.hash_password(adminPass)
            admin.token = token
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
                    'error_message': str(msg)}

        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def runAWSBackups(request):
    try:

        data = json.loads(request.body)
        randomFile = data['randomFile']

        if os.path.exists(randomFile):
            s3 = S3Backups(request, None, 'runAWSBackups')
            s3.start()
    except BaseException, msg:
        logging.writeToFile(str(msg) + ' [API.runAWSBackups]')