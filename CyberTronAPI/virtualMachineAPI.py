from CyberTronLogger import CyberTronLogger as logger
from inspect import stack
from shlex import split
from subprocess import call,CalledProcessError
from os.path import join
from os import remove
from random import randint
from shutil import move
import libvirt
from logLevel import logLevel

class virtualMachineAPI:

    ## os.path.join
    templatesPath = join('/var','lib','libvirt','templates')
    imagesPath = join('/var','lib','libvirt','images')


    @staticmethod
    def setupNetworkingFiles(vmName, osName, ipAddress, netmask, gateway, hostName):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Setting up network for: ' + vmName + '.', 'Debug', stack()[0][3])

            uploadSource = []

            if osName.find("centos") > -1:
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

                network = "network_" +  str(randint(10000, 99999) + 1)
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
            elif osName.find("debian") > -1 or osName.find("ubuntu") > -1:

                ###### /etc/network/interfaces

                eth0 = "interfaces_" + str(randint(10000, 99999))
                eth0File = open(eth0, 'w')

                eth0File.writelines('# This file describes the network interfaces available on your system\n')
                eth0File.writelines('# and how to activate them. For more information, see interfaces(5).\n')

                eth0File.writelines('\n')

                eth0File.writelines('# The loopback network interface\n')
                eth0File.writelines('auto lo\n')
                eth0File.writelines('iface lo inet loopback\n')

                eth0File.writelines('\n')

                ## To deal with Debian 9.3 and ubuntu 16.04 issue.

                eth0File.writelines('# The primary network interface\n')

                if osName == "debian-9.3.x64" or osName == "ubuntu-16.04.x32" or osName == "ubuntu-16.04.x64" or  osName == "ubuntu-17.10.x64":
                    eth0File.writelines('allow-hotplug ens3\n')
                    eth0File.writelines('iface ens3 inet static\n')
                else:
                    eth0File.writelines('allow-hotplug eth0\n')
                    eth0File.writelines('iface eth0 inet static\n')

                eth0File.writelines('	address '+ipAddress+'\n')
                eth0File.writelines('	netmask ' + netmask +'\n')
                eth0File.writelines('	gateway ' + gateway + '\n')
                eth0File.writelines('# dns-* options are implemented by the resolvconf package, if installed\n')
                eth0File.writelines('dns-nameservers 8.8.8.8\n')
                eth0File.writelines('dns-search com\n')

                eth0File.close()

                uploadSource.append(eth0)
            elif osName.find("fedora") > -1:

                ###### /etc/sysconfig/network-scripts/ifcfg-ens3

                eth0 = "interfaces_" + str(randint(10000, 99999))
                eth0File = open(eth0, 'w')

                eth0File.writelines('TYPE=Ethernet\n')
                eth0File.writelines('PROXY_METHOD=none\n')


                eth0File.writelines('BROWSER_ONLY=no\n')
                eth0File.writelines('BOOTPROTO=none\n')
                eth0File.writelines('DEFROUTE=yes\n')


                eth0File.writelines('IPV4_FAILURE_FATAL=no\n')
                eth0File.writelines('IPV6INIT=yes\n')
                eth0File.writelines('IPV6_AUTOCONF=yes\n')

                eth0File.writelines('IPV6_DEFROUTE=yes\n')
                eth0File.writelines('IPV6_FAILURE_FATAL=no\n')
                eth0File.writelines('IPV6_ADDR_GEN_MODE=stable-privacy\n')
                eth0File.writelines('NAME=ens3\n')
                eth0File.writelines('ONBOOT=yes\n')
                eth0File.writelines('AUTOCONNECT_PRIORITY=-999\n')

                eth0File.writelines('DEVICE=ens3\n')
                eth0File.writelines('IPADDR=' + ipAddress + '\n')
                eth0File.writelines('NETMASK=' + netmask + '\n')
                eth0File.writelines('GATEWAY=' + gateway + '\n')
                eth0File.writelines('DNS1=8.8.8.8\n')
                eth0File.writelines('IPV6_PRIVACY=no\n')

                eth0File.close()
                uploadSource.append(eth0)
            elif osName.find("freebsd") > -1:

                ###### /etc/rc.conf

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
    def setupVMDisk(vmName, osName, size, uploadSource, rootPassword):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Creating disk image for: ' + vmName + '.', 'Debug', stack()[0][3])

            sourcePath = join(virtualMachineAPI.templatesPath,osName+".qcow2")
            tempPath = join(virtualMachineAPI.imagesPath,vmName+"-temp.qcow2")
            finalPath = join(virtualMachineAPI.imagesPath,vmName+".qcow2")

            ## Build upload command

            uploadCommand = ""

            if osName.find('centos') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/sysconfig/network-scripts/ifcfg-eth0"
                uploadCommand = uploadCommand + " --upload " + uploadSource[1] + ":" + "/etc/sysconfig/network"
                uploadCommand = uploadCommand + " --upload " + uploadSource[2] + ":" + "/etc/resolv.conf"
            elif osName.find('debian') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/network/interfaces" + " --firstboot-command 'apt-get purge openssh-server -y' --firstboot-command 'apt-get install openssh-server -y'"
            elif osName.find('ubuntu') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/network/interfaces" + " --firstboot-command 'apt-get remove openssh-server -y' --firstboot-command 'apt-get install openssh-server -y'"
            elif osName.find('fedora') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/sysconfig/network-scripts/ifcfg-ens3" + " --firstboot-command 'yum erase openssh-server -y' --firstboot-command 'yum install openssh-server -y'"

            ## Creating temporary disk image.

            command = "qemu-img create -b " + sourcePath + " -f qcow2 " + tempPath
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Temporary image created for: " + vmName + ".", "Debug", stack()[0][3])

            ## Checking size, if less or = 3GB, no need to resize.

            if int(size) <= 3:
                move(tempPath, finalPath)

                if logLevel.debug == True:
                    logger.operationsLog("Image successfully prepared for: " + vmName + ".", "Debug", stack()[0][3])

            else:

                command = "qemu-img create -f qcow2 " + finalPath + " " + size + "G"
                result = call(split(command))

                if result == 1:
                    raise CalledProcessError

                if logLevel.debug == True:
                    logger.operationsLog("Created resized final image for: " + vmName + ".", "Debug", stack()[0][3])

                if osName == "centos-7.4.x64":

                    command = "virt-resize --expand /dev/sda2 --lv-expand /dev/centos/root " + tempPath + " " + finalPath
                    result = call(split(command))


                    if result == 1:
                        remove(tempPath)
                        raise CalledProcessError
                    else:
                        remove(tempPath)

                    if logLevel.debug == True:
                        logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                                 stack()[0][3])
                elif osName == "centos-6.9.x64" or osName == "centos-6.9.x32":

                    command = "virt-resize --expand /dev/sda2 --lv-expand /dev/VolGroup/lv_root " + tempPath + " " + finalPath
                    result = call(split(command))

                    if result == 1:
                        remove(tempPath)
                        raise CalledProcessError
                    else:
                        remove(tempPath)

                    if logLevel.debug == True:
                        logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                             stack()[0][3])
                elif osName == "debian-7.11.x32" or osName == "debian-7.11.x64":

                    command = "virt-resize --expand /dev/sda1 --lv-expand /dev/debian/root " + tempPath + " " + finalPath
                    result = call(split(command))

                    if result == 1:
                        remove(tempPath)
                        raise CalledProcessError
                    else:
                        remove(tempPath)

                    if logLevel.debug == True:
                        logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                                 stack()[0][3])
                elif osName == "debian-8.10.x32" or osName == "debian-8.10.x64" or osName == "debian-9.3.x64":
                    command = "virt-resize --expand /dev/sda2 --lv-expand /dev/debian/root " + tempPath + " " + finalPath
                    result = call(split(command))

                    if result == 1:
                        remove(tempPath)
                        raise CalledProcessError
                    else:
                        remove(tempPath)

                    if logLevel.debug == True:
                        logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                             stack()[0][3])
                elif osName == "fedora-27.x64" or osName == "fedora-26.x64":
                    command = "virt-resize --expand /dev/sda2 --lv-expand /dev/fedora/root " + tempPath + " " + finalPath
                    result = call(split(command))

                    if result == 1:
                        remove(tempPath)
                        raise CalledProcessError
                    else:
                        remove(tempPath)

                    if logLevel.debug == True:
                        logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                                stack()[0][3])
                elif osName == "ubuntu-14.04.x32" or osName == "ubuntu-14.04.x64" or osName == "ubuntu-16.04.x32" or osName == "ubuntu-16.04.x64" or osName == "ubuntu-17.10.x64":
                    command = "virt-resize --expand /dev/sda2 --lv-expand /dev/ubuntu/root " + tempPath + " " + finalPath
                    result = call(split(command))

                    if result == 1:
                        remove(tempPath)
                        raise CalledProcessError
                    else:
                        remove(tempPath)

                    if logLevel.debug == True:
                        logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                                 stack()[0][3])


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

        except BaseException,msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0
        except CalledProcessError,msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0


    """
    Function to create Virtual Machine Disk, which can than be used to create virtual machine.

    vmName = Name of vps, this will be combined with imgDestination and format.
    osName = Name of OS, with which this image should be created.
    vmDestination = Destination on disk where this image should be placed.
    size = Size in GBs.
    format = Examples, qcow2, img, qcow, recommend is qcow2.
    uploadSource = An array containing complete path of files to be uploaded to the image after creation.
    debug = Enable or disable extended debug logging. Defaults to false.

    """

    @staticmethod
    def createVirtualMachineDisk(vmName, osName , vmDestination, size, format, uploadSource):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Creating disk image for: ' + vmName + '.', 'Debug', stack()[0][3])

            ## Build upload command

            uploadCommand = ""

            if osName.find('centos') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/sysconfig/network-scripts/ifcfg-eth0"
                uploadCommand = uploadCommand + " --upload " + uploadSource[1] + ":" + "/etc/sysconfig/network"
                uploadCommand = uploadCommand + " --upload " + uploadSource[2] + ":" + "/etc/resolv.conf"

            ## Final Image Location -- finalImageLocation = /var/lib/libvirt/192.168.100.1.qcow2

            finalImageLocation = join(vmDestination, vmName + "." + format)

            ## "virt-builder centos-7.1 -o /var/lib/libvirt/images192.168.100.1.qcow2 --size 50G --format qcow2 --upload ifcfg-eth0:/etc/sysconfig/network-scripts/ --upload network:/etc/sysconfig

            command = "virt-builder " + osName + " -o " + finalImageLocation + " --size " + size + " --format " + format + uploadCommand
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Disk image created for: " + vmName + ".", "Debug", stack()[0][3])

            ## Remove temporary generated files

            #for tempFiles in uploadSource:
                #remove(tempFiles)

            return 1

        except BaseException,msg:
            if logLevel.debug == True:
                logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0
        except CalledProcessError,msg:
            if logLevel.debug == True:
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
    def bootVirtualMachine(vmName, vmRam, vmVCPUs, vncHost, vncPort, osType, osVariant, bridgeName):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Booting: ' + vmName + '.','Debug',stack()[0][3])


            finalImageLocation = join(virtualMachineAPI.imagesPath,vmName+".qcow2")

            # virt-install --name 109.238.12.214 --ram 2048 --vcpus=1 --disk 109.238.12.214.qcow2 --graphics vnc,listen=localhost,port=5500 --noautoconsole --hvm --import --os-type=linux --os-variant=rhel7 --network bridge=virbr0

            command = "virt-install --name " + vmName + " --ram " + vmRam + " --vcpu " + vmVCPUs  + " --disk " + \
                      finalImageLocation + " --graphics vnc,listen=" +vncHost + ",port=" + vncPort + \
                      " --noautoconsole --hvm --import --autostart --os-type=" + osType + " --os-variant=" + \
                      osVariant + " --network bridge=" + bridgeName
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
    def createVirtualMachine(vmName, osName, rootPassword, size, vncHost, vmRam, vmVCPUs, vncPort, osType, osVariant, bridgeName, ipAddress, netmask, gateway, hostName):
        try:

            logger.operationsLog('Starting to create virtual machine: ' + vmName, 'Info', stack()[0][3])

            ##

            uploadSource = virtualMachineAPI.setupNetworkingFiles(vmName, osName, ipAddress, netmask, gateway, hostName)

            ##

            if virtualMachineAPI.setupVMDisk(vmName, osName, size, uploadSource, rootPassword) == 0:
                return 0

            ##

            if virtualMachineAPI.bootVirtualMachine(vmName, vmRam, vmVCPUs, vncHost, vncPort, osType, osVariant, bridgeName) == 0:
                return 0

            ##

            logger.operationsLog('Virtual machine ' + vmName + ' successfully created.', 'Success', stack()[0][3])

            return 1

        except BaseException, msg:
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
    def obtainVirtualMachineObject(virtualMachineName):
        try:
            connection = libvirt.open('qemu:///system')

            if connection == None:
                return 0, 'Failed to establish connection.'

            virtualMachine = connection.lookupByName(virtualMachineName)

            if virtualMachine == None:
                return 0, 'Can not find virtual machine.'

            return 1,virtualMachine


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
                if virtualMachine.reboot():
                    return 1, 'No error.'
                else:
                    return 0,'Failed to reboot.'
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
                if virtualMachine.destroy():
                    return 1, 'No error.'
                else:
                    return 0,'Failed to shutdown.'
            else:
                return 0,'Failed to obtain virtual machine object.'
        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)




virtualMachineAPI.createVirtualMachine('192.111.145.235','centos-7.4.x64',"litespeedtech","50",'192.111.145.234','2048','2','5900','linux','rhel7','virbr0','192.111.145.235','255.255.255.248','192.111.145.233','usman.cybertronproject.com')

#print virtualMachineAPI.deleteVirtualMachine('109.238.12.214')

#print virtualMachineAPI.revertToSnapshot('109.238.12.214','CyberPanel')
#virtualMachineAPI.softReboot('109.238.12.214')