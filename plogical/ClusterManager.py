import json
import os.path
import sys
import argparse
import requests
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
from plogical.processUtilities import ProcessUtilities

class ClusterManager:

    LogURL = "http://cloud.cyberpanel.net:8000/HighAvailability/RecvData"
    ClusterFile = '/home/cyberpanel/cluster'

    def __init__(self):
        ##
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        self.ipAddress = ipData.split('\n', 1)[0]
        ##
        self.config = json.loads(open(ClusterManager.ClusterFile, 'r').read())

    def PostStatus(self):
        import os
        if os.path.exists(ProcessUtilities.debugPath):
            from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
            logging.writeToFile(str(self.config))
        finalData = json.dumps(self.config)
        resp = requests.post(ClusterManager.LogURL, data=finalData, verify=False)
        print (resp.text)

    def FetchMySQLConfigFile(self):

        if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
            return '/etc/mysql/conf.d/cluster.cnf'
        else:
            return '/etc/mysql/conf.d/cluster.cnf'

    def DetechFromCluster(self, type):
        try:

            command = 'rm -rf %s' % (self.FetchMySQLConfigFile())
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl stop mysql'
            ProcessUtilities.normalExecutioner(command)

            command = 'systemctl restart mysql'
            ProcessUtilities.executioner(command)

            if type == 'Child':
                self.config['failoverServerMessage'] = 'Successfully detached. [200]'
                self.PostStatus()
            else:
                self.config['masterServerMessage'] = 'Successfully detached. [200]'
                self.PostStatus()

        except BaseException as msg:
            if type == 'Child':
                self.config['failoverServerMessage'] = 'Failed to detach, error %s [404].' % (str(msg))
                self.PostStatus()
            else:
                self.config['masterServerMessage'] = 'Failed to detach, error %s [404].' % (str(msg))
                self.PostStatus()

    def SetupCluster(self, type):
        try:

            ClusterPath = self.FetchMySQLConfigFile()
            ClusterConfigPath = '/home/cyberpanel/cluster'
            config = json.loads(open(ClusterConfigPath, 'r').read())

            command = 'systemctl stop mysql'
            ProcessUtilities.normalExecutioner(command)

            command = 'rm -rf %s' % (ClusterConfigPath)
            ProcessUtilities.executioner(command)

            if type == 'Child':

                writeToFile = open(ClusterPath, 'w')
                writeToFile.write(config['ClusterConfigFailover'])
                writeToFile.close()

                command = 'systemctl start mysql'
                ProcessUtilities.normalExecutioner(command)

                self.config['failoverServerMessage'] = 'Successfully attached to cluster. [200]'
                self.PostStatus()

            else:
                writeToFile = open(ClusterPath, 'w')
                writeToFile.write(config['ClusterConfigMaster'])
                writeToFile.close()

                command = 'galera_new_cluster'
                ProcessUtilities.normalExecutioner(command)

                self.config['masterServerMessage'] = 'Successfully attached to cluster. [200]'
                self.PostStatus()

            ###

            command = 'rm -rf %s' % (ClusterConfigPath)
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            if type == 'Child':
                self.config['failoverServerMessage'] = 'Failed to attach, error %s [404].' % (str(msg))
                self.PostStatus()
            else:
                self.config['masterServerMessage'] = 'Failed to attach, error %s [404].' % (str(msg))
                self.PostStatus()


def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('--function', help='Function to run.')
    parser.add_argument('--type', help='Type of detach.')

    args = parser.parse_args()

    uc = ClusterManager()

    if args.function == 'DetachCluster':
        uc.DetechFromCluster(args.type)
    elif args.function == 'SetupCluster':
        uc.SetupCluster(args.type)


if __name__ == "__main__":
    main()