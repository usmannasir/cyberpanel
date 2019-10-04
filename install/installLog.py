import time

class InstallLog:
    fileName = "/var/log/installLogs.txt"

    @staticmethod
    def writeToFile(message):
        file = open(InstallLog.fileName,'a')
        file.writelines("[" + time.strftime(
                    "%H-%M-%S-%b-%d-%Y") + "] "+message + "\n")
        file.close()
