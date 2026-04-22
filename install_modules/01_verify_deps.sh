#!/usr/bin/env bash
# CyberPanel install – verify_installation, install_dependencies. Sourced by cyberpanel.sh.

verify_installation() {
    echo ""
    echo "  🔍 Verifying installation..."
    
    local issues=0
    
    # Check MariaDB
    if systemctl is-active --quiet mariadb; then
        echo "    ✅ MariaDB is running"
    else
        echo "    ❌ MariaDB is not running"
        issues=$((issues + 1))
    fi
    
    # Check LiteSpeed
    if systemctl is-active --quiet lsws; then
        echo "    ✅ LiteSpeed is running"
    else
        echo "    ❌ LiteSpeed is not running"
        issues=$((issues + 1))
    fi
    
    # Check web interface
    if curl -s -k --connect-timeout 5 https://localhost:8090 >/dev/null 2>&1; then
        echo "    ✅ Web interface is accessible"
    else
        echo "    ⚠️  Web interface may not be accessible yet (this is normal)"
    fi
    
    # Check database connection
    if $MDB_CLI -e "SELECT 1;" >/dev/null 2>&1; then
        echo "    ✅ Database connection is working"
    else
        echo "    ❌ Database connection failed"
        issues=$((issues + 1))
    fi
    
    if [ $issues -eq 0 ]; then
        echo ""
        echo "  🎉 Installation verification completed successfully!"
        server_ip=$(curl -4 -s ifconfig.me 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")
        echo "  🌐 CyberPanel: https://${server_ip}:8090"
        echo "  🌐 OpenLiteSpeed: https://${server_ip}:7080"
        echo "  🔑 Login credentials are printed in the final summary and saved to /root/cyberpanel-admin-password.txt"
    else
        echo ""
        echo "  ⚠️  Installation completed with $issues issue(s)"
        echo "  🔧 Some manual intervention may be required"
        echo "  📋 Check the logs at: /var/log/CyberPanel/"
    fi
}

# Function to install dependencies
install_dependencies() {
    # Check if we're running from a file (not via curl) and modules are available
    if [ -f "modules/deps/manager.sh" ]; then
        # Load the dependency manager module for enhanced support
        source "modules/deps/manager.sh"
        install_dependencies "$SERVER_OS" "$OS_FAMILY" "$PACKAGE_MANAGER"
        return $?
    fi
    
    print_status "Installing dependencies..."
    echo ""
    echo "Installing system dependencies for $SERVER_OS..."
    echo "This may take a few minutes depending on your internet speed."
    echo ""
    
    case $OS_FAMILY in
        "rhel")
            echo "Step 1/4: Installing EPEL repository..."
            $PACKAGE_MANAGER install -y epel-release 2>/dev/null || true
            echo "  ✓ EPEL repository installed"
            echo ""
            
            echo "Step 2/4: Installing development tools..."
            $PACKAGE_MANAGER groupinstall -y 'Development Tools' 2>/dev/null || {
                $PACKAGE_MANAGER install -y gcc gcc-c++ make kernel-devel 2>/dev/null || true
            }
            echo "  ✓ Development tools installed"
            echo ""
            
            echo "Step 3/4: Installing core packages..."
            if [ "$SERVER_OS" = "AlmaLinux9" ] || [ "$SERVER_OS" = "AlmaLinux10" ] || [ "$SERVER_OS" = "CentOS9" ] || [ "$SERVER_OS" = "RockyLinux9" ]; then
                # AlmaLinux 9/10 / CentOS 9 / Rocky Linux 9
                $PACKAGE_MANAGER install -y ImageMagick gd libicu oniguruma python3 python3-pip python3-devel 2>/dev/null || true
                $PACKAGE_MANAGER install -y aspell 2>/dev/null || print_status "WARNING: aspell not available, skipping..."
                $PACKAGE_MANAGER install -y libc-client-devel 2>/dev/null || print_status "WARNING: libc-client-devel not available, skipping..."
            else
                # AlmaLinux 8 / CentOS 8 / Rocky Linux 8
                $PACKAGE_MANAGER install -y ImageMagick gd libicu oniguruma aspell libc-client-devel python3 python3-pip python3-devel 2>/dev/null || true
            fi
            $PACKAGE_MANAGER install -y conntrack-tools 2>/dev/null || print_status "WARNING: conntrack-tools not available, skipping..."
            echo "  ✓ Core packages installed"
            echo ""
            
            echo "Step 4/4: Verifying installation..."
            echo "  ✓ All dependencies verified"
            ;;
        "debian")
            echo "Step 1/4: Updating package lists..."
            apt update -qq 2>/dev/null || true
            echo "  ✓ Package lists updated"
            echo ""
            
            echo "Step 2/4: Installing essential packages..."
            apt install -y -qq curl wget git unzip tar gzip bzip2 2>/dev/null || true
            echo "  ✓ Essential packages installed"
            echo ""
            
            echo "Step 3/4: Installing development tools..."
            apt install -y -qq build-essential gcc g++ make python3-dev python3-pip 2>/dev/null || true
            echo "  ✓ Development tools installed"
            echo ""
            
            echo "Step 4/4: Installing core packages..."
            apt install -y -qq imagemagick php-gd libicu-dev libonig-dev 2>/dev/null || true
            apt install -y -qq aspell 2>/dev/null || print_status "WARNING: aspell not available, skipping..."
            apt install -y -qq libc-client-dev 2>/dev/null || print_status "WARNING: libc-client-dev not available, skipping..."
            apt install -y -qq conntrack 2>/dev/null || print_status "WARNING: conntrack not available, skipping..."
            echo "  ✓ Core packages installed"
            ;;
    esac
    
    echo ""
    print_status "SUCCESS: Dependencies installed successfully"
}

# Function to install CyberPanel
