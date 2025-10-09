#!/bin/bash

# CyberPanel Complete Standalone Installer
# Full-featured installer with interactive menus and all options
# This version works when downloaded via curl

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
BOLD='\033[1m'
DIM='\033[2m'
NC='\033[0m' # No Color

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

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to show banner
show_banner() {
    clear
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${WHITE}${BOLD}🚀 CYBERPANEL COMPLETE INSTALLER 🚀${NC}                                                              ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${CYAN}The Ultimate Web Hosting Control Panel${NC}                                                           ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${YELLOW}Powered by OpenLiteSpeed • Fast • Secure • Scalable${NC}                                            ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${GREEN}✨ Interactive Menus • Version Selection • Advanced Options ✨${NC}                                    ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

# Function to detect OS
detect_os() {
    print_status "$BLUE" "🔍 Detecting operating system..."
    
    # Detect architecture
    ARCHITECTURE=$(uname -m)
    case $ARCHITECTURE in
        x86_64)
            print_status "$GREEN" "Architecture: x86_64 (Supported)"
            ;;
        aarch64|arm64)
            print_status "$YELLOW" "Architecture: $ARCHITECTURE (Limited support)"
            ;;
        *)
            print_status "$RED" "Architecture: $ARCHITECTURE (Not supported)"
            return 1
            ;;
    esac
    
    # Get OS release information
    local OUTPUT=$(cat /etc/*release 2>/dev/null)
    if [ -z "$OUTPUT" ]; then
        print_status "$RED" "❌ Cannot read OS release information"
        return 1
    fi
    
    # Detect OS
    if echo $OUTPUT | grep -q "AlmaLinux 9" ; then
        SERVER_OS="AlmaLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: AlmaLinux 9"
    elif echo $OUTPUT | grep -q "AlmaLinux 10" ; then
        SERVER_OS="AlmaLinux10"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: AlmaLinux 10"
    elif echo $OUTPUT | grep -q "AlmaLinux 8" ; then
        SERVER_OS="AlmaLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: AlmaLinux 8"
    elif echo $OUTPUT | grep -q "CentOS Linux 9" ; then
        SERVER_OS="CentOS9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: CentOS Linux 9"
    elif echo $OUTPUT | grep -q "CentOS Linux 8" ; then
        SERVER_OS="CentOS8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: CentOS Linux 8"
    elif echo $OUTPUT | grep -q "Rocky Linux 9" ; then
        SERVER_OS="RockyLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: Rocky Linux 9"
    elif echo $OUTPUT | grep -q "Rocky Linux 8" ; then
        SERVER_OS="RockyLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: Rocky Linux 8"
    elif echo $OUTPUT | grep -q "Ubuntu 25.10" ; then
        SERVER_OS="Ubuntu2510"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 25.10"
    elif echo $OUTPUT | grep -q "Ubuntu 25.04" ; then
        SERVER_OS="Ubuntu2504"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 25.04"
    elif echo $OUTPUT | grep -q "Ubuntu 24.04.3" ; then
        SERVER_OS="Ubuntu24043"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 24.04.3"
    elif echo $OUTPUT | grep -q "Ubuntu 22.04.5" ; then
        SERVER_OS="Ubuntu22045"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 22.04.5"
    elif echo $OUTPUT | grep -q "Ubuntu 22.04" ; then
        SERVER_OS="Ubuntu2204"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 22.04"
    elif echo $OUTPUT | grep -q "Ubuntu 20.04" ; then
        SERVER_OS="Ubuntu2004"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 20.04"
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 12" ; then
        SERVER_OS="Debian12"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Debian GNU/Linux 12"
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 11" ; then
        SERVER_OS="Debian11"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Debian GNU/Linux 11"
    else
        print_status "$RED" "❌ Unsupported OS detected"
        print_status "$YELLOW" "Supported OS: AlmaLinux 8/9/10, CentOS 8/9, Rocky Linux 8/9, Ubuntu 20.04/22.04/22.04.5/24.04.3/25.04/25.10, Debian 11/12"
        return 1
    fi
    
    return 0
}

# Function to install dependencies
install_dependencies() {
    print_status "$BLUE" "📦 Installing dependencies..."
    
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
                $PACKAGE_MANAGER install -y aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
                $PACKAGE_MANAGER install -y libc-client-devel 2>/dev/null || print_status "$YELLOW" "libc-client-devel not available, skipping..."
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
            apt install -y -qq aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
            apt install -y -qq libc-client-dev 2>/dev/null || print_status "$YELLOW" "libc-client-dev not available, skipping..."
            ;;
    esac
    
    print_status "$GREEN" "✅ Dependencies installed successfully"
}

# Function to install CyberPanel
install_cyberpanel() {
    print_status "$BLUE" "🚀 Installing CyberPanel..."
    
    # Download and run the original installer
    if [ -n "$BRANCH_NAME" ]; then
        curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel.sh" 2>/dev/null
    else
        curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null
    fi
    
    chmod +x cyberpanel.sh
    
    # Run the installer
    if ./cyberpanel.sh $([ "$DEBUG_MODE" = true ] && echo "--debug") > /tmp/cyberpanel_install_output.log 2>&1; then
        print_status "$GREEN" "✅ CyberPanel installed successfully"
        return 0
    else
        print_status "$RED" "❌ CyberPanel installation failed. Check /tmp/cyberpanel_install_output.log for details"
        return 1
    fi
}

# Function to apply fixes
apply_fixes() {
    print_status "$BLUE" "🔧 Applying installation fixes..."
    
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
    
    print_status "$GREEN" "✅ All fixes applied successfully"
}

# Function to show status summary
show_status_summary() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                                               ║"
    echo "║                    📊 CYBERPANEL INSTALLATION STATUS 📊                                                      ║"
    echo "║                                                                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    echo "🔧 CORE SERVICES STATUS:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    # Check services
    if systemctl is-active --quiet mariadb; then
        echo "✅ MariaDB Database: RUNNING"
    else
        echo "❌ MariaDB Database: NOT RUNNING"
    fi
    
    if systemctl is-active --quiet lsws; then
        echo "✅ LiteSpeed Web Server: RUNNING"
    else
        echo "❌ LiteSpeed Web Server: NOT RUNNING"
    fi
    
    if systemctl is-active --quiet cyberpanel; then
        echo "✅ CyberPanel Application: RUNNING"
    else
        echo "❌ CyberPanel Application: NOT RUNNING"
    fi
    
    echo ""
    echo "🌐 NETWORK PORTS STATUS:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    # Check ports
    if netstat -tlnp | grep -q ":8090 "; then
        echo "✅ Port 8090 (CyberPanel): LISTENING"
    else
        echo "❌ Port 8090 (CyberPanel): NOT LISTENING"
    fi
    
    if netstat -tlnp | grep -q ":80 "; then
        echo "✅ Port 80 (HTTP): LISTENING"
    else
        echo "❌ Port 80 (HTTP): NOT LISTENING"
    fi
    
    echo ""
    echo "📊 SUMMARY:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    print_status "$GREEN" "🎉 INSTALLATION COMPLETED SUCCESSFULLY!"
    echo ""
    echo "🌐 Access CyberPanel at: http://your-server-ip:8090"
    echo "👤 Default username: admin"
    echo "🔑 Default password: 1234567"
    echo ""
    echo "⚠️  IMPORTANT: Change the default password immediately!"
    echo ""
}

# Function to show main menu
show_main_menu() {
    show_banner
    
    local options=(
        "🚀 Fresh Installation (Recommended)"
        "🔄 Update Existing Installation"
        "🔧 Reinstall CyberPanel"
        "📊 Check System Status"
        "🛠️  Advanced Options"
        "❌ Exit"
    )
    
    echo -e "${WHITE}${BOLD}Select Installation Type:${NC}"
    echo ""
    for i in "${!options[@]}"; do
        local option_num=$((i + 1))
        echo -e "${BLUE}${option_num}.${NC} ${options[i]}"
    done
    echo ""
    
    while true; do
        echo -e "${CYAN}Enter your choice${NC} [1-6]: "
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
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 1-6.${NC}"
                ;;
        esac
    done
}

# Function to show fresh installation menu
show_fresh_install_menu() {
    echo ""
    echo -e "${PURPLE}${BOLD}🚀 Fresh Installation Setup${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    # Check if CyberPanel is already installed
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        echo -e "${YELLOW}⚠️  CyberPanel appears to be already installed on this system.${NC}"
        echo -e "${YELLOW}Consider using 'Update' or 'Reinstall' options instead.${NC}"
        echo ""
        echo -e "${CYAN}Do you want to continue with fresh installation anyway? (y/n)${NC}: "
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
    
    # Show installation options
    local options=(
        "📦 Install Latest Stable Version"
        "🔬 Install Development Version (v2.5.5-dev)"
        "🏷️  Install Specific Version/Branch"
        "⚡ Quick Install (Auto-configure everything)"
        "🔙 Back to Main Menu"
    )
    
    echo -e "${WHITE}${BOLD}Fresh Installation Options:${NC}"
    echo ""
    for i in "${!options[@]}"; do
        local option_num=$((i + 1))
        echo -e "${BLUE}${option_num}.${NC} ${options[i]}"
    done
    echo ""
    
    while true; do
        echo -e "${CYAN}Select installation option${NC} [1-5]: "
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
                echo -e "${RED}Invalid choice. Please enter 1-5.${NC}"
                ;;
        esac
    done
}

# Function to show version selection
show_version_selection() {
    echo ""
    echo -e "${PURPLE}${BOLD}🏷️  Version Selection${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    echo -e "${WHITE}Available versions:${NC}"
    echo -e "${BLUE}1.${NC} Latest Stable (Recommended)"
    echo -e "${BLUE}2.${NC} v2.5.5-dev (Development)"
    echo -e "${BLUE}3.${NC} v2.5.4 (Previous Stable)"
    echo -e "${BLUE}4.${NC} Custom Branch/Commit"
    echo ""
    
    while true; do
        echo -e "${CYAN}Select version${NC} [1-4]: "
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
                echo -e "${CYAN}Enter branch name or commit hash${NC}: "
                read -r BRANCH_NAME
                break
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 1-4.${NC}"
                ;;
        esac
    done
    
    show_installation_preferences
}

# Function to show installation preferences
show_installation_preferences() {
    echo ""
    echo -e "${PURPLE}${BOLD}⚙️  Installation Preferences${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    # Debug mode
    echo -e "${CYAN}Enable debug mode for detailed logging? (y/n)${NC} [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            DEBUG_MODE=true
            ;;
    esac
    
    # Auto-install
    echo -e "${CYAN}Auto-install without further prompts? (y/n)${NC} [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            AUTO_INSTALL=true
            ;;
    esac
    
    # Show summary
    echo ""
    echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${BLUE}║${NC} ${WHITE}${BOLD}Installation Summary${NC}                                                                                    ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} Type: $INSTALLATION_TYPE"
    echo -e "${BLUE}║${NC} Version: ${BRANCH_NAME:-'Latest Stable'}"
    echo -e "${BLUE}║${NC} Debug Mode: $DEBUG_MODE"
    echo -e "${BLUE}║${NC} Auto Install: $AUTO_INSTALL"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    echo -e "${CYAN}Proceed with installation? (y/n)${NC} [y]: "
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
    echo -e "${PURPLE}${BOLD}🔄 Update Installation${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        echo -e "${RED}❌ CyberPanel is not installed on this system.${NC}"
        echo -e "${RED}Please use 'Fresh Installation' instead.${NC}"
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
    
    echo -e "${GREEN}Current Installation:${NC}"
    echo -e "Version: $current_version"
    echo -e "Path: /usr/local/CyberCP"
    echo ""
    
    local options=(
        "📈 Update to Latest Stable"
        "🔬 Update to Development Version"
        "🏷️  Update to Specific Version"
        "🔙 Back to Main Menu"
    )
    
    echo -e "${WHITE}${BOLD}Update Options:${NC}"
    echo ""
    for i in "${!options[@]}"; do
        local option_num=$((i + 1))
        echo -e "${BLUE}${option_num}.${NC} ${options[i]}"
    done
    echo ""
    
    while true; do
        echo -e "${CYAN}Select update option${NC} [1-4]: "
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
                echo -e "${RED}Invalid choice. Please enter 1-4.${NC}"
                ;;
        esac
    done
    
    echo -e "${CYAN}Proceed with update? (This will backup your current installation) (y/n)${NC} [y]: "
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
    echo -e "${PURPLE}${BOLD}🔧 Reinstall CyberPanel${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        echo -e "${RED}❌ CyberPanel is not installed on this system.${NC}"
        echo -e "${RED}Please use 'Fresh Installation' instead.${NC}"
        echo ""
        read -p "Press Enter to return to main menu..."
        show_main_menu
        return
    fi
    
    echo -e "${YELLOW}⚠️  WARNING: This will completely remove the existing CyberPanel installation${NC}"
    echo -e "${YELLOW}and install a fresh copy. All data will be lost!${NC}"
    echo ""
    
    echo -e "${CYAN}Are you sure you want to reinstall? (y/n)${NC} [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            ;;
        *)
            show_main_menu
            return
            ;;
    esac
    
    local options=(
        "📦 Reinstall Latest Stable"
        "🔬 Reinstall Development Version"
        "🏷️  Reinstall Specific Version"
        "🔙 Back to Main Menu"
    )
    
    echo -e "${WHITE}${BOLD}Reinstall Options:${NC}"
    echo ""
    for i in "${!options[@]}"; do
        local option_num=$((i + 1))
        echo -e "${BLUE}${option_num}.${NC} ${options[i]}"
    done
    echo ""
    
    while true; do
        echo -e "${CYAN}Select reinstall option${NC} [1-4]: "
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
                echo -e "${RED}Invalid choice. Please enter 1-4.${NC}"
                ;;
        esac
    done
    
    echo -e "${CYAN}Proceed with reinstall? (This will delete all existing data) (y/n)${NC} [n]: "
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
    echo -e "${PURPLE}${BOLD}📊 System Status Check${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    # Check OS
    local os_info=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo 'Unknown')
    echo -e "${WHITE}Operating System:${NC} $os_info"
    
    # Check CyberPanel installation
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        local version="unknown"
        if [ -f "/usr/local/CyberCP/version.txt" ]; then
            version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
        fi
        echo -e "${GREEN}CyberPanel:${NC} Installed (Version: $version)"
    else
        echo -e "${RED}CyberPanel:${NC} Not Installed"
    fi
    
    # Check services
    echo -e "\n${WHITE}Services Status:${NC}"
    if systemctl is-active --quiet mariadb; then
        echo -e "  ${GREEN}✅${NC} MariaDB: Running"
    else
        echo -e "  ${RED}❌${NC} MariaDB: Not Running"
    fi
    
    if systemctl is-active --quiet lsws; then
        echo -e "  ${GREEN}✅${NC} LiteSpeed: Running"
    else
        echo -e "  ${RED}❌${NC} LiteSpeed: Not Running"
    fi
    
    if systemctl is-active --quiet cyberpanel; then
        echo -e "  ${GREEN}✅${NC} CyberPanel: Running"
    else
        echo -e "  ${RED}❌${NC} CyberPanel: Not Running"
    fi
    
    # Check ports
    echo -e "\n${WHITE}Port Status:${NC}"
    if netstat -tlnp | grep -q ":8090 "; then
        echo -e "  ${GREEN}✅${NC} Port 8090 (CyberPanel): Listening"
    else
        echo -e "  ${RED}❌${NC} Port 8090 (CyberPanel): Not Listening"
    fi
    
    if netstat -tlnp | grep -q ":80 "; then
        echo -e "  ${GREEN}✅${NC} Port 80 (HTTP): Listening"
    else
        echo -e "  ${RED}❌${NC} Port 80 (HTTP): Not Listening"
    fi
    
    echo ""
    echo -e "${CYAN}Return to main menu? (y/n)${NC} [y]: "
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
    echo -e "${PURPLE}${BOLD}🛠️  Advanced Options${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    local options=(
        "🔧 Fix Installation Issues"
        "🧹 Clean Installation Files"
        "📋 View Installation Logs"
        "🔍 System Diagnostics"
        "🔙 Back to Main Menu"
    )
    
    echo -e "${WHITE}${BOLD}Advanced Options:${NC}"
    echo ""
    for i in "${!options[@]}"; do
        local option_num=$((i + 1))
        echo -e "${BLUE}${option_num}.${NC} ${options[i]}"
    done
    echo ""
    
    while true; do
        echo -e "${CYAN}Select advanced option${NC} [1-5]: "
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
                echo -e "${RED}Invalid choice. Please enter 1-5.${NC}"
                ;;
        esac
    done
}

# Function to show fix menu
show_fix_menu() {
    echo ""
    echo -e "${PURPLE}${BOLD}🔧 Fix Installation Issues${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}This will attempt to fix common CyberPanel installation issues:${NC}"
    echo "• Database connection problems"
    echo "• Service configuration issues"
    echo "• SSL certificate problems"
    echo "• File permission issues"
    echo ""
    
    echo -e "${CYAN}Proceed with fixing installation issues? (y/n)${NC} [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_advanced_menu
            ;;
        *)
            print_status "$BLUE" "🔧 Applying fixes..."
            apply_fixes
            print_status "$GREEN" "✅ Fixes applied successfully"
            echo ""
            read -p "Press Enter to return to advanced menu..."
            show_advanced_menu
            ;;
    esac
}

# Function to show clean menu
show_clean_menu() {
    echo ""
    echo -e "${PURPLE}${BOLD}🧹 Clean Installation Files${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    echo -e "${YELLOW}⚠️  WARNING: This will remove temporary installation files and logs.${NC}"
    echo -e "${YELLOW}This action cannot be undone!${NC}"
    echo ""
    
    echo -e "${CYAN}Proceed with cleaning? (y/n)${NC} [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            rm -rf /tmp/cyberpanel_*
            rm -rf /var/log/cyberpanel_install.log
            echo -e "${GREEN}✅ Cleanup complete! Temporary files and logs have been removed.${NC}"
            ;;
    esac
    
    echo ""
    echo -e "${CYAN}Return to advanced menu? (y/n)${NC} [y]: "
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
    echo -e "${PURPLE}${BOLD}📋 View Installation Logs${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    local log_file="/var/log/cyberpanel_install.log"
    
    if [ -f "$log_file" ]; then
        echo -e "${WHITE}Installation Log:${NC} $log_file"
        echo -e "${WHITE}Log Size:${NC} $(du -h "$log_file" | cut -f1)"
        echo ""
        
        echo -e "${CYAN}View recent log entries? (y/n)${NC} [y]: "
        read -r response
        case $response in
            [nN]|[nN][oO])
                ;;
            *)
                echo -e "${CYAN}Recent log entries:${NC}"
                tail -n 20 "$log_file"
                ;;
        esac
    else
        echo -e "${YELLOW}No installation logs found at $log_file${NC}"
    fi
    
    echo ""
    echo -e "${CYAN}Return to advanced menu? (y/n)${NC} [y]: "
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
    echo -e "${PURPLE}${BOLD}🔍 System Diagnostics${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    echo -e "${WHITE}Running system diagnostics...${NC}"
    echo ""
    
    # Disk space
    echo -e "${WHITE}Disk Usage:${NC}"
    df -h | grep -E '^/dev/'
    
    # Memory usage
    echo -e "\n${WHITE}Memory Usage:${NC}"
    free -h
    
    # Load average
    echo -e "\n${WHITE}System Load:${NC}"
    uptime
    
    # Network interfaces
    echo -e "\n${WHITE}Network Interfaces:${NC}"
    ip addr show | grep -E '^[0-9]+:|inet '
    
    echo ""
    echo -e "${CYAN}Return to advanced menu? (y/n)${NC} [y]: "
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
    echo -e "${PURPLE}${BOLD}🚀 Starting Installation${NC}"
    echo -e "${PURPLE}═══════════════════════════════════════════════════════════════════════════════════════════════════════════════${NC}"
    
    # Detect OS
    if ! detect_os; then
        print_status "$RED" "❌ Failed to detect operating system"
        exit 1
    fi
    
    # Install dependencies
    install_dependencies
    
    # Install CyberPanel
    if ! install_cyberpanel; then
        print_status "$RED" "❌ CyberPanel installation failed"
        exit 1
    fi
    
    # Apply fixes
    apply_fixes
    
    # Show status summary
    show_status_summary
    
    print_status "$GREEN" "🎉 Installation completed successfully!"
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
                print_status "$YELLOW" "Unknown option: $1"
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
    
    print_status "$BLUE" "🚀 CyberPanel Complete Installer Starting..."
    print_status "$BLUE" "Log file: /var/log/cyberpanel_install.log"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Check if auto mode is requested
    if [ "$AUTO_INSTALL" = true ]; then
        # Run auto mode
        print_status "$BLUE" "🤖 Starting auto mode..."
        
        # Detect OS
        if ! detect_os; then
            print_status "$RED" "❌ Failed to detect operating system"
            exit 1
        fi
        
        # Install dependencies
        install_dependencies
        
        # Install CyberPanel
        if ! install_cyberpanel; then
            print_status "$RED" "❌ CyberPanel installation failed"
            exit 1
        fi
        
        # Apply fixes
        apply_fixes
        
        # Show status summary
        show_status_summary
        
        print_status "$GREEN" "🎉 Installation completed successfully!"
    else
        # Run interactive mode
        show_main_menu
    fi
}

# Run main function
main "$@"
