from CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
import shlex
import os

class ProcessUtilities:
    litespeedProcess = "litespeed"
    ent = 1
    OLS = 0
    centos = 1
    ubuntu = 0

    @staticmethod
    def getLitespeedProcessNumber():
        finalListOfProcesses = []

        try:
            import psutil
            for proc in psutil.process_iter():
                if proc.name().find(ProcessUtilities.litespeedProcess) > -1:
                    finalListOfProcesses.append(proc.pid)

        except BaseException,msg:
            logging.writeToFile(
                str(msg) + " [getLitespeedProcessNumber]")
            return 0

        if len(finalListOfProcesses) > 0:
         return finalListOfProcesses
        else:
            return 0

    @staticmethod
    def restartLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl restart lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError,msg:
            logging.writeToFile(str(msg) + "[restartLitespeed]")

    @staticmethod
    def stopLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl stop lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl stop"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError, msg:
            logging.writeToFile(str(msg) + "[stopLitespeed]")

    @staticmethod
    def executioner(command):
        try:
            res = subprocess.call(shlex.split(command))
            if res == 0:
                return 1
            else:
                return 0
        except BaseException, msg:
            return 0

    @staticmethod
    def killLiteSpeed():
        try:
            command = 'sudo systemctl stop lsws'
            ProcessUtilities.executioner(command)
        except:
            pass

        pids = ProcessUtilities.getLitespeedProcessNumber()
        if pids !=0:
            for items in pids:
                try:
                    command = 'sudo kill -9 ' + str(items)
                    ProcessUtilities.executioner(command)
                except:
                    pass

    @staticmethod
    def decideServer():
        entPath = '/usr/local/lsws/bin/lshttpd'

        if os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            return ProcessUtilities.OLS
        else:
            return ProcessUtilities.ent

    @staticmethod
    def decideDistro():
        distroPath = '/etc/lsb-release'

        if os.path.exists(distroPath):
            return ProcessUtilities.ubuntu
        else:
            return ProcessUtilities.centos



