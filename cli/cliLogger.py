import subprocess
import time

class cliLogger:
    fileName = "/home/cyberpanel/error-logs.txt"


    @staticmethod
    def writeforCLI(message, level, method):
        try:
            file = open(cliLogger.fileName, 'a')
            file.writelines("[" + time.strftime(
                "%m.%d.%Y_%H-%M-%S") + "] [" + level + ":" + method + "] " + message + "\n")
            file.close()
            file.close()
        except IOError:
            return "Can not write to error file!"

    @staticmethod
    def readLastNFiles(numberOfLines,fileName):
        try:

            lastFewLines = subprocess.check_output(["tail", "-n",str(numberOfLines),fileName]).decode("utf-8")

            return lastFewLines

        except subprocess.CalledProcessError as msg:
            return "File was empty"
