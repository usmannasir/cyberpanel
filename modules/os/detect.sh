#!/bin/bash

# OS Detection Module for CyberPanel Installer
# This module handles OS detection and basic package manager setup
# Max 500 lines - Current: ~200 lines

# Global variables
SERVER_OS=""
OS_FAMILY=""
PACKAGE_MANAGER=""
ARCHITECTURE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [OS-DETECT] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [OS-DETECT] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to detect system architecture
detect_architecture() {
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
    return 0
}

# Function to detect CentOS variants
detect_centos() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "CentOS Linux 7" ; then
        SERVER_OS="CentOS7"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: CentOS Linux 7"
        return 0
    elif echo $OUTPUT | grep -q "CentOS Linux 8" ; then
        SERVER_OS="CentOS8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: CentOS Linux 8"
        return 0
    elif echo $OUTPUT | grep -q "CentOS Linux 9" ; then
        SERVER_OS="CentOS9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: CentOS Linux 9"
        return 0
    elif echo $OUTPUT | grep -q "CentOS Stream 8" ; then
        SERVER_OS="CentOSStream8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: CentOS Stream 8"
        return 0
    elif echo $OUTPUT | grep -q "CentOS Stream 9" ; then
        SERVER_OS="CentOSStream9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: CentOS Stream 9"
        return 0
    fi
    return 1
}

# Function to detect AlmaLinux variants
detect_almalinux() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "AlmaLinux 8" ; then
        SERVER_OS="AlmaLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: AlmaLinux 8"
        return 0
    elif echo $OUTPUT | grep -q "AlmaLinux 9" ; then
        SERVER_OS="AlmaLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: AlmaLinux 9"
        return 0
    elif echo $OUTPUT | grep -q "AlmaLinux 10" ; then
        SERVER_OS="AlmaLinux10"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: AlmaLinux 10"
        return 0
    fi
    return 1
}

# Function to detect Rocky Linux variants
detect_rocky() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "Rocky Linux 8" ; then
        SERVER_OS="RockyLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: Rocky Linux 8"
        return 0
    elif echo $OUTPUT | grep -q "Rocky Linux 9" ; then
        SERVER_OS="RockyLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: Rocky Linux 9"
        return 0
    fi
    return 1
}

# Function to detect RHEL variants
detect_rhel() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "Red Hat Enterprise Linux 8" ; then
        SERVER_OS="RHEL8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: Red Hat Enterprise Linux 8"
        return 0
    elif echo $OUTPUT | grep -q "Red Hat Enterprise Linux 9" ; then
        SERVER_OS="RHEL9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: Red Hat Enterprise Linux 9"
        return 0
    fi
    return 1
}

# Function to detect CloudLinux variants
detect_cloudlinux() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "CloudLinux 7" ; then
        SERVER_OS="CloudLinux7"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: CloudLinux 7"
        return 0
    elif echo $OUTPUT | grep -q "CloudLinux 8" ; then
        SERVER_OS="CloudLinux8"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: CloudLinux 8"
        return 0
    elif echo $OUTPUT | grep -q "CloudLinux 9" ; then
        SERVER_OS="CloudLinux9"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="dnf"
        print_status "$GREEN" "Detected: CloudLinux 9"
        return 0
    fi
    return 1
}

# Function to detect Ubuntu variants
detect_ubuntu() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "Ubuntu 18.04" ; then
        SERVER_OS="Ubuntu1804"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 18.04"
        return 0
    elif echo $OUTPUT | grep -q "Ubuntu 20.04" ; then
        SERVER_OS="Ubuntu2004"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 20.04"
        return 0
    elif echo $OUTPUT | grep -q "Ubuntu 20.10" ; then
        SERVER_OS="Ubuntu2010"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 20.10"
        return 0
    elif echo $OUTPUT | grep -q "Ubuntu 22.04" ; then
        SERVER_OS="Ubuntu2204"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 22.04"
        return 0
    elif echo $OUTPUT | grep -q "Ubuntu 24.04" ; then
        SERVER_OS="Ubuntu2404"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 24.04"
        return 0
    elif echo $OUTPUT | grep -q "Ubuntu 24.04.3" ; then
        SERVER_OS="Ubuntu24043"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Ubuntu 24.04.3"
        return 0
    fi
    return 1
}

