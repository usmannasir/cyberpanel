#!/bin/bash

# CyberPanel Installer Menu System
# Interactive menu system for installation options
# Max 500 lines - Current: ~400 lines

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MODULES_DIR="$(dirname "$SCRIPT_DIR")"

# Load UI module
source "$MODULES_DIR/utils/ui.sh"

# Global variables
INSTALLATION_TYPE=""
BRANCH_NAME=""
DEBUG_MODE=false
AUTO_INSTALL=false

# Function to show main menu
show_main_menu() {
    print_header
    
    local options=(
        "🚀 Fresh Installation (Recommended)"
        "🔄 Update Existing Installation"
        "🔧 Reinstall CyberPanel"
        "📊 Check System Status"
        "🛠️  Advanced Options"
        "❌ Exit"
    )
    
    print_menu "Select Installation Type" "${options[@]}"
    
    local choice=$(get_user_choice "Enter your choice" 6 "1")
    
    case $choice in
        1)
            INSTALLATION_TYPE="fresh"
            show_fresh_install_menu
            ;;
        2)
            INSTALLATION_TYPE="update"
            show_update_menu
            ;;
        3)
            INSTALLATION_TYPE="reinstall"
            show_reinstall_menu
            ;;
        4)
            show_system_status
            ;;
        5)
            show_advanced_menu
            ;;
        6)
            print_footer
            exit 0
            ;;
    esac
}

# Function to show fresh installation menu
show_fresh_install_menu() {
    print_section "Fresh Installation Setup" "🚀"
    
    # Check if CyberPanel is already installed
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        print_warning_box "CyberPanel Already Installed" "CyberPanel appears to be already installed on this system. Consider using 'Update' or 'Reinstall' options instead."
        
        if ! get_yes_no "Do you want to continue with fresh installation anyway?" "n"; then
            show_main_menu
            return
        fi
    fi
    
    # Show installation options
    local options=(
        "📦 Install Latest Stable Version"
        "🔬 Install Development Version (v2.5.5-dev)"
        "🏷️  Install Specific Version/Branch"
        "⚡ Quick Install (Auto-configure everything)"
        "🔙 Back to Main Menu"
    )
    
    print_menu "Fresh Installation Options" "${options[@]}"
    
    local choice=$(get_user_choice "Select installation option" 5 "1")
    
    case $choice in
        1)
            BRANCH_NAME=""
            show_installation_preferences
            ;;
        2)
            BRANCH_NAME="v2.5.5-dev"
            show_installation_preferences
            ;;
        3)
            show_version_selection
            ;;
        4)
            BRANCH_NAME=""
            AUTO_INSTALL=true
            start_installation
            ;;
        5)
            show_main_menu
            ;;
    esac
}

# Function to show version selection
show_version_selection() {
    print_section "Version Selection" "🏷️"
    
    echo -e "${WHITE}Available versions:${NC}"
    echo -e "${BLUE}1.${NC} Latest Stable (Recommended)"
    echo -e "${BLUE}2.${NC} v2.5.5-dev (Development)"
    echo -e "${BLUE}3.${NC} v2.5.4 (Previous Stable)"
    echo -e "${BLUE}4.${NC} Custom Branch/Commit"
    echo ""
    
    local choice=$(get_user_choice "Select version" 4 "1")
    
    case $choice in
        1)
            BRANCH_NAME=""
            ;;
        2)
            BRANCH_NAME="v2.5.5-dev"
            ;;
        3)
            BRANCH_NAME="v2.5.4"
            ;;
        4)
            get_user_input "Enter branch name or commit hash" ""
            read -r BRANCH_NAME
            ;;
    esac
    
    show_installation_preferences
}

# Function to show installation preferences
show_installation_preferences() {
    print_section "Installation Preferences" "⚙️"
    
    # Debug mode
    if get_yes_no "Enable debug mode for detailed logging?" "n"; then
        DEBUG_MODE=true
    fi
    
    # Auto-install
    if get_yes_no "Auto-install without further prompts?" "n"; then
        AUTO_INSTALL=true
    fi
    
    # Show summary
    print_info_box "Installation Summary" "Type: $INSTALLATION_TYPE\nVersion: ${BRANCH_NAME:-'Latest Stable'}\nDebug Mode: $DEBUG_MODE\nAuto Install: $AUTO_INSTALL" "$BLUE"
    
    if get_yes_no "Proceed with installation?" "y"; then
        start_installation
    else
        show_main_menu
    fi
}

