# Ubuntu 24.04.3 LTS Troubleshooting Guide for CyberPanel

## Overview

This guide provides Ubuntu 24.04.3 LTS-specific troubleshooting information for CyberPanel installation and operation issues.

## System Information

- **OS**: Ubuntu 24.04.3 LTS (Noble Numbat)
- **Architecture**: x86_64
- **Support Status**: Full Support until April 2029
- **Package Manager**: APT (Advanced Package Tool)

## Ubuntu-Specific Commands

### **System Status Checks**

```bash
# Check Ubuntu version
lsb_release -a
cat /etc/os-release

# Check CyberPanel service status
sudo systemctl status lscpd

# Check Apache2 status (Ubuntu uses Apache2)
sudo systemctl status apache2

# Check if CyberPanel is accessible
curl -I http://localhost:8090
```

### **Package Management**

```bash
# Update package lists
sudo apt update

# Upgrade system packages
sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git

# Check for broken packages
sudo apt --fix-broken install

# Clean package cache
sudo apt autoremove -y
sudo apt autoclean
```

### **Ubuntu-Specific Log Locations**

```bash
# CyberPanel logs
tail -f /usr/local/lscp/logs/error.log

# Apache2 logs (Ubuntu default)
tail -f /var/log/apache2/error.log
tail -f /var/log/apache2/access.log

# System logs
tail -f /var/log/syslog
journalctl -u lscpd -f
journalctl -u apache2 -f

# Installation logs
tail -f /root/cyberpanel-install.log
```

## Common Ubuntu 24.04.3 Issues

### **1. Package Installation Failures**

**Issue**: APT package installation errors during CyberPanel setup

**Symptoms**:
- `E: Unable to locate package` errors
- `E: Package has no installation candidate` errors
- Repository connection failures

**Solution**:
```bash
# Update package lists
sudo apt update

# Fix broken packages
sudo apt --fix-broken install

# Clean package cache
sudo apt clean
sudo apt autoclean

# Retry installation
sudo ./install.sh
```

### **2. Apache2 Configuration Issues**

**Issue**: Apache2 service conflicts or configuration problems

**Symptoms**:
- Apache2 fails to start
- Port 80/443 conflicts
- Configuration syntax errors

**Solution**:
```bash
# Check Apache2 configuration
sudo apache2ctl configtest

# Check for port conflicts
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443

# Restart Apache2
sudo systemctl restart apache2

# Check Apache2 status
sudo systemctl status apache2
```

### **3. PHP Version Issues**

**Issue**: PHP version compatibility problems

**Symptoms**:
- PHP version not supported
- Missing PHP extensions
- PHP configuration errors

**Solution**:
```bash
# Check current PHP version
php -v

# Install PHP 8.1 (recommended for CyberPanel)
sudo apt install -y php8.1 php8.1-cli php8.1-common php8.1-mysql php8.1-zip php8.1-gd php8.1-mbstring php8.1-curl php8.1-xml php8.1-bcmath

# Enable PHP 8.1
sudo a2enmod php8.1

# Restart Apache2
sudo systemctl restart apache2
```

### **4. Firewall Configuration (UFW)**

**Issue**: Ubuntu's UFW firewall blocking CyberPanel ports

**Symptoms**:
- Cannot access CyberPanel web interface
- Connection refused errors
- Port access denied

**Solution**:
```bash
# Check UFW status
sudo ufw status

# Allow CyberPanel ports
sudo ufw allow 8090/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw allow 21/tcp
sudo ufw allow 25/tcp
sudo ufw allow 53/tcp
sudo ufw allow 587/tcp
sudo ufw allow 993/tcp
sudo ufw allow 995/tcp

# Enable UFW if not already enabled
sudo ufw enable
```

### **5. SystemD Service Issues**

**Issue**: CyberPanel service not starting properly

**Symptoms**:
- `systemctl status lscpd` shows failed
- Service won't start on boot
- Service dependency errors

