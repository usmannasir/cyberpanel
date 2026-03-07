# CyberPanel 2FA Authentication Guide

## Overview

CyberPanel supports multiple two-factor authentication (2FA) methods to enhance security for user accounts. This guide covers all available authentication methods, their setup, and best practices.

## Table of Contents

1. [Available Authentication Methods](#available-authentication-methods)
2. [Traditional 2FA (TOTP)](#traditional-2fa-totp)
3. [WebAuthn/Passkey Authentication](#webauthnpasskey-authentication)
4. [Password Authentication](#password-authentication)
5. [Combined Authentication Strategies](#combined-authentication-strategies)
6. [Administrator Management](#administrator-management)
7. [Troubleshooting](#troubleshooting)
8. [Security Best Practices](#security-best-practices)

## Available Authentication Methods

### 1. Traditional 2FA (TOTP)
- **Type**: Time-based One-Time Password
- **Method**: Google Authenticator, Authy, or similar apps
- **Security Level**: High
- **User Experience**: Requires manual code entry

### 2. WebAuthn/Passkey Authentication
- **Type**: Modern passwordless authentication
- **Method**: Biometric authentication, security keys, or device passkeys
- **Security Level**: Very High
- **User Experience**: Seamless and user-friendly

### 3. Password Authentication
- **Type**: Traditional username/password
- **Method**: Standard login credentials
- **Security Level**: Basic
- **User Experience**: Simple but less secure

## Traditional 2FA (TOTP)

### How It Works
TOTP generates time-based codes that change every 30 seconds. Users scan a QR code with their authenticator app to set up 2FA.

### Setting Up TOTP 2FA

#### For Users
1. **Access User Management**
   - Log in to CyberPanel
   - Go to **User Management** → **Modify User**
   - Select your user account

2. **Enable 2FA**
   - Scroll to **Additional Features** section
   - Check **"Enable Two-Factor Authentication (2FA)"**
   - A QR code will appear

3. **Configure Authenticator App**
   - Open your authenticator app (Google Authenticator, Authy, etc.)
   - Scan the QR code displayed
   - Or manually enter the secret key shown below the QR code

4. **Test 2FA**
   - Enter a 6-digit code from your authenticator app
   - Verify the setup works correctly

#### For Administrators
1. **Access User Management**
   - Go to **User Management** → **Modify User**
   - Select the user you want to configure

2. **Enable 2FA for User**
   - Check **"Enable Two-Factor Authentication (2FA)"**
   - Provide the QR code or secret key to the user
   - Ensure the user completes the setup

### TOTP Configuration Options

#### Secret Key Management
- **Auto-generation**: CyberPanel automatically generates secure secret keys
- **Manual Entry**: Users can manually enter the secret key if QR scanning fails
- **Regeneration**: Secret keys can be regenerated if needed

#### QR Code Display
- **Automatic Display**: QR code appears when 2FA is enabled
- **Manual Key**: Secret key is always displayed for manual entry
- **Copy Function**: One-click copy to clipboard functionality

### Supported Authenticator Apps
- **Google Authenticator** (iOS/Android)
- **Authy** (iOS/Android/Desktop)
- **Microsoft Authenticator** (iOS/Android)
- **1Password** (iOS/Android/Desktop)
- **Bitwarden** (iOS/Android/Desktop)
- **Any TOTP-compatible app**

## WebAuthn/Passkey Authentication

### What is WebAuthn?
WebAuthn is a web standard that enables secure, passwordless authentication using public-key cryptography. It supports biometric authentication, security keys, and device passkeys.

**Login behaviour**: The login page supports **passkey-first** sign-in: users can click "Login with Passkey" without entering a username. Passkeys are managed under **User Management → Modify User**. The relying party ID (`rp_id`) and origin are derived from the current request host only (never hardcoded), so WebAuthn works on any domain or IP (e.g. `https://207.180.193.210:2087`).

### Setting Up WebAuthn

#### Prerequisites
- **HTTPS Required**: WebAuthn only works over secure connections
- **Modern Browser**: Chrome 67+, Firefox 60+, Safari 14+, Edge 79+
- **Compatible Device**: Device with biometric sensors or security key

#### For Users
1. **Access User Management**
   - Go to **User Management** → **Modify User**
   - Select your user account

2. **Enable WebAuthn**
   - Scroll to **Passkey Authentication (WebAuthn)** section
   - Check **"Enable Passkey Authentication"**

3. **Configure Settings**
   - **Require Passkey for Login**: Enable for passwordless authentication
   - **Allow Multiple Passkeys**: Enable to register multiple devices
   - **Max Passkeys**: Set limit (default: 10)
   - **Timeout**: Set timeout in seconds (default: 60)

4. **Register Passkeys**
   - Click **"Register New Passkey"**
   - Enter a name for your passkey (e.g., "iPhone", "Laptop")
   - Follow your browser's prompts to complete registration
   - Repeat for additional devices

#### For Administrators
1. **Access User Management**
   - Go to **User Management** → **Modify User**
   - Select the user you want to configure

2. **Enable WebAuthn for User**
   - Check **"Enable Passkey Authentication"**
   - Configure security policies
   - Monitor registered passkeys

### WebAuthn Features

#### Passkey Management
- **Multiple Devices**: Register passkeys on phones, laptops, security keys
- **Custom Names**: Give descriptive names to your passkeys
- **Easy Removal**: Delete passkeys you no longer need
- **Backup Options**: Multiple passkeys for redundancy

#### Security Features
- **Replay Protection**: Each authentication uses a unique challenge
- **Credential Isolation**: Passkeys cannot be extracted or shared
- **User Verification**: Optional biometric or PIN verification
- **Session Management**: Secure session handling with expiration

### Supported WebAuthn Devices
- **Smartphones**: iPhone, Android phones with biometrics
- **Laptops**: MacBooks with Touch ID, Windows Hello devices
- **Security Keys**: YubiKey, Google Titan, etc.
- **Tablets**: iPads, Android tablets with biometrics

## Password Authentication

### Traditional Login
- **Username/Password**: Standard login credentials
- **Security Level**: Basic (not recommended alone)
- **Use Case**: Fallback authentication method

### Password Requirements
- **Minimum Length**: 8 characters (recommended: 12+)
- **Complexity**: Mix of uppercase, lowercase, numbers, symbols
- **Uniqueness**: Different from other accounts
- **Regular Updates**: Change passwords periodically

## Combined Authentication Strategies

### Strategy 1: Password + 2FA
- **Login Process**: Username + Password + TOTP code
- **Security Level**: High
- **User Experience**: Moderate (requires manual code entry)
- **Best For**: Users who prefer traditional 2FA

### Strategy 2: Password + Passkeys
- **Login Process**: Username + Password + Passkey
- **Security Level**: Very High
- **User Experience**: Good (biometric authentication)
- **Best For**: Users with compatible devices

### Strategy 3: Passkeys Only (Passwordless)
- **Login Process**: Username + Passkey only
- **Security Level**: Very High
- **User Experience**: Excellent (no password required)
- **Best For**: Security-conscious users with multiple devices

### Strategy 4: All Methods (Maximum Security)
- **Login Process**: Username + Password + 2FA + Passkeys
- **Security Level**: Maximum
- **User Experience**: Complex but flexible
- **Best For**: High-security environments

## Administrator Management

### User Authentication Settings

#### Accessing User Settings
1. **Navigate to User Management**
   - Go to **User Management** → **Modify User**
   - Select the user to manage

#### Available Settings
- **Enable/Disable 2FA**: Toggle TOTP authentication
- **Enable/Disable WebAuthn**: Toggle passkey authentication
- **Security Policies**: Set passkey limits and timeouts
- **View Credentials**: See registered passkeys and 2FA status

### Security Policies

#### Passkey Policies
- **Maximum Passkeys**: Limit number of registered passkeys per user
- **Timeout Settings**: Set authentication timeout duration
- **Device Requirements**: Specify required device capabilities

#### 2FA Policies
- **Secret Key Management**: Control secret key generation and regeneration
- **QR Code Display**: Manage QR code visibility
- **Backup Codes**: Generate backup codes for recovery

### Monitoring and Auditing

#### Authentication Logs
- **Login Attempts**: Track all authentication attempts
- **Method Used**: Record which authentication method was used
- **Success/Failure**: Monitor authentication success rates
- **Device Information**: Log device and browser details

#### Security Alerts
- **Failed Attempts**: Alert on multiple failed login attempts
- **Unusual Activity**: Detect suspicious authentication patterns
- **Device Changes**: Notify when new devices are registered

## Troubleshooting

### Common TOTP Issues

#### QR Code Not Scanning
**Problem**: QR code cannot be scanned by authenticator app
**Solutions**:
- Try manual key entry instead
- Ensure good lighting and camera focus
- Try a different authenticator app
- Regenerate the QR code

#### Time Synchronization Issues
**Problem**: Codes not working due to time differences
**Solutions**:
- Check device time is correct
- Sync device time with internet
- Try a different authenticator app
- Contact administrator for assistance

#### Lost Authenticator Device
**Problem**: Cannot access authenticator app
**Solutions**:
- Use backup codes if available
- Contact administrator to reset 2FA
- Set up 2FA on a new device
- Use alternative authentication methods

### Common WebAuthn Issues

#### "WebAuthn not supported" Error
**Problem**: Browser or device doesn't support WebAuthn
**Solutions**:
- Update browser to latest version
- Ensure HTTPS is enabled
- Check device compatibility
- Try a different browser

#### Registration Failed
**Problem**: Passkey registration fails
**Solutions**:
- Check browser console for errors
- Ensure user has permission to register passkeys
- Verify WebAuthn settings are properly configured
- Try a different device or browser

#### Authentication Failed
**Problem**: Passkey authentication fails
**Solutions**:
- Ensure passkey is still active
- Check that user has registered passkeys
- Verify challenge hasn't expired
- Try a different passkey or device

### General Authentication Issues

#### Login Not Working
**Problem**: Cannot log in with any method
**Solutions**:
- Check username and password
- Verify 2FA codes are current
- Ensure passkeys are properly registered
- Contact administrator for assistance

#### Account Locked
**Problem**: Account is locked due to failed attempts
**Solutions**:
- Wait for lockout period to expire
- Contact administrator to unlock account
- Check for security alerts
- Review recent login attempts

## Security Best Practices

### For Users

#### Password Security
- **Use Strong Passwords**: 12+ characters with mixed case, numbers, symbols
- **Unique Passwords**: Different password for each account
- **Regular Updates**: Change passwords every 90 days
- **Password Manager**: Use a reputable password manager

#### 2FA Security
- **Secure Device**: Use a trusted device for authenticator apps
- **Backup Codes**: Save backup codes in a secure location
- **Multiple Methods**: Set up multiple authentication methods
- **Regular Testing**: Test authentication methods regularly

#### WebAuthn Security
- **Multiple Passkeys**: Register passkeys on multiple devices
- **Secure Devices**: Only register passkeys on trusted devices
- **Regular Review**: Periodically review registered passkeys
- **Device Security**: Keep devices updated and secure

### For Administrators

#### System Security
- **HTTPS Enforcement**: Ensure all authentication uses HTTPS
- **Regular Updates**: Keep CyberPanel and dependencies updated
- **Monitoring**: Monitor authentication logs and alerts
- **Backup**: Regular backups of authentication data

#### User Management
- **Access Control**: Implement proper user access controls
- **Security Policies**: Enforce strong security policies
- **Training**: Provide security training to users
- **Incident Response**: Have procedures for security incidents

#### Configuration Security
- **Default Settings**: Change default passwords and settings
- **Network Security**: Implement proper network security
- **Logging**: Enable comprehensive logging
- **Auditing**: Regular security audits

## Advanced Configuration

### Custom Security Policies

#### Passkey Policies
```python
# Example: Custom passkey policies
WEBAUTHN_POLICIES = {
    'max_credentials_per_user': 5,
    'timeout_seconds': 120,
    'require_user_verification': True,
    'allowed_attestation_formats': ['none', 'packed']
}
```

#### 2FA Policies
```python
# Example: Custom 2FA policies
TOTP_POLICIES = {
    'secret_key_length': 32,
    'time_step': 30,
    'window': 1,
    'issuer_name': 'CyberPanel'
}
```

### Integration with External Systems

#### LDAP Integration
- **Active Directory**: Integrate with Windows Active Directory
- **OpenLDAP**: Connect to OpenLDAP servers
- **Multi-Factor**: Combine with external MFA systems

#### SSO Integration
- **SAML**: Single Sign-On with SAML providers
- **OAuth**: OAuth-based authentication
- **Custom Providers**: Integration with custom identity providers

## Migration and Upgrades

### Upgrading Authentication Methods

#### From Password to 2FA
1. **Enable 2FA**: Add TOTP authentication
2. **Test Setup**: Verify 2FA works correctly
3. **User Training**: Train users on 2FA usage
4. **Gradual Rollout**: Enable for users progressively

#### From 2FA to WebAuthn
1. **Enable WebAuthn**: Add passkey support
2. **User Migration**: Help users register passkeys
3. **Dual Support**: Support both methods during transition
4. **Full Migration**: Complete transition to WebAuthn

### Backup and Recovery

#### Authentication Backup
- **Secret Keys**: Backup TOTP secret keys securely
- **Passkey Data**: Backup WebAuthn credential data
- **User Data**: Regular backups of user authentication data
- **Configuration**: Backup authentication configuration

#### Recovery Procedures
- **Account Recovery**: Procedures for locked accounts
- **Data Restoration**: Restore authentication data from backups
- **Emergency Access**: Emergency access procedures
- **User Support**: Support procedures for authentication issues

## Conclusion

CyberPanel's multi-layered authentication system provides flexible and secure access control. By combining traditional 2FA with modern WebAuthn passkeys, administrators can offer users both security and convenience.

Choose the authentication methods that best fit your security requirements and user needs. Remember to regularly review and update your authentication policies to maintain optimal security.

For additional support and advanced configuration options, refer to the CyberPanel documentation and community resources.

---

**Note**: This guide covers all available authentication methods in CyberPanel. For the latest updates and additional features, refer to the official CyberPanel documentation.

*Last updated: January 2025*
