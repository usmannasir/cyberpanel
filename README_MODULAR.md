# CyberPanel Modular Installer

This is an enhanced, modular version of the CyberPanel installer that organizes code into manageable modules, each under 500 lines for better maintainability and updates.

## 📁 Module Structure

```
cyberpanel/
├── install.sh                          # Main installer script
├── modules/
│   ├── os/
│   │   └── detect.sh                   # OS detection module (~200 lines)
│   ├── deps/
│   │   ├── manager.sh                  # Dependency manager coordinator (~150 lines)
│   │   ├── rhel_deps.sh               # RHEL-based OS dependencies (~300 lines)
│   │   └── debian_deps.sh             # Debian-based OS dependencies (~250 lines)
│   ├── install/
│   │   └── cyberpanel_installer.sh    # CyberPanel installation logic (~400 lines)
│   └── fixes/
│       └── cyberpanel_fixes.sh        # Common fixes and repairs (~450 lines)
└── README_MODULAR.md                   # This documentation
```

## 🚀 Usage

### Basic Installation
```bash
bash install.sh
```

### Installation with Specific Branch
```bash
bash install.sh -b v2.5.5-dev
```

### Installation with Debug Mode
```bash
bash install.sh --debug
```

### Installation with Commit Hash
```bash
bash install.sh -b commit:abc1234
```

## 🔧 Module Details

### OS Detection Module (`modules/os/detect.sh`)
- Detects operating system and architecture
- Identifies package manager (yum, dnf, apt)
- Installs basic tools (curl, wget)
- Supports: CentOS, AlmaLinux, Rocky Linux, RHEL, CloudLinux, Ubuntu, Debian, openEuler

### Dependency Management (`modules/deps/`)
- **manager.sh**: Coordinates dependency installation
- **rhel_deps.sh**: Handles RHEL-based OS dependencies
- **debian_deps.sh**: Handles Debian-based OS dependencies
- Installs development tools, core packages, and OS-specific requirements

### Installation Logic (`modules/install/cyberpanel_installer.sh`)
- Handles CyberPanel installation process
- Supports fresh install, update, and reinstall
- Includes retry logic (up to 5 attempts)
- Manages different installation types

### Fixes Module (`modules/fixes/cyberpanel_fixes.sh`)
- Fixes common installation issues
- Database connection fixes
- Service configuration fixes
- SSL certificate generation
- File permission fixes
- Status checking and reporting

## 🎯 Benefits of Modular Architecture

1. **Maintainability**: Each module is under 500 lines, making it easy to understand and modify
2. **Modularity**: Changes to one OS don't affect others
3. **Debugging**: Easier to isolate and fix issues
4. **Updates**: Can update individual modules without touching others
5. **Testing**: Each module can be tested independently
6. **Documentation**: Clear separation of concerns

## 🔄 Update Process

To update specific functionality:

1. **OS Support**: Modify `modules/os/detect.sh`
2. **Dependencies**: Update `modules/deps/rhel_deps.sh` or `modules/deps/debian_deps.sh`
3. **Installation Logic**: Modify `modules/install/cyberpanel_installer.sh`
4. **Fixes**: Update `modules/fixes/cyberpanel_fixes.sh`

## 🐛 Troubleshooting

### Module Loading Issues
If a module fails to load, check:
- File permissions (should be executable)
- File path (relative to install.sh)
- Syntax errors in the module

### Dependency Issues
- Check the specific OS module in `modules/deps/`
- Verify package manager commands
- Check for missing repositories

### Installation Issues
- Review the installation module logs
- Check retry attempts in the installer
- Verify CyberPanel source availability

## 📝 Logging

All modules log to `/var/log/cyberpanel_install.log` with timestamps and module identification.

## 🔧 Customization

To add support for a new OS:

1. Add detection logic to `modules/os/detect.sh`
2. Create a new dependency module in `modules/deps/`
3. Update the dependency manager to handle the new OS
4. Test thoroughly

## 📊 Status Reporting

The installer provides comprehensive status reporting including:
- Service status (running, enabled, disabled)
- Port status (listening, not listening)
- Database connectivity
- File system checks
- Resource usage

## 🎉 Success Criteria

A successful installation should show:
- ✅ All critical services running
- ✅ All required ports listening
- ✅ Database connections working
- ✅ No critical failures

This modular approach makes the CyberPanel installer much more maintainable and easier to extend for new operating systems and features.
