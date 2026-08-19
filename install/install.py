import sys
import os
import re

# Ensure install dir is on path for ols_binaries_config
_install_dir = os.path.dirname(os.path.abspath(__file__))
if _install_dir not in sys.path:
    sys.path.insert(0, _install_dir)
import ols_binaries_config
import ols_version_policy

import subprocess
import shutil
import installLog as logging
import argparse
import errno
import shlex
from firewallUtilities import FirewallUtilities
import time
import string
import random
import socket
from os.path import *
from stat import *
import stat
import secrets
import install_utils

VERSION = '2.5.5'
BUILD = 'dev'

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
debian12 = install_utils.debian12
cent9 = 4  # Not in install_utils yet
CloudLinux8 = 0  # Not in install_utils yet

# Using shared function from install_utils
FetchCloudLinuxAlmaVersionVersion = install_utils.FetchCloudLinuxAlmaVersionVersion


# Using shared function from install_utils
get_distro = install_utils.get_distro


def _normalize_mariadb_version(ver):
    """Accept 10.3-10.11, 11.0-11.8, 12.0-12.x; return major.minor for repo or 11.8 if invalid."""
    if not ver or not isinstance(ver, str):
        return '11.8'
    v = ver.strip()
    m = re.match(r'^(\d+)\.(\d+)(?:\.\d+)*$', v)
    if not m:
        return '11.8'
    major, minor = int(m.group(1)), int(m.group(2))
    if major == 10 and 3 <= minor <= 11:
        return '10.%d' % minor
    if major == 11 and 0 <= minor <= 8:
        return '11.%d' % minor
    if major == 12 and 0 <= minor <= 99:
        return '12.%d' % minor
    return '11.8'


