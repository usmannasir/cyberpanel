import subprocess, shlex
from random import randint
from plogical.processUtilities import ProcessUtilities

class ServiceManager:

    def __init__(self, extraArgs):
        self.extraArgs = extraArgs


    def managePDNS(self):
        type = self.extraArgs['type']
        path = '/etc/pdns/pdns.conf'

        data = subprocess.check_output(shlex.split('sudo cat ' + path)).splitlines()

        if type == 'MASTER':
            counter = 0

            slaveIPData = self.extraArgs['slaveIPData']
            ipsString = slaveIPData.replace(',', '/32,')


            for items in data:
                if items.find('allow-axfr-ips') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('also-notify') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('daemon=') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('disable-axfr') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('slave') > -1:
                    data[counter] = '#' + data[counter]

                counter = counter + 1

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            writeToFile = open(tempPath, 'w')

            for items in data:
                writeToFile.writelines(items + '\n')

            writeToFile.writelines('allow-axfr-ips=' + ipsString + '\n')
            writeToFile.writelines('also-notify=' + slaveIPData + '\n')
            writeToFile.writelines('daemon=no\n')
            writeToFile.writelines('disable-axfr=no\n')
            writeToFile.writelines('master=yes\n')
            writeToFile.close()
        else:
            counter = 0

            for items in data:
                if items.find('allow-axfr-ips') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('also-notify') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('daemon=') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('disable-axfr') > -1:
                    data[counter] = '#' + data[counter]

                if items.find('slave') > -1:
                    data[counter] = '#' + data[counter]

                counter = counter + 1

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            writeToFile = open(tempPath, 'w')

            for items in data:
                writeToFile.writelines(items  + '\n')

            writeToFile.writelines('slave=yes\n')
            writeToFile.writelines('daemon=no\n')
            writeToFile.close()

        command = 'sudo mv ' + tempPath + ' ' + path
        ProcessUtilities.executioner(command)

