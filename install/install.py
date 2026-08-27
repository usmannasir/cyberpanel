import sys
import subprocess
import shutil
import installLog as logging
import argparse
import os
import re
import shlex
from firewallUtilities import FirewallUtilities
import time
import random
import socket
from os.path import *
from stat import *
import stat
import install_utils
import json
import hashlib

sys.path.insert(1, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from cyberpanel_version import BUILD, VERSION
from database_consumers import (
    configure_phpmyadmin_signon,
    dovecot_connect_line,
)
from env_generator import DatabaseConfigError, build_database_config
from plogical.legacyWebmail import legacy_data_permission_commands

# Using shared char_set from install_utils
char_set = install_utils.char_set


# Using shared function from install_utils
generate_pass = install_utils.generate_pass


# There can not be peace without first a great suffering.

# distros - using from install_utils
centos = install_utils.centos
ubuntu = install_utils.ubuntu
cent8 = install_utils.cent8
openeuler = install_utils.openeuler
cent9 = 4  # Not in install_utils yet
CloudLinux8 = 0  # Not in install_utils yet

LITESPEED_EL10_KEY_SHA256 = 'cd0578a8febe98cb7d7d437a73419b8407ddd98cd848f2c9c7fdd288d768af01'


def is_el10_release(os_release_path='/etc/os-release'):
    """Return True only for supported Enterprise Linux 10 distributions."""
    values = {}
    try:
        with open(os_release_path, 'r') as release_file:
            for raw_line in release_file:
                key, separator, value = raw_line.partition('=')
                if separator:
                    values[key.strip()] = value.strip().strip('"\'').lower()
    except OSError:
        return False

    supported_ids = {'almalinux', 'rocky', 'rhel', 'centos', 'cloudlinux', 'ol'}
    return (values.get('ID') in supported_ids
            and values.get('VERSION_ID', '').split('.', 1)[0] == '10')


def verify_litespeed_el10_key(key_path):
    """Verify the replacement LiteSpeed RPM signing key before importing it."""
    try:
        digest = hashlib.sha256()
        with open(key_path, 'rb') as key_file:
            for chunk in iter(lambda: key_file.read(65536), b''):
                digest.update(chunk)
        return digest.hexdigest() == LITESPEED_EL10_KEY_SHA256
    except OSError:
        return False

# Using shared function from install_utils
FetchCloudLinuxAlmaVersionVersion = install_utils.FetchCloudLinuxAlmaVersionVersion


# Using shared function from install_utils
get_distro = install_utils.get_distro


def get_Ubuntu_release():
    release = install_utils.get_Ubuntu_release(use_print=False, exit_on_error=True)
    if release == -1:
        preFlightsChecks.stdOut("Can't find distro release name in /etc/lsb-release - fatal error", 1, 1,
                                os.EX_UNAVAILABLE)
    return release


def normalize_opendkim_socket_lines(lines):
    """Return an OpenDKIM config with one inet socket directive."""
    normalized = []
    socket_written = False

    for line in lines:
        if re.match(r'^\s*Socket(?:\s|$)', line):
            if not socket_written:
                normalized.append('Socket  inet:8891@localhost\n')
                socket_written = True
            continue
        normalized.append(line)

    if not socket_written:
        normalized.append('Socket  inet:8891@localhost\n')

    return normalized


class preFlightsChecks:
    debug = 1
    cyberPanelMirror = "mirror.cyberpanel.net/pip"
    cdn = 'cyberpanel.sh'
    apt_updated = False  # Track if apt update has been run
    
    def install_package(self, package_name, options="", silent=False):
        """Unified package installation across distributions"""
        command, shell = install_utils.get_package_install_command(self.distro, package_name, options)
        
        if not silent:
            return preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, shell)
        else:
            return preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR, shell)
    
    def is_centos_family(self):
        """Check if distro is CentOS, CentOS 8, or OpenEuler"""
        return self.distro in [centos, cent8, openeuler]
    
    def manage_service(self, service_name, action="start"):
        """Unified service management"""
        command = f'systemctl {action} {service_name}'
        return preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
    
    def remove_package(self, package_name, silent=False):
        """Unified package removal across distributions"""
        command, shell = install_utils.get_package_remove_command(self.distro, package_name)
        
        if not silent:
            return preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, shell)
        else:
            return preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR, shell)

    def setupLSCPDAccount(self):
        """Create the panel daemon account before files are assigned to it."""
        group_exists = subprocess.run(
            ['getent', 'group', 'lscpd'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).returncode == 0
        if not group_exists:
            command = 'groupadd lscpd'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        user_exists = subprocess.run(
            ['id', '-u', 'lscpd'],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        ).returncode == 0
        if not user_exists:
            command = 'useradd -g lscpd -M -d /usr/local/lscp lscpd'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def __init__(self, rootPath, ip, path, cwd, cyberPanelPath, distro, remotemysql=None, mysqlhost=None, mysqldb=None,
                 mysqluser=None, mysqlpassword=None, mysqlport=None):
        self.ipAddr = ip
        self.path = path
        self.cwd = cwd
        self.server_root_path = rootPath
        self.cyberPanelPath = cyberPanelPath
        self.distro = distro
        self.remotemysql = remotemysql
        self.mysqlhost = mysqlhost
        self.mysqluser = mysqluser
        self.mysqlpassword = mysqlpassword
        self.mysqlport = mysqlport
        self.mysqldb = mysqldb


    def installQuota(self,):
        try:

            if self.is_centos_family():
                self.install_package("quota", silent=True)

                if self.edit_fstab('/', '/') == 0:
                    preFlightsChecks.stdOut("Quotas will not be abled as we failed to modify fstab file.")
                    return 0


                command = 'mount -o remount /'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'mount -o remount /'
                try:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,universal_newlines=True, shell=True)
                except:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

                if mResult.returncode != 0:
                    fstab_path = '/etc/fstab'
                    backup_path = fstab_path + '.bak'
                    if os.path.exists(fstab_path):
                        os.remove(fstab_path)
                    shutil.copy(backup_path, fstab_path)

                    preFlightsChecks.stdOut("Re-mount failed, restoring original FSTab and existing quota setup.")
                    return 0



            ##

            if self.distro == ubuntu:
                self.stdOut("Install Quota on Ubuntu")
                # Skip apt update as it was already done in cyberpanel.sh
                self.install_package("quota", silent=True)

                running_kernel = os.uname().release
                module_root = '/lib/modules/%s' % running_kernel
                quota_modules = []
                for root, directories, files in os.walk(module_root):
                    quota_modules.extend(
                        os.path.join(root, name) for name in files
                        if name.startswith('quota_v') and '.ko' in name
                    )

                if not quota_modules:
                    extra_package = 'linux-modules-extra-%s' % running_kernel
                    candidate = subprocess.run(
                        ['apt-cache', 'show', extra_package],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    if candidate.returncode == 0:
                        self.install_package(extra_package, silent=True)

                if self.edit_fstab('/', '/') == 0:
                    preFlightsChecks.stdOut("Quotas will not be abled as we are are failed to modify fstab file.")
                    return 0

                command = 'mount -o remount /'
                try:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                except:
                    mResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             universal_newlines=True, shell=True)

                if mResult.returncode != 0:
                    fstab_path = '/etc/fstab'
                    backup_path = fstab_path + '.bak'
                    if os.path.exists(fstab_path):
                        os.remove(fstab_path)
                    shutil.copy(backup_path, fstab_path)

                    preFlightsChecks.stdOut("Re-mount failed, restoring original FSTab and existing quota setup.")
                    return 0

                command = 'quotacheck -ugm /'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = f'modprobe quota_v1 -S {running_kernel}'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = f'modprobe quota_v2 -S {running_kernel}'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = f'quotacheck -ugm /'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = f'quotaon -v /'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile("[ERROR] installQuota. " + str(msg))

    def edit_fstab(self,mount_point, options_to_add):

        try:
            retValue = 1
            # Backup the original fstab file
            fstab_path = '/etc/fstab'
            backup_path = fstab_path + '.bak'

            rData = open(fstab_path, 'r').read()

            if rData.find('xfs') > -1:
                options_to_add = 'uquota'
            else:
                options_to_add = 'usrquota,grpquota'

            if not os.path.exists(backup_path):
                shutil.copy(fstab_path, backup_path)

            # Read the fstab file
            with open(fstab_path, 'r') as file:
                lines = file.readlines()

            # Modify the appropriate line
            WriteToFile = open(fstab_path, 'w')
            for i, line in enumerate(lines):

                if line.find('\t') > -1:
                    parts = line.split('\t')
                else:
                    parts = line.split(' ')

                print(parts)
                try:
                    if parts[1] == '/' and parts[3].find(options_to_add) == -1 and len(parts[3]) > 4:

                        parts[3] = f'{parts[3]},{options_to_add}'
                        tempParts = [item for item in parts if item.strip()]
                        finalString = '\t'.join(tempParts)
                        print(finalString)
                        WriteToFile.write(finalString)

                    elif parts[1] == '/':

                        for ii, p in enumerate(parts):
                            if p.find('defaults') > -1 or p.find('discard') > -1 or p.find('errors=') > -1:
                                parts[ii] = f'{parts[ii]},{options_to_add}'
                                tempParts = [item for item in parts if item.strip()]
                                finalString = '\t'.join(tempParts)
                                print(finalString)
                                WriteToFile.write(finalString)
                    else:
                        WriteToFile.write(line)
                except:
                    WriteToFile.write(line)

            WriteToFile.close()

            return retValue
        except:
            return 0

    @staticmethod
    def stdOut(message, log=0, do_exit=0, code=os.EX_OK):
        install_utils.stdOut(message, log, do_exit, code)

    def mountTemp(self):
        try:

            try:
                result = subprocess.run('systemd-detect-virt', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
            except:
                result = subprocess.run('systemd-detect-virt', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

            if result.stdout.find('openvz') > -1:
                if self.distro == ubuntu:
                    self.install_package("inetutils-inetd")

            # ## On OpenVZ there is an issue using .tempdisk for /tmp as it breaks network on container after reboot.
            #
            # if subprocess.check_output('systemd-detect-virt').decode("utf-8").find("openvz") > -1:
            #
            #     varTmp = "/var/tmp /tmp none bind 0 0\n"
            #
            #     fstab = "/etc/fstab"
            #     writeToFile = open(fstab, "a")
            #     writeToFile.writelines(varTmp)
            #     writeToFile.close()
            #
            # else:
            #
            #     command = "dd if=/dev/zero of=/usr/.tempdisk bs=100M count=15"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     command = "mkfs.ext4 -F /usr/.tempdisk"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     command = "mkdir -p /usr/.tmpbak/"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     command = "cp -pr /tmp/* /usr/.tmpbak/"
            #     subprocess.call(command, shell=True)
            #
            #     command = "mount -o loop,rw,nodev,nosuid,noexec,nofail /usr/.tempdisk /tmp"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     command = "chmod 1777 /tmp"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     command = "cp -pr /usr/.tmpbak/* /tmp/"
            #     subprocess.call(command, shell=True)
            #
            #     command = "rm -rf /usr/.tmpbak"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     command = "mount --bind /tmp /var/tmp"
            #     preFlightsChecks.call(command, self.distro, command,
            #                           command,
            #                           1, 0, os.EX_OSERR)
            #
            #     tmp = "/usr/.tempdisk /tmp ext4 loop,rw,noexec,nosuid,nodev,nofail 0 0\n"
            #     varTmp = "/tmp /var/tmp none bind 0 0\n"
            #
            #     fstab = "/etc/fstab"
            #     writeToFile = open(fstab, "a")
            #     writeToFile.writelines(tmp)
            #     writeToFile.writelines(varTmp)
            #     writeToFile.close()

            pass

        except BaseException as msg:
            preFlightsChecks.stdOut('[ERROR] ' + str(msg))
            return 0

    @staticmethod
    def pureFTPDServiceName(distro):
        if distro == ubuntu:
            return 'pure-ftpd-mysql'
        return 'pure-ftpd'

    # Using shared function from install_utils
    @staticmethod
    def resFailed(distro, res):
        return install_utils.resFailed(distro, res)

    # Using shared function from install_utils
    @staticmethod
    def call(command, distro, bracket, message, log=0, do_exit=0, code=os.EX_OK, shell=False):
        return install_utils.call(command, distro, bracket, message, log, do_exit, code, shell)

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

            if self.is_centos_family():
                self.install_package("sudo", silent=True)

            ##

            if self.distro == ubuntu:
                self.stdOut("Add Cyberpanel user")
                command = 'adduser --disabled-login --gecos "" cyberpanel'
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            else:
                command = "useradd -s /bin/false cyberpanel"
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ###############################

            ### Docker User/group

            if self.distro == ubuntu:
                command = 'adduser --disabled-login --gecos "" docker'
            else:
                command = "adduser docker"

            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'groupadd -f docker'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'usermod -aG docker docker'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'usermod -aG docker cyberpanel'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ###

            command = "mkdir -p /etc/letsencrypt/live/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile("[ERROR] setup_account_cyberpanel. " + str(msg))

    def configureLiteSpeedEL10Key(self):
        """Install LiteSpeed's EL10-compatible RPM key after pin verification."""
        if not is_el10_release():
            return

        download_path = '/tmp/RPM-GPG-KEY-litespeed2025'
        key_path = '/etc/pki/rpm-gpg/RPM-GPG-KEY-litespeed'
        key_url = 'https://rpms.litespeedtech.com/centos/RPM-GPG-KEY-litespeed2025'
        command = f'wget --https-only -q -O {download_path} {key_url}'
        preFlightsChecks.call(
            command, self.distro, command,
            'Download LiteSpeed EL10 signing key', 1, 1, os.EX_OSERR,
        )

        if not verify_litespeed_el10_key(download_path):
            try:
                os.remove(download_path)
            except OSError:
                pass
            preFlightsChecks.stdOut(
                'LiteSpeed EL10 signing key failed SHA256 verification.',
                1, 1, os.EX_DATAERR,
            )

        os.makedirs(os.path.dirname(key_path), exist_ok=True)
        os.replace(download_path, key_path)
        os.chmod(key_path, 0o644)
        result = subprocess.call(['rpmkeys', '--import', key_path])
        if result != 0:
            preFlightsChecks.stdOut(
                'Unable to import the LiteSpeed EL10 signing key.',
                1, 1, os.EX_OSERR,
            )

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

                if get_Ubuntu_release() >= 26.0:
                    # APT 3 verifies repository keys as its unprivileged user.
                    # LiteSpeed's helper installs these files as root-only.
                    for key_file in ('/etc/apt/trusted.gpg.d/lst_debian_repo.gpg',
                                     '/etc/apt/trusted.gpg.d/lst_repo.gpg'):
                        if os.path.exists(key_file):
                            os.chmod(key_file, 0o644)

                # LiteSpeed's helper only knows Ubuntu 16/18/20/22/24. On a newer release
                # every branch falls through, so it writes no sources file, prints no
                # warning and still exits 0 - the first sign is "Unable to locate package
                # openlitespeed" much later. The repo itself does publish newer suites, so
                # write the list ourselves whenever the helper left it missing or empty.
                # It still runs first because it registers the LiteSpeed GPG keys.
                repoFile = '/etc/apt/sources.list.d/lst_debian_repo.list'
                wrote_repo = False
                if not os.path.exists(repoFile) or os.path.getsize(repoFile) == 0:
                    codename = install_utils.get_Ubuntu_code_name()
                    self.stdOut(f"LiteSpeed repo not configured by their helper; writing it for '{codename}'")
                    logging.InstallLog.writeToFile(
                        f"enable_lst_debain_repo.sh did not configure a repo; falling back to codename {codename}")

                    with open(repoFile, 'w') as f:
                        f.write(f"deb http://rpms.litespeedtech.com/debian/ {codename} main\n")
                        f.write(f"#deb http://rpms.litespeedtech.com/edge/debian/ {codename} main\n")
                    wrote_repo = True

                if get_Ubuntu_release() >= 26.0:
                    # The helper may return success even when its APT refresh only
                    # emitted warnings. Require a usable package index on Ubuntu 26.
                    command = 'apt-get update -y -o APT::Update::Error-Mode=any'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                elif wrote_repo:
                    command = 'apt-get update -y'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            except:
                logging.InstallLog.writeToFile("[ERROR] Exception during CyberPanel install")
                preFlightsChecks.stdOut("[ERROR] Exception during CyberPanel install")
                os._exit(os.EX_SOFTWARE)

        elif self.distro == centos:
            command = 'rpm -ivh http://rpms.litespeedtech.com/centos/litespeed-repo-1.2-1.el7.noarch.rpm'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
        elif self.distro == cent8:
            command = 'rpm -Uvh http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            self.configureLiteSpeedEL10Key()

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
        self.install_package("psmisc")

    def generate_secure_env_file(self, mysql_root_password, cyberpanel_db_password):
        """
        Generate secure .env file with random passwords during installation
        """
        try:
            import sys
            import socket
            
            # Import the environment generator
            sys.path.append(os.path.join(self.cyberPanelPath, 'install'))
            from env_generator import (create_env_file, create_env_backup,
                                       build_database_config)

            # A remote installation moves both the application connection and
            # the administrative connection to --mysqlhost:--mysqlport. This
            # validates the endpoint and raises before anything is written if
            # a required value is missing.
            database_config = build_database_config(
                remote=(self.remotemysql == 'ON'),
                host=getattr(self, 'mysqlhost', None),
                port=getattr(self, 'mysqlport', None),
                root_db=getattr(self, 'mysqldb', None),
                root_user=getattr(self, 'mysqluser', None),
            )

            # Generate secure credentials
            credentials = create_env_file(
                self.cyberPanelPath,
                mysql_root_password,
                cyberpanel_db_password,
                database_config=database_config
            )
            
            # Create backup for recovery
            create_env_backup(self.cyberPanelPath, credentials)
            
            logging.InstallLog.writeToFile("✓ Secure .env file generated successfully")
            logging.InstallLog.writeToFile("✓ Credentials backup created for recovery")
            
            return credentials
            
        except Exception as e:
            logging.InstallLog.writeToFile(f"[ERROR] Failed to generate secure environment file: {str(e)}")
            # Fallback to original method if environment generation fails
            self.fallback_settings_update(mysql_root_password, cyberpanel_db_password)

    def fallback_settings_update(self, mysql_root_password, cyberpanel_db_password):
        """
        Fallback method to update settings.py directly if environment generation fails

        DATABASES declares 'default' (the cyberpanel application user) before
        'rootdb' (the administrative user), so the first 'PASSWORD:' line
        encountered belongs to the application connection. The previous
        ordering wrote the administrative password there and the application
        password into rootdb, leaving both connections wrong.
        """
        logging.InstallLog.writeToFile("Using fallback method for settings.py update")

        remote = (self.remotemysql == 'ON')

        # This runs because environment generation already failed, so it must
        # not depend on env_generator being importable. The local values are
        # inlined; the helper is only consulted to validate a remote endpoint.
        db = {
            'db_name': 'cyberpanel',
            'db_user': 'cyberpanel',
            'db_host': 'localhost',
            'db_port': '3306',
            'root_db_name': 'mysql',
            'root_db_user': 'root',
            'root_db_host': 'localhost',
            'root_db_port': '3306',
        }

        if remote:
            try:
                sys.path.append(os.path.join(self.cyberPanelPath, 'install'))
                from env_generator import build_database_config
                db = build_database_config(
                    remote=True,
                    host=getattr(self, 'mysqlhost', None),
                    port=getattr(self, 'mysqlport', None),
                    root_db=getattr(self, 'mysqldb', None),
                    root_user=getattr(self, 'mysqluser', None),
                )
            except Exception as endpoint_error:
                # Writing the local defaults for a remote installation would
                # point every connection at a database that is not there, and
                # the installation would fail later with a confusing error.
                logging.InstallLog.writeToFile(
                    "[ERROR] Could not resolve the remote database endpoint "
                    "for the fallback settings update: %s"
                    % str(endpoint_error))
                raise

        path = self.cyberPanelPath + "/CyberCP/settings.py"
        data = open(path, "r").readlines()
        writeDataToFile = open(path, "w")
        # 0 = still inside 'default', 1 = inside 'rootdb'.
        block = 0

        for items in data:
            if items.find('SECRET_KEY') > -1:
                SK = "SECRET_KEY = %r\n" % generate_pass(50)
                writeDataToFile.writelines(SK)
                continue

            if items.find("'PASSWORD':") > -1:
                if block == 0:
                    writeDataToFile.writelines(
                        "        'PASSWORD': %r,\n" % cyberpanel_db_password)
                else:
                    writeDataToFile.writelines(
                        "        'PASSWORD': %r,\n" % mysql_root_password)
            elif items.find("'HOST':") > -1:
                host = db['db_host'] if block == 0 else db['root_db_host']
                writeDataToFile.writelines("        'HOST': %r,\n" % host)
            elif items.find("'PORT':") > -1:
                port = db['db_port'] if block == 0 else db['root_db_port']
                writeDataToFile.writelines("        'PORT': %r,\n" % port)
                # PORT is the last entry of each database block.
                block = block + 1
            elif items.find("'USER':") > -1 and block == 1:
                writeDataToFile.writelines(
                    "        'USER': %r,\n" % db['root_db_user'])
            elif items.find("'NAME':") > -1 and block == 1:
                writeDataToFile.writelines(
                    "        'NAME': %r,\n" % db['root_db_name'])
            else:
                writeDataToFile.writelines(items)

        if self.distro == ubuntu:
            os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

        writeDataToFile.close()

    def download_install_CyberPanel(self, mysqlPassword, mysql):
        ##

        os.chdir(self.path)

        os.chdir('/usr/local')

        command = "git clone https://github.com/usmannasir/cyberpanel"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        shutil.move('cyberpanel', 'CyberCP')

        ##

        ### update password:

        if self.remotemysql == 'OFF':
            passFile = "/etc/cyberpanel/mysqlPassword"

            f = open(passFile)
            data = f.read()
            password = data.split('\n', 1)[0]
        else:
            password = self.mysqlpassword

        ### Put correct mysql passwords in settings file!

        # This allows root/sudo users to be able to work with MySQL/MariaDB without hunting down the password like
        # all the other control panels allow
        # reference: https://oracle-base.com/articles/mysql/mysql-password-less-logins-using-option-files
        sys.path.append(os.path.join(self.cyberPanelPath, 'install'))
        from env_generator import build_mysql_client_config

        mysql_my_root_cnf = '/root/.my.cnf'
        mysql_root_cnf_content = build_mysql_client_config(
            password,
            remote=(self.remotemysql == 'ON'),
            host=getattr(self, 'mysqlhost', None),
            port=getattr(self, 'mysqlport', None),
            user=getattr(self, 'mysqluser', None),
        )

        with open(mysql_my_root_cnf, 'w') as f:
            f.write(mysql_root_cnf_content)
        os.chmod(mysql_my_root_cnf, 0o600)
        command = 'chown root:root %s' % mysql_my_root_cnf
        subprocess.call(shlex.split(command))

        logging.InstallLog.writeToFile("Updating /root/.my.cnf!")

        logging.InstallLog.writeToFile("Generating secure environment configuration!")

        # Generate secure environment file instead of hardcoding passwords
        # Note: password = MySQL root password, mysqlPassword = CyberPanel DB password
        # The remote endpoint is now part of the generated environment rather
        # than something patched into settings.py afterwards. Three text
        # substitutions used to run here against an undefined `path`, which
        # raised before migrations on every remote installation; even with the
        # name defined they edited settings.py, whose database values are only
        # fallbacks — .env is what Django actually reads.
        self.generate_secure_env_file(password, mysqlPassword)

        logging.InstallLog.writeToFile("Environment configuration generated successfully!")

        # self.setupVirtualEnv(self.distro)

        ### Applying migrations

        os.chdir("/usr/local/CyberCP")

        command = "/usr/local/CyberPanel/bin/python manage.py makemigrations"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        ##

        command = "/usr/local/CyberPanel/bin/python manage.py migrate"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        if not os.path.exists("/usr/local/CyberCP/public"):
            os.mkdir("/usr/local/CyberCP/public")

        command = "/usr/local/CyberPanel/bin/python manage.py collectstatic --noinput --clear"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        ## Moving static content to lscpd location
        command = 'mv static /usr/local/CyberCP/public/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        try:
            path = "/usr/local/CyberCP/version.txt"
            with open(path, 'w') as writeToFile:
                json.dump({'version': VERSION, 'build': BUILD}, writeToFile)
        except:
            pass

    def fixCyberPanelPermissions(self):

        ###### fix Core CyberPanel permissions

        system_group = 'nogroup' if self.distro == ubuntu else 'nobody'
        command = "usermod -G lscpd,lsadm,%s lscpd" % system_group
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

        for command in legacy_data_permission_commands():
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

        # The panel worker must read one shared environment and Django signing
        # key, but no unrelated account should be able to read either file.
        for path in ('/usr/local/CyberCP/.env', '/usr/local/CyberCP/secret_key'):
            if os.path.exists(path):
                command = "chown root:cyberpanel %s" % path
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                command = "chmod 640 %s" % path
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        backup_env = '/usr/local/CyberCP/.env.backup'
        if os.path.exists(backup_env):
            command = "chown root:root %s" % backup_env
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            command = "chmod 600 %s" % backup_env
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        files = ['/etc/yum.repos.d/MariaDB.repo', '/etc/pdns/pdns.conf', '/etc/systemd/system/lscpd.service',
                 '/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                 '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                 '/etc/dovecot/dovecot.conf', '/usr/local/lsws/conf/httpd_config.xml',
                 '/usr/local/lsws/conf/modsec.conf', '/usr/local/lsws/conf/httpd.conf']

        for items in files:
            if os.path.exists(items):
                command = 'chmod 644 %s' % (items)
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        impFile = ['/etc/pure-ftpd/pure-ftpd.conf', '/etc/pure-ftpd/pureftpd-pgsql.conf',
                   '/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/pureftpd-ldap.conf',
                   '/etc/dovecot/dovecot.conf', '/etc/pdns/pdns.conf', '/etc/pure-ftpd/db/mysql.conf',
                   '/etc/powerdns/pdns.conf']

        for items in impFile:
            if os.path.exists(items):
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

        for dovecot_sql in ('/etc/dovecot/dovecot-sql.conf.ext',
                            '/etc/dovecot/dovecot-sql-2.4.conf'):
            if os.path.exists(dovecot_sql):
                os.chmod(dovecot_sql, 0o640)

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
                     '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py', '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxDB.py', '/usr/local/CyberCP/CLScript/UserInfo.py']

        for items in clScripts:
            command = 'chmod +x %s' % (items)
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'chmod 600 /usr/local/CyberCP/plogical/adminPass.py'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        if os.path.exists('/etc/cagefs/exclude/cyberpanelexclude'):
            command = 'chmod 600 /etc/cagefs/exclude/cyberpanelexclude'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "find /usr/local/CyberCP/ -name '*.pyc' -delete"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        if self.is_centos_family():
            command = 'chown root:pdns /etc/pdns/pdns.conf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'chmod 640 /etc/pdns/pdns.conf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        else:
            command = 'chown root:pdns /etc/powerdns/pdns.conf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'chmod 640 /etc/powerdns/pdns.conf'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        if os.path.exists('/usr/local/lscp/cyberpanel/logs/access.log'):
            command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        WriteToFile = open('/etc/fstab', 'a')
        WriteToFile.write('proc    /proc        proc        defaults,hidepid=2    0 0\n')
        WriteToFile.close()

        command = 'mount -o remount,rw,hidepid=2 /proc'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## symlink protection

        writeToFile = open('/usr/lib/sysctl.d/50-default.conf', 'a')
        writeToFile.writelines('fs.protected_hardlinks = 1\n')
        writeToFile.writelines('fs.protected_symlinks = 1\n')
        writeToFile.close()

        command = 'sysctl --system'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'chmod 700 %s' % ('/home/cyberpanel')
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        destPrivKey = "/usr/local/lscp/conf/key.pem"

        command = 'chmod 600 %s' % (destPrivKey)
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ###

    def install_unzip(self):
        self.stdOut("Install unzip")
        try:
            self.install_package("unzip")
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_unzip]")

    def install_zip(self):
        self.stdOut("Install zip")
        try:
            self.install_package("zip")
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_zip]")

    def download_install_phpmyadmin(self):
        try:

            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            command = 'wget -O /usr/local/CyberCP/public/phpmyadmin.zip https://github.com/usmannasir/cyberpanel/raw/stable/phpmyadmin.zip'

            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)

            command = 'unzip /usr/local/CyberCP/public/phpmyadmin.zip -d /usr/local/CyberCP/public'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)

            command = 'mv /usr/local/CyberCP/public/phpMyAdmin-*-all-languages /usr/local/CyberCP/public/phpmyadmin'
            subprocess.call(command, shell=True)

            command = 'rm -f /usr/local/CyberCP/public/phpmyadmin.zip'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin]',
                                  command, 1, 0, os.EX_OSERR)

            ## Write secret phrase

            rString = install_utils.generate_random_string(32)

            data = open('/usr/local/CyberCP/public/phpmyadmin/config.sample.inc.php', 'r').readlines()

            writeToFile = open('/usr/local/CyberCP/public/phpmyadmin/config.inc.php', 'w')

            writeE = 1

            phpMyAdminContent = """
$cfg['Servers'][$i]['AllowNoPassword'] = false;
$cfg['Servers'][$i]['auth_type'] = 'signon';
$cfg['Servers'][$i]['SignonSession'] = 'SignonSession';
$cfg['Servers'][$i]['SignonURL'] = 'phpmyadminsignin.php';
$cfg['Servers'][$i]['LogoutURL'] = 'phpmyadminsignin.php?logout';
"""

            for items in data:
                if items.find('blowfish_secret') > -1:
                    writeToFile.writelines(
                        "$cfg['blowfish_secret'] = '" + rString + "'; /* YOU MUST FILL IN THIS FOR COOKIE AUTH! */\n")
                elif items.find('/* Authentication type */') > -1:
                    writeToFile.writelines(items)
                    writeToFile.write(phpMyAdminContent)
                    writeE = 0
                elif items.find("$cfg['Servers'][$i]['AllowNoPassword']") > -1:
                    writeE = 1
                else:
                    if writeE:
                        writeToFile.writelines(items)

            writeToFile.writelines("$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';\n")

            writeToFile.close()

            os.mkdir('/usr/local/CyberCP/public/phpmyadmin/tmp')

            command = 'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin'
            preFlightsChecks.call(command, self.distro, '[chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin]',
                                  'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin', 1, 0, os.EX_OSERR)

            command = 'cp /usr/local/CyberCP/plogical/phpmyadminsignin.php /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.remotemysql == 'ON':
                configure_phpmyadmin_signon(
                    '/usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php',
                    self.mysqlhost,
                    self.mysqlport,
                )


        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [download_install_phpmyadmin]")
            return 0

    ###################################################### Email setup

    def install_postfix_dovecot(self):
        self.stdOut("Install dovecot - first remove postfix")

        try:
            if self.distro == centos:
                self.remove_package("postfix")
            elif self.distro == ubuntu:
                self.remove_package("postfix")

            self.stdOut("Install dovecot - do the install")

            if self.distro == centos:
                command = 'yum install --enablerepo=gf-plus -y postfix3 postfix3-ldap postfix3-mysql postfix3-pcre'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            elif self.distro == cent8:
                if is_el10_release():
                    command = 'dnf install -y postfix postfix-mysql cyrus-sasl-plain'
                else:
                    clAPVersion = FetchCloudLinuxAlmaVersionVersion()
                    type = clAPVersion.split('-')[0]
                    version = int(clAPVersion.split('-')[1])

                    if type == 'al' and version >= 90:
                        command = 'dnf --nogpg install -y https://mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el9.noarch.rpm'
                        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    else:
                        command = 'dnf --nogpg install -y https://mirror.ghettoforge.net/distributions/gf/gf-release-latest.gf.el8.noarch.rpm'
                        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                    command = 'dnf install --enablerepo=gf-plus postfix3 postfix3-mysql cyrus-sasl-plain -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            elif self.distro == openeuler:
                command = 'dnf install postfix cyrus-sasl-plain -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            else:
                self.install_package("debconf-utils", silent=True)
                file_name = self.cwd + '/pf.unattend.text'
                pf = open(file_name, 'w')
                pf.write('postfix postfix/mailname string ' + str(socket.getfqdn() + '\n'))
                pf.write('postfix postfix/main_mailer_type string "Internet Site"\n')
                pf.close()
                command = 'debconf-set-selections ' + file_name
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install postfix postfix-mysql'
                # os.remove(file_name)

            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

            ##

            if self.distro == centos:
                command = 'yum --enablerepo=gf-plus -y install dovecot23 dovecot23-mysql'
            elif self.distro == cent8:
                clAPVersion = FetchCloudLinuxAlmaVersionVersion()
                type = clAPVersion.split('-')[0]
                version = int(clAPVersion.split('-')[1])
                if type == 'al' and version >= 90:
                    command = 'dnf install -y dovecot dovecot-mysql'
                else:
                    command = 'dnf install --enablerepo=gf-plus dovecot23 dovecot23-mysql -y'
            elif self.distro == openeuler:
                command = 'dnf install -y dovecot dovecot-mysql'
            else:
                command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install dovecot-mysql dovecot-imapd dovecot-pop3d'

            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_postfix_dovecot]")
            return 0

        return 1

    def setup_email_Passwords(self, mysqlPassword, mysql):
        try:

            logging.InstallLog.writeToFile("Setting up authentication for Postfix and Dovecot...")

            os.chdir(self.cwd)

            mysql_virtual_domains = "email-configs-one/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "email-configs-one/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "email-configs-one/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "email-configs-one/mysql-virtual_email2email.cf"
            dovecot_24 = self.distro == ubuntu and get_Ubuntu_release() >= 26.0
            if dovecot_24:
                dovecotmysql = "email-configs-one/dovecot-sql-2.4.conf"
            else:
                dovecotmysql = "email-configs-one/dovecot-sql.conf.ext"

            ### update password:

            data = open(dovecotmysql, "r").readlines()

            writeDataToFile = open(dovecotmysql, "w")

            if dovecot_24:
                if self.remotemysql == 'ON':
                    database_host = self.mysqlhost
                    database_port = self.mysqlport
                else:
                    database_host = '127.0.0.1' if mysql == 'Two' else 'localhost'
                    database_port = '3307' if mysql == 'Two' else '3306'
                for items in data:
                    if items.startswith('mysql '):
                        writeDataToFile.write('mysql %s {\n' % database_host)
                    elif items.strip().startswith('password ='):
                        writeDataToFile.write('    password = %s\n' % mysqlPassword)
                    elif items.strip().startswith('port ='):
                        writeDataToFile.write('    port = %s\n' % database_port)
                    else:
                        writeDataToFile.write(items)
            else:
                dataWritten = dovecot_connect_line(
                    mysqlPassword,
                    mysql=mysql,
                    remote=(self.remotemysql == 'ON'),
                    host=self.mysqlhost,
                    port=self.mysqlport,
                )

                for items in data:
                    if items.find("connect") > -1:
                        writeDataToFile.writelines(dataWritten)
                    else:
                        writeDataToFile.writelines(items)

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

            writeDataToFile.close()

            if self.remotemysql == 'ON':
                if not dovecot_24:
                    command = "sed -i 's|host=localhost|host=%s|g' %s" % (self.mysqlhost, dovecotmysql)
                    preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                    command = "sed -i 's|port=3306|port=%s|g' %s" % (self.mysqlport, dovecotmysql)
                    preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                ##

                command = "sed -i 's|localhost|%s:%s|g' %s" % (self.mysqlhost, self.mysqlport, mysql_virtual_domains)
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_forwardings)
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_mailboxes)
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

                command = "sed -i 's|localhost|%s:%s|g' %s" % (
                    self.mysqlhost, self.mysqlport, mysql_virtual_email2email)
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

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
            self.stdOut(
                "[ERROR] Error converting: " + filename + " from centos defaults to ubuntu defaults: " + str(err), 1,
                1, os.EX_OSERR)

    def setup_postfix_dovecot_config(self, mysql):
        try:
            logging.InstallLog.writeToFile("Configuring postfix and dovecot...")

            os.chdir(self.cwd)

            mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
            main = "/etc/postfix/main.cf"
            master = "/etc/postfix/master.cf"
            dovecot = "/etc/dovecot/dovecot.conf"
            dovecot_24 = self.distro == ubuntu and get_Ubuntu_release() >= 26.0
            if dovecot_24:
                dovecotmysql = "/etc/dovecot/dovecot-sql-2.4.conf"
            else:
                dovecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"

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

            if os.path.exists(dovecot):
                os.remove(dovecot)

            if os.path.exists(dovecotmysql):
                os.remove(dovecotmysql)

            ###############Getting SSL

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/postfix/key.pem -out /etc/postfix/cert.pem'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'openssl req -newkey rsa:2048 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /etc/dovecot/key.pem -out /etc/dovecot/cert.pem'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Cleanup config files for ubuntu
            if self.distro == ubuntu:
                preFlightsChecks.stdOut("Cleanup postfix/dovecot config files", 1)

                self.centos_lib_dir_to_ubuntu("email-configs-one/master.cf", "/usr/libexec/", "/usr/lib/")
                self.centos_lib_dir_to_ubuntu("email-configs-one/main.cf", "/usr/libexec/postfix",
                                              "/usr/lib/postfix/sbin")

            ########### Copy config files

            shutil.copy("email-configs-one/mysql-virtual_domains.cf", "/etc/postfix/mysql-virtual_domains.cf")
            shutil.copy("email-configs-one/mysql-virtual_forwardings.cf",
                        "/etc/postfix/mysql-virtual_forwardings.cf")
            shutil.copy("email-configs-one/mysql-virtual_mailboxes.cf", "/etc/postfix/mysql-virtual_mailboxes.cf")
            shutil.copy("email-configs-one/mysql-virtual_email2email.cf",
                        "/etc/postfix/mysql-virtual_email2email.cf")
            shutil.copy("email-configs-one/main.cf", main)
            shutil.copy("email-configs-one/master.cf", master)
            if dovecot_24:
                shutil.copy("email-configs-one/dovecot-2.4.conf", dovecot)
                shutil.copy("email-configs-one/dovecot-sql-2.4.conf", dovecotmysql)
            else:
                shutil.copy("email-configs-one/dovecot.conf", dovecot)
                shutil.copy("email-configs-one/dovecot-sql.conf.ext", dovecotmysql)
            
            ########### Set custom settings

            # We are going to leverage postconfig -e to edit the settings for hostname
            command = "postconf -e 'myhostname = %s'" % (str(socket.getfqdn()))
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # We are explicitly going to use sed to set the hostname default from "myhostname = server.example.com"
            # to the fqdn from socket if the default is still found
            command = "sed -i 's|server.example.com|%s|g' %s" % (str(socket.getfqdn()), main)
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

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

            self.manage_service('postfix', 'enable')
            self.manage_service('postfix', 'start')

            ######################################## Permissions

            command = 'chgrp dovecot ' + dovecotmysql
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= ' + dovecotmysql
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ## The dovecot.conf template enables the sieve (pigeonhole) plugin in the
            ## `protocols` line and the `protocol lda` mail_plugins, but no distro
            ## branch above installs pigeonhole. Where it is absent (and on AlmaLinux 9
            ## /dovecot23 it cannot be installed — the package conflicts) Dovecot
            ## refuses to start with "unknown protocol sieve" and all mail defers.
            ## Strip sieve from those two lines only when the plugin is not installed,
            ## so servers that do have pigeonhole keep sieve filtering. #1733
            sieveAvailable = False
            for modDir in ('/usr/lib/dovecot/modules', '/usr/lib64/dovecot/modules',
                           '/usr/lib/dovecot', '/usr/lib64/dovecot'):
                try:
                    if os.path.isdir(modDir) and any('sieve' in fn for fn in os.listdir(modDir)):
                        sieveAvailable = True
                        break
                except Exception:
                    pass

            if not sieveAvailable and os.path.exists(dovecot):
                try:
                    with open(dovecot, 'r') as f:
                        confLines = f.readlines()
                    with open(dovecot, 'w') as f:
                        for confLine in confLines:
                            key = confLine.split('=', 1)[0].strip()
                            if key in ('protocols', 'mail_plugins') and 'sieve' in confLine:
                                prefix, _, rhs = confLine.partition('=')
                                tokens = [t for t in rhs.split() if t not in ('sieve', 'managesieve')]
                                confLine = '%s= %s\n' % (prefix, ' '.join(tokens))
                            f.write(confLine)
                    logging.InstallLog.writeToFile(
                        "Sieve plugin not installed; removed sieve from dovecot.conf so Dovecot can start.")
                except BaseException as sieveMsg:
                    logging.InstallLog.writeToFile(
                        '[ERROR] Could not strip sieve from dovecot.conf: ' + str(sieveMsg))

            ################################### Restart dovecot

            self.manage_service('dovecot', 'enable')
            self.manage_service('dovecot', 'start')

            ##

            self.manage_service('postfix', 'restart')

            ## chaging permissions for main.cf

            command = "chmod 755 " + main
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.distro == ubuntu:
                command = "mkdir -p /etc/pki/dovecot/private/"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = "mkdir -p /etc/pki/dovecot/certs/"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                # Copy self-signed certs to where Postfix main.cf expects them
                command = "cp /etc/dovecot/cert.pem /etc/pki/dovecot/certs/dovecot.pem"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = "cp /etc/dovecot/key.pem /etc/pki/dovecot/private/dovecot.pem"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = "chmod 600 /etc/pki/dovecot/private/dovecot.pem"
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

                self.manage_service('dovecot', 'restart')

            logging.InstallLog.writeToFile("Postfix and Dovecot configured")
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setup_postfix_dovecot_config]")
            return 0

        return 1

    ###################################################### Email setup ends!

    def reStartLiteSpeed(self):
        command = install_utils.format_restart_litespeed_command(self.server_root_path)
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
            preFlightsChecks.call('DEBIAN_FRONTEND=noninteractive apt-get -y remove ufw', self.distro, '[remove_ufw]', 'Remove ufw firewall ' +
                                  '(using firewalld)', 1, 0, os.EX_OSERR, True)
        except:
            pass
        return True


    def findSSHPort(self):
        try:
            with open('/etc/ssh/sshd_config', 'r') as ssh_config:
                for line in ssh_config:
                    match = re.match(r'^\s*Port\s+(\d+)\s*(?:#.*)?$', line, re.IGNORECASE)
                    if match:
                        port = int(match.group(1))
                        if 1 <= port <= 65535:
                            return str(port)

            return '22'
        except BaseException as msg:
            return '22'

    def installFirewalld(self):

        if self.distro == ubuntu:
            self.removeUfw()

        try:
            preFlightsChecks.stdOut("Enabling Firewall!")

            self.install_package("firewalld")

            ######
            if self.distro == centos:
                # Not available in ubuntu
                self.manage_service('dbus', 'restart')

            # Newer systemd releases terminate the installer's SSH session scope
            # when logind restarts. Keep earlier distributions unchanged.
            skip_logind_restart = is_el10_release() or (
                self.distro == ubuntu and get_Ubuntu_release() >= 26.04
            )
            if not skip_logind_restart:
                self.manage_service('systemd-logind', 'restart')
            else:
                logging.InstallLog.writeToFile(
                    "Keeping systemd-logind running during installation."
                )

            self.manage_service('firewalld', 'start')
            self.manage_service('firewalld', 'enable')

            FirewallUtilities.addRule("tcp", "8090")
            FirewallUtilities.addRule("tcp", "7080")
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
            FirewallUtilities.addRule("tcp", "8888")
            FirewallUtilities.addRule("udp", "443")
            FirewallUtilities.addRule("tcp", "40110-40210")

            try:
                SSHPort = self.findSSHPort()
                if SSHPort != '22':
                    FirewallUtilities.addRule('tcp', SSHPort)
            except BaseException as msg:
                logging.InstallLog.writeToFile(f'[Error Custom SSH port] {str(msg)}')
                preFlightsChecks.stdOut(f'[Error Custom SSH port] {str(msg)}')


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
                self.install_package("gcc g++ make autoconf rcs")
            else:
                self.install_package("gcc gcc-c++ make autoconf glibc")

            if self.distro == ubuntu:
                # libpcre3/libpcre3-dev (PCRE1) were dropped from Ubuntu 26.04; only
                # pcre2 remains. Older releases keep PCRE1 - lscpd links against
                # libpcre.so.1 there (see the symlink in installLSCPD).
                release = install_utils.get_Ubuntu_release(use_print=False, exit_on_error=False)
                if release and release >= 26.04:
                    pcre_packages = "libpcre2-8-0 libpcre2-dev"
                else:
                    pcre_packages = "libpcre3 libpcre3-dev"
                self.install_package(f"{pcre_packages} openssl libexpat1 libexpat1-dev libgeoip-dev zlib1g zlib1g-dev libudns-dev whichman curl")
            else:
                self.install_package("pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel")

            command = 'tar zxf lscp.tar.gz -C /usr/local/'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ###

            lscpdPath = '/usr/local/lscp/bin/lscpd'

            # if subprocess.check_output('uname -a').decode("utf-8").find("aarch64") == -1:
            #     lscpdPath = '/usr/local/lscp/bin/lscpd'
            #
            #     lscpdSelection = 'lscpd-0.3.1'
            #     if os.path.exists('/etc/lsb-release'):
            #         result = open('/etc/lsb-release', 'r').read()
            #         if result.find('22.04') > -1 or result.find('24.04') > -1 or result.find('26.04') > -1:
            #             lscpdSelection = 'lscpd.0.4.0'
            # else:
            #     lscpdSelection = 'lscpd.aarch64'

            try:
                try:
                    result = subprocess.run('uname -a', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                except:
                    result = subprocess.run('uname -a', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

                if result.stdout.find('aarch64') == -1:
                    lscpdSelection = 'lscpd-0.3.1'
                    if os.path.exists('/etc/lsb-release'):
                        result = open('/etc/lsb-release', 'r').read()
                        if result.find('22.04') > -1 or result.find('24.04') > -1 or result.find('26.04') > -1:
                            lscpdSelection = 'lscpd.0.4.0'
                else:
                    lscpdSelection = 'lscpd.aarch64'

            except:

                lscpdSelection = 'lscpd-0.3.1'
                if os.path.exists('/etc/lsb-release'):
                    result = open('/etc/lsb-release', 'r').read()
                    if result.find('22.04') > -1 or result.find('24.04') > -1 or result.find('26.04') > -1:
                        lscpdSelection = 'lscpd.0.4.0'


            command = f'cp -f /usr/local/CyberCP/{lscpdSelection} /usr/local/lscp/bin/{lscpdSelection}'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = 'rm -f /usr/local/lscp/bin/lscpd'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = f'mv /usr/local/lscp/bin/{lscpdSelection} /usr/local/lscp/bin/lscpd'
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = 'chmod 755 %s' % (lscpdPath)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ##

            command = 'openssl req -newkey rsa:1024 -new -nodes -x509 -days 3650 -subj "/C=US/ST=Denial/L=Springfield/O=Dis/CN=www.example.com" -keyout /usr/local/lscp/conf/key.pem -out /usr/local/lscp/conf/cert.pem'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Create lsphp symlink for fcgi-bin with better error handling
            self.setup_lsphp_symlink()

            if self.is_centos_family():
                command = 'adduser lscpd -M -d /usr/local/lscp'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'groupadd lscpd'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            else:
                self.setupLSCPDAccount()

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

            command = "wget http://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "tar xf wsgi-lsapi-2.1.tgz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir("wsgi-lsapi-2.1")

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

            command = "chmod 755 /usr/local/lscpd /usr/local/lscpd/admin"
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
            self.manage_service('lscpd', 'enable')

            ##
            count = 0

            # In Ubuntu, the library that lscpd looks for is libpcre.so.1, but the one it installs is libpcre.so.3...
            # Ubuntu 26.04 dropped PCRE1 entirely, so libpcre.so.3 no longer exists there and
            # this symlink has nothing to point at. Only create it when the source is present;
            # on 26.04 lscpd is expected to be linked against pcre2 by LiteSpeed's resolute build.
            if self.distro == ubuntu:
                pcre_source = '/lib/x86_64-linux-gnu/libpcre.so.3'
                pcre_target = '/lib/x86_64-linux-gnu/libpcre.so.1'
                if os.path.exists(pcre_source) and not os.path.exists(pcre_target):
                    command = f'ln -s {pcre_source} {pcre_target}'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                elif not os.path.exists(pcre_source):
                    logging.InstallLog.writeToFile(
                        'libpcre.so.3 not present (expected on Ubuntu 26.04+); skipping libpcre.so.1 symlink')

            ##

            command = 'systemctl start lscpd'
            # preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            preFlightsChecks.stdOut("LSCPD Daemon Set!")

            logging.InstallLog.writeToFile("LSCPD Daemon Set!")

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setupLSCPDDaemon]")
            return 0

        return 1

    def setup_cron(self):

        try:
            ## first install crontab

            if self.is_centos_family():
                self.install_package('cronie')
            else:
                self.install_package('cron')

            if self.is_centos_family():
                self.manage_service('crond', 'enable')
                self.manage_service('crond', 'start')
            else:
                self.manage_service('cron', 'enable')
                self.manage_service('cron', 'start')

            ##

            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            if os.path.exists(CentOSPath) or os.path.exists(openEulerPath):
                cronPath = '/var/spool/cron/root'
            else:
                cronPath = '/var/spool/cron/crontabs/root'

            cronFile = open(cronPath, "w")

            content = """
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1
0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1
0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1
0 0 * * 4 /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1
7 0 * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
0 0 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Daily
0 0 * * 0 /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py Weekly

*/30 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '30 Minutes'
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '1 Hour'
0 */6 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '6 Hours'
0 */12 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '12 Hours'
0 1 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '1 Day'
0 0 */3 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '3 Days'
0 0 * * 0 /usr/local/CyberCP/bin/python /usr/local/CyberCP/IncBackups/IncScheduler.py '1 Week'

*/3 * * * * if ! find /home/*/public_html/ -maxdepth 2 -type f -newer /usr/local/lsws/cgid -name '.htaccess' -exec false {} +; then /usr/local/lsws/bin/lswsctrl restart; fi
"""

            cronFile.write(content)
            cronFile.close()

            ### Check and remove OLS restart if lsws ent detected

            if not os.path.exists('/usr/local/lsws/bin/openlitespeed'):

                data = open(cronPath, 'r').readlines()

                writeToFile = open(cronPath, 'w')

                for items in data:
                    if items.find('-maxdepth 2 -type f -newer') > -1:
                        pass
                    else:
                        writeToFile.writelines(items)

                writeToFile.close()

            if not os.path.exists(CentOSPath) or not os.path.exists(openEulerPath):
                command = 'chmod 600 %s' % (cronPath)
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if self.is_centos_family():
                self.manage_service('crond', 'restart')
            else:
                self.manage_service('cron', 'restart')

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
            self.install_package('rsync')

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_rsync]")
            return 0

    def test_Requests(self):
        try:
            import requests
            getVersion = requests.get('https://cyberpanel.net/version.txt')
            latest = getVersion.json()
        except BaseException as msg:

            # Handle Ubuntu 24.04's externally-managed-environment policy
            pip_flags = ""
            if self.distro == ubuntu:
                try:
                    release = install_utils.get_Ubuntu_release(use_print=False, exit_on_error=False)
                    if release and release >= 24.04:
                        pip_flags = " --break-system-packages"
                except:
                    pass  # If version detection fails, try without flags

            command = f"pip uninstall --yes{pip_flags} urllib3"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = f"pip uninstall --yes{pip_flags} requests"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = f"pip install{pip_flags} http://mirror.cyberpanel.net/urllib3-1.22.tar.gz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = f"pip install{pip_flags} http://mirror.cyberpanel.net/requests-2.18.4.tar.gz"
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
        if is_el10_release():
            return 1

        try:

            pathToRemoveGarbageFile = os.path.join(self.server_root_path, "modules/mod_security.so")
            os.remove(pathToRemoveGarbageFile)

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [modSecPreReqs]")
            return 0

    def installOpenDKIM(self):
        try:
            if self.distro == cent8 or self.distro == openeuler or self.distro == ubuntu:
                self.install_package('opendkim opendkim-tools')

                if self.distro == ubuntu and get_Ubuntu_release() >= 26.0:
                    os.makedirs('/etc/opendkim/keys', exist_ok=True)
                    for table_path in (
                        '/etc/opendkim/KeyTable',
                        '/etc/opendkim/SigningTable',
                        '/etc/opendkim/TrustedHosts',
                    ):
                        if not os.path.exists(table_path):
                            with open(table_path, 'a'):
                                pass
                        os.chmod(table_path, 0o644)
                elif is_el10_release():
                    keys_path = '/etc/opendkim/keys'
                    os.makedirs(keys_path, exist_ok=True)
                    shutil.chown(keys_path, user='root', group='opendkim')
                    os.chmod(keys_path, 0o750)
                    for table_path in (
                        '/etc/opendkim/KeyTable',
                        '/etc/opendkim/SigningTable',
                        '/etc/opendkim/TrustedHosts',
                    ):
                        if not os.path.exists(table_path):
                            with open(table_path, 'a'):
                                pass
                        shutil.chown(table_path, user='root', group='opendkim')
                        os.chmod(table_path, 0o640)
            else:
                self.install_package('opendkim')

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

            if self.distro == ubuntu and get_Ubuntu_release() >= 26.0:
                data = open(openDKIMConfigurePath, 'r').readlines()
                with open(openDKIMConfigurePath, 'w') as writeToFile:
                    writeToFile.writelines(normalize_opendkim_socket_lines(data))
            elif self.distro == ubuntu or self.distro == cent8:
                data = open(openDKIMConfigurePath, 'r').readlines()
                writeToFile = open(openDKIMConfigurePath, 'w')
                for items in data:
                    if items.find('Socket') > -1 and items.find('local:'):
                        writeToFile.writelines('Socket  inet:8891@localhost\n')
                    else:
                        writeToFile.writelines(items)
                writeToFile.close()

            #### Restarting Postfix and OpenDKIM

            self.manage_service('opendkim', 'start')
            self.manage_service('opendkim', 'enable')
            self.manage_service('postfix', 'start')

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [configureOpenDKIM]")
            return 0

        return 1

    def setupCLI(self):
        command = "ln -s /usr/local/CyberCP/cli/cyberPanel.py /usr/bin/cyberpanel"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod +x /usr/local/CyberCP/cli/cyberPanel.py"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def setupPHPSymlink(self):
        try:
            # Check if PHP 8.2 exists
            if not os.path.exists('/usr/local/lsws/lsphp82/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.2 not found, ensuring it's installed...")
                
                # Install PHP 8.2 based on OS
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'yum install lsphp82 lsphp82-* -y'
                else:
                    command = 'env DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp82 lsphp82-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Check if PHP 8.3 exists
            if not os.path.exists('/usr/local/lsws/lsphp83/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.3 not found, ensuring it's installed...")
                
                # Install PHP 8.3 based on OS
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'yum install lsphp83 lsphp83-* -y'
                else:
                    command = 'env DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp83 lsphp83-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                # Verify installation
                if not os.path.exists('/usr/local/lsws/lsphp83/bin/php'):
                    logging.InstallLog.writeToFile('[ERROR] Failed to install PHP 8.3')
                    return 0

            # Install PHP 8.4
            if not os.path.exists('/usr/local/lsws/lsphp84/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.4 not found, ensuring it's installed...")
                
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'yum install lsphp84 lsphp84-* -y'
                else:
                    command = 'env DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp84 lsphp84-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Install PHP 8.5
            if not os.path.exists('/usr/local/lsws/lsphp85/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.5 not found, ensuring it's installed...")
                
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'yum install lsphp85 lsphp85-* -y'
                else:
                    command = 'env DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp85 lsphp85-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Remove existing PHP symlink if it exists (lexists also catches a
            # broken symlink, which os.path.exists misses — otherwise the ln below
            # would fail with "File exists" and leave /usr/bin/php broken). (#1727)
            if os.path.lexists('/usr/bin/php'):
                os.remove('/usr/bin/php')

            # Create symlink to PHP 8.3 (default)
            command = 'ln -s /usr/local/lsws/lsphp83/bin/php /usr/bin/php'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            logging.InstallLog.writeToFile("[setupPHPSymlink] PHP symlink updated to PHP 8.3 successfully.")

        except OSError as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setupPHPSymlink]")
            return 0

    def setup_lsphp_symlink(self):
        """Create lsphp symlink in fcgi-bin directory with robust error handling"""
        try:
            fcgi_bin_dir = "/usr/local/lscp/fcgi-bin"
            lsphp_target = os.path.join(fcgi_bin_dir, "lsphp")

            # Ensure fcgi-bin directory exists
            if not os.path.exists(fcgi_bin_dir):
                os.makedirs(fcgi_bin_dir, exist_ok=True)
                logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Created fcgi-bin directory: {fcgi_bin_dir}")

            # Remove existing lsphp file/symlink if it exists
            if os.path.exists(lsphp_target) or os.path.islink(lsphp_target):
                os.remove(lsphp_target)
                logging.InstallLog.writeToFile("[setup_lsphp_symlink] Removed existing lsphp file/symlink")

            # Try to find and use the best available PHP version
            # Priority: 83, 82, 81, 80, 74, 73, 72 (newest to oldest)
            php_versions = ['83', '82', '81', '80', '74', '73', '72']
            lsphp_source = None

            for php_ver in php_versions:
                candidate_path = f"/usr/local/lsws/lsphp{php_ver}/bin/lsphp"
                if os.path.exists(candidate_path):
                    lsphp_source = candidate_path
                    logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Found lsphp binary: {candidate_path}")
                    break

            # If no lsphp binary found, try to find php binary as fallback
            if not lsphp_source:
                for php_ver in php_versions:
                    candidate_path = f"/usr/local/lsws/lsphp{php_ver}/bin/php"
                    if os.path.exists(candidate_path):
                        lsphp_source = candidate_path
                        logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Using php binary as fallback: {candidate_path}")
                        break

            # If still no source found, try admin_php as last resort
            if not lsphp_source:
                admin_php_path = "/usr/local/lscp/admin/fcgi-bin/admin_php"
                if os.path.exists(admin_php_path):
                    lsphp_source = admin_php_path
                    logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Using admin_php as fallback: {admin_php_path}")

                admin_php5_path = "/usr/local/lscp/admin/fcgi-bin/admin_php5"
                if not lsphp_source and os.path.exists(admin_php5_path):
                    lsphp_source = admin_php5_path
                    logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Using admin_php5 as fallback: {admin_php5_path}")

            # Create the symlink/copy
            if lsphp_source:
                try:
                    # Try to create symlink first (preferred)
                    os.symlink(lsphp_source, lsphp_target)
                    logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Created symlink: {lsphp_target} -> {lsphp_source}")
                except OSError:
                    # If symlink fails (e.g., cross-filesystem), copy the file
                    shutil.copy2(lsphp_source, lsphp_target)
                    logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] Copied file: {lsphp_source} -> {lsphp_target}")

                # Set proper permissions
                os.chmod(lsphp_target, 0o755)
                logging.InstallLog.writeToFile("[setup_lsphp_symlink] Set permissions to 755")

                # Verify the file was created successfully
                if os.path.exists(lsphp_target):
                    logging.InstallLog.writeToFile("[setup_lsphp_symlink] lsphp symlink creation successful")
                    return True
                else:
                    logging.InstallLog.writeToFile("[setup_lsphp_symlink] ERROR: lsphp file was not created")
                    return False
            else:
                logging.InstallLog.writeToFile("[setup_lsphp_symlink] ERROR: No suitable PHP binary found")
                return False

        except Exception as e:
            logging.InstallLog.writeToFile(f"[setup_lsphp_symlink] ERROR: {str(e)}")
            return False

    def setupPHPAndComposer(self):
        try:
            # First setup the PHP symlink
            self.setupPHPSymlink()

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

            #command = "cp /usr/local/lsws/lsphp71/bin/php /usr/bin/"
            #preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

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
        res = subprocess.call(shlex.split('DEBIAN_FRONTEND=noninteractive apt-get -y install ' + package))
        if res != 0:
            preFlightsChecks.stdOut("Error #" + str(res) + ' installing:' + package + '.  This may not be an issue ' \
                                                                                      'but may affect installation of something later',
                                    1)

        return res  # Though probably not used

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
    def fixSudoers():
        try:
            distroPath = '/etc/lsb-release'

            if not os.path.exists(distroPath):
                fileName = '/etc/sudoers'
                data = open(fileName, 'r').readlines()

                writeDataToFile = open(fileName, 'w')
                for line in data:
                    if line.find("root") > -1 and line.find("ALL=(ALL)") > -1 and line[0] != '#':
                        writeDataToFile.writelines('root	ALL=(ALL:ALL) 	ALL\n')
                    else:
                        writeDataToFile.write(line)
                writeDataToFile.close()

        except IOError as err:
            pass

    @staticmethod
    def setUpFirstAccount():
        try:
            command = 'python /usr/local/CyberCP/plogical/adminPass.py --password 1234567'
            subprocess.call(shlex.split(command))
        except:
            pass

    def installRestic(self):
        try:

            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            if os.path.exists(CentOSPath) or os.path.exists(openEulerPath):
                if self.distro == centos:
                    command = 'yum install -y yum-plugin-copr'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    command = 'yum copr enable -y copart/restic'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                command = 'yum install -y restic'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                command = 'restic self-update'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            else:
                # Skip apt-get update as it was already done in cyberpanel.sh
                # Just install the package directly
                command = 'DEBIAN_FRONTEND=noninteractive apt-get install restic -y'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)

        except:
            pass

    def installCLScripts(self):
        try:

            CentOSPath = '/etc/redhat-release'
            openEulerPath = '/etc/openEuler-release'

            if os.path.exists(CentOSPath) or os.path.exists(openEulerPath):
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

        ##

        os.chdir(self.cwd)

        confPath = '/usr/local/lsws/conf/'

        if os.path.exists('%shttpd.conf' % (confPath)):
            os.remove('%shttpd.conf' % (confPath))

        shutil.copy('litespeed/httpd-redis.conf', '%shttpd.conf' % (confPath))

        ## start and enable

        command = 'systemctl start redis'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'systemctl enable redis'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def disablePackegeUpdates(self):
        if self.distro == centos:
            mainConfFile = '/etc/yum.conf'
            content = 'exclude=MariaDB-client MariaDB-common MariaDB-devel MariaDB-server MariaDB-shared ' \
                      'pdns pdns-backend-mysql dovecot dovecot-mysql postfix3 postfix3-ldap postfix3-mysql ' \
                      'postfix3-pcre restic opendkim libopendkim pure-ftpd ftp\n'

            writeToFile = open(mainConfFile, 'a')
            writeToFile.write(content)
            writeToFile.close()


    def installDNS_CyberPanelACMEFile(self):

        os.chdir(self.cwd)

        filePath = '/root/.acme.sh/dns_cyberpanel.sh'
        shutil.copy('dns_cyberpanel.sh', filePath)

        command = f'chmod +x {filePath}'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
    
    def startDeferredServices(self):
        """Start services that were deferred during installation (PowerDNS and Pure-FTPd)
        These services require database tables that are created by Django migrations"""
        
        preFlightsChecks.stdOut("Starting deferred services that depend on database tables...")
        
        # Start PowerDNS if it was installed
        if os.path.exists('/home/cyberpanel/powerdns'):
            # Bring the PDNS gmysql schema up to PDNS 4.7+/5.x expectations
            # before first start. The AlmaLinux/RHEL mirrors may already serve
            # PDNS 5.x, whose binary requires `domains.catalog` and
            # `domains.options`. Running this migration here keeps fresh
            # installs from hitting the same crash-loop that bites upgrades.
            try:
                sys.path.append('/usr/local/CyberCP')
                from plogical.pdnsSchemaMigration import migrate_pdns_schema
                migrate_pdns_schema(restart_service=False)
            except BaseException as msg:
                preFlightsChecks.stdOut(
                    "[WARNING] PDNS schema pre-flight migration failed: " + str(msg))

            preFlightsChecks.stdOut("Starting PowerDNS service...")
            command = 'systemctl start pdns'
            result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            if result == 1:
                # Check if service started successfully
                command = 'systemctl is-active pdns'
                try:
                    output = subprocess.check_output(shlex.split(command)).decode("utf-8").strip()
                    if output == 'active':
                        preFlightsChecks.stdOut("PowerDNS service started successfully!")
                    else:
                        preFlightsChecks.stdOut("[WARNING] PowerDNS service may not have started properly. Status: " + output)
                except:
                    preFlightsChecks.stdOut("[WARNING] Could not verify PowerDNS service status")
        
        # Start Pure-FTPd if it was installed
        if os.path.exists('/home/cyberpanel/pureftpd'):
            # Configure Pure-FTPd for Ubuntu 24.04 (SHA512 password hashing compatibility)
            if self.distro == ubuntu:
                import install_utils
                try:
                    release = install_utils.get_Ubuntu_release(use_print=False, exit_on_error=False)
                    if release and release >= 24.04:
                        preFlightsChecks.stdOut("Configuring Pure-FTPd for Ubuntu 24.04...")
                        # Change MYSQLCrypt from md5 to crypt for SHA512 compatibility
                        command = "sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' /etc/pure-ftpd/db/mysql.conf"
                        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                except:
                    pass  # If version detection fails, continue without configuration change

            preFlightsChecks.stdOut("Starting Pure-FTPd service...")
            ftpService = self.pureFTPDServiceName(self.distro)
            command = f'systemctl start {ftpService}'
            result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            if result == 1:
                # Check if service started successfully
                command = f'systemctl is-active {ftpService}'
                try:
                    output = subprocess.check_output(shlex.split(command)).decode("utf-8").strip()
                    if output == 'active':
                        preFlightsChecks.stdOut("Pure-FTPd service started successfully!")
                    else:
                        preFlightsChecks.stdOut("[WARNING] Pure-FTPd service may not have started properly. Status: " + output)
                except:
                    preFlightsChecks.stdOut("[WARNING] Could not verify Pure-FTPd service status")

def configure_jwt_secret():
    try:
        sys.path.insert(0, '/usr/local/CyberCP')
        from plogical.securityUtils import (
            DEFAULT_TERMINAL_JWT_SECRET_FILE,
            TERMINAL_JWT_SECRET_FILE_ENV,
            get_terminal_jwt_secret,
        )
        get_terminal_jwt_secret(create_if_missing=True)
        secret_path = os.environ.get(
            TERMINAL_JWT_SECRET_FILE_ENV,
            DEFAULT_TERMINAL_JWT_SECRET_FILE,
        )
        if os.path.exists(secret_path):
            shutil.chown(secret_path, user='cyberpanel', group='cyberpanel')
            os.chmod(secret_path, 0o600)
        print("Configured Web Terminal authentication secret")
    except Exception as error:
        preFlightsChecks.stdOut(
            "[WARNING] Could not configure Web Terminal authentication: %s" % error
        )

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
    parser.add_argument('--remotemysql', help='Opt to choose local or remote MySQL')
    parser.add_argument('--mysqlhost', help='MySQL host if remote is chosen.')
    parser.add_argument('--mysqldb', help='MySQL DB if remote is chosen.')
    parser.add_argument('--mysqluser', help='MySQL user if remote is chosen.')
    parser.add_argument('--mysqlpassword', help='MySQL password if remote is chosen.')
    parser.add_argument('--mysqlport', help='MySQL port if remote is chosen.')
    parser.add_argument('--container', default='OFF', help='Container runtime install (ON/OFF).')

    args = parser.parse_args()

    if args.remotemysql == 'ON':
        try:
            build_database_config(
                remote=True,
                host=args.mysqlhost,
                port=args.mysqlport,
                root_db=args.mysqldb,
                root_user=args.mysqluser,
            )
        except DatabaseConfigError as error:
            parser.error(str(error))

    logging.InstallLog.ServerIP = args.publicip
    logging.InstallLog.writeToFile("Starting CyberPanel installation..,10")
    preFlightsChecks.stdOut("Starting CyberPanel installation..")

    if args.ent is None:
        ent = 0
        preFlightsChecks.stdOut("OpenLiteSpeed web server will be installed.")
    else:
        if args.ent == 'ols':
            ent = 0
            preFlightsChecks.stdOut("OpenLiteSpeed web server will be installed.")
        else:
            preFlightsChecks.stdOut("LiteSpeed Enterprise web server will be installed.")
            ent = 1
            if args.serial is not None:
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
    os.chmod("/etc/cyberpanel", 0o755)

    machineIP = open("/etc/cyberpanel/machineIP", "w")
    machineIP.writelines(args.publicip)
    machineIP.close()
    os.chmod("/etc/cyberpanel/machineIP", 0o644)

    cwd = os.getcwd()

    if args.remotemysql == 'ON':
        remotemysql = args.remotemysql
        mysqlhost = args.mysqlhost
        mysqluser = args.mysqluser
        mysqlpassword = os.environ.pop(
            'CP_INSTALL_MYSQL_PASSWORD', None
        )
        if mysqlpassword is None:
            # Retained for callers that invoke install.py directly. The shell
            # installer uses the process environment so the secret is not
            # exposed in the command line shown by process tools.
            mysqlpassword = args.mysqlpassword
        mysqlport = args.mysqlport
        mysqldb = args.mysqldb

        if preFlightsChecks.debug:
            # debug is on for every installation and this output lands in
            # /root/install.log, which is what people paste into support
            # threads. Print what is needed to diagnose a connection problem
            # and never the password itself.
            print('mysqlhost: %s, mysqldb: %s,  mysqluser: %s, mysqlpassword: %s, mysqlport: %s' % (
                mysqlhost, mysqldb, mysqluser,
                '<set>' if mysqlpassword else '<empty>', mysqlport))
            time.sleep(10)

    else:
        remotemysql = args.remotemysql
        mysqlhost = ''
        mysqluser = ''
        mysqlpassword = ''
        mysqlport = ''
        mysqldb = ''

    distro = get_distro()
    checks = preFlightsChecks("/usr/local/lsws/", args.publicip, "/usr/local", cwd, "/usr/local/CyberCP", distro,
                              remotemysql, mysqlhost, mysqldb, mysqluser, mysqlpassword, mysqlport)
    checks.mountTemp()
    checks.installQuota()

    if args.port is None:
        port = "8090"
    else:
        port = args.port

    if args.mysql is None:
        mysql = 'One'
        preFlightsChecks.stdOut("Single MySQL instance version will be installed.")
    else:
        mysql = args.mysql
        preFlightsChecks.stdOut("Dobule MySQL instance version will be installed.")

    checks.checkPythonVersion()
    checks.setup_account_cyberpanel()
    checks.installCyberPanelRepo()

    import installCyberPanel

    if distro == ubuntu:
        checks.setupLSCPDAccount()

    if ent == 0:
        installCyberPanel.Main(cwd, mysql, distro, ent, None, port, args.ftp, args.powerdns, args.publicip, remotemysql,
                               mysqlhost, mysqldb, mysqluser, mysqlpassword, mysqlport)
    else:
        installCyberPanel.Main(cwd, mysql, distro, ent, serial, port, args.ftp, args.powerdns, args.publicip,
                               remotemysql, mysqlhost, mysqldb, mysqluser, mysqlpassword, mysqlport)

    checks.setupPHPAndComposer()
    checks.fix_selinux_issue()
    checks.install_psmisc()
    checks.fixSudoers()

    if args.postfix is None:
        checks.install_postfix_dovecot()
        checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
        checks.setup_postfix_dovecot_config(mysql)
        installCyberPanel.InstallCyberPanel.setupWebmail()
    else:
        if args.postfix == 'ON':
            checks.install_postfix_dovecot()
            checks.setup_email_Passwords(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
            checks.setup_postfix_dovecot_config(mysql)
            installCyberPanel.InstallCyberPanel.setupWebmail()

    checks.install_unzip()
    checks.install_zip()
    checks.install_rsync()

    checks.installFirewalld()
    checks.install_default_keys()

    checks.download_install_CyberPanel(installCyberPanel.InstallCyberPanel.mysqlPassword, mysql)
    checks.download_install_phpmyadmin()
    checks.setupCLI()
    checks.setup_cron()
    checks.installRestic()
    checks.installAcme()

    ## Install and Configure OpenDKIM.

    if args.postfix is None:
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
    checks.installDNS_CyberPanelACMEFile()

    if args.redis is not None:
        checks.installRedis()

    if args.postfix is not None:
        checks.enableDisableEmail(args.postfix.lower())
    else:
        preFlightsChecks.stdOut("Postfix will be installed and enabled.")
        checks.enableDisableEmail('on')

    if args.powerdns is not None:
        checks.enableDisableDNS(args.powerdns.lower())
    else:
        preFlightsChecks.stdOut("PowerDNS will be installed and enabled.")
        checks.enableDisableDNS('on')

    if args.ftp is not None:
        checks.enableDisableFTP(args.ftp.lower(), distro)
    else:
        preFlightsChecks.stdOut("Pure-FTPD will be installed and enabled.")
        checks.enableDisableFTP('on', distro)

    checks.installCLScripts()
    # checks.disablePackegeUpdates()
    checks.fixCyberPanelPermissions()
    configure_jwt_secret()

    # Start services that were enabled but not started during installation
    # These services require database tables that are created by Django migrations
    checks.startDeferredServices()

    logging.InstallLog.writeToFile("CyberPanel installation successfully completed!,80")


if __name__ == "__main__":
    main()
