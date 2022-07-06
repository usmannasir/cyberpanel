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

### Version

VERSION = '2.3'
BUILD = 2

def serverStatusHome(request):
    proc = httpProc(request, 'serverStatus/index.html',
                    None, 'admin')
    return proc.render()

def litespeedStatus(request):
    try:
        userID = request.session['userID']

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
            proc = httpProc(request, 'serverStatus/litespeedStatus.html',
                            {"processList": processList,
                             "liteSpeedVersionStatus": "For some reaons not able to load version details, see CyberCP main log file.",
                             'OLS': OLS, 'message': message}, 'admin')
            return proc.render()
        if (processList != 0):
            dataForHtml = {"processList": processList, "lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules, 'OLS': OLS, 'message': message}
            proc = httpProc(request, 'serverStatus/litespeedStatus.html', dataForHtml, 'admin')
            return proc.render()
        else:
            dataForHtml = {"lsversion": lsversion, "modules": modules,
                           "loadedModules": loadedModules, 'OLS': OLS, 'message': message}
            proc = httpProc(request, 'serverStatus/litespeedStatus.html', dataForHtml, 'admin')
            return proc.render()

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
    proc = httpProc(request, 'serverStatus/cybercpmainlogfile.html', None, 'admin')
    return proc.render()

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

    proc = httpProc(request, 'serverStatus/services.html', data, 'admin')
    return proc.render()

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

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos:

            mysqlResult = ProcessUtilities.outputExecutioner('systemctl status mysql')

            if mysqlResult.find('active (running)') > -1:
                sqlStatus.append(1)
                sqlStatus.append(getMemStats('mariadbd'))
            else:
                sqlStatus.append(0)
                sqlStatus.append(0)


        else:
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

            if serial.find('No such file or directory') > -1:
                final_dic = {'status': 1, "erroMessage": 0, 'lsSerial': 'Trial License in use.', 'lsexpiration': 'Trial license expires 15 days after activation.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

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

def refreshLicense(request):
    try:
        userID = request.session['userID']

        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('status', 0)


            command = 'sudo /usr/local/lsws/bin/lshttpd -V'
            ProcessUtilities.outputExecutioner(command)

            installUtilities.reStartLiteSpeed()

            final_dic = {'status': 1}
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
    proc = httpProc(request, "serverStatus/topProcesses.html", None, 'admin')
    return proc.render()

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

        memoryInf0 = ProcessUtilities.outputExecutioner('free -m').splitlines()

        memoryInf0[1] = list(filter(None, memoryInf0[1].split(' ')))
        memoryInf0[2] = list(filter(None, memoryInf0[2].split(' ')))


        try:
            data['totalMemory'] = '%sMB' % (memoryInf0[1][1])
        except:
            data['totalMemory'] = '%sMB' % ('0')
        try:
            data['usedMemory'] = '%sMB' % (memoryInf0[1][2])
        except:
            data['usedMemory'] = '%sMB' % ('0')

        try:
            data['freeMemory'] = '%sMB' % (memoryInf0[1][3])
        except:
            data['freeMemory'] = '%sMB' % ('0')

        try:
            data['buffCache'] = '%sMB' % (memoryInf0[1][5])
        except:
            data['buffCache'] = '%sMB' % ('0')


        ## Swap

        try:
            data['swapTotalMemory'] = '%sMB' % (memoryInf0[2][1])
        except:
            data['swapTotalMemory'] = '%sMB' % ('0')

        try:
            data['swapUsedMemory'] = '%sMB' % (memoryInf0[2][2])
        except:
            data['swapUsedMemory'] = '%sMB' % ('0')

        try:
            data['swapFreeMemory'] = '%sMB' % (memoryInf0[2][3])
        except:
            data['swapFreeMemory'] = '%sMB' % ('0')

        try:
            data['swapBuffCache'] = '%sMB' % (memoryInf0[2][5])
        except:
            data['swapBuffCache'] = '%sMB' % ('0')

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

        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        data['ipAddress'] = ipAddress
        data['CyberPanelVersion'] = 'v%s.%s' % (VERSION, str(BUILD))

        if ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            data['OS'] = 'Centos 8'
        elif ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
            data['OS'] = 'Ubuntu 20.04'
        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos:
            data['OS'] = 'Centos 7'
        elif ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
            data['OS'] = 'Ubuntu 18.04'

        data['Kernel'] = ProcessUtilities.outputExecutioner('uname -r')

        import shutil

        total, used, free = shutil.disk_usage("/")

        data['TotalDisk'] = '%s GB' % (total // (2 ** 30))
        data['TotalDiskUsed'] = '%s GB' %  (used // (2 ** 30))
        data['TotalDiskFree'] =' %s GB' %  (free // (2 ** 30))

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

def packageManager(request):
    proc = httpProc(request, "serverStatus/packageManager.html", None, 'admin')
    return proc.render()

def fetchPackages(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        data = json.loads(request.body)
        page = int(str(data['page']).rstrip('\n'))
        recordsToShow = int(data['recordsToShow'])
        type = data['type']

        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

            command = 'apt-mark showhold'
            locked = ProcessUtilities.outputExecutioner(command).split('\n')

            if type == 'CyberPanel':

                command = 'cat /usr/local/CyberCP/AllCPUbuntu.json'
                packages = json.loads(ProcessUtilities.outputExecutioner(command))

            else:
                command = 'apt list --installed'
                packages = ProcessUtilities.outputExecutioner(command).split('\n')
                packages = packages[4:]

                upgradePackages = []

                if type == 'upgrade':
                    for pack in packages:
                        if pack.find('upgradable') > -1:
                            upgradePackages.append(pack)

                    packages = upgradePackages


        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

            ### Check Package Lock status

            if os.path.exists('/etc/yum.conf'):
                yumConf = '/etc/yum.conf'
            elif os.path.exists('/etc/yum/yum.conf'):
                yumConf = '/etc/yum/yum.conf'

            yumConfData = open(yumConf, 'r').read()
            locked = []

            if yumConfData.find('exclude') > -1:

                data = open(yumConf, 'r').readlines()

                for items in data:
                    if items.find('exclude') > -1:
                        locked = items.split('=')[1].rstrip('\n').split(' ')
                        break

            if type == 'installed':

                #### Cater for packages that need updates.

                startForUpdate = 1

                command = 'yum check-update'
                updates = ProcessUtilities.outputExecutioner(command).split('\n')

                for items in updates:
                    if items == '':
                        updates = updates[startForUpdate:]
                        break
                    else:
                        startForUpdate = startForUpdate + 1

                ## make list of packages that need update

                updateNeeded = []
                for items in updates:
                    updateNeeded.append(items.split(' ')[0])

                ###

                command = 'yum list installed'
                packages = ProcessUtilities.outputExecutioner(command).split('\n')

                startFrom = 1

                for items in packages:
                    if items.find('Installed Packages') > -1:
                        packages = packages[startFrom:]
                        break
                    else:
                        startFrom = startFrom + 1
            elif type == 'upgrade':
                #### Cater for packages that need updates.

                startForUpdate = 1

                command = 'yum check-update'
                packages = ProcessUtilities.outputExecutioner(command).split('\n')

                for items in packages:
                    if items == '':
                        packages = packages[startForUpdate:-1]
                        break
                    else:
                        startForUpdate = startForUpdate + 1
            elif type == 'CyberPanel':
                command = 'cat /usr/local/CyberCP/CPCent7repo.json'
                packages = json.loads(ProcessUtilities.outputExecutioner(command))

        ## make list of packages that need update


        #if os.path.exists(ProcessUtilities.debugPath):
        #    logging.CyberCPLogFileWriter.writeToFile('All packages: %s' % (str(packages)))

        from s3Backups.s3Backups import S3Backups

        pagination = S3Backups.getPagination(len(packages), recordsToShow)
        endPageNumber, finalPageNumber = S3Backups.recordsPointer(page, recordsToShow)
        finalPackages = packages[finalPageNumber:endPageNumber]

        json_data = "["
        checker = 0
        counter = 0

        if os.path.exists(ProcessUtilities.debugPath):
             logging.CyberCPLogFileWriter.writeToFile('Final packages: %s' % (str(finalPackages)))

        import re
        for items in finalPackages:
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
                try:
                    if type == 'CyberPanel':

                        packageName = items['Package'].split('/')[0]

                        if packageName in locked:
                            lock = 1
                        else:
                            lock = 0

                        dic = {'package': packageName,
                               'version': items['Version'], 'lock': lock}

                        counter = counter + 1
                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)

                    else:
                        nowSplitted = items.split('now')

                        upgrade = 'Not Needed'

                        if nowSplitted[1].split(' ')[3].find('upgradable') > -1:
                            current = nowSplitted[1].split(' ')
                            upgrade = '%s %s %s' % (current[3], current[4], current[5])

                        if nowSplitted[0].split('/')[0] in locked:
                            lock = 1
                        else:
                            lock = 0

                        dic = {'package': nowSplitted[0].split('/')[0], 'version': '%s %s' % (nowSplitted[1].split(' ')[1], nowSplitted[1].split(' ')[2]), 'upgrade': upgrade, 'lock': lock}

                        counter = counter + 1
                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile('[ERROR] %s. [fetchPackages:773]' % (str(msg)))
            elif ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
                try:
                    if type == 'installed' or type == 'upgrade':

                        ###

                        details = items.split(' ')
                        details = [a for a in details if a != '']

                        if type == 'installed':
                            if details[0] in updateNeeded:
                                upgrade = 'Upgrade available'
                            else:
                                upgrade = 'Not needed.'
                        else:
                            upgrade = 'Upgrade available'


                        if details[0].split('.')[0] in locked:
                            lock = 1
                        else:
                            lock = 0

                        dic = {'package': details[0],
                               'version': details[1],
                               'upgrade': upgrade, 'lock': lock}

                        counter = counter + 1
                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)
                    elif type == 'CyberPanel':

                        packageName = items['Package']

                        if packageName.split('.')[0] in locked:
                            lock = 1
                        else:
                            lock = 0

                        dic = {'package': packageName,
                               'version': items['Version'], 'lock': lock}

                        counter = counter + 1
                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)


                except BaseException as msg:
                    print(str(msg))
                    logging.CyberCPLogFileWriter.writeToFile('[ERROR] %s. [fetchPackages:839]' % (str(msg)))

        json_data = json_data + ']'

        data_ret = {'status': 1, 'packages': json_data, 'pagination': pagination, 'fetchedPackages': counter, 'totalPackages': len(packages)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def fetchPackageDetails(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        data = json.loads(request.body)
        package = data['package']

        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:
            command = 'apt-cache show %s' % (package)
            packageDetails = ProcessUtilities.outputExecutioner(command)
        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            command = 'yum info %s' % (package)
            packageDetails = ProcessUtilities.outputExecutioner(command)

        data_ret = {'status': 1, 'packageDetails': packageDetails}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def updatePackage(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        data = json.loads(request.body)
        package = data['package']

        from serverStatus.serverStatusUtil import ServerStatusUtil

        logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                  'Starting package(s) upgrade..',
                                                  1)

        extraArgs = {}
        extraArgs['package'] = package

        from plogical.applicationInstaller import  ApplicationInstaller

        background = ApplicationInstaller('updatePackage', extraArgs)
        background.start()

        time.sleep(2)

        data_ret = {'status': 1}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def lockStatus(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        data = json.loads(request.body)
        package = data['package']
        type = data['type']

        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20:

            if type == 0:
                command = 'apt-mark unhold %s' % (package)
                ProcessUtilities.executioner(command)
            else:
                command = 'apt-mark hold %s' % (package)
                ProcessUtilities.executioner(command)

        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:

            package = package.split('.')[0]

            if os.path.exists('/etc/yum.conf'):
                yumConf = '/etc/yum.conf'
            elif os.path.exists('/etc/yum/yum.conf'):
                yumConf = '/etc/yum/yum.conf'

            yumConfData = ProcessUtilities.outputExecutioner('cat %s' % (yumConf))
            data = yumConfData.splitlines()

            yumConfTmp = '/home/cyberpanel/yumTemp'

            if type == 0:
                writeToFile = open(yumConfTmp, 'w')

                for items in data:
                    if items.find('exclude') > -1:
                        writeToFile.writelines(items.replace(package, ''))
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()
            else:

                if yumConfData.find('exclude') == -1:

                    writeToFile = open(yumConfTmp, 'a')
                    writeToFile.writelines('exclude=%s\n' % (package))
                    writeToFile.close()

                else:
                    writeToFile = open(yumConfTmp, 'w')

                    for items in data:
                        if items.find('exclude') > -1:
                            excludeLine = items.strip('\n')
                            writeToFile.writelines('%s %s\n' % (excludeLine, package))
                        else:
                            writeToFile.writelines(items)

                    writeToFile.close()

            command = 'mv %s %s' % (yumConfTmp, yumConf)
            ProcessUtilities.executioner(command)

        data_ret = {'status': 1}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def CyberPanelPort(request):
    port = ProcessUtilities.fetchCurrentPort()
    proc = httpProc(request, "serverStatus/changeCyberPanelPort.html", {'port': port}, 'admin')
    return proc.render()


def submitPortChange(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        data = json.loads(request.body)
        port = data['port']

        ## First Add Port to available firewall
        from plogical.firewallUtilities import FirewallUtilities
        from firewall.firewallManager import FirewallManager
        from firewall.models import FirewallRules

        csfPath = '/etc/csf'

        if os.path.exists(csfPath):
            fm = FirewallManager(request)
            dataIn = {'protocol': 'TCP_IN', 'ports': port}
            fm.modifyPorts(dataIn)
            dataIn = {'protocol': 'TCP_OUT', 'ports': port}
            fm.modifyPorts(dataIn)
        else:
            try:
                updateFW = FirewallRules.objects.get(name="CPCustomPort")
                FirewallUtilities.deleteRule("tcp", updateFW.port, "0.0.0.0/0")
                updateFW.port = port
                updateFW.save()
                FirewallUtilities.addRule('tcp', port, "0.0.0.0/0")
            except:
                try:
                    newFireWallRule = FirewallRules(name="SSHCustom", port=port, proto="tcp")
                    newFireWallRule.save()
                    FirewallUtilities.addRule('tcp', port, "0.0.0.0/0")
                    command = 'firewall-cmd --permanent --remove-service=ssh'
                    ProcessUtilities.executioner(command)
                except BaseException as msg:
                    logging.CyberCPLogFileWriter.writeToFile(str(msg))

        command = "echo '*:%s' > /usr/local/lscp/conf/bind.conf" % (port)
        ProcessUtilities.executioner(command)

        ProcessUtilities.executioner('systemctl restart lscpd')

        data_ret = {'status': 1,}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)