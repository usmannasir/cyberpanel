#!/bin/bash

# Enhanced CyberPanel Installer with Smart Installation Logic
# This installer includes fix scripts, retry logic, and comprehensive status checking

set -e

# Global variables
MAX_RETRY_ATTEMPTS=5
INSTALL_LOG="/var/log/cyberpanel_install.log"
CURRENT_VERSION=""
INSTALLATION_TYPE=""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$INSTALL_LOG"
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
    
    while [ $attempt -le $MAX_RETRY_ATTEMPTS ]; do
        print_status "$BLUE" "Installation attempt $attempt of $MAX_RETRY_ATTEMPTS"
        
        if install_cyberpanel; then
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
    print_status "$BLUE" "Starting CyberPanel installation..."
    
    # Download and run the original installer
    if [ -n "$BRANCH_NAME" ]; then
        if [[ "$BRANCH_NAME" =~ ^[a-f0-9]{7,40}$ ]]; then
            curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel.sh" 2>/dev/null
        elif [[ "$BRANCH_NAME" =~ ^commit: ]]; then
            commit_hash="${BRANCH_NAME#commit:}"
            curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$commit_hash/cyberpanel.sh" 2>/dev/null
        else
            curl --silent -o cyberpanel.sh "https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel.sh" 2>/dev/null
        fi
    else
        curl --silent -o cyberpanel.sh "https://cyberpanel.sh/?dl&$SERVER_OS" 2>/dev/null
    fi
    
    chmod +x cyberpanel.sh
    
    # Run the installer and capture output
    if ./cyberpanel.sh $@ > /tmp/cyberpanel_install_output.log 2>&1; then
        return 0
    else
        print_status "$RED" "Installation failed. Check /tmp/cyberpanel_install_output.log for details"
        return 1
    fi
}

# Function to fix installation issues
fix_installation_issues() {
    print_status "$BLUE" "Applying installation fixes..."
    
    # 1. Fix Database Connection Issues
    print_status "$YELLOW" "Fixing database connection issues..."
    systemctl start mariadb 2>/dev/null || true
    systemctl enable mariadb 2>/dev/null || true
    
    # Set MariaDB root password
    mysqladmin -u root password '1234567' 2>/dev/null || true
    
    # Create cyberpanel database user
    mysql -u root -p1234567 -e "
    CREATE DATABASE IF NOT EXISTS cyberpanel;
    CREATE USER IF NOT EXISTS 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';
    GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost';
    FLUSH PRIVILEGES;
    " 2>/dev/null || true
    
    # 2. Fix LiteSpeed Service Configuration
    print_status "$YELLOW" "Fixing LiteSpeed service configuration..."
    
    # Create LiteSpeed service file
    cat > /etc/systemd/system/lsws.service << 'EOF'
[Unit]
Description=LiteSpeed Web Server
After=network.target

[Service]
Type=forking
User=root
Group=root
ExecStart=/usr/local/lsws/bin/lswsctrl start
ExecStop=/usr/local/lsws/bin/lswsctrl stop
ExecReload=/usr/local/lsws/bin/lswsctrl restart
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable lsws
    systemctl start lsws
    
    # 3. Fix SSL Certificates
    print_status "$YELLOW" "Fixing SSL certificates..."
    
    mkdir -p /root/cyberpanel
    cat > /root/cyberpanel/cert_conf << 'EOF'
[req]
distinguished_name = req_distinguished_name
req_extensions = v3_req
prompt = no

[req_distinguished_name]
C = US
ST = State
L = City
O = Organization
OU = Organizational Unit
CN = localhost

[v3_req]
keyUsage = keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names

[alt_names]
DNS.1 = localhost
IP.1 = 127.0.0.1
EOF
    
    # Generate SSL certificates
    openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
        -keyout /usr/local/lsws/admin/conf/cert/admin.key \
        -out /usr/local/lsws/admin/conf/cert/admin.crt \
        -config /root/cyberpanel/cert_conf 2>/dev/null || true
    
    chmod 600 /usr/local/lsws/admin/conf/cert/admin.key 2>/dev/null || true
    chmod 644 /usr/local/lsws/admin/conf/cert/admin.crt 2>/dev/null || true
    
    # 4. Fix Admin Console Files
    print_status "$YELLOW" "Fixing admin console files..."
    
    mkdir -p /usr/local/lsws/admin/fcgi-bin
    mkdir -p /usr/local/lsws/admin/conf
    
    cat > /usr/local/lsws/admin/fcgi-bin/admin_php << 'EOF'
#!/bin/bash
export PHP_LSAPI_CHILDREN=35
export PHP_LSAPI_MAX_REQUESTS=1000
exec /usr/local/lsws/lsphp82/bin/lsphp -b /usr/local/lsws/admin/fcgi-bin/admin_php
EOF
    
    chmod +x /usr/local/lsws/admin/fcgi-bin/admin_php 2>/dev/null || true
    htpasswd -cb /usr/local/lsws/admin/conf/htpasswd admin 1234567 2>/dev/null || true
    chown -R lsadm:lsadm /usr/local/lsws/admin/ 2>/dev/null || true
    
    # 5. Fix CyberPanel Service
    print_status "$YELLOW" "Fixing CyberPanel service..."
    
    cat > /etc/systemd/system/cyberpanel.service << 'EOF'
[Unit]
Description=CyberPanel Web Interface
After=network.target mariadb.service

[Service]
Type=simple
User=root
Group=root
WorkingDirectory=/usr/local/CyberCP
ExecStart=/usr/local/CyberPanel-venv/bin/python manage.py runserver 0.0.0.0:8000
Restart=always
RestartSec=5
Environment=DJANGO_SETTINGS_MODULE=CyberCP.settings

[Install]
WantedBy=multi-user.target
EOF
    
    systemctl daemon-reload
    systemctl enable cyberpanel
    
    print_status "$GREEN" "Installation fixes applied successfully"
}

