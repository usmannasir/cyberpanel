# -*- coding: utf-8 -*-


from django.shortcuts import redirect
from django.http import HttpResponse, JsonResponse
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
import json
import plogical.CyberCPLogFileWriter as logging
from plogical.acl import ACLManager

from plogical.httpProc import httpProc
from websiteFunctions.models import wpplugins
from websiteFunctions.website import WebsiteManager
from websiteFunctions.pluginManager import pluginManager
from django.views.decorators.csrf import csrf_exempt
from .dockerviews import startContainer as docker_startContainer
from .dockerviews import stopContainer as docker_stopContainer
from .dockerviews import restartContainer as docker_restartContainer
from .resource_monitoring import get_website_resource_usage
import jwt
from datetime import datetime, timedelta
import OpenSSL
from plogical.processUtilities import ProcessUtilities
import os
import re
from plogical.securityUtils import get_terminal_jwt_secret



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
        return wm.WPCreate(request, userID, )
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
        return wm.AddRemoteBackupsite(request, userID, ID, DeleteSiteID)
    except KeyError:
        return redirect(loadLoginPage)


def WordpressPricing(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.WordpressPricing(request, userID, )
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
                logging.CyberCPLogFileWriter.writeToFile("DeleteFileID ....... %s....msg.....%s" % (DeleteFileID, msg))
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        # result = pluginManager.preWebsiteCreation(request)

        # if result != 200:
        #    return result

        wm = WebsiteManager()
        return wm.DeploytoProduction(userID, json.loads(request.body))

        # result = pluginManager.postWebsiteCreation(request, coreResult)
        # if result != 200:
        #    return result

        # return coreResult

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

        if result != 200:
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
        data = json.loads(request.body)

        wm = WebsiteManager()
        return wm.UpdateWPSettings(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def UpdatePlugins(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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

        if result != 200:
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


def siteWorkspace(request, domain):
    # Single-site workspace: one hub that gathers every action for a domain
    # (files, SSL, DNS, email, databases, backups, advanced) into tabbed tiles.
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        admin = Administrator.objects.get(pk=userID)

        if ACLManager.checkOwnership(domain, admin, currentACL) != 1:
            return ACLManager.loadError()

        from websiteFunctions.models import Websites
        try:
            website = Websites.objects.get(domain=domain)
        except Websites.DoesNotExist:
            return ACLManager.loadError()

        try:
            packageName = website.package.packageName
        except BaseException:
            packageName = ''

        data = {
            'domain': domain,
            'adminEmail': website.adminEmail,
            'phpSelection': website.phpSelection,
            'sslState': website.ssl,
            'siteState': website.state,
            'externalApp': website.externalApp,
            'packageName': packageName,
        }
        proc = httpProc(request, 'baseTemplate/siteWorkspace.html', data)
        return proc.render()
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
        return wm.gitNotify(request=request)
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
        # from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter
        # # Ensure FastAPI SSH server systemd service file is in place
        # try:
        #     service_path = '/etc/systemd/system/fastapi_ssh_server.service'
        #     local_service_path = 'fastapi_ssh_server.service'
        #     check_service = ProcessUtilities.outputExecutioner(f'test -f {service_path} && echo exists || echo missing')
        #     if 'missing' in check_service:
        #         ProcessUtilities.outputExecutioner(f'cp /usr/local/CyberCP/fastapi_ssh_server.service {service_path}')
        #         ProcessUtilities.outputExecutioner('systemctl daemon-reload')
        # except Exception as e:
        #     CyberCPLogFileWriter.writeLog(f"Failed to copy or reload fastapi_ssh_server.service: {e}")

        # # Ensure FastAPI SSH server is running using ProcessUtilities
        # try:
        #     ProcessUtilities.outputExecutioner('systemctl is-active --quiet fastapi_ssh_server')
        #     ProcessUtilities.outputExecutioner('systemctl enable --now fastapi_ssh_server')
        #     ProcessUtilities.outputExecutioner('systemctl start fastapi_ssh_server')
        # except Exception as e:
        #     CyberCPLogFileWriter.writeLog(f"Failed to ensure fastapi_ssh_server is running: {e}")

        # # Add-on check logic
        # url = "https://platform.cyberpersons.com/CyberpanelAdOns/Adonpermission"
        # data = {
        #     "name": "all",
        #     "IP": ACLManager.GetServerIP()
        # }
        # import requests
        # import json
        # try:
        #     response = requests.post(url, data=json.dumps(data))
        #     Status = response.json().get('status', 0)
        # except Exception:
        #     Status = 0
        # has_addons = (Status == 1) or ProcessUtilities.decideServer() == ProcessUtilities.ent

        # from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter

        # CyberCPLogFileWriter.writeToFile(f"has_addons: {has_addons}")

        # userID = request.session['userID']
        # wm = WebsiteManager(domain)
        # # SSL check
        # cert_path = '/usr/local/lscp/conf/cert.pem'
        # is_selfsigned = False
        # ssl_issue_link = '/manageSSL/sslForHostName'
        # try:
        #     cert_content = ProcessUtilities.outputExecutioner(f'cat {cert_path}')
        #     cert = OpenSSL.crypto.load_certificate(OpenSSL.crypto.FILETYPE_PEM, cert_content)
        #     is_selfsigned = cert.get_issuer().der() == cert.get_subject().der()
        # except Exception:
        #     is_selfsigned = True  # If cert missing or unreadable, treat as self-signed
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
        return wm.webhook(domain, json.loads(request.body), request=request)
    except KeyError:
        return redirect(loadLoginPage)


def ApacheManager(request, domain):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(domain)
        return wm.ApacheManager(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def getSwitchStatus(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.getSwitchStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def switchServer(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.switchServer(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def statusFunc(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        from cloudAPI.cloudManager import CloudManager
        admin = Administrator.objects.get(pk=userID)
        cm = CloudManager(data, admin)
        return cm.statusFunc()
    except KeyError:
        return redirect(loadLoginPage)


def tuneSettings(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.tuneSettings(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def saveApacheConfigsToFile(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.saveApacheConfigsToFile(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def CreateDockerPackage(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        proc = httpProc(request, 'websiteFunctions/CreateDockerPackage.html',
                        {"type": admin.type})
        return proc.render()
    except BaseException as msg:
        return HttpResponse(msg)


def CreateDockerPackage(request):
    try:
        userID = request.session['userID']
        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.CreateDockerPackage(request, userID, None, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)


def AssignPackage(request):
    try:
        userID = request.session['userID']
        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.AssignPackage(request, userID, None, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)


def CreateDockersite(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.CreateDockersite(request, userID)
    except KeyError:
        return redirect(loadLoginPage)


def AddDockerpackage(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.AddDockerpackage(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def Getpackage(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.Getpackage(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def Updatepackage(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.Updatepackage(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def AddAssignment(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.AddAssignment(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def submitDockerSiteCreation(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.submitDockerSiteCreation(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def ListDockerSites(request):
    try:
        userID = request.session['userID']
        DeleteID = request.GET.get('DeleteID')
        wm = WebsiteManager()
        return wm.ListDockerSites(request, userID, None, DeleteID)
    except KeyError:
        return redirect(loadLoginPage)


def fetchDockersite(request):
    try:
        userID = request.session['userID']
        data = json.loads(request.body)
        wm = WebsiteManager()
        return wm.fetchDockersite(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


def Dockersitehome(request, dockerapp):
    try:
        userID = request.session['userID']
        wm = WebsiteManager(dockerapp)
        return wm.Dockersitehome(request, userID, None)
    except KeyError:
        return redirect(loadLoginPage)


def fetchWPDetails(request):
    try:
        userID = request.session['userID']
        data = {
            'domain': request.POST.get('domain')
        }
        wm = WebsiteManager()
        return wm.fetchWPSitesForDomain(userID, data)
    except KeyError:
        return redirect(loadLoginPage)


@csrf_exempt
def startContainer(request):
    try:
        if request.method == 'POST':
            return docker_startContainer(request)
        return HttpResponse('Not allowed')
    except KeyError:
        return redirect(loadLoginPage)


@csrf_exempt
def stopContainer(request):
    try:
        if request.method == 'POST':
            return docker_stopContainer(request)
        return HttpResponse('Not allowed')
    except KeyError:
        return redirect(loadLoginPage)


@csrf_exempt
def restartContainer(request):
    try:
        if request.method == 'POST':
            return docker_restartContainer(request)
        return HttpResponse('Not allowed')
    except KeyError:
        return redirect(loadLoginPage)


@csrf_exempt
def get_website_resources(request):
    try:
        data = json.loads(request.body)
        domain = data['domain']

        # Get userID from session
        try:
            userID = request.session['userID']
            admin = Administrator.objects.get(pk=userID)
        except:
            return JsonResponse({'status': 0, 'error_message': 'Unauthorized access'})

        # Verify domain ownership
        currentACL = ACLManager.loadedACL(userID)

        from websiteFunctions.models import Websites
        try:
            website = Websites.objects.get(domain=domain)
        except Websites.DoesNotExist:
            return JsonResponse({'status': 0, 'error_message': 'Website not found'})

        if ACLManager.checkOwnership(domain, admin, currentACL) == 1:
            pass
        else:
            return ACLManager.loadError()

        # Get resource usage data using externalApp
        resource_data = get_website_resource_usage(website.externalApp)
        if resource_data['status'] == 0:
            return JsonResponse(resource_data)

        return JsonResponse(resource_data)

    except BaseException as msg:
        logging.CyberCPLogFileWriter.writeToFile(f'Error in get_website_resources: {str(msg)}')
        return JsonResponse({'status': 0, 'error_message': str(msg)})


@csrf_exempt
def get_terminal_jwt(request):
    import logging
    logger = logging.getLogger("cyberpanel.ssh.jwt")
    try:
        data = json.loads(request.body)
        domain = data.get('domain')
        if not domain:
            return JsonResponse({'status': 0, 'error_message': 'Domain required'})
        user_id = request.session.get('userID')
        if not user_id:
            return JsonResponse({'status': 0, 'error_message': 'Not authenticated'})
        from websiteFunctions.models import Websites
        from plogical.acl import ACLManager
        from loginSystem.models import Administrator
        admin = Administrator.objects.get(pk=user_id)
        currentACL = ACLManager.loadedACL(user_id)
        if ACLManager.checkOwnership(domain, admin, currentACL) != 1:
            return JsonResponse({'status': 0, 'error_message': 'Not authorized'})
        try:
            website = Websites.objects.get(domain=domain)
        except Websites.DoesNotExist:
            return JsonResponse({'status': 0, 'error_message': 'Website not found'})
        ssh_user = website.externalApp
        if not ssh_user:
            return JsonResponse({'status': 0, 'error_message': 'SSH user not configured for this website.'})
        from datetime import datetime, timedelta
        import jwt as pyjwt
        jwt_secret = get_terminal_jwt_secret(create_if_missing=True)
        payload = {
            'user_id': user_id,
            'ssh_user': ssh_user,
            'exp': datetime.utcnow() + timedelta(minutes=10)
        }
        token = pyjwt.encode(payload, jwt_secret, algorithm='HS256')
        return JsonResponse({'status': 1, 'token': token, 'ssh_user': ssh_user})
    except Exception as e:
        logger.error(f"Exception in get_terminal_jwt: {str(e)}")
        return JsonResponse({'status': 0, 'error_message': str(e)})


def fetchWPBackups(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preWebsiteCreation(request)
        if result != 200:
            return result

        wm = WebsiteManager()
        coreResult = wm.fetchWPBackups(userID, json.loads(request.body))

        result = pluginManager.postWebsiteCreation(request, coreResult)
        if result != 200:
            return result

        return coreResult

    except KeyError:
        return redirect(loadLoginPage)
