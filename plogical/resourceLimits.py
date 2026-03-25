#!/usr/local/CyberCP/bin/python
"""
CyberPanel Resource Limits Manager
Handles resource limits using OpenLiteSpeed native cgroups v2 integration
"""

import os
import subprocess
import logging as log
import time
from pathlib import Path

# Django imports
import sys
sys.path.append('/usr/local/CyberCP')
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "CyberCP.settings")
django.setup()

from plogical.CyberCPLogFileWriter import CyberCPLogFileWriter as logging


class ResourceLimitsManager:
    """
    Manages resource limits for websites using OpenLiteSpeed native cgroups v2 API
    This uses the lscgctl command to set per-user limits, which OLS enforces automatically
    """

    # Path to OLS cgroups control tool
    LSCGCTL_PATH = "/usr/local/lsws/lsns/bin/lscgctl"
    LSSETUP_PATH = "/usr/local/lsws/lsns/bin/lssetup"
    OLS_CONF_PATH = "/usr/local/lsws/conf/httpd_config.conf"

    def __init__(self):
        """Initialize the resource limits manager"""
        self._initialized = False

    def _check_rhel8_cgroups_v2(self):
        """
        Check if RHEL 8 family needs manual cgroups v2 enablement

        RHEL 8, AlmaLinux 8, Rocky Linux 8, and CloudLinux 8 have cgroups v2
        backported to kernel 4.18 but it's disabled by default.

        Returns:
            bool: True if cgroups v2 is available or not RHEL 8, False if needs enablement
        """
        try:
            # Check if this is a RHEL 8 family system
            redhat_release_paths = ['/etc/redhat-release', '/etc/system-release']
            is_rhel8 = False
            os_name = "Unknown"

            for release_file in redhat_release_paths:
                if os.path.exists(release_file):
                    try:
                        with open(release_file, 'r') as f:
                            release_content = f.read().lower()
                            os_name = release_content.strip()

                            # Check for RHEL 8 family (RHEL, AlmaLinux, Rocky, CloudLinux, CentOS 8)
                            if ('release 8' in release_content or
                                'release 8.' in release_content):
                                if any(distro in release_content for distro in
                                      ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                                    is_rhel8 = True
                                    break
                    except:
                        pass

            if not is_rhel8:
                # Not RHEL 8 family, no special handling needed
                return True

            # This is RHEL 8 family - check if cgroups v2 is actually enabled
            logging.writeToFile(f"Detected RHEL 8 family system: {os_name}")

            # Check if cgroups v2 is mounted (indicates it's enabled)
            try:
                result = subprocess.run(
                    ['mount'],
                    capture_output=True,
                    text=True,
                    timeout=5
                )

                if 'cgroup2' in result.stdout:
                    logging.writeToFile("cgroups v2 is enabled on RHEL 8 family system")
                    return True
                else:
                    # cgroups v2 is not enabled - provide instructions
                    logging.writeToFile("=" * 80)
                    logging.writeToFile("RHEL 8 FAMILY: cgroups v2 MANUAL ENABLEMENT REQUIRED")
                    logging.writeToFile("=" * 80)
                    logging.writeToFile(f"System: {os_name}")
                    logging.writeToFile(f"Kernel: {os.uname().release}")
                    logging.writeToFile("")
                    logging.writeToFile("RHEL 8, AlmaLinux 8, Rocky Linux 8, and CloudLinux 8 have cgroups v2")
                    logging.writeToFile("backported but disabled by default. To enable, run these commands:")
                    logging.writeToFile("")
                    logging.writeToFile("1. Enable cgroups v2 in boot parameters:")
                    logging.writeToFile("   grubby --update-kernel=ALL --args='systemd.unified_cgroup_hierarchy=1'")
                    logging.writeToFile("")
                    logging.writeToFile("2. Reboot the system:")
                    logging.writeToFile("   reboot")
                    logging.writeToFile("")
                    logging.writeToFile("3. After reboot, verify cgroups v2 is enabled:")
                    logging.writeToFile("   mount | grep cgroup2")
                    logging.writeToFile("")
                    logging.writeToFile("4. Then create websites with resource limits")
                    logging.writeToFile("=" * 80)
                    return False

            except Exception as e:
                logging.writeToFile(f"Error checking cgroups v2 mount status: {str(e)}")
                return False

        except Exception as e:
            logging.writeToFile(f"Error checking RHEL 8 family status: {str(e)}")
            # If we can't detect, assume it's OK and let the normal checks proceed
            return True

    def _ensure_cgroups_enabled(self):
        """
        Ensure OpenLiteSpeed cgroups are enabled
        This performs automatic setup if needed

        Returns:
            bool: True if cgroups are enabled, False otherwise
        """
        if self._initialized:
            return True

        try:
            # Special check for RHEL 8 family systems
            if not self._check_rhel8_cgroups_v2():
                return False

            # Check kernel support first
            if not os.path.exists('/sys/fs/cgroup/cgroup.controllers'):
                logging.writeToFile("cgroups v2 not available on this system (requires kernel 5.2+)")
                logging.writeToFile("For RHEL 8 family, see instructions above to enable cgroups v2")
                return False

            # Check if lscgctl exists and is properly configured
            needs_setup = False

            if not os.path.exists(self.LSCGCTL_PATH):
                logging.writeToFile("lscgctl not found, attempting to run lssetup...")
                needs_setup = True
            else:
                # lscgctl exists, but check if LiteSpeed Containers is actually configured
                # by testing a simple command
                try:
                    test_result = subprocess.run(
                        [self.LSCGCTL_PATH, 'version'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    # Check for the error message that indicates setup is needed
                    if "You must configure LiteSpeed for LiteSpeed Containers" in test_result.stderr:
                        logging.writeToFile("LiteSpeed Containers not configured, attempting to run lssetup...")
                        needs_setup = True
                except Exception as e:
                    logging.writeToFile(f"Error testing lscgctl: {str(e)}, attempting to run lssetup...")
                    needs_setup = True

            # Run lssetup if needed
            if needs_setup:
                if os.path.exists(self.LSSETUP_PATH):
                    logging.writeToFile("Running lssetup to configure LiteSpeed Containers...")
                    result = subprocess.run(
                        [self.LSSETUP_PATH, '-c', '2', '-n', '0', '-s', '/usr/local/lsws'],
                        capture_output=True,
                        text=True,
                        timeout=30
                    )

                    if result.returncode == 0:
                        logging.writeToFile(f"lssetup completed: {result.stdout}")

                        # Verify lssetup actually configured things by testing lscgctl
                        time.sleep(2)  # Give it a moment to initialize
                        verify_result = subprocess.run(
                            [self.LSCGCTL_PATH, 'version'],
                            capture_output=True,
                            text=True,
                            timeout=10
                        )

                        if "You must configure LiteSpeed" in verify_result.stderr:
                            logging.writeToFile("lssetup completed but lscgctl still not configured")
                            logging.writeToFile(f"lscgctl error: {verify_result.stderr}")
                            logging.writeToFile("Trying lssetup with different parameters...")

                            # Try again with more slices
                            result2 = subprocess.run(
                                [self.LSSETUP_PATH, '-c', '10', '-n', '0', '-s', '/usr/local/lsws'],
                                capture_output=True,
                                text=True,
                                timeout=30
                            )
                            logging.writeToFile(f"Second lssetup attempt: {result2.stdout if result2.returncode == 0 else result2.stderr}")

                            # Give it another moment and verify again
                            time.sleep(2)
                            verify_result2 = subprocess.run(
                                [self.LSCGCTL_PATH, 'version'],
                                capture_output=True,
                                text=True,
                                timeout=10
                            )

                            if "You must configure LiteSpeed" in verify_result2.stderr:
                                logging.writeToFile("lscgctl still not working after second attempt")
                                logging.writeToFile("Please manually run: /usr/local/lsws/lsns/bin/lssetup -c 10 -n 0 -s /usr/local/lsws")
                                return False
                            else:
                                logging.writeToFile("lssetup successful on second attempt")
                        else:
                            logging.writeToFile("lssetup verification successful")
                    else:
                        logging.writeToFile(f"lssetup failed: {result.stderr}")
                        return False
                else:
                    logging.writeToFile(f"lssetup not found at {self.LSSETUP_PATH}")
                    return False

            # Check if cgroups are enabled in OLS config
            if not self._check_ols_cgroups_enabled():
                logging.writeToFile("Enabling cgroups in OpenLiteSpeed configuration...")
                if not self._enable_ols_cgroups():
                    return False

            self._initialized = True
            logging.writeToFile("OpenLiteSpeed cgroups support ready")
            return True

        except Exception as e:
            logging.writeToFile(f"Error ensuring cgroups enabled: {str(e)}")
            return False

    def _check_ols_cgroups_enabled(self):
        """
        Check if cgroups are enabled in OpenLiteSpeed config

        Returns:
            bool: True if enabled, False otherwise
        """
        try:
            if not os.path.exists(self.OLS_CONF_PATH):
                logging.writeToFile(f"OLS config not found at {self.OLS_CONF_PATH}")
                return False

            with open(self.OLS_CONF_PATH, 'r') as f:
                config = f.read()

            # Look for CGIRLimit section and check cgroups value
            # Pattern: cgroups followed by whitespace and value
            import re

            # Find CGIRLimit section
            cgirlimit_match = re.search(r'CGIRLimit\s*\{([^}]+)\}', config, re.DOTALL)
            if not cgirlimit_match:
                logging.writeToFile("CGIRLimit section not found in OLS config")
                return False

            cgirlimit_section = cgirlimit_match.group(1)

            # Check for cgroups setting
            cgroups_match = re.search(r'cgroups\s+(\d+)', cgirlimit_section)
            if cgroups_match:
                value = int(cgroups_match.group(1))
                # 1 = On, 0 = Off, 2 = Disabled
                if value == 1:
                    logging.writeToFile("cgroups already enabled in OLS config")
                    return True
                else:
                    logging.writeToFile(f"cgroups is set to {value} (need 1 for enabled)")
                    return False
            else:
                logging.writeToFile("cgroups setting not found in CGIRLimit section")
                return False

        except Exception as e:
            logging.writeToFile(f"Error checking OLS cgroups config: {str(e)}")
            return False

    def _enable_ols_cgroups(self):
        """
        Enable cgroups in OpenLiteSpeed configuration

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if not os.path.exists(self.OLS_CONF_PATH):
                return False

            # Read the config file
            with open(self.OLS_CONF_PATH, 'r') as f:
                config = f.read()

            import re

            # Find CGIRLimit section
            cgirlimit_match = re.search(r'(CGIRLimit\s*\{[^}]+\})', config, re.DOTALL)
            if not cgirlimit_match:
                logging.writeToFile("CGIRLimit section not found, cannot enable cgroups")
                return False

            old_section = cgirlimit_match.group(1)

            # Check if cgroups line exists
            if re.search(r'cgroups\s+\d+', old_section):
                # Replace existing cgroups value with 1
                new_section = re.sub(r'cgroups\s+\d+', 'cgroups                 1', old_section)
            else:
                # Add cgroups line before the closing brace
                new_section = old_section.replace('}', '  cgroups                 1\n}')

            # Replace in config
            new_config = config.replace(old_section, new_section)

            # Backup original config
            backup_path = self.OLS_CONF_PATH + '.backup'
            with open(backup_path, 'w') as f:
                f.write(config)

            # Write new config
            with open(self.OLS_CONF_PATH, 'w') as f:
                f.write(new_config)

            logging.writeToFile("Enabled cgroups in OLS config, restarting OpenLiteSpeed...")

            # Graceful restart of OLS
            result = subprocess.run(
                ['/usr/local/lsws/bin/lswsctrl', 'restart'],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logging.writeToFile("OpenLiteSpeed restarted successfully")
                return True
            else:
                logging.writeToFile(f"Failed to restart OpenLiteSpeed: {result.stderr}")
                return False

        except Exception as e:
            logging.writeToFile(f"Error enabling OLS cgroups: {str(e)}")
            return False

    def set_user_limits(self, username, package):
        """
        Set resource limits for a Linux user using OpenLiteSpeed lscgctl

        Args:
            username (str): Linux username (e.g., website owner)
            package (Package): Package model instance with resource limits

        Returns:
            bool: True if successful, False otherwise
        """
        # Skip if limits not enforced
        if not package.enforceDiskLimits:
            logging.writeToFile(f"Resource limits not enforced for {username} (enforceDiskLimits=0)")
            return True

        # Ensure cgroups are enabled (auto-setup if needed)
        if not self._ensure_cgroups_enabled():
            logging.writeToFile(f"cgroups not available, skipping resource limits for {username}")
            return False

        try:
            # Convert package limits to lscgctl format
            # CPU: convert cores to percentage (1 core = 100%, 2 cores = 200%, etc.)
            cpu_percent = package.cpuCores * 100

            # Memory: convert MB to format with M suffix
            memory_limit = f"{package.memoryLimitMB}M"

            # Tasks: use procHardLimit as max tasks
            max_tasks = package.procHardLimit

            # I/O: convert MB/s to bytes/s (lscgctl expects bytes/sec)
            io_limit_bytes = package.ioLimitMBPS * 1024 * 1024

            # Build lscgctl command
            # Format: lscgctl set username --cpu 100 --mem 1024M --io 10485760 --tasks 500
            cmd = [
                self.LSCGCTL_PATH,
                'set',
                username,
                '--cpu', str(cpu_percent),
                '--mem', memory_limit,
                '--io', str(io_limit_bytes),
                '--tasks', str(max_tasks)
            ]

            # Note: I/O limits are configured but may not be enforced at kernel level
            # without systemd io controller delegation to user slices

            logging.writeToFile(f"Setting limits for user {username}: CPU={cpu_percent}%, MEM={memory_limit}, I/O={package.ioLimitMBPS}MB/s, TASKS={max_tasks}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logging.writeToFile(f"Successfully set resource limits for {username}")
                return True
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                logging.writeToFile(f"Failed to set limits for {username}: {error_msg}")
                return False

        except subprocess.TimeoutExpired:
            logging.writeToFile(f"Timeout setting resource limits for {username}")
            return False
        except Exception as e:
            logging.writeToFile(f"Error setting resource limits for {username}: {str(e)}")
            return False

    def remove_user_limits(self, username):
        """
        Remove resource limits for a Linux user

        Args:
            username (str): Linux username

        Returns:
            bool: True if successful, False otherwise
        """
        if not os.path.exists(self.LSCGCTL_PATH):
            logging.writeToFile(f"lscgctl not available, skipping limit removal for {username}")
            return False

        try:
            # Use lscgctl to remove limits
            # Format: lscgctl remove username
            cmd = [self.LSCGCTL_PATH, 'remove', username]

            logging.writeToFile(f"Removing resource limits for user {username}")

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                logging.writeToFile(f"Successfully removed resource limits for {username}")
                return True
            else:
                error_msg = result.stderr if result.stderr else result.stdout
                # It's not critical if removal fails (user may not have had limits)
                logging.writeToFile(f"Note: Could not remove limits for {username}: {error_msg}")
                return True

        except subprocess.TimeoutExpired:
            logging.writeToFile(f"Timeout removing resource limits for {username}")
            return False
        except Exception as e:
            logging.writeToFile(f"Error removing resource limits for {username}: {str(e)}")
            return False

    def get_user_limits(self, username):
        """
        Get current resource limits for a Linux user

        Args:
            username (str): Linux username

        Returns:
            dict: Current limits or None
        """
        if not os.path.exists(self.LSCGCTL_PATH):
            return None

        try:
            # Use lscgctl to get limits
            # Format: lscgctl get username
            cmd = [self.LSCGCTL_PATH, 'get', username]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                # Parse the output (format may vary)
                return {'output': result.stdout.strip()}
            else:
                return None

        except Exception as e:
            logging.writeToFile(f"Error getting resource limits for {username}: {str(e)}")
            return None

    def set_inode_limit(self, domain, username, inode_limit):
        """
        Set inode (file count) limit for a website using filesystem quotas

        Args:
            domain (str): Website domain name
            username (str): System username for the website
            inode_limit (int): Maximum number of files/directories

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if quota tools are available
            result = subprocess.run(
                ['which', 'setquota'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                logging.writeToFile("setquota command not found, skipping inode limit")
                return False

            # Set inode quota using setquota
            # Format: setquota -u username 0 0 soft_inode hard_inode /
            result = subprocess.run(
                ['setquota', '-u', username, '0', '0',
                 str(inode_limit), str(inode_limit), '/'],
                check=True,
                capture_output=True,
                timeout=10
            )
            logging.writeToFile(f"Set inode limit for {domain} ({username}): {inode_limit}")
            return True
        except subprocess.TimeoutExpired:
            logging.writeToFile(f"Timeout setting inode limit for {domain}")
            return False
        except subprocess.CalledProcessError as e:
            logging.writeToFile(f"Failed to set inode limit: {e.stderr.decode() if e.stderr else str(e)}")
            return False
        except Exception as e:
            logging.writeToFile(f"Failed to set inode limit: {str(e)}")
            return False


    def check_cgroup_support(self):
        """
        Check if OpenLiteSpeed cgroups v2 support is available

        Returns:
            dict: Support status for various features
        """
        support = {
            'cgroups_v2': False,
            'lscgctl_available': False,
            'memory_controller': False,
            'cpu_controller': False,
            'io_controller': False,
            'quota_tools': False,
            'rhel8_family': False,
            'rhel8_needs_enablement': False,
            'os_name': 'Unknown'
        }

        try:
            # Check for RHEL 8 family
            redhat_release_paths = ['/etc/redhat-release', '/etc/system-release']
            for release_file in redhat_release_paths:
                if os.path.exists(release_file):
                    try:
                        with open(release_file, 'r') as f:
                            release_content = f.read()
                            support['os_name'] = release_content.strip()

                            # Check for RHEL 8 family
                            if ('release 8' in release_content.lower() or
                                'release 8.' in release_content.lower()):
                                if any(distro in release_content.lower() for distro in
                                      ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                                    support['rhel8_family'] = True

                                    # Check if cgroups v2 is actually mounted
                                    result = subprocess.run(['mount'], capture_output=True,
                                                          text=True, timeout=5)
                                    if 'cgroup2' not in result.stdout:
                                        support['rhel8_needs_enablement'] = True
                                    break
                    except:
                        pass

            # Check cgroups v2
            if os.path.exists('/sys/fs/cgroup/cgroup.controllers'):
                support['cgroups_v2'] = True

                # Check controllers
                with open('/sys/fs/cgroup/cgroup.controllers', 'r') as f:
                    controllers = f.read().strip().split()
                    support['memory_controller'] = 'memory' in controllers
                    support['cpu_controller'] = 'cpu' in controllers
                    support['io_controller'] = 'io' in controllers

            # Check lscgctl tool
            support['lscgctl_available'] = os.path.exists(self.LSCGCTL_PATH)

            # Check quota tools
            result = subprocess.run(['which', 'setquota'], capture_output=True, timeout=5)
            support['quota_tools'] = result.returncode == 0

        except Exception as e:
            logging.writeToFile(f"Error checking cgroup support: {str(e)}")

        return support


# Singleton instance
resource_manager = ResourceLimitsManager()
