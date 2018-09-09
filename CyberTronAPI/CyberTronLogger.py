import subprocess
import time

class CyberTronLogger:
    fileName = "/home/cyberpanel/error-logs.txt"
    operationsLogFile = "/home/cyberpanel/error-logs.txt"

    @staticmethod
    def writeToFile(message,level,method):
        try:
            file = open(CyberTronLogger.fileName,'a')
            file.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "] [" + level + ":" + method + "] " + message + "\n")
            file.close()
            file.close()
        except IOError:
            return "Can not write to error file!"

    @staticmethod
    def operationsLog(message,level,method):
        try:
            file = open(CyberTronLogger.operationsLogFile, 'a')
            file.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "] [" + level + ":"+ method + "] " + message + "\n")
            file.close()
        except IOError:
            return "Can not write to error file!"

    @staticmethod
    def readLastNFiles(numberOfLines,fileName):
        try:
            lastFewLines = subprocess.check_output(["tail", "-n",str(numberOfLines),fileName])
            return lastFewLines
        except subprocess.CalledProcessError:
            return "File was empty!"