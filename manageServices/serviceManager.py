import os
import os.path
import sys
import django
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if repo_root not in sys.path:
    sys.path.append(repo_root)
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
from manageServices.application_detection import managed_apps_os_support
from manageServices import application_elasticsearch
from manageServices import application_redis
from manageServices import application_rabbitmq

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
prmary=no
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
    def InstallElasticSearch(version='latest', esMajor='8'):
        return application_elasticsearch.install(version=version, es_major=esMajor)

    @staticmethod
    def UpgradeElasticSearch(version='latest', esMajor='8'):
        return application_elasticsearch.upgrade(version=version, es_major=esMajor)

    @staticmethod
    def RemoveElasticSearch():
        return application_elasticsearch.remove()

    @staticmethod
    def InstallRedis(version='latest'):
        return application_redis.install(version=version)

    @staticmethod
    def UpgradeRedis(version='latest'):
        return application_redis.upgrade(version=version)

    @staticmethod
    def RemoveRedis():
        return application_redis.remove()

    @staticmethod
    def InstallRabbitMQ(version='latest', stream='3'):
        return application_rabbitmq.install(version=version, stream=stream)

    @staticmethod
    def UpgradeRabbitMQ(version='latest', stream='3'):
        return application_rabbitmq.upgrade(version=version, stream=stream)

    @staticmethod
    def RemoveRabbitMQ():
        return application_rabbitmq.remove()

def main():

    parser = argparse.ArgumentParser(description='CyberPanel Application Manager')
    parser.add_argument('--function', help='Function')
    parser.add_argument('--app', help='Application name')
    parser.add_argument('--action', help='Action to run: install|remove|upgrade')
    parser.add_argument('--version', default='latest', help='Target package version or latest')
    parser.add_argument('--esMajor', default='8', help='Elasticsearch major stream (7|8|9)')
    parser.add_argument('--rabbitmqStream', default='4', help='RabbitMQ major stream (3|4)')

    args = vars(parser.parse_args())

    support = managed_apps_os_support()
    if not support['supported']:
        logging.CyberCPLogFileWriter.statusWriter(
            ServerStatusUtil.lswsInstallStatusPath,
            support['reason'] + '\n',
            1
        )
        return

    if args["function"] == "InstallElasticSearch":
        ServiceManager.InstallElasticSearch(version=args.get('version', 'latest'), esMajor=args.get('esMajor', '8'))
    elif args["function"] == "UpgradeElasticSearch":
        ServiceManager.UpgradeElasticSearch(version=args.get('version', 'latest'), esMajor=args.get('esMajor', '8'))
    elif args["function"] == "RemoveElasticSearch":
        ServiceManager.RemoveElasticSearch()
    elif args["function"] == "InstallRedis":
        ServiceManager.InstallRedis(version=args.get('version', 'latest'))
    elif args["function"] == "UpgradeRedis":
        ServiceManager.UpgradeRedis(version=args.get('version', 'latest'))
    elif args["function"] == "RemoveRedis":
        ServiceManager.RemoveRedis()
    elif args["function"] == "InstallRabbitMQ":
        ServiceManager.InstallRabbitMQ(
            version=args.get('version', 'latest'),
            stream=args.get('rabbitmqStream', '4'),
        )
    elif args["function"] == "UpgradeRabbitMQ":
        ServiceManager.UpgradeRabbitMQ(
            version=args.get('version', 'latest'),
            stream=args.get('rabbitmqStream', '4'),
        )
    elif args["function"] == "RemoveRabbitMQ":
        ServiceManager.RemoveRabbitMQ()
    elif args.get("app") and args.get("action"):
        app_name = args.get("app")
        action = args.get("action").lower()
        version = args.get("version", "latest")
        es_major = args.get("esMajor", "8")
        rmq_stream = args.get("rabbitmqStream", "4")

        if app_name == 'Elasticsearch':
            if action == 'install':
                ServiceManager.InstallElasticSearch(version=version, esMajor=es_major)
            elif action == 'upgrade':
                ServiceManager.UpgradeElasticSearch(version=version, esMajor=es_major)
            elif action == 'remove':
                ServiceManager.RemoveElasticSearch()
        elif app_name == 'Redis':
            if action == 'install':
                ServiceManager.InstallRedis(version=version)
            elif action == 'upgrade':
                ServiceManager.UpgradeRedis(version=version)
            elif action == 'remove':
                ServiceManager.RemoveRedis()
        elif app_name == 'RabbitMQ':
            if action == 'install':
                ServiceManager.InstallRabbitMQ(version=version, stream=rmq_stream)
            elif action == 'upgrade':
                ServiceManager.UpgradeRabbitMQ(version=version, stream=rmq_stream)
            elif action == 'remove':
                ServiceManager.RemoveRabbitMQ()



if __name__ == "__main__":
    main()
