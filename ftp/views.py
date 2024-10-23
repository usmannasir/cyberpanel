# -*- coding: utf-8 -*-
import json
import time
from random import randint

from django.shortcuts import redirect, HttpResponse

from plogical.acl import ACLManager
from plogical.httpProc import httpProc
from plogical.processUtilities import ProcessUtilities
from .ftpManager import FTPManager
from loginSystem.views import loadLoginPage
from .pluginManager import pluginManager
# Create your views here.

def loadFTPHome(request):
    try:
        fm = FTPManager(request)
        return fm.loadFTPHome()
    except KeyError:
        return redirect(loadLoginPage)

def createFTPAccount(request):
    try:

        result = pluginManager.preCreateFTPAccount(request)
        if result != 200:
            return result

        fm = FTPManager(request)
        coreResult =  fm.createFTPAccount()

        result = pluginManager.postCreateFTPAccount(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def submitFTPCreation(request):
    try:

        result = pluginManager.preSubmitFTPCreation(request)
        if result != 200:
            return result

        fm = FTPManager(request)
        coreResult = fm.submitFTPCreation()

        result = pluginManager.postSubmitFTPCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def deleteFTPAccount(request):
    try:
        fm = FTPManager(request)
        return fm.deleteFTPAccount()
    except KeyError:
        return redirect(loadLoginPage)

def fetchFTPAccounts(request):
    try:
        fm = FTPManager(request)
        return fm.fetchFTPAccounts()
    except KeyError:
        return redirect(loadLoginPage)

def submitFTPDelete(request):
    try:

        result = pluginManager.preSubmitFTPDelete(request)
        if result != 200:
            return result

        fm = FTPManager(request)
        coreResult = fm.submitFTPDelete()

        result = pluginManager.postSubmitFTPDelete(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def listFTPAccounts(request):
    try:
        fm = FTPManager(request)
        return fm.listFTPAccounts()
    except KeyError:
        return redirect(loadLoginPage)


def ResetFTPConfigurations(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)


        proc = httpProc(request, 'ftp/ResetFTPconf.html')
        return proc.render()
    except KeyError:
        return redirect(loadLoginPage)


def resetftpnow(request):
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

        execPath = f"/usr/local/CyberCP/bin/python /usr/local/CyberCP/ftp/ftpManager.py ResetFTPConfigurations --tempStatusPath {tempStatusPath}"


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

def getAllFTPAccounts(request):
    try:
        fm = FTPManager(request)
        return fm.getAllFTPAccounts()
    except KeyError:
        return redirect(loadLoginPage)

def changePassword(request):
    try:

        result = pluginManager.preChangePassword(request)
        if result != 200:
            return result

        fm = FTPManager(request)
        coreResult = fm.changePassword()

        result = pluginManager.postChangePassword(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)