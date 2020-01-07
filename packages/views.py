# -*- coding: utf-8 -*-


from django.shortcuts import redirect
from loginSystem.views import loadLoginPage
from .packagesManager import PackagesManager
from .pluginManager import pluginManager

# Create your views here.


def packagesHome(request):
    try:
        pm = PackagesManager(request)
        return pm.packagesHome()
    except KeyError:
        return redirect(loadLoginPage)

def createPacakge(request):
    try:

        result = pluginManager.preCreatePacakge(request)
        if result != 200:
            return result

        pm = PackagesManager(request)
        coreResult = pm.createPacakge()

        result = pluginManager.postCreatePacakge(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def deletePacakge(request):
    try:
        pm = PackagesManager(request)
        return pm.deletePacakge()
    except KeyError:
        return redirect(loadLoginPage)

def submitPackage(request):
    try:

        result = pluginManager.preSubmitPackage(request)
        if result != 200:
            return result

        pm = PackagesManager(request)
        coreResult = pm.submitPackage()

        result = pluginManager.postSubmitPackage(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def submitDelete(request):
    try:

        result = pluginManager.preSubmitDelete(request)
        if result != 200:
            return result

        pm = PackagesManager(request)
        coreResult = pm.submitDelete()

        result = pluginManager.postSubmitDelete(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def modifyPackage(request):
    try:
        pm = PackagesManager(request)
        return pm.modifyPackage()
    except KeyError:
        return redirect(loadLoginPage)

def submitModify(request):
    try:
        pm = PackagesManager(request)
        return pm.submitModify()
    except KeyError:
        return redirect(loadLoginPage)

def saveChanges(request):
    try:

        result = pluginManager.preSaveChanges(request)
        if result != 200:
            return result

        pm = PackagesManager(request)
        coreResult = pm.saveChanges()

        result = pluginManager.postSaveChanges(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)


def listPackages(request):
    try:
        pm = PackagesManager(request)
        return pm.listPackages()
    except KeyError:
        return redirect(loadLoginPage)



def fetchPackagesTable(request):
    try:

        pm = PackagesManager(request)
        coreResult = pm.fetchPackagesTable()

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
