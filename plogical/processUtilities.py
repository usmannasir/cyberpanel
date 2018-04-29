from CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
import shlex
import platform

system=platform.dist()[0]
version=float(platform.dist()[1])

class ProcessUtilities:
    litespeedProcess = "litespeed"

    @staticmethod
    def getLitespeedProcessNumber():
        finalListOfProcesses = []

        try:
            import psutil
            for proc in psutil.process_iter():
                if proc.name() == ProcessUtilities.litespeedProcess:
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
            if version >= 7:
                command = "sudo systemctl restart lsws"
            elif version >= 6:
                command = "sudo service lsws restart"
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
            if version >= 7:
                command = "sudo systemctl stop lsws"
            elif version >= 6:
                command = "sudo service lsws stop"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError, msg:
            logging.writeToFile(str(msg) + "[stopLitespeed]")


