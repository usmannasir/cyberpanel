#!/usr/bin/env bash
# CyberPanel install – main/fresh/version menus. Sourced by cyberpanel.sh.

show_main_menu() {
    show_banner
    
    echo "==============================================================================================================="
    echo "                                    SELECT INSTALLATION TYPE"
    echo "==============================================================================================================="
    echo ""
    echo "   1.  Fresh Installation (Recommended)"
    echo "   2.  Update Existing Installation"
    echo "   3.  Reinstall CyberPanel"
    echo "   4.  Force Reinstall (Clean & Install)"
    echo "   5.  Pre-Upgrade (Download latest upgrade script)"
    echo "   6.  Check System Status"
    echo "   7.  Advanced Options"
    echo "   8.  Exit"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Enter your choice [1-8]: "
        read -r choice
        
        case $choice in
            1)
                INSTALLATION_TYPE="fresh"
                show_fresh_install_menu
                return
                ;;
            2)
                INSTALLATION_TYPE="update"
                show_update_menu
                return
                ;;
            3)
                INSTALLATION_TYPE="reinstall"
                show_reinstall_menu
                return
                ;;
            4)
                INSTALLATION_TYPE="force_reinstall"
                start_force_reinstall
                return
                ;;
            5)
                start_preupgrade
                return
                ;;
            6)
                show_system_status
                return
                ;;
            7)
                show_advanced_menu
                return
                ;;
            8)
                echo "Goodbye!"
                exit 0
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-7."
                echo ""
      ;;
    esac
    done
}

# Function to show fresh installation menu
show_fresh_install_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    FRESH INSTALLATION SETUP"
    echo "==============================================================================================================="
    echo ""
    
    # Check if CyberPanel is already installed
    if [ -d "/usr/local/CyberCP" ] && [ -f "/usr/local/CyberCP/manage.py" ]; then
        echo "WARNING: CyberPanel appears to be already installed on this system."
        echo "         Consider using 'Update' or 'Reinstall' options instead."
        echo ""
        echo -n "Do you want to continue with fresh installation anyway? (y/n): "
        read -r response
        case $response in
            [yY]|[yY][eE][sS])
                ;;
            *)
                show_main_menu
                return
                ;;
        esac
    fi
    
    echo "Select installation option:"
    echo ""
    echo "   1.  Install Latest Stable Version"
    echo "   2.  Install Development Version (v2.5.5-dev)"
    echo "   3.  Install Specific Version/Branch"
    echo "   4.  Install from Commit Hash"
    echo "   5.  Quick Install (Auto-configure everything)"
    echo "   6.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select installation option [1-6]: "
        read -r choice
        
        case $choice in
            1)
                BRANCH_NAME=""
                show_installation_preferences
                return
                ;;
            2)
                BRANCH_NAME="v2.5.5-dev"
                show_installation_preferences
                return
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
                BRANCH_NAME=""
                AUTO_INSTALL=true
                prompt_mariadb_version_preference
                start_installation
                return
                ;;
            6)
                show_main_menu
                return
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-6."
                echo ""
  ;;
esac
    done
}

# Function to show commit selection
show_commit_selection() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    COMMIT HASH SELECTION"
    echo "==============================================================================================================="
    echo ""
    echo "Enter a specific commit hash to install from:"
    echo ""
    echo "Examples:"
    echo "  • Latest commit: Leave empty (press Enter)"
    echo "  • Specific commit: a1b2c3d4e5f6789012345678901234567890abcd"
    echo "  • Short commit: a1b2c3d (first 7 characters)"
    echo ""
    echo "You can find commit hashes at: https://github.com/usmannasir/cyberpanel/commits"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Enter commit hash (or press Enter for latest): "
        read -r commit_hash
        
        if [ -z "$commit_hash" ]; then
            echo "Using latest commit..."
            BRANCH_NAME=""
            show_installation_preferences
            return
        elif [[ "$commit_hash" =~ ^[a-f0-9]{7,40}$ ]]; then
            echo "Using commit: $commit_hash"
            BRANCH_NAME="$commit_hash"
            show_installation_preferences
            return
        else
            echo ""
            echo "ERROR: Invalid commit hash format."
            echo "       Please enter a valid Git commit hash (7-40 hexadecimal characters)."
            echo ""
        fi
    done
}

