from CyberTronLogger import CyberTronLogger as logger
from inspect import stack
from shlex import split
from subprocess import call, CalledProcessError
from os.path import join
from os import remove,path
from random import randint
from shutil import move
from time import sleep
from logLevel import logLevel
from multiprocessing import Process

class virtualMachineAPIOpenVZ:
    ## os.path.join
    templatesPath = join('/var', 'lib', 'libvirt', 'templates')
    imagesPath = join('/vz', 'root')
    defaultInterface = 'eth0'
    backupPath = join('/vz','dump')

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


                eth0File.writelines('allow-hotplug eth0\n')
                eth0File.writelines('iface eth0 inet static\n')

                eth0File.writelines('	address ' + ipAddress + '\n')
                eth0File.writelines('	netmask ' + netmask + '\n')
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
                eth0File.writelines('NAME=eth0\n')
                eth0File.writelines('ONBOOT=yes\n')
                eth0File.writelines('AUTOCONNECT_PRIORITY=-999\n')

                eth0File.writelines('DEVICE=eth0\n')
                eth0File.writelines('IPADDR=' + ipAddress + '\n')
                eth0File.writelines('NETMASK=' + netmask + '\n')
                eth0File.writelines('GATEWAY=' + gateway + '\n')
                eth0File.writelines('DNS1=8.8.8.8\n')
                eth0File.writelines('IPV6_PRIVACY=no\n')

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

    @staticmethod
    def createContainer(vmName, containerID, osTemplate):
        try:

            command = "vzctl create " + containerID + " --ostemplate " + osTemplate
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Container successfully created for: " + vmName + ".", "Debug",
                                     stack()[0][3])
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
    def bootVirtualMachine(vmName, osTemplate, containerID, rootPassword, hostName, macAddress, uploadSource, cpuUnits,
                           cpuPercentage, vmVCPUs, vmRam, vmSwap, burstVMRam, size,
                           dnsNSOne="8.8.8.8", dnsNSTwo="8.8.4.4",
                           ioPriority=3, uploadSpeed=0, bandwidthSuspend=1, debug=False):
        try:
            ioPriority = str(ioPriority)

            command = "vzctl set " + containerID + " --save --name " + vmName + " --onboot yes --hostname " + hostName + \
                      " --netif_add eth0,,," + macAddress + " --nameserver " + dnsNSOne + " --nameserver " + dnsNSTwo + \
                      " --cpus " + vmVCPUs + " --ram " + vmRam + " --swap " + vmSwap + " --diskspace " + size + \
                      " --userpasswd root:" + rootPassword + " --ioprio " + ioPriority + " --cpuunits " + cpuUnits + \
                      " --cpulimit " + cpuPercentage


            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass



            command = "vzctl start " + containerID


            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            sleep(2)

            finalVMPath = join(virtualMachineAPIOpenVZ.imagesPath,containerID)

            if osTemplate.find('centos') > -1:
                move(uploadSource[0],finalVMPath + '/etc/sysconfig/network-scripts/ifcfg-eth0')
                move(uploadSource[1], finalVMPath + '/etc/sysconfig/network')
                move(uploadSource[2], finalVMPath + '/etc/resolv.conf')
            elif osTemplate.find('debian') > -1:
                move(uploadSource[0], finalVMPath + '/etc/network/interfaces')
            elif osTemplate.find('ubuntu') > -1:
                move(uploadSource[0], finalVMPath + '/etc/network/interfaces')
            elif osTemplate.find('fedora') > -1:
                move(uploadSource[0], finalVMPath + '/etc/sysconfig/network-scripts/ifcfg-eth0')

            command = "vzctl exec " + containerID + " /etc/init.d/network restart"


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



    """

        vmName = Name of the virtual machine, usually the IP Address.
        containerID = Container ID of VPS, which usually identify OpenVZ VPS. Starts 100 and above.
        osTemplate = osTemplate that will be used to boot OpenVZ Container.
        rootPassword = VPS Root Password.
        size = Size in GBs of OpenVZ Container.
        vmRam = Guranteed dedicated virtual machine ram.
        burstVMRam = Burstable ram, ram that VM can acquire if it is avaiable by host node.
        bandwidth = Bandwidth allowed to container.
    """

    @staticmethod
    def createVirtualMachine(vmName, containerID, osTemplate, rootPassword, size, vmRam, vmSwap, burstVMRam, bandwidth, cpuUnits,
                             vmVCPUs,cpuPercentage, ipAddress, netmask, gateway, hostName, macAddress,
                             dnsNSOne = "8.8.8.8", dnsNSTwo = "8.8.4.4", networkSpeed = '0',
                             ioPriority = 3, uploadSpeed = 0,  bandwidthSuspend = 1):
        try:

            logger.operationsLog('Starting to create virtual machine: ' + vmName, 'Info', stack()[0][3])

            ##

            uploadSource = virtualMachineAPIOpenVZ.setupNetworkingFiles(vmName, osTemplate, ipAddress, netmask, gateway, hostName)

            ##

            if virtualMachineAPIOpenVZ.createContainer(vmName, containerID, osTemplate) == 0:
                raise BaseException("Failed to create container.")

            ##

            if virtualMachineAPIOpenVZ.bootVirtualMachine(vmName, osTemplate, containerID, rootPassword, hostName, macAddress, uploadSource,
                                                          cpuUnits, cpuPercentage, vmVCPUs, vmRam, vmSwap, burstVMRam,
                                                          size, dnsNSOne, dnsNSTwo,
                                                          ioPriority, uploadSpeed,bandwidthSuspend) == 0:
                raise BaseException("Failed to boot container.")


            #if virtualMachineAPIOpenVZ.limitContainerSpeed(containerID, ipAddress, virtualMachineAPIOpenVZ.defaultInterface, networkSpeed) == 0:
            #    raise BaseException("Failed to set network limits.")

            ##

            logger.operationsLog('Virtual machine ' + vmName + ' successfully created.', 'Success', stack()[0][3])

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0

    @staticmethod
    def deleteVirtualMachine(containerID):
        try:

            result = virtualMachineAPIOpenVZ.hardShutdown(containerID)

            if result[0] == 1:

                command = "vzctl destroy " + containerID
                result = call(split(command))

                if result == 1:
                    raise CalledProcessError
                else:
                    pass

                return 1,'No error.'

            else:
                return 0, 'Failed to stop virtual machine.'


        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def softReboot(containerID):
        try:

            command = "vzctl restart " + containerID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1,'No error.'

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def hardShutdown(containerID):
        try:

            command = "vzctl stop " + containerID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1,'No error.'

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def startContainer(containerID):
        try:

            command = "vzctl start " + containerID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1,'No error.'

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def suspendContainer(containerID):
        try:

            command = "vzctl suspend " + containerID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1,'No error.'

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def resumeContainer(containerID):
        try:
            command = "vzctl resume " + containerID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            return 1, 'No error.'

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            return 0, str(msg)

    @staticmethod
    def limitContainerSpeed(containerID, containerIP, interface, interfaceLimit):
        try:
            ## Creating class

            command = 'tc class add dev ' + interface + ' parent 2:1 classid ' + '2:' + containerID + ' htb rate '+ interfaceLimit

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            ## Create IP Filter.

            command = 'tc filter add dev ' + interface + ' parent 2:0 protocol ip prio 1 u32 match ip src ' + containerIP + ' flowid 2:' + containerID

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
    def removeContainerSpeedLimit(containerID, interface):
        try:
            ## Removing filter.

            command = 'tc filter del dev ' + interface + ' parent 2:0 protocol ip prio 1 u32 flowid 2:' + containerID

            result = call(split(command))

            if result == 1:
                raise CalledProcessError
            else:
                pass

            ## Removing class.

            command = 'tc class del dev ' + interface + ' classid 2:' + containerID

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
    def createBackup(containerID, suspend = False , stop = False):
        try:

            statusFilePath = join(virtualMachineAPIOpenVZ.backupPath, 'vzdump-' + containerID + '.log')

            if path.exists(statusFilePath):
                remove(statusFilePath)

            if suspend == True:
                command = 'vzdump --compress --suspend ' + containerID
            elif stop == True:
                command = 'vzdump --compress --stop ' + containerID
            else:
                command = 'vzdump --compress ' + containerID

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
    def initiateBackup(containerID, suspend=False, stop=False):
        try:
            p = Process(target=virtualMachineAPIOpenVZ.createBackup, args=(containerID, suspend, stop,))
            p.start()
            # pid = open(backupPath + 'pid', "w")
            # pid.write(str(p.pid))
            # pid.close()
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
    def checkBackupCreationStatus(containerID):
        try:

            statusFilePath = join(virtualMachineAPIOpenVZ.backupPath,'vzdump-' + containerID + '.log')

            statusFile = open(statusFilePath, 'r')
            dataInStatusFile = statusFile.read()
            statusFile.close()

            if dataInStatusFile.find('Finished Backup of') > -1:
                return 1,dataInStatusFile
            else:
                return 0,dataInStatusFile


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


