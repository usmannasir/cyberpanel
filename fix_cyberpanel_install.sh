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

# lswsgi uses system Python when pythonenv.conf sets PYTHONHOME=/usr (PEP 668 may require --break-system-packages).
if [[ -f /usr/local/lscp/conf/pythonenv.conf ]] && grep -q '^PYTHONHOME=/usr' /usr/local/lscp/conf/pythonenv.conf 2>/dev/null; then
    print_status "PYTHONHOME=/usr: mirroring requirements into system Python for lswsgi..."
    py_cmd=""
    command -v python3 >/dev/null 2>&1 && py_cmd="$(command -v python3)"
    [[ -z "$py_cmd" && -x /usr/bin/python3 ]] && py_cmd=/usr/bin/python3
    RUNTIME_REQ=""
    if [[ -f /etc/cyberpanel/cyberpanel-requirments-runtime.txt ]] && grep -q 'Django==' /etc/cyberpanel/cyberpanel-requirments-runtime.txt 2>/dev/null; then
        RUNTIME_REQ="/etc/cyberpanel/cyberpanel-requirments-runtime.txt"
    elif [[ -f /tmp/requirements.txt ]] && grep -q 'Django==' /tmp/requirements.txt 2>/dev/null; then
        RUNTIME_REQ="/tmp/requirements.txt"
    elif [[ -f /usr/local/requirments.txt ]] && grep -q 'Django==' /usr/local/requirments.txt 2>/dev/null; then
        RUNTIME_REQ="/usr/local/requirments.txt"
    else
        mkdir -p /etc/cyberpanel
        if wget -q -O /etc/cyberpanel/cyberpanel-requirments-runtime.txt "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/requirments.txt" 2>/dev/null \
          && grep -q 'Django==' /etc/cyberpanel/cyberpanel-requirments-runtime.txt 2>/dev/null; then
            RUNTIME_REQ="/etc/cyberpanel/cyberpanel-requirments-runtime.txt"
        fi
    fi
    if [[ -z "$py_cmd" ]]; then
        print_error "python3 not found; cannot install system packages for lswsgi."
    elif [[ -z "$RUNTIME_REQ" ]]; then
        print_error "No requirements file for system Python; wget requirments.txt from GitHub stable failed or network down."
    else
        PIP_EXTRA=()
        if compgen -G "/usr/lib/python3.*/EXTERNALLY-MANAGED" >/dev/null 2>&1 \
          || compgen -G "/usr/lib64/python3.*/EXTERNALLY-MANAGED" >/dev/null 2>&1; then
            PIP_EXTRA+=(--break-system-packages)
        fi
        if ! "$py_cmd" -m pip --version >/dev/null 2>&1; then
            "$py_cmd" -m ensurepip --upgrade >/dev/null 2>&1 || true
        fi
        set +e
        env PIP_DISABLE_PIP_VERSION_CHECK=1 "$py_cmd" -m pip install --upgrade pip setuptools wheel packaging "${PIP_EXTRA[@]}"
        env PIP_DISABLE_PIP_VERSION_CHECK=1 "$py_cmd" -m pip install --default-timeout=3600 --ignore-installed "${PIP_EXTRA[@]}" -r "$RUNTIME_REQ"
        rt=$?
        if [[ $rt -ne 0 ]]; then
            print_status "Retrying system pip with PIP_BREAK_SYSTEM_PACKAGES=1..."
            env PIP_DISABLE_PIP_VERSION_CHECK=1 PIP_BREAK_SYSTEM_PACKAGES=1 "$py_cmd" -m pip install --default-timeout=3600 --ignore-installed --break-system-packages -r "$RUNTIME_REQ"
            rt=$?
        fi
        set -e
        if [[ $rt -ne 0 ]]; then
            print_error "System pip failed ($rt). Manual: $py_cmd -m pip install -r $RUNTIME_REQ --break-system-packages"
        elif env PYTHONHOME=/usr PYTHONPATH= "$py_cmd" -c "import django" 2>/dev/null; then
            print_status "System Python OK for lswsgi (django imports with PYTHONHOME=/usr)."
        else
            print_error "django still not importable under PYTHONHOME=/usr after system pip."
        fi
    fi
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