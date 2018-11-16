import subprocess
import CyberCPLogFileWriter as logging
import shlex
from processUtilities import ProcessUtilities



class FirewallUtilities:

    @staticmethod
    def resFailed(res):
        if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu and res != 0:
            return True
        elif ProcessUtilities.decideDistro() == ProcessUtilities.centos and res == 1:
            return True
        return False

    @staticmethod
    def doCommand(command):
        try:
            cmd = shlex.split(command)
            res = subprocess.call(cmd)
            if FirewallUtilities.resFailed(res):
                logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error #" + str(res))
                return 0

        except OSError, msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error: " + str(msg))
            return 0
        except ValueError, msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error: " + str(msg), 1)
            return 0
        return 1



    @staticmethod
    def addRule(proto,port,ipAddress):
        ruleFamily = 'rule family="ipv4"'
        sourceAddress = 'source address="' + ipAddress + '"'
        ruleProtocol = 'port protocol="' + proto + '"'
        rulePort = 'port="' + port + '"'

        command = "sudo firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        if not FirewallUtilities.doCommand(command):
            return 0

        ruleFamily = 'rule family="ipv6"'
        sourceAddress = ''

        command = "sudo firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        if not FirewallUtilities.doCommand(command):
            return 0

        command = 'sudo firewall-cmd --reload'

        if not FirewallUtilities.doCommand(command):
            return 0

        return 1

    @staticmethod
    def deleteRule(proto, port, ipAddress):
        ruleFamily = 'rule family="ipv4"'
        sourceAddress = 'source address="' + ipAddress + '"'
        ruleProtocol = 'port protocol="' + proto + '"'
        rulePort = 'port="' + port + '"'

        command = "sudo firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        if not FirewallUtilities.doCommand(command):
            return 0

        ruleFamily = 'rule family="ipv6"'
        sourceAddress = ''

        command = "sudo firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        if not FirewallUtilities.doCommand(command):
            return 0

        command = 'sudo firewall-cmd --reload'

        if not FirewallUtilities.doCommand(command):
            return 0

        return 1