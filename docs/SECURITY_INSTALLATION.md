# CyberPanel Secure Installation Guide

## Overview

This document describes the secure installation process for CyberPanel that generates secure passwords and updates configuration files directly during installation.

## Security Improvements

### ✅ **Fixed Security Vulnerabilities**

1. **Hardcoded Database Passwords** - Now generated securely during installation
2. **Hardcoded Django Secret Key** - Now generated using cryptographically secure random generation
3. **Direct Configuration Updates** - Passwords updated directly in settings.py during installation
4. **File Permissions** - settings.py file set to 640 (owner read/write, group read only)

### 🔐 **Security Features**

- **Cryptographically Secure Passwords**: Uses Python's `secrets` module for password generation
- **Direct Configuration Updates**: Passwords updated directly in settings.py, no external files needed
- **Secure File Permissions**: settings.py protected with 640 permissions
- **Simplified Architecture**: No external environment files required
- **Linux/Unix Focused**: Optimized for supported platforms only

## Installation Process

### 1. **Automatic Secure Installation**

The installation script now automatically:

1. Generates secure random passwords for:
   - MySQL root user
   - CyberPanel database user
   - Django secret key

2. Updates `settings.py` directly with secure configuration:
   ```python
   SECRET_KEY = 'generated_secure_key'
   DATABASES = {
       'default': {
           'PASSWORD': 'generated_cyberpanel_password',
       },
       'rootdb': {
           'PASSWORD': 'generated_root_password',
       }
   }
   ```

3. Sets secure file permissions (640) on settings.py
4. No external environment files required

### 2. **Manual Configuration** (if needed)

If you need to manually update configuration, edit the settings.py file directly:

```bash
nano /usr/local/CyberCP/CyberCP/settings.py
```

## File Structure

```
/usr/local/CyberCP/
├── CyberCP/
│   └── settings.py        # Main configuration file (640 permissions)
```

## Security Best Practices

### ✅ **Do's**

- Keep `.env` and `.env.backup` files secure
- Record credentials from `.env.backup` and delete the file after installation
- Use strong, unique passwords for production deployments
- Regularly rotate database passwords
- Monitor access to environment files

### ❌ **Don'ts**

- Never commit `.env` files to version control
- Don't share `.env` files via insecure channels
- Don't use default passwords in production
- Don't leave `.env.backup` files on the system after recording credentials

## Recovery

### **Lost Credentials**

If you lose your database credentials:

1. Check if `.env.backup` file exists:
   ```bash
   sudo cat /usr/local/CyberCP/.env.backup
   ```

2. If backup doesn't exist, you'll need to reset MySQL passwords using MySQL recovery procedures

### **Regenerate Environment**

To regenerate environment configuration:

```bash
cd /usr/local/CyberCP
sudo python install/env_generator.py /usr/local/CyberCP
```

## Configuration Options

### **Environment Variables**

| Variable | Description | Default |
|----------|-------------|---------|
| `SECRET_KEY` | Django secret key | Generated (64 chars) |
| `DB_PASSWORD` | CyberPanel DB password | Generated (24 chars) |
| `ROOT_DB_PASSWORD` | MySQL root password | Generated (24 chars) |
| `DEBUG` | Debug mode | False |
| `ALLOWED_HOSTS` | Allowed hosts | localhost,127.0.0.1,hostname |

### **Custom Configuration**

To use custom passwords during installation:

```bash
python install/env_generator.py /usr/local/CyberCP "your_root_password" "your_db_password"
```

## Troubleshooting

### **Installation Fails**

If the new secure installation fails:

1. Check installation logs for error messages
2. The system will automatically fallback to the original installation method
3. Verify Python dependencies are installed:
   ```bash
   pip install python-dotenv
   ```

### **Environment Loading Issues**

If Django can't load environment variables:

1. Ensure `.env` file exists and has correct permissions:
   ```bash
   ls -la /usr/local/CyberCP/.env
   # Should show: -rw------- 1 root root
   ```

2. Install python-dotenv if missing:
   ```bash
   pip install python-dotenv
   ```

## Migration from Old Installation

### **Existing Installations**

For existing CyberPanel installations with hardcoded passwords:

1. **Backup current configuration**:
   ```bash
   cp /usr/local/CyberCP/CyberCP/settings.py /usr/local/CyberCP/CyberCP/settings.py.backup
   ```

2. **Generate new environment configuration**:
   ```bash
   cd /usr/local/CyberCP
   python install/env_generator.py /usr/local/CyberCP
   ```

3. **Update settings.py** (already done in new installations):
   - The settings.py file now supports environment variables
   - It will fallback to hardcoded values if .env is not available

4. **Test the configuration**:
   ```bash
   cd /usr/local/CyberCP
   python manage.py check
   ```

## Support

For issues with the secure installation:

1. Check the installation logs
2. Verify file permissions
3. Ensure all dependencies are installed
4. Review the fallback installation method if needed

---

**Security Notice**: This installation method significantly improves security by eliminating hardcoded credentials. Always ensure proper file permissions and secure handling of environment files.

