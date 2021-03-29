import json
import os.path
import sys
import argparse
import requests
from plogical.processUtilities import ProcessUtilities

sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")

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


def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('--function', help='Function to run.')
    parser.add_argument('--type', help='Type of detach.')

    args = parser.parse_args()

    uc = ClusterManager()

    if args.function == 'DetachCluster':
        uc.DetechFromCluster()


if __name__ == "__main__":
    main()