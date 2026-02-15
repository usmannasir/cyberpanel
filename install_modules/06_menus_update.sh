#!/usr/bin/env bash
# CyberPanel install – update/reinstall/status menus. Sourced by cyberpanel.sh.

show_update_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    UPDATE INSTALLATION"
    echo "==============================================================================================================="
    echo ""
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        echo "ERROR: CyberPanel is not installed on this system."
        echo "       Please use 'Fresh Installation' instead."
        echo ""
        read -p "Press Enter to return to main menu..."
        show_main_menu
        return
    fi
    
    # Check current version
    local current_version="unknown"
    if [ -f "/usr/local/CyberCP/version.txt" ]; then
        current_version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
    fi
    
    echo "Current Installation:"
    echo "Version: $current_version"
    echo "Path: /usr/local/CyberCP"
    echo ""
    
    echo "Select update option:"
    echo ""
    echo "   1.  Update to Latest Stable"
    echo "   2.  Update to Development Version"
    echo "   3.  Update to Specific Version/Branch"
    echo "   4.  Update from Commit Hash"
    echo "   5.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select update option [1-5]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
                break
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                break
                ;;
            3)
                show_version_selection
                return
                ;;
            4)
                show_commit_selection
                return
                ;;
            5)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-5."
                echo ""
                ;;
        esac
    done
    
    echo -n "Proceed with update? (This will backup your current installation) (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            start_upgrade
            ;;
    esac
}

# Function to show reinstall menu
show_reinstall_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    REINSTALL CYBERPANEL"
    echo "==============================================================================================================="
    echo ""
    
    if [ ! -d "/usr/local/CyberCP" ] || [ ! -f "/usr/local/CyberCP/manage.py" ]; then
        echo "ERROR: CyberPanel is not installed on this system."
        echo "       Please use 'Fresh Installation' instead."
        echo ""
        read -p "Press Enter to return to main menu..."
        show_main_menu
        return
    fi
    
    echo "WARNING: This will completely remove the existing CyberPanel installation"
    echo "         and install a fresh copy. All data will be lost!"
    echo ""
    
    echo -n "Are you sure you want to reinstall? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            ;;
        *)
            show_main_menu
            return
            ;;
    esac
    
    echo "Select reinstall option:"
    echo ""
    echo "   1.  Reinstall Latest Stable"
    echo "   2.  Reinstall Development Version"
    echo "   3.  Reinstall Specific Version/Branch"
    echo "   4.  Reinstall from Commit Hash"
    echo "   5.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select reinstall option [1-5]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
    break
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                break
                ;;
            3)
                show_version_selection
                return
                ;;
            4)
                show_commit_selection
                return
                ;;
            5)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-5."
                echo ""
                ;;
        esac
    done
    
    echo -n "Proceed with reinstall? (This will delete all existing data) (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            start_reinstall
            ;;
        *)
            show_main_menu
            ;;
    esac
}

# Function to show system status
show_system_status() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    SYSTEM STATUS CHECK"
    echo "==============================================================================================================="
    echo ""
    
    # Check OS
    local os_info=$(cat /etc/os-release | grep PRETTY_NAME | cut -d'"' -f2 2>/dev/null || echo 'Unknown')
    echo "Operating System: $os_info"
    
    # Check CyberPanel installation
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        local version="unknown"
        if [ -f "/usr/local/CyberCP/version.txt" ]; then
            version=$(cat /usr/local/CyberCP/version.txt 2>/dev/null)
        fi
        echo "CyberPanel: Installed (Version: $version)"
    else
        echo "CyberPanel: Not Installed"
    fi
    
    # Check services
    echo ""
    echo "Services Status:"
    if systemctl is-active --quiet mariadb; then
        echo "  SUCCESS: MariaDB - Running"
    else
        echo "  ERROR: MariaDB - Not Running"
    fi
    
    if systemctl is-active --quiet lsws; then
        echo "  SUCCESS: LiteSpeed - Running"
    else
        echo "  ERROR: LiteSpeed - Not Running"
    fi
    
    if systemctl is-active --quiet lscpd; then
        echo "  SUCCESS: CyberPanel - Running"
    else
        echo "  ERROR: CyberPanel - Not Running"
    fi
    
    # Check ports
    echo ""
    echo "Port Status:"
    if netstat -tlnp | grep -q ":8090 "; then
        echo "  SUCCESS: Port 8090 (CyberPanel) - Listening"
    else
        echo "  ERROR: Port 8090 (CyberPanel) - Not Listening"
    fi
    
    if netstat -tlnp | grep -q ":80 "; then
        echo "  SUCCESS: Port 80 (HTTP) - Listening"
    else
        echo "  ERROR: Port 80 (HTTP) - Not Listening"
    fi
    
    echo ""
    echo -n "Return to main menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            exit 0
            ;;
        *)
            show_main_menu
            ;;
    esac
}

# Function to show advanced menu
