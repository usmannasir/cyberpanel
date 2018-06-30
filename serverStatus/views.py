# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
from plogical.processUtilities import ProcessUtilities
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import json
import subprocess
from loginSystem.models import Administrator
import psutil
import shlex
import socket
# Create your views here.


def serverStatusHome(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")


        return render(request,'serverStatus/index.html')
    except KeyError:
        return redirect(loadLoginPage)

def litespeedStatus(request):

    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        processList = ProcessUtilities.getLitespeedProcessNumber()

        try:

            versionInformation = subprocess.check_output(["/usr/local/lsws/bin/lshttpd", "-v"]).split("\n")
            lsversion = versionInformation[0]
            modules = versionInformation[1]

            counter = 0
            loadedModules = []

            for items in versionInformation:
                if counter == 0 or counter == 1:
                    counter = counter + 1
                    continue
                else:
                    loadedModules.append(items)

        except subprocess.CalledProcessError,msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[litespeedStatus]")
            return render(request,"serverStatus/litespeedStatus.html",{"processList":processList,"liteSpeedVersionStatus":"For some reaons not able to load version details, see CyberCP main log file."})


        if(processList!=0):
            dataForHtml = {"processList": processList, "lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules}
            return render(request,"serverStatus/litespeedStatus.html",dataForHtml)
        else:
            dataForHtml = {"lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules}
            return render(request, "serverStatus/litespeedStatus.html",dataForHtml)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[litespeedStatus]")
        return redirect(loadLoginPage)



def stopOrRestartLitespeed(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        data = json.loads(request.body)

        reboot = data['reboot']

        if reboot==1:
            if ProcessUtilities.restartLitespeed() == 1:
                status = {"reboot":1,"shutdown":0}
            else:
                status = {"reboot": 0, "shutdown": 0, "error_message":"Please see CyberCP main log file."}
        else:
            if ProcessUtilities.stopLitespeed() == 1:
                status = {"reboot":0,"shutdown":1}
            else:
                status = {"reboot": 0, "shutdown": 0, "error_message":"Please see CyberCP main log file."}

        final_json = json.dumps(status)
        return HttpResponse(final_json)

    except KeyError, msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[stopOrRestartLitespeed]")
        return HttpResponse("Not Logged in as admin")



def cyberCPMainLogFile(request):

    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")


        return render(request,'serverStatus/cybercpmainlogfile.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[cyberCPMainLogFile]")
        return redirect(loadLoginPage)


def getFurtherDataFromLogFile(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)

        if admin.type == 1:

            fewLinesOfLogFile = logging.CyberCPLogFileWriter.readLastNFiles(50,logging.CyberCPLogFileWriter.fileName)
            fewLinesOfLogFile = str(fewLinesOfLogFile)
            status = {"logstatus": 1, "logsdata": fewLinesOfLogFile}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

        else:
            status = {"logstatus": 0,'error':"You don't have enough privilege to view logs."}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getFurtherDataFromLogFile]")
        return HttpResponse("Not Logged in as admin")


def services(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        return render(request, 'serverStatus/services.html')
    except KeyError:
        return redirect(loadLoginPage)


def servicesStatus(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            final = {'error': 1, "error_message": "Not enough privilege"}
            final_json = json.dumps(final)
            return HttpResponse(final_json)

        lsStatus = []
        sqlStatus = []
        dnsStatus = []
        ftpStatus = []
        mailStatus = []

        processlist = subprocess.check_output(['ps', '-A'])

        def getServiceStats(service):
            if service in processlist:
                return 1
            else:
                return 0

        def getMemStats(service):
            memCount = 0
            for proc in psutil.process_iter():
                if service in proc.name():
                    process = psutil.Process(proc.pid)
                    memCount += process.memory_info().rss
            return memCount

        ### [1] status [2] mem
        lsStatus.append(getServiceStats('litespeed'))
        if getServiceStats('litespeed'):
            lsStatus.append(getMemStats('litespeed'))
        else:
            lsStatus.append(0)

        # mysql status

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = s.connect_ex(('127.0.0.1', 3306))

        if result == 0:
            sqlStatus.append(1)
        else:
            sqlStatus.append(0)
        s.close()

        if getServiceStats('mysql'):
            sqlStatus.append(getMemStats('mysql'))
        else:
            sqlStatus.append(0)

        dnsStatus.append(getServiceStats('pdns'))
        if getServiceStats('pdns'):
            dnsStatus.append(getMemStats('pdns'))
        else:
            dnsStatus.append(0)

        ftpStatus.append(getServiceStats('pure-ftpd'))
        if getServiceStats('pure-ftpd'):
            ftpStatus.append(getMemStats('pure-ftpd'))
        else:
            ftpStatus.append(0)

        mailStatus.append(getServiceStats('postfix'))
        if getServiceStats('postfix'):
            mailStatus.append(getMemStats('postfix'))
        else:
            mailStatus.append(0)

        json_data = {'status':
                         {'litespeed': lsStatus[0],
                          'mysql': sqlStatus[0],
                          'powerdns': dnsStatus[0],
                          'pureftp': ftpStatus[0],
                          'postfix': mailStatus[0]},
                     'memUsage':
                         {'litespeed': lsStatus[1],
                          'mysql': sqlStatus[1],
                          'powerdns': dnsStatus[1],
                          'pureftp': ftpStatus[1],
                          'postfix': mailStatus[1]}}

        return HttpResponse(json.dumps(json_data))
    except KeyError:
        return redirect(loadLoginPage)


def servicesAction(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            final = {'serviceAction': 0, "error_message": "Not enough privileges."}
            final_json = json.dumps(final)
            return HttpResponse(final_json)

        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                service = data['service']
                action = data['action']

                if action not in ["stop", "start", "restart"]:

                    final_dic = {'serviceAction': 0, "error_message": "Invalid Action"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    pass

                if service not in ["lsws", "mysql", "pdns", "pure-ftpd"]:

                    final_dic = {'serviceAction': 0, "error_message": "Invalid Service"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                else:

                    command = 'sudo systemctl %s %s' % (action, service)
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)

                    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
                    result = p.communicate()[0]

                    if res != 0:
                        final_dic = {'serviceAction': 0, "error_message": "Error while performing action"}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)
                    else:
                        final_dic = {'serviceAction': 1, "error_message": 0}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'serviceAction': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError, msg:
        final_dic = {'serviceAction': 0, 'error_message': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
