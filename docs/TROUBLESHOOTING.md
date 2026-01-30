# CyberPanel Troubleshooting Guide

## Overview

This guide provides comprehensive troubleshooting information for common CyberPanel issues, including file integrity verification, system diagnostics, and support commands.

## Quick Support Commands

### **System Status Checks**

```bash
# Check CyberPanel service status
sudo systemctl status lscpd

# Check web server status
sudo systemctl status apache2

# Check if CyberPanel is accessible
curl -I http://localhost:8090

# Check system resources
free -h
df -h
top
```

### **File Integrity Verification**

```bash
# Check Python syntax
python -m py_compile manage.py
python -m py_compile CyberCP/settings.py
python -m py_compile CyberCP/urls.py

# Verify Django configuration
python manage.py check

# Check file count (should be ~5,597)
find . -type f | wc -l

# Verify critical directories
ls -la /usr/local/CyberCP/CyberCP/
ls -la /usr/local/CyberCP/plogical/
ls -la /usr/local/CyberCP/websiteFunctions/
```

### **Log Analysis**

```bash
# Check CyberPanel logs
tail -f /usr/local/lscp/logs/error.log

# Check Django logs
tail -f /usr/local/CyberCP/logs/cyberpanel.log

# Check system logs
journalctl -u lscpd -f
journalctl -u apache2 -f

# Check installation logs
tail -f /root/cyberpanel-install.log
```

## File Integrity & Verification

CyberPanel includes comprehensive file integrity verification to ensure all components are properly installed and synchronized.

### **Verification Status**

- **Total Files Verified**: 5,597 files synchronized and validated
- **Python Syntax**: All core Python modules validated for syntax errors
- **Django Configuration**: Complete Django application integrity verified
- **Environment Files**: All configuration files (.env, .env.backup) verified
- **Static Assets**: All UI assets and templates synchronized
- **Core Modules**: All application modules (loginSystem, websiteFunctions, plogical) verified

### **Verification Process**

The verification system automatically checks:

1. **File Completeness**: Ensures all critical files are present
2. **Python Syntax**: Validates all Python files for syntax errors
3. **Django Integrity**: Verifies Django configuration and URL routing
4. **Environment Configuration**: Checks .env files and configuration
5. **Module Dependencies**: Ensures all application modules are complete
6. **Static Assets**: Verifies UI components and templates

## Common Issues & Solutions

### **Missing Files or Broken Installation**

- **Issue**: CyberPanel components not working due to missing files
- **Symptoms**: Import errors, Django configuration issues, missing modules
- **Solution**: 
  ```bash
  # Verify file integrity
  python -m py_compile manage.py
  python manage.py check
  
  # Check for missing files
  find . -name "*.py" -exec python -m py_compile {} \;
  ```
- **Prevention**: Regular file integrity checks and proper installation procedures

### **Django Configuration Issues**

- **Issue**: Django application fails to start or load
- **Symptoms**: ModuleNotFoundError, ImportError, settings issues
- **Solution**:
  ```bash
  # Check Django configuration
  python manage.py check --deploy
  
  # Verify environment files
  ls -la .env*
  
  # Test Django setup
  python -c "import django; django.setup(); print('Django OK')"
  ```

### **Bandwidth Not Resetting Monthly**

- **Issue**: Bandwidth usage shows cumulative values instead of monthly usage
- **Solution**: Run the bandwidth reset script: `/usr/local/CyberCP/scripts/reset_bandwidth.sh`
- **Prevention**: Ensure monthly cron job is running: `0 0 1 * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/postfixSenderPolicy/client.py monthlyCleanup`

### **Environment Configuration Issues**

- **Issue**: Missing or corrupted .env files
- **Symptoms**: Configuration errors, missing environment variables
- **Solution**:
  ```bash
  # Check for .env files
  ls -la .env*
  
  # Verify .env template exists
  cp .env.template .env
  # Edit .env with your configuration
  ```

### **Python Module Import Errors**

- **Issue**: Python modules cannot be imported
- **Symptoms**: ImportError, ModuleNotFoundError
- **Solution**:
  ```bash
  # Check Python syntax
  python -m py_compile path/to/module.py
  
  # Verify all core modules
  python -m py_compile CyberCP/settings.py
  python -m py_compile loginSystem/views.py
  python -m py_compile websiteFunctions/views.py
  ```

### **Service Won't Start**

- **Issue**: CyberPanel service fails to start
- **Solution**: Check logs and restart services
  ```bash
  # Check service status
  sudo systemctl status lscpd
  
  # Check logs
  sudo journalctl -u lscpd -f
  
  # Restart service
  sudo systemctl restart lscpd
  ```

### **Web Server Issues**

- **Issue**: Apache2 configuration problems
- **Solution**: Reconfigure web server
  ```bash
  # Check Apache2 status
  sudo systemctl status apache2
  
  # Test configuration
  sudo apache2ctl configtest
  
  # Restart Apache2
  sudo systemctl restart apache2
  ```

## Diagnostic Commands

### **System Diagnostics**

```bash
# Check disk usage
df -h

# Check memory usage
free -h

# Check running processes
ps aux | grep cyberpanel

# Check network connectivity
ping -c 4 google.com

# Check firewall status
sudo ufw status
sudo firewall-cmd --state
```

### **Permission Checks**

