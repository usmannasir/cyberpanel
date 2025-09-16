#!/bin/bash

# CyberPanel phpMyAdmin Access Control Deployment Script
# This script implements redirect functionality for unauthenticated phpMyAdmin access

echo "=== CyberPanel phpMyAdmin Access Control Deployment ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"
    exit 1
fi

# Backup original phpMyAdmin index.php if it exists
if [ -f "/usr/local/CyberCP/public/phpmyadmin/index.php" ]; then
    echo "Backing up original phpMyAdmin index.php..."
    cp /usr/local/CyberCP/public/phpmyadmin/index.php /usr/local/CyberCP/public/phpmyadmin/index.php.backup.$(date +%Y%m%d_%H%M%S)
fi

# Deploy the redirect index.php
echo "Deploying phpMyAdmin access control..."
cp /usr/local/CyberCP/phpmyadmin_index_redirect.php /usr/local/CyberCP/public/phpmyadmin/index.php

# Deploy .htaccess for additional protection
echo "Deploying .htaccess protection..."
cp /usr/local/CyberCP/phpmyadmin_htaccess /usr/local/CyberCP/public/phpmyadmin/.htaccess

# Set proper permissions
echo "Setting permissions..."
chown lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/index.php
chmod 644 /usr/local/CyberCP/public/phpmyadmin/index.php
chown lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/.htaccess
chmod 644 /usr/local/CyberCP/public/phpmyadmin/.htaccess

# Restart LiteSpeed to ensure changes take effect
echo "Restarting LiteSpeed..."
systemctl restart lscpd

echo "=== Deployment Complete ==="
echo ""
echo "phpMyAdmin access control has been deployed successfully!"
echo ""
echo "What this does:"
echo "- Users trying to access phpMyAdmin directly without being logged into CyberPanel"
echo "  will now be redirected to the CyberPanel login page (/base/)"
echo "- Authenticated users will continue to access phpMyAdmin normally"
echo ""
echo "To revert changes, restore the backup:"
echo "cp /usr/local/CyberCP/public/phpmyadmin/index.php.backup.* /usr/local/CyberCP/public/phpmyadmin/index.php"
echo ""
echo "Test the implementation by:"
echo "1. Opening an incognito/private browser window"
echo "2. Going to https://your-server:2087/phpmyadmin/"
echo "3. You should be redirected to the CyberPanel login page"
