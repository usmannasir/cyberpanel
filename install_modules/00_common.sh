#!/usr/bin/env bash
# CyberPanel install – common (globals, log, banner, detect_os, fix_*). Sourced by cyberpanel.sh.

#!/bin/bash

# CyberPanel Simple Installer
# Ultra-simple version that works reliably in all terminals

set -e

# Global variables
SERVER_OS=""
OS_FAMILY=""
PACKAGE_MANAGER=""
ARCHITECTURE=""
BRANCH_NAME=""
MARIADB_VER=""
DEBUG_MODE=false
AUTO_INSTALL=false
INSTALLATION_TYPE=""
# Prefer mariadb CLI (mysql is deprecated)
MDB_CLI="mariadb"; command -v mariadb >/dev/null 2>&1 || MDB_CLI="mysql"

# Target interpreter for /usr/local/CyberCP venv (install.py reads CYBERCP_VENV_PYTHON). v2.5.5-dev prefers 3.11 on EL9+.
CYBERCP_VENV_PYTHON=""

# Resolve and export CYBERCP_VENV_PYTHON after OS packages are installed (call from install_dependencies).
ensure_cybercp_system_python() {
    CYBERCP_VENV_PYTHON=""
    local p=""
    for p in /usr/bin/python3.11 /usr/local/bin/python3.11 /usr/bin/python3.12 /usr/bin/python3.13 /usr/bin/python3.10; do
        if [[ -x "$p" ]] && "$p" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' 2>/dev/null; then
            CYBERCP_VENV_PYTHON="$p"
            export CYBERCP_VENV_PYTHON
            print_status "CyberCP venv will use Python: $CYBERCP_VENV_PYTHON"
            return 0
        fi
    done
    if command -v python3 >/dev/null 2>&1 && python3 -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' 2>/dev/null; then
        CYBERCP_VENV_PYTHON="$(command -v python3)"
        export CYBERCP_VENV_PYTHON
        print_status "CyberCP venv will use Python: $CYBERCP_VENV_PYTHON (default python3 is 3.10+)"
        return 0
    fi

    case "${SERVER_OS:-}" in
        AlmaLinux9|AlmaLinux10|CentOS9|RockyLinux9)
            if command -v dnf >/dev/null 2>&1; then
                print_status "Installing Python 3.11 packages for CyberCP venv (dnf)..."
                dnf install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || true
            fi
            ;;
        AlmaLinux8|RockyLinux8|CentOS8)
            if [[ -n "${PACKAGE_MANAGER:-}" ]] && command -v "${PACKAGE_MANAGER}" >/dev/null 2>&1; then
                print_status "Installing Python 3.11 for CyberCP venv if available (${PACKAGE_MANAGER})..."
                "${PACKAGE_MANAGER}" install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || true
            fi
            ;;
    esac

    if [[ "${OS_FAMILY:-}" = "debian" ]]; then
        print_status "Attempting apt install python3.11 for CyberCP venv..."
        DEBIAN_FRONTEND=noninteractive apt-get install -y -qq python3.11 python3.11-venv python3.11-dev 2>/dev/null || true
    fi

    for p in /usr/bin/python3.11 /usr/local/bin/python3.11 /usr/bin/python3.10; do
        if [[ -x "$p" ]] && "$p" -c 'import sys; sys.exit(0 if sys.version_info[:2] >= (3, 10) else 1)' 2>/dev/null; then
            CYBERCP_VENV_PYTHON="$p"
            export CYBERCP_VENV_PYTHON
            print_status "CyberCP venv will use Python: $CYBERCP_VENV_PYTHON"
            return 0
        fi
    done

    CYBERCP_VENV_PYTHON="$(command -v python3 2>/dev/null || echo /usr/bin/python3)"
    export CYBERCP_VENV_PYTHON
    print_status "WARNING: Python 3.10+ not found for CyberCP venv; using $CYBERCP_VENV_PYTHON (install may still work)"
}

# Logging function
log_message() {
    # Ensure log directory exists
    mkdir -p "/var/log/CyberPanel"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL] $1" | tee -a "/var/log/CyberPanel/install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL] $1"
}

# Print status
print_status() {
    local message="$1"
    echo "$message"
    log_message "$message"
}

# Function to show banner
show_banner() {
    clear
    echo ""
    echo "==============================================================================================================="
    echo "                                    CYBERPANEL COMPLETE INSTALLER"
    echo "==============================================================================================================="
    echo ""
    echo "                                    The Ultimate Web Hosting Control Panel"
    echo "                                    Powered by OpenLiteSpeed • Fast • Secure • Scalable"
    echo ""
    echo "                                    Interactive Menus • Version Selection • Advanced Options"
    echo ""
    echo "==============================================================================================================="
    echo ""
}

