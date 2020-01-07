# -*- coding: utf-8 -*-


from django.shortcuts import render, redirect
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites, ChildDomains
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from django.http import HttpResponse
import json
import shlex
import subprocess
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.processUtilities import ProcessUtilities


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

        return render(request, 'manageSSL/manageSSL.html', {'websiteList': websitesName})
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

                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                try:
                    website = ChildDomains.objects.get(domain=virtualHost)
                    adminEmail = website.master.adminEmail
                    path = website.path
                except:
                    website = Websites.objects.get(domain=virtualHost)
                    adminEmail = website.adminEmail
                    path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSL --virtualHostName " + virtualHost + " --administratorEmail " + adminEmail + " --path " + path
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    pass
                else:
                    data_ret = {'status': 0, "SSL": 0,
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

        except BaseException as msg:
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

        return render(request, 'manageSSL/sslForHostName.html', {'websiteList': websitesName})
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

                data = json.loads(request.body)
                virtualHost = data['virtualHost']
                admin = Administrator.objects.get(pk=userID)
                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                ## ssl issue

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSLForHostName --virtualHostName " + virtualHost + " --path " + path
                output = ProcessUtilities.outputExecutioner(execPath)

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

        except BaseException as msg:
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
        websitesName = websitesName + ACLManager.findChildDomains(websitesName)

        return render(request, 'manageSSL/sslForMailServer.html', {'websiteList': websitesName})
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

                admin = Administrator.objects.get(pk=userID)
                if ACLManager.checkOwnership(virtualHost, admin, currentACL) == 1:
                    pass
                else:
                    return ACLManager.loadErrorJson()

                path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"
                execPath = execPath + " issueSSLForMailServer --virtualHostName " + virtualHost + " --path " + path
                output = ProcessUtilities.outputExecutioner(execPath)

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


        except BaseException as msg:
            data_ret = {"status": 0, "SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError as msg:
        data_ret = {"status": 0, "SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
