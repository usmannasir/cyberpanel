#!/usr/local/CyberCP/bin/python
import sys
sys.path.append('/usr/local/CyberCP')
from plogical import CyberCPLogFileWriter as logging
import subprocess
import shlex
import argparse
import os
import threading as multi
from plogical.processUtilities import ProcessUtilities


class CSF(multi.Thread):
    installLogPath = "/home/cyberpanel/csfInstallLog"
    csfURL = 'https://download.configserver.com/csf.tgz'

    def __init__(self, installApp, extraArgs):
        multi.Thread.__init__(self)
        self.installApp = installApp
        self.extraArgs = extraArgs

    def run(self):
        try:
            if self.installApp == 'installCSF':
                self.installCSF()
            elif self.installApp == 'removeCSF':
                self.removeCSF()
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + ' [CSF.run]')

    @staticmethod
    def installCSF():
        try:
            ##

            logging.CyberCPLogFileWriter.statusWriter(CSF.installLogPath, 'Downloading CSF..\n', 1)

            command = 'wget ' + CSF.csfURL
            ProcessUtilities.normalExecutioner(command)

            ##

            logging.CyberCPLogFileWriter.statusWriter(CSF.installLogPath, 'Extracting CSF..\n', 1)

            command = 'tar -xzf csf.tgz'
            ProcessUtilities.normalExecutioner(command)

            ##

            logging.CyberCPLogFileWriter.statusWriter(CSF.installLogPath, 'Installing CSF..\n', 1)

            os.chdir('csf')

            command = "chmod +x install.sh"
            ProcessUtilities.normalExecutioner(command)

            command = 'bash install.sh'
            ProcessUtilities.normalExecutioner(command)

            command = 'mv /etc/csf/ui/server.crt /etc/csf/ui/server.crt-bak'
            ProcessUtilities.normalExecutioner(command)

            command = 'mv /etc/csf/ui/server.key /etc/csf/ui/server.key-bak'
            ProcessUtilities.normalExecutioner(command)

            command = 'ln -s /usr/local/lscp/conf/cert.pem /etc/csf/ui/server.crt'
            ProcessUtilities.normalExecutioner(command)

            command = 'ln -s /usr/local/lscp/conf/key.pem /etc/csf/ui/server.key'
            ProcessUtilities.normalExecutioner(command)

            # install required packages for CSF perl and /usr/bin/host
            if ProcessUtilities.decideDistro() == ProcessUtilities.centos:
                command = 'yum install bind-utils net-tools perl-libwww-perl.noarch perl-LWP-Protocol-https.noarch perl-GDGraph ipset -y'
                ProcessUtilities.normalExecutioner(command)
            elif ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                command = 'apt-get install dnsutils libwww-perl liblwp-protocol-https-perl libgd-graph-perl net-tools ipset -y'
                ProcessUtilities.normalExecutioner(command)
                command = 'ln -s /bin/systemctl /usr/bin/systemctl'
                ProcessUtilities.normalExecutioner(command)
            else:

                logging.CyberCPLogFileWriter.statusWriter(CSF.installLogPath,
                                                          'CSF required packages successfully Installed.[200]\n', 1)

            # Some initial configurations

            data = open('/etc/csf/csf.conf', 'r').readlines()
            writeToConf = open('/etc/csf/csf.conf', 'w')

            for items in data:
                if items.find('TCP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines(
                        'TCP_IN = "20,21,22,25,53,80,110,995,143,443,465,587,993,995,1025,8090,40110:40210"\n')
                elif items.find('TCP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines(
                        'TCP_OUT = "20,21,22,25,43,53,80,110,113,443,587,993,995,8090,40110:40210"\n')
                elif items.find('UDP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('UDP_IN = "20,21,53,443"\n')
                elif items.find('UDP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('UDP_OUT = "20,21,53,113,123,443"\n')
                elif items.find('TESTING =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('TESTING = "0"\n')
                # setting RESTRICT_SYSLOG to "3" for use with option RESTRICT_SYSLOG_GROUP
                elif items.find('RESTRICT_SYSLOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RESTRICT_SYSLOG = "3"\n')

                #  Send an email alert if an IP address is blocked by one of the [*] triggers: disabled
                elif items.find('LF_EMAIL_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_EMAIL_ALERT = "0"\n')

                # Set LF_PERMBLOCK_ALERT to "0" to disable this feature
                elif items.find('LF_PERMBLOCK_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_PERMBLOCK_ALERT = "0"\n')

                #  Set LF_NETBLOCK_ALERT to "0" to disable this feature
                elif items.find('LF_NETBLOCK_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_NETBLOCK_ALERT = "0"\n')

                # Login Failure Blocking and Alerts
                # LF_TRIGGER_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_TRIGGER_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_TRIGGER_PERM = "1800"\n')

                #  Enable login failure detection of sshd connections: 10 failures triggers
                elif items.find('LF_SSHD =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_SSHD = "10"\n')

                #  LF_SSHD_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_SSHD_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_SSHD_PERM = "1800"\n')

                #  Enable login failure detection of ftp connections: 10 failures triggers
                elif items.find('LF_FTPD =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_FTPD = "10"\n')

                #  LF_FTPD_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_FTPD_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_FTPD_PERM = "1800"\n')

                #  Enable login failure detection of SMTP AUTH connections: 10 failures triggers
                elif items.find('LF_SMTPAUTH =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_SMTPAUTH = "10"\n')

                #  LF_SMTPAUTH_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_SMTPAUTH_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_SMTPAUTH_PERM = "1800"\n')

                #  Enable login failure detection of pop3 connections: 10 failures triggers
                elif items.find('LF_POP3D =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_POP3D = "10"\n')

                #  LF_POP3D_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_POP3D_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_POP3D_PERM = "1800"\n')

                #  Enable login failure detection of imap connections: 10 failures triggers
                elif items.find('LF_IMAPD =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_IMAPD = "10"\n')

                #  LF_IMAPD_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_IMAPD_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_IMAPD_PERM = "1800"\n')

                #  LF_HTACCESS_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_HTACCESS_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_HTACCESS_PERM = "1800"\n')

                #  Enable failure detection of repeated Apache mod_security rule triggers: 10 failures triggers
                elif items.find('LF_MODSEC =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_MODSEC = "10"\n')

                #  LF_MODSEC_PERM = "1800" => the IP is blocked temporarily for 30 minutes
                elif items.find('LF_MODSEC_PERM') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_MODSEC_PERM = "1800"\n')

                #  MODSEC_LOG location
                elif items.find('MODSEC_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('MODSEC_LOG = "/usr/local/lsws/logs/auditmodsec.log"\n')

                #  Send an email alert if anyone logs in successfully using SSH: Disabled
                elif items.find('LF_SSH_EMAIL_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_SSH_EMAIL_ALERT = "0"\n')

                #  Send an email alert if anyone accesses webmin: Disabled not applicable
                elif items.find('LF_WEBMIN_EMAIL_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_WEBMIN_EMAIL_ALERT = "0"\n')

                #  LF_QUEUE_ALERT disabled
                elif items.find('LF_QUEUE_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_QUEUE_ALERT = "0"\n')

                #  LF_QUEUE_INTERVAL disabled
                elif items.find('LF_QUEUE_INTERVAL = "0"') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_TRIGGER_PERM = "1800"\n')

                #  Relay Tracking. This allows you to track email that is relayed through the server. Disabled
                elif items.find('RT_RELAY_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_RELAY_ALERT = "0"\n')

                #  RT_[relay type]_LIMIT: the limit/hour afterwhich an email alert will be sent
                elif items.find('RT_RELAY_LIMIT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_RELAY_LIMIT = "500"\n')

                #  RT_[relay type]_BLOCK: 0 = no block;1 = perm block;nn=temp block for nn secs
                elif items.find('RT_RELAY_BLOCK') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_RELAY_BLOCK = "0"\n')

                #   This option triggers for email authenticated by SMTP AUTH disabled
                elif items.find('RT_AUTHRELAY_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_AUTHRELAY_ALERT = "0"\n')

                #  RT_AUTHRELAY_LIMIT set to 100
                elif items.find('RT_AUTHRELAY_LIMIT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_AUTHRELAY_LIMIT = "100"\n')

                #  RT_AUTHRELAY_LIMIT set to 0
                elif items.find('RT_AUTHRELAY_BLOCK') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_AUTHRELAY_BLOCK = "0"\n')

                #   This option triggers for email authenticated by POP before SMTP
                elif items.find('RT_POPRELAY_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_POPRELAY_ALERT = "0"\n')

                #   This option triggers for email authenticated by POP before SMTP
                elif items.find('RT_POPRELAY_LIMIT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_POPRELAY_LIMIT = "100"\n')

                #  RT_POPRELAY_BLOCK disabled
                elif items.find('RT_POPRELAY_BLOCK') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_POPRELAY_BLOCK = "0"\n')

                #   This option triggers for email sent via /usr/sbin/sendmail or /usr/sbin/exim: Disabled
                elif items.find('RT_LOCALRELAY_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_LOCALRELAY_ALERT = "0"\n')

                #   This option triggers for email sent via a local IP addresses
                elif items.find('RT_LOCALRELAY_LIMIT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_LOCALRELAY_LIMIT = "100"\n')

                #   This option triggers for email sent via a local IP addresses
                elif items.find('RT_LOCALHOSTRELAY_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_LOCALHOSTRELAY_ALERT = "0"\n')

                #   This option triggers for email sent via a local IP addresses disabled
                elif items.find('RT_LOCALHOSTRELAY_LIMIT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_LOCALHOSTRELAY_LIMIT = "100"\n')

                #  If an RT_* event is triggered, then if the following contains the path to a script
                elif items.find('RT_ACTION') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('RT_ACTION = ""\n')

                #   Send an email alert if an IP address is blocked due to connection tracking disabled
                elif items.find('CT_EMAIL_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('CT_EMAIL_ALERT = "0"\n')

                #  User Process Tracking.  Set to 0 to disable this feature
                elif items.find('PT_USERPROC =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('PT_USERPROC = "0"\n')

                #  This User Process Tracking option sends an alert if any user process exceeds the virtual memory usage set (MB)
                elif items.find('PT_USERMEM =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('PT_USERMEM = "0"\n')

                #  This User Process Tracking option sends an alert if any user process exceeds the RSS memory usage set (MB) - RAM used, not virtual.
                elif items.find('PT_USERRSS =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('PT_USERRSS = "0"\n')

                #  If this option is set then processes detected by PT_USERMEM, PT_USERTIME or PT_USERPROC are killed. Disabled
                elif items.find('PT_USERTIME =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('PT_USERTIME = "0"\n')

                #  If you want to disable email alerts if PT_USERKILL is triggered, then set this option to 0. Disabled
                elif items.find('PT_USERKILL_ALERT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('PT_USERKILL_ALERT = "0"\n')

                #  Check the PT_LOAD_AVG minute Load Average (can be set to 1 5 or 15 and defaults to 5 if set otherwise) on the server every PT_LOAD seconds. Disabled
                elif items.find('PT_LOAD =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('PT_LOAD = "0"\n')

                #  Enable LF_IPSET for CSF for more efficient ipables rules with ipset
                elif items.find('LF_IPSET =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('LF_IPSET = "1"\n')

                #  HTACCESS_LOG is ins main error.log
                elif items.find('HTACCESS_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('HTACCESS_LOG = "/usr/local/lsws/logs/error.log"\n')

                #  SYSLOG_CHECK Check whether syslog is running
                elif items.find('SYSLOG_CHECK =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    writeToConf.writelines('SYSLOG_CHECK = "300"\n')

                #  CSF UI enable
                # elif items.find('UI = "0"') > -1 and items.find('=') > -1 and (items[0] != '#'):
                #    writeToConf.writelines('UI = "1"\n')
                # elif items.find('UI_ALLOW') > -1 and items.find('=') > -1 and (items[0] != '#'):
                #    writeToConf.writelines('UI_ALLOW = "0"\n')
                # elif items.find('UI_PORT =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                #    writeToConf.writelines('UI_PORT = "1025"\n')
                # elif items.find('UI_USER') > -1 and items.find('=') > -1 and (items[0] != '#'):
                #    writeToConf.writelines('UI_USER = "cyberpanel"\n')
                # elif items.find('UI_PASS') > -1 and items.find('=') > -1 and (items[0] != '#'):
                #    writeToConf.writelines('UI_PASS = "csfadmin1234567"\n')
                else:
                    writeToConf.writelines(items)

            writeToConf.close()

            ##

            # Some Ubuntu initial configurations
            if ProcessUtilities.decideDistro() == ProcessUtilities.ubuntu:
                data = open('/etc/csf/csf.conf', 'r').readlines()
                writeToConf = open('/etc/csf/csf.conf', 'w')

                for items in data:
                    if items.find('SSHD_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('SSHD_LOG = "/var/log/auth.log"\n')
                    elif items.find('SU_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('SU_LOG = "/var/log/auth.log"\n')
                    elif items.find('SMTPAUTH_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('SMTPAUTH_LOG = "/var/log/mail.log"\n')
                    elif items.find('POP3D_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('POP3D_LOG = "/var/log/mail.log"\n')
                    elif items.find('IMAPD_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('IMAPD_LOG = "/var/log/mail.log"\n')
                    elif items.find('IPTABLES_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('IPTABLES_LOG = "/var/log/kern.log"\n')
                    elif items.find('SYSLOG_LOG =') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToConf.writelines('SYSLOG_LOG = "/var/log/syslog"\n')
                    else:
                        writeToConf.writelines(items)
                writeToConf.close()

                ##

            command = 'csf -s'
            ProcessUtilities.normalExecutioner(command)

            command = 'sleep 5'
            ProcessUtilities.normalExecutioner(command)

            command = 'csf -ra'
            ProcessUtilities.normalExecutioner(command)

            logging.CyberCPLogFileWriter.statusWriter(CSF.installLogPath, 'CSF successfully Installed.[200]\n', 1)

            try:
                os.remove('csf.tgz')
                os.removedirs('csf')
            except:
                pass

            return 1
        except BaseException as msg:
            try:
                os.remove('csf.tgz')
                os.removedirs('csf')
            except:
                pass
            writeToFile = open(CSF.installLogPath, 'a')
            writeToFile.writelines(str(msg) + " [404]")
            writeToFile.close()
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[installCSF]")

    def removeCSF(self):
        try:

            ##

            os.chdir('/etc/csf')

            command = './uninstall.sh'
            cmd = shlex.split(command)
            subprocess.call(cmd)

            os.chdir('/usr/local/CyberCP')

            #

            command = 'systemctl unmask firewalld'
            subprocess.call(shlex.split(command))

            #

            command = 'systemctl start firewalld'
            subprocess.call(shlex.split(command))

            ##

            command = 'systemctl enable firewalld'
            subprocess.call(shlex.split(command))

            return 1
        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[removeCSF]")

    @staticmethod
    def fetchCSFSettings():
        try:

            currentSettings = {}

            command = 'sudo cat /etc/csf/csf.conf'
            output = ProcessUtilities.outputExecutioner(command).splitlines()

            for items in output:
                if items.find('TESTING') > -1 and items.find('=') > -1 and (items[0] != '#') and items.find(
                        'TESTING_INTERVAL') == -1:
                    if items.find('0') > -1:
                        currentSettings['TESTING'] = 0
                    else:
                        currentSettings['TESTING'] = 1
                elif items.find('TCP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    tcpIN = items[items.find('"'):]
                    currentSettings['tcpIN'] = tcpIN.strip('"')
                elif items.find('TCP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    tcpOUT = items[items.find('"'):]
                    currentSettings['tcpOUT'] = tcpOUT.strip('"')
                elif items.find('UDP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    udpIN = items[items.find('"'):]
                    currentSettings['udpIN'] = udpIN.strip('"')
                elif items.find('UDP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                    udpOUT = items[items.find('"'):]
                    currentSettings['udpOUT'] = udpOUT.strip('"')

            ### Check if rules are applied

            currentSettings['firewallStatus'] = 0

            command = 'sudo iptables -nv -L'
            output = ProcessUtilities.outputExecutioner(command)

            if output.find('0.0.0.0/0') > -1:
                currentSettings['firewallStatus'] = 1

            return currentSettings

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + " [fetchCSFSettings]")

    @staticmethod
    def changeStatus(controller, status):
        try:
            if controller == 'csf':
                if status == 'enable':
                    command = 'csf -s'
                    subprocess.call(shlex.split(command))
                    print('1,None')
                else:
                    command = 'csf -f'
                    subprocess.call(shlex.split(command))
                    print('1,None')

            elif controller == 'testingMode':
                data = open('/etc/csf/csf.conf', 'r').readlines()
                writeToFile = open('/etc/csf/csf.conf', 'w')

                for items in data:
                    if items.find('TESTING') > -1 and items.find('=') > -1 and (items[0] != '#') and items.find(
                            'TESTING_INTERVAL') == -1:
                        if status == 'enable':
                            writeToFile.writelines('TESTING = "1"\n')
                        else:
                            writeToFile.writelines('TESTING = "0"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
                print('1,None')

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[changeStatus]")
            print('0', str(msg))

    @staticmethod
    def modifyPorts(protocol, portsPath):
        try:

            data = open('/etc/csf/csf.conf', 'r').readlines()
            writeToFile = open('/etc/csf/csf.conf', 'w')

            ports = open(portsPath, 'r').read()

            if protocol == 'TCP_IN':
                for items in data:
                    if items.find('TCP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        if ports.find(',') > -1:
                            writeToFile.writelines('TCP_IN = "' + ports + '"\n')
                        else:
                            content = '%s,%s"\n' % (items.rstrip('\n"'), ports)
                            writeToFile.writelines(content)
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
            elif protocol == 'TCP_OUT':
                for items in data:
                    if items.find('TCP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        if ports.find(',') > -1:
                            writeToFile.writelines('TCP_OUT = "' + ports + '"\n')
                        else:
                            content = '%s,%s"\n' % (items.rstrip('\n"'), ports)
                            writeToFile.writelines(content)
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
            elif protocol == 'UDP_IN':
                for items in data:
                    if items.find('UDP_IN') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToFile.writelines('UDP_IN = "' + ports + '"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()
            elif protocol == 'UDP_OUT':
                for items in data:
                    if items.find('UDP_OUT') > -1 and items.find('=') > -1 and (items[0] != '#'):
                        writeToFile.writelines('UDP_OUT = "' + ports + '"\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

            command = 'csf -r'
            subprocess.call(shlex.split(command))

            try:
                os.remove(portsPath)
            except:
                pass

            print('1,None')

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[modifyPorts]")
            print('0', str(msg))

    @staticmethod
    def allowIP(ipAddress):
        try:
            command = 'sudo csf -dr ' + ipAddress
            ProcessUtilities.executioner(command)

            command = 'sudo csf -a ' + ipAddress
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[allowIP]")

    @staticmethod
    def blockIP(ipAddress):
        try:

            command = 'sudo csf -tr ' + ipAddress
            ProcessUtilities.executioner(command)

            command = 'sudo csf -d ' + ipAddress
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[blockIP]")

    @staticmethod
    def checkIP(ipAddress):
        try:
            command = 'sudo csf -g ' + ipAddress
            ProcessUtilities.executioner(command)

        except BaseException as msg:
            logging.CyberCPLogFileWriter.writeToFile(str(msg) + "[checkIP]")


def main():
    parser = argparse.ArgumentParser(description='CSF Manager')
    parser.add_argument('function', help='Specific a function to call!')

    parser.add_argument('--controller', help='Controller selection!')
    parser.add_argument('--status', help='Controller status!')
    parser.add_argument('--protocol', help='Protocol Modifications!')
    parser.add_argument('--ports', help='Ports!')

    args = parser.parse_args()

    if args.function == "installCSF":
        CSF.installCSF()
    elif args.function == 'removeCSF':
        controller = CSF(args.function, {})
        controller.run()
    elif args.function == 'changeStatus':
        CSF.changeStatus(args.controller, args.status)
    elif args.function == 'modifyPorts':
        CSF.modifyPorts(args.protocol, args.ports)


if __name__ == "__main__":
    main()
