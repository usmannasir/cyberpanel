#!/bin/bash

# CyberPanel Installation Validation Script
# Validates that CyberPanel is properly installed and running
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

# Validation results
TOTAL_CHECKS=0
PASSED_CHECKS=0
FAILED_CHECKS=0
WARNING_CHECKS=0

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    
    case $status in
        "INFO")
            echo -e "${BLUE}[INFO]${NC} ${message}"
            ;;
        "SUCCESS")
            echo -e "${GREEN}[SUCCESS]${NC} ${message}"
            ((PASSED_CHECKS++))
            ;;
        "ERROR")
            echo -e "${RED}[ERROR]${NC} ${message}"
            ((FAILED_CHECKS++))
            ;;
        "WARNING")
            echo -e "${YELLOW}[WARNING]${NC} ${message}"
            ((WARNING_CHECKS++))
            ;;
        "HEADER")
            echo -e "${CYAN}${message}${NC}"
            ;;
        "DETAIL")
            echo -e "${WHITE}  ${message}${NC}"
            ;;
    esac
    ((TOTAL_CHECKS++))
}

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check service status
check_service() {
    local service_name=$1
    local service_display_name=$2
    
    if systemctl is-active --quiet "$service_name"; then
        print_status "SUCCESS" "$service_display_name service is running"
        return 0
    else
        print_status "ERROR" "$service_display_name service is not running"
        return 1
    fi
}

# Function to check if port is listening
check_port() {
    local port=$1
    local service_name=$2
    
    if netstat -tlnp 2>/dev/null | grep -q ":$port " || ss -tlnp 2>/dev/null | grep -q ":$port "; then
        print_status "SUCCESS" "$service_name is listening on port $port"
        return 0
    else
        print_status "ERROR" "$service_name is not listening on port $port"
        return 1
    fi
}

# Function to check file/directory exists
check_path() {
    local path=$1
    local description=$2
    
    if [ -e "$path" ]; then
        print_status "SUCCESS" "$description exists: $path"
        return 0
    else
        print_status "ERROR" "$description missing: $path"
        return 1
    fi
}

# Function to check web interface accessibility
check_web_interface() {
    local url=$1
    local service_name=$2
    
    if curl -s -I "$url" >/dev/null 2>&1; then
        print_status "SUCCESS" "$service_name web interface is accessible at $url"
        return 0
    else
        print_status "ERROR" "$service_name web interface is not accessible at $url"
        return 1
    fi
}

# Function to check database connectivity
check_database() {
    if mysql -u root -e "SHOW DATABASES;" >/dev/null 2>&1; then
        print_status "SUCCESS" "Database connectivity test passed"
        return 0
    else
        print_status "ERROR" "Database connectivity test failed"
        return 1
    fi
}

# Function to check Python environment
check_python_env() {
    local python_path=$1
    local env_name=$2
    
    if [ -f "$python_path" ]; then
        print_status "SUCCESS" "Python environment found: $python_path"
        
        # Check if virtual environment is activated
        if [ -n "$VIRTUAL_ENV" ]; then
            print_status "SUCCESS" "Virtual environment is activated: $VIRTUAL_ENV"
        else
            print_status "WARNING" "Virtual environment may not be activated"
        fi
        
        return 0
    else
        print_status "ERROR" "Python environment not found: $python_path"
        return 1
    fi
}

# Function to check CyberPanel installation
check_cyberpanel_installation() {
    print_status "INFO" "Checking CyberPanel installation..."
    
    # Check CyberPanel directory
    check_path "/usr/local/CyberCP" "CyberPanel installation directory"
    
    # Check CyberPanel Python environment
    check_python_env "/usr/local/CyberPanel-venv/bin/python3" "CyberPanel Python environment"
    
    # Check CyberPanel configuration
    check_path "/etc/cyberpanel" "CyberPanel configuration directory"
    
    # Check CyberPanel logs
    check_path "/usr/local/lscp/logs" "CyberPanel logs directory"
}

