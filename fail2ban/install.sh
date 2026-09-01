#!/bin/bash
# Fail2ban Security Manager - Installation Script
# Portable deployment script for any CyberPanel installation

set -e  # Exit on error

echo "============================================================"
echo "  Fail2ban Security Manager - Installation Script"
echo "============================================================"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo -e "${RED}❌ Error: This script must be run as root${NC}"
    exit 1
fi

# Check if CyberPanel is installed
if [ ! -d "/usr/local/CyberCP" ]; then
    echo -e "${RED}❌ Error: CyberPanel not found at /usr/local/CyberCP${NC}"
    echo "   Please install CyberPanel first."
    exit 1
fi

echo -e "${GREEN}✅ CyberPanel installation detected${NC}"
echo ""

# Get script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLUGIN_SOURCE="$SCRIPT_DIR"

echo "Installation steps:"
echo "1. Copy plugin files to CyberPanel directories"
echo "2. Update security middleware configuration"
echo "3. Set proper permissions"
echo "4. Restart LiteSpeed web server"
echo ""
read -p "Continue with installation? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Installation cancelled."
    exit 0
fi

echo ""
echo "Step 1: Copying plugin files..."
echo "----------------------------------------"

# Create plugin directories if they don't exist
mkdir -p /home/cyberpanel/plugins/fail2ban
mkdir -p /usr/local/CyberCP/fail2ban_plugin
mkdir -p /usr/local/CyberCP/pluginHolder/fail2ban_plugin

