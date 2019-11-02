# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.shortcuts import render, redirect
from plogical.acl import ACLManager
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from loginSystem.views import loadLoginPage
from random import randint
import os
from plogical.processUtilities import ProcessUtilities
# Create your views here.

def terminal(request):
    try:
        userID = request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        verifyPath = "/home/cyberpanel/" + str(randint(100000, 999999))
        writeToFile = open(verifyPath, 'w')
        writeToFile.writelines('code')
        writeToFile.close()

        ## setting up ssh server
        path = '/etc/systemd/system/cpssh.service'
        curPath = '/usr/local/CyberCP/WebTerminal/cpssh.service'

        if not os.path.exists(path):
            command = 'mv %s %s' % (curPath, path)
            ProcessUtilities.executioner(command)

            command = 'systemctl start cpssh'
            ProcessUtilities.executioner(command)

        return render(request, 'WebTerminal/WebTerminal.html', {'verifyPath': verifyPath})
    except BaseException, msg:
        logging.writeToFile(str(msg))
        return redirect(loadLoginPage)