# -*- coding: utf-8 -*-


from django.shortcuts import HttpResponse, redirect
from loginSystem.views import loadLoginPage
from .containerManager import ContainerManager
import json
from websiteFunctions.models import Websites
from .models import ContainerLimits
from random import randint
from plogical.processUtilities import ProcessUtilities
import os
import subprocess
import multiprocessing
from plogical.httpProc import httpProc
from plogical.acl import ACLManager
# Create your views here.

def cHome(request):
    try:
        templateName = 'containerization/listWebsites.html'
        c = ContainerManager(request, templateName)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

def submitContainerInstall(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        c = ContainerManager(request, None, 'submitContainerInstall')
        c.start()

        data_ret = {'status': 1, 'error_message': 'None'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def websiteContainerLimit(request, domain):
    try:
        templateName = 'containerization/websiteContainerLimit.html'
        data = {}
        data['domain'] = domain
        c = ContainerManager(request, templateName, None, data)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

def fetchWebsiteLimits(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)
        domain = data['domain']
        website = Websites.objects.get(domain=domain)

        try:
            websiteLimits = ContainerLimits.objects.get(owner=website)
        except:
            confPathTemp = "/home/cyberpanel/" + str(randint(1000, 9999))
            confPath = '/etc/cgconfig.d/' + domain
            count = ContainerLimits.objects.all().count() + 1
            hexValue = ContainerManager.fetchHexValue(count)
            cfs_quota_us = multiprocessing.cpu_count() * 10000
            finalContent = ContainerManager.prepConf(website.externalApp, str(cfs_quota_us), str(100000), str(356), 1, 1024, hexValue)

            if finalContent == 0:
                return httpProc.AJAX(0, 'Please check CyberPanel main log file.')


            writeToFile = open(confPathTemp, 'w')
            writeToFile.write(finalContent)
            writeToFile.close()

            command = 'sudo mv ' + confPathTemp + ' ' + confPath
            ProcessUtilities.executioner(command)

            try:
                os.remove(confPathTemp)
            except:
                pass

            websiteLimits = ContainerLimits(owner=website, cpuPers='10', IO='1', IOPS='1024', memory='300', networkSpeed='1mbit', networkHexValue=hexValue)
            websiteLimits.save()

        finalData = {}
        finalData['status'] = 1
        finalData['cpuPers'] = int(websiteLimits.cpuPers)
        finalData['IO'] = int(websiteLimits.IO)
        finalData['IOPS'] = int(websiteLimits.IOPS)
        finalData['memory'] = int(websiteLimits.memory)
        finalData['networkSpeed'] = websiteLimits.networkSpeed

        if websiteLimits.enforce == 1:
            finalData['enforce'] = 1
        else:
            finalData['enforce'] = 0

        json_data = json.dumps(finalData)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def saveWebsiteLimits(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)
        domain = data['domain']
        cpuPers = data['cpuPers']
        IO = data['IO']
        IOPS = data['IOPS']
        memory = data['memory']
        networkSpeed = data['networkSpeed']
        networkHandle = data['networkHandle']

        try:
            enforce = data['enforce']
        except:
            enforce = False

        if cpuPers > 100:
            return httpProc.AJAX(0, 'CPU Percentage can not be greater then 100%')

        website = Websites.objects.get(domain=domain)
        websiteLimits = ContainerLimits.objects.get(owner=website)


        if enforce == True:
            if websiteLimits.enforce == 0:

                cgrulesTemp = "/home/cyberpanel/" + str(randint(1000, 9999))
                cgrules = '/etc/cgrules.conf'
                enforceString = '{}  cpu,memory,blkio,net_cls  {}/\n'.format(website.externalApp, website.externalApp)

                cgrulesData = ProcessUtilities.outputExecutioner('sudo cat /etc/cgrules.conf').splitlines()

                writeToFile = open(cgrulesTemp, 'w')

                for items in cgrulesData:
                    writeToFile.writelines(items + '\n')

                writeToFile.writelines(enforceString)
                writeToFile.close()

                command = 'sudo mv ' + cgrulesTemp + ' ' + cgrules
                ProcessUtilities.executioner(command)

                try:
                    os.remove(cgrulesTemp)
                except:
                    pass

            websiteLimits.enforce = 1

            ## Main Conf File

            confPathTemp = "/home/cyberpanel/" + str(randint(1000, 9999))
            confPath = '/etc/cgconfig.d/' + domain
            cfs_quota_us = multiprocessing.cpu_count() * 1000
            finalContent = ContainerManager.prepConf(website.externalApp, str(cpuPers * cfs_quota_us), str(100000),
                                                     str(memory), IO, IOPS, websiteLimits.networkHexValue)

            if finalContent == 0:
                return httpProc.AJAX(0, 'Please check CyberPanel main log file.')

            writeToFile = open(confPathTemp, 'w')
            writeToFile.write(finalContent)
            writeToFile.close()

            command = 'sudo mv ' + confPathTemp + ' ' + confPath
            ProcessUtilities.executioner(command)

            try:
                os.remove(confPathTemp)
            except:
                pass

            ## Add Traffic Control / Restart Services

            additionalArgs = {}
            additionalArgs['classID'] = websiteLimits.id
            additionalArgs['rateLimit'] = str(networkSpeed) + networkHandle

            c = ContainerManager(None, None, 'addTrafficController', additionalArgs)
            c.start()
        else:
            websiteLimits.enforce = 0

            cgrulesTemp = "/home/cyberpanel/" + str(randint(1000, 9999))
            cgrules = '/etc/cgrules.conf'

            cgrulesData = ProcessUtilities.outputExecutioner('sudo cat /etc/cgrules.conf').splitlines()

            writeToFile = open(cgrulesTemp, 'w')

            for items in cgrulesData:
                if items.find(website.externalApp) > -1:
                    continue
                writeToFile.writelines(items + '\n')

            writeToFile.close()

            command = 'sudo mv ' + cgrulesTemp + ' ' + cgrules
            ProcessUtilities.executioner(command)

            confPath = '/etc/cgconfig.d/' + domain

            command = 'sudo rm ' + confPath
            ProcessUtilities.executioner(command)

            ## Not needed, to be removed later

            additionalArgs = {}
            additionalArgs['classID'] = websiteLimits.id

            c = ContainerManager(None, None, 'removeLimits', additionalArgs)
            c.start()

            try:
                os.remove(cgrulesTemp)
            except:
                pass



        websiteLimits.cpuPers = str(cpuPers)
        websiteLimits.memory = str(memory)
        websiteLimits.IO = str(IO)
        websiteLimits.IOPS = str(IOPS)
        websiteLimits.networkSpeed = str(networkSpeed) + str(networkHandle)
        websiteLimits.save()

        finalData = {}
        finalData['status'] = 1
        json_data = json.dumps(finalData)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def getUsageData(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)
        domain = data['domain']
        website = Websites.objects.get(domain=domain)

        try:
            type = data['type']
            finalData = {}
            finalData['status'] = 1

            try:
                if type == 'memory':

                    command = 'sudo cat /sys/fs/cgroup/memory/' + website.externalApp + '/memory.usage_in_bytes'
                    output = str(ProcessUtilities.outputExecutioner(command))
                    finalData['memory'] = int(float(output)/float(1024 * 1024))

                elif type == 'io':

                    path = '/home/cyberpanel/' + website.externalApp
                    blkioPath = path + '/blkio'

                    if not os.path.exists(path):
                        os.mkdir(path)

                    command = 'sudo cat /sys/fs/cgroup/blkio/' + website.externalApp + '/blkio.throttle.io_service_bytes'
                    output = ProcessUtilities.outputExecutioner(command).splitlines()

                    readCurrent = output[0].split(' ')[2]
                    writeCurrent = output[1].split(' ')[2]

                    if os.path.exists(blkioPath):

                        old = open(blkioPath, 'r').read()
                        oldRead = float(old.split(',')[0])
                        oldWrite = float(old.split(',')[1])

                        finalData['readRate'] = int((float(readCurrent) - oldRead)/float(65536000))
                        finalData['writeRate'] = int((float(writeCurrent) - oldWrite) / float(65536000))

                    else:
                        finalData['readRate'] = 0
                        finalData['writeRate'] = 0

                    writeToFile = open(blkioPath, 'w')
                    writeToFile.write(readCurrent + ',' + writeCurrent)
                    writeToFile.close()

            except:
                finalData['memory'] = '0'
                finalData['readRate'] = 0
                finalData['writeRate'] = 0
        except:
            command = "top -b -n 1 -u " + website.externalApp + " | awk 'NR>7 { sum += $9; } END { print sum; }'"
            output = str(subprocess.check_output(command, shell=True).decode("utf-8"))

            finalData = {}
            finalData['status'] = 1
            if len(output) == 0:
                finalData['cpu'] = '0'
            else:
                finalData['cpu'] = str(float(output)/float(multiprocessing.cpu_count()))

        final_json = json.dumps(finalData)
        return HttpResponse(final_json)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg), 'cpu': 0, 'memory':0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)