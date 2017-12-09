import sys
import subprocess
import shutil
import installLog as logging
import argparse
import os
import shlex
import socket



class FirewallUtilities:

    @staticmethod
    def addRule(proto,port):
        try:
            if port == "21":
                command = "sudo firewall-cmd --add-service=ftp --permanent"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

            ipAddress = "0.0.0.0/0"

            ruleFamily = 'rule family="ipv4"'
            sourceAddress = 'source address="' + ipAddress + '"'
            ruleProtocol = 'port protocol="' + proto + '"'
            rulePort = 'port="' + port + '"'

            command = "sudo firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'sudo firewall-cmd --reload'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [addRule]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [addRule]")
            return 0

        return 1

    @staticmethod
    def deleteRule(proto, port):
        try:
            if port=="21":
                command = "sudo firewall-cmd --remove-service=ftp --permanent"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

            ipAddress = "0.0.0.0/0"

            ruleFamily = 'rule family="ipv4"'
            sourceAddress = 'source address="' + ipAddress + '"'
            ruleProtocol = 'port protocol="' + proto + '"'
            rulePort = 'port="' + port + '"'

            command = "sudo firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'sudo firewall-cmd --reload'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [deleteRule]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [deleteRule]")
            return 0

        return 1
