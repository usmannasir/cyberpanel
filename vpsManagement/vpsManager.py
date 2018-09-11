import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from plogical.acl import  ACLManager
from plogical.aclVMM import vmmACLManager
from vpsManagement.models import SSHKeys, VPS
from django.shortcuts import render, HttpResponse
from loginSystem.models import Administrator
from CyberTronAPI.virtualMachineAPIKVM import virtualMachineAPI
from CyberTronAPI.cybertron import CyberTron
import json
from hypervisor.models import HyberVisors
from random import randint
import time
from math import ceil
from vpsManagement.models import Snapshots
import subprocess
import shlex

class VPSManager:

    def vpsHome(self, request = None, userID = None, data = None):
        try:
            return render(request, 'vpsManagement/indexVMM.html')
        except BaseException, msg:
            return HttpResponse(str(msg))

    def createVPS(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'createVPS') == 0:
                return ACLManager.loadError()

            hvNames = vmmACLManager.findHyperVisorNames(currentACL, userID)
            sshKeys = vmmACLManager.findSSHkeyNames(currentACL, userID)
            packageNames = vmmACLManager.findAllPackages(currentACL, userID)
            ownerNames = ACLManager.loadAllUsers(userID)
            osNames = vmmACLManager.findOsNames()

            data = {'hvNames': hvNames, 'sshKeys': sshKeys, 'packageNames': packageNames, 'ownerNames': ownerNames, 'osNames': osNames}

            return render(request, 'vpsManagement/createVPS.html', data)

        except BaseException, msg:
            return HttpResponse(str(msg))

    def listVPSs(self, request = None, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            vpss = vmmACLManager.findAllVPSOBjs(currentACL, userID)

            pages = float(len(vpss)) / float(10)
            pagination = []

            if pages <= 1.0:
                pages = 1
                pagination.append('<li><a href="\#"></a></li>')
            else:
                pages = ceil(pages)
                finalPages = int(pages) + 1

                for i in range(1, finalPages):
                    pagination.append('<li><a href="\#">' + str(i) + '</a></li>')

            return render(request, 'vpsManagement/listVPS.html', {"pagination": pagination})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def fetchVPS(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            pageNumber = int(data['page'])
            finalPageNumber = ((pageNumber * 10)) - 10
            endPageNumber = finalPageNumber + 10

            vpss = vmmACLManager.findAllVPSOBjs(currentACL, userID)[finalPageNumber:endPageNumber]

            json_data = "["
            checker = 0

            for vps in vpss:
                if virtualMachineAPI.isActive(vps.hostName) == 1:
                    status = 1
                else:
                    status = 0
                dic = {
                    'id': vps.id,
                    'status': status,
                    'ipAddress': vps.ipAddr.ipAddr,
                    'hostname': vps.hostName,
                    'package': vps.package.packageName,
                    'networkSpeed': vps.networkSpeed,
                    'owner': vps.owner.userName
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_dic = {'success': 1, 'error_message': "None", "data": json_data,
                         'successMessage': 'Successfully fetched!'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def restartVPS(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            vpsID = data['vpsID']
            vps = VPS.objects.get(id=vpsID)
            success, message = virtualMachineAPI.softReboot(vps.hostName)

            if success == 1:
                data_ret = {"success": 1, 'error_message': "None",
                            'successMessage': 'VPS will restart in background.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"success": 0, 'error_message': message}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def shutdownVPS(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            vpsID = data['vpsID']
            vps = VPS.objects.get(id=vpsID)
            success, message = virtualMachineAPI.hardShutdown(vps.hostName)
            if success == 1:
                data_ret = {"success": 1, 'error_message': "None",
                            'successMessage': 'VPS has been stopped.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"success": 0, 'error_message': message}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def getVPSDetails(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']
            vps = VPS.objects.get(hostName=hostName)
            ## Calculating disk usage percentage
            vpsImagePath = '/var/lib/libvirt/images/' + hostName + ".qcow2"
            sizeInMB = float(os.path.getsize(vpsImagePath)) / (1024.0 * 1024)
            diskUsagePercentage = float(100) / float((int(vps.package.diskSpace.rstrip('GB')) * 1024))
            diskUsagePercentage = float(diskUsagePercentage) * float(sizeInMB)
            diskUsagePercentage = int(diskUsagePercentage)

            ## Calculate ram usage percentage

            unUsedRam = virtualMachineAPI.getCurrentUsedRam(hostName)
            usedRam = int(vps.package.guaranteedRam.rstrip('MB')) - unUsedRam

            final_dic = {'success': 1, 'error_message': "None",
                         'successMessage': 'Successfully fetched!',
                         'sizeInMB': int(sizeInMB),
                         'diskUsage': diskUsagePercentage}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def findIPs(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'createVPS') == 0:
                return ACLManager.loadError()

            hvName = data['hvName']
            hv = HyberVisors.objects.get(hypervisorName=hvName)
            allIps = vmmACLManager.jsonIPs(hv)

            final_json = json.dumps({'status': 1, 'errorMessage': "None", 'allIps': allIps})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def manageVPS(self, request = None, userID = None, hostName = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadError()

            if VPS.objects.filter(hostName=hostName).exists():
                vps = VPS.objects.get(hostName=hostName)

                ## Calculating disk usage percentage
                diskUsagePercentage, sizeInMB = virtualMachineAPI.calculateDiskPercentage(hostName, vps.package.diskSpace)

                ## Calculate ram usage percentage

                ramUsagePercentage = virtualMachineAPI.calculateRamPercentage(hostName, vps.package.guaranteedRam)

                ## Calculate bwusage usage percentage

                bwPercentage = virtualMachineAPI.calculateBWPercentage(hostName, vps.package.bandwidth)


                ## VNC URL

                ipFile = "/etc/cyberpanel/machineIP"
                f = open(ipFile)
                ipData = f.read()
                vncHostIP = ipData.split('\n', 1)[0]

                consoleURL = '/noVNC/vnc.html?host=' + vncHostIP + '&port=570' + str(vps.websocketPort) + '&password=' + vps.vncPassword

                ## Snapshot url

                snapshotsURL = '/backup/' + hostName + '/snapshots'
                sshKeys = vmmACLManager.findSSHkeyNames(currentACL, userID)
                osNames = vmmACLManager.findOsNames()


                return render(request, 'vpsManagement/manageVPS.html', {'hostName':hostName,
                                                                        'owner': vps.owner.userName,
                                                                        'ipAddr':vps.ipAddr.ipAddr,
                                                                        'package':vps.package.packageName,
                                                                        'vncPort':str(vps.vncPort),
                                                                        'websocketPort':"570" + str(vps.websocketPort),
                                                                        'sizeInMB':int(sizeInMB),
                                                                        'diskUsage': diskUsagePercentage,
                                                                        'ramUsage':ramUsagePercentage,
                                                                        'bwUsage':bwPercentage,
                                                                        'consoleURL':consoleURL,
                                                                        'snapshotsURL':snapshotsURL,
                                                                        'sshKeys' : sshKeys,
                                                                        'osNames': osNames
                                                                        })
            else:
                return render(request, 'vpsManagement/manageVPS.html',
                              {"error": 1, "hostName": "Virtual Machine with this hostname does not exists."})
        except BaseException, msg:
            return HttpResponse(str(msg))

    def changeHostname(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']
            newHostname = data['newHostname']

            vps = VPS.objects.get(hostName=hostName)

            success, message = virtualMachineAPI.hardShutdown(hostName)

            if success == 1:
                virtualMachineAPI.changeHostname(vps.hostName, newHostname)
                virtualMachineAPI.softReboot(hostName)

                data_ret = {"success": 1, 'error_message': "None",
                            'successMessage': 'VPS Hostname has been successfully changed.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"success": 0, 'error_message': message}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def changeRootPassword(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']
            newPassword = data['newPassword']

            vps = VPS.objects.get(hostName=hostName)

            success, message = virtualMachineAPI.hardShutdown(hostName)

            if success == 1:
                virtualMachineAPI.changeRootPassword(vps.hostName, newPassword)
                virtualMachineAPI.softReboot(hostName)

                data_ret = {"success": 1, 'error_message': "None",
                            'successMessage': 'VPS Root Password has been successfully changed.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {"success": 0, 'error_message': message}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def reInstallOS(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostname = data['hostname']

            vps = VPS.objects.get(hostName=hostname)

            data['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))
            data['vpsOwner'] = vps.owner.userName

            ##

            ipAddr = vps.ipAddr
            data['vpsIP'] = ipAddr.ipAddr
            ipAddr.used = 0
            ipAddr.save()

            ##

            data['networkSpeed'] = vps.networkSpeed
            data['vpsPackage'] = vps.package.packageName
            data['vpsID'] = vps.id

            ## First let us delete the VPS

            self.deleteVPS(1, data)

            ## Creating VPS

            ct = CyberTron(data)
            ct.start()
            time.sleep(2)

            data_ret = {"success": 1, 'error_message': "None",
                        'tempStatusPath': data['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def deleteVPS(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'deleteVPS') == 0:
                return ACLManager.loadErrorJson()

            vpsID = data['vpsID']

            vps = VPS.objects.get(id=vpsID)
            ip = vps.ipAddr
            ip.used = 0
            ip.save()
            hostName = vps.hostName
            vps.delete()

            virtualMachineAPI.deleteVirtualMachine(hostName)

            interfaceFile = "/etc/cyberpanel/interfaceName"
            f = open(interfaceFile)
            interfaceData = f.read()
            interfaceName = interfaceData.split('\n', 1)[0]

            virtualMachineAPI.removeVMSpeedLimit(str(vpsID), interfaceName)


            data_ret = {"success": 1, 'error_message': "None",
                        'successMessage': 'VPS Successfully Deleted!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def sshKeys(self, request = None, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'sshKeys') == 0:
                return ACLManager.loadError()

            return render(request, 'vpsManagement/sshKeys.html')

        except BaseException, msg:
            return HttpResponse(str(msg))

    def addKey(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'sshKeys') == 0:
                return ACLManager.loadErrorJson()

            keyName = data['keyName']
            keyData = data['keyData']

            admin = Administrator.objects.get(pk=userID)

            newKey = SSHKeys(owner=admin, keyName=keyName, key=keyData)
            newKey.save()

            final_json = json.dumps({'status': 1, 'errorMessage': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def fetchKeys(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'sshKeys') == 0:
                return ACLManager.loadErrorJson()

            sshKeys = vmmACLManager.fetchSSHkeys(currentACL, userID)

            final_json = json.dumps({'status': 1, 'errorMessage': "None", 'sshKeys': sshKeys})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def deleteKey(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'sshKeys') == 0:
                return ACLManager.loadErrorJson()

            delKey = SSHKeys.objects.get(keyName=data['keyName'])
            delKey.delete()

            final_json = json.dumps({'status': 1, 'errorMessage': "None"})
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def submitVPSCreation(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.currentContextPermission(currentACL, 'createVPS') == 0:
                return ACLManager.loadErrorJson()

            ## Creating VPS

            data['tempStatusPath'] = "/home/cyberpanel/" + str(randint(1000, 9999))

            ct = CyberTron(data)
            ct.start()
            time.sleep(2)

            data_ret = {"success": 1, 'error_message': "None",
                        'tempStatusPath': data['tempStatusPath']}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            virtualMachineAPI.deleteVirtualMachine(data['hostname'])
            data_ret = {"success": 0,
                        'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def createSnapshots(self, request = None, userID = None, hostName = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            return render(request, 'backup/createSnapshots.html', {'hostName': hostName})

        except BaseException, msg:
            return HttpResponse(str(msg))

    def fetchCurrentSnapshots(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']

            vps = VPS.objects.get(hostName=hostName)
            snapshots = vps.snapshots_set.all()

            json_data = "["
            checker = 0

            for snapshot in snapshots:
                dic = {
                    'id': snapshot.id,
                    'hostname': hostName,
                    'name': snapshot.name,
                    'creationTime': snapshot.creationTime,
                }

                if checker == 0:
                    json_data = json_data + json.dumps(dic)
                    checker = 1
                else:
                    json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_dic = {'success': 1, 'error_message': "None", "data": json_data,
                         'successMessage': 'Successfully fetched!'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def submitSnapshotCreation(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']
            snapshotName = data['snapshotName']

            vps = VPS.objects.get(hostName=hostName)

            if Snapshots.objects.filter(vps=vps, name=snapshotName).count() > 0:
                data_ret = {"success": 0,
                            'error_message': 'Snapshot with this name already exists for this Virtual Machine.'}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

            virtualMachineAPI.createSnapshot(hostName, snapshotName)

            newSnapshot = Snapshots(vps=vps, name=snapshotName, creationTime=time.strftime("%I-%M-%S-%a-%b-%Y"))
            newSnapshot.save()

            data_ret = {"success": 1, 'error_message': "None",
                        'successMessage': 'Snapshot Successfully Created!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def deletSnapshot(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']
            snapshotName = data['snapshotName']

            virtualMachineAPI.deleteSnapshot(hostName, snapshotName)

            newSnapshot = Snapshots.objects.get(name=snapshotName)
            newSnapshot.delete()

            data_ret = {"success": 1, 'error_message': "None",
                        'successMessage': 'Snapshot Successfully Deleted!'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def revertToSnapshot(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            hostName = data['hostName']
            snapshotName = data['snapshotName']

            virtualMachineAPI.revertToSnapshot(hostName, snapshotName)

            data_ret = {"success": 1, 'error_message': "None",
                        'successMessage': 'Successfully reverted Virtual Machine to: ' + snapshotName}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

    def startWebsocketServer(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)
            if vmmACLManager.checkOwner(currentACL, userID) == 0:
                return ACLManager.loadErrorJson()

            vpsHostname = data['hostname']

            vps = VPS.objects.get(hostName=vpsHostname)

            hostnameFile = "/etc/cyberpanel/hostname"
            hostname = open(hostnameFile, 'r')
            actualHostName = hostname.read()
            actualHostName = actualHostName.split('\n', 1)[0]

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            vncHostIP = ipData.split('\n', 1)[0]

            frontVNCPort = str(vps.websocketPort + 9000)
            backVNCPort = str(vps.websocketPort + 5900)


            command = 'sudo /usr/local/lscp/cyberpanel/noVNC/utils/launch.sh --listen ' + frontVNCPort + ' --vnc ' \
                      +  vncHostIP + ':' + backVNCPort + ' --cert /usr/local/lscp/cyberpanel/noVNC/utils/self.pem'
            subprocess.Popen(shlex.split(command))

            finalURL = 'https://' + actualHostName + ":" + frontVNCPort + "/vnc.html?host=" + actualHostName + \
                       "&port=" + frontVNCPort + '&password=' + vps.vncPassword + "&autoconnect"


            data_ret = {"success": 1, 'error_message': "None",
                        'finalURL': finalURL}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException, msg:
            final_json = json.dumps({'status': 0, 'errorMessage': str(msg)})
            return HttpResponse(final_json)

