#!/bin/bash

# Fail2ban Plugin Uninstall Script
# This script will completely remove the fail2ban plugin from CyberPanel

echo "🔒 Fail2ban Plugin Uninstall Script"
echo "=================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get the plugin directory
PLUGIN_DIR="/home/cyberpanel/plugins/fail2ban_plugin"

echo "📁 Plugin directory: $PLUGIN_DIR"

# Check if plugin exists
if [ ! -d "$PLUGIN_DIR" ]; then
    echo "❌ Plugin directory not found: $PLUGIN_DIR"
    exit 1
fi

echo "🔄 Stopping any running fail2ban processes..."

# Stop fail2ban service
systemctl stop fail2ban 2>/dev/null || echo "⚠️  fail2ban service not running"

# Kill any remaining fail2ban processes
pkill -f fail2ban 2>/dev/null || echo "⚠️  No fail2ban processes found"

echo "🗑️  Removing plugin files..."

# Remove the plugin directory
rm -rf "$PLUGIN_DIR"

# Remove any backup directories
rm -rf /home/cyberpanel/plugins/fail2ban_plugin.backup.*

echo "🔄 Restarting web server..."

# Restart LiteSpeed
systemctl restart lshttpd

echo "✅ Plugin uninstalled successfully!"
echo ""
echo "📋 Summary:"
echo "  - Plugin files removed"
echo "  - Backup directories cleaned up"
echo "  - Web server restarted"
echo ""
echo "🎯 You can now reinstall the plugin from CyberPanel's plugin manager"
