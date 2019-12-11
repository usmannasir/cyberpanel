# -*- coding: utf-8 -*-

from django.shortcuts import redirect
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