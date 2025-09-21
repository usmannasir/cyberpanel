# CyberPanel Utility Scripts

This folder contains utility scripts for CyberPanel installation, maintenance, and troubleshooting.

## 📁 Folder Structure

```
utils/
├── README.md                    # This file
├── windows/                     # Windows-specific scripts
│   ├── cyberpanel_install.bat  # Windows installation script
│   ├── cyberpanel_upgrade.bat  # Windows upgrade script
│   └── install_webauthn.bat    # WebAuthn setup for Windows
└── linux/                      # Linux-specific scripts
    └── install_webauthn.sh     # WebAuthn setup for Linux
```

## 🪟 Windows Scripts

**⚠️ IMPORTANT**: These Windows scripts are for **development and testing purposes only**. CyberPanel is designed for Linux systems and does not officially support Windows for production use.

### Development Scripts

#### `cyberpanel_install.bat`
**Purpose**: Set up CyberPanel development environment on Windows

**Requirements**:
- Windows 7/8.1/10/11
- Administrator privileges
- Python 3.8+ installed
- Internet connection

**Limitations**:
- No web server (OpenLiteSpeed/LiteSpeed)
- No system services (MariaDB, PowerDNS)
- Limited functionality
- Development/testing only

**Usage**:
1. Right-click and select "Run as administrator"
2. Follow the on-screen prompts
3. Access CyberPanel at `http://localhost:8090`

**Features**:
- Automatic Python environment setup
- Virtual environment creation
- Source code download
- Requirements installation
- Admin user creation
- Windows service setup

#### `cyberpanel_upgrade.bat`
**Purpose**: Upgrade existing CyberPanel installation

**Requirements**:
- Existing CyberPanel installation
- Administrator privileges
- Internet connection

**Usage**:
1. Right-click and select "Run as administrator"
2. Script will automatically backup and upgrade
3. Restart CyberPanel after completion

**Features**:
- Automatic backup creation
- Source code update
- Requirements upgrade
- Database migration
- Service restart

#### `install_webauthn.bat`
**Purpose**: Set up WebAuthn/Passkey authentication

**Requirements**:
- CyberPanel already installed
- Administrator privileges

**Usage**:
1. Run as administrator
2. Follow configuration prompts
3. Access User Management to enable WebAuthn

## 🐧 Linux Scripts

### Installation Scripts

#### `install_webauthn.sh`
**Purpose**: Set up WebAuthn/Passkey authentication on Linux

**Requirements**:
- CyberPanel installed
- Root privileges

**Usage**:
```bash
sudo ./install_webauthn.sh
```

**Features**:
- Database migration
- Static files setup
- Service configuration
- Permission fixing

## 🚀 Quick Start

### Windows Users
1. **First Installation**:
   ```cmd
   # Run as administrator
   cyberpanel_install.bat
   ```

2. **Upgrade Existing Installation**:
   ```cmd
   # Run as administrator
   cyberpanel_upgrade.bat
   ```

3. **Enable WebAuthn**:
   ```cmd
   # Run as administrator
   install_webauthn.bat
   ```

### Linux Users
1. **Fix Installation Issues**:
   ```bash
   sudo ./fix_cyberpanel_install.sh
   ```

2. **Enable WebAuthn**:
   ```bash
   sudo ./install_webauthn.sh
   ```

## 🔧 Troubleshooting

### Common Windows Issues

#### "Python not found" Error
- **Solution**: Install Python 3.8+ from [python.org](https://python.org)
- **Important**: Check "Add Python to PATH" during installation

#### "Access Denied" Error
- **Solution**: Right-click script and select "Run as administrator"
- **Alternative**: Open Command Prompt as administrator

#### "Failed to install requirements" Error
- **Solution**: Check internet connection
- **Alternative**: Try running script again
- **Advanced**: Install requirements manually with pip

### Common Linux Issues

#### "Permission denied" Error
- **Solution**: Run with `sudo` or as root user
- **Example**: `sudo ./script.sh`

#### "Command not found" Error
- **Solution**: Ensure script is executable
- **Fix**: `chmod +x script.sh`

#### "Django not found" Error
- **Solution**: Run the fix script first
- **Alternative**: Reinstall CyberPanel

## 📚 Additional Resources

### Documentation
- **Main Guide**: [2FA Authentication Guide](../guides/2FA_AUTHENTICATION_GUIDE.md)
- **Troubleshooting**: [Troubleshooting Guide](../guides/TROUBLESHOOTING.md)
- **Complete Index**: [Guides Index](../guides/INDEX.md)

### Support
- **CyberPanel Forums**: https://community.cyberpanel.net
- **GitHub Issues**: https://github.com/usmannasir/cyberpanel/issues
- **Discord Server**: https://discord.gg/cyberpanel

## ⚠️ Important Notes

### Security
- Always run scripts as administrator/root when required
- Change default passwords immediately after installation
- Keep CyberPanel updated regularly

### Backups
- The upgrade script automatically creates backups
- Store backups in a safe location
- Test restore procedures regularly

### Compatibility
- Windows scripts tested on Windows 7/8.1/10/11
- Linux scripts tested on Ubuntu, Debian, AlmaLinux, RockyLinux
- Python 3.8+ required for all scripts

---

**Note**: These utility scripts are provided as-is. Always test in a non-production environment first and ensure you have proper backups before running any scripts.

*Last updated: January 2025*
