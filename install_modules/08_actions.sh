#!/usr/bin/env bash
# CyberPanel install – start_* actions. Sourced by cyberpanel.sh.

start_upgrade() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING UPGRADE"
    echo "==============================================================================================================="
    echo ""
    
    # Detect OS
    echo "Step 1/5: Detecting operating system..."
    if ! detect_os; then
        print_status "ERROR: Failed to detect operating system"
        exit 1
    fi
    echo "  ✓ Operating system detected successfully"
    echo ""
    
    # Install dependencies
    echo "Step 2/5: Installing/updating dependencies..."
    install_dependencies
    echo ""
    
    # Download and run the upgrade script
    echo "Step 3/5: Downloading CyberPanel upgrade script..."
    local upgrade_url=""
    if [ -n "$BRANCH_NAME" ]; then
        if [[ "$BRANCH_NAME" =~ ^[a-f0-9]{40}$ ]]; then
            # It's a commit hash
            echo "Downloading from commit: $BRANCH_NAME"
            upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh"
        else
            # It's a branch name
            echo "Downloading from branch: $BRANCH_NAME"
            upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh"
        fi
    else
        echo "Downloading from: https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh"
        upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh"
    fi
    
    curl --silent -o cyberpanel_upgrade.sh "$upgrade_url" 2>/dev/null
    
    chmod +x cyberpanel_upgrade.sh
    
    echo "  ✓ CyberPanel upgrade script downloaded"
    echo "  🔄 Starting CyberPanel upgrade..."
  echo ""
    echo "IMPORTANT: The upgrade is now running in the background."
    echo "You will see detailed output from the CyberPanel upgrade script below."
    echo "This is normal and expected - the upgrade is proceeding!"
  echo ""
    echo "==============================================================================================================="
  echo ""
    
    # Run the upgrade with live progress monitoring
    echo "Starting CyberPanel upgrade process..."
    echo "This may take several minutes. Please be patient."
    echo ""
    
    # Create log directory
    mkdir -p /var/log/CyberPanel
    
    # Run the upgrade with live output monitoring
    echo "Starting CyberPanel upgrade with live progress monitoring..."
    echo ""
    echo "==============================================================================================================="
    echo "                                    LIVE UPGRADE PROGRESS"
    echo "==============================================================================================================="
    echo ""
    
    # Run upgrade and show live output
    if [ "$DEBUG_MODE" = true ]; then
        ./cyberpanel_upgrade.sh --debug 2>&1 | tee /var/log/CyberPanel/upgrade_output.log
    else
        ./cyberpanel_upgrade.sh 2>&1 | tee /var/log/CyberPanel/upgrade_output.log
    fi
    
    local upgrade_exit_code=${PIPESTATUS[0]}
    
    echo ""
    echo "==============================================================================================================="
    echo "                                    UPGRADE COMPLETED"
    echo "==============================================================================================================="
    echo ""
    
    # Clean up downloaded upgrade script
    rm -f cyberpanel_upgrade.sh 2>/dev/null
    
    # Check if upgrade was successful
    if [ $upgrade_exit_code -eq 0 ]; then
        print_status "SUCCESS: CyberPanel upgraded successfully"
        return 0
    else
        print_status "ERROR: CyberPanel upgrade failed with exit code $upgrade_exit_code"
        echo ""
        echo "Upgrade log (last 50 lines):"
        echo "==============================================================================================================="
        tail -50 /var/log/CyberPanel/upgrade_output.log 2>/dev/null || echo "Could not read upgrade log"
        echo "==============================================================================================================="
        echo ""
        echo "Full upgrade log available at: /var/log/CyberPanel/upgrade_output.log"
        echo ""
        return 1
    fi
}

# Function to start force reinstall
start_force_reinstall() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    FORCE REINSTALL CYBERPANEL"
    echo "==============================================================================================================="
    echo ""
    echo "This will completely remove the existing CyberPanel installation and install a fresh copy."
    echo "All data and configurations will be lost!"
    echo ""
    
    while true; do
        echo -n "Are you sure you want to proceed? (y/N): "
        read -r confirm
        case $confirm in
            [Yy]*)
                echo ""
                echo "Starting force reinstall..."
                echo ""
                
                # Clean up existing installation
                cleanup_existing_cyberpanel
                
                # Start fresh installation
                start_installation
                break
                ;;
            [Nn]*|"")
                echo "Force reinstall cancelled."
                return
                ;;
            *)
                echo "Please answer yes or no."
                ;;
        esac
    done
}

