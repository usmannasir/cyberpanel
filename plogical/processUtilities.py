from CyberCPLogFileWriter import CyberCPLogFileWriter as logging
import subprocess
import shlex
import os
import socket
import threading as multi

class ProcessUtilities(multi.Thread):
    litespeedProcess = "litespeed"
    ent = 1
    OLS = 0
    centos = 1
    ubuntu = 0
    server_address = '/usr/local/lscpd/admin/comm.sock'
    token = "unset"

    def __init__(self, function, extraArgs):
        multi.Thread.__init__(self)
        self.function = function
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.function == 'popen':
                self.customPoen()
        except BaseException, msg:
            logging.writeToFile( str(msg) + ' [ApplicationInstaller.run]')

    @staticmethod
    def getLitespeedProcessNumber():
        finalListOfProcesses = []

        try:
            import psutil
            for proc in psutil.process_iter():
                if proc.name().find(ProcessUtilities.litespeedProcess) > -1:
                    finalListOfProcesses.append(proc.pid)

        except BaseException,msg:
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
                command = "sudo systemctl restart lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl restart"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError,msg:
            logging.writeToFile(str(msg) + "[restartLitespeed]")

    @staticmethod
    def stopLitespeed():
        try:
            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                command = "sudo systemctl stop lsws"
            else:
                command = "sudo /usr/local/lsws/bin/lswsctrl stop"

            cmd = shlex.split(command)
            res = subprocess.call(cmd)

            if res == 0:
                return 1
            else:
                return 0

        except subprocess.CalledProcessError, msg:
            logging.writeToFile(str(msg) + "[stopLitespeed]")

    @staticmethod
    def normalExecutioner(command):
        try:
            res = subprocess.call(shlex.split(command))
            if res == 0:
                return 1
            else:
                return 0
        except BaseException, msg:
            return 0

    @staticmethod
    def killLiteSpeed():
        try:
            command = 'sudo systemctl stop lsws'
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
        entPath = '/usr/local/lsws/bin/lshttpd'

        if os.path.exists('/usr/local/lsws/bin/openlitespeed'):
            return ProcessUtilities.OLS
        else:
            return ProcessUtilities.ent

    @staticmethod
    def decideDistro():
        distroPath = '/etc/lsb-release'

        if os.path.exists(distroPath):
            return ProcessUtilities.ubuntu
        else:
            return ProcessUtilities.centos

    @staticmethod
    def containerCheck():
        try:
            command = 'sudo cat /etc/cgrules.conf'
            result = subprocess.call(shlex.split(command))
            if result == 1:
                return 0
            else:
                return 1
        except BaseException:
            return 0

    @staticmethod
    def setupUDSConnection():
        try:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            sock.connect(ProcessUtilities.server_address)
            return [sock, "None"]
        except BaseException, msg:
            logging.writeToFile(str(msg) + ". [setupUDSConnection:138]")
            return [-1, str(msg)]

    @staticmethod
    def sendCommand(command):
        try:
            logging.writeToFile(command)

            ret = ProcessUtilities.setupUDSConnection()

            if ret[0] == -1:
                return ret[0]

            if ProcessUtilities.token == "unset":
                ProcessUtilities.token = os.environ.get('TOKEN')
                del os.environ['TOKEN']

            sock = ret[0]

            sock.sendall(ProcessUtilities.token + command)
            data = ""

            while (1):
                currentData = sock.recv(32)
                if len(currentData) == 0 or currentData == None:
                    break
                data = data + currentData

            sock.close()
            return data
        except BaseException, msg:
            logging.writeToFile(str(msg) + " [sendCommand]")
            return "0" + str(msg)

    @staticmethod
    def executioner(command):
        try:
            ret = ProcessUtilities.sendCommand(command)

            exitCode = ret[len(ret) -1]
            exitCode = int(exitCode.encode('hex'), 16)

            if exitCode == 0:
                #logging.writeToFile("Command: " + command + ", resturn code: " + str(exitCode) + ".")
                return 1
            else:
                #logging.writeToFile("Command: " + command + ", resturn code: " + str(exitCode) + ".")
                return 0

        except BaseException, msg:
            logging.writeToFile(str(msg) + " [executioner]")
            return 0

    @staticmethod
    def outputExecutioner(command):
        try:
            if type(command) == str or type(command) == unicode:
                pass
            else:
                command = " ".join(command)

            return ProcessUtilities.sendCommand(command)[:-1]
        except BaseException, msg:
            logging.writeToFile(str(msg) + "[outputExecutioner:188]")

    def customPoen(self):
        try:
            if type(self.extraArgs['command']) == str or type(self.extraArgs['command']) == unicode:
                command = self.extraArgs['command']
            else:
                command = " ".join(self.extraArgs['command'])

            ProcessUtilities.sendCommand(command)

            return 1
        except BaseException, msg:
            logging.writeToFile(str(msg) + " [customPoen]")

    @staticmethod
    def popenExecutioner(command):
        try:
            extraArgs = {}
            extraArgs['command'] = command
            pu = ProcessUtilities("popen", extraArgs)
            pu.start()
        except BaseException, msg:
            logging.writeToFile(str(msg) + " [popenExecutioner]")



