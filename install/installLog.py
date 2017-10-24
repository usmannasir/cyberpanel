import subprocess

class InstallLog:
    fileName = "installLogs.txt"

    @staticmethod
    def writeToFile(message):
        file = open(InstallLog.fileName,'a')
        file.writelines(message + "\n")
        file.close()

    @staticmethod
    def readLastNFiles(numberOfLines):
        try:

            lastFewLines = subprocess.check_output(["tail", "-n",str(numberOfLines),CyberCPLogFileWriter.fileName])

            return lastFewLines

        except subprocess.CalledProcessError,msg:
            CyberCPLogFileWriter.writeToFile(str(msg) + "[readLastNFiles]")
