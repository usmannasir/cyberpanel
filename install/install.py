import sys
import subprocess
import shutil
import installLog as logging
import argparse
import os
import shlex
from firewallUtilities import FirewallUtilities
import time
import string
import random
import socket
from os.path import *
from stat import *
import stat

char_set = {'small': 'abcdefghijklmnopqrstuvwxyz',
            'nums': '0123456789',
            'big': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
            }


def generate_pass(length=14):
  chars = string.ascii_uppercase + string.ascii_lowercase + string.digits
  size = length
  return ''.join(random.choice(chars) for x in range(size))


# There can not be peace without first a great suffering.

# distros

centos = 0
ubuntu = 1
cent8 = 2


def get_distro():
    distro = -1
    distro_file = ""
    if exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line == "DISTRIB_ID=Ubuntu\n":
                    distro = ubuntu

    elif exists("/etc/os-release"):
        distro_file = "/etc/os-release"
        distro = centos

        data = open('/etc/redhat-release', 'r').read()

        if data.find('CentOS Linux release 8') > -1:
            return cent8

    else:
        logging.InstallLog.writeToFile("Can't find linux release file - fatal error")
        preFlightsChecks.stdOut("Can't find linux release file - fatal error")
        os._exit(os.EX_UNAVAILABLE)

    if distro == -1:
        logging.InstallLog.writeToFile("Can't find distro name in " + distro_file + " - fatal error")
        preFlightsChecks.stdOut("Can't find distro name in " + distro_file + " - fatal error")
        os._exit(os.EX_UNAVAILABLE)

    return distro


def get_Ubuntu_release():
    release = -1
    if exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line[:16] == "DISTRIB_RELEASE=":
                    release = float(line[16:])

        if release == -1:
            preFlightsChecks.stdOut("Can't find distro release name in " + distro_file + " - fatal error", 1, 1,
                                    os.EX_UNAVAILABLE)

    else:
        logging.InstallLog.writeToFile("Can't find linux release file - fatal error")
        preFlightsChecks.stdOut("Can't find linux release file - fatal error")
        os._exit(os.EX_UNAVAILABLE)

    return release


