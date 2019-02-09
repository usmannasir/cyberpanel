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

# There can not be peace without first a great suffering.

# distros

centos = 0
ubuntu = 1


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
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")
        print("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + message + "\n")
        print ("[" + time.strftime(
            "%I-%M-%S-%a-%b-%Y") + "] #########################################################################\n")

        if log:
            logging.InstallLog.writeToFile(message)
        if do_exit:
            sys.exit(code)

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
        preFlightsChecks.stdOut(message + " " + bracket, log)
        count = 0
        while True:
            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(distro, res):
                count = count + 1
                preFlightsChecks.stdOut(message + " failed, trying again, try number: " + str(count))
                if count == 3:
                    fatal_message = ''
                    if do_exit:
                        fatal_message = '.  Fatal error, see /var/log/installLogs.txt for full details'

                    preFlightsChecks.stdOut("[ERROR] We are not able to " + message + ' return code: ' + str(res) +
                                            fatal_message + " " + bracket, 1, do_exit, code)
                    return False
            else:
                preFlightsChecks.stdOut(message + ' successful', log)
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

        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + "[checkIfSeLinuxDisabled]")
            logging.InstallLog.writeToFile("SELinux Check OK. [checkIfSeLinuxDisabled]")
            preFlightsChecks.stdOut("SELinux Check OK.")
            return 1

    def checkPythonVersion(self):
        if sys.version_info[0] == 2 and sys.version_info[1] == 7:
            return 1
        else:
            preFlightsChecks.stdOut("You are running Unsupported python version, please install python 2.7")
            os._exit(0)

    def setup_account_cyberpanel(self):
        try:

            if self.distro == centos:
                command = "yum install sudo -y"
                preFlightsChecks.call(command, self.distro, '[setup_account_cyberpanel]',
                                      'Install sudo.',
                                      1, 0, os.EX_OSERR)

            ##

            count = 0

            if self.distro == ubuntu:
                self.stdOut("Fix sudoers")
                try:
                    fileName = '/etc/sudoers'
                    data = open(fileName, 'r').readlines()

                    writeDataToFile = open(fileName, 'w')
                    for line in data:
                        if line[:5] == '%sudo':
                            writeDataToFile.write('%sudo ALL=(ALL:ALL) NOPASSWD: ALL\n')
                        else:
                            writeDataToFile.write(line)
                    writeDataToFile.close()
                except IOError as err:
                    self.stdOut("Error in fixing sudoers file: " + str(err), 1, 1, os.EX_OSERR)

                self.stdOut("Add Cyberpanel user")
                command = "useradd cyberpanel -m -U -G sudo"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)
                if res != 0 and res != 9:
                    logging.InstallLog.writeToFile("Can not create cyberpanel user, error #" + str(res))
                    preFlightsChecks.stdOut("Can not create cyberpanel user, error #" + str(res))
                    os._exit(0)
                if res == 0:
                    logging.InstallLog.writeToFile("CyberPanel user added")
                    preFlightsChecks.stdOut("CyberPanel user added")

            else:
                command = "adduser cyberpanel"
                preFlightsChecks.call(command, self.distro, '[setup_account_cyberpanel]',
                                      'add user cyberpanel',
                                      1, 0, os.EX_OSERR)

                ##

                command = "usermod -aG wheel cyberpanel"
                preFlightsChecks.call(command, self.distro, '[setup_account_cyberpanel]',
                                      'add user cyberpanel',
                                      1, 0, os.EX_OSERR)

            ###############################

            path = "/etc/sudoers"

            data = open(path, 'r').readlines()

            writeToFile = open(path, 'w')

            for items in data:
                if items.find("wheel	ALL=(ALL)	NOPASSWD: ALL") > -1:
                    writeToFile.writelines("%wheel	ALL=(ALL)	NOPASSWD: ALL")
                else:
                    writeToFile.writelines(items)

            writeToFile.close()

            ###############################

            command = "mkdir -p /etc/letsencrypt/live/"
            preFlightsChecks.call(command, self.distro, '[setup_account_cyberpanel]',
                                  'add user cyberpanel',
                                  1, 0, os.EX_OSERR)

        except BaseException, msg:
            logging.InstallLog.writeToFile("[ERROR] setup_account_cyberpanel. " + str(msg))

    def yum_update(self):
        try:
            count = 0
            while (1):

                command = 'yum update -y'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("YUM UPDATE FAILED, trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "YUM update failed to run, we are being optimistic that installer will still be able to complete installation. [yum_update]")
                        break
                else:
                    logging.InstallLog.writeToFile("YUM UPDATE ran successfully.")
                    preFlightsChecks.stdOut("YUM UPDATE ran successfully.")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [yum_update]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [yum_update]")
            return 0

        return 1

    def installCyberPanelRepo(self):
        self.stdOut("Install Cyberpanel repo")
        cmd = []
        count = 0

        if self.distro == ubuntu:
            try:
                filename = "enable_lst_debain_repo.sh"
                command = "wget http://rpms.litespeedtech.com/debian/" + filename
                cmd = shlex.split(command)
                res = subprocess.call(cmd)
                if res != 0:
                    logging.InstallLog.writeToFile(
                        "Unable to download Ubuntu CyberPanel installer! [installCyberPanelRepo]:"
                        " Error #" + str(res))
                    preFlightsChecks.stdOut("Unable to download Ubuntu CyberPanel installer! [installCyberPanelRepo]:"
                                            " Error #" + str(res))
                    os._exit(os.EX_NOINPUT)

                os.chmod(filename, S_IRWXU | S_IRWXG)

                command = "./" + filename
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if res != 0:
                    logging.InstallLog.writeToFile("Unable to install Ubuntu CyberPanel! [installCyberPanelRepo]:"
                                                   " Error #" + str(res))
                    preFlightsChecks.stdOut("Unable to install Ubuntu CyberPanel! [installCyberPanelRepo]:"
                                            " Error #" + str(res))
                    os._exit(os.EX_NOINPUT)

            except OSError as err:
                logging.InstallLog.writeToFile("Exception during CyberPanel install: " + str(err))
                preFlightsChecks.stdOut("Exception during CyberPanel install: " + str(err))
                os._exit(os.EX_OSERR)

            except:
                logging.InstallLog.writeToFile("Exception during CyberPanel install")
                preFlightsChecks.stdOut("Exception during CyberPanel install")
                os._exit(os.EX_SOFTWARE)

        else:
            while (1):
                cmd.append("rpm")
                cmd.append("-ivh")
                cmd.append("http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el7.noarch.rpm")
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to add CyberPanel official repository, trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to add CyberPanel official repository, exiting installer! [installCyberPanelRepo]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("CyberPanel Repo added!")
                    preFlightsChecks.stdOut("CyberPanel Repo added!")
                    break

    def enableEPELRepo(self):
        try:
            cmd = []
            count = 0

            while (1):
                cmd.append("yum")
                cmd.append("-y")
                cmd.append("install")
                cmd.append("epel-release")
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to add EPEL repository, trying again, try number: " + str(count) + "\n")
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to add EPEL repository, exiting installer! [enableEPELRepo]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("EPEL Repo added!")
                    preFlightsChecks.stdOut("EPEL Repo added!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableEPELRepo]")
            preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
            os._exit(0)
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableEPELRepo]")
            preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
            os._exit(0)
            return 0

        return 1

    def install_pip(self):
        self.stdOut("Install pip")
        count = 0
        while (1):
            if self.distro == ubuntu:
                command = "apt-get -y install python-pip"
            else:
                command = "yum -y install python-pip"
            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut("Unable to install PIP, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install PIP, exiting installer! [install_pip]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("PIP successfully installed!")
                preFlightsChecks.stdOut("PIP successfully installed!")
                break

    def install_python_dev(self):
        self.stdOut("Install python development environment")
        count = 0
        while (1):
            if self.distro == centos:
                command = "yum -y install python-devel"
            else:
                command = "apt-get -y install python-dev"
            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut(
                    "We are trying to install python development tools, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile(
                        "Unable to install python development tools, exiting installer! [install_python_dev]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("Python development tools successfully installed!")
                preFlightsChecks.stdOut("Python development tools successfully installed!")
                break

    def install_gcc(self):
        self.stdOut("Install gcc")
        count = 0

        while (1):
            if self.distro == centos:
                command = "yum -y install gcc"
            else:
                command = "apt-get -y install gcc"
            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut("Unable to install GCC, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install GCC, exiting installer! [install_gcc]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("GCC Successfully installed!")
                preFlightsChecks.stdOut("GCC Successfully installed!")
                break

    def install_python_setup_tools(self):
        count = 0
        while (1):
            command = "yum -y install python-setuptools"
            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                print("[" + time.strftime(
                    "%I-%M-%S-%a-%b-%Y") + "] " + "Unable to install Python setup tools, trying again, try number: " + str(
                    count) + "\n")
                if count == 3:
                    logging.InstallLog.writeToFile(
                        "Unable to install Python setup tools, exiting installer! [install_python_setup_tools]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("Python setup tools Successfully installed!")
                print("[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + "Python setup tools Successfully installed!")
                break

    def install_python_requests(self):
        try:
            import requests

            ## Un-install ULRLIB3 and requests

            command = "pip uninstall --yes urllib3"
            res = subprocess.call(shlex.split(command))

            command = "pip uninstall --yes requests"
            res = subprocess.call(shlex.split(command))

            ## Install specific versions

            count = 0
            while (1):

                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/urllib3-1.22.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install urllib3 module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install urllib3 module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("urllib3 module Successfully installed!")
                    preFlightsChecks.stdOut("urllib3 module Successfully installed!")
                    break

            count = 0
            while (1):

                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/requests-2.18.4.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install requests module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install requests module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("Requests module Successfully installed!")
                    preFlightsChecks.stdOut("Requests module Successfully installed!")
                    break

        except:

            count = 0
            while (1):

                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/urllib3-1.22.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install urllib3 module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install urllib3 module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("urllib3 module Successfully installed!")
                    preFlightsChecks.stdOut("urllib3 module Successfully installed!")
                    break

            count = 0
            while (1):

                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/requests-2.18.4.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install requests module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install requests module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("Requests module Successfully installed!")
                    preFlightsChecks.stdOut("Requests module Successfully installed!")
                    break

    def install_pexpect(self):
        try:
            import pexpect

            command = "pip uninstall --yes pexpect"
            res = subprocess.call(shlex.split(command))

            count = 0

            while (1):
                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/pexpect-4.4.0.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install pexpect, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install pexpect, exiting installer! [install_pexpect]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("pexpect successfully installed!")
                    preFlightsChecks.stdOut("pexpect successfully installed!")
                    break

        except:
            count = 0
            while (1):
                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/pexpect-4.4.0.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install pexpect, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install pexpect, exiting installer! [install_pexpect]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("pexpect successfully installed!")
                    preFlightsChecks.stdOut("pexpect successfully installed!")
                    break

    def install_django(self):
        count = 0
        while (1):
            command = "pip install django==1.11"

            res = subprocess.call(shlex.split(command))

            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut("Unable to install DJANGO, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install DJANGO, exiting installer! [install_django]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("DJANGO successfully installed!")
                preFlightsChecks.stdOut("DJANGO successfully installed!")
                break

    def install_python_mysql_library(self):
        self.stdOut("Install MySQL python library")
        count = 0
        while (1):
            if self.distro == centos:
                command = "yum -y install MySQL-python"
            else:
                command = "apt-get -y install libmysqlclient-dev"
            res = subprocess.call(shlex.split(command))
            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut("Unable to install MySQL-python, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile(
                        "Unable to install MySQL-python, exiting installer! [install_python_mysql_library]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("MySQL-python successfully installed!")
                preFlightsChecks.stdOut("MySQL-python successfully installed!")
                break

        if self.distro == ubuntu:
            command = "pip install MySQL-python"
            res = subprocess.call(shlex.split(command))
            if res != 0:
                logging.InstallLog.writeToFile(
                    "Unable to install MySQL-python, exiting installer! [install_python_mysql_library] Error: " + str(
                        res))
                preFlightsChecks.stdOut(
                    "Unable to install MySQL-python, exiting installer! [install_python_mysql_library] Error: " + str(
                        res))
                os._exit(os.EX_OSERR)

    def install_gunicorn(self):
        self.stdOut("Install GUnicorn")
        count = 0
        while (1):
            if self.distro == ubuntu:
                command = "pip install gunicorn"
            else:
                command = "easy_install gunicorn"
            res = subprocess.call(shlex.split(command))
            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut("Unable to install GUNICORN, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install GUNICORN, exiting installer! [install_gunicorn]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("GUNICORN successfully installed!")
                preFlightsChecks.stdOut("GUNICORN successfully installed!")
                break

    def setup_gunicorn(self):
        try:

            os.chdir(self.cwd)

            ##

            logging.InstallLog.writeToFile("Configuring Gunicorn..")

            service = "/etc/systemd/system/gunicorn.service"
            socket = "/etc/systemd/system/gunicorn.socket"
            conf = "/etc/tmpfiles.d/gunicorn.conf"

            shutil.copy("gun-configs/gunicorn.service", service)
            shutil.copy("gun-configs/gunicorn.socket", socket)
            shutil.copy("gun-configs/gunicorn.conf", conf)

            logging.InstallLog.writeToFile("Gunicorn Configured!")

            ### Enable at system startup

            count = 0

            while (1):
                command = "systemctl enable gunicorn.socket"
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to enable Gunicorn at system startup, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Gunicorn will not start after system restart, you can manually enable using systemctl enable gunicorn.socket! [setup_gunicorn]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        break
                else:
                    logging.InstallLog.writeToFile("Gunicorn can now start after system restart!")
                    preFlightsChecks.stdOut("Gunicorn can now start after system restart!")
                    break

        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_gunicorn]")
            preFlightsChecks.stdOut("Not able to setup gunicorn, see install log.")

    def install_psutil(self):

        try:
            import psutil

            ##

            command = "pip uninstall --yes psutil"
            res = subprocess.call(shlex.split(command))

            count = 0
            while (1):
                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/psutil-5.4.3.tar.gz"
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install psutil, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install psutil, exiting installer! [install_psutil]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("psutil successfully installed!")
                    preFlightsChecks.stdOut("psutil successfully installed!")
                    break

        except:
            count = 0
            while (1):
                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/psutil-5.4.3.tar.gz"
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install psutil, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to install psutil, exiting installer! [install_psutil]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("psutil successfully installed!")
                    preFlightsChecks.stdOut("psutil successfully installed!")
                    break

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
            logging.InstallLog.writeToFile("fix_selinux_issue problem")

    def install_psmisc(self):
        self.stdOut("Install psmisc")
        count = 0
        while (1):
            if self.distro == centos:
                command = "yum -y install psmisc"
            else:
                command = "apt-get -y install psmisc"
            res = subprocess.call(shlex.split(command))
            if preFlightsChecks.resFailed(self.distro, res):
                count = count + 1
                preFlightsChecks.stdOut("Unable to install psmisc, trying again, try number: " + str(count))
                if count == 3:
                    logging.InstallLog.writeToFile("Unable to install psmisc, exiting installer! [install_psmisc]")
                    preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                    os._exit(0)
            else:
                logging.InstallLog.writeToFile("psmisc successfully installed!")
                preFlightsChecks.stdOut("psmisc successfully installed!")
                break

    def download_install_CyberPanel(self, mysqlPassword, mysql):
        try:
            ## On OpenVZ there is an issue with requests module, which needs to upgrade requests module

            if subprocess.check_output('systemd-detect-virt').find("openvz") > -1:
                command = "pip install --upgrade requests"
                preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                              'Upgrade requests',
                                              1, 0, os.EX_OSERR)
        except:
            pass

        ##

        os.chdir(self.path)

        command = "wget http://cyberpanel.sh/CyberPanel.1.8.1.tar.gz"
        #command = "wget http://cyberpanel.sh/CyberPanelTemp.tar.gz"
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'CyberPanel Download',
                                      1, 1, os.EX_OSERR)

        ##

        count = 0
        command = "tar zxf CyberPanel.1.8.1.tar.gz"
        #command = "tar zxf CyberPanelTemp.tar.gz"
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'Extract CyberPanel',1, 1, os.EX_OSERR)

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

        ### Applying migrations


        os.chdir("CyberCP")

        command = "python manage.py makemigrations"
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'CyberPanel Make Migrations',
                                      1, 1, os.EX_OSERR)

        ##

        command = "python manage.py migrate"
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'CyberPanel Migrate',1, 1, os.EX_OSERR)


        ## Moving static content to lscpd location
        command = 'mv static /usr/local/lscp/cyberpanel'
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'Move static content', 1, 1, os.EX_OSERR)

        ## fix permissions

        command = "chmod -R 744 /usr/local/CyberCP"
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'change permissions /usr/local/CyberCP', 1, 0, os.EX_OSERR)


        ## change owner

        command = "chown -R cyberpanel:cyberpanel /usr/local/CyberCP"
        preFlightsChecks.call(command, self.distro, '[download_install_CyberPanel]',
                                      'change owner /usr/local/CyberCP', 1, 0, os.EX_OSERR)


    def install_unzip(self):
        self.stdOut("Install unzip")
        try:
            if self.distro == centos:
                command = 'yum -y install unzip'
            else:
                command = 'apt-get -y install unzip'

            preFlightsChecks.call(command, self.distro, '[install_unzip]',
                                          'Install unzip', 1, 0, os.EX_OSERR)
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_unzip]")

    def install_zip(self):
        self.stdOut("Install zip")
        try:
            if self.distro == centos:
                command = 'yum -y install zip'
            else:
                command = 'apt-get -y install zip'

            preFlightsChecks.call(command, self.distro, '[install_zip]',
                                          'Install zip', 1, 0, os.EX_OSERR)
        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_zip]")

    def download_install_phpmyadmin(self):
        try:
            os.chdir("/usr/local/lscp/cyberpanel/")

            command = 'wget https://files.phpmyadmin.net/phpMyAdmin/4.8.2/phpMyAdmin-4.8.2-all-languages.zip'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                          'Download PHPMYAdmin', 1, 0, os.EX_OSERR)
            #####

            command = 'unzip phpMyAdmin-4.8.2-all-languages.zip'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                          'Unzip PHPMYAdmin', 1, 0, os.EX_OSERR)


            ###

            os.remove("phpMyAdmin-4.8.2-all-languages.zip")

            command = 'mv phpMyAdmin-4.8.2-all-languages phpmyadmin'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                          'Move PHPMYAdmin', 1, 0, os.EX_OSERR)

            ## Write secret phrase

            rString = ''.join([random.choice(string.ascii_letters + string.digits) for n in xrange(32)])

            data = open('phpmyadmin/config.sample.inc.php', 'r').readlines()

            writeToFile = open('phpmyadmin/config.inc.php', 'w')

            for items in data:
                if items.find('blowfish_secret') > -1:
                    writeToFile.writelines(
                        "$cfg['blowfish_secret'] = '" + rString + "'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n")
                else:
                    writeToFile.writelines(items)

            writeToFile.writelines("$cfg['TempDir'] = '/usr/local/lscp/cyberpanel/phpmyadmin/tmp';\n")

            writeToFile.close()

            os.mkdir('/usr/local/lscp/cyberpanel/phpmyadmin/tmp')

            command = 'chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/phpmyadmin'
            subprocess.call(shlex.split(command))

        except BaseException, msg:
            logging.InstallLog.writeToFile(str(msg) + " [download_install_phpmyadmin]")
            return 0

    ###################################################### Email setup


    def install_postfix_davecot(self):
        self.stdOut("Install dovecot - first remove postfix")
        try:
            if self.distro == centos:
                command = 'yum remove postfix -y'
            else:
                command = 'apt-get -y remove postfix'

            subprocess.call(shlex.split(command))

            self.stdOut("Install dovecot - do the install")
            count = 0
            while (1):
                if self.distro == centos:
                    command = 'yum install -y http://mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64//postfix3-3.2.4-1.gf.el7.x86_64.rpm'
                else:
                    command = 'apt-get -y debconf-utils'
                    subprocess.call(shlex.split(command))
                    file_name = self.cwd + '/pf.unattend.text'
                    pf = open(file_name, 'w')
                    pf.write('postfix postfix/mailname string ' + str(socket.getfqdn() + '\n'))
                    pf.write('postfix postfix/main_mailer_type string "Internet Site"\n')
                    pf.close()
                    command = 'debconf-set-selections ' + file_name
                    subprocess.call(shlex.split(command))
                    command = 'apt-get -y install postfix'
                    # os.remove(file_name)

                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install Postfix, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install Postfix, you will not be able to send mails and rest should work fine! [install_postfix_davecot]")
                        break
                else:
                    logging.InstallLog.writeToFile("Postfix successfully installed!")
                    preFlightsChecks.stdOut("Postfix successfully installed!")
                    break

            count = 0

            while (1):
                if self.distro == centos:
                    command = 'yum install -y http://mirror.ghettoforge.org/distributions/gf/el/7/plus/x86_64//postfix3-mysql-3.2.4-1.gf.el7.x86_64.rpm'
                else:
                    command = 'apt-get -y install dovecot-imapd dovecot-pop3d postfix-mysql'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to install Postfix agent, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install Postfix agent, you will not be able to send mails and rest should work fine! [install_postfix_davecot]")
                        break
                else:
                    logging.InstallLog.writeToFile("Postfix successfully installed!")
                    preFlightsChecks.stdOut("Postfix successfully installed!")
                    break

            count = 0

            while (1):

                if self.distro == centos:
                    command = 'yum -y install dovecot dovecot-mysql'
                else:
                    command = 'apt-get -y install dovecot-mysql'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install Dovecot and Dovecot-MySQL, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install install Dovecot and Dovecot-MySQL, you will not be able to send mails and rest should work fine! [install_postfix_davecot]")
                        break
                else:
                    logging.InstallLog.writeToFile("Dovecot and Dovecot-MySQL successfully installed!")
                    preFlightsChecks.stdOut("Dovecot and Dovecot-MySQL successfully installed!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_postfix_davecot]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_postfix_davecot]")
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

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_email_Passwords]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_email_Passwords]")
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
            self.stdOut("Error converting: " + filename + " from centos defaults to ubuntu defaults: " + str(err), 1,
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

            count = 0

            while (1):
                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to generate SSL for Postfix, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to generate SSL for Postfix, you will not be able to send emails and rest should work fine! [setup_postfix_davecot_config]")
                        return
                else:
                    logging.InstallLog.writeToFile("SSL for Postfix generated!")
                    preFlightsChecks.stdOut("SSL for Postfix generated!")
                    break
            ##

            count = 0

            while (1):

                command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to generate ssl for Dovecot, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to generate SSL for Dovecot, you will not be able to send emails and rest should work fine! [setup_postfix_davecot_config]")
                        return
                else:
                    logging.InstallLog.writeToFile("SSL generated for Dovecot!")
                    preFlightsChecks.stdOut("SSL generated for Dovecot!")
                    break

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

            count = 0

            while (1):

                command = 'chmod o= /etc/postfix/mysql-virtual_domains.cf'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for mysql-virtual_domains.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for mysql-virtual_domains.cf. [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_domains.cf!")
                    preFlightsChecks.stdOut("Permissions changed for mysql-virtual_domains.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chmod o= /etc/postfix/mysql-virtual_forwardings.cf'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for mysql-virtual_forwardings.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for mysql-virtual_forwardings.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_forwardings.cf!")
                    preFlightsChecks.stdOut("Permissions changed for mysql-virtual_forwardings.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chmod o= /etc/postfix/mysql-virtual_mailboxes.cf'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for mysql-virtual_mailboxes.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for mysql-virtual_mailboxes.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_mailboxes.cf!")
                    preFlightsChecks.stdOut("Permissions changed for mysql-virtual_mailboxes.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chmod o= /etc/postfix/mysql-virtual_email2email.cf'
                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for mysql-virtual_email2email.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for mysql-virtual_email2email.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for mysql-virtual_email2email.cf!")
                    preFlightsChecks.stdOut("Permissions changed for mysql-virtual_email2email.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chmod o= ' + main
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for /etc/postfix/main.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for /etc/postfix/main.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for /etc/postfix/main.cf!")
                    preFlightsChecks.stdOut("Permissions changed for /etc/postfix/main.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chmod o= ' + master

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for /etc/postfix/master.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for /etc/postfix/master.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for /etc/postfix/master.cf!")
                    preFlightsChecks.stdOut("Permissions changed for /etc/postfix/master.cf!")
                    break

            #######################################

            count = 0

            while (1):
                command = 'chgrp postfix /etc/postfix/mysql-virtual_domains.cf'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for mysql-virtual_domains.cf, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for mysql-virtual_domains.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for mysql-virtual_domains.cf!")
                    preFlightsChecks.stdOut("Group changed for mysql-virtual_domains.cf!")
                    break

            ##

            count = 0

            while (1):
                command = 'chgrp postfix /etc/postfix/mysql-virtual_forwardings.cf'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for mysql-virtual_forwardings.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for mysql-virtual_forwardings.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for mysql-virtual_forwardings.cf!")
                    preFlightsChecks.stdOut("Group changed for mysql-virtual_forwardings.cf!")
                    break

            ##

            count = 0

            while (1):
                command = 'chgrp postfix /etc/postfix/mysql-virtual_mailboxes.cf'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for mysql-virtual_mailboxes.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for mysql-virtual_mailboxes.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for mysql-virtual_mailboxes.cf!")
                    preFlightsChecks.stdOut("Group changed for mysql-virtual_mailboxes.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chgrp postfix /etc/postfix/mysql-virtual_email2email.cf'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for mysql-virtual_email2email.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for mysql-virtual_email2email.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for mysql-virtual_email2email.cf!")
                    preFlightsChecks.stdOut("Group changed for mysql-virtual_email2email.cf!")
                    break

            ##

            count = 0
            while (1):
                command = 'chgrp postfix ' + main
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for /etc/postfix/main.cf, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for /etc/postfix/main.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for /etc/postfix/main.cf!")
                    preFlightsChecks.stdOut("Group changed for /etc/postfix/main.cf!")
                    break

            ##

            count = 0

            while (1):

                command = 'chgrp postfix ' + master

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for /etc/postfix/master.cf, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for /etc/postfix/master.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for /etc/postfix/master.cf!")
                    preFlightsChecks.stdOut("Group changed for /etc/postfix/master.cf!")
                    break

            ######################################## users and groups

            count = 0

            while (1):

                command = 'groupadd -g 5000 vmail'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to add system group vmail, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to add system group vmail! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("System group vmail created successfully!")
                    preFlightsChecks.stdOut("System group vmail created successfully!")
                    break

            ##

            count = 0

            while (1):

                command = 'useradd -g vmail -u 5000 vmail -d /home/vmail -m'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to add system user vmail, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to add system user vmail! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("System user vmail created successfully!")
                    preFlightsChecks.stdOut("System user vmail created successfully!")
                    break

            ######################################## Further configurations

            # hostname = socket.gethostname()

            ################################### Restart postix

            count = 0

            while (1):

                command = 'systemctl enable postfix.service'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to add Postfix to system startup, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to enable Postfix to run at system restart you can manually do this using systemctl enable postfix.service! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("postfix.service successfully enabled!")
                    preFlightsChecks.stdOut("postfix.service successfully enabled!")
                    break

            ##

            count = 0

            while (1):

                command = 'systemctl start  postfix.service'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to start Postfix, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to start Postfix, you can not send email until you manually start Postfix using systemctl start postfix.service! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("postfix.service started successfully!")
                    preFlightsChecks.stdOut("postfix.service started successfully!")
                    break

            ######################################## Permissions

            count = 0

            while (1):

                command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change group for /etc/dovecot/dovecot-sql.conf.ext, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change group for /etc/dovecot/dovecot-sql.conf.ext! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Group changed for /etc/dovecot/dovecot-sql.conf.ext!")
                    preFlightsChecks.stdOut("Group changed for /etc/dovecot/dovecot-sql.conf.ext!")
                    break
            ##


            count = 0

            while (1):

                command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for /etc/dovecot/dovecot-sql.conf.ext, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for /etc/dovecot/dovecot-sql.conf.ext! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for /etc/dovecot/dovecot-sql.conf.ext!")
                    preFlightsChecks.stdOut("Permissions changed for /etc/dovecot/dovecot-sql.conf.ext!")
                    break

            ################################### Restart davecot

            count = 0

            while (1):

                command = 'systemctl enable dovecot.service'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to enable dovecot.service, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to enable dovecot.service! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("dovecot.service successfully enabled!")
                    preFlightsChecks.stdOut("dovecot.service successfully enabled!")
                    break

            ##


            count = 0

            while (1):
                command = 'systemctl start dovecot.service'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to start dovecot.service, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to start dovecot.service! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("dovecot.service successfully started!")
                    preFlightsChecks.stdOut("dovecot.service successfully started!")
                    break

            ##

            count = 0

            while (1):

                command = 'systemctl restart  postfix.service'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to restart postfix.service, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to restart postfix.service! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("dovecot.service successfully restarted!")
                    preFlightsChecks.stdOut("postfix.service successfully restarted!")
                    break

            ## chaging permissions for main.cf

            count = 0

            while (1):

                command = "chmod 755 " + main
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for /etc/postfix/main.cf, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for /etc/postfix/main.cf! [setup_postfix_davecot_config]")
                        break
                else:
                    logging.InstallLog.writeToFile("Permissions changed for /etc/postfix/main.cf!")
                    preFlightsChecks.stdOut("Permissions changed for /etc/postfix/main.cf!")
                    break

            if self.distro == ubuntu:
                command = "mkdir -p /etc/pki/dovecot/private/"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                command = "mkdir -p /etc/pki/dovecot/certs/"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                command = "mkdir -p /etc/opendkim/keys/"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                command = "sed -i 's/auth_mechanisms = plain/#auth_mechanisms = plain/g' /etc/dovecot/conf.d/10-auth.conf"
                subprocess.call(shlex.split(command))

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
                subprocess.call(shlex.split(command))

            logging.InstallLog.writeToFile("Postfix and Dovecot configured")

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_postfix_davecot_config]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_postfix_davecot_config]")
            return 0

        return 1

    def downoad_and_install_raindloop(self):
        try:
            ###########
            count = 0

            while (1):
                command = 'chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to change owner for /usr/local/lscp/cyberpanel/, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to change owner for /usr/local/lscp/cyberpanel/, but installer can continue! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Owner changed for /usr/local/lscp/cyberpanel/!")
                    preFlightsChecks.stdOut("Owner changed for /usr/local/lscp/cyberpanel/!")
                    break
            #######


            os.chdir("/usr/local/lscp/cyberpanel")

            count = 1

            while (1):
                command = 'wget https://www.rainloop.net/repository/webmail/rainloop-community-latest.zip'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to download Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to download Rainloop, installation can continue but you will not be able to send emails! [downoad_and_install_raindloop]")
                        return
                else:
                    logging.InstallLog.writeToFile("Rainloop Downloaded!")
                    preFlightsChecks.stdOut("Rainloop Downloaded!")
                    break

            #############

            count = 0

            while (1):
                command = 'unzip rainloop-community-latest.zip -d /usr/local/lscp/cyberpanel/rainloop'

                cmd = shlex.split(command)

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to unzip rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "We could not unzip Rainloop, so you will not be able to send emails! [downoad_and_install_raindloop]")
                        return
                else:
                    logging.InstallLog.writeToFile("Rainloop successfully unzipped!")
                    preFlightsChecks.stdOut("Rainloop successfully unzipped!")
                    break

            os.remove("rainloop-community-latest.zip")

            #######

            os.chdir("/usr/local/lscp/cyberpanel/rainloop")

            count = 0

            while (1):
                command = 'find . -type d -exec chmod 755 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to change permissions for Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to change permissions for Rainloop, so you will not be able to send emails!! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Rainloop permissions changed!")
                    print(
                        "[" + time.strftime("%I-%M-%S-%a-%b-%Y") + "] " + "Rainloop permissions changed!")
                    break

            #############

            count = 0

            while (1):

                command = 'find . -type f -exec chmod 644 {} \;'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to change permissions for Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to change permissions for Rainloop, so you will not be able to send emails!! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Rainloop permissions changed!")
                    preFlightsChecks.stdOut("Rainloop permissions changed!")
                    break
            ######

            count = 0

            while (1):

                command = 'chown -R lscpd:lscpd .'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to change owner for Rainloop, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to change owner for Rainloop, so you will not be able to send emails!! [downoad_and_install_raindloop]")
                        break
                else:
                    logging.InstallLog.writeToFile("Rainloop owner changed!")
                    preFlightsChecks.stdOut("Rainloop owner changed!")
                    break




        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [downoad_and_install_rainloop]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [downoad_and_install_rainloop]")
            return 0

        return 1

    ###################################################### Email setup ends!


    def reStartLiteSpeed(self):
        try:
            count = 0
            while (1):
                cmd = []

                cmd.append(self.server_root_path + "bin/lswsctrl")
                cmd.append("restart")

                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to restart OpenLiteSpeed, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to restart OpenLiteSpeed! [reStartLiteSpeed]")
                        break
                else:
                    logging.InstallLog.writeToFile("OpenLiteSpeed restarted Successfully!")
                    preFlightsChecks.stdOut("OpenLiteSpeed restarted Successfully!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [reStartLiteSpeed]")
            return 0
        return 1

    def removeUfw(self):
        try:
            preFlightsChecks.stdOut("Checking to see if ufw firewall is installed (will be removed)", 1)
            status = subprocess.check_output(shlex.split('ufw status'))
            preFlightsChecks.stdOut("ufw current status: " + status + "...will be removed")
        except BaseException, msg:
            preFlightsChecks.stdOut("Expected access to ufw not available, do not need to remove it", 1)
            return True
        try:
            preFlightsChecks.call('apt-get -y remove ufw', self.distro, '[remove_ufw]', 'Remove ufw firewall ' +
                                  '(using firewalld)', 1, 0, os.EX_OSERR)
        except:
            pass
        return True

    def installFirewalld(self):
        if self.distro == ubuntu:
            self.removeUfw()

        try:
            preFlightsChecks.stdOut("Enabling Firewall!")

            if self.distro == ubuntu:
                command = 'apt-get -y install firewalld'
            else:
                command = 'yum -y install firewalld'

            preFlightsChecks.call(command, self.distro, '[installFirewalld]',
                                  'Install FirewallD',
                                  1, 0, os.EX_OSERR)


            ######
            if self.distro == centos:
                # Not available in ubuntu
                command = 'systemctl restart dbus'
                preFlightsChecks.call(command, self.distro, '[installFirewalld]',
                                      'Start dbus',
                                      1, 0, os.EX_OSERR)

            command = 'systemctl restart systemd-logind'
            preFlightsChecks.call(command, self.distro, '[installFirewalld]',
                                  'restart logind',
                                  1, 0, os.EX_OSERR)

            command = 'systemctl start firewalld'
            preFlightsChecks.call(command, self.distro, '[installFirewalld]',
                                  'Restart FirewallD',
                                  1, 0, os.EX_OSERR)


            ##########

            command = 'systemctl enable firewalld'
            preFlightsChecks.call(command, self.distro, '[installFirewalld]',
                                  'Install FirewallD',
                                  1, 0, os.EX_OSERR)



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
            FirewallUtilities.addRule("udp", "53")
            FirewallUtilities.addRule("tcp", "53")
            FirewallUtilities.addRule("tcp", "40110-40210")

            logging.InstallLog.writeToFile("FirewallD installed and configured!")
            preFlightsChecks.stdOut("FirewallD installed and configured!")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installFirewalld]")
            return 0

        return 1

    ## from here

    def setupLSCPDDaemon(self):
        try:

            preFlightsChecks.stdOut("Trying to setup LSCPD Daemon!")
            logging.InstallLog.writeToFile("Trying to setup LSCPD Daemon!")

            os.chdir(self.cwd)

            shutil.copy("lscpd/lscpd.service", "/etc/systemd/system/lscpd.service")
            shutil.copy("lscpd/lscpdctrl", "/usr/local/lscp/bin/lscpdctrl")

            ##

            count = 0

            while (1):
                command = 'chmod +x /usr/local/lscp/bin/lscpdctrl'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to change permissions for /usr/local/lscp/bin/lscpdctrl, trying again, try number: " + str(
                            count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for /usr/local/lscp/bin/lscpdctrl [setupLSCPDDaemon]")
                        break
                else:
                    logging.InstallLog.writeToFile(
                        "Successfully changed permissions for /usr/local/lscp/bin/lscpdctrl!")
                    preFlightsChecks.stdOut("Successfully changed permissions for /usr/local/lscp/bin/lscpdctrl!")
                    break

            ##

            count = 1

            while (1):

                command = 'systemctl enable lscpd.service'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to enable LSCPD on system startup, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to change permissions for /usr/local/lscp/bin/lscpdctrl, you can do it manually using  systemctl enable lscpd.service [setupLSCPDDaemon]")
                        break
                else:
                    logging.InstallLog.writeToFile("LSCPD Successfully enabled at system startup!")
                    preFlightsChecks.stdOut("LSCPD Successfully enabled at system startup!")
                    break
            ##
            count = 0

            # In Ubuntu, the library that lscpd looks for is libpcre.so.1, but the one it installs is libpcre.so.3...
            if self.distro == ubuntu:
                command = 'ln -s /lib/x86_64-linux-gnu/libpcre.so.3 /lib/x86_64-linux-gnu/libpcre.so.1'
                res = subprocess.call(shlex.split(command))
                if res == 0:
                    self.stdOut("Created ubuntu symbolic link to pcre")
                else:
                    self.stdOut("Error creating symbolic link to pcre: " + str(res))

            ##

            count = 0

            while (1):

                command = 'systemctl start lscpd'
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Unable to start LSCPD, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to start LSCPD! [setupLSCPDDaemon]")
                        break
                else:
                    logging.InstallLog.writeToFile("LSCPD successfully started!")
                    preFlightsChecks.stdOut("LSCPD successfully started!")
                    break

            preFlightsChecks.stdOut("LSCPD Daemon Set!")

            logging.InstallLog.writeToFile("LSCPD Daemon Set!")


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupLSCPDDaemon]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupLSCPDDaemon]")
            return 0

        return 1

    def setup_cron(self):

        try:
            ## first install crontab
            file = open("installLogs.txt", 'a')
            count = 0
            while (1):
                if self.distro == centos:
                    command = 'yum install cronie -y'
                else:
                    command = 'apt-get -y install cron'

                cmd = shlex.split(command)

                res = subprocess.call(cmd, stdout=file)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to install cronie, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install cronie, cron jobs will not work. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Cronie successfully installed!")
                    preFlightsChecks.stdOut("Cronie successfully installed!")
                    break

            count = 0

            while (1):

                if self.distro == centos:
                    command = 'systemctl enable crond'
                else:
                    command = 'systemctl enable cron'

                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=file)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to enable cronie on system startup, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "We are not able to enable cron jobs at system startup, you can manually run systemctl enable crond. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Cronie successfully enabled at system startup!")
                    preFlightsChecks.stdOut("Cronie successfully enabled at system startup!")
                    break

            count = 0

            while (1):
                if self.distro == centos:
                    command = 'systemctl start crond'
                else:
                    command = 'systemctl start cron'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=file)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to start crond, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "We are not able to start crond, you can manually run systemctl start crond. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Crond successfully started!")
                    preFlightsChecks.stdOut("Crond successfully started!")
                    break

            ##

            cronFile = open("/etc/crontab", "a")
            cronFile.writelines("0 * * * * root python /usr/local/CyberCP/plogical/findBWUsage.py" + "\n")
            cronFile.writelines("0 * * * * root /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup" + "\n")
            cronFile.writelines("0 0 1 * * root /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup" + "\n")
            cronFile.close()

            command = 'chmod +x /usr/local/CyberCP/plogical/findBWUsage.py'
            cmd = shlex.split(command)
            res = subprocess.call(cmd, stdout=file)

            if preFlightsChecks.resFailed(self.distro, res):
                logging.InstallLog.writeToFile("1427 [setup_cron]")
            else:
                pass

            command = 'chmod +x /usr/local/CyberCP/postfixSenderPolicy/client.py'
            cmd = shlex.split(command)

            res = subprocess.call(cmd, stdout=file)

            if preFlightsChecks.resFailed(self.distro, res):
                logging.InstallLog.writeToFile("1428 [setup_cron]")
            else:
                pass

            count = 0

            while (1):
                if self.distro == centos:
                    command = 'systemctl restart crond.service'
                else:
                    command = 'systemctl restart cron.service'
                cmd = shlex.split(command)
                res = subprocess.call(cmd, stdout=file)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to restart crond, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "We are not able to restart crond, you can manually run systemctl restart crond. [setup_cron]")
                        break
                else:
                    logging.InstallLog.writeToFile("Crond successfully restarted!")
                    preFlightsChecks.stdOut("Crond successfully restarted!")
                    break

            file.close()


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_cron]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setup_cron]")
            return 0

        return 1

    def install_default_keys(self):
        try:
            count = 0

            path = "/root/.ssh"

            if not os.path.exists(path):
                os.mkdir(path)

            while (1):

                command = "ssh-keygen -f /root/.ssh/cyberpanel -t rsa -N ''"
                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to setup default SSH keys, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile("Unable to setup default SSH keys. [install_default_keys]")
                        break
                else:
                    logging.InstallLog.writeToFile("Succcessfully created default SSH keys!")
                    preFlightsChecks.stdOut("Succcessfully created default SSH keys!")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_default_keys]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_default_keys]")
            return 0

        return 1

    def install_rsync(self):
        try:
            count = 0
            while (1):

                if self.distro == centos:
                    command = 'yum -y install rsync'
                else:
                    command = 'apt-get -y install rsync'

                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to install rsync, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install rsync, some of backup functions will not work. [install_rsync]")
                        break
                else:
                    logging.InstallLog.writeToFile("Succcessfully installed rsync!")
                    preFlightsChecks.stdOut("Succcessfully installed rsync!")
                    break


        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_rsync]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [install_rsync]")
            return 0

        return 1

    def test_Requests(self):
        try:
            import requests
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
        except BaseException, msg:

            command = "pip uninstall --yes urllib3"
            subprocess.call(shlex.split(command))

            command = "pip uninstall --yes requests"
            subprocess.call(shlex.split(command))

            count = 0
            while (1):

                command = "pip install http://mirror.cyberpanel.net/urllib3-1.22.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install urllib3 module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install urllib3 module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("urllib3 module Successfully installed!")
                    preFlightsChecks.stdOut("urllib3 module Successfully installed!")
                    break

            count = 0
            while (1):

                command = "pip install http://mirror.cyberpanel.net/requests-2.18.4.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Unable to install requests module, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install requests module, exiting installer! [install_python_requests]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("Requests module Successfully installed!")
                    preFlightsChecks.stdOut("Requests module Successfully installed!")
                    break

    def installation_successfull(self):
        print("###################################################################")
        print("                CyberPanel Successfully Installed                  ")
        print("                                                                   ")

        print("                                                                   ")
        print("                                                                   ")

        print("                Visit: https://" + self.ipAddr + ":8090                ")
        print("                Username: admin                                    ")
        print("                Password: 1234567                                  ")

        print("###################################################################")

    def installCertBot(self):
        try:

            command = "pip uninstall --yes pyOpenSSL"
            res = subprocess.call(shlex.split(command))

            command = "pip uninstall --yes certbot"
            res = subprocess.call(shlex.split(command))

            count = 0
            while (1):
                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/pyOpenSSL-17.5.0.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install pyOpenSSL, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install pyOpenSSL, exiting installer! [installCertBot]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("pyOpenSSL successfully installed!  [pip]")
                    preFlightsChecks.stdOut("pyOpenSSL successfully installed!  [pip]")
                    break

            count = 0
            while (1):
                command = "pip install http://" + preFlightsChecks.cyberPanelMirror + "/certbot-0.21.1.tar.gz"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install CertBot, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install CertBot, exiting installer! [installCertBot]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("CertBot successfully installed!  [pip]")
                    preFlightsChecks.stdOut("CertBot successfully installed!  [pip]")
                    break

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCertBot]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installCertBot]")
            return 0

        return 1

    def modSecPreReqs(self):
        try:

            pathToRemoveGarbageFile = os.path.join(self.server_root_path, "modules/mod_security.so")
            os.remove(pathToRemoveGarbageFile)

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [modSecPreReqs]")
            return 0

    def installTLDExtract(self):
        try:
            count = 0
            while (1):
                command = "pip install tldextract"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install tldextract, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install tldextract! [installTLDExtract]")
                else:
                    logging.InstallLog.writeToFile("tldextract successfully installed!  [pip]")
                    preFlightsChecks.stdOut("tldextract successfully installed!  [pip]")
                    break
        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installTLDExtract]")
            return 0

    def installPYDNS(self):
        command = "pip install pydns"
        preFlightsChecks.call(command, self.distro, '[installPYDNS]',
                                      'Install PYDNS',
                                      1, 0, os.EX_OSERR)
    def installDockerPY(self):
        command = "pip install docker"
        preFlightsChecks.call(command, self.distro, '[installDockerPY]',
                                      'Install DockerPY',
                                      1, 0, os.EX_OSERR)

    def installOpenDKIM(self):
        try:
            count = 0
            while (1):

                if self.distro == centos:
                    command = 'yum -y install opendkim'
                else:
                    command = 'apt-get -y install opendkim'

                cmd = shlex.split(command)
                res = subprocess.call(cmd)

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut("Trying to install opendkim, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Unable to install opendkim, your mail may not end up in inbox. [installOpenDKIM]")
                        break
                else:
                    logging.InstallLog.writeToFile("Succcessfully installed opendkim!")
                    preFlightsChecks.stdOut("Succcessfully installed opendkim!")
                    break

            if self.distro == ubuntu:
                try:
                    command = 'apt install opendkim-tools'
                    subprocess.call(shlex.split(command))
                except:
                    pass

                try:
                    command = 'mkdir -p /etc/opendkim/keys/'
                    subprocess.call(shlex.split(command))
                except:
                    pass

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installOpenDKIM]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installOpenDKIM]")
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
            subprocess.call(shlex.split(command))

            command = "systemctl enable opendkim"
            subprocess.call(shlex.split(command))

            ##

            command = "systemctl start postfix"
            subprocess.call(shlex.split(command))

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [configureOpenDKIM]")
            return 0
        except ValueError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [configureOpenDKIM]")
            return 0

        return 1

    def installdnsPython(self):
        try:
            count = 0
            while (1):
                command = "pip install dnspython"

                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install dnspython, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install dnspython! [installdnsPython]")
                else:
                    logging.InstallLog.writeToFile("dnspython successfully installed!  [pip]")
                    preFlightsChecks.stdOut("dnspython successfully installed!  [pip]")
                    break
        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [installdnsPython]")
            return 0

    def setupCLI(self):
        try:
            count = 0
            while (1):
                command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(self.distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to setup CLI, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to setup CLI! [setupCLI]")
                else:
                    logging.InstallLog.writeToFile("CLI setup successfull!")
                    preFlightsChecks.stdOut("CLI setup successfull!")
                    break

            command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
            res = subprocess.call(shlex.split(command))

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupCLI]")
            return 0

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
            res = subprocess.call(shlex.split(command))

            os.chdir(self.cwd)

            if self.distro == centos:
                command = "chmod +x composer.sh"
            else:
                command = "chmod +x composer-no-test.sh"

            res = subprocess.call(shlex.split(command))

            if self.distro == centos:
                command = "./composer.sh"
            else:
                command = "./composer-no-test.sh"

            res = subprocess.call(shlex.split(command))

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupPHPAndComposer]")
            return 0

    @staticmethod
    def installOne(package):
        res = subprocess.call(shlex.split('apt-get -y install ' + package))
        if res != 0:
            preFlightsChecks.stdOut("Error #" + str(res) + ' installing:' + package + '.  This may not be an issue ' \
                                                                                      'but may affect installation of something later',
                                    1)

        return res  # Though probably not used

    @staticmethod
    def setupVirtualEnv(distro):
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
                while (1):
                    command = "yum install -y libattr-devel xz-devel gpgme-devel mariadb-devel curl-devel"
                    res = subprocess.call(shlex.split(command))

                    if preFlightsChecks.resFailed(distro, res):
                        count = count + 1
                        preFlightsChecks.stdOut(
                            "Trying to install project dependant modules, trying again, try number: " + str(count))
                        if count == 3:
                            logging.InstallLog.writeToFile(
                                "Failed to install project dependant modules! [setupVirtualEnv]")
                            preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                            os._exit(0)
                    else:
                        logging.InstallLog.writeToFile("Project dependant modules installed successfully!")
                        preFlightsChecks.stdOut("Project dependant modules installed successfully!!")
                        break

            ##


            count = 0
            while (1):
                command = "pip install virtualenv"
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install virtualenv, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed install virtualenv! [setupVirtualEnv]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("virtualenv installed successfully!")
                    preFlightsChecks.stdOut("virtualenv installed successfully!")
                    break

            ####

            count = 0
            while (1):
                command = "virtualenv --system-site-packages /usr/local/CyberCP"
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to setup virtualenv, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to setup virtualenv! [setupVirtualEnv]")
                        preFlightsChecks.stdOut("Installation failed, consult: /var/log/installLogs.txt")
                        os._exit(0)
                else:
                    logging.InstallLog.writeToFile("virtualenv setup successfully!")
                    preFlightsChecks.stdOut("virtualenv setup successfully!")
                    break

            ##

            env_path = '/usr/local/CyberCP'
            subprocess.call(['virtualenv', env_path])
            activate_this = os.path.join(env_path, 'bin', 'activate_this.py')
            execfile(activate_this, dict(__file__=activate_this))

            ##

            install_file = '/usr/local/CyberCP/requirments.txt'
            if distro == ubuntu and get_Ubuntu_release() < 18.04:
                install_file_new = '/usr/local/CyberCP/requirements.txt'
                fd = open(install_file, 'r')
                fd_new = open(install_file_new, 'w')
                lines = fd.readlines()
                for line in lines:
                    if line[:6] != 'pycurl' and line[:7] != 'pygpgme':
                        fd_new.write(line)
                fd.close()
                fd_new.close()
                preFlightsChecks.stdOut("Install updated " + install_file_new, 1)
                install_file = install_file_new

            count = 0
            while (1):
                command = "pip install --ignore-installed -r " + install_file
                res = subprocess.call(shlex.split(command))

                if preFlightsChecks.resFailed(distro, res):
                    count = count + 1
                    preFlightsChecks.stdOut(
                        "Trying to install Python project dependant modules, trying again, try number: " + str(count))
                    if count == 3:
                        logging.InstallLog.writeToFile(
                            "Failed to install Python project dependant modules! [setupVirtualEnv]")
                        break
                else:
                    logging.InstallLog.writeToFile("Python project dependant modules installed successfully!")
                    preFlightsChecks.stdOut("Python project dependant modules installed successfully!!")
                    break

            command = "systemctl restart gunicorn.socket"
            res = subprocess.call(shlex.split(command))

            command = "virtualenv --system-site-packages /usr/local/CyberCP"
            res = subprocess.call(shlex.split(command))



        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [setupVirtualEnv]")
            return 0

    @staticmethod
    def enableDisableDNS(state):
        try:
            servicePath = '/home/cyberpanel/powerdns'

            if state == 'Off':

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

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableDisableDNS]")
            return 0

    @staticmethod
    def enableDisableEmail(state):
        try:
            servicePath = '/home/cyberpanel/postfix'

            if state == 'Off':

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

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableDisableEmail]")
            return 0

    @staticmethod
    def enableDisableFTP(state, distro):
        try:
            servicePath = '/home/cyberpanel/pureftpd'

            if state == 'Off':

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

        except OSError, msg:
            logging.InstallLog.writeToFile(str(msg) + " [enableDisableEmail]")
            return 0

    @staticmethod
    def setUpFirstAccount():
        try:
            command = 'python /usr/local/CyberCP/plogical/adminPass.py --password 1234567'
            subprocess.call(shlex.split(command))
        except:
            pass


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


