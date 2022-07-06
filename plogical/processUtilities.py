from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
import shlex
import os
import socket
import threading as multi
import time
import getpass
import codecs

class ProcessUtilities(multi.Thread):
    debugPath = '/usr/local/CyberCP/debug'
    litespeedProcess = "litespeed"
    ent = 1
    OLS = 0
    centos = 1
    cent8 = 2
    ubuntu = 0
    ubuntu20 = 3
    server_address = '/usr/local/lscpd/admin/comm.sock'
    token = "unset"
    portPath = '/usr/local/lscp/conf/bind.conf'

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'popen':
                self.customPoen()
        except BaseException as msg:
            logging.writeToFile( str(msg) + ' [ApplicationInstaller.run]')

    @staticmethod
    def fetchCurrentPort():
        command = 'cat %s' % (ProcessUtilities.portPath)
        port = ProcessUtilities.outputExecutioner(command)

        if port.find('*') > -1:
            return port.split(':')[1].rstrip('\n')
        else:
            return '8090'

    @staticmethod
    def getLitespeedProcessNumber():
        finalListOfProcesses = []

        try:
            import psutil
            for proc in psutil.process_iter():
                if proc.name().find(ProcessUtilities.litespeedProcess) > -1:
                    finalListOfProcesses.append(proc.pid)

        except BaseException as msg:
            logging.writeToFile(
                str(msg) + " [getLitespeedProcessNumber]")
            return 0

        if len(finalListOfProcesses) > 0:
         return finalListOfProcesses
        else:
            return 0

    @staticmethod
    def restartLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "systemctl restart lsws"
            else:
                command = "/usr/local/lsws/bin/lswsctrl restart"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError as msg:
            logging.writeToFile(str(msg) + "[restartLitespeed]")

    @staticmethod
    def stopLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "systemctl stop lsws"
            else:
                command = "/usr/local/lsws/bin/lswsctrl stop"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError as msg:
            logging.writeToFile(str(msg) + "[stopLitespeed]")

    @staticmethod
    def normalExecutioner(command, shell=False, User=None):
        try:

            f = open(os.devnull, 'w')

            if User == None:
                if shell == False:
                    res = subprocess.call(shlex.split(command), stdout=f, stderr=f)
                else:
                    res = subprocess.call(command, shell=shell, stdout=f, stderr=f)
            else:
                if command.find('export') > -1:
                    pass
                elif command.find('sudo') == -1:
                    command = 'sudo -u %s %s' % (User, command)

                if shell == False:
                    res = subprocess.call(shlex.split(command), stdout=f, stderr=f)
                else:
                    res = subprocess.call(command, shell=shell, stdout=f, stderr=f)

            if os.path.exists(ProcessUtilities.debugPath):
                logging.writeToFile(command)

            if res == 0:
                return 1
            else:
                return 0
        except subprocess.CalledProcessError as msg:
            logging.writeToFile('%s. [ProcessUtilities.normalExecutioner]' % (str(msg)))
            return 0
        except BaseException as msg:
            logging.writeToFile('%s. [ProcessUtilities.normalExecutioner.Base]' % (str(msg)))
            return 0

    @staticmethod
    def killLiteSpeed():
        try:
            command = 'systemctl stop lsws'
            ProcessUtilities.normalExecutioner(command)
        except:
            pass

        pids = ProcessUtilities.getLitespeedProcessNumber()
        if pids !=0:
            for items in pids:
                try:
                    command = 'sudo kill -9 ' + str(items)
                    ProcessUtilities.normalExecutioner(command)
                except:
                    pass

    @staticmethod
    def decideServer():
        if os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            return ProcessUtilities.OLS
        else:
            return ProcessUtilities.ent

    @staticmethod
    def decideDistro():
        distroPath = '/etc/lsb-release'

        if os.path.exists(distroPath):
            if open(distroPath, 'r').read().find('20.04') > -1:
                return ProcessUtilities.ubuntu20
            return ProcessUtilities.ubuntu
        else:
            if open('/etc/redhat-release', 'r').read().find('CentOS Linux release 8') > -1 or open('/etc/redhat-release', 'r').read().find('AlmaLinux release 8') > -1 or open('/etc/redhat-release', 'r').read().find('Rocky Linux release 8') > -1:
                return ProcessUtilities.cent8
            return ProcessUtilities.centos


    @staticmethod
    def containerCheck():
        try:
            command = 'cat /etc/cgrules.conf'
            output = ProcessUtilities.outputExecutioner(command)
            if output.find('No such') > -1:
                return 0
            else:
                return 1
        except BaseException:
            return 0

    @staticmethod
    def setupUDSConnection():
        count = 0
        while 1:
            try:
                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(ProcessUtilities.server_address)
                return [sock, "None"]
            except BaseException as msg:
                if count == 3:
                    logging.writeToFile("Failed to connect to LSCPD socket, run 'systemctl restart lscpd' on command line to fix this issue.")
                    return [-1, str(msg)]
                else:
                    count = count + 1

                logging.writeToFile("Failed to connect to LSCPD UDS, error message:" + str(msg) + ". Attempt " + str(count) + ", we will attempt again in 2 seconds. [setupUDSConnection:138]")
                time.sleep(2)

    @staticmethod
    def sendCommand(command, user=None, dir=None):
        try:
            ret = ProcessUtilities.setupUDSConnection()

            if ret[0] == -1:
                return ret[0]

            if ProcessUtilities.token == "unset":
                ProcessUtilities.token = os.environ.get('TOKEN')
                del os.environ['TOKEN']

            sock = ret[0]

            if user == None:
                if command.find('export') > -1:
                    pass
                elif command.find('sudo') == -1:
                    command = 'sudo %s' % (command)

                if os.path.exists(ProcessUtilities.debugPath):
                    if command.find('cat') == -1:
                        logging.writeToFile(ProcessUtilities.token + command)

                if dir == None:
                    sock.sendall((ProcessUtilities.token + command).encode('utf-8'))
                else:
                    command = '%s-d %s %s' % (ProcessUtilities.token, dir, command)
                    sock.sendall(command.encode('utf-8'))
            else:
                if dir == None:
                    command = '%s-u %s %s' % (ProcessUtilities.token, user, command)
                else:
                    command = '%s-u %s -d %s %s' % (ProcessUtilities.token, user, dir, command)
                command = command.replace('sudo', '')


                if os.path.exists(ProcessUtilities.debugPath):
                    if command.find('cat') == -1:
                        logging.writeToFile(command)

                sock.sendall(command.encode('utf-8'))

            data = ""

            while (1):
                currentData = sock.recv(32)
                if len(currentData) == 0 or currentData == None:
                    break
                try:
                    data = data + currentData.decode(errors = 'ignore')
                except BaseException as msg:
                    logging.writeToFile('Some data could not be decoded to str, error message: %s' % str(msg))

            sock.close()
            #logging.writeToFile('Final data: %s.' % (str(data)))

            return data
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [hey:sendCommand]")
            return "0" + str(msg)

    @staticmethod
    def executioner(command, user=None, shell=False):
        try:
            if getpass.getuser() == 'root':
                ProcessUtilities.normalExecutioner(command, shell, user)
                return 1

            ret = ProcessUtilities.sendCommand(command, user)

            exitCode = ret[len(ret) -1]
            exitCode = int(codecs.encode(exitCode.encode(), 'hex'))

            if exitCode == 0:
                return 1
            else:
                return 0

        except BaseException as msg:
            logging.writeToFile(str(msg) + " [executioner]")
            return 0

    @staticmethod
    def outputExecutioner(command, user=None, shell = None, dir = None, retRequired = None):
        try:
            if getpass.getuser() == 'root':
                if os.path.exists(ProcessUtilities.debugPath):
                    logging.writeToFile(command)
                if shell == None or shell == True:
                    p = subprocess.Popen(command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                else:
                    p = subprocess.Popen(shlex.split(command),  stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

                if retRequired:
                    return 1, p.communicate()[0].decode("utf-8")
                else:
                    return p.communicate()[0].decode("utf-8")

            if type(command) == list:
                command = " ".join(command)

            if retRequired:
                ret = ProcessUtilities.sendCommand(command, user)

                exitCode = ret[len(ret) - 1]
                exitCode = int(codecs.encode(exitCode.encode(), 'hex'))

                if exitCode == 0:
                    return 1, ret[:-1]
                else:
                    return 0, ret[:-1]
            else:
                return ProcessUtilities.sendCommand(command, user, dir)[:-1]
        except BaseException as msg:
            logging.writeToFile(str(msg) + "[outputExecutioner:188]")

    def customPoen(self):
        try:

            if type(self.extraArgs['command']) == str or type(self.extraArgs['command']) == bytes:
                command = self.extraArgs['command']
            else:
                command = " ".join(self.extraArgs['command'])

            if getpass.getuser() == 'root':
                subprocess.call(command, shell=True)
            else:
                ProcessUtilities.sendCommand(command, self.extraArgs['user'])

            return 1
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [customPoen]")

    @staticmethod
    def popenExecutioner(command, user=None):
        try:
            extraArgs = {}
            extraArgs['command'] = command
            extraArgs['user'] = user
            pu = ProcessUtilities("popen", extraArgs)
            pu.start()
        except BaseException as msg:
            logging.writeToFile(str(msg) + " [popenExecutioner]")

    @staticmethod
    def BuildCommand(path, functionName, parameters):

        execPath = "/usr/local/CyberCP/bin/python %s %s " % (path, functionName)
        for key, value in parameters.items():
            execPath = execPath + ' --%s %s' % (key, value)

        return execPath



