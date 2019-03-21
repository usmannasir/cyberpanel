import subprocess
import time
from plogical.processUtilities import ProcessUtilities
class cliLogger:
    fileName = "/home/cyberpanel/error-logs.txt"


    @staticmethod
    def writeforCLI(message, level, method):
        try:
            file = open(cliLogger.fileName, 'a')
            file.writelines("[" + time.strftime(
                "%I-%M-%S-%a-%b-%Y") + "] [" + level + ":" + method + "] " + message + "\n")
            file.close()
            file.close()
        except IOError:
            return "Can not write to error file!"

    @staticmethod
    def readLastNFiles(numberOfLines,fileName):
        try:

            lastFewLines = ProcessUtilities.outputExecutioner(["tail", "-n",str(numberOfLines),fileName])

            return lastFewLines

        except subprocess.CalledProcessError,msg:
            return "File was empty"
