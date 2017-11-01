from django.shortcuts import render,redirect
from .models import FirewallRules
from django.http import HttpResponse
import json
from plogical.firewallUtilities import FirewallUtilities
import shlex
import subprocess
from loginSystem.views import loadLoginPage
from plogical.firewallUtilities import FirewallUtilities
from .models import FirewallRules
import os
from loginSystem.models import Administrator
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
        try:
            if request.method == 'POST':

                data = json.loads(request.body)

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
        try:
            if request.method == 'POST':

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
        try:
            if request.method == 'POST':

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
        try:
            if request.method == 'POST':


                command = 'firewall-cmd --reload'

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
        try:
            if request.method == 'POST':


                command = 'systemctl start firewalld'

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
        try:
            if request.method == 'POST':


                command = 'systemctl stop firewalld'

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
        try:
            if request.method == 'POST':


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
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                type = data['type']


                if type=="1":


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

                    final_dic = {'permitRootLogin': permitRootLogin, 'sshPort': sshPort}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
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

                    final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
                    return HttpResponse(final_json)



        except BaseException,msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'v': 0, 'error_message': "Not Logged In, please refresh the page or login again."}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def saveSSHConfigs(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                type = data['type']


                if type=="1":

                    sshPort = data['sshPort']
                    rootLogin = data['rootLogin']

                    command = 'semanage port -a -t ssh_port_t -p tcp ' +sshPort

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)

                    FirewallUtilities.addRule('tcp',sshPort)

                    try:
                        updateFW = FirewallRules.objects.get(name="SSHCustom")
                        FirewallUtilities.deleteRule("tcp",updateFW.port)
                        updateFW.port = sshPort
                        updateFW.save()
                    except:
                        newFireWallRule = FirewallRules(name="SSHCustom",port=sshPort,proto="tcp")
                        newFireWallRule.save()


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

                    command = 'systemctl restart sshd'

                    cmd = shlex.split(command)

                    res = subprocess.call(cmd)


                    final_dic = {'saveStatus': 1}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

        except BaseException,msg:
            final_dic = {'saveStatus': 0}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)
    except KeyError,msg:
        final_dic = {'saveStatus': 0}
        final_json = json.dumps(final_dic)
        return HttpResponse(final_json)


def deleteSSHKey(request):
    try:
        val = request.session['userID']
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                key = data['key']

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
        try:
            if request.method == 'POST':
                data = json.loads(request.body)
                key = data['key']

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
