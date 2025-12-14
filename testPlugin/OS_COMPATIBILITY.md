# OS Compatibility Guide - CyberPanel Test Plugin

## 🌐 Supported Operating Systems

The CyberPanel Test Plugin is designed to work seamlessly across all CyberPanel-supported operating systems with comprehensive multi-OS compatibility.

### ✅ Currently Supported OS

| Operating System | Version | Support Status | Python Version | Package Manager | Service Manager |
|------------------|---------|----------------|----------------|-----------------|-----------------|
| **Ubuntu** | 22.04 | ✅ Full Support | 3.10+ | apt-get | systemctl |
| **Ubuntu** | 20.04 | ✅ Full Support | 3.8+ | apt-get | systemctl |
| **Debian** | 13 | ✅ Full Support | 3.11+ | apt-get | systemctl |
| **Debian** | 12 | ✅ Full Support | 3.10+ | apt-get | systemctl |
| **Debian** | 11 | ✅ Full Support | 3.9+ | apt-get | systemctl |
| **AlmaLinux** | 10 | ✅ Full Support | 3.11+ | dnf | systemctl |
| **AlmaLinux** | 9 | ✅ Full Support | 3.9+ | dnf | systemctl |
| **AlmaLinux** | 8 | ✅ Full Support | 3.6+ | dnf/yum | systemctl |
| **RockyLinux** | 9 | ✅ Full Support | 3.9+ | dnf | systemctl |
| **RockyLinux** | 8 | ✅ Full Support | 3.6+ | dnf | systemctl |
| **RHEL** | 9 | ✅ Full Support | 3.9+ | dnf | systemctl |
| **RHEL** | 8 | ✅ Full Support | 3.6+ | dnf | systemctl |
| **CloudLinux** | 8 | ✅ Full Support | 3.6+ | yum | systemctl |
| **CentOS** | 9 | ✅ Full Support | 3.9+ | dnf | systemctl |

### 🔧 Third-Party OS Support

| Operating System | Compatibility | Notes |
|------------------|---------------|-------|
| **Fedora** | ✅ Compatible | Uses dnf package manager |
| **openEuler** | ⚠️ Limited | Community-supported, limited testing |
| **Other RHEL derivatives** | ⚠️ Limited | May work with AlmaLinux/RockyLinux packages |

## 🚀 Installation Compatibility

### Automatic OS Detection

The installation script automatically detects your operating system and configures the plugin accordingly:

```bash
# The script automatically detects:
# - OS name and version
# - Python executable path
# - Package manager (apt-get, dnf, yum)
# - Service manager (systemctl, service)
# - Web server (apache2, httpd)
```

### OS-Specific Configurations

#### Ubuntu/Debian Systems
```bash
# Package Manager: apt-get
# Python: python3
# Pip: pip3
# Service Manager: systemctl
# Web Server: apache2
# User/Group: cyberpanel:cyberpanel
```

#### RHEL-based Systems (AlmaLinux, RockyLinux, RHEL, CentOS)
```bash
# Package Manager: dnf (RHEL 8+) / yum (RHEL 7)
# Python: python3
# Pip: pip3
# Service Manager: systemctl
# Web Server: httpd
# User/Group: cyberpanel:cyberpanel
```

#### CloudLinux
```bash
# Package Manager: yum
# Python: python3
# Pip: pip3
# Service Manager: systemctl
# Web Server: httpd
# User/Group: cyberpanel:cyberpanel
```

## 🐍 Python Compatibility

### Supported Python Versions

| Python Version | Ubuntu 22.04 | Ubuntu 20.04 | AlmaLinux 9 | AlmaLinux 8 | RockyLinux 9 | RockyLinux 8 | RHEL 9 | RHEL 8 | CloudLinux 8 |
|----------------|--------------|--------------|-------------|-------------|--------------|--------------|-------|-------|--------------|
| **3.6** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **3.7** | ❌ | ❌ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **3.8** | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ❌ | ✅ | ✅ |
| **3.9** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **3.10** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **3.11** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **3.12** | ✅ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### Python Path Detection

The plugin automatically detects the correct Python executable:

```python
# Detection order:
1. python3.12
2. python3.11
3. python3.10
4. python3.9
5. python3.8
6. python3.7
7. python3.6
8. python3
9. python (fallback)
```

## 📦 Package Manager Compatibility

### Ubuntu/Debian (apt-get)
```bash
# Required packages
apt-get update
apt-get install -y python3 python3-pip python3-venv git curl
apt-get install -y build-essential python3-dev

# Python packages
pip3 install Django>=2.2,<4.0 django-cors-headers Pillow requests psutil
```

