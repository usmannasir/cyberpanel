#!/bin/bash

# Enhanced CyberPanel Installer with Modular Architecture
# This installer uses modules for better organization and maintainability
# Each module is kept under 500 lines for easy management

# Note: We use 'set -e' carefully - some operations need to handle failures gracefully
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
    # Try multiple locations if /tmp is full
    TEMP_DIR=""
    early_log "Checking available disk space..."
    
    # Try to clean up old temp directories first
    rm -rf /tmp/cyberpanel-installer-* 2>/dev/null || true
    rm -rf /var/tmp/cyberpanel-installer-* 2>/dev/null || true
    
    # Try multiple temp locations (disable set -e for this section)
    set +e
    for temp_location in "/tmp/cyberpanel-installer-$$" "/var/tmp/cyberpanel-installer-$$" "$HOME/cyberpanel-installer-$$" "/root/cyberpanel-installer-$$"; do
        if mkdir -p "$temp_location" 2>/dev/null; then
            TEMP_DIR="$temp_location"
            early_log "Using temporary directory: $TEMP_DIR"
            break
        fi
    done
    set -e
    
    # If we still don't have a temp dir, skip git clone and use fallback
    if [ -z "$TEMP_DIR" ]; then
        early_log "⚠️  Cannot create temporary directory (disk may be full)"
        early_log "Skipping git clone, using fallback installer directly..."
        # Skip to fallback installer
        TEMP_DIR=""
    fi
    
    # Only attempt git clone if we have a temp directory
    if [ -n "$TEMP_DIR" ]; then
        early_log "📦 Cloning CyberPanel repository (branch: $BRANCH_NAME)..."
        early_log "This may take a minute depending on your connection speed..."
        
        # Try git clone with timeout and better error handling
        GIT_CLONE_SUCCESS=false
        
        if command -v timeout >/dev/null 2>&1; then
            if timeout 180 git clone --depth 1 --branch "$BRANCH_NAME" https://github.com/master3395/cyberpanel.git "$TEMP_DIR/cyberpanel" >/tmp/git-clone.log 2>&1; then
                GIT_CLONE_SUCCESS=true
            fi
        else
            # No timeout command, try without timeout
            if git clone --depth 1 --branch "$BRANCH_NAME" https://github.com/master3395/cyberpanel.git "$TEMP_DIR/cyberpanel" >/tmp/git-clone.log 2>&1; then
                GIT_CLONE_SUCCESS=true
            fi
        fi
        
        # Verify clone was successful and structure is valid
        if [ "$GIT_CLONE_SUCCESS" = true ] && [ -d "$TEMP_DIR/cyberpanel" ] && [ -f "$TEMP_DIR/cyberpanel/install.sh" ] && [ -d "$TEMP_DIR/cyberpanel/modules" ]; then
            SCRIPT_DIR="$TEMP_DIR/cyberpanel"
            cd "$SCRIPT_DIR"
            early_log "✅ Repository cloned successfully"
        else
            # Git clone failed or structure invalid, use fallback
            GIT_ERROR=$(tail -3 /tmp/git-clone.log 2>/dev/null | tr '\n' ' ')
            early_log "⚠️  Git clone failed or incomplete"
            if [ -n "$GIT_ERROR" ]; then
                early_log "Last error: $GIT_ERROR"
            fi
            early_log "Falling back to legacy installer..."
            rm -rf "$TEMP_DIR/cyberpanel" 2>/dev/null || true
            TEMP_DIR=""  # Clear TEMP_DIR to trigger fallback
        fi
    fi
    
    # If git clone failed or we couldn't create temp dir, use fallback
    if [ -z "$TEMP_DIR" ] || [ ! -d "$TEMP_DIR/cyberpanel" ] || [ ! -f "$TEMP_DIR/cyberpanel/install.sh" ]; then
        # Fallback: try to download install.sh from the old method
        early_log "Using fallback installer method..."
        OUTPUT=$(cat /etc/*release 2>/dev/null || echo "")
        if echo "$OUTPUT" | grep -qE "(CentOS|AlmaLinux|CloudLinux|Rocky)" ; then
            SERVER_OS="CentOS8"
            yum install -y -q curl wget 2>/dev/null || dnf install -y -q curl wget 2>/dev/null || true
        elif echo "$OUTPUT" | grep -qE "Ubuntu" ; then
            SERVER_OS="Ubuntu"
            apt install -y -qq wget curl 2>/dev/null || true
        else
            early_log "❌ Unable to detect OS for fallback installer"
            exit 1
        fi
        
        # Try multiple locations for fallback script
        FALLBACK_SCRIPT=""
        for fallback_location in "/tmp/cyberpanel.sh" "/var/tmp/cyberpanel.sh" "$HOME/cyberpanel.sh"; do
            rm -f "$fallback_location" 2>/dev/null || true
            if curl --silent -o "$fallback_location" "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null || \
               wget -q -O "$fallback_location" "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null; then
                if [ -f "$fallback_location" ]; then
                    FALLBACK_SCRIPT="$fallback_location"
                    chmod +x "$FALLBACK_SCRIPT"
                    break
                fi
            fi
        done
        
        if [ -n "$FALLBACK_SCRIPT" ] && [ -f "$FALLBACK_SCRIPT" ]; then
            early_log "✅ Fallback installer downloaded, executing..."
            exec "$FALLBACK_SCRIPT" "$@"
        else
            early_log "❌ Failed to download fallback installer"
            early_log "Please free up disk space or check your internet connection"
            exit 1
        fi
    fi
    fi  # Close the if [ -n "$TEMP_DIR" ] block
fi  # Close the if [[ "$SCRIPT_DIR" == /dev/fd/* ]] block

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
        # Get OS information using get_os_info() to ensure we capture the values
        # This outputs variable assignments that we can eval
        eval $(get_os_info)
        
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
    
    # Debug: Show current variable values
    print_status "$YELLOW" "DEBUG: SERVER_OS='$SERVER_OS', OS_FAMILY='$OS_FAMILY', PACKAGE_MANAGER='$PACKAGE_MANAGER'"
    
    # Ensure variables are set (they should be from detect_operating_system)
    if [ -z "$SERVER_OS" ] || [ -z "$OS_FAMILY" ] || [ -z "$PACKAGE_MANAGER" ]; then
        print_status "$YELLOW" "⚠️  OS variables not set, re-detecting..."
        # Try to get them again
        if detect_os; then
            # Variables should be set by detect_os() in the sourced module
            export SERVER_OS OS_FAMILY PACKAGE_MANAGER ARCHITECTURE
            print_status "$GREEN" "✅ Re-detected: SERVER_OS=$SERVER_OS, OS_FAMILY=$OS_FAMILY, PACKAGE_MANAGER=$PACKAGE_MANAGER"
        else
            print_status "$RED" "❌ Failed to detect OS for dependency installation"
            return 1
        fi
    fi
    
    # Verify variables one more time before calling
    if [ -z "$SERVER_OS" ] || [ -z "$OS_FAMILY" ] || [ -z "$PACKAGE_MANAGER" ]; then
        print_status "$RED" "❌ OS variables still not set after re-detection"
        return 1
    fi
    
    print_status "$BLUE" "Calling manage_dependencies with: SERVER_OS='$SERVER_OS', OS_FAMILY='$OS_FAMILY', PACKAGE_MANAGER='$PACKAGE_MANAGER'"
    
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

# Function to check disk space
check_disk_space() {
    local required_gb=10  # Minimum 10GB required
    local root_available_gb=0
    
    # Get available space on root filesystem
    if command -v df >/dev/null 2>&1; then
        root_available_gb=$(df -BG / | awk 'NR==2 {print $4}' | sed 's/G//' | cut -d. -f1)
        if [ -z "$root_available_gb" ] || [ "$root_available_gb" = "" ]; then
            # Try alternative method
            root_available_gb=$(df -BG / | tail -1 | awk '{print $4}' | sed 's/G//' | cut -d. -f1)
        fi
    fi
    
    # If we couldn't get the value, try without -BG flag
    if [ -z "$root_available_gb" ] || ! [[ "$root_available_gb" =~ ^[0-9]+$ ]]; then
        root_available_gb=$(df / | awk 'NR==2 {print $4}' | awk '{printf "%.0f", $1/1024/1024}')
    fi
    
    print_status "$BLUE" "💾 Checking disk space..."
    print_status "$BLUE" "   Required: ${required_gb}GB minimum"
    
    if [[ "$root_available_gb" =~ ^[0-9]+$ ]] && [ "$root_available_gb" -ge "$required_gb" ]; then
        print_status "$GREEN" "   Available: ${root_available_gb}GB (✅ Sufficient)"
        return 0
    elif [[ "$root_available_gb" =~ ^[0-9]+$ ]]; then
        print_status "$YELLOW" "   Available: ${root_available_gb}GB (⚠️  Less than ${required_gb}GB recommended)"
        print_status "$YELLOW" "   Installation may fail if disk space runs out"
        return 1
    else
        print_status "$YELLOW" "   Could not determine available disk space"
        print_status "$YELLOW" "   Please ensure at least ${required_gb}GB is available"
        return 1
    fi
}

# Main installation function
main() {
    # Initialize log file
    mkdir -p /var/log
    touch "/var/log/cyberpanel_install.log"
    
    print_status "$BLUE" "🚀 Enhanced CyberPanel Installer Starting..."
    print_status "$BLUE" "Log file: /var/log/cyberpanel_install.log"
    
    # Check disk space before proceeding
    check_disk_space
    
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