#!/usr/bin/env python3
"""
Simplified CyberPanel Installation Script
Based on 2.4.4 approach but with AlmaLinux 9 fixes
"""

import os
import sys
import subprocess
import platform

class SimpleInstaller:
    def __init__(self):
        self.distro = self.detect_os()
        self.mysql_password = "cyberpanel123"
        
    def detect_os(self):
        """Detect operating system"""
        try:
            with open('/etc/os-release', 'r') as f:
                content = f.read()
                
            if 'AlmaLinux 9' in content:
                return 'almalinux9'
            elif 'AlmaLinux 8' in content:
                return 'almalinux8'
            elif 'Ubuntu' in content:
                return 'ubuntu'
            elif 'CentOS' in content:
                return 'centos'
            else:
                return 'unknown'
        except:
            return 'unknown'
    
    def run_command(self, command, shell=True):
        """Run system command"""
        try:
            result = subprocess.run(command, shell=shell, capture_output=True, text=True)
            return result.returncode == 0, result.stdout, result.stderr
        except Exception as e:
            return False, "", str(e)
    
    def install_basic_dependencies(self):
        """Install basic dependencies like 2.4.4"""
        print("Installing basic dependencies...")
        
        if self.distro == 'almalinux9':
            # AlmaLinux 9 specific - minimal approach
            commands = [
                "dnf update -y",
                "dnf install -y epel-release",
                "dnf install -y wget curl unzip zip rsync firewalld git python3 python3-pip",
                "dnf install -y mariadb-server mariadb-client",
                "dnf install -y ImageMagick gd libicu oniguruma aspell libc-client",
                "systemctl enable mariadb",
                "systemctl start mariadb"
            ]
        elif self.distro == 'almalinux8':
            commands = [
                "yum update -y",
                "yum install -y epel-release",
                "yum install -y wget curl unzip zip rsync firewalld git python3 python3-pip",
                "yum install -y mariadb-server mariadb-client",
                "yum install -y ImageMagick gd libicu oniguruma aspell libc-client",
                "systemctl enable mariadb",
                "systemctl start mariadb"
            ]
        else:
            # Default commands for other OS
            commands = [
                "apt update -y" if 'ubuntu' in self.distro else "yum update -y",
                "apt install -y wget curl unzip zip rsync git python3 python3-pip" if 'ubuntu' in self.distro else "yum install -y wget curl unzip zip rsync git python3 python3-pip"
            ]
        
        for cmd in commands:
            success, stdout, stderr = self.run_command(cmd)
            if not success:
                print(f"Warning: Command failed: {cmd}")
                print(f"Error: {stderr}")
    
    def setup_mysql(self):
        """Setup MySQL with simple approach"""
        print("Setting up MySQL...")
        
        # Create password file
        os.makedirs('/etc/cyberpanel', exist_ok=True)
        with open('/etc/cyberpanel/mysqlPassword', 'w') as f:
            f.write(self.mysql_password)
        os.chmod('/etc/cyberpanel/mysqlPassword', 0o600)
        
        # Secure MySQL installation
        mysql_secure_cmd = f"""
        mysql -u root -e "ALTER USER 'root'@'localhost' IDENTIFIED BY '{self.mysql_password}';"
        mysql -u root -p{self.mysql_password} -e "DELETE FROM mysql.user WHERE User='';"
        mysql -u root -p{self.mysql_password} -e "DELETE FROM mysql.user WHERE User='root' AND Host NOT IN ('localhost', '127.0.0.1', '::1');"
        mysql -u root -p{self.mysql_password} -e "DROP DATABASE IF EXISTS test;"
        mysql -u root -p{self.mysql_password} -e "DELETE FROM mysql.db WHERE Db='test' OR Db='test\\_%';"
        mysql -u root -p{self.mysql_password} -e "FLUSH PRIVILEGES;"
        """
        
        self.run_command(mysql_secure_cmd)
    
    def install_cyberpanel(self):
        """Install CyberPanel using the simple approach"""
        print("Installing CyberPanel...")
        
        # Download and run the main installer
        commands = [
            "rm -f cyberpanel.sh",
            "curl -o cyberpanel.sh https://cyberpanel.sh/?dl&AlmaLinux9" if self.distro == 'almalinux9' else "curl -o cyberpanel.sh https://cyberpanel.sh/?dl&CentOS8",
            "chmod +x cyberpanel.sh",
            "./cyberpanel.sh"
        ]
        
        for cmd in commands:
            success, stdout, stderr = self.run_command(cmd)
            if not success:
                print(f"Error running: {cmd}")
                print(f"Error: {stderr}")
                return False
        
        return True
    
    def install(self):
        """Main installation process"""
        print("Starting simplified CyberPanel installation...")
        print(f"Detected OS: {self.distro}")
        
        # Install basic dependencies
        self.install_basic_dependencies()
        
        # Setup MySQL
        self.setup_mysql()
        
        # Install CyberPanel
        if self.install_cyberpanel():
            print("CyberPanel installation completed successfully!")
        else:
            print("CyberPanel installation failed!")

if __name__ == "__main__":
    installer = SimpleInstaller()
    installer.install()