def cybercp_venv_python_executable():
    """
    Interpreter for creating /usr/local/CyberCP venv.
    Prefer CYBERCP_VENV_PYTHON from the shell installer, then Python 3.11+ on disk, else sys.executable.
    """
    env_p = (os.environ.get('CYBERCP_VENV_PYTHON') or '').strip()
    if env_p and os.path.isfile(env_p) and os.access(env_p, os.X_OK):
        return env_p
    for cand in (
            '/usr/bin/python3.11',
            '/usr/local/bin/python3.11',
            '/usr/bin/python3.12',
            '/usr/bin/python3.13',
            '/usr/bin/python3.10',
    ):
        if not (os.path.isfile(cand) and os.access(cand, os.X_OK)):
            continue
        try:
            r = subprocess.run(
                [cand, '-c', 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)'],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if r.returncode == 0:
                return cand
        except (OSError, subprocess.SubprocessError):
            continue
    return sys.executable or shutil.which('python3') or 'python3'


def setup_webmail_master_user():
    """
    Configure Dovecot master user and /etc/cyberpanel/webmail.conf for SSO.
    Uses webmail_master_setup (no MySQLdb) so install can finish even if mysqlclient
    is missing from the bootstrap interpreter (common on WSL Ubuntu).
    """
    try:
        import install_utils
        install_utils.ensure_mysqlclient_for_python(sys.executable, log=1)
    except Exception as exc:
        logging.InstallLog.writeToFile(
            '[WARNING] mysqlclient bootstrap check failed (webmail may still run): %s' % exc
        )

    try:
        from webmail_master_setup import configure_webmail_master_user
        return configure_webmail_master_user()
    except ImportError:
        try:
            import installCyberPanel
            return installCyberPanel.InstallCyberPanel.setupWebmail()
        except ImportError as exc:
            logging.InstallLog.writeToFile(
                '[WARNING] webmail setup skipped (MySQLdb/installCyberPanel): %s' % exc
            )
            preFlightsChecks.stdOut(
                'Warning: webmail master user setup skipped (panel install continues).', 1
            )
            return 0


def get_Ubuntu_release():
    release = install_utils.get_Ubuntu_release(use_print=False, exit_on_error=True)
    if release == -1:
        preFlightsChecks.stdOut("Can't find distro release name in /etc/lsb-release - fatal error", 1, 1,
                                os.EX_UNAVAILABLE)
    return release


class preFlightsChecks:
    debug = 1
    cyberPanelMirror = "mirror.cyberpanel.net/pip"
    cdn = 'cyberpanel.sh'
    SnappyVersion = '2.38.2'
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

    def is_debian_family(self):
        """Check if distro is Ubuntu or Debian 12"""
        return self.distro in [ubuntu, debian12]

    def add_litespeed_repo(self):
        """Add LiteSpeed repository (repo.litespeed.sh) for current openlitespeed packages."""
        try:
            self.stdOut("Adding LiteSpeed repository for OpenLiteSpeed (see ols_version_policy.py)...", 1)
            cmd = 'wget -q -O - https://repo.litespeed.sh | bash'
            ret = subprocess.run(cmd, shell=True, timeout=120, capture_output=True, universal_newlines=True)
            if ret.returncode != 0 and ret.stderr:
                self.stdOut(f"LiteSpeed repo script warning: {ret.stderr[:200]}", 1)
            if ret.returncode == 0:
                self.stdOut("LiteSpeed repository added", 1)
                return True
            # Non-fatal: distro openlitespeed may still be used
            self.stdOut("Could not add LiteSpeed repo; using distro package", 1)
            return False
        except Exception as e:
            self.stdOut(f"LiteSpeed repo add failed: {e}", 1)
            return False

    def get_installed_ols_version(self):
        """Return installed OpenLiteSpeed version as (major, minor, patch) or None"""
        return install_utils.get_installed_ols_version()

    def upgrade_openlitespeed_to_latest(self):
        """Try to upgrade OpenLiteSpeed from configured repos; failures are non-fatal."""
        try:
            if self.distro == ubuntu or self.distro == debian12:
                cmd = (
                    'apt-get -y update && DEBIAN_FRONTEND=noninteractive apt-get -y '
                    'install --only-upgrade openlitespeed 2>/dev/null || true'
                )
                subprocess.run(cmd, shell=True, timeout=600, capture_output=True, universal_newlines=True)
            else:
                subprocess.run(
                    'dnf -y upgrade openlitespeed || true',
                    shell=True,
                    timeout=600,
                    capture_output=True,
                    universal_newlines=True,
                )
                subprocess.run(
                    'yum -y upgrade openlitespeed 2>/dev/null || true',
                    shell=True,
                    timeout=600,
                    capture_output=True,
                    universal_newlines=True,
                )
        except Exception:
            pass

    def detect_os_info(self):
        """Detect OS information for all supported platforms"""
        os_info = {
            'name': 'unknown',
            'version': 'unknown',
            'major_version': 0,
            'family': 'unknown'
        }
        
        # Check for Ubuntu
        if os.path.exists('/etc/os-release'):
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                if 'Ubuntu' in content:
                    os_info['family'] = 'ubuntu'
                    os_info['name'] = 'ubuntu'
                    # Extract version
                    for line in content.split('\n'):
                        if line.startswith('VERSION_ID='):
                            version = line.split('=')[1].strip('"')
                            os_info['version'] = version
                            os_info['major_version'] = int(version.split('.')[0])
                            break
                elif 'Debian' in content:
                    os_info['family'] = 'debian'
                    os_info['name'] = 'debian'
                    for line in content.split('\n'):
                        if line.startswith('VERSION_ID='):
                            version = line.split('=')[1].strip('"')
                            os_info['version'] = version
                            os_info['major_version'] = int(version)
                            break
                elif 'AlmaLinux' in content:
                    os_info['family'] = 'rhel'
                    os_info['name'] = 'almalinux'
                    for line in content.split('\n'):
                        if line.startswith('VERSION_ID='):
                            version = line.split('=')[1].strip('"')
                            os_info['version'] = version
                            os_info['major_version'] = int(version.split('.')[0])
                            break
                elif 'Rocky Linux' in content:
                    os_info['family'] = 'rhel'
                    os_info['name'] = 'rocky'
                    for line in content.split('\n'):
                        if line.startswith('VERSION_ID='):
                            version = line.split('=')[1].strip('"')
                            os_info['version'] = version
                            os_info['major_version'] = int(version.split('.')[0])
                            break
                elif 'Red Hat Enterprise Linux' in content:
                    os_info['family'] = 'rhel'
                    os_info['name'] = 'rhel'
                    for line in content.split('\n'):
                        if line.startswith('VERSION_ID='):
                            version = line.split('=')[1].strip('"')
                            os_info['version'] = version
                            os_info['major_version'] = int(version.split('.')[0])
                            break
                elif 'CloudLinux' in content:
                    os_info['family'] = 'rhel'
                    os_info['name'] = 'cloudlinux'
                    for line in content.split('\n'):
                        if line.startswith('VERSION_ID='):
                            version = line.split('=')[1].strip('"')
                            os_info['version'] = version
                            os_info['major_version'] = int(version.split('.')[0])
                            break
        
        # Check for CentOS (legacy)
        if os.path.exists('/etc/redhat-release'):
            with open('/etc/redhat-release', 'r') as f:
                content = f.read()
                if 'CentOS' in content:
                    os_info['family'] = 'rhel'
                    os_info['name'] = 'centos'
                    # Extract version from CentOS release
                    import re
                    match = re.search(r'CentOS.*?(\d+)', content)
                    if match:
                        os_info['major_version'] = int(match.group(1))
                        os_info['version'] = match.group(1)
        
        return os_info

    def is_almalinux9(self):
        """Check if running on AlmaLinux 9"""
        os_info = self.detect_os_info()
        return os_info['name'] == 'almalinux' and os_info['major_version'] == 9

    def is_almalinux10(self):
        """Check if running on AlmaLinux 10 (GH usmannasir/cyberpanel#1736)"""
        os_info = self.detect_os_info()
        return os_info['name'] == 'almalinux' and os_info['major_version'] == 10

    def is_ubuntu(self):
        """Check if running on Ubuntu"""
        os_info = self.detect_os_info()
        return os_info['family'] == 'ubuntu'

    def is_debian(self):
        """Check if running on Debian"""
        os_info = self.detect_os_info()
        return os_info['family'] == 'debian'

    def is_rhel_family(self):
        """Check if running on RHEL family (RHEL, AlmaLinux, Rocky, CloudLinux, CentOS)"""
        os_info = self.detect_os_info()
        return os_info['family'] == 'rhel'

    def get_os_specific_fixes_needed(self):
        """Determine which fixes are needed for the current OS"""
        os_info = self.detect_os_info()
        fixes = []
        
        if os_info['name'] == 'almalinux' and os_info['major_version'] == 9:
            fixes.extend(['mariadb', 'services', 'litespeed', 'mysql_gpg'])
        elif os_info['name'] == 'almalinux' and os_info['major_version'] == 10:
            fixes.extend(['mariadb', 'services', 'litespeed'])
        elif os_info['name'] == 'rocky' and os_info['major_version'] >= 8:
            fixes.extend(['mariadb', 'services'])
        elif os_info['name'] == 'rhel' and os_info['major_version'] >= 8:
            fixes.extend(['mariadb', 'services'])
        elif os_info['name'] == 'cloudlinux' and os_info['major_version'] >= 8:
            fixes.extend(['mariadb', 'services'])
        elif os_info['family'] == 'ubuntu':
            fixes.extend(['ubuntu_specific'])
        elif os_info['family'] == 'debian':
            fixes.extend(['debian_specific'])
        
        return fixes

    def fix_almalinux9_comprehensive(self):
        """Apply comprehensive AlmaLinux 9 fixes"""
        if not self.is_almalinux9():
            return
        
        self.stdOut("Applying comprehensive AlmaLinux 9 fixes...", 1)
        
        try:
            # Update system packages
            self.stdOut("Updating system packages...", 1)
            command = "dnf update -y"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Install essential build tools and dependencies
            self.stdOut("Installing essential build tools...", 1)
            command = "dnf groupinstall -y 'Development Tools'"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            command = "dnf install -y epel-release"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Install AlmaLinux 9 compatibility packages
            self.stdOut("Installing AlmaLinux 9 compatibility packages...", 1)
            compat_packages = [
                "libxcrypt-compat",
                "libnsl",
                "compat-openssl11",
                "compat-openssl11-devel"
            ]
            
            for package in compat_packages:
                command = f"dnf install -y {package}"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Install PHP dependencies that are missing (with AlmaLinux 9 compatibility)
            self.stdOut("Installing PHP dependencies...", 1)
            
            # Base packages that should work on all systems
            base_deps = [
                "ImageMagick", "ImageMagick-devel",
                "gd", "gd-devel",
                "libicu", "libicu-devel",
                "oniguruma", "oniguruma-devel",
                "aspell", "aspell-devel",
                "freetype-devel",
                "libjpeg-turbo-devel",
                "libpng-devel",
                "libwebp-devel",
                "libXpm-devel",
                "libzip-devel",
                "openssl-devel",
                "sqlite-devel",
                "libxml2-devel",
                "libxslt-devel",
                "curl-devel",
                "libedit-devel",
                "readline-devel",
                "pkgconfig",
                "cmake",
                "gcc-c++"
            ]
            
            # Install base packages
            for dep in base_deps:
                command = f"dnf install -y {dep}"
                self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Install AlmaLinux 9 specific packages with fallbacks
            alma9_specific = [
                ("libc-client", "libc-client-devel"),
                ("libmemcached", "libmemcached-devel")
            ]
            
            for package, dev_package in alma9_specific:
                installed = False
                
                # Try to install both packages together first
                try:
                    command = f"dnf install -y {package} {dev_package}"
                    result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    if result == 1:
                        self.stdOut(f"Successfully installed {package} and {dev_package}", 1)
                        installed = True
                except:
                    pass
                
                if not installed:
                    # Try to install packages individually
                    try:
                        command = f"dnf install -y {package}"
                        result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                        if result == 1:
                            self.stdOut(f"Successfully installed {package}", 1)
                    except:
                        pass
                    
                    try:
                        dev_command = f"dnf install -y {dev_package}"
                        result = self.call(dev_command, self.distro, dev_command, dev_command, 1, 0, os.EX_OSERR)
                        if result == 1:
                            self.stdOut(f"Successfully installed {dev_package}", 1)
                            installed = True
                    except:
                        pass
                
                if not installed:
                    self.stdOut(f"Package {package} not available, trying alternatives...", 1)
                    
                    # For AlmaLinux 9, try enabling PowerTools repository first
                    if self.distro == openeuler and os_info['name'] == 'almalinux' and os_info['major_version'] == '9':
                        try:
                            self.stdOut("Enabling AlmaLinux 9 PowerTools repository...", 1)
                            self.call("dnf config-manager --set-enabled powertools", self.distro, "Enable PowerTools", "Enable PowerTools", 1, 0, os.EX_OSERR)
                            # Try installing again with PowerTools enabled
                            command = f"dnf install -y {package} {dev_package}"
                            result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                            if result == 1:
                                self.stdOut(f"Successfully installed {package} and {dev_package} from PowerTools", 1)
                                installed = True
                        except:
                            self.stdOut("PowerTools repository not available, trying alternatives...", 1)
                    
                    if not installed:
                        # Try alternative package names for AlmaLinux 9
                        alternatives = {
                            "libc-client": ["libc-client-devel", "uw-imap-devel"],
                            "libmemcached": ["libmemcached-devel", "memcached-devel"]
                        }
                        
                        if package in alternatives:
                            for alt_package in alternatives[package]:
                                alt_command = f"dnf install -y {alt_package}"
                                result = self.call(alt_command, self.distro, alt_command, alt_command, 1, 0, os.EX_OSERR)
                                if result == 1:
                                    self.stdOut(f"Successfully installed alternative: {alt_package}", 1)
                                    break
            
            # Disable MariaDB 12.1 repository if MariaDB 10.x is already installed
            # This prevents upgrade attempts in Pre_Install_Required_Components
            self.disableMariaDB12RepositoryIfNeeded()
            
            # CRITICAL: Remove conflicting MariaDB compat packages before installation
            # These packages from MariaDB 12.1 can conflict with MariaDB 10.11
            self.stdOut("Removing conflicting MariaDB compat packages...", 1)
            try:
                subprocess.run("rpm -e --nodeps MariaDB-server-compat-12.1.2-1.el9.noarch 2>/dev/null; true", shell=True, timeout=30)
                subprocess.run("dnf remove -y 'MariaDB-server-compat*' 2>/dev/null || true", shell=True, timeout=60)
                r = subprocess.run("rpm -qa 2>/dev/null | grep -i MariaDB-server-compat", shell=True, capture_output=True, text=True, timeout=30)
                for line in (r.stdout or "").strip().splitlines():
                    pkg = (line.strip().split() or [""])[0]
                    if pkg and "MariaDB-server-compat" in pkg:
                        subprocess.run(["rpm", "-e", "--nodeps", pkg], timeout=30)
                self.stdOut("Removed conflicting MariaDB compat packages", 1)
            except Exception as e:
                self.stdOut("Warning: Could not remove compat packages: " + str(e), 0)
            
            # Do NOT install MariaDB here with plain dnf (that would install distro default 10.11).
            # installMySQL() runs later with the user's chosen version (--mariadb-version: 10.11, 11.8 or 12.1).
            is_installed, installed_version, major_minor = self.checkExistingMariaDB()
            if is_installed:
                self.stdOut(f"MariaDB/MySQL already installed (version: {installed_version}), skipping", 1)
            
            # Install additional required packages
            self.stdOut("Installing additional required packages...", 1)
            additional_packages = [
                "wget", "curl", "unzip", "zip", "rsync",
                "firewalld", "psmisc", "git", "python3",
                "python3-pip", "python3-devel"
            ]
            
            for package in additional_packages:
                command = f"dnf install -y {package}"
                self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Configure firewall
            self.stdOut("Configuring firewall...", 1)
            command = "systemctl enable firewalld"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            command = "systemctl start firewalld"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Add required firewall ports
            self.stdOut("Adding firewall ports...", 1)
            ports = [
                "8090/tcp", "7080/tcp", "80/tcp", "443/tcp",
                "21/tcp", "25/tcp", "587/tcp", "465/tcp",
                "110/tcp", "143/tcp", "993/tcp", "995/tcp",
                "53/tcp", "53/udp", "40110-40210/tcp"
            ]
            
            for port in ports:
                command = f"firewall-cmd --permanent --add-port={port}"
                self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            command = "firewall-cmd --reload"
            self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            self.stdOut("AlmaLinux 9 comprehensive fixes completed successfully!", 1)
            
        except Exception as e:
            self.stdOut(f"Error applying AlmaLinux 9 comprehensive fixes: {str(e)}", 0)

    def fix_rhel_family_common(self):
        """Fix common RHEL family (AlmaLinux, Rocky, RHEL, CloudLinux) issues"""
        try:
            self.stdOut("Applying RHEL family common fixes...", 1)
            
            # Install EPEL repository
            self.stdOut("Installing EPEL repository...", 1)
            try:
                self.call('dnf install -y epel-release', self.distro, 'Installing EPEL', 'Installing EPEL', 1, 1, os.EX_OSERR)
            except:
                try:
                    self.call('yum install -y epel-release', self.distro, 'Installing EPEL (yum)', 'Installing EPEL (yum)', 1, 1, os.EX_OSERR)
                except:
                    self.stdOut("Warning: Could not install EPEL", 1)
            
            # Apply graphics library fixes for RHEL 9+ systems
            os_info = self.detect_os_info()
            if os_info['major_version'] >= 9:
                self.stdOut("Applying RHEL 9+ graphics library fixes...", 1)
                try:
                    command = "dnf install -y --allowerasing mesa-dri-drivers mesa-filesystem mesa-libEGL mesa-libGL mesa-libgbm mesa-libglapi libdrm libglvnd libglvnd-glx libglvnd-egl"
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    self.stdOut("RHEL 9+ graphics library fixes applied successfully", 1)
                except Exception as e:
                    self.stdOut(f"Warning: Graphics library fixes failed: {str(e)}", 1)
            
            # Install common dependencies (conntrack-tools for firewall/SSH security connection termination)
            self.stdOut("Installing common RHEL dependencies...", 1)
            common_deps = [
                'curl',
                'wget',
                'git',
                'python3',
                'python3-pip',
                'gcc',
                'gcc-c++',
                'make',
                'cmake',
                'pcre2-devel',
                'openssl-devel',
                'zlib-devel',
                'conntrack-tools'
            ]
            
            for dep in common_deps:
                try:
                    self.call(f'dnf install -y {dep}', self.distro, f'Installing {dep}', f'Installing {dep}', 1, 0, os.EX_OSERR)
                except:
                    try:
                        self.call(f'yum install -y {dep}', self.distro, f'Installing {dep} (yum)', f'Installing {dep} (yum)', 1, 0, os.EX_OSERR)
                    except:
                        self.stdOut(f"Warning: Could not install {dep}", 1)
            
            return True
            
        except Exception as e:
            self.stdOut(f"Error in fix_rhel_family_common: {str(e)}", 0)
            return False

    def fix_almalinux9_mariadb(self):
        """Apply AlmaLinux 9 MariaDB fixes"""
        try:
            self.stdOut("Applying AlmaLinux 9 MariaDB fixes...", 1)
            
            # Get OS information for AlmaLinux 9 specific handling
            os_info = self.detect_os_info()
            
            # Install AlmaLinux 9 compatibility packages
            self.stdOut("Installing AlmaLinux 9 compatibility packages...", 1)
            compat_packages = [
                "libxcrypt-compat",
                "libnsl",
                "compat-openssl11",
                "compat-openssl11-devel"
            ]
            
            for package in compat_packages:
                command = f"dnf install -y {package}"
                self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Install problematic packages with enhanced fallback logic
            self.stdOut("Installing AlmaLinux 9 specific packages with fallbacks...", 1)
            alma9_specific = [
                ("libc-client", "libc-client-devel"),
                ("libmemcached", "libmemcached-devel")
            ]
            
            for package, dev_package in alma9_specific:
                installed = False
                
                # Try to install both packages together first
                try:
                    command = f"dnf install -y {package} {dev_package}"
                    result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    if result == 1:
                        self.stdOut(f"Successfully installed {package} and {dev_package}", 1)
                        installed = True
                except:
                    pass
                
                if not installed:
                    # Try enabling PowerTools repository for AlmaLinux 9
                    try:
                        self.stdOut("Enabling AlmaLinux 9 PowerTools repository...", 1)
                        self.call("dnf config-manager --set-enabled powertools", self.distro, "Enable PowerTools", "Enable PowerTools", 1, 0, os.EX_OSERR)
                        # Try installing again with PowerTools enabled
                        command = f"dnf install -y {package} {dev_package}"
                        result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                        if result == 1:
                            self.stdOut(f"Successfully installed {package} and {dev_package} from PowerTools", 1)
                            installed = True
                    except:
                        self.stdOut("PowerTools repository not available, trying alternatives...", 1)
                    
                    if not installed:
                        # Try alternative package names and repositories for AlmaLinux 9.6+
                        alternatives = {
                            "libc-client": ["libc-client-devel", "uw-imap-devel"],
                            "libmemcached": ["libmemcached-devel", "memcached-devel"]
                        }
                        
                        if package in alternatives:
                            for alt_package in alternatives[package]:
                                # Try standard repository first
                                alt_command = f"dnf install -y {alt_package}"
                                result = self.call(alt_command, self.distro, alt_command, alt_command, 1, 0, os.EX_OSERR)
                                if result == 1:
                                    self.stdOut(f"Successfully installed alternative: {alt_package}", 1)
                                    break
                                
                                # Try remi repository for uw-imap-devel (AlmaLinux 9.6+)
                                if alt_package == "uw-imap-devel":
                                    try:
                                        self.stdOut("Trying remi repository for uw-imap-devel...", 1)
                                        # Enable remi repository
                                        self.call(
                                            "dnf install -y https://rpms.remirepo.net/enterprise/remi-release-%s.rpm"
                                            % ("10" if install_utils.is_rhel_el10() else "9"),
                                            self.distro, "Install remi repo", "Install remi repo", 1, 0, os.EX_OSERR)
                                        # Try installing from remi
                                        remi_command = f"dnf install -y --enablerepo=remi {alt_package}"
                                        result = self.call(remi_command, self.distro, remi_command, remi_command, 1, 0, os.EX_OSERR)
                                        if result == 1:
                                            self.stdOut(f"Successfully installed {alt_package} from remi repository", 1)
                                            break
                                    except:
                                        self.stdOut(f"Remi repository installation failed for {alt_package}", 1)
                                
                                # Try direct RPM download as last resort
                                if result != 1:
                                    try:
                                        self.stdOut(f"Trying direct RPM download for {alt_package}...", 1)
                                        rpm_urls = {
                                            "uw-imap-devel": "https://rhel.pkgs.org/9/remi-x86_64/uw-imap-devel-2007f-30.el9.remi.x86_64.rpm",
                                            "libc-client-devel": "https://pkgs.org/download/libc-client-devel"
                                        }
                                        
                                        if alt_package in rpm_urls:
                                            # Download and install RPM directly
                                            download_command = f"curl -L {rpm_urls[alt_package]} -o /tmp/{alt_package}.rpm"
                                            self.call(download_command, self.distro, f"Download {alt_package}", f"Download {alt_package}", 1, 0, os.EX_OSERR)
                                            
                                            install_command = f"rpm -ivh /tmp/{alt_package}.rpm --force"
                                            result = self.call(install_command, self.distro, f"Install {alt_package}", f"Install {alt_package}", 1, 0, os.EX_OSERR)
                                            if result == 1:
                                                self.stdOut(f"Successfully installed {alt_package} via direct RPM download", 1)
                                                # Clean up downloaded file
                                                self.call(f"rm -f /tmp/{alt_package}.rpm", self.distro, f"Cleanup {alt_package}", f"Cleanup {alt_package}", 1, 0, os.EX_OSERR)
                                                break
                                    except:
                                        self.stdOut(f"Direct RPM download failed for {alt_package}", 1)
            
            self.stdOut("AlmaLinux 9 MariaDB fixes applied successfully", 1)
        except Exception as e:
            self.stdOut(f"Error applying AlmaLinux 9 MariaDB fixes: {str(e)}", 0)

    def fix_almalinux10_mariadb(self):
        """EPEL/CRB + MariaDB official repo for AlmaLinux 10 (installer prereqs, GH #1736)."""
        if not self.is_almalinux10():
            return
        try:
            self.stdOut("Applying AlmaLinux 10 MariaDB / repo fixes...", 1)
            for cmd, desc in (
                ("dnf install -y curl ca-certificates", "curl and ca-certificates for mariadb_repo_setup"),
                ("dnf install -y epel-release", "EPEL"),
                ("dnf config-manager --set-enabled crb 2>/dev/null || dnf config-manager --set-enabled powertools 2>/dev/null || true", "CRB/PowerTools"),
                ("dnf install -y htop 2>/dev/null || true", "htop"),
                ("dnf install -y libxcrypt-compat 2>/dev/null || true", "libxcrypt-compat for lscpd"),
                ("dnf install -y openssh-server 2>/dev/null || true", "openssh-server for sshd_config"),
            ):
                self.call(cmd, self.distro, desc, desc, 1, 0, os.EX_OSERR)
            for cmd, desc in (
                ("dnf config-manager --disable mariadb-maxscale 2>/dev/null || true", "disable maxscale"),
                ("rm -f /etc/yum.repos.d/mariadb-maxscale.repo /etc/yum.repos.d/mariadb-maxscale.repo.rpmnew 2>/dev/null || true", "remove maxscale repo files"),
            ):
                self.call(cmd, self.distro, desc, desc, 1, 0, os.EX_OSERR)
            mariadb_ver = getattr(preFlightsChecks, 'mariadb_version', '11.8')
            self.call(
                "dnf config-manager --disable mariadb-maxscale 2>/dev/null || true",
                self.distro,
                "disable maxscale after setup",
                "disable maxscale after setup",
                1,
                0,
                os.EX_OSERR,
            )
            if install_utils.install_mariadb_server_rhel(self.distro, mariadb_ver, 1):
                self.stdOut("AlmaLinux 10 MariaDB fixes applied successfully", 1)
            else:
                self.stdOut(
                    "Warning: AlmaLinux 10 MariaDB preflight incomplete (install.py will retry)",
                    1,
                )
        except Exception as e:
            self.stdOut(f"Error applying AlmaLinux 10 MariaDB fixes: {str(e)}", 0)

    def install_package_with_fallbacks(self, package_name, dev_package_name=None):
        """Install package with comprehensive fallback methods for AlmaLinux 9.6+"""
        try:
            installed = False
            
            # Method 1: Try standard repository
            if dev_package_name:
                command = f"dnf install -y {package_name} {dev_package_name}"
            else:
                command = f"dnf install -y {package_name}"
            
            result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            if result == 1:
                self.stdOut(f"Successfully installed {package_name} from standard repository", 1)
                return True
            
            # Method 2: Try PowerTools repository
            try:
                self.stdOut("Trying PowerTools repository...", 1)
                self.call("dnf config-manager --set-enabled powertools", self.distro, "Enable PowerTools", "Enable PowerTools", 1, 0, os.EX_OSERR)
                result = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                if result == 1:
                    self.stdOut(f"Successfully installed {package_name} from PowerTools", 1)
                    return True
            except:
                pass
            
            # Method 3: Try remi repository
            try:
                self.stdOut("Trying remi repository...", 1)
                self.call(
                    "dnf install -y https://rpms.remirepo.net/enterprise/remi-release-%s.rpm"
                    % ("10" if install_utils.is_rhel_el10() else "9"),
                    self.distro, "Install remi repo", "Install remi repo", 1, 0, os.EX_OSERR)
                remi_command = f"dnf install -y --enablerepo=remi {package_name}"
                result = self.call(remi_command, self.distro, remi_command, remi_command, 1, 0, os.EX_OSERR)
                if result == 1:
                    self.stdOut(f"Successfully installed {package_name} from remi repository", 1)
                    return True
            except:
                pass
            
            # Method 4: Try direct RPM download
            rpm_sources = {
                "libc-client-devel": "https://pkgs.org/download/libc-client-devel",
                "uw-imap-devel": "https://rhel.pkgs.org/9/remi-x86_64/uw-imap-devel-2007f-30.el9.remi.x86_64.rpm",
                "libmemcached-devel": "https://mirror.mariadb.org/yum/12.1/rhel9-amd64/rpms/libmemcached-devel-1.0.18-17.el8.x86_64.rpm"
            }
            
            for package in [package_name, dev_package_name]:
                if package and package in rpm_sources:
                    try:
                        self.stdOut(f"Trying direct RPM download for {package}...", 1)
                        download_command = f"curl -L {rpm_sources[package]} -o /tmp/{package}.rpm"
                        self.call(download_command, self.distro, f"Download {package}", f"Download {package}", 1, 0, os.EX_OSERR)
                        
                        install_command = f"rpm -ivh /tmp/{package}.rpm --force"
                        result = self.call(install_command, self.distro, f"Install {package}", f"Install {package}", 1, 0, os.EX_OSERR)
                        if result == 1:
                            self.stdOut(f"Successfully installed {package} via direct RPM download", 1)
                            # Clean up downloaded file
                            self.call(f"rm -f /tmp/{package}.rpm", self.distro, f"Cleanup {package}", f"Cleanup {package}", 1, 0, os.EX_OSERR)
                            installed = True
                    except:
                        self.stdOut(f"Direct RPM download failed for {package}", 1)
            
            return installed
            
        except Exception as e:
            self.stdOut(f"Error in package installation fallback: {str(e)}", 0)
            return False

    def fix_ubuntu_specific(self):
        """Fix Ubuntu-specific installation issues"""
        try:
            self.stdOut("Applying Ubuntu-specific fixes...", 1)
            
            # Install required dependencies (conntrack for firewall/SSH security connection termination)
            self.stdOut("Installing Ubuntu dependencies...", 1)
            ubuntu_deps = [
                'software-properties-common',
                'apt-transport-https',
                'curl',
                'wget',
                'gnupg',
                'lsb-release',
                'conntrack'
            ]
            
            for dep in ubuntu_deps:
                try:
                    self.call(f'apt-get install -y {dep}', self.distro, f'Installing {dep}', f'Installing {dep}', 1, 0, os.EX_OSERR)
                except:
                    self.stdOut(f"Warning: Could not install {dep}", 1)
            
            # Ubuntu 24.04 specific fixes
            os_info = self.detect_os_info()
            if os_info['name'] == 'ubuntu' and os_info['major_version'] >= 24:
                self.stdOut("Applying Ubuntu 24.04 specific fixes...", 1)
                try:
                    command = "DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-dev"
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    self.stdOut("Ubuntu 24.04 specific fixes applied successfully", 1)
                except Exception as e:
                    self.stdOut(f"Warning: Ubuntu 24.04 fixes failed: {str(e)}", 1)
            
            # Update package lists
            self.call('apt-get update', self.distro, 'Updating package lists', 'Updating package lists', 1, 1, os.EX_OSERR)
            
            return True
            
        except Exception as e:
            self.stdOut(f"Error in fix_ubuntu_specific: {str(e)}", 0)
            return False

    def fix_debian_specific(self):
        """Fix Debian-specific installation issues"""
        try:
            self.stdOut("Applying Debian-specific fixes...", 1)
            
            # Install required dependencies (conntrack for firewall/SSH security connection termination)
            self.stdOut("Installing Debian dependencies...", 1)
            debian_deps = [
                'software-properties-common',
                'apt-transport-https',
                'curl',
                'wget',
                'gnupg',
                'lsb-release',
                'conntrack'
            ]
            
            for dep in debian_deps:
                try:
                    self.call(f'apt-get install -y {dep}', self.distro, f'Installing {dep}', f'Installing {dep}', 1, 0, os.EX_OSERR)
                except:
                    self.stdOut(f"Warning: Could not install {dep}", 1)
            
            # Debian 13 specific fixes
            os_info = self.detect_os_info()
            if os_info['name'] == 'debian' and os_info['major_version'] >= 13:
                self.stdOut("Applying Debian 13 specific fixes...", 1)
                try:
                    command = "DEBIAN_FRONTEND=noninteractive apt-get install -y python3-venv python3-dev build-essential"
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    self.stdOut("Debian 13 specific fixes applied successfully", 1)
                except Exception as e:
                    self.stdOut(f"Warning: Debian 13 fixes failed: {str(e)}", 1)
            
            # Update package lists
            self.call('apt-get update', self.distro, 'Updating package lists', 'Updating package lists', 1, 1, os.EX_OSERR)
            
            return True
            
        except Exception as e:
            self.stdOut(f"Error in fix_debian_specific: {str(e)}", 0)
            return False

    def apply_os_specific_fixes(self):
        """Apply OS-specific fixes based on detected OS"""
        try:
            os_info = self.detect_os_info()
            fixes_needed = self.get_os_specific_fixes_needed()
            
            self.stdOut(f"Detected OS: {os_info['name']} {os_info['version']} (family: {os_info['family']})", 1)
            self.stdOut(f"Applying fixes: {', '.join(fixes_needed)}", 1)
            
            # Try universal OS fixes first
            try:
                import sys
                import os
                sys.path.append(os.path.dirname(__file__))
                from universal_os_fixes import UniversalOSFixes
                
                self.stdOut("Applying universal OS compatibility fixes...", 1)
                universal_fixes = UniversalOSFixes()
                if universal_fixes.run_comprehensive_setup():
                    self.stdOut("Universal OS fixes applied successfully", 1)
                    os_i = self.detect_os_info()
                    if os_i.get('name') == 'almalinux' and os_i.get('major_version') == 10:
                        self.stdOut("AlmaLinux 10: running legacy RHEL integration steps after universal fixes...", 1)
                    else:
                        return True
                else:
                    self.stdOut("Universal OS fixes failed, falling back to legacy fixes...", 1)
            except ImportError:
                self.stdOut("Universal OS fixes not available, using legacy fixes...", 1)
            except Exception as e:
                self.stdOut(f"Universal OS fixes error: {str(e)}, falling back to legacy fixes...", 1)
            
            # Apply common RHEL family fixes first
            if self.is_rhel_family():
                self.fix_rhel_family_common()
            
            # Apply specific fixes
            for fix in fixes_needed:
                if fix == 'mariadb' and self.is_almalinux9():
                    self.fix_almalinux9_mariadb()
                elif fix == 'mariadb' and self.is_almalinux10():
                    self.fix_almalinux10_mariadb()
                elif fix == 'ubuntu_specific' and self.is_ubuntu():
                    self.fix_ubuntu_specific()
                elif fix == 'debian_specific' and self.is_debian():
                    self.fix_debian_specific()
            
            self.stdOut("OS-specific fixes completed successfully", 1)
            return True
            
        except Exception as e:
            self.stdOut(f"Error applying OS-specific fixes: {str(e)}", 0)
            return False

    def detectArchitecture(self):
        """Detect system architecture - custom binaries only for x86_64"""
        try:
            import platform
            arch = platform.machine()
            return arch == "x86_64"
        except Exception as msg:
            self.stdOut(str(msg) + " [detectArchitecture]", 0)
            return False

    def detectPlatform(self):
        """Detect OS platform for binary selection (rhel8, rhel9, ubuntu)"""
        try:
            # Check for Ubuntu
            if os.path.exists('/etc/lsb-release'):
                with open('/etc/lsb-release', 'r') as f:
                    content = f.read()
                    if 'Ubuntu' in content or 'ubuntu' in content:
                        return 'ubuntu'

            # Check for RHEL-based distributions
            if os.path.exists('/etc/os-release'):
                with open('/etc/os-release', 'r') as f:
                    content = f.read().lower()

                    # Check for version 8.x (RHEL, AlmaLinux, Rocky, CloudLinux, CentOS 8)
                    if 'version="8.' in content or 'version_id="8.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel8'

                    # Check for version 9.x
                    if 'version="9.' in content or 'version_id="9.' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel9'

                    # EL10: use rhel9 OLS/custom binaries until el10-specific builds ship (GLIBC-compatible)
                    if 'version="10.' in content or 'version_id="10.' in content or 'version_id="10"' in content:
                        if any(distro in content for distro in ['red hat', 'almalinux', 'rocky', 'cloudlinux', 'centos']):
                            return 'rhel9'

            # Default to rhel8 if can't detect (safer default - rhel9 binaries may require GLIBC 2.35)
            self.stdOut("WARNING: Could not detect platform, defaulting to rhel8", 1)
            return 'rhel8'

        except Exception as msg:
            self.stdOut(f"ERROR detecting platform: {msg}, defaulting to rhel8", 0)
            return 'rhel8'

    def getSystemGLIBCVersion(self):
        """Get the system's GLIBC version"""
        try:
            import subprocess
            # Try to get GLIBC version from ldd
            result = subprocess.run(['ldd', '--version'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                # ldd --version output format: "ldd (GNU libc) 2.34"
                for line in result.stdout.split('\n'):
                    if 'GNU libc' in line or 'glibc' in line.lower():
                        import re
                        version_match = re.search(r'(\d+)\.(\d+)', line)
                        if version_match:
                            major = int(version_match.group(1))
                            minor = int(version_match.group(2))
                            return (major, minor)
            
            # Fallback: try to read from libc.so.6
            try:
                result = subprocess.run(['/lib64/libc.so.6'], capture_output=True, text=True, timeout=5)
                if result.returncode != 0 and 'version' in result.stderr.lower():
                    import re
                    version_match = re.search(r'(\d+)\.(\d+)', result.stderr)
                    if version_match:
                        major = int(version_match.group(1))
                        minor = int(version_match.group(2))
                        return (major, minor)
            except:
                pass
            
            # If we can't detect, assume a safe minimum
            self.stdOut("WARNING: Could not detect GLIBC version, assuming 2.34", 1)
            return (2, 34)
        except Exception as msg:
            self.stdOut(f"WARNING: Error detecting GLIBC version: {msg}, assuming 2.34", 0)
            return (2, 34)

    def checkBinaryGLIBCRequirements(self, binary_path):
        """Check GLIBC version requirements of a binary file"""
        try:
            import subprocess
            import re
            
            # Use objdump to check GLIBC version requirements
            # objdump -T shows dynamic symbols and their GLIBC version requirements
            result = subprocess.run(['objdump', '-T', binary_path], capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                # objdump might not be available, try readelf
                result = subprocess.run(['readelf', '-d', binary_path], capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    self.stdOut("WARNING: Could not check binary GLIBC requirements (objdump/readelf not available)", 1)
                    return None
            
            # Look for GLIBC version requirements in the output
            # Format: GLIBC_2.35, GLIBC_2.34, etc.
            max_version = None
            for line in result.stdout.split('\n') + result.stderr.split('\n'):
                # Look for GLIBC version symbols
                matches = re.findall(r'GLIBC_(\d+)\.(\d+)', line)
                for match in matches:
                    major = int(match[0])
                    minor = int(match[1])
                    if max_version is None or (major, minor) > max_version:
                        max_version = (major, minor)
            
            return max_version
            
        except FileNotFoundError:
            # objdump/readelf not available
            self.stdOut("WARNING: objdump/readelf not available, skipping GLIBC check", 1)
            return None
        except Exception as msg:
            self.stdOut(f"WARNING: Error checking binary GLIBC requirements: {msg}", 0)
            return None

    def verifyBinaryCompatibility(self, binary_path):
        """Verify that a binary is compatible with the system's GLIBC version"""
        try:
            system_glibc = self.getSystemGLIBCVersion()
            binary_glibc = self.checkBinaryGLIBCRequirements(binary_path)
            
            if binary_glibc is None:
                # Can't check, but we can try a test run
                self.stdOut("Cannot verify GLIBC requirements, performing test run...", 1)
                return self.testBinaryExecution(binary_path)
            
            self.stdOut(f"System GLIBC: {system_glibc[0]}.{system_glibc[1]}", 1)
            self.stdOut(f"Binary requires GLIBC: {binary_glibc[0]}.{binary_glibc[1]}", 1)
            
            # Check if binary requires newer GLIBC than system has
            if binary_glibc > system_glibc:
                self.stdOut(f"ERROR: Binary requires GLIBC {binary_glibc[0]}.{binary_glibc[1]}, but system has {system_glibc[0]}.{system_glibc[1]}", 1)
                return False
            
            self.stdOut("GLIBC compatibility check passed", 1)
            return True
            
        except Exception as msg:
            self.stdOut(f"WARNING: Error verifying binary compatibility: {msg}", 0)
            # If we can't verify, try test execution
            return self.testBinaryExecution(binary_path)

    def testBinaryExecution(self, binary_path):
        """Test if binary can execute (checks GLIBC compatibility indirectly)"""
        try:
            import subprocess
            # Try to run the binary with --version or -v flag
            # This will fail immediately if GLIBC is incompatible
            # The error format is: "./binary: /lib64/libc.so.6: version `GLIBC_X.Y' not found"
            result = subprocess.run([binary_path, '--version'], capture_output=True, text=True, timeout=5)
            
            # Check both stdout and stderr for GLIBC errors
            output = result.stdout + result.stderr
            
            # Look for GLIBC version not found errors
            if 'GLIBC' in output and ('not found' in output or 'version' in output.lower()):
                # Extract the required GLIBC version from error message
                import re
                glibc_match = re.search(r"GLIBC_(\d+)\.(\d+)'?\s+not found", output)
                if glibc_match:
                    required_major = int(glibc_match.group(1))
                    required_minor = int(glibc_match.group(2))
                    self.stdOut(f"ERROR: Binary requires GLIBC {required_major}.{required_minor} which is not available", 1)
                else:
                    self.stdOut(f"ERROR: Binary GLIBC compatibility test failed: {output[:200]}", 1)
                return False
            
            # If binary executed (even with non-zero return code for --version), it's compatible
            if result.returncode == 0 or len(result.stdout) > 0:
                return True
            
            # If we get here, binary might not support --version, try -v
            result = subprocess.run([binary_path, '-v'], capture_output=True, text=True, timeout=5)
            output = result.stdout + result.stderr
            
            if 'GLIBC' in output and ('not found' in output or 'version' in output.lower()):
                import re
                glibc_match = re.search(r"GLIBC_(\d+)\.(\d+)'?\s+not found", output)
                if glibc_match:
                    required_major = int(glibc_match.group(1))
                    required_minor = int(glibc_match.group(2))
                    self.stdOut(f"ERROR: Binary requires GLIBC {required_major}.{required_minor} which is not available", 1)
                else:
                    self.stdOut(f"ERROR: Binary GLIBC compatibility test failed: {output[:200]}", 1)
                return False
            
            # If no GLIBC error and we got some output, assume compatible
            if len(output) > 0:
                return True
            
            # If binary doesn't support --version/-v, try to check if it's executable
            # by checking file type
            try:
                result = subprocess.run(['file', binary_path], capture_output=True, text=True, timeout=5)
                if 'ELF' in result.stdout and 'executable' in result.stdout:
                    self.stdOut("WARNING: Cannot test binary execution, but file appears valid", 1)
                    return True
            except:
                pass
            
            # Conservative approach: if we can't verify, assume incompatible to be safe
            self.stdOut("WARNING: Could not verify binary execution, skipping installation for safety", 1)
            return False
            
        except subprocess.TimeoutExpired:
            self.stdOut("WARNING: Binary test timed out, assuming compatible", 1)
            return True
        except FileNotFoundError as e:
            # Binary file not found or command not found
            self.stdOut(f"ERROR: Binary test failed - file or command not found: {e}", 1)
            return False
        except Exception as msg:
            # Check if it's a GLIBC error in the exception itself
            error_str = str(msg)
            if 'GLIBC' in error_str and 'not found' in error_str:
                self.stdOut(f"ERROR: Binary GLIBC compatibility test failed: {error_str}", 1)
                return False
            
            self.stdOut(f"WARNING: Could not test binary execution: {msg}", 0)
            # Conservative approach: if we can't test, assume incompatible to be safe
            return False

    def downloadCustomBinary(self, url, destination, expected_sha256=None):
        """Download custom binary file with optional checksum verification"""
        try:
            self.stdOut(f"Downloading {os.path.basename(destination)}...", 1)

            # Use wget for better progress display
            command = f'wget -q --show-progress {url} -O {destination}'
            res = self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Check if file was downloaded successfully by verifying it exists and has reasonable size
            if os.path.exists(destination):
                file_size = os.path.getsize(destination)
                # Verify file size is reasonable (at least 10KB to avoid error pages/empty files)
                if file_size > 10240:  # 10KB
                    if file_size > 1048576:  # 1MB
                        self.stdOut(f"Downloaded successfully ({file_size / (1024*1024):.2f} MB)", 1)
                    else:
                        self.stdOut(f"Downloaded successfully ({file_size / 1024:.2f} KB)", 1)

                    # Verify checksum if provided
                    if expected_sha256:
                        self.stdOut("Verifying checksum...", 1)
                        import hashlib
                        sha256_hash = hashlib.sha256()
                        with open(destination, "rb") as f:
                            for byte_block in iter(lambda: f.read(4096), b""):
                                sha256_hash.update(byte_block)
                        actual_sha256 = sha256_hash.hexdigest()

                        if actual_sha256 == expected_sha256:
                            self.stdOut("Checksum verified successfully", 1)
                            return True
                        else:
                            self.stdOut(f"ERROR: Checksum mismatch!", 1)
                            self.stdOut(f"Expected: {expected_sha256}", 1)
                            self.stdOut(f"Got:      {actual_sha256}", 1)
                            return False
                    else:
                        return True
                else:
                    self.stdOut(f"ERROR: Downloaded file too small ({file_size} bytes)", 1)
                    return False
            else:
                self.stdOut("ERROR: Download failed - file not found", 1)
                return False

        except Exception as msg:
            self.stdOut(f"ERROR: {msg} [downloadCustomBinary]", 0)
            return False

    def downloadCDNLibraries(self):
        """
        Download CDN libraries (qrious, chart.js) locally to eliminate tracking prevention warnings.
        These files are downloaded before collectstatic runs so they're included in the static files.
        Tries latest version of qrious first, falls back to hardcoded version if latest fails.
        """
        try:
            custom_js_dir = '/usr/local/CyberCP/baseTemplate/static/baseTemplate/custom-js'
            
            # Ensure directory exists
            if not os.path.exists(custom_js_dir):
                os.makedirs(custom_js_dir, mode=0o755)
            
            # Download qrious.min.js - try latest first, fallback to known working version
            qrious_path = os.path.join(custom_js_dir, 'qrious.min.js')
            qrious_urls = [
                'https://cdn.jsdelivr.net/npm/qrious@latest/dist/qrious.min.js',  # Try latest first
                'https://cdn.jsdelivr.net/npm/qrious@4.0.2/dist/qrious.min.js'   # Fallback to known working version
            ]
            qrious_downloaded = False
            for qrious_url in qrious_urls:
                command = f'wget -q --timeout=30 {qrious_url} -O {qrious_path}'
                result = self.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)
                if result and os.path.exists(qrious_path) and os.path.getsize(qrious_path) > 1000:  # At least 1KB
                    os.chmod(qrious_path, 0o644)
                    version_info = "latest" if "latest" in qrious_url else "4.0.2"
                    logging.InstallLog.writeToFile(f"Downloaded qrious.min.js ({version_info})")
                    qrious_downloaded = True
                    break
            if not qrious_downloaded:
                logging.InstallLog.writeToFile("Warning: Failed to download qrious.min.js, continuing anyway")
            
            # Download chart.js - try latest first, fallback to known working version
            chartjs_path = os.path.join(custom_js_dir, 'chart.umd.min.js')
            chartjs_urls = [
                'https://cdn.jsdelivr.net/npm/chart.js@latest/dist/chart.umd.min.js',  # Try latest first
                'https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js'   # Fallback to known working version
            ]
            chartjs_downloaded = False
            for chartjs_url in chartjs_urls:
                command = f'wget -q --timeout=30 {chartjs_url} -O {chartjs_path}'
                result = self.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)
                if result and os.path.exists(chartjs_path) and os.path.getsize(chartjs_path) > 100000:  # At least 100KB
                    os.chmod(chartjs_path, 0o644)
                    version_info = "latest" if "latest" in chartjs_url else "4.4.1"
                    logging.InstallLog.writeToFile(f"Downloaded chart.umd.min.js ({version_info})")
                    chartjs_downloaded = True
                    # Create copy for chart.js compatibility (some code may expect chart.js name)
                    chartjs_compat_path = os.path.join(custom_js_dir, 'chart.js')
                    if not os.path.exists(chartjs_compat_path):
                        shutil.copy2(chartjs_path, chartjs_compat_path)
                    break
            if not chartjs_downloaded:
                logging.InstallLog.writeToFile("Warning: Failed to download chart.umd.min.js, continuing anyway")
                
        except Exception as msg:
            logging.InstallLog.writeToFile(f"Warning: Error downloading CDN libraries: {str(msg)}, continuing anyway")

    def installCustomOLSBinaries(self):
        """Install custom OpenLiteSpeed binaries with PHP config support"""
        try:
            self.stdOut("Installing Custom OpenLiteSpeed Binaries", 1)
            self.stdOut("=" * 50, 1)

            # Check architecture
            if not self.detectArchitecture():
                self.stdOut("WARNING: Custom binaries only available for x86_64", 1)
                self.stdOut("Skipping custom binary installation", 1)
                self.stdOut("Standard OLS will be used", 1)
                return True  # Not a failure, just skip

            # Detect platform
            platform = self.detectPlatform()
            self.stdOut(f"Detected platform: {platform}", 1)

            config = ols_binaries_config.BINARY_CONFIGS.get(platform)
            if not config:
                self.stdOut(f"ERROR: No binaries available for platform {platform}", 1)
                self.stdOut("Skipping custom binary installation", 1)
                return True  # Not fatal

            OLS_BINARY_URL = config['url']
            OLS_BINARY_SHA256 = config['sha256']
            MODULE_URL = config['module_url']
            MODULE_SHA256 = config['module_sha256']
            OLS_BINARY_PATH = "/usr/local/lsws/bin/openlitespeed"
            MODULE_PATH = "/usr/local/lsws/modules/cyberpanel_ols.so"

            # Create backup
            from datetime import datetime
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            backup_dir = f"/usr/local/lsws/backup-{timestamp}"

            try:
                os.makedirs(backup_dir, exist_ok=True)
                if os.path.exists(OLS_BINARY_PATH):
                    shutil.copy2(OLS_BINARY_PATH, f"{backup_dir}/openlitespeed.backup")
                    self.stdOut(f"Backup created at: {backup_dir}", 1)
            except Exception as e:
                self.stdOut(f"WARNING: Could not create backup: {e}", 1)

            # Download binaries to temp location
            tmp_binary = "/tmp/openlitespeed-custom"
            tmp_module = "/tmp/cyberpanel_ols.so"

            self.stdOut("Downloading custom binaries...", 1)

            # Download OpenLiteSpeed binary with checksum verification
            if not self.downloadCustomBinary(OLS_BINARY_URL, tmp_binary, OLS_BINARY_SHA256):
                self.stdOut("ERROR: Failed to download or verify OLS binary", 1)
                self.stdOut("Continuing with standard OLS", 1)
                return True  # Not fatal, continue with standard OLS

            # CRITICAL: Verify GLIBC compatibility before installation
            self.stdOut("Verifying GLIBC compatibility...", 1)
            if not self.verifyBinaryCompatibility(tmp_binary):
                self.stdOut("=" * 50, 1)
                self.stdOut("ERROR: Binary GLIBC requirements incompatible with system", 1)
                self.stdOut("This binary would cause OpenLiteSpeed to fail to start", 1)
                self.stdOut("Skipping custom binary installation to preserve system stability", 1)
                self.stdOut("Standard OLS binary from package manager will be used", 1)
                self.stdOut("=" * 50, 1)
                # Clean up downloaded binary
                try:
                    if os.path.exists(tmp_binary):
                        os.remove(tmp_binary)
                except:
                    pass
                return True  # Not fatal, continue with standard OLS

            # Download module with checksum verification (if available)
            module_downloaded = False
            if MODULE_URL and MODULE_SHA256:
                if not self.downloadCustomBinary(MODULE_URL, tmp_module, MODULE_SHA256):
                    self.stdOut("ERROR: Failed to download or verify module", 1)
                    self.stdOut("Continuing with standard OLS", 1)
                    return True  # Not fatal, continue with standard OLS
                module_downloaded = True
            else:
                self.stdOut("Note: No CyberPanel module for this platform", 1)

            # Install OpenLiteSpeed binary
            self.stdOut("Installing custom binaries...", 1)

            try:
                # Ensure /usr/local/lsws/bin exists (dnf openlitespeed may use different layout)
                ols_bin_dir = os.path.dirname(OLS_BINARY_PATH)
                os.makedirs(ols_bin_dir, mode=0o755, exist_ok=True)
                ols_base = os.path.dirname(ols_bin_dir)
                if not os.path.isdir(ols_base):
                    os.makedirs(ols_base, mode=0o755, exist_ok=True)

                # Make binary executable before moving
                os.chmod(tmp_binary, 0o755)
                
                # Final compatibility test before installation
                if not self.testBinaryExecution(tmp_binary):
                    self.stdOut("ERROR: Final binary compatibility test failed", 1)
                    self.stdOut("Skipping installation to prevent OpenLiteSpeed failure", 1)
                    try:
                        if os.path.exists(tmp_binary):
                            os.remove(tmp_binary)
                    except:
                        pass
                    return True  # Not fatal, continue with standard OLS
                
                shutil.move(tmp_binary, OLS_BINARY_PATH)
                self.stdOut("Installed OpenLiteSpeed binary", 1)
            except Exception as e:
                self.stdOut(f"ERROR: Failed to install binary: {e}", 1)
                # Try to restore backup if installation failed
                try:
                    if os.path.exists(f"{backup_dir}/openlitespeed.backup"):
                        shutil.copy2(f"{backup_dir}/openlitespeed.backup", OLS_BINARY_PATH)
                        self.stdOut("Restored original binary from backup", 1)
                except:
                    pass
                return False

            # Install module (if downloaded)
            if module_downloaded:
                try:
                    os.makedirs(os.path.dirname(MODULE_PATH), exist_ok=True)
                    shutil.move(tmp_module, MODULE_PATH)
                    os.chmod(MODULE_PATH, 0o644)
                    self.stdOut("Installed CyberPanel module", 1)
                except Exception as e:
                    self.stdOut(f"ERROR: Failed to install module: {e}", 1)
                    return False

            # Verify installation
            if os.path.exists(OLS_BINARY_PATH):
                if not module_downloaded or os.path.exists(MODULE_PATH):
                    self.stdOut("=" * 50, 1)
                    self.stdOut("Custom Binaries Installed Successfully", 1)
                    self.stdOut("Features enabled:", 1)
                    self.stdOut("  - Static-linked cross-platform binary", 1)
                    if module_downloaded:
                        self.stdOut("  - Apache-style .htaccess support", 1)
                        self.stdOut("  - php_value/php_flag directives", 1)
                        self.stdOut("  - Enhanced header control", 1)
                    self.stdOut(f"Backup: {backup_dir}", 1)
                    self.stdOut("=" * 50, 1)
                    # Configure module after installation
                    self.configureCustomModule()
                    # Enable Auto-SSL if not already configured
                    conf_path = '/usr/local/lsws/conf/httpd_config.conf'
                    try:
                        if os.path.exists(conf_path):
                            with open(conf_path, 'r') as f:
                                content = f.read()
                            if 'autoSSL' not in content:
                                content = re.sub(
                                    r'(adminEmails\s+\S+)',
                                    r'\1\nautoSSL                   1\nacmeEmail                 admin@cyberpanel.net',
                                    content,
                                    count=1
                                )
                                with open(conf_path, 'w') as f:
                                    f.write(content)
                                self.stdOut("Auto-SSL enabled in httpd_config.conf", 1)
                    except Exception as e:
                        self.stdOut(f"WARNING: Could not enable Auto-SSL: {e}", 1)
                    return True

            self.stdOut("ERROR: Installation verification failed", 1)
            return False

        except Exception as msg:
            self.stdOut(f"ERROR: {msg} [installCustomOLSBinaries]", 0)
            self.stdOut("Continuing with standard OLS", 1)
            return True  # Non-fatal error, continue

    def configureCustomModule(self):
        """Configure CyberPanel module in OpenLiteSpeed config"""
        try:
            self.stdOut("Configuring CyberPanel module...", 1)

            CONFIG_FILE = "/usr/local/lsws/conf/httpd_config.conf"

            if not os.path.exists(CONFIG_FILE):
                self.stdOut("WARNING: Config file not found", 1)
                self.stdOut("Module will be auto-loaded", 1)
                return True

            # Check if module is already configured
            with open(CONFIG_FILE, 'r') as f:
                content = f.read()
                if 'cyberpanel_ols' in content:
                    self.stdOut("Module already configured", 1)
                    return True

            # Add module configuration
            module_config = """
module cyberpanel_ols {
  ls_enabled          1
}
"""
            # Backup config
            shutil.copy2(CONFIG_FILE, f"{CONFIG_FILE}.backup")

            # Append module config
            with open(CONFIG_FILE, 'a') as f:
                f.write(module_config)

            self.stdOut("Module configured successfully", 1)
            return True

        except Exception as msg:
            self.stdOut(f"WARNING: Module configuration failed: {msg}", 1)
            self.stdOut("Module may still work via auto-load", 1)
            return True  # Non-fatal

    def installLiteSpeed(self, ent, serial):
        """Install LiteSpeed Web Server (OpenLiteSpeed or Enterprise)"""
        try:
            self.stdOut("Installing LiteSpeed Web Server...", 1)
            
            if ent == 0:
                # Install OpenLiteSpeed from LiteSpeed repo when possible (min official: ols_version_policy)
                self.stdOut("Installing OpenLiteSpeed (see install/ols_version_policy.py for minimum version)...", 1)
                self.add_litespeed_repo()
                if self.distro == ubuntu or self.distro == debian12:
                    self.install_package('openlitespeed')
                else:
                    self.install_package('openlitespeed')
                install_utils.ensure_openlitespeed_rpm_layout(self.distro, log=1)
                self.upgrade_openlitespeed_to_latest()
                install_utils.ensure_openlitespeed_rpm_layout(self.distro, log=1)
                # Official repo OLS when version/layout OK; custom overlay breaks re-install on EL10
                if install_utils.should_skip_custom_ols_overlay():
                    ols_ver = self.get_installed_ols_version()
                    ver_txt = (
                        '%d.%d.%d' % ols_ver if ols_ver
                        else '%d.%d.%d' % ols_version_policy.MIN_OFFICIAL_OLS
                    )
                    self.stdOut(
                        'Using official OpenLiteSpeed %s+ (no custom binary overlay)' % ver_txt,
                        1,
                    )
                else:
                    self.installCustomOLSBinaries()
                    install_utils.ensure_openlitespeed_rpm_layout(self.distro, log=1)
                
                # Configure OpenLiteSpeed
                self.fix_ols_configs()
                self.changePortTo80()
            else:
                # Install LiteSpeed Enterprise
                self.stdOut("Installing LiteSpeed Enterprise...", 1)
                self.installLiteSpeedEnterprise(serial)
            
            self.stdOut("LiteSpeed Web Server installed successfully", 1)
            return True
            
        except Exception as e:
            self.stdOut(f"Error installing LiteSpeed: {str(e)}", 0)
            return False

    def installLiteSpeedEnterprise(self, serial):
        """Install LiteSpeed Enterprise"""
        try:
            # Get the latest LSWS Enterprise version
            lsws_version = self.getLatestLSWSVersion()
            
            # Download and install LiteSpeed Enterprise
            if self.ISARM():
                command = f'wget https://www.litespeedtech.com/packages/6.0/lsws-{lsws_version}-ent-aarch64-linux.tar.gz'
            else:
                command = f'wget https://www.litespeedtech.com/packages/6.0/lsws-{lsws_version}-ent-x86_64-linux.tar.gz'
            
            self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            if self.ISARM():
                command = f'tar zxf lsws-{lsws_version}-ent-aarch64-linux.tar.gz'
            else:
                command = f'tar zxf lsws-{lsws_version}-ent-x86_64-linux.tar.gz'
            
            self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            # Handle license
            if str.lower(serial) == 'trial':
                command = f'wget -q --output-document=lsws-{lsws_version}/trial.key http://license.litespeedtech.com/reseller/trial.key'
            elif serial == '1111-2222-3333-4444':
                command = f'wget -q --output-document=/root/cyberpanel/install/lsws-{lsws_version}/trial.key http://license.litespeedtech.com/reseller/trial.key'
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            else:
                writeSerial = open(f'lsws-{lsws_version}/serial.no', 'w')
                writeSerial.writelines(serial)
                writeSerial.close()
            
            # Install LiteSpeed Enterprise
            os.chdir(f'lsws-{lsws_version}')
            command = 'chmod +x install.sh'
            self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            command = 'chmod +x functions.sh'
            self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            command = './install.sh'
            self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            os.chdir(self.cwd)
            
            return True
            
        except Exception as e:
            self.stdOut(f"Error installing LiteSpeed Enterprise: {str(e)}", 0)
            return False

    def getLatestLSWSVersion(self):
        """Fetch the latest LSWS Enterprise version"""
        try:
            import urllib.request
            import re
            url = "https://www.litespeedtech.com/products/litespeed-web-server/download"
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=10) as response:
                html = response.read().decode('utf-8')
            
            version_pattern = r'lsws-(\d+\.\d+\.\d+)-ent'
            versions = re.findall(version_pattern, html)
            
            if versions:
                latest_version = sorted(versions, key=lambda v: [int(x) for x in v.split('.')])[-1]
                return latest_version
        except:
            pass
        
        return "6.3.4"  # Fallback version

    def ISARM(self):
        """Check if running on ARM architecture"""
        try:
            command = 'uname -a'
            result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
            return 'aarch64' in result.stdout
        except:
            return False

    def disableMariaDB12RepositoryIfNeeded(self):
        """Disable MariaDB 12.x repository if MariaDB 10.x is already installed so 11.8 LTS upgrade can be used"""
        try:
            is_installed, installed_version, major_minor = self.checkExistingMariaDB()
            
            if is_installed and major_minor and major_minor != "unknown":
                try:
                    major_ver = float(major_minor)
                    if major_ver < 11.0:
                        # MariaDB 10.x is installed, disable 12.x repo so we use 11.8 LTS
                        self.stdOut(f"MariaDB {installed_version} detected, disabling MariaDB 12.x repository", 1)
                        logging.InstallLog.writeToFile(f"MariaDB {installed_version} detected, disabling MariaDB 12.x repository")
                        
                        repo_files = [
                            '/etc/yum.repos.d/mariadb-main.repo',
                            '/etc/yum.repos.d/mariadb.repo',
                            '/etc/yum.repos.d/mariadb-12.1.repo',
                            '/etc/yum.repos.d/mariadb-main.repo.bak'
                        ]
                        
                        # Also check for any mariadb repo files
                        import glob
                        repo_files.extend(glob.glob('/etc/yum.repos.d/*mariadb*.repo'))
                        
                        disabled_any = False
                        for repo_file in repo_files:
                            if os.path.exists(repo_file):
                                try:
                                    # Read the file
                                    with open(repo_file, 'r') as f:
                                        lines = f.readlines()
                                    
                                    # Modify the file to disable all MariaDB repositories
                                    modified = False
                                    new_lines = []
                                    in_mariadb_section = False
                                    
                                    for line in lines:
                                        # Check if we're entering a MariaDB repository section
                                        if line.strip().startswith('[') and 'mariadb' in line.lower():
                                            in_mariadb_section = True
                                            new_lines.append(line)
                                            # Add enabled=0 if not already present
                                            if 'enabled' not in line.lower():
                                                new_lines.append('enabled=0\n')
                                                modified = True
                                        elif in_mariadb_section:
                                            # If we see enabled=1, change it to enabled=0
                                            if line.strip().startswith('enabled=') and 'enabled=0' not in line.lower():
                                                new_lines.append('enabled=0\n')
                                                modified = True
                                            elif line.strip().startswith('['):
                                                # New section, exit MariaDB section
                                                in_mariadb_section = False
                                                new_lines.append(line)
                                            else:
                                                new_lines.append(line)
                                        else:
                                            new_lines.append(line)
                                    
                                    # Write back if modified
                                    if modified:
                                        with open(repo_file, 'w') as f:
                                            f.writelines(new_lines)
                                        self.stdOut(f"Disabled MariaDB repository in {repo_file}", 1)
                                        logging.InstallLog.writeToFile(f"Disabled MariaDB repository in {repo_file}")
                                        disabled_any = True
                                    
                                except Exception as e:
                                    self.stdOut(f"Warning: Could not disable repository {repo_file}: {e}", 1)
                                    logging.InstallLog.writeToFile(f"Warning: Could not disable repository {repo_file}: {e}")
                        
                        # Always exclude MariaDB-server from dnf/yum operations to prevent upgrades
                        try:
                            # Add exclude to dnf.conf
                            dnf_conf = '/etc/dnf/dnf.conf'
                            exclude_line = 'exclude=MariaDB-server'
                            
                            if os.path.exists(dnf_conf):
                                with open(dnf_conf, 'r') as f:
                                    dnf_content = f.read()
                                
                                # Check if exclude line already exists
                                if exclude_line not in dnf_content:
                                    # Check if there's already an exclude line
                                    if 'exclude=' in dnf_content:
                                        # Append to existing exclude line
                                        dnf_content = re.sub(r'(exclude=.*)', r'\1 MariaDB-server', dnf_content)
                                    else:
                                        # Add new exclude line
                                        dnf_content = dnf_content.rstrip() + '\n' + exclude_line + '\n'
                                    
                                    with open(dnf_conf, 'w') as f:
                                        f.write(dnf_content)
                                    self.stdOut("Added MariaDB-server to dnf excludes to prevent upgrade", 1)
                                    logging.InstallLog.writeToFile("Added MariaDB-server to dnf excludes")
                            else:
                                # Create dnf.conf with exclude
                                with open(dnf_conf, 'w') as f:
                                    f.write('[main]\n')
                                    f.write(exclude_line + '\n')
                                self.stdOut("Created dnf.conf with MariaDB-server exclude", 1)
                                logging.InstallLog.writeToFile("Created dnf.conf with MariaDB-server exclude")
                        except Exception as e:
                            self.stdOut(f"Warning: Could not add exclude to dnf.conf: {e}", 1)
                            logging.InstallLog.writeToFile(f"Warning: Could not add exclude to dnf.conf: {e}")
                        
                        return True
                except (ValueError, TypeError):
                    pass
            
            return False
        except Exception as e:
            self.stdOut(f"Warning: Error checking MariaDB repository: {e}", 1)
            logging.InstallLog.writeToFile(f"Warning: Error checking MariaDB repository: {e}")
            return False

    def checkExistingMariaDB(self):
        """Check if MariaDB/MySQL is already installed and return version info"""
        try:
            # Check if MariaDB/MySQL server package is installed
            if self.distro == ubuntu:
                command = 'dpkg -l | grep -iE "^(ii|rc).*mariadb-server|mysql-server" 2>/dev/null || echo ""'
            else:
                command = 'rpm -qa | grep -iE "^(mariadb-server|mysql-server|MariaDB-server)" 2>/dev/null || echo ""'
            
            result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
            
            if result.stdout.strip():
                # MariaDB/MySQL server package is installed, get version
                version_command = 'mysql --version 2>/dev/null || mariadb --version 2>/dev/null || echo ""'
                version_result = subprocess.run(version_command, shell=True, capture_output=True, universal_newlines=True)
                version_output = version_result.stdout.strip()
                
                if version_output:
                    # Extract version number (e.g., "10.11.15" from "mysql  Ver 10.11.15-MariaDB")
                    import re
                    version_match = re.search(r'(\d+\.\d+\.\d+)', version_output)
                    if version_match:
                        installed_version = version_match.group(1)
                        major_minor = '.'.join(installed_version.split('.')[:2])  # e.g., "10.11"
                        logging.InstallLog.writeToFile(f"Found existing MariaDB installation: {installed_version} (major.minor: {major_minor})")
                        return True, installed_version, major_minor
                
                logging.InstallLog.writeToFile("Found MariaDB/MySQL package but could not determine version")
                return True, "unknown", "unknown"
            
            # Also check if MariaDB service exists and data directory exists (might be installed but package query failed)
            if os.path.exists('/var/lib/mysql') and os.listdir('/var/lib/mysql'):
                logging.InstallLog.writeToFile("Found MariaDB data directory, assuming MariaDB is installed")
                # Try to get version one more time
                version_command = 'mysql --version 2>/dev/null || mariadb --version 2>/dev/null || echo ""'
                version_result = subprocess.run(version_command, shell=True, capture_output=True, universal_newlines=True)
                version_output = version_result.stdout.strip()
                if version_output:
                    import re
                    version_match = re.search(r'(\d+\.\d+\.\d+)', version_output)
                    if version_match:
                        installed_version = version_match.group(1)
                        major_minor = '.'.join(installed_version.split('.')[:2])
                        return True, installed_version, major_minor
                return True, "unknown", "unknown"
            
            return False, None, None
        except Exception as e:
            logging.InstallLog.writeToFile(f"Error checking existing MariaDB: {str(e)}")
            return False, None, None

    def _attemptMariaDBUpgrade(self):
        """Attempt to upgrade MariaDB to 11.8 LTS. Returns True if successful, False otherwise."""
        try:
            if self.distro == ubuntu:
                # Ubuntu MariaDB upgrade
                command = 'DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common apt-transport-https curl -y'
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    logging.InstallLog.writeToFile(f"Failed to install prerequisites: {result.stderr}")
                    return False
                
                command = "mkdir -p /etc/apt/keyrings"
                subprocess.run(command, shell=True, check=False)
                
                command = "curl -o /etc/apt/keyrings/mariadb-keyring.pgp 'https://mariadb.org/mariadb_release_signing_key.pgp'"
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    logging.InstallLog.writeToFile(f"Failed to download MariaDB keyring: {result.stderr}")
                    return False
                
                # Setup MariaDB 11.8 LTS repository
                command = 'curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash -s -- --mariadb-server-version=11.8'
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    logging.InstallLog.writeToFile(f"Failed to setup MariaDB repository: {result.stderr}")
                    return False
                try:
                    import install_utils
                    install_utils.strip_mariadb_maxscale_apt_repos()
                except Exception:
                    pass
                
                command = 'DEBIAN_FRONTEND=noninteractive apt-get update -y'
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    logging.InstallLog.writeToFile(f"Failed to update package list: {result.stderr}")
                    return False
                
                # Attempt to install MariaDB 12.1
                command = "DEBIAN_FRONTEND=noninteractive apt-get install mariadb-server -y"
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    # Check if error is due to upgrade restrictions
                    error_output = result.stderr + result.stdout
                    if "upgrade" in error_output.lower() or "manual" in error_output.lower():
                        logging.InstallLog.writeToFile("MariaDB upgrade blocked - requires manual intervention")
                    else:
                        logging.InstallLog.writeToFile(f"MariaDB installation failed: {error_output}")
                    return False
                
                return True
            else:
                # RHEL-based MariaDB upgrade
                subprocess.run("dnf module reset -y mariadb", shell=True, capture_output=True, text=True, timeout=180)
                dis = subprocess.run(
                    "dnf module disable -y mariadb",
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=180,
                )
                if dis.returncode != 0:
                    logging.InstallLog.writeToFile(
                        "dnf module disable mariadb non-zero (ignored on non-modular images): "
                        + (dis.stderr or "")[:500]
                    )
                # Setup MariaDB 11.8 LTS repository
                command = 'curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | sudo bash -s -- --mariadb-server-version=11.8'
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    logging.InstallLog.writeToFile(f"Failed to setup MariaDB repository: {result.stderr}")
                    return False
                
                # Canonical MariaDB.org package names (AppStream module must stay disabled).
                command = (
                    'dnf install -y MariaDB-server MariaDB-client MariaDB-shared MariaDB-backup '
                    'MariaDB-common MariaDB-devel --allowerasing'
                )
                result = subprocess.run(command, shell=True, capture_output=True, universal_newlines=True)
                if result.returncode != 0:
                    # Check if error is due to upgrade restrictions
                    error_output = result.stderr + result.stdout
                    if "PREIN scriptlet failed" in error_output or "upgrade" in error_output.lower() or "manual" in error_output.lower():
                        logging.InstallLog.writeToFile("MariaDB upgrade blocked by package manager - requires manual intervention")
                    else:
                        logging.InstallLog.writeToFile(f"MariaDB installation failed: {error_output}")
                    return False
                
                return True
                
        except Exception as e:
            logging.InstallLog.writeToFile(f"Exception during MariaDB upgrade attempt: {str(e)}")
            return False

    def installMySQL(self, mysql):
        """Install MySQL/MariaDB"""
        try:
            # Check if MariaDB is already installed
            is_installed, installed_version, major_minor = self.checkExistingMariaDB()
            
            if is_installed:
                self.stdOut(f"MariaDB/MySQL is already installed (version: {installed_version})", 1)
                
                # Check if we need to upgrade
                should_try_upgrade = False
                if major_minor and major_minor != "unknown":
                    try:
                        major_ver = float(major_minor)
                        import install_utils
                        if major_ver < 11.0 and not install_utils.is_rhel_el10():
                            should_try_upgrade = True
                            self.stdOut(f"Existing MariaDB {major_minor} detected. Attempting to upgrade to MariaDB 11.8 LTS...", 1)
                            self.stdOut("If upgrade fails, we will use the existing MariaDB installation.", 1)
                        elif major_ver < 11.0 and install_utils.is_rhel_el10():
                            self.stdOut(
                                f"MariaDB {major_minor} from AppStream on AlmaLinux/RHEL 10 "
                                "(MariaDB.org 11.8 is not installed due to package conflicts).",
                                1,
                            )
                    except (ValueError, TypeError):
                        pass
                
                # If MariaDB 10.x is installed, try to upgrade to 11.8 LTS first
                if should_try_upgrade:
                    try:
                        self.stdOut("Attempting to install MariaDB 11.8 LTS...", 1)
                        upgrade_success = self._attemptMariaDBUpgrade()
                        if upgrade_success:
                            self.stdOut("✅ Successfully upgraded to MariaDB 11.8 LTS", 1)
                            self.startMariaDB()
                            self.changeMYSQLRootPassword()
                            self.fixMariaDB()
                            return True
                        else:
                            self.stdOut("⚠️  MariaDB 11.8 LTS upgrade failed, using existing MariaDB installation", 1)
                            self.startMariaDB()
                            return True
                    except Exception as upgrade_error:
                        error_msg = str(upgrade_error)
                        logging.InstallLog.writeToFile(f"MariaDB upgrade attempt failed: {error_msg}")
                        
                        # Check if error is due to upgrade restrictions
                        if "PREIN scriptlet failed" in error_msg or "upgrade" in error_msg.lower() or "manual" in error_msg.lower():
                            self.stdOut("⚠️  MariaDB upgrade blocked by package manager (10.x to 12.x requires manual upgrade)", 1)
                            self.stdOut(f"Using existing MariaDB {installed_version} installation", 1)
                        else:
                            self.stdOut(f"⚠️  MariaDB upgrade failed: {error_msg}", 1)
                            self.stdOut(f"Using existing MariaDB {installed_version} installation", 1)
                        
                        # Fall back to existing installation
                        self.startMariaDB()
                        return True
                
                # MariaDB 12.x or higher already installed, or version unknown but working
                # Just ensure it's running
                self.stdOut("Using existing MariaDB installation", 1)
                self.startMariaDB()
                return True
            
            self.stdOut("Installing MySQL/MariaDB...", 1)
            
            if self.distro == ubuntu:
                # Ubuntu MariaDB installation
                command = 'DEBIAN_FRONTEND=noninteractive apt-get install software-properties-common apt-transport-https curl -y'
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                
                command = "mkdir -p /etc/apt/keyrings"
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                
                command = "curl -o /etc/apt/keyrings/mariadb-keyring.pgp 'https://mariadb.org/mariadb_release_signing_key.pgp'"
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                
                # Setup MariaDB repository (respect --mariadb-version / installer preference)
                mariadb_ver = getattr(preFlightsChecks, 'mariadb_version', None) or '11.8'
                mariadb_ver = _normalize_mariadb_version(mariadb_ver)
                self.stdOut(f"Configuring MariaDB.org repository for version {mariadb_ver}...", 1)
                command = (
                    'curl -LsS https://downloads.mariadb.com/MariaDB/mariadb_repo_setup | '
                    'sudo bash -s -- --mariadb-server-version=%s'
                ) % mariadb_ver
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                try:
                    import install_utils
                    install_utils.strip_mariadb_maxscale_apt_repos()
                except Exception:
                    pass
                
                command = 'DEBIAN_FRONTEND=noninteractive apt-get update -y'
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                
                command = "DEBIAN_FRONTEND=noninteractive apt-get install mariadb-server -y"
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
                
            else:
                # RHEL-based MariaDB installation
                # CRITICAL: Remove conflicting MariaDB compat packages first
                # These packages from MariaDB 12.x can conflict with 10.x/11.x
                self.stdOut("Removing conflicting MariaDB compat packages...", 1)
                try:
                    # Multiple aggressive removal attempts to ensure compat package is gone
                    # Step 1: Try dnf remove with allowerasing
                    subprocess.run("dnf remove -y --allowerasing 'MariaDB-server-compat*' 2>/dev/null || true", shell=True, timeout=60)
                    
                    # Step 2: Force remove with rpm
                    subprocess.run("rpm -e --nodeps MariaDB-server-compat-12.1.2-1.el9.noarch 2>/dev/null; true", shell=True, timeout=30)
                    
                    # Step 3: Find and remove any remaining compat packages
                    r = subprocess.run("rpm -qa 2>/dev/null | grep -i MariaDB-server-compat", shell=True, capture_output=True, text=True, timeout=30)
                    for line in (r.stdout or "").strip().splitlines():
                        pkg = (line.strip().split() or [""])[0]
                        if pkg and "MariaDB-server-compat" in pkg:
                            self.stdOut(f"Force removing remaining compat package: {pkg}", 1)
                            subprocess.run(["rpm", "-e", "--nodeps", pkg], timeout=30)
                    
                    # Step 4: Verify removal and exclude from future installs
                    r = subprocess.run("rpm -qa 2>/dev/null | grep -i MariaDB-server-compat", shell=True, capture_output=True, text=True, timeout=30)
                    if r.stdout.strip():
                        self.stdOut(f"Warning: Some compat packages still present: {r.stdout.strip()}", 0)
                        # Add to dnf exclude to prevent reinstallation
                        subprocess.run("dnf config-manager --setopt exclude='MariaDB-server-compat*' --save 2>/dev/null || true", shell=True, timeout=30)
                    else:
                        self.stdOut("Successfully removed all MariaDB-server-compat packages", 1)
                except Exception as e:
                    self.stdOut("Warning: Could not remove compat packages: " + str(e), 0)
                
                # Check if MariaDB is already installed before setting up repository
                is_installed, installed_version, major_minor = self.checkExistingMariaDB()
                
                if is_installed:
                    self.stdOut(f"MariaDB/MySQL is already installed (version: {installed_version}), skipping installation", 1)
                    # Use existing if already on 10.x, 11.x or 12.x
                    if major_minor and major_minor != "unknown":
                        try:
                            major_ver = float(major_minor)
                            if major_ver >= 10.0:
                                self.stdOut("Using existing MariaDB installation (10.x/11.x/12.x)", 1)
                                self.startMariaDB()
                                self.changeMYSQLRootPassword()
                                self.fixMariaDB()
                                return True
                        except (ValueError, TypeError):
                            pass
                
                # Set up MariaDB repository only if not already installed (version from --mariadb-version)
                mariadb_ver = getattr(preFlightsChecks, 'mariadb_version', '11.8')
                # Allow MariaDB-server to be installed: remove from dnf exclude if present (e.g. from previous run or cyberpanel.sh)
                dnf_conf = '/etc/dnf/dnf.conf'
                if os.path.exists(dnf_conf) and ('MariaDB-server' in open(dnf_conf).read()):
                    try:
                        with open(dnf_conf, 'r') as f:
                            dnf_content = f.read()
                        if 'MariaDB-server' in (dnf_content or '') and 'exclude=' in (dnf_content or ''):
                            # Remove MariaDB-server and MariaDB-server* from exclude= line(s)
                            def strip_mariadb_exclude(match):
                                line = match.group(0)
                                rest = re.sub(r'\bMariaDB-server\*?\s*', '', line).strip()
                                if rest == 'exclude=' or rest == 'exclude':
                                    return ''
                                return rest.rstrip() + '\n'
                            new_content = re.sub(r'exclude=[^\n]*', strip_mariadb_exclude, dnf_content)
                            new_content = re.sub(r'\n\n+', '\n', new_content)
                            if new_content != dnf_content:
                                with open(dnf_conf, 'w') as f:
                                    f.write(new_content)
                                self.stdOut("Temporarily removed MariaDB-server from dnf exclude for installation", 1)
                    except Exception as e:
                        self.stdOut(f"Warning: Could not adjust dnf exclude: {e}", 1)
                    # Fallback: use sed so exclude is cleared even if Python path failed
                    if 'MariaDB-server' in open(dnf_conf).read():
                        subprocess.run(
                            "sed -i '/^exclude=/s/MariaDB-server\\*\\s*//g; /^exclude=/s/\\s*MariaDB-server\\*//g; /^exclude=\\s*$/d' " + dnf_conf,
                            shell=True, timeout=5, capture_output=True
                        )
                        self.stdOut("Temporarily removed MariaDB-server from dnf exclude for installation (fallback)", 1)
                if not install_utils.install_mariadb_server_rhel(self.distro, mariadb_ver, 1):
                    self.stdOut(
                        "Error: Failed to install MariaDB server packages (MariaDB.org and AppStream)",
                        0,
                    )
                    return False
            
            # Verify MariaDB client exists (EL10 may only expose /usr/sbin/mariadb until symlinked)
            install_utils.ensure_mariadb_client_cli(self.distro, 1)
            mysql_cli = install_utils.resolve_mysql_cli()
            if not mysql_cli:
                import time
                for _wait in range(5):
                    time.sleep(2)
                    install_utils.ensure_mariadb_client_cli(self.distro, 1)
                    mysql_cli = install_utils.resolve_mysql_cli()
                    if mysql_cli:
                        break
            if not mysql_cli:
                self.stdOut("Error: MariaDB binaries not found after installation. Installation may have failed.", 0)
                return False
            
            # Start and enable MariaDB
            if not self.startMariaDB():
                self.stdOut("Error: Failed to start MariaDB service", 0)
                return False
            
            # Wait a moment for MariaDB to be ready
            import time
            time.sleep(3)
            
            # Verify MariaDB is running before changing password
            mariadb_running = False
            for service_name in ['mariadb', 'mysql', 'mysqld']:
                try:
                    result = subprocess.run(f"systemctl is-active {service_name}", shell=True, capture_output=True, text=True, timeout=5)
                    if result.returncode == 0 and 'active' in result.stdout.lower():
                        mariadb_running = True
                        break
                except:
                    continue
            
            if not mariadb_running:
                self.stdOut("Warning: MariaDB service may not be running. Attempting password change anyway...", 0)
            
            self.changeMYSQLRootPassword()
            self.fixMariaDB()
            
            self.stdOut("MySQL/MariaDB installed successfully", 1)
            return True
            
        except Exception as e:
            self.stdOut(f"Error installing MySQL/MariaDB: {str(e)}", 0)
            return False

    def startMariaDB(self):
        """Start MariaDB service"""
        try:
            self.stdOut("Starting MariaDB service...", 1)
            
            # Try different service names
            service_names = ['mariadb', 'mysql', 'mysqld']
            started = False
            
            for service_name in service_names:
                try:
                    try:
                        chk = subprocess.run(
                            f"systemctl is-active {service_name}",
                            shell=True,
                            capture_output=True,
                            text=True,
                            timeout=5,
                        )
                        if chk.returncode == 0 and 'active' in (chk.stdout or '').lower():
                            self.manage_service(service_name, 'enable')
                            self.stdOut(f"{service_name} already active", 1)
                            started = True
                            break
                    except Exception:
                        pass
                    self.manage_service(service_name, 'start')
                    self.manage_service(service_name, 'enable')
                    self.stdOut(f"Successfully started {service_name} service", 1)
                    started = True
                    break
                except Exception as e:
                    self.stdOut(f"Could not start {service_name}: {str(e)}", 0)
                    continue
            
            if not started:
                self.stdOut("Warning: Could not start MariaDB service", 0)
                return False
                
            return True
        except Exception as e:
            self.stdOut(f"Error starting MariaDB: {str(e)}", 0)
            return False

    def changeMYSQLRootPassword(self):
        """Change MySQL root password"""
        try:
            if self.remotemysql == 'OFF':
                # Verify mysql/mariadb command exists before attempting password change
                mysql_exists = False
                for cmd in ['mysql', 'mariadb', '/usr/bin/mysql', '/usr/bin/mariadb']:
                    if self.command_exists(cmd.split()[-1]) or os.path.exists(cmd):
                        mysql_exists = True
                        break
                
                if not mysql_exists:
                    self.stdOut("Error: mysql/mariadb command not found. MariaDB may not have been installed successfully.", 0)
                    self.ensure_mysql_password_file()  # Still save password for manual fix
                    return False
                
                # MariaDB 11+ ships root@localhost with unix_socket OR mysql_native_password USING 'invalid'.
                # Plain IDENTIFIED BY leaves password auth broken for non-root OS users (CyberPanel runs as cyberpanel).
                root_pw = self.mysql_Root_password.replace("'", "''")
                passwordCMD = (
                    "use mysql;"
                    "DROP DATABASE IF EXISTS test;"
                    "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%%';"
                    "ALTER USER 'root'@'localhost' IDENTIFIED VIA mysql_native_password USING PASSWORD('%s');"
                    "GRANT ALL PRIVILEGES ON *.* TO 'root'@'localhost' WITH GRANT OPTION;"
                    "flush privileges;"
                ) % (root_pw)

                # Try socket authentication first (for fresh MariaDB installations)
                socket_commands = ['sudo mysql', 'sudo mariadb', 'sudo /usr/bin/mysql', 'sudo /usr/bin/mariadb']
                password_commands = ['mysql -u root', 'mariadb -u root', '/usr/bin/mysql -u root', '/usr/bin/mariadb -u root']

                success = False

                # First try socket authentication (common for fresh MariaDB installs)
                self.stdOut("Attempting to set MySQL root password using socket authentication...", 1)
                for cmd in socket_commands:
                    try:
                        if self.command_exists(cmd.split()[-1]):  # Check if the mysql/mariadb command exists
                            command = f'{cmd} -e "{passwordCMD}"'
                            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                            if result.returncode == 0:
                                self.stdOut(f"Successfully set MySQL root password using: {cmd}", 1)
                                success = True
                                break
                            else:
                                self.stdOut(f"Socket auth failed with {cmd}: {result.stderr}", 0)
                    except Exception as e:
                        self.stdOut(f"Error with socket auth {cmd}: {str(e)}", 0)
                        continue

                # If socket auth failed, try traditional password-based connection
                if not success:
                    self.stdOut("Socket authentication failed, trying traditional connection...", 1)
                    for cmd in password_commands:
                        try:
                            if self.command_exists(cmd.split()[0]):  # Check if command exists
                                command = f'{cmd} -e "{passwordCMD}"'
                                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                                if result.returncode == 0:
                                    self.stdOut(f"Successfully set MySQL root password using: {cmd}", 1)
                                    success = True
                                    break
                                else:
                                    self.stdOut(f"Traditional auth failed with {cmd}: {result.stderr}", 0)
                        except Exception as e:
                            self.stdOut(f"Error with traditional auth {cmd}: {str(e)}", 0)
                            continue

                if not success:
                    self.stdOut("Failed to set MySQL root password with all methods. Database may need manual configuration.", 0)
                    # Still save the password file so manual fix is possible
                    self.ensure_mysql_password_file()
                    return False

                # Save MySQL password to file for later use
                self.ensure_mysql_password_file()

                # Verify password auth works without unix_socket (required for CyberPanel web UI)
                verified = False
                cli = install_utils.resolve_mysql_cli() or 'mariadb'
                for verify_cmd in [
                    f"{cli} -h127.0.0.1 -uroot -p{self.mysql_Root_password} -e 'SELECT 1;'",
                    f"{cli} -uroot -p{self.mysql_Root_password} -e 'SELECT 1;'",
                ]:
                    try:
                        vr = subprocess.run(
                            verify_cmd, shell=True, capture_output=True, text=True, timeout=15,
                        )
                        if vr.returncode == 0:
                            verified = True
                            break
                    except Exception:
                        continue
                if verified:
                    self.stdOut("MySQL root password verified for application access", 1)
                else:
                    self.stdOut(
                        "Warning: MySQL root password set but password auth verification failed; "
                        "database creation in the panel may not work until fixed.",
                        0,
                    )
                    logging.InstallLog.writeToFile(
                        "MySQL root password verification failed after changeMYSQLRootPassword"
                    )

                self.stdOut("MySQL root password set successfully", 1)
                return True

        except Exception as e:
            self.stdOut(f"Error changing MySQL root password: {str(e)}", 0)
            return False

    def execute_mysql_command(self, sql_command, description="MySQL command"):
        """Execute MySQL command with proper authentication fallback"""
        try:
            # Try password-based authentication first if password file exists
            try:
                passFile = "/etc/cyberpanel/mysqlPassword"
                if os.path.exists(passFile):
                    with open(passFile, 'r') as f:
                        password = f.read().split('\n', 1)[0]

                    # Try mariadb first, then mysql
                    for cmd_base in ['mariadb', 'mysql']:
                        if self.command_exists(cmd_base):
                            command = f'{cmd_base} -u root -p{password} -e "{sql_command}"'
                            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                            if result.returncode == 0:
                                self.stdOut(f"✓ {description} executed successfully with password auth", 1)
                                return True
            except:
                pass

            # Fallback to socket authentication
            for cmd_base in ['sudo mariadb', 'sudo mysql']:
                try:
                    if self.command_exists(cmd_base.split()[-1]):
                        command = f'{cmd_base} -e "{sql_command}"'
                        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                        if result.returncode == 0:
                            self.stdOut(f"✓ {description} executed successfully with socket auth", 1)
                            return True
                except:
                    continue

            self.stdOut(f"✗ Failed to execute {description}: {sql_command}", 0)
            return False

        except Exception as e:
            self.stdOut(f"Error executing MySQL command: {str(e)}", 0)
            return False

    def ensure_mysql_password_file(self):
        """Ensure MySQL password file exists and is properly configured"""
        try:
            os.makedirs('/etc/cyberpanel', exist_ok=True)
            
            # Check if password file already exists
            passFile = '/etc/cyberpanel/mysqlPassword'
            if os.path.exists(passFile):
                # Verify the file has content
                with open(passFile, 'r') as f:
                    content = f.read().strip()
                if content:
                    # Fix permissions on existing file
                    import pwd, grp
                    try:
                        uid = pwd.getpwnam('root').pw_uid
                        gid = grp.getgrnam('cyberpanel').gr_gid
                        os.chown(passFile, uid, gid)
                        os.chmod(passFile, 0o640)
                        self.stdOut("MySQL password file exists - fixed permissions (root:cyberpanel 640)", 1)
                    except KeyError:
                        # If cyberpanel group doesn't exist yet, keep current permissions
                        self.stdOut("MySQL password file already exists and has content", 1)
                    return
            
            # Create or update the password file
            if hasattr(self, 'mysql_Root_password') and self.mysql_Root_password:
                with open(passFile, 'w') as f:
                    f.write(self.mysql_Root_password)

                # Set proper ownership and permissions
                # root:cyberpanel with 640 permissions so cyberpanel group can read
                import pwd, grp
                try:
                    uid = pwd.getpwnam('root').pw_uid
                    gid = grp.getgrnam('cyberpanel').gr_gid
                    os.chown(passFile, uid, gid)
                    os.chmod(passFile, 0o640)  # rw-r----- (owner read/write, group read)
                    self.stdOut("MySQL password saved with proper permissions (root:cyberpanel 640)", 1)
                except KeyError as e:
                    # If cyberpanel group doesn't exist yet, fall back to root-only access
                    os.chmod(passFile, 0o600)
                    self.stdOut("MySQL password saved (cyberpanel group not found, using root-only permissions)", 1)

                logging.InstallLog.writeToFile("MySQL password file created successfully")
            else:
                raise Exception("No MySQL root password available to save")
                
        except Exception as e:
            error_msg = f"Critical: Could not save MySQL password to file: {str(e)}"
            self.stdOut(error_msg, 0)
            logging.InstallLog.writeToFile(error_msg)
            raise Exception(error_msg)

    def _ensure_mariadb_client_no_ssl(self):
        """Ensure MariaDB client connects without SSL (avoids ERROR 2026 when server has have_ssl=DISABLED)."""
        client_cnf = "[client]\nssl=0\nskip-ssl\n"
        try:
            # RHEL/AlmaLinux: /etc/my.cnf.d/cyberpanel-client.cnf
            if not os.path.exists('/etc/my.cnf.d'):
                os.makedirs('/etc/my.cnf.d', mode=0o755, exist_ok=True)
            with open('/etc/my.cnf.d/cyberpanel-client.cnf', 'w') as f:
                f.write(client_cnf)
            logging.InstallLog.writeToFile("Created /etc/my.cnf.d/cyberpanel-client.cnf (client SSL disabled)")
        except Exception as e:
            logging.InstallLog.writeToFile("_ensure_mariadb_client_no_ssl: /etc/my.cnf.d: %s" % str(e))
        try:
            # Debian/Ubuntu: /etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf
            if os.path.exists('/etc/mysql/mariadb.conf.d'):
                with open('/etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf', 'w') as f:
                    f.write(client_cnf)
                logging.InstallLog.writeToFile("Created /etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf (client SSL disabled)")
        except Exception as e:
            logging.InstallLog.writeToFile("_ensure_mariadb_client_no_ssl: mariadb.conf.d: %s" % str(e))

    def command_exists(self, command):
        """Check if a command exists in PATH"""
        try:
            result = subprocess.run(['which', command], capture_output=True, text=True)
            return result.returncode == 0
        except:
            return False

    def fixMariaDB(self):
        """Configure MariaDB for CyberPanel"""
        try:
            self.stdOut("Configuring MariaDB for CyberPanel...", 1)
            
            # Connect to MySQL and configure
            import MySQLdb as mariadb
            conn = mariadb.connect(user='root', passwd=self.mysql_Root_password)
            cursor = conn.cursor()
            cursor.execute('set global innodb_file_per_table = on;')
            try:
                cursor.execute('set global innodb_file_format = Barracuda;')
                cursor.execute('set global innodb_large_prefix = on;')
            except:
                pass
            cursor.close()
            conn.close()
            
            # Update MariaDB configuration
            try:
                fileName = '/etc/mysql/mariadb.conf.d/50-server.cnf'
                if os.path.exists(fileName):
                    with open(fileName, 'r') as f:
                        data = f.readlines()
                    
                    with open(fileName, 'w') as f:
                        for line in data:
                            f.write(line.replace('utf8mb4', 'utf8'))
            except:
                pass
            
            # Restart MariaDB
            self.manage_service('mariadb', 'restart')
            
            self.stdOut("MariaDB configured successfully", 1)
            return True
            
        except Exception as e:
            self.stdOut(f"Error configuring MariaDB: {str(e)}", 0)
            return False

    def installPowerDNS(self):
        """Install PowerDNS"""
        try:
            self.stdOut("Installing PowerDNS...", 1)

            if self.distro == ubuntu:
                # Stop and disable systemd-resolved
                self.manage_service('systemd-resolved', 'stop')
                self.manage_service('systemd-resolved.service', 'disable')

                # Create temporary resolv.conf
                try:
                    os.rename('/etc/resolv.conf', '/etc/resolv.conf.bak')
                except:
                    pass

                with open('/etc/resolv.conf', 'w') as f:
                    f.write('nameserver 8.8.8.8\n')
                    f.write('nameserver 8.8.4.4\n')

                # Install PowerDNS
                command = "DEBIAN_FRONTEND=noninteractive apt-get update"
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = "DEBIAN_FRONTEND=noninteractive apt-get -y install pdns-server pdns-backend-mysql"
                self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

                command = 'systemctl stop pdns || true'
                self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)

            else:
                # RHEL-based PowerDNS installation
                self.install_package('pdns pdns-backend-mysql')

            # Configure PowerDNS after installation
            self.installPowerDNSConfigurations()

            self.stdOut("PowerDNS installed successfully", 1)
            return True

        except Exception as e:
            self.stdOut(f"Error installing PowerDNS: {str(e)}", 0)
            return False

    def installPowerDNSConfigurations(self):
        """Configure PowerDNS with MySQL backend"""
        try:
            self.stdOut("Configuring PowerDNS...", 1)

            # Get the MySQL password
            mysqlPassword = getattr(self, 'mysql_Root_password', 'cyberpanel')

            # Determine the correct config path based on distribution
            if self.distro in [centos, cent8, openeuler]:
                dnsPath = "/etc/pdns/pdns.conf"
            else:
                dnsPath = "/etc/powerdns/pdns.conf"
                # Ensure directory exists for Ubuntu
                dnsDir = os.path.dirname(dnsPath)
                if not os.path.exists(dnsDir):
                    try:
                        os.makedirs(dnsDir, mode=0o755)
                    except OSError as e:
                        if e.errno != errno.EEXIST:
                            raise

            # Copy the PowerDNS configuration file (cwd may be temp dir with install/ subdir when run from cyberpanel.sh)
            source_file = os.path.join(self.cwd, "dns-one", "pdns.conf")
            if not os.path.exists(source_file):
                source_file = os.path.join(self.cwd, "install", "dns-one", "pdns.conf")
            if not os.path.exists(source_file):
                source_file = os.path.join(self.cwd, "dns", "pdns.conf")

            if os.path.exists(source_file):
                import shutil
                shutil.copy2(source_file, dnsPath)
                self.stdOut(f"PowerDNS config copied to {dnsPath}", 1)
            else:
                self.stdOut(f"[WARNING] PowerDNS config source not found, creating basic config...", 1)
                # Create a basic configuration if source doesn't exist
                with open(dnsPath, 'w') as f:
                    f.write("# PowerDNS MySQL Backend Configuration\n")
                    f.write("launch=gmysql\n")
                    f.write("gmysql-host=localhost\n")
                    f.write("gmysql-port=3306\n")
                    f.write("gmysql-user=cyberpanel\n")
                    f.write(f"gmysql-password={mysqlPassword}\n")
                    f.write("gmysql-dbname=cyberpanel\n")
                    f.write("\n# Basic PowerDNS settings\n")
                    f.write("daemon=no\n")
                    f.write("guardian=no\n")
                    f.write("setgid=pdns\n")
                    f.write("setuid=pdns\n")

            # Update the MySQL password in the config file
            if os.path.exists(dnsPath):
                with open(dnsPath, 'r') as f:
                    data = f.readlines()

                writeDataToFile = open(dnsPath, 'w')
                for line in data:
                    if line.find("gmysql-password") > -1:
                        writeDataToFile.write(f"gmysql-password={mysqlPassword}\n")
                    else:
                        writeDataToFile.write(line)
                writeDataToFile.close()

                # Set proper permissions
                if self.distro in [centos, cent8, openeuler]:
                    command = f'chown root:pdns {dnsPath}'
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    command = f'chmod 640 {dnsPath}'
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                else:
                    command = f'chown root:pdns {dnsPath}'
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                    command = f'chmod 640 {dnsPath}'
                    self.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                self.stdOut("PowerDNS configuration completed", 1)
                install_utils.restore_selinux_contexts(dnsPath, os.path.dirname(dnsPath))
                return True

        except Exception as e:
            self.stdOut(f"Error configuring PowerDNS: {str(e)}", 0)
            logging.InstallLog.writeToFile(f'[ERROR] Failed to configure PowerDNS: {str(e)}')
            return False

    def installPureFTPD(self):
        """Install Pure-FTPd"""
        try:
            self.stdOut("Installing Pure-FTPd...", 1)
            
            if self.distro == ubuntu:
                self.install_package('pure-ftpd-mysql')
            else:
                self.install_package('pure-ftpd')
            
            # Enable service
            service_name = self.pureFTPDServiceName(self.distro)
            command = f"systemctl enable {service_name}"
            self.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            # Create FTP groups and users (idempotent for re-install)
            install_utils.ensure_pureftpd_system_user(self.distro, log=1)
            
            self.stdOut("Pure-FTPd installed successfully", 1)
            return True
            
        except Exception as e:
            self.stdOut(f"Error installing Pure-FTPd: {str(e)}", 0)
            return False

    def fix_ols_configs(self):
        """Fix OpenLiteSpeed configurations"""
        try:
            self.stdOut("Fixing OpenLiteSpeed configurations...", 1)
            
            # Check if OpenLiteSpeed configuration file exists
            config_file = self.server_root_path + "conf/httpd_config.conf"
            if not os.path.exists(config_file):
                self.stdOut("OpenLiteSpeed configuration file not found, creating default configuration...", 1)
                # Create the configuration directory if it doesn't exist
                os.makedirs(os.path.dirname(config_file), exist_ok=True)
                # Create a basic configuration file
                with open(config_file, 'w') as f:
                    f.write("# OpenLiteSpeed Configuration\n")
                    f.write("serverName localhost\n")
                    f.write("listener *:8088 {\n")
                    f.write("  address *:8088\n")
                    f.write("  secure 0\n")
                    f.write("  map *:8088 *\n")
                    f.write("}\n")
                    f.write("listener *:80 {\n")
                    f.write("  address *:80\n")
                    f.write("  secure 0\n")
                    f.write("  map *:80 *\n")
                    f.write("}\n")
                self.stdOut("Default OpenLiteSpeed configuration created", 1)
            
            # Remove example virtual host
            data = open(config_file, 'r').readlines()
            writeDataToFile = open(config_file, 'w')
            
            for items in data:
                if items.find("map") > -1 and items.find("Example") > -1:
                    continue
                else:
                    writeDataToFile.writelines(items)
            
            writeDataToFile.close()
            
            self.stdOut("OpenLiteSpeed configurations fixed", 1)
            return True
            
        except Exception as e:
            self.stdOut(f"Error fixing OpenLiteSpeed configs: {str(e)}", 0)
            return False

    def changePortTo80(self):
        """Change OpenLiteSpeed port to 80"""
        try:
            self.stdOut("Changing OpenLiteSpeed port to 80...", 1)
            
            file_path = self.server_root_path + "conf/httpd_config.conf"
            if os.path.exists(file_path):
                if self.modify_file_content(file_path, {"*:8088": "*:80"}):
                    self.stdOut("OpenLiteSpeed port changed to 80", 1)
                    if not install_utils.restart_litespeed(self.server_root_path):
                        self.stdOut(
                            "Note: port set to 80; LiteSpeed restart deferred (run systemctl restart lsws)",
                            1,
                        )
                    return True
                return False
            self.stdOut("OpenLiteSpeed configuration file not found, skipping port change", 1)
            install_utils.ensure_openlitespeed_rpm_layout(self.distro, log=1)
            return False

        except Exception as e:
            self.stdOut(f"Error changing port to 80: {str(e)}", 0)
            return False

    def modify_file_content(self, file_path, replacements):
        """Generic file content modification"""
        try:
            with open(file_path, 'r') as f:
                data = f.readlines()
            
            with open(file_path, 'w') as f:
                for line in data:
                    modified_line = line
                    for old, new in replacements.items():
                        if old in line:
                            modified_line = line.replace(old, new)
                            break
                    f.write(modified_line)
            return True
        except Exception as e:
            self.stdOut(f"Error modifying file {file_path}: {str(e)}", 0)
            return False

    def reStartLiteSpeed(self):
        """Restart LiteSpeed"""
        try:
            if install_utils.restart_litespeed(self.server_root_path):
                return True
            self.stdOut(
                "Warning: LiteSpeed restart skipped (lswsctrl missing; install may continue)",
                1,
            )
            return False
        except Exception as e:
            self.stdOut(f"Error restarting LiteSpeed: {str(e)}", 0)
            return False

    def get_service_name(self, service):
        """Get the correct service name for the current distribution"""
        service_map = {
            'pdns': 'pdns',
            'powerdns': 'pdns',
            'pure-ftpd': 'pure-ftpd',
            'pureftpd': 'pure-ftpd'
        }
        
        # Platform-specific service name mapping
        if self.is_debian_family():
            if service in ['pdns', 'powerdns']:
                return 'pdns-server'
            elif service in ['pure-ftpd', 'pureftpd']:
                return 'pure-ftpd'
        elif self.is_centos_family():
            if service in ['pdns', 'powerdns']:
                return 'pdns'
            elif service in ['pure-ftpd', 'pureftpd']:
                return 'pure-ftpd'
        
        return service_map.get(service, service)
    
    def manage_service(self, service_name, action="start"):
        """Unified service management with error handling"""
        # Check if service exists before trying to manage it
        check_command = f'systemctl list-unit-files | grep -q "{service_name}.service"'
        result = subprocess.run(check_command, shell=True, capture_output=True)
        
        if result.returncode != 0:
            preFlightsChecks.stdOut(f"Service {service_name} not found, skipping {action}", 1)
            return 1  # Return success since service doesn't exist
        
        command = f'systemctl {action} {service_name}'
        return preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
    
    def remove_package(self, package_name, silent=False):
        """Unified package removal across distributions"""
        command, shell = install_utils.get_package_remove_command(self.distro, package_name)
        
        if not silent:
            return preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, shell)
        else:
            return preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR, shell)

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
        self.cyberpanel_db_password = None  # Will be set during password generation
        self.mysql_Root_password = install_utils.generate_pass()  # Generate MySQL root password


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
                    mResult = subprocess.run(command, capture_output=True,universal_newlines=True, shell=True)
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

                command = "find /lib/modules/ -type f -name '*quota_v*.ko*'"


                if subprocess.check_output(command,shell=True).decode("utf-8").find("quota/") == -1:
                    self.install_package("linux-image-extra-virtual", silent=True)

                if self.edit_fstab('/', '/') == 0:
                    preFlightsChecks.stdOut("Quotas will not be abled as we are are failed to modify fstab file.")
                    return 0

                command = 'mount -o remount /'
                try:
                    mResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
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

                ####

                command = "find /lib/modules/ -type f -name '*quota_v*.ko*'"
                try:
                    iResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                except:
                    iResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                             universal_newlines=True, shell=True)

                print(repr(iResult.stdout))

                # Only if the first command works, run the rest

                if iResult.returncode == 0:
                    command = "echo '{}' | sed -n 's|/lib/modules/\\([^/]*\\)/.*|\\1|p' | sort -u".format(iResult.stdout)
                    try:
                        result = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except:
                        result = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)
                    fResult = result.stdout.rstrip('\n')
                    print(repr(result.stdout.rstrip('\n')))

                    command  = 'uname -r'
                    try:
                        ffResult = subprocess.run(command, capture_output=True, universal_newlines=True, shell=True)
                    except:
                        ffResult = subprocess.run(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

                    ffResult = ffResult.stdout.rstrip('\n')

                    command = f"DEBIAN_FRONTEND=noninteractive  apt-get install linux-modules-extra-{ffResult}"
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)

                ###

                    command = f'modprobe quota_v1 -S {ffResult}'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

                    command = f'modprobe quota_v2 -S {ffResult}'
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
                result = subprocess.run('systemd-detect-virt', capture_output=True, universal_newlines=True, shell=True)
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
    def resFailed(distro, res, command=None):
        return install_utils.resFailed(distro, res, command)

    # Using shared function from install_utils
    @staticmethod
    def call(command, distro, bracket, message, log=0, do_exit=0, code=os.EX_OK, shell=False):
        # Fix missing /usr/local/CyberPanel/bin/python on install/upgrade (avoid FileNotFoundError)
        if isinstance(command, str) and '/usr/local/CyberPanel/bin/python' in command:
            if not os.path.isfile('/usr/local/CyberPanel/bin/python'):
                fallback = '/usr/bin/python3' if os.path.isfile('/usr/bin/python3') else '/usr/local/bin/python3'
                if os.path.isfile(fallback):
                    command = command.replace('/usr/local/CyberPanel/bin/python', fallback, 1)
                    shell = True
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
                if subprocess.run(
                    'id -u cyberpanel >/dev/null 2>&1',
                    shell=True,
                ).returncode != 0:
                    command = "useradd -s /bin/false cyberpanel"
                    preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                else:
                    logging.InstallLog.writeToFile(
                        "cyberpanel system user already exists; skipping useradd"
                    )

            ###############################

            ### Docker User/group

            if self.distro == ubuntu or self.distro == debian12:
                if subprocess.run('id -u docker >/dev/null 2>&1', shell=True).returncode != 0:
                    command = 'adduser --disabled-login --gecos "" docker'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            else:
                if subprocess.run('id -u docker >/dev/null 2>&1', shell=True).returncode != 0:
                    command = "useradd -r -s /bin/false docker"
                    preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'getent group docker >/dev/null || groupadd docker'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)

            command = 'usermod -aG docker docker'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'usermod -aG docker cyberpanel'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ###

            command = "mkdir -p /etc/letsencrypt/live/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        except BaseException as msg:
            logging.InstallLog.writeToFile("[ERROR] setup_account_cyberpanel. " + str(msg))

    def installCyberPanelRepo(self):
        self.stdOut("Install Cyberpanel repo")

        if self.distro == ubuntu:
            try:
                # Use the new LiteSpeed repository setup method
                command = "bash -c 'wget -O - https://repo.litespeed.sh | bash'"
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            except:
                logging.InstallLog.writeToFile("[ERROR] Exception during CyberPanel install")
                preFlightsChecks.stdOut("[ERROR] Exception during CyberPanel install")
                os._exit(os.EX_SOFTWARE)
        elif self.distro == debian12:
            try:
                # Use the official LiteSpeed repository setup method for Debian 12
                command = "bash -c 'wget -O - https://repo.litespeed.sh | bash'"
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            except:
                logging.InstallLog.writeToFile("[ERROR] Exception during CyberPanel install - Debian 12 repository setup")
                preFlightsChecks.stdOut("[ERROR] Exception during CyberPanel install - Debian 12 repository setup")
                os._exit(os.EX_SOFTWARE)

        elif self.distro in (centos, cent8):
            import install_utils
            if not install_utils.install_litespeed_repo_rhel(self.distro, log=1):
                logging.InstallLog.writeToFile(
                    "[ERROR] LiteSpeed repository setup failed during installCyberPanelRepo"
                )
                preFlightsChecks.stdOut("[ERROR] LiteSpeed repository setup failed")
                os._exit(os.EX_SOFTWARE)

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

            install_utils.restore_selinux_contexts(
                '/etc/pdns',
                '/etc/powerdns',
                '/etc/dovecot',
                '/etc/postfix',
            )
        except:
            logging.InstallLog.writeToFile("[ERROR] fix_selinux_issue problem")

    def install_psmisc(self):
        self.stdOut("Install psmisc")
        self.install_package("psmisc")


    def update_settings_file(self, mysqlPassword, cyberpanel_password, mysql):
        """
        Update settings.py file with correct passwords
        mysqlPassword: Root MySQL password
        cyberpanel_password: CyberPanel database user password
        """
        logging.InstallLog.writeToFile("Updating settings.py!")

        # Validate passwords are not empty
        if not mysqlPassword or not cyberpanel_password:
            logging.InstallLog.writeToFile("ERROR: Empty passwords provided to update_settings_file")
            raise Exception("Cannot update settings with empty passwords")

        path = self.cyberPanelPath + "/CyberCP/settings.py"

        data = open(path, "r").readlines()

        writeDataToFile = open(path, "w")

        default_db_found = False
        rootdb_found = False

        in_default_db = False
        in_rootdb = False
        secret_key_replaced = False

        for items in data:
            # Only rewrite one top-level SECRET_KEY assignment. Matching any line that
            # contains SECRET_KEY also replaced comments and indented statements in the
            # env/file fallback block, which caused IndentationError on settings.py.
            if items.startswith('SECRET_KEY =') and not secret_key_replaced:
                SK = "SECRET_KEY = '%s'\n" % (install_utils.generate_pass(50))
                writeDataToFile.writelines(SK)
                secret_key_replaced = True
                continue

            # Track which database section we're in - more robust detection
            stripped_line = items.strip()

            # Detect database section start
            if "'default'" in stripped_line and ":" in stripped_line:
                in_default_db = True
                in_rootdb = False
                logging.InstallLog.writeToFile("Detected 'default' database section")
            elif "'rootdb'" in stripped_line and ":" in stripped_line:
                in_default_db = False
                in_rootdb = True
                logging.InstallLog.writeToFile("Detected 'rootdb' database section")
            elif stripped_line in ["},", "}"] or (stripped_line.startswith("}") and len(stripped_line) <= 2):
                # End of database section
                if in_default_db or in_rootdb:
                    logging.InstallLog.writeToFile(f"End of database section (default: {in_default_db}, rootdb: {in_rootdb})")
                in_default_db = False
                in_rootdb = False

            # Handle password replacement based on current database section
            if "'PASSWORD':" in items:
                if in_default_db and not default_db_found:
                    # This is the cyberpanel database password
                    new_line = "        'PASSWORD': '" + cyberpanel_password + "',\n"
                    writeDataToFile.writelines(new_line)
                    default_db_found = True
                    logging.InstallLog.writeToFile(f"✓ Set cyberpanel database password (length: {len(cyberpanel_password)})")
                elif in_rootdb and not rootdb_found:
                    # This is the root database password
                    new_line = "        'PASSWORD': '" + mysqlPassword + "',\n"
                    writeDataToFile.writelines(new_line)
                    rootdb_found = True
                    logging.InstallLog.writeToFile(f"✓ Set root database password (length: {len(mysqlPassword)})")
                else:
                    # Fallback - write original line
                    logging.InstallLog.writeToFile(f"⚠ Password line found but not in expected section (default: {in_default_db}, rootdb: {in_rootdb})")
                    writeDataToFile.writelines(items)
            elif mysql == 'Two':
                # Handle special MySQL Two configuration
                writeDataToFile.writelines(items)
            else:
                # Only rewrite MySQL HOST inside DATABASES. CSRF trusted origins also
                # contain 127.0.0.1 and must stay valid URL strings.
                if (in_default_db or in_rootdb) and '127.0.0.1' in items and 'HOST' in items:
                    writeDataToFile.writelines("        'HOST': 'localhost',\n")
                elif (in_default_db or in_rootdb) and items.find("'PORT':'3307'") > -1:
                    writeDataToFile.writelines("        'PORT': '',\n")
                else:
                    writeDataToFile.writelines(items)

        if self.distro == install_utils.ubuntu:
            os.fchmod(writeDataToFile.fileno(), stat.S_IRUSR | stat.S_IWUSR)

        writeDataToFile.close()

        # Verify both passwords were set
        if not default_db_found or not rootdb_found:
            error_msg = f"ERROR: Failed to update all database passwords. Default: {default_db_found}, Root: {rootdb_found}"
            logging.InstallLog.writeToFile(error_msg)
            raise Exception(error_msg)

        if self.remotemysql == 'ON':
            command = "sed -i 's|localhost|%s|g' %s" % (self.mysqlhost, path)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = "sed -i 's|root|%s|g' %s" % (self.mysqluser, path)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = "sed -i \"s|'PORT': ''|'PORT':'%s'|g\" %s" % (self.mysqlport, path)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        logging.InstallLog.writeToFile("settings.py updated successfully - both database passwords configured!")


    def download_install_CyberPanel(self, mysqlPassword, mysql):
        ##

        os.chdir(self.path)

        os.chdir('/usr/local')

        # Since cyberpanel.sh has already cloned the repository and we're running from it,
        # we simply need to clone a fresh copy to /usr/local/CyberCP for the application

        logging.InstallLog.writeToFile("Setting up CyberPanel application directory...")

        # Remove existing CyberCP directory if it exists
        if os.path.exists('/usr/local/CyberCP'):
            logging.InstallLog.writeToFile("Removing existing CyberCP directory...")
            shutil.rmtree('/usr/local/CyberCP')

        # Clone directly to /usr/local/CyberCP with explicit path
        logging.InstallLog.writeToFile("Cloning repository to /usr/local/CyberCP...")
        
        # Ensure the parent directory exists
        os.makedirs("/usr/local", exist_ok=True)
        
        # Determine the correct branch/tag/commit to clone
        branch_name = os.environ.get('CYBERPANEL_BRANCH', 'stable')
        clone_owner = install_utils.cyberpanel_github_owner()
        logging.InstallLog.writeToFile(
            "Cloning CyberCP from github.com/%s/cyberpanel (branch %s)"
            % (clone_owner, branch_name)
        )

        # Try multiple clone methods (fork first, then upstream)
        clone_commands = install_utils.build_cyberpanel_clone_commands(branch_name)
        
        clone_success = False
        for cmd in clone_commands:
            try:
                result = preFlightsChecks.call(cmd, self.distro, cmd, cmd, 1, 1, os.EX_OSERR)
                if result == 1 and os.path.exists('/usr/local/CyberCP'):
                    clone_success = True
                    break
            except:
                continue
        
        if not clone_success or not os.path.exists('/usr/local/CyberCP'):
            logging.InstallLog.writeToFile("[ERROR] All Git clone attempts failed!")
            preFlightsChecks.stdOut("[ERROR] All Git clone attempts failed!")
            
            # Try manual download as fallback
            logging.InstallLog.writeToFile("Attempting manual download as fallback...")
            
            download_url = None
            extract_dir = None
            for owner in install_utils.cyberpanel_github_owners_to_try():
                download_url, extract_dir = install_utils.build_cyberpanel_archive_download(
                    branch_name, owner=owner
                )
                logging.InstallLog.writeToFile(
                    "Trying archive download from github.com/%s/cyberpanel" % owner
                )
                break
            if not download_url:
                download_url, extract_dir = install_utils.build_cyberpanel_archive_download(
                    branch_name
                )
            
            command = f"wget -O /tmp/cyberpanel.zip {download_url}"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            command = "unzip /tmp/cyberpanel.zip -d /usr/local/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            command = f"mv /usr/local/{extract_dir} /usr/local/CyberCP"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            command = "rm -f /tmp/cyberpanel.zip"
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
            
            if not os.path.exists('/usr/local/CyberCP'):
                logging.InstallLog.writeToFile("[ERROR] Manual download also failed!")
                preFlightsChecks.stdOut("[ERROR] Manual download also failed!")
                sys.exit(1)

        logging.InstallLog.writeToFile("Successfully cloned repository to /usr/local/CyberCP")

        ##

        ### update password:

        if self.remotemysql == 'OFF':
            passFile = "/etc/cyberpanel/mysqlPassword"

            # Check if MySQL password file exists, create it if missing
            if not os.path.exists(passFile):
                logging.InstallLog.writeToFile("MySQL password file not found, creating it...")
                try:
                    # Ensure directory exists
                    os.makedirs('/etc/cyberpanel', exist_ok=True)
                    
                    # Use the stored MySQL root password
                    if hasattr(self, 'mysql_Root_password') and self.mysql_Root_password:
                        password = self.mysql_Root_password
                        # Create the password file
                        with open(passFile, 'w') as f:
                            f.write(password)
                        os.chmod(passFile, 0o600)
                        logging.InstallLog.writeToFile("MySQL password file created successfully")
                    else:
                        logging.InstallLog.writeToFile("ERROR: No MySQL root password available")
                        raise Exception("MySQL root password not available")
                except Exception as e:
                    logging.InstallLog.writeToFile(f"ERROR: Failed to create MySQL password file: {str(e)}")
                    raise Exception(f"Failed to create MySQL password file: {str(e)}")
            else:
                # Read existing password file
                try:
                    with open(passFile, 'r') as f:
                        data = f.read()
                    password = data.split('\n', 1)[0].strip()
                    if not password:
                        raise Exception("Empty password in file")
                except Exception as e:
                    logging.InstallLog.writeToFile(f"ERROR: Failed to read MySQL password file: {str(e)}")
                    raise Exception(f"Failed to read MySQL password file: {str(e)}")
        else:
            password = self.mysqlpassword

        ### Put correct mysql passwords in settings file!

        # This allows root/sudo users to be able to work with MySQL/MariaDB without hunting down the password like
        # all the other control panels allow
        # reference: https://oracle-base.com/articles/mysql/mysql-password-less-logins-using-option-files
        mysql_my_root_cnf = '/root/.my.cnf'
        # Include skip-ssl/ssl=0 so client does not require SSL (avoids ERROR 2026 when server has have_ssl=DISABLED)
        mysql_root_cnf_content = """
[client]
user=root
password="%s"
ssl=0
skip-ssl
""" % password

        with open(mysql_my_root_cnf, 'w') as f:
            f.write(mysql_root_cnf_content)
        os.chmod(mysql_my_root_cnf, 0o600)
        command = 'chown root:root %s' % mysql_my_root_cnf
        subprocess.call(shlex.split(command))

        logging.InstallLog.writeToFile("Updating /root/.my.cnf!")

        # Ensure system-wide MariaDB client uses no SSL (all installs: avoids ERROR 2026 on servers with SSL disabled)
        if self.remotemysql == 'OFF':
            self._ensure_mariadb_client_no_ssl()

        logging.InstallLog.writeToFile("Generating secure environment configuration!")

        # Determine the correct MySQL root password to use
        mysql_root_password = mysqlPassword if self.remotemysql == 'ON' else self.mysql_Root_password

        # For CentOS, we need to get the actual cyberpanel database password
        # which is different from the root password
        if self.distro == centos:
            # On CentOS, generate a separate password for cyberpanel database
            self.cyberpanel_db_password = install_utils.generate_pass()
        else:
            # On Ubuntu/Debian, the cyberpanel password is the same as root password
            self.cyberpanel_db_password = mysql_root_password

        # Update settings.py with correct passwords (no .env files for secrets)
        self.update_settings_file(mysql_root_password, self.cyberpanel_db_password, mysql)

        logging.InstallLog.writeToFile("Environment configuration generated successfully!")

        if self.remotemysql == 'ON':
            path = self.cyberPanelPath + "/CyberCP/settings.py"
            command = "sed -i 's|localhost|%s|g' %s" % (self.mysqlhost, path)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            # command = "sed -i 's|'mysql'|'%s'|g' %s" % (self.mysqldb, path)
            # preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = "sed -i 's|root|%s|g' %s" % (self.mysqluser, path)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            command = "sed -i \"s|'PORT': ''|'PORT':'%s'|g\" %s" % (self.mysqlport, path)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

        logging.InstallLog.writeToFile("settings.py updated!")

        # CyberCP venv + Django must exist before migrations (git clone leaves tree without deps)
        logging.InstallLog.writeToFile("Ensuring CyberCP virtualenv and Django dependencies...")
        preFlightsChecks.stdOut("Ensuring CyberCP Python virtual environment...")
        if not install_utils.ensure_cybercp_venv(log=1):
            logging.InstallLog.writeToFile(
                "FATAL: CyberCP venv/Django setup failed; cannot run migrations"
            )
            preFlightsChecks.stdOut(
                "FATAL: Could not install Django in /usr/local/CyberCP venv", 0
            )
            return False
        preFlightsChecks.stdOut("CyberCP virtual environment ready", 1)

        # Now run Django migrations since we're in /usr/local/CyberCP and database exists
        os.chdir("/usr/local/CyberCP")
        logging.InstallLog.writeToFile("Running Django migrations...")
        preFlightsChecks.stdOut("Running Django migrations...")

        # Clean any existing migration files first (except __init__.py and excluding virtual environment)
        logging.InstallLog.writeToFile("Cleaning existing migration files...")

        apps_with_migrations = install_utils.discover_cybercp_migration_apps()
        logging.InstallLog.writeToFile(
            "Migration cleanup for apps: %s" % ', '.join(apps_with_migrations)
        )

        # Clean migration files for each app (including emailDelivery/webmail)
        for app in apps_with_migrations:
            migration_dir = f"/usr/local/CyberCP/{app}/migrations"
            if os.path.exists(migration_dir):
                # Remove all .py files except __init__.py
                command = f"bash -c \"find {migration_dir} -name '*.py' ! -name '__init__.py' -delete 2>/dev/null || true\""
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                # Remove all .pyc files
                command = f"bash -c \"find {migration_dir} -name '*.pyc' -delete 2>/dev/null || true\""
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                # Remove __pycache__ directory
                command = f"bash -c \"rm -rf {migration_dir}/__pycache__ 2>/dev/null || true\""
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        logging.InstallLog.writeToFile("Migration cleanup completed")

        # Ensure virtual environment or system Python is available
        logging.InstallLog.writeToFile("Ensuring Python is available for migrations...")
        if not self.ensureVirtualEnvironmentSetup():
            logging.InstallLog.writeToFile("WARNING: No venv found; will try system Python")

        # Prefer CyberCP venv (Django lives there); fall back to system Python
        python_paths = []
        if os.path.isfile("/usr/local/CyberCP/bin/python"):
            python_paths.append("/usr/local/CyberCP/bin/python")
        python_paths.extend([
            "/usr/bin/python3",
            "/usr/local/bin/python3",
        ])
        if sys.executable and sys.executable not in python_paths:
            python_paths.append(sys.executable)

        python_path = None
        for path in python_paths:
            if not path:
                continue
            try:
                # Skip broken symlinks: resolve and require executable file
                if os.path.lexists(path):
                    resolved = os.path.realpath(path)
                    if not os.path.isfile(resolved) or not os.access(resolved, os.X_OK):
                        continue
                elif not os.path.isfile(path) or not os.access(path, os.X_OK):
                    continue
            except OSError:
                continue
            try:
                r = subprocess.run([path, "--version"], capture_output=True, text=True, timeout=5)
                if r.returncode == 0 and install_utils.cybercp_venv_has_django(path):
                    python_path = path
                    logging.InstallLog.writeToFile(f"Using Python at: {path}")
                    break
            except (FileNotFoundError, OSError, subprocess.SubprocessError):
                continue

        if not python_path:
            if install_utils.ensure_cybercp_venv(log=1):
                candidate = "/usr/local/CyberCP/bin/python"
                if install_utils.cybercp_venv_has_django(candidate):
                    python_path = candidate
                    logging.InstallLog.writeToFile(
                        "Using Python at: %s (after venv repair)" % candidate
                    )

        if not python_path:
            logging.InstallLog.writeToFile("ERROR: No working Python found for migrations!")
            preFlightsChecks.stdOut("ERROR: No working Python found!", 0)
            return False

        manage_py = "/usr/local/CyberCP/manage.py"
        if not os.path.isfile(manage_py):
            logging.InstallLog.writeToFile("ERROR: %s not found" % manage_py)
            preFlightsChecks.stdOut("ERROR: manage.py not found at %s" % manage_py, 0)
            return False

        # Create migrations in dependency order - loginSystem first since other apps depend on it
        logging.InstallLog.writeToFile("Creating migrations for loginSystem first...")
        command = f"{python_path} {manage_py} makemigrations loginSystem --noinput"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        # Now create migrations for all other apps
        logging.InstallLog.writeToFile("Creating migrations for all other apps...")
        command = f"{python_path} {manage_py} makemigrations --noinput"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        # Apply all migrations
        logging.InstallLog.writeToFile("Applying all migrations...")
        command = f"{python_path} {manage_py} migrate --noinput"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        # Ensure firewall (banned IPs) table exists so /firewall/#banned-ips works
        logging.InstallLog.writeToFile("Applying firewall migrations (firewall_bannedips)...")
        command = f"{python_path} {manage_py} migrate firewall --noinput"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        logging.InstallLog.writeToFile("Django migrations completed successfully!")
        preFlightsChecks.stdOut("Django migrations completed successfully!")

        if not os.path.exists("/usr/local/CyberCP/public"):
            os.mkdir("/usr/local/CyberCP/public")

        # Download CDN libraries before collectstatic runs
        self.downloadCDNLibraries()

        command = f"{python_path} {manage_py} collectstatic --noinput --clear --verbosity 0"
        preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)

        ## Merge static content into public/static for LiteSpeed (mv fails if public/static exists)
        static_root = "/usr/local/CyberCP/static"
        public_static = "/usr/local/CyberCP/public/static"
        static_sync_ok = False
        if os.path.isdir(static_root):
            try:
                if '/usr/local/CyberCP' not in sys.path:
                    sys.path.insert(0, '/usr/local/CyberCP')
                from plogical import panel_static_sync

                panel_static_sync.sync_static_root_to_public()
                static_sync_ok = True
                logging.InstallLog.writeToFile(
                    "Merged %s into %s via panel_static_sync" % (static_root, public_static)
                )
            except BaseException as sync_merge_err:
                logging.InstallLog.writeToFile(
                    "[WARNING] panel_static_sync merge failed, trying shell merge: %s" % sync_merge_err
                )
                os.chdir("/usr/local/CyberCP")
                if os.path.isdir(public_static):
                    command = "cp -a static/. public/static/ && rm -rf static"
                else:
                    command = "mv static /usr/local/CyberCP/public/"
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                static_sync_ok = os.path.isdir(public_static)
        else:
            logging.InstallLog.writeToFile(
                "No %s after collectstatic; using existing public/static if present" % static_root
            )
            static_sync_ok = os.path.isdir(public_static)

        if not static_sync_ok:
            logging.InstallLog.writeToFile(
                "[ERROR] public/static was not created after collectstatic/sync"
            )
            preFlightsChecks.stdOut("ERROR: Failed to sync panel static files to public/static", 0)
            return False

        try:
            if '/usr/local/CyberCP' not in sys.path:
                sys.path.insert(0, '/usr/local/CyberCP')
            from plogical import panel_static_sync

            if not panel_static_sync.ensure_litespeed_panel_static_complete():
                logging.InstallLog.writeToFile(
                    "[WARNING] public/static/webmail/webmail.js missing after collectstatic; "
                    "verify webmail static and LiteSpeed public/static."
                )
        except BaseException as sync_err:
            logging.InstallLog.writeToFile(
                "[WARNING] panel_static_sync after install (non-fatal): " + str(sync_err)
            )

        try:
            path = "/usr/local/CyberCP/version.txt"
            writeToFile = open(path, 'w')
            writeToFile.writelines('%s\n' % (VERSION))
            writeToFile.writelines(str(BUILD))
            writeToFile.close()
        except:
            pass

    def fixBaseTemplateMigrations(self):
        """
        Fix baseTemplate migrations to prevent NodeNotFoundError on AlmaLinux 9 and Ubuntu 24
        """
        try:
            # Ensure baseTemplate migrations directory exists
            migrations_dir = "/usr/local/CyberCP/baseTemplate/migrations"
            if not os.path.exists(migrations_dir):
                os.makedirs(migrations_dir)
                logging.InstallLog.writeToFile("Created baseTemplate migrations directory")

            # Create __init__.py if it doesn't exist
            init_file = os.path.join(migrations_dir, "__init__.py")
            if not os.path.exists(init_file):
                with open(init_file, 'w') as f:
                    f.write("")
                logging.InstallLog.writeToFile("Created baseTemplate migrations __init__.py")

            # Create 0001_initial.py if it doesn't exist
            initial_migration = os.path.join(migrations_dir, "0001_initial.py")
            if not os.path.exists(initial_migration):
                initial_content = '''# Generated by Django 3.2.25 on 2024-01-01 00:00

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='CyberPanelCosmetic',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('MainDashboardCSS', models.TextField(default='')),
            ],
        ),
        migrations.CreateModel(
            name='UserNotificationPreferences',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('backup_notification_dismissed', models.BooleanField(default=False, help_text='Whether user has dismissed the backup notification')),
                ('ai_scanner_notification_dismissed', models.BooleanField(default=False, help_text='Whether user has dismissed the AI scanner notification')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'User Notification Preferences',
                'verbose_name_plural': 'User Notification Preferences',
            },
        ),
        migrations.CreateModel(
            name='version',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=10)),
                ('build', models.IntegerField()),
            ],
        ),
    ]
'''
                with open(initial_migration, 'w') as f:
                    f.write(initial_content)
                logging.InstallLog.writeToFile("Created baseTemplate 0001_initial.py migration")

            # Create 0002_usernotificationpreferences.py if it doesn't exist
            notification_migration = os.path.join(migrations_dir, "0002_usernotificationpreferences.py")
            if not os.path.exists(notification_migration):
                notification_content = '''# Generated by Django 3.2.25 on 2024-01-01 00:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('baseTemplate', '0001_initial'),
        ('loginSystem', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='usernotificationpreferences',
            name='user',
            field=models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='notification_preferences', to='loginSystem.administrator'),
        ),
    ]
'''
                with open(notification_migration, 'w') as f:
                    f.write(notification_content)
                logging.InstallLog.writeToFile("Created baseTemplate 0002_usernotificationpreferences.py migration")

            # Set proper permissions
            command = "chown -R root:root " + migrations_dir
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            command = "chmod -R 755 " + migrations_dir
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            logging.InstallLog.writeToFile("baseTemplate migrations fixed successfully")
            preFlightsChecks.stdOut("baseTemplate migrations fixed successfully")

        except Exception as e:
            logging.InstallLog.writeToFile("Error fixing baseTemplate migrations: " + str(e))
            preFlightsChecks.stdOut("Warning: Could not fix baseTemplate migrations: " + str(e))

    def fixCyberPanelPermissions(self):

        ###### fix Core CyberPanel permissions

        command = "usermod -G lscpd,lsadm,nobody lscpd"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "usermod -G lscpd,lsadm,nogroup lscpd"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = r"find /usr/local/CyberCP -type d -exec chmod 0755 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = r"find /usr/local/CyberCP -type f -exec chmod 0644 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod -R 755 /usr/local/CyberCP/bin"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## change owner

        command = "chown -R root:root /usr/local/CyberCP"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ########### Fix LSCPD

        command = r"find /usr/local/lscp -type d -exec chmod 0755 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = r"find /usr/local/lscp -type f -exec chmod 0644 {} \;"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod -R 755 /usr/local/lscp/bin"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chmod -R 755 /usr/local/lscp/fcgi-bin"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## CRITICAL FIX: Restore public directory ownership after root:root override
        ## The public directory MUST be owned by lscpd for web server to serve files
        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## Ensure correct permissions: directories 755, files 644 (NO execute bit on static files!)
        command = r'find /usr/local/CyberCP/public/ -type d -exec chmod 755 {} \;'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = r'find /usr/local/CyberCP/public/ -type f -exec chmod 644 {} \;'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ## change owner

        command = "chown -R root:root /usr/local/lscp"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail"
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
                     '/usr/local/CyberCP/CLScript/CloudLinuxDomains.py',
                     '/usr/local/CyberCP/CLScript/CloudLinuxResellers.py', '/usr/local/CyberCP/CLScript/CloudLinuxAdmins.py',
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

        command = 'chmod 640 /usr/local/lscp/cyberpanel/logs/access.log'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        # Create complete SnappyMail directory structure early in installation
        command = 'mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        # Set proper ownership early
        command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        # Set proper permissions - make all data directories group writable
        command = "chmod -R 775 /usr/local/lscp/cyberpanel/snappymail/data/"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        # Ensure the web server user (nobody) can access the directories
        # Note: lscpd is already added to nobody group earlier in the installation
        command = "usermod -a -G lscpd nobody 2>/dev/null || true"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        # Fix SnappyMail public directory ownership early
        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail/data || true"
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        snappymailinipath = '/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/application.ini'

        command = 'chmod 600 /usr/local/CyberCP/public/snappymail.php'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        ###

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
            try:
                shutil.rmtree("/usr/local/CyberCP/public/phpmyadmin")
            except Exception:
                pass

            # Resolve phpMyAdmin version: CLI override (--phpmyadmin-version), else latest from API, else fallback
            phpmyadmin_version = getattr(preFlightsChecks, 'phpmyadmin_version', None) or ''
            phpmyadmin_version = (phpmyadmin_version or '').strip()
            if not phpmyadmin_version or not re.match(r'^\d+\.\d+\.\d+$', phpmyadmin_version):
                phpmyadmin_version = '5.2.3'
                try:
                    from plogical.versionFetcher import get_latest_phpmyadmin_version
                    latest_version = get_latest_phpmyadmin_version()
                    if latest_version and re.match(r'^\d+\.\d+\.\d+$', latest_version):
                        self.stdOut(f"Using latest phpMyAdmin version: {latest_version}", 1)
                        phpmyadmin_version = latest_version
                    else:
                        self.stdOut(f"Using fallback phpMyAdmin version: {phpmyadmin_version}", 1)
                except Exception as e:
                    self.stdOut(f"Failed to fetch latest phpMyAdmin version, using fallback: {e}", 1)
            else:
                self.stdOut(f"Using phpMyAdmin version: {phpmyadmin_version}", 1)

            self.stdOut("Installing phpMyAdmin...", 1)
            tarball = '/usr/local/CyberCP/public/phpmyadmin.tar.gz'
            command = (
                f'wget -q -O {tarball} '
                f'https://files.phpmyadmin.net/phpMyAdmin/{phpmyadmin_version}/phpMyAdmin-{phpmyadmin_version}-all-languages.tar.gz'
            )
            preFlightsChecks.call(command, self.distro, f'[download_install_phpmyadmin] {phpmyadmin_version}',
                                  command, 1, 0, os.EX_OSERR)
            if not os.path.isfile(tarball) or os.path.getsize(tarball) < 1000000:
                raise RuntimeError('phpMyAdmin download failed or file too small')
            command = 'tar -xzf /usr/local/CyberCP/public/phpmyadmin.tar.gz -C /usr/local/CyberCP/public/'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin] extract',
                                  command, 1, 0, os.EX_OSERR)
            import glob
            extracted = glob.glob('/usr/local/CyberCP/public/phpMyAdmin-*-all-languages')
            if not extracted:
                extracted = glob.glob('/usr/local/CyberCP/public/phpMyAdmin-*')
            if extracted:
                if os.path.exists('/usr/local/CyberCP/public/phpmyadmin'):
                    shutil.rmtree('/usr/local/CyberCP/public/phpmyadmin')
                os.rename(extracted[0], '/usr/local/CyberCP/public/phpmyadmin')
            else:
                command = 'mv /usr/local/CyberCP/public/phpMyAdmin-*-all-languages /usr/local/CyberCP/public/phpmyadmin'
                subprocess.call(command, shell=True)
            if not os.path.isdir('/usr/local/CyberCP/public/phpmyadmin'):
                raise RuntimeError('phpMyAdmin directory was not created after extract/mv')
            command = 'rm -f /usr/local/CyberCP/public/phpmyadmin.tar.gz'
            preFlightsChecks.call(command, self.distro, '[download_install_phpmyadmin] cleanup',
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

            os.makedirs('/usr/local/CyberCP/public/phpmyadmin/tmp', exist_ok=True)

            command = 'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin'
            preFlightsChecks.call(command, self.distro, '[chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin]',
                                  'chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin', 1, 0, os.EX_OSERR)

            if self.remotemysql == 'ON':
                command = "sed -i 's|'localhost'|'%s'|g' %s" % (
                    self.mysqlhost, '/usr/local/CyberCP/public/phpmyadmin/config.inc.php')
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = 'cp /usr/local/CyberCP/plogical/phpmyadminsignin.php /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            lpma_src = '/usr/local/CyberCP/plogical/lpma_policy_read.inc.php'
            lpma_dst = '/usr/local/CyberCP/public/phpmyadmin/lpma_policy_read.inc.php'
            if os.path.isfile(lpma_src):
                shutil.copy2(lpma_src, lpma_dst)

            if self.remotemysql == 'ON':
                command = "sed -i 's|localhost|%s|g' /usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php" % (
                    self.mysqlhost)
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Ensure signin file exists (idempotent; fixes 404 if plogical was not present earlier)
            signin_dest = '/usr/local/CyberCP/public/phpmyadmin/phpmyadminsignin.php'
            signin_src = '/usr/local/CyberCP/plogical/phpmyadminsignin.php'
            if not os.path.isfile(signin_dest) and os.path.isfile(signin_src):
                try:
                    shutil.copy2(signin_src, signin_dest)
                except Exception:
                    pass

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

            # Remove conflicting dovecot packages first
            try:
                if self.distro in [centos, cent8, openeuler]:
                    # CentOS 8, AlmaLinux 8/9/10, RockyLinux 8/9, RHEL 8/9, CloudLinux 8/9 - use dnf
                    preFlightsChecks.call('dnf remove -y dovecot dovecot-*', self.distro, 
                                        'Remove conflicting dovecot packages', 
                                        'Remove conflicting dovecot packages', 1, 0, os.EX_OSERR)
                else:
                    # Ubuntu 24.04/22.04/20.04, Debian 13/12/11 - use apt
                    preFlightsChecks.call('apt-get remove -y dovecot dovecot-*', self.distro, 
                                        'Remove conflicting dovecot packages', 
                                        'Remove conflicting dovecot packages', 1, 0, os.EX_OSERR)
            except:
                pass  # Continue if removal fails

            if self.distro in (centos, cent8):
                clAPVersion = FetchCloudLinuxAlmaVersionVersion()
                type = clAPVersion.split('-')[0]
                version = int(clAPVersion.split('-')[1])
                if type == 'al' and version >= 90:
                    command = 'dnf install -y dovecot dovecot-mysql dovecot-pigeonhole'
                else:
                    command = 'dnf install --enablerepo=gf-plus dovecot23 dovecot23-mysql dovecot23-pigeonhole -y --allowerasing'
            elif self.distro == openeuler:
                dovecot_commands = [
                    'dnf install dovecot dovecot-mysql -y --skip-broken --nobest',
                    'dnf install dovecot23 dovecot23-mysql -y --skip-broken --nobest',
                    'dnf install dovecot -y --skip-broken --nobest'
                ]

                dovecot_installed = False
                for cmd in dovecot_commands:
                    try:
                        preFlightsChecks.call(cmd, self.distro, cmd, cmd, 1, 1, os.EX_OSERR, True)
                        if os.path.exists('/etc/dovecot') or os.path.exists('/usr/sbin/dovecot'):
                            dovecot_installed = True
                            break
                    except Exception:
                        continue

                if not dovecot_installed:
                    command = 'dnf install dovecot -y --skip-broken --nobest --allowerasing'
                    preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
            else:
                # Ubuntu 24.04/22.04/20.04, Debian 13/12/11
                command = 'DEBIAN_FRONTEND=noninteractive apt-get -y install dovecot-mysql dovecot-imapd dovecot-pop3d dovecot-sieve dovecot-managesieved'

            if self.distro != openeuler:
                preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR, True)
            
            # Ensure Dovecot service is properly configured
            self.manage_service('dovecot', 'enable')
            self.manage_service('dovecot', 'start')
            
            # Verify Dovecot installation
            if os.path.exists('/usr/sbin/dovecot') or os.path.exists('/usr/bin/dovecot'):
                logging.InstallLog.writeToFile("Dovecot installation successful")
            else:
                logging.InstallLog.writeToFile("[WARNING] Dovecot binary not found after installation")

        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [install_postfix_dovecot]")
            return 0

        return 1

    def setup_email_Passwords(self, mysqlPassword, mysql):
        try:
            # Ensure mysqlPassword is not None
            if mysqlPassword is None:
                mysqlPassword = self.mysql_Root_password
                logging.InstallLog.writeToFile("Warning: mysqlPassword was None, using mysql_Root_password")

            logging.InstallLog.writeToFile("Setting up authentication for Postfix and Dovecot...")

            install_dir = os.path.dirname(os.path.abspath(__file__))
            email_cfg_dir = os.path.join(install_dir, "email-configs-one")

            def _email_cfg(name):
                return os.path.join(email_cfg_dir, name)

            mysql_virtual_domains = _email_cfg("mysql-virtual_domains.cf")
            mysql_virtual_forwardings = _email_cfg("mysql-virtual_forwardings.cf")
            mysql_virtual_mailboxes = _email_cfg("mysql-virtual_mailboxes.cf")
            mysql_virtual_email2email = _email_cfg("mysql-virtual_email2email.cf")
            dovecotmysql = _email_cfg("dovecot-sql.conf.ext")

            for cfg_path in (
                dovecotmysql,
                mysql_virtual_domains,
                mysql_virtual_forwardings,
                mysql_virtual_mailboxes,
                mysql_virtual_email2email,
            ):
                if not os.path.isfile(cfg_path):
                    raise FileNotFoundError(
                        "Missing email template: %s (expected under %s)"
                        % (cfg_path, email_cfg_dir)
                    )

            ### update password:

            data = open(dovecotmysql, "r").readlines()

            writeDataToFile = open(dovecotmysql, "w")

            if mysql == 'Two':
                dataWritten = "connect = host=127.0.0.1 dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3307\n"
            else:
                dataWritten = "connect = host=localhost dbname=cyberpanel user=cyberpanel password=" + mysqlPassword + " port=3306\n"

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

            install_dir = os.path.dirname(os.path.abspath(__file__))
            email_cfg_dir = os.path.join(install_dir, "email-configs-one")

            def _email_cfg(name):
                return os.path.join(email_cfg_dir, name)

            mysql_virtual_domains = "/etc/postfix/mysql-virtual_domains.cf"
            mysql_virtual_forwardings = "/etc/postfix/mysql-virtual_forwardings.cf"
            mysql_virtual_mailboxes = "/etc/postfix/mysql-virtual_mailboxes.cf"
            mysql_virtual_email2email = "/etc/postfix/mysql-virtual_email2email.cf"
            main = "/etc/postfix/main.cf"
            master = "/etc/postfix/master.cf"
            dovecot = "/etc/dovecot/dovecot.conf"
            dovecotmysql = "/etc/dovecot/dovecot-sql.conf.ext"
            
            # Ensure dovecot directory exists
            os.makedirs("/etc/dovecot", exist_ok=True)
            
            # Also ensure dovecot conf.d directory exists
            os.makedirs("/etc/dovecot/conf.d", exist_ok=True)
            
            # Check if Dovecot is installed before proceeding
            if not os.path.exists('/usr/sbin/dovecot') and not os.path.exists('/usr/bin/dovecot'):
                logging.InstallLog.writeToFile("[ERROR] Dovecot not installed, cannot configure")
                return 0

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

                self.centos_lib_dir_to_ubuntu(_email_cfg("master.cf"), "/usr/libexec/", "/usr/lib/")
                self.centos_lib_dir_to_ubuntu(_email_cfg("main.cf"), "/usr/libexec/postfix",
                                              "/usr/lib/postfix/sbin")

            ########### Copy config files

            shutil.copy(_email_cfg("mysql-virtual_domains.cf"), "/etc/postfix/mysql-virtual_domains.cf")
            shutil.copy(_email_cfg("mysql-virtual_forwardings.cf"),
                        "/etc/postfix/mysql-virtual_forwardings.cf")
            shutil.copy(_email_cfg("mysql-virtual_mailboxes.cf"), "/etc/postfix/mysql-virtual_mailboxes.cf")
            shutil.copy(_email_cfg("mysql-virtual_email2email.cf"),
                        "/etc/postfix/mysql-virtual_email2email.cf")
            shutil.copy(_email_cfg("main.cf"), main)
            shutil.copy(_email_cfg("master.cf"), master)
            # Copy Dovecot configuration files with fallback
            try:
                shutil.copy(_email_cfg("dovecot.conf"), dovecot)
                shutil.copy(_email_cfg("dovecot-sql.conf.ext"), dovecotmysql)
            except FileNotFoundError:
                # Fallback: create basic dovecot.conf if template not found
                logging.InstallLog.writeToFile("[WARNING] Dovecot config templates not found, creating basic configuration")
                
                # Create basic dovecot.conf
                with open(dovecot, 'w') as f:
                    f.write('''protocols = imap pop3
log_timestamp = "%Y-%m-%d %H:%M:%S "

ssl_cert = <cert.pem
ssl_key = <key.pem

mail_plugins = zlib

namespace {
    type = private
    separator = .
    prefix = INBOX.
    inbox = yes
}

service auth {
    unix_listener auth-master {
        mode = 0600
        user = vmail
    }

    unix_listener /var/spool/postfix/private/auth {
        mode = 0666
        user = postfix
        group = postfix
    }

    user = root
}

service auth-worker {
    user = root
}

protocol lda {
    log_path = /home/vmail/dovecot-deliver.log
    auth_socket_path = /var/run/dovecot/auth-master
    postmaster_address = postmaster@example.com

    mail_plugins = zlib
}

protocol pop3 {
    pop3_uidl_format = %08Xu%08Xv
    mail_plugins = $mail_plugins zlib
}

protocol imap {
    mail_plugins = $mail_plugins zlib imap_zlib
}

passdb {
    driver = sql
    args = /etc/dovecot/dovecot-sql.conf.ext
}

userdb {
    driver = sql
    args = /etc/dovecot/dovecot-sql.conf.ext
}

plugin {
  zlib_save = gz
  zlib_save_level = 6
}

service stats {
    unix_listener stats-reader {
        user = vmail
        group = vmail
        mode = 0660
    }
    unix_listener stats-writer {
        user = vmail
        group = vmail
        mode = 0660
    }
}
''')
                
                # Create basic dovecot-sql.conf.ext
                with open(dovecotmysql, 'w') as f:
                    f.write(f'''# Database driver: mysql, pgsql, sqlite
driver = mysql

# Database connection string
connect = host=localhost dbname=cyberpanel user=cyberpanel password={self.mysqlPassword}

# Default password scheme
default_pass_scheme = MD5-CRYPT

# SQL query to get password
password_query = SELECT email as user, password FROM mail_users WHERE email='%u';

# SQL query to get user info
user_query = SELECT email as user, password, 'vmail' as uid, 'vmail' as gid, '/home/vmail/%d/%n' as home FROM mail_users WHERE email='%u';
''')
            
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

            command = 'chgrp dovecot /etc/dovecot/dovecot-sql.conf.ext'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'chmod o= /etc/dovecot/dovecot-sql.conf.ext'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ################################### Restart dovecot

            self.manage_service('dovecot', 'enable')
            self.manage_service('dovecot', 'start')
            
            # Verify Dovecot service is running
            if self.manage_service('dovecot', 'status') == 0:
                logging.InstallLog.writeToFile("Dovecot service started successfully")
            else:
                logging.InstallLog.writeToFile("[WARNING] Dovecot service may not be running properly")

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

            install_utils.restore_selinux_contexts('/etc/postfix', '/etc/dovecot')
            logging.InstallLog.writeToFile("Postfix and Dovecot configured")
        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [setup_postfix_dovecot_config]")
            return 0

        return 1

    def downoad_and_install_raindloop(self):
        try:
            if not os.path.exists("/usr/local/CyberCP/public"):
                os.mkdir("/usr/local/CyberCP/public")

            # Require a real entrypoint — an empty or removed tree must be reinstalled.
            if os.path.isfile("/usr/local/CyberCP/public/snappymail/index.php"):
                return 0
            if os.path.isdir("/usr/local/CyberCP/public/snappymail"):
                shutil.rmtree("/usr/local/CyberCP/public/snappymail", ignore_errors=True)

            # Version: CLI override (--snappymail-version), then latest from API, else class default
            snappy_ver = getattr(preFlightsChecks, 'snappymail_version', None) or ''
            snappy_ver = (snappy_ver or '').strip()
            if not snappy_ver or not re.match(r'^\d+\.\d+(\.\d+)?$', snappy_ver):
                try:
                    from plogical.versionFetcher import get_latest_snappymail_version
                    latest = get_latest_snappymail_version()
                    if latest and re.match(r'^\d+\.\d+', latest):
                        snappy_ver = latest
                    else:
                        snappy_ver = preFlightsChecks.SnappyVersion
                except Exception:
                    snappy_ver = preFlightsChecks.SnappyVersion
            self.stdOut("Using SnappyMail version: %s" % snappy_ver, 1)

            os.chdir("/usr/local/CyberCP/public")

            command = 'wget https://github.com/the-djmaze/snappymail/releases/download/v%s/snappymail-%s.zip' % (snappy_ver, snappy_ver)

            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            #############

            command = 'unzip snappymail-%s.zip -d /usr/local/CyberCP/public/snappymail' % (snappy_ver,)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            try:
                os.remove("snappymail-%s.zip" % (snappy_ver,))
            except:
                pass

            #######

            os.chdir("/usr/local/CyberCP/public/snappymail")

            command = r'find . -type d -exec chmod 755 {} \;'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            #############

            command = r'find . -type f -exec chmod 644 {} \;'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ######

            # Create SnappyMail data directories with proper structure
            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Set proper ownership for SnappyMail data directories
            command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Set proper permissions for SnappyMail data directories (group writable)
            command = "chmod -R 775 /usr/local/lscp/cyberpanel/snappymail/data/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Ensure web server users are in the lscpd group for access
            command = "usermod -a -G lscpd nobody 2>/dev/null || true"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Fix SnappyMail public directory ownership immediately after creation
            command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail/data || true"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ### Enable sub-folders

            command = "mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

