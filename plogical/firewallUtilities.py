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
import re
import ipaddress
import shlex
from plogical.processUtilities import ProcessUtilities
from plogical.sshKeyUtilities import delete_authorized_key
from plogical.sshConfigUtilities import update_ssh_config, ssh_service_is_listening

_FW_ALLOWED_PROTOCOLS = {'tcp', 'udp', 'sctp', 'dccp'}
_FW_PORT_RE = re.compile(r'[0-9]{1,5}(?:-[0-9]{1,5})?')
_PUBLIC_ZONE = 'firewall-cmd --zone=public'


def _richRules(proto, port, address, dual_stack=False):
    port = str(port)
    if proto not in _FW_ALLOWED_PROTOCOLS or not _FW_PORT_RE.fullmatch(port):
        raise ValueError('Enter a valid protocol and port.')
    ports = [int(item) for item in port.split('-')]
    if not 1 <= ports[0] <= ports[-1] <= 65535:
        raise ValueError('Enter a valid port or port range.')
    if not isinstance(address, str) or '%' in address:
        raise ValueError('Enter a valid IPv4 or IPv6 source.')
    network = ipaddress.ip_network(address, strict=False)
    source = str(network.network_address) if network.prefixlen == network.max_prefixlen else str(network)
    spec = 'port port="%s" protocol="%s" accept' % ('-'.join(map(str, ports)), proto)
    rules = ['rule family="ipv%d" source address="%s" %s' % (network.version, source, spec)]
    if dual_stack:
        if network.version != 4 or network.prefixlen != 0:
            raise ValueError('Dual-stack service rules require an unrestricted IPv4 source.')
        rules.append('rule family="ipv6" ' + spec)
    return rules


def _ruleKey(rule):
    # firewalld can reorder port attributes and render a host with or without its mask.
    words = shlex.split(rule)
    for index, word in enumerate(words):
        if word.startswith('address='):
            try:
                words[index] = 'address=' + str(ipaddress.ip_network(word[8:], strict=False))
            except ValueError:
                pass
    return sorted(words)


def _firewalld(command):
    result = ProcessUtilities.outputExecutioner(command, shell=False, retRequired=True)
    if not isinstance(result, (tuple, list)) or len(result) != 2 or result[0] != 1:
        raise RuntimeError('firewalld could not complete the requested operation.')
    output = result[1]
    if not isinstance(output, (str, bytes)):
        raise RuntimeError('firewalld returned an invalid response.')
    return output.decode('utf-8', 'replace') if isinstance(output, bytes) else output


def _changeRules(rules, *, remove=False, require_new=False):
    planned = []
    for scope in (_PUBLIC_ZONE + ' --permanent', _PUBLIC_ZONE):
        existing = _firewalld(scope + ' --list-rich-rules').splitlines()
        for rule in rules:
            matches = [line for line in existing if _ruleKey(line) == _ruleKey(rule)]
            if len(matches) > 1 or (require_new and matches):
                raise ValueError('A matching firewalld rule already exists. Review it before changing it.')
            if remove and matches:
                planned.append((scope, matches[0]))
            elif not remove and not matches:
                planned.append((scope, rule))
    verb, undo = ('remove', 'add') if remove else ('add', 'remove')
    changed = []
    try:
        for scope, rule in planned:
            output = _firewalld(scope + ' --' + verb + '-rich-rule=' + shlex.quote(rule))
            if 'ALREADY_ENABLED:' in output or 'NOT_ENABLED:' in output:
                raise RuntimeError('The rule changed during the operation. Refresh the firewalld view.')
            changed.append((scope, rule))
        for scope in (_PUBLIC_ZONE + ' --permanent', _PUBLIC_ZONE):
            observed = _firewalld(scope + ' --list-rich-rules').splitlines()
            for rule in rules:
                present = any(_ruleKey(line) == _ruleKey(rule) for line in observed)
                if present == remove:
                    raise RuntimeError('Firewall rule readback did not match the requested change.')
    except RuntimeError:
        rollback_failed = False
        for scope, rule in reversed(changed):
            try:
                _firewalld(scope + ' --' + undo + '-rich-rule=' + shlex.quote(rule))
            except RuntimeError:
                rollback_failed = True
        if rollback_failed:
            raise RuntimeError('Firewall rollback incomplete. Review runtime and permanent rules.')
        raise


class FirewallUtilities:

    @staticmethod
    def ruleIdentity(proto, port, ipAddress):
        try:
            return _richRules(proto, port, ipAddress)[0]
        except ValueError:
            return None

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
    def addRule(proto, port, ipAddress, *, dual_stack=False, require_new=False):
        try:
            _changeRules(_richRules(proto, port, ipAddress, dual_stack), require_new=require_new)
        except (ValueError, RuntimeError) as error:
            logging.CyberCPLogFileWriter.writeToFile(str(error))
            return 0
        return 1

    @staticmethod
    def currentFirewalldConfiguration():
        return {
            'runtime': _firewalld('firewall-cmd --list-all-zones'),
            'permanent': _firewalld('firewall-cmd --permanent --list-all-zones'),
        }

    @staticmethod
    def addSieveFirewallRule():
        """Add Sieve port 4190 to firewall for all OS variants"""
        try:
            # Add Sieve port 4190 to firewall
            if not FirewallUtilities.addRule('tcp', '4190', '0.0.0.0/0', dual_stack=True):
                return 0
            logging.CyberCPLogFileWriter.writeToFile("Sieve port 4190 added to firewall successfully")
            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile("Failed to add Sieve port 4190 to firewall: " + str(msg))
            return 0

    @staticmethod
    def deleteRule(proto, port, ipAddress, *, dual_stack=False):
        try:
            _changeRules(_richRules(proto, port, ipAddress, dual_stack), remove=True)
        except (ValueError, RuntimeError) as error:
            logging.CyberCPLogFileWriter.writeToFile(str(error))
            return 0
        return 1

    @staticmethod
    def saveSSHConfigs(type, sshPort, rootLogin):
        try:
            if type != "1":
                raise ValueError('Unsupported SSH configuration action.')

            def prepare():
                ProcessUtilities.normalExecutioner('semanage port -a -t ssh_port_t -p tcp ' + str(int(sshPort)))
                FirewallUtilities.addRule('tcp', str(int(sshPort)), "0.0.0.0/0", dual_stack=True)

            update_ssh_config(
                '/etc/ssh/sshd_config', sshPort, 'yes' if rootLogin == '1' else 'no',
                prepare=prepare,
                restart=lambda: ProcessUtilities.normalExecutioner('systemctl restart sshd') == 1,
                is_active=lambda: ProcessUtilities.normalExecutioner('systemctl is-active --quiet sshd') == 1,
                is_listening=lambda: ssh_service_is_listening(sshPort))
            print("1,None")
        except Exception as msg:
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
            if path == None:
                pathToSSH = "/root/.ssh/authorized_keys"
            else:
                pathToSSH = path

            if delete_authorized_key(pathToSSH, key):
                print("1,None")
            else:
                print("0,SSH key not found.")

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
