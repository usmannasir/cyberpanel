# Debian 13 Installation Guide for CyberPanel

## 🎯 Overview

This guide provides step-by-step instructions for installing CyberPanel on Debian 13 (Bookworm). Debian 13 support has been added to CyberPanel with full compatibility for package management, service configuration, and web server setup.

## 📋 Prerequisites

### System Requirements
- **OS**: Debian 13 (Bookworm) x86_64
- **RAM**: Minimum 1GB (2GB+ recommended)
- **Storage**: Minimum 10GB free space (20GB+ recommended)
- **CPU**: 2+ cores recommended
- **Network**: Internet connection required

### Supported Debian Versions
- ✅ **Debian 13** (Bookworm) - Full Support
- ✅ **Debian 12** (Bookworm) - Full Support  
- ✅ **Debian 11** (Bullseye) - Full Support

## 🚀 Installation Steps

### Step 1: Update System

```bash
# Update package lists
sudo apt update

# Upgrade system packages
sudo apt upgrade -y

# Install essential packages
sudo apt install -y curl wget git
```

### Step 2: Download and Run CyberPanel Installer

```bash
# Download the latest CyberPanel installer
wget https://cyberpanel.sh/install.sh

# Make the installer executable
chmod +x install.sh

# Run the installer
sudo ./install.sh
```

### Step 3: Follow Installation Prompts

The installer will guide you through:

1. **License Agreement**: Accept the terms
2. **Installation Type**: Choose between:
   - OpenLiteSpeed (Free)
   - LiteSpeed Enterprise (Requires license)
3. **MySQL Configuration**: 
   - Single MySQL instance (recommended)
   - Double MySQL instance (for high availability)
4. **Additional Services**:
   - Postfix/Dovecot (Email server)
   - PowerDNS (DNS server)
   - PureFTPD (FTP server)

### Step 4: Verify Installation

```bash
# Check CyberPanel service status
sudo systemctl status lscpd

# Check web server status
sudo systemctl status apache2

# Check if CyberPanel is accessible
curl -I http://localhost:8090
```

## 🔧 Post-Installation Configuration

### Access CyberPanel

1. Open your web browser
2. Navigate to: `http://your-server-ip:8090`
3. Default login credentials:
   - **Username**: `admin`
   - **Password**: `123456` (change immediately!)

### Change Default Password

```bash
# Login to CyberPanel CLI
sudo cyberpanel

# Change admin password
cyberpanel --change-password admin
```

### Configure Firewall

```bash
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

# Enable firewall
sudo ufw enable
```

## 🐛 Troubleshooting

### Common Issues

#### 1. OS Detection Failed
**Problem**: Installer doesn't recognize Debian 13
**Solution**: Ensure you're running the latest installer version

```bash
# Download latest installer
wget https://cyberpanel.sh/install.sh
chmod +x install.sh
sudo ./install.sh
```

#### 2. Package Installation Failed
**Problem**: apt-get errors during installation
**Solution**: Update repositories and retry

```bash
# Update package lists
sudo apt update

# Fix broken packages
sudo apt --fix-broken install

# Retry installation
sudo ./install.sh
```

#### 3. Service Won't Start
**Problem**: CyberPanel service fails to start
**Solution**: Check logs and restart services

```bash
# Check service status
sudo systemctl status lscpd

# Check logs
sudo journalctl -u lscpd -f

# Restart service
sudo systemctl restart lscpd
```

#### 4. Web Server Issues
**Problem**: Apache2 configuration problems
**Solution**: Reconfigure web server

```bash
# Check Apache2 status
sudo systemctl status apache2

# Test configuration
sudo apache2ctl configtest

# Restart Apache2
sudo systemctl restart apache2
```

### Log Files

Important log locations:
- **CyberPanel**: `/usr/local/CyberCP/logs/`
- **Apache2**: `/var/log/apache2/`
- **System**: `/var/log/syslog`
- **Installation**: `/root/cyberpanel-install.log`

## 🔒 Security Considerations

### Initial Security Setup

1. **Change Default Password**
   ```bash
   sudo cyberpanel --change-password admin
   ```

2. **Update System**
   ```bash
   sudo apt update && sudo apt upgrade -y
   ```

3. **Configure Firewall**
   ```bash
   sudo ufw enable
   sudo ufw default deny incoming
   sudo ufw default allow outgoing
   ```

4. **Enable Fail2Ban**
   ```bash
   sudo apt install fail2ban -y
   sudo systemctl enable fail2ban
   sudo systemctl start fail2ban
   ```

### SSL Certificate Setup

1. **Access CyberPanel Web Interface**
2. **Navigate to**: SSL → Let's Encrypt
3. **Enter your domain name**
4. **Click "Issue" to get free SSL certificate**

## 📊 Performance Optimization

### System Optimization

```bash
# Optimize Apache2 for Debian
sudo nano /etc/apache2/apache2.conf

# Add these lines:
ServerTokens Prod
ServerSignature Off
KeepAlive On
MaxKeepAliveRequests 100
KeepAliveTimeout 5
```

### PHP Optimization

1. **Access CyberPanel Web Interface**
2. **Navigate to**: PHP → PHP Settings
3. **Configure**:
   - Memory limit: 256M
   - Max execution time: 300
   - Upload max filesize: 64M

## 🔄 Updates and Maintenance

### Update CyberPanel

```bash
# Update to latest version
sudo cyberpanel --update

# Or use the upgrade script
sudo ./cyberpanel_upgrade.sh
```

### System Maintenance

```bash
# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean package cache
sudo apt autoremove -y
sudo apt autoclean

# Check disk usage
df -h

# Check memory usage
free -h
```

## 📚 Additional Resources

### Documentation
- [CyberPanel Official Docs](https://cyberpanel.net/docs/)
- [Debian 13 Release Notes](https://www.debian.org/releases/bookworm/releasenotes)
- [Apache2 Configuration Guide](https://httpd.apache.org/docs/2.4/)

### Community Support
- [CyberPanel Community Forum](https://forums.cyberpanel.net/)
- [GitHub Issues](https://github.com/usmannasir/cyberpanel/issues)
- [Discord Server](https://discord.gg/cyberpanel)

### Testing Compatibility

Run the compatibility test script:

```bash
# Download test script
wget https://raw.githubusercontent.com/cyberpanel/cyberpanel/main/test_debian13_support.sh

# Make executable
chmod +x test_debian13_support.sh

# Run test
sudo ./test_debian13_support.sh
```

## ✅ Verification Checklist

After installation, verify these components:

- [ ] CyberPanel web interface accessible
- [ ] Admin password changed
- [ ] SSL certificate installed
- [ ] Firewall configured
- [ ] Email server working (if installed)
- [ ] DNS server working (if installed)
- [ ] FTP server working (if installed)
- [ ] System updates applied
- [ ] Logs are clean
- [ ] Services are running

## 🆘 Getting Help

If you encounter issues:

1. **Check the logs** (see Troubleshooting section)
2. **Run the compatibility test**
3. **Search the documentation**
4. **Ask in the community forum**
5. **Create a GitHub issue** with detailed information

---

**Note**: This guide is specifically for Debian 13. For other operating systems, refer to the main CyberPanel documentation.
