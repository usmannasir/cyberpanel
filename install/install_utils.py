#!/usr/bin/env python
"""
Common utility functions for CyberPanel installation scripts.
This module contains shared functions used by both install.py and installCyberPanel.py
"""

import os
import glob
import sys
import time
import logging
import subprocess
import shlex
import secrets
import string
from os.path import exists


def FetchCloudLinuxAlmaVersionVersion():
    """
    Detect CloudLinux or AlmaLinux version by parsing /etc/os-release
    Returns: version string or -1 if not found
    """
    if os.path.exists('/etc/os-release'):
        data = open('/etc/os-release', 'r').read()
        if (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('8.9') > -1 or data.find('Anatoly Levchenko') > -1 or data.find('VERSION="8.') > -1):
            return 'cl-89'
        elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('8.8') > -1 or data.find('Anatoly Filipchenko') > -1):
            return 'cl-88'
        elif (data.find('CloudLinux') > -1 or data.find('cloudlinux') > -1) and (data.find('9.4') > -1 or data.find('VERSION="9.') > -1):
            return 'cl-88'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('8.9') > -1 or data.find('Midnight Oncilla') > -1 or data.find('VERSION="8.') > -1):
            return 'al-88'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('8.7') > -1 or data.find('Stone Smilodon') > -1):
            return 'al-87'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('9.4') > -1 or data.find('9.3') > -1 or data.find('Shamrock Pampas') > -1 or data.find('Seafoam Ocelot') > -1 or data.find('VERSION="9.') > -1):
            return 'al-93'
        elif data.find('CentOS Stream 9') > -1:
            return 'el-9'
        elif data.find('CentOS Linux 9') > -1:
            return 'el-9'
        elif data.find('Rocky Linux 9') > -1:
            return 'el-9'
        elif data.find('Red Hat Enterprise Linux 9') > -1:
            return 'el-9'
        elif (data.find('AlmaLinux') > -1 or data.find('almalinux') > -1) and (data.find('10.0') > -1 or data.find('Purple Lion') > -1 or data.find('VERSION="10.') > -1):
            return 'al-100'
    else:
        return -1


def get_Ubuntu_release(use_print=False, exit_on_error=True):
    """
    Get Ubuntu release version from /etc/lsb-release

    Args:
        use_print: If True, use print() for errors, otherwise use the provided output function
        exit_on_error: If True, exit on error

    Returns: float release number or -1 if not found
    """
    release = -1
    if exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line[:16] == "DISTRIB_RELEASE=":
                    release = float(line[16:])

        if release == -1:
            error_msg = "Can't find distro release name in " + distro_file + " - fatal error"
            if use_print:
                print(error_msg)
            else:
                # This will be overridden by the calling module
                return -1

    else:
        error_msg = "Can't find linux release file - fatal error"
        if hasattr(logging, 'InstallLog'):
            logging.InstallLog.writeToFile(error_msg)
        if use_print:
            print(error_msg)
        if exit_on_error:
            os._exit(os.EX_UNAVAILABLE)

    return release


def get_Debian_version():
    """
    Get Debian version from /etc/debian_version

    Returns: float version number or -1 if not found
    """
    if exists("/etc/debian_version"):
        try:
            with open("/etc/debian_version", 'r') as f:
                version_str = f.read().strip()
                # Extract numeric version (e.g., "13.8" from "13.8" or "13" from "13/sid")
                if '/' in version_str:
                    version_str = version_str.split('/')[0]
                try:
                    return float(version_str)
                except ValueError:
                    # Handle non-numeric versions like "bookworm/sid"
                    if 'bookworm' in version_str.lower():
                        return 12.0
                    elif 'trixie' in version_str.lower():
                        return 13.0
                    elif 'bullseye' in version_str.lower():
                        return 11.0
                    else:
                        return -1
        except Exception:
            return -1
    return -1


def is_debian():
    """
    Check if the system is Debian (not Ubuntu)

    Returns: bool indicating if it's Debian
    """
    if exists("/etc/debian_version") and not exists("/etc/lsb-release"):
        return True
    return False


