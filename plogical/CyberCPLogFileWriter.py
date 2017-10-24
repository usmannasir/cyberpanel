import subprocess
import time

class CyberCPLogFileWriter:
    fileName = "error-logs.txt"

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
    def readLastNFiles(numberOfLines,fileName):
        try:

            lastFewLines = subprocess.check_output(["tail", "-n",str(numberOfLines),fileName])

            return lastFewLines

        except subprocess.CalledProcessError,msg:
            return "File was empty"
