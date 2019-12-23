# -*- coding: utf-8 -*-


from django.shortcuts import render,redirect
from django.http import HttpResponse
from loginSystem.models import Administrator
from loginSystem.views import loadLoginPage
import json
from websiteFunctions.website import WebsiteManager
from websiteFunctions.pluginManager import pluginManager
from django.views.decorators.csrf import csrf_exempt

def loadWebsitesHome(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        return render(request,'websiteFunctions/index.html',{"type":admin.type})
    except KeyError:
        return redirect(loadLoginPage)

def createWebsite(request):
    try:
        userID = request.session['userID']
        wm = WebsiteManager()
        return wm.createWebsite(request, userID)
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