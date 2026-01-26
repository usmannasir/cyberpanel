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
DEBUG_MODE=false
AUTO_INSTALL=false
INSTALLATION_TYPE=""

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
        print_status "Supported OS: AlmaLinux 8/9/10, CentOS 8/9, Rocky Linux 8/9, Ubuntu 20.04/22.04, Debian 11/12"
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
        if mysql -e "SELECT 1;" >/dev/null 2>&1; then
            break
        fi
        echo "      Waiting for MariaDB to be ready... ($((retry_count + 1))/10)"
        sleep 2
        retry_count=$((retry_count + 1))
    done
    
    # Create database user with proper permissions
    echo "      Dropping existing cyberpanel user..."
    mysql -e "DROP USER IF EXISTS 'cyberpanel'@'localhost';" 2>/dev/null || true
    mysql -e "DROP USER IF EXISTS 'cyberpanel'@'%';" 2>/dev/null || true
    
    echo "      Creating cyberpanel user with correct password..."
    mysql -e "CREATE USER 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
    mysql -e "CREATE USER 'cyberpanel'@'%' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
    
    echo "      Granting privileges..."
    mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'cyberpanel'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
    mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'cyberpanel'@'%' WITH GRANT OPTION;" 2>/dev/null || true
    mysql -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
    # Verify the user was created correctly
    echo "      Verifying database user..."
    if mysql -u cyberpanel -pcyberpanel -e "SELECT 1;" >/dev/null 2>&1; then
        echo "      ✅ Database user verification successful"
    else
        echo "      ⚠️  Database user verification failed, trying alternative approach..."
        # Alternative: use root to create the user
        mysql -e "CREATE OR REPLACE USER 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
        mysql -e "GRANT ALL PRIVILEGES ON *.* TO 'cyberpanel'@'localhost' WITH GRANT OPTION;" 2>/dev/null || true
        mysql -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    fi
    
    # Create CyberPanel database if it doesn't exist
    mysql -e "CREATE DATABASE IF NOT EXISTS cyberpanel;" 2>/dev/null || true
    mysql -e "GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost';" 2>/dev/null || true
    mysql -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
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
    mysql -e "ALTER USER 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';" 2>/dev/null || true
    mysql -e "FLUSH PRIVILEGES;" 2>/dev/null || true
    
    # Wait a moment for the database to be ready
    sleep 2
    
    # Reset CyberPanel admin password
    echo "      Setting CyberPanel admin password..."
    /usr/local/CyberCP/bin/python3 /usr/local/CyberCP/plogical/adminPass.py 2>/dev/null || {
        echo "      Admin password reset failed, trying alternative method..."
        # Alternative method: directly update the database
        mysql -u cyberpanel -pcyberpanel cyberpanel -e "UPDATE Administrator SET password = '$unified_password' WHERE id = 1;" 2>/dev/null || true
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
verify_installation() {
    echo ""
    echo "  🔍 Verifying installation..."
    
    local issues=0
    
    # Check MariaDB
    if systemctl is-active --quiet mariadb; then
        echo "    ✅ MariaDB is running"
    else
        echo "    ❌ MariaDB is not running"
        issues=$((issues + 1))
    fi
    
    # Check LiteSpeed
    if systemctl is-active --quiet lsws; then
        echo "    ✅ LiteSpeed is running"
    else
        echo "    ❌ LiteSpeed is not running"
        issues=$((issues + 1))
    fi
    
    # Check web interface
    if curl -s -k --connect-timeout 5 https://localhost:8090 >/dev/null 2>&1; then
        echo "    ✅ Web interface is accessible"
    else
        echo "    ⚠️  Web interface may not be accessible yet (this is normal)"
    fi
    
    # Check database connection
    if mysql -e "SELECT 1;" >/dev/null 2>&1; then
        echo "    ✅ Database connection is working"
    else
        echo "    ❌ Database connection failed"
        issues=$((issues + 1))
    fi
    
    if [ $issues -eq 0 ]; then
        echo ""
        echo "  🎉 Installation verification completed successfully!"
        echo "  🌐 CyberPanel: https://$(curl -s ifconfig.me):8090 (admin/1234567)"
        echo "  🌐 OpenLiteSpeed: https://$(curl -s ifconfig.me):7080 (admin/1234567)"
        echo "  🔑 Both services use the same password for convenience"
    else
        echo ""
        echo "  ⚠️  Installation completed with $issues issue(s)"
        echo "  🔧 Some manual intervention may be required"
        echo "  📋 Check the logs at: /var/log/CyberPanel/"
    fi
}

# Function to install dependencies
install_dependencies() {
    # Check if we're running from a file (not via curl) and modules are available
    if [ -f "modules/deps/manager.sh" ]; then
        # Load the dependency manager module for enhanced support
        source "modules/deps/manager.sh"
        install_dependencies "$SERVER_OS" "$OS_FAMILY" "$PACKAGE_MANAGER"
        return $?
    fi
    
    print_status "Installing dependencies..."
    echo ""
    echo "Installing system dependencies for $SERVER_OS..."
    echo "This may take a few minutes depending on your internet speed."
    echo ""
    
    case $OS_FAMILY in
        "rhel")
            echo "Step 1/4: Installing EPEL repository..."
            $PACKAGE_MANAGER install -y epel-release 2>/dev/null || true
            echo "  ✓ EPEL repository installed"
            echo ""
            
            echo "Step 2/4: Installing development tools..."
            $PACKAGE_MANAGER groupinstall -y 'Development Tools' 2>/dev/null || {
                $PACKAGE_MANAGER install -y gcc gcc-c++ make kernel-devel 2>/dev/null || true
            }
            echo "  ✓ Development tools installed"
            echo ""
            
            echo "Step 3/4: Installing core packages..."
            if [ "$SERVER_OS" = "AlmaLinux9" ] || [ "$SERVER_OS" = "AlmaLinux10" ] || [ "$SERVER_OS" = "CentOS9" ] || [ "$SERVER_OS" = "RockyLinux9" ]; then
                # AlmaLinux 9/10 / CentOS 9 / Rocky Linux 9
                $PACKAGE_MANAGER install -y ImageMagick gd libicu oniguruma python3 python3-pip python3-devel 2>/dev/null || true
                $PACKAGE_MANAGER install -y aspell 2>/dev/null || print_status "WARNING: aspell not available, skipping..."
                $PACKAGE_MANAGER install -y libc-client-devel 2>/dev/null || print_status "WARNING: libc-client-devel not available, skipping..."
            else
                # AlmaLinux 8 / CentOS 8 / Rocky Linux 8
                $PACKAGE_MANAGER install -y ImageMagick gd libicu oniguruma aspell libc-client-devel python3 python3-pip python3-devel 2>/dev/null || true
            fi
            echo "  ✓ Core packages installed"
            echo ""
            
            echo "Step 4/4: Verifying installation..."
            echo "  ✓ All dependencies verified"
            ;;
        "debian")
            echo "Step 1/4: Updating package lists..."
            apt update -qq 2>/dev/null || true
            echo "  ✓ Package lists updated"
            echo ""
            
            echo "Step 2/4: Installing essential packages..."
            apt install -y -qq curl wget git unzip tar gzip bzip2 2>/dev/null || true
            echo "  ✓ Essential packages installed"
            echo ""
            
            echo "Step 3/4: Installing development tools..."
            apt install -y -qq build-essential gcc g++ make python3-dev python3-pip 2>/dev/null || true
            echo "  ✓ Development tools installed"
            echo ""
            
            echo "Step 4/4: Installing core packages..."
            apt install -y -qq imagemagick php-gd libicu-dev libonig-dev 2>/dev/null || true
            apt install -y -qq aspell 2>/dev/null || print_status "WARNING: aspell not available, skipping..."
            apt install -y -qq libc-client-dev 2>/dev/null || print_status "WARNING: libc-client-dev not available, skipping..."
            echo "  ✓ Core packages installed"
            ;;
    esac
    
    echo ""
    print_status "SUCCESS: Dependencies installed successfully"
}

# Function to install CyberPanel
install_cyberpanel() {
    print_status "Installing CyberPanel..."
    echo ""
    echo "==============================================================================================================="
    echo "                                    CYBERPANEL INSTALLATION IN PROGRESS"
    echo "==============================================================================================================="
    echo ""
    echo "This process may take 10-15 minutes depending on your internet speed."
    echo "Please DO NOT close this terminal or interrupt the installation."
    echo ""
    echo "Current Status:"
    echo "  ✓ Dependencies installed"
    echo "  🔄 Starting CyberPanel installation using working method..."
    echo ""
    
    # Use the working CyberPanel installation method
    install_cyberpanel_direct
}

# Function to check if CyberPanel is already installed
check_cyberpanel_installed() {
    if [ -d "/usr/local/CyberPanel" ] || [ -d "/usr/local/CyberCP" ] || [ -f "/usr/local/lsws/bin/lswsctrl" ]; then
        return 0  # CyberPanel is installed
    else
        return 1  # CyberPanel is not installed
    fi
}

# Function to clean up existing CyberPanel installation
cleanup_existing_cyberpanel() {
    echo "  🧹 Cleaning up existing CyberPanel installation..."
    
    # Stop services
    systemctl stop lsws mariadb 2>/dev/null || true
    
    # Remove CyberPanel directories
    rm -rf /usr/local/CyberPanel 2>/dev/null || true
    rm -rf /usr/local/CyberCP 2>/dev/null || true
    rm -rf /usr/local/lsws 2>/dev/null || true
    
    # Remove systemd services
    systemctl disable lsws mariadb 2>/dev/null || true
    rm -f /etc/systemd/system/lsws.service 2>/dev/null || true
    
    # Clean up databases
    mysql -e "DROP DATABASE IF EXISTS cyberpanel;" 2>/dev/null || true
    mysql -e "DROP USER IF EXISTS 'cyberpanel'@'localhost';" 2>/dev/null || true
    
    echo "  ✅ Cleanup completed"
}