def get_debian_mariadb_packages():
    """
    Get appropriate MariaDB packages for Debian based on version

    Returns: dict with package mappings
    """
    debian_version = get_Debian_version()

    # Package mappings for different Debian versions
    if debian_version >= 13.0:
        # Debian 13 (Trixie) uses newer package names
        return {
            'libmariadbclient-dev': 'libmariadb-dev-compat libmariadb-dev',
            'python-mysqldb': 'python3-mysqldb',
            'python-dev': 'python3-dev',
            'python-pip': 'python3-pip',
            'python-setuptools': 'python3-setuptools',
            'python-minimal': '',  # Not needed in newer versions
            'python-gpg': 'python3-gpg',
            'python': 'python3',
            'dovecot-pigeonhole': 'dovecot-sieve',
            'pdns': 'pdns-server',
            'pdns-backend-mysql': 'pdns-backend-mysql',
            'firewalld': 'firewalld'
        }
    elif debian_version >= 12.0:
        # Debian 12 (Bookworm)
        return {
            'libmariadbclient-dev': 'libmariadb-dev',
            'python-mysqldb': 'python3-mysqldb',
            'python-dev': 'python3-dev',
            'python-pip': 'python3-pip',
            'python-setuptools': 'python3-setuptools',
            'python-minimal': '',
            'python-gpg': 'python3-gpg',
            'python': 'python3',
            'dovecot-pigeonhole': 'dovecot-sieve',
            'pdns': 'pdns-server',
            'pdns-backend-mysql': 'pdns-backend-mysql',
            'firewalld': 'firewalld'
        }
    else:
        # Older Debian versions (11 and below)
        return {
            'libmariadbclient-dev': 'libmariadbclient-dev',
            'python-mysqldb': 'python-mysqldb',
            'python-dev': 'python-dev',
            'python-pip': 'python-pip',
            'python-setuptools': 'python-setuptools',
            'python-minimal': 'python-minimal',
            'python-gpg': 'python-gpg',
            'python': 'python'
        }


# ANSI color codes
class Colors:
    HEADER = '\033[95m'      # Purple
    INFO = '\033[94m'        # Blue
    SUCCESS = '\033[92m'     # Green
    WARNING = '\033[93m'     # Yellow
    ERROR = '\033[91m'       # Red
    ENDC = '\033[0m'         # Reset
    BOLD = '\033[1m'         # Bold
    UNDERLINE = '\033[4m'    # Underline


def get_message_color(message):
    """
    Determine the appropriate color based on message content
    
    Args:
        message: The message to analyze
        
    Returns:
        str: ANSI color code
    """
    message_lower = message.lower()
    
    # Error messages
    if any(word in message_lower for word in ['error', 'failed', 'fatal', 'critical', 'unable']):
        return Colors.ERROR
    
    # Warning messages
    elif any(word in message_lower for word in ['warning', 'warn', 'caution', 'alert']):
        return Colors.WARNING
    
    # Success messages
    elif any(word in message_lower for word in ['success', 'completed', 'installed', 'finished', 'done', 'enabled']):
        return Colors.SUCCESS
    
    # Running/Processing messages
    elif any(word in message_lower for word in ['running', 'installing', 'downloading', 'processing', 'starting', 'configuring']):
        return Colors.INFO
    
    # Default color
    else:
        return Colors.HEADER


