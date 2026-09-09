import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
from random import randint
from plogical.processUtilities import ProcessUtilities
from dns.models import Supermasters
from manageServices.models import SlaveServers
import argparse
from serverStatus.serverStatusUtil import ServerStatusUtil
from plogical import CyberCPLogFileWriter as logging
import subprocess

class ServiceManager:

    slaveConfPath = '/home/cyberpanel/slaveConf'

    def __init__(self, extraArgs):
        self.extraArgs = extraArgs

    def managePDNS(self):
        type = self.extraArgs['type']

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            path = '/etc/pdns/pdns.conf'
        else:
            path = '/etc/powerdns/pdns.conf'

        data = ProcessUtilities.outputExecutioner('sudo cat ' + path).splitlines()
        #data = subprocess.check_output(shlex.split('sudo cat ' + path)).decode("utf-8").splitlines()


        if type == 'MASTER':
            counter = 0

            ipsString = ''
            ipStringNoSubnet = ''

            for items in SlaveServers.objects.all():
                if items.slaveServerIP:
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
            writeToFile.writelines('primary=yes\n')
            writeToFile.close()

            command = 'sudo mv ' + tempPath + ' ' + path
            ProcessUtilities.executioner(command)
        else:
            import os

            if not os.path.exists(ServiceManager.slaveConfPath):

                writeToFile = open(ServiceManager.slaveConfPath, 'w')
                writeToFile.write('configured')
                writeToFile.close()

                counter = 0

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

                    counter = counter + 1

                    writeToFile.writelines(items  + '\n')

                slaveData = """
secondary=yes
daemon=yes
disable-axfr=yes
guardian=yes
local-address=0.0.0.0
local-port=53
primary=no
xfr-cycle-interval=60
setgid=pdns
setuid=pdns
autosecondary=yes
"""

                writeToFile.writelines(slaveData)
                writeToFile.close()

                command = 'sudo mv ' + tempPath + ' ' + path
                ProcessUtilities.executioner(command)

            for items in Supermasters.objects.all():
                items.delete()

            Supermasters(ip=self.extraArgs['masterServerIP'], nameserver=self.extraArgs['slaveServerNS'], account='').save()

    @staticmethod
    def InstallElasticSearch():

        statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            command = 'rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch'
            ServerStatusUtil.executioner(command, statusFile)

            repoPath = '/etc/yum.repos.d/elasticsearch.repo'

            content = '''
[elasticsearch]
name=Elasticsearch repository for 7.x packages
baseurl=https://artifacts.elastic.co/packages/7.x/yum
gpgcheck=1
gpgkey=https://artifacts.elastic.co/GPG-KEY-elasticsearch
enabled=0
autorefresh=1
type=rpm-md
'''

            writeToFile = open(repoPath, 'w')
            writeToFile.write(content)
            writeToFile.close()

            command = 'yum install --enablerepo=elasticsearch elasticsearch -y'
            ServerStatusUtil.executioner(command, statusFile)
        else:
            command = 'wget -qO - https://artifacts.elastic.co/GPG-KEY-elasticsearch | sudo apt-key add -'
            subprocess.call(command, shell=True)

            command = 'apt-get install apt-transport-https -y'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'echo "deb https://artifacts.elastic.co/packages/7.x/apt stable main" | sudo tee /etc/apt/sources.list.d/elastic-7.x.list'
            subprocess.call(command, shell=True)

            command = 'apt-get update -y'
            ServerStatusUtil.executioner(command, statusFile)

            command = 'apt-get install elasticsearch -y'
            ServerStatusUtil.executioner(command, statusFile)

        ### Tmp folder configurations

        command = 'mkdir -p /home/elasticsearch/tmp'
        ServerStatusUtil.executioner(command, statusFile)

        command = 'chown elasticsearch:elasticsearch /home/elasticsearch/tmp'
        ServerStatusUtil.executioner(command, statusFile)

        jvmOptions = '/etc/elasticsearch/jvm.options'

        writeToFile = open(jvmOptions, 'a')
        writeToFile.write('-Djava.io.tmpdir=/home/elasticsearch/tmp\n')
        writeToFile.close()

        command = 'systemctl enable elasticsearch'
        ServerStatusUtil.executioner(command, statusFile)

        command = 'systemctl start elasticsearch'
        ServerStatusUtil.executioner(command, statusFile)

        command = 'touch /home/cyberpanel/elasticsearch'
        ServerStatusUtil.executioner(command, statusFile)



        logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                      "Packages successfully installed.[200]\n", 1)
        return 0

    @staticmethod
    def RemoveElasticSearch():

        statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            command = 'rpm --import https://artifacts.elastic.co/GPG-KEY-elasticsearch'
            ServerStatusUtil.executioner(command, statusFile)

            repoPath = '/etc/yum.repos.d/elasticsearch.repo'

            try:
                os.remove(repoPath)
            except:
                pass

            command = 'yum erase elasticsearch -y'
            ServerStatusUtil.executioner(command, statusFile)
        else:

            try:
                os.remove('/etc/apt/sources.list.d/elastic-7.x.list')
            except:
                pass


            command = 'apt-get remove elasticsearch -y'
            ServerStatusUtil.executioner(command, statusFile)

        ### Tmp folder configurations

        command = 'rm -rf /home/elasticsearch/tmp'
        ServerStatusUtil.executioner(command, statusFile)


        command = 'rm -f /home/cyberpanel/elasticsearch'
        ServerStatusUtil.executioner(command, statusFile)

        logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                  "ElasticSearch successfully removed.[200]\n", 1)
        return 0

    @staticmethod
    def InstallRedis():

        statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            command = 'yum install redis -y'
            ServerStatusUtil.executioner(command, statusFile)
        else:

            command = 'DEBIAN_FRONTEND=noninteractive apt-get install redis-server -y'
            ServerStatusUtil.executioner(command, statusFile)


        command = 'systemctl enable redis'
        ServerStatusUtil.executioner(command, statusFile)

        command = 'systemctl start redis'
        ServerStatusUtil.executioner(command, statusFile)

        command = 'touch /home/cyberpanel/redis'
        ServerStatusUtil.executioner(command, statusFile)

        logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                  "Redis successfully installed.[200]\n", 1)
        return 0

    @staticmethod
    def RemoveRedis():

        statusFile = open(ServerStatusUtil.lswsInstallStatusPath, 'w')

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8:
            command = 'yum erase redis -y'
            ServerStatusUtil.executioner(command, statusFile)
        else:

            command = 'apt-get remove redis-server -y'
            ServerStatusUtil.executioner(command, statusFile)


        command = 'rm -f /home/cyberpanel/redis'
        ServerStatusUtil.executioner(command, statusFile)

        logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                  "Redis successfully removed.[200]\n", 1)
        return 0

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Application Manager')
    parser.add_argument('--function', help='Function')


    args = vars(parser.parse_args())

    if args["function"] == "InstallElasticSearch":
        ServiceManager.InstallElasticSearch()
    elif args["function"] == "RemoveElasticSearch":
        ServiceManager.RemoveElasticSearch()
    elif args["function"] == "InstallRedis":
        ServiceManager.InstallRedis()
    elif args["function"] == "RemoveRedis":
        ServiceManager.RemoveRedis()



if __name__ == "__main__":
    main()