# Function to check service status
check_service_status() {
    local service_name=$1
    local display_name=$2
    
    if systemctl is-active --quiet $service_name; then
        echo "✅ $display_name: RUNNING"
        return 0
    elif systemctl is-enabled --quiet $service_name; then
        echo "⚠️  $display_name: ENABLED BUT NOT RUNNING"
        return 1
    else
        echo "❌ $display_name: NOT INSTALLED/DISABLED"
        return 2
    fi
}

# Function to check port status
check_port_status() {
    local port=$1
    local service_name=$2
    
    if netstat -tlnp | grep -q ":$port "; then
        echo "✅ Port $port ($service_name): LISTENING"
        return 0
    else
        echo "❌ Port $port ($service_name): NOT LISTENING"
        return 1
    fi
}

# Function to generate comprehensive status summary
generate_status_summary() {
    local critical_failures=0
    local warnings=0
    
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                                               ║"
    echo "║                    📊 CYBERPANEL INSTALLATION STATUS SUMMARY 📊                                              ║"
    echo "║                                                                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    echo "🔧 CORE SERVICES STATUS:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    # Check critical services
    if ! check_service_status "mariadb" "MariaDB Database"; then
        critical_failures=$((critical_failures + 1))
    fi
    
    if ! check_service_status "lsws" "LiteSpeed Web Server"; then
        critical_failures=$((critical_failures + 1))
    fi
    
    if ! check_service_status "lsmcd" "LiteSpeed Memcached"; then
        warnings=$((warnings + 1))
    fi
    
    if ! check_service_status "cyberpanel" "CyberPanel Application"; then
        critical_failures=$((critical_failures + 1))
    fi
    
    if ! check_service_status "watchdog" "Watchdog Service"; then
        warnings=$((warnings + 1))
    fi
    
    echo ""
    echo "🌐 NETWORK PORTS STATUS:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    # Check critical ports
    if ! check_port_status "3306" "MariaDB"; then
        critical_failures=$((critical_failures + 1))
    fi
    
    if ! check_port_status "80" "HTTP"; then
        critical_failures=$((critical_failures + 1))
    fi
    
    if ! check_port_status "443" "HTTPS"; then
        warnings=$((warnings + 1))
    fi
    
    if ! check_port_status "8090" "CyberPanel"; then
        critical_failures=$((critical_failures + 1))
    fi
    
    if ! check_port_status "7080" "LiteSpeed Admin"; then
        warnings=$((warnings + 1))
    fi
    
    echo ""
    echo "🗄️  DATABASE CONNECTION TEST:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    if systemctl is-active --quiet mariadb; then
        if mysql -u root -p1234567 -e "SELECT 1;" >/dev/null 2>&1; then
            echo "✅ MariaDB Root Connection: SUCCESS"
        else
            echo "❌ MariaDB Root Connection: FAILED"
            critical_failures=$((critical_failures + 1))
        fi
        
        if mysql -u cyberpanel -pcyberpanel -e "SELECT 1;" >/dev/null 2>&1; then
            echo "✅ CyberPanel DB Connection: SUCCESS"
        else
            echo "❌ CyberPanel DB Connection: FAILED"
            critical_failures=$((critical_failures + 1))
        fi
    else
        echo "❌ MariaDB: NOT RUNNING"
        critical_failures=$((critical_failures + 1))
    fi
    
    echo ""
    echo "📁 CRITICAL DIRECTORIES:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    directories=(
        "/usr/local/lsws"
        "/usr/local/CyberCP"
        "/etc/cyberpanel"
        "/var/lib/lsphp"
    )
    
    for dir in "${directories[@]}"; do
        if [ -d "$dir" ]; then
            echo "✅ $dir: EXISTS"
        else
            echo "❌ $dir: MISSING"
            critical_failures=$((critical_failures + 1))
        fi
    done
    
    echo ""
    echo "🔐 SSL CERTIFICATES:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    if [ -f "/usr/local/lsws/admin/conf/cert/admin.crt" ]; then
        echo "✅ LiteSpeed Admin SSL: EXISTS"
    else
        echo "❌ LiteSpeed Admin SSL: MISSING"
        warnings=$((warnings + 1))
    fi
    
    echo ""
    echo "💾 SYSTEM RESOURCES:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    df -h / | tail -n1 | awk '{print "Root Filesystem: " $3 "/" $2 " (" $5 " used)"}'
    free -h | grep "Mem:" | awk '{print "Memory: " $3 "/" $2 " (" int($3/$2*100) "% used)"}'
    
    echo ""
    echo "📊 SUMMARY:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    
    if [ $critical_failures -eq 0 ]; then
        print_status "$GREEN" "🎉 INSTALLATION SUCCESSFUL! All critical services are running."
        echo "✅ Critical Failures: $critical_failures"
        echo "⚠️  Warnings: $warnings"
        return 0
    else
        print_status "$RED" "❌ INSTALLATION HAS CRITICAL ISSUES! $critical_failures critical failures detected."
        echo "❌ Critical Failures: $critical_failures"
        echo "⚠️  Warnings: $warnings"
        
        if [ $critical_failures -ge 3 ]; then
            print_status "$RED" "🚨 CRITICAL: Multiple core services failed. Server restart will likely result in Error 500!"
            echo ""
            echo "RECOMMENDED ACTIONS:"
            echo "1. Fix the critical issues before restarting"
            echo "2. Check system logs for detailed error information"
            echo "3. Consider running the installation again"
            return 2
        else
            print_status "$YELLOW" "⚠️  WARNING: Some issues detected. Server may have problems after restart."
            return 1
        fi
    fi
}