# Function to detect OS
detect_os() {
    # Check if we're running from a file (not via curl) and modules are available
    if [ -f "modules/os/detect.sh" ]; then
        # Load the OS detection module for enhanced support
        source "modules/os/detect.sh"
        detect_os
        return $?
    fi
    
    print_status "Detecting operating system..."
    
    # Detect architecture
    ARCHITECTURE=$(uname -m)
    case $ARCHITECTURE in
        x86_64)
            print_status "Architecture: x86_64 (Supported)"
            ;;
        aarch64|arm64)
            print_status "Architecture: $ARCHITECTURE (Limited support)"
            ;;
        *)
            print_status "Architecture: $ARCHITECTURE (Not supported)"
            return 1
            ;;
    esac
    
    # Get OS release information
    local OUTPUT=$(cat /etc/*release 2>/dev/null)
    if [ -z "$OUTPUT" ]; then
        print_status "ERROR: Cannot read OS release information"
        return 1
    fi
    
    # Detect OS
    if echo $OUTPUT | grep -q "AlmaLinux 10" ; then
        SERVER_OS="AlmaLinux10"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "Detected: AlmaLinux 10"
    elif echo $OUTPUT | grep -q "AlmaLinux 9" ; then
        SERVER_OS="AlmaLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "Detected: AlmaLinux 9"
    elif echo $OUTPUT | grep -q "AlmaLinux 8" ; then
        SERVER_OS="AlmaLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "Detected: AlmaLinux 8"
    elif echo $OUTPUT | grep -q "CentOS Linux 9" ; then
        SERVER_OS="CentOS9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "Detected: CentOS Linux 9"
    elif echo $OUTPUT | grep -q "CentOS Linux 8" ; then
        SERVER_OS="CentOS8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "Detected: CentOS Linux 8"
    elif echo $OUTPUT | grep -q "Rocky Linux 9" ; then
        SERVER_OS="RockyLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "Detected: Rocky Linux 9"
    elif echo $OUTPUT | grep -q "Rocky Linux 8" ; then
        SERVER_OS="RockyLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "Detected: Rocky Linux 8"
    elif echo $OUTPUT | grep -q "Ubuntu 24.04" ; then
        SERVER_OS="Ubuntu2404"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 24.04"
    elif echo $OUTPUT | grep -q "Ubuntu 22.04" ; then
        SERVER_OS="Ubuntu2204"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 22.04"
    elif echo $OUTPUT | grep -q "Ubuntu 20.04" ; then
        SERVER_OS="Ubuntu2004"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 20.04"
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 13" ; then
        SERVER_OS="Debian13"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Debian GNU/Linux 13"
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 12" ; then
        SERVER_OS="Debian12"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Debian GNU/Linux 12"
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 11" ; then
        SERVER_OS="Debian11"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Debian GNU/Linux 11"
    else
        print_status "ERROR: Unsupported OS detected"
        print_status "Supported OS: AlmaLinux 8/9/10, CentOS 8/9, Rocky Linux 8/9, Ubuntu 20.04/22.04/24.04, Debian 11/12/13"
        return 1
    fi
    
    return 0
}

# Function to fix static file permissions (critical for LiteSpeed)
fix_static_file_permissions() {
    echo "  🔧 Fixing static file permissions for web server access..."

    # CRITICAL: Fix ownership and permissions for all public files
    # LiteSpeed requires files to be owned by lscpd and NOT have execute permissions

    # Check if the public directory exists
    if [ -d "/usr/local/CyberCP/public/" ]; then
        echo "    • Setting ownership to lscpd:lscpd for public directory..."
        chown -R lscpd:lscpd /usr/local/CyberCP/public/ 2>/dev/null || true

        echo "    • Setting directory permissions to 755..."
        find /usr/local/CyberCP/public/ -type d -exec chmod 755 {} \; 2>/dev/null || true

        echo "    • Setting file permissions to 644 (removing execute bit)..."
        find /usr/local/CyberCP/public/ -type f -exec chmod 644 {} \; 2>/dev/null || true

        # Ensure parent directories have correct permissions
        chmod 755 /usr/local/CyberCP/public/ 2>/dev/null || true
        chmod 755 /usr/local/CyberCP/public/static/ 2>/dev/null || true

        echo "    ✅ Static file permissions fixed successfully"
    else
        echo "    ⚠️  Warning: /usr/local/CyberCP/public/ directory not found"
    fi

    # Also check the alternative path
    if [ -d "/usr/local/CyberPanel/public/" ]; then
        echo "    • Fixing permissions for /usr/local/CyberPanel/public/..."
        chown -R lscpd:lscpd /usr/local/CyberPanel/public/ 2>/dev/null || true
        find /usr/local/CyberPanel/public/ -type d -exec chmod 755 {} \; 2>/dev/null || true
        find /usr/local/CyberPanel/public/ -type f -exec chmod 644 {} \; 2>/dev/null || true
    fi
}

# Function to fix post-installation issues
fix_post_install_issues() {
    echo "  🔧 Fixing database connection issues..."
    
    # Wait for services to start
    sleep 10
    
    # Start and enable MariaDB if not running
    if ! systemctl is-active --quiet mariadb; then
        echo "    Starting MariaDB service..."
        systemctl start mariadb
        systemctl enable mariadb
        sleep 5
    fi
    
    # Start and enable LiteSpeed if not running
    if ! systemctl is-active --quiet lsws; then
        echo "    Starting LiteSpeed service..."
        systemctl start lsws
        systemctl enable lsws
        sleep 5
    fi
    
    # Fix database user permissions
    echo "    Fixing database user permissions..."
    
    # Wait for MariaDB to be ready
    local retry_count=0
    while [ $retry_count -lt 10 ]; do
        if $MDB_CLI -e "SELECT 1;" >/dev/null 2>&1; then
            break
        fi
        echo "      Waiting for MariaDB to be ready... ($((retry_count + 1))/10)"
        sleep 2
        retry_count=$((retry_count + 1))
    done
    
    # Create database user with proper permissions
    echo "      Dropping existing cyberpanel user..."
    $MDB_CLI -e "DROP USER IF EXISTS 'cyberpanel'@'localhost';" 2>/dev/null || true
    $MDB_CLI -e "DROP USER IF EXISTS 'cyberpanel'@'%';" 2>/dev/null || true
    
    echo "      Creating cyberpanel user with correct password..."
    $MDB_CLI -e "CREATE USER 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
    $MDB_CLI -e "CREATE USER 'cyberpanel'@'%' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
    
    echo "      Granting privileges..."
    $MDB_CLI -e "GRANT ALL PRIVILEGES ON *.* TO 'cyberpanel'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
    $MDB_CLI -e "GRANT ALL PRIVILEGES ON *.* TO 'cyberpanel'@'%' WITH GRANT OPTION;" 2>/dev/null || true
    $MDB_CLI -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
    # Verify the user was created correctly
    echo "      Verifying database user..."
    if $MDB_CLI -u cyberpanel -pcyberpanel -e "SELECT 1;" >/dev/null 2>&1; then
        echo "      ✅ Database user verification successful"
    else
        echo "      ⚠️  Database user verification failed, trying alternative approach..."
        # Alternative: use root to create the user
        $MDB_CLI -e "CREATE OR REPLACE USER 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
        $MDB_CLI -e "GRANT ALL PRIVILEGES ON *.* TO 'cyberpanel'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
        $MDB_CLI -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    fi
    
    # Create CyberPanel database if it doesn't exist
    $MDB_CLI -e "CREATE DATABASE IF NOT EXISTS cyberpanel;" 2>/dev/null || true
    $MDB_CLI -e "GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost';" 2>/dev/null || true
    $MDB_CLI -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
    # Get or set unified password for both CyberPanel and OpenLiteSpeed
    local unified_password=""
    if [ -f "/root/.cyberpanel_password" ]; then
        unified_password=$(cat /root/.cyberpanel_password 2>/dev/null)
    fi

    # If no password was captured from installation, use default
    if [ -z "$unified_password" ]; then
        unified_password="1234567"
        # Save password to file for later retrieval
        echo "$unified_password" > /root/.cyberpanel_password 2>/dev/null || true
        chmod 600 /root/.cyberpanel_password 2>/dev/null || true
    fi

    echo "    Setting unified password for CyberPanel and OpenLiteSpeed..."
    echo "    Password: $unified_password"
    
    # First, ensure the cyberpanel user exists and has correct password
    $MDB_CLI -e "ALTER USER 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
    $MDB_CLI -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
    # Wait a moment for the database to be ready
    sleep 2
    
    # Reset CyberPanel admin password
    echo "      Setting CyberPanel admin password..."
    /usr/local/CyberCP/bin/python3 /usr/local/CyberCP/plogical/adminPass.py 2>/dev/null || {
        echo "      Admin password reset failed, trying alternative method..."
        # Alternative method: directly update the database
        $MDB_CLI -u cyberpanel -pcyberpanel cyberpanel -e "UPDATE Administrator SET password = '$unified_password' WHERE id = 1;" 2>/dev/null || true
    }
    
    # Set OpenLiteSpeed admin password
    echo "      Setting OpenLiteSpeed admin password..."
    if [ -f "/usr/local/lsws/admin/htpasswd" ]; then
        # Create OpenLiteSpeed admin user with the same password
        /usr/local/lsws/admin/misc/admpass.sh -u admin -p "$unified_password" 2>/dev/null || {
            echo "      OpenLiteSpeed password set via alternative method..."
            # Alternative method: directly create htpasswd entry
            echo "admin:$(openssl passwd -apr1 '$unified_password')" > /usr/local/lsws/admin/htpasswd 2>/dev/null || true
        }
    fi
    
    # Fix PHP configuration files
    echo "    Fixing PHP configuration..."
    
    # Find the reference PHP version (usually lsphp82)
    local reference_php=""
    for php_version in lsphp82 lsphp81 lsphp80 lsphp84 lsphp83 lsphp74 lsphp73 lsphp72; do
        if [ -d "/usr/local/lsws/$php_version" ] && [ -f "/usr/local/lsws/$php_version/etc/php.ini" ]; then
            reference_php="$php_version"
            echo "      Using $php_version as reference for PHP configuration"
            break
        fi
    done
    
    if [ -n "$reference_php" ]; then
        for php_version in lsphp72 lsphp73 lsphp74 lsphp80 lsphp81 lsphp82 lsphp83 lsphp84; do
            if [ -d "/usr/local/lsws/$php_version" ]; then
                # Create missing php.ini if it doesn't exist
                if [ ! -f "/usr/local/lsws/$php_version/etc/php.ini" ]; then
                    echo "      Creating missing php.ini for $php_version..."
                    cp "/usr/local/lsws/$reference_php/etc/php.ini" "/usr/local/lsws/$php_version/etc/php.ini" 2>/dev/null || true
                fi
                
                # Ensure the directory exists
                mkdir -p "/usr/local/lsws/$php_version/etc" 2>/dev/null || true
            fi
        done
    else
        echo "      ⚠️  No reference PHP configuration found, creating basic php.ini files..."
        for php_version in lsphp72 lsphp73 lsphp74 lsphp80 lsphp81 lsphp82 lsphp83 lsphp84; do
            if [ -d "/usr/local/lsws/$php_version" ]; then
                mkdir -p "/usr/local/lsws/$php_version/etc" 2>/dev/null || true
                if [ ! -f "/usr/local/lsws/$php_version/etc/php.ini" ]; then
                    echo "      Creating basic php.ini for $php_version..."
                    cat > "/usr/local/lsws/$php_version/etc/php.ini" << 'EOF'
[PHP]
engine = On
short_open_tag = Off
precision = 14
output_buffering = 4096
zlib.output_compression = Off
implicit_flush = Off
unserialize_callback_func =
serialize_precision = -1
disable_functions =
disable_classes =
zend.enable_gc = On
expose_php = Off
max_execution_time = 30
max_input_time = 60
memory_limit = 128M
error_reporting = E_ALL & ~E_DEPRECATED & ~E_STRICT
display_errors = Off
display_startup_errors = Off
log_errors = On
log_errors_max_len = 1024
ignore_repeated_errors = Off
ignore_repeated_source = Off
report_memleaks = On
variables_order = "GPCS"
request_order = "GP"
register_argc_argv = Off
auto_globals_jit = On
post_max_size = 8M
auto_prepend_file =
auto_append_file =
default_mimetype = "text/html"
default_charset = "UTF-8"
file_uploads = On
upload_max_filesize = 2M
max_file_uploads = 20
allow_url_fopen = On
allow_url_include = Off
default_socket_timeout = 60
EOF
                fi
            fi
        done
    fi
    
    # Restart services
    echo "    Restarting services..."
    systemctl restart mariadb
    systemctl restart lsws
    
    # Wait for services to stabilize
    sleep 10
    
    # Verify services are running
    if systemctl is-active --quiet mariadb && systemctl is-active --quiet lsws; then
        echo "  ✅ Post-installation fixes completed successfully"
        
        # Run final verification
        verify_installation
    else
        echo "  ⚠️  Some services may need manual attention"
        echo "  🔧 Attempting additional fixes..."
        
        # Additional service fixes
        systemctl daemon-reload
        systemctl reset-failed mariadb lsws
        systemctl start mariadb lsws
        
        sleep 5
        verify_installation
    fi
}

# Function to verify installation
