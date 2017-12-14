import subprocess

class InstallLog:
    fileName = "installLogs.txt"

    @staticmethod
    def writeToFile(message):
        file = open(InstallLog.fileName,'a')
        file.writelines(message + "\n")
        file.close()
