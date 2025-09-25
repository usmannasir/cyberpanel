#!/bin/bash

# CyberPanel Universal OS Compatibility Test Script
# Tests installation on ALL supported operating systems
# Author: CyberPanel Team
# Version: 2.5.5-dev

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Test results tracking
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0
SKIPPED_TESTS=0

# Log file
LOG_FILE="/tmp/cyberpanel_os_test_$(date +%Y%m%d_%H%M%S).log"

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $status in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${message}" | tee -a "$LOG_FILE"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${message}" | tee -a "$LOG_FILE"
            ((PASSED_TESTS++))
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${message}" | tee -a "$LOG_FILE"
            ((FAILED_TESTS++))
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${message}" | tee -a "$LOG_FILE"
            ;;
        "SKIP")
            echo -e "${PURPLE}[SKIP]${NC} ${message}" | tee -a "$LOG_FILE"
            ((SKIPPED_TESTS++))
            ;;
        "HEADER")
            echo -e "${CYAN}${message}${NC}" | tee -a "$LOG_FILE"
            ;;
        "DETAIL")
            echo -e "${WHITE}  ${message}${NC}" | tee -a "$LOG_FILE"
            ;;
    esac
    ((TOTAL_TESTS++))
}

# Function to detect OS
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        ID=$ID
    elif type lsb_release >/dev/null 2>&1; then
        OS=$(lsb_release -si)
        VER=$(lsb_release -sr)
        ID=$(lsb_release -si | tr '[:upper:]' '[:lower:]')
    elif [ -f /etc/lsb-release ]; then
        . /etc/lsb-release
        OS=$DISTRIB_ID
        VER=$DISTRIB_RELEASE
        ID=$DISTRIB_ID
    elif [ -f /etc/debian_version ]; then
        OS=Debian
        VER=$(cat /etc/debian_version)
        ID=debian
    elif [ -f /etc/SuSe-release ]; then
        OS=SuSE
        VER=$(cat /etc/SuSe-release | head -n1 | cut -d' ' -f3)
        ID=suse
    elif [ -f /etc/redhat-release ]; then
        OS=$(cat /etc/redhat-release | cut -d' ' -f1)
        VER=$(cat /etc/redhat-release | cut -d' ' -f3)
        ID=redhat
    else
        OS=$(uname -s)
        VER=$(uname -r)
        ID=unknown
    fi
    
    # Normalize OS names
    case $ID in
        "ubuntu")
            OS="Ubuntu"
            ;;
        "debian")
            OS="Debian"
            ;;
        "almalinux")
            OS="AlmaLinux"
            ;;
        "rocky")
            OS="RockyLinux"
            ;;
        "rhel")
            OS="RHEL"
            ;;
        "cloudlinux")
            OS="CloudLinux"
            ;;
        "centos")
            OS="CentOS"
            ;;
    esac
}

# Function to check system requirements
check_system_requirements() {
    print_status "INFO" "Checking system requirements..."
    
    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" != "x86_64" ]; then
        print_status "ERROR" "Unsupported architecture: $ARCH (only x86_64 supported)"
        return 1
    fi
    print_status "SUCCESS" "Architecture check passed: $ARCH"
    
    # Check memory
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$MEMORY_GB" -lt 1 ]; then
        print_status "WARNING" "Low memory: ${MEMORY_GB}GB (recommended: 2GB+)"
    else
        print_status "SUCCESS" "Memory check passed: ${MEMORY_GB}GB"
    fi
    
    # Check disk space
    DISK_GB=$(df / | awk 'NR==2{print int($4/1024/1024)}')
    if [ "$DISK_GB" -lt 10 ]; then
        print_status "ERROR" "Insufficient disk space: ${DISK_GB}GB (minimum: 10GB)"
        return 1
    fi
    print_status "SUCCESS" "Disk space check passed: ${DISK_GB}GB"
    
    # Check network connectivity
    if ping -c 1 google.com >/dev/null 2>&1; then
        print_status "SUCCESS" "Network connectivity check passed"
    else
        print_status "ERROR" "Network connectivity check failed"
        return 1
    fi
}

