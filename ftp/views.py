# -*- coding: utf-8 -*-
import json
import os
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


def ftpQuotaManagementPage(request):
    """Render the FTP Quota Management page (served from /ftp/ to avoid websites/<domain> conflict)."""
    try:
        proc = httpProc(request, 'websiteFunctions/ftpQuotaManagement.html', {}, 'admin')
        return proc.render()
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
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] != 1:
            return ACLManager.loadErrorJson('FilemanagerAdmin', 0)

        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8') if body else '{}'
            data = json.loads(body) if body and body.strip() else {}
        except (json.JSONDecodeError, ValueError):
            data = {}

        tempStatusPath = os.path.join('/tmp', 'cyberpanel_ftp_reset_' + str(randint(10000, 99999)))
        try:
            with open(tempStatusPath, 'w') as f:
                f.write("Starting FTP reset...,0\n")
        except OSError as e:
            data_ret = {'status': 0, 'error_message': 'Cannot create status file: ' + str(e), 'tempStatusPath': ''}
            return HttpResponse(json.dumps(data_ret), content_type='application/json')
        python_path = '/usr/local/CyberCP/bin/python'
        if not os.path.exists(python_path):
            for p in ('/usr/bin/python3', '/usr/bin/python'):
                if os.path.exists(p):
                    python_path = p
                    break
            else:
                python_path = 'python3'
        execPath = f"{python_path} /usr/local/CyberCP/ftp/ftpManager.py ResetFTPConfigurations --tempStatusPath {tempStatusPath}"

        ProcessUtilities.popenExecutioner(execPath)
        time.sleep(2)

        data_ret = {'status': 1, 'error_message': "None", 'tempStatusPath': tempStatusPath}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data, content_type='application/json')
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

        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8') if body else '{}'
            data = json.loads(body) if body and body.strip() else {}
        except (json.JSONDecodeError, ValueError, TypeError):
            data = {}
        statusfile = data.get('statusfile', '')
        if not statusfile:
            return HttpResponse(json.dumps({'abort': 1, 'installed': 0, 'error_message': 'Missing status file', 'requestStatus': ''}), content_type='application/json')
        result = ProcessUtilities.outputExecutioner("cat " + statusfile)
        if result is None:
            installStatus = ""
        elif isinstance(result, tuple):
            installStatus = result[1] if len(result) > 1 else ""
        else:
            installStatus = str(result) if result else ""



        if installStatus.find("[200]") > -1:
            command = 'rm -f ' + statusfile
            ProcessUtilities.executioner(command)

            return HttpResponse(json.dumps({
                'error_message': "None",
                'requestStatus': installStatus,
                'abort': 1,
                'installed': 1,
            }), content_type='application/json')
        elif installStatus.find("[404]") > -1:
            command = 'rm -f ' + statusfile
            ProcessUtilities.executioner(command)
            err_msg = installStatus.replace('[404]', '').strip() if installStatus else 'Reset failed'
            if not err_msg or err_msg == ',':
                err_msg = 'FTP configuration reset failed'
            final_json = json.dumps({
                'abort': 1,
                'installed': 0,
                'error_message': err_msg,
                'requestStatus': installStatus,
            })
            return HttpResponse(final_json, content_type='application/json')

        else:
            return HttpResponse(json.dumps({
                'abort': 0,
                'error_message': "None",
                'requestStatus': installStatus or '',
            }), content_type='application/json')
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

def changeFTPDirectory(request):
    try:
        result = pluginManager.preChangeFTPDirectory(request)
        if result != 200:
            return result

        fm = FTPManager(request)
        coreResult = fm.changeFTPDirectory()

        result = pluginManager.postChangeFTPDirectory(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def setFTPAccountStatus(request):
    try:
        result = pluginManager.preSetFTPAccountStatus(request)
        if result != 200:
            return result

        fm = FTPManager(request)
        coreResult = fm.setFTPAccountStatus()

        result = pluginManager.postSetFTPAccountStatus(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def updateFTPQuota(request):
    try:
        fm = FTPManager(request)
        return fm.updateFTPQuota()
    except KeyError:
        return redirect(loadLoginPage)

def getFTPQuotaUsage(request):
    try:
        fm = FTPManager(request)
        return fm.getFTPQuotaUsage()
    except KeyError:
        return redirect(loadLoginPage)

def migrateFTPQuotas(request):
    try:
        fm = FTPManager(request)
        return fm.migrateFTPQuotas()
    except KeyError:
        return redirect(loadLoginPage)