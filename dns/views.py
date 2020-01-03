# -*- coding: utf-8 -*-

from django.shortcuts import redirect
from loginSystem.views import loadLoginPage
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
        coreResult =  dm.zoneCreation(userID, json.loads(request.body))

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
        coreResult =  dm.addDNSRecord(userID, json.loads(request.body))

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
        coreResult =  dm.deleteDNSRecord(userID, json.loads(request.body))

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






