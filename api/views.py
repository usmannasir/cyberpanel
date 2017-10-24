# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from websiteFunctions.models import Websites
import json
from django.shortcuts import render,redirect
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
import plogical.remoteBackup as rBackup
from websiteFunctions.models import Websites
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


            try:
                website = Websites.objects.get(domain=domain)
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


            if virtualHostUtilities.checkIfVirtualHostExists(domain) == 1:
                data_ret = {"existsStatus": 1, 'createWebSiteStatus': 0,
                            'error_message': "This domain already exists in Litespeed Configurations, first delete the domain to perform sweap."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if virtualHostUtilities.createDirectoryForVirtualHost(domain, adminEmail, phpSelection) != 1:
                numberOfWebsites = Websites.objects.count()
                virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                data_ret = {"existsStatus": 1, 'createWebSiteStatus': 0,
                            'error_message': "Can not create configurations, see CyberCP main log file."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if virtualHostUtilities.createConfigInMainVirtualHostFile(domain) != 1:
                numberOfWebsites = Websites.objects.count()
                virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                data_ret = {"existsStatus": 1, 'createWebSiteStatus': 0,
                            'error_message': "Can not create configurations, see CyberCP main log file."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            installUtilities.reStartLiteSpeed()

            selectedPackage = Package.objects.get(packageName=packageName)

            websiteOwn = Administrator.objects.get(userName=websiteOwner)

            website = Websites(admin=websiteOwn, package=selectedPackage, domain=domain, adminEmail=adminEmail,
                               phpSelection=phpSelection, ssl=0)

            website.save()

            shutil.copy("/usr/local/CyberCP/index.html", "/home/" + domain + "/public_html/index.html")

            data_ret = {'createWebSiteStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        numberOfWebsites = Websites.objects.count()
        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
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

            numberOfWebsites = Websites.objects.count()

            virtualHostUtilities.deleteVirtualHostConfigurations(websiteName, numberOfWebsites)

            delWebsite = Websites.objects.get(domain=websiteName)
            databases = Databases.objects.filter(website=delWebsite)

            for items in databases:
                mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)

            delWebsite.delete()

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
                pubKey = "/root/.ssh/cyberpanel.pub"

                f = open(pubKey)
                data = f.read()
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

            admin = Administrator.objects.get(userName=username)
            if hashPassword.check_password(admin.password, password):
                dir = str(randint(1000, 9999))
                transferRequest = rBackup.remoteBackup.remoteTransfer(ipAddress, dir)

                if transferRequest[0] == 1:
                    pass
                else:
                    data_ret = {'transferStatus': 0, 'error_message': transferRequest[1]}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                return HttpResponse(json.dumps({"transferStatus": 1, "dir":dir}))


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
        data = {'transferStatus': 0,'error_message': str(msg)}
        json_data = json.dumps(data)
        return HttpResponse(json_data)