def main():
    parser = argparse.ArgumentParser(description='CyberPanel Installer')
    parser.add_argument('publicip', help='Please enter public IP for your VPS or dedicated server.')
    parser.add_argument('--mysql', help='Specify number of MySQL instances to be used.')
    parser.add_argument('--postfix', help='Enable or disable Email Service.')
    parser.add_argument('--powerdns', help='Enable or disable DNS Service.')
    parser.add_argument('--ftp', help='Enable or disable ftp Service.')
    parser.add_argument('--ent', help='Install LS Ent or OpenLiteSpeed')
    parser.add_argument('--serial', help='Install LS Ent or OpenLiteSpeed')
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

    if distro == ubuntu:
        os.chdir("/etc/cyberpanel")

    if args.mysql == None:
        mysql = 'One'
        preFlightsChecks.stdOut("Single MySQL instance version will be installed.")
    else:
        mysql = args.mysql
        preFlightsChecks.stdOut("Dobule MySQL instance version will be installed.")

    checks.checkPythonVersion()
    checks.setup_account_cyberpanel()
    if distro == centos:
        checks.yum_update()
    checks.installCyberPanelRepo()
    if distro == centos:
        checks.enableEPELRepo()
    checks.install_pip()
    checks.install_python_dev()
    checks.install_gcc()
    if distro == centos:
        checks.install_python_setup_tools()
    checks.install_django()
    checks.install_pexpect()
    checks.install_python_mysql_library()
    checks.install_gunicorn()
    checks.install_psutil()
    checks.setup_gunicorn()

    import installCyberPanel
    if ent == 0:
        installCyberPanel.Main(cwd, mysql, distro, ent)
    else:
        installCyberPanel.Main(cwd, mysql, distro, ent, serial)

    checks.fix_selinux_issue()
    checks.install_psmisc()
    checks.install_postfix_davecot()
    checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
    checks.setup_postfix_davecot_config(mysql)

    checks.install_unzip()
    checks.install_zip()
    checks.install_rsync()

    checks.downoad_and_install_raindloop()
    checks.download_install_phpmyadmin()

    checks.installFirewalld()

    checks.setupLSCPDDaemon()
    checks.install_python_requests()
    checks.install_default_keys()

    checks.installCertBot()
    checks.test_Requests()
    checks.installPYDNS()
    checks.installDockerPY()
    checks.download_install_CyberPanel(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
    checks.setupCLI()
    checks.setup_cron()
    checks.installTLDExtract()
    # checks.installdnsPython()

    ## Install and Configure OpenDKIM.

    checks.installOpenDKIM()
    checks.configureOpenDKIM()

    checks.modSecPreReqs()
    checks.setupVirtualEnv(distro)
    checks.setupPHPAndComposer()

    if args.postfix != None:
        checks.enableDisableEmail(args.postfix)
    else:
        preFlightsChecks.stdOut("Postfix will be installed and enabled.")
        checks.enableDisableEmail('On')

    if args.powerdns != None:
        checks.enableDisableDNS(args.powerdns)
    else:
        preFlightsChecks.stdOut("PowerDNS will be installed and enabled.")
        checks.enableDisableDNS('On')

    if args.ftp != None:
        checks.enableDisableFTP(args.ftp, distro)
    else:
        preFlightsChecks.stdOut("Pure-FTPD will be installed and enabled.")
        checks.enableDisableFTP('On', distro)
    checks.setUpFirstAccount()
    logging.InstallLog.writeToFile("CyberPanel installation successfully completed!")
    checks.installation_successfull()


if __name__ == "__main__":
    main()