# Function to check required commands
check_required_commands() {
    print_status "INFO" "Checking required commands..."
    
    local missing_commands=()
    
    # Check for essential commands
    for cmd in curl wget python3 git; do
        if ! command -v $cmd >/dev/null 2>&1; then
            missing_commands+=($cmd)
        else
            print_status "SUCCESS" "Command '$cmd' found: $(which $cmd)"
        fi
    done
    
    if [ ${#missing_commands[@]} -gt 0 ]; then
        print_status "WARNING" "Missing commands: ${missing_commands[*]}"
        print_status "INFO" "Installing missing commands..."
        
        # Install missing commands based on OS
        case $ID in
            "ubuntu"|"debian")
                apt update && apt install -y ${missing_commands[*]}
                ;;
            "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
                if command -v dnf >/dev/null 2>&1; then
                    dnf install -y ${missing_commands[*]}
                else
                    yum install -y ${missing_commands[*]}
                fi
                ;;
        esac
        
        # Verify installation
        for cmd in ${missing_commands[*]}; do
            if command -v $cmd >/dev/null 2>&1; then
                print_status "SUCCESS" "Command '$cmd' installed successfully"
            else
                print_status "ERROR" "Failed to install command '$cmd'"
                return 1
            fi
        done
    fi
}

# Function to test package manager
test_package_manager() {
    print_status "INFO" "Testing package manager compatibility..."
    
    case $ID in
        "ubuntu"|"debian")
            if apt update >/dev/null 2>&1; then
                print_status "SUCCESS" "APT package manager working"
            else
                print_status "ERROR" "APT package manager failed"
                return 1
            fi
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf >/dev/null 2>&1; then
                if dnf repolist >/dev/null 2>&1; then
                    print_status "SUCCESS" "DNF package manager working"
                else
                    print_status "ERROR" "DNF package manager failed"
                    return 1
                fi
            elif command -v yum >/dev/null 2>&1; then
                if yum repolist >/dev/null 2>&1; then
                    print_status "SUCCESS" "YUM package manager working"
                else
                    print_status "ERROR" "YUM package manager failed"
                    return 1
                fi
            else
                print_status "ERROR" "No package manager found"
                return 1
            fi
            ;;
        *)
            print_status "WARNING" "Unknown package manager for $OS"
            ;;
    esac
}

# Function to test Python compatibility
test_python_compatibility() {
    print_status "INFO" "Testing Python compatibility..."
    
    # Check Python version
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_status "SUCCESS" "Python version compatible: $PYTHON_VERSION"
    else
        print_status "ERROR" "Python version incompatible: $PYTHON_VERSION (requires 3.8+)"
        return 1
    fi
    
    # Test Python modules
    for module in os sys subprocess json; do
        if python3 -c "import $module" >/dev/null 2>&1; then
            print_status "SUCCESS" "Python module '$module' available"
        else
            print_status "ERROR" "Python module '$module' not available"
            return 1
        fi
    done
}

# Function to test network connectivity
test_network_connectivity() {
    print_status "INFO" "Testing network connectivity..."
    
    # Test CyberPanel URLs
    local urls=(
        "https://cyberpanel.net/install.sh"
        "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh"
        "https://github.com/usmannasir/cyberpanel"
    )
    
    for url in "${urls[@]}"; do
        if curl -I "$url" >/dev/null 2>&1; then
            print_status "SUCCESS" "URL accessible: $url"
        else
            print_status "ERROR" "URL not accessible: $url"
            return 1
        fi
    done
}

# Function to test installation script download
test_script_download() {
    print_status "INFO" "Testing installation script download..."
    
    # Test curl download
    if curl -s https://cyberpanel.net/install.sh | head -20 >/dev/null 2>&1; then
        print_status "SUCCESS" "Installation script download via curl successful"
    else
        print_status "ERROR" "Installation script download via curl failed"
        return 1
    fi
    
    # Test wget download
    if wget -qO- https://cyberpanel.net/install.sh | head -20 >/dev/null 2>&1; then
        print_status "SUCCESS" "Installation script download via wget successful"
    else
        print_status "ERROR" "Installation script download via wget failed"
        return 1
    fi
}

# Function to test OS-specific packages
test_os_specific_packages() {
    print_status "INFO" "Testing OS-specific package availability..."
    
    case $ID in
        "ubuntu"|"debian")
            # Test Ubuntu/Debian specific packages
            local packages=("python3-dev" "python3-pip" "build-essential" "libssl-dev" "libffi-dev")
            for package in "${packages[@]}"; do
                if apt list --installed 2>/dev/null | grep -q "^$package/" || apt search "$package" >/dev/null 2>&1; then
                    print_status "SUCCESS" "Package '$package' available for Ubuntu/Debian"
                else
                    print_status "WARNING" "Package '$package' not available for Ubuntu/Debian"
                fi
            done
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            # Test RHEL family specific packages
            local packages=("python3-devel" "gcc" "openssl-devel" "libffi-devel" "mariadb-server")
            for package in "${packages[@]}"; do
                if command -v dnf >/dev/null 2>&1; then
                    if dnf list available "$package" >/dev/null 2>&1; then
                        print_status "SUCCESS" "Package '$package' available for RHEL family"
                    else
                        print_status "WARNING" "Package '$package' not available for RHEL family"
                    fi
                elif command -v yum >/dev/null 2>&1; then
                    if yum list available "$package" >/dev/null 2>&1; then
                        print_status "SUCCESS" "Package '$package' available for RHEL family"
                    else
                        print_status "WARNING" "Package '$package' not available for RHEL family"
                    fi
                fi
            done
            ;;
    esac
}

