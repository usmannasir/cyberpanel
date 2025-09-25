#!/bin/bash

# CyberPanel Installation Module
# Handles the actual CyberPanel installation process
# Max 500 lines - Current: ~400 lines

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Global variables
MAX_RETRY_ATTEMPTS=5
INSTALL_LOG="/var/log/cyberpanel_install.log"
CURRENT_VERSION=""
INSTALLATION_TYPE=""

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL-INSTALL] $1" | tee -a "$INSTALL_LOG" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL-INSTALL] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to check if CyberPanel is installed
check_cyberpanel_installation() {
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        return 0
    else
        return 1
    fi
}

# Function to get current CyberPanel version
get_current_version() {
    if [ -f "/usr/local/CyberCP/version.txt" ]; then
        CURRENT_VERSION=$(cat /usr/local/CyberCP/version.txt 2>/dev/null || echo "unknown")
    else
        CURRENT_VERSION="unknown"
    fi
}

# Function to get latest version from GitHub
get_latest_version() {
    local latest_version
    latest_version=$(curl -s https://api.github.com/repos/usmannasir/cyberpanel/releases/latest | grep '"tag_name"' | cut -d'"' -f4 2>/dev/null || echo "unknown")
    echo "$latest_version"
}

# Function to check if update is needed
check_for_updates() {
    local latest_version
    latest_version=$(get_latest_version)
    
    if [ "$CURRENT_VERSION" != "unknown" ] && [ "$latest_version" != "unknown" ]; then
        if [ "$CURRENT_VERSION" != "$latest_version" ]; then
            print_status "$YELLOW" "Update available: $CURRENT_VERSION -> $latest_version"
            return 0
        else
            print_status "$GREEN" "CyberPanel is up to date ($CURRENT_VERSION)"
            return 1
        fi
    else
        print_status "$YELLOW" "Cannot determine version status"
        return 1
    fi
}

# Function to uninstall CyberPanel
uninstall_cyberpanel() {
    print_status "$YELLOW" "Uninstalling existing CyberPanel installation..."
    
    # Stop services
    systemctl stop cyberpanel 2>/dev/null || true
    systemctl stop lsws 2>/dev/null || true
    systemctl stop lsmcd 2>/dev/null || true
    
    # Remove systemd services
    systemctl disable cyberpanel 2>/dev/null || true
    systemctl disable lsws 2>/dev/null || true
    systemctl disable lsmcd 2>/dev/null || true
    
    # Remove service files
    rm -f /etc/systemd/system/cyberpanel.service
    rm -f /etc/systemd/system/lsws.service
    rm -f /etc/systemd/system/lsmcd.service
    
    # Remove directories
    rm -rf /usr/local/CyberCP
    rm -rf /usr/local/lsws
    rm -rf /usr/local/lsmcd
    rm -rf /etc/cyberpanel
    rm -rf /var/lib/lsphp
    
    # Remove users
    userdel -r cyberpanel 2>/dev/null || true
    userdel -r lsadm 2>/dev/null || true
    
    print_status "$GREEN" "CyberPanel uninstalled successfully"
}

# Function to install CyberPanel with retry logic
install_cyberpanel_with_retry() {
    local attempt=1
    local server_os=$1
    local branch_name=$2
    shift 2
    local install_args=("$@")
    
    while [ $attempt -le $MAX_RETRY_ATTEMPTS ]; do
        print_status "$BLUE" "Installation attempt $attempt of $MAX_RETRY_ATTEMPTS"
        
        if install_cyberpanel "$server_os" "$branch_name" "${install_args[@]}"; then
            print_status "$GREEN" "CyberPanel installed successfully on attempt $attempt"
            return 0
        else
            print_status "$RED" "Installation attempt $attempt failed"
            
            if [ $attempt -lt $MAX_RETRY_ATTEMPTS ]; then
                print_status "$YELLOW" "Retrying in 10 seconds..."
                sleep 10
                
                # Clean up failed installation
                cleanup_failed_installation
            fi
            
            attempt=$((attempt + 1))
        fi
    done
    
    print_status "$RED" "CyberPanel installation failed after $MAX_RETRY_ATTEMPTS attempts"
    return 1
}

# Function to clean up failed installation
cleanup_failed_installation() {
    print_status "$YELLOW" "Cleaning up failed installation..."
    
    # Stop any running services
    systemctl stop cyberpanel 2>/dev/null || true
    systemctl stop lsws 2>/dev/null || true
    systemctl stop lsmcd 2>/dev/null || true
    
    # Remove partial installations
    rm -rf /usr/local/CyberCP
    rm -rf /usr/local/lsws
    rm -rf /usr/local/lsmcd
    
    # Remove service files
    rm -f /etc/systemd/system/cyberpanel.service
    rm -f /etc/systemd/system/lsws.service
    rm -f /etc/systemd/system/lsmcd.service
    
    systemctl daemon-reload
}

# Function to install CyberPanel (original installation logic)
install_cyberpanel() {
    local server_os=$1
    local branch_name=$2
    shift 2
    local install_args=("$@")
    
    print_status "$BLUE" "Starting CyberPanel installation..."
    
    # Download and run the original installer
    if [ -n "$branch_name" ]; then
        if [[ "$branch_name" =~ ^[a-f0-9]{7,40}$ ]]; then
            curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$branch_name/cyberpanel.sh" 2>/dev/null
        elif [[ "$branch_name" =~ ^commit: ]]; then
            commit_hash="${branch_name#commit:}"
            curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$commit_hash/cyberpanel.sh" 2>/dev/null
        else
            curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$branch_name/cyberpanel.sh" 2>/dev/null
        fi
    else
        curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$server_os" 2>/dev/null
    fi
    
    chmod +x cyberpanel.sh
    
    # Run the installer and capture output
    if ./cyberpanel.sh "${install_args[@]}" > /tmp/cyberpanel_install_output.log 2>&1; then
        return 0
    else
        print_status "$RED" "Installation failed. Check /tmp/cyberpanel_install_output.log for details"
        return 1
    fi
}

# Function to determine installation type
determine_installation_type() {
    if check_cyberpanel_installation; then
        get_current_version
        if check_for_updates; then
            INSTALLATION_TYPE="update"
            print_status "$YELLOW" "Update installation detected"
        else
            print_status "$GREEN" "CyberPanel is already installed and up to date"
            print_status "$YELLOW" "Reinstalling to ensure proper configuration..."
            INSTALLATION_TYPE="reinstall"
        fi
    else
        INSTALLATION_TYPE="fresh"
        print_status "$BLUE" "Fresh installation detected"
    fi
}

# Function to perform installation based on type
perform_installation() {
    local server_os=$1
    local branch_name=$2
    shift 2
    local install_args=("$@")
    
    case $INSTALLATION_TYPE in
        "update"|"reinstall")
            uninstall_cyberpanel
            sleep 5
            if ! install_cyberpanel_with_retry "$server_os" "$branch_name" "${install_args[@]}"; then
                print_status "$RED" "Installation failed. Exiting..."
                return 1
            fi
            ;;
        "fresh")
            if ! install_cyberpanel_with_retry "$server_os" "$branch_name" "${install_args[@]}"; then
                print_status "$RED" "Installation failed. Exiting..."
                return 1
            fi
            ;;
    esac
    
    return 0
}

# Main installation function
install_cyberpanel_main() {
    local server_os=$1
    local branch_name=$2
    shift 2
    local install_args=("$@")
    
    print_status "$BLUE" "🚀 Starting CyberPanel installation process..."
    
    # Determine installation type
    determine_installation_type
    
    # Perform installation
    if perform_installation "$server_os" "$branch_name" "${install_args[@]}"; then
        print_status "$GREEN" "✅ CyberPanel installation completed successfully"
        return 0
    else
        print_status "$RED" "❌ CyberPanel installation failed"
        return 1
    fi
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <server_os> [branch_name] [install_args...]"
        echo "Example: $0 AlmaLinux9 v2.5.5-dev --debug"
        exit 1
    fi
    
    install_cyberpanel_main "$@"
fi
