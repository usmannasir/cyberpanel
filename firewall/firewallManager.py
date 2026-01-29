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
import tempfile
from plogical.acl import ACLManager
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

    def modifyRule(self, userID=None, data=None):
        """
        Modify an existing firewall rule
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modify_status', 0)

            ruleID = data.get('id')
            newRuleName = data.get('ruleName', '').strip()
            newRuleProtocol = data.get('ruleProtocol', '').strip()
            newRulePort = data.get('rulePort', '').strip()
            newRuleIP = data.get('ruleIP', '').strip()

            # Validate inputs
            if not newRuleName:
                final_dic = {'status': 0, 'modify_status': 0, 'error_message': 'Rule name is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if not newRuleProtocol or newRuleProtocol not in ['tcp', 'udp']:
                final_dic = {'status': 0, 'modify_status': 0, 'error_message': 'Valid protocol (tcp/udp) is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if not newRulePort:
                final_dic = {'status': 0, 'modify_status': 0, 'error_message': 'Port is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if not newRuleIP:
                final_dic = {'status': 0, 'modify_status': 0, 'error_message': 'IP address is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Get existing rule
            try:
                existingRule = FirewallRules.objects.get(id=ruleID)
            except FirewallRules.DoesNotExist:
                final_dic = {'status': 0, 'modify_status': 0, 'error_message': 'Rule not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Check if anything changed
            changed = False
            if (existingRule.name != newRuleName or 
                existingRule.proto != newRuleProtocol or 
                existingRule.port != newRulePort or 
                existingRule.ipAddress != newRuleIP):
                changed = True

            if changed:
                # Check if new rule already exists (different ID)
                existingDuplicate = FirewallRules.objects.filter(
                    name=newRuleName,
                    proto=newRuleProtocol,
                    port=newRulePort,
                    ipAddress=newRuleIP
                ).exclude(id=ruleID).first()

                if existingDuplicate:
                    final_dic = {'status': 0, 'modify_status': 0, 'error_message': 'A rule with these settings already exists'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                # Delete old firewall rule
                try:
                    FirewallUtilities.deleteRule(existingRule.proto, existingRule.port, existingRule.ipAddress)
                    logging.CyberCPLogFileWriter.writeToFile(f'Removed old firewall rule: {existingRule.proto}/{existingRule.port}/{existingRule.ipAddress}')
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not remove old firewall rule: {str(e)}')

                # Add new firewall rule
                try:
                    FirewallUtilities.addRule(newRuleProtocol, newRulePort, newRuleIP)
                    logging.CyberCPLogFileWriter.writeToFile(f'Added new firewall rule: {newRuleProtocol}/{newRulePort}/{newRuleIP}')
                except Exception as e:
                    final_dic = {'status': 0, 'modify_status': 0, 'error_message': f'Failed to add firewall rule: {str(e)}'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                # Update database record
                existingRule.name = newRuleName
                existingRule.proto = newRuleProtocol
                existingRule.port = newRulePort
                existingRule.ipAddress = newRuleIP
                existingRule.save()

            final_dic = {'status': 1, 'modify_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'modify_status': 0, 'error_message': str(msg)}
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

            if rootLogin == True:
                rootLogin = "1"
            else:
                rootLogin = "0"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " saveSSHConfigs --type " + str(type) + " --sshPort " + sshPort + " --rootLogin " + rootLogin

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
            execPath = execPath + " deleteSSHKey --key '" + key + "'"

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
                        # Check for Comodo rules
                        if items.find('modsec/comodo') > -1:
                            comodoInstalled = 1
                        # Check for OWASP rules - improved detection
                        elif items.find('modsec/owasp') > -1 or items.find('owasp-modsecurity-crs') > -1:
                            owaspInstalled = 1

                        if owaspInstalled == 1 and comodoInstalled == 1:
                            break

                    # Also check rules.conf for manual OWASP installations (case-insensitive)
                    if owaspInstalled == 0:
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

                    # Additional check: verify OWASP files actually exist
                    if owaspInstalled == 0:
                        owaspPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-4.18.0")
                        if os.path.exists(owaspPath) and os.path.exists(os.path.join(owaspPath, "owasp-master.conf")):
                            owaspInstalled = 1

                    # Additional check: verify Comodo files actually exist
                    if comodoInstalled == 0:
                        comodoPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/comodo")
                        if os.path.exists(comodoPath) and os.path.exists(os.path.join(comodoPath, "modsecurity.conf")):
                            comodoInstalled = 1

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

                try:
                    command = 'cat /usr/local/lsws/conf/modsec.conf'
                    output = ProcessUtilities.outputExecutioner(command)
                    if output.find('modsec/owasp') > -1:
                        owaspInstalled = 1
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
            execPath = execPath + " modifyPorts --protocol " + protocol + " --ports " + portsPath
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

        # Auto-fix PHP-FPM issues when accessing Imunify360 page
        try:
            from plogical import upgrade
            logging.CyberCPLogFileWriter.writeToFile("Auto-fixing PHP-FPM pool configurations for Imunify360 compatibility...")
            fix_result = upgrade.Upgrade.CreateMissingPoolsforFPM()
            if fix_result == 0:
                logging.CyberCPLogFileWriter.writeToFile("PHP-FPM pool configurations auto-fixed successfully")
            else:
                logging.CyberCPLogFileWriter.writeToFile("Warning: PHP-FPM auto-fix had issues")
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in auto-fix for Imunify360: {str(e)}")

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

        # Auto-fix PHP-FPM issues when accessing ImunifyAV page
        try:
            from plogical import upgrade
            logging.CyberCPLogFileWriter.writeToFile("Auto-fixing PHP-FPM pool configurations for ImunifyAV compatibility...")
            fix_result = upgrade.Upgrade.CreateMissingPoolsforFPM()
            if fix_result == 0:
                logging.CyberCPLogFileWriter.writeToFile("PHP-FPM pool configurations auto-fixed successfully")
            else:
                logging.CyberCPLogFileWriter.writeToFile("Warning: PHP-FPM auto-fix had issues")
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in auto-fix for ImunifyAV: {str(e)}")

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

    def getBannedIPs(self, userID=None):
        """
        Get list of banned IP addresses
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            # For now, we'll use a simple file-based storage
            # In production, you might want to use a database
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            
            banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        banned_ips = json.load(f)
                except:
                    banned_ips = []
            
            # Filter out expired bans and format data consistently
            current_time = time.time()
            active_banned_ips = []
            
            for banned_ip in banned_ips:
                # Get original values
                expires_val = banned_ip.get('expires')
                banned_on_val = banned_ip.get('banned_on', current_time)
                
                # Convert banned_on to timestamp if it's a string
                if isinstance(banned_on_val, str):
                    try:
                        # Try parsing formatted date string
                        banned_on_val = time.mktime(time.strptime(banned_on_val, '%Y-%m-%d %H:%M:%S'))
                    except:
                        banned_on_val = current_time
                elif not isinstance(banned_on_val, (int, float)):
                    banned_on_val = current_time
                
                # Check if expired
                is_expired = False
                if expires_val == 'Never' or expires_val is None:
                    expires_timestamp = None
                    expires_display = 'Never'
                elif isinstance(expires_val, str):
                    if expires_val == 'Never':
                        expires_timestamp = None
                        expires_display = 'Never'
                    else:
                        try:
                            expires_timestamp = time.mktime(time.strptime(expires_val, '%Y-%m-%d %H:%M:%S'))
                            expires_display = expires_val
                        except:
                            expires_timestamp = None
                            expires_display = 'Never'
                else:
                    expires_timestamp = expires_val
                    if expires_val > current_time:
                        expires_display = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_val))
                    else:
                        expires_display = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_val))
                        is_expired = True
                
                # Determine if active
                if expires_timestamp is None:
                    is_active = True
                else:
                    is_active = expires_timestamp > current_time and not is_expired
                
                # Format banned_on for display
                banned_on_display = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(banned_on_val))
                
                # Create formatted entry
                formatted_ip = {
                    'id': banned_ip.get('id'),
                    'ip': banned_ip.get('ip'),
                    'reason': banned_ip.get('reason', ''),
                    'duration': banned_ip.get('duration', 'never'),
                    'banned_on': banned_on_display,  # String for display
                    'banned_on_timestamp': banned_on_val * 1000,  # Milliseconds for AngularJS date filter
                    'expires': expires_display,  # String for display
                    'expires_timestamp': expires_timestamp * 1000 if expires_timestamp else None,  # Milliseconds for AngularJS
                    'active': is_active
                }
                
                active_banned_ips.append(formatted_ip)
            
            final_dic = {'status': 1, 'bannedIPs': active_banned_ips}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addBannedIP(self, userID=None, data=None):
        """
        Add a banned IP address
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('status', 0)

            ip = data.get('ip', '').strip()
            reason = data.get('reason', '').strip()
            duration = data.get('duration', '24h')

            if not ip or not reason:
                final_dic = {'status': 0, 'error_message': 'IP address and reason are required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Validate IP address format
            import ipaddress
            try:
                ipaddress.ip_address(ip.split('/')[0])  # Handle CIDR notation
            except ValueError:
                final_dic = {'status': 0, 'error_message': 'Invalid IP address format'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Calculate expiration time
            current_time = time.time()
            if duration == 'permanent':
                expires = 'Never'
            else:
                duration_map = {
                    '1h': 3600,
                    '24h': 86400,
                    '7d': 604800,
                    '30d': 2592000
                }
                duration_seconds = duration_map.get(duration, 86400)
                expires = current_time + duration_seconds

            # Load existing banned IPs
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        banned_ips = json.load(f)
                except:
                    banned_ips = []

            # Check if IP is already banned
            for banned_ip in banned_ips:
                if banned_ip.get('ip') == ip and banned_ip.get('active', True):
                    final_dic = {'status': 0, 'error_message': f'IP address {ip} is already banned'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

            # Add new banned IP
            new_banned_ip = {
                'id': int(time.time()),
                'ip': ip,
                'reason': reason,
                'duration': duration,
                'banned_on': current_time,
                'expires': expires,
                'active': True
            }
            banned_ips.append(new_banned_ip)

            # Write to temp file in /tmp (web server user has write permissions here)
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f'banned_ips_{int(time.time())}.json')
            
            with open(temp_file, 'w') as f:
                json.dump(banned_ips, f, indent=2)
            
            # Ensure /etc/cyberpanel directory exists with proper permissions
            command = f'mkdir -p {os.path.dirname(banned_ips_file)} && chmod 755 {os.path.dirname(banned_ips_file)}'
            ProcessUtilities.executioner(command, None, True)
            
            # Move temp file to final location and set permissions using ProcessUtilities
            command = f'mv {temp_file} {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)
            
            command = f'chmod 644 {banned_ips_file} && chown root:root {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)

            # Apply firewall rule to block the IP using ProcessUtilities (handles sudo)
            try:
                # Check if rule already exists to avoid duplicate rules
                check_command = f"iptables -C INPUT -s {ip} -j DROP 2>&1"
                check_result = ProcessUtilities.executioner(check_command, None, True)
                
                # If rule doesn't exist (check returns non-zero), add it
                if check_result != 0:
                    # Add iptables rule to block the IP using ProcessUtilities (handles sudo)
                    command = f"iptables -A INPUT -s {ip} -j DROP"
                    result = ProcessUtilities.executioner(command, None, True)
                    
                    if result == 0:
                        logging.CyberCPLogFileWriter.writeToFile(f'Successfully added iptables rule to ban IP {ip} with reason: {reason}')
                    else:
                        logging.CyberCPLogFileWriter.writeToFile(f'Warning: Failed to add iptables rule for {ip} (exit code: {result}), but IP was added to banned list')
                        # Don't fail the entire operation - IP is still in banned list
                else:
                    logging.CyberCPLogFileWriter.writeToFile(f'IPTables rule already exists for {ip}, skipping')
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Error adding iptables rule for {ip}: {str(e)}, but IP was added to banned list')
                # Don't fail the entire operation - IP is still in banned list

            final_dic = {'status': 1, 'message': f'IP address {ip} has been banned successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def removeBannedIP(self, userID=None, data=None):
        """
        Remove/unban an IP address
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            banned_ip_id = data.get('id')

            # Load existing banned IPs
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        banned_ips = json.load(f)
                except:
                    banned_ips = []

            # Find and update the banned IP
            ip_to_unban = None
            for banned_ip in banned_ips:
                if banned_ip.get('id') == banned_ip_id:
                    banned_ip['active'] = False
                    banned_ip['unbanned_on'] = time.time()
                    ip_to_unban = banned_ip['ip']
                    break

            if not ip_to_unban:
                final_dic = {'status': 0, 'error_message': 'Banned IP not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Write to temp file in /tmp (web server user has write permissions here)
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f'banned_ips_{int(time.time())}.json')
            
            with open(temp_file, 'w') as f:
                json.dump(banned_ips, f, indent=2)
            
            # Ensure /etc/cyberpanel directory exists with proper permissions
            command = f'mkdir -p {os.path.dirname(banned_ips_file)} && chmod 755 {os.path.dirname(banned_ips_file)}'
            ProcessUtilities.executioner(command, None, True)
            
            # Move temp file to final location and set permissions using ProcessUtilities
            command = f'mv {temp_file} {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)
            
            command = f'chmod 644 {banned_ips_file} && chown root:root {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)

            # Remove iptables rule
            try:
                # Remove iptables rule to unblock the IP
                if '/' in ip_to_unban:
                    # CIDR notation
                    subprocess.run(['iptables', '-D', 'INPUT', '-s', ip_to_unban, '-j', 'DROP'], check=False)
                else:
                    # Single IP
                    subprocess.run(['iptables', '-D', 'INPUT', '-s', ip_to_unban, '-j', 'DROP'], check=False)
                
                logging.CyberCPLogFileWriter.writeToFile(f'Unbanned IP {ip_to_unban}')
            except subprocess.CalledProcessError as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Failed to remove iptables rule for {ip_to_unban}: {str(e)}')

            final_dic = {'status': 1, 'message': f'IP address {ip_to_unban} has been unbanned successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def modifyBannedIP(self, userID=None, data=None):
        """
        Modify a banned IP address (update reason and/or expiration)
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            banned_ip_id = data.get('id')
            new_ip = data.get('ip', '').strip()
            reason = data.get('reason', '').strip()
            duration = data.get('duration', 'never')

            if not new_ip:
                final_dic = {'status': 0, 'error_message': 'IP address is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Validate IP address format
            import ipaddress
            try:
                ipaddress.ip_address(new_ip.split('/')[0])  # Handle CIDR notation
            except ValueError:
                final_dic = {'status': 0, 'error_message': 'Invalid IP address format'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            if not reason:
                final_dic = {'status': 0, 'error_message': 'Reason is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Load existing banned IPs
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        banned_ips = json.load(f)
                except:
                    banned_ips = []

            # Find and update the banned IP
            old_ip = None
            found = False
            for banned_ip in banned_ips:
                if banned_ip.get('id') == banned_ip_id:
                    found = True
                    old_ip = banned_ip['ip']
                    
                    # Check if new IP is already banned (and not the same record)
                    ip_changed = (new_ip != old_ip)
                    if ip_changed:
                        for other_banned_ip in banned_ips:
                            if other_banned_ip.get('id') != banned_ip_id and other_banned_ip.get('ip') == new_ip and other_banned_ip.get('active', True):
                                final_dic = {'status': 0, 'error_message': f'IP address {new_ip} is already banned'}
                                final_json = json.dumps(final_dic)
                                return HttpResponse(final_json)
                    
                    # Update IP address if changed
                    if ip_changed:
                        # Remove old iptables rule
                        try:
                            if '/' in old_ip:
                                subprocess.run(['iptables', '-D', 'INPUT', '-s', old_ip, '-j', 'DROP'], check=False)
                            else:
                                subprocess.run(['iptables', '-D', 'INPUT', '-s', old_ip, '-j', 'DROP'], check=False)
                            logging.CyberCPLogFileWriter.writeToFile(f'Removed iptables rule for old IP {old_ip}')
                        except Exception as e:
                            logging.CyberCPLogFileWriter.writeToFile(f'Warning: Could not remove old iptables rule for {old_ip}: {str(e)}')
                        
                        # Add new iptables rule
                        try:
                            if '/' in new_ip:
                                subprocess.run(['iptables', '-A', 'INPUT', '-s', new_ip, '-j', 'DROP'], check=True)
                            else:
                                subprocess.run(['iptables', '-A', 'INPUT', '-s', new_ip, '-j', 'DROP'], check=True)
                            logging.CyberCPLogFileWriter.writeToFile(f'Added iptables rule for new IP {new_ip}')
                        except subprocess.CalledProcessError as e:
                            final_dic = {'status': 0, 'error_message': f'Failed to add firewall rule for IP {new_ip}: {str(e)}'}
                            final_json = json.dumps(final_dic)
                            return HttpResponse(final_json)
                        
                        banned_ip['ip'] = new_ip
                    
                    # Update reason
                    banned_ip['reason'] = reason
                    
                    # Update expiration if duration changed
                    if duration == 'never' or duration == 'permanent':
                        banned_ip['expires'] = 'Never'
                        banned_ip['duration'] = 'never'
                    else:
                        # Calculate new expiration time
                        current_time = time.time()
                        duration_map = {
                            '1h': 3600,
                            '6h': 21600,
                            '12h': 43200,
                            '24h': 86400,
                            '48h': 172800,
                            '7d': 604800,
                            '30d': 2592000
                        }
                        duration_seconds = duration_map.get(duration, 86400)
                        banned_ip['expires'] = current_time + duration_seconds
                        banned_ip['duration'] = duration
                    
                    break

            if not found:
                final_dic = {'status': 0, 'error_message': 'Banned IP record not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Write to temp file in /tmp (web server user has write permissions here)
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f'banned_ips_{int(time.time())}.json')
            
            with open(temp_file, 'w') as f:
                json.dump(banned_ips, f, indent=2)
            
            # Ensure /etc/cyberpanel directory exists with proper permissions
            command = f'mkdir -p {os.path.dirname(banned_ips_file)} && chmod 755 {os.path.dirname(banned_ips_file)}'
            ProcessUtilities.executioner(command, None, True)
            
            # Move temp file to final location and set permissions using ProcessUtilities
            command = f'mv {temp_file} {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)
            
            command = f'chmod 644 {banned_ips_file} && chown root:root {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)

            ip_display = new_ip if new_ip != old_ip else old_ip
            change_msg = f'IP changed from {old_ip} to {new_ip}' if new_ip != old_ip else f'IP unchanged ({old_ip})'
            logging.CyberCPLogFileWriter.writeToFile(f'Modified banned IP record: {change_msg}, reason={reason}, duration={duration}')

            final_dic = {'status': 1, 'message': f'Banned IP has been modified successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteBannedIP(self, userID=None, data=None):
        """
        Permanently delete a banned IP record
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            banned_ip_id = data.get('id')

            # Load existing banned IPs
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        banned_ips = json.load(f)
                except:
                    banned_ips = []

            # Find and remove the banned IP
            ip_to_delete = None
            updated_banned_ips = []
            for banned_ip in banned_ips:
                if banned_ip.get('id') == banned_ip_id:
                    ip_to_delete = banned_ip['ip']
                else:
                    updated_banned_ips.append(banned_ip)

            if not ip_to_delete:
                final_dic = {'status': 0, 'error_message': 'Banned IP record not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            # Write to temp file in /tmp (web server user has write permissions here)
            temp_dir = tempfile.gettempdir()
            temp_file = os.path.join(temp_dir, f'banned_ips_{int(time.time())}.json')
            with open(temp_file, 'w') as f:
                json.dump(updated_banned_ips, f, indent=2)
            
            # Ensure /etc/cyberpanel directory exists with proper permissions
            command = f'mkdir -p {os.path.dirname(banned_ips_file)} && chmod 755 {os.path.dirname(banned_ips_file)}'
            ProcessUtilities.executioner(command, None, True)
            
            # Move temp file to final location and set permissions using ProcessUtilities
            command = f'mv {temp_file} {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)
            
            command = f'chmod 644 {banned_ips_file} && chown root:root {banned_ips_file}'
            ProcessUtilities.executioner(command, None, True)

            # Remove iptables rule to unban the IP
            try:
                # Remove iptables rule to unblock the IP
                if '/' in ip_to_delete:
                    # CIDR notation
                    subprocess.run(['iptables', '-D', 'INPUT', '-s', ip_to_delete, '-j', 'DROP'], check=False)
                else:
                    # Single IP
                    subprocess.run(['iptables', '-D', 'INPUT', '-s', ip_to_delete, '-j', 'DROP'], check=False)
                
                logging.CyberCPLogFileWriter.writeToFile(f'Deleted and unbanned IP {ip_to_delete}')
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Failed to remove iptables rule for {ip_to_delete}: {str(e)}')

            logging.CyberCPLogFileWriter.writeToFile(f'Deleted banned IP record for {ip_to_delete}')

            final_dic = {'status': 1, 'message': f'Banned IP record for {ip_to_delete} has been deleted successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def exportFirewallRules(self, userID=None):
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

    def importFirewallRules(self, userID=None, data=None):
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

    def exportBannedIPs(self, userID=None):
        """
        Export all banned IPs to a JSON file
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('exportStatus', 0)

            # Load banned IPs from file
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        banned_ips = json.load(f)
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error reading banned IPs file: {str(e)}")
                    banned_ips = []
            
            # Filter out expired bans for export (optional - you might want to include all)
            current_time = time.time()
            active_banned_ips = []
            for banned_ip in banned_ips:
                expires_val = banned_ip.get('expires')
                expires_timestamp = banned_ip.get('expires_timestamp')
                
                # Include if never expires or not yet expired
                if expires_val == 'Never' or expires_timestamp is None:
                    active_banned_ips.append(banned_ip)
                elif isinstance(expires_timestamp, (int, float)) and expires_timestamp > current_time:
                    active_banned_ips.append(banned_ip)
            
            # Create export data with metadata
            export_data = {
                'version': '1.0',
                'exported_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_banned_ips': len(active_banned_ips),
                'banned_ips': active_banned_ips
            }
            
            # Create JSON response with file download
            json_content = json.dumps(export_data, indent=2)
            
            logging.CyberCPLogFileWriter.writeToFile(f"Banned IPs exported successfully. Total IPs: {len(active_banned_ips)}")
            
            # Return file as download
            response = HttpResponse(json_content, content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="banned_ips_export_{int(time.time())}.json"'
            
            return response

        except BaseException as msg:
            final_dic = {'exportStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def importBannedIPs(self, userID=None, data=None):
        """
        Import banned IPs from a JSON file
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
                import_file_path = data.get('import_file_path', '') if data else ''
                
                if not import_file_path or not os.path.exists(import_file_path):
                    final_dic = {'importStatus': 0, 'error_message': 'Import file not found or invalid path'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                
                # Read and parse the import file
                with open(import_file_path, 'r') as f:
                    import_data = json.load(f)
            
            # Validate the import data structure
            if 'banned_ips' not in import_data:
                final_dic = {'importStatus': 0, 'error_message': 'Invalid import file format. Missing banned_ips array.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # Load existing banned IPs
            banned_ips_file = '/etc/cyberpanel/banned_ips.json'
            existing_banned_ips = []
            if os.path.exists(banned_ips_file):
                try:
                    with open(banned_ips_file, 'r') as f:
                        existing_banned_ips = json.load(f)
                except:
                    existing_banned_ips = []
            
            # Create a set of existing IPs for quick lookup
            existing_ips = {banned_ip.get('ip') for banned_ip in existing_banned_ips}
            
            # Import IP address validation
            import ipaddress
            
            for banned_ip_data in import_data['banned_ips']:
                try:
                    ip_address = banned_ip_data.get('ip', '').strip()
                    reason = banned_ip_data.get('reason', '').strip()
                    
                    # Validate IP address
                    if not ip_address:
                        error_count += 1
                        errors.append(f"Invalid entry: Missing IP address")
                        continue
                    
                    try:
                        ipaddress.ip_address(ip_address.split('/')[0])  # Handle CIDR notation
                    except ValueError:
                        error_count += 1
                        errors.append(f"IP '{ip_address}': Invalid IP address format")
                        continue
                    
                    # Check if IP already exists
                    if ip_address in existing_ips:
                        skipped_count += 1
                        continue
                    
                    # Validate reason
                    if not reason:
                        reason = 'Imported from backup'
                    
                    # Get duration or calculate from expires
                    duration = banned_ip_data.get('duration', 'never')
                    expires = banned_ip_data.get('expires', 'Never')
                    expires_timestamp = banned_ip_data.get('expires_timestamp')
                    
                    # Calculate expiration if needed
                    if expires == 'Never' or expires_timestamp is None:
                        expires_timestamp = None
                        expires_display = 'Never'
                        duration = 'never'
                    elif expires_timestamp and isinstance(expires_timestamp, (int, float)):
                        expires_display = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(expires_timestamp))
                    else:
                        expires_display = expires if isinstance(expires, str) else 'Never'
                        expires_timestamp = None
                    
                    # Create banned IP entry
                    banned_on = banned_ip_data.get('banned_on', time.time())
                    if isinstance(banned_on, str):
                        try:
                            banned_on = time.mktime(time.strptime(banned_on, '%Y-%m-%d %H:%M:%S'))
                        except:
                            banned_on = time.time()
                    
                    new_banned_ip = {
                        'id': banned_ip_data.get('id', randint(100000, 999999)),
                        'ip': ip_address,
                        'reason': reason,
                        'banned_on': banned_on,
                        'banned_on_timestamp': banned_on if isinstance(banned_on, (int, float)) else time.time(),
                        'expires': expires_display,
                        'expires_timestamp': expires_timestamp,
                        'duration': duration,
                        'active': True
                    }
                    
                    # Add iptables rule
                    try:
                        if '/' in ip_address:
                            subprocess.run(['iptables', '-A', 'INPUT', '-s', ip_address, '-j', 'DROP'], check=True)
                        else:
                            subprocess.run(['iptables', '-A', 'INPUT', '-s', ip_address, '-j', 'DROP'], check=True)
                        logging.CyberCPLogFileWriter.writeToFile(f'Added iptables rule for imported IP {ip_address}')
                    except subprocess.CalledProcessError as e:
                        error_count += 1
                        errors.append(f"IP '{ip_address}': Failed to add firewall rule - {str(e)}")
                        continue
                    
                    # Add to existing list
                    existing_banned_ips.append(new_banned_ip)
                    existing_ips.add(ip_address)
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"IP '{banned_ip_data.get('ip', 'Unknown')}': {str(e)}")
                    logging.CyberCPLogFileWriter.writeToFile(f"Error importing banned IP {banned_ip_data.get('ip', 'Unknown')}: {str(e)}")
            
            # Save updated banned IPs
            if imported_count > 0 or error_count > 0:
                try:
                    # Create temp file
                    temp_file = f'/tmp/banned_ips_{randint(100000, 999999)}.json'
                    with open(temp_file, 'w') as f:
                        json.dump(existing_banned_ips, f, indent=2)
                    
                    # Ensure directory exists
                    command = f'mkdir -p {os.path.dirname(banned_ips_file)} && chmod 755 {os.path.dirname(banned_ips_file)}'
                    ProcessUtilities.executioner(command)
                    
                    # Move temp file to final location
                    command = f'mv {temp_file} {banned_ips_file}'
                    ProcessUtilities.executioner(command)
                    
                    # Set permissions
                    command = f'chmod 644 {banned_ips_file} && chown root:root {banned_ips_file}'
                    ProcessUtilities.executioner(command)
                    
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Error saving imported banned IPs: {str(e)}")
                    final_dic = {'importStatus': 0, 'error_message': f'Failed to save imported IPs: {str(e)}'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            
            logging.CyberCPLogFileWriter.writeToFile(f"Banned IPs import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}")
            
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




