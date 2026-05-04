#!/bin/bash

# RHEL-based OS Dependencies Module
# Handles CentOS, AlmaLinux, Rocky Linux, RHEL, CloudLinux, openEuler
# Max 500 lines - Current: ~300 lines

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [RHEL-DEPS] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [RHEL-DEPS] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to install EPEL repository
install_epel() {
    local package_manager=$1
    local os_version=$2
    
    print_status "$BLUE" "Installing EPEL repository..."
    
    case $os_version in
        "CentOS7"|"AlmaLinux8"|"RockyLinux8"|"RHEL8"|"CloudLinux7"|"CloudLinux8"|"openEuler2003")
            $package_manager install -y epel-release 2>/dev/null || {
                print_status "$YELLOW" "EPEL not available via $package_manager, trying alternative method..."
                yum install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm 2>/dev/null || true
            }
            ;;
        "CentOS8"|"CentOSStream8"|"AlmaLinux9"|"RockyLinux9"|"RHEL9"|"CloudLinux9"|"openEuler2203"|"openEuler2403")
            $package_manager install -y epel-release 2>/dev/null || {
                print_status "$YELLOW" "EPEL not available via $package_manager, trying alternative method..."
                dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-8.noarch.rpm 2>/dev/null || true
            }
            ;;
        "CentOS9"|"CentOSStream9"|"AlmaLinux10")
            $package_manager install -y epel-release 2>/dev/null || {
                print_status "$YELLOW" "EPEL not available via $package_manager, trying alternative method..."
                dnf install -y https://dl.fedoraproject.org/pub/epel/epel-release-latest-9.noarch.rpm 2>/dev/null || true
            }
            ;;
    esac
    
    print_status "$GREEN" "✅ EPEL repository installed"
}

# Function to install development tools
install_dev_tools() {
    local package_manager=$1
    
    print_status "$BLUE" "Installing development tools..."
    
    case $package_manager in
        "yum")
            yum groupinstall -y 'Development Tools' 2>/dev/null || {
                print_status "$YELLOW" "Development Tools group not available, installing individual packages..."
                yum install -y gcc gcc-c++ make kernel-devel 2>/dev/null || true
            }
            ;;
        "dnf")
            dnf groupinstall -y 'Development Tools' 2>/dev/null || {
                print_status "$YELLOW" "Development Tools group not available, installing individual packages..."
                dnf install -y gcc gcc-c++ make kernel-devel 2>/dev/null || true
            }
            ;;
    esac
    
    print_status "$GREEN" "✅ Development tools installed"
}

# Function to install core dependencies
install_core_deps() {
    local package_manager=$1
    local os_version=$2
    
    print_status "$BLUE" "Installing core dependencies..."
    
    # Common packages for all RHEL variants
    local common_packages="ImageMagick gd libicu oniguruma python3 python3-pip python3-devel"
    
    # OS-specific packages
    case $os_version in
        "CentOS7"|"CloudLinux7")
            # CentOS 7 specific packages
            $package_manager install -y $common_packages aspell libc-client 2>/dev/null || {
                print_status "$YELLOW" "Some packages not available on CentOS 7, continuing..."
            }
            ;;
        "CentOS8"|"CentOSStream8"|"AlmaLinux8"|"RockyLinux8"|"RHEL8"|"CloudLinux8"|"openEuler2003")
            # CentOS 8 / RHEL 8 family
            $package_manager install -y $common_packages aspell libc-client-devel 2>/dev/null || {
                print_status "$YELLOW" "Some packages not available, trying alternatives..."
                $package_manager install -y $common_packages 2>/dev/null || true
            }
            ;;
        "CentOS9"|"CentOSStream9"|"AlmaLinux9"|"RockyLinux9"|"RHEL9"|"CloudLinux9"|"openEuler2203"|"openEuler2403")
            # CentOS 9 / RHEL 9 family
            $package_manager install -y $common_packages 2>/dev/null || {
                print_status "$YELLOW" "Some packages not available, trying alternatives..."
                $package_manager install -y ImageMagick gd libicu oniguruma python3 python3-pip python3-devel 2>/dev/null || true
            }
            $package_manager install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || print_status "$YELLOW" "python3.11 packages not available, skipping..."
            # Try to install aspell and libc-client separately
            $package_manager install -y aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
            $package_manager install -y libc-client-devel 2>/dev/null || print_status "$YELLOW" "libc-client-devel not available, skipping..."
            ;;
        "AlmaLinux10")
            # AlmaLinux 10 specific
            $package_manager install -y $common_packages 2>/dev/null || {
                print_status "$YELLOW" "Some packages not available, trying alternatives..."
                $package_manager install -y ImageMagick gd libicu oniguruma python3 python3-pip python3-devel 2>/dev/null || true
            }
            $package_manager install -y python3.11 python3.11-pip python3.11-devel 2>/dev/null || print_status "$YELLOW" "python3.11 packages not available, skipping..."
            ;;
    esac
    
    print_status "$GREEN" "✅ Core dependencies installed"
}

