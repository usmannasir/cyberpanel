# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from loginSystem.views import loadLoginPage
from django.http import HttpResponse
import json
import plogical.CyberCPLogFileWriter as logging
from plogical.installUtilities import installUtilities
from loginSystem.models import Administrator
import subprocess
import shlex
from plogical.virtualHostUtilities import virtualHostUtilities
# Create your views here.


def logsHome(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

    except KeyError:
        return redirect(loadLoginPage)

    return render(request,'serverLogs/index.html')


def accessLogs(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)
        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        return render(request,'serverLogs/accessLogs.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[accessLogs]")
        return redirect(loadLoginPage)


def errorLogs(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")


        return render(request,'serverLogs/errorLogs.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[accessLogs]")
        return redirect(loadLoginPage)

def ftplogs(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")


        return render(request,'serverLogs/ftplogs.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[accessLogs]")
        return redirect(loadLoginPage)

def emailLogs(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")


        return render(request,'serverLogs/emailLogs.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[accessLogs]")
        return redirect(loadLoginPage)

def modSecAuditLogs(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")


        return render(request,'serverLogs/modSecAuditLog.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[accessLogs]")
        return redirect(loadLoginPage)


def getLogsFromFile(request):
    try:
        val = request.session['userID']

        admin = Administrator.objects.get(id=val)

        if admin.type == 1:
            data = json.loads(request.body)
            type = data['type']

            if type=="access":
                fileName = installUtilities.Server_root_path+"/logs/access.log"
            elif type=="error":
                fileName = installUtilities.Server_root_path + "/logs/error.log"
            elif type=="email":
                fileName="/var/log/maillog"
            elif type=="ftp":
                fileName="/var/log/messages"
            elif type == "modSec":
                fileName = "/usr/local/lsws/logs/auditmodsec.log"


            command = "sudo tail -50 " + fileName

            fewLinesOfLogFile = subprocess.check_output(shlex.split(command))

            status = {"logstatus":1,"logsdata":fewLinesOfLogFile}
            final_json = json.dumps(status)
            return HttpResponse(final_json)

        else:
            status = {"logstatus": 0, 'error': "You don't have enough privileges to access this page."}
            final_json = json.dumps(status)
            return HttpResponse(final_json)


    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getLogsFromFile]")
        return HttpResponse("Not Logged in as admin")

def clearLogFile(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if admin.type == 1:
                if request.method == 'POST':

                    data = json.loads(request.body)

                    fileName = data['fileName']

                    execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/serverLogs.py"

                    execPath = execPath + " cleanLogFile --fileName " + fileName

                    output = subprocess.check_output(shlex.split(execPath))

                    if output.find("1,None") > -1:
                        data_ret = {'cleanStatus': 1, 'error_message': "None"}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
                    else:
                        data_ret = {'cleanStatus': 0, 'error_message': output}
                        json_data = json.dumps(data_ret)
                        return HttpResponse(json_data)
            else:
                data_ret = {'cleanStatus': 0, 'error_message': 'Not enough privileges.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            data_ret = {'cleanStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'cleanStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)