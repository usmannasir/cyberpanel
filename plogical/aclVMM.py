#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from loginSystem.models import Administrator
from django.shortcuts import HttpResponse
from hypervisor.models import HyberVisors
from vpsManagement.models import SSHKeys, VPS
import json
from packages.models import VMPackage as Package

class vmmACLManager:

    @staticmethod
    def inspectHyperVisor():
        return 1

    @staticmethod
    def loadError():
        try:
            return HttpResponse('You are not authorized to access this resource.')
        except:
            pass

    @staticmethod
    def currentContextPermission(currentACL, context):
        return 1

    @staticmethod
    def findServersObjs(currentACL, userID):
        if currentACL['admin'] == 1:
            return HyberVisors.objects.all()
        else:

            hvList = []
            admin = Administrator.objects.get(pk=userID)

            hvs = admin.hybervisors_set.all()

            for items in hvs:
                hvList.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                hvs = items.hybervisors_set.all()
                for hv in hvs:
                    hvList.append(hv)

            return hvList

    @staticmethod
    def prepareServers(serverObjs):
        preparedServers = []
        for items in serverObjs:
            data = {}
            data['id'] = items.id
            data['hypervisorOwner'] = items.hypervisorOwner.userName
            data['hypervisorName'] = items.hypervisorName
            data['hypervisorIP'] = items.hypervisorIP
            data['vms'] = items.vps_set.all().count()
            data['hypervisorStoragePath'] = items.hypervisorStoragePath
            preparedServers.append(data)
        return preparedServers

    @staticmethod
    def fetchSSHkeys(currentACL, userID):
        if currentACL['admin'] == 1:

            allKeys = SSHKeys.objects.all()

            json_data = "["
            checker = 0

            for items in allKeys:
                dic = {
                    'keyName': items.keyName,
                       'key': items.key,
                       }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)



            json_data = json_data + ']'

            return json_data
        else:

            admin = Administrator.objects.get(pk=userID)

            sshkeys = admin.sshkeys_set.all()

            json_data = "["
            checker = 0

            for items in sshkeys:
                dic = {
                    'keyName': items.keyName,
                    'key': items.key,
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:

                sshkeys = items.sshkeys_set.all()
                for items in sshkeys:
                    dic = {
                        'keyName': items.keyName,
                        'key': items.key,
                    }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'

            return json_data

    @staticmethod
    def fetchSSHkeysObjects(currentACL, userID):

        if currentACL['admin'] == 1:
            return SSHKeys.objects.all()
        else:

            keysObjects = []
            admin = Administrator.objects.get(pk=userID)
            sshkeys = admin.sshkeys_set.all()

            for items in sshkeys:
                keysObjects.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                sshkeys = items.sshkeys_set.all()
                for items in sshkeys:
                    keysObjects.append(items)


            return keysObjects

    @staticmethod
    def findSSHkeyNames(currentACL, userID):
        sshKeysObjects = vmmACLManager.fetchSSHkeysObjects(currentACL, userID)
        keyNames = []
        for items in sshKeysObjects:
            keyNames.append(items.keyName)
        return keyNames

    @staticmethod
    def fetchHyperVisorObjects(currentACL, userID):

        if currentACL['admin'] == 1:
            return HyberVisors.objects.all()
        else:
            hvObjects = []
            admin = Administrator.objects.get(pk=userID)
            hvs = admin.hybervisors_set.all()

            for items in hvs:
                hvObjects.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                hvs = items.hybervisors_set.all()
                for items in hvs:
                    hvObjects.append(items)

            return hvObjects

    @staticmethod
    def findHyperVisorNames(currentACL, userID):
        hvs = vmmACLManager.fetchHyperVisorObjects(currentACL, userID)
        hvNames = []
        for items in hvs:
            hvNames.append(items.hypervisorName)
        return hvNames

    @staticmethod
    def findAllIPObjs(hv):
        ipObjs = []
        allPools = hv.ippool_set.all()
        for ipPool in allPools:
            allIPs = ipPool.ipaddresses_set.all()
            for ip in allIPs:
                ipObjs.append(ip)
        return ipObjs

    @staticmethod
    def findAllIPs(hv):
        allIps = vmmACLManager.findAllIPObjs(hv)
        ipAddresses = []

        for items in allIps:
            if items.used == 1:
                continue
            ipAddresses.append(items.ipAddr)
        return ipAddresses

    @staticmethod
    def jsonIPs(hv):
        allIPs = vmmACLManager.findAllIPs(hv)

        json_data = "["
        checker = 0

        for items in allIPs:
            dic = {'ipAddr': items}

            if checker == 0:
                json_data = json_data + json.dumps(dic)
                checker = 1
            else:
                json_data = json_data + ',' + json.dumps(dic)

        json_data = json_data + ']'

        return json_data

    @staticmethod
    def findAllPackages(currentACL, userID):
        if currentACL['admin'] == 1:
            packageNames = []

            packages = Package.objects.all()
            for package in packages:
                packageNames.append(package.packageName)
            return packageNames

    @staticmethod
    def checkOwner(currentACL, userID):
        return 1

    @staticmethod
    def findAllVPSOBjs(currentACL, userID):
        if currentACL['admin'] == 1:
            return VPS.objects.all()
        else:
            vmObjects = []
            admin = Administrator.objects.get(pk=userID)
            hvs = admin.vps_set.all()

            for items in hvs:
                vmObjects.append(items)

            admins = Administrator.objects.filter(owner=admin.pk)

            for items in admins:
                hvs = items.vps_set.all()
                for items in hvs:
                    vmObjects.append(items)

            return vmObjects





