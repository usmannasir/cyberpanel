# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites,ChildDomains
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from django.http import HttpResponse
import json
import shlex
import subprocess
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
# Create your views here.


def loadSSLHome(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        return render(request, 'manageSSL/index.html', currentACL)
    except KeyError:
        return redirect(loadLoginPage)

def manageSSL(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        elif currentACL['manageSSL'] == 1:
            pass
        else:
            return ACLManager.loadError()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        return render(request, 'manageSSL/manageSSL.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)

def issueSSL(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        try:
            if request.method == 'POST':
                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['manageSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']


                adminEmail = ""
                path = ""

                try:
                    website = ChildDomains.objects.get(domain=virtualHost)
                    adminEmail = website.master.adminEmail
                    path = website.path
                except:
                    website = Websites.objects.get(domain=virtualHost)
                    adminEmail = website.adminEmail
                    path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSL --virtualHostName " + virtualHost + " --administratorEmail " + adminEmail + " --path " + path
                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    pass
                else:
                    data_ret = {'status': 0 ,"SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                ## ssl issue ends

                website.ssl = 1
                website.save()

                data_ret = {'status': 1, "SSL": 1,
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'status': 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {'status': 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def sslForHostName(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        elif currentACL['hostnameSSL'] == 1:
            pass
        else:
            return ACLManager.loadError()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        return render(request, 'manageSSL/sslForHostName.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)

def obtainHostNameSSL(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['hostnameSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " issueSSLForHostName --virtualHostName " + virtualHost + " --path " + path

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    data_ret = {"status": 1, "SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"status": 0, "SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                    ## ssl issue ends

        except BaseException,msg:
            data_ret = {"status": 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"status": 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def sslForMailServer(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        elif currentACL['mailServerSSL'] == 1:
            pass
        else:
            return ACLManager.loadError()

        websitesName = ACLManager.findAllSites(currentACL, userID)

        return render(request, 'manageSSL/sslForMailServer.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)

def obtainMailServerSSL(request):
    try:
        userID = request.session['userID']
        try:
            if request.method == 'POST':

                currentACL = ACLManager.loadedACL(userID)

                if currentACL['admin'] == 1:
                    pass
                elif currentACL['mailServerSSL'] == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson('SSL', 0)

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " issueSSLForMailServer --virtualHostName " + virtualHost + " --path " + path

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    data_ret = {"status": 1, "SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"status": 0, "SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                    ## ssl issue ends


        except BaseException,msg:
            data_ret = {"status": 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {"status": 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)