def main():

    virtualMachineAPIOpenVZ.initiateBackup('105')

    while(1):
        retValue = virtualMachineAPIOpenVZ.checkBackupCreationStatus('105')

        if retValue[0] == 0:
            print retValue[1]
        else:
            print "Completed"
            break

#main()






virtualMachineAPIOpenVZ.createVirtualMachine('192.111.145.235','102',"centos-7-x86_64-minimal","litespeed12",
                                             '70G','4G','2G','6G','100GB','900','2','20%','192.111.145.235','255.255.255.248',
                                             '192.111.145.233','cybertronproject.com','FE:FF:FF:FF:FF:FF', '8.8.8.8', '8.8.4.4',
                                             '2Mbit', 4, 0, 1)


#virtualMachineAPIOpenVZ.removeContainerSpeedLimit('105','eth0')
#virtualMachineAPIOpenVZ.limitContainerSpeed('105','192.111.145.238','eth0','256Kbit')

#print virtualMachineAPI.deleteVirtualMachine('109.238.12.214')

#print virtualMachineAPI.revertToSnapshot('109.238.12.214','CyberPanel')

#virtualMachineAPIOpenVZ.deleteVirtualMachine('102')
#virtualMachineAPIOpenVZ.softReboot('102')
#virtualMachineAPIOpenVZ.hardShutdown('102')
#virtualMachineAPIOpenVZ.startContainer('102')