**Solution**:
```bash
# Check service status
sudo systemctl status lscpd

# Check service logs
sudo journalctl -u lscpd -f

# Reload systemd configuration
sudo systemctl daemon-reload

# Restart CyberPanel service
sudo systemctl restart lscpd

# Enable service to start on boot
sudo systemctl enable lscpd
```

### **6. Permission Issues**

**Issue**: File permission problems specific to Ubuntu

**Symptoms**:
- Permission denied errors
- Cannot write to directories
- File ownership issues

**Solution**:
```bash
# Check file permissions
ls -la /usr/local/CyberCP/

# Fix ownership (replace 'cyberpanel' with actual user)
sudo chown -R cyberpanel:cyberpanel /usr/local/CyberCP/

# Fix permissions
sudo chmod -R 755 /usr/local/CyberCP/

# Check user groups
groups cyberpanel
```

## Ubuntu-Specific Diagnostic Commands

### **System Information**

```bash
# Check Ubuntu version and details
lsb_release -a
cat /etc/os-release

# Check kernel version
uname -r

# Check system architecture
arch
lscpu
```

### **Network Configuration**

```bash
# Check network interfaces
ip addr show
ip route show

# Check DNS resolution
nslookup google.com
dig google.com

# Test connectivity
ping -c 4 google.com
```

### **Disk and Memory Usage**

```bash
# Check disk usage
df -h
du -sh /usr/local/CyberCP/

# Check memory usage
free -h
cat /proc/meminfo

# Check swap usage
swapon -s
```

## Ubuntu 24.04.3 Specific Considerations

### **1. Snap Package Conflicts**

Ubuntu 24.04.3 comes with many snap packages that might conflict:

```bash
# Check for snap packages
snap list

# Remove conflicting snap packages if needed
sudo snap remove package-name
```

### **2. SystemD-Resolved**

Ubuntu 24.04.3 uses systemd-resolved for DNS:

```bash
# Check DNS resolution
systemd-resolve --status

# Restart DNS resolver if needed
sudo systemctl restart systemd-resolved
```

### **3. AppArmor**

Ubuntu 24.04.3 has AppArmor enabled by default:

```bash
# Check AppArmor status
sudo aa-status

# Check AppArmor logs
sudo dmesg | grep apparmor
```

## Performance Optimization for Ubuntu 24.04.3

### **System Optimization**

```bash
# Optimize APT for faster package installation
echo 'APT::Install-Recommends "false";' | sudo tee /etc/apt/apt.conf.d/99-no-recommends

# Enable APT caching
echo 'APT::Cache-Limit "100000000";' | sudo tee /etc/apt/apt.conf.d/99-cache-limit
```

### **Apache2 Optimization**

```bash
# Edit Apache2 configuration
sudo nano /etc/apache2/apache2.conf

# Add these optimizations:
ServerTokens Prod
ServerSignature Off
KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 5
```

## Getting Help for Ubuntu 24.04.3

### **Ubuntu-Specific Resources**

- **Ubuntu Documentation**: https://help.ubuntu.com/
- **Ubuntu Forums**: https://ubuntuforums.org/
- **Ask Ubuntu**: https://askubuntu.com/

### **CyberPanel Resources**

- **General Troubleshooting**: [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Complete Guides**: [Guides Index](INDEX.md)
- **CyberPanel Forums**: https://community.cyberpanel.net

### **System Logs to Check**

```bash
# Ubuntu system logs
sudo journalctl -xe
sudo dmesg | tail -50

# CyberPanel specific logs
tail -f /usr/local/lscp/logs/error.log
tail -f /usr/local/CyberCP/logs/cyberpanel.log
```

---

**Note**: This guide is specifically tailored for Ubuntu 24.04.3 LTS. For other Ubuntu versions or operating systems, refer to the appropriate OS-specific troubleshooting guide.
