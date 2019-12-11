# -*- coding: utf-8 -*-


from django.shortcuts import render, redirect
from django.http import HttpResponse
import plogical.CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
import json
import subprocess
import psutil
import socket
from plogical.acl import ACLManager
import os
from plogical.virtualHostUtilities import virtualHostUtilities
import time
from . import serverStatusUtil
from plogical.processUtilities import ProcessUtilities
from plogical.httpProc import httpProc
from plogical.installUtilities import installUtilities


# Create your views here.

NOTHING = 0
BUNDLE = 2
EXPIRE = 3

def serverStatusHome(request):
    try:
        userID = request.session['userID']
        return render(request, 'serverStatus/index.html')
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

        message = 0

        if request.META['QUERY_STRING'] == 'bundle':
            message = ''
            message = BUNDLE
        elif request.META['QUERY_STRING'] == 'expire':
            message = 'It looks like your license has expired. Kindly renew your license.'
            message = EXPIRE
        else:
            message = NOTHING
        try:

            versionInformation = ProcessUtilities.outputExecutioner(["/usr/local/lsws/bin/lshttpd", "-v"]).split("\n")
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

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[litespeedStatus]")
            return render(request, "serverStatus/litespeedStatus.html", {"processList": processList,
                                                                         "liteSpeedVersionStatus": "For some reaons not able to load version details, see CyberCP main log file.",
                                                                         'OLS': OLS , 'message': message})
        if (processList != 0):
            dataForHtml = {"processList": processList, "lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules, 'OLS': OLS, 'message': message}
            return render(request, "serverStatus/litespeedStatus.html", dataForHtml)
        else:
            dataForHtml = {"lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules, 'OLS': OLS, 'message': message}
            return render(request, "serverStatus/litespeedStatus.html", dataForHtml)

    except KeyError as msg:
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

        if reboot == 1:
            if installUtilities.reStartLiteSpeedSocket() == 1:
                status = {"reboot": 1, "shutdown": 0}
            else:
                status = {"reboot": 0, "shutdown": 0, "error_message": "Please see CyberCP main log file."}
        else:
            if installUtilities.stopLiteSpeedSocket() == 1:
                status = {"reboot": 0, "shutdown": 1}
            else:
                status = {"reboot": 0, "shutdown": 0, "error_message": "Please see CyberCP main log file."}

        final_json = json.dumps(status)
        return HttpResponse(final_json)

    except KeyError as msg:
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

        return render(request, 'serverStatus/cybercpmainlogfile.html')

    except KeyError as msg:
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

    except KeyError as msg:
        status = {"logstatus": 0,
                  "error": "Could not fetch data from log file, please see CyberCP main log file through command line."}
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

        dockerInstallPath = '/usr/bin/docker'
        if not os.path.exists(dockerInstallPath):
            data['isDocker'] = False
        else:
            data['isDocker'] = True

        return render(request, 'serverStatus/services.html', data)
    except KeyError:
        return redirect(loadLoginPage)


def servicesStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('serviceAction', 0)

        lsStatus = []
        sqlStatus = []
        dnsStatus = []
        ftpStatus = []
        mailStatus = []
        dockerStatus = []

        processlist = ProcessUtilities.outputExecutioner('ps -A')

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

        # Docker status
        dockerStatus.append(getServiceStats('docker'))

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
                          'postfix': mailStatus[0],
                          'docker': dockerStatus[0]},
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

                if service not in ["lsws", "mysql", "pdns", "pure-ftpd", "docker"]:
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
                    ProcessUtilities.executioner(command)
                    final_dic = {'serviceAction': 1, "error_message": 0}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)


        except BaseException as msg:
            final_dic = {'serviceAction': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError as msg:
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

        try:
            licenseKey = data['licenseKey']
        except:
            licenseKey = 'trial'

        execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/serverStatus/serverStatusUtil.py"
        execPath = execPath + " switchTOLSWS --licenseKey " + licenseKey

        ProcessUtilities.popenExecutioner(execPath)
        time.sleep(2)

        data_ret = {'status': 1, 'error_message': "None", }
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def switchTOLSWSStatus(request):
    try:

        command = 'sudo cat ' + serverStatusUtil.ServerStatusUtil.lswsInstallStatusPath
        output = ProcessUtilities.outputExecutioner(command)

        if output.find('[404]') > -1:
            command = "sudo rm -f " + serverStatusUtil.ServerStatusUtil.lswsInstallStatusPath
            ProcessUtilities.popenExecutioner(command)
            data_ret = {'status': 1, 'abort': 1, 'requestStatus': output, 'installed': 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        elif output.find('[200]') > -1:
            command = "sudo rm -f " + serverStatusUtil.ServerStatusUtil.lswsInstallStatusPath
            ProcessUtilities.popenExecutioner(command)
            data_ret = {'status': 1, 'abort': 1, 'requestStatus': output, 'installed': 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        else:
            data_ret = {'status': 1, 'abort': 0, 'requestStatus': output, 'installed': 0}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except BaseException as msg:
        command = "sudo rm -f " + serverStatusUtil.ServerStatusUtil.lswsInstallStatusPath
        ProcessUtilities.popenExecutioner(command)
        data_ret = {'status': 0,'abort': 1, 'requestStatus': str(msg), 'installed': 0}
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
            serial = ProcessUtilities.outputExecutioner(command)

            command = 'sudo /usr/local/lsws/bin/lshttpd -V'
            expiration = ProcessUtilities.outputExecutioner(command)

            final_dic = {'status': 1, "erroMessage": 0, 'lsSerial': serial, 'lsexpiration': expiration}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'erroMessage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError as msg:
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
            ProcessUtilities.executioner(command)

            serialPath = '/usr/local/lsws/conf/serial.no'
            serialFile = open(serialPath, 'w')
            serialFile.write(newKey)
            serialFile.close()

            command = 'sudo chown -R lsadm:lsadm /usr/local/lsws/conf'
            ProcessUtilities.executioner(command)

            command = 'sudo /usr/local/lsws/bin/lshttpd -r'
            ProcessUtilities.executioner(command)

            command = 'sudo /usr/local/lsws/bin/lswsctrl restart'
            ProcessUtilities.executioner(command)

            final_dic = {'status': 1, "erroMessage": 'None'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'erroMessage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError as msg:
        final_dic = {'status': 0, 'erroMessage': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def topProcesses(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        templateName = "serverStatus/topProcesses.html"
        proc = httpProc(request, templateName)
        return proc.renderPre()

    except KeyError as msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[litespeedStatus]")
        return redirect(loadLoginPage)


def topProcessesStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        with open("/home/cyberpanel/top", "w") as outfile:
            subprocess.call("top -n1 -b", shell=True, stdout=outfile)

        data = open('/home/cyberpanel/top', 'r').readlines()

        json_data = "["
        checker = 0
        counter = 0

        loadAVG = data[0].split(' ')
        loadAVG = [a for a in loadAVG if a != '']

        loadNow = data[2].split(' ')
        loadNow = [a for a in loadNow if a != '']

        memory = data[3].split(' ')
        memory = [a for a in memory if a != '']

        swap = data[4].split(' ')
        swap = [a for a in swap if a != '']

        processes = data[1].split(' ')
        processes = [a for a in processes if a != '']

        for items in data:
            counter = counter + 1
            if counter <= 7:
                continue

            points = items.split(' ')
            points = [a for a in points if a != '']

            dic = {'PID': points[0], 'User': points[1], 'VIRT': points[4],
                   'RES': points[5], 'S': points[7], 'CPU': points[8], 'MEM': points[9],
                   'Time': points[10], 'Command': points[11]
                   }

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        data = {}
        data['status'] = 1
        data['error_message'] = 'None'
        data['data'] = json_data

        ## CPU
        data['cpuNow'] = loadNow[1]
        data['cpuOne'] = loadAVG[-3].rstrip(',')
        data['cpuFive'] = loadAVG[-2].rstrip(',')
        data['cpuFifteen'] = loadAVG[-1]

        ## CPU Time spent

        data['ioWait'] = loadNow[9] + '%'
        data['idleTime'] = loadNow[7] + '%'
        data['hwInterrupts'] = loadNow[11] + '%'
        data['Softirqs'] = loadNow[13] + '%'

        ## Memory
        data['totalMemory'] = str(int(float(memory[3]) / 1024)) + 'MB'
        data['freeMemory'] = str(int(float(memory[5]) / 1024)) + 'MB'
        data['usedMemory'] = str(int(float(memory[7]) / 1024)) + 'MB'
        data['buffCache'] = str(int(float(memory[9]) / 1024)) + 'MB'

        ## Swap

        data['swapTotalMemory'] = str(int(float(swap[2]) / 1024)) + 'MB'
        data['swapFreeMemory'] = str(int(float(swap[4]) / 1024)) + 'MB'
        data['swapUsedMemory'] = str(int(float(swap[6]) / 1024)) + 'MB'
        data['swapBuffCache'] = str(int(float(swap[8]) / 1024)) + 'MB'

        ## Processes

        data['totalProcesses'] = processes[1]
        data['runningProcesses'] = processes[3]
        data['sleepingProcesses'] = processes[5]
        data['stoppedProcesses'] = processes[7]
        data['zombieProcesses'] = processes[9]

        ## CPU Details

        command = 'sudo cat /proc/cpuinfo'
        output = ProcessUtilities.outputExecutioner(command).splitlines()

        import psutil

        data['cores'] = psutil.cpu_count()

        for items in output:
            if items.find('model name') > -1:
                modelName = items.split(':')[1].strip(' ')
                index = modelName.find('CPU')
                data['modelName'] = modelName[0:index]
            elif items.find('cpu MHz') > -1:
                data['cpuMHZ'] = items.split(':')[1].strip(' ')
            elif items.find('cache size') > -1:
                data['cacheSize'] = items.split(':')[1].strip(' ')
                break

        final_json = json.dumps(data)
        return HttpResponse(final_json)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def killProcess(request):
    try:
        userID = request.session['userID']

        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)

            data = json.loads(request.body)
            pid = data['pid']

            ProcessUtilities.executioner('sudo kill ' + pid)

            proc = httpProc(request, None)
            return proc.ajax(1, None)

        except BaseException as msg:
            final_dic = {'status': 0, 'erroMessage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError as msg:
        final_dic = {'status': 0, 'erroMessage': str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)