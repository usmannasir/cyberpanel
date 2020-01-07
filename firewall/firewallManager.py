#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
from django.shortcuts import HttpResponse, render
from random import randint
import time
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
from plogical.modSec import modSec
from plogical.csf import CSF
from plogical.processUtilities import ProcessUtilities

class FirewallManager:

    def __init__(self, request = None):
        self.request = request

    def securityHome(self, request = None, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'firewall/index.html')
        except BaseException as msg:
            return HttpResponse(str(msg))

    def firewallHome(self, request = None, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'firewall/firewall.html')
        except BaseException as msg:
            return HttpResponse(str(msg))

    def getCurrentRules(self, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

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
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'firewall/secureSSH.html')
        except BaseException as msg:
            return HttpResponse(str(msg))

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
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

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

            return render(request, 'firewall/modSecurity.html', {'modSecInstalled': modSecInstalled, 'OLS': OLS})
        except BaseException as msg:
            return HttpResponse(str(msg))

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
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

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

            return render(request, 'firewall/modSecurityRules.html', {'modSecInstalled': modSecInstalled})

        except BaseException as msg:
            return HttpResponse(str(msg))

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
                    currentModSecRules = ProcessUtilities.outputExecutioner(command).split('\n')

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
                currentModSecRules = ProcessUtilities.outputExecutioner(command).split('\n')

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
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

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

            return render(request, 'firewall/modSecurityRulesPacks.html', {'modSecInstalled': modSecInstalled})

        except BaseException as msg:
            return HttpResponse(msg)

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
                if packName == 'disableOWASP' or packName == 'installOWASP':
                    final_json = json.dumps({'installStatus': 0, 'error_message': "OWASP will be available later.", })
                    return HttpResponse(final_json)

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

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/httpd_config.conf')

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
            else:
                if packName == 'owasp':
                    final_json = json.dumps({'fetchStatus': 0, 'error_message': "OWASP will be available later.", })
                    return HttpResponse(final_json)

                comodoPath = '/usr/local/lsws/conf/comodo_litespeed'
                command = 'sudo chown -R cyberpanel:cyberpanel /usr/local/lsws/conf'
                ProcessUtilities.executioner(command)

                json_data = "["

                counter = 0
                checker = 0
                for fileName in os.listdir(comodoPath):

                    if fileName == 'categories.conf':
                        continue

                    if fileName.endswith('bak'):
                        status = 0
                        fileName = fileName.rstrip('.bak')
                    elif fileName.endswith('conf'):
                        status = 1
                    else:
                        continue

                    dic = {
                        'id': counter,
                        'fileName': fileName,
                        'packName': packName,
                        'status': status,

                    }

                    counter = counter + 1

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

                command = 'sudo chown -R lsadm:lsadm /usr/local/lsws/conf'
                ProcessUtilities.executioner(command)

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

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

            execPath = execPath + " " + functionName + ' --packName ' + packName + ' --fileName ' + fileName

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
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            csfInstalled = 1
            try:
                command = 'sudo csf -h'
                output = ProcessUtilities.outputExecutioner(command)
                if output.find("command not found") > -1:
                    csfInstalled = 0
            except subprocess.CalledProcessError:
                csfInstalled = 0
            return render(self.request,'firewall/csf.html', {'csfInstalled' : csfInstalled})
        except BaseException as msg:
                return HttpResponse(str(msg))

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
            currentACL = ACLManager.loadedACL(userID)

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

            portsPath = '/tmp/ports'

            if os.path.exists(portsPath):
                os.remove(portsPath)

            writeToFile = open(portsPath, 'w')
            writeToFile.write(ports)
            writeToFile.close()

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
