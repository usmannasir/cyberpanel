# Dynamic Version Fetching Implementation

## Overview

CyberPanel has been enhanced to automatically fetch and use the latest versions of phpMyAdmin and SnappyMail from GitHub during installation and upgrade processes, instead of relying on hardcoded version numbers.

## What's New

### ✅ **Dynamic Version Fetching**
- **GitHub API Integration**: Fetches latest versions from official GitHub repositories
- **Automatic Updates**: Always installs the latest available versions
- **Fallback Protection**: Uses stable fallback versions if GitHub API is unavailable
- **Real-time Detection**: Checks for new versions every time install/upgrade runs

### ✅ **Components Updated**
- **phpMyAdmin**: Fetches from `phpmyadmin/phpmyadmin` repository
- **SnappyMail**: Fetches from `the-djmaze/snappymail` repository

## Implementation Details

### 1. Version Fetcher Module (`plogical/versionFetcher.py`)

**Features:**
- GitHub API integration with proper error handling
- Fallback versions for reliability
- Comprehensive logging
- Easy-to-use interface

**Key Functions:**
```python
get_latest_phpmyadmin_version()  # Get latest phpMyAdmin version
get_latest_snappymail_version()  # Get latest SnappyMail version
get_latest_versions()            # Get all latest versions
test_connectivity()              # Test GitHub API access
```

### 2. Updated Installation Script (`install/install.py`)

**Changes:**
- Dynamic version fetching before installation
- Fallback to stable versions if API fails
- Clear logging of version selection process

**Process:**
1. Try to fetch latest version from GitHub
2. If successful, use latest version
3. If failed, use fallback version
4. Log the decision for transparency

### 3. Updated Upgrade Script (`plogical/upgrade.py`)

**Changes:**
- Dynamic version fetching before upgrade
- Same fallback mechanism as installation
- Maintains existing upgrade logic

### 4. Enhanced Version Managers

**phpMyAdmin Version Manager (`cyberpanel-mods/version-managers/phpmyadmin_v_changer.sh`):**
- Fetches latest version from GitHub API
- Uses latest as default option
- Falls back to 5.2.2 if API unavailable

**SnappyMail Version Manager (`cyberpanel-mods/version-managers/snappymail_v_changer.sh`):**
- Fetches latest version from GitHub API
- Uses latest as default option
- Falls back to 2.38.2 if API unavailable

## How It Works

### Installation Process
1. **Version Detection**: Script queries GitHub API for latest versions
2. **Version Selection**: Uses latest if available, fallback if not
3. **Download**: Downloads the selected version
4. **Installation**: Proceeds with normal installation process

### Upgrade Process
1. **Version Detection**: Same as installation
2. **Backup**: Creates backup of existing installation
3. **Download**: Downloads latest version
4. **Replacement**: Replaces old version with new
5. **Configuration**: Restores configuration files

### Fallback Mechanism
- **API Unavailable**: Uses hardcoded fallback versions
- **Invalid Response**: Uses hardcoded fallback versions
- **Network Issues**: Uses hardcoded fallback versions
- **Timeout**: Uses hardcoded fallback versions

## Benefits

### 🚀 **Always Latest**
- Users automatically get the newest versions
- No need to manually update version numbers
- Immediate access to new features and security fixes

### 🛡️ **Reliable**
- Fallback versions ensure installation always works
- No dependency on external services for basic functionality
- Graceful degradation if GitHub API is down

### 🔧 **Maintainable**
- No more manual version updates in code
- Centralized version management
- Easy to add new components

### 📊 **Transparent**
- Clear logging of version selection process
- Users can see which version is being used
- Easy to debug version-related issues

## Usage Examples

### For New Installations
```bash
# CyberPanel will automatically fetch latest versions
sh <(curl https://cyberpanel.net/install.sh)
```

### For Upgrades
```bash
# CyberPanel will automatically fetch latest versions
sh <(curl https://cyberpanel.net/upgrade.sh)
```

### For Manual Version Management
```bash
# phpMyAdmin version manager (now with latest detection)
cd /path/to/cyberpanel-mods/version-managers/
./phpmyadmin_v_changer.sh

# SnappyMail version manager (now with latest detection)
./snappymail_v_changer.sh
```

## Configuration

### Fallback Versions
Current fallback versions (can be updated in `versionFetcher.py`):
- **phpMyAdmin**: 5.2.2
- **SnappyMail**: 2.38.2

### API Settings
- **Timeout**: 10 seconds
- **User Agent**: CyberPanel-VersionFetcher/1.0
- **Rate Limiting**: Respects GitHub API limits

## Testing

### Test Script
A test script is provided to verify functionality:
```bash
cd /usr/local/CyberCP/
python3 test_version_fetcher.py
```

### Manual Testing
1. **Check Logs**: Look for version selection messages
2. **Verify Versions**: Check installed versions in admin panels
3. **Test Fallback**: Disconnect internet and test installation

## Troubleshooting

### Common Issues

1. **GitHub API Rate Limiting**
   - **Solution**: Wait and retry, or use fallback versions

2. **Network Connectivity**
   - **Solution**: Check internet connection, fallback versions will be used

3. **Invalid Version Format**
   - **Solution**: Fallback versions will be used automatically

4. **Import Errors**
   - **Solution**: Ensure `versionFetcher.py` is in the correct location

### Debug Information

**Log Messages:**
- `"Using latest [component] version: X.Y.Z"`
- `"Using fallback [component] version: X.Y.Z"`
- `"Failed to fetch latest [component] version, using fallback: [error]"`

**Test Connectivity:**
```python
from plogical.versionFetcher import VersionFetcher
print(VersionFetcher.test_connectivity())
```

## Future Enhancements

### Potential Improvements
1. **Caching**: Cache version information to reduce API calls
2. **More Components**: Add support for other CyberPanel components
3. **Version Comparison**: Compare current vs latest versions
4. **Update Notifications**: Notify users of available updates
5. **Custom Repositories**: Support for custom component repositories

### Adding New Components
To add support for a new component:

1. **Add to `REPOSITORIES`** in `versionFetcher.py`
2. **Add fallback version** to `FALLBACK_VERSIONS`
3. **Update install/upgrade scripts** to use the new component
4. **Test thoroughly** with the new component

## Changelog

- **2025-01-21**: Initial implementation of dynamic version fetching
  - Created `versionFetcher.py` module
  - Updated install script with dynamic version fetching
  - Updated upgrade script with dynamic version fetching
  - Enhanced version managers with latest version detection
  - Added comprehensive fallback mechanisms
  - Created test script and documentation

## Security Considerations

- **API Access**: Only reads public release information
- **No Authentication**: No credentials required
- **Rate Limiting**: Respects GitHub API limits
- **Fallback Security**: Fallback versions are known stable versions
- **Validation**: Version strings are validated before use

This implementation ensures that CyberPanel users always get the latest versions of phpMyAdmin and SnappyMail while maintaining reliability through robust fallback mechanisms.
