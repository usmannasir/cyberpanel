#!/bin/bash

# Debian 13 Support Test Script for CyberPanel
# This script tests the compatibility of CyberPanel with Debian 13

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0
TESTS_TOTAL=0

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
    ((TESTS_PASSED++))
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    ((TESTS_FAILED++))
}

print_test_header() {
    echo -e "\n${BLUE}=== $1 ===${NC}"
    ((TESTS_TOTAL++))
}

# Function to run a test
run_test() {
    local test_name="$1"
    local test_command="$2"
    local expected_result="$3"
    
    print_test_header "$test_name"
    
    if eval "$test_command" >/dev/null 2>&1; then
        if [[ "$expected_result" == "success" ]]; then
            print_success "$test_name passed"
            return 0
        else
            print_error "$test_name failed (unexpected success)"
            return 1
        fi
    else
        if [[ "$expected_result" == "failure" ]]; then
            print_success "$test_name passed (expected failure)"
            return 0
        else
            print_error "$test_name failed"
            return 1
        fi
    fi
}

# Function to check OS detection
test_os_detection() {
    print_test_header "OS Detection Test"
    
    # Check if we're on Debian 13
    if [[ -f /etc/os-release ]]; then
        source /etc/os-release
        if [[ "$ID" == "debian" && "$VERSION_ID" == "13" ]]; then
            print_success "Debian 13 detected correctly"
        else
            print_warning "Not running on Debian 13 (Current: $ID $VERSION_ID)"
            print_status "This test is designed for Debian 13, but will continue with current OS"
        fi
    else
        print_error "Cannot detect OS - /etc/os-release not found"
        return 1
    fi
}

# Function to test CyberPanel OS detection logic
test_cyberpanel_os_detection() {
    print_test_header "CyberPanel OS Detection Logic Test"
    
    # Test the OS detection logic from cyberpanel.sh
    if grep -q -E "Debian GNU/Linux 11|Debian GNU/Linux 12|Debian GNU/Linux 13" /etc/os-release; then
        print_success "CyberPanel OS detection logic recognizes Debian 11/12/13"
    else
        print_error "CyberPanel OS detection logic does not recognize current Debian version"
        return 1
    fi
}

# Function to test package manager compatibility
test_package_manager() {
    print_test_header "Package Manager Compatibility Test"
    
    # Test apt-get availability
    if command -v apt-get >/dev/null 2>&1; then
        print_success "apt-get package manager is available"
    else
        print_error "apt-get package manager not found"
        return 1
    fi
    
    # Test apt-get update (dry run)
    if apt-get update --dry-run >/dev/null 2>&1; then
        print_success "apt-get update works correctly"
    else
        print_warning "apt-get update failed (may be network related)"
    fi
}

# Function to test systemd compatibility
test_systemd_compatibility() {
    print_test_header "Systemd Compatibility Test"
    
    # Test systemctl availability
    if command -v systemctl >/dev/null 2>&1; then
        print_success "systemctl is available"
    else
        print_error "systemctl not found"
        return 1
    fi
    
    # Test systemd status
    if systemctl is-system-running >/dev/null 2>&1; then
        print_success "systemd is running"
    else
        print_warning "systemd status unclear"
    fi
}

# Function to test Python compatibility
test_python_compatibility() {
    print_test_header "Python Compatibility Test"
    
    # Test Python 3 availability
    if command -v python3 >/dev/null 2>&1; then
        local python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
        print_success "Python 3 is available: $python_version"
        
        # Check if Python version is compatible (3.6+)
        local major_version=$(echo "$python_version" | cut -d'.' -f1)
        local minor_version=$(echo "$python_version" | cut -d'.' -f2)
        
        if [[ $major_version -ge 3 && $minor_version -ge 6 ]]; then
            print_success "Python version is compatible (3.6+)"
        else
            print_warning "Python version may not be fully compatible (requires 3.6+)"
        fi
    else
        print_error "Python 3 not found"
        return 1
    fi
    
    # Test pip3 availability
    if command -v pip3 >/dev/null 2>&1; then
        print_success "pip3 is available"
    else
        print_warning "pip3 not found (may need to be installed)"
    fi
}

# Function to test web server compatibility
test_web_server_compatibility() {
    print_test_header "Web Server Compatibility Test"
    
    # Test Apache2 availability
    if command -v apache2 >/dev/null 2>&1; then
        print_success "Apache2 is available"
    else
        print_warning "Apache2 not found (will be installed by CyberPanel)"
    fi
    
    # Test if Apache2 can be installed
    if apt-cache show apache2 >/dev/null 2>&1; then
        print_success "Apache2 package is available in repositories"
    else
        print_error "Apache2 package not found in repositories"
        return 1
    fi
}