# Function to install additional packages
install_additional_packages() {
    local package_manager=$1
    local os_version=$2
    
    print_status "$BLUE" "Installing additional packages..."
    
    # Additional packages that might be needed (conntrack-tools for firewall/SSH security connection termination)
    local additional_packages="git wget curl unzip tar gzip bzip2 conntrack-tools"
    
    $package_manager install -y $additional_packages 2>/dev/null || {
        print_status "$YELLOW" "Some additional packages not available, continuing..."
    }
    
    # OS-specific additional packages
    case $os_version in
        "CentOS7"|"CloudLinux7")
            # CentOS 7 specific
            $package_manager install -y openssl-devel zlib-devel 2>/dev/null || true
            ;;
        "CentOS8"|"CentOSStream8"|"AlmaLinux8"|"RockyLinux8"|"RHEL8"|"CloudLinux8"|"openEuler2003")
            # CentOS 8 / RHEL 8 family
            $package_manager install -y openssl-devel zlib-devel 2>/dev/null || true
            ;;
        "CentOS9"|"CentOSStream9"|"AlmaLinux9"|"RockyLinux9"|"RHEL9"|"CloudLinux9"|"openEuler2203"|"openEuler2403")
            # CentOS 9 / RHEL 9 family
            $package_manager install -y openssl-devel zlib-devel 2>/dev/null || true
            ;;
    esac
    
    print_status "$GREEN" "✅ Additional packages installed"
}

# Function to verify dependencies
verify_dependencies() {
    local package_manager=$1
    
    print_status "$BLUE" "Verifying installed dependencies..."
    
    local required_packages="curl wget python3"
    local missing_packages=""
    
    for package in $required_packages; do
        if ! $package_manager list installed | grep -q "^$package\."; then
            missing_packages="$missing_packages $package"
        fi
    done
    
    if [ -n "$missing_packages" ]; then
        print_status "$YELLOW" "Missing packages:$missing_packages"
        print_status "$YELLOW" "Attempting to install missing packages..."
        $package_manager install -y $missing_packages 2>/dev/null || true
    else
        print_status "$GREEN" "✅ All required dependencies are installed"
    fi
}

# Main function to install all dependencies
install_rhel_dependencies() {
    local server_os=$1
    local package_manager=$2
    
    print_status "$BLUE" "🚀 Installing RHEL-based OS dependencies for $server_os..."
    
    # Install EPEL repository
    install_epel "$package_manager" "$server_os"
    
    # Install development tools
    install_dev_tools "$package_manager"
    
    # Install core dependencies
    install_core_deps "$package_manager" "$server_os"
    
    # Install additional packages
    install_additional_packages "$package_manager" "$server_os"
    
    # Verify dependencies
    verify_dependencies "$package_manager"
    
    print_status "$GREEN" "✅ RHEL dependencies installation completed"
    return 0
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    if [ $# -lt 2 ]; then
        echo "Usage: $0 <server_os> <package_manager>"
        echo "Example: $0 AlmaLinux9 dnf"
        exit 1
    fi
    
    install_rhel_dependencies "$1" "$2"
fi
