#!/bin/bash

# Debian-based OS Dependencies Module
# Handles Ubuntu and Debian distributions
# Max 500 lines - Current: ~250 lines

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEBIAN-DEPS] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [DEBIAN-DEPS] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to update package lists
update_package_lists() {
    print_status "$BLUE" "Updating package lists..."
    
    apt update -qq 2>/dev/null || {
        print_status "$YELLOW" "Package list update failed, continuing..."
    }
    
    print_status "$GREEN" "✅ Package lists updated"
}

# Function to install essential packages
install_essential_packages() {
    local os_version=$1
    
    print_status "$BLUE" "Installing essential packages..."
    
    # Common essential packages for all Debian variants (conntrack for firewall/SSH security connection termination)
    local essential_packages="curl wget git unzip tar gzip bzip2 conntrack"
    
    apt install -y -qq $essential_packages 2>/dev/null || {
        print_status "$YELLOW" "Some essential packages failed to install, continuing..."
    }
    
    print_status "$GREEN" "✅ Essential packages installed"
}

# Function to install development tools
install_dev_tools() {
    local os_version=$1
    
    print_status "$BLUE" "Installing development tools..."
    
    # Development tools package group
    local dev_packages="build-essential gcc g++ make python3-dev python3-pip"
    
    apt install -y -qq $dev_packages 2>/dev/null || {
        print_status "$YELLOW" "Some development tools failed to install, continuing..."
    }

    # Optional Python 3.11 for CyberCP venv when default python3 is below 3.10 (e.g. Ubuntu 20.04, Debian 11)
    case $os_version in
        "Ubuntu2004"|"Ubuntu2204"|"Debian11"|"Debian12")
            apt install -y -qq python3.11 python3.11-venv python3.11-dev 2>/dev/null || print_status "$YELLOW" "python3.11 not available from apt, skipping..."
            ;;
    esac
    
    print_status "$GREEN" "✅ Development tools installed"
}

# Function to install core dependencies
install_core_deps() {
    local os_version=$1
    
    print_status "$BLUE" "Installing core dependencies..."
    
    # Core packages for CyberPanel
    local core_packages="imagemagick php-gd libicu-dev libonig-dev"
    
    # OS-specific packages
    case $os_version in
        "Ubuntu1804"|"Ubuntu2004"|"Ubuntu2010")
            # Ubuntu 18.04, 20.04, 20.10
            apt install -y -qq $core_packages aspell libc-client-dev 2>/dev/null || {
                print_status "$YELLOW" "Some core packages not available, trying alternatives..."
                apt install -y -qq $core_packages 2>/dev/null || true
            }
            ;;
        "Ubuntu2204"|"Ubuntu2404"|"Ubuntu24043")
            # Ubuntu 22.04, 24.04, 24.04.3
            apt install -y -qq $core_packages 2>/dev/null || {
                print_status "$YELLOW" "Some core packages not available, trying alternatives..."
                apt install -y -qq imagemagick php-gd libicu-dev libonig-dev 2>/dev/null || true
            }
            # Try to install aspell and libc-client separately
            apt install -y -qq aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
            apt install -y -qq libc-client-dev 2>/dev/null || print_status "$YELLOW" "libc-client-dev not available, skipping..."
            ;;
        "Debian11"|"Debian12"|"Debian13")
            # Debian 11, 12, 13
            apt install -y -qq $core_packages 2>/dev/null || {
                print_status "$YELLOW" "Some core packages not available, trying alternatives..."
                apt install -y -qq imagemagick php-gd libicu-dev libonig-dev 2>/dev/null || true
            }
            # Try to install aspell and libc-client separately
            apt install -y -qq aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
            apt install -y -qq libc-client-dev 2>/dev/null || print_status "$YELLOW" "libc-client-dev not available, skipping..."
            ;;
    esac
    
    print_status "$GREEN" "✅ Core dependencies installed"
}

# Function to install PHP dependencies
install_php_deps() {
    local os_version=$1
    
    print_status "$BLUE" "Installing PHP dependencies..."
    
    # PHP-related packages
    local php_packages="php-cli php-common php-mysql php-curl php-gd php-mbstring php-xml php-zip"
    
    apt install -y -qq $php_packages 2>/dev/null || {
        print_status "$YELLOW" "Some PHP packages not available, continuing..."
    }
    
    print_status "$GREEN" "✅ PHP dependencies installed"
}

# Function to install additional packages
install_additional_packages() {
    local os_version=$1
    
    print_status "$BLUE" "Installing additional packages..."
    
    # Additional packages that might be needed
    local additional_packages="openssl libssl-dev zlib1g-dev libxml2-dev libcurl4-openssl-dev"
    
    apt install -y -qq $additional_packages 2>/dev/null || {
        print_status "$YELLOW" "Some additional packages not available, continuing..."
    }
    
    print_status "$GREEN" "✅ Additional packages installed"
}

# Function to configure repositories
configure_repositories() {
    local os_version=$1
    
    print_status "$BLUE" "Configuring repositories..."
    
    case $os_version in
        "Ubuntu1804"|"Ubuntu2004"|"Ubuntu2010"|"Ubuntu2204"|"Ubuntu2404"|"Ubuntu24043")
            # Ubuntu repositories are usually already configured
            print_status "$GREEN" "✅ Ubuntu repositories configured"
            ;;
        "Debian11"|"Debian12"|"Debian13")
            # Debian repositories are usually already configured
            print_status "$GREEN" "✅ Debian repositories configured"
            ;;
    esac
}

# Function to verify dependencies
verify_dependencies() {
    print_status "$BLUE" "Verifying installed dependencies..."
    
    local required_packages="curl wget python3"
    local missing_packages=""
    
    for package in $required_packages; do
        if ! dpkg -l | grep -q "^ii  $package "; then
            missing_packages="$missing_packages $package"
        fi
    done
    
    if [ -n "$missing_packages" ]; then
        print_status "$YELLOW" "Missing packages:$missing_packages"
        print_status "$YELLOW" "Attempting to install missing packages..."
        apt install -y -qq $missing_packages 2>/dev/null || true
    else
        print_status "$GREEN" "✅ All required dependencies are installed"
    fi
}

# Main function to install all dependencies
install_debian_dependencies() {
    local server_os=$1
    
    print_status "$BLUE" "🚀 Installing Debian-based OS dependencies for $server_os..."
    
    # Update package lists
    update_package_lists
    
    # Configure repositories
    configure_repositories "$server_os"
    
    # Install essential packages
    install_essential_packages "$server_os"
    
    # Install development tools
    install_dev_tools "$server_os"
    
    # Install core dependencies
    install_core_deps "$server_os"
    
    # Install PHP dependencies
    install_php_deps "$server_os"
    
    # Install additional packages
    install_additional_packages "$server_os"
    
    # Verify dependencies
    verify_dependencies
    
    print_status "$GREEN" "✅ Debian dependencies installation completed"
    return 0
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <server_os>"
        echo "Example: $0 Ubuntu2204"
        exit 1
    fi
    
    install_debian_dependencies "$1"
fi
