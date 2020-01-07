# -*- coding: utf-8 -*-

from django.shortcuts import redirect, HttpResponse
from loginSystem.views import loadLoginPage
from plogical.acl import ACLManager
from .CLManagerMain import CLManagerMain
import json
from websiteFunctions.models import Websites
from plogical.processUtilities import ProcessUtilities
import os
from packages.models import Package
from .models import CLPackages
import subprocess
import multiprocessing
import pwd
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
# Create your views here.

def CageFS(request):
    try:
        templateName = 'CLManager/listWebsites.html'
        c = CLManagerMain(request, templateName)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

def submitCageFSInstall(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        c = CLManagerMain(request, None, 'submitCageFSInstall')
        c.start()

        data_ret = {'status': 1, 'error_message': 'None'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def getFurtherAccounts(request):
    try:
        userID = request.session['userID']
        wm = CLManagerMain()
        return wm.getFurtherAccounts(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def enableOrDisable(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)

        if data['toggle'] == 1:
            cageFSPath = '/home/cyberpanel/cagefs'
            if os.path.exists(cageFSPath):
                os.remove(cageFSPath)
            else:
                writeToFile = open(cageFSPath, 'w')
                writeToFile.writelines('enable')
                writeToFile.close()

            data_ret = {'status': 1, 'error_message': 'None', 'success': 'Default status successfully changed changed.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        if data['all'] == 0:
            if data['mode'] == 1:
                website = Websites.objects.get(domain=data['domain'])
                command = '/usr/sbin/cagefsctl --enable %s' % (website.externalApp)
            else:
                website = Websites.objects.get(domain=data['domain'])
                command = '/usr/sbin/cagefsctl --disable %s' % (website.externalApp)

            ProcessUtilities.executioner(command)
            data_ret = {'status': 1, 'error_message': 'None', 'success': 'Changes successfully applied.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
        else:
            c = CLManagerMain(request, None, 'enableOrDisable', data)
            c.start()

            data_ret = {'status': 1, 'error_message': 'None', 'success': 'Job started in background, refresh in few seconds to see the status.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)



    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def CreatePackage(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        templateName = 'CLManager/createPackage.html'
        packageList = ACLManager.loadPackages(userID, currentACL)
        data = {}
        data['packList'] = packageList
        c = CLManagerMain(request, templateName, None, data)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

def submitCreatePackage(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)

        selectedPackage = data['selectedPackage']

        package = Package.objects.get(packageName=selectedPackage)

        if package.clpackages_set.all().count() == 1:
            data_ret = {'status': 0, 'error_message': 'This package already have one associated CloudLinux Package.'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        name = data['name']
        SPEED = data['SPEED']
        VMEM = data['VMEM']
        PMEM = data['PMEM']
        IO = data['IO']
        IOPS = data['IOPS']
        EP = data['EP']
        NPROC = data['NPROC']
        INODESsoft = data['INODESsoft']
        INODEShard = data['INODEShard']

        clPackage = CLPackages(name=name, owner=package, speed=SPEED, vmem=VMEM, pmem=PMEM, io=IO, iops=IOPS, ep=EP, nproc=NPROC, inodessoft=INODESsoft, inodeshard=INODEShard)
        clPackage.save()

        command = 'sudo lvectl package-set %s --speed=%s --pmem=%s --io=%s --nproc=%s --iops=%s --vmem=%s --ep=%s' % (name, SPEED, PMEM, IO, NPROC, IOPS, VMEM, EP)
        ProcessUtilities.executioner(command)

        command = 'sudo lvectl apply all'
        ProcessUtilities.popenExecutioner(command)

        data_ret = {'status': 1}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def listPackages(request):
    try:
        templateName = 'CLManager/listPackages.html'
        c = CLManagerMain(request, templateName)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

def fetchPackages(request):
    try:
        userID = request.session['userID']
        wm = CLManagerMain()
        return wm.fetchPackages(ACLManager.loadedACL(userID))
    except KeyError:
        return redirect(loadLoginPage)

def deleteCLPackage(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)

        name = data['name']

        clPackage = CLPackages.objects.get(name=name)
        clPackage.delete()

        data_ret = {'status': 1}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def saveSettings(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        data = json.loads(request.body)

        name = data['name']
        SPEED = data['SPEED']
        VMEM = data['VMEM']
        PMEM = data['PMEM']
        IO = data['IO']
        IOPS = data['IOPS']
        EP = data['EP']
        NPROC = data['NPROC']
        INODESsoft = data['INODESsoft']
        INODEShard = data['INODEShard']

        clPackage = CLPackages.objects.get(name=name)
        clPackage.speed = SPEED
        clPackage.vmem = VMEM
        clPackage.pmem = PMEM
        clPackage.io = IO
        clPackage.iops = IOPS
        clPackage.ep = EP
        clPackage.nproc = NPROC
        clPackage.inodessoft = INODESsoft
        clPackage.inodeshard = INODEShard
        clPackage.save()

        command = 'sudo lvectl package-set %s --speed=%s --pmem=%s --io=%s --nproc=%s --iops=%s --vmem=%s --ep=%s' % (
        name, SPEED, PMEM, IO, NPROC, IOPS, VMEM, EP)
        ProcessUtilities.executioner(command)

        command = 'sudo lvectl apply all'
        ProcessUtilities.popenExecutioner(command)

        data_ret = {'status': 1}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def monitorUsage(request):
    try:
        templateName = 'CLManager/monitorUsage.html'
        c = CLManagerMain(request, templateName)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

def websiteContainerLimit(request, domain):
    try:
        templateName = 'CLManager/websiteContainerLimit.html'
        data = {}
        data['domain'] = domain
        c = CLManagerMain(request, templateName, None, data)
        return c.renderC()
    except KeyError:
        return redirect(loadLoginPage)

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
        uid = pwd.getpwnam(website.externalApp).pw_uid

        try:
            type = data['type']
            finalData = {}
            finalData['status'] = 1

            try:
                if type == 'memory':

                    command = 'sudo lveps -o id:10,mem:10'
                    output = ProcessUtilities.outputExecutioner(command).splitlines()
                    for items in output:
                        if items.find(website.externalApp) > -1:
                            finalData['memory'] = int(items.split(' ')[-1])
                            break

                elif type == 'io':

                    finalData['readRate'] = 0
                    finalData['writeRate'] = 0

                    command = 'sudo lveps -o id:10,iops:10'
                    output = ProcessUtilities.outputExecutioner(command).splitlines()
                    for items in output:
                        if items.find(website.externalApp) > -1:
                            finalData['readRate'] = int(items.split(' ')[-1])
                            break

            except:
                finalData['memory'] = '0'
                finalData['readRate'] = 0
                finalData['writeRate'] = 0
        except:

            finalData = {}
            finalData['status'] = 1

            command = 'sudo lveps -o id:10,cpu:10 -d'
            output = ProcessUtilities.outputExecutioner(command).splitlines()

            for items in output:
                if items.find(website.externalApp) > -1:
                    finalData['cpu'] = int(items.split(' ')[-1].rstrip('%'))
                    break

        final_json = json.dumps(finalData)
        return HttpResponse(final_json)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg), 'cpu': 0, 'memory':0}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)