# Copy files to main Django app location
echo -n "Copying to /usr/local/CyberCP/fail2ban_plugin/... "
cp -r "$PLUGIN_SOURCE"/* /usr/local/CyberCP/fail2ban_plugin/ 2>/dev/null || true
echo -e "${GREEN}✅${NC}"

# Copy files to pluginHolder location
echo -n "Copying to /usr/local/CyberCP/pluginHolder/fail2ban_plugin/... "
cp -r "$PLUGIN_SOURCE"/* /usr/local/CyberCP/pluginHolder/fail2ban_plugin/ 2>/dev/null || true
echo -e "${GREEN}✅${NC}"

# Copy files to development location
echo -n "Copying to /home/cyberpanel/plugins/fail2ban/... "
cp -r "$PLUGIN_SOURCE"/* /home/cyberpanel/plugins/fail2ban/ 2>/dev/null || true
echo -e "${GREEN}✅${NC}"

echo ""
echo "Step 2: Updating security middleware..."
echo "----------------------------------------"

MIDDLEWARE_FILE="/usr/local/CyberCP/CyberCP/secMiddleware.py"

# Check if middleware file exists
if [ ! -f "$MIDDLEWARE_FILE" ]; then
    echo -e "${RED}❌ Error: secMiddleware.py not found${NC}"
    exit 1
fi

# Check if plugin exception already exists
if grep -q "pathActual.startswith('/plugins/')" "$MIDDLEWARE_FILE"; then
    echo -e "${YELLOW}⚠️  Plugin exception already exists in secMiddleware.py${NC}"
else
    # Backup middleware file
    cp "$MIDDLEWARE_FILE" "$MIDDLEWARE_FILE.backup.$(date +%Y%m%d%H%M%S)"
    echo -e "${GREEN}✅ Backed up secMiddleware.py${NC}"
    
    # Add plugin exception
    # Find the line with the if condition and add our exception
    sed -i '/if pathActual == "\/verifyLogin" or/s/$/ or pathActual.startswith("\/plugins\/")/' "$MIDDLEWARE_FILE"
    
    if grep -q "pathActual.startswith('/plugins/')" "$MIDDLEWARE_FILE"; then
        echo -e "${GREEN}✅ Added plugin exception to secMiddleware.py${NC}"
    else
        echo -e "${YELLOW}⚠️  Could not automatically add plugin exception${NC}"
        echo -e "${YELLOW}   Please manually add this to secMiddleware.py:${NC}"
        echo -e "${YELLOW}   or pathActual.startswith('/plugins/')${NC}"
    fi
fi

echo ""
echo "Step 3: Setting permissions..."
echo "----------------------------------------"

# Set ownership for development location
echo -n "Setting permissions for /home/cyberpanel/plugins/fail2ban/... "
chown -R cyberpanel:cyberpanel /home/cyberpanel/plugins/fail2ban/
chmod -R 755 /home/cyberpanel/plugins/fail2ban/
echo -e "${GREEN}✅${NC}"

# Set ownership for Django app location
echo -n "Setting permissions for /usr/local/CyberCP/fail2ban_plugin/... "
chown -R root:root /usr/local/CyberCP/fail2ban_plugin/
chmod -R 755 /usr/local/CyberCP/fail2ban_plugin/
echo -e "${GREEN}✅${NC}"

# Set ownership for pluginHolder location
echo -n "Setting permissions for /usr/local/CyberCP/pluginHolder/fail2ban_plugin/... "
chown -R root:root /usr/local/CyberCP/pluginHolder/fail2ban_plugin/
chmod -R 755 /usr/local/CyberCP/pluginHolder/fail2ban_plugin/
echo -e "${GREEN}✅${NC}"

echo ""
echo "Step 4: Restarting LiteSpeed..."
echo "----------------------------------------"

# Check which service is running
if systemctl is-active --quiet lshttpd; then
    echo -n "Restarting lshttpd... "
    systemctl restart lshttpd
    echo -e "${GREEN}✅${NC}"
elif systemctl is-active --quiet lsws; then
    echo -n "Restarting lsws... "
    systemctl restart lsws
    echo -e "${GREEN}✅${NC}"
else
    echo -e "${YELLOW}⚠️  LiteSpeed service not found${NC}"
    echo "   Please restart your web server manually."
fi

echo ""
echo "============================================================"
echo -e "${GREEN}✅ Installation Complete!${NC}"
echo "============================================================"
echo ""
echo "Next steps:"
echo "1. Navigate to: https://YOUR_SERVER_IP:2087/"
echo "2. Login to CyberPanel"
echo "3. Go to: Plugins"
echo "4. Find: Fail2ban Security Manager"
echo "5. Click: Enable"
echo "6. Click: Settings (to access the dashboard)"
echo ""
echo "Plugin URLs:"
echo "  Dashboard:  https://YOUR_SERVER_IP:2087/plugins/fail2ban/"
echo "  Settings:   https://YOUR_SERVER_IP:2087/plugins/fail2ban/settings/"
echo "  Changelog:  https://YOUR_SERVER_IP:2087/plugins/fail2ban/changelog/"
echo ""
echo "For verification, run:"
echo "  cd /usr/local/CyberCP && python3 -c 'import os, django; os.environ.setdefault(\"DJANGO_SETTINGS_MODULE\", \"CyberCP.settings\"); django.setup(); from pluginHolder.fail2ban_plugin.views.core import dashboard; print(\"✅ Plugin loaded successfully\")'"
echo ""
echo "============================================================"


# --- Fail2ban SQLite hardening (prevents database disk image is malformed) ---
if [ -x /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh ]; then
  /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh install-hardening || true
elif [ -f "$(dirname "$0")/../../CyberCP/scripts/security/fail2ban-db-maintain.sh" ]; then
  bash "$(dirname "$0")/../../CyberCP/scripts/security/fail2ban-db-maintain.sh" install-hardening || true
fi
# Also copy maintain script into CyberCP scripts if this plugin ships a copy
if [ -f "$(dirname "$0")/scripts/fail2ban-db-maintain.sh" ]; then
  mkdir -p /usr/local/CyberCP/scripts/security
  cp -f "$(dirname "$0")/scripts/fail2ban-db-maintain.sh" /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh
  chmod 755 /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh
  /usr/local/CyberCP/scripts/security/fail2ban-db-maintain.sh install-hardening || true
fi