# Function to check LiteSpeed installation
check_litespeed_installation() {
    print_status "INFO" "Checking LiteSpeed installation..."
    
    # Check LiteSpeed directory
    check_path "/usr/local/lsws" "LiteSpeed installation directory"
    
    # Check LiteSpeed binary
    check_path "/usr/local/lsws/bin/lswsctrl" "LiteSpeed control binary"
    
    # Check LiteSpeed configuration
    check_path "/usr/local/lsws/conf" "LiteSpeed configuration directory"
    
    # Check LiteSpeed service
    check_service "lsws" "LiteSpeed"
    
    # Check LiteSpeed port
    check_port "8088" "LiteSpeed"
}

# Function to check MariaDB installation
check_mariadb_installation() {
    print_status "INFO" "Checking MariaDB installation..."
    
    # Check MariaDB service
    check_service "mariadb" "MariaDB"
    
    # Check MariaDB port
    check_port "3306" "MariaDB"
    
    # Check database connectivity
    check_database
}

# Function to check additional services
check_additional_services() {
    print_status "INFO" "Checking additional services..."
    
    # Check Pure-FTPd
    if systemctl list-units --type=service | grep -q "pure-ftpd"; then
        check_service "pure-ftpd" "Pure-FTPd"
    else
        print_status "WARNING" "Pure-FTPd service not found"
    fi
    
    # Check Postfix
    if systemctl list-units --type=service | grep -q "postfix"; then
        check_service "postfix" "Postfix"
    else
        print_status "WARNING" "Postfix service not found"
    fi
    
    # Check Dovecot
    if systemctl list-units --type=service | grep -q "dovecot"; then
        check_service "dovecot" "Dovecot"
    else
        print_status "WARNING" "Dovecot service not found"
    fi
}

# Function to check web interface
check_web_interface_access() {
    print_status "INFO" "Checking web interface accessibility..."
    
    # Check CyberPanel web interface
    check_web_interface "http://localhost:8090" "CyberPanel"
    
    # Check if HTTPS is working
    if curl -s -k -I "https://localhost:8090" >/dev/null 2>&1; then
        print_status "SUCCESS" "CyberPanel HTTPS interface is accessible"
    else
        print_status "WARNING" "CyberPanel HTTPS interface is not accessible"
    fi
}

# Function to check system resources
check_system_resources() {
    print_status "INFO" "Checking system resources..."
    
    # Check memory usage
    local memory_usage=$(free | awk '/^Mem:/{printf "%.1f", $3/$2 * 100.0}')
    if (( $(echo "$memory_usage < 90" | bc -l) )); then
        print_status "SUCCESS" "Memory usage is normal: ${memory_usage}%"
    else
        print_status "WARNING" "High memory usage: ${memory_usage}%"
    fi
    
    # Check disk usage
    local disk_usage=$(df / | awk 'NR==2{print $5}' | sed 's/%//')
    if [ "$disk_usage" -lt 90 ]; then
        print_status "SUCCESS" "Disk usage is normal: ${disk_usage}%"
    else
        print_status "WARNING" "High disk usage: ${disk_usage}%"
    fi
    
    # Check load average
    local load_avg=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | sed 's/,//')
    if (( $(echo "$load_avg < 5" | bc -l) )); then
        print_status "SUCCESS" "System load is normal: $load_avg"
    else
        print_status "WARNING" "High system load: $load_avg"
    fi
}