# Function to show update menu
show_update_menu() {
    print_section "Update Installation" "🔄"
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        print_error_box "CyberPanel Not Found" "CyberPanel is not installed on this system. Please use 'Fresh Installation' instead."
        show_main_menu
        return
    fi
    
    # Check current version
    local current_version="unknown"
    if [ -f "/usr/local/CyberCP/version.txt" ]; then
        current_version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
    fi
    
    print_info_box "Current Installation" "Version: $current_version\nPath: /usr/local/CyberCP" "$GREEN"
    
    local options=(
        "📈 Update to Latest Stable"
        "🔬 Update to Development Version"
        "🏷️  Update to Specific Version"
        "🔙 Back to Main Menu"
    )
    
    print_menu "Update Options" "${options[@]}"
    
    local choice=$(get_user_choice "Select update option" 4 "1")
    
    case $choice in
        1)
            BRANCH_NAME=""
            ;;
        2)
            BRANCH_NAME="v2.5.5-dev"
            ;;
        3)
            show_version_selection
            ;;
        4)
            show_main_menu
            return
            ;;
    esac
    
    if get_yes_no "Proceed with update? (This will backup your current installation)" "y"; then
        start_installation
    else
        show_main_menu
    fi
}

# Function to show reinstall menu
show_reinstall_menu() {
    print_section "Reinstall CyberPanel" "🔧"
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        print_error_box "CyberPanel Not Found" "CyberPanel is not installed on this system. Please use 'Fresh Installation' instead."
        show_main_menu
        return
    fi
    
    print_warning_box "Reinstall Warning" "This will completely remove the existing CyberPanel installation and install a fresh copy. All data will be lost!"
    
    if ! get_yes_no "Are you sure you want to reinstall?" "n"; then
        show_main_menu
        return
    fi
    
    local options=(
        "📦 Reinstall Latest Stable"
        "🔬 Reinstall Development Version"
        "🏷️  Reinstall Specific Version"
        "🔙 Back to Main Menu"
    )
    
    print_menu "Reinstall Options" "${options[@]}"
    
    local choice=$(get_user_choice "Select reinstall option" 4 "1")
    
    case $choice in
        1)
            BRANCH_NAME=""
            ;;
        2)
            BRANCH_NAME="v2.5.5-dev"
            ;;
        3)
            show_version_selection
            ;;
        4)
            show_main_menu
            return
            ;;
    esac
    
    if get_yes_no "Proceed with reinstall? (This will delete all existing data)" "n"; then
        start_installation
    else
        show_main_menu
    fi
}

# Function to show system status
show_system_status() {
    print_section "System Status Check" "📊"
    
    # Check OS
    local os_info=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo 'Unknown')
    echo -e "${WHITE}Operating System:${NC} $os_info"
    
    # Check CyberPanel installation
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        local version="unknown"
        if [ -f "/usr/local/CyberCP/version.txt" ]; then
            version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
        fi
        echo -e "${GREEN}CyberPanel:${NC} Installed (Version: $version)"
    else
        echo -e "${RED}CyberPanel:${NC} Not Installed"
    fi
    
    # Check services
    echo -e "\n${WHITE}Services Status:${NC}"
    if systemctl is-active --quiet mariadb; then
        echo -e "  ${GREEN}✅${NC} MariaDB: Running"
    else
        echo -e "  ${RED}❌${NC} MariaDB: Not Running"
    fi
    
    if systemctl is-active --quiet lsws; then
        echo -e "  ${GREEN}✅${NC} LiteSpeed: Running"
    else
        echo -e "  ${RED}❌${NC} LiteSpeed: Not Running"
    fi
    
    if systemctl is-active --quiet cyberpanel; then
        echo -e "  ${GREEN}✅${NC} CyberPanel: Running"
    else
        echo -e "  ${RED}❌${NC} CyberPanel: Not Running"
    fi
    
    # Check ports
    echo -e "\n${WHITE}Port Status:${NC}"
    if netstat -tlnp | grep -q ":8090 "; then
        echo -e "  ${GREEN}✅${NC} Port 8090 (CyberPanel): Listening"
    else
        echo -e "  ${RED}❌${NC} Port 8090 (CyberPanel): Not Listening"
    fi
    
    if netstat -tlnp | grep -q ":80 "; then
        echo -e "  ${GREEN}✅${NC} Port 80 (HTTP): Listening"
    else
        echo -e "  ${RED}❌${NC} Port 80 (HTTP): Not Listening"
    fi
    
    echo ""
    if get_yes_no "Return to main menu?" "y"; then
        show_main_menu
    else
        exit 0
    fi
}

# Function to show advanced menu
show_advanced_menu() {
    print_section "Advanced Options" "🛠️"
    
    local options=(
        "🔧 Fix Installation Issues"
        "🧹 Clean Installation Files"
        "📋 View Installation Logs"
        "🔍 System Diagnostics"
        "🔙 Back to Main Menu"
    )
    
    print_menu "Advanced Options" "${options[@]}"
    
    local choice=$(get_user_choice "Select advanced option" 5 "1")
    
    case $choice in
        1)
            show_fix_menu
            ;;
        2)
            show_clean_menu
            ;;
        3)
            show_logs_menu
            ;;
        4)
            show_diagnostics
            ;;
        5)
            show_main_menu
            ;;
    esac
}

