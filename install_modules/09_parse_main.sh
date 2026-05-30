#!/usr/bin/env bash
# CyberPanel install – parse_arguments, main. Sourced by cyberpanel.sh.

parse_arguments() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--branch)
                if [ -n "$2" ]; then
                    # Convert version number to branch name if needed
                    if [[ "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        if [[ "$2" == *"-"* ]]; then
                            # Already has suffix like 2.5.5-dev, add v prefix
                            BRANCH_NAME="v$2"
                        else
                            # Add v prefix and dev suffix for development versions
                            BRANCH_NAME="v$2-dev"
                        fi
                    elif [[ "$2" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        # Already has v prefix, use as is
                        BRANCH_NAME="$2"
                    else
                        # Assume it's already a branch name or commit hash
                        BRANCH_NAME="$2"
                    fi
                    shift 2
                else
                    echo "ERROR: -b/--branch requires a version number or branch name"
                    echo "Example: -b 2.5.5-dev or -b v2.5.5-dev"
                    exit 1
                fi
                ;;
            -v|--version)
                if [ -n "$2" ]; then
                    # Convert version number to branch name if needed
                    if [[ "$2" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        if [[ "$2" == *"-"* ]]; then
                            # Already has suffix like 2.5.5-dev, add v prefix
                            BRANCH_NAME="v$2"
                        else
                            # Add v prefix and dev suffix for development versions
                            BRANCH_NAME="v$2-dev"
                        fi
                    elif [[ "$2" =~ ^v[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9]+)?$ ]]; then
                        # Already has v prefix, use as is
                        BRANCH_NAME="$2"
                    else
                        # Assume it's already a branch name or commit hash
                        BRANCH_NAME="$2"
                    fi
                    shift 2
                else
                    echo "ERROR: -v/--version requires a version number or branch name"
                    echo "Example: -v 2.5.5-dev or -v v2.5.5-dev"
                    exit 1
                fi
                ;;
            --debug)
                DEBUG_MODE=true
                set -x
                shift
                ;;
            --mariadb-version)
                if [ -n "$2" ]; then
                    MARIADB_VER="$(normalize_mariadb_version "$2")"
                    shift 2
                else
                    echo "ERROR: --mariadb-version requires a version (e.g. 10.11, 11.8, 12.1, 12.3)"
                    exit 1
                fi
                ;;
            --auto)
                AUTO_INSTALL=true
                shift
                ;;
            --powerdns)
                if [ -n "$2" ]; then
                    INSTALL_POWERDNS="$(echo "$2" | tr '[:lower:]' '[:upper:]')"
                    shift 2
                else
                    echo "ERROR: --powerdns requires ON or OFF"
                    exit 1
                fi
                ;;
            --postfix)
                if [ -n "$2" ]; then
                    INSTALL_POSTFIX="$(echo "$2" | tr '[:lower:]' '[:upper:]')"
                    shift 2
                else
                    echo "ERROR: --postfix requires ON or OFF"
                    exit 1
                fi
                ;;
            --ftp)
                if [ -n "$2" ]; then
                    INSTALL_FTP="$(echo "$2" | tr '[:lower:]' '[:upper:]')"
                    shift 2
                else
                    echo "ERROR: --ftp requires ON or OFF"
                    exit 1
                fi
                ;;
            -h|--help)
                echo "Usage: $0 [OPTIONS]"
                echo "Options:"
                echo "  -b, --branch BRANCH    Install from specific branch/commit"
                echo "  -v, --version VER      Install specific version (auto-adds v prefix)"
                echo "  --mariadb-version VER  MariaDB version X.Y (e.g. 10.11, 11.8, 12.3); else asked in preferences"
                echo "  --debug               Enable debug mode"
                echo "  --auto                Auto mode: OpenLiteSpeed + MariaDB 11.8 unless --mariadb-version set"
                echo "  --powerdns ON|OFF     Install PowerDNS (default ON)"
                echo "  --postfix ON|OFF      Install Postfix/Dovecot email (default ON)"
                echo "  --ftp ON|OFF          Install Pure-FTPd (default ON)"
                echo "  -h, --help            Show this help message"
                echo ""
                echo "Examples:"
                echo "  $0                    # Interactive installation"
                echo "  $0 --debug            # Debug mode installation"
                echo "  $0 --auto             # Auto installation"
                echo "  $0 -b v2.5.5-dev      # Install development version"
                echo "  $0 -v 2.5.5-dev       # Install version 2.5.5-dev"
                echo "  $0 -v 2.4.3           # Install version 2.4.3"
                echo "  $0 -b main            # Install from main branch"
                echo "  $0 -b a1b2c3d4        # Install from specific commit"
                echo "  $0 --mariadb-version 10.11  # Use MariaDB 10.11 (same as v2.4.4 style)"
                echo "  $0 --mariadb-version 12.1   # Use MariaDB 12.1 (no prompt)"
                echo "  $0 --auto --mariadb-version 11.8   # Fully non-interactive with MariaDB 11.8"
                echo ""
                echo "Standard CyberPanel Installation Methods:"
                echo "  sh <(curl https://cyberpanel.net/install.sh)"
                echo "  bash <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b 2.4.3"
                echo "  bash <(curl https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh) -b 2.5.5-dev"
                exit 0
                ;;
            *)
                print_status "WARNING: Unknown option: $1"
                shift
                ;;
        esac
    done
}

