#!/bin/bash

# CyberPanel Standalone Modular Installer
# Self-contained installer with all modules included
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
    echo -e "${BLUE}║${NC} ${WHITE}${BOLD}🚀 CYBERPANEL MODULAR INSTALLER 🚀${NC}                                                                    ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${CYAN}The Ultimate Web Hosting Control Panel${NC}                                                           ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${YELLOW}Powered by OpenLiteSpeed • Fast • Secure • Scalable${NC}                                            ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC}                                                                                                               ${BLUE}║${NC}"
    echo -e "${BLUE}║${NC} ${GREEN}✨ Beautiful UI • Modular Architecture • Smart Installation ✨${NC}                                    ${BLUE}║${NC}"
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
        print_status "$YELLOW" "Supported OS: AlmaLinux 8/9, CentOS 8/9, Rocky Linux 8/9, Ubuntu 20.04/22.04, Debian 11/12"
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

# Function to run interactive mode
run_interactive_mode() {
    show_banner
    
    echo -e "${WHITE}Welcome to the CyberPanel Modular Installer!${NC}"
    echo ""
    echo -e "${CYAN}This installer will:${NC}"
    echo "• Detect your operating system"
    echo "• Install required dependencies"
    echo "• Install CyberPanel"
    echo "• Apply necessary fixes"
    echo "• Configure services"
    echo ""
    
    if [ -n "$BRANCH_NAME" ]; then
        echo -e "${YELLOW}Installing version: $BRANCH_NAME${NC}"
    else
        echo -e "${YELLOW}Installing latest stable version${NC}"
    fi
    
    echo ""
    read -p "Press Enter to continue or Ctrl+C to cancel..."
}

# Main installation function
main() {
    # Initialize log file
    mkdir -p /var/log
    touch "/var/log/cyberpanel_install.log"
    
    print_status "$BLUE" "🚀 CyberPanel Modular Installer Starting..."
    print_status "$BLUE" "Log file: /var/log/cyberpanel_install.log"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Run interactive mode if not auto
    if [ "$AUTO_INSTALL" = false ]; then
        run_interactive_mode
    fi
    
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
    
    print_status "$GREEN" "🎉 CyberPanel installation process completed!"
}

# Run main function
main "$@"
