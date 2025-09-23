# CyberPanel Windows Development Guide

## 🎯 Overview

**⚠️ IMPORTANT**: CyberPanel is designed specifically for Linux systems and does not officially support Windows. This guide is for **development and testing purposes only**.

This guide provides instructions for running CyberPanel in a Windows development environment using Python and Django. This setup is intended for:
- **Developers** working on CyberPanel features
- **Testing** CyberPanel functionality
- **Learning** CyberPanel architecture
- **Development** of CyberPanel extensions

**For production use, always use a supported Linux distribution.**

## 📋 Prerequisites

### System Requirements
- **OS**: Windows 7/8.1/10/11 (64-bit recommended)
- **RAM**: Minimum 4GB (8GB+ recommended)
- **Storage**: Minimum 20GB free space
- **CPU**: 2+ cores recommended
- **Network**: Internet connection required

### Required Software
- **Python 3.8+**: Download from [python.org](https://python.org)
- **Git**: Download from [git-scm.com](https://git-scm.com)
- **Administrator Access**: Required for installation

### ⚠️ Limitations
- **No Web Server**: OpenLiteSpeed/LiteSpeed not available on Windows
- **No System Services**: MariaDB, PowerDNS, etc. not included
- **Limited Functionality**: Many CyberPanel features require Linux
- **Development Only**: Not suitable for production use

## 🚀 Installation Methods

### Method 1: Automated Installation (Recommended)

#### Step 1: Download Installation Script
1. Navigate to the `utils/windows/` folder
2. Download `cyberpanel_install.bat`
3. Right-click and select "Run as administrator"

#### Step 2: Follow Installation Prompts
The script will automatically:
- Check system requirements
- Create Python virtual environment
- Download CyberPanel source code
- Install all dependencies
- Set up the web interface

#### Step 3: Access CyberPanel
1. Open your web browser
2. Navigate to: `http://localhost:8090`
3. Use default credentials:
   - **Username**: `admin`
   - **Password**: `123456`

### Method 2: Manual Installation

#### Step 1: Install Python
1. Download Python 3.8+ from [python.org](https://python.org)
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```cmd
   python --version
   pip --version
   ```

#### Step 2: Install Git
1. Download Git from [git-scm.com](https://git-scm.com)
2. Install with default settings
3. Verify installation:
   ```cmd
   git --version
   ```

#### Step 3: Create CyberPanel Directory
```cmd
mkdir C:\usr\local\CyberCP
cd C:\usr\local\CyberCP
```

#### Step 4: Set Up Python Environment
```cmd
python -m venv . --system-site-packages
Scripts\activate.bat
```

#### Step 5: Download CyberPanel
```cmd
git clone https://github.com/usmannasir/cyberpanel.git
cd cyberpanel
```

#### Step 6: Install Dependencies
```cmd
pip install --upgrade pip setuptools wheel
pip install -r requirments.txt
```

#### Step 7: Set Up Django
```cmd
python manage.py collectstatic --noinput
python manage.py migrate
```

#### Step 8: Create Admin User
```cmd
python manage.py createsuperuser
```

#### Step 9: Start CyberPanel
```cmd
python manage.py runserver 0.0.0.0:8090
```

## 🔧 Post-Installation Configuration

### Change Default Password
1. Access CyberPanel at `http://localhost:8090`
2. Log in with default credentials
3. Go to **User Management** → **Modify User**
4. Change the admin password immediately

### Configure Windows Firewall
1. Open Windows Defender Firewall
2. Add inbound rule for port 8090
3. Allow Python through firewall

### Set Up Windows Service (Optional)
1. Run `install_service.bat` as administrator
2. CyberPanel will start automatically on boot
3. Manage service through Windows Services

## 🔄 Upgrading CyberPanel

### Using Upgrade Script
1. Download `cyberpanel_upgrade.bat`
2. Right-click and select "Run as administrator"
3. Script will automatically backup and upgrade

### Manual Upgrade
```cmd
cd C:\usr\local\CyberCP\cyberpanel
Scripts\activate.bat
git pull origin stable
pip install --upgrade -r requirments.txt
python manage.py migrate
python manage.py collectstatic --noinput
```

## 🛠️ Utility Scripts

### Available Scripts
- **`cyberpanel_install.bat`**: Complete installation
- **`cyberpanel_upgrade.bat`**: Upgrade existing installation
- **`install_webauthn.bat`**: Enable WebAuthn/Passkey authentication

### Script Usage
1. **Right-click** on any script
2. Select **"Run as administrator"**
3. Follow on-screen prompts
4. Check output for any errors

## 🐛 Troubleshooting

### Common Issues

#### "Python not found" Error
**Problem**: Python is not installed or not in PATH
**Solution**:
1. Install Python from [python.org](https://python.org)
2. Check "Add Python to PATH" during installation
3. Restart Command Prompt
4. Verify with `python --version`

#### "Access Denied" Error
**Problem**: Insufficient privileges
**Solution**:
1. Right-click script and select "Run as administrator"
2. Or open Command Prompt as administrator
3. Navigate to script location and run

#### "Failed to install requirements" Error
**Problem**: Network or dependency issues
**Solution**:
1. Check internet connection
2. Try running script again
3. Install requirements manually:
   ```cmd
   pip install --upgrade pip
   pip install -r requirments.txt
   ```

#### "Port 8090 already in use" Error
**Problem**: Another service is using port 8090
**Solution**:
1. Stop other services using port 8090
2. Or change CyberPanel port in settings
3. Check with: `netstat -an | findstr :8090`

#### "Django not found" Error
**Problem**: Virtual environment not activated
**Solution**:
1. Navigate to CyberPanel directory
2. Activate virtual environment:
   ```cmd
   Scripts\activate.bat
   ```
3. Verify with `python -c "import django"`

### Advanced Troubleshooting

#### Check Installation Logs
```cmd
cd C:\usr\local\CyberCP\cyberpanel
python manage.py check
```

#### Verify Dependencies
```cmd
pip list
pip check
```

#### Test Database Connection
```cmd
python manage.py dbshell
```

#### Reset Database (Last Resort)
```cmd
python manage.py flush
python manage.py migrate
python manage.py createsuperuser
```

## 🔒 Security Considerations

### Initial Security Setup
1. **Change Default Password**: Immediately after installation
2. **Enable 2FA**: Use the 2FA guide for additional security
3. **Configure Firewall**: Restrict access to necessary ports only
4. **Regular Updates**: Keep CyberPanel and dependencies updated

### Windows-Specific Security
1. **User Account Control**: Keep UAC enabled
2. **Windows Defender**: Ensure real-time protection is on
3. **Regular Backups**: Backup CyberPanel data regularly
4. **Service Account**: Consider using dedicated service account

## 📊 Performance Optimization

### System Optimization
1. **Disable Unnecessary Services**: Free up system resources
2. **SSD Storage**: Use SSD for better performance
3. **Memory**: Ensure adequate RAM (8GB+ recommended)
4. **CPU**: Multi-core processor recommended

### CyberPanel Optimization
1. **Static Files**: Ensure static files are properly collected
2. **Database**: Regular database maintenance
3. **Logs**: Regular log cleanup
4. **Caching**: Enable appropriate caching

## 🔄 Maintenance

### Regular Maintenance Tasks
1. **Updates**: Regular CyberPanel updates
2. **Backups**: Regular data backups
3. **Logs**: Monitor and clean logs
4. **Security**: Regular security checks

### Backup Procedures
1. **Database Backup**:
   ```cmd
   python manage.py dumpdata > backup.json
   ```

2. **File Backup**:
   ```cmd
   xcopy C:\usr\local\CyberCP backup_folder /E /I /H
   ```

3. **Restore from Backup**:
   ```cmd
   python manage.py loaddata backup.json
   ```

## 📚 Additional Resources

### Documentation
- **Main Guide**: [2FA Authentication Guide](2FA_AUTHENTICATION_GUIDE.md)
- **Troubleshooting**: [Troubleshooting Guide](TROUBLESHOOTING.md)
- **Utility Scripts**: [Utility Scripts](../utils/README.md)

### Support
- **CyberPanel Forums**: https://community.cyberpanel.net
- **GitHub Issues**: https://github.com/usmannasir/cyberpanel/issues
- **Discord Server**: https://discord.gg/cyberpanel

## ✅ Verification Checklist

After installation, verify these components:
- [ ] CyberPanel accessible at `http://localhost:8090`
- [ ] Admin password changed from default
- [ ] Windows Firewall configured
- [ ] Python virtual environment working
- [ ] All dependencies installed
- [ ] Database migrations applied
- [ ] Static files collected
- [ ] Logs are clean
- [ ] Service starts automatically (if configured)

## 🆘 Getting Help

If you encounter issues:
1. **Check the logs** for error messages
2. **Run the troubleshooting commands** above
3. **Search the documentation** for solutions
4. **Ask in the community forum** for help
5. **Create a GitHub issue** with detailed information

---

**Note**: This guide is specifically for Windows installations. For Linux installations, refer to the main CyberPanel documentation.

*Last updated: January 2025*