#             labsPath = '/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/application.ini'
#
#             labsData = """[labs]
# imap_folder_list_limit = 0
# autocreate_system_folders = On
# """
#
#             # writeToFile = open(labsPath, 'a')
#             # writeToFile.write(labsData)
#             # writeToFile.close()
#
#             iPath = os.listdir('/usr/local/CyberCP/public/snappymail/snappymail/v/')
#
#             path = "/usr/local/CyberCP/public/snappymail/snappymail/v/%s/include.php" % (iPath[0])
#
#             data = open(path, 'r').readlines()
#             writeToFile = open(path, 'w')
#
#             for items in data:
#                 if items.find("$sCustomDataPath = '';") > -1:
#                     writeToFile.writelines(
#                         "			$sCustomDataPath = '/usr/local/lscp/cyberpanel/snappymail/data';\n")
#                 else:
#                     writeToFile.writelines(items)
#
#             writeToFile.close()
#
#             includeFileOldPath = '/usr/local/CyberCP/public/snappymail/_include.php'
#             includeFileNewPath = '/usr/local/CyberCP/public/snappymail/include.php'
#
#             if os.path.exists(includeFileOldPath):
#                 writeToFile = open(includeFileOldPath, 'a')
#                 writeToFile.write("\ndefine('APP_DATA_FOLDER_PATH', '/usr/local/lscp/cyberpanel/snappymail/data/');\n")
#                 writeToFile.close()
#
#             command = 'mv %s %s' % (includeFileOldPath, includeFileNewPath)
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             #command = "sed -i 's|autocreate_system_folders = Off|autocreate_system_folders = On|g' %s" % (labsPath)
#             command = "sed -i 's|verify_certificate = On|verify_certificate = Off|g' %s" % (labsPath)
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             ### now download and install actual plugin
#
#             command = f'mkdir /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/plugins/mailbox-detect'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             command = f'chmod 700 /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/plugins/mailbox-detect'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             command = f'chmod 700 /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/plugins/mailbox-detect'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             command = f'wget -O /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/plugins/mailbox-detect/index.php https://raw.githubusercontent.com/the-djmaze/snappymail/master/plugins/mailbox-detect/index.php'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             command = f'chmod 644 /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/plugins/mailbox-detect/index.php'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             command = f'chown lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/plugins/mailbox-detect/index.php'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             ### Enable plugins and enable mailbox creation plugin
#
#             labsDataLines = open(labsPath, 'r').readlines()
#             PluginsActivator = 0
#             WriteToFile = open(labsPath, 'w')
#             for lines in labsDataLines:
#                 if lines.find('[plugins]') > -1:
#                     PluginsActivator = 1
#                     WriteToFile.write(lines)
#                 elif PluginsActivator and lines.find('enable = ') > -1:
#                     WriteToFile.write(f'enable = On\n')
#                 elif PluginsActivator and lines.find('enabled_list = ') > -1:
#                     WriteToFile.write(f'enabled_list = "mailbox-detect"\n')
#                 elif PluginsActivator == 1 and lines.find('[defaults]') > -1:
#                     PluginsActivator = 0
#                     WriteToFile.write(lines)
#                 else:
#                     WriteToFile.write(lines)
#             WriteToFile.close()
#
#             ## enable auto create in the enabled plugin
#             PluginsFilePath = '/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/plugin-mailbox-detect.json'
#
#             WriteToFile = open(PluginsFilePath, 'w')
#             WriteToFile.write("""{
#     "plugin": {
#         "autocreate_system_folders": true
#     }
# }
# """)
#             WriteToFile.close()
#
#             command = f'chown lscpd:lscpd {PluginsFilePath}'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
#
#             command = f'chmod 600 {PluginsFilePath}'
#             preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            bundled_sm_src = os.path.join(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                'snappymail_cyberpanel.php'
            )
            bundled_sm_dst = '/usr/local/CyberCP/snappymail_cyberpanel.php'
            if os.path.isfile(bundled_sm_src):
                shutil.copy2(bundled_sm_src, bundled_sm_dst)
            else:
                command = (
                    'wget -O %s https://raw.githubusercontent.com/the-djmaze/snappymail/master/integrations/cyberpanel/install.php'
                    % bundled_sm_dst
                )
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                if os.path.isfile(bundled_sm_dst):
                    try:
                        with open(bundled_sm_dst, 'r', encoding='utf-8', errors='replace') as smf:
                            sm_helper = smf.read()
                        sm_helper = sm_helper.replace(
                            '/usr/local/lscp/cyberpanel/rainloop/data/',
                            '/usr/local/lscp/cyberpanel/snappymail/data/'
                        )
                        with open(bundled_sm_dst, 'w', encoding='utf-8') as smf:
                            smf.write(sm_helper)
                    except BaseException:
                        pass

            snappy_php = install_utils.resolve_lsphp_binary('php')
            if not snappy_php:
                raise FileNotFoundError(
                    'No LiteSpeed PHP binary found for SnappyMail integration (expected lsphp82+ under /usr/local/lsws/)'
                )
            command = '%s /usr/local/CyberCP/snappymail_cyberpanel.php' % snappy_php
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            include_sm = '/usr/local/CyberCP/public/snappymail/include.php'
            if os.path.isfile(include_sm):
                try:
                    with open(include_sm, 'r', encoding='utf-8', errors='replace') as incf:
                        inc_body = incf.read()
                    inc_body = inc_body.replace(
                        '/usr/local/lscp/cyberpanel/rainloop/data',
                        '/usr/local/lscp/cyberpanel/snappymail/data'
                    )
                    with open(include_sm, 'w', encoding='utf-8') as incf:
                        incf.write(inc_body)
                except BaseException:
                    pass

            try:
                from plogical.snappymail_plugin_utilities import install_and_enable_list_unsubscribe_header_plugin
                if install_and_enable_list_unsubscribe_header_plugin():
                    logging.InstallLog.writeToFile("SnappyMail list-unsubscribe-header plugin installed and enabled")
            except BaseException as plug_msg:
                logging.InstallLog.writeToFile("Warning: list-unsubscribe SnappyMail plugin: " + str(plug_msg), 0)


        except BaseException as msg:
            logging.InstallLog.writeToFile('[ERROR] ' + str(msg) + " [downoad_and_install_snappymail]")
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
            ssh_config = '/etc/ssh/sshd_config'
            if not os.path.isfile(ssh_config):
                self.install_package('openssh-server')
            if not os.path.isfile(ssh_config):
                return '22'
            sshData = subprocess.check_output(shlex.split('cat ' + ssh_config)).decode("utf-8").split('\n')

            for items in sshData:
                if items.find('Port') > -1:
                    if items[0] == 0:
                        pass
                    else:
                        return items.split(' ')[1]

            return '22'
        except BaseException as msg:
            return '22'

    def installFirewalld(self):

        if self.distro == ubuntu or self.distro == debian12:
            self.removeUfw()

        try:
            preFlightsChecks.stdOut("Enabling Firewall!")

            self.install_package("firewalld")

            ######
            if self.distro == centos:
                # Not available in ubuntu/debian
                self.manage_service('dbus', 'restart')
            elif self.distro == debian12:
                # For Debian 12, ensure dbus is running for firewalld
                self.manage_service('dbus', 'start')
                self.manage_service('dbus', 'enable')

            # Restart systemd-logind on all systems
            self.manage_service('systemd-logind', 'restart')

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

            install_dir = os.path.dirname(os.path.abspath(__file__))
            lscp_archive = os.path.join(install_dir, "lscp.tar.gz")
            if not os.path.isfile(lscp_archive):
                alt = os.path.join(self.cwd or "", "install", "lscp.tar.gz")
                if os.path.isfile(alt):
                    lscp_archive = alt
                else:
                    logging.InstallLog.writeToFile(
                        "[ERROR] lscp.tar.gz not found under %s" % install_dir
                    )
                    preFlightsChecks.stdOut("ERROR: lscp.tar.gz missing from install directory", 0)
                    return 0

            if self.distro == ubuntu:
                self.install_package("gcc g++ make autoconf rcs")
            else:
                self.install_package("gcc gcc-c++ make autoconf glibc")

            if self.distro == ubuntu:
                self.install_package("libpcre3 libpcre3-dev openssl libexpat1 libexpat1-dev libgeoip-dev zlib1g zlib1g-dev libudns-dev whichman curl")
            elif self.is_almalinux10():
                # AlmaLinux 10 / EL10: pcre-devel was removed; use pcre2-devel
                self.install_package("pcre2-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel")
            else:
                self.install_package("pcre-devel openssl-devel expat-devel geoip-devel zlib-devel udns-devel")

            command = 'tar zxf %s -C /usr/local/' % shlex.quote(lscp_archive)
            preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)

            ###

            lscpdPath = '/usr/local/lscp/bin/lscpd'

            # if subprocess.check_output('uname -a').decode("utf-8").find("aarch64") == -1:
            #     lscpdPath = '/usr/local/lscp/bin/lscpd'
            #
            #     lscpdSelection = 'lscpd-0.3.1'
            #     if os.path.exists('/etc/lsb-release'):
            #         result = open('/etc/lsb-release', 'r').read()
            #         if result.find('22.04') > -1 or result.find('24.04') > -1:
            #             lscpdSelection = 'lscpd.0.4.0'
            # else:
            #     lscpdSelection = 'lscpd.aarch64'

            try:
                try:
                    result = subprocess.run('uname -a', capture_output=True, universal_newlines=True, shell=True)
                except:
                    result = subprocess.run('uname -a', stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, shell=True)

                if result.stdout.find('aarch64') == -1:
                    lscpdSelection = 'lscpd-0.3.1'
                    if os.path.exists('/etc/lsb-release'):
                        result = open('/etc/lsb-release', 'r').read()
                        if result.find('22.04') > -1 or result.find('24.04') > -1:
                            lscpdSelection = 'lscpd.0.4.0'
                    # AlmaLinux/RHEL 9 and 10: lscpd.0.4.0 (el9 binary on el10; origin/v2.4.5)
                    try:
                        cl_al_ver = FetchCloudLinuxAlmaVersionVersion()
                        if cl_al_ver in ('al-93', 'al-100'):
                            lscpdSelection = 'lscpd.0.4.0'
                    except Exception:
                        pass
                    if os.path.exists('/etc/os-release'):
                        with open('/etc/os-release', 'r') as f:
                            osrel = f.read()
                        if (('VERSION_ID="9"' in osrel or 'VERSION_ID="10"' in osrel or
                             'VERSION_ID="9.' in osrel or 'VERSION_ID="10.' in osrel) and
                                ('AlmaLinux' in osrel or 'Rocky' in osrel or 'Red Hat' in osrel or
                                 'CentOS' in osrel)):
                            lscpdSelection = 'lscpd.0.4.0'
                else:
                    lscpdSelection = 'lscpd.aarch64'

            except:

                lscpdSelection = 'lscpd-0.3.1'
                if os.path.exists('/etc/lsb-release'):
                    result = open('/etc/lsb-release', 'r').read()
                    if result.find('22.04') > -1 or result.find('24.04') > -1:
                        lscpdSelection = 'lscpd.0.4.0'
                try:
                    cl_al_ver = FetchCloudLinuxAlmaVersionVersion()
                    if cl_al_ver in ('al-93', 'al-100'):
                        lscpdSelection = 'lscpd.0.4.0'
                except Exception:
                    pass


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

            if subprocess.run('id -u lscpd >/dev/null 2>&1', shell=True).returncode != 0:
                if self.is_centos_family():
                    command = 'adduser lscpd -M -d /usr/local/lscp'
                else:
                    command = 'useradd lscpd -M -d /usr/local/lscp'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            else:
                logging.InstallLog.writeToFile("lscpd system user already exists; skipping useradd")

            if self.is_centos_family():
                command = 'getent group lscpd >/dev/null || groupadd lscpd'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR, True)
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
            # lscpd is the WSGI backend. OpenLiteSpeed owns the public panel port
            # (usually 8090) and proxies to 127.0.0.1:5003. Writing *:8090 here
            # makes lscpd and OLS fight for the same socket, so lscpd fails and
            # the panel returns HTTP 503.
            backend_bind = "127.0.0.1:5003"
            writeToFile.write(backend_bind)
            writeToFile.close()

        except:
            return 0

    def setupPythonWSGI(self):
        try:
            preFlightsChecks.stdOut("Setting up Python WSGI-LSAPI with optimized compilation...", 1)
            
            # Ensure virtual environment is properly set up
            self.ensureVirtualEnvironmentSetup()
            
            # Upgrade pip to latest version for better package compatibility
            self.upgradePip()

            # Determine the correct Python path
            python_paths = [
                "/usr/local/CyberCP/bin/python",
                "/usr/local/CyberPanel/bin/python",
                "/usr/bin/python3",
                "/usr/local/bin/python3"
            ]
            
            python_path = None
            for path in python_paths:
                if os.path.exists(path):
                    python_path = path
                    preFlightsChecks.stdOut(f"Using Python at: {python_path}", 1)
                    break
            
            if not python_path:
                preFlightsChecks.stdOut("ERROR: No Python executable found for WSGI setup", 0)
                preFlightsChecks.stdOut("Attempting to create virtual environment symlink...", 1)
                
                # Try to create symlink for compatibility
                if os.path.exists('/usr/local/CyberCP/bin/python') and not os.path.exists('/usr/local/CyberPanel'):
                    try:
                        os.symlink('/usr/local/CyberCP', '/usr/local/CyberPanel')
                        python_path = "/usr/local/CyberPanel/bin/python"
                        preFlightsChecks.stdOut(f"Created symlink, using Python at: {python_path}", 1)
                    except Exception as e:
                        preFlightsChecks.stdOut(f"Failed to create symlink: {str(e)}", 0)
                        return 0
                else:
                    return 0

            command = "wget http://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            command = "tar xf wsgi-lsapi-2.1.tgz"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir("wsgi-lsapi-2.1")

            command = f"{python_path} ./configure.py"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Fix Makefile to use proper optimization flags to avoid _FORTIFY_SOURCE warnings
            self._fixWSGIMakefile()

            # Compile with proper optimization flags
            command = "make clean"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            command = "make"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if not os.path.exists('/usr/local/CyberCP/bin/'):
                os.mkdir('/usr/local/CyberCP/bin/')

            command = "cp lswsgi /usr/local/CyberCP/bin/"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Set proper permissions
            command = "chmod +x /usr/local/CyberCP/bin/lswsgi"
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            os.chdir(self.cwd)
            preFlightsChecks.stdOut("WSGI-LSAPI compiled successfully with optimized flags", 1)

        except Exception as e:
            preFlightsChecks.stdOut(f"WSGI setup error: {str(e)}", 0)
            return 0

    def ensureVirtualEnvironmentSetup(self):
        """Ensure virtual environment is properly set up and accessible"""
        try:
            # Check multiple possible virtual environment locations (prefer CyberCP - app path)
            venv_paths = [
                '/usr/local/CyberCP/bin/python',
                '/usr/local/CyberPanel/bin/python',
                '/usr/local/CyberPanel-venv/bin/python'
            ]
            
            found_venv = None
            for path in venv_paths:
                if os.path.exists(path):
                    found_venv = path
                    preFlightsChecks.stdOut(f"Virtual environment found at: {path}", 1)
                    break
            
            if not found_venv:
                preFlightsChecks.stdOut("No virtual environment found in expected locations", 0)
                return False
            
            # Create symlinks for compatibility if needed
            if found_venv == '/usr/local/CyberCP/bin/python':
                if not os.path.exists('/usr/local/CyberPanel/bin/python'):
                    if not os.path.exists('/usr/local/CyberPanel'):
                        preFlightsChecks.stdOut("Creating CyberPanel symlink for compatibility", 1)
                        os.symlink('/usr/local/CyberCP', '/usr/local/CyberPanel')
                    else:
                        preFlightsChecks.stdOut("CyberPanel directory exists but Python not found", 0)
                        return False
            
            # Test if Python is executable
            try:
                result = os.system(f"{found_venv} --version > /dev/null 2>&1")
                if result != 0:
                    preFlightsChecks.stdOut(f"Python at {found_venv} is not executable", 0)
                    return False
            except Exception as e:
                preFlightsChecks.stdOut(f"Error testing Python executable: {str(e)}", 0)
                return False
                
            return True
                
        except Exception as e:
            preFlightsChecks.stdOut(f"Error setting up virtual environment: {str(e)}", 0)
            return False

    def upgradePip(self):
        """Upgrade pip to latest version for better package compatibility"""
        try:
            preFlightsChecks.stdOut("Upgrading pip to latest version...", 1)
            
            # Determine the correct Python path
            python_paths = [
                "/usr/local/CyberCP/bin/python",
                "/usr/local/CyberPanel/bin/python",
                "/usr/bin/python3",
                "/usr/local/bin/python3"
            ]
            
            python_path = None
            for path in python_paths:
                if os.path.exists(path):
                    python_path = path
                    break
            
            if not python_path:
                preFlightsChecks.stdOut("No Python executable found for pip upgrade", 0)
                return False
            
            # Upgrade pip and essential packages
            upgrade_command = f"{python_path} -m pip install --upgrade pip setuptools wheel packaging"
            result = preFlightsChecks.call(upgrade_command, self.distro, "Upgrade pip", upgrade_command, 1, 0, os.EX_OSERR)
            
            if result == 1:
                preFlightsChecks.stdOut("pip upgraded successfully", 1)
                return True
            else:
                preFlightsChecks.stdOut("WARNING: pip upgrade failed, continuing with current version", 0)
                return False
                
        except Exception as e:
            preFlightsChecks.stdOut(f"Error upgrading pip: {str(e)}", 0)
            return False

    def _fixWSGIMakefile(self):
        """Fix the Makefile to use proper compiler optimization flags"""
        try:
            makefile_path = "Makefile"
            
            if not os.path.exists(makefile_path):
                preFlightsChecks.stdOut("Makefile not found, skipping optimization fix", 1)
                return
            
            # Read the Makefile
            with open(makefile_path, 'r') as f:
                content = f.read()
            
            # Fix compiler flags to avoid _FORTIFY_SOURCE warnings
            # Replace -O0 -g3 with -O2 -g to satisfy _FORTIFY_SOURCE
            content = content.replace('-O0 -g3', '-O2 -g')
            
            # Ensure we have proper optimization flags
            if 'CFLAGS' in content and '-O2' not in content:
                content = content.replace('CFLAGS =', 'CFLAGS = -O2')
            
            # Write the fixed Makefile
            with open(makefile_path, 'w') as f:
                f.write(content)
            
            preFlightsChecks.stdOut("Makefile optimized for proper compilation", 1)
            
        except Exception as e:
            preFlightsChecks.stdOut(f"Warning: Could not optimize Makefile: {str(e)}", 1)


    def ensureCyberPanelPhpmyadminOls(self):
        """Write OLS vhost so /phpmyadmin/ runs via lsphp on panel port (not Django download)."""
        try:
            from plogical.cyberpanelOlsPhpmyadmin import ensure_cyberpanel_phpmyadmin_ols
            preFlightsChecks.stdOut("Configuring OpenLiteSpeed phpMyAdmin PHP contexts...", 1)
            ensure_cyberpanel_phpmyadmin_ols(restart=True, verify=True)
            # OLS now owns :8090. Restart lscpd so it binds 127.0.0.1:5003
            # instead of racing OLS for the public port.
            preFlightsChecks.call(
                'systemctl restart lscpd',
                self.distro,
                'systemctl restart lscpd',
                'systemctl restart lscpd',
                0,
                0,
                os.EX_OSERR,
            )
            preFlightsChecks.stdOut("phpMyAdmin OLS configuration applied", 1)
            return True
        except Exception as e:
            preFlightsChecks.stdOut("WARNING: phpMyAdmin OLS setup failed: %s" % str(e), 0)
            logging.InstallLog.writeToFile('[WARNING] phpMyAdmin OLS: ' + str(e))
            return False

    def setupLSCPDDaemon(self):
        try:

            preFlightsChecks.stdOut("Trying to setup LSCPD Daemon!")
            logging.InstallLog.writeToFile("Trying to setup LSCPD Daemon!")

            install_dir = os.path.dirname(os.path.abspath(__file__))
            lscpd_service = os.path.join(install_dir, "lscpd", "lscpd.service")
            lscpd_ctrl = os.path.join(install_dir, "lscpd", "lscpdctrl")
            os.makedirs("/usr/local/lscp/bin", exist_ok=True)

            shutil.copy(lscpd_service, "/etc/systemd/system/lscpd.service")
            shutil.copy(lscpd_ctrl, "/usr/local/lscp/bin/lscpdctrl")

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
            self.manage_service('lscpd', 'enable')

            ##
            count = 0

            # In Ubuntu, the library that lscpd looks for is libpcre.so.1, but the one it installs is libpcre.so.3...
            if self.distro == ubuntu:
                command = 'ln -s /lib/x86_64-linux-gnu/libpcre.so.3 /lib/x86_64-linux-gnu/libpcre.so.1'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            ##

            command = 'systemctl daemon-reload'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            command = 'systemctl start lscpd'
            ret = preFlightsChecks.call(command, self.distro, command, command, 0, 0, os.EX_OSERR)
            if ret != 0:
                preFlightsChecks.stdOut("LSCPD start failed, reloading systemd and retrying...")
                logging.InstallLog.writeToFile("LSCPD first start failed, retrying after daemon-reload")
                preFlightsChecks.call('systemctl daemon-reload', self.distro, 'daemon-reload', 'daemon-reload', 1, 0, os.EX_OSERR)
                ret = preFlightsChecks.call('systemctl start lscpd', self.distro, 'systemctl start lscpd', 'systemctl start lscpd', 0, 0, os.EX_OSERR)
            if ret != 0:
                preFlightsChecks.stdOut("[WARNING] LSCPD may not have started. Run: systemctl status lscpd")
                logging.InstallLog.writeToFile("[WARNING] LSCPD start failed after retry - run systemctl status lscpd")

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

            try:
                if '/usr/local/CyberCP' not in sys.path:
                    sys.path.insert(0, '/usr/local/CyberCP')
                from plogical.cyberpanel_python import ensure_cyberpanel_bin_python_shim
                ensure_cyberpanel_bin_python_shim()
            except BaseException:
                pass

            cronFile = open(cronPath, "w")

            # Randomize acme.sh and renew.py cron schedules to avoid traffic spikes to Let's Encrypt
            # Each installation gets a random day (0-6 Sun-Sat), hour, and minute to spread load
            acme_hour = random.randint(0, 23)
            acme_minute = random.randint(0, 59)
            renew_weekday = random.randint(0, 6)  # 0=Sun, 1=Mon, ..., 6=Sat
            renew_hour = random.randint(0, 23)
            renew_minute = random.randint(0, 59)

            content = """
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/findBWUsage.py >/dev/null 2>&1
0 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py hourlyCleanup >/dev/null 2>&1
0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup >/dev/null 2>&1
0 2 * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/upgradeCritical.py >/dev/null 2>&1
%d %d * * %d /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/renew.py >/dev/null 2>&1
%d %d * * * "/root/.acme.sh"/acme.sh --cron --home "/root/.acme.sh" > /dev/null
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
""" % (renew_minute, renew_hour, renew_weekday, acme_minute, acme_hour)

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
            key_path = "/root/.ssh/cyberpanel"
            key_pub = "/root/.ssh/cyberpanel.pub"

            if not os.path.exists(path):
                os.mkdir(path)

            # Remove existing key files so ssh-keygen never prompts "Overwrite (y/n)?"
            # Use shell rm -f so removal is reliable (avoids os.remove permission/state issues)
            subprocess.run(
                "rm -f /root/.ssh/cyberpanel /root/.ssh/cyberpanel.pub",
                shell=True,
                timeout=5,
                capture_output=True,
            )

            # Run ssh-keygen with stdin=input so we never block on "Overwrite (y/n)?"
            command = "ssh-keygen -f /root/.ssh/cyberpanel -t rsa -N ''"
            preFlightsChecks.stdOut("Running: %s" % command, 1)
            res = subprocess.run(
                ["ssh-keygen", "-f", "/root/.ssh/cyberpanel", "-t", "rsa", "-N", ""],
                stdin=subprocess.PIPE,
                input=b"y\n",
                timeout=30,
                capture_output=True,
            )
            if res.returncode != 0:
                err = (res.stderr or b"").decode("utf-8", errors="replace").strip()
                preFlightsChecks.stdOut("[ERROR] ssh-keygen failed (return %s). %s" % (res.returncode, err), 1)
                return 0
            preFlightsChecks.stdOut("Successfully ran: %s." % command, 1)

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

        print(("               Visit: https://" + self.ipAddr + ":8090            "))
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
            # Install dependencies first
            if self.distro == ubuntu:
                deps = ['libmilter-dev', 'libmemcached-dev']
                for dep in deps:
                    try:
                        self.install_package(dep)
                    except:
                        pass
                self.install_package('opendkim opendkim-tools')
            else:
                # Install dependencies for RHEL-based systems
                deps = ['sendmail-milter', 'sendmail-milter-devel']
                for dep in deps:
                    try:
                        self.install_package(dep, '--skip-broken')
                    except:
                        pass
                
                # Handle libmemcached with fallback for AlmaLinux 9
                try:
                    self.install_package('libmemcached libmemcached-devel', '--skip-broken')
                except:
                    # Fallback for AlmaLinux 9
                    try:
                        self.install_package('memcached-devel', '--skip-broken')
                    except:
                        self.stdOut("Warning: libmemcached packages not available, continuing...", 1)
                
                if self.distro == cent8 or self.distro == openeuler:
                    self.install_package('opendkim opendkim-tools', '--skip-broken')
                else:
                    self.install_package('opendkim', '--skip-broken')

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

            if self.distro == ubuntu or self.distro == cent8:
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
            # Ensure LiteSpeed repository is available for PHP packages
            if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                # Check if LiteSpeed repository is available
                command = 'dnf repolist | grep -q litespeed'
                result = preFlightsChecks.call(command, self.distro, command, command, 1, 1, os.EX_OSERR)
                if result != 1:
                    logging.InstallLog.writeToFile("[setupPHPSymlink] LiteSpeed repository not found, attempting to add it...")
                    # Add LiteSpeed repository
                    # Use compatible repository version for RHEL-based systems
                    # AlmaLinux 9 is compatible with el8 repositories
                    import install_utils
                    install_utils.install_litespeed_repo_rhel(self.distro, log=1)
            
            # Check if PHP 8.2 exists
            if not os.path.exists('/usr/local/lsws/lsphp82/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.2 not found, ensuring it's installed...")
                
                # Install PHP 8.2 based on OS
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'dnf install lsphp82 lsphp82-* -y --skip-broken --nobest'
                else:
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp82 lsphp82-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Check if PHP 8.3 exists
            if not os.path.exists('/usr/local/lsws/lsphp83/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.3 not found, ensuring it's installed...")
                
                # Install PHP 8.3 based on OS
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'dnf install lsphp83 lsphp83-* -y --skip-broken --nobest'
                else:
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp83 lsphp83-*'
                
                result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                # Verify installation
                if not os.path.exists('/usr/local/lsws/lsphp83/bin/php'):
                    logging.InstallLog.writeToFile('[ERROR] Failed to install PHP 8.3, trying alternative method...')
                    # Try alternative installation method
                    alt_command = 'dnf install lsphp83 -y --skip-broken --nobest --allowerasing'
                    preFlightsChecks.call(alt_command, self.distro, alt_command, alt_command, 1, 0, os.EX_OSERR)
                    
                    if not os.path.exists('/usr/local/lsws/lsphp83/bin/php'):
                        logging.InstallLog.writeToFile('[ERROR] Alternative PHP 8.3 installation also failed')
                        return 0

            # Install PHP 8.4
            if not os.path.exists('/usr/local/lsws/lsphp84/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.4 not found, ensuring it's installed...")
                
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'dnf install lsphp84 lsphp84-* -y --skip-broken --nobest'
                else:
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp84 lsphp84-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Install PHP 8.5
            if not os.path.exists('/usr/local/lsws/lsphp85/bin/php'):
                logging.InstallLog.writeToFile("[setupPHPSymlink] PHP 8.5 not found, ensuring it's installed...")
                
                if self.distro == centos or self.distro == cent8 or self.distro == openeuler:
                    command = 'dnf install lsphp85 lsphp85-* -y --skip-broken --nobest'
                else:
                    command = 'DEBIAN_FRONTEND=noninteractive apt-get update && DEBIAN_FRONTEND=noninteractive apt-get -y install lsphp85 lsphp85-*'
                
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Remove existing PHP symlink if it exists
            if os.path.exists('/usr/bin/php'):
                os.remove('/usr/bin/php')

            # Create symlink to the best available PHP version
            # Try to find and use the best available PHP version
            # Priority: 85, 84, 83, 82, 81, 80, 74 (newest to oldest)
            php_versions = ['85', '84', '83', '82', '81', '80', '74']
            php_symlink_source = None
            
            for php_ver in php_versions:
                candidate_path = f"/usr/local/lsws/lsphp{php_ver}/bin/php"
                if os.path.exists(candidate_path):
                    if not install_utils.verify_lsphp_binary_runnable(candidate_path, log=0):
                        logging.InstallLog.writeToFile(
                            f"[setupPHPSymlink] Skipping PHP {php_ver}: binary not runnable on this CPU ({candidate_path})"
                        )
                        continue
                    php_symlink_source = candidate_path
                    logging.InstallLog.writeToFile(f"[setupPHPSymlink] Found PHP {php_ver} binary: {candidate_path}")
                    break
            
            if php_symlink_source:
                command = f'ln -sf {php_symlink_source} /usr/bin/php'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                logging.InstallLog.writeToFile(f"[setupPHPSymlink] PHP symlink updated to {php_symlink_source} successfully.")
                
                # Verify symlink works
                if install_utils.verify_lsphp_binary_runnable(php_symlink_source, log=1):
                    logging.InstallLog.writeToFile("[setupPHPSymlink] PHP symlink verification successful")
                else:
                    logging.InstallLog.writeToFile("[ERROR] PHP symlink verification failed (CPU may lack x86-64-v3 / AVX2 on AlmaLinux 10)")
                    if install_utils.is_rhel_el10():
                        install_utils.el10_cpu_preflight(log=1, fatal=False)
                    return 0
            else:
                logging.InstallLog.writeToFile("[ERROR] No runnable PHP versions found for symlink creation")
                # List available PHP versions for debugging
                command = 'find /usr/local/lsws -name "lsphp*" -type d 2>/dev/null || true'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                return 0

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
            # Priority: 85, 84, 83, 82, 81, 80, 74 (newest to oldest)
            php_versions = ['85', '84', '83', '82', '81', '80', '74']
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

            # Download composer.sh to a known path so chmod never fails with "cannot access 'composer.sh'"
            composer_sh = "/tmp/composer.sh"
            if not os.path.isfile(composer_sh):
                command = "wget -q https://cyberpanel.sh/composer.sh -O " + composer_sh
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            if not os.path.isfile(composer_sh):
                command = "curl -sSL https://cyberpanel.sh/composer.sh -o " + composer_sh
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            if os.path.isfile(composer_sh):
                command = "chmod +x " + composer_sh
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                command = "bash " + composer_sh
                preFlightsChecks.call(command, self.distro, "composer.sh", command, 1, 0, os.EX_OSERR, True)
            else:
                logging.InstallLog.writeToFile("composer.sh download failed, skipping [setupPHPAndComposer]")

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

                pdns_service = preFlightsChecks.get_service_name('pdns')
                command = f'sudo systemctl stop {pdns_service}'
                subprocess.call(shlex.split(command))

                command = f'sudo systemctl disable {pdns_service}'
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
                # Stop and disable postfix service if it exists
                try:
                    command = 'systemctl stop postfix'
                    subprocess.call(shlex.split(command), 
                                  stdout=subprocess.DEVNULL, 
                                  stderr=subprocess.DEVNULL)
                    
                    command = 'systemctl disable postfix'
                    subprocess.call(shlex.split(command),
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.DEVNULL)
                except:
                    pass
                
                # Remove marker file if it exists
                if os.path.exists(servicePath):
                    try:
                        os.remove(servicePath)
                        logging.InstallLog.writeToFile(
                            'Removed postfix marker file (mail services disabled)'
                        )
                    except Exception as e:
                        logging.InstallLog.writeToFile(
                            f'Warning: Could not remove postfix marker: {str(e)}'
                        )
            
            else:  # state == 'on'
                # Only create marker if postfix is actually installed
                if (os.path.exists('/usr/sbin/postfix') or 
                    os.path.exists('/usr/bin/postfix')):
                    # Ensure /home/cyberpanel exists
                    if not os.path.exists('/home/cyberpanel'):
                        os.makedirs('/home/cyberpanel', mode=0o755)
                    
                    # Create marker file
                    with open(servicePath, 'w+') as f:
                        f.write('')
                    logging.InstallLog.writeToFile(
                        'Created postfix marker file (mail services enabled)'
                    )
                else:
                    logging.InstallLog.writeToFile(
                        'Skipping postfix marker creation (postfix not installed)'
                    )
        
        except OSError as msg:
            logging.InstallLog.writeToFile(
                '[ERROR] ' + str(msg) + " [enableDisableEmail]"
            )
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
            admin_pass = os.environ.get('CYBERPANEL_ADMIN_PASSWORD', '1234567')
            command = 'python /usr/local/CyberCP/plogical/adminPass.py --password %s' % (admin_pass,)
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
                
                command = 'restic self-update'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

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

    def installRabbitMQ(self):
        rabbitMQMarker = '/home/cyberpanel/rabbitmq'

        # Keep optional installer idempotent for reruns/retries.
        if os.path.exists(rabbitMQMarker):
            preFlightsChecks.stdOut("RabbitMQ marker already exists, skipping optional RabbitMQ installation.")
            return

        if self.distro == ubuntu or self.distro == debian12:
            command = 'DEBIAN_FRONTEND=noninteractive apt install rabbitmq-server -y'
        elif self.distro == centos:
            command = 'yum install rabbitmq-server -y'
        else:
            command = 'dnf install rabbitmq-server -y'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'systemctl enable rabbitmq-server'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        command = 'systemctl start rabbitmq-server'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

        writeToFile = open(rabbitMQMarker, 'w')
        writeToFile.close()

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
        install_dir = os.path.dirname(os.path.abspath(__file__))
        src = os.path.join(install_dir, 'dns_cyberpanel.sh')
        filePath = '/root/.acme.sh/dns_cyberpanel.sh'

        if not os.path.isfile(src):
            logging.InstallLog.writeToFile(
                "[ERROR] dns_cyberpanel.sh not found at %s" % src
            )
            preFlightsChecks.stdOut("ERROR: dns_cyberpanel.sh missing from install directory", 0)
            return

        os.makedirs(os.path.dirname(filePath), exist_ok=True)
        shutil.copy(src, filePath)

        command = f'chmod +x {filePath}'
        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
    
    def startDeferredServices(self):
        """Start services that were deferred during installation (PowerDNS and Pure-FTPd)
        These services require database tables that are created by Django migrations"""
        
        preFlightsChecks.stdOut("Starting deferred services that depend on database tables...")
        
        # Ensure database is ready first
        self.ensureDatabaseReady()
        
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

            self.fixAndStartPowerDNS()
        
        # Start Pure-FTPd if it was installed
        if os.path.exists('/home/cyberpanel/pureftpd'):
            self.fixAndStartPureFTPd()
        
        # Ensure LiteSpeed services are running
        self.ensureLiteSpeedServicesRunning()
        
        # Final service verification
        self.verifyCriticalServices()

    def ensureDatabaseReady(self):
        """Ensure database is ready before starting dependent services"""
        preFlightsChecks.stdOut("Ensuring database is ready...")
        
        # Wait for MySQL/MariaDB to be ready
        max_attempts = 30
        for attempt in range(max_attempts):
            try:
                if subprocess.run(['mysqladmin', 'ping', '-h', 'localhost', '--silent'], 
                                capture_output=True).returncode == 0:
                    preFlightsChecks.stdOut("Database is ready")
                    return
            except:
                pass
            preFlightsChecks.stdOut(f"Waiting for database... ({attempt + 1}/{max_attempts})")
            time.sleep(2)
        
        preFlightsChecks.stdOut("[WARNING] Database may not be fully ready")

    def ensurePowerDNSDatabaseAccess(self):
        """Ensure PowerDNS database tables and access are properly set up"""
        try:
            preFlightsChecks.stdOut("Setting up PowerDNS database access...", 1)
            
            # Create PowerDNS database tables if they don't exist
            sql_commands = [
                ("CREATE DATABASE IF NOT EXISTS powerdns", "PowerDNS database creation"),
                ("CREATE USER IF NOT EXISTS 'powerdns'@'localhost' IDENTIFIED BY 'cyberpanel'", "PowerDNS user creation"),
                ("GRANT ALL PRIVILEGES ON powerdns.* TO 'powerdns'@'localhost'", "PowerDNS privileges"),
                ("FLUSH PRIVILEGES", "PowerDNS privilege flush")
            ]

            for sql_cmd, desc in sql_commands:
                if not self.execute_mysql_command(sql_cmd, desc):
                    self.stdOut(f"Warning: {desc} may have failed", 0)

            # Import PowerDNS schema if tables don't exist
            schema_check_success = self.execute_mysql_command("USE powerdns; SHOW TABLES", "PowerDNS schema check")

            # For now, assume schema needs import if we can't check properly
            if not schema_check_success:
                preFlightsChecks.stdOut("Importing PowerDNS database schema...", 1)
                # Try to find and import PowerDNS schema
                schema_files = [
                    '/usr/share/doc/pdns-backend-mysql/schema.mysql.sql',
                    '/usr/share/doc/powerdns/schema.mysql.sql',
                    '/usr/share/pdns/schema.mysql.sql'
                ]
                
                for schema_file in schema_files:
                    if os.path.exists(schema_file):
                        import_cmd = f"mysql powerdns < {schema_file}"
                        preFlightsChecks.call(import_cmd, self.distro, f"Import PowerDNS schema", import_cmd, 1, 0, os.EX_OSERR)
                        break
                else:
                    preFlightsChecks.stdOut("PowerDNS schema not found, creating basic tables...", 1)
                    # Create basic PowerDNS tables
                    basic_schema = """
                    CREATE TABLE IF NOT EXISTS domains (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        name VARCHAR(255) NOT NULL,
                        master VARCHAR(128) DEFAULT NULL,
                        last_check INT DEFAULT NULL,
                        type VARCHAR(6) NOT NULL,
                        notified_serial INT DEFAULT NULL,
                        account VARCHAR(40) DEFAULT NULL,
                        UNIQUE KEY name (name)
                    );
                    CREATE TABLE IF NOT EXISTS records (
                        id BIGINT AUTO_INCREMENT PRIMARY KEY,
                        domain_id INT DEFAULT NULL,
                        name VARCHAR(255) DEFAULT NULL,
                        type VARCHAR(10) DEFAULT NULL,
                        content TEXT DEFAULT NULL,
                        ttl INT DEFAULT NULL,
                        prio INT DEFAULT NULL,
                        change_date INT DEFAULT NULL,
                        disabled TINYINT(1) DEFAULT 0,
                        ordername VARCHAR(255) DEFAULT NULL,
                        auth TINYINT(1) DEFAULT 1,
                        KEY domain_id (domain_id),
                        KEY name (name),
                        KEY type (type)
                    );
                    """
                    with open('/tmp/powerdns_schema.sql', 'w') as f:
                        f.write(basic_schema)
                    preFlightsChecks.call("mysql powerdns < /tmp/powerdns_schema.sql", self.distro, "Create PowerDNS tables", "mysql powerdns < /tmp/powerdns_schema.sql", 1, 0, os.EX_OSERR)
            
        except Exception as e:
            preFlightsChecks.stdOut(f"Warning: Could not set up PowerDNS database access: {str(e)}", 0)

    def fixAndStartPowerDNS(self):
        """Fix PowerDNS configuration and start the service"""
        preFlightsChecks.stdOut("Fixing and starting PowerDNS service...")
        
        # Check if PowerDNS is enabled first
        if not os.path.exists('/home/cyberpanel/powerdns'):
            preFlightsChecks.stdOut("PowerDNS not enabled, skipping...", 1)
            return
        
        # Determine correct service name
        pdns_service = None
        try:
            result = subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True, timeout=10)
            if 'pdns.service' in result.stdout:
                pdns_service = 'pdns'
            elif 'powerdns.service' in result.stdout:
                pdns_service = 'powerdns'
        except:
            preFlightsChecks.stdOut("Could not check systemctl services", 1)
        
        if not pdns_service:
            preFlightsChecks.stdOut("[WARNING] PowerDNS service not found, attempting to install...", 1)
            # Try to install PowerDNS
            try:
                if self.distro in [centos, cent8, openeuler]:
                    preFlightsChecks.call('dnf install -y pdns pdns-backend-mysql', self.distro, 'Install PowerDNS', 'Install PowerDNS', 1, 0, os.EX_OSERR)
                else:
                    preFlightsChecks.call('apt-get install -y pdns-server pdns-backend-mysql', self.distro, 'Install PowerDNS', 'Install PowerDNS', 1, 0, os.EX_OSERR)
                pdns_service = 'pdns'
            except:
                preFlightsChecks.stdOut("[WARNING] Could not install PowerDNS, skipping...", 1)
                return
        
        # Fix PowerDNS configuration - first check if config exists, if not copy it
        config_files = ['/etc/pdns/pdns.conf', '/etc/powerdns/pdns.conf']
        config_found = False
        for config_file in config_files:
            if os.path.exists(config_file):
                config_found = True
                preFlightsChecks.stdOut(f"Found PowerDNS config at: {config_file}")
                break

        if not config_found:
            # No config file found, need to copy it
            preFlightsChecks.stdOut("PowerDNS config not found, copying from template...")

            # Determine the correct config path based on distribution
            if self.distro in [centos, cent8, openeuler]:
                dnsPath = "/etc/pdns/pdns.conf"
                os.makedirs("/etc/pdns", exist_ok=True)
            else:
                dnsPath = "/etc/powerdns/pdns.conf"
                os.makedirs("/etc/powerdns", exist_ok=True)

            # Copy the PowerDNS configuration file (cwd may be temp dir with install/ subdir)
            source_file = os.path.join(self.cwd, "dns-one", "pdns.conf")
            if not os.path.exists(source_file):
                source_file = os.path.join(self.cwd, "install", "dns-one", "pdns.conf")
            if not os.path.exists(source_file):
                source_file = os.path.join(self.cwd, "dns", "pdns.conf")

            if os.path.exists(source_file):
                import shutil
                shutil.copy2(source_file, dnsPath)
                preFlightsChecks.stdOut(f"PowerDNS config copied to {dnsPath}")
                config_file = dnsPath
            else:
                preFlightsChecks.stdOut("[ERROR] PowerDNS template not found", 1)
                return

        # Now configure the existing or newly copied file
        if os.path.exists(config_file):
            preFlightsChecks.stdOut(f"Configuring PowerDNS: {config_file}")

            # Get MySQL password
            mysqlPassword = getattr(self, 'mysql_Root_password', 'cyberpanel')

            # Read existing content
            try:
                with open(config_file, 'r') as f:
                    content = f.read()
            except:
                content = ""

            # Add missing configuration if not present
            config_additions = []
            if 'gmysql-password=' not in content:
                config_additions.append(f'gmysql-password={mysqlPassword}')
            if 'launch=' not in content:
                config_additions.append('launch=gmysql')
            if 'gmysql-host=' not in content:
                config_additions.append('gmysql-host=localhost')
            if 'gmysql-user=' not in content:
                config_additions.append('gmysql-user=cyberpanel')
            if 'gmysql-dbname=' not in content:
                config_additions.append('gmysql-dbname=cyberpanel')

            if config_additions:
                with open(config_file, 'a') as f:
                    f.write('\n# CyberPanel configuration\n')
                    for config in config_additions:
                        f.write(config + '\n')

            # Ensure proper permissions
            os.chmod(config_file, 0o644)
            install_utils.restore_selinux_contexts(config_file, os.path.dirname(config_file))
        
        # Ensure PowerDNS can connect to database
        self.ensurePowerDNSDatabaseAccess()
        
        # Start PowerDNS service with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            preFlightsChecks.stdOut(f"Starting PowerDNS service (attempt {attempt + 1}/{max_retries})...", 1)
            
            # Stop service first to ensure clean start
            command = f'systemctl stop {pdns_service}'
            preFlightsChecks.call(command, self.distro, f"Stop {pdns_service}", command, 0, 0, os.EX_OSERR)
            time.sleep(2)
            
            # Start service
            command = f'systemctl start {pdns_service}'
            result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

            # Wait a moment for service to start
            time.sleep(3)
            
            # Check if service is actually running
            command = f'systemctl is-active {pdns_service}'
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                output = result.stdout.strip()
                if output == 'active':
                    preFlightsChecks.stdOut("PowerDNS service started successfully!", 1)
                    # Double-check with systemctl status for more details
                    status_command = f'systemctl status {pdns_service} --no-pager -l'
                    try:
                        status_result = subprocess.run(status_command, shell=True, capture_output=True, text=True, timeout=10)
                        if status_result.returncode == 0:
                            preFlightsChecks.stdOut("PowerDNS service status verified", 1)
                        else:
                            preFlightsChecks.stdOut("PowerDNS service running but status check failed", 0)
                    except:
                        preFlightsChecks.stdOut("PowerDNS service running but status verification failed", 0)
                    break
                else:
                    preFlightsChecks.stdOut(f"PowerDNS service status: {output} (attempt {attempt + 1})", 0)
                    if attempt < max_retries - 1:
                        preFlightsChecks.stdOut("Retrying PowerDNS startup...", 1)
                        time.sleep(5)
            except subprocess.TimeoutExpired:
                preFlightsChecks.stdOut(f"PowerDNS service status check timed out (attempt {attempt + 1})", 0)
                if attempt < max_retries - 1:
                    time.sleep(5)
            except Exception as e:
                preFlightsChecks.stdOut(f"Could not verify PowerDNS service status (attempt {attempt + 1}): {str(e)}", 0)
                if attempt < max_retries - 1:
                    time.sleep(5)
        else:
            preFlightsChecks.stdOut("[WARNING] PowerDNS service failed to start after all retries", 0)
            # Try to get more details about the failure
            command = f'systemctl status {pdns_service} --no-pager'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        
        # Enable service for auto-start (with error handling)
        command = f'systemctl enable {pdns_service}'
        enable_result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        if enable_result != 1:
            preFlightsChecks.stdOut(f"Warning: Could not enable {pdns_service} for auto-start", 0)

    def fixAndStartPureFTPd(self):
        """Fix Pure-FTPd configuration and start the service"""
        preFlightsChecks.stdOut("Fixing and starting Pure-FTPd service...")
        
        # Determine correct service name
        ftp_service = None
        if subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True).stdout.find('pure-ftpd.service') != -1:
            ftp_service = 'pure-ftpd'
        elif subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True).stdout.find('pureftpd.service') != -1:
            ftp_service = 'pureftpd'
        
        if not ftp_service:
            preFlightsChecks.stdOut("[WARNING] Pure-FTPd service not found")
            return
        
        # Fix Pure-FTPd configuration
        config_files = ['/etc/pure-ftpd/pureftpd-mysql.conf', '/etc/pure-ftpd/db/mysql.conf']
        for config_file in config_files:
            if os.path.exists(config_file):
                preFlightsChecks.stdOut(f"Configuring Pure-FTPd: {config_file}")
                
                # Fix MySQL password configuration
                command = f"sed -i 's/MYSQLPassword.*/MYSQLPassword cyberpanel/' {config_file}"
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                # Fix MySQL crypt method for Ubuntu 24.04 compatibility
            if self.distro == ubuntu:
                import install_utils
                try:
                    release = install_utils.get_Ubuntu_release(use_print=False, exit_on_error=False)
                    if release and release >= 24.04:
                        preFlightsChecks.stdOut("Configuring Pure-FTPd for Ubuntu 24.04...")
                        command = f"sed -i 's/MYSQLCrypt md5/MYSQLCrypt crypt/g' {config_file}"
                        preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                except:
                    pass
        
        # Start Pure-FTPd service with retry mechanism
        max_retries = 3
        for attempt in range(max_retries):
            preFlightsChecks.stdOut(f"Starting Pure-FTPd service (attempt {attempt + 1}/{max_retries})...", 1)
            
            # Stop service first to ensure clean start
            command = f'systemctl stop {ftp_service}'
            preFlightsChecks.call(command, self.distro, f"Stop {ftp_service}", command, 0, 0, os.EX_OSERR)
            time.sleep(2)
            
            # Start service
            command = f'systemctl start {ftp_service}'
            result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
            
            # Wait a moment for service to start
            time.sleep(3)
            
            # Check if service is actually running
            command = f'systemctl is-active {ftp_service}'
            try:
                result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=10)
                output = result.stdout.strip()
                if output == 'active':
                    preFlightsChecks.stdOut("Pure-FTPd service started successfully!", 1)
                    # Double-check with systemctl status for more details
                    status_command = f'systemctl status {ftp_service} --no-pager -l'
                    try:
                        status_result = subprocess.run(status_command, shell=True, capture_output=True, text=True, timeout=10)
                        if status_result.returncode == 0:
                            preFlightsChecks.stdOut("Pure-FTPd service status verified", 1)
                        else:
                            preFlightsChecks.stdOut("Pure-FTPd service running but status check failed", 0)
                    except:
                        preFlightsChecks.stdOut("Pure-FTPd service running but status verification failed", 0)
                    break
                else:
                    preFlightsChecks.stdOut(f"Pure-FTPd service status: {output} (attempt {attempt + 1})", 0)
                    if attempt < max_retries - 1:
                        preFlightsChecks.stdOut("Retrying Pure-FTPd startup...", 1)
                        time.sleep(5)
            except subprocess.TimeoutExpired:
                preFlightsChecks.stdOut(f"Pure-FTPd service status check timed out (attempt {attempt + 1})", 0)
                if attempt < max_retries - 1:
                    time.sleep(5)
            except Exception as e:
                preFlightsChecks.stdOut(f"Could not verify Pure-FTPd service status (attempt {attempt + 1}): {str(e)}", 0)
                if attempt < max_retries - 1:
                    time.sleep(5)
        else:
            preFlightsChecks.stdOut("[WARNING] Pure-FTPd service failed to start after all retries", 0)
            # Try to get more details about the failure
            command = f'systemctl status {ftp_service} --no-pager'
            preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        
        # Enable service for auto-start (with error handling)
        command = f'systemctl enable {ftp_service}'
        enable_result = preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
        if enable_result != 1:
            preFlightsChecks.stdOut(f"Warning: Could not enable {ftp_service} for auto-start", 0)

    def ensureLiteSpeedServicesRunning(self):
        """Ensure LiteSpeed services are running properly"""
        preFlightsChecks.stdOut("Ensuring LiteSpeed services are running...")
        
        # Fix LiteSpeed permissions first
        self.fixLiteSpeedPermissions()
        
        # Restart LiteSpeed services
        litespeed_services = ['lsws', 'lscpd']
        for service in litespeed_services:
            if subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True).stdout.find(f'{service}.service') != -1:
                preFlightsChecks.stdOut(f"Restarting {service}...")
                command = f'systemctl restart {service}'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                # Enable service for auto-start
                command = f'systemctl enable {service}'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                # Verify service is running
                command = f'systemctl is-active {service}'
                try:
                    output = subprocess.check_output(shlex.split(command)).decode("utf-8").strip()
                    if output == 'active':
                        preFlightsChecks.stdOut(f"{service} is running successfully!")
                    else:
                        preFlightsChecks.stdOut(f"[WARNING] {service} status: {output}")
                except:
                    preFlightsChecks.stdOut(f"[WARNING] Could not verify {service} status")

    def fixLiteSpeedPermissions(self):
        """Fix LiteSpeed directory permissions"""
        preFlightsChecks.stdOut("Fixing LiteSpeed permissions...")
        
        litespeed_dirs = ['/usr/local/lsws', '/usr/local/lscp', '/usr/local/CyberCP']
        for directory in litespeed_dirs:
            if os.path.exists(directory):
                command = f'chown -R lscpd:lscpd {directory}'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)
                
                command = f'chmod -R 755 {directory}'
                preFlightsChecks.call(command, self.distro, command, command, 1, 0, os.EX_OSERR)

    def verifyCriticalServices(self):
        """Verify that all critical services are running"""
        preFlightsChecks.stdOut("Verifying critical services...")
        
        critical_services = ['lsws', 'lscpd']
        all_services_ok = True
        
        for service in critical_services:
            if subprocess.run(['systemctl', 'list-unit-files'], capture_output=True, text=True).stdout.find(f'{service}.service') != -1:
                command = f'systemctl is-active {service}'
                try:
                    output = subprocess.check_output(shlex.split(command)).decode("utf-8").strip()
                    if output == 'active':
                        preFlightsChecks.stdOut(f"✓ {service} is running")
                    else:
                        preFlightsChecks.stdOut(f"✗ {service} is not running (status: {output})")
                        all_services_ok = False
                except:
                    preFlightsChecks.stdOut(f"✗ Could not verify {service} status")
                    all_services_ok = False
        
        if all_services_ok:
            preFlightsChecks.stdOut("All critical services are running successfully!")
            preFlightsChecks.stdOut("CyberPanel should now be accessible at https://your-server-ip:8090")
        else:
            preFlightsChecks.stdOut("[WARNING] Some critical services are not running properly")
            preFlightsChecks.stdOut("Please check the logs and consider running: systemctl restart lsws lscpd")

