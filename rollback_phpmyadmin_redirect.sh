#!/bin/bash

# CyberPanel phpMyAdmin Access Control Rollback Script
# This script reverts the phpMyAdmin access control changes

echo "=== CyberPanel phpMyAdmin Access Control Rollback ==="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run this script as root"
    exit 1
fi

# Find the most recent backup
LATEST_BACKUP=$(ls -t /usr/local/CyberCP/public/phpmyadmin/index.php.backup.* 2>/dev/null | head -n1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "No backup found. Cannot rollback changes."
    echo "You may need to reinstall phpMyAdmin or restore from your own backup."
    exit 1
fi

echo "Found backup: $LATEST_BACKUP"
echo "Restoring original phpMyAdmin index.php..."

# Restore the original index.php
cp "$LATEST_BACKUP" /usr/local/CyberCP/public/phpmyadmin/index.php

# Remove the .htaccess file if it exists
if [ -f "/usr/local/CyberCP/public/phpmyadmin/.htaccess" ]; then
    echo "Removing .htaccess file..."
    rm /usr/local/CyberCP/public/phpmyadmin/.htaccess
fi

# Set proper permissions
echo "Setting permissions..."
chown lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/index.php
chmod 644 /usr/local/CyberCP/public/phpmyadmin/index.php

# Restart LiteSpeed to ensure changes take effect
echo "Restarting LiteSpeed..."
systemctl restart lscpd

echo "=== Rollback Complete ==="
echo ""
echo "phpMyAdmin access control has been reverted!"
echo "phpMyAdmin should now work as it did before the changes."
echo ""
echo "Backup file used: $LATEST_BACKUP"