# Function to detect Debian variants
detect_debian() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "Debian GNU/Linux 11" ; then
        SERVER_OS="Debian11"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Debian GNU/Linux 11"
        return 0
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 12" ; then
        SERVER_OS="Debian12"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Debian GNU/Linux 12"
        return 0
    elif echo $OUTPUT | grep -q "Debian GNU/Linux 13" ; then
        SERVER_OS="Debian13"
        OS_FAMILY="debian"
        PACKAGE_MANAGER="apt"
        print_status "$GREEN" "Detected: Debian GNU/Linux 13"
        return 0
    fi
    return 1
}

# Function to detect openEuler variants
detect_openeuler() {
    local OUTPUT=$1
    
    if echo $OUTPUT | grep -q "openEuler 20.03" ; then
        SERVER_OS="openEuler2003"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: openEuler 20.03"
        return 0
    elif echo $OUTPUT | grep -q "openEuler 22.03" ; then
        SERVER_OS="openEuler2203"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: openEuler 22.03"
        return 0
    elif echo $OUTPUT | grep -q "openEuler 24.03" ; then
        SERVER_OS="openEuler2403"
        OS_FAMILY="rhel"
        PACKAGE_MANAGER="yum"
        print_status "$GREEN" "Detected: openEuler 24.03"
        return 0
    fi
    return 1
}

# Main OS detection function
detect_os() {
    print_status "$BLUE" "🔍 Detecting operating system..."
    
    # Detect architecture first
    if ! detect_architecture; then
        print_status "$RED" "❌ Unsupported architecture: $ARCHITECTURE"
        return 1
    fi
    
    # Get OS release information
    local OUTPUT=$(cat /etc/*release 2>/dev/null)
    if [ -z "$OUTPUT" ]; then
        print_status "$RED" "❌ Cannot read OS release information"
        return 1
    fi
    
    # Try to detect each OS family
    if detect_centos "$OUTPUT"; then
        return 0
    elif detect_almalinux "$OUTPUT"; then
        return 0
    elif detect_rocky "$OUTPUT"; then
        return 0
    elif detect_rhel "$OUTPUT"; then
        return 0
    elif detect_cloudlinux "$OUTPUT"; then
        return 0
    elif detect_ubuntu "$OUTPUT"; then
        return 0
    elif detect_debian "$OUTPUT"; then
        return 0
    elif detect_openeuler "$OUTPUT"; then
        return 0
    else
        print_status "$RED" "❌ Unable to detect your OS..."
        print_status "$YELLOW" "Supported operating systems:"
        echo -e "• Ubuntu: 18.04, 20.04, 20.10, 22.04, 24.04, 24.04.3"
        echo -e "• Debian: 11, 12, 13"
        echo -e "• AlmaLinux: 8, 9, 10"
        echo -e "• RockyLinux: 8, 9"
        echo -e "• RHEL: 8, 9"
        echo -e "• CentOS: 7, 8, 9, Stream 8, Stream 9"
        echo -e "• CloudLinux: 7, 8, 9"
        echo -e "• openEuler: 20.03, 22.03, 24.03"
        return 1
    fi
}

# Function to install basic tools
install_basic_tools() {
    print_status "$BLUE" "📦 Installing basic tools..."
    
    case $PACKAGE_MANAGER in
        "yum"|"dnf")
            $PACKAGE_MANAGER install curl wget -y 1> /dev/null
            $PACKAGE_MANAGER update curl wget ca-certificates -y 1> /dev/null
            ;;
        "apt")
            apt update -qq 2>/dev/null
            apt install -y -qq wget curl 2>/dev/null
            ;;
        *)
            print_status "$RED" "❌ Unknown package manager: $PACKAGE_MANAGER"
            return 1
            ;;
    esac
    
    print_status "$GREEN" "✅ Basic tools installed successfully"
    return 0
}

# Function to get OS information
get_os_info() {
    echo "SERVER_OS=$SERVER_OS"
    echo "OS_FAMILY=$OS_FAMILY"
    echo "PACKAGE_MANAGER=$PACKAGE_MANAGER"
    echo "ARCHITECTURE=$ARCHITECTURE"
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    detect_os
    if [ $? -eq 0 ]; then
        install_basic_tools
        get_os_info
    else
        exit 1
    fi
fi
