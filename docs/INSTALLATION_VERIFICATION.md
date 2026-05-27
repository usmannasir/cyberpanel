# CyberPanel Installation Verification Guide

## 🎯 Overview

This guide provides verification steps to ensure CyberPanel installation and upgrade commands work correctly across all supported operating systems.

## ✅ Installation Command Verification

### **Primary Installation Command**
```bash
sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
```

### **Verification Steps**

#### 1. **Test URL Accessibility**
```bash
# Test if install script is accessible
curl -I https://cyberpanel.net/install.sh

# Expected response: HTTP/1.1 200 OK
# Content-Type: text/plain
```

#### 2. **Test Download**
```bash
# Download and check script content
curl -s https://cyberpanel.net/install.sh | head -20

# Should show script header and OS detection logic
```

#### 3. **Test with wget fallback**
```bash
# Test wget fallback
wget -qO- https://cyberpanel.net/install.sh | head -20

# Should show same content as curl
```

## ✅ Upgrade Command Verification

### **Primary Upgrade Command**
```bash
sh <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh || wget -O - https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh)
```

### **Verification Steps**

#### 1. **Test URL Accessibility**
```bash
# Test if upgrade script is accessible
curl -I https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh

# Expected response: HTTP/1.1 200 OK
# Content-Type: text/plain
```

#### 2. **Test Download**
```bash
# Download and check script content
curl -s https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh | head -20

# Should show script header and upgrade logic
```

## 🐧 Operating System Support Verification

### **Ubuntu Family**
- **Ubuntu 24.04.3**: ✅ Supported
- **Ubuntu 22.04**: ✅ Supported  
- **Ubuntu 20.04**: ✅ Supported

### **Debian Family**
- **Debian 13**: ✅ Supported
- **Debian 12**: ✅ Supported
- **Debian 11**: ✅ Supported

### **RHEL Family**
- **AlmaLinux 10**: ✅ Supported
- **AlmaLinux 9**: ✅ Supported
- **AlmaLinux 8**: ✅ Supported
- **RockyLinux 9**: ✅ Supported
- **RockyLinux 8**: ✅ Supported
- **RHEL 9**: ✅ Supported
- **RHEL 8**: ✅ Supported

### **Other Distributions**
- **CloudLinux 8**: ✅ Supported
- **CentOS 9**: ✅ Supported
- **CentOS Stream 9**: ✅ Supported

## 🔧 Installation Process Verification

### **What the Installation Script Does**

1. **System Detection**
   - Detects operating system and version
   - Checks architecture (x86_64 required)
   - Verifies system requirements

2. **Dependency Installation**
   - Installs Python 3.8+
   - Installs Git
   - Installs system packages (curl, wget, etc.)

3. **Web Server Setup**
   - Downloads and installs OpenLiteSpeed
   - Configures web server settings
   - Sets up virtual hosts

4. **Database Setup**
   - Installs and configures MariaDB
   - Creates CyberPanel database
   - Sets up database users

5. **CyberPanel Installation**
   - Downloads CyberPanel source code
   - Installs Python dependencies
   - Configures Django settings
   - Runs database migrations

6. **Service Configuration**
   - Creates systemd services
   - Starts all required services
   - Configures firewall rules

7. **Final Setup**
   - Creates admin user
   - Sets up file permissions
   - Provides access information

## 🔄 Upgrade Process Verification

### **What the Upgrade Script Does**

1. **Backup Creation**
   - Creates backup of current installation
   - Backs up database and configuration files
   - Stores backup in safe location

2. **Source Update**
   - Downloads latest CyberPanel source code
   - Updates all files to latest version
   - Preserves custom configurations

3. **Dependency Update**
   - Updates Python packages
   - Updates system dependencies
   - Handles version conflicts

4. **Database Migration**
   - Runs Django migrations
   - Updates database schema
   - Preserves existing data

5. **Service Restart**
   - Restarts all CyberPanel services
   - Verifies service status
   - Reports any issues

## 🧪 Testing Procedures

### **Pre-Installation Testing**

#### 1. **System Requirements Check**
```bash
# Check OS version
cat /etc/os-release

# Check architecture
uname -m

# Check available memory
free -h

# Check available disk space
df -h

# Check network connectivity
ping -c 4 google.com
```

#### 2. **Dependency Check**
```bash
# Check if Python is available
python3 --version

# Check if Git is available
git --version

# Check if curl/wget are available
curl --version
wget --version
```

### **Installation Testing**

#### 1. **Dry Run Test**
```bash
# Download and examine script without executing
curl -s https://cyberpanel.net/install.sh > install_test.sh
chmod +x install_test.sh

# Review script content
head -50 install_test.sh
```

