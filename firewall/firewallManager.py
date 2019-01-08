#!/usr/local/CyberCP/bin/python2
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
import shlex
from plogical.installUtilities import installUtilities
from django.shortcuts import HttpResponse, render
from random import randint
import time
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
import thread
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
        except BaseException, msg:
            return HttpResponse(str(msg))

    def firewallHome(self, request = None, userID = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadError()

            return render(request, 'firewall/firewall.html')
        except BaseException, msg:
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

        except BaseException, msg:
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

        except BaseException, msg:
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

        except BaseException, msg:
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
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                final_dic = {'reload_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'reload_status': 0,
                             'error_message': "Can not reload firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException, msg:
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

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            if res == 0:
                final_dic = {'start_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'start_status': 0,
                             'error_message': "Can not start firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException, msg:
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
            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                final_dic = {'stop_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'stop_status': 0,
                             'error_message': "Can not stop firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException, msg:
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

            command = 'sudo systemctl status firewalld'

            status = subprocess.check_output(shlex.split(command))

            if status.find("active") > -1:
                final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 0}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException, msg:
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
        except BaseException, msg:
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

                command = 'sudo chown -R  cyberpanel:cyberpanel /etc/ssh/sshd_config'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                pathToSSH = "/etc/ssh/sshd_config"

                data = open(pathToSSH, 'r').readlines()

                permitRootLogin = 0
                sshPort = "22"

                for items in data:
                    if items.find("PermitRootLogin") > -1:
                        if items.find("Yes") > -1 or items.find("yes") > -1:
                            permitRootLogin = 1
                            continue
                    if items.find("Port") > -1 and not items.find("GatewayPorts") > -1:
                        sshPort = items.split(" ")[1].strip("\n")

                ## changing permission back

                command = 'sudo chown -R  root:root /etc/ssh/sshd_config'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                final_dic = {'status': 1, 'permitRootLogin': permitRootLogin, 'sshPort': sshPort}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:

                ## temporarily changing permission for sshd files

                command = 'sudo chown -R  cyberpanel:cyberpanel /root'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                pathToKeyFile = "/root/.ssh/authorized_keys"

                json_data = "["
                checker = 0

                data = open(pathToKeyFile, 'r').readlines()

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

                ## changing permission back

                command = 'sudo chown -R  root:root /root'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException, msg:
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

            if type == "1":

                sshPort = data['sshPort']
                rootLogin = data['rootLogin']

                command = 'sudo semanage port -a -t ssh_port_t -p tcp ' + sshPort
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")

                try:
                    updateFW = FirewallRules.objects.get(name="SSHCustom")
                    FirewallUtilities.deleteRule("tcp", updateFW.port, "0.0.0.0/0")
                    updateFW.port = sshPort
                    updateFW.save()
                except:
                    try:
                        newFireWallRule = FirewallRules(name="SSHCustom", port=sshPort, proto="tcp")
                        newFireWallRule.save()
                    except BaseException, msg:
                        logging.CyberCPLogFileWriter.writeToFile(str(msg))

                ## temporarily changing permission for sshd files

                command = 'sudo chown -R  cyberpanel:cyberpanel /etc/ssh/sshd_config'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ##


                if rootLogin == True:
                    rootLogin = "PermitRootLogin yes\n"
                else:
                    rootLogin = "PermitRootLogin no\n"

                sshPort = "Port " + sshPort + "\n"

                pathToSSH = "/etc/ssh/sshd_config"

                data = open(pathToSSH, 'r').readlines()

                writeToFile = open(pathToSSH, "w")

                for items in data:
                    if items.find("PermitRootLogin") > -1:
                        if items.find("Yes") > -1 or items.find("yes"):
                            writeToFile.writelines(rootLogin)
                            continue
                    elif items.find("Port") > -1:
                        writeToFile.writelines(sshPort)
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

                command = 'sudo systemctl restart sshd'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ## changin back permissions

                command = 'sudo chown -R  root:root /etc/ssh/sshd_config'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ##

                final_dic = {'status': 1, 'saveStatus': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException, msg:
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

            # temp change of permissions

            command = 'sudo chown -R  cyberpanel:cyberpanel /root'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

            keyPart = key.split(" ")[1]

            pathToSSH = "/root/.ssh/authorized_keys"

            data = open(pathToSSH, 'r').readlines()

            writeToFile = open(pathToSSH, "w")

            for items in data:
                if items.find("ssh-rsa") > -1 and items.find(keyPart) > -1:
                    continue
                else:
                    writeToFile.writelines(items)
            writeToFile.close()

            # change back permissions

            command = 'sudo chown -R  root:root /root'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

            final_dic = {'status': 1, 'delete_status': 1}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
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

            # temp change of permissions

            command = 'sudo chown -R cyberpanel:cyberpanel /root'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

            sshDir = "/root/.ssh"

            pathToSSH = "/root/.ssh/authorized_keys"

            if os.path.exists(sshDir):
                pass
            else:
                os.mkdir(sshDir)

            if os.path.exists(pathToSSH):
                pass
            else:
                sshFile = open(pathToSSH, 'w')
                sshFile.writelines("#Created by CyberPanel\n")
                sshFile.close()

            presenseCheck = 0
            try:
                data = open(pathToSSH, "r").readlines()
                for items in data:
                    if items.find(key) > -1:
                        presenseCheck = 1
            except:
                pass

            if presenseCheck == 0:
                writeToFile = open(pathToSSH, 'a')
                writeToFile.writelines("#Added by CyberPanel\n")
                writeToFile.writelines("\n")
                writeToFile.writelines(key)
                writeToFile.writelines("\n")
                writeToFile.close()

            # change back permissions

            command = 'sudo chown -R  root:root /root'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            ##

            final_dic = {'status': 1, 'add_status': 1}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
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
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break
            else:
                OLS = 0
                modSecInstalled = 1

            return render(request, 'firewall/modSecurity.html', {'modSecInstalled': modSecInstalled, 'OLS': OLS})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def installModSec(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installModSec', 0)

            thread.start_new_thread(modSec.installModSec, ('Install', 'modSec'))
            final_json = json.dumps({'installModSec': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_dic = {'installModSec': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusModSec(self, userID = None, data = None):
        try:

            installStatus = unicode(open(modSec.installLogPath, "r").read())

            if installStatus.find("[200]") > -1:

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " installModSecConfigs"

                output = subprocess.check_output(shlex.split(execPath))

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

                installUtilities.reStartLiteSpeed()

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

        except BaseException, msg:
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
                    data = subprocess.check_output(shlex.split(command)).splitlines()

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

                data = subprocess.check_output(shlex.split(command)).splitlines()

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

        except BaseException, msg:
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

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " saveModSecConfigs --tempConfigPath " + tempConfigPath

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    installUtilities.reStartLiteSpeed()
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

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " saveModSecConfigs --tempConfigPath " + tempConfigPath

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    installUtilities.reStartLiteSpeed()
                    data_ret = {'saveStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException, msg:
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
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break
            else:
                modSecInstalled = 1

            return render(request, 'firewall/modSecurityRules.html', {'modSecInstalled': modSecInstalled})

        except BaseException, msg:
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
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break

                rulesPath = os.path.join(virtualHostUtilities.Server_root + "/conf/modsec/rules.conf")

                if modSecInstalled:
                    command = "sudo cat " + rulesPath
                    currentModSecRules = subprocess.check_output(shlex.split(command))

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
                currentModSecRules = subprocess.check_output(shlex.split(command))

                final_dic = {'modSecInstalled': 1,
                             'currentModSecRules': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException, msg:
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

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
            execPath = execPath + " saveModSecRules"
            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                installUtilities.reStartLiteSpeed()
                data_ret = {'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
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
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break
            else:
                modSecInstalled = 1

            return render(request, 'firewall/modSecurityRulesPacks.html', {'modSecInstalled': modSecInstalled})

        except BaseException, msg:
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
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break

                comodoInstalled = 0
                owaspInstalled = 0

                if modSecInstalled:
                    command = "sudo cat " + confPath
                    httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

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
                    command = 'sudo cat /usr/local/lsws/conf/comodo_litespeed/rules.conf.main'
                    res = subprocess.call(shlex.split(command))

                    if res == 0:
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

        except BaseException, msg:
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

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " " + packName

                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    installUtilities.reStartLiteSpeed()
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

                execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " " + packName
                output = subprocess.check_output(shlex.split(execPath))

                if output.find("1,None") > -1:
                    installUtilities.reStartLiteSpeed()
                    data_ret = {'installStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'installStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException, msg:
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
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

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
                subprocess.call(shlex.split(command))

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
                subprocess.call(shlex.split(command))

                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException, msg:
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

            execPath = "sudo python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

            execPath = execPath + " " + functionName + ' --packName ' + packName + ' --fileName ' + fileName

            output = subprocess.check_output(shlex.split(execPath))

            if output.find("1,None") > -1:
                installUtilities.reStartLiteSpeed()
                data_ret = {'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
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
                res = subprocess.call(shlex.split(command))
                if res == 1:
                    csfInstalled = 0
            except subprocess.CalledProcessError:
                csfInstalled = 0
            return render(self.request,'firewall/csf.html', {'csfInstalled' : csfInstalled})
        except BaseException, msg:
                return HttpResponse(str(msg))

    def installCSF(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            execPath = "sudo /usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
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

    def installStatusCSF(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

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

            execPath = "sudo /usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
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

        except BaseException,msg:
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

            execPath = "sudo /usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
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

    def modifyPorts(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            protocol = data['protocol']
            ports = data['ports']

            execPath = "sudo /usr/local/CyberCP/bin/python2 " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
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

        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
