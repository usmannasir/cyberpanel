#!/bin/bash

# Enhanced CyberPanel Installer with Modular Architecture
# This installer uses modules for better organization and maintainability
# Each module is kept under 500 lines for easy management

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="$SCRIPT_DIR/modules"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
SERVER_OS=""
OS_FAMILY=""
PACKAGE_MANAGER=""
ARCHITECTURE=""
BRANCH_NAME=""

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MAIN-INSTALLER] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [MAIN-INSTALLER] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to load modules
load_module() {
    local module_path="$1"
    local module_name="$2"
    
    if [ -f "$module_path" ]; then
        source "$module_path"
        print_status "$GREEN" "✅ Loaded module: $module_name"
        return 0
    else
        print_status "$RED" "❌ Module not found: $module_path"
        return 1
    fi
}

# Function to initialize modules
initialize_modules() {
    print_status "$BLUE" "🔧 Initializing modules..."
    
    # Load OS detection module
    if ! load_module "$MODULES_DIR/os/detect.sh" "OS Detection"; then
        print_status "$RED" "❌ Failed to load OS detection module"
                exit 1
fi

    # Load dependency manager module
    if ! load_module "$MODULES_DIR/deps/manager.sh" "Dependency Manager"; then
        print_status "$RED" "❌ Failed to load dependency manager module"
        exit 1
    fi
    
    # Load CyberPanel installer module
    if ! load_module "$MODULES_DIR/install/cyberpanel_installer.sh" "CyberPanel Installer"; then
        print_status "$RED" "❌ Failed to load CyberPanel installer module"
        exit 1
    fi
    
    # Load fixes module
    if ! load_module "$MODULES_DIR/fixes/cyberpanel_fixes.sh" "CyberPanel Fixes"; then
        print_status "$RED" "❌ Failed to load fixes module"
        exit 1
    fi
    
    print_status "$GREEN" "✅ All modules loaded successfully"
}

# Function to detect operating system
detect_operating_system() {
    print_status "$BLUE" "🔍 Detecting operating system..."
    
    if detect_os; then
        # Get OS information
        eval $(get_os_info)
        print_status "$GREEN" "✅ OS detected: $SERVER_OS ($OS_FAMILY)"
        print_status "$GREEN" "✅ Package manager: $PACKAGE_MANAGER"
        print_status "$GREEN" "✅ Architecture: $ARCHITECTURE"
        return 0
    else
        print_status "$RED" "❌ Failed to detect operating system"
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "$BLUE" "📦 Installing dependencies..."
    
    if manage_dependencies "$SERVER_OS" "$OS_FAMILY" "$PACKAGE_MANAGER"; then
        print_status "$GREEN" "✅ Dependencies installed successfully"
        return 0
    else
        print_status "$YELLOW" "⚠️  Dependency installation had issues, continuing..."
        return 1
    fi
}

# Function to install CyberPanel
install_cyberpanel_main() {
    print_status "$BLUE" "🚀 Installing CyberPanel..."
    
    # Prepare installation arguments
    local install_args=()
    for arg in "$@"; do
        install_args+=("$arg")
    done
    
    if install_cyberpanel_main "$SERVER_OS" "$BRANCH_NAME" "${install_args[@]}"; then
        print_status "$GREEN" "✅ CyberPanel installed successfully"
        return 0
    else
        print_status "$RED" "❌ CyberPanel installation failed"
        return 1
    fi
}

# Function to apply fixes
apply_fixes() {
    print_status "$BLUE" "🔧 Applying installation fixes..."
    
    if apply_cyberpanel_fixes "$PACKAGE_MANAGER"; then
        print_status "$GREEN" "✅ All fixes applied successfully"
        return 0
    else
        print_status "$YELLOW" "⚠️  Some fixes had issues, but continuing..."
        return 1
    fi
}

# Function to show firewall information
show_firewall_info() {
    echo ""
    echo "🔥 FIREWALL CONFIGURATION REQUIRED:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    echo "If your provider has a network-level firewall, please ensure these ports are open:"
    echo ""
    echo "• TCP 8090 - CyberPanel Web Interface"
    echo "• TCP 80, 443 - Web Server (HTTP/HTTPS)"
    echo "• TCP 7080 - LiteSpeed Admin Console"
    echo "• TCP 21, 40110-40210 - FTP Service"
    echo "• TCP 25, 587, 465, 110, 143, 993 - Mail Services"
    echo "• TCP/UDP 53 - DNS Service"
    echo ""
}

# Function to show final restart prompt
show_restart_prompt() {
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                                               ║"
    echo "║                    🔄 SERVER RESTART PROMPT 🔄                                                              ║"
    echo "║                                                                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    print_status "$GREEN" "✅ Installation completed! Safe to restart server."
    echo "Would you like to restart your server now? [Y/n]: "
    
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]|"")
            print_status "$GREEN" "🔄 Restarting server..."
            shutdown -r now
            ;;
        *)
            print_status "$BLUE" "Server restart cancelled. You can restart manually when ready."
            ;;
    esac
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
                set -x
                shift
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -b, --branch BRANCH    Install from specific branch/commit"
                echo "  --debug               Enable debug mode"
                echo "  -h, --help            Show this help message"
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
    
    print_status "$BLUE" "🚀 Enhanced CyberPanel Installer Starting..."
    print_status "$BLUE" "Log file: /var/log/cyberpanel_install.log"
    
    # Parse command line arguments
    parse_arguments "$@"
    
    # Initialize modules
    initialize_modules
    
    # Detect operating system
    detect_operating_system
    
    # Install dependencies
    install_dependencies
    
    # Install CyberPanel
    install_cyberpanel_main "$@"
    
    # Apply fixes
    apply_fixes
    
    # Show firewall information
    show_firewall_info
    
    # Show restart prompt
    show_restart_prompt
    
    print_status "$GREEN" "🎉 CyberPanel installation process completed!"
}

# Run main function
main "$@"