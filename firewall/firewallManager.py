#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django

from loginSystem.models import Administrator
from plogical.httpProc import httpProc

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
import shlex
from plogical.acl import ACLManager
from plogical.securityUtils import is_safe_port
import plogical.CyberCPLogFileWriter as logging
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
from django.shortcuts import HttpResponse, render, redirect
from random import randint
import time
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
from plogical.modSec import modSec
from plogical.csf import CSF
from plogical.processUtilities import ProcessUtilities
from serverStatus.serverStatusUtil import ServerStatusUtil

class FirewallManager:

    imunifyPath = '/usr/bin/imunify360-agent'
    CLPath = '/etc/sysconfig/cloudlinux'
    imunifyAVPath = '/etc/sysconfig/imunify360/integration.conf'

    def __init__(self, request = None):
        self.request = request

    def securityHome(self, request = None, userID = None):
        proc = httpProc(request, 'firewall/index.html',
                        None, 'admin')
        return proc.render()

    def firewallHome(self, request = None, userID = None):
        csfPath = '/etc/csf'

        if os.path.exists(csfPath):
            return redirect('/configservercsf/')
        else:
            proc = httpProc(request, 'firewall/firewall.html',
                            None, 'admin')
            return proc.render()

    def getCurrentRules(self, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            rules = FirewallRules.objects.all()

            # Ensure CyberPanel port 7080 rule exists in database for visibility
            cyberpanel_rule_exists = False
            for rule in rules:
                if rule.port == '7080':
                    cyberpanel_rule_exists = True
                    break
            
            if not cyberpanel_rule_exists:
                # Create database entry for port 7080 (already enabled in system firewall)
                try:
                    cyberpanel_rule = FirewallRules(
                        name="CyberPanel Admin",
                        proto="tcp",
                        port="7080",
                        ipAddress="0.0.0.0/0"
                    )
                    cyberpanel_rule.save()
                    logging.CyberCPLogFileWriter.writeToFile("Added CyberPanel port 7080 to firewall database for UI visibility")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Failed to add CyberPanel port 7080 to database: {str(e)}")

            # Refresh rules after potential creation
            rules = FirewallRules.objects.all()

            json_data = "["
            checker = 0

            for items in rules:
                dic = {
                       'id': items.id,
                       'name': items.name,
                       'proto': items.proto,
                       'port': items.port,
                       'ipAddress': items.ipAddress,
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'status': 1, 'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addRule(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('add_status', 0)

            ruleName = data['ruleName']
            ruleProtocol = data['ruleProtocol']
            rulePort = data['rulePort']
            ruleIP = data['ruleIP']

            FirewallUtilities.addRule(ruleProtocol, rulePort, ruleIP)

            newFWRule = FirewallRules(name=ruleName, proto=ruleProtocol, port=rulePort, ipAddress=ruleIP)
            newFWRule.save()

            final_dic = {'status': 1, 'add_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteRule(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('delete_status', 0)

            ruleID = data['id']
            ruleProtocol = data['proto']
            rulePort = data['port']
            ruleIP = data['ruleIP']

            FirewallUtilities.deleteRule(ruleProtocol, rulePort, ruleIP)

            delRule = FirewallRules.objects.get(id=ruleID)
            delRule.delete()

            final_dic = {'status': 1, 'delete_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def editRule(self, userID = None, data = None):
        """
        Edit an existing firewall rule
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('edit_status', 0)

            ruleID = data['id']
            newRuleName = data['ruleName']
            newRuleProtocol = data['ruleProtocol']
            newRulePort = data['rulePort']
            newRuleIP = data['ruleIP']

            # Get the existing rule
            try:
                existingRule = FirewallRules.objects.get(id=ruleID)
            except FirewallRules.DoesNotExist:
                final_dic = {'status': 0, 'edit_status': 0, 'error_message': 'Rule not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Store old values for system firewall update
            oldProtocol = existingRule.proto
            oldPort = existingRule.port
            oldIP = existingRule.ipAddress

            # Check if any values actually changed
            if (existingRule.name == newRuleName and 
                existingRule.proto == newRuleProtocol and 
                existingRule.port == newRulePort and 
                existingRule.ipAddress == newRuleIP):
                final_dic = {'status': 1, 'edit_status': 1, 'error_message': "No changes detected"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Check if another rule with the same name already exists (excluding current rule)
            if existingRule.name != newRuleName:
                duplicateRule = FirewallRules.objects.filter(name=newRuleName).exclude(id=ruleID).first()
                if duplicateRule:
                    final_dic = {'status': 0, 'edit_status': 0, 'error_message': f'A rule with name "{newRuleName}" already exists'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

            # Update the rule in the system firewall
            # First remove the old rule
            FirewallUtilities.deleteRule(oldProtocol, oldPort, oldIP)
            
            # Then add the new rule
            FirewallUtilities.addRule(newRuleProtocol, newRulePort, newRuleIP)

            # Update the database record
            existingRule.name = newRuleName
            existingRule.proto = newRuleProtocol
            existingRule.port = newRulePort
            existingRule.ipAddress = newRuleIP
            existingRule.save()

            logging.CyberCPLogFileWriter.writeToFile(f"Firewall rule edited successfully. ID: {ruleID}, Name: {newRuleName}")

            final_dic = {'status': 1, 'edit_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'edit_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def reloadFirewall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('reload_status', 0)

            command = 'sudo firewall-cmd --reload'
            res = ProcessUtilities.executioner(command)

            if res == 1:
                final_dic = {'reload_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'reload_status': 0,
                             'error_message': "Can not reload firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'reload_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def startFirewall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('start_status', 0)

            command = 'sudo systemctl start firewalld'
            res = ProcessUtilities.executioner(command)

            if res == 1:
                final_dic = {'start_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'start_status': 0,
                             'error_message': "Can not start firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'start_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def stopFirewall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('stop_status', 0)

            command = 'sudo systemctl stop firewalld'
            res = ProcessUtilities.executioner(command)

            if res == 1:
                final_dic = {'stop_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'stop_status': 0,
                             'error_message': "Can not stop firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'stop_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def firewallStatus(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            command = 'systemctl status firewalld'
            status = ProcessUtilities.outputExecutioner(command)

            if status.find("dead") > -1:
                final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 0}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def secureSSH(self, request = None, userID = None):
        proc = httpProc(request, 'firewall/secureSSH.html',
                        None, 'admin')
        return proc.render()

    def getSSHConfigs(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            type = data['type']

            if type == "1":

                ## temporarily changing permission for sshd files

                pathToSSH = "/etc/ssh/sshd_config"

                cat = "sudo cat " + pathToSSH
                data = ProcessUtilities.outputExecutioner(cat).split('\n')

                permitRootLogin = 0
                sshPort = "22"

                for items in data:
                    if items.find("PermitRootLogin") > -1:
                        if items.find("Yes") > -1 or items.find("yes") > -1:
                            permitRootLogin = 1
                            continue
                    if items.find("Port") > -1 and not items.find("GatewayPorts") > -1:
                        sshPort = items.split(" ")[1].strip("\n")

                final_dic = {'status': 1, 'permitRootLogin': permitRootLogin, 'sshPort': sshPort}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:

                pathToKeyFile = "/root/.ssh/authorized_keys"

                cat = "sudo cat " + pathToKeyFile
                data = ProcessUtilities.outputExecutioner(cat).split('\n')

                json_data = "["
                checker = 0

                for items in data:
                    if items.find("ssh-rsa") > -1:
                        keydata = items.split(" ")

                        try:
                            key = "ssh-rsa " + keydata[1][:50] + "  ..  " + keydata[2]
                            try:
                                userName = keydata[2][:keydata[2].index("@")]
                            except:
                                userName = keydata[2]
                        except:
                            key = "ssh-rsa " + keydata[1][:50]
                            userName = ''



                        dic = {'userName': userName,
                               'key': key,
                               }

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'

                final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveSSHConfigs(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            type = data['type']
            sshPort = data['sshPort']
            rootLogin = data['rootLogin']

            if not is_safe_port(sshPort):
                return ACLManager.loadErrorJson('saveStatus', 0)

            if rootLogin == True:
                rootLogin = "1"
            else:
                rootLogin = "0"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " saveSSHConfigs --type " + shlex.quote(str(type)) + " --sshPort " + str(sshPort) + " --rootLogin " + rootLogin

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:

                csfPath = '/etc/csf'

                if os.path.exists(csfPath):
                    dataIn = {'protocol': 'TCP_IN', 'ports': sshPort}
                    self.modifyPorts(dataIn)
                    dataIn = {'protocol': 'TCP_OUT', 'ports': sshPort}
                    self.modifyPorts(dataIn)
                else:
                    try:
                        updateFW = FirewallRules.objects.get(name="SSHCustom")
                        FirewallUtilities.deleteRule("tcp", updateFW.port, "0.0.0.0/0")
                        updateFW.port = sshPort
                        updateFW.save()
                        FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                    except:
                        try:
                            newFireWallRule = FirewallRules(name="SSHCustom", port=sshPort, proto="tcp")
                            newFireWallRule.save()
                            FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                            command = 'firewall-cmd --permanent --remove-service=ssh'
                            ProcessUtilities.executioner(command)
                        except BaseException as msg:
                            logging.CyberCPLogFileWriter.writeToFile(str(msg))

                final_dic = {'status': 1, 'saveStatus': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 0, 'saveStatus': 0, "error_message": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0 ,'saveStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteSSHKey(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('delete_status', 0)

            key = data['key']

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " deleteSSHKey --key " + shlex.quote(key)

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                final_dic = {'status': 1, 'delete_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 1, 'delete_status': 1, "error_mssage": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_mssage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addSSHKey(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('add_status', 0)

            key = data['key']

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempPath, "w")
            writeToFile.write(key)
            writeToFile.close()

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " addSSHKey --tempPath " + tempPath

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                final_dic = {'status': 1, 'add_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 0, 'add_status': 0, "error_mssage": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_mssage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def loadModSecurityHome(self, request = None, userID = None):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            OLS = 1
            confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

            modSecInstalled = 0

            for items in httpdConfig:
                if items.find('module mod_security') > -1:
                    modSecInstalled = 1
                    break
        else:
            OLS = 0
            modSecInstalled = 1

        proc = httpProc(request, 'firewall/modSecurity.html',
                        {'modSecInstalled': modSecInstalled, 'OLS': OLS}, 'admin')
        return proc.render()

    def installModSec(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installModSec', 0)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
            execPath = execPath + " installModSec"

            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(3)

            final_json = json.dumps({'installModSec': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'installModSec': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusModSec(self, userID = None, data = None):
        try:

            command = "sudo cat " + modSec.installLogPath
            installStatus = ProcessUtilities.outputExecutioner(command)

            if installStatus.find("[200]") > -1:

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " installModSecConfigs"

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    pass
                else:
                    final_json = json.dumps({
                        'error_message': "Failed to install ModSecurity configurations.",
                        'requestStatus': installStatus,
                        'abort': 1,
                        'installed': 0,
                    })
                    return HttpResponse(final_json)

                final_json = json.dumps({
                    'error_message': "None",
                    'requestStatus': installStatus,
                    'abort': 1,
                    'installed': 1,
                })
                return HttpResponse(final_json)
            elif installStatus.find("[404]") > -1:

                final_json = json.dumps({
                    'abort': 1,
                    'installed': 0,
                    'error_message': "None",
                    'requestStatus': installStatus,
                })
                return HttpResponse(final_json)

            else:
                final_json = json.dumps({
                    'abort': 0,
                    'error_message': "None",
                    'requestStatus': installStatus,
                })
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchModSecSettings(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                modsecurity = 0
                SecAuditEngine = 0
                SecRuleEngine = 0
                SecDebugLogLevel = "9"
                SecAuditLogRelevantStatus = '^(?:5|4(?!04))'
                SecAuditLogParts = 'ABIJDEFHZ'
                SecAuditLogType = 'Serial'

                confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/httpd_config.conf')
                modSecPath = os.path.join(virtualHostUtilities.Server_root, 'modules', 'mod_security.so')

                if os.path.exists(modSecPath):
                    command = "sudo cat " + confPath
                    data = ProcessUtilities.outputExecutioner(command).split('\n')

                    for items in data:

                        if items.find('modsecurity ') > -1:
                            if items.find('on') > -1 or items.find('On') > -1:
                                modsecurity = 1
                                continue
                        if items.find('SecAuditEngine ') > -1:
                            if items.find('on') > -1 or items.find('On') > -1:
                                SecAuditEngine = 1
                                continue

                        if items.find('SecRuleEngine ') > -1:
                            if items.find('on') > -1 or items.find('On') > -1:
                                SecRuleEngine = 1
                                continue

                        if items.find('SecDebugLogLevel') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecDebugLogLevel':
                                SecDebugLogLevel = result[1]
                                continue
                        if items.find('SecAuditLogRelevantStatus') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecAuditLogRelevantStatus':
                                SecAuditLogRelevantStatus = result[1]
                                continue
                        if items.find('SecAuditLogParts') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecAuditLogParts':
                                SecAuditLogParts = result[1]
                                continue
                        if items.find('SecAuditLogType') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecAuditLogType':
                                SecAuditLogType = result[1]
                                continue

                    final_dic = {'fetchStatus': 1,
                                 'installed': 1,
                                 'SecRuleEngine': SecRuleEngine,
                                 'modsecurity': modsecurity,
                                 'SecAuditEngine': SecAuditEngine,
                                 'SecDebugLogLevel': SecDebugLogLevel,
                                 'SecAuditLogParts': SecAuditLogParts,
                                 'SecAuditLogRelevantStatus': SecAuditLogRelevantStatus,
                                 'SecAuditLogType': SecAuditLogType,
                                 }

                else:
                    final_dic = {'fetchStatus': 1,
                                 'installed': 0}
            else:
                SecAuditEngine = 0
                SecRuleEngine = 0
                SecDebugLogLevel = "9"
                SecAuditLogRelevantStatus = '^(?:5|4(?!04))'
                SecAuditLogParts = 'ABIJDEFHZ'
                SecAuditLogType = 'Serial'

                confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/modsec.conf')

                command = "sudo cat " + confPath

                data = ProcessUtilities.outputExecutioner(command).split('\n')

                for items in data:
                    if items.find('SecAuditEngine ') > -1:
                        if items.find('on') > -1 or items.find('On') > -1:
                            SecAuditEngine = 1
                            continue

                    if items.find('SecRuleEngine ') > -1:
                        if items.find('on') > -1 or items.find('On') > -1:
                            SecRuleEngine = 1
                            continue

                    if items.find('SecDebugLogLevel') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecDebugLogLevel':
                            SecDebugLogLevel = result[1]
                            continue
                    if items.find('SecAuditLogRelevantStatus') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecAuditLogRelevantStatus':
                            SecAuditLogRelevantStatus = result[1]
                            continue
                    if items.find('SecAuditLogParts') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecAuditLogParts':
                            SecAuditLogParts = result[1]
                            continue
                    if items.find('SecAuditLogType') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecAuditLogType':
                            SecAuditLogType = result[1]
                            continue

                final_dic = {'fetchStatus': 1,
                             'installed': 1,
                             'SecRuleEngine': SecRuleEngine,
                             'SecAuditEngine': SecAuditEngine,
                             'SecDebugLogLevel': SecDebugLogLevel,
                             'SecAuditLogParts': SecAuditLogParts,
                             'SecAuditLogRelevantStatus': SecAuditLogRelevantStatus,
                             'SecAuditLogType': SecAuditLogType,
                             }

            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveModSecConfigurations(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                modsecurity = data['modsecurity_status']
                SecAuditEngine = data['SecAuditEngine']
                SecRuleEngine = data['SecRuleEngine']
                SecDebugLogLevel = data['SecDebugLogLevel']
                SecAuditLogParts = data['SecAuditLogParts']
                SecAuditLogRelevantStatus = data['SecAuditLogRelevantStatus']
                SecAuditLogType = data['SecAuditLogType']

                if modsecurity == True:
                    modsecurity = "modsecurity  on"
                else:
                    modsecurity = "modsecurity  off"

                if SecAuditEngine == True:
                    SecAuditEngine = "SecAuditEngine on"
                else:
                    SecAuditEngine = "SecAuditEngine off"

                if SecRuleEngine == True:
                    SecRuleEngine = "SecRuleEngine On"
                else:
                    SecRuleEngine = "SecRuleEngine off"

                SecDebugLogLevel = "SecDebugLogLevel " + str(SecDebugLogLevel)
                SecAuditLogParts = "SecAuditLogParts " + str(SecAuditLogParts)
                SecAuditLogRelevantStatus = "SecAuditLogRelevantStatus " + SecAuditLogRelevantStatus
                SecAuditLogType = "SecAuditLogType " + SecAuditLogType

                ## writing data temporary to file


                tempConfigPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                confPath = open(tempConfigPath, "w")

                confPath.writelines(modsecurity + "\n")
                confPath.writelines(SecAuditEngine + "\n")
                confPath.writelines(SecRuleEngine + "\n")
                confPath.writelines(SecDebugLogLevel + "\n")
                confPath.writelines(SecAuditLogParts + "\n")
                confPath.writelines(SecAuditLogRelevantStatus + "\n")
                confPath.writelines(SecAuditLogType + "\n")

                confPath.close()

                ## save configuration data

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " saveModSecConfigs --tempConfigPath " + tempConfigPath

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'saveStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            else:
                SecAuditEngine = data['SecAuditEngine']
                SecRuleEngine = data['SecRuleEngine']
                SecDebugLogLevel = data['SecDebugLogLevel']
                SecAuditLogParts = data['SecAuditLogParts']
                SecAuditLogRelevantStatus = data['SecAuditLogRelevantStatus']
                SecAuditLogType = data['SecAuditLogType']

                if SecAuditEngine == True:
                    SecAuditEngine = "SecAuditEngine on"
                else:
                    SecAuditEngine = "SecAuditEngine off"

                if SecRuleEngine == True:
                    SecRuleEngine = "SecRuleEngine On"
                else:
                    SecRuleEngine = "SecRuleEngine off"

                SecDebugLogLevel = "SecDebugLogLevel " + str(SecDebugLogLevel)
                SecAuditLogParts = "SecAuditLogParts " + str(SecAuditLogParts)
                SecAuditLogRelevantStatus = "SecAuditLogRelevantStatus " + SecAuditLogRelevantStatus
                SecAuditLogType = "SecAuditLogType " + SecAuditLogType

                ## writing data temporary to file


                tempConfigPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                confPath = open(tempConfigPath, "w")

                confPath.writelines(SecAuditEngine + "\n")
                confPath.writelines(SecRuleEngine + "\n")
                confPath.writelines(SecDebugLogLevel + "\n")
                confPath.writelines(SecAuditLogParts + "\n")
                confPath.writelines(SecAuditLogRelevantStatus + "\n")
                confPath.writelines(SecAuditLogType + "\n")

                confPath.close()

                ## save configuration data

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " saveModSecConfigs --tempConfigPath " + tempConfigPath

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'saveStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def modSecRules(self, request = None, userID = None):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).split('\n')

            modSecInstalled = 0

            for items in httpdConfig:
                if items.find('module mod_security') > -1:
                    modSecInstalled = 1
                    break
        else:
            modSecInstalled = 1

        proc = httpProc(request, 'firewall/modSecurityRules.html',
                        {'modSecInstalled': modSecInstalled}, 'admin')
        return proc.render()

    def fetchModSecRules(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

                command = "sudo cat " + confPath
                httpdConfig = ProcessUtilities.outputExecutioner(command).split('\n')

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break

                rulesPath = os.path.join(virtualHostUtilities.Server_root + "/conf/modsec/rules.conf")

                if modSecInstalled:
                    command = "sudo cat " + rulesPath
                    currentModSecRules = ProcessUtilities.outputExecutioner(command)

                    final_dic = {'modSecInstalled': 1,
                                 'currentModSecRules': currentModSecRules}

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'modSecInstalled': 0}

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            else:
                rulesPath = os.path.join(virtualHostUtilities.Server_root + "/conf/rules.conf")

                command = "sudo cat " + rulesPath
                currentModSecRules = ProcessUtilities.outputExecutioner(command)

                final_dic = {'modSecInstalled': 1,
                             'currentModSecRules': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'modSecInstalled': 0,
                         'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveModSecRules(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            newModSecRules = data['modSecRules']

            ## writing data temporary to file

            rulesPath = open(modSec.tempRulesFile, "w")
            rulesPath.write(newModSecRules)
            rulesPath.close()

            ## save configuration data

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
            execPath = execPath + " saveModSecRules"
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def modSecRulesPacks(self, request = None, userID = None):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

            confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).split('\n')

            modSecInstalled = 0

            for items in httpdConfig:
                if items.find('module mod_security') > -1:
                    modSecInstalled = 1
                    break
        else:
            modSecInstalled = 1

        proc = httpProc(request, 'firewall/modSecurityRulesPacks.html',
                        {'modSecInstalled': modSecInstalled}, 'admin')
        return proc.render()

    def getOWASPAndComodoStatus(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

                command = "sudo cat " + confPath
                httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break

                comodoInstalled = 0
                owaspInstalled = 0

                if modSecInstalled:
                    command = "sudo cat " + confPath
                    httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

                    for items in httpdConfig:

                        if items.find('modsec/comodo') > -1:
                            comodoInstalled = 1
                        elif items.find('modsec/owasp') > -1:
                            owaspInstalled = 1

                        if owaspInstalled == 1 and comodoInstalled == 1:
                            break

                    # Check multiple locations for OWASP CRS installation
                    if owaspInstalled == 0:
                        # Check 1: rules.conf for OWASP includes
                        rulesConfPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/rules.conf")
                        if os.path.exists(rulesConfPath):
                            try:
                                command = "sudo cat " + rulesConfPath
                                rulesConfig = ProcessUtilities.outputExecutioner(command).splitlines()
                                for items in rulesConfig:
                                    # Check for OWASP includes in rules.conf (case-insensitive)
                                    if ('owasp' in items.lower() or 'crs-setup' in items.lower()) and \
                                       ('include' in items.lower() or 'modsecurity_rules_file' in items.lower()):
                                        owaspInstalled = 1
                                        break
                            except:
                                pass

                        # Check 2: owasp-master.conf exists and has rules loaded
                        if owaspInstalled == 0:
                            owaspMasterConf = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf")
                            if os.path.exists(owaspMasterConf):
                                try:
                                    command = "sudo cat " + owaspMasterConf
                                    owaspConfig = ProcessUtilities.outputExecutioner(command).splitlines()
                                    # Check if at least one rule file is enabled (not commented)
                                    for items in owaspConfig:
                                        if items.strip() and not items.strip().startswith('#') and 'include' in items.lower():
                                            owaspInstalled = 1
                                            break
                                except:
                                    pass

                        # Check 3: OWASP CRS directory exists with rules
                        if owaspInstalled == 0:
                            owaspRulesDir = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-3.0-master/rules")
                            if os.path.exists(owaspRulesDir):
                                try:
                                    command = "sudo ls " + owaspRulesDir + " | grep -c '.conf'"
                                    output = ProcessUtilities.outputExecutioner(command).strip()
                                    if output.isdigit() and int(output) > 0:
                                        # Rules exist, check if referenced in httpd_config.conf
                                        for items in httpdConfig:
                                            if 'owasp-modsecurity-crs' in items.lower() or 'owasp-master.conf' in items.lower():
                                                owaspInstalled = 1
                                                break
                                except:
                                    pass

                    final_dic = {
                        'modSecInstalled': 1,
                        'owaspInstalled': owaspInstalled,
                        'comodoInstalled': comodoInstalled
                    }

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'modSecInstalled': 0}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

            else:
                comodoInstalled = 0
                owaspInstalled = 0

                try:
                    command = 'sudo ls /usr/local/lsws/conf/comodo_litespeed/'
                    output = ProcessUtilities.outputExecutioner(command)

                    if output.find('No such') > -1:
                        comodoInstalled = 0
                    else:
                        comodoInstalled = 1

                except subprocess.CalledProcessError:
                    pass

                # Check multiple locations for OWASP in LiteSpeed Enterprise
                try:
                    command = 'cat /usr/local/lsws/conf/modsec.conf'
                    output = ProcessUtilities.outputExecutioner(command)
                    if output.find('modsec/owasp') > -1:
                        owaspInstalled = 1
                except:
                    pass

                # Also check owasp-master.conf for LSWS Enterprise
                if owaspInstalled == 0:
                    owaspMasterConf = '/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf'
                    if os.path.exists(owaspMasterConf):
                        try:
                            command = "cat " + owaspMasterConf
                            owaspConfig = ProcessUtilities.outputExecutioner(command).splitlines()
                            for items in owaspConfig:
                                if items.strip() and not items.strip().startswith('#') and 'include' in items.lower():
                                    owaspInstalled = 1
                                    break
                        except:
                            pass

                final_dic = {
                    'modSecInstalled': 1,
                    'owaspInstalled': owaspInstalled,
                    'comodoInstalled': comodoInstalled
                }
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'modSecInstalled': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installModSecRulesPack(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            packName = data['packName']

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " " + packName

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'installStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'installStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            else:
                # if packName == 'disableOWASP' or packName == 'installOWASP':
                #     final_json = json.dumps({'installStatus': 0, 'error_message': "OWASP will be available later.", })
                #     return HttpResponse(final_json)

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " " + packName
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'installStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'installStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getRulesFiles(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            packName = data['packName']

            confPath = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

            json_data = "["
            checker = 0
            counter = 0

            for items in httpdConfig:

                if items.find('modsec/' + packName) > -1:
                    counter = counter + 1
                    if items[0] == '#':
                        status = False
                    else:
                        status = True

                    fileName = items.lstrip('#')
                    fileName = fileName.split('/')[-1]

                    dic = {
                        'id': counter,
                        'fileName': fileName,
                        'packName': packName,
                        'status': status,

                    }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

            # if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            #     confPath = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')
            #
            #     command = "sudo cat " + confPath
            #     httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()
            #
            #     json_data = "["
            #     checker = 0
            #     counter = 0
            #
            #     for items in httpdConfig:
            #
            #         if items.find('modsec/' + packName) > -1:
            #             counter = counter + 1
            #             if items[0] == '#':
            #                 status = False
            #             else:
            #                 status = True
            #
            #             fileName = items.lstrip('#')
            #             fileName = fileName.split('/')[-1]
            #
            #             dic = {
            #                 'id': counter,
            #                 'fileName': fileName,
            #                 'packName': packName,
            #                 'status': status,
            #
            #             }
            #
            #             if checker == 0:
            #                 json_data = json_data + json.dumps(dic)
            #                 checker = 1
            #             else:
            #                 json_data = json_data + ',' + json.dumps(dic)
            #
            #     json_data = json_data + ']'
            #     final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            #     return HttpResponse(final_json)
            # else:
            #
            #     command = 'cat /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf'
            #     files = ProcessUtilities.outputExecutioner(command).splitlines()
            #
            #     json_data = "["
            #
            #     counter = 0
            #     checker = 0
            #     for fileName in files:
            #
            #         if fileName == 'categories.conf':
            #             continue
            #
            #         if fileName.endswith('bak'):
            #             status = 0
            #             fileName = fileName.rstrip('.bak')
            #         elif fileName.endswith('conf'):
            #             status = 1
            #         else:
            #             continue
            #
            #         dic = {
            #             'id': counter,
            #             'fileName': fileName,
            #             'packName': packName,
            #             'status': status,
            #
            #         }
            #
            #         counter = counter + 1
            #
            #         if checker == 0:
            #             json_data = json_data + json.dumps(dic)
            #             checker = 1
            #         else:
            #             json_data = json_data + ',' + json.dumps(dic)
            #
            #     json_data = json_data + ']'
            #     final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            #     return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def enableDisableRuleFile(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            packName = data['packName']
            fileName = data['fileName']
            currentStatus = data['status']

            if currentStatus == True:
                functionName = 'disableRuleFile'
            else:
                functionName = 'enableRuleFile'

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

            execPath = execPath + " " + functionName + ' --packName ' + packName + ' --fileName "%s"' % (fileName)

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def csf(self):
        csfInstalled = 1
        try:
            command = 'csf -h'
            output = ProcessUtilities.outputExecutioner(command)
            if output.find("command not found") > -1:
                csfInstalled = 0
        except subprocess.CalledProcessError:
            csfInstalled = 0

        proc = httpProc(self.request, 'firewall/csf.html',
                        {'csfInstalled': csfInstalled}, 'admin')
        return proc.render()

    def installCSF(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)


            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " installCSF"

            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(2)

            data_ret = {"installStatus": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'installStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusCSF(self):
        try:
            userID = self.request.session['userID']

            installStatus = ProcessUtilities.outputExecutioner("sudo cat " + CSF.installLogPath)

            if installStatus.find("[200]")>-1:

                command = 'sudo rm -f ' + CSF.installLogPath
                ProcessUtilities.executioner(command)

                final_json = json.dumps({
                                         'error_message': "None",
                                         'requestStatus': installStatus,
                                         'abort':1,
                                         'installed': 1,
                                         })
                return HttpResponse(final_json)
            elif installStatus.find("[404]") > -1:
                command = 'sudo rm -f ' + CSF.installLogPath
                ProcessUtilities.executioner(command)
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

        except BaseException as msg:
            final_dic = {'abort':1, 'installed':0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def removeCSF(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " removeCSF"
            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(2)

            data_ret = {"installStatus": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'installStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchCSFSettings(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

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

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': 'CSF is not installed.'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def changeStatus(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            controller = data['controller']
            status = data['status']

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " changeStatus --controller " + controller + " --status " + status
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {"status": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def modifyPorts(self, data = None):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            protocol = data['protocol']
            ports = data['ports']

            portsPath = '/home/cyberpanel/' + str(randint(1000, 9999))

            if os.path.exists(portsPath):
                os.remove(portsPath)

            writeToFile = open(portsPath, 'w')
            writeToFile.write(ports)
            writeToFile.close()

            command = 'chmod 600 %s' % (portsPath)
            ProcessUtilities.executioner(command)

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " modifyPorts --protocol " + shlex.quote(protocol) + " --ports " + portsPath
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {"status": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def modifyIPs(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            mode = data['mode']
            ipAddress = data['ipAddress']

            if mode == 'allowIP':
                CSF.allowIP(ipAddress)
            elif mode == 'blockIP':
                CSF.blockIP(ipAddress)

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def imunify(self):
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        fullAddress = '%s:%s' % (ipAddress, ProcessUtilities.fetchCurrentPort())

        data = {}
        data['ipAddress'] = fullAddress

        data['CL'] = 1

        if os.path.exists(FirewallManager.imunifyPath):
            data['imunify'] = 1
        else:
            data['imunify'] = 0

        if data['CL'] == 0:
            proc = httpProc(self.request, 'firewall/notAvailable.html',
                            data, 'admin')
            return proc.render()
        elif data['imunify'] == 0:
            proc = httpProc(self.request, 'firewall/notAvailable.html',
                            data, 'admin')
            return proc.render()
        else:
            proc = httpProc(self.request, 'firewall/imunify.html',
                            data, 'admin')
            return proc.render()

    def submitinstallImunify(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          'Not authorized to install container packages. [404].',
                                                          1)
                return 0

            data = json.loads(self.request.body)

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
            execPath = execPath + " --function submitinstallImunify --key %s" % (data['key'])
            ProcessUtilities.popenExecutioner(execPath)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def imunifyAV(self):
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        fullAddress = '%s:%s' % (ipAddress, ProcessUtilities.fetchCurrentPort())

        data = {}
        data['ipAddress'] = fullAddress

        if os.path.exists(FirewallManager.imunifyAVPath):
            data['imunify'] = 1
        else:
            data['imunify'] = 0

        if data['imunify'] == 0:
            proc = httpProc(self.request, 'firewall/notAvailableAV.html',
                            data, 'admin')
            return proc.render()
        else:
            proc = httpProc(self.request, 'firewall/imunifyAV.html',
                            data, 'admin')
            return proc.render()

    def submitinstallImunifyAV(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          'Not authorized to install container packages. [404].',
                                                          1)
                return 0

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
            execPath = execPath + " --function submitinstallImunifyAV"
            ProcessUtilities.popenExecutioner(execPath)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)



    def litespeed_ent_conf(self, request = None, userID = None):
        proc = httpProc(request, 'firewall/litespeed_ent_conf.html',
                        None, 'admin')
        return proc.render()

    def fetchlitespeed_Conf(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            file_path = "/usr/local/lsws/conf/pre_main_global.conf"

            if not os.path.exists(file_path):
                command = "touch /usr/local/lsws/conf/pre_main_global.conf"
                ProcessUtilities.executioner(command)


                command = f'cat {file_path}'

                currentModSecRules = ProcessUtilities.outputExecutioner(command)
                final_dic = {'status': 1,
                             'currentLitespeed_conf': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                command = f'cat {file_path}'

                currentModSecRules = ProcessUtilities.outputExecutioner(command)
                final_dic = {'status': 1,
                             'currentLitespeed_conf': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


    def saveLitespeed_conf(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            file_path = "/usr/local/lsws/conf/pre_main_global.conf"

            command = f'rm -f {file_path}'
            ProcessUtilities.executioner(command)

            currentLitespeed_conf = data['modSecRules']

            tempRulesPath = '/home/cyberpanel/pre_main_global.conf'

            WriteToFile = open(tempRulesPath, 'w')
            WriteToFile.write(currentLitespeed_conf)
            WriteToFile.close()

            command = f'mv {tempRulesPath} {file_path}'
            ProcessUtilities.executioner(command)

            command = f'chmod 644 {file_path} && chown lsadm:lsadm {file_path}'
            ProcessUtilities.executioner(command, None, True)


            command = f'cat {file_path}'

            currentModSecRules = ProcessUtilities.outputExecutioner(command)
            final_dic = {'status': 1,
                             'currentLitespeed_conf': currentModSecRules}

            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def exportFirewallRules(self, userID = None):
        """
        Export all custom firewall rules to a JSON file, excluding default CyberPanel rules
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('exportStatus', 0)

            # Get all firewall rules
            rules = FirewallRules.objects.all()
            
            # Default CyberPanel rules to exclude
            default_rules = ['CyberPanel Admin', 'SSHCustom']
            
            # Filter out default rules
            custom_rules = []
            for rule in rules:
                if rule.name not in default_rules:
                    custom_rules.append({
                        'name': rule.name,
                        'proto': rule.proto,
                        'port': rule.port,
                        'ipAddress': rule.ipAddress
                    })
            
            # Create export data with metadata
            export_data = {
                'version': '1.0',
                'exported_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_rules': len(custom_rules),
                'rules': custom_rules
            }
            
            # Create JSON response with file download
            json_content = json.dumps(export_data, indent=2)
            
            logging.CyberCPLogFileWriter.writeToFile(f"Firewall rules exported successfully. Total rules: {len(custom_rules)}")
            
            # Return file as download
            response = HttpResponse(json_content, content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="firewall_rules_export_{int(time.time())}.json"'
            
            return response

        except BaseException as msg:
            final_dic = {'exportStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def importFirewallRules(self, userID = None, data = None):
        """
        Import firewall rules from a JSON file
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('importStatus', 0)

            # Handle file upload
            if hasattr(self.request, 'FILES') and 'import_file' in self.request.FILES:
                import_file = self.request.FILES['import_file']
                
                # Read file content
                import_data = json.loads(import_file.read().decode('utf-8'))
            else:
                # Fallback to file path method
                import_file_path = data.get('import_file_path', '')
                
                if not import_file_path or not os.path.exists(import_file_path):
                    final_dic = {'importStatus': 0, 'error_message': 'Import file not found or invalid path'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                
                # Read and parse the import file
                with open(import_file_path, 'r') as f:
                    import_data = json.load(f)
            
            # Validate the import data structure
            if 'rules' not in import_data:
                final_dic = {'importStatus': 0, 'error_message': 'Invalid import file format. Missing rules array.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # Default CyberPanel rules to exclude from import
            default_rules = ['CyberPanel Admin', 'SSHCustom']
            
            for rule_data in import_data['rules']:
                try:
                    # Skip default rules
                    if rule_data.get('name', '') in default_rules:
                        skipped_count += 1
                        continue
                    
                    # Check if rule already exists
                    existing_rule = FirewallRules.objects.filter(
                        name=rule_data['name'],
                        proto=rule_data['proto'],
                        port=rule_data['port'],
                        ipAddress=rule_data['ipAddress']
                    ).first()
                    
                    if existing_rule:
                        skipped_count += 1
                        continue
                    
                    # Add the rule to the system firewall
                    FirewallUtilities.addRule(
                        rule_data['proto'], 
                        rule_data['port'], 
                        rule_data['ipAddress']
                    )
                    
                    # Add the rule to the database
                    new_rule = FirewallRules(
                        name=rule_data['name'],
                        proto=rule_data['proto'],
                        port=rule_data['port'],
                        ipAddress=rule_data['ipAddress']
                    )
                    new_rule.save()
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Rule '{rule_data.get('name', 'Unknown')}': {str(e)}")
                    logging.CyberCPLogFileWriter.writeToFile(f"Error importing rule {rule_data.get('name', 'Unknown')}: {str(e)}")
            
            logging.CyberCPLogFileWriter.writeToFile(f"Firewall rules import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}")
            
            final_dic = {
                'importStatus': 1,
                'error_message': "None",
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'error_count': error_count,
                'errors': errors
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'importStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)








