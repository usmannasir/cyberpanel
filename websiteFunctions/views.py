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
import shutil
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.installUtilities import installUtilities
from plogical.sslUtilities import sslUtilities
import plogical.randomPassword as randomPassword
import subprocess
import shlex
from databases.models import Databases
from os.path import join
from os import listdir, rmdir
from shutil import move
from filemanager_app import views as fileManage
from plogical.findBWUsage import findBWUsage
from dns.models import Domains,Records
import requests
# Create your views here.


def loadWebsitesHome(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        viewStatus = 1

        if admin.type == 3:
            viewStatus = 0

        return render(request,'websiteFunctions/index.html',{"viewStatus":viewStatus})
    except KeyError:
        return redirect(loadLoginPage)


def createWebsite(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])
            packages = admin.package_set.all()
            packagesName = []

            for items in packages:
                packagesName.append(items.packageName)

            if admin.type == 1:
                admins = Administrator.objects.all()
                adminNames = []
                for items in admins:
                    adminNames.append(items.userName)
            else:
                admins = Administrator.objects.filter(owner=admin.pk)
                adminNames = []
                adminNames.append(admin.userName)
                for items in admins:
                    adminNames.append(items.userName)

            Data = {'packageList': packagesName,"owernList":adminNames}



            return render(request, 'websiteFunctions/createWebsite.html', Data)
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def modifyWebsite(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = admin.websites_set.all()
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = items.websites_set.all()

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)

            return render(request, 'websiteFunctions/modifyWebsite.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def deleteWebsite(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = admin.websites_set.all()
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = items.websites_set.all()

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)

            return render(request, 'websiteFunctions/deleteWebsite.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def siteState(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = admin.websites_set.all()
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = items.websites_set.all()

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)

            return render(request, 'websiteFunctions/suspendWebsite.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)



def submitWebsiteCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['domainName']
                adminEmail = data['adminEmail']
                phpSelection = data['phpSelection']
                packageName = data['package']
                websiteOwner = data['websiteOwner']

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


                ####### Limitations check

                admin = Administrator.objects.get(userName=websiteOwner)

                if admin.type == 1:
                    pass
                elif admin.type == 3:
                    if admin.initWebsitesLimit == 0:
                        pass
                    elif admin.websites_set.all().count() == admin.initWebsitesLimit:
                        data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                                    'error_message': "Selected owner have reached maximum websites limit"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        pass

                else:

                    initialLimit = admin.initWebsitesLimit
                    try:
                        subaccounts = Administrator.objects.filter(owner=admin.pk)
                        for items in subaccounts:
                            initialLimit = initialLimit - items.initWebsitesLimit
                    except:
                        pass

                    if admin.initWebsitesLimit == 0:
                        pass
                    elif admin.websites_set.all().count() == initialLimit:
                        data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                                    'error_message': "Selected owner have reached maximum websites limit"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        pass

                ####### Limitations Check End

                ssl = data['ssl']

                if virtualHostUtilities.checkIfVirtualHostExists(domain) == 1:
                    data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                'error_message': "This domain already exists in Litespeed Configurations, first delete the domain to perform sweap."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if virtualHostUtilities.createDirectoryForVirtualHost(domain, adminEmail, phpSelection) != 1:
                    numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
                    virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                    data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                'error_message': "Can not create configurations, see CyberCP main log file."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if virtualHostUtilities.createConfigInMainVirtualHostFile(domain) != 1:
                    numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
                    virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                    data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                'error_message': "Can not create configurations, see CyberCP main log file."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


                if ssl == 1:
                    installUtilities.reStartOpenLiteSpeed("restart","ols")
                else:
                    installUtilities.reStartLiteSpeed()

                if ssl == 1:
                    sslpath = "/home/" + domain + "/public_html"
                    ssl_responce = sslUtilities.obtainSSLForADomain(domain, adminEmail,sslpath)
                    if ssl_responce == 1:
                        sslUtilities.installSSLForDomain(domain)
                        installUtilities.reStartLiteSpeed()
                    else:
                        numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
                        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)

                        data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                    'error_message': str(
                                        ssl_responce) + ", for more information see CyberCP main log file."}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)


                ## zone creation and
                try:

                    newZone = Domains(admin=admin, name=domain, type="NATIVE")
                    newZone.save()

                    content = "ns1." + domain + " hostmaster." + domain + " 1 10800 3600 604800 3600"

                    soaRecord = Records(domainOwner=newZone,
                                        domain_id=newZone.id,
                                        name=domain,
                                        type="SOA",
                                        content=content,
                                        ttl=3600,
                                        prio=0,
                                        disabled=0,
                                        auth=1)
                    soaRecord.save()

                    try:
                        recordContentA = requests.get('https://api.ipify.org').text
                        zone = Domains.objects.get(name=domain)
                        record = Records(domainOwner=zone,
                                         domain_id=zone.id,
                                         name=domain,
                                         type="A",
                                         content=recordContentA,
                                         ttl=3600,
                                         prio=0,
                                         disabled=0,
                                         auth=1)
                        record.save()
                    except:
                        pass

                except:
                    try:
                        recordContentA = requests.get('https://api.ipify.org').text
                        zone = Domains.objects.get(name=domain)
                        record = Records(domainOwner=zone,
                                         domain_id=zone.id,
                                         name=domain,
                                         type="A",
                                         content=recordContentA,
                                         ttl=3600,
                                         prio=0,
                                         disabled=0,
                                         auth=1)
                        record.save()
                    except:
                        pass

                ## zone creation



                selectedPackage = Package.objects.get(packageName=packageName)

                website = Websites(admin=admin, package=selectedPackage, domain=domain, adminEmail=adminEmail,
                                   phpSelection=phpSelection, ssl=ssl)

                website.save()

                shutil.copy("/usr/local/CyberCP/index.html", "/home/" + domain + "/public_html/index.html")

                data_ret = {'createWebSiteStatus': 1, 'error_message': "None", "existsStatus": 0}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
            virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
            data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg),"existsStatus":0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {'createWebSiteStatus': 0, 'error_message': "not logged in as admin","existsStatus":0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def submitDomainCreation(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            masterDomain = data['masterDomain']
            domain = data['domainName']
            phpSelection = data['phpSelection']

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

            ####### Limitations check

            master = Websites.objects.get(domain=masterDomain)

            if master.package.allowedDomains > master.childdomains_set.all().count():
                pass
            else:
                data_ret = {"existsStatus": 0, 'createWebSiteStatus': 0,
                            'error_message': "Exceeded maximum number of domains for this package"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            ####### Limitations Check End

            ssl = data['ssl']
            path = data['path']

            ####### Creation
            try:
                restore = data['restore']
            except:
                if len(path) > 0:
                    path = path.lstrip("/")
                    path = "/home/" + masterDomain + "/public_html/" + path
                else:
                    path = "/home/" + masterDomain + "/public_html/" + domain

            if virtualHostUtilities.createDirectoryForDomain(masterDomain, domain, phpSelection, path,
                                                             master.adminEmail) != 1:
                numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
                virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                data_ret = {"existsStatus": 1, 'createWebSiteStatus': 0,
                            'error_message': "Can not create configurations, see CyberCP main log file."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if virtualHostUtilities.createConfigInMainDomainHostFile(domain, masterDomain) != 1:
                numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
                virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                data_ret = {"existsStatus": 1, 'createWebSiteStatus': 0,
                            'error_message': "Can not create configurations, see CyberCP main log file."}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            if ssl == 1:
                installUtilities.reStartOpenLiteSpeed("restart", "ols")
            else:
                installUtilities.reStartLiteSpeed()

            if ssl == 1:
                ssl_responce = sslUtilities.obtainSSLForADomain(domain, master.adminEmail, path)
                if ssl_responce == 1:
                    sslUtilities.installSSLForDomain(domain)
                    installUtilities.reStartLiteSpeed()
                else:
                    numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
                    virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)

                    data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                'error_message': str(
                                    ssl_responce) + ", for more information see CyberCP main log file."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

            website = ChildDomains(master=master, domain=domain, path=path, phpSelection=phpSelection, ssl=ssl)

            website.save()

            shutil.copy("/usr/local/CyberCP/index.html", path + "/index.html")

            data_ret = {'createWebSiteStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        numberOfWebsites = Websites.objects.count() + ChildDomains.objects.count()
        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
        data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg), "existsStatus": 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def fetchDomains(request):
    try:
        val = request.session['userID']
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
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)


                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
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
        val = request.session['userID']

        try:

            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = admin.websites_set.all()
            else:
                websites = Websites.objects.filter(admin=admin)


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
        val = request.session['userID']

        try:

            admin = Administrator.objects.get(pk=request.session['userID'])

            if request.method == 'POST':
                try:
                    data = json.loads(request.body)
                    status = data['page']
                    pageNumber = int(status)

                except BaseException, msg:
                    status = str(msg)
            if admin.type == 1:
                finalPageNumber = ((pageNumber * 10))-10
                endPageNumber = finalPageNumber + 10
                websites = Websites.objects.all()[finalPageNumber:endPageNumber]

            else:
                finalPageNumber = ((pageNumber * 10)) - 10
                endPageNumber = finalPageNumber + 10
                websites = Websites.objects.filter(admin=admin)[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0

            for items in websites:
                if items.state == 0:
                    state = "Suspended"
                else:
                    state = "Active"
                dic = {'domain': items.domain, 'adminEmail': items.adminEmail,'admin': items.admin.userName,'package': items.package.packageName,'state':state}

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
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                websiteName = data['websiteName']

                numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()

                virtualHostUtilities.deleteVirtualHostConfigurations(websiteName,numberOfWebsites)


                delWebsite = Websites.objects.get(domain=websiteName)
                databases = Databases.objects.filter(website=delWebsite)

                childDomains = delWebsite.childdomains_set.all()

                for items in childDomains:
                    numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
                    virtualHostUtilities.deleteVirtualHostConfigurations(items.domain, numberOfWebsites)


                for items in databases:
                    mysqlUtilities.deleteDatabase(items.dbName, items.dbUser)


                delWebsite.delete()



                installUtilities.reStartLiteSpeed()

                data_ret = {'websiteDeleteStatus': 1,'error_message': "None"}
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

                numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()

                virtualHostUtilities.deleteVirtualHostConfigurations(websiteName,numberOfWebsites)


                delWebsite = ChildDomains.objects.get(domain=websiteName)

                delWebsite.delete()


                installUtilities.reStartLiteSpeed()

                data_ret = {'websiteDeleteStatus': 1,'error_message': "None"}
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
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                websiteName = data['websiteName']
                state = data['state']

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

                data_ret = {'websiteStatus': 1,'error_message': "None"}
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
        val = request.session['userID']
        try:

            if request.method == 'POST':

                admin = Administrator.objects.get(pk=request.session['userID'])

                if admin.type == 1:
                    packs = Package.objects.all()
                else:
                    packs = Package.objects.filter(admin=admin)

                if admin.type == 1:
                    admins = Administrator.objects.all()
                else:
                    admins = Administrator.objects.filter(owner=admin.pk)


                ## Get packs name

                json_data = "["
                checker = 0


                for items in packs:
                    dic = {"pack":items.packageName}

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
                    dic = {"adminNames": items.userName}

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
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['domain']
                package = data['packForWeb']
                email = data['email']
                phpVersion = data['phpVersion']
                admin = data['admin']

                newOwner = Administrator.objects.get(userName=admin)

                modifyWeb = Websites.objects.get(domain=domain)
                webpack = Package.objects.get(packageName=package)

                modifyWeb.package = webpack
                modifyWeb.adminEmail = email
                modifyWeb.phpSelection = phpVersion
                modifyWeb.admin = newOwner

                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + domain
                completePathToConfigFile = confPath + "/vhost.conf"

                virtualHostUtilities.changePHP(completePathToConfigFile,phpVersion)
                installUtilities.reStartLiteSpeed()

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


def domain(request,domain):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)


        if Websites.objects.filter(domain=domain).exists():
            if admin.type == 1:
                website = Websites.objects.get(domain=domain)

                Data = {}

                Data['ftpTotal'] = website.package.ftpAccounts
                Data['ftpUsed'] = website.users_set.all().count()

                Data['databasesUsed'] = website.databases_set.all().count()
                Data['databasesTotal'] = website.package.dataBases

                Data['domain'] = domain

                diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/"+domain,website.package.diskSpace)

                ## bw usage calculation

                bwData = findBWUsage.findDomainBW(domain,website.package.bandwidth)

                Data['bwInMBTotal'] = website.package.bandwidth
                Data['bwInMB'] = bwData[0]
                Data['bwUsage'] = bwData[1]






                if diskUsageDetails!=None:
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
                website = Websites.objects.get(domain=domain)
                if website.admin == admin:

                    Data = {}

                    Data['ftpTotal'] = website.package.ftpAccounts
                    Data['ftpUsed'] = website.users_set.all().count()

                    Data['databasesUsed'] = website.databases_set.all().count()
                    Data['databasesTotal'] = website.package.dataBases

                    Data['domain'] = domain

                    diskUsageDetails = virtualHostUtilities.getDiskUsage("/home/" + domain, website.package.diskSpace)

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
                    return render(request, 'websiteFunctions/website.html',
                                  {"error": 1, "domain": "You do not own this domain."})

        else:
            return render(request, 'websiteFunctions/website.html', {"error":1,"domain": "This domain does not exists"})
    except KeyError:
        return redirect(loadLoginPage)



def getDataFromLogFile(request):
    data = json.loads(request.body)
    logType = data['logType']
    virtualHost = data['virtualHost']
    page = data['page']

    if logType == 1:
        fileName = "/home/" + virtualHost + "/logs/" + virtualHost + ".access_log"
    else:
        fileName = "/home/" + virtualHost + "/logs/" + virtualHost + ".error_log"

    numberOfTotalLines = int(subprocess.check_output(["wc", "-l", fileName]).split(" ")[0])

    if numberOfTotalLines < 25 :
        data = subprocess.check_output(["cat", fileName])
    else:
        if page == 1:
            end = numberOfTotalLines
            start = end - 24
            if start <= 0:
                start = 1
            startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
            command = "sed -n " + startingAndEnding + " " + fileName
            proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            data = proc.stdout.read()
        else:
            end = numberOfTotalLines - ((page-1)*25)
            start = end - 24
            if start <= 0:
                start = 1
            startingAndEnding = "'" + str(start) + "," + str(end) + "p'"
            command = "sed -n " + startingAndEnding + " " + fileName
            proc = subprocess.Popen(shlex.split(command), stdout=subprocess.PIPE)
            data = proc.stdout.read()

    data = data.split("\n")


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


def installWordpress(request):
    try:
        val = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                domainName = data['domain']
                home = data['home']

                finalPath = ""

                if home == '0':
                    path = data['path']
                    finalPath = "/home/" + domainName + "/public_html/" + path + "/"
                else:
                    finalPath = "/home/" + domainName + "/public_html/"


                if not os.path.exists(finalPath):
                    os.makedirs(finalPath)

                if not os.listdir(finalPath):
                    pass
                else:
                    data_ret = {'installStatus': 0, 'error_message': "Target directory should be empty before installation, otherwise data loss could occur."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)



                ## Get wordpress

                if not os.path.exists("latest.tar.gz"):
                    command = 'wget --no-check-certificate http://wordpress.org/latest.tar.gz'

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                command = 'tar -xzvf latest.tar.gz -C ' + finalPath

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ## Get plugin

                if not os.path.exists("litespeed-cache.1.1.5.1.zip"):
                    command = 'wget --no-check-certificate https://downloads.wordpress.org/plugin/litespeed-cache.1.1.5.1.zip'

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                command = 'unzip litespeed-cache.1.1.5.1.zip -d ' + finalPath

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                root = finalPath

                for filename in listdir(join(root, 'wordpress')):
                    move(join(root, 'wordpress', filename), join(root, filename))

                rmdir(root + "wordpress")

                shutil.copytree(finalPath + "litespeed-cache", finalPath + "wp-content/plugins/litespeed-cache")
                shutil.rmtree(finalPath + "litespeed-cache")


                ## DB Creation

                dbName = randomPassword.generate_pass()
                dbUser = dbName
                dbPassword = randomPassword.generate_pass()


                ## DB Creation

                website = Websites.objects.get(domain=domainName)

                if website.package.dataBases > website.databases_set.all().count():
                    pass
                else:
                    # remove the downloaded files if installation fails
                    shutil.rmtree(finalPath)
                    homeDir = "/home/"+domainName+"/public_html"

                    if not os.path.exists(homeDir):
                        os.mkdir(homeDir)
                        command = 'chown -R nobody:nobody '+homeDir
                        cmd = shlex.split(command)
                        res = subprocess.call(cmd)

                    data_ret = {'installStatus': 0,
                                'error_message': "Maximum database limit reached for this website."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                if Databases.objects.filter(dbName=dbName).exists() or Databases.objects.filter(
                        dbUser=dbUser).exists():
                    # remove the downloaded files if installation fails
                    shutil.rmtree(finalPath)
                    homeDir = "/home/" + domainName + "/public_html"

                    if not os.path.exists(homeDir):
                        os.mkdir(homeDir)
                        command = 'chown -R nobody:nobody ' + homeDir
                        cmd = shlex.split(command)
                        res = subprocess.call(cmd)
                    data_ret = {'installStatus': 0,
                                'error_message': "This database or user is already taken."}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                result = mysqlUtilities.createDatabase(dbName, dbUser, dbPassword)

                if result == 1:
                    pass
                else:
                    # remove the downloaded files
                    shutil.rmtree(finalPath)
                    homeDir = "/home/" + domainName + "/public_html"

                    if not os.path.exists(homeDir):
                        os.mkdir(homeDir)
                        command = 'chown -R nobody:nobody ' + homeDir
                        cmd = shlex.split(command)
                        res = subprocess.call(cmd)

                    data_ret = {'installStatus': 0,
                                'error_message': result}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                db = Databases(website=website, dbName=dbName, dbUser=dbUser)
                db.save()

                ## edit config file

                wpconfigfile = finalPath + "wp-config-sample.php"

                data = open(wpconfigfile, "r").readlines()

                writeDataToFile = open(wpconfigfile, "w")

                defDBName = "define('DB_NAME', '" + dbName + "');" + "\n"
                defDBUser = "define('DB_USER', '" + dbUser + "');" + "\n"
                defDBPassword = "define('DB_PASSWORD', '" + dbPassword + "');" + "\n"

                for items in data:
                    if items.find("DB_NAME") > -1:
                        if items.find("database_name_here") > -1:
                            writeDataToFile.writelines(defDBName)
                            print ("database_name_here")
                    elif items.find("DB_USER") > -1:
                        if items.find("username_here") > -1:
                            writeDataToFile.writelines(defDBUser)
                            print ("username_here")
                    elif items.find("DB_PASSWORD") > -1:
                        writeDataToFile.writelines(defDBPassword)
                    else:
                        writeDataToFile.writelines(items)

                writeDataToFile.close()

                os.rename(wpconfigfile, finalPath + 'wp-config.php')

                command = 'chown -R nobody:nobody ' + finalPath

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                virtualHostUtilities.addRewriteRules(domainName)

                installUtilities.reStartLiteSpeed()

                status = {"installStatus": 1}

                final_json = json.dumps(status)
                return HttpResponse(final_json)

            except BaseException, msg:
                # remove the downloaded files
                shutil.rmtree(finalPath)
                homeDir = "/home/" + domainName + "/public_html"

                if not os.path.exists(homeDir):
                    os.mkdir(homeDir)
                    command = 'chown -R nobody:nobody ' + homeDir
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)
                data_ret = {'installStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


    except KeyError, msg:
        status = {"installStatus":0,"error":str(msg)}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getDataFromLogFile]")
        return HttpResponse("Not Logged in as admin")

def getDataFromConfigFile(request):
    try:
        val = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                filePath = installUtilities.Server_root_path + "/conf/vhosts/"+virtualHost+"/vhost.conf"

                configData = open(filePath,"r").read()

                if len(configData) == 0:
                    status = {"logstatus": 0, "error_message": "Log file is currently empty"}

                    final_json = json.dumps(status)
                    return HttpResponse(final_json)



                status = {"configstatus":1,"configData":configData}

                final_json = json.dumps(status)
                return HttpResponse(final_json)

            except BaseException, msg:
                data_ret = {'configstatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getDataFromConfigFile]")
        return HttpResponse("Not Logged in as admin")

def saveConfigsToFile(request):
    try:
        val = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']
                configData = data['configData']

                filePath = installUtilities.Server_root_path + "/conf/vhosts/"+virtualHost+"/vhost.conf"

                vhost = open(filePath,"w")

                vhost.write(configData)

                vhost.close()


                status = {"configstatus":1,"configData":configData}

                final_json = json.dumps(status)
                return HttpResponse(final_json)

            except BaseException, msg:
                data_ret = {'configstatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not save, see main log file."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[saveConfigsToFile]")
        return HttpResponse("Not Logged in as admin")


def getRewriteRules(request):
    try:
        val = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                filePath = "/home/"+virtualHost+"/public_html/.htaccess"

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
        val = request.session['userID']

        if request.method == 'POST':
            try:
                data = json.loads(request.body)
                virtualHost = data['virtualHost']
                rewriteRules = data['rewriteRules']

                virtualHostUtilities.addRewriteRules(virtualHost)

                filePath = "/home/" + virtualHost + "/public_html/.htaccess"

                vhost = open(filePath,"w")

                vhost.write(rewriteRules)

                vhost.close()


                status = {"rewriteStatus":1}

                final_json = json.dumps(status)
                return HttpResponse(final_json)

            except BaseException, msg:
                data_ret = {'rewriteStatus': 0, 'error_message': str(msg)}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not save, see main log file."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[saveConfigsToFile]")
        return HttpResponse("Not Logged in as admin")



def saveSSL(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['virtualHost']
                cert = data['cert']
                key = data['key']

                pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + domain

                website = Websites.objects.get(domain=domain)


                if website.ssl == 0:
                    try:
                        os.mkdir(pathToStoreSSL)

                        pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                        pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                        privkey = open(pathToStoreSSLPrivKey, 'w')
                        privkey.write(key)
                        privkey.close()

                        fullchain = open(pathToStoreSSLFullChain, 'w')
                        fullchain.write(cert)
                        fullchain.close()

                        sslUtilities.installSSLForDomain(domain)

                        installUtilities.reStartLiteSpeed()

                        website.ssl = 1
                        website.save()

                        data_ret = {'sslStatus': 1, 'error_message': "None"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Can not create directory to stroe SSL [saveSSL]]")
                        data_ret = {'sslStatus': 0, 'error_message': str(msg)}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                else:


                    pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                    pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                    privkey = open(pathToStoreSSLPrivKey, 'w')
                    privkey.write(key)
                    privkey.close()

                    fullchain = open(pathToStoreSSLFullChain, 'w')
                    fullchain.write(cert)
                    fullchain.close()

                    installUtilities.reStartLiteSpeed()

                    website.ssl = 1
                    website.save()

                    data_ret = {'sslStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)



                data_ret = {'saveStatus': 1,'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Can not create directory to stroe SSL [saveSSL]]")
            data_ret = {'sslStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [Can not create directory to stroe SSL [saveSSL]]")
        data_ret = {'sslStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)

def filemanager(request, domain):
    try:
        val = request.session['userID']
        request.session['fileManagerHome'] = '/home/' + domain
        fileManage.fm.root = request.session['fileManagerHome']
        return fileManage.index(request)
    except KeyError:
        return redirect(loadLoginPage)



def CreateWebsiteFromBackup(request):
    try:
        if request.method == 'POST':

            data = json.loads(request.body)
            backupFile = data['backupFile'].strip(".tar.gz")

            originalFile = "/home/backup/" + data['backupFile']

            if not os.path.exists(originalFile):
                dir = data['dir']
                path = "/home/backup/transfer-"+str(dir)+"/"+backupFile
            else:
                path = "/home/backup/" + backupFile

            admin = Administrator.objects.get(pk=1)
            websiteOwner = admin.userName

            adminEmail = admin.email

            ## open meta file to read data


            data = open(path + "/meta", 'r').readlines()
            domain = data[0].split('-')[0]
            phpSelection = data[0].split("-")[1].strip("\n")

            try:
                website = Websites.objects.get(domain=domain)
                data_ret = {"existsStatus": 1, 'createWebSiteStatus': 0,
                            'error_message': "Website Already Exists, please delete this account to restore."}

                status = open(path + '/status', "w")
                status.write("Website already exists")
                status.close()

                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            except:
                pass

            check = 0
            dbCheck = 0

            for items in data:
                if check == 0:
                    if virtualHostUtilities.createDirectoryForVirtualHost(domain, adminEmail, phpSelection) != 1:
                        numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
                        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                        data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                    'error_message': "Can not create configurations, see CyberCP main log file."}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                    if virtualHostUtilities.createConfigInMainVirtualHostFile(domain) != 1:
                        numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
                        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
                        data_ret = {"existsStatus": 1, 'createWebSiteStatus': 1,
                                    'error_message': "Can not create configurations, see CyberCP main log file."}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                    installUtilities.reStartLiteSpeed()

                    selectedPackage = Package.objects.get(packageName="Default")

                    website = Websites(admin=admin, package=selectedPackage, domain=domain, adminEmail=adminEmail,
                                       phpSelection=phpSelection, ssl=0)

                    website.save()

                    #shutil.copy("/usr/local/CyberCP/index.html", "/home/" + domain + "/public_html/index.html")

                    check = check + 1
                else:
                    if items.find("Databases") > -1:
                        dbCheck = 1
                        continue

                    if dbCheck == 1:
                        dbData = items.split('-')
                        mysqlUtilities.createDatabase(dbData[0], dbData[1], "cyberpanel")
                        newDB = Databases(website=website, dbName=dbData[0], dbUser=dbData[1])
                        newDB.save()

            status = open(path + '/status', "w")
            status.write("Accounts and DBs Created")
            status.close()

            data_ret = {'createWebSiteStatus': 1, 'error_message': "None", "existsStatus": 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        numberOfWebsites = Websites.objects.count()+ChildDomains.objects.count()
        virtualHostUtilities.deleteVirtualHostConfigurations(domain, numberOfWebsites)
        data_ret = {'createWebSiteStatus': 0, 'error_message': str(msg), "existsStatus": 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def changePHP(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                childDomain = data['childDomain']
                phpVersion = data['phpSelection']


                confPath = virtualHostUtilities.Server_root + "/conf/vhosts/" + childDomain
                completePathToConfigFile = confPath + "/vhost.conf"

                virtualHostUtilities.changePHP(completePathToConfigFile,phpVersion)
                installUtilities.reStartLiteSpeed()


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