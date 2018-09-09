#!/usr/local/CyberCP/bin/python2
import os,sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import threading as multi
from CyberTronLogger import CyberTronLogger as logger
from inspect import stack
from shlex import split
from subprocess import call,CalledProcessError
from os.path import join
from random import randint
from logLevel import logLevel
from ipManagement.models import IPAddresses
from packages.models import VMPackage as Package
from django.db.models import Max
import CyberTronAPI.randomPassword as randomPassword
from vpsManagement.models import VPS, SSHKeys
from loginSystem.models import Administrator
from CyberTronAPI.virtualMachineAPIKVM import virtualMachineAPI
import plogical.CyberCPLogFileWriter as logging
from os import remove


class CyberTron(multi.Thread):
    imagesPath = join('/var', 'lib', 'libvirt', 'images')
    templatesPath = join('/var', 'lib', 'libvirt', 'templates')

    def __init__(self, data):
        multi.Thread.__init__(self)
        self.data = data

    def run(self):
        try:
            self.createVirtualMachine(self.data)
        except BaseException, msg:
            logger.writeToFile(str(msg), "Error", stack()[0][3])

    def setupNetworkingFiles(self, ipAddress, osName, ipPool, hostName, tempStatusPath):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Setting up network for: ' + ipAddress + '.', 'Debug', stack()[0][3])

            uploadSource = []

            ## Set Device name
            deviceName = ''

            if osName == 'centos-6':
                deviceName = 'eth0'
            elif osName == 'centos-7.2':
                deviceName = 'ens3'
            elif osName == 'debian-9' or osName == 'ubuntu-16.04':
                deviceName = 'ens3'


            if osName.find("centos") > -1:
                ###### /etc/sysconfig/network-scripts/ifcfg-eth0

                eth0 = "/home/cyberpanel/ifcfg-ens3" + str(randint(10000, 99999))
                eth0File = open(eth0, 'w')

                eth0File.writelines('DEVICE="' + deviceName + '"\n')
                eth0File.writelines('NM_CONTROLLED="yes"\n')
                eth0File.writelines('ONBOOT=yes\n')
                eth0File.writelines('TYPE=Ethernet\n')
                eth0File.writelines('BOOTPROTO=static\n')
                eth0File.writelines('NAME="System ' + deviceName + '"\n')
                eth0File.writelines('IPADDR=' + ipAddress + '\n')
                eth0File.writelines('NETMASK=' + ipPool.netmask + '\n')

                eth0File.close()

                uploadSource.append(eth0)

                ###### /etc/sysconfig/network

                network = "/home/cyberpanel/network_" + str(randint(10000, 99999) + 1)
                networkFile = open(network, 'w')

                networkFile.writelines('NETWORKING=yes\n')
                networkFile.writelines('HOSTNAME=' + hostName + '\n')
                networkFile.writelines('GATEWAY=' + ipPool.gateway + '\n')

                networkFile.close()

                uploadSource.append(network)

                ###### /etc/resolv.conf

                resolv = "/home/cyberpanel/resolv_" + str(randint(10000, 99999) + 2)
                resolvFile = open(resolv, 'w')

                resolvFile.writelines("nameserver 8.8.8.8\n")

                resolvFile.close()

                uploadSource.append(resolv)
            elif osName == 'ubuntu-18.04':

                eth0 = "/home/cyberpanel/interfaces_" + str(randint(10000, 99999))
                eth0File = open(eth0, 'w')

                eth0File.writelines('# This file describes the network interfaces available on your system\n')
                eth0File.writelines('# For more information, see netplan(5).\n')

                eth0File.writelines('\n')

                eth0File.writelines('network:\n')
                eth0File.writelines('  version: 2\n')
                eth0File.writelines('  renderer: networkd\n')
                eth0File.writelines('  ethernets:\n')
                eth0File.writelines('    ens2:\n')
                eth0File.writelines('      dhcp4: yes\n')
                eth0File.writelines('    ens3:\n')
                eth0File.writelines('      dhcp4: no\n')
                eth0File.writelines('      addresses: [' + ipAddress + '/24]\n')
                eth0File.writelines('      gateway4: ' + ipPool.gateway + '\n')
                eth0File.writelines('      nameservers:\n')
                eth0File.writelines('       addresses: [8.8.8.8,8.8.4.4]\n')

                eth0File.writelines('\n')

                eth0File.close()

                uploadSource.append(eth0)
            elif osName.find("debian") > -1 or osName.find("ubuntu") > -1:
                ###### ip

                eth0 = "/home/cyberpanel/interfaces_" + str(randint(10000, 99999))
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


                eth0File.writelines('allow-hotplug ' + deviceName + '\n')
                eth0File.writelines('iface ' + deviceName + ' inet static\n')


                eth0File.writelines('	address ' + ipAddress + '\n')
                eth0File.writelines('	netmask ' + ipPool.netmask + '\n')
                eth0File.writelines('	gateway ' + ipPool.gateway + '\n')
                eth0File.writelines('# dns-* options are implemented by the resolvconf package, if installed\n')
                eth0File.writelines('dns-nameservers 8.8.8.8\n')
                eth0File.writelines('dns-search com\n')

                eth0File.close()

                uploadSource.append(eth0)
            elif osName.find("fedora") > -1:

                ###### /etc/sysconfig/network-scripts/ifcfg-ens3

                eth0 = "/home/cyberpanel/interfaces_" + str(randint(10000, 99999))
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
                eth0File.writelines('NETMASK=' + ipPool.netmask + '\n')
                eth0File.writelines('GATEWAY=' + ipPool.gateway + '\n')
                eth0File.writelines('DNS1=8.8.8.8\n')
                eth0File.writelines('IPV6_PRIVACY=no\n')

                eth0File.close()
                uploadSource.append(eth0)
            elif osName.find("freebsd") > -1:

                ###### /etc/rc.conf

                eth0 = "/home/cyberpanel/ifcfg-eth0_" + str(randint(10000, 99999))
                eth0File = open(eth0, 'w')

                eth0File.writelines('DEVICE="eth0"\n')
                eth0File.writelines('NM_CONTROLLED="yes"\n')
                eth0File.writelines('ONBOOT=yes\n')
                eth0File.writelines('TYPE=Ethernet\n')
                eth0File.writelines('BOOTPROTO=static\n')
                eth0File.writelines('NAME="System eth0"\n')
                eth0File.writelines('IPADDR=' + ipAddress + '\n')
                eth0File.writelines('NETMASK=' + ipPool.gateway + '\n')

                eth0File.close()

                uploadSource.append(eth0)
            if logLevel.debug == True:
                logger.operationsLog('Network settings installed for: ' + ipAddress + '.', 'Debug', stack()[0][3])

            return uploadSource

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ' [404]')
            return 0

    def buildCustomDisk(self, vmName, osName, size, rootPassword, uploadCommand, tempStatusPath):
        try:

            sourcePath = join(virtualMachineAPI.templatesPath, osName + ".img")
            tempPath = join(virtualMachineAPI.imagesPath, vmName + "-temp.qcow2")
            finalPath = join(virtualMachineAPI.imagesPath, vmName + ".qcow2")

            ## Creating temporary disk image.

            command = "sudo cp " + sourcePath + " " + tempPath
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Temporary image created for: " + vmName + ".", "Debug", stack()[0][3])

            command = "sudo qemu-img create -f qcow2 " + finalPath + " " + size
            result = call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Created resized final image for: " + vmName + ".", "Debug", stack()[0][3])

            command = "sudo virt-resize --expand /dev/sda1 " + tempPath + " " + finalPath
            result = call(split(command))

            if result == 1:
                remove(tempPath)
                raise CalledProcessError
            else:
                remove(tempPath)

            if logLevel.debug == True:
                logger.operationsLog("Disk resized and ready to use for: " + vmName + ".", "Debug",
                                     stack()[0][3])

            command = "sudo virt-customize -a " + finalPath + " --root-password password:" + rootPassword + uploadCommand
            call(split(command))

            if result == 1:
                raise CalledProcessError

            if logLevel.debug == True:
                logger.operationsLog("Root password and network configured for: " + vmName + ".", "Debug",
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
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ' [404]')
            return 0

    def setupVMDisk(self, vmName, osName, uploadSource, rootPassword, package, tempStatusPath, sshKey = None):
        try:
            size = package.diskSpace + 'G'

            if osName.find('centos') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/sysconfig/network-scripts/ifcfg-eth0"
                uploadCommand = uploadCommand + " --upload " + uploadSource[1] + ":" + "/etc/sysconfig/network"
                uploadCommand = uploadCommand + " --upload " + uploadSource[2] + ":" + "/etc/resolv.conf"
            elif osName == 'ubuntu-18.04':
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/netplan/01-netcfg.yaml --firstboot-command 'dpkg-reconfigure openssh-server'"
            elif osName.find('debian') > -1 or osName.find('ubuntu') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/network/interfaces --firstboot-command 'ssh-keygen -t rsa -f /etc/ssh/ssh_host_rsa_key && ssh-keygen -t dsa -f /etc/ssh/ssh_host_dsa_key && ssh-keygen -t ecdsa -f /etc/ssh/ssh_host_ecdsa_key'"
            elif osName.find('fedora') > -1:
                uploadCommand = " --upload " + uploadSource[0] + ":" + "/etc/sysconfig/network-scripts/ifcfg-ens3"

            finalImageLocation = join(CyberTron.imagesPath, vmName + '.qcow2')

            ## "virt-builder centos-7.1 -o /var/lib/libvirt/images192.168.100.1.qcow2 --size 50G --format qcow2 --upload ifcfg-eth0:/etc/sysconfig/network-scripts/ --upload network:/etc/sysconfig

            if osName == 'debian-9' or osName == 'fedora-28' or osName == 'ubuntu-16.04':
                self.buildCustomDisk(vmName, osName, size, rootPassword, uploadCommand, tempStatusPath)
            else:
                if sshKey != None:
                    command = "sudo virt-builder " + osName + " -o " + finalImageLocation + " --size " + size + \
                              " --format qcow2 --root-password password:" + rootPassword + uploadCommand + " --ssh-inject 'root:string:" + sshKey + "'"
                else:
                    command = "sudo virt-builder " + osName + " -o " + finalImageLocation + " --size " + size + \
                              " --format qcow2 --root-password password:" + rootPassword + uploadCommand

                result = call(split(command))

                if result == 1:
                    raise CalledProcessError

                if logLevel.debug == True:
                    logger.operationsLog("Disk image created for: " + vmName + ".", "Debug", stack()[0][3])


        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ' [404]')
            return 0
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ' [404]')
            return 0

    def bootVirtualMachine(self, package, vmName, vncHost, vncPort, vncPassword, webSocketPort, hostname, bridgeName, tempStatusPath):
        try:

            if logLevel.debug == True:
                logger.operationsLog('Booting: ' + vmName + '.', 'Debug', stack()[0][3])

            finalImageLocation = join(CyberTron.imagesPath, vmName + ".qcow2")

            # virt-install --name 109.238.12.214 --ram 2048 --vcpus=1 --disk 109.238.12.214.qcow2 --graphics vnc,listen=localhost,port=5500 --noautoconsole --hvm --import --os-type=linux --os-variant=rhel7 --network bridge=virbr0

            command = "sudo virt-install --name " + hostname + " --ram " + str(package.guaranteedRam) + " --vcpu " + str(package.cpuCores) + " --disk " + \
                      finalImageLocation + " --graphics vnc,listen=" + vncHost + ",port=" + vncPort + ",password=" + vncPassword + \
                      " --noautoconsole --hvm --import --autostart --os-type=linux " \
                      + "--network bridge=" + bridgeName

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
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ' [404]')
            return 0
        except CalledProcessError, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            logging.CyberCPLogFileWriter.statusWriter(tempStatusPath, str(msg) + ' [404]')
            return 0

    def createVirtualMachine(self, data):
        try:

            osName = data['osName']
            vpsPackage = data['vpsPackage']
            vpsOwner = data['vpsOwner']
            vpsIP = data['vpsIP']
            hostname = data['hostname']
            rootPassword = data['rootPassword']
            networkSpeed = data['networkSpeed']

            logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'Running some checks..,0')

            try:
                sshKey = data['sshKey']
                key = SSHKeys.objects.get(keyName=sshKey)
                sshKey = key.key
            except:
                sshKey = None


            owner = Administrator.objects.get(userName=vpsOwner)
            package = Package.objects.get(packageName=vpsPackage)
            ip = IPAddresses.objects.get(ipAddr=vpsIP)

            ## Some checks

            if ip.used == 1:
                logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'This IP is already in use. [404]')
                return 0, 'This IP is already in use.'

            if VPS.objects.filter(hostName=hostname).count() > 0:
                logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'Hostname is already taken. [404]')
                return 0, 'Hostname is already taken.'

            logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'Starting to create virtual machine..,10')

            logger.operationsLog('Starting to create virtual machine: ' + vpsIP, 'Info', stack()[0][3])

            ##

            uploadSource = self.setupNetworkingFiles(vpsIP, osName, ip.pool, hostname, data['tempStatusPath'])

            ##

            logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'],
                                                      'Creating virtual machine disk..,20')

            if self.setupVMDisk(hostname, osName, uploadSource, rootPassword, package, data['tempStatusPath'], sshKey) == 0:
                logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'Failed to setup virtual machine disk. [404]')
                return 0

            logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'],
                                                      'Booting virtual machine..,80')

            ## Server IP

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            vncHost = ipData.split('\n', 1)[0]

            ## Finding VNC Port
            if VPS.objects.count() == 0:
                vncPort = 5900
                webSocketPort = 0
            else:
                vncPort = VPS.objects.all().aggregate(Max('vncPort'))['vncPort__max'] + 1
                webSocketPort = VPS.objects.count()

            vncPassword = randomPassword.generate_pass(50)

            if self.bootVirtualMachine(package, hostname, vncHost, str(vncPort), vncPassword, str(webSocketPort), hostname, 'virbr0', data['tempStatusPath']) == 0:
                logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'Failed to boot virtual machine. [404]')
                return 0

            ## Saving VM To database

            newVPS = VPS(owner=owner, ipAddr=ip, package=package, hostName=hostname, networkSpeed=networkSpeed,
                            vncPort=vncPort, vncPassword=vncPassword, websocketPort=webSocketPort)
            newVPS.save()
            ip.used = 1
            ip.save()

            ## Installing network limitations

            ## Reading interface name

            interfaceFile = "/etc/cyberpanel/interfaceName"
            f = open(interfaceFile)
            interfaceData = f.read()
            interfaceName = interfaceData.split('\n', 1)[0]

            virtualMachineAPI.limitVMSpeed(str(newVPS.id), vpsIP, 'virbr0', networkSpeed)
            logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], 'Virtual Machine successfully created.. [200]')

            logger.operationsLog('Virtual machine ' + vpsIP + ' successfully created.', 'Success', stack()[0][3])

            return 1

        except BaseException, msg:
            if logLevel.debug == True:
                logger.operationsLog(str(msg), "Error", stack()[0][3])
            logger.writeToFile(str(msg), "Error", stack()[0][3])
            logging.CyberCPLogFileWriter.statusWriter(data['tempStatusPath'], str(msg) + ' [404]')
            return 0