# Function to show fix menu
show_fix_menu() {
    print_section "Fix Installation Issues" "🔧"
    
    print_info_box "Fix Options" "This will attempt to fix common CyberPanel installation issues:\n• Database connection problems\n• Service configuration issues\n• SSL certificate problems\n• File permission issues" "$YELLOW"
    
    if get_yes_no "Proceed with fixing installation issues?" "y"; then
        # Load fixes module and apply fixes
        source "$MODULES_DIR/fixes/cyberpanel_fixes.sh"
        apply_cyberpanel_fixes "auto"
    else
        show_advanced_menu
    fi
}

# Function to show clean menu
show_clean_menu() {
    print_section "Clean Installation Files" "🧹"
    
    print_warning_box "Clean Warning" "This will remove temporary installation files and logs. This action cannot be undone!"
    
    if get_yes_no "Proceed with cleaning?" "n"; then
        rm -rf /tmp/cyberpanel_*
        rm -rf /var/log/cyberpanel_install.log
        print_success_box "Cleanup Complete" "Temporary files and logs have been removed."
    fi
    
    if get_yes_no "Return to advanced menu?" "y"; then
        show_advanced_menu
    else
        show_main_menu
    fi
}

# Function to show logs menu
show_logs_menu() {
    print_section "View Installation Logs" "📋"
    
    local log_file="/var/log/cyberpanel_install.log"
    
    if [ -f "$log_file" ]; then
        echo -e "${WHITE}Installation Log:${NC} $log_file"
        echo -e "${WHITE}Log Size:${NC} $(du -h "$log_file" | cut -f1)"
        echo ""
        
        if get_yes_no "View recent log entries?" "y"; then
            echo -e "${CYAN}Recent log entries:${NC}"
            tail -n 20 "$log_file"
        fi
    else
        print_info_box "No Logs Found" "No installation logs found at $log_file" "$YELLOW"
    fi
    
    echo ""
    if get_yes_no "Return to advanced menu?" "y"; then
        show_advanced_menu
    else
        show_main_menu
    fi
}

# Function to show diagnostics
show_diagnostics() {
    print_section "System Diagnostics" "🔍"
    
    echo -e "${WHITE}Running system diagnostics...${NC}"
    echo ""
    
    # Disk space
    echo -e "${WHITE}Disk Usage:${NC}"
    df -h | grep -E '^/dev/'
    
    # Memory usage
    echo -e "\n${WHITE}Memory Usage:${NC}"
    free -h
    
    # Load average
    echo -e "\n${WHITE}System Load:${NC}"
    uptime
    
    # Network interfaces
    echo -e "\n${WHITE}Network Interfaces:${NC}"
    ip addr show | grep -E '^[0-9]+:|inet '
    
    echo ""
    if get_yes_no "Return to advanced menu?" "y"; then
        show_advanced_menu
    else
        show_main_menu
    fi
}

# Function to start installation
start_installation() {
    print_section "Starting Installation" "🚀"
    
    # Set total steps
    TOTAL_STEPS=6
    CURRENT_STEP=0
    
    # Step 1: Load modules
    print_step "Loading modules" "info"
    source "$MODULES_DIR/os/detect.sh"
    source "$MODULES_DIR/deps/manager.sh"
    source "$MODULES_DIR/install/cyberpanel_installer.sh"
    source "$MODULES_DIR/fixes/cyberpanel_fixes.sh"
    
    # Step 2: Detect OS
    print_step "Detecting operating system" "running"
    if detect_os; then
        eval $(get_os_info)
        print_step "Detecting operating system" "success"
    else
        print_step "Detecting operating system" "error"
        print_error_box "Installation Failed" "Failed to detect operating system. Installation cannot continue."
        exit 1
    fi
    
    # Step 3: Install dependencies
    print_step "Installing dependencies" "running"
    if manage_dependencies "$SERVER_OS" "$OS_FAMILY" "$PACKAGE_MANAGER"; then
        print_step "Installing dependencies" "success"
    else
        print_step "Installing dependencies" "warning"
    fi
    
    # Step 4: Install CyberPanel
    print_step "Installing CyberPanel" "running"
    if install_cyberpanel_main "$SERVER_OS" "$BRANCH_NAME" $([ "$DEBUG_MODE" = true ] && echo "--debug"); then
        print_step "Installing CyberPanel" "success"
    else
        print_step "Installing CyberPanel" "error"
        print_error_box "Installation Failed" "CyberPanel installation failed. Check logs for details."
        exit 1
    fi
    
    # Step 5: Apply fixes
    print_step "Applying fixes" "running"
    if apply_cyberpanel_fixes "$PACKAGE_MANAGER"; then
        print_step "Applying fixes" "success"
    else
        print_step "Applying fixes" "warning"
    fi
    
    # Step 6: Final status
    print_step "Final status check" "running"
    print_installation_summary "success" "CyberPanel has been installed successfully!"
    
    # Show next steps
    print_info_box "Next Steps" "1. Access CyberPanel at: http://your-server-ip:8090\n2. Default username: admin\n3. Default password: 1234567\n4. Change default password immediately\n5. Configure firewall to allow port 8090" "$GREEN"
    
    print_footer
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    show_main_menu
fi