def stdOut(message, log=0, do_exit=0, code=os.EX_OK):
    """
    Standard output function with timestamps, coloring, and logging
    
    Args:
        message: Message to output
        log: If 1, write to log file
        do_exit: If 1, exit after outputting
        code: Exit code to use if do_exit is 1
    """
    # Get appropriate color for the message
    color = get_message_color(message)
    
    # Check if terminal supports color
    try:
        # Check if output is to a terminal
        if not sys.stdout.isatty():
            color = ''
            color_end = ''
        else:
            color_end = Colors.ENDC
    except:
        color = ''
        color_end = ''
    
    # Format timestamps
    timestamp = time.strftime("%m.%d.%Y_%H-%M-%S")
    
    print("\n\n")
    print(f"{color}[{timestamp}] #########################################################################{color_end}\n")
    print(f"{color}[{timestamp}] {message}{color_end}\n")
    print(f"{color}[{timestamp}] #########################################################################{color_end}\n")

    if log and hasattr(logging, 'InstallLog'):
        logging.InstallLog.writeToFile(message)
    if do_exit:
        if hasattr(logging, 'InstallLog'):
            logging.InstallLog.writeToFile(message)
        sys.exit(code)


def format_restart_litespeed_command(server_root_path):
    """
    Format the LiteSpeed restart command
    
    Args:
        server_root_path: Root path of the server installation
    
    Returns: Formatted command string
    """
    return '%sbin/lswsctrl restart' % (server_root_path)


# Distribution constants
ubuntu = 0
centos = 1
cent8 = 2
openeuler = 3
debian12 = 4


def get_distro():
    """
    Detect Linux distribution

    Returns: Distribution constant (ubuntu, centos, cent8, openeuler, or debian12)
    """
    distro = -1
    distro_file = ""

    # Check for Debian first
    if exists("/etc/debian_version"):
        # Check if it's actually Ubuntu (which also has debian_version)
        if exists("/etc/lsb-release"):
            distro_file = "/etc/lsb-release"
            with open(distro_file) as f:
                for line in f:
                    if line == "DISTRIB_ID=Ubuntu\n":
                        distro = ubuntu
                        break
        else:
            # Pure Debian system - check version
            distro_file = "/etc/debian_version"
            with open(distro_file) as f:
                debian_version = f.read().strip()
                # Check specific Debian versions
                if debian_version.startswith('bookworm') or '12' in debian_version:
                    distro = debian12
                else:
                    # For other Debian versions, treat same as Ubuntu for compatibility
                    distro = ubuntu

    elif exists("/etc/lsb-release"):
        distro_file = "/etc/lsb-release"
        with open(distro_file) as f:
            for line in f:
                if line == "DISTRIB_ID=Ubuntu\n":
                    distro = ubuntu

    elif exists("/etc/redhat-release"):
        distro_file = "/etc/redhat-release"
        distro = centos

        data = open('/etc/redhat-release', 'r').read()

        if data.find('CentOS Linux release 8') > -1:
            return cent8
        if data.find('CentOS Linux release 9') > -1 or data.find('CentOS Stream 9') > -1:
            return cent8
        if data.find('Rocky Linux release 9') > -1 or data.find('Rocky Linux 9') > -1:
            return cent8
        if data.find('Red Hat Enterprise Linux 8') > -1 or data.find('Red Hat Enterprise Linux 9') > -1:
            return cent8
        ## if almalinux 9 or 10 then pretty much same as cent8
        if data.find('AlmaLinux release 8') > -1 or data.find('AlmaLinux release 9') > -1 or data.find('AlmaLinux release 10') > -1:
            return cent8
        if data.find('Rocky Linux release 8') > -1 or data.find('Rocky Linux 8') > -1 or data.find('rocky:8') > -1:
            return cent8
        if data.find('CloudLinux 8') or data.find('cloudlinux 8') or data.find('CloudLinux 9') or data.find('cloudlinux 9'):
            return cent8

    else:
        if exists("/etc/openEuler-release"):
            distro_file = "/etc/openEuler-release"
            distro = openeuler

        else:
            if hasattr(logging, 'InstallLog'):
                logging.InstallLog.writeToFile("Can't find linux release file - fatal error")
            print("Can't find linux release file - fatal error")
            os._exit(os.EX_UNAVAILABLE)

    if distro == -1:
        error_msg = "Can't find distro name in " + distro_file + " - fatal error"
        if hasattr(logging, 'InstallLog'):
            logging.InstallLog.writeToFile(error_msg)
        print(error_msg)
        os._exit(os.EX_UNAVAILABLE)

    return distro


