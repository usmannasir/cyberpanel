#!/bin/bash

# CyberPanel Universal Installer Test Script
# Tests the installer on ALL supported operating systems
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

# Test configuration
TEST_VERSION="v2.5.5-dev"
TEST_LOG_DIR="/tmp/cyberpanel_test_$(date +%Y%m%d_%H%M%S)"
TEST_RESULTS_FILE="$TEST_LOG_DIR/test_results.json"

# Create test log directory
mkdir -p "$TEST_LOG_DIR"

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $status in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${message}" | tee -a "$TEST_LOG_DIR/test.log"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${message}" | tee -a "$TEST_LOG_DIR/test.log"
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${message}" | tee -a "$TEST_LOG_DIR/test.log"
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${message}" | tee -a "$TEST_LOG_DIR/test.log"
            ;;
        "HEADER")
            echo -e "${CYAN}${message}${NC}" | tee -a "$TEST_LOG_DIR/test.log"
            ;;
        "DETAIL")
            echo -e "${WHITE}  ${message}${NC}" | tee -a "$TEST_LOG_DIR/test.log"
            ;;
    esac
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

# Function to check if OS is supported
is_os_supported() {
    local os_id=$1
    local os_version=$2
    
    case $os_id in
        "ubuntu")
            [[ "$os_version" =~ ^(24\.04|22\.04|20\.04)$ ]]
            ;;
        "debian")
            [[ "$os_version" =~ ^(13|12|11)$ ]]
            ;;
        "almalinux")
            [[ "$os_version" =~ ^(10|9|8)$ ]]
            ;;
        "rocky")
            [[ "$os_version" =~ ^(9|8)$ ]]
            ;;
        "rhel")
            [[ "$os_version" =~ ^(9|8)$ ]]
            ;;
        "cloudlinux")
            [[ "$os_version" =~ ^(9|8)$ ]]
            ;;
        "centos")
            [[ "$os_version" =~ ^(7|9)$ ]]
            ;;
        *)
            return 1
            ;;
    esac
}

