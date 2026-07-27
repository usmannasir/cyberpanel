# -*- coding: utf-8 -*-
"""
Operating System Configuration for Test Plugin
Provides OS-specific configurations and compatibility checks
"""
import os
import platform
import subprocess
import sys
from pathlib import Path


class OSConfig:
    """Operating System Configuration Manager"""
    
    def __init__(self):
        self.os_name = self._detect_os_name()
        self.os_version = self._detect_os_version()
        self.os_arch = platform.machine()
        self.python_path = self._detect_python_path()
        self.pip_path = self._detect_pip_path()
        self.service_manager = self._detect_service_manager()
        self.web_server = self._detect_web_server()
        self.package_manager = self._detect_package_manager()
        
    def _detect_os_name(self):
        """Detect operating system name"""
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('ID='):
                        return line.split('=')[1].strip().strip('"')
        except FileNotFoundError:
            pass
        
        # Fallback detection
        if os.path.exists('/etc/redhat-release'):
            return 'rhel'
        elif os.path.exists('/etc/debian_version'):
            return 'debian'
        else:
            return platform.system().lower()
    
    def _detect_os_version(self):
        """Detect operating system version"""
        try:
            with open('/etc/os-release', 'r') as f:
                for line in f:
                    if line.startswith('VERSION_ID='):
                        return line.split('=')[1].strip().strip('"')
        except FileNotFoundError:
            pass
        
        # Fallback detection
        if os.path.exists('/etc/redhat-release'):
            try:
                with open('/etc/redhat-release', 'r') as f:
                    content = f.read()
                    import re
                    match = re.search(r'(\d+\.\d+)', content)
                    if match:
                        return match.group(1)
            except:
                pass
        
        return platform.release()
    
    def _detect_python_path(self):
        """Detect Python executable path"""
        # Try different Python commands
        python_commands = ['python3', 'python3.11', 'python3.10', 'python3.9', 'python3.8', 'python3.7', 'python3.6', 'python']
        
        for cmd in python_commands:
            try:
                result = subprocess.run([cmd, '--version'], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
                if result.returncode == 0:
                    # Check if it's Python 3.6+
                    version = result.stdout.strip()
                    if 'Python 3' in version:
                        version_num = version.split()[1]
                        major, minor = map(int, version_num.split('.')[:2])
                        if major == 3 and minor >= 6:
                            return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
                continue
        
        # Fallback to sys.executable
        return sys.executable
    
    def _detect_pip_path(self):
        """Detect pip executable path"""
        # Try different pip commands
        pip_commands = ['pip3', 'pip3.11', 'pip3.10', 'pip3.9', 'pip3.8', 'pip3.7', 'pip3.6', 'pip']
        
        for cmd in pip_commands:
            try:
                result = subprocess.run([cmd, '--version'], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
                if result.returncode == 0:
                    return cmd
            except (subprocess.TimeoutExpired, FileNotFoundError):
                continue
        
        # Fallback
        return 'pip3'
    
    def _detect_service_manager(self):
        """Detect service manager (systemd, init.d, etc.)"""
        if os.path.exists('/bin/systemctl') or os.path.exists('/usr/bin/systemctl'):
            return 'systemctl'
        elif os.path.exists('/etc/init.d'):
            return 'service'
        else:
            return 'systemctl'  # Default to systemctl
    
    def _detect_web_server(self):
        """Detect web server"""
        if os.path.exists('/etc/apache2') or os.path.exists('/etc/httpd'):
            if os.path.exists('/etc/apache2'):
                return 'apache2'
            else:
                return 'httpd'
        else:
            return 'httpd'  # Default
    
    def _detect_package_manager(self):
        """Detect package manager"""
        if os.path.exists('/usr/bin/dnf'):
            return 'dnf'
        elif os.path.exists('/usr/bin/yum'):
            return 'yum'
        elif os.path.exists('/usr/bin/apt'):
            return 'apt'
        elif os.path.exists('/usr/bin/apt-get'):
            return 'apt-get'
        else:
            return 'unknown'
    
    def get_os_info(self):
        """Get comprehensive OS information"""
        return {
            'name': self.os_name,
            'version': self.os_version,
            'architecture': self.os_arch,
            'python_path': self.python_path,
            'pip_path': self.pip_path,
            'service_manager': self.service_manager,
            'web_server': self.web_server,
            'package_manager': self.package_manager,
            'platform': platform.platform(),
            'python_version': sys.version
        }
    
    def is_supported_os(self):
        """Check if the current OS is supported"""
        supported_os = [
            'ubuntu', 'debian', 'almalinux', 'rocky', 'rhel', 
            'centos', 'cloudlinux', 'fedora'
        ]
        return self.os_name in supported_os
    
    def get_os_specific_config(self):
        """Get OS-specific configuration"""
        configs = {
            'ubuntu': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'apache2',
                'package_manager': 'apt-get',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            },
            'debian': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'apache2',
                'package_manager': 'apt-get',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            },
            'almalinux': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'httpd',
                'package_manager': 'dnf',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            },
            'rocky': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'httpd',
                'package_manager': 'dnf',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            },
            'rhel': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'httpd',
                'package_manager': 'dnf',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            },
            'centos': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'httpd',
                'package_manager': 'dnf',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            },
            'cloudlinux': {
                'python_cmd': 'python3',
                'pip_cmd': 'pip3',
                'service_cmd': 'systemctl',
                'web_server': 'httpd',
                'package_manager': 'yum',
                'cyberpanel_user': 'cyberpanel',
                'cyberpanel_group': 'cyberpanel'
            }
        }
        
        return configs.get(self.os_name, configs['ubuntu'])  # Default to Ubuntu config
    
    def get_python_requirements(self):
        """Get Python requirements for the current OS"""
        base_requirements = [
            'Django>=2.2,<4.0',
            'django-cors-headers',
            'Pillow',
            'requests',
            'psutil'
        ]
        
        # OS-specific requirements
        os_requirements = {
            'ubuntu': [],
            'debian': [],
            'almalinux': ['python3-devel', 'gcc'],
            'rocky': ['python3-devel', 'gcc'],
            'rhel': ['python3-devel', 'gcc'],
            'centos': ['python3-devel', 'gcc'],
            'cloudlinux': ['python3-devel', 'gcc']
        }
        
        return base_requirements + os_requirements.get(self.os_name, [])
    
    def get_install_commands(self):
        """Get OS-specific installation commands"""
        config = self.get_os_specific_config()
        
        if config['package_manager'] in ['apt-get', 'apt']:
            return {
                'update': 'apt-get update',
                'install_python': 'apt-get install -y python3 python3-pip python3-venv',
                'install_git': 'apt-get install -y git',
                'install_curl': 'apt-get install -y curl',
                'install_dev_tools': 'apt-get install -y build-essential python3-dev'
            }
        elif config['package_manager'] == 'dnf':
            return {
                'update': 'dnf update -y',
                'install_python': 'dnf install -y python3 python3-pip python3-devel',
                'install_git': 'dnf install -y git',
                'install_curl': 'dnf install -y curl',
                'install_dev_tools': 'dnf install -y gcc gcc-c++ make python3-devel'
            }
        elif config['package_manager'] == 'yum':
            return {
                'update': 'yum update -y',
                'install_python': 'yum install -y python3 python3-pip python3-devel',
                'install_git': 'yum install -y git',
                'install_curl': 'yum install -y curl',
                'install_dev_tools': 'yum install -y gcc gcc-c++ make python3-devel'
            }
        else:
            # Fallback to Ubuntu commands
            return {
                'update': 'apt-get update',
                'install_python': 'apt-get install -y python3 python3-pip python3-venv',
                'install_git': 'apt-get install -y git',
                'install_curl': 'apt-get install -y curl',
                'install_dev_tools': 'apt-get install -y build-essential python3-dev'
            }
    
    def validate_environment(self):
        """Validate the current environment"""
        issues = []
        
        # Check Python version
        try:
            result = subprocess.run([self.python_path, '--version'], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                if 'Python 3' in version:
                    version_num = version.split()[1]
                    major, minor = map(int, version_num.split('.')[:2])
                    if major < 3 or (major == 3 and minor < 6):
                        issues.append(f"Python 3.6+ required, found {version}")
                else:
                    issues.append(f"Python 3 required, found {version}")
            else:
                issues.append("Python not found or not working")
        except Exception as e:
            issues.append(f"Error checking Python: {e}")
        
        # Check pip
        try:
            result = subprocess.run([self.pip_path, '--version'], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=5)
            if result.returncode != 0:
                issues.append("pip not found or not working")
        except Exception as e:
            issues.append(f"Error checking pip: {e}")
        
        # Check if OS is supported
        if not self.is_supported_os():
            issues.append(f"Unsupported operating system: {self.os_name}")
        
        return issues
    
    def get_compatibility_info(self):
        """Get compatibility information for the current OS"""
        return {
            'os_supported': self.is_supported_os(),
            'python_available': self.python_path is not None,
            'pip_available': self.pip_path is not None,
            'service_manager': self.service_manager,
            'web_server': self.web_server,
            'package_manager': self.package_manager,
            'validation_issues': self.validate_environment()
        }


# Global instance
os_config = OSConfig()


def get_os_config():
    """Get the global OS configuration instance"""
    return os_config


def is_os_supported():
    """Check if the current OS is supported"""
    return os_config.is_supported_os()


def get_python_path():
    """Get the Python executable path"""
    return os_config.python_path


def get_pip_path():
    """Get the pip executable path"""
    return os_config.pip_path
