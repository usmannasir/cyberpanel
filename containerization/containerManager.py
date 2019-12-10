from django.shortcuts import render
from plogical.processUtilities import ProcessUtilities
import threading as multi
from plogical.acl import ACLManager
import plogical.CyberCPLogFileWriter as logging
from serverStatus.serverStatusUtil import ServerStatusUtil
import os, stat


class ContainerManager(multi.Thread):
    defaultConf = """group {groupName}{
        cpu {
                cpu.cfs_quota_us = {cfs_quota_us};
                cpu.cfs_period_us = {cfs_period_us};
        }
        memory {
                memory.limit_in_bytes = {memory}m;
        }
        blkio {
                blkio.throttle.read_bps_device = "{major}:{minor}         {io}";
                blkio.throttle.write_bps_device = "{major}:{minor}         {io}";
                blkio.throttle.read_iops_device = "{major}:{minor}         {iops}";
                blkio.throttle.write_iops_device = "{major}:{minor}         {iops}";
        }
        net_cls
             {
               net_cls.classid = 0x10{net_cls};
        }
}"""

    def __init__(self, request=None, templateName=None, function=None, data=None):
        multi.Thread.__init__(self)
        self.request = request
        self.templateName = templateName
        self.function = function
        self.data = data

    def run(self):
        try:
            if self.function == 'submitContainerInstall':
                self.submitContainerInstall()
            elif self.function == 'addTrafficController':
                self.addTrafficController()
            elif self.function == 'removeLimits':
                self.removeLimits()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [ContainerManager.run]')

    @staticmethod
    def fetchHexValue(count):
        hexValue = format(count, '02x')

        if len(hexValue) == 1:
            return '000' + hexValue
        elif len(hexValue) == 2:
            return '00' + hexValue
        elif len(hexValue) == 3:
            return '0' + hexValue
        elif len(hexValue) == 3:
            return hexValue

    @staticmethod
    def prepConf(groupName, cfs_quota_us, cfs_period_us, memory, io, iops, net_cls):
        try:
            dev = os.stat('/')[stat.ST_DEV]
            major = str(os.major(dev))
            minor = str(0)
            finalIO = str(int(io) * 1024 * 1024)

            ioConf = ContainerManager.defaultConf.replace('{groupName}', groupName)
            ioConf = ioConf.replace('{cfs_quota_us}', cfs_quota_us)
            ioConf = ioConf.replace('{cfs_period_us}', cfs_period_us)
            ioConf = ioConf.replace('{memory}', memory)
            ioConf = ioConf.replace('{major}', major)
            ioConf = ioConf.replace('{minor}', minor)
            ioConf = ioConf.replace('{io}', finalIO)
            ioConf = ioConf.replace('{iops}', str(iops))
            ioConf = ioConf.replace('{net_cls}', str(net_cls))

            return ioConf
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg))
            return 0

    def renderC(self):

        userID = self.request.session['userID']
        currentACL = ACLManager.loadedACL(userID)

        if currentACL['admin'] == 1:
            pass
        else:
            return ACLManager.loadError()

        data = {}
        data['OLS'] = 0
        data['notInstalled'] = 0

        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            data['OLS'] = 1
            data['notInstalled'] = 0
            return render(self.request, 'containerization/notAvailable.html', data)
        elif not ProcessUtilities.containerCheck():
            data['OLS'] = 0
            data['notInstalled'] = 1
            return render(self.request, 'containerization/notAvailable.html', data)
        else:
            if self.data == None:
                self.data = {}
            self.data['OLS'] = 0
            self.data['notInstalled'] = 0
            return render(self.request, self.templateName, self.data)

    def submitContainerInstall(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath,
                                                          'Not authorized to install container packages. [404].',
                                                          1)
                return 0

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/containerization/container.py"
            execPath = execPath + " --function submitContainerInstall"
            ProcessUtilities.outputExecutioner(execPath)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def restartServices(self):
        command = 'sudo systemctl restart cgconfig'
        ProcessUtilities.executioner(command)

        command = 'sudo systemctl restart cgred'
        ProcessUtilities.executioner(command)

    def addTrafficController(self):
        command = 'sudo tc qdisc add dev eth0 root handle 10: htb default 1000'
        #logging.CyberCPLogFileWriter.writeToFile(command)
        ProcessUtilities.executioner(command)

        try:
            command = 'sudo tc class del dev eth0 classid 10:' + str(self.data['classID'])
            # logging.CyberCPLogFileWriter.writeToFile(command)
            ProcessUtilities.executioner(command)
        except:
            pass

        command = 'sudo tc class add dev eth0 parent 10: classid 10:1000 htb rate 100mbit'
        #logging.CyberCPLogFileWriter.writeToFile(command)
        ProcessUtilities.executioner(command)

        command = 'sudo tc class add dev eth0 parent 10: classid 10:' + str(self.data['classID']) + ' htb rate ' + str(self.data['rateLimit'])
        #logging.CyberCPLogFileWriter.writeToFile(command)
        ProcessUtilities.executioner(command)

        #if str(self.data['classID']) == '1':
        #    command = 'sudo tc filter add dev eth0 parent 10: protocol ip prio 10 handle 1: cgroup'
        #else:
        #    command = 'sudo tc filter add dev eth0 parent 10:' + str(
        #        self.data['classID']) + ' protocol ip prio 10 handle 1: cgroup'

        command = 'sudo tc filter add dev eth0 parent 10: protocol ip prio 10 handle 1: cgroup'
        #logging.CyberCPLogFileWriter.writeToFile(command)
        ProcessUtilities.executioner(command)

        self.restartServices()

    def removeLimits(self):
        command = 'sudo tc class del dev eth0 classid 10:' + str(self.data['classID'])
        #logging.CyberCPLogFileWriter.writeToFile(command)
        ProcessUtilities.executioner(command)

        self.restartServices()

