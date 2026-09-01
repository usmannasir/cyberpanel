#!/bin/bash

# Fail2ban Plugin Reinstall Script
# This script will properly reinstall the fail2ban plugin

echo "🔒 Fail2ban Plugin Reinstall Script"
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
    echo "Please run the uninstall script first, then reinstall from CyberPanel"
    exit 1
fi

echo "🔄 Setting proper permissions..."

# Set proper ownership
chown -R cyberpanel:cyberpanel "$PLUGIN_DIR"

# Set proper permissions
find "$PLUGIN_DIR" -type f -exec chmod 644 {} \;
find "$PLUGIN_DIR" -type d -exec chmod 755 {} \;
chmod +x "$PLUGIN_DIR"/*.sh 2>/dev/null || true

echo "🔧 Installing fail2ban if not present..."

# Install fail2ban if not present
if ! command -v fail2ban-client &> /dev/null; then
    echo "📦 Installing fail2ban..."
    dnf install -y fail2ban
    systemctl enable fail2ban
    systemctl start fail2ban
else
    echo "✅ fail2ban is already installed"
fi

echo "🔄 Restarting services..."

# Restart fail2ban
systemctl restart fail2ban

# Restart LiteSpeed
systemctl restart lshttpd

echo "🧪 Testing plugin..."

# Test the plugin endpoints
python3 /home/test-plugin-fix.py

echo "✅ Plugin reinstall completed!"
echo ""
echo "📋 Summary:"
echo "  - Plugin permissions set correctly"
echo "  - fail2ban service installed/restarted"
echo "  - Web server restarted"
echo "  - Plugin tested"
echo ""
echo "🎯 You can now access the plugin at: https://207.180.193.210:2087/fail2ban_plugin/"
