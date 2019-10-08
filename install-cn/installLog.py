import time

class InstallLog:
    fileName = "/var/log/installLogs.txt"

    @staticmethod
    def writeToFile(message):
        file = open(InstallLog.fileName,'a')
        file.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "] "+message + "\n")
        file.close()
