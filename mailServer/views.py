# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from models import Domains,EUsers
# Create your views here.
from loginSystem.models import Administrator
from websiteFunctions.models import Websites
from loginSystem.views import loadLoginPage
import plogical.CyberCPLogFileWriter as logging
import json
import os
import shutil
import shlex
import subprocess


def loadEmailHome(request):
    try:
        val = request.session['userID']
        return render(request, 'mailServer/index.html')
    except KeyError:
        return redirect(loadLoginPage)


def createEmailAccount(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = admin.websites_set.all()
            else:
                websites = Websites.objects.filter(admin=admin)

            websitesName = []

            for items in websites:
                websitesName.append(items.domain)

            return render(request, 'mailServer/createEmailAccount.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def submitEmailCreation(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['domain']
                userName = data['username']
                password = data['password']

                path = "/usr/local/CyberCP/install/rainloop/cyberpanel.net.ini"

                if not os.path.exists("/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/"):
                    command = 'sudo mkdir -p /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains'
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)



                finalPath = "/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/domains/" + domain + ".ini"

                if not os.path.exists(finalPath):
                    command = 'sudo cp '+path +" "+finalPath

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                command = 'sudo chown -R nobody:nobody /usr/local/lscp/rainloop'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                command = 'sudo chown -R nobody:nobody /usr/local/lscp/cyberpanel/rainloop/data/_data_'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                command = 'sudo chown -R vmail:vmail /home/vmail'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)



                finalEmailUsername = userName+"@"+domain


                website = Websites.objects.get(domain=domain)


                if EUsers.objects.filter(email=finalEmailUsername).exists():
                    data_ret = {'createEmailStatus': 0, 'error_message': "This account already exists"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


                if not Domains.objects.filter(domain=domain).exists():
                    newEmailDomain = Domains(domainOwner=website,domain=domain)
                    newEmailDomain.save()

                    emailAcct = EUsers(emailOwner=newEmailDomain,email=finalEmailUsername,password=password)
                    emailAcct.save()

                    data_ret = {'createEmailStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

                else:
                    emailDomain = Domains.objects.get(domain=domain)
                    emailAcct = EUsers(emailOwner=emailDomain, email=finalEmailUsername, password=password)
                    emailAcct.save()

                    data_ret = {'createEmailStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)


        except BaseException,msg:
            data_ret = {'createEmailStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'createEmailStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def deleteEmailAccount(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = admin.websites_set.all()
            else:
                websites = Websites.objects.filter(admin=admin)

            websitesName = []

            for items in websites:
                websitesName.append(items.domain)

            return render(request, 'mailServer/deleteEmailAccount.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)



def getEmailsForDomain(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                domain = data['domain']

                domain = Domains.objects.get(domain=domain)

                emails = domain.eusers_set.all()

                if emails.count() == 0:
                    final_dic = {'fetchStatus': 0, 'error_message': "No email accounts exits"}

                    final_json = json.dumps(final_dic)

                    return HttpResponse(final_json)

                json_data = "["
                checker = 0

                for items in emails:
                    dic = {'email': items.email}

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'

                final_dic = {'fetchStatus': 1, 'error_message': "None", "data": json_data}

                final_json = json.dumps(final_dic)

                return HttpResponse(final_json)


        except BaseException,msg:
            data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'fetchStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def submitEmailDeletion(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':

                data = json.loads(request.body)
                email = data['email']

                email = EUsers(email=email)

                email.delete()

                data_ret = {'deleteEmailStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



        except BaseException,msg:
            data_ret = {'deleteEmailStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'deleteEmailStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)



#######


def changeEmailAccountPassword(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=request.session['userID'])

            if admin.type == 1:
                websites = admin.websites_set.all()
            else:
                websites = Websites.objects.filter(admin=admin)

            websitesName = []

            for items in websites:
                websitesName.append(items.domain)

            return render(request, 'mailServer/changeEmailPassword.html', {'websiteList':websitesName})
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)


def submitPasswordChange(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)

                domain = data['domain']
                email = data['email']
                password = data['password']

                dom = Domains(domain=domain)

                emailAcct = EUsers(email=email)
                emailAcct.delete()

                emailAcct = EUsers(emailOwner=dom, email=email, password=password)
                emailAcct.save()

                data_ret = {'passChangeStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)



        except BaseException,msg:
            data_ret = {'passChangeStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except KeyError,msg:
        data_ret = {'passChangeStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

