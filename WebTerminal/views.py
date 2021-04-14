# -*- coding: utf-8 -*-


from django.shortcuts import render, redirect, HttpResponse
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
from random import randint
import os

from plogical.httpProc import httpProc
from plogical.processUtilities import ProcessUtilities
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
import json
import plogical.randomPassword

# Create your views here.

def terminal(request):
    password = plogical.randomPassword.generate_pass()

    verifyPath = "/home/cyberpanel/" + str(randint(100000, 999999))
    writeToFile = open(verifyPath, 'w')
    writeToFile.write(password)
    writeToFile.close()

    ## setting up ssh server
    path = '/etc/systemd/system/cpssh.service'
    curPath = '/usr/local/CyberCP/WebTerminal/cpssh.service'

    if not os.path.exists(path):
        command = 'mv %s %s' % (curPath, path)
        ProcessUtilities.executioner(command)

        command = 'systemctl start cpssh'
        ProcessUtilities.executioner(command)

        FirewallUtilities.addRule('tcp', '5678', '0.0.0.0/0')

        newFWRule = FirewallRules(name='terminal', proto='tcp', port='5678', ipAddress='0.0.0.0/0')
        newFWRule.save()

    proc = httpProc(request, 'WebTerminal/WebTerminal.html',
                    {'verifyPath': verifyPath, 'password': password}, 'admin')
    return proc.render()

def restart(request):
    try:

        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadErrorJson()

        command = 'systemctl restart cpssh'
        ProcessUtilities.executioner(command)

        data_ret = {'status': 1, 'error_message': 'None'}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)

    except BaseException as msg:
        data_ret = {'status': 0, 'error_message': str(msg)}
        json_data = json.dumps(data_ret)
        return HttpResponse(json_data)