class preFlightsChecks:
    cyberPanelMirror = "mirror.cyberpanel.net/pip"
    cdn = 'cyberpanel.sh'

    def __init__(self, rootPath, ip, path, cwd, cyberPanelPath, distro):
        self.ipAddr = ip
        self.path = path
        self.cwd = cwd
        self.server_root_path = rootPath
        self.cyberPanelPath = cyberPanelPath
        self.distro = distro

    @staticmethod
    def stdOut(message, log=0, do_exit=0, code=os.EX_OK):
        print("\n\n")
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))
        print(("[" + time.strftime("%m.%d.%Y_%H-%M-%S") + "] " + message + "\n"))
        print(("[" + time.strftime(
            "%m.%d.%Y_%H-%M-%S") + "] #########################################################################\n"))

        if log:
            logging.InstallLog.writeToFile(message)
        if do_exit:
            logging.InstallLog.writeToFile(message)
            sys.exit(code)

    def mountTemp(self):
        try:
            ## On OpenVZ there is an issue using .tempdisk for /tmp as it breaks network on container after reboot.

            if subprocess.check_output('systemd-detect-virt').decode("utf-8").find("openvz") > -1:

                varTmp = "/var/tmp /tmp none bind 0 0\n"

                fstab = "/etc/fstab"
                writeToFile = open(fstab, "a")
                writeToFile.writelines(varTmp)
                writeToFile.close()

            else:

                command = "dd if=/dev/zero of=/usr/.tempdisk bs=100M count=15"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                command = "mkfs.ext4 -F /usr/.tempdisk"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                command = "mkdir -p /usr/.tmpbak/"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                command = "cp -pr /tmp/* /usr/.tmpbak/"
                subprocess.call(command, shell=True)

                command = "mount -o loop,rw,nodev,nosuid,noexec,nofail /usr/.tempdisk /tmp"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                command = "chmod 1777 /tmp"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                command = "cp -pr /usr/.tmpbak/* /tmp/"
                subprocess.call(command, shell=True)

                command = "rm -rf /usr/.tmpbak"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                command = "mount --bind /tmp /var/tmp"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

                tmp = "/usr/.tempdisk /tmp ext4 loop,rw,noexec,nosuid,nodev,nofail 0 0\n"
                varTmp = "/tmp /var/tmp none bind 0 0\n"

                fstab = "/etc/fstab"
                writeToFile = open(fstab, "a")
                writeToFile.writelines(tmp)
                writeToFile.writelines(varTmp)
                writeToFile.close()

        except BaseException as msg:
            preFlightsChecks.stdOut('[ERROR] ' + str(msg))
            return 0

    @staticmethod
    def pureFTPDServiceName(distro):
        if distro == ubuntu:
            return 'pure-ftpd'
        return 'pure-ftpd'

    @staticmethod
    def resFailed(distro, res):
        if distro == ubuntu and res != 0:
            return True
        elif distro == centos and res != 0:
            return True
        return False

    @staticmethod
    def call(command, distro, bracket, message, log=0, do_exit=0, code=os.EX_OK):
        finalMessage = 'Running: %s' % (message)
        preFlightsChecks.stdOut(finalMessage, log)
        count = 0
        while True:
            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(distro, res):
                count = count + 1
                finalMessage = 'Running %s failed. Running again, try number %s' % (message, str(count))
                preFlightsChecks.stdOut(finalMessage)
                if count == 3:
                    fatal_message = ''
                    if do_exit:
                        fatal_message = '.  Fatal error, see /var/log/installLogs.txt for full details'

                    preFlightsChecks.stdOut("[ERROR] We are not able to run " + message + ' return code: ' + str(res) +
                                            fatal_message + ".", 1, do_exit, code)
                    return False
            else:
                preFlightsChecks.stdOut('Successfully ran: %s.' % (message), log)
                break

        return True

    def checkIfSeLinuxDisabled(self):
        try:
            command = "sestatus"
            output = subprocess.check_output(shlex.split(command)).decode("utf-8")

            if output.find("disabled") > -1 or output.find("permissive") > -1:
                logging.InstallLog.writeToFile("SELinux Check OK. [checkIfSeLinuxDisabled]")
                preFlightsChecks.stdOut("SELinux Check OK.")
                return 1
            else:
                logging.InstallLog.writeToFile(
                    "SELinux is enabled, please disable SELinux and restart the installation!")
                preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                os._exit(0)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + "[checkIfSeLinuxDisabled]")
            logging.InstallLog.writeToFile('[ERROR] ' + "SELinux Check OK. [checkIfSeLinuxDisabled]")
            preFlightsChecks.stdOut('[ERROR] ' + "SELinux Check OK.")
            return 1

    def checkPythonVersion(self):
        if sys.version_info[0] == 3:
            return 1
        else:
            preFlightsChecks.stdOut("You are running Unsupported python version, please install python 3.x")
            os._exit(0)

    def setup_account_cyberpanel(self):
        try:

            if self.distro == centos or self.distro == cent8:
                command = "yum install sudo -y"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

            ##

            if self.distro == ubuntu:
                self.stdOut("Add Cyberpanel user")
                command = 'adduser --disabled-login --gecos "" cyberpanel'
                preFlightsChecks.call(command, self.distro, command,command,1, 1, os.EX_OSERR)

            else:
                command = "useradd -s /bin/false cyberpanel"
                preFlightsChecks.call(command, self.distro, command,command,1, 1, os.EX_OSERR)


            ###############################

            ### Docker User/group

            if self.distro == ubuntu:
                command = 'adduser --disabled-login --gecos "" docker'
            else:
                command = "adduser docker"

            preFlightsChecks.call(command, self.distro, command,command,1, 0, os.EX_OSERR)

            command = 'groupadd docker'
            preFlightsChecks.call(command, self.distro, command,command,1, 0, os.EX_OSERR)

            command = 'usermod -aG docker docker'
            preFlightsChecks.call(command, self.distro, command,command,1, 0, os.EX_OSERR)

            command = 'usermod -aG docker cyberpanel'
            preFlightsChecks.call(command, self.distro, command,command,1, 0, os.EX_OSERR)

            ###

            command = "mkdir -p /etc/letsencrypt/live/"
            preFlightsChecks.call(command, self.distro, command,command,1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile("[ERROR] setup_account_cyberpanel. " + str(msg))

    def yum_update(self):
        command = 'yum update -y'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def installCyberPanelRepo(self):
        self.stdOut("Install Cyberpanel repo")

        if self.distro == ubuntu:
            try:
                filename = "enable_lst_debain_repo.sh"
                command = "wget http://rpms.litespeedtech.com/debian/" + filename
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                os.chmod(filename, S_IRWXU | S_IRWXG)

                command = "./" + filename
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            except:
                logging.InstallLog.writeToFile("[ERROR] Exception during CyberPanel install")
                preFlightsChecks.stdOut("[ERROR] Exception during CyberPanel install")
                os._exit(os.EX_SOFTWARE)

        elif self.distro == centos:
            command = 'rpm -ivh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        elif self.distro == cent8:
            command = 'rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def enableEPELRepo(self):
        command = 'yum -y install epel-release'
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def install_pip(self):
        self.stdOut("Install pip")
        if self.distro == ubuntu:
            command = "apt-get -y install python-pip"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        elif self.distro == centos:
            command = "yum -y install python-pip"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)


    def install_python_dev(self):
        self.stdOut("Install python development environment")

        if self.distro == centos:
            command = "yum -y install python-devel"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        elif self.distro == ubuntu:
            command = "apt-get -y install python-dev"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)



    def install_gcc(self):
        self.stdOut("Install gcc")

        if self.distro == centos:
            command = "yum -y install gcc"
        else:
            command = "apt-get -y install gcc"

        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def install_python_setup_tools(self):
        command = "yum -y install python-setuptools"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def install_python_mysql_library(self):
        self.stdOut("Install MySQL python library")

        if self.distro == centos:
            command = "yum install mariadb-devel gcc python36u-devel -y"
        else:
            command = "apt-get -y install libmysqlclient-dev"

        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        if self.distro == ubuntu:
            command = "pip install MySQL-python"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def fix_selinux_issue(self):
        try:
            cmd = []

            cmd.append("setsebool")
            cmd.append("-P")
            cmd.append("httpd_can_network_connect")
            cmd.append("1")

            res = subprocess.call(cmd)

            if preFlightsChecks.resFailed(self.distro, res):
                logging.InstallLog.writeToFile("fix_selinux_issue problem")
            else:
                pass
        except:
            logging.InstallLog.writeToFile("[ERROR] fix_selinux_issue problem")

    def install_psmisc(self):
        self.stdOut("Install psmisc")

        if self.distro == centos or self.distro == cent8:
            command = "yum -y install psmisc"
        else:
            command = "apt-get -y install psmisc"

        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def installGit(self):
        if os.path.exists("/etc/lsb-release"):
            command = 'apt -y install git'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        else:
            command = 'yum -y install http://repo.iotti.biz/CentOS/7/noarch/lux-release-7-1.noarch.rpm'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'yum install git -y'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def download_install_CyberPanel(self, mysqlPassword, mysql):
        ##

        os.chdir(self.path)

        self.installGit()

        os.chdir('/usr/local')

        command = "git clone https://github.com/usmannasir/cyberpanel"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        shutil.move('cyberpanel', 'CyberCP')

        ##

        ### update password:

        passFile = "/etc/cyberpanel/mysqlPassword"

        f = open(passFile)
        data = f.read()
        password = data.split('\n', 1)[0]

        ### Put correct mysql passwords in settings file!

        logging.InstallLog.writeToFile("Updating settings.py!")

        path = self.cyberPanelPath + "/CyberCP/settings.py"

        data = open(path, "r").readlines()

        writeDataToFile = open(path, "w")

        counter = 0

        for items in data:
            if items.find('SECRET_KEY') > -1:
                SK = "SECRET_KEY = '%s'\n" % (generate_pass(50))
                writeDataToFile.writelines(SK)
                continue
            if mysql == 'Two':
                if items.find("'PASSWORD':") > -1:
                    if counter == 0:
                        writeDataToFile.writelines("        'PASSWORD': '" + mysqlPassword + "'," + "\n")
                        counter = counter + 1
                    else:
                        writeDataToFile.writelines("        'PASSWORD': '" + password + "'," + "\n")

                else:
                    writeDataToFile.writelines(items)
            else:
                if items.find("'PASSWORD':") > -1:
                    if counter == 0:
                        writeDataToFile.writelines("        'PASSWORD': '" + mysqlPassword + "'," + "\n")
                        counter = counter + 1

                    else:
                        writeDataToFile.writelines("        'PASSWORD': '" + password + "'," + "\n")
                elif items.find('127.0.0.1') > -1:
                    writeDataToFile.writelines("        'HOST': 'localhost',\n")
                elif items.find("'PORT':'3307'") > -1:
                    writeDataToFile.writelines("        'PORT': '',\n")
                else:
                    writeDataToFile.writelines(items)

        if self.distro == ubuntu:
            os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

        writeDataToFile.close()

        logging.InstallLog.writeToFile("settings.py updated!")

        #self.setupVirtualEnv(self.distro)

        ### Applying migrations

        os.chdir("/usr/local/CyberCP")

        command = "/usr/local/CyberPanel/bin/python manage.py makemigrations"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        ##

        command = "/usr/local/CyberPanel/bin/python manage.py migrate"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        if not os.path.exists("/usr/local/CyberCP/public"):
            os.mkdir("/usr/local/CyberCP/public")

        ## Moving static content to lscpd location
        command = 'mv static /usr/local/CyberCP/public/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        try:
            import requests
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
            path = "/usr/local/CyberCP/version.txt"
            writeToFile = open(path, 'w')
            writeToFile.writelines('%s\n' % (str(latest['version'])))
            writeToFile.writelines(str(latest['build']))
            writeToFile.close()
        except:
            pass

    def fixCyberPanelPermissions(self):

        ###### fix Core CyberPanel permissions

        command = "usermod -G lscpd,lsadm,nobody lscpd"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "usermod -G lscpd,lsadm,nogroup lscpd"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "find /usr/local/CyberCP -type d -exec chmod 0755 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "find /usr/local/CyberCP -type f -exec chmod 0644 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod -R 755 /usr/local/CyberCP/bin"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## change owner

        command = "chown -R root:root /usr/local/CyberCP"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ########### Fix LSCPD

        command = "find /usr/local/lscp -type d -exec chmod 0755 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "find /usr/local/lscp -type f -exec chmod 0644 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod -R 755 /usr/local/lscp/bin"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod -R 755 /usr/local/lscp/fcgi-bin"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## change owner

        command = "chown -R root:root /usr/local/lscp"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/data"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod 700 /usr/local/CyberCP/cli/cyberPanel.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod 700 /usr/local/CyberCP/plogical/upgradeCritical.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod 755 /usr/local/CyberCP/postfixSenderPolicy/client.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod 640 /usr/local/CyberCP/CyberCP/settings.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chown root:cyberpanel /usr/local/CyberCP/CyberCP/settings.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
                 '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                 '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                 '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
                 '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

        for items in files:
            command = 'chmod 644 %s' % (items)
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                   '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                   '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
                   '/etc/powerdns/pdns.conf']

        for items in impFile:
            command = 'chmod 600 %s' % (items)
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'chmod 640 /etc/postfix/*.cf'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/postfix/main.cf'
        subprocess.call(command, shell=True)

        command = 'chmod 640 /etc/dovecot/*.conf'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/dovecot/dovecot.conf'
        subprocess.call(command, shell=True)

        command = 'chmod 640 /etc/dovecot/dovecot-sql.conf.ext'
        subprocess.call(command, shell=True)

        command = 'chmod 644 /etc/postfix/dynamicmaps.cf'
        subprocess.call(command, shell=True)

        fileM = ['/usr/local/lsws/FileManager/', '/usr/local/CyberCP/install/FileManager',
                 '/usr/local/CyberCP/serverStatus/litespeed/FileManager', '/usr/local/lsws/Example/html/FileManager']

        for items in fileM:
            try:
                shutil.rmtree(items)
            except:
                pass

        command = 'chmod 755 /etc/pure-ftpd/'
        subprocess.call(command, shell=True)

        command = 'chmod +x /usr/local/CyberCP/plogical/renew.py'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'chmod +x /usr/local/CyberCP/CLManager/CLPackages.py'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        clScripts = ['/usr/local/CyberCP/CLScript/panel_info.py', '/usr/local/CyberCP/CLScript/CloudLinuxPackages.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxUsers.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py'
            , '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py', '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDB.py', '/usr/local/CyberCP/CLScript/UserInfo.py']

        for items in clScripts:
            command = 'chmod +x %s' % (items)
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'chmod 600 /usr/local/CyberCP/plogical/adminPass.py'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'chmod 600 /etc/cagefs/exclude/cyberpanelexclude'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "find /usr/local/CyberCP/ -name '*.pyc' -delete"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def install_unzip(self):
        self.stdOut("Install unzip")
        try:
            if self.distro == centos or self.distro == cent8:
                command = 'yum -y install unzip'
            else:
                command = 'apt-get -y install unzip'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] '+ str(msg) + " [install_unzip]")

    def install_zip(self):
        self.stdOut("Install zip")
        try:
            if self.distro == centos or self.distro == cent8:
                command = 'yum -y install zip'
            else:
                command = 'apt-get -y install zip'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_zip]")

    def download_install_phpmyadmin(self):
        try:

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            command = 'wget -O /usr/local/CyberCP/public/phpmyadmin.zip https://%s/misc/phpmyadmin.zip' % (preFlightsChecks.cdn)

            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)

            command = 'unzip /usr/local/CyberCP/public/phpmyadmin.zip -d /usr/local/CyberCP/public/'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)

            command = 'mv /usr/local/CyberCP/public/phpMyAdmin-5.0.0-all-languages /usr/local/CyberCP/public/phpmyadmin'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)

            command = 'rm -f /usr/local/CyberCP/public/phpmyadmin.zip'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)


            ## Write secret phrase

            rString = ''.join([random.choice(string.ascii_letters + string.digits) for n in range(32)])

            data = open('/usr/local/CyberCP/public/phpmyadmin/config.sample.inc.php', 'r').readlines()

            writeToFile = open('/usr/local/CyberCP/public/phpmyadmin/config.inc.php', 'w')

            for items in data:
                if items.find('blowfish_secret') > -1:
                    writeToFile.writelines(
                        "$cfg['blowfish_secret'] = '" + rString + "'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.writelines("$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';\n")

            writeToFile.close()

            os.mkdir('/usr/local/CyberCP/public/phpmyadmin/tmp')

            command = 'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin'
            preFlightsChecks.call(command, self.distro, '[chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin]',
                                  'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin', 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [download_install_phpmyadmin]")
            return 0

    ###################################################### Email setup

    def install_postfix_davecot(self):
        self.stdOut("Install dovecot - first remove postfix")

        if self.distro == centos:
            path = '/etc/yum.repos.d/dovecot.repo'
            content = """[dovecot-2.3-latest]
name=Dovecot 2.3 CentOS $releasever - $basearch
baseurl=http://repo.dovecot.org/ce-2.3-latest/centos/$releasever/RPMS/$basearch
gpgkey=https://repo.dovecot.org/DOVECOT-REPO-GPG
gpgcheck=1
enabled=1"""
            writeToFile = open(path, 'w')
            writeToFile.write(content)
            writeToFile.close()

        try:
            if self.distro == centos:

                command = 'yum -y install http://cyberpanel.sh/gf-release-latest.gf.el7.noarch.rpm'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'yum remove postfix -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            elif self.distro == ubuntu:
                command = 'apt-get -y remove postfix'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)



            self.stdOut("Install dovecot - do the install")

            if self.distro == centos:
                command = 'yum install --enablerepo=gf-plus -y postfix3 postfix3-ldap postfix3-mysql postfix3-pcre'
            elif self.distro == cent8:
                command = 'dnf install postfix postfix-mysql -y'
            else:
                command = 'apt-get -y debconf-utils'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                file_name = self.cwd + '/pf.unattend.text'
                pf = open(file_name, 'w')
                pf.write('postfix postfix/mailname string ' + str(socket.getfqdn() + '\n'))
                pf.write('postfix postfix/main_mailer_type string "Internet Site"\n')
                pf.close()
                command = 'debconf-set-selections ' + file_name
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'apt-get -y install postfix'
                # os.remove(file_name)

            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            if self.distro == centos or self.distro == cent8:
                pass
            else:
                command = 'apt-get -y install dovecot-imapd dovecot-pop3d postfix-mysql'

            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ##

            if self.distro == centos or self.distro == cent8:
                command = 'yum -y install dovecot dovecot-mysql'
            else:
                command = 'apt-get -y install dovecot-mysql'

            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            if self.distro != centos:
                command = 'curl https://repo.dovecot.org/DOVECOT-REPO-GPG | gpg --import'
                subprocess.call(command, shell=True)

                command = 'gpg --export ED409DA1 > /etc/apt/trusted.gpg.d/dovecot.gpg'
                subprocess.call(command, shell=True)

                debPath = '/etc/apt/sources.list.d/dovecot.list'
                writeToFile = open(debPath, 'w')
                writeToFile.write('deb https://repo.dovecot.org/ce-2.3-latest/ubuntu/bionic bionic main\n')
                writeToFile.close()

                try:
                    command = 'apt update -y'
                    subprocess.call(command, shell=True)
                except:
                    pass

                try:
                    command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical sudo apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" --only-upgrade install dovecot-mysql -y'
                    subprocess.call(command, shell=True)

                    command = 'dpkg --configure -a'
                    subprocess.call(command, shell=True)

                    command = 'apt --fix-broken install -y'
                    subprocess.call(command, shell=True)

                    command = 'DEBIAN_FRONTEND=noninteractive DEBIAN_PRIORITY=critical sudo apt-get -q -y -o "Dpkg::Options::=--force-confdef" -o "Dpkg::Options::=--force-confold" --only-upgrade install dovecot-mysql -y'
                    subprocess.call(command, shell=True)
                except:
                    pass

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_postfix_davecot]")
            return 0

        return 1

    def setup_email_Passwords(self, mysqlPassword, mysql):
        try:

            logging.InstallLog.writeToFile("Setting up authentication for Postfix and Dovecot...")

            os.chdir(self.cwd)

            if mysql == 'Two':
                mysql_virtual_domains = "email-configs/mysql-virtual_domains.cf"
                mysql_virtual_forwardings = "email-configs/mysql-virtual_forwardings.cf"
                mysql_virtual_mailboxes = "email-configs/mysql-virtual_mailboxes.cf"
                mysql_virtual_email2email = "email-configs/mysql-virtual_email2email.cf"
                davecotmysql = "email-configs/dovecot-sql.conf.ext"
            else:
                mysql_virtual_domains = "email-configs-one/mysql-virtual_domains.cf"
                mysql_virtual_forwardings = "email-configs-one/mysql-virtual_forwardings.cf"
                mysql_virtual_mailboxes = "email-configs-one/mysql-virtual_mailboxes.cf"
                mysql_virtual_email2email = "email-configs-one/mysql-virtual_email2email.cf"
                davecotmysql = "email-configs-one/dovecot-sql.conf.ext"

                ### update password:

            data = open(davecotmysql, "r").readlines()

            writeDataToFile = open(davecotmysql, "w")

            if mysql == 'Two':
                dataWritten = "connect = host=127.0.0.1 dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3307\n"
            else:
                dataWritten = "connect = host=localhost dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3306\n"

            for items in data:
                if items.find("connect") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_domains, "r").readlines()

            writeDataToFile = open(mysql_virtual_domains, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_forwardings, "r").readlines()

            writeDataToFile = open(mysql_virtual_forwardings, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_mailboxes, "r").readlines()

            writeDataToFile = open(mysql_virtual_mailboxes, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            ### update password:

            data = open(mysql_virtual_email2email, "r").readlines()

            writeDataToFile = open(mysql_virtual_email2email, "w")

            dataWritten = "password = " + mysqlPassword + "\n"

            for items in data:
                if items.find("password") > -1:
                    writeDataToFile.writelines(dataWritten)
                else:
                    writeDataToFile.writelines(items)

            # if self.distro == ubuntu:
            #    os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

            writeDataToFile.close()

            logging.InstallLog.writeToFile("Authentication for Postfix and Dovecot set.")

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR]' + str(msg) + " [setup_email_Passwords]")
            return 0

        return 1

    def centos_lib_dir_to_ubuntu(self, filename, old, new):
        try:
            fd = open(filename, 'r')
            lines = fd.readlines()
            fd.close()
            fd = open(filename, 'w')
            centos_prefix = old
            ubuntu_prefix = new
            for line in lines:
                index = line.find(centos_prefix)
                if index != -1:
                    line = line[:index] + ubuntu_prefix + line[index + len(centos_prefix):]
                fd.write(line)
            fd.close()
        except IOError as err:
            self.stdOut("[ERROR] Error converting: " + filename + " from centos defaults to ubuntu defaults: " + str(err), 1,
                        1, os.EX_OSERR)

    def setup_postfix_davecot_config(self, mysql):
        try:
            logging.InstallLog.writeToFile("Configuring postfix and dovecot...")

            os.chdir(self.cwd)

            mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
            main = "/etc/postfix/main.cf"
            master = "/etc/postfix/master.cf"
            davecot = "/etc/dovecot/dovecot.conf"
            davecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"

            if os.path.exists(mysql_virtual_domains):
                os.remove(mysql_virtual_domains)

            if os.path.exists(mysql_virtual_forwardings):
                os.remove(mysql_virtual_forwardings)

            if os.path.exists(mysql_virtual_mailboxes):
                os.remove(mysql_virtual_mailboxes)

            if os.path.exists(mysql_virtual_email2email):
                os.remove(mysql_virtual_email2email)

            if os.path.exists(main):
                os.remove(main)

            if os.path.exists(master):
                os.remove(master)

            if os.path.exists(davecot):
                os.remove(davecot)

            if os.path.exists(davecotmysql):
                os.remove(davecotmysql)

            ###############Getting SSL

            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Cleanup config files for ubuntu
            if self.distro == ubuntu:
                preFlightsChecks.stdOut("Cleanup postfix/dovecot config files", 1)
                if mysql == 'Two':
                    self.centos_lib_dir_to_ubuntu("email-configs/master.cf", "/usr/libexec/", "/usr/lib/")
                    self.centos_lib_dir_to_ubuntu("email-configs/main.cf", "/usr/libexec/postfix",
                                                  "/usr/lib/postfix/sbin")
                else:
                    self.centos_lib_dir_to_ubuntu("email-configs-one/master.cf", "/usr/libexec/", "/usr/lib/")
                    self.centos_lib_dir_to_ubuntu("email-configs-one/main.cf", "/usr/libexec/postfix",
                                                  "/usr/lib/postfix/sbin")

            ########### Copy config files

            if mysql == 'Two':
                shutil.copy("email-configs/mysql-virtual_domains.cf", "/etc/postfix/mysql-virtual_domains.cf")
                shutil.copy("email-configs/mysql-virtual_forwardings.cf", "/etc/postfix/mysql-virtual_forwardings.cf")
                shutil.copy("email-configs/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
                shutil.copy("email-configs/mysql-virtual_email2email.cf", "/etc/postfix/mysql-virtual_email2email.cf")
                shutil.copy("email-configs/main.cf", main)
                shutil.copy("email-configs/master.cf", master)
                shutil.copy("email-configs/dovecot.conf", davecot)
                shutil.copy("email-configs/dovecot-sql.conf.ext", davecotmysql)
            else:
                shutil.copy("email-configs-one/mysql-virtual_domains.cf", "/etc/postfix/mysql-virtual_domains.cf")
                shutil.copy("email-configs-one/mysql-virtual_forwardings.cf",
                            "/etc/postfix/mysql-virtual_forwardings.cf")
                shutil.copy("email-configs-one/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
                shutil.copy("email-configs-one/mysql-virtual_email2email.cf",
                            "/etc/postfix/mysql-virtual_email2email.cf")
                shutil.copy("email-configs-one/main.cf", main)
                shutil.copy("email-configs-one/master.cf", master)
                shutil.copy("email-configs-one/dovecot.conf", davecot)
                shutil.copy("email-configs-one/dovecot-sql.conf.ext", davecotmysql)

            ######################################## Permissions

            command = 'chmod o= /etc/postfix/mysql-virtual_domains.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_forwardings.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_mailboxes.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= /etc/postfix/mysql-virtual_email2email.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= ' + main
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= ' + master
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            #######################################

            command = 'chgrp postfix /etc/postfix/mysql-virtual_domains.cf'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_forwardings.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_mailboxes.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chgrp postfix /etc/postfix/mysql-virtual_email2email.cf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chgrp postfix ' + main
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chgrp postfix ' + master
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ######################################## users and groups

            command = 'groupadd -g 5000 vmail'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'useradd -g vmail -u 5000 vmail -d /home/vmail -m'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ######################################## Further configurations

            # hostname = socket.gethostname()

            ################################### Restart postix

            command = 'systemctl enable postfix.service'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'systemctl start postfix.service'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ######################################## Permissions

            command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ################################### Restart davecot

            command = 'systemctl enable dovecot.service'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'systemctl start dovecot.service'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'systemctl restart  postfix.service'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ## chaging permissions for main.cf

            command = "chmod 755 " + main
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "mkdir -p /etc/pki/dovecot/private/"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = "mkdir -p /etc/pki/dovecot/certs/"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = "mkdir -p /etc/opendkim/keys/"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = "sed -i 's/auth_mechanisms = plain/#auth_mechanisms = plain/g' /etc/dovecot/conf.d/10-auth.conf"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                ## Ubuntu 18.10 ssl_dh for dovecot 2.3.2.1

                if get_Ubuntu_release() == 18.10:
                    dovecotConf = '/etc/dovecot/dovecot.conf'

                    data = open(dovecotConf, 'r').readlines()
                    writeToFile = open(dovecotConf, 'w')
                    for items in data:
                        if items.find('ssl_key = <key.pem') > -1:
                            writeToFile.writelines(items)
                            writeToFile.writelines('ssl_dh = </usr/share/dovecot/dh.pem\n')
                        else:
                            writeToFile.writelines(items)
                    writeToFile.close()

                command = "systemctl restart dovecot"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            logging.InstallLog.writeToFile("Postfix and Dovecot configured")
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setup_postfix_davecot_config]")
            return 0

        return 1

    def downoad_and_install_raindloop(self):
        try:
            #######

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            if os.path.exists("/usr/local/CyberCP/public/rainloop"):
                return 0

            os.chdir("/usr/local/CyberCP/public")

            command = 'wget https://www.rainloop.net/repository/webmail/rainloop-community-latest.zip'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            #############

            command = 'unzip rainloop-community-latest.zip -d /usr/local/CyberCP/public/rainloop'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            os.remove("rainloop-community-latest.zip")

            #######

            os.chdir("/usr/local/CyberCP/public/rainloop")

            command = 'find . -type d -exec chmod 755 {} \;'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            #############

            command = 'find . -type f -exec chmod 644 {} \;'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ######

            command = "mkdir -p /usr/local/lscp/cyberpanel/rainloop/data"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ### Enable sub-folders

            command = "mkdir -p /usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            labsPath = '/usr/local/lscp/cyberpanel/rainloop/data/_data_/_default_/configs/application.ini'

            labsData = """[labs]
imap_folder_list_limit = 0
"""

            writeToFile = open(labsPath, 'w')
            writeToFile.write(labsData)
            writeToFile.close()

            iPath = os.listdir('/usr/local/CyberCP/public/rainloop/rainloop/v/')

            path = "/usr/local/CyberCP/public/rainloop/rainloop/v/%s/include.php" % (iPath[0])

            data = open(path, 'r').readlines()
            writeToFile = open(path, 'w')

            for items in data:
                if items.find("$sCustomDataPath = '';") > -1:
                    writeToFile.writelines(
                        "			$sCustomDataPath = '/usr/local/lscp/cyberpanel/rainloop/data';\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [downoad_and_install_rainloop]")
            return 0

        return 1

    ###################################################### Email setup ends!

    def reStartLiteSpeed(self):
        command = '%sbin/lswsctrl restart' % (self.server_root_path)
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def removeUfw(self):
        try:
            preFlightsChecks.stdOut("Checking to see if ufw firewall is installed (will be removed)", 1)
            status = subprocess.check_output(shlex.split('ufw status')).decode("utf-8")
            preFlightsChecks.stdOut("ufw current status: " + status + "...will be removed")
        except BaseException as msg:
            preFlightsChecks.stdOut("[ERROR] Expected access to ufw not available, do not need to remove it", 1)
            return True
        try:
            preFlightsChecks.call('apt-get -y remove ufw', self.distro, '[remove_ufw]', 'Remove ufw firewall ' +
                                  '(using firewalld)', 1, 0, os.EX_OSERR)
        except:
            pass
        return True

    def installFirewalld(self):

        if self.distro == cent8:
            return 0
        if self.distro == ubuntu:
            self.removeUfw()

        try:
            preFlightsChecks.stdOut("Enabling Firewall!")

            if self.distro == ubuntu:
                command = 'apt-get -y install firewalld'
            else:
                command = 'yum -y install firewalld'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ######
            if self.distro == centos or self.distro == cent8:
                # Not available in ubuntu
                command = 'systemctl restart dbus'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'systemctl restart systemd-logind'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'systemctl start firewalld'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##########

            command = 'systemctl enable firewalld'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            FirewallUtilities.addRule("tcp", "8090")
            FirewallUtilities.addRule("tcp", "80")
            FirewallUtilities.addRule("tcp", "443")
            FirewallUtilities.addRule("tcp", "21")
            FirewallUtilities.addRule("tcp", "25")
            FirewallUtilities.addRule("tcp", "587")
            FirewallUtilities.addRule("tcp", "465")
            FirewallUtilities.addRule("tcp", "110")
            FirewallUtilities.addRule("tcp", "143")
            FirewallUtilities.addRule("tcp", "993")
            FirewallUtilities.addRule("tcp", "995")
            FirewallUtilities.addRule("udp", "53")
            FirewallUtilities.addRule("tcp", "53")
            FirewallUtilities.addRule("udp", "443")
            FirewallUtilities.addRule("tcp", "40110-40210")

            logging.InstallLog.writeToFile("FirewallD installed and configured!")
            preFlightsChecks.stdOut("FirewallD installed and configured!")


        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installFirewalld]")
            return 0
        except ValueError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installFirewalld]")
            return 0

        return 1

    ## from here

    def installLSCPD(self):
        try:

            logging.InstallLog.writeToFile("Starting LSCPD installation..")

            os.chdir(self.cwd)

            if self.distro == ubuntu:
                command = "apt-get -y install gcc g++ make autoconf rcs"
            else:
                command = 'yum -y install gcc gcc-c++ make autoconf glibc'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "apt-get -y install libpcre3 libpcre3-dev openssl libexpat1 libexpat1-dev libgeoip-dev" \
                          " zlib1g zlib1g-dev libudns-dev whichman curl"
            else:
                command = 'yum -y install pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'tar zxf lscp.tar.gz -C /usr/local/'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /usr/local/lscp/conf/key.pem -out /usr/local/lscp/conf/cert.pem'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            try:
                os.remove("/usr/local/lscp/fcgi-bin/lsphp")
                shutil.copy("/usr/local/lsws/lsphp72/bin/lsphp", "/usr/local/lscp/fcgi-bin/lsphp")
            except:
                pass

            if self.distro == centos or self.distro == cent8:
                command = 'adduser lscpd -M -d /usr/local/lscp'
            else:
                command = 'useradd lscpd -M -d /usr/local/lscp'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == centos or self.distro == cent8:
                command = 'groupadd lscpd'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                # Added group in useradd for Ubuntu

            command = 'usermod -a -G lscpd lscpd'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'usermod -a -G lsadm lscpd'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            try:
                os.mkdir('/usr/local/lscp/cyberpanel')
            except:
                pass
            try:
                os.mkdir('/usr/local/lscp/cyberpanel/logs')
            except:
                pass

            # self.setupComodoRules()

            logging.InstallLog.writeToFile("LSCPD successfully installed!")

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installLSCPD]")

    def setupComodoRules(self):
        try:
            os.chdir(self.cwd)

            extractLocation = "/usr/local/lscp/modsec"

            command = "mkdir -p /usr/local/lscp/modsec"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            try:
                if os.path.exists('comodo.tar.gz'):
                    os.remove('comodo.tar.gz')
            except:
                pass

            command = "wget https://cyberpanel.net/modsec/comodo.tar.gz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "tar -zxf comodo.tar.gz -C /usr/local/lscp/modsec"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ###

            modsecConfPath = "/usr/local/lscp/conf/modsec.conf"

            modsecConfig = """
        module mod_security {
        ls_enabled 0
        modsecurity  on
        modsecurity_rules `
        SecDebugLogLevel 0
        SecDebugLog /usr/local/lscp/logs/modsec.log
        SecAuditEngine on
        SecAuditLogRelevantStatus "^(?:5|4(?!04))"
        SecAuditLogParts AFH
        SecAuditLogType Serial
        SecAuditLog /usr/local/lscp/logs/auditmodsec.log
        SecRuleEngine Off
        `
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/modsecurity.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/00_Init_Initialization.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/01_Init_AppsInitialization.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/02_Global_Generic.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/03_Global_Agents.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/04_Global_Domains.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/05_Global_Backdoor.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/06_XSS_XSS.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/07_Global_Other.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/08_Bruteforce_Bruteforce.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/09_HTTP_HTTP.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/10_HTTP_HTTPDoS.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/11_HTTP_Protocol.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/12_HTTP_Request.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/13_Outgoing_FilterGen.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/14_Outgoing_FilterASP.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/15_Outgoing_FilterPHP.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/16_Outgoing_FilterSQL.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/17_Outgoing_FilterOther.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/18_Outgoing_FilterInFrame.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/19_Outgoing_FiltersEnd.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/20_PHP_PHPGen.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/21_SQL_SQLi.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/22_Apps_Joomla.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/23_Apps_JComponent.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/24_Apps_WordPress.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/25_Apps_WPPlugin.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/26_Apps_WHMCS.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/27_Apps_Drupal.conf
            modsecurity_rules_file /usr/local/lscp/modsec/comodo/28_Apps_OtherApps.conf
        }
        """

            writeToFile = open(modsecConfPath, 'w')
            writeToFile.write(modsecConfig)
            writeToFile.close()

            ###

            command = "chown -R lscpd:lscpd /usr/local/lscp/modsec"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            return 1

        except BaseException as msg:
            logging.InstallLog.writeToFile("[ERROR]" + str(msg))
            return 0

    def setupPort(self):
        try:
            ###
            bindConfPath = "/usr/local/lscp/conf/bind.conf"

            writeToFile = open(bindConfPath, 'w')
            writeToFile.write("*:" + self.port)
            writeToFile.close()

        except:
            return 0

    def setupPythonWSGI(self):
        try:

            command = "wget http://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-1.4.tgz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "tar xf wsgi-lsapi-1.4.tgz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir("wsgi-lsapi-1.4")

            command = "/usr/local/CyberPanel/bin/python ./configure.py"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "make"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if not os.path.exists('/usr/local/CyberCP/bin/'):
                os.mkdir('/usr/local/CyberCP/bin/')

            command = "cp lswsgi /usr/local/CyberCP/bin/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir(self.cwd)

        except:
            return 0

    def setupLSCPDDaemon(self):
        try:

            preFlightsChecks.stdOut("Trying to setup LSCPD Daemon!")
            logging.InstallLog.writeToFile("Trying to setup LSCPD Daemon!")

            os.chdir(self.cwd)

            shutil.copy("lscpd/lscpd.service", "/etc/systemd/system/lscpd.service")
            shutil.copy("lscpd/lscpdctrl", "/usr/local/lscp/bin/lscpdctrl")

            ##

            command = 'chmod +x /usr/local/lscp/bin/lscpdctrl'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            path = "/usr/local/lscpd/admin/"

            command = "mkdir -p " + path
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            path = "/usr/local/CyberCP/conf/"
            command = "mkdir -p " + path
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            path = "/usr/local/CyberCP/conf/token_env"
            writeToFile = open(path, "w")
            writeToFile.write("abc\n")
            writeToFile.close()

            command = "chmod 600 " + path
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##
            command = 'systemctl enable lscpd.service'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##
            count = 0

            # In Ubuntu, the library that lscpd looks for is libpcre.so.1, but the one it installs is libpcre.so.3...
            if self.distro == ubuntu:
                command = 'ln -s /lib/x86_64-linux-gnu/libpcre.so.3 /lib/x86_64-linux-gnu/libpcre.so.1'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'systemctl start lscpd'
            #preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            preFlightsChecks.stdOut("LSCPD Daemon Set!")

            logging.InstallLog.writeToFile("LSCPD Daemon Set!")


        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setupLSCPDDaemon]")
            return 0

        return 1

    def setup_cron(self):

        try:
            ## first install crontab

            if self.distro == centos or self.distro == cent8:
                command = 'yum install cronie -y'
            else:
                command = 'apt-get -y install cron'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == centos or self.distro == cent8:
                command = 'systemctl enable crond'
            else:
                command = 'systemctl enable cron'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == centos or self.distro == cent8:
                command = 'systemctl start crond'
            else:
                command = 'systemctl start cron'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            cronFile = open("/var/spool/cron/root", "a")
            cronFile.writelines("0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1" + "\n")
            cronFile.writelines("0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1" + "\n")
            cronFile.writelines("0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1" + "\n")
            cronFile.writelines("0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1" + "\n")
            cronFile.writelines("0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1" + "\n")
            cronFile.close()

            command = 'chmod +x /usr/local/CyberCP/plogical/findBWUsage.py'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'chmod +x /usr/local/CyberCP/plogical/upgradeCritical.py'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'chmod +x /usr/local/CyberCP/postfixSenderPolicy/client.py'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == centos or self.distro == cent8:
                command = 'systemctl restart crond.service'
            else:
                command = 'systemctl restart cron.service'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setup_cron]")
            return 0

    def install_default_keys(self):
        try:
            path = "/root/.ssh"

            if not os.path.exists(path):
                os.mkdir(path)

            command = "ssh-keygen -f /root/.ssh/cyberpanel -t rsa -N ''"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_default_keys]")
            return 0

    def install_rsync(self):
        try:
            if self.distro == centos or self.distro == cent8:
                command = 'yum -y install rsync'
            else:
                command = 'apt-get -y install rsync'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_rsync]")
            return 0

    def test_Requests(self):
        try:
            import requests
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
        except BaseException as msg:

            command = "pip uninstall --yes urllib3"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "pip uninstall --yes requests"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "pip install http://mirror.cyberpanel.net/urllib3-1.22.tar.gz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "pip install http://mirror.cyberpanel.net/requests-2.18.4.tar.gz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def installation_successfull(self):
        print("###################################################################")
        print("                CyberPanel Successfully Installed                  ")
        print("                                                                   ")

        print("                                                                   ")
        print("                                                                   ")

        print(("                Visit: https://" + self.ipAddr + ":8090                "))
        print("                Username: admin                                    ")
        print("                Password: 1234567                                  ")

        print("###################################################################")

    def modSecPreReqs(self):
        try:

            pathToRemoveGarbageFile = os.path.join(self.server_root_path, "modules/mod_security.so")
            os.remove(pathToRemoveGarbageFile)

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [modSecPreReqs]")
            return 0

    def installOpenDKIM(self):
        try:
            if self.distro == centos or self.distro == cent8:
                command = 'yum -y install opendkim'
            else:
                command = 'apt-get -y install opendkim'

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == ubuntu:
                command = 'apt install opendkim-tools -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'mkdir -p /etc/opendkim/keys/'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [installOpenDKIM]")
            return 0

        return 1

    def configureOpenDKIM(self):
        try:

            ## Configure OpenDKIM specific settings

            openDKIMConfigurePath = "/etc/opendkim.conf"

            configData = """
Mode	sv
Canonicalization	relaxed/simple
KeyTable	refile:/etc/opendkim/KeyTable
SigningTable	refile:/etc/opendkim/SigningTable
ExternalIgnoreList	refile:/etc/opendkim/TrustedHosts
InternalHosts	refile:/etc/opendkim/TrustedHosts
"""

            writeToFile = open(openDKIMConfigurePath, 'a')
            writeToFile.write(configData)
            writeToFile.close()

            ## Configure postfix specific settings

            postfixFilePath = "/etc/postfix/main.cf"

            configData = """
smtpd_milters = inet:127.0.0.1:8891
non_smtpd_milters = $smtpd_milters
milter_default_action = accept
"""

            writeToFile = open(postfixFilePath, 'a')
            writeToFile.write(configData)
            writeToFile.close()

            if self.distro == ubuntu:
                data = open(openDKIMConfigurePath, 'r').readlines()
                writeToFile = open(openDKIMConfigurePath, 'w')
                for items in data:
                    if items.find('Socket') > -1 and items.find('local:') and items[0] != '#':
                        writeToFile.writelines('Socket  inet:8891@localhost\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

            #### Restarting Postfix and OpenDKIM

            command = "systemctl start opendkim"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "systemctl enable opendkim"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = "systemctl start postfix"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)


        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [configureOpenDKIM]")
            return 0

        return 1

    def setupCLI(self):
        command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def setupPHPAndComposer(self):
        try:

            if self.distro == ubuntu:
                if not os.access('/usr/local/lsws/lsphp70/bin/php', os.R_OK):
                    if os.access('/usr/local/lsws/lsphp70/bin/php7.0', os.R_OK):
                        os.symlink('/usr/local/lsws/lsphp70/bin/php7.0', '/usr/local/lsws/lsphp70/bin/php')
                if not os.access('/usr/local/lsws/lsphp71/bin/php', os.R_OK):
                    if os.access('/usr/local/lsws/lsphp71/bin/php7.1', os.R_OK):
                        os.symlink('/usr/local/lsws/lsphp71/bin/php7.1', '/usr/local/lsws/lsphp71/bin/php')
                if not os.access('/usr/local/lsws/lsphp72/bin/php', os.R_OK):
                    if os.access('/usr/local/lsws/lsphp72/bin/php7.2', os.R_OK):
                        os.symlink('/usr/local/lsws/lsphp72/bin/php7.2', '/usr/local/lsws/lsphp72/bin/php')

            command = "cp /usr/local/lsws/lsphp71/bin/php /usr/bin/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir(self.cwd)

            command = "chmod +x composer.sh"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "./composer.sh"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setupPHPAndComposer]")
            return 0

    @staticmethod
    def installOne(package):
        res = subprocess.call(shlex.split('apt-get -y install ' + package))
        if res != 0:
            preFlightsChecks.stdOut("Error #" + str(res) + ' installing:' + package + '.  This may not be an issue ' \
                                                                                      'but may affect installation of something later',
                                    1)

        return res  # Though probably not used

    def setupVirtualEnv(self, distro):
        try:

            ##

            count = 0
            if distro == ubuntu:
                # You can't install all at once!  So install one at a time.
                preFlightsChecks.stdOut("Installing python prerequisites", 1)
                preFlightsChecks.installOne('libcurl4-gnutls-dev')
                preFlightsChecks.installOne('libgnutls-dev')
                preFlightsChecks.installOne('libgcrypt20-dev')
                preFlightsChecks.installOne('libattr1')
                preFlightsChecks.installOne('libattr1-dev')
                preFlightsChecks.installOne('liblzma-dev')
                preFlightsChecks.installOne('libgpgme-dev')
                preFlightsChecks.installOne('libmariadbclient-dev')
                preFlightsChecks.installOne('libcurl4-gnutls-dev')
                preFlightsChecks.installOne('libssl-dev')
                preFlightsChecks.installOne('nghttp2')
                preFlightsChecks.installOne('libnghttp2-dev')
                preFlightsChecks.installOne('idn2')
                preFlightsChecks.installOne('libidn2-dev')
                preFlightsChecks.installOne('libidn2-0-dev')
                preFlightsChecks.installOne('librtmp-dev')
                preFlightsChecks.installOne('libpsl-dev')
                preFlightsChecks.installOne('nettle-dev')
                preFlightsChecks.installOne('libgnutls28-dev')
                preFlightsChecks.installOne('libldap2-dev')
                preFlightsChecks.installOne('libgssapi-krb5-2')
                preFlightsChecks.installOne('libk5crypto3')
                preFlightsChecks.installOne('libkrb5-dev')
                preFlightsChecks.installOne('libcomerr2')
                preFlightsChecks.installOne('libldap2-dev')
                preFlightsChecks.installOne('python-gpg')
                preFlightsChecks.installOne('python-gpgme')
            else:
                command = "yum install -y libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel"
                preFlightsChecks.call(command, distro, command, command, 1, 1, os.EX_OSERR)

            ##

            os.chdir(self.cwd)

            command = "chmod +x venvsetup.sh"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "./venvsetup.sh"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setupVirtualEnv]")
            return 0

    @staticmethod
    def enableDisableDNS(state):
        try:
            servicePath = '/home/cyberpanel/powerdns'

            if state == 'off':

                command = 'sudo systemctl stop pdns'
                subprocess.call(shlex.split(command))

                command = 'sudo systemctl disable pdns'
                subprocess.call(shlex.split(command))

                try:
                    os.remove(servicePath)
                except:
                    pass

            else:
                writeToFile = open(servicePath, 'w+')
                writeToFile.close()

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [enableDisableDNS]")
            return 0

    @staticmethod
    def enableDisableEmail(state):
        try:
            servicePath = '/home/cyberpanel/postfix'

            if state == 'off':

                command = 'sudo systemctl stop postfix'
                subprocess.call(shlex.split(command))

                command = 'sudo systemctl disable postfix'
                subprocess.call(shlex.split(command))

                try:
                    os.remove(servicePath)
                except:
                    pass

            else:
                writeToFile = open(servicePath, 'w+')
                writeToFile.close()

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [enableDisableEmail]")
            return 0

    @staticmethod
    def enableDisableFTP(state, distro):
        try:
            servicePath = '/home/cyberpanel/pureftpd'

            if state == 'off':

                command = 'sudo systemctl stop ' + preFlightsChecks.pureFTPDServiceName(distro)
                subprocess.call(shlex.split(command))

                command = 'sudo systemctl disable ' + preFlightsChecks.pureFTPDServiceName(distro)
                subprocess.call(shlex.split(command))

                try:
                    os.remove(servicePath)
                except:
                    pass

            else:
                writeToFile = open(servicePath, 'w+')
                writeToFile.close()

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [enableDisableEmail]")
            return 0

    @staticmethod
    def setUpFirstAccount():
        try:
            command = 'python /usr/local/CyberCP/plogical/adminPass.py --password 1234567'
            subprocess.call(shlex.split(command))
        except:
            pass

    @staticmethod
    def p3(distro):
        ### Virtual Env 3

        if distro == centos:
            command = 'yum -y install python36 -y'
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

            command = 'virtualenv -p python3 /usr/local/CyberPanel/p3'
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

            env_path = '/usr/local/CyberPanel/p3'
            subprocess.call(['virtualenv', env_path])
            activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
            exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

            command = "pip3 install --ignore-installed -r %s" % ('/usr/local/CyberCP/WebTerminal/requirments.txt')
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

        else:
            command = 'apt install -y python3-pip'
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

            command = 'apt install build-essential libssl-dev libffi-dev python3-dev -y'
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

            command = 'apt install -y python3-venv'
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

            command = 'virtualenv -p python3 /usr/local/CyberPanel/p3'
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

            env_path = '/usr/local/CyberPanel/p3'
            subprocess.call(['virtualenv', env_path])
            activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
            exec(compile(open(activate_this, "rb").read(), activate_this, 'exec'), dict(__file__=activate_this))

            command = "pip3 install --ignore-installed -r %s" % ('/usr/local/CyberCP/WebTerminal/requirments.txt')
            preFlightsChecks.call(command, distro, '[install python36]',
                                  'install python36',
                                  1, 0, os.EX_OSERR)

    def installRestic(self):
        try:

            CentOSPath = '/etc/redhat-release'

            if os.path.exists(CentOSPath):

                command = 'yum install yum-utils -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'yum-config-manager --add-repo https://copr.fedorainfracloud.org/coprs/copart/restic/repo/epel-7/copart-restic-epel-7.repo'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'yum install restic -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            else:
                command = 'apt-get update -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'apt-get install restic -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            cronTab = '/etc/crontab'

            data = open(cronTab, 'r').read()

            if data.find('IncScheduler') == -1:
                cronJob = '0 12 * * * root /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Daily\n'

                writeToFile = open(cronTab, 'a')
                writeToFile.writelines(cronJob)

                cronJob = '0 0 * * 0 root /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Weekly\n'
                writeToFile.writelines(cronJob)
                writeToFile.close()
        except:
            pass

    def installCLScripts(self):
        try:

            CentOSPath = '/etc/redhat-release'

            if os.path.exists(CentOSPath):
                command = 'mkdir -p /opt/cpvendor/etc/'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                content = """[integration_scripts]

panel_info = /usr/local/CyberCP/CLScript/panel_info.py
packages = /usr/local/CyberCP/CLScript/CloudLinuxPackages.py
users = /usr/local/CyberCP/CLScript/CloudLinuxUsers.py
domains = /usr/local/CyberCP/CLScript/CloudLinuxDomains.py
resellers = /usr/local/CyberCP/CLScript/CloudLinuxResellers.py
admins = /usr/local/CyberCP/CLScript/CloudLinuxAdmins.py
db_info = /usr/local/CyberCP/CLScript/CloudLinuxDB.py

[lvemanager_config]
ui_user_info =/usr/local/CyberCP/CLScript/UserInfo.py
base_path = /usr/local/lvemanager
run_service = 1
service_port = 9000
"""

                writeToFile = open('/opt/cpvendor/etc/integration.ini', 'w')
                writeToFile.write(content)
                writeToFile.close()

                command = 'mkdir -p /etc/cagefs/exclude'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                content = """cyberpanel
docker
ftpuser
lscpd
opendkim
pdns
vmail
"""

                writeToFile = open('/etc/cagefs/exclude/cyberpanelexclude', 'w')
                writeToFile.write(content)
                writeToFile.close()

        except:
            pass

    def installAcme(self):
        command = 'wget -O -  https://get.acme.sh | sh'
        subprocess.call(command, shell=True)

        command = '/root/.acme.sh/acme.sh --upgrade --auto-upgrade'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def installRedis(self):
        if self.distro == ubuntu:
            command = 'apt install redis-server -y'
        elif self.distro == centos:
            command = 'yum install redis -y'
        else:
            command = 'dnf install redis -y'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## install redis conf

        redisConf = '/usr/local/lsws/conf/dvhost_redis.conf'

        writeToFile = open(redisConf, 'w')
        writeToFile.write('127.0.0.1,6379,<auth_password>\n')
        writeToFile.close()

        confPath = '/usr/local/lsws/conf/'

        if os.path.exists('%shttpd.conf' % (confPath)):
            os.remove('%shttpd.conf' % (confPath))

        shutil.copy('litespeed/httpd.conf', confPath)

        ## start and enable

        command = 'systemctl start redis'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'systemctl enable redis'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)




