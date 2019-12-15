#!/usr/local/CyberCP/bin/python
import os.path
import sys
import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import subprocess, shlex
from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
from plogical.httpProc import httpProc
from plogical.processUtilities import ProcessUtilities
from plogical.acl import ACLManager
import threading as multi
import argparse
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules


class HAManager(multi.Thread):

    def __init__(self, request = None, data = None, function = None):
        multi.Thread.__init__(self)
        self.request = request
        self.data = data
        self.function = function

    def run(self):
        try:
            if self.function == 'setupNode':
                self.setupNode()
            elif self.function == 'addManager':
                self.setupNode()
        except BaseException as msg:
            logging.writeToFile( str(msg) + ' [HAManager.run]')

    def setupNode(self):
        try:

            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                mesg = 'Clusters are only supported on Ubuntu 18.04. [404]'
                logging.statusWriter(self.data['tempStatusPath'], mesg)
                return 0

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                mesg = 'Only administrators can create clusters. [404]'
                logging.statusWriter(self.data['tempStatusPath'], mesg)
                return 0

            logging.statusWriter(self.data['tempStatusPath'], 'Setting up node in progress..')

            commands = self.data['commands']

            for command in commands:
                try:
                    result = subprocess.call(command, shell=True)
                    if result != 0:
                        logging.writeToFile(command +  ' Failed.')
                except BaseException:
                    logging.statusWriter(self.data['tempStatusPath'], command +  ' Failed. [404]')
                    return 0

            try:
                FirewallUtilities.addRule('tcp', '2377', "0.0.0.0/0")
                fwRule = FirewallRules(name="Docker", port='2377', proto="tcp")
                fwRule.save()
            except:
                pass

            mesg = 'Node successfully configured. [200]'
            logging.statusWriter(self.data['tempStatusPath'], mesg)

        except BaseException as msg:
            logging.writeToFile(str(msg))
            logging.statusWriter(self.data['tempStatusPath'], str(msg) + '. [404]')

    def fetchManagerTokens(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can create clusters.')

            ipFile = "/etc/cyberpanel/machineIP"
            f = open(ipFile)
            ipData = f.read()
            ipAddress = ipData.split('\n', 1)[0]

            command = 'sudo docker swarm init --advertise-addr ' + ipAddress
            ProcessUtilities.executioner(command)

            managerToken = ''
            workerToken = ''

            command = "sudo docker swarm join-token manager"
            output = subprocess.check_output(shlex.split(command)).decode("utf-8").splitlines()

            for items in output:
                if items.find('--token') > -1:
                    managerToken = items.split(' ')[-2]

            command = "sudo docker swarm join-token worker"
            output = subprocess.check_output(shlex.split(command)).decode("utf-8").splitlines()

            for items in output:
                if items.find('--token') > -1:
                    workerToken = items.split(' ')[-2]

            data = {}
            data['managerToken'] = managerToken
            data['workerToken'] = workerToken

            return proc.ajax(1, None, data)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, None, str(msg))

    def addWorker(self):
        try:

            proc = httpProc(self.request, None, None)

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can create clusters.')

            token = self.data['token']
            ipAddress = self.data['ipAddress']
            command = 'sudo docker swarm join --token ' + token + ' ' + ipAddress + ':2377'

            if ProcessUtilities.executioner(command) == 0:
                return proc.ajax(0, 'Failed to join as worker.')

            return proc.ajax(1, None)

        except BaseException as msg:
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, None, str(msg))

    def leaveSwarm(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            proc = httpProc(self.request, None, None)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can create clusters.')

            commands = self.data['commands']

            for command in commands:
                try:
                    result = subprocess.call(command, shell=True)
                    if result != 0:
                        logging.writeToFile(command +  ' Failed.')
                except BaseException as msg:
                    logging.writeToFile(command + 'Failed.')
                    return 0

        except BaseException as msg:
            logging.writeToFile(str(msg))

    def setUpDataNode(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            proc = httpProc(self.request, None, None)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can create clusters.')

            composePath = '/home/cyberpanel/composePath'

            if not os.path.exists(composePath):
                os.mkdir(composePath)

            composeFile = composePath + '/docker-compose.yml'

            compose = open(composeFile, 'w')
            for items in self.data['composeData']:
                compose.writelines(items)
            compose.close()

            return proc.ajax(1, None)

        except BaseException as msg:
            logging.writeToFile(str(msg))
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

    def submitEditCluster(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)
            proc = httpProc(self.request, None, None)

            if currentACL['admin'] == 0:
                return proc.ajax(0, 'Only administrators can create clusters.')

            composePath = '/home/cyberpanel/composePath'
            composeFile = composePath + '/docker-compose.yml'

            data = open(composeFile, 'r').readlines()
            compose = open(composeFile, 'w')
            for items in data:
                if items.find('replicas') > -1:
                    compose.writelines('      replicas: ' + str(self.data['containers']) + '\n')
                elif items.find('memory') > -1:
                    compose.writelines('          memory: ' + self.data['containerRam'] + '\n')
                elif items.find('cpus:') > -1:
                    compose.writelines('          cpus: "' + self.data['containerCPU'] + '"\n')
                else:
                    compose.writelines(items)
            compose.close()

            return proc.ajax(1, None)

        except BaseException as msg:
            logging.writeToFile(str(msg))
            proc = httpProc(self.request, None, None)
            return proc.ajax(0, str(msg))

def main():

    parser = argparse.ArgumentParser(description='CyberPanel HA Manager')
    parser.add_argument('function', help='Specific a function to call!')
    parser.add_argument('--id', help='ID!')
    parser.add_argument('--ipAddress', help='IP Address!')

    args = parser.parse_args()

if __name__ == "__main__":
    main()
