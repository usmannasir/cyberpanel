# -*- coding: utf-8 -*-
from __future__ import unicode_literals

# Create your views here.
import json

from django.shortcuts import redirect

from backup.backupManager import BackupManager
from backup.pluginManager import pluginManager
from loginSystem.views import loadLoginPage


def loadBackupHome(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.loadBackupHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def backupSite(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.backupSite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def restoreSite(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.restoreSite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def getCurrentBackups(request):
    try:
        userID = request.session['userID']
        wm = BackupManager()
        return wm.getCurrentBackups(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def submitBackupCreation(request):
    try:
        userID = 1

        result = pluginManager.preSubmitBackupCreation(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult =  wm.submitBackupCreation(userID, json.loads(request.body))

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def backupStatus(request):
    try:
        userID = 1
        wm = BackupManager()
        return wm.backupStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def cancelBackupCreation(request):
    try:
        userID = request.session['userID']
        wm = BackupManager()
        return wm.cancelBackupCreation(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteBackup(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preDeleteBackup(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.deleteBackup(userID, json.loads(request.body))

        result = pluginManager.postDeleteBackup(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def submitRestore(request):
    try:
        result = pluginManager.preSubmitRestore(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.submitRestore(json.loads(request.body))

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def restoreStatus(request):
    try:
        wm = BackupManager()
        return wm.restoreStatus(json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def backupDestinations(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.backupDestinations(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def submitDestinationCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSubmitDestinationCreation(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.submitDestinationCreation(userID, json.loads(request.body))

        result = pluginManager.postSubmitDestinationCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def getCurrentBackupDestinations(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.getCurrentBackupDestinations(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def getConnectionStatus(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.getConnectionStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteDestination(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preDeleteDestination(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.deleteDestination(userID, json.loads(request.body))

        result = pluginManager.postDeleteDestination(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def scheduleBackup(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.scheduleBackup(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def getCurrentBackupSchedules(request):
    try:
        userID = request.session['userID']
        wm = BackupManager()
        return wm.getCurrentBackupSchedules(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def submitBackupSchedule(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preSubmitBackupSchedule(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.submitBackupSchedule(userID, json.loads(request.body))

        result = pluginManager.postSubmitBackupSchedule(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def scheduleDelete(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preScheduleDelete(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.scheduleDelete(userID, json.loads(request.body))

        result = pluginManager.postScheduleDelete(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def remoteBackups(request):
    try:
        userID = request.session['userID']
        bm = BackupManager()
        return bm.remoteBackups(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def submitRemoteBackups(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preSubmitRemoteBackups(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.submitRemoteBackups(userID, json.loads(request.body))

        result = pluginManager.postSubmitRemoteBackups(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def starRemoteTransfer(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preStarRemoteTransfer(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.starRemoteTransfer(userID, json.loads(request.body))

        result = pluginManager.postStarRemoteTransfer(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def getRemoteTransferStatus(request):
    try:
        userID = request.session['userID']
        wm = BackupManager()
        return wm.getRemoteTransferStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def remoteBackupRestore(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preRemoteBackupRestore(request)
        if result != 200:
            return result

        wm = BackupManager()
        coreResult = wm.remoteBackupRestore(userID, json.loads(request.body))

        result = pluginManager.postRemoteBackupRestore(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def localRestoreStatus(request):
    try:
        userID = request.session['userID']
        wm = BackupManager()
        return wm.localRestoreStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def cancelRemoteBackup(request):
    try:
        userID = request.session['userID']
        wm = BackupManager()
        return wm.cancelRemoteBackup(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)
