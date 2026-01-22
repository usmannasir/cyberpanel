# CyberPanel AI Security Scanner Documentation

## Overview

The CyberPanel AI Security Scanner is an advanced security tool that uses artificial intelligence to scan WordPress websites for vulnerabilities, malware, and security threats. It provides comprehensive security analysis with detailed findings and recommendations.

## Table of Contents

1. [Features](#features)
2. [Getting Started](#getting-started)
3. [Configuration](#configuration)
4. [Running Scans](#running-scans)
5. [Understanding Scan Results](#understanding-scan-results)
6. [VPS Free Scans](#vps-free-scans)
7. [API Integration](#api-integration)
8. [Troubleshooting](#troubleshooting)

## Features

- **AI-Powered Analysis**: Uses advanced AI models to detect security threats and vulnerabilities
- **Real-time Scanning**: Monitor scan progress in real-time with live updates
- **Comprehensive Coverage**: Scans WordPress core files, themes, plugins, and custom code
- **Multiple Scan Types**: Choose between quick scans or full comprehensive scans
- **Detailed Reports**: Get detailed findings with severity levels and remediation suggestions
- **Platform Integration**: View detailed analysis on the CyberPersons platform
- **VPS Free Scans**: Eligible VPS customers get free security scans

## Getting Started

### Prerequisites

- CyberPanel v2.4.2 or higher
- WordPress website(s) hosted on your server
- Active internet connection for API communication

### Initial Setup

1. **Access AI Scanner**
   - Log in to your CyberPanel admin panel
   - Navigate to **Security** → **AI Security Scanner**

2. **Configure Payment Method** (Skip if using VPS free scans)
   - Click on **Setup Payment Method**
   - You'll be redirected to the CyberPersons platform
   - Complete the payment setup process
   - Return to CyberPanel after completion

3. **Verify Setup**
   - Your account balance will be displayed
   - API key will be automatically configured

## Configuration

### Payment Methods

The AI Scanner uses a pay-per-scan model. You can:

1. **Add Payment Method**
   - Click **Add Payment Method** button
   - Complete the setup on the platform
   - Multiple payment methods supported

2. **Check Balance**
   - Current balance displayed on main page
   - Click **Refresh Balance** to update

### User Permissions

- **Admin Users**: Full access to all scans and settings
- **Reseller Users**: Can scan their own websites and view their scan history
- **Regular Users**: Can only scan websites they own

## Running Scans

### Starting a New Scan

1. **Select Website**
   - Choose the WordPress website to scan from the dropdown
   - Only websites you have access to will be shown

2. **Choose Scan Type**
   - **Quick Scan**: Faster scan focusing on critical areas
   - **Full Scan**: Comprehensive scan of all files

3. **Start Scan**
   - Click **Start Scan** button
   - Scan will begin immediately

### Monitoring Progress

During the scan, you can see:
- Current scan phase (Discovering files, Scanning, Analyzing)
- Progress percentage
- Files discovered and scanned
- Threats found in real-time
- Current file being analyzed

### Scan Phases

1. **Starting**: Initializing scan and setting up access
2. **Discovering Files**: Mapping website structure
3. **Scanning Files**: Analyzing files for threats
4. **Completing**: Finalizing analysis and generating report
5. **Completed**: Scan finished, results available

## Understanding Scan Results

### Scan Summary

Each completed scan shows:
- **Domain**: Website that was scanned
- **Scan Type**: Quick or Full scan
- **Duration**: Time taken to complete
- **Files Scanned**: Total number of files analyzed
- **Threats Found**: Number of security issues detected
- **Cost**: Scan cost (if applicable)

### Threat Levels

Threats are categorized by severity:
- **CRITICAL**: Immediate action required
- **HIGH**: Serious issues that should be addressed soon
- **MEDIUM**: Moderate risks that need attention
- **LOW**: Minor issues or recommendations

### Viewing Detailed Results

1. **In CyberPanel**
   - Click on a scan in the history table
   - View summary and key findings
   
2. **On Platform** (Detailed Analysis)
   - Click **View on Platform** button
   - Opens detailed AI analysis in new tab
   - Includes code snippets, explanations, and fixes

## VPS Free Scans

### Eligibility

VPS customers hosted with participating providers receive free security scans:
- Automatic detection based on server IP
- No payment setup required
- Limited number of free scans per month

### Using Free Scans

1. System automatically detects VPS eligibility
2. Free scans available immediately
3. Remaining free scans shown when starting scan
4. After free scans exhausted, payment required

### Security

- Time-limited access tokens
- Scan-specific permissions
- Automatic token expiration
- IP-based restrictions

## Troubleshooting

### Common Issues

1. **"Payment not configured" Error**
   - Complete payment setup process
   - Verify API key is saved
   - Check account balance

2. **"API key not configured" Error**
   - Ensure payment setup completed
   - For VPS users, check eligibility
   - Try refreshing the page

3. **Scan Stuck in "Running" State**
   - Wait 5-10 minutes for completion
   - Check scan status on platform
   - Contact support if persists

4. **"Access Denied" Errors**
   - Verify you own the website
   - Check user permissions
   - Ensure website exists

### Getting Help

1. **Check Logs**
   ```bash
   tail -f /home/cyberpanel/error-logs.txt | grep "AI Scanner"
   ```

2. **Support Channels**
   - CyberPanel Forums: https://community.cyberpanel.net
   - Support Ticket: https://platform.cyberpersons.com

## Best Practices

1. **Regular Scanning** (Upcoming feature)
   - Schedule weekly or monthly scans
   - Scan after major updates
   - Scan new installations

2. **Act on Findings**
   - Address CRITICAL issues immediately
   - Plan remediation for HIGH issues
   - Review all recommendations

3. **Security Hygiene**
   - Keep WordPress updated
   - Remove unused plugins/themes
   - Use strong passwords

## Advanced Usage

### Command Line Interface

For automated scanning:

```python
# Example using CyberPanel API
import requests

# Start a scan
response = requests.post(
    'https://your-server:8090/aiscanner/start-scan/',
    json={
        'domain': 'example.com',
        'scan_type': 'full'
    },
    headers={'Authorization': 'your-api-key'}
)
```

### Integration with CI/CD

Include security scanning in your deployment pipeline:

1. Trigger scan after deployment
2. Wait for completion webhook
3. Fail pipeline if critical issues found

## Changelog

### Version 2.4.2
- Added platform monitor URL integration
- Support for VPS free scans
- Improved error handling
- Enhanced scan progress tracking

### Version 2.4.1
- Initial AI Scanner release
- WordPress security scanning
- Real-time progress updates
- Payment integration

---

**Note**: This documentation is for CyberPanel AI Security Scanner. For platform-specific features, refer to the [CyberPersons Platform Documentation](https://platform.cyberpersons.com/).