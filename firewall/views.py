from django.shortcuts import redirect
import json
from loginSystem.views import loadLoginPage
from .firewallManager import FirewallManager
from .pluginManager import pluginManager
# Create your views here.


def securityHome(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.securityHome(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def firewallHome(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preFirewallHome(request)
        if result != 200:
            return result
        fm = FirewallManager()
        coreResult = fm.firewallHome(request, userID)

        result = pluginManager.postFirewallHome(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def getCurrentRules(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.getCurrentRules(userID)
    except KeyError:
        return redirect(loadLoginPage)

def addRule(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preAddRule(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.addRule(userID, json.loads(request.body))

        result = pluginManager.postAddRule(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def deleteRule(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preDeleteRule(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.deleteRule(userID, json.loads(request.body))

        result = pluginManager.postDeleteRule(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def reloadFirewall(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preReloadFirewall(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.reloadFirewall(userID)

        result = pluginManager.postReloadFirewall(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def startFirewall(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preStartFirewall(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.startFirewall(userID)

        result = pluginManager.postStartFirewall(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def stopFirewall(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preStopFirewall(request)
        if result != 200:
            return result


        fm = FirewallManager()
        coreResult = fm.stopFirewall(userID)

        result = pluginManager.postStopFirewall(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def firewallStatus(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preFirewallStatus(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.firewallStatus(userID)

        result = pluginManager.postFirewallStatus(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def secureSSH(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSecureSSH(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.secureSSH(request, userID)

        result = pluginManager.postSecureSSH(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def getSSHConfigs(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.getSSHConfigs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveSSHConfigs(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSaveSSHConfigs(request)
        if result != 200:
            return result

        fm = FirewallManager(request)
        coreResult = fm.saveSSHConfigs(userID, json.loads(request.body))

        result = pluginManager.postSaveSSHConfigs(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def deleteSSHKey(request):
    try:
        userID = request.session['userID']
        result = pluginManager.preDeleteSSHKey(request)

        if result != 200:
            return result
        fm = FirewallManager()
        coreResult = fm.deleteSSHKey(userID, json.loads(request.body))

        result = pluginManager.postDeleteSSHKey(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def addSSHKey(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preAddSSHKey(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.addSSHKey(userID, json.loads(request.body))

        result = pluginManager.postAddSSHKey(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def loadModSecurityHome(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preLoadModSecurityHome(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.loadModSecurityHome(request, userID)

        result = pluginManager.postLoadModSecurityHome(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def installModSec(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.installModSec(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def installStatusModSec(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.installStatusModSec(userID)
    except KeyError:
        return redirect(loadLoginPage)

def fetchModSecSettings(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.fetchModSecSettings(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveModSecConfigurations(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSaveModSecConfigurations(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.saveModSecConfigurations(userID, json.loads(request.body))

        result = pluginManager.postSaveModSecConfigurations(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def modSecRules(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preModSecRules(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.modSecRules(request, userID)

        result = pluginManager.postModSecRules(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def fetchModSecRules(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.fetchModSecRules(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def saveModSecRules(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preSaveModSecRules(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.saveModSecRules(userID, json.loads(request.body))

        result = pluginManager.postSaveModSecRules(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def modSecRulesPacks(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preModSecRulesPacks(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.modSecRulesPacks(request, userID)

        result = pluginManager.postModSecRulesPacks(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def getOWASPAndComodoStatus(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preGetOWASPAndComodoStatus(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.getOWASPAndComodoStatus(userID, json.loads(request.body))

        result = pluginManager.postGetOWASPAndComodoStatus(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def installModSecRulesPack(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preInstallModSecRulesPack(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.installModSecRulesPack(userID, json.loads(request.body))

        result = pluginManager.postInstallModSecRulesPack(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def getRulesFiles(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preGetRulesFiles(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.getRulesFiles(userID, json.loads(request.body))

        result = pluginManager.postGetRulesFiles(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def enableDisableRuleFile(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preEnableDisableRuleFile(request)
        if result != 200:
            return result

        fm = FirewallManager()
        coreResult = fm.enableDisableRuleFile(userID, json.loads(request.body))

        result = pluginManager.postEnableDisableRuleFile(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def csf(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preCSF(request)
        if result != 200:
            return result

        fm = FirewallManager(request)
        coreResult = fm.csf()

        result = pluginManager.postCSF(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def installCSF(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager(request)
        return fm.installCSF()
    except KeyError:
        return redirect(loadLoginPage)

def installStatusCSF(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager(request)
        return fm.installStatusCSF()
    except KeyError:
        return redirect(loadLoginPage)

def removeCSF(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager(request)
        return fm.removeCSF()
    except KeyError:
        return redirect(loadLoginPage)

def fetchCSFSettings(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager(request)
        return fm.fetchCSFSettings()
    except KeyError:
        return redirect(loadLoginPage)

def changeStatus(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preChangeStatus(request)
        if result != 200:
            return result

        fm = FirewallManager(request)
        coreResult = fm.changeStatus()

        result = pluginManager.postChangeStatus(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def modifyPorts(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preModifyPorts(request)
        if result != 200:
            return result

        fm = FirewallManager(request)
        coreResult = fm.modifyPorts(json.loads(request.body))

        result = pluginManager.postModifyPorts(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)

def modifyIPs(request):
    try:
        userID = request.session['userID']

        result = pluginManager.preModifyIPs(request)
        if result != 200:
            return result

        fm = FirewallManager(request)
        coreResult = fm.modifyIPs()

        result = pluginManager.postModifyIPs(request, coreResult)
        if result != 200:
            return result

        return coreResult
    except KeyError:
        return redirect(loadLoginPage)
