<div align="center">

<img src="https://community.cyberpanel.net/uploads/default/original/1X/416fdec0e96357d11f7b2756166c61b1aeca5939.png" alt="CyberPanel Logo" width="500"/>

# 🛠️ CyberPanel

Web Hosting Control Panel powered by OpenLiteSpeed, designed to simplify hosting management.

> **Current Version**: 2.4 Build 3 | **Last Updated**: September 20, 2025

[![GitHub](https://img.shields.io/badge/GitHub-Repository-blue?style=flat-square&logo=github)](https://github.com/usmannasir/cyberpanel)
[![Discord](https://img.shields.io/badge/Discord-Join%20Chat-7289DA?style=flat-square&logo=discord)](https://discord.gg/g8k8Db3)
[![Facebook](https://img.shields.io/badge/Facebook-Community-1877F2?style=flat-square&logo=facebook)](https://www.facebook.com/groups/cyberpanel)
[![YouTube](https://img.shields.io/badge/YouTube-Channel-FF0000?style=flat-square&logo=youtube)](https://www.youtube.com/@Cyber-Panel)
[![Documentation](https://img.shields.io/badge/Documentation-Read%20Now-green?style=flat-square&logo=gitbook)](https://cyberpanel.net/KnowledgeBase/)

---

## 🔧 Features & Services

- 🔐 **Different User Access Levels** (via ACLs).
- 🌌 **Auto SSL** for secure websites.
- 💻 **FTP Server** for file transfers.
- 🕒 **Light-weight DNS Server** (PowerDNS).
- 🔐 **phpMyAdmin** to manage databases (MariaDB).
- 📧 **Email Support** (SnappyMail).
- 🕌 **File Manager** for quick file access.
- 🌐 **PHP Management** made easy.
- 🔒 **Firewall** (FirewallD & ConfigServer Firewall Integration).
- 📀 **One-click Backups and Restores**.
- 🐳 **Docker Management** with command execution capabilities.
- 🤖 **AI-Powered Security Scanner** for enhanced protection.
- 📊 **Monthly Bandwidth Reset** - Automatic bandwidth usage reset (Fixed in latest version).

---

## 📖 **Documentation & Guides**

CyberPanel comes with comprehensive documentation and step-by-step guides:

- 📚 **[Complete Guides Index](guides/INDEX.md)** - All available documentation in one place
- 🐳 **[Docker Command Execution](guides/Docker_Command_Execution_Guide.md)** - Execute commands in Docker containers
- 🤖 **[AI Scanner Setup](guides/AIScannerDocs.md)** - Configure AI-powered security scanning
- 📧 **[Mautic Installation](guides/MAUTIC_INSTALLATION_GUIDE.md)** - Email marketing platform setup
- 🎨 **[Custom CSS Guide](guides/CUSTOM_CSS_GUIDE.md)** - Create custom themes for CyberPanel 2.5.5-dev

---

## 🔢 Supported PHP Versions

CyberPanel supports a wide range of PHP versions across different operating systems:

### ☑️ **Currently Supported PHP Versions**

- **PHP 8.5** - Latest stable version (EOL: Dec 2028) ⭐ **NEW!**
- **PHP 8.4** - Stable version (EOL: Dec 2027)
- **PHP 8.3** - **Default version** - Stable version (EOL: Dec 2027) 🎯
- **PHP 8.2** - Stable version (EOL: Dec 2026)
- **PHP 8.1** - Stable version (EOL: Dec 2025)
- **PHP 8.0** - Legacy support (EOL: Nov 2023)
- **PHP 7.4** - Legacy support (EOL: Nov 2022)

### 🔧 **Third-Party PHP Add-ons**

For additional PHP versions or specific requirements, you can install third-party packages:

#### **Ubuntu/Debian**

- **Ondrej's PPA**: Provides PHP 5.6 to 8.5
- **Sury's PPA**: Alternative repository with latest PHP versions

#### **RHEL-based Systems** (AlmaLinux, RockyLinux, CentOS, RHEL)

- **Remi Repository**: Comprehensive PHP package collection
- **EPEL Repository**: Additional packages for enterprise Linux

#### **CloudLinux**

- **CloudLinux PHP Selector**: Built-in tool for managing multiple PHP versions
- **Remi Repository**: Additional PHP versions and extensions

> **Note**: Third-party repositories may provide additional PHP versions beyond what's available in default repositories. Always verify compatibility with your specific use case.

---

## 🌐 Supported Operating Systems

CyberPanel runs on x86_64 architecture and supports the following operating systems:

### **✅ Currently Supported**

- **Ubuntu 24.04.3** - Supported until April 2029 ⭐ **NEW!**
- **Ubuntu 22.04** - Supported until April 2027
- **Ubuntu 20.04** - Supported until April 2025
- **Debian 13** - Supported until 2029 ⭐ **NEW!**
- **Debian 12** - Supported until 2027
- **Debian 11** - Supported until 2026
- **AlmaLinux 10** - Supported until May 2030 ⭐ **NEW!**
- **AlmaLinux 9** - Supported until May 2032
- **AlmaLinux 8** - Supported until May 2029
- **RockyLinux 9** - Supported until May 2032
- **RockyLinux 8** - Supported until May 2029
- **RHEL 9** - Supported until May 2032
- **RHEL 8** - Supported until May 2029
- **CloudLinux 8** - Supported until May 2029
- **CentOS 9** - Supported until May 2027
- **CentOS 7** - Supported until June 2024
- **CentOS Stream 9** - Supported until May 2027

### **🔧 Third-Party OS Support**

Additional operating systems may be supported through third-party repositories or community efforts:

- **openEuler** - Community-supported with limited testing
- **Other RHEL derivatives** - May work with AlmaLinux/RockyLinux packages

> **Note**: For unsupported operating systems, compatibility is not guaranteed. Always test in a non-production environment first.

---

## ⚙️ Installation Instructions

Install CyberPanel easily with the following command:

```bash
sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
```

---

## 📊 Upgrading CyberPanel

Upgrade your CyberPanel installation using:

```bash
sh <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh || wget -O - https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh)
```

---

## 🆕 Recent Updates & Fixes

### **File Integrity & Verification System** (September 2025)

- **Enhancement**: Comprehensive file integrity verification system implemented
- **Features**:
  - Automatic detection of missing critical files
  - Python syntax validation for all core modules
  - Environment configuration verification
  - Django application integrity checks
- **Coverage**: All core components (Django settings, URLs, middleware, application modules)
- **Status**: ✅ All files verified and synchronized (5,597 files)

### **Bandwidth Reset Issue Fixed** (September 2025)

- **Enhancement**: Implemented automatic monthly bandwidth reset for all websites and child domains
- **Coverage**: All supported operating systems (Ubuntu 20.04+, AlmaLinux, RockyLinux, RHEL, CloudLinux 8, CentOS 7/9)
- **Status**: ✅ Automatic monthly reset now functional

### **New Operating System Support Added** (September 2025)

- **Ubuntu 24.04.3**: Full compatibility with latest Ubuntu LTS
- **Debian 13**: Full compatibility with latest Debian stable release
- **AlmaLinux 10**: Full compatibility with latest AlmaLinux release
- **Long-term Support**: All supported until 2029-2030

### **Core Module Enhancements** (September 2025)

- **Django Configuration**: Enhanced settings.py with improved environment variable handling
- **Security Middleware**: Updated security middleware for better protection
- **Application Modules**: Verified and synchronized all core application modules
- **Static Assets**: Complete synchronization of UI assets and templates

---

## 📚 Resources

- 🌐 [Official Site](https://cyberpanel.net)
- ✏️ [Docs (New)](https://cyberpanel.net/KnowledgeBase/)
- 🎓 [Docs (Old)](https://community.cyberpanel.net/docs)
- 📖 [Additional Guides](guides/INDEX.md) - Detailed guides for Docker, AI Scanner, Mautic, and more
- 📚 [Local Documentation](guides/) - All guides available in this repository
- 🤝 [Contributing Guide](CONTRIBUTING.md) - How to contribute to CyberPanel development
- ✅ [Changelog](https://community.cyberpanel.net/t/change-logs/161)
- 💬 [Forums](https://community.cyberpanel.net)
- 📢 [Discord](https://discord.gg/g8k8Db3)
- 📵 [Facebook Group](https://www.facebook.com/groups/cyberpanel)
- 🎥 [YouTube Channel](https://www.youtube.com/@Cyber-Panel)

### 📖 **Quick Start Guides**

- 🐳 [Docker Command Execution](guides/Docker_Command_Execution_Guide.md) - Execute commands in Docker containers
- 🤖 [AI Scanner Setup](guides/AIScannerDocs.md) - Configure AI-powered security scanning
- 📧 [Mautic Installation](guides/MAUTIC_INSTALLATION_GUIDE.md) - Email marketing platform setup
- 🎨 [Custom CSS Guide](guides/CUSTOM_CSS_GUIDE.md) - Create custom themes for CyberPanel 2.5.5+
- 📚 [All Guides Index](guides/INDEX.md) - Complete documentation hub

### 🔗 **Direct Guide Links**

| Category    | Guide                                                         | Description                    |
| ----------- | ------------------------------------------------------------- | ------------------------------ |
| 📚 All      | [Complete Guides Index](guides/INDEX.md)                         | Browse all available guides    |
| 🔧 General  | [Troubleshooting Guide](guides/TROUBLESHOOTING.md)               | Comprehensive troubleshooting  |
| 🐳 Docker   | [Command Execution](guides/Docker_Command_Execution_Guide.md)    | Execute commands in containers |
| 🤖 Security | [AI Scanner](guides/AIScannerDocs.md)                            | AI-powered security scanning   |
| 📧 Email    | [Mautic Setup](guides/MAUTIC_INSTALLATION_GUIDE.md)              | Email marketing platform       |
| 🎨 Design   | [Custom CSS Guide](guides/CUSTOM_CSS_GUIDE.md)                   | Create custom themes           |
| 🔥 Security | [Firewall Blocking Feature](guides/FIREWALL_BLOCKING_FEATURE.md) | Advanced security features     |

---

## 🔧 Support & Documentation

For detailed troubleshooting, installation guides, and advanced configuration:

### **📚 General Guides**

- **📚 [Complete Guides Index](guides/INDEX.md)** - All available documentation and troubleshooting guides
- **🔧 [Troubleshooting Guide](guides/TROUBLESHOOTING.md)** - Comprehensive troubleshooting and diagnostic commands

### **🛠️ Feature-Specific Guides**

- **🐳 [Docker Command Execution Guide](guides/Docker_Command_Execution_Guide.md)** - Docker management and troubleshooting
- **🤖 [AI Scanner Documentation](guides/AIScannerDocs.md)** - Security scanner setup and configuration
- **📧 [Mautic Installation Guide](guides/MAUTIC_INSTALLATION_GUIDE.md)** - Email marketing platform setup
- **🎨 [Custom CSS Guide](guides/CUSTOM_CSS_GUIDE.md)** - Interface customization and theming
- **🔥 [Firewall Blocking Feature Guide](guides/FIREWALL_BLOCKING_FEATURE.md)** - Security features and configuration
