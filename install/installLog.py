import json
import time

import requests

import install_events


class InstallLog:
    fileName = "/var/log/installLogs.txt"
    currentPercent = '10'
    LogURL = 'https://platform.cyberpersons.com/servers/RecvData'
    ServerIP = ''

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

        try:
            finalData = json.dumps({'ipAddress': InstallLog.ServerIP, "InstallCyberPanelStatus": message})
            requests.post(InstallLog.LogURL, data=finalData, timeout=10)
        except:
            pass

    @staticmethod
    def step(name, enabled=True):
        """Record that an installation step starts, or that it is left out."""
        install_events.step(name, enabled)

    @staticmethod
    def stepsFinished():
        """Record that the last installation step is done."""
        install_events.finish()
