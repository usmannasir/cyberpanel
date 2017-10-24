# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.sslUtilities import sslUtilities
from plogical.installUtilities import installUtilities
from django.http import HttpResponse
import json
import os
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import shutil
import shlex
import subprocess
# Create your views here.


def loadSSLHome(request):
    try:
        val = request.session['userID']

        return render(request, 'manageSSL/index.html')
    except KeyError:
        return redirect(loadLoginPage)

def manageSSL(request):
    try:
        val = request.session['userID']

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


        return render(request, 'manageSSL/manageSSL.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)


def issueSSL(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                website = Websites.objects.get(domain=virtualHost)

                srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
                srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

                pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHost

                pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                if os.path.exists(pathToStoreSSLPrivKey):
                    os.remove(pathToStoreSSLPrivKey)
                if os.path.exists(pathToStoreSSLFullChain):
                    os.remove(pathToStoreSSLFullChain)

                adminEmail = "email@"+virtualHost


                if not (os.path.exists(srcPrivKey) and os.path.exists(srcFullChain)):
                    ssl_responce = sslUtilities.obtainSSLForADomain(virtualHost, adminEmail)
                    if ssl_responce == 1:
                        sslUtilities.installSSLForDomain(virtualHost)
                        installUtilities.reStartLiteSpeed()
                        website.ssl = 1
                        website.save()
                        data_ret = {"SSL": 1,
                                    'error_message': "None"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                    else:
                        data_ret = {"SSL": 0,
                                    'error_message': str(ssl_responce) + ", for more information see CyberCP main log file."}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                else:
                    ###### Copy SSL To config location ######

                    try:
                        os.mkdir(pathToStoreSSL)
                    except BaseException, msg:
                        logging.writeToFile(
                            str(msg) + " [Directory for SSL already exists.. Continuing [obtainSSLForADomain]]")

                    srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
                    srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"


                    shutil.copy(srcPrivKey, pathToStoreSSLPrivKey)
                    shutil.copy(srcFullChain, pathToStoreSSLFullChain)

                    website.ssl = 1
                    website.save()

                    data_ret = {"SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"SSL": 1,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"SSL": 1,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def sslForHostName(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=request.session['userID'])

        if admin.type==1:
            pass
        else:
            return HttpResponse("You should be admin to issue SSL For Hostname.")

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

        return render(request, 'manageSSL/sslForHostName.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)


def obtainHostNameSSL(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                website = Websites.objects.get(domain=virtualHost)

                srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
                srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"

                pathToStoreSSL = virtualHostUtilities.Server_root + "/conf/vhosts/" + "SSL-" + virtualHost

                pathToStoreSSLPrivKey = pathToStoreSSL + "/privkey.pem"
                pathToStoreSSLFullChain = pathToStoreSSL + "/fullchain.pem"

                destPrivKey = "/usr/local/lscp/key.pem"
                destCert = "/usr/local/lscp/cert.pem"


                ## removing old certs

                if os.path.exists(pathToStoreSSLPrivKey):
                    os.remove(pathToStoreSSLPrivKey)
                if os.path.exists(pathToStoreSSLFullChain):
                    os.remove(pathToStoreSSLFullChain)

                ## removing old certs for lscpd
                if os.path.exists(destPrivKey):
                    os.remove(destPrivKey)
                if os.path.exists(destCert):
                    os.remove(destCert)

                adminEmail = "email@"+virtualHost


                if not (os.path.exists(srcPrivKey) and os.path.exists(srcFullChain)):
                    ssl_responce = sslUtilities.obtainSSLForADomain(virtualHost, adminEmail)
                    if ssl_responce == 1:
                        sslUtilities.installSSLForDomain(virtualHost)
                        installUtilities.reStartLiteSpeed()
                        website.ssl = 1
                        website.save()

                        ## lcpd specific functions

                        shutil.copy(srcPrivKey, destPrivKey)
                        shutil.copy(srcFullChain, destCert)

                        command = 'systemctl restart lscpd'

                        cmd = shlex.split(command)

                        res = subprocess.call(cmd)

                        data_ret = {"SSL": 1,
                                    'error_message': "None"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                    else:
                        data_ret = {"SSL": 0,
                                    'error_message': str(ssl_responce) + ", for more information see CyberCP main log file."}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                else:
                    ###### Copy SSL To config location ######

                    try:
                        os.mkdir(pathToStoreSSL)
                    except BaseException, msg:
                        logging.writeToFile(str(msg) + " [Directory for SSL already exists.. Continuing [obtainSSLForADomain]]")

                    srcPrivKey = "/etc/letsencrypt/live/" + virtualHost + "/privkey.pem"
                    srcFullChain = "/etc/letsencrypt/live/" + virtualHost + "/fullchain.pem"


                    shutil.copy(srcPrivKey, pathToStoreSSLPrivKey)
                    shutil.copy(srcFullChain, pathToStoreSSLFullChain)

                    ## lcpd specific functions

                    shutil.copy(srcPrivKey, destPrivKey)
                    shutil.copy(srcFullChain, destCert)

                    command = 'systemctl restart lscpd'

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)
                    website.ssl = 1
                    website.save()

                    data_ret = {"SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"SSL": 1,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"SSL": 1,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)