# Function to show firewall information
show_firewall_info() {
    echo ""
    echo "🔥 FIREWALL CONFIGURATION REQUIRED:"
    echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
    echo "If your provider has a network-level firewall, please ensure these ports are open:"
    echo ""
    echo "• TCP 8090 - CyberPanel Web Interface"
    echo "• TCP 80, 443 - Web Server (HTTP/HTTPS)"
    echo "• TCP 7080 - LiteSpeed Admin Console"
    echo "• TCP 21, 40110-40210 - FTP Service"
    echo "• TCP 25, 587, 465, 110, 143, 993 - Mail Services"
    echo "• TCP/UDP 53 - DNS Service"
    echo ""
}

# Main installation logic
main() {
    # Initialize log file
    mkdir -p /var/log
    touch "$INSTALL_LOG"
    
    print_status "$BLUE" "🚀 Enhanced CyberPanel Installer Starting..."
    print_status "$BLUE" "Log file: $INSTALL_LOG"
    
    # Detect OS (reuse existing logic)
    OUTPUT=$(cat /etc/*release)
    if echo $OUTPUT | grep -q "AlmaLinux 9" ; then
        SERVER_OS="AlmaLinux9"
        dnf install curl wget -y 1> /dev/null
        dnf update curl wget ca-certificates -y 1> /dev/null
        dnf install -y epel-release 1> /dev/null
        dnf groupinstall -y 'Development Tools' 1> /dev/null
        dnf install -y ImageMagick gd libicu oniguruma aspell libc-client 1> /dev/null
    else
        print_status "$RED" "Unsupported OS detected. This installer is optimized for AlmaLinux 9."
        exit 1
    fi
    
    # Check for branch parameter
    BRANCH_NAME=""
    if [ "$1" = "-b" ] || [ "$1" = "--branch" ]; then
        BRANCH_NAME="$2"
        shift 2
    fi
    
    # Determine installation type
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
    
    # Perform installation based on type
    case $INSTALLATION_TYPE in
        "update"|"reinstall")
            uninstall_cyberpanel
            sleep 5
            if ! install_cyberpanel_with_retry; then
                print_status "$RED" "Installation failed. Exiting..."
                exit 1
            fi
            ;;
        "fresh")
            if ! install_cyberpanel_with_retry; then
                print_status "$RED" "Installation failed. Exiting..."
                exit 1
            fi
            ;;
    esac
    
    # Apply fixes
    fix_installation_issues
    
    # Generate status summary
    local status_result
    generate_status_summary
    status_result=$?
    
    # Show firewall information
    show_firewall_info
    
    # Final restart prompt
    echo ""
    echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                                                               ║"
    echo "║                    🔄 SERVER RESTART PROMPT 🔄                                                              ║"
    echo "║                                                                                                               ║"
    echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
    echo ""
    
    if [ $status_result -eq 0 ]; then
        print_status "$GREEN" "✅ All systems ready! Safe to restart server."
        echo "Would you like to restart your server now? [Y/n]: "
    elif [ $status_result -eq 1 ]; then
        print_status "$YELLOW" "⚠️  Some issues detected. Server may have problems after restart."
        echo "Would you like to restart your server anyway? [y/N]: "
    else
        print_status "$RED" "❌ Critical issues detected. Server restart NOT recommended!"
        echo "Fix the issues first, then restart manually when ready."
        echo "Would you like to restart your server anyway? (NOT RECOMMENDED) [y/N]: "
    fi
    
    read -r response
    case "$response" in
        [yY]|[yY][eE][sS]|"")
            if [ $status_result -eq 0 ]; then
                print_status "$GREEN" "🔄 Restarting server..."
                shutdown -r now
            else
                print_status "$YELLOW" "⚠️  Restarting server despite issues..."
                shutdown -r now
            fi
            ;;
        *)
            print_status "$BLUE" "Server restart cancelled. You can restart manually when ready."
            ;;
    esac
}

# Run main function
main "$@"
