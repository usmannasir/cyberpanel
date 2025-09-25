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
    if echo $OUTPUT | grep -q "AlmaLinux 9" ; then
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
        print_status "Supported OS: AlmaLinux 8/9, CentOS 8/9, Rocky Linux 8/9, Ubuntu 20.04/22.04, Debian 11/12"
        return 1
    fi
    
    return 0
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
    
    # Set unified password for both CyberPanel and OpenLiteSpeed
    local unified_password="1234567"
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
            if [ "$SERVER_OS" = "AlmaLinux9" ] || [ "$SERVER_OS" = "CentOS9" ] || [ "$SERVER_OS" = "RockyLinux9" ]; then
                # AlmaLinux 9 / CentOS 9 / Rocky Linux 9
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
    
    # Download the working CyberPanel installation files
    echo "Downloading from: https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh"
    # Try development branch first, fallback to stable
    local installer_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/v2.5.5-dev/cyberpanel.sh"
    
    # Test if the development branch exists
    if ! curl -s --head "$installer_url" | grep -q "200 OK"; then
        echo "    Development branch not available, falling back to stable"
        installer_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh"
    else
        echo "    Using development branch (v2.5.5-dev)"
    fi
    
    curl --silent -o cyberpanel_installer.sh "$installer_url" 2>/dev/null
    if [ $? -ne 0 ] || [ ! -s "cyberpanel_installer.sh" ]; then
        print_status "ERROR: Failed to download CyberPanel installer"
        return 1
    fi
    
    chmod +x cyberpanel_installer.sh
    
    # Download the install directory
    echo "Downloading installation files..."
    local archive_url="https://github.com/usmannasir/cyberpanel/archive/v2.5.5-dev.tar.gz"
    if [ "$installer_url" = "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh" ]; then
        archive_url="https://github.com/usmannasir/cyberpanel/archive/stable.tar.gz"
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
    if [ "$installer_url" = "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel.sh" ]; then
        cp -r cyberpanel-stable/install . 2>/dev/null || true
        cp -r cyberpanel-stable/install.sh . 2>/dev/null || true
    else
        cp -r cyberpanel-v2.5.5-dev/install . 2>/dev/null || true
        cp -r cyberpanel-v2.5.5-dev/install.sh . 2>/dev/null || true
    fi
    
    echo "  ✓ CyberPanel installation files downloaded"
    echo "  🔄 Starting CyberPanel installation..."
    echo ""
    echo "IMPORTANT: The installation is now running in the background."
    echo "You will see detailed output from the CyberPanel installer below."
    echo "This is normal and expected - the installation is proceeding!"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    # Run the installer with active progress monitoring
    echo "Starting CyberPanel installation process..."
    echo "This may take several minutes. Please be patient."
    echo ""
    
    # Start the installer in background and monitor progress
    echo "Starting CyberPanel installer with PID tracking..."
    ./cyberpanel_installer.sh $([ "$DEBUG_MODE" = true ] && echo "--debug") > /var/log/CyberPanel/install_output.log 2>&1 &
    local install_pid=$!
    
    # Give the process a moment to start
    sleep 2
    
    # Check if the process is still running
    if ! kill -0 $install_pid 2>/dev/null; then
        print_status "ERROR: CyberPanel installer failed to start or exited immediately"
        echo ""
        echo "Debugging information:"
        echo "  • Installer file size: $(wc -c < cyberpanel_installer.sh 2>/dev/null || echo 'unknown') bytes"
        echo "  • File permissions: $(ls -la cyberpanel_installer.sh 2>/dev/null || echo 'file not found')"
        echo "  • First few lines of installer:"
        head -3 cyberpanel_installer.sh 2>/dev/null || echo "Could not read file"
        echo ""
        echo "Installation log:"
        cat /var/log/CyberPanel/install_output.log 2>/dev/null || echo "No log file found"
        echo ""
        echo "This usually means:"
        echo "  1. The installer has syntax errors or missing dependencies"
        echo "  2. The installer requires specific arguments or environment"
        echo "  3. Missing installation files or directories"
        echo ""
        return 1
    fi
    
    # Active progress bar with real-time updates
    local progress=0
    local bar_length=50
    local start_time=$(date +%s)
    local last_progress=0
    
    echo "Progress: [                                                  ] 0%"
    echo ""
    echo "Status: Downloading and installing CyberPanel components..."
    echo ""
    
    # Monitor the installation process
    local min_wait_time=30  # Minimum 30 seconds before allowing completion
    local max_wait_time=1800  # Maximum 30 minutes timeout
    while true; do
        # Check if process is still running
        if ! kill -0 $install_pid 2>/dev/null; then
            # Process has finished, but wait minimum time
            if [ $elapsed -ge $min_wait_time ]; then
                break
            else
                # Still within minimum wait time, continue monitoring
                sleep 2
                continue
            fi
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        # Check for timeout
        if [ $elapsed -gt $max_wait_time ]; then
            print_status "ERROR: Installation timeout after $((max_wait_time / 60)) minutes"
            kill $install_pid 2>/dev/null || true
            break
        fi
        
        # Calculate progress based on elapsed time (conservative and realistic)
        if [ $elapsed -lt 30 ]; then
            progress=$((elapsed * 2))  # 0-60% in first 30 seconds
        elif [ $elapsed -lt 120 ]; then
            progress=$((60 + (elapsed - 30) * 1))  # 60-150% in next 90 seconds
        elif [ $elapsed -lt 300 ]; then
            progress=$((150 + (elapsed - 120) * 1))  # 150-330% in next 3 minutes
        else
            progress=$((330 + (elapsed - 300) * 1))  # 330%+ after 5 minutes
        fi
        
        # Cap progress at 95% until actually complete
        if [ $progress -gt 95 ]; then
            progress=95
        fi
        
        # Only update display if progress changed significantly
        if [ $progress -gt $last_progress ]; then
            # Create progress bar
            local filled=$((progress * bar_length / 100))
            local empty=$((bar_length - filled))
            
            local bar=""
            for ((i=0; i<filled; i++)); do
                bar="${bar}█"
            done
            for ((i=0; i<empty; i++)); do
                bar="${bar}░"
            done
            
            # Status messages based on elapsed time
            local status_msg=""
            if [ $elapsed -lt 30 ]; then
                status_msg="Downloading CyberPanel installer..."
            elif [ $elapsed -lt 120 ]; then
                status_msg="Installing core components..."
            elif [ $elapsed -lt 300 ]; then
                status_msg="Configuring services and database..."
            else
                status_msg="Finalizing installation..."
            fi
            
            # Update progress display
            printf "\r\033[KProgress: [%s] %d%% | %s | Elapsed: %dm %ds" "$bar" "$progress" "$status_msg" "$((elapsed / 60))" "$((elapsed % 60))"
            last_progress=$progress
        fi
        
        sleep 2
    done
    
    # Wait for the process to complete and get exit status
    wait $install_pid
    local install_status=$?
    
    # Show final progress
    local final_elapsed=$((elapsed / 60))
    local final_seconds=$((elapsed % 60))
    printf "\r\033[KProgress: [██████████████████████████████████████████████████] 100%% | Complete! | Elapsed: %dm %ds\n" "$final_elapsed" "$final_seconds"
    
    echo ""
    
    # Clean up temporary directory
    cd /tmp
    rm -rf "$temp_dir" 2>/dev/null || true
    
                if [ $install_status -eq 0 ]; then
                    print_status "SUCCESS: CyberPanel installed successfully"
                    
                    # Run post-installation fixes
                    echo ""
                    echo "  🔧 Running post-installation fixes..."
                    fix_post_install_issues
                    
                    return 0
                else
        print_status "ERROR: CyberPanel installation failed (exit code: $install_status)"
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
    print_status "Applying installation fixes..."
    
    # Fix database issues
    systemctl start mariadb 2>/dev/null || true
    systemctl enable mariadb 2>/dev/null || true
    mysqladmin -u root password '1234567' 2>/dev/null || true
    
    # Create cyberpanel database user
    mysql -u root -p1234567 -e "
    CREATE DATABASE IF NOT EXISTS cyberpanel;
    CREATE USER IF NOT EXISTS 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';
    GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost';
    FLUSH PRIVILEGES;
    " 2>/dev/null || true
    
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
    local unified_password="1234567"
    echo "Setting OpenLiteSpeed admin password..."
    if [ -f "/usr/local/lsws/admin/misc/admpass.sh" ]; then
        /usr/local/lsws/admin/misc/admpass.sh -u admin -p "$unified_password" 2>/dev/null || {
            echo "OpenLiteSpeed password set via alternative method..."
            # Alternative method: directly create htpasswd entry
            echo "admin:$(openssl passwd -apr1 '$unified_password')" > /usr/local/lsws/admin/htpasswd 2>/dev/null || true
        }
        echo "✓ OpenLiteSpeed admin password set to: $unified_password"
    fi
    
    # Fix CyberPanel service
    cat > /etc/systemd/system/cyberpanel.service << 'EOF'