#### 2. **Full Installation Test**
```bash
# Run installation in test environment
sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)

# Monitor installation process
# Check for any errors or warnings
```

### **Post-Installation Verification**

#### 1. **Service Status Check**
```bash
# Check CyberPanel service
systemctl status lscpd

# Check web server
systemctl status lsws

# Check database
systemctl status mariadb
```

#### 2. **Web Interface Test**
```bash
# Test web interface accessibility
curl -I http://localhost:8090

# Expected: HTTP/1.1 200 OK
```

#### 3. **Database Connection Test**
```bash
# Test database connection
mysql -u root -p -e "SHOW DATABASES;"

# Should show CyberPanel database
```

## 🐛 Common Issues and Solutions

### **Installation Issues**

#### 1. **"Command not found" Errors**
**Problem**: Required commands not available
**Solution**:
```bash
# Install missing packages
# Ubuntu/Debian
sudo apt update && sudo apt install curl wget git python3

# RHEL/CentOS/AlmaLinux/RockyLinux
sudo yum install curl wget git python3
```

#### 2. **Permission Denied Errors**
**Problem**: Insufficient privileges
**Solution**:
```bash
# Run with sudo
sudo sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
```

#### 3. **Network Connectivity Issues**
**Problem**: Cannot download installation script
**Solution**:
```bash
# Check internet connection
ping -c 4 google.com

# Check DNS resolution
nslookup cyberpanel.net

# Try alternative download method
wget https://cyberpanel.net/install.sh
chmod +x install.sh
sudo ./install.sh
```

#### 4. **Port Already in Use**
**Problem**: Port 8090 already occupied
**Solution**:
```bash
# Check what's using port 8090
sudo netstat -tlnp | grep :8090

# Kill process if necessary
sudo kill -9 <PID>

# Or change CyberPanel port in configuration
```

### **Upgrade Issues**

#### 1. **Backup Creation Failed**
**Problem**: Cannot create backup
**Solution**:
```bash
# Check disk space
df -h

# Free up space if necessary
sudo apt autoremove
sudo apt autoclean

# Or specify different backup location
```

#### 2. **Database Migration Failed**
**Problem**: Database migration errors
**Solution**:
```bash
# Check database status
systemctl status mariadb

# Restart database service
sudo systemctl restart mariadb

# Run migration manually
cd /usr/local/CyberCP
python3 manage.py migrate
```

#### 3. **Service Restart Failed**
**Problem**: Services won't restart
**Solution**:
```bash
# Check service logs
journalctl -u lscpd -f

# Restart services manually
sudo systemctl restart lscpd
sudo systemctl restart lsws
```

## 📊 Verification Checklist

### **Installation Verification**
- [ ] Installation script downloads successfully
- [ ] All dependencies installed correctly
- [ ] Web server starts and responds
- [ ] Database server starts and responds
- [ ] CyberPanel web interface accessible
- [ ] Admin user can log in
- [ ] All services running properly
- [ ] No error messages in logs

### **Upgrade Verification**
- [ ] Upgrade script downloads successfully
- [ ] Backup created successfully
- [ ] Source code updated correctly
- [ ] Dependencies updated properly
- [ ] Database migrations completed
- [ ] Services restarted successfully
- [ ] Web interface still accessible
- [ ] Data integrity maintained

## 🔍 Monitoring and Logging

### **Installation Logs**
```bash
# Check installation logs
tail -f /root/cyberpanel-install.log

# Check system logs
journalctl -f
```

### **Service Logs**
```bash
# Check CyberPanel logs
tail -f /usr/local/lscp/logs/error.log

# Check web server logs
tail -f /usr/local/lsws/logs/error.log

# Check database logs
tail -f /var/log/mysql/error.log
```

## 🆘 Getting Help

### **If Installation Fails**
1. **Check the logs** for specific error messages
2. **Verify system requirements** are met
3. **Try alternative installation methods** (wget, manual download)
4. **Use troubleshooting commands** from the README
5. **Contact support** with detailed error information

### **If Upgrade Fails**
1. **Restore from backup** if available
2. **Check service status** and restart if needed
3. **Run manual upgrade** steps
4. **Use troubleshooting commands** from the README
5. **Contact support** with upgrade logs

### **Support Resources**
- **CyberPanel Forums**: https://community.cyberpanel.net
- **GitHub Issues**: https://github.com/usmannasir/cyberpanel/issues
- **Discord Server**: https://discord.gg/cyberpanel

---

**Note**: This verification guide ensures CyberPanel installation and upgrade processes work correctly across all supported operating systems. Always test in a non-production environment first.

*Last updated: January 2025*
