from django.shortcuts import redirect
from django.http import HttpResponse
import json
from loginSystem.views import loadLoginPage
from plogical.processUtilities import ProcessUtilities
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


def firewallRedirect(request):
    """Redirect /firewall/ to /firewall/firewall-rules/ so the default tab has a clear URL."""
    try:
        if request.session.get('userID'):
            return redirect('/firewall/firewall-rules/')
        return redirect(loadLoginPage)
    except Exception:
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
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body) if body and body.strip() else {}
        except (json.JSONDecodeError, Exception):
            data = {}
        return fm.getCurrentRules(userID, data)
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


def modifyRule(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.modifyRule(userID, json.loads(request.body))
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


def reorderRules(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            data = json.loads(body) if body and body.strip() else {}
        except (json.JSONDecodeError, Exception):
            data = {}
        return fm.reorderRules(userID, data)
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
        fm = FirewallManager(request)
        return fm.installCSF()
    except KeyError:
        return redirect(loadLoginPage)


def installStatusCSF(request):
    try:
        fm = FirewallManager(request)
        return fm.installStatusCSF()
    except KeyError:
        return redirect(loadLoginPage)


def removeCSF(request):
    try:
        fm = FirewallManager(request)
        return fm.removeCSF()
    except KeyError:
        return redirect(loadLoginPage)


def fetchCSFSettings(request):
    try:
        fm = FirewallManager(request)
        return fm.fetchCSFSettings()
    except KeyError:
        return redirect(loadLoginPage)


def changeStatus(request):
    try:

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


## Imunify

def imunify(request):
    try:

        fm = FirewallManager(request)
        return fm.imunify()

    except KeyError:
        return redirect(loadLoginPage)


def submitinstallImunify(request):
    try:

        fm = FirewallManager(request)
        return fm.submitinstallImunify()

    except KeyError:
        return redirect(loadLoginPage)


## ImunifyAV

def imunifyAV(request):
    try:

        fm = FirewallManager(request)
        return fm.imunifyAV()

    except KeyError:
        return redirect(loadLoginPage)


def submitinstallImunifyAV(request):
    try:

        fm = FirewallManager(request)
        return fm.submitinstallImunifyAV()

    except KeyError:
        return redirect(loadLoginPage)


def litespeed_ent_conf(request):
    try:
        if ProcessUtilities.decideServer() == ProcessUtilities.ent:
            userID = request.session['userID']
            fm = FirewallManager()
            return fm.litespeed_ent_conf(request, userID)
        else:
            return redirect(loadLoginPage)
    except KeyError:
        return redirect(loadLoginPage)


def fetchlitespeed_conf(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.fetchlitespeed_Conf(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)
def saveLitespeed_conf(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.saveLitespeed_conf(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

# Banned IPs Views
def getBannedIPs(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        data = {}
        if request.method == 'POST':
            try:
                body = request.body
                if isinstance(body, bytes):
                    body = body.decode('utf-8')
                data = json.loads(body) if body and body.strip() else {}
            except (json.JSONDecodeError, Exception):
                pass
        # GET also supported (no body); pagination uses defaults
        result = fm.getBannedIPs(userID, data)
        # Ensure we return JSON (FirewallManager may return HttpResponse)
        return result
    except KeyError:
        final_dic = {'status': 0, 'error_message': 'Session expired. Please log in again.', 'bannedIPs': [], 'total_count': 0}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=403)

def addBannedIP(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            request_data = json.loads(body) if body and body.strip() else {}
        except json.JSONDecodeError as e:
            final_dic = {'status': 0, 'error_message': 'Invalid JSON in request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        except Exception as e:
            final_dic = {'status': 0, 'error_message': 'Error parsing request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        result = fm.addBannedIP(userID, request_data)
        return result
    except KeyError:
        final_dic = {'status': 0, 'error_message': 'Session expired. Please refresh the page and try again.'}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=403)
    except Exception as e:
        import traceback
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as _log
        error_trace = traceback.format_exc()
        _log.writeToFile('Error in addBannedIP view: %s\n%s' % (str(e), error_trace))
        final_dic = {'status': 0, 'error_message': 'Server error: %s' % str(e)}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=500)

def modifyBannedIP(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            request_data = json.loads(body) if body and body.strip() else {}
        except json.JSONDecodeError as e:
            final_dic = {'status': 0, 'error_message': 'Invalid JSON in request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        except Exception as e:
            final_dic = {'status': 0, 'error_message': 'Error parsing request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        return fm.modifyBannedIP(userID, request_data)
    except KeyError:
        final_dic = {'status': 0, 'error_message': 'Session expired. Please refresh the page and try again.'}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=403)
    except Exception as e:
        import traceback
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as _log
        error_trace = traceback.format_exc()
        _log.writeToFile('Error in modifyBannedIP view: %s\n%s' % (str(e), error_trace))
        final_dic = {'status': 0, 'error_message': 'Server error: %s' % str(e)}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=500)

def removeBannedIP(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            request_data = json.loads(body) if body and body.strip() else {}
        except json.JSONDecodeError as e:
            final_dic = {'status': 0, 'error_message': 'Invalid JSON in request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        except Exception as e:
            final_dic = {'status': 0, 'error_message': 'Error parsing request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        return fm.removeBannedIP(userID, request_data)
    except KeyError:
        final_dic = {'status': 0, 'error_message': 'Session expired. Please refresh the page and try again.'}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=403)
    except Exception as e:
        import traceback
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as _log
        error_trace = traceback.format_exc()
        _log.writeToFile('Error in removeBannedIP view: %s\n%s' % (str(e), error_trace))
        final_dic = {'status': 0, 'error_message': 'Server error: %s' % str(e)}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=500)

def deleteBannedIP(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        try:
            body = request.body
            if isinstance(body, bytes):
                body = body.decode('utf-8')
            request_data = json.loads(body) if body and body.strip() else {}
        except json.JSONDecodeError as e:
            final_dic = {'status': 0, 'error_message': 'Invalid JSON in request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        except Exception as e:
            final_dic = {'status': 0, 'error_message': 'Error parsing request: %s' % str(e)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json', status=400)
        return fm.deleteBannedIP(userID, request_data)
    except KeyError:
        final_dic = {'status': 0, 'error_message': 'Session expired. Please refresh the page and try again.'}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=403)
    except Exception as e:
        import traceback
        from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as _log
        error_trace = traceback.format_exc()
        _log.writeToFile('Error in deleteBannedIP view: %s\n%s' % (str(e), error_trace))
        final_dic = {'status': 0, 'error_message': 'Server error: %s' % str(e)}
        return HttpResponse(json.dumps(final_dic), content_type='application/json', status=500)


def exportFirewallRules(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager(request)
        return fm.exportFirewallRules(userID)
    except KeyError:
        return redirect(loadLoginPage)


def importFirewallRules(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager(request)
        
        # Handle file upload
        if request.method == 'POST' and 'import_file' in request.FILES:
            return fm.importFirewallRules(userID, None)
        else:
            # Handle JSON data
            return fm.importFirewallRules(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)


def exportBannedIPs(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.exportBannedIPs(userID)
    except KeyError:
        return redirect(loadLoginPage)


def importBannedIPs(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        fm.request = request  # Set request for file upload handling
        
        # Handle file upload
        if request.method == 'POST' and 'import_file' in request.FILES:
            return fm.importBannedIPs(userID, None)
        else:
            # Handle JSON data
            return fm.importBannedIPs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)