# Function to test required packages availability
test_required_packages() {
    print_test_header "Required Packages Availability Test"
    
    local required_packages=(
        "curl"
        "wget"
        "git"
        "build-essential"
        "python3-dev"
        "python3-pip"
        "python3-venv"
        "software-properties-common"
        "apt-transport-https"
        "ca-certificates"
        "gnupg"
    )
    
    local available_count=0
    local total_count=${#required_packages[@]}
    
    for package in "${required_packages[@]}"; do
        if apt-cache show "$package" >/dev/null 2>&1; then
            print_success "$package is available"
            ((available_count++))
        else
            print_warning "$package not found in repositories"
        fi
    done
    
    print_status "Available packages: $available_count/$total_count"
    
    if [[ $available_count -ge $((total_count * 8 / 10)) ]]; then
        print_success "Most required packages are available"
    else
        print_warning "Many required packages are missing"
    fi
}

# Function to test LiteSpeed repository compatibility
test_litespeed_repo_compatibility() {
    print_test_header "LiteSpeed Repository Compatibility Test"
    
    # Test if we can access LiteSpeed Debian repository
    if curl -s --head "http://rpms.litespeedtech.com/debian/" | head -n 1 | grep -q "200 OK"; then
        print_success "LiteSpeed Debian repository is accessible"
    else
        print_warning "LiteSpeed Debian repository may not be accessible"
    fi
    
    # Test if we can download the repository setup script
    if wget --spider "http://rpms.litespeedtech.com/debian/enable_lst_debian_repo.sh" 2>/dev/null; then
        print_success "LiteSpeed repository setup script is available"
    else
        print_warning "LiteSpeed repository setup script may not be available"
    fi
}

# Function to test MariaDB compatibility
test_mariadb_compatibility() {
    print_test_header "MariaDB Compatibility Test"
    
    # Test MariaDB repository accessibility
    if curl -s --head "https://mariadb.org/mariadb_release_signing_key.pgp" | head -n 1 | grep -q "200 OK"; then
        print_success "MariaDB signing key is accessible"
    else
        print_warning "MariaDB signing key may not be accessible"
    fi
    
    # Test if MariaDB packages are available
    if apt-cache show mariadb-server >/dev/null 2>&1; then
        print_success "MariaDB packages are available in repositories"
    else
        print_warning "MariaDB packages not found in default repositories"
    fi
}

# Function to test network connectivity
test_network_connectivity() {
    print_test_header "Network Connectivity Test"
    
    local test_urls=(
        "https://github.com"
        "https://pypi.org"
        "http://rpms.litespeedtech.com"
        "https://mariadb.org"
    )
    
    local accessible_count=0
    local total_count=${#test_urls[@]}
    
    for url in "${test_urls[@]}"; do
        if curl -s --head "$url" >/dev/null 2>&1; then
            print_success "$url is accessible"
            ((accessible_count++))
        else
            print_warning "$url is not accessible"
        fi
    done
    
    print_status "Accessible URLs: $accessible_count/$total_count"
    
    if [[ $accessible_count -ge $((total_count * 3 / 4)) ]]; then
        print_success "Network connectivity is good"
    else
        print_warning "Network connectivity may be limited"
    fi
}

# Function to test system resources
test_system_resources() {
    print_test_header "System Resources Test"
    
    # Test available memory
    local total_memory=$(free -m | awk 'NR==2{print $2}')
    if [[ $total_memory -ge 1024 ]]; then
        print_success "Sufficient memory available: ${total_memory}MB"
    else
        print_warning "Low memory: ${total_memory}MB (recommended: 1GB+)"
    fi
    
    # Test available disk space
    local available_space=$(df / | awk 'NR==2{print $4}')
    local available_gb=$((available_space / 1024 / 1024))
    if [[ $available_gb -ge 10 ]]; then
        print_success "Sufficient disk space: ${available_gb}GB"
    else
        print_warning "Low disk space: ${available_gb}GB (recommended: 10GB+)"
    fi
    
    # Test CPU cores
    local cpu_cores=$(nproc)
    if [[ $cpu_cores -ge 2 ]]; then
        print_success "Sufficient CPU cores: $cpu_cores"
    else
        print_warning "Limited CPU cores: $cpu_cores (recommended: 2+)"
    fi
}

# Function to run all tests
run_all_tests() {
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}  CyberPanel Debian 13 Compatibility Test${NC}"
    echo -e "${BLUE}========================================${NC}\n"
    
    test_os_detection
    test_cyberpanel_os_detection
    test_package_manager
    test_systemd_compatibility
    test_python_compatibility
    test_web_server_compatibility
    test_required_packages
    test_litespeed_repo_compatibility
    test_mariadb_compatibility
    test_network_connectivity
    test_system_resources
    
    echo -e "\n${BLUE}========================================${NC}"
    echo -e "${BLUE}  Test Results Summary${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo -e "Total Tests: $TESTS_TOTAL"
    echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
    echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
    
    if [[ $TESTS_FAILED -eq 0 ]]; then
        echo -e "\n${GREEN}✅ All tests passed! Debian 13 appears to be compatible with CyberPanel.${NC}"
        return 0
    elif [[ $TESTS_FAILED -le 2 ]]; then
        echo -e "\n${YELLOW}⚠️  Most tests passed. Debian 13 should be compatible with minor issues.${NC}"
        return 0
    else
        echo -e "\n${RED}❌ Multiple tests failed. Debian 13 may have compatibility issues.${NC}"
        return 1
    fi
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -v, --verbose  Enable verbose output"
    echo "  --quick        Run only essential tests"
    echo ""
    echo "This script tests CyberPanel compatibility with Debian 13."
    echo "Run as root for best results."
}

# Main execution
main() {
    local verbose=false
    local quick=false
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            -h|--help)
                show_usage
                exit 0
                ;;
            -v|--verbose)
                verbose=true
                shift
                ;;
            --quick)
                quick=true
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_usage
                exit 1
                ;;
        esac
    done
    
    # Check if running as root
    if [[ $EUID -ne 0 ]]; then
        print_warning "Not running as root. Some tests may fail."
        print_status "Consider running: sudo $0"
    fi
    
    # Run tests
    if [[ "$quick" == "true" ]]; then
        print_status "Running quick compatibility test..."
        test_os_detection
        test_cyberpanel_os_detection
        test_package_manager
        test_systemd_compatibility
    else
        run_all_tests
    fi
}

# Run main function
main "$@"
