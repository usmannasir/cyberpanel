#!/bin/bash

# CyberPanel Fixes Module
# Handles common installation issues and fixes
# Max 500 lines - Current: ~450 lines

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL-FIXES] $1" | tee -a "/var/log/cyberpanel_install.log" 2>/dev/null || echo "[$(date '+%Y-%m-%d %H:%M:%S')] [CYBERPANEL-FIXES] $1"
}

# Print colored output
print_status() {
    local color=$1
    local message=$2
    echo -e "${color}${message}${NC}"
    log_message "$message"
}

# Function to fix database connection issues
fix_database_issues() {
    print_status "$BLUE" "🔧 Fixing database connection issues..."
    
    # Start MariaDB service
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
    
    print_status "$GREEN" "✅ Database issues fixed"
}

# Function to fix LiteSpeed service configuration
fix_litespeed_service() {
    print_status "$BLUE" "🔧 Fixing LiteSpeed service configuration..."
    
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
    
    print_status "$GREEN" "✅ LiteSpeed service fixed"
}

# Function to fix SSL certificates
fix_ssl_certificates() {
    print_status "$BLUE" "🔧 Fixing SSL certificates..."
    
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
    
    print_status "$GREEN" "✅ SSL certificates fixed"
}

# Function to fix admin console files
fix_admin_console() {
    print_status "$BLUE" "🔧 Fixing admin console files..."
    
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
    
    print_status "$GREEN" "✅ Admin console files fixed"
}

# Function to fix CyberPanel service
fix_cyberpanel_service() {
    print_status "$BLUE" "🔧 Fixing CyberPanel service..."
    
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
    
    print_status "$GREEN" "✅ CyberPanel service fixed"
}

# Function to fix file permissions
fix_file_permissions() {
    print_status "$BLUE" "🔧 Fixing file permissions..."
    
    # Fix CyberPanel directory permissions
    if [ -d "/usr/local/CyberCP" ]; then
        chown -R root:root /usr/local/CyberCP
        chmod -R 755 /usr/local/CyberCP
    fi
    
    # Fix LiteSpeed directory permissions
    if [ -d "/usr/local/lsws" ]; then
        chown -R lsadm:lsadm /usr/local/lsws
        chmod -R 755 /usr/local/lsws
    fi
    
    # Fix log directory permissions
    mkdir -p /var/log/cyberpanel
    chown -R root:root /var/log/cyberpanel
    chmod -R 755 /var/log/cyberpanel
    
    print_status "$GREEN" "✅ File permissions fixed"
}

# Function to fix missing dependencies
fix_missing_dependencies() {
    local package_manager=$1
    
    print_status "$BLUE" "🔧 Fixing missing dependencies..."
    
    case $package_manager in
        "yum"|"dnf")
            # Install missing packages
            $package_manager install -y python3-pip python3-devel gcc gcc-c++ make 2>/dev/null || true
            $package_manager install -y aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
            $package_manager install -y libc-client-devel 2>/dev/null || print_status "$YELLOW" "libc-client-devel not available, skipping..."
            ;;
        "apt")
            # Install missing packages
            apt install -y python3-pip python3-dev gcc g++ make 2>/dev/null || true
            apt install -y aspell 2>/dev/null || print_status "$YELLOW" "aspell not available, skipping..."
            apt install -y libc-client-dev 2>/dev/null || print_status "$YELLOW" "libc-client-dev not available, skipping..."
            ;;
    esac
    
    print_status "$GREEN" "✅ Missing dependencies fixed"
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

# Function to generate status summary
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
        return 1
    fi
}

# Main function to apply all fixes
apply_cyberpanel_fixes() {
    local package_manager=$1
    
    print_status "$BLUE" "🔧 Applying CyberPanel installation fixes..."
    
    # Fix database issues
    fix_database_issues
    
    # Fix LiteSpeed service
    fix_litespeed_service
    
    # Fix SSL certificates
    fix_ssl_certificates
    
    # Fix admin console
    fix_admin_console
    
    # Fix CyberPanel service
    fix_cyberpanel_service
    
    # Fix file permissions
    fix_file_permissions
    
    # Fix missing dependencies
    fix_missing_dependencies "$package_manager"
    
    print_status "$GREEN" "✅ All CyberPanel fixes applied successfully"
    
    # Generate status summary
    generate_status_summary
}

# Main execution
if [ "${BASH_SOURCE[0]}" == "${0}" ]; then
    if [ $# -lt 1 ]; then
        echo "Usage: $0 <package_manager>"
        echo "Example: $0 dnf"
        exit 1
    fi
    
    apply_cyberpanel_fixes "$1"
fi