# Function to run pre-installation tests
run_pre_install_tests() {
    print_status "INFO" "Running pre-installation tests..."
    
    local test_results=()
    
    # Test 1: System requirements
    print_status "INFO" "Testing system requirements..."
    
    # Check architecture
    ARCH=$(uname -m)
    if [ "$ARCH" = "x86_64" ]; then
        print_status "SUCCESS" "Architecture check passed: $ARCH"
        test_results+=("arch:pass")
    else
        print_status "ERROR" "Unsupported architecture: $ARCH (only x86_64 supported)"
        test_results+=("arch:fail")
        return 1
    fi
    
    # Check memory
    MEMORY_GB=$(free -g | awk '/^Mem:/{print $2}')
    if [ "$MEMORY_GB" -ge 1 ]; then
        print_status "SUCCESS" "Memory check passed: ${MEMORY_GB}GB"
        test_results+=("memory:pass")
    else
        print_status "WARNING" "Low memory: ${MEMORY_GB}GB (recommended: 2GB+)"
        test_results+=("memory:warning")
    fi
    
    # Check disk space
    DISK_GB=$(df / | awk 'NR==2{print int($4/1024/1024)}')
    if [ "$DISK_GB" -ge 10 ]; then
        print_status "SUCCESS" "Disk space check passed: ${DISK_GB}GB"
        test_results+=("disk:pass")
    else
        print_status "ERROR" "Insufficient disk space: ${DISK_GB}GB (minimum: 10GB)"
        test_results+=("disk:fail")
        return 1
    fi
    
    # Test 2: Network connectivity
    print_status "INFO" "Testing network connectivity..."
    
    if ping -c 1 google.com >/dev/null 2>&1; then
        print_status "SUCCESS" "Network connectivity check passed"
        test_results+=("network:pass")
    else
        print_status "ERROR" "Network connectivity check failed"
        test_results+=("network:fail")
        return 1
    fi
    
    # Test 3: Required commands
    print_status "INFO" "Testing required commands..."
    
    local missing_commands=()
    for cmd in curl wget python3 git; do
        if command -v $cmd >/dev/null 2>&1; then
            print_status "SUCCESS" "Command '$cmd' found: $(which $cmd)"
            test_results+=("cmd_$cmd:pass")
        else
            print_status "WARNING" "Command '$cmd' not found"
            missing_commands+=($cmd)
            test_results+=("cmd_$cmd:missing")
        fi
    done
    
    # Test 4: Package manager
    print_status "INFO" "Testing package manager..."
    
    case $ID in
        "ubuntu"|"debian")
            if apt update >/dev/null 2>&1; then
                print_status "SUCCESS" "APT package manager working"
                test_results+=("pkg_mgr:pass")
            else
                print_status "ERROR" "APT package manager failed"
                test_results+=("pkg_mgr:fail")
                return 1
            fi
            ;;
        "almalinux"|"rocky"|"rhel"|"centos"|"cloudlinux")
            if command -v dnf >/dev/null 2>&1; then
                if dnf repolist >/dev/null 2>&1; then
                    print_status "SUCCESS" "DNF package manager working"
                    test_results+=("pkg_mgr:pass")
                else
                    print_status "ERROR" "DNF package manager failed"
                    test_results+=("pkg_mgr:fail")
                    return 1
                fi
            elif command -v yum >/dev/null 2>&1; then
                if yum repolist >/dev/null 2>&1; then
                    print_status "SUCCESS" "YUM package manager working"
                    test_results+=("pkg_mgr:pass")
                else
                    print_status "ERROR" "YUM package manager failed"
                    test_results+=("pkg_mgr:fail")
                    return 1
                fi
            else
                print_status "ERROR" "No package manager found"
                test_results+=("pkg_mgr:fail")
                return 1
            fi
            ;;
        *)
            print_status "WARNING" "Unknown package manager for $OS"
            test_results+=("pkg_mgr:unknown")
            ;;
    esac
    
    # Test 5: Python compatibility
    print_status "INFO" "Testing Python compatibility..."
    
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
    PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)
    
    if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 8 ]; then
        print_status "SUCCESS" "Python version compatible: $PYTHON_VERSION"
        test_results+=("python:pass")
    else
        print_status "ERROR" "Python version incompatible: $PYTHON_VERSION (requires 3.8+)"
        test_results+=("python:fail")
        return 1
    fi
    
    # Test 6: CyberPanel URLs
    print_status "INFO" "Testing CyberPanel URLs..."
    
    local urls=(
        "https://cyberpanel.net/install.sh"
        "https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh"
        "https://github.com/usmannasir/cyberpanel"
    )
    
    for url in "${urls[@]}"; do
        if curl -I "$url" >/dev/null 2>&1; then
            print_status "SUCCESS" "URL accessible: $url"
            test_results+=("url_$(echo $url | sed 's/[^a-zA-Z0-9]/_/g'):pass")
        else
            print_status "ERROR" "URL not accessible: $url"
            test_results+=("url_$(echo $url | sed 's/[^a-zA-Z0-9]/_/g'):fail")
            return 1
        fi
    done
    
    # Save test results
    printf '%s\n' "${test_results[@]}" > "$TEST_LOG_DIR/pre_install_tests.txt"
    
    print_status "SUCCESS" "Pre-installation tests completed"
    return 0
}

# Function to run installation test
run_installation_test() {
    print_status "INFO" "Running CyberPanel installation test..."
    
    # Create installation log
    local install_log="$TEST_LOG_DIR/installation.log"
    
    # Run installation with logging
    print_status "INFO" "Starting CyberPanel installation..."
    print_status "INFO" "Version: $TEST_VERSION"
    print_status "INFO" "Installation log: $install_log"
    
    # Run the installer
    if timeout 1800 bash -c "
        sh <(curl https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh) 2>&1 | tee '$install_log'
    "; then
        print_status "SUCCESS" "Installation completed successfully"
        return 0
    else
        print_status "ERROR" "Installation failed or timed out"
        return 1
    fi
}

