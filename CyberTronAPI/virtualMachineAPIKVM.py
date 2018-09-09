from CyberTronLogger import CyberTronLogger as logger
from inspect import stack
from shlex import split
from subprocess import call,CalledProcessError
from os.path import join
from os import remove, path
from random import randint
import libvirt
from logLevel import logLevel
from xml.etree import ElementTree



class virtualMachineAPI:

    ## os.path.join
    templatesPath = join('/var','lib','libvirt','templates')
    imagesPath = join('/var','lib','libvirt','images')

    @staticmethod
    def obtainVirtualMachineObject(virtualMachineName):
        try:
            connection = libvirt.open('qemu:///system')

            if connection == None:
                return 0, 'Failed to establish connection.'

            virtualMachine = connection.lookupByName(virtualMachineName)

            if virtualMachine == None:
                return 0, 'Can not find virtual machine.'

            return 1, virtualMachine


        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def limitVMSpeed(vpsID, vpsIP, interface, interfaceLimit):
        try:
            ## Creating class

            command = 'tc class add dev ' + interface + ' parent 2:1 classid ' + '2:' + vpsID + ' htb rate ' + interfaceLimit
            logger.writeToFile(command,'Info',stack()[0][3])

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            ## Create IP Filter.

            command = 'tc filter add dev ' + interface + ' parent 2:0 protocol ip prio 1 u32 match ip src ' + vpsIP + ' flowid 2:' + vpsID
            logger.writeToFile(command,'Info',stack()[0][3])
            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def removeVMSpeedLimit(vpsID, interface):
        try:
            ## Removing filter.

            command = 'tc filter del dev ' + interface + ' parent 2:0 protocol ip prio 1 u32 flowid 2:' + vpsID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            ## Removing class.

            command = 'tc class del dev ' + interface + ' classid 2:' + vpsID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def deleteVirtualMachine(virtualMachineName):
        try:

            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)

            if obtainStatus == 1:

                if virtualMachine.hasCurrentSnapshot():
                    snapShots = virtualMachine.listAllSnapshots()
                    for snapShot in snapShots:
                        snapShot.delete()

                if virtualMachine.isActive():
                    virtualMachine.destroy()

                virtualMachine.undefine()

                ## Removing virtual machine file.

                try:
                    pathToImg = join(virtualMachineAPI.imagesPath, virtualMachineName + '.qcow2')
                    remove(pathToImg)
                except BaseException,msg:
                    if logLevel.debug == True:
                        logger.operationsLog(str(msg), "Error", stack()[0][3])
                    logger.writeToFile(str(msg), "Error", stack()[0][3])

                ##

                return 1,'No error.'
            else:
                return 0,'Failed to obtain virtual machine object.'

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def revertToSnapshot(virtualMachineName, snapshotName):
        try:
            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)

            if obtainStatus == 1:
                snapshot = virtualMachine.snapshotLookupByName(snapshotName)
                virtualMachine.revertToSnapshot(snapshot)
                return 1, 'No error.'
            else:
                return 0,'Failed to obtain virtual machine object.'
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def softReboot(virtualMachineName):
        try:
            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)
            if obtainStatus == 1:
                if virtualMachine.isActive():
                    virtualMachine.reboot()
                    return 1, 'No error.'
                else:
                    command = 'virsh start ' + virtualMachineName
                    call(split(command))
                    return 1, 'No error.'
            else:
                return 0,'Failed to obtain virtual machine object.'
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def hardShutdown(virtualMachineName):
        try:
            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)
            if obtainStatus == 1:
                if virtualMachine.isActive():
                    virtualMachine.destroy()
                    return 1, 'No error.'
                else:
                    return 0, 'VPS is not running.'
            else:
                return 0,'Failed to obtain virtual machine object.'
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def setupNetworkingFiles(vmName, ipAddress, netmask, gateway, hostName):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Setting up network for: ' + vmName + '.', 'Debug', stack()[0][3])

            uploadSource = []

            ###### /etc/sysconfig/network-scripts/ifcfg-eth0

            eth0 = "ifcfg-eth0_" + str(randint(10000, 99999))
            eth0File = open(eth0, 'w')

            eth0File.writelines('DEVICE="eth0"\n')
            eth0File.writelines('NM_CONTROLLED="yes"\n')
            eth0File.writelines('ONBOOT=yes\n')
            eth0File.writelines('TYPE=Ethernet\n')
            eth0File.writelines('BOOTPROTO=static\n')
            eth0File.writelines('NAME="System eth0"\n')
            eth0File.writelines('IPADDR=' + ipAddress + '\n')
            eth0File.writelines('NETMASK=' + netmask + '\n')

            eth0File.close()

            uploadSource.append(eth0)

            ###### /etc/sysconfig/network

            network = "network_" + str(randint(10000, 99999) + 1)
            networkFile = open(network, 'w')

            networkFile.writelines('NETWORKING=yes\n')
            networkFile.writelines('HOSTNAME=' + hostName + '\n')
            networkFile.writelines('GATEWAY=' + gateway + '\n')

            networkFile.close()

            uploadSource.append(network)

            ###### /etc/resolv.conf

            resolv = "resolv_" + str(randint(10000, 99999) + 2)
            resolvFile = open(resolv, 'w')

            resolvFile.writelines("nameserver 8.8.8.8\n")

            resolvFile.close()

            uploadSource.append(resolv)

            if logLevel.debug == True:
                logger.operationsLog('Network settings installed for: ' + vmName + '.', 'Debug', stack()[0][3])

            return uploadSource


        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    '''
    vmName = Usually IP Address.
    osName = Examples operatingSystem-X.xx.x86
    uploadSource = An array containing complete path of files to be uploaded to the image after creation.
    rootPassword = Virtual Machine root password.
    '''

    @staticmethod
    def setupVMDisk(vmName, package, uploadSource, rootPassword):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Creating disk image for: ' + vmName + '.', 'Debug', stack()[0][3])

            sourcePath = join(virtualMachineAPI.templatesPath, package + ".qcow2")
            finalPath = join(virtualMachineAPI.imagesPath, vmName + ".qcow2")

            ## Build upload command

            uploadCommand = ""

            uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/sysconfig/network-scripts/ifcfg-eth0"
            uploadCommand = uploadCommand + " --upload " + uploadSource[1] + ":" + "/etc/sysconfig/network"
            uploadCommand = uploadCommand + " --upload " + uploadSource[2] + ":" + "/etc/resolv.conf"
            ## Creating temporary disk image.

            command = "qemu-img create -b " + sourcePath + " -f qcow2 " + finalPath
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Temporary image created for: " + vmName + ".", "Debug", stack()[0][3])

            ## Setup network and customize root password

            command = "virt-customize -a " + finalPath + " --root-password password:" + rootPassword + uploadCommand
            call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Root password and network configured for: " + vmName + ".", "Debug",
                                     stack()[0][3])
                return 1

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    """  
        vmName = Name of the virtual machine, usually the IP Address.
        vmRam = Ram to be assigned to this virtual machine.
        vmVCPUs = Virtual CPUs to be assigned to this virtual machine.
        vmDestination = Path where VM image will be housed.
        format = Examples, qcow2, img, qcow, recommend is qcow2.
        vncPort = VNC Port for this virtual machine.
        osType = OS Type e.g. linux,windows.
        osVariant = OS Variant e.g. centos 6, centos 7.
        bridgeName = Bridge name to which the interface of this VM will be attached.
        debug = Enable or disable extended debug logging. Defaults to false.

        """

    @staticmethod
    def bootVirtualMachine(vmName, vmVCPUs, vmRam,  vncHost, vncPort, bridgeName, webSocketPort, vncPassword):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Booting: ' + vmName + '.', 'Debug', stack()[0][3])

            finalImageLocation = join(virtualMachineAPI.imagesPath, vmName + ".qcow2")

            # virt-install --name 109.238.12.214 --ram 2048 --vcpus=1 --disk 109.238.12.214.qcow2 --graphics vnc,listen=localhost,port=5500 --noautoconsole --hvm --import --os-type=linux --os-variant=rhel7 --network bridge=virbr0

            command = "virt-install --name " + vmName + " --ram " + vmRam + " --vcpu " + vmVCPUs + " --disk " + \
                      finalImageLocation + " --graphics vnc,listen=" + vncHost + ",port=" + vncPort + ",password=" + vncPassword + \
                      ' --qemu-commandline=' + '"' + '-vnc :' + webSocketPort + ',websocket' + '"' + \
                      " --noautoconsole --hvm --import --autostart --os-type=linux " \
                      + "--network bridge=" + bridgeName
            logger.writeToFile(command,"Info", stack()[0][3])
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Successfully booted: " + vmName + ".", "Debug", stack()[0][3])

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    """


            osName = Name of OS, with which this image should be created.
            imgDestination = Destination on disk where this image should be placed.
            imgName = Name of vps, this will be combined with imgDestination.
            size = Size in GBs.
            format = Examples, qcow2, img, qcow, recommend is qcow2.
            uploadSource = An array containing complete path of files to be uploaded to the image after creation.
            UploadDestination = Corressponding array of upload source, defining upload destination of files.

            --

            vmName = Name of the virtual machine, usually the IP Address.
            vmRam = Ram to be assigned to this virtual machine.
            vmVCPUs = Virtual CPUs to be assigned to this virtual machine.
            diskImage = A complete path to disk image for this virtual machine.
            vncPort = VNC Port for this virtual machine.
            osType = OS Type e.g. linux,windows.
            osVariant = OS Variant e.g. centos 6, centos 7.
            bridgeName = Bridge name to which the interface of this VM will be attached.

        """

    @staticmethod
    def createVirtualMachine(vmName, package, rootPassword, vmVCPUs, vmRam, vncHost, vncPort, bridgeName, ipAddress, netmask, gateway, hostName, webSocketPort, vncPassword):
        try:

            logger.operationsLog('Starting to create virtual machine: ' + vmName, 'Info', stack()[0][3])

            ##

            uploadSource = virtualMachineAPI.setupNetworkingFiles(vmName, ipAddress, netmask, gateway, hostName)

            ##
            if virtualMachineAPI.setupVMDisk(vmName, package, uploadSource, rootPassword) == 0:
                return 0

            ##

            if virtualMachineAPI.bootVirtualMachine(vmName, vmVCPUs, vmRam, vncHost, vncPort, bridgeName, webSocketPort, vncPassword) == 0:
                return 0

            ##

            logger.operationsLog('Virtual machine ' + vmName + ' successfully created.', 'Success', stack()[0][3])

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0