def map_debian_packages(package_string):
    """
    Map package names for Debian compatibility

    Args:
        package_string: Space-separated package names

    Returns:
        str: Mapped package names for Debian
    """
    if not is_debian():
        return package_string

    package_map = get_debian_mariadb_packages()
    packages = package_string.split()
    mapped_packages = []

    for package in packages:
        if package in package_map:
            replacement = package_map[package]
            if replacement:  # Skip empty replacements
                mapped_packages.extend(replacement.split())
        else:
            mapped_packages.append(package)

    return ' '.join(mapped_packages)


def get_package_install_command(distro, package_name, options=""):
    """
    Get the package installation command for a specific distribution

    Args:
        distro: Distribution constant
        package_name: Name of the package to install
        options: Additional options for the package manager

    Returns:
        tuple: (command, shell) where shell indicates if shell=True is needed
    """
    if distro == ubuntu or distro == debian12:
        # Map packages for Debian compatibility
        package_name = map_debian_packages(package_name)
        command = f"DEBIAN_FRONTEND=noninteractive apt-get -y install {package_name} {options}"
        shell = True
    elif distro == centos:
        command = f"yum install -y {package_name} {options}"
        shell = False
    else:  # cent8, openeuler
        command = f"dnf install -y {package_name} {options}"
        shell = False

    return command, shell


def get_package_remove_command(distro, package_name):
    """
    Get the package removal command for a specific distribution
    
    Args:
        distro: Distribution constant
        package_name: Name of the package to remove
    
    Returns:
        tuple: (command, shell) where shell indicates if shell=True is needed
    """
    if distro == ubuntu or distro == debian12:
        command = f"DEBIAN_FRONTEND=noninteractive apt-get -y remove {package_name}"
        shell = True
    elif distro == centos:
        command = f"yum remove -y {package_name}"
        shell = False
    else:  # cent8, openeuler
        command = f"dnf remove -y {package_name}"
        shell = False
    
    return command, shell


def resFailed(distro, res):
    """
    Check if a command execution result indicates failure
    
    Args:
        distro: Distribution constant
        res: Return code from subprocess
    
    Returns:
        bool: True if failed, False if successful
    """
    if (distro == ubuntu or distro == debian12) and res != 0:
        return True
    elif distro == centos and res != 0:
        return True
    return False


def wait_for_apt_lock():
    """
    Wait for apt lock to be released and clean up stuck processes if needed
    """
    import time
    import glob

    lock_files = [
        '/var/lib/dpkg/lock-frontend',
        '/var/lib/dpkg/lock',
        '/var/cache/apt/archives/lock'
    ]

    max_wait = 300  # Wait up to 5 minutes
    wait_time = 0

    while wait_time < max_wait:
        locks_exist = any(os.path.exists(lock) for lock in lock_files)

        if not locks_exist:
            return True

        # Check if any apt processes are actually running
        try:
            result = subprocess.run(['pgrep', '-f', 'apt'], capture_output=True)
            if result.returncode != 0:
                # No apt processes running but locks exist - remove them
                stdOut("No apt processes running, removing stale locks...")
                for lock_file in lock_files:
                    if os.path.exists(lock_file):
                        try:
                            os.remove(lock_file)
                            stdOut(f"Removed stale lock: {lock_file}")
                        except:
                            pass
                return True
        except:
            pass

        stdOut(f"Waiting for apt lock to be released... ({wait_time}s/{max_wait}s)")
        time.sleep(10)
        wait_time += 10

    # If we get here, we've waited too long - try to clean up
    stdOut("Timeout waiting for apt lock, attempting cleanup...")
    try:
        # Kill any stuck apt processes
        subprocess.run(['killall', '-9', 'apt-get'], capture_output=True)
        subprocess.run(['killall', '-9', 'apt'], capture_output=True)

        # Remove locks
        for lock_file in lock_files:
            if os.path.exists(lock_file):
                try:
                    os.remove(lock_file)
                except:
                    pass

        # Reconfigure dpkg
        subprocess.run(['dpkg', '--configure', '-a'], capture_output=True)
        return True
    except:
        return False


