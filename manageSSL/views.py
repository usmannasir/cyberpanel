# -*- coding: utf-8 -*-

from plogical.httpProc import httpProc
from websiteFunctions.models import Websites, ChildDomains
from loginSystem.models import Administrator
from plogical.virtualHostUtilities import virtualHostUtilities
from django.http import HttpResponse
import json
from plogical.acl import ACLManager
from plogical.processUtilities import ProcessUtilities

# Create your views here.

def loadSSLHome(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    proc = httpProc(request, 'manageSSL/index.html',
                    currentACL, 'admin')
    return proc.render()


def manageSSL(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    websitesName = ACLManager.findAllSites(currentACL, userID)
    proc = httpProc(request, 'manageSSL/manageSSL.html',
                    {'websiteList': websitesName}, 'manageSSL')
    return proc.render()

def v2ManageSSL(request):
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    websitesName = ACLManager.findAllSites(currentACL, userID)

    data = {}

    if ACLManager.CheckForPremFeature('all'):
        data['PremStat'] = 1
    else:
        data['PremStat'] = 0

    if request.method == 'POST':
        SAVED_CF_Key = request.POST.get('SAVED_CF_Key')
        SAVED_CF_Email = request.POST.get('SAVED_CF_Email')
        from plogical.dnsUtilities import DNS
        DNS.ConfigureCloudflareInAcme(SAVED_CF_Key, SAVED_CF_Email)
        data['SaveSuccess'] = 1


    RetStatus, SAVED_CF_Key, SAVED_CF_Email = ACLManager.FetchCloudFlareAPIKeyFromAcme()
    from plogical.dnsUtilities import DNS
    DNS.ConfigurePowerDNSInAcme()

    data['SAVED_CF_Key'] = SAVED_CF_Key
    data['SAVED_CF_Email'] = SAVED_CF_Email
    data['websiteList'] = websitesName

    proc = httpProc(request, 'manageSSL/v2ManageSSL.html',
                    data, 'manageSSL')
    return proc.render()

def v2IssueSSL(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)
        try:
            if ACLManager.CheckForPremFeature('all'):
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
                    execPath = execPath + " issueSSLv2 --virtualHostName " + virtualHost + " --administratorEmail " + adminEmail + " --path " + path
                    output = ProcessUtilities.outputExecutioner(execPath)

                    if output.find("1,") > -1:
                        ## ssl issue ends

                        website.ssl = 1
                        website.save()

                        data_ret = {'status': 1, "SSL": 1,
                                    'error_message': "None", 'sslLogs': output}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'status': 0, "SSL": 0,
                                    'error_message': output, 'sslLogs': output}
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
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)
    websitesName = ACLManager.findAllSites(currentACL, userID, 1)
    proc = httpProc(request, 'manageSSL/sslForHostName.html',
                    {'websiteList': websitesName}, 'hostnameSSL')
    return proc.render()


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

                try:
                    website = Websites.objects.get(domain=virtualHost)
                    path = "/home/" + virtualHost + "/public_html"
                except:
                    website = ChildDomains.objects.get(domain=virtualHost)
                    path = website.path

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
    userID = request.session['userID']
    currentACL = ACLManager.loadedACL(userID)

    websitesName = ACLManager.findAllSites(currentACL, userID)
    websitesName = websitesName + ACLManager.findChildDomains(websitesName)

    proc = httpProc(request, 'manageSSL/sslForMailServer.html',
                    {'websiteList': websitesName}, 'mailServerSSL')
    return proc.render()


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
