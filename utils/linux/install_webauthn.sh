#!/bin/bash

# WebAuthn Installation Script for CyberPanel
# This script helps install and configure WebAuthn/Passkey authentication

echo "=========================================="
echo "CyberPanel WebAuthn Installation Script"
echo "=========================================="

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "Please run as root (use sudo)"
    exit 1
fi

# Check if CyberPanel is installed
if [ ! -d "/usr/local/CyberCP" ]; then
    echo "Error: CyberPanel not found at /usr/local/CyberCP"
    echo "Please install CyberPanel first"
    exit 1
fi

echo "✓ CyberPanel installation found"

# Navigate to CyberPanel directory
cd /usr/local/CyberCP

# Check if Django is available
if ! python3 -c "import django" 2>/dev/null; then
    echo "Error: Django not found. Please ensure CyberPanel is properly installed"
    exit 1
fi

echo "✓ Django installation found"

# Run database migrations
echo "Running database migrations..."
python3 manage.py makemigrations loginSystem
if [ $? -eq 0 ]; then
    echo "✓ Database migrations created"
else
    echo "Error: Failed to create migrations"
    exit 1
fi

python3 manage.py migrate
if [ $? -eq 0 ]; then
    echo "✓ Database migrations applied"
else
    echo "Error: Failed to apply migrations"
    exit 1
fi

# Check if static files directory exists
if [ ! -d "static/loginSystem" ]; then
    echo "Creating static files directory..."
    mkdir -p static/loginSystem
fi

# Copy WebAuthn JavaScript file if it doesn't exist
if [ ! -f "static/loginSystem/webauthn.js" ]; then
    echo "WebAuthn JavaScript file not found. Please ensure webauthn.js is in static/loginSystem/"
    echo "You can copy it from the source files"
fi

# Set proper permissions
echo "Setting file permissions..."
chown -R lscpd:lscpd /usr/local/CyberCP/static/loginSystem/
chmod -R 755 /usr/local/CyberCP/static/loginSystem/

# Test the installation
echo "Testing WebAuthn installation..."
python3 -c "
import sys
sys.path.append('/usr/local/CyberCP')
try:
    from loginSystem.webauthn_models import WebAuthnCredential, WebAuthnChallenge, WebAuthnSettings
    print('✓ WebAuthn models imported successfully')
except ImportError as e:
    print(f'Error importing WebAuthn models: {e}')
    sys.exit(1)

try:
    from loginSystem.webauthn_backend import WebAuthnBackend
    backend = WebAuthnBackend()
    print('✓ WebAuthn backend initialized successfully')
except Exception as e:
    print(f'Error initializing WebAuthn backend: {e}')
    sys.exit(1)
"

if [ $? -eq 0 ]; then
    echo "✓ WebAuthn installation test passed"
else
    echo "Error: WebAuthn installation test failed"
    exit 1
fi

# Create configuration file
echo "Creating WebAuthn configuration..."
cat > /usr/local/CyberCP/webauthn_config.py << 'EOF'
# WebAuthn Configuration for CyberPanel
# Update these values according to your setup

WEBAUTHN_CONFIG = {
    'RP_ID': 'cyberpanel.local',  # Replace with your actual domain
    'RP_NAME': 'CyberPanel',
    'ORIGIN': 'https://cyberpanel.local:8090',  # Replace with your actual origin
    'CHALLENGE_TIMEOUT': 300,  # 5 minutes
    'MAX_CREDENTIALS_PER_USER': 10,
    'DEFAULT_TIMEOUT_SECONDS': 60,
}

# Instructions:
# 1. Update RP_ID to your actual domain (e.g., 'yourdomain.com')
# 2. Update ORIGIN to your actual origin (e.g., 'https://yourdomain.com:8090')
# 3. Restart CyberPanel after making changes
EOF

echo "✓ Configuration file created at /usr/local/CyberCP/webauthn_config.py"

# Restart CyberPanel services
echo "Restarting CyberPanel services..."
systemctl restart lscpd
if [ $? -eq 0 ]; then
    echo "✓ CyberPanel services restarted"
else
    echo "Warning: Failed to restart CyberPanel services. Please restart manually"
fi

echo ""
echo "=========================================="
echo "WebAuthn Installation Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update the configuration file: /usr/local/CyberCP/webauthn_config.py"
echo "2. Replace 'cyberpanel.local' with your actual domain"
echo "3. Replace 'https://cyberpanel.local:8090' with your actual origin"
echo "4. Restart CyberPanel: systemctl restart lscpd"
echo "5. Access CyberPanel and go to User Management to enable WebAuthn"
echo ""
echo "Features available:"
echo "- Passkey registration and management"
echo "- Passwordless login option"
echo "- Multiple device support"
echo "- Admin management interface"
echo ""
echo "For more information, see: /usr/local/CyberCP/to-do/WEBAUTHN_IMPLEMENTATION.md"
echo ""
