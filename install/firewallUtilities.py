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
                command = "firewall-cmd --add-service=ftp --permanent"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)


            command = 'firewall-cmd --add-port=' + port +'/' + proto +' --permanent'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'firewall-cmd --reload'

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
                command = "firewall-cmd --remove-service=ftp --permanent"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)


            command = 'firewall-cmd --remove-port=' + port + '/' + proto +' --permanent'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

            command = 'firewall-cmd --reload'

            cmd = shlex.split(command)

            res = subprocess.call(cmd)

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [deleteRule]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [deleteRule]")
            return 0

        return 1
