#!/usr/local/CyberCP/bin/python2
import CyberCPLogFileWriter as logging
import subprocess
import shlex
import argparse
from virtualHostUtilities import virtualHostUtilities
import os
import tarfile
import shutil
from mailUtilities import mailUtilities
import threading as multi

class CSF(multi.Thread):
    installLogPath = "/home/cyberpanel/csfInstallLog"
    csfURL = 'https://download.configserver.com/csf.tgz'

    def __init__(self, installApp, extraArgs):
        multi.Thread.__init__(self)
        self.installApp = installApp
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.installApp == 'installCSF':
                self.installCSF()
            elif self.installApp == 'removeCSF':
                self.removeCSF()
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [CSF.run]')

    def installCSF(self):
        try:
            ##

            command = 'wget ' + CSF.csfURL
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'a') as f:
                subprocess.call(cmd, stdout=f)

            ##

            command = 'tar -xzf csf.tgz'
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'a') as f:
                res = subprocess.call(cmd, stdout=f)

            ##

            os.chdir('csf')

            command = './install.sh'
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'a') as f:
                res = subprocess.call(cmd, stdout=f)

            os.chdir('/usr/local/CyberCP')

            ## Some initial configurations

            data = open('/etc/csf/csf.conf', 'r').readlines()
            writeToConf = open('/etc/csf/csf.conf', 'w')

            for items in data:
                if items.find('TCP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('TCP_IN = "20,21,22,25,53,80,110,143,443,465,587,993,995,8090,40110:40210"\n')
                elif items.find('TCP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('TCP_OUT = "20,21,22,25,53,80,110,113,443,587,993,995,8090,40110:40210"\n')
                elif items.find('UDP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('UDP_IN = "20,21,53"\n')
                elif items.find('UDP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('UDP_OUT = "20,21,53,113,123"\n')
                else:
                    writeToConf.writelines(items)

            writeToConf.close()
            ##

            command = 'csf -s'
            cmd = shlex.split(command)

            with open(CSF.installLogPath, 'a') as f:
                subprocess.call(cmd, stdout=f)


            writeToFile = open(CSF.installLogPath, 'a')
            writeToFile.writelines("CSF successfully Installed.[200]\n")
            writeToFile.close()

            os.remove('csf.tgz')
            os.removedirs('csf')

            return 1
        except BaseException, msg:
            os.remove('csf.tgz')
            os.removedirs('csf')
            writeToFile = open(CSF.installLogPath, 'a')
            writeToFile.writelines(str(msg) + " [404]")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installCSF]")

    def removeCSF(self):
        try:

            ##

            os.chdir('/etc/csf')

            command = './uninstall.sh'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            os.chdir('/usr/local/CyberCP')

            #

            command = 'systemctl unmask firewalld'
            subprocess.call(shlex.split(command))

            #

            command = 'systemctl start firewalld'
            subprocess.call(shlex.split(command))

            ##

            command = 'systemctl enable firewalld'
            subprocess.call(shlex.split(command))

            return 1
        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[removeCSF]")

    @staticmethod
    def fetchCSFSettings():
        try:

            currentSettings = {}

            command = 'sudo cat /etc/csf/csf.conf'
            output = subprocess.check_output(shlex.split(command)).splitlines()

            for items in output:
                if items.find('TESTING') > -1 and items.find('=') > -1 and (items[0]!= '#') and items.find('TESTING_INTERVAL') == -1:
                    if items.find('0') > -1:
                        currentSettings['TESTING'] = 0
                    else:
                        currentSettings['TESTING'] = 1
                elif items.find('TCP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    tcpIN = items[items.find('"'):]
                    currentSettings['tcpIN'] = tcpIN.strip('"')
                elif items.find('TCP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    tcpOUT = items[items.find('"'):]
                    currentSettings['tcpOUT'] = tcpOUT.strip('"')
                elif items.find('UDP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    udpIN = items[items.find('"'):]
                    currentSettings['udpIN'] = udpIN.strip('"')
                elif items.find('UDP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    udpOUT = items[items.find('"'):]
                    currentSettings['udpOUT'] = udpOUT.strip('"')

            ### Check if rules are applied

            currentSettings['firewallStatus'] = 0

            command = 'sudo iptables -nv -L'
            output = subprocess.check_output(shlex.split(command))

            if output.find('0.0.0.0/0') > -1:
                currentSettings['firewallStatus'] = 1


            return currentSettings

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [fetchCSFSettings]")

    @staticmethod
    def changeStatus(controller, status):
        try:
            if controller == 'csf':
                if status == 'enable':
                    command = 'csf -s'
                    subprocess.call(shlex.split(command))
                    print '1,None'
                else:
                    command = 'csf -f'
                    subprocess.call(shlex.split(command))
                    print '1,None'

            elif controller == 'testingMode':
                data = open('/etc/csf/csf.conf', 'r').readlines()
                writeToFile = open('/etc/csf/csf.conf', 'w')

                for items in data:
                    if items.find('TESTING') > -1 and items.find('=') > -1 and (items[0] != '#') and items.find(
                            'TESTING_INTERVAL') == -1:
                        if status == 'enable':
                            writeToFile.writelines('TESTING = "1"\n')
                        else:
                            writeToFile.writelines('TESTING = "0"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
                print '1,None'

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[changeStatus]")
            print '0',str(msg)

    @staticmethod
    def modifyPorts(protocol, ports):
        try:
            data = open('/etc/csf/csf.conf', 'r').readlines()
            writeToFile = open('/etc/csf/csf.conf', 'w')

            if protocol == 'TCP_IN':
                for items in data:
                    if items.find('TCP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToFile.writelines('TCP_IN = "' + ports + '"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
            elif protocol == 'TCP_OUT':
                for items in data:
                    if items.find('TCP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToFile.writelines('TCP_OUT = "' + ports + '"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
            elif protocol == 'UDP_IN':
                for items in data:
                    if items.find('UDP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToFile.writelines('UDP_IN = "' + ports + '"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
            elif protocol == 'UDP_OUT':
                for items in data:
                    if items.find('UDP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToFile.writelines('UDP_OUT = "' + ports + '"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

            command = 'csf -r'
            subprocess.call(shlex.split(command))

            print '1,None'

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[modifyPorts]")
            print '0', str(msg)

    @staticmethod
    def allowIP(ipAddress):
        try:
            command = 'sudo csf -dr ' + ipAddress
            subprocess.call(shlex.split(command))

            command = 'sudo csf -a ' + ipAddress
            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[allowIP]")

    @staticmethod
    def blockIP(ipAddress):
        try:

            command = 'sudo csf -tr ' + ipAddress
            subprocess.call(shlex.split(command))

            command = 'sudo csf -d ' + ipAddress
            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[blockIP]")


def main():

    parser = argparse.ArgumentParser(description='CSF Manager')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--controller', help='Controller selection!')
    parser.add_argument('--status', help='Controller status!')
    parser.add_argument('--protocol', help='Protocol Modifications!')
    parser.add_argument('--ports', help='Ports!')

    args = parser.parse_args()

    if args.function == "installCSF":
       controller = CSF(args.function, {})
       controller.run()
    elif args.function == 'removeCSF':
        controller = CSF(args.function, {})
        controller.run()
    elif args.function == 'changeStatus':
        CSF.changeStatus(args.controller, args.status)
    elif args.function == 'modifyPorts':
        CSF.modifyPorts(args.protocol, args.ports)

if __name__ == "__main__":
    main()