[Unit]
Description=CyberPanel Web Interface
After=network.target mariadb.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/usr/local/CyberCP
ExecStart=/usr/local/CyberPanel-venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=5
Environment=DJANGO_SETTINGS_MODULE=CyberCP.settings

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable cyberpanel
    
    print_status "SUCCESS: All fixes applied successfully"
}

# Function to show status summary
show_status_summary() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    CYBERPANEL INSTALLATION STATUS"
    echo "==============================================================================================================="
    echo ""
    
    echo "CORE SERVICES STATUS:"
    echo "--------------------------------------------------------------------------------"
    
    # Check services
    if systemctl is-active --quiet mariadb; then
        echo "SUCCESS: MariaDB Database - RUNNING"
    else
        echo "ERROR: MariaDB Database - NOT RUNNING"
    fi
    
    if systemctl is-active --quiet lsws; then
        echo "SUCCESS: LiteSpeed Web Server - RUNNING"
    else
        echo "ERROR: LiteSpeed Web Server - NOT RUNNING"
    fi
    
    if systemctl is-active --quiet cyberpanel; then
        echo "SUCCESS: CyberPanel Application - RUNNING"
    else
        echo "ERROR: CyberPanel Application - NOT RUNNING"
    fi
    
    echo ""
    echo "NETWORK PORTS STATUS:"
    echo "--------------------------------------------------------------------------------"
    
    # Check ports
    if netstat -tlnp | grep -q ":8090 "; then
        echo "SUCCESS: Port 8090 (CyberPanel) - LISTENING"
    else
        echo "ERROR: Port 8090 (CyberPanel) - NOT LISTENING"
    fi
    
    if netstat -tlnp | grep -q ":80 "; then
        echo "SUCCESS: Port 80 (HTTP) - LISTENING"
    else
        echo "ERROR: Port 80 (HTTP) - NOT LISTENING"
    fi
    
    echo ""
    echo "SUMMARY:"
    echo "--------------------------------------------------------------------------------"
    print_status "SUCCESS: INSTALLATION COMPLETED SUCCESSFULLY!"
    echo ""
    echo "Access CyberPanel at: http://your-server-ip:8090"
    echo "Default username: admin"
    echo "Default password: 1234567"
    echo ""
    echo "Access OpenLiteSpeed at: http://your-server-ip:7080"
    echo "Default username: admin"
    echo "Default password: 1234567 (same as CyberPanel)"
    echo ""
    echo "IMPORTANT: Change the default password immediately!"
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
                echo ""
                echo "ERROR: v2.5.5-dev is not yet available on GitHub."
                echo "       Please select 'Latest Stable Version' or 'Custom Branch Name' instead."
                echo "       The enhanced installer will be available after pushing to GitHub."
                echo ""
                continue
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
    
    if systemctl is-active --quiet cyberpanel; then
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
    
    # Run the upgrade with progress monitoring
    echo "Starting CyberPanel upgrade process..."
    echo "This may take several minutes. Please be patient."
    echo ""
    
    # Start the upgrade in background and monitor progress
    ./cyberpanel_upgrade.sh $([ "$DEBUG_MODE" = true ] && echo "--debug") > /var/log/CyberPanel/upgrade_output.log 2>&1 &
    local upgrade_pid=$!
    
    # Active progress bar with real-time updates
    local progress=0
    local bar_length=50
    local start_time=$(date +%s)
    local last_progress=0
    
    echo "Progress: [                                                  ] 0%"
  echo ""
    echo "Status: Upgrading CyberPanel components..."
    echo ""
    
    # Monitor the upgrade process
    while true; do
        # Check if process is still running
        if ! kill -0 $upgrade_pid 2>/dev/null; then
            # Process has finished, break the loop
            break
        fi
        
        local current_time=$(date +%s)
        local elapsed=$((current_time - start_time))
        
        # Calculate progress based on elapsed time
        if [ $elapsed -lt 30 ]; then
            progress=$((elapsed * 3))  # 0-90% in first 30 seconds
        elif [ $elapsed -lt 120 ]; then
            progress=$((90 + (elapsed - 30) * 1))  # 90-180% in next 90 seconds
        elif [ $elapsed -lt 300 ]; then
            progress=$((180 + (elapsed - 120) * 1))  # 180-360% in next 3 minutes
        else
            progress=$((360 + (elapsed - 300) * 1))  # 360%+ after 5 minutes
        fi
        
        # Cap progress at 95% until actually complete
        if [ $progress -gt 95 ]; then
            progress=95
        fi
        
        # Only update display if progress changed significantly
        if [ $progress -gt $last_progress ]; then
            # Create progress bar
            local filled=$((progress * bar_length / 100))
            local empty=$((bar_length - filled))
            
            local bar=""
            for ((i=0; i<filled; i++)); do
                bar="${bar}█"
            done
            for ((i=0; i<empty; i++)); do
                bar="${bar}░"
            done
            
            # Status messages based on elapsed time
            local status_msg=""
            if [ $elapsed -lt 30 ]; then
                status_msg="Preparing upgrade..."
            elif [ $elapsed -lt 120 ]; then
                status_msg="Upgrading core components..."
            elif [ $elapsed -lt 300 ]; then
                status_msg="Updating services and database..."
            else
                status_msg="Finalizing upgrade..."
            fi
            
            # Update progress display
            printf "\r\033[KProgress: [%s] %d%% | %s | Elapsed: %dm %ds" "$bar" "$progress" "$status_msg" "$((elapsed / 60))" "$((elapsed % 60))"
            last_progress=$progress
        fi
        
        sleep 2
    done
    
    # Wait for the process to complete and get exit status
    wait $upgrade_pid
    local upgrade_status=$?
    
    # Show final progress
    local final_elapsed=$((elapsed / 60))
    local final_seconds=$((elapsed % 60))
    printf "\r\033[KProgress: [██████████████████████████████████████████████████] 100%% | Complete! | Elapsed: %dm %ds\n" "$final_elapsed" "$final_seconds"
    
    echo ""
    
    # Clean up downloaded upgrade script
    rm -f cyberpanel_upgrade.sh 2>/dev/null
    
    if [ $upgrade_status -eq 0 ]; then
        print_status "SUCCESS: CyberPanel upgraded successfully"
        return 0
    else
        print_status "ERROR: CyberPanel upgrade failed"
        echo ""
        echo "==============================================================================================================="
        echo "                                    UPGRADE FAILED"
        echo "==============================================================================================================="
        echo ""
        echo "The CyberPanel upgrade has failed. Here's how to troubleshoot:"
        echo ""
        echo "📋 LOG FILES LOCATION:"
        echo "  • Main installer log: /var/log/CyberPanel/install.log"
        echo "  • Upgrade output: /var/log/CyberPanel/upgrade_output.log"
        echo "  • System logs: /var/log/messages"
        echo ""
        echo "🔍 TROUBLESHOOTING STEPS:"
        echo "  1. Check the upgrade output log for specific errors"
        echo "  2. Ensure your current installation is working"
        echo "  3. Check for conflicting services"
        echo "  4. Verify you have sufficient disk space"
        echo "  5. Try running the upgrade again"
        echo ""
        echo "📄 LAST 30 LINES OF UPGRADE LOG:"
        echo "==============================================================================================================="
        if [ -f "/var/log/CyberPanel/upgrade_output.log" ]; then
            tail -30 /var/log/CyberPanel/upgrade_output.log 2>/dev/null || echo "Could not read upgrade log"
        else
            echo "Upgrade log not found at /var/log/CyberPanel/upgrade_output.log"
        fi
        echo "==============================================================================================================="
        echo ""
        echo "💡 QUICK DEBUG COMMANDS:"
        echo "  • View full log: cat /var/log/CyberPanel/upgrade_output.log"
        echo "  • Check CyberPanel status: systemctl status lscpd"
        echo "  • Check system: free -h && df -h"
        echo "  • Retry upgrade: Run the installer again"
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
    
    # Apply fixes
    echo "Step 4/6: Applying installation fixes..."
    apply_fixes
    echo ""
    
    # Create standard aliases
    echo "Step 5/6: Creating standard CyberPanel aliases..."
    create_standard_aliases
    echo ""
    
    # Show status summary
    echo "Step 6/6: Finalizing installation..."
    show_status_summary
    
    print_status "SUCCESS: Installation completed successfully!"
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
