import time

class InstallLog:
    fileName = "/var/log/installLogs.txt"

    @staticmethod
    def writeToFile(message):
        file = open(InstallLog.fileName,'a')
        file.writelines("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "] "+message + "\n")
        file.close()