### RHEL-based (dnf/yum)
```bash
# RHEL 8+ (dnf)
dnf install -y python3 python3-pip python3-devel git curl
dnf install -y gcc gcc-c++ make

# RHEL 7 (yum)
yum install -y python3 python3-pip python3-devel git curl
yum install -y gcc gcc-c++ make

# Python packages
pip3 install Django>=2.2,<4.0 django-cors-headers Pillow requests psutil
```

### CloudLinux (yum)
```bash
# Required packages
yum install -y python3 python3-pip python3-devel git curl
yum install -y gcc gcc-c++ make

# Python packages
pip3 install Django>=2.2,<4.0 django-cors-headers Pillow requests psutil
```

## 🔧 Service Management Compatibility

### systemd (All supported OS)
```bash
# Service management commands
systemctl start lscpd
systemctl restart lscpd
systemctl status lscpd
systemctl enable lscpd

# Web server management
systemctl start apache2    # Ubuntu/Debian
systemctl start httpd      # RHEL-based
systemctl restart apache2  # Ubuntu/Debian
systemctl restart httpd    # RHEL-based
```

### Legacy init.d (Fallback)
```bash
# Service management commands
service lscpd start
service lscpd restart
service lscpd status

# Web server management
service apache2 start    # Ubuntu/Debian
service httpd start      # RHEL-based
```

## 🌐 Web Server Compatibility

### Apache2 (Ubuntu/Debian)
```bash
# Configuration paths
/etc/apache2/apache2.conf
/etc/apache2/sites-available/
/etc/apache2/sites-enabled/

# Service management
systemctl start apache2
systemctl restart apache2
systemctl status apache2
```

### HTTPD (RHEL-based)
```bash
# Configuration paths
/etc/httpd/conf/httpd.conf
/etc/httpd/conf.d/

# Service management
systemctl start httpd
systemctl restart httpd
systemctl status httpd
```

## 🔐 Security Compatibility

### SELinux (RHEL-based systems)
```bash
# Check SELinux status
sestatus

# Set proper context for plugin files
setsebool -P httpd_can_network_connect 1
chcon -R -t httpd_exec_t /usr/local/CyberCP/testPlugin/
```

### AppArmor (Ubuntu/Debian)
```bash
# Check AppArmor status
aa-status

# Allow Apache to access plugin files
aa-complain apache2
```

### Firewall Compatibility
```bash
# Ubuntu/Debian (ufw)
ufw allow 8090/tcp
ufw allow 80/tcp
ufw allow 443/tcp

# RHEL-based (firewalld)
firewall-cmd --permanent --add-port=8090/tcp
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload

# iptables (legacy)
iptables -A INPUT -p tcp --dport 8090 -j ACCEPT
iptables -A INPUT -p tcp --dport 80 -j ACCEPT
iptables -A INPUT -p tcp --dport 443 -j ACCEPT
```

## 🧪 Testing Compatibility

### Run Compatibility Test
```bash
# Navigate to plugin directory
cd /usr/local/CyberCP/testPlugin

# Run compatibility test
python3 test_os_compatibility.py

# Or make it executable and run
chmod +x test_os_compatibility.py
./test_os_compatibility.py
```

### Test Results
The compatibility test checks:
- ✅ OS detection and version
- ✅ Python installation and version
- ✅ Package manager availability
- ✅ Service manager functionality
- ✅ Web server configuration
- ✅ File permissions and ownership
- ✅ Network connectivity
- ✅ CyberPanel integration

### Sample Output
```
🔍 Testing OS Compatibility for CyberPanel Test Plugin
============================================================

📋 Testing OS Detection...
   ✅ OS: ubuntu 22.04 (x86_64)
   ✅ Supported: True

🐍 Testing Python Detection...
   ✅ Python: Python 3.10.12
   ✅ Path: /usr/bin/python3
   ✅ Pip: /usr/bin/pip3
   ✅ Compatible: True

📦 Testing Package Manager Detection...
   ✅ Package Manager: apt-get
   ✅ Available: True

🔧 Testing Service Manager Detection...
   ✅ Service Manager: systemctl
   ✅ Web Server: apache2
   ✅ Available: True

🌐 Testing Web Server Detection...
   ✅ Web Server: apache2
   ✅ Installed: True

🔐 Testing File Permissions...
   ✅ Plugin Directory: /home/cyberpanel/plugins
   ✅ CyberPanel Directory: /usr/local/CyberCP

🌍 Testing Network Connectivity...
   ✅ GitHub: True
   ✅ Internet: True

⚡ Testing CyberPanel Integration...
   ✅ CyberPanel Installed: True
   ✅ Settings File: True
   ✅ URLs File: True
   ✅ LSCPD Service: True

============================================================
📊 COMPATIBILITY TEST RESULTS
============================================================
Total Tests: 8
✅ Passed: 8
⚠️  Warnings: 0
❌ Failed: 0

🎉 All tests passed! The plugin is compatible with this OS.
```

