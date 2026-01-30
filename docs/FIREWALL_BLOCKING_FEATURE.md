# Firewall Blocking Feature for CyberPanel

## Overview

This feature adds a convenient "Block IP" button directly in the CyberPanel dashboard's SSH Security Analysis section, allowing administrators to quickly block malicious IP addresses without needing to access SSH or manually run firewall commands.

## Features

- **One-Click IP Blocking**: Block malicious IPs directly from the dashboard
- **Firewalld Integration**: Works with firewalld (the standard Linux firewall)
- **Visual Feedback**: Loading states, success notifications, and blocked status indicators
- **Security Integration**: Automatically appears on "Brute Force Attack Detected" alerts
- **Admin-Only Access**: Restricted to administrators with CyberPanel addons

## Implementation Details

### Backend Changes

#### 1. New API Endpoint (`/base/blockIPAddress`)
- **File**: `cyberpanel/baseTemplate/views.py`
- **Method**: POST
- **Authentication**: Admin-only with CyberPanel addons
- **Functionality**:
  - Validates IP address format
  - Verifies firewalld is active
  - Blocks IP using firewalld commands
  - Logs the action for audit purposes

#### 2. URL Configuration
- **File**: `cyberpanel/baseTemplate/urls.py`
- **Route**: `re_path(r'^blockIPAddress$', views.blockIPAddress, name='blockIPAddress')`

### Frontend Changes

#### 1. Template Updates
- **File**: `cyberpanel/baseTemplate/templates/baseTemplate/homePage.html`
- **Changes**:
  - Added "Block IP" button for brute force attack alerts
  - Visual feedback for blocking status
  - Success indicators for blocked IPs

#### 2. JavaScript Functionality
- **File**: `cyberpanel/baseTemplate/static/baseTemplate/custom-js/system-status.js`
- **Features**:
  - `blockIPAddress()` function for handling IP blocking
  - Loading states and error handling
  - Success notifications using PNotify
  - Automatic security analysis refresh

## Usage

### Prerequisites
1. CyberPanel with admin privileges
2. CyberPanel addons enabled
3. Active firewalld service

### How to Use
1. Navigate to **Dashboard** in CyberPanel
2. Click on **SSH Logs** tab in the Activity Board
3. Click **Refresh Analysis** to scan for security threats
4. Look for **"Brute Force Attack Detected"** alerts
5. Click the **"Block IP"** button next to malicious IP addresses
6. Confirm the blocking action in the success notification

### Visual Indicators
- **Red "Block IP" Button**: Available for blocking
- **Spinning Icon**: Blocking in progress
- **Green "Blocked" Status**: IP successfully blocked
- **Notifications**: Success/error messages with details

## Firewall Commands Used

### firewalld
```bash
firewall-cmd --permanent --add-rich-rule="rule family=ipv4 source address=<ip_address> drop"
firewall-cmd --reload
```

## Security Considerations

1. **Admin-Only Access**: Feature restricted to administrators
2. **Premium Feature**: Requires CyberPanel addons
3. **Enhanced IP Validation**: Validates IP address format and prevents blocking private/reserved ranges
4. **Command Injection Protection**: Uses subprocess with explicit argument lists
5. **Timeout Protection**: Prevents hanging processes with configurable timeouts
6. **Firewalld Verification**: Ensures firewalld service is active
7. **Audit Logging**: All blocking actions are logged
8. **Comprehensive Error Handling**: Detailed error messages with captured stderr

## Error Handling

The feature includes robust error handling for:
- Invalid IP addresses and formats
- Private/reserved IP address ranges
- Firewalld service not active
- Firewall command failures and timeouts
- Network connectivity issues
- Permission errors
- Command injection attempts
- Process timeouts

## Testing

A test script is provided for basic functionality testing:
- `test_firewall_blocking.py` - Basic functionality testing

The feature is best tested through the web interface with various IP address types.

## Enhanced Security Features

### IP Range Validation
The system now prevents blocking of:
- **Private IP ranges**: 10.0.0.0/8, 172.16.0.0/12, 192.168.0.0/16
- **Loopback addresses**: 127.0.0.0/8
- **Link-local addresses**: 169.254.0.0/16
- **Multicast addresses**: 224.0.0.0/4
- **Broadcast addresses**: 255.255.255.255
- **Reserved addresses**: 0.0.0.0

### Command Execution Security
- **Subprocess with explicit arguments**: Prevents command injection
- **Timeout protection**: 10s for status checks, 30s for firewall commands
- **Error capture**: Captures both stdout and stderr for better debugging
- **No shell interpretation**: Eliminates shell injection vulnerabilities

### Example Error Messages
```
"Cannot block private, loopback, link-local, or reserved IP addresses"
"Cannot block system or reserved IP addresses"
"Timeout checking firewalld status"
"Firewall command timed out"
```

## Browser Compatibility

The feature uses modern web technologies and is compatible with:
- Chrome 60+
- Firefox 55+
- Safari 12+
- Edge 79+

## Future Enhancements

Potential improvements for future versions:
1. Bulk IP blocking for multiple threats
2. Temporary blocking with automatic unblocking
3. Integration with threat intelligence feeds
4. Custom blocking rules and policies
5. Blocking history and management interface

## Troubleshooting

### Common Issues

1. **"Premium feature required" error**
   - Ensure CyberPanel addons are enabled
   - Verify admin privileges

2. **"Failed to block IP address" error**
   - Check firewalld service status: `systemctl status firewalld`
   - Verify admin has necessary permissions
   - Check firewalld configuration

3. **Button not appearing**
   - Ensure SSH Security Analysis is enabled
   - Check for brute force attack alerts
   - Verify JavaScript is enabled

### Debug Information

Check CyberPanel logs for detailed error information:
- `/usr/local/CyberCP/logs/cyberpanel.log`
- Firewalld logs: `journalctl -u firewalld`

## Support

For issues or questions regarding this feature:
1. Check CyberPanel documentation
2. Review firewall configuration
3. Check system logs for detailed error messages
4. Contact CyberPanel support if needed

---

**Note**: This feature enhances CyberPanel's security capabilities by providing a streamlined way to block malicious IP addresses directly from the web interface, improving the overall user experience for server administrators.