def call(command, distro, bracket, message, log=0, do_exit=0, code=os.EX_OK, shell=False):
    """
    Execute a shell command with retry logic and error handling
    
    Args:
        command: Command to execute
        distro: Distribution constant
        bracket: Not used (kept for compatibility)
        message: Description of the command for logging
        log: If 1, write to log file
        do_exit: If 1, exit on failure
        code: Exit code to use if do_exit is 1
        shell: If True, execute through shell
    
    Returns:
        bool: True if successful, False if failed
    """
    # CRITICAL (first): Replace missing CyberPanel Python so old/cached installers never hit FileNotFoundError
    if isinstance(command, str):
        bad_path = '/usr/local/CyberPanel/bin/python'
        if bad_path in command and not os.path.isfile(bad_path):
            fallback = '/usr/bin/python3'
            if not os.path.isfile(fallback):
                fallback = '/usr/local/bin/python3'
            if os.path.isfile(fallback):
                command = command.replace(bad_path, fallback)
                shell = True
        # Use /tmp/composer.sh when command references relative composer.sh (avoids "chmod: cannot access 'composer.sh'")
        # Only replace local file refs, not URLs (e.g. https://cyberpanel.sh/composer.sh)
        if not os.path.isfile(os.path.join(os.getcwd(), 'composer.sh')):
            if './composer.sh' in command:
                command = command.replace('./composer.sh', '/tmp/composer.sh')
                shell = True
            elif ' composer.sh' in command and 'http' not in command.split('composer.sh')[0][-20:]:
                command = command.replace(' composer.sh', ' /tmp/composer.sh')
                shell = True

    # Check for apt lock before running apt commands
    if 'apt-get' in command or 'apt ' in command:
        if not wait_for_apt_lock():
            stdOut("Failed to acquire apt lock after waiting")
            if do_exit:
                os._exit(code)
            return False

    # CRITICAL: Use shell=True for commands with shell metacharacters
    # Avoids "No matching repo to modify: 2>/dev/null, true, ||" and "Could not resolve host: |" when shlex.split splits them
    if not shell and (any(x in command for x in (' || ', ' 2>/dev', ' 2>', ' | ', '; true', '|| true')) or '|' in command):
        shell = True

    # CRITICAL: For mysql/mariadb commands, always use shell=True and full binary path
    # This fixes "No such file or directory: 'mysql'" when run via shlex.split
    if not shell and ('mysql' in command or 'mariadb' in command):
        import re
        mysql_bin = '/usr/bin/mariadb' if os.path.exists('/usr/bin/mariadb') else '/usr/bin/mysql'
        if not os.path.exists(mysql_bin):
            mysql_bin = '/usr/bin/mysql'
        # Replace only leading "mysql" or "mariadb" (executable), not "mysql" in SQL like "use mysql;"
        if re.match(r'^\s*(sudo\s+)?(mysql|mariadb)\s', command):
            command = re.sub(r'^(\s*)(?:sudo\s+)?(mysql|mariadb)(\s)', r'\g<1>' + mysql_bin + r'\g<3>', command, count=1)
        shell = True

    finalMessage = 'Running: %s' % (message)
    stdOut(finalMessage, log)
    count = 0
    while True:
        try:
            if shell:
                res = subprocess.call(command, shell=True)
            else:
                res = subprocess.call(shlex.split(command))
        except FileNotFoundError as e:
            # Old installer may pass /usr/local/CyberPanel/bin/python; retry with system python once
            if isinstance(command, str) and '/usr/local/CyberPanel/bin/python' in command:
                fallback = '/usr/bin/python3'
                if not os.path.isfile(fallback):
                    fallback = '/usr/local/bin/python3'
                if os.path.isfile(fallback):
                    command = command.replace('/usr/local/CyberPanel/bin/python', fallback)
                    shell = True
                    stdOut("Retrying with %s (CyberPanel python missing)" % fallback, log)
                    res = subprocess.call(command, shell=True)
                else:
                    raise
            else:
                raise

        if resFailed(distro, res):
            count = count + 1
            finalMessage = 'Running %s failed. Running again, try number %s' % (message, str(count))
            stdOut(finalMessage)
            if count == 3:
                fatal_message = ''
                if do_exit:
                    fatal_message = '.  Fatal error, see /var/log/installLogs.txt for full details'

                stdOut("[ERROR] We are not able to run " + message + ' return code: ' + str(res) +
                       fatal_message + ".", 1, do_exit, code)
                return False
        else:
            stdOut('Successfully ran: %s.' % (message), log)
            break

    return True