# Function to show version selection
show_version_selection() {
    echo ""
    echo "==============================================================================================================="
    echo "                                        VERSION SELECTION"
    echo "==============================================================================================================="
    echo ""
    echo "Available versions:"
    echo ""
    echo "   1.  Latest Stable (Recommended)"
    echo "   2.  v2.5.5-dev (Development)"
    echo "   3.  v2.4.4 (Previous Stable)"
    echo "   4.  Custom Branch Name"
    echo "   5.  Custom Commit Hash"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select version [1-5]: "
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
                BRANCH_NAME="v2.4.4"
                break
                ;;
            4)
                echo -n "Enter branch name (e.g., main, v2.5.5-dev): "
                read -r BRANCH_NAME
                if [ -z "$BRANCH_NAME" ]; then
                    echo "ERROR: Branch name cannot be empty."
                    continue
                fi
                # Add v prefix if it's a version number without v
                if [[ "$BRANCH_NAME" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                    if [[ "$BRANCH_NAME" == *"-"* ]]; then
                        # Already has suffix like 2.5.5-dev, add v prefix
                        BRANCH_NAME="v$BRANCH_NAME"
                    else
                        # Add v prefix and dev suffix for development versions
                        BRANCH_NAME="v$BRANCH_NAME-dev"
                    fi
                fi
                break
                ;;
            5)
                echo -n "Enter commit hash (7-40 characters): "
                read -r commit_hash
                if [[ "$commit_hash" =~ ^[a-f0-9]{7,40}$ ]]; then
                    BRANCH_NAME="$commit_hash"
                    break
                else
                    echo "ERROR: Invalid commit hash format."
                    continue
                fi
                ;;
            *)
                echo ""
                echo "ERROR: Invalid choice. Please enter 1-5."
                echo ""
  ;;
esac
    done
    
    show_installation_preferences
}

# Function to show installation preferences
show_installation_preferences() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    INSTALLATION PREFERENCES"
    echo "==============================================================================================================="
    echo ""
    
    # Debug mode
    echo -n "Enable debug mode for detailed logging? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            DEBUG_MODE=true
            ;;
        *)
            DEBUG_MODE=false
            ;;
    esac

    # MariaDB version (before auto-install so it is chosen even in auto mode)
    prompt_mariadb_version_preference

    # Optional components (ask before auto-install so choices apply to unattended run)
    echo -n "Install PowerDNS (DNS management)? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            INSTALL_POWERDNS="OFF"
            ;;
        *)
            INSTALL_POWERDNS="ON"
            ;;
    esac

    echo -n "Install Postfix/Dovecot (Email)? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            INSTALL_POSTFIX="OFF"
            ;;
        *)
            INSTALL_POSTFIX="ON"
            ;;
    esac

    echo -n "Install Pure-FTPd? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            INSTALL_FTP="OFF"
            ;;
        *)
            INSTALL_FTP="ON"
            ;;
    esac
    
    # Auto-install
    echo -n "Auto-install without further prompts? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            AUTO_INSTALL=false
            ;;
        *)
            AUTO_INSTALL=true
            ;;
    esac
    
    # Show summary
    echo ""
    echo "==============================================================================================================="
    echo "                                    INSTALLATION SUMMARY"
    echo "==============================================================================================================="
    echo ""
    echo "   Type: $INSTALLATION_TYPE"
    echo "   Version: ${BRANCH_NAME:-'Latest Stable'}"
    echo "   MariaDB: ${MARIADB_VER:-11.8}"
    echo "   PowerDNS: $INSTALL_POWERDNS"
    echo "   Email (Postfix/Dovecot): $INSTALL_POSTFIX"
    echo "   Pure-FTPd: $INSTALL_FTP"
    echo "   Debug Mode: $DEBUG_MODE"
    echo "   Auto Install: $AUTO_INSTALL"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    echo -n "Proceed with installation? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            start_installation
            ;;
    esac
}

# Function to show update menu
