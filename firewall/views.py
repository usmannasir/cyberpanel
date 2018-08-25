from django.shortcuts import render,redirect
from django.http import HttpResponse
import json
import shlex
import subprocess
from loginSystem.views import loadLoginPage
from plogical.virtualHostUtilities import virtualHostUtilities
from plogical.csf import CSF
import time
from plogical.acl import ACLManager
from plogical.firewallManager import FirewallManager
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
        fm = FirewallManager()
        return fm.firewallHome(request, userID)
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
        fm = FirewallManager()
        return fm.addRule(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteRule(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.deleteRule(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def reloadFirewall(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.reloadFirewall(userID)
    except KeyError:
        return redirect(loadLoginPage)

def startFirewall(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.startFirewall(userID)
    except KeyError:
        return redirect(loadLoginPage)

def stopFirewall(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.stopFirewall(userID)
    except KeyError:
        return redirect(loadLoginPage)

def firewallStatus(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.firewallStatus(userID)
    except KeyError:
        return redirect(loadLoginPage)

def secureSSH(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.secureSSH(request, userID)
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
        fm = FirewallManager()
        return fm.saveSSHConfigs(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def deleteSSHKey(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.deleteSSHKey(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def addSSHKey(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.addSSHKey(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def loadModSecurityHome(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.loadModSecurityHome(request, userID)
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
        fm = FirewallManager()
        return fm.saveModSecConfigurations(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def modSecRules(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.modSecRules(request, userID)
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
        fm = FirewallManager()
        return fm.saveModSecRules(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def modSecRulesPacks(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.modSecRulesPacks(request, userID)
    except KeyError:
        return redirect(loadLoginPage)

def getOWASPAndComodoStatus(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.getOWASPAndComodoStatus(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def installModSecRulesPack(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.installModSecRulesPack(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def getRulesFiles(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.getRulesFiles(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def enableDisableRuleFile(request):
    try:
        userID = request.session['userID']
        fm = FirewallManager()
        return fm.enableDisableRuleFile(userID, json.loads(request.body))
    except KeyError:
        return redirect(loadLoginPage)

def csf(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        csfInstalled = 1

        try:
            command = 'sudo csf -h'
            res = subprocess.call(shlex.split(command))
            if res == 1:
                csfInstalled = 0
        except subprocess.CalledProcessError:
            csfInstalled = 0

        return render(request,'firewall/csf.html', {'csfInstalled' : csfInstalled})
    except KeyError:
        return redirect(loadLoginPage)

def installCSF(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('installStatus', 0)
        try:

            execPath = "sudo " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " installCSF"
            subprocess.Popen(shlex.split(execPath))

            time.sleep(2)

            data_ret = {"installStatus": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException,msg:
            final_dic = {'installStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'installStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def installStatusCSF(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)
        try:
            if request.method == 'POST':

                installStatus = unicode(open(CSF.installLogPath, "r").read())

                if installStatus.find("[200]")>-1:

                    command = 'sudo rm -f ' + CSF.installLogPath
                    subprocess.call(shlex.split(command))

                    final_json = json.dumps({
                                             'error_message': "None",
                                             'requestStatus': installStatus,
                                             'abort':1,
                                             'installed': 1,
                                             })
                    return HttpResponse(final_json)
                elif installStatus.find("[404]") > -1:
                    command = 'sudo rm -f ' + CSF.installLogPath
                    subprocess.call(shlex.split(command))
                    final_json = json.dumps({
                                             'abort':1,
                                             'installed':0,
                                             'error_message': "None",
                                             'requestStatus': installStatus,
                                             })
                    return HttpResponse(final_json)

                else:
                    final_json = json.dumps({
                                             'abort':0,
                                             'error_message': "None",
                                             'requestStatus': installStatus,
                                             })
                    return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'abort':1,'installed':0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'abort':1,'installed':0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def removeCSF(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('installStatus', 0)
        try:

            execPath = "sudo " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " removeCSF"
            subprocess.Popen(shlex.split(execPath))

            time.sleep(2)

            data_ret = {"installStatus": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException,msg:
            final_dic = {'installStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'installStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def fetchCSFSettings(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson('fetchStatus', 0)
        try:

            currentSettings = CSF.fetchCSFSettings()


            data_ret = {"fetchStatus": 1, 'testingMode' : currentSettings['TESTING'],
                        'tcpIN' : currentSettings['tcpIN'],
                        'tcpOUT': currentSettings['tcpOUT'],
                        'udpIN': currentSettings['udpIN'],
                        'udpOUT': currentSettings['udpOUT'],
                        'firewallStatus': currentSettings['firewallStatus']
                        }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def changeStatus(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            data = json.loads(request.body)

            controller = data['controller']
            status = data['status']

            execPath = "sudo " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " changeStatus --controller " + controller + " --status " + status
            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                data_ret = {"status": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def modifyPorts(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        try:
            data = json.loads(request.body)

            protocol = data['protocol']
            ports = data['ports']

            execPath = "sudo " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " modifyPorts --protocol " + protocol + " --ports " + ports
            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                data_ret = {"status": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def modifyIPs(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()
        try:

            data = json.loads(request.body)

            mode = data['mode']
            ipAddress = data['ipAddress']

            if mode == 'allowIP':
                CSF.allowIP(ipAddress)
            elif mode == 'blockIP':
                CSF.blockIP(ipAddress)

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)


        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)
