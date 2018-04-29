# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites,ChildDomains
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

                adminEmail = ""
                path = ""

                try:
                    website = ChildDomains.objects.get(domain=virtualHost)
                    adminEmail = website.master.adminEmail
                    path = data['path']
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
                    data_ret = {"SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                ## ssl issue ends

                website.ssl = 1
                website.save()

                data_ret = {"SSL": 1,
                            'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {"SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"SSL": 0,
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

                path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " issueSSLForHostName --virtualHostName " + virtualHost + " --path " + path


                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    data_ret = {"SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                ## ssl issue ends

        except BaseException,msg:
            data_ret = {"SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError:
        data_ret = {"SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def sslForMailServer(request):
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

        return render(request, 'manageSSL/sslForMailServer.html',{'websiteList':websitesName})
    except KeyError:
        return redirect(loadLoginPage)

def obtainMailServerSSL(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                virtualHost = data['virtualHost']

                website = Websites.objects.get(domain=virtualHost)

                path = "/home/" + virtualHost + "/public_html"

                ## ssl issue

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/virtualHostUtilities.py"

                execPath = execPath + " issueSSLForMailServer --virtualHostName " + virtualHost + " --path " + path

                logging.writeToFile(execPath)


                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    data_ret = {"SSL": 1,
                                'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {"SSL": 0,
                                'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                ## ssl issue ends

        except BaseException,msg:
            data_ret = {"SSL": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {"SSL": 0,
                    'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)