def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('publicip', help='Please enter public IP for your VPS or dedicated server.')
    parser.add_argument('--mysql', help='Specify number of MySQL instances to be used.')
    parser.add_argument('--postfix', help='Enable or disable Email Service.')
    parser.add_argument('--powerdns', help='Enable or disable DNS Service.')
    parser.add_argument('--ftp', help='Enable or disable ftp Service.')
    parser.add_argument('--ent', help='Install LS Ent or OpenLiteSpeed')
    parser.add_argument('--serial', help='Install LS Ent or OpenLiteSpeed')
    parser.add_argument('--port', help='LSCPD Port')
    parser.add_argument('--redis', help='vHosts on Redis - Requires LiteSpeed Enterprise')
    args = parser.parse_args()

    logging.InstallLog.writeToFile("Starting CyberPanel installation..")
    preFlightsChecks.stdOut("Starting CyberPanel installation..")

    if args.ent == None:
        ent = 0
        preFlightsChecks.stdOut("OpenLiteSpeed web server will be installed.")
    else:
        if args.ent == 'ols':
            ent = 0
            preFlightsChecks.stdOut("OpenLiteSpeed web server will be installed.")
        else:
            preFlightsChecks.stdOut("LiteSpeed Enterprise web server will be installed.")
            ent = 1
            if args.serial != None:
                serial = args.serial
                preFlightsChecks.stdOut("LiteSpeed Enterprise Serial detected: " + serial)
            else:
                preFlightsChecks.stdOut("Installation failed, please specify LiteSpeed Enterprise key using --serial")
                os._exit(0)

    ## Writing public IP

    try:
        os.mkdir("/etc/cyberpanel")
    except:
        pass

    machineIP = open("/etc/cyberpanel/machineIP", "w")
    machineIP.writelines(args.publicip)
    machineIP.close()

    cwd = os.getcwd()

    distro = get_distro()
    checks = preFlightsChecks("/usr/local/lsws/", args.publicip, "/usr/local", cwd, "/usr/local/CyberCP", distro)
    checks.mountTemp()

