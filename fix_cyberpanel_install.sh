#!/bin/bash

# CyberPanel Post-Upgrade Fix Script
# This script completes the installation when the upgrade exits early due to TypeError

set -e  # Exit on error

echo "==================================="
echo "CyberPanel Installation Fix Script"
echo "==================================="
echo ""

# Check if running as root
if [[ $(id -u) != 0 ]]; then
    echo "This script must be run as root!"
    exit 1
fi

# Function to print colored output
print_status() {
    echo -e "\033[1;32m[$(date +"%Y-%m-%d %H:%M:%S")]\033[0m $1"
}

print_error() {
    echo -e "\033[1;31m[$(date +"%Y-%m-%d %H:%M:%S")] ERROR:\033[0m $1"
}

# Check if virtual environment exists
if [[ ! -f /usr/local/CyberCP/bin/activate ]]; then
    print_error "CyberPanel virtual environment not found!"
    print_status "Creating virtual environment..."
    
    # Try python3 -m venv first
    if python3 -m venv --system-site-packages /usr/local/CyberCP 2>/dev/null; then
        print_status "Virtual environment created successfully with python3 -m venv"
    else
        # Fallback to virtualenv
        virtualenv -p /usr/bin/python3 --system-site-packages /usr/local/CyberCP
    fi
fi

# Activate virtual environment
print_status "Activating CyberPanel virtual environment..."
source /usr/local/CyberCP/bin/activate

# Check if Django is already installed
if python -c "import django" 2>/dev/null; then
    print_status "Django is already installed. Checking version..."
    python -c "import django; print(f'Django version: {django.__version__}')"
else
    print_status "Installing Python requirements..."
    
    # Download requirements file
    print_status "Downloading requirements.txt..."
    if [[ -f /tmp/requirements.txt ]]; then
        rm -f /tmp/requirements.txt
    fi
    
    # Detect OS version and download appropriate requirements
    if grep -q "22.04" /etc/os-release || grep -q "VERSION_ID=\"9" /etc/os-release; then
        wget -q -O /tmp/requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.4.5/requirments.txt
    else
        wget -q -O /tmp/requirements.txt https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.4.5/requirments-old.txt
    fi
    
    # Upgrade pip first
    print_status "Upgrading pip, setuptools, and wheel..."
    pip install --upgrade pip setuptools wheel packaging
    
    # Install requirements
    print_status "Installing CyberPanel requirements (this may take a few minutes)..."
    pip install --default-timeout=3600 --ignore-installed -r /tmp/requirements.txt
fi

# Install WSGI-LSAPI if not present
if [[ ! -f /usr/local/CyberCP/bin/lswsgi ]]; then
    print_status "Installing WSGI-LSAPI..."
    
    cd /tmp
    rm -rf wsgi-lsapi-2.1*
    
    wget -q https://www.litespeedtech.com/packages/lsapi/wsgi-lsapi-2.1.tgz
    tar xf wsgi-lsapi-2.1.tgz
    cd wsgi-lsapi-2.1
    
    /usr/local/CyberCP/bin/python ./configure.py
    make
    
    cp lswsgi /usr/local/CyberCP/bin/
    print_status "WSGI-LSAPI installed successfully"
fi

# Fix permissions
print_status "Fixing permissions..."
chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib 2>/dev/null || true
chown -R cyberpanel:cyberpanel /usr/local/CyberCP/lib64 2>/dev/null || true

# Test Django installation
print_status "Testing Django installation..."
cd /usr/local/CyberCP

if python manage.py check 2>&1 | grep -q "System check identified no issues"; then
    print_status "Django is working correctly!"
else
    print_error "Django check failed. Checking for specific issues..."
    python manage.py check
fi

# Restart LSCPD
print_status "Restarting LSCPD service..."
systemctl restart lscpd

# Check service status
if systemctl is-active --quiet lscpd; then
    print_status "LSCPD service is running"
else
    print_error "LSCPD service failed to start"
    systemctl status lscpd
fi

echo ""
print_status "CyberPanel fix completed!"
echo ""
echo "You can now access CyberPanel at: https://$(hostname -I | awk '{print $1}'):8090"
echo ""

# Deactivate virtual environment
deactivate 2>/dev/null || true