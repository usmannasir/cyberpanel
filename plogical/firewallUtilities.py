#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys

import django
sys.path.append('/usr/local/CyberCP')
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
try:
    django.setup()
except:
    pass

import plogical.CyberCPLogFileWriter as logging
import argparse
from plogical.processUtilities import ProcessUtilities


class FirewallUtilities:

    @staticmethod
    def resFailed(res):
        if (ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu or ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu20) and res != 0:
            return True
        elif (ProcessUtilities.decideDistro() == ProcessUtilities.centos or ProcessUtilities.decideDistro() == ProcessUtilities.cent8) and res == 1:
            return True
        return False

    @staticmethod
    def doCommand(command):
        try:
            res = ProcessUtilities.executioner(command)
            if res == 0:
                logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error #" + str(res))
                return 0

        except OSError as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error: " + str(msg))
            return 0
        except ValueError as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to apply rule: " + command + " Error: " + str(msg), 1)
            return 0
        return 1


    @staticmethod
    def addRule(proto,port,ipAddress):
        ruleFamily = 'rule family="ipv4"'
        sourceAddress = 'source address="' + ipAddress + '"'
        ruleProtocol = 'port protocol="' + proto + '"'
        rulePort = 'port="' + port + '"'

        command = "firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        ruleFamily = 'rule family="ipv6"'
        sourceAddress = ''

        command = "firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        command = 'firewall-cmd --reload'

        ProcessUtilities.executioner(command)

        return 1

    @staticmethod
    def addSieveFirewallRule():
        """Add Sieve port 4190 to firewall for all OS variants"""
        try:
            # Add Sieve port 4190 to firewall
            FirewallUtilities.addRule('tcp', '4190', '0.0.0.0/0')
            logging.CyberCPLogFileWriter.writeToFile("Sieve port 4190 added to firewall successfully")
            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to add Sieve port 4190 to firewall: " + str(msg))
            return 0

    @staticmethod
    def deleteRule(proto, port, ipAddress):
        ruleFamily = 'rule family="ipv4"'
        sourceAddress = 'source address="' + ipAddress + '"'
        ruleProtocol = 'port protocol="' + proto + '"'
        rulePort = 'port="' + port + '"'

        command = "firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        ruleFamily = 'rule family="ipv6"'
        sourceAddress = ''

        command = "firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + ruleProtocol + " " + rulePort + " " + "accept'"

        ProcessUtilities.executioner(command)

        command = 'firewall-cmd --reload'

        ProcessUtilities.executioner(command)

        return 1

    @staticmethod
    def blockIP(ip_address, reason="Manual block"):
        """
        Block an IP address using firewalld
        """
        try:
            # Create a drop rule for the IP address
            ruleFamily = 'rule family="ipv4"'
            sourceAddress = 'source address="' + ip_address + '"'
            action = 'drop'

            command = "firewall-cmd --permanent --zone=public --add-rich-rule='" + ruleFamily + " " + sourceAddress + " " + action + "'"
            
            logging.CyberCPLogFileWriter.writeToFile(f"Blocking IP address: {ip_address} - Reason: {reason}")
            
            # executioner returns 1 on success, 0 on failure
            result = ProcessUtilities.executioner(command)
            if result == 1:
                logging.CyberCPLogFileWriter.writeToFile(f"Successfully blocked IP: {ip_address}")
                ProcessUtilities.executioner('firewall-cmd --reload')
                block_log_path = "/usr/local/CyberCP/data/blocked_ips.log"
                try:
                    import os
                    os.makedirs(os.path.dirname(block_log_path), exist_ok=True)
                    with open(block_log_path, "a") as f:
                        from datetime import datetime
                        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {ip_address} - {reason}\n")
                except Exception as log_err:
                    logging.CyberCPLogFileWriter.writeToFile(f"Warning: could not write blocked_ips.log: {log_err}")
                return True, f"IP {ip_address} blocked successfully"
            else:
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to block IP: {ip_address} (executioner returned %s)" % result)
                return False, f"Failed to block IP: {ip_address}"
                
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error blocking IP {ip_address}: {str(e)}")
            return False, f"Error blocking IP: {str(e)}"

    @staticmethod
    def unblockIP(ip_address):
        """
        Unblock an IP address by removing the drop rule
        """
        try:
            ruleFamily = 'rule family="ipv4"'
            sourceAddress = 'source address="' + ip_address + '"'
            action = 'drop'

            command = "firewall-cmd --permanent --zone=public --remove-rich-rule='" + ruleFamily + " " + sourceAddress + " " + action + "'"
            
            logging.CyberCPLogFileWriter.writeToFile(f"Unblocking IP address: {ip_address}")
            
            # executioner returns 1 on success, 0 on failure
            result = ProcessUtilities.executioner(command)
            if result == 1:
                logging.CyberCPLogFileWriter.writeToFile(f"Successfully unblocked IP: {ip_address}")
                ProcessUtilities.executioner('firewall-cmd --reload')
                return True, f"IP {ip_address} unblocked successfully"
            else:
                logging.CyberCPLogFileWriter.writeToFile(f"Failed to unblock IP: {ip_address} (executioner returned %s)" % result)
                return False, f"Failed to unblock IP: {ip_address}"
                
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error unblocking IP {ip_address}: {str(e)}")
            return False, f"Error unblocking IP: {str(e)}"

    @staticmethod
    def isIPBlocked(ip_address):
        """
        Check if an IP address is currently blocked
        """
        try:
            command = "firewall-cmd --list-rich-rules | grep -i '" + ip_address + "'"
            result = ProcessUtilities.normalExecutioner(command)
            return result == 0
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error checking if IP {ip_address} is blocked: {str(e)}")
            return False

    @staticmethod
    def closeConnectionsFromIP(ip_address):
        """
        Try to close/drop existing connections from the given IP so the remote host
        cannot keep trying (e.g. when IP is already banned and admin clicks Ban again).
        Uses conntrack when available; safe to call even if no connections exist.
        """
        try:
            # conntrack -D -s IP deletes connection tracking entries from this source IP,
            # which drops existing TCP connections from that IP (kernel sends RST or they time out).
            command = "conntrack -D -s %s 2>/dev/null" % ip_address
            result = ProcessUtilities.executioner(command)
            logging.CyberCPLogFileWriter.writeToFile("closeConnectionsFromIP %s: conntrack returned %s" % (ip_address, result))
            # executioner returns 1 on success; conntrack may also return 0 when no entries found (still ok)
            return True, "Connections from %s have been closed" % ip_address
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile("closeConnectionsFromIP error for %s: %s" % (ip_address, str(e)))
            return False, str(e)

    @staticmethod
    def getBlockedIPs():
        """
        Get list of currently blocked IP addresses
        """
        try:
            command = "firewall-cmd --list-rich-rules | grep 'drop' | grep 'source address'"
            result = ProcessUtilities.normalExecutioner(command)
            if result == 0:
                # Parse the output to extract IP addresses
                import subprocess
                try:
                    output = subprocess.check_output(command, shell=True, text=True)
                    blocked_ips = []
                    for line in output.split('\n'):
                        if 'source address=' in line:
                            # Extract IP from the line
                            import re
                            ip_match = re.search(r'source address="([^"]+)"', line)
                            if ip_match:
                                blocked_ips.append(ip_match.group(1))
                    return blocked_ips
                except:
                    return []
            return []
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error getting blocked IPs: {str(e)}")
            return []

    @staticmethod
    def saveSSHConfigs(type, sshPort, rootLogin):
        try:
            if type == "1":

                command = 'semanage port -a -t ssh_port_t -p tcp ' + sshPort
                ProcessUtilities.normalExecutioner(command)

                FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")


                if rootLogin == "1":
                    rootLogin = "PermitRootLogin yes\n"
                else:
                    rootLogin = "PermitRootLogin no\n"

                sshPortLine = "Port " + sshPort + "\n"

                pathToSSH = "/etc/ssh/sshd_config"

                data = open(pathToSSH, 'r').readlines()

                writeToFile = open(pathToSSH, "w")

                # Only one Port line must be written (sshd binds once per Port directive;
                # duplicates cause "Address already in use"). Only match actual "Port N"
                # directive, not GatewayPorts or other lines containing "Port".
                port_line_written = False

                def is_ssh_port_directive(line):
                    stripped = line.strip()
                    if 'GatewayPorts' in line or not stripped.startswith('Port '):
                        return False
                    parts = stripped.split()
                    return len(parts) >= 2 and parts[0] == 'Port' and parts[1].isdigit()

                for items in data:
                    if items.find("PermitRootLogin") > -1:
                        if items.find("Yes") > -1 or items.find("yes"):
                            writeToFile.writelines(rootLogin)
                            continue
                    elif is_ssh_port_directive(items):
                        if not port_line_written:
                            writeToFile.writelines(sshPortLine)
                            port_line_written = True
                        # skip duplicate Port lines (do not write again)
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

                # If no Port line was present in config, append one (sshd defaults to 22 otherwise)
                if not port_line_written:
                    with open(pathToSSH, 'a') as appendFile:
                        appendFile.write(sshPortLine)

                command = 'systemctl restart sshd'
                ProcessUtilities.normalExecutioner(command)

                print("1,None")

        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def addSSHKey(tempPath, path=None):
        try:
            key = open(tempPath, 'r').read()

            if path == None:
                sshDir = "/root/.ssh"
                pathToSSH = "/root/.ssh/authorized_keys"

                if os.path.exists(sshDir):
                    pass
                else:
                    os.mkdir(sshDir)
            else:
                pathToSSH = path

            if os.path.exists(pathToSSH):
                pass
            else:
                sshFile = open(pathToSSH, 'w')
                sshFile.writelines("#Created by CyberPanel\n")
                sshFile.close()

            presenseCheck = 0
            try:
                data = open(pathToSSH, "r").readlines()
                for items in data:
                    if items.find(key) > -1:
                        presenseCheck = 1
            except:
                pass

            if presenseCheck == 0:
                writeToFile = open(pathToSSH, 'a')
                writeToFile.writelines("#Added by CyberPanel\n")
                writeToFile.writelines("\n")
                writeToFile.writelines(key)
                writeToFile.writelines("\n")
                writeToFile.close()

            if os.path.split(tempPath):
                os.remove(tempPath)

            print("1,None")

        except BaseException as msg:
            print("0," + str(msg))

    @staticmethod
    def deleteSSHKey(key, path=None):
        try:
            keyPart = key.split(" ")[1]

            if path == None:
                pathToSSH = "/root/.ssh/authorized_keys"
            else:
                pathToSSH = path

            data = open(pathToSSH, 'r').readlines()

            writeToFile = open(pathToSSH, "w")

            for items in data:
                if items.find("ssh-rsa") > -1 and items.find(keyPart) > -1:
                    continue
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            print("1,None")

        except BaseException as msg:
            print("0," + str(msg))


def main():

    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('function', help='Specific a function to call!')

    ## Litespeed Tuning Arguments

    parser.add_argument("--tempPath", help="Temporary path to file where PHP is storing data!")

    parser.add_argument("--type", help="Type")
    parser.add_argument("--sshPort", help="SSH Port")
    parser.add_argument("--rootLogin", help="Root Login")
    parser.add_argument("--key", help="Key")
    parser.add_argument("--path", help="Path to key file.")


    args = parser.parse_args()

    if args.function == "saveSSHConfigs":
        FirewallUtilities.saveSSHConfigs(args.type, args.sshPort, args.rootLogin)
    elif args.function == "addSSHKey":
        if not args.path:
            FirewallUtilities.addSSHKey(args.tempPath)
        else:
            FirewallUtilities.addSSHKey(args.tempPath, args.path)
    elif args.function == "deleteSSHKey":
        if not args.path:
            FirewallUtilities.deleteSSHKey(args.key)
        else:
            FirewallUtilities.deleteSSHKey(args.key, args.path)



if __name__ == "__main__":
    main()