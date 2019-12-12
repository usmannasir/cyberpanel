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

            if subprocess.check_output('systemd-detect-virt').find("openvz") > -1:

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
            output = subprocess.check_output(shlex.split(command))

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
            preFlightsChecks.stdOut("You are running Unsupported python version, please install python 2.7")
            os._exit(0)

    def setup_account_cyberpanel(self):
        try:

            if self.distro == centos:
                command = "yum install sudo -y"
                preFlightsChecks.call(command, self.distro, command,
                                      command,
                                      1, 0, os.EX_OSERR)

            ##

            if self.distro == ubuntu:
                # self.stdOut("Fix sudoers")
                # try:
                #     fileName = '/etc/sudoers'
                #     data = open(fileName, 'r').readlines()
                #
                #     writeDataToFile = open(fileName, 'w')
                #     for line in data:
                #         if line[:5] == '%sudo':
                #             writeDataToFile.write('%sudo ALL=(ALL:ALL) NOPASSWD: ALL\n')
                #         else:
                #             writeDataToFile.write(line)
                #     writeDataToFile.close()
                # except IOError as err:
                #     self.stdOut("Error in fixing sudoers file: " + str(err), 1, 1, os.EX_OSERR)

                self.stdOut("Add Cyberpanel user")
                command = 'adduser --disabled-login --gecos "" cyberpanel'
                preFlightsChecks.call(command, self.distro, command,command,1, 1, os.EX_OSERR)

            else:
                command = "useradd -s /bin/false cyberpanel"
                preFlightsChecks.call(command, self.distro, command,command,1, 1, os.EX_OSERR)

                # ##
                #
                # command = "usermod -aG wheel cyberpanel"
                # preFlightsChecks.call(command, self.distro, '[setup_account_cyberpanel]',
                #                       'add user cyberpanel',
                #                       1, 0, os.EX_OSERR)

            ###############################

            # path = "/etc/sudoers"
            #
            # data = open(path, 'r').readlines()
            #
            # writeToFile = open(path, 'w')
            #
            # for items in data:
            #     if items.find("wheel	ALL=(ALL)	NOPASSWD: ALL") > -1:
            #         writeToFile.writelines("%wheel	ALL=(ALL)	NOPASSWD: ALL")
            #     else:
            #         writeToFile.writelines(items)
            #
            # writeToFile.close()

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

        else:
            command = 'rpm -ivh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def enableEPELRepo(self):
        command = 'yum -y install epel-release'
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def install_pip(self):
        self.stdOut("Install pip")
        if self.distro == ubuntu:
            command = "apt-get -y install python-pip"
        else:
            command = "yum -y install python-pip"

        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

    def install_python_dev(self):
        self.stdOut("Install python development environment")

        if self.distro == centos:
            command = "yum -y install python-devel"
        else:
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

        if self.distro == centos:
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

        ### Put correct mysql passwords in settings f