# Character sets for password generation (kept for backward compatibility)
char_set = {
    'small': 'abcdefghijklmnopqrstuvwxyz',
    'nums': '0123456789',
    'big': 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
}


def generate_pass(length=14):
    """
    Generate a cryptographically secure random password
    
    Args:
        length: Length of the password to generate (default 14)
    
    Returns:
        str: Random password containing uppercase, lowercase letters and digits
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def generate_random_string(length=32, include_special=False):
    """
    Generate a random string with optional special characters
    
    Args:
        length: Length of the string to generate
        include_special: If True, include special characters
    
    Returns:
        str: Random string
    """
    alphabet = string.ascii_letters + string.digits
    if include_special:
        alphabet += string.punctuation
    return ''.join(secrets.choice(alphabet) for _ in range(length))



def strip_mariadb_maxscale_apt_repos():
    """
    MariaDB mariadb_repo_setup adds MaxScale apt repo; Ubuntu noble has no Release (GH usmannasir/cyberpanel#1740).
    """
    slist = '/etc/apt/sources.list.d'
    try:
        if not os.path.isdir(slist):
            return
        for pattern in (
            'mariadb-maxscale*.list', 'mariadb-maxscale*.sources',
            '*maxscale*.list', '*maxscale*.sources',
        ):
            for fp in glob.glob(os.path.join(slist, pattern)):
                try:
                    os.remove(fp)
                except OSError:
                    pass
        for fp in glob.glob(os.path.join(slist, 'mariadb*.list')):
            try:
                with open(fp, 'r', encoding='utf-8', errors='replace') as handle:
                    lines = handle.readlines()
                new_lines = [
                    ln for ln in lines
                    if 'maxscale' not in ln.lower()
                    and 'dlm.mariadb.com/repo/maxscale' not in ln
                ]
                if new_lines != lines:
                    with open(fp, 'w', encoding='utf-8') as handle:
                        handle.writelines(new_lines)
            except OSError:
                pass
        for fp in glob.glob(os.path.join(slist, 'mariadb*.sources')):
            try:
                with open(fp, 'r', encoding='utf-8', errors='replace') as handle:
                    content = handle.read()
                if 'maxscale' not in content.lower() and 'dlm.mariadb.com/repo/maxscale' not in content:
                    continue
                blocks = content.split('\n\n')
                kept = []
                for block in blocks:
                    bl = block.lower()
                    if 'maxscale' in bl or 'dlm.mariadb.com/repo/maxscale' in block:
                        continue
                    kept.append(block)
                new_content = '\n\n'.join(kept)
                if new_content.strip() != content.strip():
                    with open(fp, 'w', encoding='utf-8') as handle:
                        handle.write(new_content)
            except OSError:
                pass
    except Exception:
        pass


def writeToFile(message):
    """
    Write a message to the installation log file
    
    Args:
        message: Message to write to the log file
    """
    # Import logging module if available
    try:
        import installLog as logging
        if hasattr(logging, 'InstallLog') and hasattr(logging.InstallLog, 'writeToFile'):
            logging.InstallLog.writeToFile(message)
    except ImportError:
        # If installLog module is not available, just print the message
        print(f"[LOG] {message}")