#    if distro == ubuntu:
#        os.chdir("/etc/cyberpanel")

    if args.port == None:
        port = "8090"
    else:
        port = args.port

    if args.mysql == None:
        mysql = 'One'
        preFlightsChecks.stdOut("Single MySQL instance version will be installed.")
    else:
        mysql = args.mysql
        preFlightsChecks.stdOut("Dobule MySQL instance version will be installed.")

    checks.checkPythonVersion()
    checks.setup_account_cyberpanel()
    checks.installCyberPanelRepo()
    #checks.install_gcc()
    if distro == centos:
        checks.install_python_setup_tools()
    #checks.install_python_mysql_library()

    import installCyberPanel

    if ent == 0:
        installCyberPanel.Main(cwd, mysql, distro, ent, None, port, args.ftp, args.powerdns, args.publicip)
    else:
        installCyberPanel.Main(cwd, mysql, distro, ent, serial, port, args.ftp, args.powerdns, args.publicip)

    checks.setupPHPAndComposer()
    checks.fix_selinux_issue()
    checks.install_psmisc()

    if args.postfix == None:
        checks.install_postfix_davecot()
        checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
        checks.setup_postfix_davecot_config(mysql)
    else:
        if args.postfix == 'ON':
            checks.install_postfix_davecot()
            checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
            checks.setup_postfix_davecot_config(mysql)

    checks.install_unzip()
    checks.install_zip()
    checks.install_rsync()

    checks.installFirewalld()

    checks.install_default_keys()

    checks.download_install_CyberPanel(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
    checks.downoad_and_install_raindloop()
    checks.download_install_phpmyadmin()
    checks.setupCLI()
    checks.setup_cron()
    checks.installRestic()
    checks.installAcme()
    # checks.installdnsPython()

    ## Install and Configure OpenDKIM.

    if args.postfix == None:
        checks.installOpenDKIM()
        checks.configureOpenDKIM()
    else:
        if args.postfix == 'ON':
            checks.installOpenDKIM()
            checks.configureOpenDKIM()

    checks.modSecPreReqs()
    checks.installLSCPD()
    checks.setupPort()
    checks.setupPythonWSGI()
    checks.setupLSCPDDaemon()
    checks.fixCyberPanelPermissions()

    if args.postfix != None:
        checks.enableDisableEmail(args.postfix.lower())
    else:
        preFlightsChecks.stdOut("Postfix will be installed and enabled.")
        checks.enableDisableEmail('on')

    if args.powerdns != None:
        checks.enableDisableDNS(args.powerdns.lower())
    else:
        preFlightsChecks.stdOut("PowerDNS will be installed and enabled.")
        checks.enableDisableDNS('on')

    if args.ftp != None:
        checks.enableDisableFTP(args.ftp.lower(), distro)
    else:
        preFlightsChecks.stdOut("Pure-FTPD will be installed and enabled.")
        checks.enableDisableFTP('on', distro)

    if args.redis != None:
        checks.installRedis()

    checks.installCLScripts()
    logging.InstallLog.writeToFile("CyberPanel installation successfully completed!")


if __name__ == "__main__":
    main()
