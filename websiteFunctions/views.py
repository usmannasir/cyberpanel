# -*- coding: utf-8 -*-


from django.shortcuts import redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
import json
import plogical.CyberCPLogFileWriter as logging


from plogical.httpProc import httpProc
from websiteFunctions.models import wpplugins
from websiteFunctions.website import WebsiteManager
from websiteFunctions.pluginManager import pluginManager
from django.views.decorators.csrf import csrf_exempt

def loadWebsitesHome(request):
    val = request.session['userID']
    admin = Administrator.objects.get(pk=val)
    proc = httpProc(request, 'websiteFunctions/index.html',
                    {"type": admin.type})
    return proc.render()

def createWebsite(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.createWebsite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)
def WPCreate(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.WPCreate(request, userID,)
    except KeyError:
        return redirect(loadLoginPage)

def ListWPSites(request):
    try:
        userID = request.session['userID']
        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.ListWPSites(request, userID, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)

def WPHome(request):
    try:
        userID = request.session['userID']

        WPid = request.GET.get('ID')
        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.WPHome(request, userID, WPid, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)
def RestoreHome(request):
    try:
        userID = request.session['userID']

        BackupID = request.GET.get('BackupID')
        wm = WebsiteManager()
        return wm.RestoreHome(request, userID, BackupID)
    except KeyError:
        return redirect(loadLoginPage)


def RemoteBackupConfig(request):
    try:
        userID = request.session['userID']

        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.RemoteBackupConfig(request, userID, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)

def BackupfileConfig(request):
    try:
        userID = request.session['userID']

        ID = request.GET.get('ID')
        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.BackupfileConfig(request, userID, ID, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)

def AddRemoteBackupsite(request):
    try:
        userID = request.session['userID']

        ID = request.GET.get('ID')
        DeleteSiteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.AddRemoteBackupsite(request, userID, ID,DeleteSiteID )
    except KeyError:
        return redirect(loadLoginPage)

def WordpressPricing(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.WordpressPricing(request, userID,)
    except KeyError:
        return redirect(loadLoginPage)

def RestoreBackups(request):
    try:
        userID = request.session['userID']

        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.RestoreBackups(request, userID, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)

def AutoLogin(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.AutoLogin(request, userID)

    except KeyError:
        return redirect(loadLoginPage)
def ConfigurePlugins(request):
    try:
        userID = request.session['userID']
        userobj = Administrator.objects.get(pk=userID)
        DeleteFileID = request.GET.get('delete', None)
        if DeleteFileID != None:
            try:
                jobobj = wpplugins.objects.get(pk=DeleteFileID, owner=userobj)
                jobobj.delete()
                Deleted = 1
            except BaseException as msg:
                logging.CyberCPLogFileWriter.writeToFile("DeleteFileID ....... %s....msg.....%s" % (DeleteFileID,msg))
                Deleted = 0
        wm = WebsiteManager()
        return wm.ConfigurePlugins(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def Addnewplugin(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.Addnewplugin(request, userID)
    except KeyError:
        return redirect(loadLoginPage)




def SearchOnkeyupPlugin(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.SearchOnkeyupPlugin(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def AddNewpluginAjax(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.AddNewpluginAjax(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def EidtPlugin(request):
    try:
        userID = request.session['userID']

        pluginbID = request.GET.get('ID')
        wm = WebsiteManager()
        return wm.EidtPlugin(request, userID, pluginbID)
    except KeyError:
        return redirect(loadLoginPage)


def deletesPlgin(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.deletesPlgin(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def Addplugineidt(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.Addplugineidt(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def submitWorpressCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitWorpressCreation(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def FetchWPdata(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.FetchWPdata(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def GetCurrentPlugins(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.GetCurrentPlugins(userID, json.loads(request.body))
        # coreResult = wm.GetCsurrentPlugins(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def fetchstaging(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.fetchstaging(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def fetchDatabase(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.fetchDatabase(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def SaveUpdateConfig(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.SaveUpdateConfig(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def DeploytoProduction(request):
    try:
        userID = request.session['userID']

        #result = pluginManager.preWebsiteCreation(request)

        #if result != 200:
        #    return result

        wm = WebsiteManager()
        return wm.DeploytoProduction(userID, json.loads(request.body))

        #result = pluginManager.postWebsiteCreation(request, coreResult)
        #if result != 200:
        #    return result

        #return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def WPCreateBackup(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.WPCreateBackup(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)



def RestoreWPbackupNow(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.RestoreWPbackupNow(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def SaveBackupConfig(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.SaveBackupConfig(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def SaveBackupSchedule(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.SaveBackupSchedule(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def AddWPsiteforRemoteBackup(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.AddWPsiteforRemoteBackup(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def UpdateRemoteschedules(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.UpdateRemoteschedules(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def ScanWordpressSite(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.ScanWordpressSite(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def installwpcore(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.installwpcore(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def dataintegrity(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.dataintegrity(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)



def GetCurrentThemes(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.GetCurrentThemes(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def UpdateWPSettings(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.UpdateWPSettings(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def UpdatePlugins(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.UpdatePlugins(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def UpdateThemes(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.UpdateThemes(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def DeletePlugins(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.DeletePlugins(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def DeleteThemes(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.DeleteThemes(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def ChangeStatus(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.ChangeStatus(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def StatusThemes(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.ChangeStatusThemes(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)


def CreateStagingNow(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.CreateStagingNow(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)



def modifyWebsite(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.modifyWebsite(request, userID)
    except BaseException as msg:
        return HttpResponse(str(msg))

    except KeyError:
        return redirect(loadLoginPage)

def deleteWebsite(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.deleteWebsite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def CreateNewDomain(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.CreateNewDomain(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def siteState(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.siteState(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def listWebsites(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.listWebsites(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def listChildDomains(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.listChildDomains(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def submitWebsiteCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if  result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitWebsiteCreation(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def submitDomainCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preDomainCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitDomainCreation(userID, json.loads(request.body))

        result = pluginManager.postDomainCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def fetchDomains(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchDomains(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def searchWebsites(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.searchWebsites(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def searchChilds(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.searchChilds(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def getFurtherAccounts(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getFurtherAccounts(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchWebsitesList(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchWebsitesList(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchChildDomainsMain(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchChildDomainsMain(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def submitWebsiteDeletion(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteDeletion(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitWebsiteDeletion(userID, json.loads(request.body))

        result = pluginManager.postWebsiteDeletion(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def submitDomainDeletion(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preDomainDeletion(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitDomainDeletion(userID, json.loads(request.body))

        result = pluginManager.postDomainDeletion(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def convertDomainToSite(request):
    try:

        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.convertDomainToSite(userID, request)

    except KeyError:
        return redirect(loadLoginPage)

def submitWebsiteStatus(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preWebsiteSuspension(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitWebsiteStatus(userID, json.loads(request.body))

        result = pluginManager.postWebsiteSuspension(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def submitWebsiteModify(request):
    try:

        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.submitWebsiteModify(userID, json.loads(request.body))

    except KeyError:
        return redirect(loadLoginPage)

def saveWebsiteChanges(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preWebsiteModification(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.saveWebsiteChanges(userID, json.loads(request.body))

        result = pluginManager.postWebsiteModification(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def domain(request, domain):
    try:

        if not request.GET._mutable:
            request.GET._mutable = True
        request.GET['domain'] = domain

        result = pluginManager.preDomain(request)
        if result != 200:
            return result

        userID = request.session['userID']
        wm = WebsiteManager(domain)
        coreResult = wm.loadDomainHome(request, userID)

        result = pluginManager.postDomain(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def launchChild(request, domain, childDomain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain, childDomain)
        return wm.launchChild(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def getDataFromLogFile(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getDataFromLogFile(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchErrorLogs(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchErrorLogs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def getDataFromConfigFile(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getDataFromConfigFile(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveConfigsToFile(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preSaveConfigsToFile(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.saveConfigsToFile(userID, json.loads(request.body))

        result = pluginManager.postSaveConfigsToFile(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def getRewriteRules(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getRewriteRules(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveRewriteRules(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preSaveRewriteRules(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.saveRewriteRules(userID, json.loads(request.body))

        result = pluginManager.postSaveRewriteRules(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def saveSSL(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preSaveSSL(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.saveSSL(userID, json.loads(request.body))

        result = pluginManager.postSaveSSL(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def changePHP(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preChangePHP(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.changePHP(userID, json.loads(request.body))

        result = pluginManager.postChangePHP(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def listCron(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.listCron(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def getWebsiteCron(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getWebsiteCron(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def getCronbyLine(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getCronbyLine(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveCronChanges(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.saveCronChanges(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def remCronbyLine(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preRemCronbyLine(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.remCronbyLine(userID, json.loads(request.body))

        result = pluginManager.postRemCronbyLine(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def addNewCron(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preAddNewCron(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.addNewCron(userID, json.loads(request.body))

        result = pluginManager.postAddNewCron(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def domainAlias(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.domainAlias(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def submitAliasCreation(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSubmitAliasCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.submitAliasCreation(userID, json.loads(request.body))

        result = pluginManager.postSubmitAliasCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def issueAliasSSL(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.issueAliasSSL(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def delateAlias(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preDelateAlias(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.delateAlias(userID, json.loads(request.body))

        result = pluginManager.postDelateAlias(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def changeOpenBasedir(request):
    try:

        userID = request.session['userID']

        result = pluginManager.preChangeOpenBasedir(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.changeOpenBasedir(userID, json.loads(request.body))

        result = pluginManager.postChangeOpenBasedir(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)

def wordpressInstall(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.wordpressInstall(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def installWordpress(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.installWordpress(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def installWordpressStatus(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.installWordpressStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def joomlaInstall(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.joomlaInstall(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def installJoomla(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.installJoomla(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def setupGit(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.setupGit(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def setupGitRepo(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.setupGitRepo(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

@csrf_exempt
def gitNotify(request, domain):
    try:
        wm = WebsiteManager(domain)
        return wm.gitNotify()
    except KeyError:
        return redirect(loadLoginPage)

def detachRepo(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.detachRepo(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def changeBranch(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.changeBranch(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def installPrestaShop(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.installPrestaShop(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def installMagento(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.installMagento(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def magentoInstall(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.magentoInstall(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def installMautic(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.installMautic(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def mauticInstall(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.mauticInstall(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def prestaShopInstall(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.prestaShopInstall(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def sshAccess(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.sshAccess(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def saveSSHAccessChanges(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.saveSSHAccessChanges(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def setupStaging(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.setupStaging(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def startCloning(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.startCloning(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def syncToMaster(request, domain, childDomain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.syncToMaster(request, userID, None, childDomain)
    except KeyError:
        return redirect(loadLoginPage)

def startSync(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.startSync(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


### Manage GIT

def manageGIT(request, domain):
    try:

        if not request.GET._mutable:
            request.GET._mutable = True

        request.GET['domain'] = domain

        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.manageGIT(request, userID)

    except KeyError:
        return redirect(loadLoginPage)

def fetchFolderDetails(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchFolderDetails(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def initRepo(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.initRepo(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def setupRemote(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.setupRemote(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def changeGitBranch(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.changeGitBranch(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def createNewBranch(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.createNewBranch(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def commitChanges(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.commitChanges(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def gitPull(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.gitPull(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def gitPush(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.gitPush(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def attachRepoGIT(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.attachRepoGIT(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def removeTracking(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.removeTracking(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchGitignore(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchGitignore(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveGitIgnore(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.saveGitIgnore(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchCommits(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchCommits(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchFiles(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchFiles(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchChangesInFile(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchChangesInFile(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveGitConfigurations(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.saveGitConfigurations(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def fetchGitLogs(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.fetchGitLogs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def getSSHConfigs(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getSSHConfigs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteSSHKey(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.deleteSSHKey(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def addSSHKey(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.addSSHKey(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

@csrf_exempt
def webhook(request, domain):
    try:
        wm = WebsiteManager()
        return wm.webhook(domain, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)
