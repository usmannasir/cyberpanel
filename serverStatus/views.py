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
        status = {"reboot": 0, "shutdown": 0, "error_message": "Not logged in as admin"}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[stopOrRestartLitespeed]")
        return HttpResponse("Not Logged in as admin")



def cyberCPMainLogFile(request):

    try:
        val = request.session['userID']

        admin = Administrator.objects.get(pk=val)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")


        return render(request,'serverStatus/cybercpmainlogfile.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[cyberCPMainLogFile]")
        return redirect(loadLoginPage)




def getFurtherDataFromLogFile(request):
    try:
        val = request.session['userID']

        fewLinesOfLogFile = logging.CyberCPLogFileWriter.readLastNFiles(50,logging.CyberCPLogFileWriter.fileName)

        fewLinesOfLogFile = str(fewLinesOfLogFile)


        status = {"logstatus":1,"logsdata":fewLinesOfLogFile}

        final_json = json.dumps(status)
        return HttpResponse(final_json)



    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getFurtherDataFromLogFile]")
        return HttpResponse("Not Logged in as admin")