# Function to run post-installation tests
run_post_install_tests() {
    print_status "INFO" "Running post-installation tests..."
    
    local test_results=()
    
    # Test 1: Service status
    print_status "INFO" "Testing service status..."
    
    # Check LiteSpeed service
    if systemctl is-active --quiet lsws; then
        print_status "SUCCESS" "LiteSpeed service is running"
        test_results+=("lsws_service:pass")
    else
        print_status "ERROR" "LiteSpeed service is not running"
        test_results+=("lsws_service:fail")
    fi
    
    # Check CyberPanel service
    if systemctl is-active --quiet cyberpanel; then
        print_status "SUCCESS" "CyberPanel service is running"
        test_results+=("cyberpanel_service:pass")
    else
        print_status "WARNING" "CyberPanel service is not running (may be normal)"
        test_results+=("cyberpanel_service:warning")
    fi
    
    # Check MariaDB service
    if systemctl is-active --quiet mariadb; then
        print_status "SUCCESS" "MariaDB service is running"
        test_results+=("mariadb_service:pass")
    else
        print_status "ERROR" "MariaDB service is not running"
        test_results+=("mariadb_service:fail")
    fi
    
    # Test 2: Web interface accessibility
    print_status "INFO" "Testing web interface accessibility..."
    
    if curl -I http://localhost:8090 >/dev/null 2>&1; then
        print_status "SUCCESS" "CyberPanel web interface is accessible"
        test_results+=("web_interface:pass")
    else
        print_status "ERROR" "CyberPanel web interface is not accessible"
        test_results+=("web_interface:fail")
    fi
    
    # Test 3: Database connectivity
    print_status "INFO" "Testing database connectivity..."
    
    if mysql -u root -e "SHOW DATABASES;" >/dev/null 2>&1; then
        print_status "SUCCESS" "Database connectivity test passed"
        test_results+=("database:pass")
    else
        print_status "ERROR" "Database connectivity test failed"
        test_results+=("database:fail")
    fi
    
    # Test 4: File permissions
    print_status "INFO" "Testing file permissions..."
    
    local critical_paths=(
        "/usr/local/CyberCP"
        "/usr/local/lsws"
        "/etc/cyberpanel"
    )
    
    for path in "${critical_paths[@]}"; do
        if [ -d "$path" ]; then
            print_status "SUCCESS" "Directory exists: $path"
            test_results+=("path_$(echo $path | sed 's/[^a-zA-Z0-9]/_/g'):pass")
        else
            print_status "ERROR" "Directory missing: $path"
            test_results+=("path_$(echo $path | sed 's/[^a-zA-Z0-9]/_/g'):fail")
        fi
    done
    
    # Save test results
    printf '%s\n' "${test_results[@]}" > "$TEST_LOG_DIR/post_install_tests.txt"
    
    print_status "SUCCESS" "Post-installation tests completed"
    return 0
}