# Function to check firewall
check_firewall() {
    print_status "INFO" "Checking firewall configuration..."
    
    # Check if firewall is running
    if systemctl is-active --quiet firewalld; then
        print_status "SUCCESS" "FirewallD is running"
        
        # Check if port 8090 is open
        if firewall-cmd --list-ports 2>/dev/null | grep -q "8090"; then
            print_status "SUCCESS" "Port 8090 is open in firewall"
        else
            print_status "WARNING" "Port 8090 may not be open in firewall"
        fi
    elif systemctl is-active --quiet ufw; then
        print_status "SUCCESS" "UFW is running"
        
        # Check if port 8090 is open
        if ufw status 2>/dev/null | grep -q "8090"; then
            print_status "SUCCESS" "Port 8090 is open in UFW"
        else
            print_status "WARNING" "Port 8090 may not be open in UFW"
        fi
    else
        print_status "WARNING" "No firewall service detected"
    fi
}

# Function to generate validation report
generate_validation_report() {
    local report_file="/tmp/cyberpanel_validation_$(date +%Y%m%d_%H%M%S).txt"
    
    cat > "$report_file" << EOF
CyberPanel Installation Validation Report
========================================

Generated: $(date)
OS: $(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2)
Kernel: $(uname -r)
Architecture: $(uname -m)

Validation Results:
- Total Checks: $TOTAL_CHECKS
- Passed: $PASSED_CHECKS
- Failed: $FAILED_CHECKS
- Warnings: $WARNING_CHECKS

Success Rate: $(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))%

System Information:
- Memory: $(free -h | awk '/^Mem:/{print $2}')
- Disk: $(df -h / | awk 'NR==2{print $4}')
- Load: $(uptime | awk -F'load average:' '{print $2}')

Service Status:
$(systemctl status lsws mariadb cyberpanel 2>/dev/null | grep -E "(Active:|Main PID:)")

Network Status:
$(netstat -tlnp | grep -E ":(80|443|8090|3306)" || echo "No relevant ports found")

EOF

    print_status "INFO" "Validation report generated: $report_file"
}

# Main validation function
run_validation() {
    print_status "HEADER" "=========================================="
    print_status "HEADER" "CyberPanel Installation Validation"
    print_status "HEADER" "=========================================="
    
    # Check if running as root
    if [ "$EUID" -ne 0 ]; then
        print_status "ERROR" "This script must be run as root"
        exit 1
    fi
    
    # Run all validation checks
    check_cyberpanel_installation
    check_litespeed_installation
    check_mariadb_installation
    check_additional_services
    check_web_interface_access
    check_system_resources
    check_firewall
    
    # Generate report
    generate_validation_report
    
    # Print summary
    print_status "HEADER" "=========================================="
    print_status "HEADER" "Validation Summary"
    print_status "HEADER" "=========================================="
    print_status "INFO" "Total checks: $TOTAL_CHECKS"
    print_status "SUCCESS" "Passed: $PASSED_CHECKS"
    print_status "ERROR" "Failed: $FAILED_CHECKS"
    print_status "WARNING" "Warnings: $WARNING_CHECKS"
    
    local success_rate=$(( (PASSED_CHECKS * 100) / TOTAL_CHECKS ))
    
    if [ $FAILED_CHECKS -eq 0 ]; then
        print_status "SUCCESS" "All critical checks passed! CyberPanel is properly installed."
        exit 0
    elif [ $success_rate -ge 80 ]; then
        print_status "WARNING" "Most checks passed ($success_rate%), but some issues found."
        exit 1
    else
        print_status "ERROR" "Multiple critical issues found. CyberPanel installation may be incomplete."
        exit 2
    fi
}

# Function to show help
show_help() {
    echo "CyberPanel Installation Validation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  -q, --quiet    Run in quiet mode (errors only)"
    echo "  -v, --verbose  Run in verbose mode"
    echo ""
    echo "This script validates that CyberPanel is properly installed and running."
    echo "It checks services, ports, files, and web interface accessibility."
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
            -q|--quiet)
                exec 1>/dev/null
                shift
                ;;
            -v|--verbose)
                set -x
                shift
                ;;
            *)
                echo "Unknown option: $1"
                show_help
                exit 1
                ;;
        esac
    done
    
    # Run validation
    run_validation
}

# Run main function
main "$@"
