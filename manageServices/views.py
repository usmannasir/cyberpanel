# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render
from loginSystem.models import Administrator
from django.shortcuts import HttpResponse, redirect
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import os
import json
from plogical.mailUtilities import mailUtilities
import subprocess, shlex
# Create your views here.


# Create your views here.

def managePowerDNS(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                return render(request, 'manageServices/managePowerDNS.html', {"status": 1})
            else:
                return render(request, 'manageServices/managePowerDNS.html', {"status": 0})

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def managePostfix(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                return render(request, 'manageServices/managePostfix.html', {"status": 1})
            else:
                return render(request, 'manageServices/managePostfix.html', {"status": 0})

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def managePureFtpd(request):
    try:
        val = request.session['userID']
        try:
            admin = Administrator.objects.get(pk=val)

            if admin.type == 1:
                return render(request, 'manageServices/managePureFtpd.html', {"status": 1})
            else:
                return render(request, 'manageServices/managePureFtpd.html', {"status": 0})

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return HttpResponse("See CyberCP main log file.")

    except KeyError:
        return redirect(loadLoginPage)

def fetchStatus(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'status': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                mailUtilities.checkHome()

                data = json.loads(request.body)
                service = data['service']

                if service == 'powerdns':
                    if os.path.exists('/home/cyberpanel/powerdns'):
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 1}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 0}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                elif service == 'postfix':
                    if os.path.exists('/home/cyberpanel/postfix'):
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 1}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 0}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

                elif service == 'pureftpd':
                    if os.path.exists('/home/cyberpanel/pureftpd'):
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 1}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'status': 1, 'error_message': 'None', 'installCheck': 0}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def saveStatus(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    dic = {'status': 0, 'error_message': "Only administrator can view this page."}
                    json_data = json.dumps(dic)
                    return HttpResponse(json_data)

                data = json.loads(request.body)

                status = data['status']
                service = data['service']

                mailUtilities.checkHome()

                if service == 'powerdns':

                    servicePath = '/home/cyberpanel/powerdns'
                    if status == True:
                        writeToFile = open(servicePath, 'w+')
                        writeToFile.close()
                        command = 'sudo systemctl start pdns'
                        subprocess.call(shlex.split(command))


                    else:
                        command = 'sudo systemctl stop pdns'
                        subprocess.call(shlex.split(command))

                        command = 'sudo systemctl disable pdns'
                        subprocess.call(shlex.split(command))

                        try:
                            os.remove(servicePath)
                        except:
                            pass


                elif service == 'postfix':

                    servicePath = '/home/cyberpanel/postfix'
                    if status == True:
                        writeToFile = open(servicePath, 'w+')
                        writeToFile.close()
                        command = 'sudo systemctl start postfix'
                        subprocess.call(shlex.split(command))
                    else:
                        command = 'sudo systemctl stop postfix'
                        subprocess.call(shlex.split(command))

                        command = 'sudo systemctl disable postfix'
                        subprocess.call(shlex.split(command))

                        try:
                            os.remove(servicePath)
                        except:
                            pass

                elif service == 'pureftpd':

                    servicePath = '/home/cyberpanel/pureftpd'
                    if status == True:
                        writeToFile = open(servicePath, 'w+')
                        writeToFile.close()
                        command = 'sudo systemctl start pure-ftpd'
                        subprocess.call(shlex.split(command))
                    else:
                        command = 'sudo systemctl stop pure-ftpd'
                        subprocess.call(shlex.split(command))

                        command = 'sudo systemctl disable pure-ftpd'
                        subprocess.call(shlex.split(command))

                        try:
                            os.remove(servicePath)
                        except:
                            pass

                data_ret = {'status': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)


        except BaseException,msg:
            data_ret = {'status': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)