def configure_jwt_secret():
    """
    Web Terminal: write JWT and claims to /etc/cyberpanel/fastapi_ssh_server.conf (never embed in .py).
    """
    try:
        sys.path.insert(0, "/usr/local/CyberCP")
        from plogical import fastapi_ssh_config

        fastapi_ssh_config.ensure_runtime_files_on_install()
    except Exception as exc:
        try:
            logging.InstallLog.writeToFile(
                "[configure_jwt_secret] Web Terminal runtime config failed: %s" % str(exc)
            )
        except Exception:
            pass

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
    parser.add_argument('--rabbitmq', help='Enable optional RabbitMQ installation.')
    parser.add_argument('--remotemysql', help='Opt to choose local or remote MySQL')
    parser.add_argument('--mysqlhost', help='MySQL host if remote is chosen.')
    parser.add_argument('--mysqldb', help='MySQL DB if remote is chosen.')
    parser.add_argument('--mysqluser', help='MySQL user if remote is chosen.')
    parser.add_argument('--mysqlpassword', help='MySQL password if remote is chosen.')
    parser.add_argument('--mysqlport', help='MySQL port if remote is chosen.')
    parser.add_argument('--mariadb-version', default='11.8', help='MariaDB version: 10.3-10.11, 11.0-11.8, 12.0-12.x (default 11.8)')
    parser.add_argument('--phpmyadmin-version', default='', help='phpMyAdmin version (e.g. 5.2.3); empty = latest from API')
    parser.add_argument('--snappymail-version', default='', help='SnappyMail version (e.g. 2.38.2); empty = latest from API')
    parser.add_argument('--container', default='OFF', help='Container runtime install (ON/OFF).')

    args = parser.parse_args()
    # Normalize and validate MariaDB version choice (default 11.8)
    mariadb_ver = _normalize_mariadb_version(getattr(args, 'mariadb_version', None) or '11.8')
    preFlightsChecks.mariadb_version = mariadb_ver
    # Optional phpMyAdmin/SnappyMail version overrides (empty = use latest from API)
    if getattr(args, 'phpmyadmin_version', ''):
        preFlightsChecks.phpmyadmin_version = (args.phpmyadmin_version or '').strip()
    if getattr(args, 'snappymail_version', ''):
        preFlightsChecks.snappymail_version = (args.snappymail_version or '').strip()

    logging.InstallLog.ServerIP = args.publicip
    logging.InstallLog.writeToFile("Starting CyberPanel installation..,10")
    if str(getattr(args, 'container', 'OFF')).upper() == 'ON' or install_utils.is_container_runtime():
        os.environ['CYBERPANEL_CONTAINER'] = '1'
        mode = install_utils.resolve_install_mode_from_env()
        install_utils.container_prepare_hostname(os.environ.get('CYBERPANEL_HOSTNAME', ''))
        install_utils.container_prepare_dns(mode.get('powerdns', 'ON'))
        logging.InstallLog.writeToFile(
            "Container install mode: %s (postfix=%s powerdns=%s ftp=%s)"
            % (mode.get('mode'), mode.get('postfix'), mode.get('powerdns'), mode.get('ftp'))
        )
    install_utils.el10_cpu_preflight(log=1, fatal=True)
    preFlightsChecks.stdOut("Starting CyberPanel installation..")

    # Initialize serial variable
    serial = None

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

    machineIP = open("/etc/cyberpanel/machineIP", "w")
    machineIP.writelines(args.publicip)
    machineIP.close()

    cwd = os.getcwd()

    if args.remotemysql == 'ON':
        remotemysql = args.remotemysql
        mysqlhost = args.mysqlhost
        mysqluser = args.mysqluser
        mysqlpassword = args.mysqlpassword
        mysqlport = args.mysqlport
        mysqldb = args.mysqldb

        if preFlightsChecks.debug:
            print('mysqlhost: %s, mysqldb: %s,  mysqluser: %s, mysqlpassword: %s, mysqlport: %s' % (
                mysqlhost, mysqldb, mysqluser, mysqlpassword, mysqlport))
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

    # Check Python version early
    checks.checkPythonVersion()

    # Setup CyberPanel account early before other operations
    preFlightsChecks.stdOut("Setting up CyberPanel system account...")
    checks.setup_account_cyberpanel()

    # Apply OS-specific fixes early in the installation process
    checks.apply_os_specific_fixes()
    
    # CRITICAL: Disable MariaDB 12.1 repository and add dnf exclude BEFORE any MariaDB installation attempts
    # This must run before Pre_Install_Required_Components tries to install MariaDB
    checks.disableMariaDB12RepositoryIfNeeded()

    # CRITICAL: Remove MariaDB-server-compat* before ANY MariaDB installation
    # This package conflicts with MariaDB 10.11 and must be removed early
    preFlightsChecks.stdOut("Removing conflicting MariaDB-server-compat packages...", 1)
    try:
        subprocess.run("rpm -e --nodeps MariaDB-server-compat-12.1.2-1.el9.noarch 2>/dev/null; true", shell=True, timeout=30)
        subprocess.run("dnf remove -y 'MariaDB-server-compat*' 2>/dev/null || true", shell=True, timeout=60)
        r = subprocess.run("rpm -qa 2>/dev/null | grep -i MariaDB-server-compat", shell=True, capture_output=True, text=True, timeout=30)
        for line in (r.stdout or "").strip().splitlines():
            pkg = (line.strip().split() or [""])[0]
            if pkg and "MariaDB-server-compat" in pkg:
                subprocess.run(["rpm", "-e", "--nodeps", pkg], timeout=30)
        preFlightsChecks.stdOut("MariaDB compat cleanup completed", 1)
    except Exception as e:
        preFlightsChecks.stdOut("Warning: compat cleanup: " + str(e), 0)

    # Ensure MySQL password file is created early to prevent FileNotFoundError
    checks.ensure_mysql_password_file()

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

    checks.installCyberPanelRepo()

    # Note: OS-specific fixes are now applied earlier in the installation process
    # The installCyberPanel.Main() functionality has been integrated into the main installation flow

    # Apply AlmaLinux 9 comprehensive fixes first if needed
    if checks.is_almalinux9():
        checks.fix_almalinux9_comprehensive()
    
    # Disable MariaDB 12.1 repository if MariaDB 10.x is already installed
    # This prevents upgrade attempts in Pre_Install_Required_Components
    checks.disableMariaDB12RepositoryIfNeeded()

    # Install core services in the correct order
    checks.installLiteSpeed(ent, serial)
    if not checks.installMySQL(mysql):
        logging.InstallLog.writeToFile("FATAL: MySQL/MariaDB installation failed")
        preFlightsChecks.stdOut("MySQL/MariaDB installation failed. Installation cannot continue.", 1)
        os._exit(1)

    # Create cyberpanel database and user immediately after MySQL installation
    logging.InstallLog.writeToFile("Creating cyberpanel database and user...")
    preFlightsChecks.stdOut("Creating cyberpanel database and user...", 1)

    try:
        import mysqlUtilities

        # Generate cyberpanel database password using the same logic as download_install_CyberPanel
        if checks.distro == centos:
            # On CentOS, generate a separate password for cyberpanel database
            checks.cyberpanel_db_password = install_utils.generate_pass()
        else:
            # On Ubuntu/Debian, the cyberpanel password is the same as root password
            checks.cyberpanel_db_password = checks.mysql_Root_password

        # Create cyberpanel database and user (restored from v2.4.4 installCyberPanel.py)
        logging.InstallLog.writeToFile(f"Attempting to create cyberpanel database with password length: {len(checks.cyberpanel_db_password)}")

        result = mysqlUtilities.mysqlUtilities.createDatabase("cyberpanel", "cyberpanel", checks.cyberpanel_db_password, "localhost")
        if result == 1:
            logging.InstallLog.writeToFile("✅ Cyberpanel database and user created successfully!")
            preFlightsChecks.stdOut("Cyberpanel database and user created successfully!", 1)

            # Verify the user was created by testing the connection
            try:
                test_success = False
                # Try mariadb first, then mysql
                for cmd_base in ['mariadb', 'mysql']:
                    if checks.command_exists(cmd_base):
                        test_cmd = f"{cmd_base} -u cyberpanel -p{checks.cyberpanel_db_password} -e 'SELECT 1;'"
                        test_result = subprocess.call(test_cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        if test_result == 0:
                            logging.InstallLog.writeToFile("✅ Verified: cyberpanel user can connect to MySQL")
                            test_success = True
                            break

                if not test_success:
                    logging.InstallLog.writeToFile("⚠️ Warning: Could not verify cyberpanel user connection")
            except Exception as verify_error:
                logging.InstallLog.writeToFile(f"Could not verify MySQL connection: {str(verify_error)}")
        else:
            error_msg = f"❌ CRITICAL ERROR: Cyberpanel database creation failed (returned {result})"
            logging.InstallLog.writeToFile(error_msg)
            preFlightsChecks.stdOut("Database creation failed - installation cannot continue", 1)

            # Don't continue with settings.py update if database creation failed
            raise Exception("Database creation failed - cyberpanel user does not exist")
    except Exception as e:
        logging.InstallLog.writeToFile(f"Error creating cyberpanel database: {str(e)}")
        preFlightsChecks.stdOut(f"Error: Database creation failed: {str(e)}", 1)
        os._exit(1)

    checks.installPowerDNS() if (args.powerdns is None or str(args.powerdns).upper() == 'ON') else (
        preFlightsChecks.stdOut("Skipping PowerDNS installation as requested.")
    )
    checks.installPureFTPD() if (args.ftp is None or str(args.ftp).upper() == 'ON') else (
        preFlightsChecks.stdOut("Skipping Pure-FTPd installation as requested.")
    )

    # Setup PHP and Composer (dependencies already installed by comprehensive fix)
    checks.setupPHPAndComposer()
    checks.fix_selinux_issue()
    checks.install_psmisc()
    checks.fixSudoers()

    if args.postfix is None:
        checks.install_postfix_dovecot()
        # Ensure cyberpanel_db_password is set before calling setup_email_Passwords
        if not hasattr(checks, 'cyberpanel_db_password') or checks.cyberpanel_db_password is None:
            checks.cyberpanel_db_password = checks.mysql_Root_password
        checks.setup_email_Passwords(checks.cyberpanel_db_password, mysql)
        checks.setup_postfix_dovecot_config(mysql)
        checks.enableDisableEmail('on')
        setup_webmail_master_user()
    elif args.postfix == 'ON':
        checks.install_postfix_dovecot()
        if not hasattr(checks, 'cyberpanel_db_password') or checks.cyberpanel_db_password is None:
            checks.cyberpanel_db_password = checks.mysql_Root_password
        checks.setup_email_Passwords(checks.cyberpanel_db_password, mysql)
        checks.setup_postfix_dovecot_config(mysql)
        checks.enableDisableEmail('on')
        setup_webmail_master_user()
    else:
        preFlightsChecks.stdOut("Skipping Postfix/Mail services installation as requested.")
        checks.enableDisableEmail('off')

    checks.install_unzip()
    checks.install_zip()
    checks.install_rsync()

    checks.installFirewalld()
    checks.install_default_keys()

    checks.download_install_CyberPanel(checks.mysqlpassword, mysql)
    checks.downoad_and_install_raindloop()
    checks.download_install_phpmyadmin()
    checks.setupCLI()
    checks.setup_cron()
    checks.installRestic()
    checks.installAcme()
    
    # Fix Django AutoField warnings
    fix_django_autofield_warnings()

    ## Install and Configure OpenDKIM.

    if args.postfix is None:
        checks.installOpenDKIM()
        checks.configureOpenDKIM()
    elif args.postfix == 'ON':
        checks.installOpenDKIM()
        checks.configureOpenDKIM()
    else:
        # Skip OpenDKIM when postfix is disabled
        preFlightsChecks.stdOut("Skipping OpenDKIM installation (mail services disabled).")

    checks.modSecPreReqs()
    checks.installLSCPD()
    checks.setupPort()
    checks.setupPythonWSGI()
    checks.setupLSCPDDaemon()
    checks.ensureCyberPanelPhpmyadminOls()
    checks.installDNS_CyberPanelACMEFile()

    if args.redis is not None:
        checks.installRedis()

    if args.rabbitmq is not None and str(args.rabbitmq).upper() == 'ON':
        checks.installRabbitMQ()

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

    # Validate service marker files match actual installations
    logging.InstallLog.writeToFile("Validating service markers...")
    
    # Check postfix marker
    postfix_marker = '/home/cyberpanel/postfix'
    postfix_installed = (os.path.exists('/etc/postfix/main.cf') and 
                         (os.path.exists('/usr/sbin/postfix') or 
                          os.path.exists('/usr/bin/postfix')))
    
    if os.path.exists(postfix_marker) and not postfix_installed:
        logging.InstallLog.writeToFile(
            'Warning: Postfix marker exists but postfix not installed. Removing marker.'
        )
        os.remove(postfix_marker)
    elif not os.path.exists(postfix_marker) and postfix_installed:
        logging.InstallLog.writeToFile(
            'Warning: Postfix installed but marker missing. Creating marker.'
        )
        checks.enableDisableEmail('on')

    checks.installCLScripts()
    # checks.disablePackegeUpdates()

    try:
        # command = 'mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/data/default/configs/'
        # subprocess.call(shlex.split(command))

        writeToFile = open('/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/application.ini', 'a')

        writeToFile.write("""
[security]
admin_login = "admin"
admin_password = "12345"
""")
        writeToFile.close()

        content = r"""<?php

$_ENV['snappymail_INCLUDE_AS_API'] = true;
include '/usr/local/CyberCP/public/snappymail/index.php';

$oConfig = \snappymail\Api::Config();
$oConfig->SetPassword('%s');
echo $oConfig->Save() ? 'Done' : 'Error';

?>""" % (generate_pass())

        writeToFile = open('/usr/local/CyberCP/public/snappymail.php', 'w')
        writeToFile.write(content)
        writeToFile.close()

        command = '%s /usr/local/CyberCP/public/snappymail.php' % (
            install_utils.resolve_lsphp_binary('php') or '/usr/local/lsws/lsphp83/bin/php'
        )
        subprocess.call(shlex.split(command))

        command = "chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/data"
        subprocess.call(shlex.split(command))

        # Ensure all data directories have group write permissions
        command = "chmod -R 775 /usr/local/lscp/cyberpanel/snappymail/data"
        subprocess.call(shlex.split(command))

        # Ensure web server users are in the lscpd group
        command = "usermod -a -G lscpd nobody 2>/dev/null || true"
        subprocess.call(shlex.split(command))

        # Fix SnappyMail public directory ownership (critical fix)
        command = "chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail/data || true"
        subprocess.call(shlex.split(command))
    except:
        pass

    checks.fixCyberPanelPermissions()
    configure_jwt_secret()

    # Start services that were enabled but not started during installation
    # These services require database tables that are created by Django migrations
    checks.startDeferredServices()

    if str(getattr(args, 'container', 'OFF')).upper() == 'ON' or install_utils.is_container_runtime():
        try:
            import container as container_mod
            postfix_flag = (args.postfix or 'ON').upper()
            powerdns_flag = (args.powerdns or 'ON').upper()
            ftp_flag = (args.ftp or 'ON').upper()
            container_mod.finalize_container_install(
                postfix_flag,
                powerdns_flag,
                ftp_flag,
                log_fn=lambda msg: logging.InstallLog.writeToFile(msg),
            )
        except Exception as exc:
            logging.InstallLog.writeToFile('[WARN] container finalize: %s' % str(exc))

    # Installation summary
    show_installation_summary()
    
    logging.InstallLog.writeToFile("CyberPanel installation successfully completed!,80")


def show_installation_summary():
    """Display comprehensive installation summary"""
    try:
        import time
        import subprocess
        
        print("\n" + "="*80)
        print("📊 CYBERPANEL INSTALLATION SUMMARY")
        print("="*80)
        
        # Check component status
        components = {
            "CyberPanel Core": check_service_status("lscpd"),
            "OpenLiteSpeed": check_openlitespeed_status(),
            "MariaDB/MySQL": check_service_status("mysql") or check_service_status("mariadb"),
            "PowerDNS": check_powerdns_status(),
            "Pure-FTPd": check_pureftpd_status(),
            "Postfix": check_service_status("postfix"),
            "Dovecot": check_service_status("dovecot"),
            "LSMCD": check_service_status("lsmcd"),
            "SnappyMail": check_file_exists("/usr/local/CyberCP/public/snappymail"),
            "phpMyAdmin": check_file_exists("/usr/local/CyberCP/public/phpmyadmin")
        }
        
        print("\n🔧 COMPONENT STATUS:")
        print("-" * 50)
        for component, status in components.items():
            if status:
                print(f"✅ {component:<20} - INSTALLED & RUNNING")
            else:
                print(f"❌ {component:<20} - NOT AVAILABLE")
        
        # System information
        try:
            memory_info = subprocess.check_output("free -m", shell=True).decode()
            memory_line = [line for line in memory_info.split('\n') if 'Mem:' in line][0]
            memory_parts = memory_line.split()
            total_mem = memory_parts[1]
            used_mem = memory_parts[2]
            mem_percent = (int(used_mem) / int(total_mem)) * 100
            
            disk_info = subprocess.check_output("df -h /", shell=True).decode()
            disk_line = [line for line in disk_info.split('\n') if '/dev/' in line][0]
            disk_parts = disk_line.split()
            disk_usage = disk_parts[4]
            
            print(f"\n📈 SYSTEM RESOURCES:")
            print(f"   • Memory Usage: {used_mem}MB / {total_mem}MB ({mem_percent:.1f}%)")
            print(f"   • Disk Usage: {disk_usage}")
            print(f"   • CPU Cores: {subprocess.check_output('nproc', shell=True).decode().strip()}")
            
        except Exception as e:
            print(f"\n📈 SYSTEM RESOURCES: Unable to retrieve ({str(e)})")
        
        # Installation time
        try:
            if hasattr(show_installation_summary, 'start_time'):
                elapsed = time.time() - show_installation_summary.start_time
                minutes = int(elapsed // 60)
                seconds = int(elapsed % 60)
                print(f"   • Install Time: {minutes}m {seconds}s")
        except:
            pass
        
        print("\n" + "="*80)
        
    except Exception as e:
        print(f"\n⚠️  Could not generate installation summary: {str(e)}")


def check_service_status(service_name):
    """Check if a service is running"""
    try:
        result = subprocess.run(['systemctl', 'is-active', service_name], 
                              capture_output=True, text=True)
        return result.returncode == 0
    except:
        return False

def check_openlitespeed_status():
    """Check if OpenLiteSpeed is running (special case)"""
    try:
        # Check if lsws process is running
        result = subprocess.run(['pgrep', '-f', 'litespeed'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        
        # Check if lsws service is active
        result = subprocess.run(['systemctl', 'is-active', 'lsws'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
            
        # Check if openlitespeed service is active
        result = subprocess.run(['systemctl', 'is-active', 'openlitespeed'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
            
        return False
    except:
        return False

def check_powerdns_status():
    """Check if PowerDNS is running (special case)"""
    try:
        # Check if pdns process is running
        result = subprocess.run(['pgrep', '-f', 'pdns'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        
        # Check various PowerDNS service names
        for service in ['pdns', 'pdns-server', 'powerdns']:
            result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
            if result.returncode == 0:
                return True
                
        return False
    except:
        return False

def check_pureftpd_status():
    """Check if Pure-FTPd is running (special case)"""
    try:
        # Check if pure-ftpd process is running
        result = subprocess.run(['pgrep', '-f', 'pure-ftpd'], capture_output=True, text=True)
        if result.returncode == 0:
            return True
        
        # Check various Pure-FTPd service names
        for service in ['pure-ftpd', 'pureftpd']:
            result = subprocess.run(['systemctl', 'is-active', service], capture_output=True, text=True)
            if result.returncode == 0:
                return True
                
        return False
    except:
        return False

def fix_django_autofield_warnings():
    """Fix Django AutoField warnings by setting DEFAULT_AUTO_FIELD"""
    try:
        settings_file = '/usr/local/CyberCP/cyberpanel/settings.py'
        if os.path.exists(settings_file):
            with open(settings_file, 'r') as f:
                content = f.read()
            
            # Add DEFAULT_AUTO_FIELD setting if not present
            if 'DEFAULT_AUTO_FIELD' not in content:
                with open(settings_file, 'a') as f:
                    f.write('\n# Fix Django AutoField warnings\n')
                    f.write('DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"\n')
                
                logging.InstallLog.writeToFile("[fix_django_autofield_warnings] Added DEFAULT_AUTO_FIELD setting")
        
    except Exception as e:
        logging.InstallLog.writeToFile(f"[ERROR] {str(e)} [fix_django_autofield_warnings]")


def check_file_exists(file_path):
    """Check if a file or directory exists"""
    try:
        return os.path.exists(file_path)
    except:
        return False


# Set installation start time
import time
installation_start_time = time.time()


if __name__ == "__main__":
    main()
