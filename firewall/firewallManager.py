#!/usr/local/CyberCP/bin/python
import os
import os.path
import sys
import django

PROJECT_ROOT = '/usr/local/CyberCP'
while PROJECT_ROOT in sys.path:
    sys.path.remove(PROJECT_ROOT)
sys.path.insert(0, PROJECT_ROOT)

from loginSystem.models import Administrator
from plogical.httpProc import httpProc
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()
import json
import shlex
from plogical.acl import ACLManager
from plogical.securityUtils import is_safe_port
import plogical.CyberCPLogFileWriter as logging
from plogical.virtualHostUtilities import virtualHostUtilities
import subprocess
from django.shortcuts import HttpResponse, render, redirect
from random import randint
import time
from plogical.firewallUtilities import FirewallUtilities
from firewall.models import FirewallRules
from firewall import ruleOrder as FirewallRuleOrder
from plogical.modSec import modSec
from plogical.csf import CSF
from plogical.processUtilities import ProcessUtilities
from serverStatus.serverStatusUtil import ServerStatusUtil

class FirewallManager:

    imunifyPath = '/usr/bin/imunify360-agent'
    CLPath = '/etc/sysconfig/cloudlinux'
    imunifyAVPath = '/etc/sysconfig/imunify360/integration.conf'
    BANNED_IPS_PRIMARY_FILE = '/usr/local/CyberCP/data/banned_ips.json'
    BANNED_IPS_LEGACY_FILE = '/etc/cyberpanel/banned_ips.json'

    def __init__(self, request = None):
        self.request = request

    @staticmethod
    def _normalize_banned_ip_key(ip):
        return (ip or '').strip().lower()

    def _remove_autoban_log_by_suffix_id(self, userID, ablog_id_str):
        final_dic = {'status': 0, 'error_message': 'Auto-ban log entries require the autoBan Security Alerts plugin.'}
        return HttpResponse(json.dumps(final_dic), content_type='application/json')


    def _load_banned_ips_store(self):
        """
        Load banned IPs from the primary store, falling back to legacy path.
        Returns (data, path_used)
        """
        for path in [self.BANNED_IPS_PRIMARY_FILE, self.BANNED_IPS_LEGACY_FILE]:
            if os.path.exists(path):
                try:
                    with open(path, 'r') as f:
                        return json.load(f), path
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Failed to read banned IPs from {path}: {str(e)}')
        return [], self.BANNED_IPS_PRIMARY_FILE

    def _save_banned_ips_store(self, data):
        """
        Persist banned IPs to the primary store in a writable location.
        """
        target = self.BANNED_IPS_PRIMARY_FILE
        try:
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f'Failed to write banned IPs to {target}: {str(e)}')
            raise
        return target

    def securityHome(self, request = None, userID = None):
        proc = httpProc(request, 'firewall/index.html',
                        None, 'admin')
        return proc.render()

    def firewallHome(self, request = None, userID = None):
        csfPath = '/etc/csf'

        if os.path.exists(csfPath):
            return redirect('/configservercsf/')
        else:
            proc = httpProc(request, 'firewall/firewall.html',
                            None, 'admin')
            return proc.render()

    def getCurrentRules(self, userID=None, data=None):
        """
        Get firewall rules with optional pagination.
        data may contain: page (1-based), page_size (default 10).
        Returns: fetchStatus 1, data (JSON array), total_count, page, page_size.
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            rules_qs = FirewallRuleOrder.ordered_queryset()

            # Ensure CyberPanel port 7080 rule exists in database for visibility
            cyberpanel_rule_exists = rules_qs.filter(port='7080').exists()
            if not cyberpanel_rule_exists:
                try:
                    FirewallRules(
                        name="CyberPanel Admin",
                        proto="tcp",
                        port="7080",
                        ipAddress="0.0.0.0/0",
                        sortOrder=FirewallRuleOrder.next_sort_order()
                    ).save()
                    logging.CyberCPLogFileWriter.writeToFile("Added CyberPanel port 7080 to firewall database for UI visibility")
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f"Failed to add CyberPanel port 7080 to database: {str(e)}")
                rules_qs = FirewallRuleOrder.ordered_queryset()

            total_count = rules_qs.count()
            page = 1
            page_size = 10
            if data:
                try:
                    page = max(1, int(data.get('page', 1)))
                except (TypeError, ValueError):
                    pass
                try:
                    page_size = max(1, min(100, int(data.get('page_size', 10))))
                except (TypeError, ValueError):
                    pass

            start = (page - 1) * page_size
            end = start + page_size
            rules = list(rules_qs[start:end])

            json_data = "["
            for i, items in enumerate(rules):
                # displayId is 1-based position in the full ordered list (top row = 1)
                display_id = start + i + 1
                dic = {
                    'id': items.id,
                    'displayId': display_id,
                    'sortOrder': items.sortOrder or display_id,
                    'name': items.name,
                    'proto': items.proto,
                    'port': items.port,
                    'ipAddress': items.ipAddress,
                }
                if i > 0:
                    json_data += ','
                json_data += json.dumps(dic)
            json_data += ']'

            final_json = json.dumps({
                'status': 1,
                'fetchStatus': 1,
                'error_message': "None",
                "data": json_data,
                "total_count": total_count,
                "page": page,
                "page_size": page_size
            })
            return HttpResponse(final_json, content_type='application/json')

        except BaseException as msg:
            final_dic = {'status': 0, 'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

    def addRule(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('add_status', 0)

            ruleName = data['ruleName']
            ruleProtocol = data['ruleProtocol']
            rulePort = data['rulePort']
            ruleIP = data['ruleIP']

            FirewallUtilities.addRule(ruleProtocol, rulePort, ruleIP)

            newFWRule = FirewallRules(
                name=ruleName,
                proto=ruleProtocol,
                port=rulePort,
                ipAddress=ruleIP,
                sortOrder=FirewallRuleOrder.next_sort_order()
            )
            newFWRule.save()

            final_dic = {'status': 1, 'add_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def reorderRules(self, userID=None, data=None):
        """
        Persist Firewall Rules table order in MariaDB (sortOrder).
        Payload options:
          - direction + id: move one step up/down
          - page_ordered_ids + page + page_size: reorder within a page
          - ordered_ids: full global order
        Works whether firewalld is running or stopped (DB-only).
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                return ACLManager.loadErrorJson('reorder_status', 0)

            data = data or {}
            direction = (data.get('direction') or '').strip().lower()
            rule_id = data.get('id')
            page_ordered_ids = data.get('page_ordered_ids')
            ordered_ids = data.get('ordered_ids')

            if direction in ('up', 'down') and rule_id is not None:
                new_order = FirewallRuleOrder.move_rule(rule_id, direction)
            elif page_ordered_ids is not None:
                page = data.get('page', 1)
                page_size = data.get('page_size', 10)
                new_order = FirewallRuleOrder.apply_page_order(
                    page_ordered_ids, page, page_size
                )
            elif ordered_ids is not None:
                new_order = FirewallRuleOrder.apply_ordered_ids(ordered_ids)
            else:
                final_dic = {
                    'status': 0,
                    'reorder_status': 0,
                    'error_message': 'Provide direction+id, page_ordered_ids, or ordered_ids'
                }
                return HttpResponse(
                    json.dumps(final_dic), content_type='application/json'
                )

            final_dic = {
                'status': 1,
                'reorder_status': 1,
                'error_message': 'None',
                'ordered_ids': new_order,
            }
            return HttpResponse(
                json.dumps(final_dic), content_type='application/json'
            )

        except ValueError as msg:
            final_dic = {
                'status': 0,
                'reorder_status': 0,
                'error_message': str(msg)
            }
            return HttpResponse(
                json.dumps(final_dic), content_type='application/json'
            )
        except BaseException as msg:
            final_dic = {
                'status': 0,
                'reorder_status': 0,
                'error_message': str(msg)
            }
            return HttpResponse(
                json.dumps(final_dic), content_type='application/json'
            )

    def deleteRule(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('delete_status', 0)

            ruleID = data['id']
            ruleProtocol = data['proto']
            rulePort = data['port']
            ruleIP = data['ruleIP']

            FirewallUtilities.deleteRule(ruleProtocol, rulePort, ruleIP)

            delRule = FirewallRules.objects.get(id=ruleID)
            delRule.delete()
            FirewallRuleOrder.renumber_all()

            final_dic = {'status': 1, 'delete_status': 1, 'error_message': "None"}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def modifyRule(self, userID=None, data=None):
        """
        Update an existing firewall rule: remove old rule from firewalld and DB, add new rule.
        data: id, name, proto, port, ruleIP (or ipAddress).
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                return ACLManager.loadErrorJson('status', 0)

            rule_id = data.get('id')
            new_name = (data.get('name') or data.get('ruleName') or '').strip()
            new_proto = (data.get('proto') or data.get('ruleProtocol') or 'tcp').strip().lower()
            new_port = (data.get('port') or data.get('rulePort') or '').strip()
            new_ip = (data.get('ruleIP') or data.get('ipAddress') or '0.0.0.0/0').strip()

            if not rule_id:
                final_dic = {'status': 0, 'error_message': 'Rule ID is required'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')
            if not new_name:
                final_dic = {'status': 0, 'error_message': 'Rule name is required'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')
            if new_proto not in ('tcp', 'udp'):
                final_dic = {'status': 0, 'error_message': 'Protocol must be tcp or udp'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')
            if not new_port:
                final_dic = {'status': 0, 'error_message': 'Port is required'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')

            existing = FirewallRules.objects.get(id=rule_id)
            old_proto = existing.proto
            old_port = existing.port
            old_ip = existing.ipAddress

            FirewallUtilities.deleteRule(old_proto, old_port, old_ip)
            FirewallUtilities.addRule(new_proto, new_port, new_ip)

            existing.name = new_name
            existing.proto = new_proto
            existing.port = new_port
            existing.ipAddress = new_ip
            existing.save()

            final_dic = {'status': 1, 'modify_status': 1, 'error_message': 'None'}
            return HttpResponse(json.dumps(final_dic), content_type='application/json')

        except FirewallRules.DoesNotExist:
            final_dic = {'status': 0, 'error_message': 'Rule not found'}
            return HttpResponse(json.dumps(final_dic), content_type='application/json')
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            return HttpResponse(json.dumps(final_dic), content_type='application/json')

    def reloadFirewall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('reload_status', 0)

            command = 'sudo firewall-cmd --reload'
            res = ProcessUtilities.executioner(command)

            if res == 1:
                final_dic = {'reload_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'reload_status': 0,
                             'error_message': "Can not reload firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'reload_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def startFirewall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('start_status', 0)

            command = 'sudo systemctl start firewalld'
            res = ProcessUtilities.executioner(command)

            if res == 1:
                # UI order lives in MariaDB sortOrder; getCurrentRules / start both read that order.
                # firewalld rich-rules are a set of accepts (port opens); order is persisted for the panel.
                try:
                    FirewallRuleOrder.ensure_sort_orders()
                except BaseException as order_msg:
                    logging.CyberCPLogFileWriter.writeToFile(
                        "Firewall start: ensure sortOrder warning: %s" % str(order_msg)
                    )
                final_dic = {'start_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'start_status': 0,
                             'error_message': "Can not start firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'start_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def stopFirewall(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('stop_status', 0)

            command = 'sudo systemctl stop firewalld'
            res = ProcessUtilities.executioner(command)

            if res == 1:
                final_dic = {'stop_status': 1, 'error_message': "None"}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'stop_status': 0,
                             'error_message': "Can not stop firewall, see CyberCP main log file."}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'stop_status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def firewallStatus(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            command = 'systemctl status firewalld'
            status = ProcessUtilities.outputExecutioner(command)

            if status.find("dead") > -1:
                final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 0}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 1, 'error_message': "none", 'firewallStatus': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def secureSSH(self, request = None, userID = None):
        proc = httpProc(request, 'firewall/secureSSH.html',
                        None, 'admin')
        return proc.render()

    def getSSHConfigs(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            type = data['type']

            if type == "1":

                ## temporarily changing permission for sshd files

                pathToSSH = "/etc/ssh/sshd_config"

                cat = "sudo cat " + pathToSSH
                data = ProcessUtilities.outputExecutioner(cat).split('\n')

                permitRootLogin = 0
                sshPort = "22"

                for items in data:
                    if items.find("PermitRootLogin") > -1:
                        if items.find("Yes") > -1 or items.find("yes") > -1:
                            permitRootLogin = 1
                            continue
                    if items.find("Port") > -1 and not items.find("GatewayPorts") > -1:
                        sshPort = items.split(" ")[1].strip("\n")

                final_dic = {'status': 1, 'permitRootLogin': permitRootLogin, 'sshPort': sshPort}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:

                pathToKeyFile = "/root/.ssh/authorized_keys"

                cat = "sudo cat " + pathToKeyFile
                data = ProcessUtilities.outputExecutioner(cat).split('\n')

                json_data = "["
                checker = 0

                for items in data:
                    if items.find("ssh-rsa") > -1:
                        keydata = items.split(" ")

                        try:
                            key = "ssh-rsa " + keydata[1][:50] + "  ..  " + keydata[2]
                            try:
                                userName = keydata[2][:keydata[2].index("@")]
                            except:
                                userName = keydata[2]
                        except:
                            key = "ssh-rsa " + keydata[1][:50]
                            userName = ''



                        dic = {'userName': userName,
                               'key': key,
                               }

                        if checker == 0:
                            json_data = json_data + json.dumps(dic)
                            checker = 1
                        else:
                            json_data = json_data + ',' + json.dumps(dic)

                json_data = json_data + ']'

                final_json = json.dumps({'status': 1, 'error_message': "None", "data": json_data})
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveSSHConfigs(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            type = data['type']
            sshPort = data['sshPort']
            rootLogin = data['rootLogin']

            if rootLogin == True:
                rootLogin = "1"
            else:
                rootLogin = "0"

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " saveSSHConfigs --type " + str(type) + " --sshPort " + sshPort + " --rootLogin " + rootLogin

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:

                csfPath = '/etc/csf'

                if os.path.exists(csfPath):
                    dataIn = {'protocol': 'TCP_IN', 'ports': sshPort}
                    self.modifyPorts(dataIn)
                    dataIn = {'protocol': 'TCP_OUT', 'ports': sshPort}
                    self.modifyPorts(dataIn)
                else:
                    try:
                        updateFW = FirewallRules.objects.get(name="SSHCustom")
                        FirewallUtilities.deleteRule("tcp", updateFW.port, "0.0.0.0/0")
                        updateFW.port = sshPort
                        updateFW.save()
                        FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                    except:
                        try:
                            newFireWallRule = FirewallRules(name="SSHCustom", port=sshPort, proto="tcp")
                            newFireWallRule.save()
                            FirewallUtilities.addRule('tcp', sshPort, "0.0.0.0/0")
                            command = 'firewall-cmd --permanent --remove-service=ssh'
                            ProcessUtilities.executioner(command)
                        except BaseException as msg:
                            logging.CyberCPLogFileWriter.writeToFile(str(msg))

                final_dic = {'status': 1, 'saveStatus': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 0, 'saveStatus': 0, "error_message": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0 ,'saveStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def deleteSSHKey(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('delete_status', 0)

            key = data['key']

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " deleteSSHKey --key '" + key + "'"

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                final_dic = {'status': 1, 'delete_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 1, 'delete_status': 1, "error_mssage": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'delete_status': 0, 'error_mssage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def addSSHKey(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('add_status', 0)

            key = data['key']

            tempPath = "/home/cyberpanel/" + str(randint(1000, 9999))

            writeToFile = open(tempPath, "w")
            writeToFile.write(key)
            writeToFile.close()

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/firewallUtilities.py"
            execPath = execPath + " addSSHKey --tempPath " + tempPath

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                final_dic = {'status': 1, 'add_status': 1}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                final_dic = {'status': 0, 'add_status': 0, "error_mssage": output}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'add_status': 0, 'error_mssage': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def loadModSecurityHome(self, request = None, userID = None):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            OLS = 1
            confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

            modSecInstalled = 0

            for items in httpdConfig:
                if items.find('module mod_security') > -1:
                    modSecInstalled = 1
                    break
        else:
            OLS = 0
            modSecInstalled = 1

        proc = httpProc(request, 'firewall/modSecurity.html',
                        {'modSecInstalled': modSecInstalled, 'OLS': OLS}, 'admin')
        return proc.render()

    def installModSec(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installModSec', 0)

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
            execPath = execPath + " installModSec"

            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(3)

            final_json = json.dumps({'installModSec': 1, 'error_message': "None"})
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'installModSec': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusModSec(self, userID = None, data = None):
        try:

            command = "sudo cat " + modSec.installLogPath
            installStatus = ProcessUtilities.outputExecutioner(command)

            if installStatus.find("[200]") > -1:

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " installModSecConfigs"

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    pass
                else:
                    final_json = json.dumps({
                        'error_message': "Failed to install ModSecurity configurations.",
                        'requestStatus': installStatus,
                        'abort': 1,
                        'installed': 0,
                    })
                    return HttpResponse(final_json)

                final_json = json.dumps({
                    'error_message': "None",
                    'requestStatus': installStatus,
                    'abort': 1,
                    'installed': 1,
                })
                return HttpResponse(final_json)
            elif installStatus.find("[404]") > -1:

                final_json = json.dumps({
                    'abort': 1,
                    'installed': 0,
                    'error_message': "None",
                    'requestStatus': installStatus,
                })
                return HttpResponse(final_json)

            else:
                final_json = json.dumps({
                    'abort': 0,
                    'error_message': "None",
                    'requestStatus': installStatus,
                })
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'abort': 1, 'installed': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchModSecSettings(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                modsecurity = 0
                SecAuditEngine = 0
                SecRuleEngine = 0
                SecDebugLogLevel = "9"
                SecAuditLogRelevantStatus = '^(?:5|4(?!04))'
                SecAuditLogParts = 'ABIJDEFHZ'
                SecAuditLogType = 'Serial'

                confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/httpd_config.conf')
                modSecPath = os.path.join(virtualHostUtilities.Server_root, 'modules', 'mod_security.so')

                if os.path.exists(modSecPath):
                    command = "sudo cat " + confPath
                    data = ProcessUtilities.outputExecutioner(command).split('\n')

                    for items in data:

                        if items.find('modsecurity ') > -1:
                            if items.find('on') > -1 or items.find('On') > -1:
                                modsecurity = 1
                                continue
                        if items.find('SecAuditEngine ') > -1:
                            if items.find('on') > -1 or items.find('On') > -1:
                                SecAuditEngine = 1
                                continue

                        if items.find('SecRuleEngine ') > -1:
                            if items.find('on') > -1 or items.find('On') > -1:
                                SecRuleEngine = 1
                                continue

                        if items.find('SecDebugLogLevel') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecDebugLogLevel':
                                SecDebugLogLevel = result[1]
                                continue
                        if items.find('SecAuditLogRelevantStatus') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecAuditLogRelevantStatus':
                                SecAuditLogRelevantStatus = result[1]
                                continue
                        if items.find('SecAuditLogParts') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecAuditLogParts':
                                SecAuditLogParts = result[1]
                                continue
                        if items.find('SecAuditLogType') > -1:
                            result = items.split(' ')
                            if result[0] == 'SecAuditLogType':
                                SecAuditLogType = result[1]
                                continue

                    final_dic = {'fetchStatus': 1,
                                 'installed': 1,
                                 'SecRuleEngine': SecRuleEngine,
                                 'modsecurity': modsecurity,
                                 'SecAuditEngine': SecAuditEngine,
                                 'SecDebugLogLevel': SecDebugLogLevel,
                                 'SecAuditLogParts': SecAuditLogParts,
                                 'SecAuditLogRelevantStatus': SecAuditLogRelevantStatus,
                                 'SecAuditLogType': SecAuditLogType,
                                 }

                else:
                    final_dic = {'fetchStatus': 1,
                                 'installed': 0}
            else:
                SecAuditEngine = 0
                SecRuleEngine = 0
                SecDebugLogLevel = "9"
                SecAuditLogRelevantStatus = '^(?:5|4(?!04))'
                SecAuditLogParts = 'ABIJDEFHZ'
                SecAuditLogType = 'Serial'

                confPath = os.path.join(virtualHostUtilities.Server_root, 'conf/modsec.conf')

                command = "sudo cat " + confPath

                data = ProcessUtilities.outputExecutioner(command).split('\n')

                for items in data:
                    if items.find('SecAuditEngine ') > -1:
                        if items.find('on') > -1 or items.find('On') > -1:
                            SecAuditEngine = 1
                            continue

                    if items.find('SecRuleEngine ') > -1:
                        if items.find('on') > -1 or items.find('On') > -1:
                            SecRuleEngine = 1
                            continue

                    if items.find('SecDebugLogLevel') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecDebugLogLevel':
                            SecDebugLogLevel = result[1]
                            continue
                    if items.find('SecAuditLogRelevantStatus') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecAuditLogRelevantStatus':
                            SecAuditLogRelevantStatus = result[1]
                            continue
                    if items.find('SecAuditLogParts') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecAuditLogParts':
                            SecAuditLogParts = result[1]
                            continue
                    if items.find('SecAuditLogType') > -1:
                        result = items.split(' ')
                        if result[0] == 'SecAuditLogType':
                            SecAuditLogType = result[1]
                            continue

                final_dic = {'fetchStatus': 1,
                             'installed': 1,
                             'SecRuleEngine': SecRuleEngine,
                             'SecAuditEngine': SecAuditEngine,
                             'SecDebugLogLevel': SecDebugLogLevel,
                             'SecAuditLogParts': SecAuditLogParts,
                             'SecAuditLogRelevantStatus': SecAuditLogRelevantStatus,
                             'SecAuditLogType': SecAuditLogType,
                             }

            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveModSecConfigurations(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                modsecurity = data['modsecurity_status']
                SecAuditEngine = data['SecAuditEngine']
                SecRuleEngine = data['SecRuleEngine']
                SecDebugLogLevel = data['SecDebugLogLevel']
                SecAuditLogParts = data['SecAuditLogParts']
                SecAuditLogRelevantStatus = data['SecAuditLogRelevantStatus']
                SecAuditLogType = data['SecAuditLogType']

                if modsecurity == True:
                    modsecurity = "modsecurity  on"
                else:
                    modsecurity = "modsecurity  off"

                if SecAuditEngine == True:
                    SecAuditEngine = "SecAuditEngine on"
                else:
                    SecAuditEngine = "SecAuditEngine off"

                if SecRuleEngine == True:
                    SecRuleEngine = "SecRuleEngine On"
                else:
                    SecRuleEngine = "SecRuleEngine off"

                SecDebugLogLevel = "SecDebugLogLevel " + str(SecDebugLogLevel)
                SecAuditLogParts = "SecAuditLogParts " + str(SecAuditLogParts)
                SecAuditLogRelevantStatus = "SecAuditLogRelevantStatus " + SecAuditLogRelevantStatus
                SecAuditLogType = "SecAuditLogType " + SecAuditLogType

                ## writing data temporary to file


                tempConfigPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                confPath = open(tempConfigPath, "w")

                confPath.writelines(modsecurity + "\n")
                confPath.writelines(SecAuditEngine + "\n")
                confPath.writelines(SecRuleEngine + "\n")
                confPath.writelines(SecDebugLogLevel + "\n")
                confPath.writelines(SecAuditLogParts + "\n")
                confPath.writelines(SecAuditLogRelevantStatus + "\n")
                confPath.writelines(SecAuditLogType + "\n")

                confPath.close()

                ## save configuration data

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " saveModSecConfigs --tempConfigPath " + tempConfigPath

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'saveStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            else:
                SecAuditEngine = data['SecAuditEngine']
                SecRuleEngine = data['SecRuleEngine']
                SecDebugLogLevel = data['SecDebugLogLevel']
                SecAuditLogParts = data['SecAuditLogParts']
                SecAuditLogRelevantStatus = data['SecAuditLogRelevantStatus']
                SecAuditLogType = data['SecAuditLogType']

                if SecAuditEngine == True:
                    SecAuditEngine = "SecAuditEngine on"
                else:
                    SecAuditEngine = "SecAuditEngine off"

                if SecRuleEngine == True:
                    SecRuleEngine = "SecRuleEngine On"
                else:
                    SecRuleEngine = "SecRuleEngine off"

                SecDebugLogLevel = "SecDebugLogLevel " + str(SecDebugLogLevel)
                SecAuditLogParts = "SecAuditLogParts " + str(SecAuditLogParts)
                SecAuditLogRelevantStatus = "SecAuditLogRelevantStatus " + SecAuditLogRelevantStatus
                SecAuditLogType = "SecAuditLogType " + SecAuditLogType

                ## writing data temporary to file


                tempConfigPath = "/home/cyberpanel/" + str(randint(1000, 9999))

                confPath = open(tempConfigPath, "w")

                confPath.writelines(SecAuditEngine + "\n")
                confPath.writelines(SecRuleEngine + "\n")
                confPath.writelines(SecDebugLogLevel + "\n")
                confPath.writelines(SecAuditLogParts + "\n")
                confPath.writelines(SecAuditLogRelevantStatus + "\n")
                confPath.writelines(SecAuditLogType + "\n")

                confPath.close()

                ## save configuration data

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

                execPath = execPath + " saveModSecConfigs --tempConfigPath " + tempConfigPath

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'saveStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'saveStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def modSecRules(self, request = None, userID = None):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).split('\n')

            modSecInstalled = 0

            for items in httpdConfig:
                if items.find('module mod_security') > -1:
                    modSecInstalled = 1
                    break
        else:
            modSecInstalled = 1

        proc = httpProc(request, 'firewall/modSecurityRules.html',
                        {'modSecInstalled': modSecInstalled}, 'admin')
        return proc.render()

    def fetchModSecRules(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

                command = "sudo cat " + confPath
                httpdConfig = ProcessUtilities.outputExecutioner(command).split('\n')

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break

                rulesPath = os.path.join(virtualHostUtilities.Server_root + "/conf/modsec/rules.conf")

                if modSecInstalled:
                    command = "sudo cat " + rulesPath
                    currentModSecRules = ProcessUtilities.outputExecutioner(command)

                    final_dic = {'modSecInstalled': 1,
                                 'currentModSecRules': currentModSecRules}

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'modSecInstalled': 0}

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
            else:
                rulesPath = os.path.join(virtualHostUtilities.Server_root + "/conf/rules.conf")

                command = "sudo cat " + rulesPath
                currentModSecRules = ProcessUtilities.outputExecutioner(command)

                final_dic = {'modSecInstalled': 1,
                             'currentModSecRules': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'modSecInstalled': 0,
                         'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def saveModSecRules(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            newModSecRules = data['modSecRules']

            ## writing data temporary to file

            rulesPath = open(modSec.tempRulesFile, "w")
            rulesPath.write(newModSecRules)
            rulesPath.close()

            ## save configuration data

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
            execPath = execPath + " saveModSecRules"
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def modSecRulesPacks(self, request = None, userID = None):
        if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

            confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).split('\n')

            modSecInstalled = 0

            for items in httpdConfig:
                if items.find('module mod_security') > -1:
                    modSecInstalled = 1
                    break
        else:
            modSecInstalled = 1

        proc = httpProc(request, 'firewall/modSecurityRulesPacks.html',
                        {'modSecInstalled': modSecInstalled}, 'admin')
        return proc.render()

    def getOWASPAndComodoStatus(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
                confPath = os.path.join(virtualHostUtilities.Server_root, "conf/httpd_config.conf")

                command = "sudo cat " + confPath
                httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

                modSecInstalled = 0

                for items in httpdConfig:
                    if items.find('module mod_security') > -1:
                        modSecInstalled = 1
                        break

                comodoInstalled = 0
                owaspInstalled = 0

                if modSecInstalled:
                    command = "sudo cat " + confPath
                    httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

                    for items in httpdConfig:
                        # Check for Comodo rules
                        if items.find('modsec/comodo') > -1:
                            comodoInstalled = 1
                        # Check for OWASP rules - improved detection
                        elif items.find('modsec/owasp') > -1 or items.find('owasp-modsecurity-crs') > -1:
                            owaspInstalled = 1

                        if owaspInstalled == 1 and comodoInstalled == 1:
                            break

                    # Check rules.conf and other OWASP CRS locations
                    if owaspInstalled == 0:
                        rulesConfPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/rules.conf")
                        if os.path.exists(rulesConfPath):
                            try:
                                command = "sudo cat " + rulesConfPath
                                rulesConfig = ProcessUtilities.outputExecutioner(command).splitlines()
                                for items in rulesConfig:
                                    # Check for OWASP includes in rules.conf (case-insensitive)
                                    if ('owasp' in items.lower() or 'crs-setup' in items.lower()) and \
                                       ('include' in items.lower() or 'modsecurity_rules_file' in items.lower()):
                                        owaspInstalled = 1
                                        break
                            except:
                                pass

                    if owaspInstalled == 0:
                        owaspPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-4.18.0")
                        if os.path.exists(owaspPath) and os.path.exists(os.path.join(owaspPath, "owasp-master.conf")):
                            owaspInstalled = 1

                    if owaspInstalled == 0:
                        owaspMasterConf = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf")
                        if os.path.exists(owaspMasterConf):
                            try:
                                command = "sudo cat " + owaspMasterConf
                                owaspConfig = ProcessUtilities.outputExecutioner(command).splitlines()
                                for items in owaspConfig:
                                    if items.strip() and not items.strip().startswith('#') and 'include' in items.lower():
                                        owaspInstalled = 1
                                        break
                            except Exception:
                                pass

                    if owaspInstalled == 0:
                        owaspRulesDir = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/owasp-modsecurity-crs-3.0-master/rules")
                        if os.path.exists(owaspRulesDir):
                            try:
                                command = "sudo ls " + owaspRulesDir + " | grep -c '.conf'"
                                output = ProcessUtilities.outputExecutioner(command).strip()
                                if output.isdigit() and int(output) > 0:
                                    for items in httpdConfig:
                                        if 'owasp-modsecurity-crs' in items.lower() or 'owasp-master.conf' in items.lower():
                                            owaspInstalled = 1
                                            break
                            except Exception:
                                pass

                    if comodoInstalled == 0:
                        comodoPath = os.path.join(virtualHostUtilities.Server_root, "conf/modsec/comodo")
                        if os.path.exists(comodoPath) and os.path.exists(os.path.join(comodoPath, "modsecurity.conf")):
                            comodoInstalled = 1

                    final_dic = {
                        'modSecInstalled': 1,
                        'owaspInstalled': owaspInstalled,
                        'comodoInstalled': comodoInstalled
                    }

                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                else:
                    final_dic = {'modSecInstalled': 0}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)

            else:
                comodoInstalled = 0
                owaspInstalled = 0

                try:
                    command = 'sudo ls /usr/local/lsws/conf/comodo_litespeed/'
                    output = ProcessUtilities.outputExecutioner(command)

                    if output.find('No such') > -1:
                        comodoInstalled = 0
                    else:
                        comodoInstalled = 1

                except subprocess.CalledProcessError:
                    pass

                # Check multiple locations for OWASP in LiteSpeed Enterprise
                try:
                    command = 'cat /usr/local/lsws/conf/modsec.conf'
                    output = ProcessUtilities.outputExecutioner(command)
                    if output.find('modsec/owasp') > -1:
                        owaspInstalled = 1
                except:
                    pass

                # Also check owasp-master.conf for LSWS Enterprise
                if owaspInstalled == 0:
                    owaspMasterConf = '/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf'
                    if os.path.exists(owaspMasterConf):
                        try:
                            command = "cat " + owaspMasterConf
                            owaspConfig = ProcessUtilities.outputExecutioner(command).splitlines()
                            for items in owaspConfig:
                                if items.strip() and not items.strip().startswith('#') and 'include' in items.lower():
                                    owaspInstalled = 1
                                    break
                        except:
                            pass

                final_dic = {
                    'modSecInstalled': 1,
                    'owaspInstalled': owaspInstalled,
                    'comodoInstalled': comodoInstalled
                }
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'modSecInstalled': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installModSecRulesPack(self, userID = None, data = None):
        try:

            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            packName = data['packName']

            if ProcessUtilities.decideServer() == ProcessUtilities.OLS:

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " " + packName

                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'installStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'installStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
            else:
                # if packName == 'disableOWASP' or packName == 'installOWASP':
                #     final_json = json.dumps({'installStatus': 0, 'error_message': "OWASP will be available later.", })
                #     return HttpResponse(final_json)

                execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"
                execPath = execPath + " " + packName
                output = ProcessUtilities.outputExecutioner(execPath)

                if output.find("1,None") > -1:
                    data_ret = {'installStatus': 1, 'error_message': "None"}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)
                else:
                    data_ret = {'installStatus': 0, 'error_message': output}
                    json_data = json.dumps(data_ret)
                    return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'installStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def getRulesFiles(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            packName = data['packName']

            confPath = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')

            command = "sudo cat " + confPath
            httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()

            json_data = "["
            checker = 0
            counter = 0

            for items in httpdConfig:

                if items.find('modsec/' + packName) > -1:
                    counter = counter + 1
                    if items[0] == '#':
                        status = False
                    else:
                        status = True

                    fileName = items.lstrip('#')
                    fileName = fileName.split('/')[-1]

                    dic = {
                        'id': counter,
                        'fileName': fileName,
                        'packName': packName,
                        'status': status,

                    }

                    if checker == 0:
                        json_data = json_data + json.dumps(dic)
                        checker = 1
                    else:
                        json_data = json_data + ',' + json.dumps(dic)

            json_data = json_data + ']'
            final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            return HttpResponse(final_json)

            # if ProcessUtilities.decideServer() == ProcessUtilities.OLS:
            #     confPath = os.path.join('/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf')
            #
            #     command = "sudo cat " + confPath
            #     httpdConfig = ProcessUtilities.outputExecutioner(command).splitlines()
            #
            #     json_data = "["
            #     checker = 0
            #     counter = 0
            #
            #     for items in httpdConfig:
            #
            #         if items.find('modsec/' + packName) > -1:
            #             counter = counter + 1
            #             if items[0] == '#':
            #                 status = False
            #             else:
            #                 status = True
            #
            #             fileName = items.lstrip('#')
            #             fileName = fileName.split('/')[-1]
            #
            #             dic = {
            #                 'id': counter,
            #                 'fileName': fileName,
            #                 'packName': packName,
            #                 'status': status,
            #
            #             }
            #
            #             if checker == 0:
            #                 json_data = json_data + json.dumps(dic)
            #                 checker = 1
            #             else:
            #                 json_data = json_data + ',' + json.dumps(dic)
            #
            #     json_data = json_data + ']'
            #     final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            #     return HttpResponse(final_json)
            # else:
            #
            #     command = 'cat /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/owasp-master.conf'
            #     files = ProcessUtilities.outputExecutioner(command).splitlines()
            #
            #     json_data = "["
            #
            #     counter = 0
            #     checker = 0
            #     for fileName in files:
            #
            #         if fileName == 'categories.conf':
            #             continue
            #
            #         if fileName.endswith('bak'):
            #             status = 0
            #             fileName = fileName.rstrip('.bak')
            #         elif fileName.endswith('conf'):
            #             status = 1
            #         else:
            #             continue
            #
            #         dic = {
            #             'id': counter,
            #             'fileName': fileName,
            #             'packName': packName,
            #             'status': status,
            #
            #         }
            #
            #         counter = counter + 1
            #
            #         if checker == 0:
            #             json_data = json_data + json.dumps(dic)
            #             checker = 1
            #         else:
            #             json_data = json_data + ',' + json.dumps(dic)
            #
            #     json_data = json_data + ']'
            #     final_json = json.dumps({'fetchStatus': 1, 'error_message': "None", "data": json_data})
            #     return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def enableDisableRuleFile(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('saveStatus', 0)

            packName = data['packName']
            fileName = data['fileName']
            currentStatus = data['status']

            if currentStatus == True:
                functionName = 'disableRuleFile'
            else:
                functionName = 'enableRuleFile'

            execPath = "/usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/modSec.py"

            execPath = execPath + " " + functionName + ' --packName ' + packName + ' --fileName "%s"' % (fileName)

            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {'saveStatus': 1, 'error_message': "None"}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'saveStatus': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            data_ret = {'saveStatus': 0, 'error_message': str(msg)}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

    def csf(self):
        csfInstalled = 1
        try:
            command = 'csf -h'
            output = ProcessUtilities.outputExecutioner(command)
            if output.find("command not found") > -1:
                csfInstalled = 0
        except subprocess.CalledProcessError:
            csfInstalled = 0

        proc = httpProc(self.request, 'firewall/csf.html',
                        {'csfInstalled': csfInstalled}, 'admin')
        return proc.render()

    def installCSF(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)


            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " installCSF"

            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(2)

            data_ret = {"installStatus": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'installStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def installStatusCSF(self):
        try:
            userID = self.request.session['userID']

            installStatus = ProcessUtilities.outputExecutioner("sudo cat " + CSF.installLogPath)

            if installStatus.find("[200]")>-1:

                command = 'sudo rm -f ' + CSF.installLogPath
                ProcessUtilities.executioner(command)

                final_json = json.dumps({
                                         'error_message': "None",
                                         'requestStatus': installStatus,
                                         'abort':1,
                                         'installed': 1,
                                         })
                return HttpResponse(final_json)
            elif installStatus.find("[404]") > -1:
                command = 'sudo rm -f ' + CSF.installLogPath
                ProcessUtilities.executioner(command)
                final_json = json.dumps({
                                         'abort':1,
                                         'installed':0,
                                         'error_message': "None",
                                         'requestStatus': installStatus,
                                         })
                return HttpResponse(final_json)

            else:
                final_json = json.dumps({
                                         'abort':0,
                                         'error_message': "None",
                                         'requestStatus': installStatus,
                                         })
                return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'abort':1, 'installed':0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def removeCSF(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('installStatus', 0)

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " removeCSF"
            ProcessUtilities.popenExecutioner(execPath)

            time.sleep(2)

            data_ret = {"installStatus": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'installStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def fetchCSFSettings(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('fetchStatus', 0)

            currentSettings = CSF.fetchCSFSettings()


            data_ret = {"fetchStatus": 1, 'testingMode' : currentSettings['TESTING'],
                        'tcpIN' : currentSettings['tcpIN'],
                        'tcpOUT': currentSettings['tcpOUT'],
                        'udpIN': currentSettings['udpIN'],
                        'udpOUT': currentSettings['udpOUT'],
                        'firewallStatus': currentSettings['firewallStatus']
                        }
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'fetchStatus': 0, 'error_message': 'CSF is not installed.'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def changeStatus(self):
        try:
            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            controller = data['controller']
            status = data['status']

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " changeStatus --controller " + controller + " --status " + status
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {"status": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def modifyPorts(self, data = None):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            protocol = data['protocol']
            ports = data['ports']

            portsPath = '/home/cyberpanel/' + str(randint(1000, 9999))

            if os.path.exists(portsPath):
                os.remove(portsPath)

            writeToFile = open(portsPath, 'w')
            writeToFile.write(ports)
            writeToFile.close()

            command = 'chmod 600 %s' % (portsPath)
            ProcessUtilities.executioner(command)

            execPath = "sudo /usr/local/CyberCP/bin/python " + virtualHostUtilities.cyberPanel + "/plogical/csf.py"
            execPath = execPath + " modifyPorts --protocol " + protocol + " --ports " + portsPath
            output = ProcessUtilities.outputExecutioner(execPath)

            if output.find("1,None") > -1:
                data_ret = {"status": 1}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)
            else:
                data_ret = {'status': 0, 'error_message': output}
                json_data = json.dumps(data_ret)
                return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def modifyIPs(self):
        try:

            userID = self.request.session['userID']
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson()

            data = json.loads(self.request.body)

            mode = data['mode']
            ipAddress = data['ipAddress']

            if mode == 'allowIP':
                CSF.allowIP(ipAddress)
            elif mode == 'blockIP':
                CSF.blockIP(ipAddress)

            data_ret = {"status": 1}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def imunify(self):
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        fullAddress = '%s:%s' % (ipAddress, ProcessUtilities.fetchCurrentPort())

        data = {}
        data['ipAddress'] = fullAddress

        data['CL'] = 1

        # Auto-fix PHP-FPM issues when accessing Imunify360 page
        try:
            from plogical import upgrade
            logging.CyberCPLogFileWriter.writeToFile("Auto-fixing PHP-FPM pool configurations for Imunify360 compatibility...")
            fix_result = upgrade.Upgrade.CreateMissingPoolsforFPM()
            if fix_result == 0:
                logging.CyberCPLogFileWriter.writeToFile("PHP-FPM pool configurations auto-fixed successfully")
            else:
                logging.CyberCPLogFileWriter.writeToFile("Warning: PHP-FPM auto-fix had issues")
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in auto-fix for Imunify360: {str(e)}")

        if os.path.exists(FirewallManager.imunifyPath):
            data['imunify'] = 1
        else:
            data['imunify'] = 0

        if data['CL'] == 0:
            proc = httpProc(self.request, 'firewall/notAvailable.html',
                            data, 'admin')
            return proc.render()
        elif data['imunify'] == 0:
            proc = httpProc(self.request, 'firewall/notAvailable.html',
                            data, 'admin')
            return proc.render()
        else:
            proc = httpProc(self.request, 'firewall/imunify.html',
                            data, 'admin')
            return proc.render()

    def submitinstallImunify(self):
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

            data = json.loads(self.request.body)

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
            execPath = execPath + " --function submitinstallImunify --key %s" % (data['key'])
            ProcessUtilities.popenExecutioner(execPath)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)

    def imunifyAV(self):
        ipFile = "/etc/cyberpanel/machineIP"
        f = open(ipFile)
        ipData = f.read()
        ipAddress = ipData.split('\n', 1)[0]

        fullAddress = '%s:%s' % (ipAddress, ProcessUtilities.fetchCurrentPort())

        data = {}
        data['ipAddress'] = fullAddress

        # Auto-fix PHP-FPM issues when accessing ImunifyAV page
        try:
            from plogical import upgrade
            logging.CyberCPLogFileWriter.writeToFile("Auto-fixing PHP-FPM pool configurations for ImunifyAV compatibility...")
            fix_result = upgrade.Upgrade.CreateMissingPoolsforFPM()
            if fix_result == 0:
                logging.CyberCPLogFileWriter.writeToFile("PHP-FPM pool configurations auto-fixed successfully")
            else:
                logging.CyberCPLogFileWriter.writeToFile("Warning: PHP-FPM auto-fix had issues")
        except Exception as e:
            logging.CyberCPLogFileWriter.writeToFile(f"Error in auto-fix for ImunifyAV: {str(e)}")

        if os.path.exists(FirewallManager.imunifyAVPath):
            data['imunify'] = 1
            try:
                from plogical.imunify_integration import (
                    integration_conf_needs_repair,
                    repair_integration_conf,
                    ensure_clscripts_executable,
                    chmod_imunify_execute_files,
                    IMUNIFY_AV_UI,
                )
                ensure_clscripts_executable()
                if integration_conf_needs_repair():
                    repair_integration_conf()
                chmod_imunify_execute_files(IMUNIFY_AV_UI)
            except BaseException:
                pass
        else:
            data['imunify'] = 0

        if data['imunify'] == 0:
            proc = httpProc(self.request, 'firewall/notAvailableAV.html',
                            data, 'admin')
            return proc.render()
        else:
            proc = httpProc(self.request, 'firewall/imunifyAV.html',
                            data, 'admin')
            return proc.render()

    def submitinstallImunifyAV(self):
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

            execPath = "/usr/local/CyberCP/bin/python /usr/local/CyberCP/CLManager/CageFS.py"
            execPath = execPath + " --function submitinstallImunifyAV"
            ProcessUtilities.popenExecutioner(execPath)

            data_ret = {'status': 1, 'error_message': 'None'}
            json_data = json.dumps(data_ret)
            return HttpResponse(json_data)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.statusWriter(ServerStatusUtil.lswsInstallStatusPath, str(msg) + ' [404].', 1)



    def litespeed_ent_conf(self, request = None, userID = None):
        proc = httpProc(request, 'firewall/litespeed_ent_conf.html',
                        None, 'admin')
        return proc.render()

    def fetchlitespeed_Conf(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            file_path = "/usr/local/lsws/conf/pre_main_global.conf"

            if not os.path.exists(file_path):
                command = "touch /usr/local/lsws/conf/pre_main_global.conf"
                ProcessUtilities.executioner(command)


                command = f'cat {file_path}'

                currentModSecRules = ProcessUtilities.outputExecutioner(command)
                final_dic = {'status': 1,
                             'currentLitespeed_conf': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            else:
                command = f'cat {file_path}'

                currentModSecRules = ProcessUtilities.outputExecutioner(command)
                final_dic = {'status': 1,
                             'currentLitespeed_conf': currentModSecRules}

                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)


    def saveLitespeed_conf(self, userID = None, data = None):
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('modSecInstalled', 0)

            file_path = "/usr/local/lsws/conf/pre_main_global.conf"

            command = f'rm -f {file_path}'
            ProcessUtilities.executioner(command)

            currentLitespeed_conf = data['modSecRules']

            tempRulesPath = '/home/cyberpanel/pre_main_global.conf'

            WriteToFile = open(tempRulesPath, 'w')
            WriteToFile.write(currentLitespeed_conf)
            WriteToFile.close()

            command = f'mv {tempRulesPath} {file_path}'
            ProcessUtilities.executioner(command)

            command = f'chmod 644 {file_path} && chown lsadm:lsadm {file_path}'
            ProcessUtilities.executioner(command, None, True)


            command = f'cat {file_path}'

            currentModSecRules = ProcessUtilities.outputExecutioner(command)
            final_dic = {'status': 1,
                             'currentLitespeed_conf': currentModSecRules}

            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def getBannedIPs(self, userID=None, data=None):
        """
        Get list of banned IP addresses with optional pagination.
        data may contain: page (1-based), page_size (default 10).
        Returns: status 1, bannedIPs (array), total_count, page, page_size.
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadErrorJson('status', 0)

            active_banned_ips = []
            db_ips = set()  # IPs already added from DB (for merge with JSON)
            current_time = int(time.time())
            from django.db.utils import OperationalError, ProgrammingError

            for _migrate_attempt in (1, 2):
                try:
                    from firewall.models import BannedIP
                    from django.db.models import Q

                    banned_ips_queryset = BannedIP.objects.filter(
                        active=True
                    ).filter(
                        Q(expires__isnull=True) | Q(expires__gt=current_time)
                    ).order_by('-banned_on')

                    for banned_ip in banned_ips_queryset:
                        try:
                            ip_data = {
                                'id': banned_ip.id,
                                'ip': banned_ip.ip_address,
                                'reason': banned_ip.reason,
                                'duration': banned_ip.duration,
                                'banned_on': banned_ip.get_banned_on_display(),
                                'expires': banned_ip.get_expires_display(),
                                'active': not banned_ip.is_expired() and banned_ip.active
                            }
                            if ip_data['active']:
                                active_banned_ips.append(ip_data)
                                db_ips.add(banned_ip.ip_address)
                        except Exception as row_e:
                            import plogical.CyberCPLogFileWriter as _log
                            _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: skip row %s: %s' % (getattr(banned_ip, 'ip_address', '?'), str(row_e)))
                    break
                except (OperationalError, ProgrammingError) as e:
                    import plogical.CyberCPLogFileWriter as _log
                    _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: DB error (table may be missing). Error: %s' % str(e))
                    if _migrate_attempt == 1:
                        try:
                            from django.core.management import call_command
                            call_command('migrate', 'firewall', verbosity=0)
                            _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: ran migrate firewall, retrying.')
                        except Exception as migrate_err:
                            _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: migrate firewall failed: %s' % str(migrate_err))
                    else:
                        _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: DB read failed after retry, merging with JSON.')
                    if _migrate_attempt == 2:
                        break
                except Exception as e:
                    import plogical.CyberCPLogFileWriter as _log
                    _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: DB read failed, merging with JSON (%s)' % str(e))
                    break

            # If ORM returned nothing but we have the table, try raw SQL as fallback
            if not active_banned_ips:
                try:
                    from django.db import connection
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """SELECT id, ip_address, reason, duration, banned_on, expires
                               FROM firewall_bannedips WHERE active = 1
                               AND (expires IS NULL OR expires > %s)
                               ORDER BY banned_on DESC""",
                            [current_time]
                        )
                        for row in cursor.fetchall():
                            bid, ip_addr, reason_val, duration_val, banned_on_val, expires_val = row
                            if ip_addr in db_ips:
                                continue
                            from datetime import datetime
                            if banned_on_val:
                                banned_on_str = banned_on_val.strftime('%Y-%m-%d %H:%M:%S') if hasattr(banned_on_val, 'strftime') else str(banned_on_val)
                            else:
                                banned_on_str = 'N/A'
                            if expires_val is None:
                                expires_str = 'Never'
                            else:
                                try:
                                    expires_str = datetime.fromtimestamp(expires_val).strftime('%Y-%m-%d %H:%M:%S')
                                except Exception:
                                    expires_str = 'Never'
                            active_banned_ips.append({
                                'id': bid,
                                'ip': ip_addr or '',
                                'reason': reason_val or '',
                                'duration': duration_val or 'permanent',
                                'banned_on': banned_on_str,
                                'expires': expires_str,
                                'active': True
                            })
                            db_ips.add(ip_addr)
                except Exception as raw_e:
                    import plogical.CyberCPLogFileWriter as _log
                    _log.CyberCPLogFileWriter.writeToFile('getBannedIPs: raw fallback failed: %s' % str(raw_e))

            # Always load JSON store and merge: show bans from both DB and JSON (e.g. bans from base/SSH logs)
            banned_ips, _ = self._load_banned_ips_store()
            for b in banned_ips:
                if not b.get('active', True):
                    continue
                ip_val = (b.get('ip') or '').strip()
                if ip_val in db_ips:
                    continue
                exp = b.get('expires')
                if exp == 'Never' or exp is None:
                    expires_display = 'Never'
                elif isinstance(exp, (int, float)):
                    from datetime import datetime
                    try:
                        expires_display = datetime.fromtimestamp(exp).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        expires_display = 'Never'
                else:
                    expires_display = str(exp)
                banned_on = b.get('banned_on')
                if isinstance(banned_on, (int, float)):
                    from datetime import datetime
                    try:
                        banned_on = datetime.fromtimestamp(banned_on).strftime('%Y-%m-%d %H:%M:%S')
                    except Exception:
                        banned_on = 'N/A'
                else:
                    banned_on = str(banned_on) if banned_on else 'N/A'
                active_banned_ips.append({
                    'id': b.get('id'),
                    'ip': ip_val,
                    'reason': b.get('reason', ''),
                    'duration': b.get('duration', 'permanent'),
                    'banned_on': banned_on,
                    'expires': expires_display,
                    'active': True
                })

            # Auto Ban Security Alerts: show log-only / plugin-visible bans on same list as firewall UI
            self._merge_autoban_security_alerts_logs(active_banned_ips, current_time)

            # Optional server-side search: filter by IP or reason (case-insensitive substring)
            # Normalize: strip query and compare against stripped IP/reason so "1.2.3.4" matches stored "  1.2.3.4  "
            search_q = (data.get('search') or data.get('q') or '').strip() if data else ''
            if search_q:
                search_lower = search_q.lower()
                def matches(b):
                    ip = (b.get('ip') or '').strip().lower()
                    reason = (b.get('reason') or '').strip().lower()
                    return search_lower in ip or search_lower in reason
                active_banned_ips = [b for b in active_banned_ips if matches(b)]

            total_count = len(active_banned_ips)
            page = 1
            page_size = 10
            if data:
                try:
                    page = max(1, int(data.get('page', 1)))
                except (TypeError, ValueError):
                    pass
                try:
                    page_size = max(1, min(100, int(data.get('page_size', 10))))
                except (TypeError, ValueError):
                    pass

            start = (page - 1) * page_size
            end = start + page_size
            paged_list = active_banned_ips[start:end]

            final_dic = {
                'status': 1,
                'bannedIPs': paged_list,
                'total_count': total_count,
                'page': page,
                'page_size': page_size
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

        except BaseException as msg:
            import plogical.CyberCPLogFileWriter as logging
            logging.CyberCPLogFileWriter.writeToFile('Error in getBannedIPs: %s' % str(msg))
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

    def addBannedIP(self, userID=None, data=None):
        """
        Add a banned IP address. Uses database (BannedIP model) as primary storage;
        JSON file is used only when the model is unavailable (fallback). Export/Import use JSON format.
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                final_dic = {'status': 0, 'error_message': 'You are not authorized to access this resource.', 'error': 'You are not authorized to access this resource.'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json', status=403)

            ip = data.get('ip', '').strip()
            reason = data.get('reason', '').strip()
            duration = (data.get('duration') or '24h').strip().lower()

            if not ip or not reason:
                final_dic = {'status': 0, 'error_message': 'IP address and reason are required', 'error': 'IP address and reason are required'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')

            # Validate IP address format
            import ipaddress
            try:
                ipaddress.ip_address(ip.split('/')[0])  # Handle CIDR notation
            except ValueError:
                final_dic = {'status': 0, 'error_message': 'Invalid IP address format', 'error': 'Invalid IP address format'}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')

            try:
                from plogical.sshSecurityWhitelistUtilities import SSHSecurityWhitelistUtilities
                if SSHSecurityWhitelistUtilities.is_whitelisted(ip):
                    final_dic = {
                        'status': 0,
                        'error_message': 'This IP is on the SSH Security trusted list and cannot be banned. Remove it from Trusted IPs first.',
                        'error': 'SSH Security whitelist',
                    }
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')
            except Exception:
                pass

            current_time = time.time()
            duration_map = {
                '1h': 3600,
                '24h': 86400,
                '7d': 604800,
                '30d': 2592000
            }
            if duration == 'permanent':
                expires_ts = None  # Never expires
            else:
                duration_seconds = duration_map.get(duration, 86400)
                expires_ts = int(current_time) + duration_seconds

            # Prefer database (BannedIP model) for primary storage
            try:
                from firewall.models import BannedIP
            except Exception as e:
                BannedIP = None
                logging.CyberCPLogFileWriter.writeToFile('addBannedIP: BannedIP model unavailable, using JSON fallback: %s' % str(e))

            if BannedIP is not None:
                # Primary path: save to database
                existing = BannedIP.objects.filter(ip_address=ip, active=True).first()
                if existing:
                    # IP already banned: close any active connections from this IP so they cannot keep trying
                    try:
                        FirewallUtilities.closeConnectionsFromIP(ip)
                    except Exception as close_err:
                        logging.CyberCPLogFileWriter.writeToFile('addBannedIP: closeConnectionsFromIP %s: %s' % (ip, str(close_err)))
                    msg = 'IP address %s was already banned; any active connections from this IP have been terminated.' % ip
                    final_dic = {'status': 1, 'message': msg}
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')
                try:
                    new_ban = BannedIP(
                        ip_address=ip,
                        reason=reason,
                        duration=duration,
                        expires=expires_ts,
                        active=True
                    )
                    new_ban.save()
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile('addBannedIP: failed to save to DB: %s' % str(e))
                    final_dic = {'status': 0, 'error_message': 'Failed to save banned IP to database: %s' % str(e), 'error': str(e)}
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')
            else:
                # Fallback: JSON store (only when DB unavailable)
                banned_ips, _ = self._load_banned_ips_store()
                for banned_ip in banned_ips:
                    if banned_ip.get('ip') == ip and banned_ip.get('active', True):
                        # IP already banned: close any active connections from this IP so they cannot keep trying
                        try:
                            FirewallUtilities.closeConnectionsFromIP(ip)
                        except Exception as close_err:
                            logging.CyberCPLogFileWriter.writeToFile('addBannedIP: closeConnectionsFromIP %s: %s' % (ip, str(close_err)))
                        msg = 'IP address %s was already banned; any active connections from this IP have been terminated.' % ip
                        final_dic = {'status': 1, 'message': msg}
                        return HttpResponse(json.dumps(final_dic), content_type='application/json')
                new_banned_ip = {
                    'id': int(current_time),
                    'ip': ip,
                    'reason': reason,
                    'duration': duration,
                    'banned_on': current_time,
                    'expires': 'Never' if expires_ts is None else expires_ts,
                    'active': True
                }
                banned_ips.append(new_banned_ip)
                try:
                    self._save_banned_ips_store(banned_ips)
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile('addBannedIP: failed to save JSON store: %s' % str(e))
                    final_dic = {'status': 0, 'error_message': 'Failed to save banned IP: %s' % str(e), 'error': str(e)}
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')

            # Apply firewall rule (same for DB and JSON path)
            try:
                block_ok, block_msg = FirewallUtilities.blockIP(ip, reason)
                if not block_ok:
                    if BannedIP is not None:
                        try:
                            BannedIP.objects.filter(ip_address=ip, active=True).delete()
                        except Exception:
                            pass
                    else:
                        banned_ips_rollback = [b for b in banned_ips if b.get('ip') != ip or not b.get('active', True)]
                        if len(banned_ips_rollback) < len(banned_ips):
                            self._save_banned_ips_store(banned_ips_rollback)
                    logging.CyberCPLogFileWriter.writeToFile('Failed to add firewalld rule for %s: %s' % (ip, block_msg))
                    err_msg = block_msg or 'Failed to add firewall rule'
                    final_dic = {'status': 0, 'error_message': err_msg, 'error': err_msg}
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')
                logging.CyberCPLogFileWriter.writeToFile('Banned IP %s with reason: %s' % (ip, reason))
            except Exception as e:
                if BannedIP is not None:
                    try:
                        BannedIP.objects.filter(ip_address=ip, active=True).delete()
                    except Exception:
                        pass
                else:
                    try:
                        banned_ips_rollback = [b for b in banned_ips if b.get('ip') != ip or not b.get('active', True)]
                        if len(banned_ips_rollback) < len(banned_ips):
                            self._save_banned_ips_store(banned_ips_rollback)
                    except Exception:
                        pass
                logging.CyberCPLogFileWriter.writeToFile('Failed to add firewalld rule for %s: %s' % (ip, str(e)))
                err_msg = 'Firewall command failed: %s' % str(e)
                final_dic = {'status': 0, 'error_message': err_msg, 'error': err_msg}
                return HttpResponse(json.dumps(final_dic), content_type='application/json')

            final_dic = {'status': 1, 'message': 'IP address %s has been banned successfully' % ip}
            return HttpResponse(json.dumps(final_dic), content_type='application/json')

        except BaseException as msg:
            err_msg = str(msg)
            final_dic = {'status': 0, 'error_message': err_msg, 'error': err_msg}
            return HttpResponse(json.dumps(final_dic), content_type='application/json')

    def removeBannedIP(self, userID=None, data=None):
        """
        Remove/unban an IP address.
        Supports both BannedIP database model and JSON file storage.
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            banned_ip_id = data.get('id')
            if isinstance(banned_ip_id, str) and banned_ip_id.startswith('ablog-'):
                final_dic = {'status': 0, 'error_message': 'Use the autoBan Security Alerts plugin.'}; return HttpResponse(json.dumps(final_dic), content_type='application/json')

            requested_ip = (data.get('ip') or '').strip()
            ip_to_unban = None

            try:
                if isinstance(banned_ip_id, str) and banned_ip_id.isdigit():
                    banned_ip_id = int(banned_ip_id)
                elif isinstance(banned_ip_id, float):
                    banned_ip_id = int(banned_ip_id)
            except Exception:
                pass

            # Try database (BannedIP model) first - ids are typically small integers
            try:
                from firewall.models import BannedIP
            except Exception as e:
                BannedIP = None
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: BannedIP model import failed, using JSON fallback: {str(e)}')

            if BannedIP is not None:
                try:
                    banned_ip = None
                    if banned_ip_id not in (None, ''):
                        try:
                            banned_ip = BannedIP.objects.get(pk=banned_ip_id)
                        except BannedIP.DoesNotExist:
                            banned_ip = None
                    if banned_ip is None and requested_ip:
                        banned_ip = BannedIP.objects.filter(ip_address=requested_ip).first()
                    if banned_ip is None:
                        raise BannedIP.DoesNotExist()
                    ip_to_unban = banned_ip.ip_address
                    banned_ip.active = False
                    banned_ip.save()
                    # Remove firewalld rule using FirewallUtilities (runs with proper privileges)
                    try:
                        FirewallUtilities.unblockIP(ip_to_unban)
                    except Exception as e:
                        logging.CyberCPLogFileWriter.writeToFile(f'Warning removing firewalld rule: {str(e)}')
                    final_dic = {'status': 1, 'message': f'IP address {ip_to_unban} has been unbanned successfully'}
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')
                except BannedIP.DoesNotExist:
                    pass

            # Fall back to JSON file storage
            banned_ips, _ = self._load_banned_ips_store()

            # Find and update the banned IP
            ip_to_unban = None
            for banned_ip in banned_ips:
                id_match = banned_ip_id not in (None, '') and str(banned_ip.get('id')) == str(banned_ip_id)
                ip_match = requested_ip and str(banned_ip.get('ip', '')).strip() == requested_ip
                if id_match or ip_match:
                    banned_ip['active'] = False
                    banned_ip['unbanned_on'] = time.time()
                    ip_to_unban = banned_ip['ip']
                    break

            if not ip_to_unban:
                final_dic = {'status': 0, 'error_message': 'Banned IP not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json, content_type='application/json')

            # Save updated banned IPs
            self._save_banned_ips_store(banned_ips)

            # Remove firewalld rule using FirewallUtilities (runs with proper privileges)
            try:
                FirewallUtilities.unblockIP(ip_to_unban)
                logging.CyberCPLogFileWriter.writeToFile(f'Unbanned IP {ip_to_unban}')
            except Exception as e:
                logging.CyberCPLogFileWriter.writeToFile(f'Warning removing firewalld rule for {ip_to_unban}: {str(e)}')

            final_dic = {'status': 1, 'message': f'IP address {ip_to_unban} has been unbanned successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

    def deleteBannedIP(self, userID=None, data=None):
        """
        Permanently delete a banned IP record.
        Supports both BannedIP database model and JSON file storage.
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            banned_ip_id = data.get('id')
            if isinstance(banned_ip_id, str) and banned_ip_id.startswith('ablog-'):
                final_dic = {'status': 0, 'error_message': 'Use the autoBan Security Alerts plugin.'}; return HttpResponse(json.dumps(final_dic), content_type='application/json')

            requested_ip = (data.get('ip') or '').strip()

            try:
                if isinstance(banned_ip_id, str) and banned_ip_id.isdigit():
                    banned_ip_id = int(banned_ip_id)
                elif isinstance(banned_ip_id, float):
                    banned_ip_id = int(banned_ip_id)
            except Exception:
                pass

            # Try database (BannedIP model) first
            try:
                from firewall.models import BannedIP
            except Exception as e:
                BannedIP = None
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: BannedIP model import failed, using JSON fallback: {str(e)}')

            if BannedIP is not None:
                try:
                    banned_ip = None
                    if banned_ip_id not in (None, ''):
                        try:
                            banned_ip = BannedIP.objects.get(pk=banned_ip_id)
                        except BannedIP.DoesNotExist:
                            banned_ip = None
                    if banned_ip is None and requested_ip:
                        banned_ip = BannedIP.objects.filter(ip_address=requested_ip).first()
                    if banned_ip is None:
                        raise BannedIP.DoesNotExist()
                    ip_to_delete = banned_ip.ip_address
                    banned_ip.delete()
                    logging.CyberCPLogFileWriter.writeToFile(f'Deleted banned IP record for {ip_to_delete}')
                    final_dic = {'status': 1, 'message': f'Banned IP record for {ip_to_delete} has been deleted successfully'}
                    return HttpResponse(json.dumps(final_dic), content_type='application/json')
                except BannedIP.DoesNotExist:
                    pass

            # Fall back to JSON file storage
            banned_ips, _ = self._load_banned_ips_store()

            # Find and remove the banned IP
            ip_to_delete = None
            updated_banned_ips = []
            for banned_ip in banned_ips:
                id_match = banned_ip_id not in (None, '') and str(banned_ip.get('id')) == str(banned_ip_id)
                ip_match = requested_ip and str(banned_ip.get('ip', '')).strip() == requested_ip
                if id_match or ip_match:
                    ip_to_delete = banned_ip['ip']
                else:
                    updated_banned_ips.append(banned_ip)

            if not ip_to_delete:
                final_dic = {'status': 0, 'error_message': 'Banned IP record not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json, content_type='application/json')

            # Save updated banned IPs
            self._save_banned_ips_store(updated_banned_ips)

            logging.CyberCPLogFileWriter.writeToFile(f'Deleted banned IP record for {ip_to_delete}')

            final_dic = {'status': 1, 'message': f'Banned IP record for {ip_to_delete} has been deleted successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

        except BaseException as msg:
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

    def modifyBannedIP(self, userID=None, data=None):
        """
        Modify an existing banned IP record (reason, duration).
        Supports both BannedIP database model and JSON file storage.
        """
        try:
            admin = Administrator.objects.get(pk=userID)
            if admin.acl.adminStatus != 1:
                return ACLManager.loadError()

            banned_ip_id = data.get('id')
            requested_ip = (data.get('ip') or '').strip()
            reason = data.get('reason', '').strip()
            duration = data.get('duration', '').strip()

            try:
                if isinstance(banned_ip_id, str) and banned_ip_id.isdigit():
                    banned_ip_id = int(banned_ip_id)
                elif isinstance(banned_ip_id, float):
                    banned_ip_id = int(banned_ip_id)
            except Exception:
                pass

            if banned_ip_id in (None, '') and not requested_ip:
                final_dic = {'status': 0, 'error_message': 'Banned IP ID or IP address is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json, content_type='application/json')

            if not reason:
                final_dic = {'status': 0, 'error_message': 'Reason is required'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json, content_type='application/json')

            # Try database (BannedIP model) first - ids are typically small integers
            try:
                from firewall.models import BannedIP
            except Exception as e:
                BannedIP = None
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: BannedIP model import failed, using JSON fallback: {str(e)}')

            if BannedIP is not None:
                try:
                    banned_ip = None
                    if banned_ip_id not in (None, ''):
                        try:
                            banned_ip = BannedIP.objects.get(pk=banned_ip_id)
                        except BannedIP.DoesNotExist:
                            banned_ip = None
                    if banned_ip is None and requested_ip:
                        banned_ip = BannedIP.objects.filter(ip_address=requested_ip).first()
                    if banned_ip is None:
                        raise BannedIP.DoesNotExist()
                    if not banned_ip.active:
                        final_dic = {'status': 0, 'error_message': 'Cannot modify an inactive/expired ban'}
                        final_json = json.dumps(final_dic)
                        return HttpResponse(final_json, content_type='application/json')

                    banned_ip.reason = reason
                    if duration:
                        banned_ip.duration = duration
                        duration_map = {
                            '1h': 3600,
                            '24h': 86400,
                            '7d': 604800,
                            '30d': 2592000,
                            'permanent': None
                        }
                        if duration == 'permanent':
                            banned_ip.expires = None
                        else:
                            duration_seconds = duration_map.get(duration, 86400)
                            banned_ip.expires = int(time.time()) + duration_seconds
                    banned_ip.save()

                    logging.CyberCPLogFileWriter.writeToFile(f'Modified banned IP {banned_ip.ip_address} (id={banned_ip_id})')
                    final_dic = {'status': 1, 'message': f'Banned IP {banned_ip.ip_address} has been updated successfully'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json, content_type='application/json')

                except BannedIP.DoesNotExist:
                    pass

            # Fall back to JSON file storage (ids are timestamps)
            banned_ips, _ = self._load_banned_ips_store()

            updated = False
            for banned_ip in banned_ips:
                id_match = banned_ip_id not in (None, '') and str(banned_ip.get('id')) == str(banned_ip_id)
                ip_match = requested_ip and str(banned_ip.get('ip', '')).strip() == requested_ip
                if (id_match or ip_match) and banned_ip.get('active', True):
                    banned_ip['reason'] = reason
                    if duration:
                        banned_ip['duration'] = duration
                        if duration == 'permanent':
                            banned_ip['expires'] = 'Never'
                        else:
                            duration_map = {
                                '1h': 3600,
                                '24h': 86400,
                                '7d': 604800,
                                '30d': 2592000
                            }
                            duration_seconds = duration_map.get(duration, 86400)
                            banned_ip['expires'] = time.time() + duration_seconds
                    updated = True
                    break

            if not updated:
                final_dic = {'status': 0, 'error_message': 'Banned IP record not found'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json, content_type='application/json')

            self._save_banned_ips_store(banned_ips)

            ip_addr = next((b.get('ip') for b in banned_ips if (str(b.get('id')) == str(banned_ip_id)) or (requested_ip and str(b.get('ip', '')).strip() == requested_ip)), 'unknown')
            logging.CyberCPLogFileWriter.writeToFile(f'Modified banned IP {ip_addr} (id={banned_ip_id}) in JSON')
            final_dic = {'status': 1, 'message': f'Banned IP {ip_addr} has been updated successfully'}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(f'Error in modifyBannedIP: {str(msg)}')
            final_dic = {'status': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json, content_type='application/json')

    def exportFirewallRules(self, userID=None):
        """
        Export all custom firewall rules. Format from POST body: { "format": "json" | "excel" }.
        JSON: application/json file. Excel: text/csv (opens in Excel).
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('exportStatus', 0)

            # Optional format from request body
            export_format = 'json'
            if getattr(self, 'request', None) and self.request.method == 'POST' and self.request.body:
                try:
                    body = self.request.body
                    if isinstance(body, bytes):
                        body = body.decode('utf-8')
                    data = json.loads(body) if body.strip() else {}
                    export_format = (data.get('format') or 'json').strip().lower()
                    if export_format not in ('json', 'excel'):
                        export_format = 'json'
                except Exception:
                    pass

            # Get all firewall rules (stable UI order)
            rules = FirewallRuleOrder.ordered_queryset()
            default_rules = ['CyberPanel Admin', 'SSHCustom']
            custom_rules = []
            for rule in rules:
                if rule.name not in default_rules:
                    custom_rules.append({
                        'name': rule.name,
                        'proto': rule.proto,
                        'port': rule.port,
                        'ipAddress': rule.ipAddress,
                        'sortOrder': rule.sortOrder
                    })

            logging.CyberCPLogFileWriter.writeToFile(f"Firewall rules exported successfully. Total rules: {len(custom_rules)}")

            if export_format == 'excel':
                import csv
                import io
                buf = io.StringIO()
                writer = csv.writer(buf)
                writer.writerow(['name', 'proto', 'port', 'ipAddress'])
                for r in custom_rules:
                    writer.writerow([r.get('name', ''), r.get('proto', ''), r.get('port', ''), r.get('ipAddress', '')])
                content = buf.getvalue()
                response = HttpResponse(content, content_type='text/csv; charset=utf-8')
                response['Content-Disposition'] = f'attachment; filename="firewall_rules_export_{int(time.time())}.csv"'
                return response

            export_data = {
                'version': '1.0',
                'exported_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_rules': len(custom_rules),
                'rules': custom_rules
            }
            json_content = json.dumps(export_data, indent=2)
            response = HttpResponse(json_content, content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename="firewall_rules_export_{int(time.time())}.json"'
            return response

        except BaseException as msg:
            final_dic = {'exportStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def importFirewallRules(self, userID=None, data=None):
        """
        Import firewall rules from a JSON file
        """
        try:
            currentACL = ACLManager.loadedACL(userID)

            if currentACL['admin'] == 1:
                pass
            else:
                return ACLManager.loadErrorJson('importStatus', 0)

            # Handle file upload
            if hasattr(self.request, 'FILES') and 'import_file' in self.request.FILES:
                import_file = self.request.FILES['import_file']
                raw = import_file.read().decode('utf-8')
                name = (import_file.name or '').lower()
                if name.endswith('.csv'):
                    import csv
                    import io
                    reader = csv.DictReader(io.StringIO(raw))
                    rules_list = []
                    for row in reader:
                        rules_list.append({
                            'name': str(row.get('name', '')).strip(),
                            'proto': str(row.get('proto', 'tcp')).strip().lower() or 'tcp',
                            'port': str(row.get('port', '')).strip(),
                            'ipAddress': str(row.get('ipAddress', '0.0.0.0/0')).strip() or '0.0.0.0/0'
                        })
                    import_data = {'rules': rules_list}
                else:
                    import_data = json.loads(raw)
            else:
                # Fallback to file path method
                import_file_path = data.get('import_file_path', '')
                
                if not import_file_path or not os.path.exists(import_file_path):
                    final_dic = {'importStatus': 0, 'error_message': 'Import file not found or invalid path'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                
                # Read and parse the import file
                with open(import_file_path, 'r') as f:
                    import_data = json.load(f)
            
            # Validate the import data structure
            if 'rules' not in import_data:
                final_dic = {'importStatus': 0, 'error_message': 'Invalid import file format. Missing rules array.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)
            
            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []
            
            # Default CyberPanel rules to exclude from import
            default_rules = ['CyberPanel Admin', 'SSHCustom']
            
            for rule_data in import_data['rules']:
                try:
                    # Skip default rules
                    if rule_data.get('name', '') in default_rules:
                        skipped_count += 1
                        continue
                    
                    # Check if rule already exists
                    existing_rule = FirewallRules.objects.filter(
                        name=rule_data['name'],
                        proto=rule_data['proto'],
                        port=rule_data['port'],
                        ipAddress=rule_data['ipAddress']
                    ).first()
                    
                    if existing_rule:
                        skipped_count += 1
                        continue
                    
                    # Add the rule to the system firewall
                    FirewallUtilities.addRule(
                        rule_data['proto'], 
                        rule_data['port'], 
                        rule_data['ipAddress']
                    )
                    
                    # Add the rule to the database
                    new_rule = FirewallRules(
                        name=rule_data['name'],
                        proto=rule_data['proto'],
                        port=rule_data['port'],
                        ipAddress=rule_data['ipAddress'],
                        sortOrder=FirewallRuleOrder.next_sort_order()
                    )
                    new_rule.save()
                    
                    imported_count += 1
                    
                except Exception as e:
                    error_count += 1
                    errors.append(f"Rule '{rule_data.get('name', 'Unknown')}': {str(e)}")
                    logging.CyberCPLogFileWriter.writeToFile(f"Error importing rule {rule_data.get('name', 'Unknown')}: {str(e)}")
            
            logging.CyberCPLogFileWriter.writeToFile(f"Firewall rules import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}")
            
            final_dic = {
                'importStatus': 1,
                'error_message': "None",
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'error_count': error_count,
                'errors': errors
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'importStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def exportBannedIPs(self, userID=None):
        """
        Export banned IPs to a JSON file
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                return ACLManager.loadErrorJson('exportStatus', 0)

            banned_records = []

            # Try database model first
            try:
                from firewall.models import BannedIP
            except Exception as e:
                BannedIP = None
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: BannedIP model import failed, using JSON fallback: {str(e)}')

            if BannedIP is not None:
                try:
                    for banned_ip in BannedIP.objects.all().order_by('-banned_on'):
                        banned_records.append({
                            'id': int(banned_ip.id),
                            'ip': str(banned_ip.ip_address or ''),
                            'reason': str(banned_ip.reason or ''),
                            'duration': str(banned_ip.duration or 'permanent'),
                            'banned_on': str(banned_ip.get_banned_on_display() or 'N/A'),
                            'expires': str(banned_ip.get_expires_display() or 'Never'),
                            'active': bool(banned_ip.active and not banned_ip.is_expired())
                        })
                except Exception as e:
                    logging.CyberCPLogFileWriter.writeToFile(f'Error exporting banned IPs from DB: {str(e)}')

            # If DB is unavailable/empty, fall back to JSON file
            if not banned_records:
                banned_ips, _ = self._load_banned_ips_store()

                for b in banned_ips:
                    banned_records.append({
                        'id': b.get('id'),
                        'ip': str(b.get('ip') or ''),
                        'reason': str(b.get('reason') or ''),
                        'duration': str(b.get('duration') or 'permanent'),
                        'banned_on': str(b.get('banned_on') if b.get('banned_on') is not None else 'N/A'),
                        'expires': str(b.get('expires') if b.get('expires') is not None else 'Never'),
                        'active': bool(b.get('active', True))
                    })

            export_data = {
                'version': '1.0',
                'exported_at': time.strftime('%Y-%m-%d %H:%M:%S'),
                'total_banned_ips': len(banned_records),
                'banned_ips': banned_records
            }

            json_content = json.dumps(export_data, indent=2)
            logging.CyberCPLogFileWriter.writeToFile(f"Banned IPs exported successfully. Total: {len(banned_records)}")

            response = HttpResponse(json_content, content_type='application/json')
            response['Content-Disposition'] = f'attachment; filename=\"banned_ips_export_{int(time.time())}.json\"'
            return response

        except BaseException as msg:
            final_dic = {'exportStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

    def importBannedIPs(self, userID=None, data=None):
        """
        Import banned IPs from a JSON file
        """
        try:
            currentACL = ACLManager.loadedACL(userID)
            if currentACL['admin'] != 1:
                return ACLManager.loadErrorJson('importStatus', 0)

            request_files = getattr(self.request, 'FILES', None)
            if request_files and 'import_file' in request_files:
                import_file = self.request.FILES['import_file']
                import_data = json.loads(import_file.read().decode('utf-8'))
            else:
                import_file_path = data.get('import_file_path', '') if data else ''
                if not import_file_path or not os.path.exists(import_file_path):
                    final_dic = {'importStatus': 0, 'error_message': 'Import file not found or invalid path'}
                    final_json = json.dumps(final_dic)
                    return HttpResponse(final_json)
                with open(import_file_path, 'r') as f:
                    import_data = json.load(f)

            if 'banned_ips' not in import_data or not isinstance(import_data.get('banned_ips'), list):
                final_dic = {'importStatus': 0, 'error_message': 'Invalid import file format. Missing banned_ips array.'}
                final_json = json.dumps(final_dic)
                return HttpResponse(final_json)

            imported_count = 0
            skipped_count = 0
            error_count = 0
            errors = []

            # Try database model first
            try:
                from firewall.models import BannedIP
            except Exception as e:
                BannedIP = None
                logging.CyberCPLogFileWriter.writeToFile(f'Warning: BannedIP model import failed, using JSON fallback: {str(e)}')

            # Prepare JSON fallback store if needed
            banned_ips_json = []
            if BannedIP is None:
                banned_ips_json, _ = self._load_banned_ips_store()

            import ipaddress
            for item in import_data.get('banned_ips', []):
                try:
                    ip = (item.get('ip') or '').strip()
                    reason = (item.get('reason') or '').strip()
                    duration = (item.get('duration') or 'permanent').strip()
                    active = bool(item.get('active', True))

                    if not ip or not reason:
                        skipped_count += 1
                        continue

                    try:
                        ipaddress.ip_address(ip.split('/')[0])
                    except ValueError:
                        error_count += 1
                        errors.append(f"Invalid IP: {ip}")
                        continue

                    if BannedIP is not None:
                        existing = BannedIP.objects.filter(ip_address=ip).first()
                        if existing:
                            skipped_count += 1
                            continue
                        new_ban = BannedIP(
                            ip_address=ip,
                            reason=reason,
                            duration=duration,
                            active=active
                        )
                        if duration == 'permanent':
                            new_ban.expires = None
                        else:
                            duration_map = {'1h': 3600, '24h': 86400, '7d': 604800, '30d': 2592000}
                            duration_seconds = duration_map.get(duration, 86400)
                            new_ban.expires = int(time.time()) + duration_seconds
                        new_ban.save()
                        imported_count += 1
                    else:
                        # JSON fallback storage
                        exists = any(str(b.get('ip', '')).strip() == ip for b in banned_ips_json)
                        if exists:
                            skipped_count += 1
                            continue
                        banned_ips_json.append({
                            'id': int(time.time() * 1000),
                            'ip': ip,
                            'reason': reason,
                            'duration': duration,
                            'banned_on': int(time.time()),
                            'expires': 'Never' if duration == 'permanent' else int(time.time()) + {
                                '1h': 3600, '24h': 86400, '7d': 604800, '30d': 2592000
                            }.get(duration, 86400),
                            'active': active
                        })
                        imported_count += 1

                except Exception as e:
                    error_count += 1
                    errors.append(f"IP '{item.get('ip', 'unknown')}': {str(e)}")
                    logging.CyberCPLogFileWriter.writeToFile(f"Error importing banned IP {item.get('ip', 'unknown')}: {str(e)}")

            if BannedIP is None:
                self._save_banned_ips_store(banned_ips_json)

            logging.CyberCPLogFileWriter.writeToFile(f"Banned IPs import completed. Imported: {imported_count}, Skipped: {skipped_count}, Errors: {error_count}")

            final_dic = {
                'importStatus': 1,
                'error_message': "None",
                'imported_count': imported_count,
                'skipped_count': skipped_count,
                'error_count': error_count,
                'errors': errors
            }
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)

        except BaseException as msg:
            final_dic = {'importStatus': 0, 'error_message': str(msg)}
            final_json = json.dumps(final_dic)
            return HttpResponse(final_json)