# Function to start preupgrade
start_preupgrade() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    PRE-UPGRADE SETUP"
    echo "==============================================================================================================="
    echo ""
    
    echo "This will download the latest CyberPanel upgrade script to /usr/local/"
    echo "and prepare it for execution."
    echo ""
    
    # Get the latest version
    echo "Step 1/3: Fetching latest version information..."
    local latest_version=$(curl -s https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g' | sed 's:}*$::')
    local branch_name="v$latest_version"
    
    echo "  ✓ Latest version: $latest_version"
    echo "  ✓ Branch: $branch_name"
    echo ""
    
    # Download the upgrade script
    echo "Step 2/3: Downloading CyberPanel upgrade script..."
    local upgrade_url="https://raw.githubusercontent.com/usmannasir/cyberpanel/$branch_name/cyberpanel_upgrade.sh"
    echo "Downloading from: $upgrade_url"
    
    if curl --silent -o /usr/local/cyberpanel_upgrade.sh "$upgrade_url" 2>/dev/null; then
        chmod 700 /usr/local/cyberpanel_upgrade.sh
        echo "  ✓ Upgrade script downloaded to /usr/local/cyberpanel_upgrade.sh"
    else
        print_status "ERROR: Failed to download upgrade script"
        return 1
    fi
    echo ""
    
    # Show instructions
    echo "Step 3/3: Setup complete!"
    echo ""
    echo "The upgrade script is now ready at: /usr/local/cyberpanel_upgrade.sh"
    echo ""
    echo "To run the upgrade, you can either:"
    echo "  1. Use this installer's 'Update Existing Installation' option"
    echo "  2. Run directly: /usr/local/cyberpanel_upgrade.sh"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    read -p "Press Enter to return to main menu..."
    show_main_menu
}

# Function to start reinstall
start_reinstall() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING REINSTALL"
    echo "==============================================================================================================="
    echo ""
    
    echo "WARNING: This will completely remove the existing CyberPanel installation!"
    echo "All data, websites, and configurations will be lost!"
    echo ""
    
    # Detect OS
    echo "Step 1/6: Detecting operating system..."
    if ! detect_os; then
        print_status "ERROR: Failed to detect operating system"
        exit 1
    fi
    echo "  ✓ Operating system detected successfully"
    echo ""
    
    # Stop services
    echo "Step 2/6: Stopping CyberPanel services..."
    systemctl stop lscpd 2>/dev/null || true
    systemctl stop lsws 2>/dev/null || true
    systemctl stop mariadb 2>/dev/null || true
    systemctl stop postfix 2>/dev/null || true
    systemctl stop dovecot 2>/dev/null || true
    systemctl stop pure-ftpd 2>/dev/null || true
    echo "  ✓ Services stopped"
    echo ""
    
    # Remove existing installation
    echo "Step 3/6: Removing existing CyberPanel installation..."
    rm -rf /usr/local/CyberCP 2>/dev/null || true
    rm -rf /usr/local/lsws 2>/dev/null || true
    rm -rf /home/cyberpanel 2>/dev/null || true
    rm -rf /var/lib/mysql 2>/dev/null || true
    rm -rf /var/log/cyberpanel 2>/dev/null || true
    echo "  ✓ Existing installation removed"
    echo ""
    
    # Install dependencies
    echo "Step 4/6: Installing dependencies..."
    install_dependencies
    echo ""
    
    # Install CyberPanel
    echo "Step 5/6: Installing CyberPanel..."
    if ! install_cyberpanel; then
        print_status "ERROR: CyberPanel installation failed"
  exit 1
fi
    echo ""
    
    # Apply fixes
    echo "Step 6/6: Applying installation fixes..."
    apply_fixes
    echo ""
    
    # Show status summary
    show_status_summary
    
    print_status "SUCCESS: CyberPanel reinstalled successfully!"
}

# Function to start installation
start_installation() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    STARTING INSTALLATION"
    echo "==============================================================================================================="
    echo ""
    
    # Detect OS
    echo "Step 1/6: Detecting operating system..."
    if ! detect_os; then
        print_status "ERROR: Failed to detect operating system"
        exit 1
    fi
    echo "  ✓ Operating system detected successfully"
    echo ""
    
    # Install dependencies
    echo "Step 2/6: Installing dependencies..."
    install_dependencies
    echo ""
    
    # Install CyberPanel
    echo "Step 3/6: Installing CyberPanel..."
    if ! install_cyberpanel; then
        print_status "ERROR: CyberPanel installation failed"
        echo ""
        echo "Would you like to see troubleshooting help? (y/n) [y]: "
        read -r show_help
        case $show_help in
            [nN]|[nN][oO])
                echo "Installation failed. Check logs at /var/log/CyberPanel/"
                echo "Run the installer again and select 'Advanced Options' → 'Show Error Help' for detailed troubleshooting."
                ;;
            *)
                show_error_help
                ;;
        esac
        exit 1
    fi
    echo ""
    
    # Apply post-installation fixes silently
    apply_fixes

    # Create standard aliases (silently)
    create_standard_aliases >/dev/null 2>&1

    # Show final status summary
    echo ""
    show_status_summary
}

# Function to parse command line arguments