```bash
# Check file permissions
ls -la /usr/local/CyberCP/

# Check directory ownership
find /usr/local/CyberCP/ -type d -exec ls -ld {} \;

# Fix common permission issues
sudo chown -R cyberpanel:cyberpanel /usr/local/CyberCP/
sudo chmod -R 755 /usr/local/CyberCP/
```

### **Cron Job Verification**

```bash
# Check cron jobs
crontab -l

# Check system cron jobs
sudo crontab -l

# Verify cron service
sudo systemctl status cron
```

## Log File Locations

### **CyberPanel Logs**
- **Main Log**: `/usr/local/lscp/logs/error.log`
- **Django Logs**: `/usr/local/CyberCP/logs/cyberpanel.log`
- **Installation Log**: `/root/cyberpanel-install.log`

### **System Logs**
- **Apache2**: `/var/log/apache2/`
- **System**: `/var/log/syslog`
- **Journal**: `journalctl -u lscpd`

### **Application Logs**
- **Database**: `/var/log/mysql/`
- **Email**: `/var/log/mail.log`
- **DNS**: `/var/log/powerdns.log`

## Getting Help

### **Self-Diagnosis Steps**

1. **Check service status** using the commands above
2. **Review relevant log files** for error messages
3. **Verify file integrity** using Python compilation checks
4. **Test network connectivity** and firewall settings
5. **Check system resources** (memory, disk space)

### **Support Resources**

- **📚 [Complete Guides Index](INDEX.md)** - All available documentation

#### **OS-Specific Troubleshooting Guides**
- **🐧 [Debian 13 Installation Guide](DEBIAN_13_INSTALLATION_GUIDE.md)** - Debian 13 troubleshooting
- **🐧 [Debian 12 Troubleshooting Guide](DEBIAN_12_TROUBLESHOOTING.md)** - Debian 12 troubleshooting
- **🐧 [Debian 11 Troubleshooting Guide](DEBIAN_11_TROUBLESHOOTING.md)** - Debian 11 troubleshooting
- **🐧 [Ubuntu 24.04.3 Troubleshooting Guide](UBUNTU_24_TROUBLESHOOTING.md)** - Ubuntu 24.04.3 troubleshooting
- **🐧 [Ubuntu 22.04 Troubleshooting Guide](UBUNTU_22_TROUBLESHOOTING.md)** - Ubuntu 22.04 troubleshooting
- **🐧 [Ubuntu 20.04 Troubleshooting Guide](UBUNTU_20_TROUBLESHOOTING.md)** - Ubuntu 20.04 troubleshooting
- **🔴 [AlmaLinux 10 Troubleshooting Guide](ALMALINUX_10_TROUBLESHOOTING.md)** - AlmaLinux 10 troubleshooting
- **🔴 [AlmaLinux 9 Troubleshooting Guide](ALMALINUX_9_TROUBLESHOOTING.md)** - AlmaLinux 9 troubleshooting
- **🔴 [AlmaLinux 8 Troubleshooting Guide](ALMALINUX_8_TROUBLESHOOTING.md)** - AlmaLinux 8 troubleshooting
- **🔴 [RockyLinux 9 Troubleshooting Guide](ROCKYLINUX_9_TROUBLESHOOTING.md)** - RockyLinux 9 troubleshooting
- **🔴 [RockyLinux 8 Troubleshooting Guide](ROCKYLINUX_8_TROUBLESHOOTING.md)** - RockyLinux 8 troubleshooting
- **🔴 [CentOS 9 Troubleshooting Guide](CENTOS_9_TROUBLESHOOTING.md)** - CentOS 9 troubleshooting
- **☁️ [CloudLinux 8 Troubleshooting Guide](CLOUDLINUX_8_TROUBLESHOOTING.md)** - CloudLinux 8 troubleshooting

#### **Feature-Specific Guides**
- **🐳 [Docker Command Execution Guide](Docker_Command_Execution_Guide.md)** - Docker-related issues
- **🤖 [AI Scanner Documentation](AIScannerDocs.md)** - Security scanner troubleshooting
- **📧 [Mautic Installation Guide](MAUTIC_INSTALLATION_GUIDE.md)** - Email marketing setup
- **🎨 [Custom CSS Guide](CUSTOM_CSS_GUIDE.md)** - Interface customization issues
- **🔥 [Firewall Blocking Feature Guide](FIREWALL_BLOCKING_FEATURE.md)** - Security features

### **Community Support**

- **CyberPanel Forums**: https://community.cyberpanel.net
- **GitHub Issues**: https://github.com/usmannasir/cyberpanel/issues
- **Discord Server**: https://discord.gg/cyberpanel

## Advanced Troubleshooting

### **Network Issues**

```bash
# Check port availability
netstat -tlnp | grep :8090
ss -tlnp | grep :8090

# Test port connectivity
telnet localhost 8090
nc -zv localhost 8090
```

### **Database Issues**

```bash
# Check MySQL/MariaDB status
sudo systemctl status mysql
sudo systemctl status mariadb

# Test database connection
mysql -u root -p -e "SHOW DATABASES;"

# Check database logs
sudo tail -f /var/log/mysql/error.log
```

### **SSL Certificate Issues**

```bash
# Check certificate status
openssl x509 -in /path/to/certificate.crt -text -noout

# Test SSL connectivity
openssl s_client -connect your-domain.com:443

# Check Let's Encrypt certificates
sudo certbot certificates
```

---

**Note**: This troubleshooting guide covers the most common issues and solutions. For specific problems not covered here, refer to the individual feature guides or contact the CyberPanel community for assistance.
