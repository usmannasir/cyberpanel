import time

class InstallLog:
    fileName = "/var/log/installLogs.txt"

    currentPercent = '10'

    @staticmethod
    def writeToFile(message):

        if message.find(',') == -1:
            message = '%s,%s' % (message, InstallLog.currentPercent)
        elif message.find('mount -o') > -1 or message.find('usermod -G lscpd,') > -1:
            message = '%s,%s' % (message.replace(',', '-'), InstallLog.currentPercent)
        else:
            try:
                InstallLog.currentPercent = message.split(',')[1]
            except:
                pass

        file = open(InstallLog.fileName,'a')
        file.writelines("[" + time.strftime(
                    "%m.%d.%Y_%H-%M-%S") + "] " + message + "\n")
        file.close()
