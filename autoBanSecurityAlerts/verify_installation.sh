#!/bin/bash
# Verification script for Auto Ban Security Alerts Plugin

echo "=== Auto Ban Security Alerts Plugin - Installation Verification ==="
echo ""

# Check if plugin directory exists
if [ ! -d "/home/cyberpanel-plugins/autoBanSecurityAlerts" ]; then
    echo "❌ Plugin directory not found!"
    exit 1
fi
echo "✅ Plugin directory exists"

# Check required files
REQUIRED_FILES=(
    "meta.xml"
    "models.py"
    "views.py"
    "urls.py"
    "apps.py"
    "__init__.py"
    "api_encryption.py"
    "templates/autoBanSecurityAlerts/settings.html"
    "templates/autoBanSecurityAlerts/subscription_required.html"
    "migrations/0001_initial.py"
)

for file in "${REQUIRED_FILES[@]}"; do
    if [ ! -f "/home/cyberpanel-plugins/autoBanSecurityAlerts/$file" ]; then
        echo "❌ Missing file: $file"
        exit 1
    fi
done
echo "✅ All required files present"

# Check Python syntax
echo ""
echo "Checking Python syntax..."
python3 -m py_compile /home/cyberpanel-plugins/autoBanSecurityAlerts/*.py 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Python syntax is valid"
else
    echo "❌ Python syntax errors found"
    exit 1
fi

# Check if plugin is in INSTALLED_APPS
if grep -q "autoBanSecurityAlerts" /usr/local/CyberCP/CyberCP/settings.py 2>/dev/null || grep -q "autoBanSecurityAlerts" /home/cyberpanel-repo/CyberCP/settings.py 2>/dev/null; then
    echo "✅ Plugin is in INSTALLED_APPS"
else
    echo "⚠️  Plugin not found in INSTALLED_APPS (may need to be added)"
fi

# Check if machineIP file exists
if [ -f "/etc/cyberpanel/machineIP" ]; then
    MACHINE_IP=$(cat /etc/cyberpanel/machineIP 2>/dev/null)
    echo "✅ Machine IP file exists: $MACHINE_IP"
else
    echo "⚠️  Machine IP file not found at /etc/cyberpanel/machineIP"
fi

echo ""
echo "=== Verification Complete ==="
echo ""
echo "Next steps:"
echo "1. Restart CyberPanel service: systemctl restart lscpd"
echo "2. Access plugin at: https://your-domain:8090/plugins/autoBanSecurityAlerts/settings/"
echo "3. Run migrations: cd /usr/local/CyberCP && python3 manage.py migrate autoBanSecurityAlerts"
