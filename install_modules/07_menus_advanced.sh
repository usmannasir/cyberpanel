#!/usr/bin/env bash
# CyberPanel install – advanced/fix/clean/logs menus. Sourced by cyberpanel.sh.

show_advanced_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    ADVANCED OPTIONS"
    echo "==============================================================================================================="
    echo ""
    echo "   1.  Fix Installation Issues"
    echo "   2.  Clean Installation Files"
    echo "   3.  View Installation Logs"
    echo "   4.  System Diagnostics"
    echo "   5.  Show Error Help"
    echo "   6.  Back to Main Menu"
    echo ""
    echo "==============================================================================================================="
    echo ""
    
    while true; do
        echo -n "Select advanced option [1-6]: "
        read -r choice
        
        case $choice in
            1)
                show_fix_menu
                return
                ;;
            2)
                show_clean_menu
                return
                ;;
            3)
                show_logs_menu
                return
                ;;
            4)
                show_diagnostics
                return
                ;;
            5)
                show_error_help
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

# Function to show error help
show_error_help() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    ERROR TROUBLESHOOTING HELP"
    echo "==============================================================================================================="
    echo ""
    echo "If your CyberPanel installation failed, here's how to troubleshoot:"
    echo ""
    echo "📋 LOG FILES LOCATION:"
    echo "  • Main installer log: /var/log/CyberPanel/install.log"
    echo "  • Installation output: /var/log/CyberPanel/install_output.log"
    echo "  • Upgrade output: /var/log/CyberPanel/upgrade_output.log"
    echo "  • System logs: /var/log/messages"
    echo ""
    echo "🔍 COMMON ISSUES & SOLUTIONS:"
    echo ""
    echo "1. DEPENDENCY INSTALLATION FAILED:"
    echo "   • Check internet connection: ping -c 3 google.com"
    echo "   • Update package lists: yum update -y (RHEL) or apt update (Debian)"
    echo "   • Check available disk space: df -h"
    echo ""
    echo "2. CYBERPANEL DOWNLOAD FAILED:"
    echo "   • Check internet connectivity"
    echo "   • Verify GitHub access: curl -I https://github.com"
    echo "   • Try different branch/version"
    echo ""
    echo "3. PERMISSION ERRORS:"
    echo "   • Ensure running as root: whoami"
    echo "   • Check file permissions: ls -la /var/log/CyberPanel/"
    echo ""
    echo "4. SYSTEM REQUIREMENTS:"
    echo "   • Minimum 1GB RAM: free -h"
    echo "   • Minimum 10GB disk space: df -h"
    echo "   • Supported OS: AlmaLinux 8/9/10, CentOS 8/9, Ubuntu 18.04+"
    echo ""
    echo "5. SERVICE CONFLICTS:"
    echo "   • Check running services: systemctl list-units --state=running"
    echo "   • Stop conflicting services: systemctl stop apache2 (if running)"
    echo ""
    echo "💡 QUICK DEBUG COMMANDS:"
    echo "  • View installation log: cat /var/log/CyberPanel/install_output.log"
    echo "  • Check system resources: free -h && df -h"
    echo "  • Test network: ping -c 3 google.com"
    echo "  • Check services: systemctl status lscpd"
    echo "  • View system logs: tail -50 /var/log/messages"
    echo ""
    echo "🆘 GETTING HELP:"
    echo "  • CyberPanel Documentation: https://docs.cyberpanel.net"
    echo "  • CyberPanel Community: https://forums.cyberpanel.net"
    echo "  • GitHub Issues: https://github.com/usmannasir/cyberpanel/issues"
    echo "  • Discord Support: https://discord.gg/cyberpanel"
    echo ""
    echo "🔄 RETRY INSTALLATION:"
    echo "  • Clean installation: Run installer with 'Clean Installation Files' option"
    echo "  • Different version: Try stable version instead of development"
    echo "  • Fresh system: Consider using a clean OS installation"
    echo ""
    echo "==============================================================================================================="
    echo ""
    read -p "Press Enter to return to main menu..."
    show_main_menu
}

# Function to show fix menu
show_fix_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    FIX INSTALLATION ISSUES"
    echo "==============================================================================================================="
    echo ""
    echo "This will attempt to fix common CyberPanel installation issues:"
    echo "• Database connection problems"
    echo "• Service configuration issues"
    echo "• SSL certificate problems"
    echo "• File permission issues"
    echo ""
    
    echo -n "Proceed with fixing installation issues? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_advanced_menu
            ;;
        *)
            print_status "Applying fixes..."
            apply_fixes
            print_status "SUCCESS: Fixes applied successfully"
            echo ""
            read -p "Press Enter to return to advanced menu..."
            show_advanced_menu
            ;;
    esac
}

# Function to show clean menu
show_clean_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    CLEAN INSTALLATION FILES"
    echo "==============================================================================================================="
    echo ""
    echo "WARNING: This will remove temporary installation files and logs."
    echo "         This action cannot be undone!"
    echo ""
    
    echo -n "Proceed with cleaning? (y/n) [n]: "
    read -r response
    case $response in
        [yY]|[yY][eE][sS])
            rm -rf /tmp/cyberpanel_*
            rm -rf /var/log/cyberpanel_install.log
            echo "SUCCESS: Cleanup complete! Temporary files and logs have been removed."
            ;;
    esac
    
    echo ""
    echo -n "Return to advanced menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            show_advanced_menu
            ;;
    esac
}

# Function to show logs menu
show_logs_menu() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    VIEW INSTALLATION LOGS"
    echo "==============================================================================================================="
    echo ""
    
    local log_file="/var/log/cyberpanel_install.log"
    
    if [ -f "$log_file" ]; then
        echo "Installation Log: $log_file"
        echo "Log Size: $(du -h "$log_file" | cut -f1)"
        echo ""
        
        echo -n "View recent log entries? (y/n) [y]: "
        read -r response
        case $response in
            [nN]|[nN][oO])
                ;;
            *)
                echo ""
                echo "Recent log entries:"
                tail -n 20 "$log_file"
                ;;
        esac
    else
        echo "No installation logs found at $log_file"
    fi
    
    echo ""
    echo -n "Return to advanced menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            show_advanced_menu
            ;;
    esac
}

# Function to show diagnostics
show_diagnostics() {
    echo ""
    echo "==============================================================================================================="
    echo "                                    SYSTEM DIAGNOSTICS"
    echo "==============================================================================================================="
    echo ""
    
    echo "Running system diagnostics..."
    echo ""
    
    # Disk space
    echo "Disk Usage:"
    df -h | grep -E '^/dev/'
    
    # Memory usage
    echo ""
    echo "Memory Usage:"
    free -h
    
    # Load average
    echo ""
    echo "System Load:"
    uptime
    
    # Network interfaces
    echo ""
    echo "Network Interfaces:"
    ip addr show | grep -E '^[0-9]+:|inet '
    
    echo ""
    echo -n "Return to advanced menu? (y/n) [y]: "
    read -r response
    case $response in
        [nN]|[nN][oO])
            show_main_menu
            ;;
        *)
            show_advanced_menu
            ;;
    esac
}

# Function to start upgrade