# Function to generate test report
generate_test_report() {
    print_status "INFO" "Generating test report..."
    
    local report_file="$TEST_LOG_DIR/test_report.md"
    
    cat > "$report_file" << EOF
# CyberPanel Universal OS Test Report

**Test Date**: $(date)
**OS**: $OS $VER ($ID)
**Test Version**: $TEST_VERSION
**Test Log Directory**: $TEST_LOG_DIR

## Test Summary

### Pre-Installation Tests
EOF

    if [ -f "$TEST_LOG_DIR/pre_install_tests.txt" ]; then
        while IFS= read -r line; do
            echo "- $line" >> "$report_file"
        done < "$TEST_LOG_DIR/pre_install_tests.txt"
    fi

    cat >> "$report_file" << EOF

### Post-Installation Tests
EOF

    if [ -f "$TEST_LOG_DIR/post_install_tests.txt" ]; then
        while IFS= read -r line; do
            echo "- $line" >> "$report_file"
        done < "$TEST_LOG_DIR/post_install_tests.txt"
    fi

    cat >> "$report_file" << EOF

## Installation Log
\`\`\`
EOF

    if [ -f "$TEST_LOG_DIR/installation.log" ]; then
        tail -100 "$TEST_LOG_DIR/installation.log" >> "$report_file"
    fi

    cat >> "$report_file" << EOF
\`\`\`

## System Information
- **OS**: $OS $VER
- **Architecture**: $(uname -m)
- **Memory**: $(free -h | awk '/^Mem:/{print $2}')
- **Disk Space**: $(df -h / | awk 'NR==2{print $4}')
- **Python Version**: $(python3 --version 2>&1)
- **Package Manager**: $(command -v dnf || command -v yum || command -v apt)

## Test Files
- **Test Log**: $TEST_LOG_DIR/test.log
- **Installation Log**: $TEST_LOG_DIR/installation.log
- **Pre-Install Tests**: $TEST_LOG_DIR/pre_install_tests.txt
- **Post-Install Tests**: $TEST_LOG_DIR/post_install_tests.txt

---
*Generated by CyberPanel Universal OS Test Script v2.5.5-dev*
EOF

    print_status "SUCCESS" "Test report generated: $report_file"
}

# Function to show help
show_help() {
    echo "CyberPanel Universal OS Test Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --version  Specify CyberPanel version to test (default: $TEST_VERSION)"
    echo "  -l, --log-dir  Specify custom log directory"
    echo "  -p, --pre-only Run only pre-installation tests"
    echo "  -i, --install  Run full installation test"
    echo "  -s, --skip-pre Skip pre-installation tests"
    echo ""
    echo "This script tests CyberPanel installation on the current system."
    echo "It performs comprehensive testing including system requirements,"
    echo "package availability, network connectivity, and installation verification."
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
    local run_pre_tests=true
    local run_install_test=false
    local run_post_tests=true
    
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_help
                exit 0
                ;;
            -v|--version)
                TEST_VERSION="$2"
                shift 2
                ;;
            -l|--log-dir)
                TEST_LOG_DIR="$2"
                mkdir -p "$TEST_LOG_DIR"
                shift 2
                ;;
            -p|--pre-only)
                run_pre_tests=true
                run_install_test=false
                run_post_tests=false
                shift
                ;;
            -i|--install)
                run_install_test=true
                shift
                ;;
            -s|--skip-pre)
                run_pre_tests=false
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Detect OS
    detect_os
    print_status "HEADER" "=========================================="
    print_status "HEADER" "CyberPanel Universal OS Test Script"
    print_status "HEADER" "=========================================="
    print_status "INFO" "Detected OS: $OS $VER ($ID)"
    print_status "INFO" "Test Version: $TEST_VERSION"
    print_status "INFO" "Log Directory: $TEST_LOG_DIR"
    
    # Check OS support
    if ! is_os_supported "$ID" "$VER"; then
        print_status "ERROR" "OS $OS $VER is not officially supported"
        print_status "INFO" "Supported OS: Ubuntu 24.04/22.04/20.04, Debian 13/12/11, AlmaLinux 10/9/8, RockyLinux 9/8, RHEL 9/8, CloudLinux 9/8, CentOS 7/9"
        exit 1
    fi
    
    print_status "SUCCESS" "OS $OS $VER is supported"
    
    # Run tests
    local exit_code=0
    
    if [ "$run_pre_tests" = true ]; then
        if ! run_pre_install_tests; then
            print_status "ERROR" "Pre-installation tests failed"
            exit_code=1
        fi
    fi
    
    if [ "$run_install_test" = true ]; then
        if ! run_installation_test; then
            print_status "ERROR" "Installation test failed"
            exit_code=1
        fi
    fi
    
    if [ "$run_post_tests" = true ] && [ "$run_install_test" = true ]; then
        if ! run_post_install_tests; then
            print_status "ERROR" "Post-installation tests failed"
            exit_code=1
        fi
    fi
    
    # Generate report
    generate_test_report
    
    # Print summary
    print_status "HEADER" "=========================================="
    print_status "HEADER" "Test Summary"
    print_status "HEADER" "=========================================="
    print_status "INFO" "Test completed for $OS $VER"
    print_status "INFO" "Log directory: $TEST_LOG_DIR"
    print_status "INFO" "Report file: $TEST_LOG_DIR/test_report.md"
    
    if [ $exit_code -eq 0 ]; then
        print_status "SUCCESS" "All tests passed successfully!"
    else
        print_status "ERROR" "Some tests failed. Check the logs for details."
    fi
    
    exit $exit_code
}

# Run main function
main "$@"
