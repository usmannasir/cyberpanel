import sys
import subprocess
import shutil
import CyberCPLogFileWriter as logging
import argparse
import os
import shlex
import socket



class FirewallUtilities:

    @staticmethod
    def addRule(proto,port,ipAddress):
        try:
            if ipAddress != '':
                ruleFamily = 'rule family="ipv4"'
                sourceAddress = 'source address="' + ipAddress + '"'
                ruleProtocol = 'port protocol="' + proto + '"'
                rulePort = 'port="' + port + '"'

                command = "sudo firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"
            else:
                command = "sudo firewall-cmd --permanent --zone=public --add-port=" + port + '/' + proto

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'sudo firewall-cmd --reload'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addRule]")
            return 0
        except ValueError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [addRule]")
            return 0

        return 1

    @staticmethod
    def deleteRule(proto, port, ipAddress):
        try:
            if ipAddress != '':
                ruleFamily = 'rule family="ipv4"'
                sourceAddress = 'source address="' + ipAddress + '"'
                ruleProtocol = 'port protocol="' + proto + '"'
                rulePort = 'port="' + port + '"'

                command = "sudo firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"
            else:
                command = 'sudo firewall-cmd --permanent --zone-public --remove-port=' + port + '/' + proto

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'sudo firewall-cmd --reload'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [deleteRule]")
            return 0
        except ValueError, msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [deleteRule]")
            return 0

        return 1
