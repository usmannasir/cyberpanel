#!/bin/bash

# Enhanced CyberPanel Installer with Modular Architecture
# This installer uses modules for better organization and maintainability
# Each module is kept under 500 lines for easy management

set -e

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Early logging function (before main functions are defined)
early_log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Check if script is being executed via curl/wget (SCRIPT_DIR will be /dev/fd/...)
# In that case, we need to clone the repository first
if [[ "$SCRIPT_DIR" == /dev/fd/* ]] || [[ ! -d "$SCRIPT_DIR/modules" ]]; then
    # Script is being executed via curl/wget, need to clone repo first
    early_log "📥 Detected curl/wget execution - cloning repository..."
    
    # Determine branch from arguments or use default
    BRANCH_NAME="v2.5.5-dev"
    ARGS=("$@")
    for i in "${!ARGS[@]}"; do
        if [[ "${ARGS[i]}" == "-b" ]] || [[ "${ARGS[i]}" == "--branch" ]]; then
            if [[ -n "${ARGS[i+1]}" ]]; then
                BRANCH_NAME="${ARGS[i+1]}"
            fi
            break
        fi
    done
    
    # Clone repository to temporary directory
    TEMP_DIR="/tmp/cyberpanel-installer-$$"
    mkdir -p "$TEMP_DIR"
    
    early_log "📦 Cloning CyberPanel repository (branch: $BRANCH_NAME)..."
    early_log "This may take a minute depending on your connection speed..."
    
    # Try git clone with timeout and better error handling
    if timeout 120 git clone --depth 1 --branch "$BRANCH_NAME" https://github.com/master3395/cyberpanel.git "$TEMP_DIR/cyberpanel" 2>&1 | tee /tmp/git-clone.log; then
        if [ -d "$TEMP_DIR/cyberpanel" ] && [ -f "$TEMP_DIR/cyberpanel/install.sh" ]; then
            SCRIPT_DIR="$TEMP_DIR/cyberpanel"
            cd "$SCRIPT_DIR"
            early_log "✅ Repository cloned successfully"
        else
            early_log "⚠️  Git clone completed but repository structure is invalid"
            early_log "Falling back to legacy installer..."
            rm -rf "$TEMP_DIR/cyberpanel"
        fi
    else
        GIT_ERROR=$(cat /tmp/git-clone.log 2>/dev/null | tail -5)
        early_log "⚠️  Git clone failed"
        if [ -n "$GIT_ERROR" ]; then
            early_log "Error details: $GIT_ERROR"
        fi
        early_log "Falling back to legacy installer..."
        rm -rf "$TEMP_DIR/cyberpanel" 2>/dev/null || true
    fi
    
    # If we reach here, git clone failed or was invalid, use fallback
    if [ ! -d "$SCRIPT_DIR/modules" ]; then
        OUTPUT=$(cat /etc/*release 2>/dev/null || echo "")
        if echo "$OUTPUT" | grep -qE "(CentOS|AlmaLinux|CloudLinux|Rocky)" ; then
            SERVER_OS="CentOS8"
            yum install -y -q curl wget 2>/dev/null || true
        elif echo "$OUTPUT" | grep -qE "Ubuntu" ; then
            SERVER_OS="Ubuntu"
            apt install -y -qq wget curl 2>/dev/null || true
        else
            early_log "❌ Unable to detect OS for fallback installer"
            exit 1
        fi
        
        rm -f /tmp/cyberpanel.sh
        curl --silent -o /tmp/cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null || \
        wget -q -O /tmp/cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null
        chmod +x /tmp/cyberpanel.sh
        exec /tmp/cyberpanel.sh "$@"
    fi
fi

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
        # Variables are set by detect_os() in the sourced module
        # Export them to ensure they're available to all functions
        export SERVER_OS OS_FAMILY PACKAGE_MANAGER ARCHITECTURE
        print_status "$GREEN" "✅ OS detected: $SERVER_OS ($OS_FAMILY)"
        print_status "$GREEN" "✅ Package manager: $PACKAGE_MANAGER"
        print_status "$GREEN" "✅ Architecture: $ARCHITECTURE"
        
        # Verify variables are set
        if [ -z "$SERVER_OS" ] || [ -z "$OS_FAMILY" ] || [ -z "$PACKAGE_MANAGER" ]; then
            print_status "$RED" "❌ OS variables not properly set after detection"
            return 1
        fi
        return 0
    else
        print_status "$RED" "❌ Failed to detect operating system"
        exit 1
    fi
}

# Function to install dependencies
install_dependencies() {
    print_status "$BLUE" "📦 Installing dependencies..."
    
    # Ensure variables are set (they should be from detect_operating_system)
    if [ -z "$SERVER_OS" ] || [ -z "$OS_FAMILY" ] || [ -z "$PACKAGE_MANAGER" ]; then
        print_status "$RED" "❌ OS variables not set. SERVER_OS=$SERVER_OS, OS_FAMILY=$OS_FAMILY, PACKAGE_MANAGER=$PACKAGE_MANAGER"
        # Try to get them again
        if detect_os; then
            eval $(get_os_info)
            export SERVER_OS OS_FAMILY PACKAGE_MANAGER ARCHITECTURE
        else
            print_status "$RED" "❌ Failed to detect OS for dependency installation"
            return 1
        fi
    fi
    
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