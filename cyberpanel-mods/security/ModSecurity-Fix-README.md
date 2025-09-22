# CyberPanel ModSecurity Rules Fix

## Overview

This fix addresses common issues with ModSecurity Rules Packages in CyberPanel where OWASP ModSecurity Core Rules show as "off" even after installation. The problem typically occurs due to:

1. **Incorrect status detection logic** - The system doesn't properly detect installed OWASP rules
2. **Outdated download URLs** - The OWASP rules download URL was incorrect
3. **JavaScript state synchronization issues** - Frontend toggle state doesn't sync with backend
4. **Missing error handling** - Insufficient logging and error reporting

## Issues Fixed

### 1. Status Detection Logic (`firewallManager.py`)
- **Problem**: The `getOWASPAndComodoStatus` method only checked for `modsec/owasp` in configuration files
- **Fix**: Added multiple detection methods:
  - Check for `modsec/owasp` in configuration
  - Check for `owasp-modsecurity-crs` in configuration  
  - Verify actual file existence in filesystem
  - Added similar verification for Comodo rules

### 2. OWASP Rules Download (`modSec.py`)
- **Problem**: Used incorrect GitHub URL that resulted in 404 errors
- **Fix**: Updated to use correct GitHub repository URL:
  - Old: `https://github.com/coreruleset/coreruleset/archive/v3.3.2/master.zip`
  - New: `https://github.com/coreruleset/coreruleset/archive/refs/tags/v4.0.0.zip`

### 3. JavaScript State Synchronization (`firewall.js`)
- **Problem**: Toggle state variables weren't properly updated when status was fetched
- **Fix**: Added proper state variable updates (`owaspInstalled`, `comodoInstalled`) in both update scenarios

### 4. Error Handling and Logging (`modSec.py`)
- **Problem**: Insufficient logging made debugging difficult
- **Fix**: Added comprehensive logging throughout the installation process:
  - Download progress logging
  - Extraction progress logging
  - File verification logging
  - Installation verification

## Files Modified

1. **`cyberpanel/firewall/firewallManager.py`**
   - Enhanced `getOWASPAndComodoStatus` method
   - Added filesystem verification for rule packages

2. **`cyberpanel/plogical/modSec.py`**
   - Updated OWASP download URL to v4.0.0
   - Added comprehensive logging
   - Added installation verification
   - Improved error handling
   - Updated to use simplified CRS v4.0.0 structure

3. **`cyberpanel/firewall/static/firewall/firewall.js`**
   - Fixed JavaScript state synchronization
   - Added proper variable updates

## Manual Fix Script

A comprehensive fix script is provided at `cyberpanel/cyberpanel-mods/security/modsecurity-fix.sh` that:

1. **Backs up** current configuration
2. **Downloads and installs** OWASP ModSecurity Core Rules v3.3.4
3. **Creates proper configuration files**
4. **Sets correct permissions**
5. **Updates LiteSpeed configuration**
6. **Restarts LiteSpeed**
7. **Verifies installation**

### Running the Fix Script

```bash
# Make the script executable
chmod +x cyberpanel/cyberpanel-mods/security/modsecurity-fix.sh

# Run the fix script
./cyberpanel/cyberpanel-mods/security/modsecurity-fix.sh
```

## Manual Installation Steps

If you prefer to fix the issue manually:

### 1. Download OWASP Rules
```bash
cd /tmp
wget https://github.com/coreruleset/coreruleset/archive/refs/tags/v4.0.0.zip -O owasp.zip
unzip owasp.zip -d /usr/local/lsws/conf/modsec/
mv /usr/local/lsws/conf/modsec/coreruleset-4.0.0 /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.0.0
```

### 2. Set Up Configuration Files
```bash
cd /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.0.0
cp crs-setup.conf.example crs-setup.conf
cp rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf.example rules/REQUEST-900-EXCLUSION-RULES-BEFORE-CRS.conf
cp rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf.example rules/RESPONSE-999-EXCLUSION-RULES-AFTER-CRS.conf
```

### 3. Create Master Configuration
Create `/usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.0.0/owasp-master.conf`:

```apache
include /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.0.0/crs.conf
```

**Note**: CRS v4.0.0 uses a simplified structure with a single `crs.conf` file that includes all necessary rules, unlike v3.x which required individual rule file includes.

### Key Differences in CRS v4.0.0:
- **Simplified Configuration**: Single `crs.conf` file instead of multiple individual rule files
- **Plugin System**: Replaced application exclusion packages with a plugin system
- **Improved Performance**: Better rule organization and execution
- **Enhanced Security**: Updated attack patterns and detection methods
- **Better Documentation**: Improved configuration examples and guides

### 4. Update LiteSpeed Configuration
Add to `/usr/local/lsws/conf/httpd_config.conf`:

```apache
modsecurity_rules_file /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-4.0.0/owasp-master.conf
```

### 5. Set Permissions and Restart
```bash
chown -R lsadm:lsadm /usr/local/lsws/conf/modsec
chmod -R 755 /usr/local/lsws/conf/modsec
systemctl restart lsws
```

## Verification

After applying the fix:

1. **Access CyberPanel** → Security → ModSecurity Rules Packages
2. **Check Status**: OWASP ModSecurity Core Rules should show as "enabled"
3. **Test Toggle**: The toggle should work properly (enable/disable)
4. **Check Logs**: Verify no errors in ModSecurity logs

## Troubleshooting

### Common Issues

1. **Rules still show as disabled**
   - Check file permissions: `ls -la /usr/local/lsws/conf/modsec/owasp-modsecurity-crs-3.0-master/`
   - Verify configuration: `grep -i owasp /usr/local/lsws/conf/httpd_config.conf`
   - Check LiteSpeed logs: `tail -f /usr/local/lsws/logs/error.log`

2. **Download fails**
   - Check internet connectivity
   - Verify GitHub access: `curl -I https://github.com/coreruleset/coreruleset/archive/refs/tags/v3.3.4.zip`
   - Try manual download and extraction

3. **LiteSpeed won't start**
   - Check configuration syntax: `/usr/local/lsws/bin/lshttpd -t`
   - Restore backup: `cp /usr/local/lsws/conf/httpd_config.conf.backup.* /usr/local/lsws/conf/httpd_config.conf`
   - Check ModSecurity syntax

### Log Files

- **ModSecurity Log**: `/usr/local/lsws/logs/modsec.log`
- **Audit Log**: `/usr/local/lsws/logs/auditmodsec.log`
- **Installation Log**: `/home/cyberpanel/modSecInstallLog`
- **LiteSpeed Error Log**: `/usr/local/lsws/logs/error.log`

## Security Considerations

1. **Rule Updates**: Regularly update OWASP rules for latest security patterns
2. **False Positives**: Monitor logs for legitimate traffic being blocked
3. **Performance**: OWASP rules can impact performance - monitor server resources
4. **Custom Rules**: Add custom rules in `/usr/local/lsws/conf/modsec/rules.conf`

## Support

If you encounter issues after applying this fix:

1. Check the troubleshooting section above
2. Review log files for specific error messages
3. Verify all file permissions and ownership
4. Test with a simple configuration first

## Changelog

- **v1.0**: Initial fix for ModSecurity status detection issues
- **v1.1**: Added comprehensive logging and error handling
- **v1.2**: Updated to OWASP CRS v4.0.0 and improved verification
- **v1.3**: Simplified configuration structure for CRS v4.0.0 compatibility
