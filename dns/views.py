# -*- coding: utf-8 -*-
import time
from random import randint

from django.shortcuts import redirect, HttpResponse
from loginSystem.views import loadLoginPage
from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from plogical.processUtilities import ProcessUtilities
from .dnsManager import DNSManager
from .pluginManager import pluginManager
import json


# Create your views here.

def loadDNSHome(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.loadDNSHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def createNameserver(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.createNameserver(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def NSCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preNSCreation(request)
        if result != 200:
            return result

        dm = DNSManager()
        coreResult = dm.NSCreation(userID, json.loads(request.body))

        result = pluginManager.postNSCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def createDNSZone(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.createDNSZone(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def zoneCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preZoneCreation(request)
        if result != 200:
            return result

        dm = DNSManager()
        coreResult = dm.zoneCreation(userID, json.loads(request.body))

        result = pluginManager.postZoneCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def addDeleteDNSRecords(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.addDeleteDNSRecords(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def updateRecord(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.updateRecord(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def getCurrentRecordsForDomain(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.getCurrentRecordsForDomain(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def addDNSRecord(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preAddDNSRecord(request)
        if result != 200:
            return result

        dm = DNSManager()
        coreResult = dm.addDNSRecord(userID, json.loads(request.body))

        result = pluginManager.postAddDNSRecord(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def deleteDNSRecord(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preDeleteDNSRecord(request)
        if result != 200:
            return result

        dm = DNSManager()
        coreResult = dm.deleteDNSRecord(userID, json.loads(request.body))

        result = pluginManager.postDeleteDNSRecord(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def deleteDNSZone(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.deleteDNSZone(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def submitZoneDeletion(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preSubmitZoneDeletion(request)
        if result != 200:
            return result

        dm = DNSManager()
        coreResult = dm.submitZoneDeletion(userID, json.loads(request.body))

        result = pluginManager.postSubmitZoneDeletion(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def configureDefaultNameServers(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.configureDefaultNameServers(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def saveNSConfigurations(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.saveNSConfigurations(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def addDeleteDNSRecordsCloudFlare(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.addDeleteDNSRecordsCloudFlare(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def ResetDNSConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        proc = httpProc(request, 'dns/resetdnsconf.html')
        return proc.render()
    except KeyError:
        return redirect(loadLoginPage)


def resetDNSnow(request):
    try:
        from plogical.virtualHostUtilities import virtualHostUtilities
        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = json.loads(request.body)
        tempStatusPath = "/home/cyberpanel/" + str(randint(1000, 9999))

        execPath = f"/usr/local/CyberCP/bin/python /usr/local/CyberCP/dns/dnsManager.py ResetDNSConfigurations --tempStatusPath {tempStatusPath}"

        ProcessUtilities.popenExecutioner(execPath)
        time.sleep(2)

        data_ret = {'status': 1, 'error_message': "None",
                    'tempStatusPath': tempStatusPath}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)
    except KeyError:
        return redirect(loadLoginPage)


def getresetstatus(request):
    try:

        userID = request.session['userID']

        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        data = json.loads(request.body)
        statusfile = data['statusfile']
        installStatus = ProcessUtilities.outputExecutioner("sudo cat " + statusfile)

        if installStatus.find("[200]") > -1:

            command = 'sudo rm -f ' + statusfile
            ProcessUtilities.executioner(command)

            final_json = json.dumps({
                'error_message': "None",
                'requestStatus': installStatus,
                'abort': 1,
                'installed': 1,
            })
            return HttpResponse(final_json)
        elif installStatus.find("[404]") > -1:
            command = 'sudo rm -f ' + statusfile
            ProcessUtilities.executioner(command)
            final_json = json.dumps({
                'abort': 1,
                'installed': 0,
                'error_message': "None",
                'requestStatus': installStatus,
            })
            return HttpResponse(final_json)

        else:
            final_json = json.dumps({
                'abort': 0,
                'error_message': "None",
                'requestStatus': installStatus,
            })
            return HttpResponse(final_json)
    except KeyError:
        return redirect(loadLoginPage)


def saveCFConfigs(request):
    try:
        userID = request.session['userID']

        dm = DNSManager()
        coreResult = dm.saveCFConfigs(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def getCurrentRecordsForDomainCloudFlare(request):
    try:
        userID = request.session['userID']
        dm = DNSManager()
        return dm.getCurrentRecordsForDomainCloudFlare(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def deleteDNSRecordCloudFlare(request):
    try:
        userID = request.session['userID']

        dm = DNSManager()
        coreResult = dm.deleteDNSRecordCloudFlare(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def addDNSRecordCloudFlare(request):
    try:
        userID = request.session['userID']

        dm = DNSManager()
        coreResult = dm.addDNSRecordCloudFlare(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def syncCF(request):
    try:
        userID = request.session['userID']

        dm = DNSManager()
        coreResult = dm.syncCF(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def enableProxy(request):
    try:
        userID = request.session['userID']

        dm = DNSManager()
        coreResult = dm.enableProxy(userID, json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
