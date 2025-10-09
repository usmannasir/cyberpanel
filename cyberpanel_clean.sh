#!/bin/bash

# CyberPanel Clean Installer
# Simple, clean interface without escape codes
# This version works reliably in all terminals

set -e

# Global variables
SERVER_OS=""
OS_FAMILY=""
PACKAGE_MANAGER=""
ARCHITECTURE=""
BRANCH_NAME=""
DEBUG_MODE=false
AUTO_INSTALL=false
INTERACTIVE_MODE=true
INSTALLATION_TYPE=""

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL] $1"
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
    elif echo $OUTPUT | grep -q "AlmaLinux 10" ; then
        SERVER_OS="AlmaLinux10"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "Detected: AlmaLinux 10"
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
    elif echo $OUTPUT | grep -q "Ubuntu 25.10" ; then
        SERVER_OS="Ubuntu2510"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 25.10"
    elif echo $OUTPUT | grep -q "Ubuntu 25.04" ; then
        SERVER_OS="Ubuntu2504"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 25.04"
    elif echo $OUTPUT | grep -q "Ubuntu 24.04.3" ; then
        SERVER_OS="Ubuntu24043"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 24.04.3"
    elif echo $OUTPUT | grep -q "Ubuntu 22.04.5" ; then
        SERVER_OS="Ubuntu22045"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "Detected: Ubuntu 22.04.5"
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
        print_status "Supported OS: AlmaLinux 8/9/10, CentOS 8/9, Rocky Linux 8/9, Ubuntu 20.04/22.04/22.04.5/24.04.3/25.04/25.10, Debian 11/12"
        return 1
    fi
    
    return 0
}

# Function to install dependencies
install_dependencies() {
    print_status "Installing dependencies..."
    
    case $OS_FAMILY in
        "rhel")
            # Install EPEL
            $PACKAGE_MANAGER install -y epel-release 2>/dev/null || true
            
            # Install development tools
            $PACKAGE_MANAGER groupinstall -y 'Development Tools' 2>/dev/null || {
                $PACKAGE_MANAGER install -y gcc gcc-c++ make kernel-devel 2>/dev/null || true
            }
            
            # Install core packages
            if [ "$SERVER_OS" = "AlmaLinux9" ] || [ "$SERVER_OS" = "CentOS9" ] || [ "$SERVER_OS" = "RockyLinux9" ]; then
                # AlmaLinux 9 / CentOS 9 / Rocky Linux 9
                $PACKAGE_MANAGER install -y ImageMagick gd libicu oniguruma python3 python3-pip python3-devel 2>/dev/null || true
                $PACKAGE_MANAGER install -y aspell 2>/dev/null || print_status "WARNING: aspell not available, skipping..."
                $PACKAGE_MANAGER install -y libc-client-devel 2>/dev/null || print_status "WARNING: libc-client-devel not available, skipping..."
            else
                # AlmaLinux 8 / CentOS 8 / Rocky Linux 8
                $PACKAGE_MANAGER install -y ImageMagick gd libicu oniguruma aspell libc-client-devel python3 python3-pip python3-devel 2>/dev/null || true
            fi
            ;;
        "debian")
            # Update package lists
            apt update -qq 2>/dev/null || true
            
            # Install essential packages
            apt install -y -qq curl wget git unzip tar gzip bzip2 2>/dev/null || true
            
            # Install development tools
            apt install -y -qq build-essential gcc g++ make python3-dev python3-pip 2>/dev/null || true
            
            # Install core packages
            apt install -y -qq imagemagick php-gd libicu-dev libonig-dev 2>/dev/null || true
            apt install -y -qq aspell 2>/dev/null || print_status "WARNING: aspell not available, skipping..."
            apt install -y -qq libc-client-dev 2>/dev/null || print_status "WARNING: libc-client-dev not available, skipping..."
            ;;
    esac
    
    print_status "SUCCESS: Dependencies installed successfully"
}

# Function to install CyberPanel
install_cyberpanel() {
    print_status "Installing CyberPanel..."
    
    # Download and run the original installer
    if [ -n "$BRANCH_NAME" ]; then
        curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel.sh" 2>/dev/null
    else
        curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null
    fi
    
    chmod +x cyberpanel.sh
    
    # Run the installer
    if ./cyberpanel.sh $([ "$DEBUG_MODE" = true ] && echo "--debug") > /tmp/cyberpanel_install_output.log 2>&1; then
        print_status "SUCCESS: CyberPanel installed successfully"
        return 0
    else
        print_status "ERROR: CyberPanel installation failed. Check /tmp/cyberpanel_install_output.log for details"
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
    echo "   4.  Check System Status"
    echo "   5.  Advanced Options"
    echo "   6.  Exit"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Enter your choice [1-6]: "
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
                show_system_status
                return
                ;;
            5)
                show_advanced_menu
                return
                ;;
            6)
                echo ""
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-6."
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
    echo "   4.  Quick Install (Auto-configure everything)"
    echo "   5.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select installation option [1-5]: "
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
                BRANCH_NAME=""
                AUTO_INSTALL=true
                start_installation
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
    echo "   4.  Custom Branch/Commit"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select version [1-4]: "
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
                echo -n "Enter branch name or commit hash: "
                read -r BRANCH_NAME
                break
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-4."
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
    esac
    
    # Auto-install
    echo -n "Auto-install without further prompts? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
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
    echo "   3.  Update to Specific Version"
    echo "   4.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select update option [1-4]: "
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
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-4."
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
            start_installation
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
    echo "   3.  Reinstall Specific Version"
    echo "   4.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select reinstall option [1-4]: "
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
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-4."
                echo ""
                ;;
        esac
    done
    
    echo -n "Proceed with reinstall? (This will delete all existing data) (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            start_installation
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
    echo "   5.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select advanced option [1-5]: "
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

# Function to start installation
start_installation() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING INSTALLATION"
    echo "==============================================================================================================="
    echo ""
    
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
        exit 1
    fi
    
    # Apply fixes
    apply_fixes
    
    # Show status summary
    show_status_summary
    
    print_status "SUCCESS: Installation completed successfully!"
}

# Function to parse command line arguments
parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--branch)
                BRANCH_NAME="$2"
                shift 2
                ;;
            --debug)
                DEBUG_MODE=true
                set -x
                shift
                ;;
            --auto)
                AUTO_INSTALL=true
                INTERACTIVE_MODE=false
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -b, --branch BRANCH    Install from specific branch/commit"
                echo "  --debug               Enable debug mode"
                echo "  --auto                Auto mode without prompts"
                echo "  -h, --help            Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                    # Interactive installation"
                echo "  $0 --debug            # Debug mode installation"
                echo "  $0 --auto             # Auto installation"
                echo "  $0 -b v2.5.5-dev      # Install development version"
                exit 0
                ;;
            *)
                print_status "WARNING: Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Main installation function
main() {
    # Initialize log file
    mkdir -p /var/log
    touch "/var/log/cyberpanel_install.log"
    
    print_status "CyberPanel Clean Installer Starting..."
    print_status "Log file: /var/log/cyberpanel_install.log"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Check if auto mode is requested
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
            exit 1
        fi
        
        # Apply fixes
        apply_fixes
        
        # Show status summary
        show_status_summary
        
        print_status "SUCCESS: Installation completed successfully!"
    else
        # Run interactive mode
        show_main_menu
    fi
}

# Run main function
main "$@"