# Function to detect installation mode
detect_installation_mode() {
    # Check if this is being called as an upgrade script
    if [[ "$0" == *"cyberpanel_upgrade.sh"* ]] || [[ "$0" == *"upgrade"* ]]; then
        INSTALLATION_TYPE="upgrade"
        return 0
    fi
    
    # Check if this is being called as a pre-upgrade script
    if [[ "$0" == *"preUpgrade.sh"* ]] || [[ "$0" == *"preupgrade"* ]]; then
        INSTALLATION_TYPE="preupgrade"
        return 0
    fi
    
    # Check if this is being called as a standard install script
    if [[ "$0" == *"install.sh"* ]] || [[ "$0" == *"cyberpanel.sh"* ]]; then
        INSTALLATION_TYPE="install"
        return 0
    fi
    
    # Default to install mode
    INSTALLATION_TYPE="install"
    return 0
}

# Function to create standard CyberPanel aliases
create_standard_aliases() {
    print_status "Creating standard CyberPanel installation aliases..."
    
    # Create symbolic links for standard installation methods
    local script_dir="/usr/local/bin"
    local script_name="cyberpanel_enhanced.sh"
    
    # Copy this script to /usr/local/bin
    if cp "$0" "$script_dir/$script_name" 2>/dev/null; then
        chmod +x "$script_dir/$script_name"
        
        # Create aliases for standard CyberPanel methods
        ln -sf "$script_dir/$script_name" "$script_dir/cyberpanel_upgrade.sh" 2>/dev/null || true
        ln -sf "$script_dir/$script_name" "$script_dir/preUpgrade.sh" 2>/dev/null || true
        ln -sf "$script_dir/$script_name" "$script_dir/install.sh" 2>/dev/null || true
        
        print_status "✓ Standard CyberPanel aliases created"
        print_status "  - cyberpanel_upgrade.sh"
        print_status "  - preUpgrade.sh" 
        print_status "  - install.sh"
    else
        print_status "WARNING: Could not create standard aliases (permission denied)"
    fi
}

# Main installation function
main() {
    require_root

    local log_dir="${CYBERPANEL_LOG_DIR:-/var/log/CyberPanel}"
    if ! mkdir -p "${log_dir}" 2>/dev/null; then
        log_dir="${HOME:-/tmp}/.cyberpanel-install/logs"
        mkdir -p "${log_dir}" 2>/dev/null || log_dir="/tmp"
        CYBERPANEL_LOG_DIR="${log_dir}"
    fi
    touch "${log_dir}/install.log" 2>/dev/null || true

    print_status "CyberPanel Enhanced Installer Starting..."
    print_status "Log file: ${log_dir}/install.log"
    
    # Detect installation mode
    detect_installation_mode
    
    # Parse command line arguments
    parse_arguments "$@"

    # Piped one-liner (curl | bash): default to auto install when no TTY and --auto not set
    if [ "$INSTALLATION_TYPE" = "install" ] && [ "$AUTO_INSTALL" != true ] && [ ! -t 0 ]; then
        AUTO_INSTALL=true
        if [ -z "$MARIADB_VER" ]; then
            MARIADB_VER="11.8"
        fi
        print_status "Non-interactive stdin detected: enabling --auto (MariaDB ${MARIADB_VER})"
    fi
    
    # Handle different installation modes
    case "$INSTALLATION_TYPE" in
        "upgrade")
            print_status "Running in upgrade mode..."
            if [ -n "$BRANCH_NAME" ]; then
                print_status "Upgrading to version: $BRANCH_NAME"
            fi
            start_upgrade
            ;;
        "preupgrade")
            print_status "Running in pre-upgrade mode..."
            start_preupgrade
            ;;
        "install"|*)
            if [ "$AUTO_INSTALL" = true ]; then
                # Run auto mode
                print_status "Starting auto mode..."
                
                # Detect OS
                if ! detect_os; then
                    print_status "ERROR: Failed to detect operating system"
                    exit 1
                fi
                
                # Install dependencies
                install_dependencies
                
                # Install CyberPanel
                if ! install_cyberpanel; then
                    print_status "ERROR: CyberPanel installation failed"
                    local _log_dir="${CYBERPANEL_LOG_DIR:-/var/log/CyberPanel}"
                    echo ""
                    echo "Installation failed. Check logs:"
                    echo "  ${_log_dir}/install.log"
                    echo "  /var/log/installLogs.txt"
                    if [ -t 0 ]; then
                        echo ""
                        echo "Would you like to see troubleshooting help? (y/n) [y]: "
                        read -r show_help
                        case $show_help in
                            [nN]|[nN][oO])
                                ;;
                            *)
                                show_error_help
                                ;;
                        esac
                    else
                        echo ""
                        echo "Non-interactive install (piped curl): use --auto --mariadb-version 11.8"
                        echo "Example: curl -sL .../install.sh | sudo sh -s -- -b v2.5.5-dev --auto --mariadb-version 11.8"
                    fi
                    exit 1
                fi
                
                # Apply fixes
                apply_fixes
                
                # Create standard aliases
                create_standard_aliases
                
                # Show status summary
                show_status_summary
                
                print_status "SUCCESS: Installation completed successfully!"
            else
                # Run interactive mode - ensure stdin is the terminal for prompts (e.g. when script was piped from curl)
                if [ ! -t 0 ]; then
                    exec 0</dev/tty
                fi
                show_main_menu
            fi
            ;;
    esac
}
