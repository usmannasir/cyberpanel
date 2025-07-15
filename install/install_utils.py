#!/usr/bin/env python
"""
Common utility functions for CyberPanel installation scripts.
This module contains shared functions used by both install.py and installCyberPanel.py
"""

import os
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


def get_distro():
    """
    Detect Linux distribution
    
    Returns: Distribution constant (ubuntu, centos, cent8, or openeuler)
    """
    distro = -1
    distro_file = ""
    if exists("/etc/lsb-release"):
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
        ## if almalinux 9 then pretty much same as cent8
        if data.find('AlmaLinux release 8') > -1 or data.find('AlmaLinux release 9') > -1:
            return cent8
        if data.find('Rocky Linux release 8') > -1 or data.find('Rocky Linux 8') > -1 or data.find('rocky:8') > -1:
            return cent8
        if data.find('CloudLinux 8') or data.find('cloudlinux 8'):
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
    if distro == ubuntu:
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
    if distro == ubuntu:
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
    if distro == ubuntu and res != 0:
        return True
    elif distro == centos and res != 0:
        return True
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
    finalMessage = 'Running: %s' % (message)
    stdOut(finalMessage, log)
    count = 0
    while True:
        if shell == False:
            res = subprocess.call(shlex.split(command))
        else:
            res = subprocess.call(command, shell=True)

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
