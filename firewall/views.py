from django.shortcuts import render,redirect
from django.http import HttpResponse
import json
import shlex
import subprocess
from loginSystem.views import loadLoginPage
from plogical.firewallUtilities import FirewallUtilities
from .models import FirewallRules
import os
from loginSystem.models import Administrator
import plogical.CyberCPLogFileWriter as logging
from plogical.virtualHostUtilities import virtualHostUtilities
import thread
from plogical.modSec import modSec
from plogical.installUtilities import installUtilities
from random import randint
# Create your views here.


def securityHome(request):
    try:
        userID = request.session['userID']
        return render(request,'firewall/index.html')
    except KeyError:
        return redirect(loadLoginPage)

def firewallHome(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        return render(request,'firewall/firewall.html')
    except KeyError:
        return redirect(loadLoginPage)


def getCurrentRules(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'fetchStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                rules = FirewallRules.objects.all()

                json_data = "["
                checker = 0

                for items in rules:
                    dic = {'id': items.id,
                           'name': items.name,
                           'proto': items.proto,
                           'port': items.port,
                           'ipAddress':items.ipAddress,
                           }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)


                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def addRule(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'add_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                data = json.loads(request.body)
                ruleName = data['ruleName']
                ruleProtocol = data['ruleProtocol']
                rulePort = data['rulePort']
                ruleIP = data['ruleIP']

                FirewallUtilities.addRule(ruleProtocol,rulePort,ruleIP)

                newFWRule = FirewallRules(name=ruleName,proto=ruleProtocol,port=rulePort,ipAddress=ruleIP)
                newFWRule.save()

                final_dic = {'add_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)



        except BaseException,msg:
            final_dic = {'add_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'add_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def deleteRule(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'delete_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                data = json.loads(request.body)
                ruleID = data['id']
                ruleProtocol = data['proto']
                rulePort = data['port']
                ruleIP = data['ruleIP']

                FirewallUtilities.deleteRule(ruleProtocol, rulePort,ruleIP)

                delRule = FirewallRules.objects.get(id=ruleID)
                delRule.delete()

                final_dic = {'delete_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'delete_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def reloadFirewall(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'reload_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                command = 'sudo firewall-cmd --reload'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res == 0:
                    final_dic = {'reload_status': 1, 'error_message': "None"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'reload_status': 0, 'error_message': "Can not reload firewall, see CyberCP main log file."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)




        except BaseException,msg:
            final_dic = {'reload_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'reload_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def startFirewall(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'start_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                command = 'sudo systemctl start firewalld'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 0:
                    final_dic = {'start_status': 1, 'error_message': "None"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'start_status': 0, 'error_message': "Can not start firewall, see CyberCP main log file."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)




        except BaseException,msg:
            final_dic = {'start_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'reload_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def stopFirewall(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'stop_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                command = 'sudo systemctl stop firewalld'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if res == 0:
                    final_dic = {'stop_status': 1, 'error_message': "None"}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'stop_status': 0, 'error_message': "Can not stop firewall, see CyberCP main log file."}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'stop_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'stop_status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def firewallStatus(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                status = subprocess.check_output(["systemctl", "status","firewalld"])

                if status.find("active") >-1:
                    final_dic = {'status': 1, 'error_message': "none",'firewallStatus':1}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 0}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'v': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def secureSSH(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough priviliges to access this page.")

        return render(request,'firewall/secureSSH.html')
    except KeyError:
        return redirect(loadLoginPage)


def getSSHConfigs(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                type = data['type']

                if admin.type != 1:
                    final_dic = {'status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                if type=="1":

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
                            if items.find("Yes") > -1 or items.find("yes")>-1:
                                permitRootLogin = 1
                                continue
                        if items.find("Port") > -1 and not items.find("GatewayPorts") > -1:
                            sshPort = items.split(" ")[1].strip("\n")

                    ## changing permission back

                    command = 'sudo chown -R  root:root /etc/ssh/sshd_config'

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                    final_dic = {'permitRootLogin': permitRootLogin, 'sshPort': sshPort}
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

                            key = "ssh-rsa " +keydata[1][:50] + " ... " + keydata[2]

                            try:
                                userName = keydata[2][:keydata[2].index("@")]
                            except:
                                userName =  keydata[2]

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



        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'status': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def saveSSHConfigs(request):
    try:
        val = request.session['userID']
        admin= Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                type = data['type']

                if admin.type != 1:
                    final_dic = {'saveStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)


                if type=="1":

                    sshPort = data['sshPort']
                    rootLogin = data['rootLogin']

                    command = 'sudo semanage port -a -t ssh_port_t -p tcp ' +sshPort
                    cmd = shlex.split(command)
                    res = subprocess.call(cmd)


                    FirewallUtilities.addRule('tcp',sshPort,"0.0.0.0/0")

                    try:
                        updateFW = FirewallRules.objects.get(name="SSHCustom")
                        FirewallUtilities.deleteRule("tcp",updateFW.port)
                        updateFW.port = sshPort
                        updateFW.save()
                    except:
                        try:
                            newFireWallRule = FirewallRules(name="SSHCustom",port=sshPort,proto="tcp")
                            newFireWallRule.save()
                        except BaseException,msg:
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

                    sshPort = "Port "+sshPort+"\n"


                    pathToSSH = "/etc/ssh/sshd_config"

                    data = open(pathToSSH, 'r').readlines()

                    writeToFile = open(pathToSSH,"w")


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


                    final_dic = {'saveStatus': 1}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'saveStatus': 0,'error_message':str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'saveStatus': 0,'error_message':str(msg)}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def deleteSSHKey(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                key = data['key']

                if admin.type != 1:
                    final_dic = {'delete_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                # temp change of permissions

                command = 'sudo chown -R  cyberpanel:cyberpanel /root'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ##

                keyPart = key.split(" ")[1]

                pathToSSH = "/root/.ssh/authorized_keys"

                data = open(pathToSSH, 'r').readlines()

                writeToFile = open(pathToSSH,"w")

                for items in data:
                    if items.find("ssh-rsa") > -1 and items.find(keyPart)>-1:
                        continue
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

                # change back permissions

                command = 'sudo chown -R  root:root /root'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ##


                final_dic = {'delete_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'delete_status': 0}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'delete_status': 0}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def addSSHKey(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                key = data['key']

                if admin.type != 1:
                    final_dic = {'add_status': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                # temp change of permissions

                command = 'sudo chown -R  cyberpanel:cyberpanel /root'

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
                    sshFile = open(pathToSSH,'w')
                    sshFile.writelines("#Created by CyberPanel\n")
                    sshFile.close()



                writeToFile = open(pathToSSH, 'a')
                writeToFile.writelines("\n")
                writeToFile.writelines(key)
                writeToFile.writelines("\n")
                writeToFile.close()

                # change back permissions

                command = 'sudo chown -R  root:root /root'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                ##


                final_dic = {'add_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'add_status': 0}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'add_status': 0}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def loadModSecurityHome(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        confPath = os.path.join(virtualHostUtilities.Server_root,"conf/httpd_config.conf")

        command = "sudo cat " + confPath
        httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

        modSecInstalled = 0

        for items in httpdConfig:
            if items.find('module mod_security') > -1:
                modSecInstalled = 1
                break

        return render(request,'firewall/modSecurity.html', {'modSecInstalled': modSecInstalled})
    except KeyError:
        return redirect(loadLoginPage)

def installModSec(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:

            if admin.type != 1:
                final_dic = {'installModSec': 0, 'error_message': 'Not enough privileges.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            thread.start_new_thread(modSec.installModSec, ('Install','modSec'))
            final_json = json.dumps({'installModSec': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'installModSec': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'installModSec': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def installStatusModSec(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'abort': 1, 'installed': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)


                installStatus = unicode(open(modSec.installLogPath, "r").read())

                if installStatus.find("[200]")>-1:

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
                                             'abort':1,
                                             'installed': 1,
                                             })
                    return HttpResponse(final_json)
                elif installStatus.find("[404]") > -1:

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


def fetchModSecSettings(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'fetchStatus': 0, 'installed': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

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



                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)


        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)


        return render(request,'managePHP/editPHPConfig.html')
    except KeyError:
        return redirect(loadLoginPage)

def saveModSecConfigurations(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'saveStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                data = json.loads(request.body)

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


        except BaseException,msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'saveStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def modSecRules(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

        command = "sudo cat " + confPath
        httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

        modSecInstalled = 0

        for items in httpdConfig:
            if items.find('module mod_security') > -1:
                modSecInstalled = 1
                break

        return render(request, 'firewall/modSecurityRules.html',{'modSecInstalled': modSecInstalled})

    except KeyError:
        return redirect(loadLoginPage)


def fetchModSecRules(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

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
    except KeyError:
        return redirect(loadLoginPage)


def saveModSecRules(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'saveStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                data = json.loads(request.body)

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


        except BaseException,msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    except KeyError,msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'saveStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)


def modSecRulesPacks(request):
    try:
        userID = request.session['userID']

        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            return HttpResponse("You don't have enough privileges to access this page.")

        confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

        command = "sudo cat " + confPath
        httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

        modSecInstalled = 0

        for items in httpdConfig:
            if items.find('module mod_security') > -1:
                modSecInstalled = 1
                break

        return render(request, 'firewall/modSecurityRulesPacks.html',{'modSecInstalled': modSecInstalled})

    except KeyError:
        return redirect(loadLoginPage)

def getOWASPAndComodoStatus(request):
    try:
        userID = request.session['userID']
        admin = Administrator.objects.get(pk=userID)

        if admin.type == 3:
            final_dic = {'modSecInstalled': 0}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/httpd_config.conf')

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
    except KeyError:
        return redirect(loadLoginPage)

def installModSecRulesPack(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'installStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                data = json.loads(request.body)

                packName = data['packName']

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

    except KeyError, msg:
        logging.CyberCPLogFileWriter.writeToFile(str(msg))
        data_ret = {'installStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

def getRulesFiles(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk=val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'fetchStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)


                data = json.loads(request.body)
                packName = data['packName']

                confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/httpd_config.conf')

                command = "sudo cat " + confPath
                httpdConfig = subprocess.check_output(shlex.split(command)).splitlines()

                json_data = "["
                checker = 0
                counter = 0

                for items in httpdConfig:

                    if items.find('modsec/'+packName) > -1:
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
                               'packName':packName,
                               'status': status,

                               }

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)


                json_data = json_data + ']'
                final_json = json.dumps({'fetchStatus': 1, 'error_message': "None","data":json_data})
                return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)

            return HttpResponse(final_json)
    except KeyError:
        final_dic = {'fetchStatus': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)

def enableDisableRuleFile(request):
    try:
        val = request.session['userID']
        admin = Administrator.objects.get(pk = val)
        try:
            if request.method == 'POST':

                if admin.type != 1:
                    final_dic = {'saveStatus': 0, 'error_message': 'Not enough privileges.'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

                data = json.loads(request.body)

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


        except BaseException,msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)
    except BaseException, msg:
        data_ret = {'saveStatus': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

