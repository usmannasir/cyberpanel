import json
import os.path
import sys
import argparse
import requests
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
from plogical.processUtilities import ProcessUtilities
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging

class ClusterManager:

    LogURL = "http://de-a.cyberhosting.org:8000/HighAvailability/RecvData"
    ClusterFile = '/home/cyberpanel/cluster'

    def __init__(self, type):
        ##
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        self.ipAddress = ipData.split('\n', 1)[0]
        ##
        self.config = json.loads(open(ClusterManager.ClusterFile, 'r').read())
        self.type = type

    def PostStatus(self, message):
        try:
            finalData = {'name': self.config['name'], 'type': self.type, 'message': message, 'token': self.config['token']}
            resp = requests.post(ClusterManager.LogURL, data=json.dumps(finalData), verify=False)
            logging.writeToFile(resp.text + '[info]')
        except BaseException as msg:
            logging.writeToFile('%s. [31:404]' % (str(msg)))

    def FetchMySQLConfigFile(self):

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
            return '/etc/mysql/conf.d/cluster.cnf'
        else:
            return '/etc/mysql/conf.d/cluster.cnf'

    def DetechFromCluster(self):
        try:

            command = 'rm -rf %s' % (self.FetchMySQLConfigFile())
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl stop mysql'
            #ProcessUtilities.normalExecutioner(command)

            command = 'systemctl restart mysql'
            #ProcessUtilities.executioner(command)

            self.PostStatus('Successfully detached. [200]')

        except BaseException as msg:
            self.PostStatus('Failed to detach, error %s [404].' % (str(msg)))

    def SetupCluster(self):
        try:

            ClusterPath = self.FetchMySQLConfigFile()
            ClusterConfigPath = '/home/cyberpanel/cluster'
            config = json.loads(open(ClusterConfigPath, 'r').read())

            if self.type == 'Child':
                writeToFile = open(ClusterPath, 'w')
                writeToFile.write(config['ClusterConfigFailover'])
                writeToFile.close()
            else:
                writeToFile = open(ClusterPath, 'w')
                writeToFile.write(config['ClusterConfigMaster'])
                writeToFile.close()

            self.PostStatus('Successfully attached to cluster. [200]')

            ###

        except BaseException as msg:
            self.PostStatus('Failed to attach, error %s [404].' % (str(msg)))

    def BootMaster(self):
        try:

            command = 'systemctl stop mysql'
            ProcessUtilities.normalExecutioner(command)

            command = 'galera_new_cluster'
            ProcessUtilities.normalExecutioner(command)

            self.PostStatus('Master server successfully booted. [200]')

            ###

        except BaseException as msg:
            self.PostStatus('Failed to boot, error %s [404].' % (str(msg)))

    def BootChild(self):
        try:

            ChildData = '/home/cyberpanel/childaata'
            data = json.loads(open(ChildData, 'r').read())

            ## CyberPanel DB Creds

            ## Update settings file using the data fetched from master


            dbName = data['dbName']
            dbUser = data['dbUser']
            password = data['password']
            host = data['host']
            port = data['port']

            ## Root DB Creds

            rootdbName = data['rootdbName']
            rootdbdbUser = data['rootdbdbUser']
            rootdbpassword = data['rootdbpassword']

            completDBString = """\nDATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '%s',
        'USER': '%s',
        'PASSWORD': '%s',
        'HOST': '%s',
        'PORT':'%s'
    },
    'rootdb': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': '%s',
        'USER': '%s',
        'PASSWORD': '%s',
        'HOST': '%s',
        'PORT': '%s',
    },
}\n""" % (dbName, dbUser, password, host, port, rootdbName, rootdbdbUser, rootdbpassword, host, port)

            settingsFile = '/usr/local/CyberCP/CyberCP/settings.py'

            settingsData = open(settingsFile, 'r').readlines()

            DATABASESCHECK = 0
            writeToFile = open(settingsFile, 'w')

            for items in settingsData:
                if items.find('DATABASES = {') > -1:
                    DATABASESCHECK = 1

                if DATABASESCHECK == 0:
                    writeToFile.write(items)

                if items.find('DATABASE_ROUTERS = [') > -1:
                    DATABASESCHECK = 0
                    writeToFile.write(completDBString)
                    writeToFile.write(items)

            writeToFile.close()



            ## new settings file restored

            command = 'systemctl stop mysql'
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl start mysql'
            ProcessUtilities.normalExecutioner(command)

            ## Restart lscpd

            command = 'systemctl restart lscpd'
            ProcessUtilities.normalExecutioner(command)

            self.PostStatus('Fail over server successfully booted. [200]')

            ###

        except BaseException as msg:
            self.PostStatus('Failed to boot, error %s [404].' % (str(msg)))


def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('--function', help='Function to run.')
    parser.add_argument('--type', help='Type of detach.')

    args = parser.parse_args()

    uc = ClusterManager(args.type)

    if args.function == 'DetachCluster':
        uc.DetechFromCluster()
    elif args.function == 'SetupCluster':
        uc.SetupCluster()
    elif args.function == 'BootMaster':
        uc.BootMaster()
    elif args.function == 'BootChild':
        uc.BootChild()


if __name__ == "__main__":
    main()