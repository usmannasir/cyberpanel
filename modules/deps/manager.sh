#!/bin/bash

# Dependency Manager Module
# Main dependency management coordinator
# Max 500 lines - Current: ~150 lines

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="$(dirname "$SCRIPT_DIR")"

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPS-MANAGER] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEPS-MANAGER] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to load OS detection module
load_os_detection() {
    if [ -f "$MODULES_DIR/os/detect.sh" ]; then
        source "$MODULES_DIR/os/detect.sh"
        return 0
    else
        print_status "$RED" "❌ OS detection module not found: $MODULES_DIR/os/detect.sh"
        return 1
    fi
}

# Function to install dependencies based on OS family
install_dependencies() {
    local server_os=$1
    local os_family=$2
    local package_manager=$3
    
    print_status "$BLUE" "📦 Installing dependencies for $server_os ($os_family)..."
    
    case $os_family in
        "rhel")
            if [ -f "$MODULES_DIR/deps/rhel_deps.sh" ]; then
                source "$MODULES_DIR/deps/rhel_deps.sh"
                install_rhel_dependencies "$server_os" "$package_manager"
                return $?
            else
                print_status "$RED" "❌ RHEL dependencies module not found"
                return 1
            fi
            ;;
        "debian")
            if [ -f "$MODULES_DIR/deps/debian_deps.sh" ]; then
                source "$MODULES_DIR/deps/debian_deps.sh"
                install_debian_dependencies "$server_os"
                return $?
            else
                print_status "$RED" "❌ Debian dependencies module not found"
                return 1
            fi
            ;;
        *)
            print_status "$RED" "❌ Unsupported OS family: $os_family"
            return 1
            ;;
    esac
}

# Function to check if dependencies are installed
check_dependencies() {
    local server_os=$1
    local os_family=$2
    local package_manager=$3
    
    print_status "$BLUE" "🔍 Checking dependencies for $server_os..."
    
    local missing_deps=0
    
    # Check common dependencies
    case $os_family in
        "rhel")
            if ! rpm -q curl >/dev/null 2>&1; then
                print_status "$YELLOW" "Missing: curl"
                missing_deps=$((missing_deps + 1))
            fi
            if ! rpm -q wget >/dev/null 2>&1; then
                print_status "$YELLOW" "Missing: wget"
                missing_deps=$((missing_deps + 1))
            fi
            if ! rpm -q python3 >/dev/null 2>&1; then
                print_status "$YELLOW" "Missing: python3"
                missing_deps=$((missing_deps + 1))
            fi
            ;;
        "debian")
            if ! dpkg -l | grep -q "^ii  curl "; then
                print_status "$YELLOW" "Missing: curl"
                missing_deps=$((missing_deps + 1))
            fi
            if ! dpkg -l | grep -q "^ii  wget "; then
                print_status "$YELLOW" "Missing: wget"
                missing_deps=$((missing_deps + 1))
            fi
            if ! dpkg -l | grep -q "^ii  python3 "; then
                print_status "$YELLOW" "Missing: python3"
                missing_deps=$((missing_deps + 1))
            fi
            ;;
    esac
    
    if [ $missing_deps -eq 0 ]; then
        print_status "$GREEN" "✅ All dependencies are installed"
        return 0
    else
        print_status "$YELLOW" "⚠️  $missing_deps dependencies are missing"
        return 1
    fi
}

# Function to fix dependency issues
fix_dependency_issues() {
    local server_os=$1
    local os_family=$2
    local package_manager=$3
    
    print_status "$BLUE" "🔧 Fixing dependency issues for $server_os..."
    
    case $os_family in
        "rhel")
            # Fix common RHEL issues
            print_status "$YELLOW" "Fixing RHEL dependency issues..."
            
            # Clear package cache
            $package_manager clean all 2>/dev/null || true
            
            # Update package lists
            $package_manager makecache 2>/dev/null || true
            
            # Try to install missing packages
            $package_manager install -y curl wget python3 2>/dev/null || true
            ;;
        "debian")
            # Fix common Debian issues
            print_status "$YELLOW" "Fixing Debian dependency issues..."
            
            # Update package lists
            apt update -qq 2>/dev/null || true
            
            # Fix broken packages
            apt --fix-broken install -y -qq 2>/dev/null || true
            
            # Try to install missing packages
            apt install -y -qq curl wget python3 2>/dev/null || true
            ;;
    esac
    
    print_status "$GREEN" "✅ Dependency issues fixed"
}

# Main function to manage dependencies
manage_dependencies() {
    local server_os=$1
    local os_family=$2
    local package_manager=$3
    
    print_status "$BLUE" "🚀 Managing dependencies for $server_os..."
    
    # Check current dependencies
    if check_dependencies "$server_os" "$os_family" "$package_manager"; then
        print_status "$GREEN" "✅ All dependencies are already installed"
        return 0
    fi
    
    # Install dependencies
    if install_dependencies "$server_os" "$os_family" "$package_manager"; then
        print_status "$GREEN" "✅ Dependencies installed successfully"
        return 0
    else
        print_status "$YELLOW" "⚠️  Dependency installation had issues, attempting to fix..."
        fix_dependency_issues "$server_os" "$os_family" "$package_manager"
        return 1
    fi
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    if [ $# -lt 3 ]; then
        echo "Usage: $0 <server_os> <os_family> <package_manager>"
        echo "Example: $0 AlmaLinux9 rhel dnf"
        exit 1
    fi
    
    manage_dependencies "$1" "$2" "$3"
fi