## 🚨 Troubleshooting

### Common Issues by OS

#### Ubuntu/Debian Issues
```bash
# Python not found
sudo apt-get update
sudo apt-get install -y python3 python3-pip

# Permission denied
sudo chown -R cyberpanel:cyberpanel /home/cyberpanel/plugins
sudo chown -R cyberpanel:cyberpanel /usr/local/CyberCP/testPlugin

# Service not starting
sudo systemctl daemon-reload
sudo systemctl restart lscpd
```

#### RHEL-based Issues
```bash
# Python not found
sudo dnf install -y python3 python3-pip
# or
sudo yum install -y python3 python3-pip

# SELinux issues
sudo setsebool -P httpd_can_network_connect 1
sudo chcon -R -t httpd_exec_t /usr/local/CyberCP/testPlugin/

# Permission denied
sudo chown -R cyberpanel:cyberpanel /home/cyberpanel/plugins
sudo chown -R cyberpanel:cyberpanel /usr/local/CyberCP/testPlugin
```

#### CloudLinux Issues
```bash
# Python not found
sudo yum install -y python3 python3-pip

# CageFS issues
cagefsctl --enable cyberpanel
cagefsctl --update

# Permission denied
sudo chown -R cyberpanel:cyberpanel /home/cyberpanel/plugins
sudo chown -R cyberpanel:cyberpanel /usr/local/CyberCP/testPlugin
```

### Debug Commands
```bash
# Check OS information
cat /etc/os-release
uname -a

# Check Python installation
python3 --version
which python3
which pip3

# Check services
systemctl status lscpd
systemctl status apache2  # Ubuntu/Debian
systemctl status httpd    # RHEL-based

# Check file permissions
ls -la /home/cyberpanel/plugins/
ls -la /usr/local/CyberCP/testPlugin/

# Check CyberPanel logs
tail -f /home/cyberpanel/logs/cyberpanel.log
tail -f /home/cyberpanel/logs/django.log
```

## 📋 Installation Checklist

### Pre-Installation
- [ ] Verify OS is supported
- [ ] Check Python 3.6+ is installed
- [ ] Ensure CyberPanel is installed and running
- [ ] Verify internet connectivity
- [ ] Check available disk space (minimum 100MB)

### Installation
- [ ] Download installation script
- [ ] Run as root user
- [ ] Monitor installation output
- [ ] Verify plugin files are created
- [ ] Check Django settings are updated
- [ ] Confirm URL configuration is added

### Post-Installation
- [ ] Test plugin access via web interface
- [ ] Verify all features work correctly
- [ ] Check security settings
- [ ] Run compatibility test
- [ ] Review installation logs

## 🔄 Updates and Maintenance

### Updating the Plugin
```bash
# Navigate to plugin directory
cd /usr/local/CyberCP/testPlugin

# Pull latest changes
git pull origin main

# Restart services
sudo systemctl restart lscpd
sudo systemctl restart apache2  # Ubuntu/Debian
sudo systemctl restart httpd    # RHEL-based
```

### Uninstalling the Plugin
```bash
# Run uninstall script
sudo ./install.sh --uninstall

# Or manually remove
sudo rm -rf /usr/local/CyberCP/testPlugin
sudo rm -f /home/cyberpanel/plugins/testPlugin
```

## 📞 Support

### OS-Specific Support
- **Ubuntu/Debian**: Check Ubuntu/Debian documentation
- **RHEL-based**: Check Red Hat documentation
- **CloudLinux**: Check CloudLinux documentation

### Plugin Support
- **GitHub Issues**: https://github.com/cyberpanel/testPlugin/issues
- **CyberPanel Forums**: https://forums.cyberpanel.net/
- **Documentation**: https://raw.githubusercontent.com/die2mrw007/cyberpanel/stable/docs/

---

**Last Updated**: September 2025  
**Compatibility Version**: 1.0.0  
**Next Review**: March 2026
