#!/usr/local/CyberCP/bin/python2
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
import subprocess
import shlex
from django.shortcuts import HttpResponse, render
from loginSystem.models import Administrator
from plogical.aclVMM import vmmACLManager
from plogical.acl import ACLManager
from models import HyberVisors

class HVManager:
    def loadHVHome(self, request = None, userID = None,):
        try:
            return render(request, 'hypervisor/indexVMM.html', {})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def createHypervisor(self, request = None, userID = None,):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'createHypervisor') == 0:
                return ACLManager.loadError()

            ownerNames = ACLManager.loadAllUsers(userID)

            return render(request, 'hypervisor/createHyperVisor.html', {'ownerNames' : ownerNames})

        except BaseException, msg:
            return HttpResponse(str(msg))

    def listHVs(self, request = None, userID = None,):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'listHV') == 0:
                return ACLManager.loadError()

            serverObjs = vmmACLManager.findServersObjs(currentACL, userID)
            hvs = vmmACLManager.prepareServers(serverObjs)
            ownerNames = ACLManager.loadAllUsers(userID)

            return render(request, 'hypervisor/listHV.html', {'hvs' : hvs, 'ownerNames' : ownerNames})

        except BaseException, msg:
            return HttpResponse(str(msg))

    def submitCreateHyperVisor(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'createHypervisor') == 0:
                return ACLManager.loadErrorJson()

            if HyberVisors.objects.all().count() == 1:
                final_json = json.dumps({'status': 0, 'errorMessage': "Only one server is allowed at this time."})
                return HttpResponse(final_json)

            name = data['name']
            serverOwner = data['serverOwner']
            serverIP = data['serverIP']
            userName = data['userName']
            password = data['password']
            storagePath = data['storagePath']

            hvOwner = Administrator.objects.get(userName=serverOwner)

            newHV = HyberVisors(hypervisorOwner=hvOwner,
                                hypervisorName=name,
                                hypervisorIP=serverIP,
                                hypervisorUserName=userName,
                                hypervisorPassword=password,
                                hypervisorStoragePath=storagePath)
            newHV.save()


            final_json = json.dumps({'status': 1, 'errorMessage': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def submitHyperVisorChanges(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'listHV') == 0:
                return ACLManager.loadErrorJson()

            name = data['name']
            serverOwner = data['serverOwner']
            userName = data['userName']
            password = data['password']
            storagePath = data['storagePath']

            hvOwner = Administrator.objects.get(userName=serverOwner)

            modifyHV = HyberVisors.objects.get(hypervisorName=name)
            modifyHV.hypervisorOwner = hvOwner
            modifyHV.hypervisorUserName = userName
            modifyHV.hypervisorPassword = password
            modifyHV.hypervisorStoragePath = storagePath

            modifyHV.save()

            final_json = json.dumps({'status': 1, 'errorMessage': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def controlCommands(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'listHV') == 0:
                return ACLManager.loadErrorJson()

            hypervisorIP = data['hypervisorIP']
            action = data['action']

            hv = HyberVisors.objects.get(hypervisorIP=hypervisorIP)

            if hypervisorIP == '127.0.0.1':
                if action == 'restart':
                    command = 'sudo reboot'
                    ACLManager.executeCall(command)
                elif action == 'shutdown':
                    command = 'sudo shutdown'
                    ACLManager.executeCall(command)
                elif action == 'delete':
                    final_json = json.dumps({'status': 0, 'errorMessage': "Local Server can not be deleted."})
                    return HttpResponse(final_json)

            final_json = json.dumps({'status': 1, 'errorMessage': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)