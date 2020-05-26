import subprocess, shlex
from random import randint
from plogical.processUtilities import ProcessUtilities
from dns.models import Supermasters
from manageServices.models import SlaveServers

class ServiceManager:

    slaveConfPath = '/home/cyberpanel/slaveConf'

    def __init__(self, extraArgs):
        self.extraArgs = extraArgs

    def managePDNS(self):
        type = self.extraArgs['type']
        path = '/etc/pdns/pdns.conf'

        data = ProcessUtilities.outputExecutioner('sudo cat ' + path).splitlines()
        #data = subprocess.check_output(shlex.split('sudo cat ' + path)).decode("utf-8").splitlines()


        if type == 'MASTER':
            counter = 0

            ipsString = ''
            ipStringNoSubnet = ''

            for items in SlaveServers.objects.all():
                ipsString = ipsString + '%s/32, ' % (items.slaveServerIP)
                ipStringNoSubnet = ipStringNoSubnet + '%s, ' % (items.slaveServerIP)

            ipsString = ipsString.rstrip(', ')
            ipStringNoSubnet = ipStringNoSubnet.rstrip(', ')

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
            writeToFile = open(tempPath, 'w')

            for items in data:
                if items.find('allow-axfr-ips') > -1:
                    continue

                if items.find('also-notify') > -1:
                    continue

                if items.find('daemon=') > -1:
                    continue

                if items.find('disable-axfr') > -1:
                    continue

                if items.find('slave') > -1:
                    continue

                if items.find('master') > -1:
                    continue

                counter = counter + 1

                writeToFile.writelines(items + '\n')


            writeToFile.writelines('allow-axfr-ips=' + ipsString + '\n')
            writeToFile.writelines('also-notify=' + ipStringNoSubnet + '\n')
            writeToFile.writelines('daemon=no\n')
            writeToFile.writelines('disable-axfr=no\n')
            writeToFile.writelines('master=yes\n')
            writeToFile.close()
        else:
            import os

            if not os.path.exists(ServiceManager.slaveConfPath):

                writeToFile = open(ServiceManager.slaveConfPath, 'w')
                writeToFile.write('configured')
                writeToFile.close()

                counter = 0

                for items in data:
                    if items.find('allow-axfr-ips') > -1:
                        continue

                    if items.find('also-notify') > -1:
                        continue

                    if items.find('daemon=') > -1:
                        continue

                    if items.find('disable-axfr') > -1:
                        continue

                    if items.find('slave') > -1:
                        continue

                    counter = counter + 1

                tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))
                writeToFile = open(tempPath, 'w')

                for items in data:
                    writeToFile.writelines(items  + '\n')

                slaveData = """
slave=yes
daemon=yes
disable-axfr=yes
guardian=yes
local-address=0.0.0.0
local-port=53
master=no
slave-cycle-interval=60
setgid=pdns
setuid=pdns
superslave=yes        
"""

                writeToFile.writelines(slaveData)
                writeToFile.close()

                command = 'sudo mv ' + tempPath + ' ' + path
                ProcessUtilities.executioner(command)

            for items in Supermasters.objects.all():
                items.delete()

            Supermasters(ip=self.extraArgs['masterServerIP'], nameserver=self.extraArgs['slaveServerNS'], account='').save()

