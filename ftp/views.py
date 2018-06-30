# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import hashlib
import json
from django.shortcuts import render,redirect
from django.http import HttpResponse
from models import Users
from loginSystem.models import Administrator
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
from websiteFunctions.models import Websites
import subprocess
from plogical.virtualHostUtilities import virtualHostUtilities
import shlex
from plogical.ftpUtilities import FTPUtilities
# Create your views here.

def loadFTPHome(request):
    try:
        val = request.session['userID']
        return render(request,'ftp/index.html')
    except KeyError:
        return redirect(loadLoginPage)


def createFTPAccount(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                websites = Websites.objects.all()
                websitesName = []

                for items in websites:
                    websitesName.append(items.domain)
            else:
                if admin.type == 2:
                    websites = Websites.objects.filter(admin=admin)
                    admins = Administrator.objects.filter(owner=admin.pk)
                    websitesName = []

                    for items in websites:
                        websitesName.append(items.domain)

                    for items in admins:
                        webs = Websites.objects.filter(admin=items)

                        for web in webs:
                            websitesName.append(web.domain)
                else:
                    websitesName = []
                    websites = Websites.objects.filter(admin=admin)
                    for items in websites:
                        websitesName.append(items.domain)

            return render(request, 'ftp/createFTPAccount.html', {'websiteList':websitesName,'admin':admin.userName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def submitFTPCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                userName = data['ftpUserName']
                password = data['ftpPassword']
                path = data['path']
                domainName = data['ftpDomain']

                admin = Administrator.objects.get(id=val)
                website = Websites.objects.get(domain=domainName)

                if admin.type != 1:
                    if website.admin != admin:
                        data_ret = {'creatFTPStatus': 0, 'error_message': 'Not enough privileges.'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                if len(path) > 0:
                    pass
                else:
                    path = 'None'

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/ftpUtilities.py"

                execPath = execPath + " submitFTPCreation --domainName " + domainName + " --userName " + userName \
                           + " --password " + password + " --path " + path + " --owner " + admin.userName


                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    data_ret = {'creatFTPStatus': 1, 'error_message': 'None'}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'creatFTPStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)



        except BaseException,msg:
            data_ret = {'creatFTPStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'creatFTPStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def deleteFTPAccount(request):
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

            return render(request, 'ftp/deleteFTPAccount.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def fetchFTPAccounts(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['ftpDomain']

                website = Websites.objects.get(domain=domain)
                admin = Administrator.objects.get(id=val)

                if admin.type != 1:
                    if website.admin != admin:
                        data_ret = {'fetchStatus': 0, 'error_message': 'Not enough privileges.'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)


                ftpAccounts = website.users_set.all()

                json_data = "["
                checker = 0

                for items in ftpAccounts:
                    dic = {"userName":items.user}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)



        except BaseException,msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def submitFTPDelete(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(id=val)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                ftpUserName = data['ftpUsername']

                ftp = Users.objects.get(user=ftpUserName)

                if admin.type != 1:
                    if ftp.domain.admin != admin:
                        data_ret = {'deleteStatus': 0, 'error_message': 'Not enough privileges.'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                FTPUtilities.submitFTPDeletion(ftpUserName)

                final_json = json.dumps({'deleteStatus': 1, 'error_message': "None"})
                return HttpResponse(final_json)

        except BaseException,msg:
            data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'deleteStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def listFTPAccounts(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

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

            return render(request, 'ftp/listFTPAccounts.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def getAllFTPAccounts(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':


                data = json.loads(request.body)
                selectedDomain = data['selectedDomain']

                domain = Websites.objects.get(domain=selectedDomain)
                admin = Administrator.objects.get(id=val)

                if admin.type != 1:
                    if domain.admin != admin:
                        data_ret = {'fetchStatus': 0, 'error_message': 'Not enough privileges.'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                records = Users.objects.filter(domain=domain)

                json_data = "["
                checker = 0

                for items in records:
                    dic = {'id': items.id,
                           'user': items.user,
                           'dir': items.dir,
                           'quotasize': str(items.quotasize)+"MB",
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


def changePassword(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(id=val)
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                userName = data['ftpUserName']
                password = data['ftpPassword']

                ftp = Users.objects.get(user=userName)

                if admin.type != 1:
                    if ftp.domain.admin != admin:
                        data_ret = {'changePasswordStatus': 0, 'error_message': 'Not enough privileges.'}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                FTPUtilities.changeFTPPassword(userName, password)

                data_ret = {'changePasswordStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'changePasswordStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'changePasswordStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)