#virtualMachineAPI.createVirtualMachine('192.111.145.237', 'forthPlan', 'litespeed12', '2', '2048', '192.111.145.234', '5904','virbr0','192.111.145.237','255.255.255.248','192.111.145.233','usman.cybertronproject.com')

#print virtualMachineAPI.deleteVirtualMachine('109.238.12.214')
#print virtualMachineAPI.revertToSnapshot('109.238.12.214','CyberPanel')
#virtualMachineAPI.softReboot('109.238.12.214')

    @staticmethod
    def isActive(virtualMachineName):
        try:
            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)
            if obtainStatus == 1:
                if virtualMachine.isActive():
                    return 1
                else:
                    return 0
            else:
                return 0

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def getCurrentUsedRam(virtualMachineName):
        try:
            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)
            if obtainStatus == 1:
                if virtualMachine.isActive():
                    memStats = virtualMachine.memoryStats()
                    return int(memStats['unused']/1024)
                else:
                    return 0
            else:
                return 0

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def getBandwidthUsage(virtualMachineName):
        try:
            obtainStatus, virtualMachine = virtualMachineAPI.obtainVirtualMachineObject(virtualMachineName)
            if obtainStatus == 1:
                if virtualMachine.isActive():
                    tree = ElementTree.fromstring(virtualMachine.XMLDesc())
                    iface = tree.find('devices/interface/target').get('dev')
                    memStats = virtualMachine.interfaceStats(iface)
                    ## memStats[0] are read bytes, memStats[4] write bytes
                    return (memStats[0] + memStats[4])/(1024 * 1024)
                else:
                    return 0
            else:
                return 0

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def calculateDiskPercentage(virtualMachineName, actualDisk):
        try:
            vpsImagePath = '/var/lib/libvirt/images/' + virtualMachineName + ".qcow2"
            sizeInMB = float(path.getsize(vpsImagePath)) / (1024.0 * 1024)
            diskUsagePercentage = float(100) / float((int(actualDisk.rstrip('GB')) * 1024))
            diskUsagePercentage = float(diskUsagePercentage) * float(sizeInMB)
            diskUsagePercentage = int(diskUsagePercentage)

            if diskUsagePercentage > 100:
                return 100, sizeInMB

            return diskUsagePercentage, sizeInMB
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0,0

    @staticmethod
    def calculateRamPercentage(virtualMachineName, actualRam):
        try:
            unUsedRam = virtualMachineAPI.getCurrentUsedRam(virtualMachineName)
            usedRam = int(actualRam.rstrip('MB')) - unUsedRam

            ramUsagePercentage = float(100) / int(actualRam.rstrip('MB'))
            ramUsagePercentage = int(float(ramUsagePercentage) * float(usedRam))

            if ramUsagePercentage > 100:
                return 100

            return ramUsagePercentage

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def calculateBWPercentage(virtualMachineName, actualBW):
        try:
            usedBW = virtualMachineAPI.getBandwidthUsage(virtualMachineName)
            availBW = int(actualBW.rstrip('TB')) * 1024 * 1024

            bwPercentage = float(100) / availBW
            bwPercentage = int(float(bwPercentage) * usedBW)

            if bwPercentage > 100:
                return 100

            return bwPercentage

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def changeHostname(virtualMachineName, newHostname):
        try:
            command = "virt-customize -d " + virtualMachineName + " --hostname " + newHostname
            call(split(command))

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def changeRootPassword(virtualMachineName, newPassword):
        try:
            command = "virt-customize -d " + virtualMachineName + " --root-password password:" + newPassword
            call(split(command))
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def createSnapshot(virtualMachineName, snapshotName):
        try:
            command = "virsh snapshot-create-as --domain " + virtualMachineName + " --name " + snapshotName
            call(split(command))
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def deleteSnapshot(virtualMachineName, snapshotName):
        try:
            command = "virsh snapshot-delete --domain " + virtualMachineName + " --snapshotname " + snapshotName
            call(split(command))
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)