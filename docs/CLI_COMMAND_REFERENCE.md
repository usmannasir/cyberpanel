# CyberPanel CLI Command Reference Guide

## Overview

This comprehensive guide covers all available CyberPanel CLI commands for managing your server directly from SSH. The CyberPanel CLI provides powerful command-line tools for website management, system administration, and automation.

## Table of Contents

1. [Getting Started](#getting-started)
2. [Website Management Commands](#website-management-commands)
3. [DNS Management Commands](#dns-management-commands)
4. [Database Management Commands](#database-management-commands)
5. [Email Management Commands](#email-management-commands)
6. [User Management Commands](#user-management-commands)
7. [Package Management Commands](#package-management-commands)
8. [System Administration Commands](#system-administration-commands)
9. [File Management Commands](#file-management-commands)
10. [Application Installation Commands](#application-installation-commands)
11. [Backup and Restore Commands](#backup-and-restore-commands)
12. [Security and Firewall Commands](#security-and-firewall-commands)
13. [Troubleshooting Commands](#troubleshooting-commands)
14. [Advanced Usage Examples](#advanced-usage-examples)

## Getting Started

### Accessing CyberPanel CLI

```bash
# Access CyberPanel CLI
sudo cyberpanel

# Or run specific commands directly
sudo cyberpanel [command] [options]
```

### Basic Syntax

```bash
cyberpanel [function] --parameter1 value1 --parameter2 value2
```

### Getting Help

```bash
# Show all available commands
cyberpanel --help

# Show help for specific command
cyberpanel createWebsite --help
```

## Website Management Commands

### Create Website

```bash
# Basic website creation
cyberpanel createWebsite \
  --package Default \
  --owner admin \
  --domainName example.com \
  --email admin@example.com \
  --php 8.1

# With SSL and DKIM
cyberpanel createWebsite \
  --package Default \
  --owner admin \
  --domainName example.com \
  --email admin@example.com \
  --php 8.1 \
  --ssl 1 \
  --dkim 1
```

**Parameters:**
- `--package`: Package name (e.g., Default, CLI)
- `--owner`: Owner username
- `--domainName`: Domain name to create
- `--email`: Administrator email
- `--php`: PHP version (5.6, 7.0, 7.1, 7.2, 7.3, 7.4, 8.0, 8.1, 8.2, 8.3)
- `--ssl`: Enable SSL (1) or disable (0)
- `--dkim`: Enable DKIM (1) or disable (0)
- `--openBasedir`: Enable open_basedir protection (1) or disable (0)

### Delete Website

```bash
# Delete a website
cyberpanel deleteWebsite \
  --domainName example.com
```

### List Websites

```bash
# List all websites
cyberpanel listWebsites
```

### Change PHP Version

```bash
# Change PHP version for a website
cyberpanel changePHP \
  --domainName example.com \
  --php 8.1
```

### Change Package

```bash
# Change website package
cyberpanel changePackage \
  --domainName example.com \
  --packageName CLI
```

## DNS Management Commands

### Create DNS Record

```bash
# Create A record
cyberpanel createDNSRecord \
  --domainName example.com \
  --name www \
  --recordType A \
  --value 192.168.1.100 \
  --priority 0 \
  --ttl 3600

# Create MX record
cyberpanel createDNSRecord \
  --domainName example.com \
  --name @ \
  --recordType MX \
  --value mail.example.com \
  --priority 10 \
  --ttl 3600

# Create CNAME record
cyberpanel createDNSRecord \
  --domainName example.com \
  --name blog \
  --recordType CNAME \
  --value example.com \
  --priority 0 \
  --ttl 3600
```

**Parameters:**
- `--domainName`: Domain name
- `--name`: Record name (subdomain or @ for root)
- `--recordType`: Record type (A, AAAA, CNAME, MX, TXT, NS, SRV)
- `--value`: Record value (IP address, hostname, text)
- `--priority`: Priority (for MX records)
- `--ttl`: Time to live in seconds

### List DNS Records

```bash
# List DNS records as JSON
cyberpanel listDNSJson \
  --domainName example.com

# List DNS records (human readable)
cyberpanel listDNS \
  --domainName example.com
```

### Delete DNS Record

```bash
# Delete DNS record by ID
cyberpanel deleteDNSRecord \
  --recordID 123
```

## Database Management Commands

### Create Database

```bash
# Create MySQL database
cyberpanel createDatabase \
  --databaseWebsite example.com \
  --dbName mydatabase \
  --dbUsername dbuser \
  --dbPassword securepassword
```

**Parameters:**
- `--databaseWebsite`: Associated website domain
- `--dbName`: Database name
- `--dbUsername`: Database username
- `--dbPassword`: Database password

### Delete Database

```bash
# Delete database
cyberpanel deleteDatabase \
  --dbName mydatabase
```

### List Databases

```bash
# List all databases
cyberpanel listDatabases
```

## Email Management Commands

### Create Email Account

```bash
# Create email account
cyberpanel createEmail \
  --userName admin \
  --password securepassword \
  --databaseWebsite example.com
```

**Parameters:**
- `--userName`: Email username (without @domain.com)
- `--password`: Email password
- `--databaseWebsite`: Associated website domain

### Delete Email Account

```bash
# Delete email account
cyberpanel deleteEmail \
  --userName admin \
  --databaseWebsite example.com
```

### List Email Accounts

```bash
# List email accounts
cyberpanel listEmails \
  --databaseWebsite example.com
```

## User Management Commands

### Create User

```bash
# Create new user
cyberpanel createUser \
  --firstName John \
  --lastName Doe \
  --userName johndoe \
  --email john@example.com \
  --websitesLimit 5 \
  --selectedACL user \
  --securityLevel 0
```

**Parameters:**
- `--firstName`: User's first name
- `--lastName`: User's last name
- `--userName`: Username
- `--email`: User's email address
- `--websitesLimit`: Maximum number of websites
- `--selectedACL`: Access control level (user, reseller, admin)
- `--securityLevel`: Security level (0=normal, 1=high)

### Delete User

```bash
# Delete user
cyberpanel deleteUser \
  --userName johndoe
```

### List Users

```bash
# List all users
cyberpanel listUsers
```

### Change User Password

```bash
# Change user password
cyberpanel changeUserPass \
  --userName johndoe \
  --password newpassword
```

### Suspend/Unsuspend User

```bash
# Suspend user
cyberpanel suspendUser \
  --userName johndoe \
  --state 1

# Unsuspend user
cyberpanel suspendUser \
  --userName johndoe \
  --state 0
```

## Package Management Commands

### Create Package

```bash
# Create hosting package
cyberpanel createPackage \
  --packageName MyPackage \
  --diskSpace 1024 \
  --bandwidth 10240 \
  --emailAccounts 10 \
  --dataBases 5 \
  --ftpAccounts 5 \
  --allowedDomains 3
```

**Parameters:**
- `--packageName`: Package name
- `--diskSpace`: Disk space in MB
- `--bandwidth`: Bandwidth in MB
- `--emailAccounts`: Number of email accounts
- `--dataBases`: Number of databases
- `--ftpAccounts`: Number of FTP accounts
- `--allowedDomains`: Number of allowed domains

### Delete Package

```bash
# Delete package
cyberpanel deletePackage \
  --packageName MyPackage
```

### List Packages

```bash
# List all packages
cyberpanel listPackages
```

## System Administration Commands

### Fix File Permissions

```bash
# Fix file permissions for a domain
cyberpanel fixFilePermissions \
  --domainName example.com
```

**Note**: This command was recently added and fixes file permissions for websites.

### Switch to LiteSpeed Enterprise

```bash
# Switch to LiteSpeed Enterprise
cyberpanel switchTOLSWS \
  --licenseKey YOUR_LITESPEED_LICENSE_KEY
```

### Verify Connection

```bash
# Verify CyberPanel connection
cyberpanel verifyConn \
  --adminUser admin \
  --adminPass yourpassword
```

## File Management Commands

### File Manager Operations

```bash
# List files (via FileManager)
cyberpanel listFiles \
  --domainName example.com \
  --path public_html
```

## Application Installation Commands

### Install WordPress

```bash
# Install WordPress
cyberpanel installWordPress \
  --domainName example.com \
  --password adminpass \
  --siteTitle "My WordPress Site" \
  --path blog
```

**Parameters:**
- `--domainName`: Domain name
- `--password`: WordPress admin password
- `--siteTitle`: Site title
- `--path`: Installation path (optional, defaults to root)

### Install Joomla

```bash
# Install Joomla
cyberpanel installJoomla \
  --domainName example.com \
  --password adminpass \
  --siteTitle "My Joomla Site" \
  --path joomla
```

## Backup and Restore Commands

### Create Backup

```bash
# Create website backup
cyberpanel createBackup \
  --domainName example.com
```

### Restore Backup

```bash
# Restore website backup
cyberpanel restoreBackup \
  --domainName example.com \
  --fileName /path/to/backup/file.tar.gz
```

**Parameters:**
- `--domainName`: Domain name
- `--fileName`: Complete path to backup file

### List Backups

```bash
# List available backups
cyberpanel listBackups \
  --domainName example.com
```

## Security and Firewall Commands

### Firewall Management

```bash
# List firewall rules
cyberpanel listFirewallRules

# Add firewall rule
cyberpanel addFirewallRule \
  --port 8080 \
  --action Allow

# Delete firewall rule
cyberpanel deleteFirewallRule \
  --ruleID 123
```

## Troubleshooting Commands

### System Status

```bash
# Check CyberPanel version
cyberpanel version

# Check system status
cyberpanel status

# Verify installation
cyberpanel verifyInstall
```

### Log Commands

```bash
# View CyberPanel logs
cyberpanel logs

# View error logs
cyberpanel errorLogs

# Clear logs
cyberpanel clearLogs
```

## Advanced Usage Examples

### Automated Website Deployment

```bash
#!/bin/bash
# Script to create a complete website setup

DOMAIN="example.com"
OWNER="admin"
EMAIL="admin@example.com"
PACKAGE="Default"

# Create website
cyberpanel createWebsite \
  --package $PACKAGE \
  --owner $OWNER \
  --domainName $DOMAIN \
  --email $EMAIL \
  --php 8.1 \
  --ssl 1

# Create database
cyberpanel createDatabase \
  --databaseWebsite $DOMAIN \
  --dbName wpdb \
  --dbUsername wpuser \
  --dbPassword $(openssl rand -base64 32)

# Create email
cyberpanel createEmail \
  --userName admin \
  --password $(openssl rand -base64 16) \
  --databaseWebsite $DOMAIN

# Install WordPress
cyberpanel installWordPress \
  --domainName $DOMAIN \
  --password $(openssl rand -base64 16) \
  --siteTitle "My Website"

echo "Website setup complete for $DOMAIN"
```

### Bulk User Creation

```bash
#!/bin/bash
# Script to create multiple users

USERS=("user1" "user2" "user3")

for USER in "${USERS[@]}"; do
    cyberpanel createUser \
      --firstName "$USER" \
      --lastName "User" \
      --userName "$USER" \
      --email "$USER@example.com" \
      --websitesLimit 3 \
      --selectedACL user \
      --securityLevel 0
done
```

### Website Maintenance Script

```bash
#!/bin/bash
# Script for website maintenance

# List all websites
WEBSITES=$(cyberpanel listWebsites | grep -o '"[^"]*\.com"' | tr -d '"')

for WEBSITE in $WEBSITES; do
    echo "Processing $WEBSITE..."
    
    # Fix permissions
    cyberpanel fixFilePermissions --domainName $WEBSITE
    
    # Create backup
    cyberpanel createBackup --domainName $WEBSITE
    
    echo "Completed $WEBSITE"
done
```

## Common Error Messages and Solutions

### "Please enter the domain" Error

```bash
# Make sure to include all required parameters
cyberpanel createWebsite \
  --package Default \
  --owner admin \
  --domainName example.com \
  --email admin@example.com \
  --php 8.1
```

### "Administrator not found" Error

```bash
# Verify the owner exists
cyberpanel listUsers | grep admin

# Create the owner if it doesn't exist
cyberpanel createUser \
  --firstName Admin \
  --lastName User \
  --userName admin \
  --email admin@example.com \
  --websitesLimit 10 \
  --selectedACL admin
```

### "Package not found" Error

```bash
# List available packages
cyberpanel listPackages

# Create package if needed
cyberpanel createPackage \
  --packageName Default \
  --diskSpace 1024 \
  --bandwidth 10240 \
  --emailAccounts 10 \
  --dataBases 5 \
  --ftpAccounts 5 \
  --allowedDomains 3
```

## Best Practices

### 1. Always Use Full Parameters

```bash
# Good - explicit parameters
cyberpanel createWebsite \
  --package Default \
  --owner admin \
  --domainName example.com \
  --email admin@example.com \
  --php 8.1

# Avoid - relying on defaults
cyberpanel createWebsite --domainName example.com
```

### 2. Use Strong Passwords

```bash
# Generate secure passwords
cyberpanel createDatabase \
  --databaseWebsite example.com \
  --dbName mydb \
  --dbUsername dbuser \
  --dbPassword $(openssl rand -base64 32)
```

### 3. Backup Before Changes

```bash
# Always backup before making changes
cyberpanel createBackup --domainName example.com
cyberpanel changePHP --domainName example.com --php 8.1
```

### 4. Use Scripts for Automation

```bash
# Create reusable scripts
cat > setup-website.sh << 'EOF'
#!/bin/bash
DOMAIN=$1
if [ -z "$DOMAIN" ]; then
    echo "Usage: $0 domain.com"
    exit 1
fi

cyberpanel createWebsite \
  --package Default \
  --owner admin \
  --domainName $DOMAIN \
  --email admin@$DOMAIN \
  --php 8.1 \
  --ssl 1
EOF

chmod +x setup-website.sh
./setup-website.sh example.com
```

## Integration with Automation Tools

### Ansible Playbook Example

```yaml
---
- name: Setup CyberPanel Website
  hosts: cyberpanel_servers
  tasks:
    - name: Create website
      command: >
        cyberpanel createWebsite
        --package {{ package_name }}
        --owner {{ owner_name }}
        --domainName {{ domain_name }}
        --email {{ admin_email }}
        --php {{ php_version }}
      register: website_result

    - name: Create database
      command: >
        cyberpanel createDatabase
        --databaseWebsite {{ domain_name }}
        --dbName {{ db_name }}
        --dbUsername {{ db_user }}
        --dbPassword {{ db_password }}
      when: website_result.rc == 0
```

### Docker Integration

```dockerfile
FROM ubuntu:20.04

# Install CyberPanel
RUN wget -O - https://cyberpanel.sh/install.sh | bash

# Copy setup script
COPY setup.sh /usr/local/bin/
RUN chmod +x /usr/local/bin/setup.sh

# Run setup on container start
CMD ["/usr/local/bin/setup.sh"]
```

## Getting Help

### Command Help

```bash
# Get help for any command
cyberpanel [command] --help

# Example
cyberpanel createWebsite --help
```

### Logs and Debugging

```bash
# Check CyberPanel logs
tail -f /usr/local/lscp/logs/error.log

# Check system logs
journalctl -u lscpd -f

# Enable debug mode
export CYBERPANEL_DEBUG=1
cyberpanel createWebsite --domainName example.com
```

### Community Support

- **CyberPanel Forums**: https://community.cyberpanel.net
- **GitHub Issues**: https://github.com/usmannasir/cyberpanel/issues
- **Discord Server**: https://discord.gg/cyberpanel

---

**Note**: This guide covers the most commonly used CyberPanel CLI commands. For the complete list of available commands and their parameters, run `cyberpanel --help` on your server.

*Last updated: January 2025*
