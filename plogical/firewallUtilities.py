#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import plogical.CyberCPLogFileWriter as logging
import argparse
from plogical.processUtilities import ProcessUtilities


class FirewallUtilities:

    @staticmethod
    def resFailed(res):
        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu and res != 0:
            return True
        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos and res == 1:
            return True
        return False

    @staticmethod
    def doCommand(command):
        try:
            res = ProcessUtilities.executioner(command)
            if res == 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error #" + str(res))
                return 0

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error: " + str(msg))
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error: " + str(msg), 1)
            return 0
        return 1


    @staticmethod
    def addRule(proto,port,ipAddress):
        ruleFamily = 'rule family="ipv4"'
        sourceAddress = 'source address="' + ipAddress + '"'
        ruleProtocol = 'port protocol="' + proto + '"'
        rulePort = 'port="' + port + '"'

        command = "firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        ruleFamily = 'rule family="ipv6"'
        sourceAddress = ''

        command = "firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        command = 'firewall-cmd --reload'

        ProcessUtilities.executioner(command)

        return 1

    @staticmethod
    def deleteRule(proto, port, ipAddress):
        ruleFamily = 'rule family="ipv4"'
        sourceAddress = 'source address="' + ipAddress + '"'
        ruleProtocol = 'port protocol="' + proto + '"'
        rulePort = 'port="' + port + '"'

        command = "firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        ruleFamily = 'rule family="ipv6"'
        sourceAddress = ''

        command = "firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        command = 'firewall-cmd --reload'

        ProcessUtilities.executioner(command)

        return 1

    @staticmethod
    def saveSSHConfigs(type, sshPort, rootLogin):
        try:
            if type == "1":

                command = 'semanage port -a -t ssh_port_t -p tcp ' + sshPort
                ProcessUtilities.normalExecutioner(command)

                FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")


                if rootLogin == "1":
                    rootLogin = "PermitRootLogin yes\n"
                else:
                    rootLogin = "PermitRootLogin no\n"

                sshPort = "Port " + sshPort + "\n"

                pathToSSH = "/etc/ssh/sshd_config"

                data = open(pathToSSH, 'r').readlines()

                writeToFile = open(pathToSSH, "w")

                for items in data:
                    if items.find("PermitRootLogin") > -1:
                        if items.find("Yes") > -1 or items.find("yes"):
                            writeToFile.writelines(rootLogin)
                            continue
                    elif items.find("Port") > -1:
                        writeToFile.writelines(sshPort)
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

                command = 'systemctl restart sshd'
                ProcessUtilities.normalExecutioner(command)

                print("1,None")

        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def addSSHKey(tempPath):
        try:
            key = open(tempPath, 'r').read()

            sshDir = "/root/.ssh"

            pathToSSH = "/root/.ssh/authorized_keys"

            if os.path.exists(sshDir):
                pass
            else:
                os.mkdir(sshDir)

            if os.path.exists(pathToSSH):
                pass
            else:
                sshFile = open(pathToSSH, 'w')
                sshFile.writelines("#Created by CyberPanel\n")
                sshFile.close()

            presenseCheck = 0
            try:
                data = open(pathToSSH, "r").readlines()
                for items in data:
                    if items.find(key) > -1:
                        presenseCheck = 1
            except:
                pass

            if presenseCheck == 0:
                writeToFile = open(pathToSSH, 'a')
                writeToFile.writelines("#Added by CyberPanel\n")
                writeToFile.writelines("\n")
                writeToFile.writelines(key)
                writeToFile.writelines("\n")
                writeToFile.close()

            if os.path.split(tempPath):
                os.remove(tempPath)

            print("1,None")

        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def deleteSSHKey(key):
        try:
            keyPart = key.split(" ")[1]
            pathToSSH = "/root/.ssh/authorized_keys"

            data = open(pathToSSH, 'r').readlines()

            writeToFile = open(pathToSSH, "w")

            for items in data:
                if items.find("ssh-rsa") > -1 and items.find(keyPart) > -1:
                    continue
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            print("1,None")

        except BaseException as msg:
            print("0," + str(msg))


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    ## Litespeed Tuning Arguments

    parser.add_argument("--tempPath", help="Temporary path to file where PHP is storing data!")

    parser.add_argument("--type", help="Type")
    parser.add_argument("--sshPort", help="SSH Port")
    parser.add_argument("--rootLogin", help="Root Login")
    parser.add_argument("--key", help="Key")


    args = parser.parse_args()

    if args.function == "saveSSHConfigs":
        FirewallUtilities.saveSSHConfigs(args.type, args.sshPort, args.rootLogin)
    elif args.function == "addSSHKey":
        FirewallUtilities.addSSHKey(args.tempPath)
    elif args.function == "deleteSSHKey":
        FirewallUtilities.deleteSSHKey(args.key)




if __name__ == "__main__":
    main()