# Function to test MariaDB compatibility
test_mariadb_compatibility() {
    print_status "INFO" "Testing MariaDB compatibility..."
    
    case $ID in
        "ubuntu"|"debian")
            if apt list --installed 2>/dev/null | grep -q "mariadb-server" || apt search "mariadb-server" >/dev/null 2>&1; then
                print_status "SUCCESS" "MariaDB available for Ubuntu/Debian"
            else
                print_status "WARNING" "MariaDB not available for Ubuntu/Debian"
            fi
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf >/dev/null 2>&1; then
                if dnf list available "mariadb-server" >/dev/null 2>&1; then
                    print_status "SUCCESS" "MariaDB available for RHEL family via DNF"
                else
                    print_status "WARNING" "MariaDB not available for RHEL family via DNF"
                fi
            elif command -v yum >/dev/null 2>&1; then
                if yum list available "mariadb-server" >/dev/null 2>&1; then
                    print_status "SUCCESS" "MariaDB available for RHEL family via YUM"
                else
                    print_status "WARNING" "MariaDB not available for RHEL family via YUM"
                fi
            fi
            ;;
    esac
}

# Function to test OpenLiteSpeed compatibility
test_openlitespeed_compatibility() {
    print_status "INFO" "Testing OpenLiteSpeed compatibility..."
    
    # Test OpenLiteSpeed repository access
    if curl -I "http://rpms.litespeedtech.com/centos/litespeed-repo-1.1-1.el8.noarch.rpm" >/dev/null 2>&1; then
        print_status "SUCCESS" "OpenLiteSpeed repository accessible"
    else
        print_status "WARNING" "OpenLiteSpeed repository not accessible"
    fi
}

# Function to run comprehensive test
run_comprehensive_test() {
    print_status "HEADER" "=========================================="
    print_status "HEADER" "CyberPanel Universal OS Compatibility Test"
    print_status "HEADER" "=========================================="
    print_status "INFO" "Starting comprehensive OS compatibility test..."
    print_status "INFO" "Log file: $LOG_FILE"
    
    # Detect OS
    detect_os
    print_status "INFO" "Detected OS: $OS $VER ($ID)"
    
    # Run all tests
    check_system_requirements || return 1
    check_required_commands || return 1
    test_package_manager || return 1
    test_python_compatibility || return 1
    test_network_connectivity || return 1
    test_script_download || return 1
    test_os_specific_packages
    test_mariadb_compatibility
    test_openlitespeed_compatibility
    
    # Print summary
    print_status "HEADER" "=========================================="
    print_status "HEADER" "Test Summary"
    print_status "HEADER" "=========================================="
    print_status "INFO" "Total tests: $TOTAL_TESTS"
    print_status "SUCCESS" "Passed: $PASSED_TESTS"
    print_status "ERROR" "Failed: $FAILED_TESTS"
    print_status "SKIP" "Skipped: $SKIPPED_TESTS"
    
    if [ $FAILED_TESTS -eq 0 ]; then
        print_status "SUCCESS" "All critical tests passed! OS is compatible with CyberPanel."
        return 0
    else
        print_status "ERROR" "Some tests failed. OS may have compatibility issues."
        return 1
    fi
}

# Function to show help
show_help() {
    echo "CyberPanel Universal OS Compatibility Test Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Enable verbose output"
    echo "  -q, --quiet    Enable quiet mode (errors only)"
    echo "  -l, --log      Specify custom log file"
    echo ""
    echo "This script tests CyberPanel compatibility on the current system."
    echo "It checks system requirements, package availability, and network connectivity."
    echo ""
    echo "Supported OS:"
    echo "  - Ubuntu 24.04, 22.04, 20.04"
    echo "  - Debian 13, 12, 11"
    echo "  - AlmaLinux 10, 9, 8"
    echo "  - RockyLinux 9, 8"
    echo "  - RHEL 9, 8"
    echo "  - CloudLinux 9, 8"
    echo "  - CentOS 7, 9, Stream 9"
}

# Main execution
main() {
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            -q|--quiet)
                exec 1>/dev/null
                shift
                ;;
            -l|--log)
                LOG_FILE="$2"
                shift 2
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Run the comprehensive test
    run_comprehensive_test
    exit $?
}

# Run main function
main "$@"
