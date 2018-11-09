# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render,redirect
from django.http import HttpResponse
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import json
import subprocess
import psutil
import shlex
import socket
from plogical.acl import ACLManager
import os
from plogical.virtualHostUtilities import virtualHostUtilities
import time
import serverStatusUtil
from plogical.processUtilities import ProcessUtilities
# Create your views here.

def serverStatusHome(request):
    try:
        userID = request.session['userID']
        return render(request,'serverStatus/index.html')
    except KeyError:
        return redirect(loadLoginPage)

def litespeedStatus(request):

    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        processList = ProcessUtilities.getLitespeedProcessNumber()

        OLS = 0
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            OLS = 1
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
            return render(request,"serverStatus/litespeedStatus.html",{"processList":processList,"liteSpeedVersionStatus":"For some reaons not able to load version details, see CyberCP main log file.", 'OLS': OLS})


        if(processList!=0):
            dataForHtml = {"processList": processList, "lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules, 'OLS':OLS}
            return render(request,"serverStatus/litespeedStatus.html",dataForHtml)
        else:
            dataForHtml = {"lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules, 'OLS': OLS}
            return render(request, "serverStatus/litespeedStatus.html",dataForHtml)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[litespeedStatus]")
        return redirect(loadLoginPage)

def stopOrRestartLitespeed(request):
    try:
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('reboot', 0)

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
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()


        return render(request,'serverStatus/cybercpmainlogfile.html')

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[cyberCPMainLogFile]")
        return redirect(loadLoginPage)

def getFurtherDataFromLogFile(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('logstatus', 0)

        fewLinesOfLogFile = logging.CyberCPLogFileWriter.readLastNFiles(50, logging.CyberCPLogFileWriter.fileName)
        fewLinesOfLogFile = str(fewLinesOfLogFile)
        status = {"logstatus": 1, "logsdata": fewLinesOfLogFile}
        final_json = json.dumps(status)
        return HttpResponse(final_json)

    except KeyError, msg:
        status = {"logstatus":0,"error":"Could not fetch data from log file, please see CyberCP main log file through command line."}
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[getFurtherDataFromLogFile]")
        return HttpResponse("Not Logged in as admin")

def services(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()
        data = {}

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            data['serverName'] = 'OpenLiteSpeed'
        else:
            data['serverName'] = 'LiteSpeed Ent'

        return render(request, 'serverStatus/services.html', data)
    except KeyError:
        return redirect(loadLoginPage)

def servicesStatus(request):
    try:
        userID = request.session['userID']

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
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('serviceAction', 0)

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
                    if service == 'pure-ftpd':
                        if os.path.exists("/etc/lsb-release"):
                            service = 'pure-ftpd-mysql'
                        else:
                            service = 'pure-ftpd'

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

def switchTOLSWS(request):
    try:
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('status', 0)

        data = json.loads(request.body)

        execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/serverStatus/serverStatusUtil.py"
        execPath = execPath + " switchTOLSWS --licenseKey " + data['licenseKey']

        subprocess.Popen(shlex.split(execPath))
        time.sleep(2)

        data_ret = {'status': 1, 'error_message': "None", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def switchTOLSWSStatus(request):
    try:

        command = 'sudo cat ' + serverStatusUtil.ServerStatusUtil.lswsInstallStatusPath
        output = subprocess.check_output(shlex.split(command))

        if output.find('[404]') > -1:
            data_ret = {'abort': 1, 'requestStatus': output, 'installed': 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        elif output.find('[200]') > -1:
            data_ret = {'abort': 1, 'requestStatus': output, 'installed': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        else:
            data_ret = {'abort': 0, 'requestStatus': output, 'installed': 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException, msg:
        data_ret = {'abort': 1, 'requestStatus': str(msg), 'installed': 0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def licenseStatus(request):
    try:
        userID = request.session['userID']

        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            command = 'sudo cat /usr/local/lsws/conf/serial.no'
            serial = subprocess.check_output(shlex.split(command))


            command = 'sudo /usr/local/lsws/bin/lshttpd -V'
            expiration = subprocess.check_output(shlex.split(command))

            final_dic = {'status': 1, "erroMessage": 0, 'lsSerial': serial, 'lsexpiration': expiration}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'status': 0, 'erroMessage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError, msg:
        final_dic = {'status': 0, 'erroMessage': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def changeLicense(request):
    try:
        userID = request.session['userID']

        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            data = json.loads(request.body)
            newKey = data['newKey']

            command = 'sudo chown -R cyberpanel:cyberpanel /usr/local/lsws/conf'
            subprocess.call(shlex.split(command))

            serialPath = '/usr/local/lsws/conf/serial.no'
            serialFile = open(serialPath, 'w')
            serialFile.write(newKey)
            serialFile.close()

            command = 'sudo chown -R lsadm:lsadm /usr/local/lsws/conf'
            subprocess.call(shlex.split(command))


            command = 'sudo /usr/local/lsws/bin/lshttpd -r'
            subprocess.call(shlex.split(command))

            command = 'sudo /usr/local/lsws/bin/lswsctrl restart'
            subprocess.call(shlex.split(command))


            final_dic = {'status': 1, "erroMessage": 'None'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'status': 0, 'erroMessage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError, msg:
        final_dic = {'status': 0, 'erroMessage': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)