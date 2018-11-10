import subprocess
import time


class CyberCPLogFileWriter:
    fileName = "/home/cyberpanel/error-logs.txt"

    @staticmethod
    def writeToFile(message):
        try:
            file = open(CyberCPLogFileWriter.fileName,'a')
            file.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "] "+ message + "\n")
            file.close()

        except IOError,msg:
            return "Can not write to error file."

    @staticmethod
    def writeforCLI(message, level, method):
        try:
            file = open(CyberCPLogFileWriter.fileName, 'a')
            file.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "] [" + level + ":" + method + "] " + message + "\n")
            file.close()
            file.close()
        except IOError:
            return "Can not write to error file!"

    @staticmethod
    def readLastNFiles(numberOfLines,fileName):
        try:

            lastFewLines = subprocess.check_output(["tail", "-n",str(numberOfLines),fileName])

            return lastFewLines

        except subprocess.CalledProcessError,msg:
            return "File was empty"

    @staticmethod
    def statusWriter(tempStatusPath, mesg, append = None):
        try:
            if append == None:
                statusFile = open(tempStatusPath, 'w')
            else:
                statusFile = open(tempStatusPath, 'a')
            statusFile.writelines(mesg)
            statusFile.close()
        except BaseException, msg:
            CyberCPLogFileWriter.writeToFile(str(msg) + ' [statusWriter]')