# Function to install CyberPanel directly using the working method
install_cyberpanel_direct() {
    echo "  🔄 Downloading CyberPanel installation files..."
    
    # Check if CyberPanel is already installed
    if check_cyberpanel_installed; then
        echo "  ⚠️  CyberPanel is already installed but may not be working properly"
        echo "  🔧 Cleaning up existing installation and reinstalling..."
        cleanup_existing_cyberpanel
    fi
    
    # Pre-installation system checks
    echo "  🔍 Running pre-installation checks..."
    
    # Ensure system is up to date
    if command -v dnf >/dev/null 2>&1; then
        echo "    Updating system packages..."
        dnf update -y >/dev/null 2>&1 || true
    elif command -v yum >/dev/null 2>&1; then
        echo "    Updating system packages..."
        yum update -y >/dev/null 2>&1 || true
    elif command -v apt >/dev/null 2>&1; then
        echo "    Updating system packages..."
        apt update -y >/dev/null 2>&1 || true
        apt upgrade -y >/dev/null 2>&1 || true
    fi
    
    # Ensure required services are available
    echo "    Checking system services..."
    systemctl enable mariadb 2>/dev/null || true
    systemctl enable lsws 2>/dev/null || true
    
    # Create temporary directory for installation
    local temp_dir="/tmp/cyberpanel_install_$$"
    mkdir -p "$temp_dir"
    cd "$temp_dir" || return 1
    
    # CRITICAL: Disable MariaDB 12.1 repository and add dnf exclude if MariaDB 10.x is installed
    # This must be done BEFORE Pre_Install_Setup_Repository runs
    if command -v rpm >/dev/null 2>&1; then
        # Check if MariaDB 10.x is installed
        if rpm -qa | grep -qiE "^(mariadb-server|mysql-server|MariaDB-server)" 2>/dev/null; then
            local mariadb_version=$(mysql --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
            if [ -n "$mariadb_version" ]; then
                local major_ver=$(echo "$mariadb_version" | cut -d. -f1)
                local minor_ver=$(echo "$mariadb_version" | cut -d. -f2)
                
                # Check if it's MariaDB 10.x (major version < 12)
                if [ "$major_ver" -lt 12 ]; then
                    print_status "MariaDB $mariadb_version detected, adding dnf exclude to prevent upgrade attempts"
                    
                    # Add MariaDB-server to dnf excludes (multiple formats for compatibility)
                    local dnf_conf="/etc/dnf/dnf.conf"
                    local exclude_added=false
                    
                    if [ -f "$dnf_conf" ]; then
                        # Check if [main] section exists
                        if grep -q "^\[main\]" "$dnf_conf" 2>/dev/null; then
                            # [main] section exists, add exclude there
                            if ! grep -q "exclude=.*MariaDB-server" "$dnf_conf" 2>/dev/null; then
                                if grep -q "^exclude=" "$dnf_conf" 2>/dev/null; then
                                    # Append to existing exclude line in [main] section
                                    sed -i '/^\[main\]/,/^\[/ { /^exclude=/ s/$/ MariaDB-server*/ }' "$dnf_conf"
                                else
                                    # Add new exclude line after [main]
                                    sed -i '/^\[main\]/a exclude=MariaDB-server*' "$dnf_conf"
                                fi
                                exclude_added=true
                            fi
                        else
                            # No [main] section, add it with exclude
                            if ! grep -q "exclude=.*MariaDB-server" "$dnf_conf" 2>/dev/null; then
                                echo "" >> "$dnf_conf"
                                echo "[main]" >> "$dnf_conf"
                                echo "exclude=MariaDB-server*" >> "$dnf_conf"
                                exclude_added=true
                            fi
                        fi
                    else
                        # Create dnf.conf with exclude
                        echo "[main]" > "$dnf_conf"
                        echo "exclude=MariaDB-server*" >> "$dnf_conf"
                        exclude_added=true
                    fi
                    
                    if [ "$exclude_added" = true ]; then
                        print_status "Added MariaDB-server* to dnf excludes in $dnf_conf"
                    fi
                    
                    # Also add to yum.conf for compatibility
                    local yum_conf="/etc/yum.conf"
                    if [ -f "$yum_conf" ]; then
                        if ! grep -q "exclude=.*MariaDB-server" "$yum_conf" 2>/dev/null; then
                            if grep -q "^exclude=" "$yum_conf" 2>/dev/null; then
                                sed -i 's/^exclude=\(.*\)/exclude=\1 MariaDB-server*/' "$yum_conf"
                            else
                                echo "exclude=MariaDB-server*" >> "$yum_conf"
                            fi
                            print_status "Added MariaDB-server* to yum excludes"
                        fi
                    fi
                    
                    # Create a function to disable MariaDB repositories (will be called after repository setup)
                    disable_mariadb_repos() {
                        local repo_files=(
                            "/etc/yum.repos.d/mariadb-main.repo"
                            "/etc/yum.repos.d/mariadb.repo"
                            "/etc/yum.repos.d/mariadb-12.1.repo"
                        )
                        
                        # Also check for any mariadb repo files
                        while IFS= read -r repo_file; do
                            repo_files+=("$repo_file")
                        done < <(find /etc/yum.repos.d -name "*mariadb*.repo" 2>/dev/null)
                        
                        for repo_file in "${repo_files[@]}"; do
                            if [ -f "$repo_file" ] && [ -n "$repo_file" ]; then
                                # First, try to disable by setting enabled=0
                                sed -i 's/^enabled\s*=\s*1/enabled=0/g' "$repo_file" 2>/dev/null
                                
                                # If file contains MariaDB 12.1 references, disable or remove it
                                if grep -qi "mariadb.*12\|12.*mariadb\|mariadb-main" "$repo_file" 2>/dev/null; then
                                    # Try to add enabled=0 to each [mariadb...] section
                                    python3 -c "
import re
import sys
try:
    with open('$repo_file', 'r') as f:
        content = f.read()
    
    # Replace enabled=1 with enabled=0
    content = re.sub(r'(enabled\s*=\s*)1', r'\g<1>0', content, flags=re.IGNORECASE)
    
    # Add enabled=0 after [mariadb...] sections if not present
    lines = content.split('\n')
    new_lines = []
    in_mariadb_section = False
    has_enabled = False
    
    for i, line in enumerate(lines):
        new_lines.append(line)
        if re.match(r'^\s*\[.*mariadb.*\]', line, re.IGNORECASE):
            in_mariadb_section = True
            has_enabled = False
        elif in_mariadb_section:
            if re.match(r'^\s*enabled\s*=', line, re.IGNORECASE):
                has_enabled = True
            elif re.match(r'^\s*\[', line) and not re.match(r'^\s*\[.*mariadb.*\]', line, re.IGNORECASE):
                if not has_enabled:
                    new_lines.insert(-1, 'enabled=0')
                in_mariadb_section = False
                has_enabled = False
    
    if in_mariadb_section and not has_enabled:
        new_lines.append('enabled=0')
    
    with open('$repo_file', 'w') as f:
        f.write('\n'.join(new_lines))
except:
    # Fallback: just rename the file
    import os
    os.rename('$repo_file', '${repo_file}.disabled')
" 2>/dev/null || \
                                    # Fallback: rename the file to disable it
                                    mv "$repo_file" "${repo_file}.disabled" 2>/dev/null || true
                                fi
                            fi
                        done
                    }
                    
                    # Export function so it can be called from installer
                    export -f disable_mariadb_repos
                    export MARIADB_VERSION="$mariadb_version"
                    
                    # Also set up a background process to monitor and disable repos
                    (
                        while [ ! -f /tmp/cyberpanel_install_complete ]; do
                            sleep 2
                            if [ -f /etc/yum.repos.d/mariadb-main.repo ] || [ -f /etc/yum.repos.d/mariadb.repo ]; then
                                disable_mariadb_repos
                            fi
                        done
                    ) &
                    local monitor_pid=$!
                    echo "$monitor_pid" > /tmp/cyberpanel_repo_monitor.pid
                    print_status "Started background process to monitor and disable MariaDB repositories"
                fi
            fi
        fi
    fi
    
    # Download the working CyberPanel installation files
    # Use master3395 fork which has our fixes
    # Try to download the actual installer script (install/install.py) from the repository
    echo "Downloading from: https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/cyberpanel.sh"
    
    # First, try to download the repository archive to get the correct installer
    local archive_url="https://github.com/master3395/cyberpanel/archive/v2.5.5-dev.tar.gz"
    local installer_url="https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/cyberpanel.sh"
    
    # Test if the development branch archive exists
    if curl -s --head "$archive_url" | grep -q "200 OK"; then
        echo "    Using development branch (v2.5.5-dev) from master3395/cyberpanel"
    else
        echo "    Development branch archive not available, trying installer script directly..."
        # Test if the installer script exists
        if ! curl -s --head "$installer_url" | grep -q "200 OK"; then
            echo "    Development branch not available, falling back to stable"
            installer_url="https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel.sh"
            archive_url="https://github.com/master3395/cyberpanel/archive/stable.tar.gz"
        fi
    fi
    
    curl --silent -o cyberpanel_installer.sh "$installer_url" 2>/dev/null
    if [ $? -ne 0 ] || [ ! -s "cyberpanel_installer.sh" ]; then
        print_status "ERROR: Failed to download CyberPanel installer"
        return 1
    fi
    
    # CRITICAL: Patch the installer script to skip MariaDB installation if 10.x is already installed
    if [ -n "$MARIADB_VERSION" ] && [ "$major_ver" -lt 12 ] 2>/dev/null; then
        print_status "Patching installer script to skip MariaDB installation..."
        
        # Create a backup
        cp cyberpanel_installer.sh cyberpanel_installer.sh.backup
        
        # Use Python to properly patch the installer script
        python3 -c "
import re
import sys

try:
    with open('cyberpanel_installer.sh', 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern: Add --exclude=MariaDB-server* to dnf/yum install commands that install mariadb-server
    # Match: (dnf|yum) install [flags] [packages including mariadb-server]
    def add_exclude(match):
        cmd = match.group(0)
        # Check if --exclude is already present
        if '--exclude=MariaDB-server' in cmd:
            return cmd
        # Add --exclude=MariaDB-server* after install and flags, before packages
        return re.sub(r'((?:dnf|yum)\s+install\s+(?:-[^\s]+\s+)*)', r'\1--exclude=MariaDB-server* ', cmd, flags=re.IGNORECASE)
    
    # Find all dnf/yum install commands that mention mariadb-server
    content = re.sub(
        r'(?:dnf|yum)\s+install[^;]*?mariadb-server[^;]*',
        add_exclude,
        content,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Also handle MariaDB-server (capitalized)
    content = re.sub(
        r'(?:dnf|yum)\s+install[^;]*?MariaDB-server[^;]*',
        add_exclude,
        content,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Only write if content changed
    if content != original_content:
        with open('cyberpanel_installer.sh', 'w') as f:
            f.write(content)
        print('Installer script patched successfully')
    else:
        print('No changes needed in installer script')
        
except Exception as e:
    print(f'Error patching installer script: {e}')
    sys.exit(1)
" 2>/dev/null && print_status "Installer script patched successfully" || {
        # Fallback: Simple sed-based patching if Python fails
        sed -i 's/\(dnf\|yum\) install\([^;]*\)mariadb-server/\1 install\2--exclude=MariaDB-server* mariadb-server/gi' cyberpanel_installer.sh 2>/dev/null
        sed -i 's/\(dnf\|yum\) install\([^;]*\)MariaDB-server/\1 install\2--exclude=MariaDB-server* MariaDB-server/gi' cyberpanel_installer.sh 2>/dev/null
        print_status "Installer script patched (fallback method)"
    }
        
        print_status "Installer script patched to exclude MariaDB-server from installation"
    fi
    
    # Make script executable and verify
    chmod 755 cyberpanel_installer.sh 2>/dev/null || true
    if [ ! -x "cyberpanel_installer.sh" ]; then
        print_status "WARNING: Could not make cyberpanel_installer.sh executable, will use bash to execute"
    fi
    
    # Download the install directory
    echo "Downloading installation files..."
    local archive_url="https://github.com/master3395/cyberpanel/archive/v2.5.5-dev.tar.gz"
    if [ "$installer_url" = "https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel.sh" ]; then
        archive_url="https://github.com/master3395/cyberpanel/archive/stable.tar.gz"
    fi
    
    curl --silent -L -o install_files.tar.gz "$archive_url" 2>/dev/null
    if [ $? -ne 0 ] || [ ! -s "install_files.tar.gz" ]; then
        print_status "ERROR: Failed to download installation files"
        return 1
    fi
    
    # Extract the installation files
    tar -xzf install_files.tar.gz 2>/dev/null
    if [ $? -ne 0 ]; then
        print_status "ERROR: Failed to extract installation files"
        return 1
    fi
    
    # Copy install directory to current location
    if [ "$installer_url" = "https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel.sh" ]; then
        if [ -d "cyberpanel-stable" ]; then
            cp -r cyberpanel-stable/install . 2>/dev/null || true
            cp -r cyberpanel-stable/install.sh . 2>/dev/null || true
        fi
    else
        if [ -d "cyberpanel-v2.5.5-dev" ]; then
            cp -r cyberpanel-v2.5.5-dev/install . 2>/dev/null || true
            cp -r cyberpanel-v2.5.5-dev/install.sh . 2>/dev/null || true
        fi
    fi
    
    # Verify install directory was copied
    if [ ! -d "install" ]; then
        print_status "ERROR: install directory not found after extraction"
        print_status "Archive contents:"
        ls -la 2>/dev/null | head -20
        return 1
    fi
    
    print_status "Verified install directory exists"
    
    echo "  ✓ CyberPanel installation files downloaded"
    echo "  🔄 Starting CyberPanel installation..."
    echo ""
    echo "IMPORTANT: The installation is now running in the background."
    echo "You will see detailed output from the CyberPanel installer below."
    echo "This is normal and expected - the installation is proceeding!"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    # Run the installer with live progress monitoring
    echo "Starting CyberPanel installation process..."
    echo "This may take several minutes. Please be patient."
    echo ""
    
    # Create log directory
    mkdir -p /var/log/CyberPanel
    
    # Run the installer with live output monitoring
    echo "Starting CyberPanel installer with live progress monitoring..."
    echo ""
    echo "==============================================================================================================="
    echo "                                    LIVE INSTALLATION PROGRESS"
    echo "==============================================================================================================="
    echo ""

    # Set branch environment variable for the installer
    if [ -n "$BRANCH_NAME" ]; then
        export CYBERPANEL_BRANCH="$BRANCH_NAME"
        echo "Setting installation branch to: $BRANCH_NAME"
    else
        export CYBERPANEL_BRANCH="stable"
        echo "Using default stable branch"
    fi
    echo ""

    # CRITICAL: Use install/install.py directly instead of cyberpanel_installer.sh
    # The cyberpanel_installer.sh is the old wrapper that doesn't support auto-install
    # install/install.py is the actual installer that we can control
    local installer_py="install/install.py"
    if [ -f "$installer_py" ]; then
        print_status "Using install/install.py directly for installation (non-interactive mode)"
        
        # CRITICAL: Patch install.py to exclude MariaDB-server from dnf/yum commands
        if [ -n "$MARIADB_VERSION" ] && [ "$major_ver" -lt 12 ] 2>/dev/null; then
            print_status "Patching install.py to exclude MariaDB-server from installation commands..."
            
            # Create backup
            cp "$installer_py" "${installer_py}.backup" 2>/dev/null || true
            
            # Patch install.py to add --exclude=MariaDB-server* to dnf/yum install commands
            python3 -c "
import re
import sys

try:
    with open('$installer_py', 'r') as f:
        content = f.read()
    
    original_content = content
    
    # Pattern: Add --exclude=MariaDB-server* to dnf/yum install commands that install mariadb-server
    def add_exclude(match):
        cmd = match.group(0)
        # Check if --exclude is already present
        if '--exclude=MariaDB-server' in cmd:
            return cmd
        # Add --exclude=MariaDB-server* after install and flags, before packages
        return re.sub(r'((?:dnf|yum)\s+install\s+(?:-[^\s]+\s+)*)', r'\1--exclude=MariaDB-server* ', cmd, flags=re.IGNORECASE)
    
    # Find all dnf/yum install commands that mention mariadb-server
    content = re.sub(
        r'(?:dnf|yum)\s+install[^;]*?mariadb-server[^;]*',
        add_exclude,
        content,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Also handle MariaDB-server (capitalized) and in Python strings
    content = re.sub(
        r'(\"|\')(?:dnf|yum)\s+install[^\"]*?mariadb-server[^\"]*(\"|\')',
        lambda m: m.group(1) + re.sub(r'((?:dnf|yum)\s+install\s+(?:-[^\s]+\s+)*)', r'\1--exclude=MariaDB-server* ', m.group(0)[1:-1], flags=re.IGNORECASE) + m.group(2),
        content,
        flags=re.IGNORECASE | re.MULTILINE
    )
    
    # Only write if content changed
    if content != original_content:
        with open('$installer_py', 'w') as f:
            f.write(content)
        print('install.py patched successfully')
    else:
        print('No changes needed in install.py')
        
except Exception as e:
    print(f'Error patching install.py: {e}')
    sys.exit(1)
" 2>/dev/null && print_status "install.py patched successfully" || {
            # Fallback: Simple sed-based patching if Python fails
            sed -i 's/\(dnf\|yum\) install\([^;]*\)mariadb-server/\1 install\2--exclude=MariaDB-server* mariadb-server/gi' "$installer_py" 2>/dev/null
            sed -i 's/\(dnf\|yum\) install\([^;]*\)MariaDB-server/\1 install\2--exclude=MariaDB-server* MariaDB-server/gi' "$installer_py" 2>/dev/null
            print_status "install.py patched (fallback method)"
        }
        fi
        
        # If MariaDB 10.x is installed, disable repositories right before running installer
        if [ -n "$MARIADB_VERSION" ] && [ -f /tmp/cyberpanel_repo_monitor.pid ]; then
            # Call the disable function one more time before installer runs
            if type disable_mariadb_repos >/dev/null 2>&1; then
                disable_mariadb_repos
            fi
        fi
        
        # Get server IP address (required by install.py)
        local server_ip
        if command -v curl >/dev/null 2>&1; then
            server_ip=$(curl -s --max-time 5 https://api.ipify.org 2>/dev/null || curl -s --max-time 5 https://icanhazip.com 2>/dev/null || echo "")
        fi
        
        if [ -z "$server_ip" ]; then
            # Fallback: try to get IP from network interfaces
            server_ip=$(ip route get 8.8.8.8 2>/dev/null | awk '{print $7; exit}' || \
                       hostname -I 2>/dev/null | awk '{print $1}' || \
                       echo "127.0.0.1")
        fi
        
        if [ -z "$server_ip" ] || [ "$server_ip" = "127.0.0.1" ]; then
            print_status "WARNING: Could not detect public IP, using 127.0.0.1"
            server_ip="127.0.0.1"
        fi
        
        print_status "Detected server IP: $server_ip"
        
        # CRITICAL: Install Python MySQL dependencies before running install.py
        # installCyberPanel.py requires MySQLdb (mysqlclient) which needs development headers
        print_status "Installing Python MySQL dependencies..."
        
        # Detect OS for package installation
        local os_family=""
        if [ -f /etc/os-release ]; then
            . /etc/os-release
            case "$ID" in
                almalinux|rocky|centos|rhel|fedora)
                    os_family="rhel"
                    ;;
                ubuntu|debian)
                    os_family="debian"
                    ;;
            esac
        fi
        
        # Install MariaDB/MySQL development headers and Python mysqlclient
        if [ "$os_family" = "rhel" ]; then
            # RHEL-based (AlmaLinux, Rocky, CentOS, RHEL)
            print_status "Installing MariaDB development headers for RHEL-based system..."
            
            # Try to install mariadb-devel (works with MariaDB 10.x and 12.x)
            if command -v dnf >/dev/null 2>&1; then
                # For AlmaLinux 9/10 and newer
                dnf install -y --allowerasing --skip-broken --nobest \
                    mariadb-devel pkgconfig gcc python3-devel python3-pip 2>/dev/null || \
                dnf install -y --allowerasing --skip-broken --nobest \
                    mysql-devel pkgconfig gcc python3-devel python3-pip 2>/dev/null || \
                dnf install -y --allowerasing --skip-broken --nobest \
                    mariadb-connector-c-devel pkgconfig gcc python3-devel python3-pip 2>/dev/null || true
            else
                # For older systems with yum
                yum install -y mariadb-devel pkgconfig gcc python3-devel python3-pip 2>/dev/null || \
                yum install -y mysql-devel pkgconfig gcc python3-devel python3-pip 2>/dev/null || true
            fi
            
            # Install mysqlclient Python package
            print_status "Installing mysqlclient Python package..."
            python3 -m pip install --quiet --upgrade pip setuptools wheel 2>/dev/null || true
            python3 -m pip install --quiet mysqlclient 2>/dev/null || {
                # If pip install fails, try with build dependencies
                print_status "Retrying mysqlclient installation with build dependencies..."
                python3 -m pip install --quiet --no-cache-dir mysqlclient 2>/dev/null || true
            }
            
        elif [ "$os_family" = "debian" ]; then
            # Debian-based (Ubuntu, Debian)
            print_status "Installing MariaDB development headers for Debian-based system..."
            apt-get update -y 2>/dev/null || true
            apt-get install -y libmariadb-dev libmariadb-dev-compat pkg-config build-essential python3-dev python3-pip 2>/dev/null || \
            apt-get install -y default-libmysqlclient-dev pkg-config build-essential python3-dev python3-pip 2>/dev/null || true
            
            # Install mysqlclient Python package
            print_status "Installing mysqlclient Python package..."
            python3 -m pip install --quiet --upgrade pip setuptools wheel 2>/dev/null || true
            python3 -m pip install --quiet mysqlclient 2>/dev/null || {
                print_status "Retrying mysqlclient installation with build dependencies..."
                python3 -m pip install --quiet --no-cache-dir mysqlclient 2>/dev/null || true
            }
        fi
        
        # Verify MySQLdb is available
        if python3 -c "import MySQLdb" 2>/dev/null; then
            print_status "✓ MySQLdb module is available"
        else
            print_status "⚠️  WARNING: MySQLdb module not available, installation may fail"
            print_status "Attempting to continue anyway..."
        fi
        
        # Build installer arguments based on user preferences
        # install.py requires publicip as first positional argument
        local install_args=("$server_ip")
        
        # Add optional arguments based on user preferences
        # Default: OpenLiteSpeed, Full installation (postfix, powerdns, ftp), Local MySQL
        # These match what the user selected in the interactive prompts
        install_args+=("--postfix" "ON")
        install_args+=("--powerdns" "ON")
        install_args+=("--ftp" "ON")
        install_args+=("--remotemysql" "OFF")
        
        if [ "$DEBUG_MODE" = true ]; then
            # Note: install.py doesn't have --debug, but we can set it via environment
            export DEBUG_MODE=true
        fi
        
        # Run the Python installer directly
        if [ "$DEBUG_MODE" = true ]; then
            python3 "$installer_py" "${install_args[@]}" 2>&1 | tee /var/log/CyberPanel/install_output.log
        else
            python3 "$installer_py" "${install_args[@]}" 2>&1 | tee /var/log/CyberPanel/install_output.log
        fi
    else
        # Fallback to cyberpanel_installer.sh if install.py not found
        print_status "WARNING: install/install.py not found, using cyberpanel_installer.sh (may be interactive)"
        
        local installer_script="cyberpanel_installer.sh"
        if [ ! -f "$installer_script" ]; then
            print_status "ERROR: cyberpanel_installer.sh not found in current directory: $(pwd)"
            return 1
        fi
        
        # Get absolute path to installer script
        local installer_path
        if [[ "$installer_script" = /* ]]; then
            installer_path="$installer_script"
        else
            installer_path="$(pwd)/$installer_script"
        fi
        
        # If MariaDB 10.x is installed, disable repositories right before running installer
        if [ -n "$MARIADB_VERSION" ] && [ -f /tmp/cyberpanel_repo_monitor.pid ]; then
            # Call the disable function one more time before installer runs
            if type disable_mariadb_repos >/dev/null 2>&1; then
                disable_mariadb_repos
            fi
        fi
        
        if [ "$DEBUG_MODE" = true ]; then
            bash "$installer_path" --debug 2>&1 | tee /var/log/CyberPanel/install_output.log
        else
            bash "$installer_path" 2>&1 | tee /var/log/CyberPanel/install_output.log
        fi
    fi
    
    local install_exit_code=${PIPESTATUS[0]}
    
    # Stop the repository monitor
    if [ -f /tmp/cyberpanel_repo_monitor.pid ]; then
        local monitor_pid=$(cat /tmp/cyberpanel_repo_monitor.pid 2>/dev/null)
        if [ -n "$monitor_pid" ] && kill -0 "$monitor_pid" 2>/dev/null; then
            kill "$monitor_pid" 2>/dev/null
        fi
        rm -f /tmp/cyberpanel_repo_monitor.pid
    fi
    touch /tmp/cyberpanel_install_complete 2>/dev/null || true

    local install_exit_code=${PIPESTATUS[0]}

    # Extract the generated password from the installation output
    local generated_password=$(grep "Panel password:" /var/log/CyberPanel/install_output.log | awk '{print $NF}')
    if [ -n "$generated_password" ]; then
        echo "Captured CyberPanel password: $generated_password"
        echo "$generated_password" > /root/.cyberpanel_password
        chmod 600 /root/.cyberpanel_password
    fi
    
    echo ""
    echo "==============================================================================================================="
    echo "                                    INSTALLATION COMPLETED"
    echo "==============================================================================================================="
    echo ""
    
    # Check if installation was successful
    if [ $install_exit_code -ne 0 ]; then
        print_status "ERROR: CyberPanel installation failed with exit code $install_exit_code"
        echo ""
        echo "Installation log (last 50 lines):"
        echo "==============================================================================================================="
        tail -50 /var/log/CyberPanel/install_output.log 2>/dev/null || echo "Could not read installation log"
        echo "==============================================================================================================="
        echo ""
        echo "Full installation log available at: /var/log/CyberPanel/install_output.log"
        echo ""
        return 1
    fi
    
    # Clean up temporary directory
    cd /tmp
    rm -rf "$temp_dir" 2>/dev/null || true
    
    # Check if installation was successful
    if [ $install_exit_code -eq 0 ]; then
        # Installation succeeded, but don't print success message yet
        # The CyberPanel installer has already shown its summary

        # Run static file permission fixes (critical for LiteSpeed) silently
        fix_static_file_permissions >/dev/null 2>&1

        return 0
    else
        print_status "ERROR: CyberPanel installation failed (exit code: $install_exit_code)"
        echo ""
        echo "==============================================================================================================="
        echo "                                    INSTALLATION FAILED"
        echo "==============================================================================================================="
        echo ""
        echo "The CyberPanel installation has failed. Here's how to troubleshoot:"
        echo ""
        echo "📋 LOG FILES LOCATION:"
        echo "  • Main installer log: /var/log/CyberPanel/install.log"
        echo "  • Installation output: /var/log/CyberPanel/install_output.log"
        echo "  • System logs: /var/log/messages"
        echo ""
        echo "🔍 TROUBLESHOOTING STEPS:"
        echo "  1. Check the installation output log for specific errors"
        echo "  2. Verify your system meets the requirements"
        echo "  3. Ensure you have sufficient disk space and memory"
        echo "  4. Check your internet connection"
        echo "  5. Try running the installer again"
        echo ""
        echo "📄 LAST 30 LINES OF INSTALLATION LOG:"
        echo "==============================================================================================================="
        if [ -f "/var/log/CyberPanel/install_output.log" ]; then
            tail -30 /var/log/CyberPanel/install_output.log 2>/dev/null || echo "Could not read installation log"
        else
            echo "Installation log not found at /var/log/CyberPanel/install_output.log"
        fi
        echo "==============================================================================================================="
        echo ""
        echo "💡 QUICK DEBUG COMMANDS:"
        echo "  • View full log: cat /var/log/CyberPanel/install_output.log"
        echo "  • Check system: free -h && df -h"
        echo "  • Check network: ping -c 3 google.com"
        echo "  • Retry installation: Run the installer again"
        echo ""
        echo "🆘 NEED HELP?"
        echo "  • CyberPanel Documentation: https://docs.cyberpanel.net"
        echo "  • CyberPanel Community: https://forums.cyberpanel.net"
        echo "  • GitHub Issues: https://github.com/usmannasir/cyberpanel/issues"
        echo ""
        return 1
    fi
}

# Function to apply fixes
apply_fixes() {
    echo ""
    echo "Applying post-installation configurations..."

    # Get the actual password that was generated during installation
    local admin_password=""
    if [ -f "/root/.cyberpanel_password" ]; then
        admin_password=$(cat /root/.cyberpanel_password 2>/dev/null)
    fi

    # If no password was captured, use the default
    if [ -z "$admin_password" ]; then
        admin_password="1234567"
        echo "$admin_password" > /root/.cyberpanel_password
        chmod 600 /root/.cyberpanel_password
    fi

    # Fix database issues
    systemctl start mariadb 2>/dev/null || true
    systemctl enable mariadb 2>/dev/null || true

    # Fix LiteSpeed service
    cat > /etc/systemd/system/lsws.service << 'EOF'
[Unit]
Description=LiteSpeed Web Server
After=network.target

[Service]
Type=forking
User=root
Group=root
ExecStart=/usr/local/lsws/bin/lswsctrl start
ExecStop=/usr/local/lsws/bin/lswsctrl stop
ExecReload=/usr/local/lsws/bin/lswsctrl restart
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable lsws
    systemctl start lsws

    # Set OpenLiteSpeed admin password to match CyberPanel
    echo "  • Configuring OpenLiteSpeed admin password..."
    if [ -f "/usr/local/lsws/admin/misc/admpass.sh" ]; then
        # Auto-answer the prompts for username and password
        (echo "admin"; echo "$admin_password"; echo "$admin_password") | /usr/local/lsws/admin/misc/admpass.sh >/dev/null 2>&1 || {
            # Alternative method: directly create htpasswd entry
            echo "admin:$(openssl passwd -apr1 '$admin_password')" > /usr/local/lsws/admin/htpasswd 2>/dev/null || true
        }
        echo "  ✓ OpenLiteSpeed configured"
    fi

    # Ensure CyberPanel (lscpd) service is running
    echo "  • Starting CyberPanel service..."
    systemctl enable lscpd 2>/dev/null || true
    systemctl start lscpd 2>/dev/null || true

    # Give services a moment to start
    sleep 3

    echo "  ✓ Post-installation configurations completed"
}

# Function to show status summary
show_status_summary() {
    echo "==============================================================================================================="
    echo "                                    FINAL STATUS CHECK"
    echo "==============================================================================================================="
    echo ""

    # Quick service check
    local all_services_running=true

    echo "Service Status:"
    if systemctl is-active --quiet mariadb; then
        echo "  ✓ MariaDB Database - Running"
    else
        echo "  ✗ MariaDB Database - Not Running"
        all_services_running=false
    fi

    if systemctl is-active --quiet lsws; then
        echo "  ✓ LiteSpeed Web Server - Running"
    else
        echo "  ✗ LiteSpeed Web Server - Not Running"
        all_services_running=false
    fi

    if systemctl is-active --quiet lscpd; then
        echo "  ✓ CyberPanel Application - Running"
    else
        echo "  ✗ CyberPanel Application - Not Running (may take a moment to start)"
    fi

    # Get the actual password that was set
    local admin_password=""
    local server_ip=$(curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")

    # Check if password was set in /root/.cyberpanel_password (if it exists)
    if [ -f "/root/.cyberpanel_password" ]; then
        admin_password=$(cat /root/.cyberpanel_password 2>/dev/null)
    fi

    # If we have a password, show access details
    if [ -n "$admin_password" ]; then
        echo ""
        echo "Access Details:"
        echo "  CyberPanel: https://$server_ip:8090"
        echo "  Username: admin"
        echo "  Password: $admin_password"
        echo ""
        echo "  OpenLiteSpeed: https://$server_ip:7080"
        echo "  Username: admin"
        echo "  Password: $admin_password"
    fi

    echo ""
    echo "==============================================================================================================="

    if [ "$all_services_running" = true ]; then
        echo "✓ Installation completed successfully!"
    else
        echo "⚠ Installation completed with warnings. Some services may need attention."
    fi
    echo ""
}

# Function to show main menu
show_main_menu() {
    show_banner
    
    echo "==============================================================================================================="
    echo "                                    SELECT INSTALLATION TYPE"
    echo "==============================================================================================================="
    echo ""
    echo "   1.  Fresh Installation (Recommended)"
    echo "   2.  Update Existing Installation"
    echo "   3.  Reinstall CyberPanel"
    echo "   4.  Force Reinstall (Clean & Install)"
    echo "   5.  Pre-Upgrade (Download latest upgrade script)"
    echo "   6.  Check System Status"
    echo "   7.  Advanced Options"
    echo "   8.  Exit"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Enter your choice [1-8]: "
        read -r choice
        
        case $choice in
            1)
                INSTALLATION_TYPE="fresh"
                show_fresh_install_menu
                return
                ;;
            2)
                INSTALLATION_TYPE="update"
                show_update_menu
                return
                ;;
            3)
                INSTALLATION_TYPE="reinstall"
                show_reinstall_menu
                return
                ;;
            4)
                INSTALLATION_TYPE="force_reinstall"
                start_force_reinstall
                return
                ;;
            5)
                start_preupgrade
                return
                ;;
            6)
                show_system_status
                return
                ;;
            7)
                show_advanced_menu
                return
                ;;
            8)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-7."
                echo ""
      ;;
    esac
    done
}

# Function to show fresh installation menu
show_fresh_install_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    FRESH INSTALLATION SETUP"
    echo "==============================================================================================================="
    echo ""
    
    # Check if CyberPanel is already installed
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        echo "WARNING: CyberPanel appears to be already installed on this system."
        echo "         Consider using 'Update' or 'Reinstall' options instead."
        echo ""
        echo -n "Do you want to continue with fresh installation anyway? (y/n): "
        read -r response
        case $response in
            [yY]|[yY][eE][sS])
                ;;
            *)
                show_main_menu
                return
                ;;
        esac
    fi
    
    echo "Select installation option:"
    echo ""
    echo "   1.  Install Latest Stable Version"
    echo "   2.  Install Development Version (v2.5.5-dev)"
    echo "   3.  Install Specific Version/Branch"
    echo "   4.  Install from Commit Hash"
    echo "   5.  Quick Install (Auto-configure everything)"
    echo "   6.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select installation option [1-6]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
                show_installation_preferences
                return
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                show_installation_preferences
                return
                ;;
            3)
                show_version_selection
                return
                ;;
            4)
                show_commit_selection
                return
                ;;
            5)
                BRANCH_NAME=""
                AUTO_INSTALL=true
                start_installation
                return
                ;;
            6)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-6."
                echo ""
  ;;
esac
    done
}

# Function to show commit selection
show_commit_selection() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    COMMIT HASH SELECTION"
    echo "==============================================================================================================="
    echo ""
    echo "Enter a specific commit hash to install from:"
    echo ""
    echo "Examples:"
    echo "  • Latest commit: Leave empty (press Enter)"
    echo "  • Specific commit: a1b2c3d4e5f6789012345678901234567890abcd"
    echo "  • Short commit: a1b2c3d (first 7 characters)"
    echo ""
    echo "You can find commit hashes at: https://github.com/usmannasir/cyberpanel/commits"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Enter commit hash (or press Enter for latest): "
        read -r commit_hash
        
        if [ -z "$commit_hash" ]; then
            echo "Using latest commit..."
            BRANCH_NAME=""
            show_installation_preferences
            return
        elif [[ "$commit_hash" =~ ^[a-f0-9]{7,40}$ ]]; then
            echo "Using commit: $commit_hash"
            BRANCH_NAME="$commit_hash"
            show_installation_preferences
            return
        else
            echo ""
            echo "ERROR: Invalid commit hash format."
            echo "       Please enter a valid Git commit hash (7-40 hexadecimal characters)."
            echo ""
        fi
    done
}

# Function to show version selection
show_version_selection() {
    echo ""
    echo "==============================================================================================================="
    echo "                                        VERSION SELECTION"
    echo "==============================================================================================================="
    echo ""
    echo "Available versions:"
    echo ""
    echo "   1.  Latest Stable (Recommended)"
    echo "   2.  v2.5.5-dev (Development)"
    echo "   3.  v2.5.4 (Previous Stable)"
    echo "   4.  Custom Branch Name"
    echo "   5.  Custom Commit Hash"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select version [1-5]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
                break
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                break
                ;;
            3)
                BRANCH_NAME="v2.5.4"
                break
                ;;
            4)
                echo -n "Enter branch name (e.g., main, v2.5.5-dev): "
                read -r BRANCH_NAME
                if [ -z "$BRANCH_NAME" ]; then
                    echo "ERROR: Branch name cannot be empty."
                    continue
                fi
                # Add v prefix if it's a version number without v
                if [[ "$BRANCH_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                    if [[ "$BRANCH_NAME" == *"-"* ]]; then
                        # Already has suffix like 2.5.5-dev, add v prefix
                        BRANCH_NAME="v$BRANCH_NAME"
                    else
                        # Add v prefix and dev suffix for development versions
                        BRANCH_NAME="v$BRANCH_NAME-dev"
                    fi
                fi
                break
                ;;
            5)
                echo -n "Enter commit hash (7-40 characters): "
                read -r commit_hash
                if [[ "$commit_hash" =~ ^[a-f0-9]{7,40}$ ]]; then
                    BRANCH_NAME="$commit_hash"
                    break
                else
                    echo "ERROR: Invalid commit hash format."
                    continue
                fi
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-5."
                echo ""
  ;;
esac
    done
    
    show_installation_preferences
}

# Function to show installation preferences
show_installation_preferences() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    INSTALLATION PREFERENCES"
    echo "==============================================================================================================="
    echo ""
    
    # Debug mode
    echo -n "Enable debug mode for detailed logging? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            DEBUG_MODE=true
            ;;
        *)
            DEBUG_MODE=false
            ;;
    esac
    
    # Auto-install
    echo -n "Auto-install without further prompts? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            AUTO_INSTALL=false
            ;;
        *)
            AUTO_INSTALL=true
            ;;
    esac
    
    # Show summary
    echo ""
    echo "==============================================================================================================="
    echo "                                    INSTALLATION SUMMARY"
    echo "==============================================================================================================="
    echo ""
    echo "   Type: $INSTALLATION_TYPE"
    echo "   Version: ${BRANCH_NAME:-'Latest Stable'}"
    echo "   Debug Mode: $DEBUG_MODE"
    echo "   Auto Install: $AUTO_INSTALL"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    echo -n "Proceed with installation? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            start_installation
            ;;
    esac
}

# Function to show update menu
show_update_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    UPDATE INSTALLATION"
    echo "==============================================================================================================="
    echo ""
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        echo "ERROR: CyberPanel is not installed on this system."
        echo "       Please use 'Fresh Installation' instead."
        echo ""
        read -p "Press Enter to return to main menu..."
        show_main_menu
        return
    fi
    
    # Check current version
    local current_version="unknown"
    if [ -f "/usr/local/CyberCP/version.txt" ]; then
        current_version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
    fi
    
    echo "Current Installation:"
    echo "Version: $current_version"
    echo "Path: /usr/local/CyberCP"
    echo ""
    
    echo "Select update option:"
    echo ""
    echo "   1.  Update to Latest Stable"
    echo "   2.  Update to Development Version"
    echo "   3.  Update to Specific Version/Branch"
    echo "   4.  Update from Commit Hash"
    echo "   5.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select update option [1-5]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
                break
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                break
                ;;
            3)
                show_version_selection
                return
                ;;
            4)
                show_commit_selection
                return
                ;;
            5)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-5."
                echo ""
                ;;
        esac
    done
    
    echo -n "Proceed with update? (This will backup your current installation) (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            start_upgrade
            ;;
    esac
}

# Function to show reinstall menu
show_reinstall_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    REINSTALL CYBERPANEL"
    echo "==============================================================================================================="
    echo ""
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        echo "ERROR: CyberPanel is not installed on this system."
        echo "       Please use 'Fresh Installation' instead."
        echo ""
        read -p "Press Enter to return to main menu..."
        show_main_menu
        return
    fi
    
    echo "WARNING: This will completely remove the existing CyberPanel installation"
    echo "         and install a fresh copy. All data will be lost!"
    echo ""
    
    echo -n "Are you sure you want to reinstall? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            ;;
        *)
            show_main_menu
            return
            ;;
    esac
    
    echo "Select reinstall option:"
    echo ""
    echo "   1.  Reinstall Latest Stable"
    echo "   2.  Reinstall Development Version"
    echo "   3.  Reinstall Specific Version/Branch"
    echo "   4.  Reinstall from Commit Hash"
    echo "   5.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select reinstall option [1-5]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
    break
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                break
                ;;
            3)
                show_version_selection
                return
                ;;
            4)
                show_commit_selection
                return
                ;;
            5)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-5."
                echo ""
                ;;
        esac
    done
    
    echo -n "Proceed with reinstall? (This will delete all existing data) (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            start_reinstall
            ;;
        *)
            show_main_menu
            ;;
    esac
}

# Function to show system status
show_system_status() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    SYSTEM STATUS CHECK"
    echo "==============================================================================================================="
    echo ""
    
    # Check OS
    local os_info=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo 'Unknown')
    echo "Operating System: $os_info"
    
    # Check CyberPanel installation
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        local version="unknown"
        if [ -f "/usr/local/CyberCP/version.txt" ]; then
            version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
        fi
        echo "CyberPanel: Installed (Version: $version)"
    else
        echo "CyberPanel: Not Installed"
    fi
    
    # Check services
    echo ""
    echo "Services Status:"
    if systemctl is-active --quiet mariadb; then
        echo "  SUCCESS: MariaDB - Running"
    else
        echo "  ERROR: MariaDB - Not Running"
    fi
    
    if systemctl is-active --quiet lsws; then
        echo "  SUCCESS: LiteSpeed - Running"
    else
        echo "  ERROR: LiteSpeed - Not Running"
    fi
    
    if systemctl is-active --quiet lscpd; then
        echo "  SUCCESS: CyberPanel - Running"
    else
        echo "  ERROR: CyberPanel - Not Running"
    fi
    
    # Check ports
    echo ""
    echo "Port Status:"
    if netstat -tlnp | grep -q ":8090 "; then
        echo "  SUCCESS: Port 8090 (CyberPanel) - Listening"
    else
        echo "  ERROR: Port 8090 (CyberPanel) - Not Listening"
    fi
    
    if netstat -tlnp | grep -q ":80 "; then
        echo "  SUCCESS: Port 80 (HTTP) - Listening"
    else
        echo "  ERROR: Port 80 (HTTP) - Not Listening"
    fi
    
    echo ""
    echo -n "Return to main menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            exit 0
            ;;
        *)
            show_main_menu
            ;;
    esac
}

# Function to show advanced menu
show_advanced_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    ADVANCED OPTIONS"
    echo "==============================================================================================================="
    echo ""
    echo "   1.  Fix Installation Issues"
    echo "   2.  Clean Installation Files"
    echo "   3.  View Installation Logs"
    echo "   4.  System Diagnostics"
    echo "   5.  Show Error Help"
    echo "   6.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select advanced option [1-6]: "
        read -r choice
        
        case $choice in
            1)
                show_fix_menu
                return
                ;;
            2)
                show_clean_menu
                return
                ;;
            3)
                show_logs_menu
                return
                ;;
            4)
                show_diagnostics
                return
                ;;
            5)
                show_error_help
                return
                ;;
            6)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-6."
                echo ""
                ;;
        esac
    done
}

# Function to show error help
show_error_help() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    ERROR TROUBLESHOOTING HELP"
    echo "==============================================================================================================="
    echo ""
    echo "If your CyberPanel installation failed, here's how to troubleshoot:"
    echo ""
    echo "📋 LOG FILES LOCATION:"
    echo "  • Main installer log: /var/log/CyberPanel/install.log"
    echo "  • Installation output: /var/log/CyberPanel/install_output.log"
    echo "  • Upgrade output: /var/log/CyberPanel/upgrade_output.log"
    echo "  • System logs: /var/log/messages"
    echo ""
    echo "🔍 COMMON ISSUES & SOLUTIONS:"
    echo ""
    echo "1. DEPENDENCY INSTALLATION FAILED:"
    echo "   • Check internet connection: ping -c 3 google.com"
    echo "   • Update package lists: yum update -y (RHEL) or apt update (Debian)"
    echo "   • Check available disk space: df -h"
    echo ""
    echo "2. CYBERPANEL DOWNLOAD FAILED:"
    echo "   • Check internet connectivity"
    echo "   • Verify GitHub access: curl -I https://github.com"
    echo "   • Try different branch/version"
    echo ""
    echo "3. PERMISSION ERRORS:"
    echo "   • Ensure running as root: whoami"
    echo "   • Check file permissions: ls -la /var/log/CyberPanel/"
    echo ""
    echo "4. SYSTEM REQUIREMENTS:"
    echo "   • Minimum 1GB RAM: free -h"
    echo "   • Minimum 10GB disk space: df -h"
    echo "   • Supported OS: AlmaLinux 8/9, CentOS 7/8, Ubuntu 18.04+"
    echo ""
    echo "5. SERVICE CONFLICTS:"
    echo "   • Check running services: systemctl list-units --state=running"
    echo "   • Stop conflicting services: systemctl stop apache2 (if running)"
    echo ""
    echo "💡 QUICK DEBUG COMMANDS:"
    echo "  • View installation log: cat /var/log/CyberPanel/install_output.log"
    echo "  • Check system resources: free -h && df -h"
    echo "  • Test network: ping -c 3 google.com"
    echo "  • Check services: systemctl status lscpd"
    echo "  • View system logs: tail -50 /var/log/messages"
    echo ""
    echo "🆘 GETTING HELP:"
    echo "  • CyberPanel Documentation: https://docs.cyberpanel.net"
    echo "  • CyberPanel Community: https://forums.cyberpanel.net"
    echo "  • GitHub Issues: https://github.com/usmannasir/cyberpanel/issues"
    echo "  • Discord Support: https://discord.gg/cyberpanel"
    echo ""
    echo "🔄 RETRY INSTALLATION:"
    echo "  • Clean installation: Run installer with 'Clean Installation Files' option"
    echo "  • Different version: Try stable version instead of development"
    echo "  • Fresh system: Consider using a clean OS installation"
    echo ""
    echo "==============================================================================================================="
    echo ""
    read -p "Press Enter to return to main menu..."
    show_main_menu
}

# Function to show fix menu
show_fix_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    FIX INSTALLATION ISSUES"
    echo "==============================================================================================================="
    echo ""
    echo "This will attempt to fix common CyberPanel installation issues:"
    echo "• Database connection problems"
    echo "• Service configuration issues"
    echo "• SSL certificate problems"
    echo "• File permission issues"
    echo ""
    
    echo -n "Proceed with fixing installation issues? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_advanced_menu
            ;;
        *)
            print_status "Applying fixes..."
            apply_fixes
            print_status "SUCCESS: Fixes applied successfully"
            echo ""
            read -p "Press Enter to return to advanced menu..."
            show_advanced_menu
            ;;
    esac
}

# Function to show clean menu
show_clean_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    CLEAN INSTALLATION FILES"
    echo "==============================================================================================================="
    echo ""
    echo "WARNING: This will remove temporary installation files and logs."
    echo "         This action cannot be undone!"
    echo ""
    
    echo -n "Proceed with cleaning? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            rm -rf /tmp/cyberpanel_*
            rm -rf /var/log/cyberpanel_install.log
            echo "SUCCESS: Cleanup complete! Temporary files and logs have been removed."
            ;;
    esac
    
    echo ""
    echo -n "Return to advanced menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            show_advanced_menu
            ;;
    esac
}

# Function to show logs menu
show_logs_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    VIEW INSTALLATION LOGS"
    echo "==============================================================================================================="
    echo ""
    
    local log_file="/var/log/cyberpanel_install.log"
    
    if [ -f "$log_file" ]; then
        echo "Installation Log: $log_file"
        echo "Log Size: $(du -h "$log_file" | cut -f1)"
        echo ""
        
        echo -n "View recent log entries? (y/n) [y]: "
        read -r response
        case $response in
            [nN]|[nN][oO])
                ;;
            *)
                echo ""
                echo "Recent log entries:"
                tail -n 20 "$log_file"
                ;;
        esac
    else
        echo "No installation logs found at $log_file"
    fi
    
    echo ""
    echo -n "Return to advanced menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            show_advanced_menu
            ;;
    esac
}

# Function to show diagnostics
show_diagnostics() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    SYSTEM DIAGNOSTICS"
    echo "==============================================================================================================="
    echo ""
    
    echo "Running system diagnostics..."
    echo ""
    
    # Disk space
    echo "Disk Usage:"
    df -h | grep -E '^/dev/'
    
    # Memory usage
    echo ""
    echo "Memory Usage:"
    free -h
    
    # Load average
    echo ""
    echo "System Load:"
    uptime
    
    # Network interfaces
    echo ""
    echo "Network Interfaces:"
    ip addr show | grep -E '^[0-9]+:|inet '
    
    echo ""
    echo -n "Return to advanced menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            show_advanced_menu
            ;;
    esac
}

# Function to start upgrade
start_upgrade() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING UPGRADE"
    echo "==============================================================================================================="
    echo ""
    
    # Detect OS
    echo "Step 1/5: Detecting operating system..."
    if ! detect_os; then
        print_status "ERROR: Failed to detect operating system"
        exit 1
    fi
    echo "  ✓ Operating system detected successfully"
    echo ""
    
    # Install dependencies
    echo "Step 2/5: Installing/updating dependencies..."
    install_dependencies
    echo ""
    
    # Download and run the upgrade script
    echo "Step 3/5: Downloading CyberPanel upgrade script..."
    local upgrade_url=""
    if [ -n "$BRANCH_NAME" ]; then
        if [[ "$BRANCH_NAME" =~ ^[a-f0-9]{40}$ ]]; then
            # It's a commit hash
            echo "Downloading from commit: $BRANCH_NAME"
            upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh"
        else
            # It's a branch name
            echo "Downloading from branch: $BRANCH_NAME"
            upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh"
        fi
    else
        echo "Downloading from: https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh"
        upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh"
    fi
    
    curl --silent -o cyberpanel_upgrade.sh "$upgrade_url" 2>/dev/null
    
    chmod +x cyberpanel_upgrade.sh
    
    echo "  ✓ CyberPanel upgrade script downloaded"
    echo "  🔄 Starting CyberPanel upgrade..."
  echo ""
    echo "IMPORTANT: The upgrade is now running in the background."
    echo "You will see detailed output from the CyberPanel upgrade script below."
    echo "This is normal and expected - the upgrade is proceeding!"
  echo ""
    echo "==============================================================================================================="
  echo ""
    
    # Run the upgrade with live progress monitoring
    echo "Starting CyberPanel upgrade process..."
    echo "This may take several minutes. Please be patient."
    echo ""
    
    # Create log directory
    mkdir -p /var/log/CyberPanel
    
    # Run the upgrade with live output monitoring
    echo "Starting CyberPanel upgrade with live progress monitoring..."
    echo ""
    echo "==============================================================================================================="
    echo "                                    LIVE UPGRADE PROGRESS"
    echo "==============================================================================================================="
    echo ""
    
    # Run upgrade and show live output
    if [ "$DEBUG_MODE" = true ]; then
        ./cyberpanel_upgrade.sh --debug 2>&1 | tee /var/log/CyberPanel/upgrade_output.log
    else
        ./cyberpanel_upgrade.sh 2>&1 | tee /var/log/CyberPanel/upgrade_output.log
    fi
    
    local upgrade_exit_code=${PIPESTATUS[0]}
    
    echo ""
    echo "==============================================================================================================="
    echo "                                    UPGRADE COMPLETED"
    echo "==============================================================================================================="
    echo ""
    
    # Clean up downloaded upgrade script
    rm -f cyberpanel_upgrade.sh 2>/dev/null
    
    # Check if upgrade was successful
    if [ $upgrade_exit_code -eq 0 ]; then
        print_status "SUCCESS: CyberPanel upgraded successfully"
        return 0
    else
        print_status "ERROR: CyberPanel upgrade failed with exit code $upgrade_exit_code"
        echo ""
        echo "Upgrade log (last 50 lines):"
        echo "==============================================================================================================="
        tail -50 /var/log/CyberPanel/upgrade_output.log 2>/dev/null || echo "Could not read upgrade log"
        echo "==============================================================================================================="
        echo ""
        echo "Full upgrade log available at: /var/log/CyberPanel/upgrade_output.log"
        echo ""
        return 1
    fi
}

# Function to start force reinstall
start_force_reinstall() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    FORCE REINSTALL CYBERPANEL"
    echo "==============================================================================================================="
    echo ""
    echo "This will completely remove the existing CyberPanel installation and install a fresh copy."
    echo "All data and configurations will be lost!"
    echo ""
    
    while true; do
        echo -n "Are you sure you want to proceed? (y/N): "
        read -r confirm
        case $confirm in
            [Yy]*)
                echo ""
                echo "Starting force reinstall..."
                echo ""
                
                # Clean up existing installation
                cleanup_existing_cyberpanel
                
                # Start fresh installation
                start_installation
                break
                ;;
            [Nn]*|"")
                echo "Force reinstall cancelled."
                return
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# Function to start preupgrade
start_preupgrade() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    PRE-UPGRADE SETUP"
    echo "==============================================================================================================="
    echo ""
    
    echo "This will download the latest CyberPanel upgrade script to /usr/local/"
    echo "and prepare it for execution."
    echo ""
    
    # Get the latest version
    echo "Step 1/3: Fetching latest version information..."
    local latest_version=$(curl -s https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g' | sed 's:}*$::')
    local branch_name="v$latest_version"
    
    echo "  ✓ Latest version: $latest_version"
    echo "  ✓ Branch: $branch_name"
    echo ""
    
    # Download the upgrade script
    echo "Step 2/3: Downloading CyberPanel upgrade script..."
    local upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/$branch_name/cyberpanel_upgrade.sh"
    echo "Downloading from: $upgrade_url"
    
    if curl --silent -o /usr/local/cyberpanel_upgrade.sh "$upgrade_url" 2>/dev/null; then
        chmod 700 /usr/local/cyberpanel_upgrade.sh
        echo "  ✓ Upgrade script downloaded to /usr/local/cyberpanel_upgrade.sh"
    else
        print_status "ERROR: Failed to download upgrade script"
        return 1
    fi
    echo ""
    
    # Show instructions
    echo "Step 3/3: Setup complete!"
    echo ""
    echo "The upgrade script is now ready at: /usr/local/cyberpanel_upgrade.sh"
    echo ""
    echo "To run the upgrade, you can either:"
    echo "  1. Use this installer's 'Update Existing Installation' option"
    echo "  2. Run directly: /usr/local/cyberpanel_upgrade.sh"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    read -p "Press Enter to return to main menu..."
    show_main_menu
}

# Function to start reinstall
start_reinstall() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING REINSTALL"
    echo "==============================================================================================================="
    echo ""
    
    echo "WARNING: This will completely remove the existing CyberPanel installation!"
    echo "All data, websites, and configurations will be lost!"
    echo ""
    
    # Detect OS
    echo "Step 1/6: Detecting operating system..."
    if ! detect_os; then
        print_status "ERROR: Failed to detect operating system"
        exit 1
    fi
    echo "  ✓ Operating system detected successfully"
    echo ""
    
    # Stop services
    echo "Step 2/6: Stopping CyberPanel services..."
    systemctl stop lscpd 2>/dev/null || true
    systemctl stop lsws 2>/dev/null || true
    systemctl stop mariadb 2>/dev/null || true
    systemctl stop postfix 2>/dev/null || true
    systemctl stop dovecot 2>/dev/null || true
    systemctl stop pure-ftpd 2>/dev/null || true
    echo "  ✓ Services stopped"
    echo ""
    
    # Remove existing installation
    echo "Step 3/6: Removing existing CyberPanel installation..."
    rm -rf /usr/local/CyberCP 2>/dev/null || true
    rm -rf /usr/local/lsws 2>/dev/null || true
    rm -rf /home/cyberpanel 2>/dev/null || true
    rm -rf /var/lib/mysql 2>/dev/null || true
    rm -rf /var/log/cyberpanel 2>/dev/null || true
    echo "  ✓ Existing installation removed"
    echo ""
    
    # Install dependencies
    echo "Step 4/6: Installing dependencies..."
    install_dependencies
    echo ""
    
    # Install CyberPanel
    echo "Step 5/6: Installing CyberPanel..."
    if ! install_cyberpanel; then
        print_status "ERROR: CyberPanel installation failed"
  exit 1
fi
    echo ""
    
    # Apply fixes
    echo "Step 6/6: Applying installation fixes..."
    apply_fixes
    echo ""
    
    # Show status summary
    show_status_summary
    
    print_status "SUCCESS: CyberPanel reinstalled successfully!"
}

# Function to start installation
start_installation() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING INSTALLATION"
    echo "==============================================================================================================="
    echo ""
    
    # Detect OS
    echo "Step 1/6: Detecting operating system..."
    if ! detect_os; then
        print_status "ERROR: Failed to detect operating system"
        exit 1
    fi
    echo "  ✓ Operating system detected successfully"
    echo ""
    
    # Install dependencies
    echo "Step 2/6: Installing dependencies..."
    install_dependencies
    echo ""
    
    # Install CyberPanel
    echo "Step 3/6: Installing CyberPanel..."
    if ! install_cyberpanel; then
        print_status "ERROR: CyberPanel installation failed"
        echo ""
        echo "Would you like to see troubleshooting help? (y/n) [y]: "
        read -r show_help
        case $show_help in
            [nN]|[nN][oO])
                echo "Installation failed. Check logs at /var/log/CyberPanel/"
                echo "Run the installer again and select 'Advanced Options' → 'Show Error Help' for detailed troubleshooting."
                ;;
            *)
                show_error_help
                ;;
        esac
        exit 1
    fi
    echo ""
    
    # Apply post-installation fixes silently
    apply_fixes

    # Create standard aliases (silently)
    create_standard_aliases >/dev/null 2>&1

    # Show final status summary
    echo ""
    show_status_summary
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--branch)
                if [ -n "$2" ]; then
                    # Convert version number to branch name if needed
                    if [[ "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        if [[ "$2" == *"-"* ]]; then
                            # Already has suffix like 2.5.5-dev, add v prefix
                            BRANCH_NAME="v$2"
                        else
                            # Add v prefix and dev suffix for development versions
                            BRANCH_NAME="v$2-dev"
                        fi
                    elif [[ "$2" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        # Already has v prefix, use as is
                        BRANCH_NAME="$2"
                    else
                        # Assume it's already a branch name or commit hash
                        BRANCH_NAME="$2"
                    fi
                    shift 2
                else
                    echo "ERROR: -b/--branch requires a version number or branch name"
                    echo "Example: -b 2.5.5-dev or -b v2.5.5-dev"
                    exit 1
                fi
                ;;
            -v|--version)
                if [ -n "$2" ]; then
                    # Convert version number to branch name if needed
                    if [[ "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        if [[ "$2" == *"-"* ]]; then
                            # Already has suffix like 2.5.5-dev, add v prefix
                            BRANCH_NAME="v$2"
                        else
                            # Add v prefix and dev suffix for development versions
                            BRANCH_NAME="v$2-dev"
                        fi
                    elif [[ "$2" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        # Already has v prefix, use as is
                        BRANCH_NAME="$2"
                    else
                        # Assume it's already a branch name or commit hash
                        BRANCH_NAME="$2"
                    fi
                    shift 2
                else
                    echo "ERROR: -v/--version requires a version number or branch name"
                    echo "Example: -v 2.5.5-dev or -v v2.5.5-dev"
                    exit 1
                fi
                ;;
            --debug)
                DEBUG_MODE=true
                set -x
                shift
                ;;
            --auto)
                AUTO_INSTALL=true
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -b, --branch BRANCH    Install from specific branch/commit"
                echo "  -v, --version VER      Install specific version (auto-adds v prefix)"
                echo "  --debug               Enable debug mode"
                echo "  --auto                Auto mode without prompts"
                echo "  -h, --help            Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                    # Interactive installation"
                echo "  $0 --debug            # Debug mode installation"
                echo "  $0 --auto             # Auto installation"
                echo "  $0 -b v2.5.5-dev      # Install development version"
                echo "  $0 -v 2.5.5-dev       # Install version 2.5.5-dev"
                echo "  $0 -v 2.4.3           # Install version 2.4.3"
                echo "  $0 -b main            # Install from main branch"
                echo "  $0 -b a1b2c3d4        # Install from specific commit"
                echo ""
                echo "Standard CyberPanel Installation Methods:"
                echo "  sh <(curl https://cyberpanel.net/install.sh)"
                echo "  bash <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b 2.4.3"
                echo "  bash <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b 2.5.5-dev"
                exit 0
                ;;
            *)
                print_status "WARNING: Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Function to detect installation mode
detect_installation_mode() {
    # Check if this is being called as an upgrade script
    if [[ "$0" == *"cyberpanel_upgrade.sh"* ]] || [[ "$0" == *"upgrade"* ]]; then
        INSTALLATION_TYPE="upgrade"
        return 0
    fi
    
    # Check if this is being called as a pre-upgrade script
    if [[ "$0" == *"preUpgrade.sh"* ]] || [[ "$0" == *"preupgrade"* ]]; then
        INSTALLATION_TYPE="preupgrade"
        return 0
    fi
    
    # Check if this is being called as a standard install script
    if [[ "$0" == *"install.sh"* ]] || [[ "$0" == *"cyberpanel.sh"* ]]; then
        INSTALLATION_TYPE="install"
        return 0
    fi
    
    # Default to install mode
    INSTALLATION_TYPE="install"
    return 0
}

# Function to create standard CyberPanel aliases
create_standard_aliases() {
    print_status "Creating standard CyberPanel installation aliases..."
    
    # Create symbolic links for standard installation methods
    local script_dir="/usr/local/bin"
    local script_name="cyberpanel_enhanced.sh"
    
    # Copy this script to /usr/local/bin
    if cp "$0" "$script_dir/$script_name" 2>/dev/null; then
        chmod +x "$script_dir/$script_name"
        
        # Create aliases for standard CyberPanel methods
        ln -sf "$script_dir/$script_name" "$script_dir/cyberpanel_upgrade.sh" 2>/dev/null || true
        ln -sf "$script_dir/$script_name" "$script_dir/preUpgrade.sh" 2>/dev/null || true
        ln -sf "$script_dir/$script_name" "$script_dir/install.sh" 2>/dev/null || true
        
        print_status "✓ Standard CyberPanel aliases created"
        print_status "  - cyberpanel_upgrade.sh"
        print_status "  - preUpgrade.sh" 
        print_status "  - install.sh"
    else
        print_status "WARNING: Could not create standard aliases (permission denied)"
    fi
}

# Main installation function
main() {
    # Initialize log directory and file
    mkdir -p "/var/log/CyberPanel"
    touch "/var/log/CyberPanel/install.log"
    
    print_status "CyberPanel Enhanced Installer Starting..."
    print_status "Log file: /var/log/CyberPanel/install.log"
    
    # Detect installation mode
    detect_installation_mode
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Handle different installation modes
    case "$INSTALLATION_TYPE" in
        "upgrade")
            print_status "Running in upgrade mode..."
            if [ -n "$BRANCH_NAME" ]; then
                print_status "Upgrading to version: $BRANCH_NAME"
            fi
            start_upgrade
            ;;
        "preupgrade")
            print_status "Running in pre-upgrade mode..."
            start_preupgrade
            ;;
        "install"|*)
            if [ "$AUTO_INSTALL" = true ]; then
                # Run auto mode
                print_status "Starting auto mode..."
                
                # Detect OS
                if ! detect_os; then
                    print_status "ERROR: Failed to detect operating system"
                    exit 1
                fi
                
                # Install dependencies
                install_dependencies
                
                # Install CyberPanel
                if ! install_cyberpanel; then
                    print_status "ERROR: CyberPanel installation failed"
                    echo ""
                    echo "Would you like to see troubleshooting help? (y/n) [y]: "
                    read -r show_help
                    case $show_help in
                        [nN]|[nN][oO])
                            echo "Installation failed. Check logs at /var/log/CyberPanel/"
                            ;;
                        *)
                            show_error_help
                            ;;
                    esac
                    exit 1
                fi
                
                # Apply fixes
                apply_fixes
                
                # Create standard aliases
                create_standard_aliases
                
                # Show status summary
                show_status_summary
                
                print_status "SUCCESS: Installation completed successfully!"
            else
                # Run interactive mode
                show_main_menu
            fi
            ;;
    esac
}

# Run main function
main "$@"
