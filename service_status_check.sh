#!/bin/bash

# CyberPanel Service Status Check Script
# This script provides a comprehensive overview of all CyberPanel services

echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                                               ║"
echo "║                    🚀 CYBERPANEL SERVICE STATUS SUMMARY 🚀                                                   ║"
echo "║                                                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Function to check service status
check_service() {
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
check_port() {
    local port=$1
    local service_name=$2
    
    if netstat -tlnp | grep -q ":$port "; then
        echo "✅ Port $port ($service_name): LISTENING"
    else
        echo "❌ Port $port ($service_name): NOT LISTENING"
    fi
}

echo "📊 CORE SERVICES STATUS:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
check_service "mariadb" "MariaDB Database"
check_service "lsws" "LiteSpeed Web Server"
check_service "lsmcd" "LiteSpeed Memcached"
check_service "cyberpanel" "CyberPanel Application"
check_service "watchdog" "Watchdog Service"
echo ""

echo "🌐 NETWORK PORTS STATUS:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
check_port "3306" "MariaDB"
check_port "80" "HTTP"
check_port "443" "HTTPS"
check_port "8090" "CyberPanel"
check_port "7080" "LiteSpeed Admin"
check_port "11211" "Memcached"
echo ""

echo "🔧 PHP VERSIONS STATUS:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
for php_version in lsphp82 lsphp83 lsphp84; do
    if [ -d "/usr/local/lsws/$php_version" ]; then
        echo "✅ $php_version: INSTALLED"
        if [ -f "/usr/local/lsws/$php_version/bin/php" ]; then
            php_version_output=$("/usr/local/lsws/$php_version/bin/php" -v 2>/dev/null | head -n1)
            echo "   Version: $php_version_output"
        fi
    else
        echo "❌ $php_version: NOT INSTALLED"
    fi
done
echo ""

echo "🗄️  DATABASE CONNECTION TEST:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
if systemctl is-active --quiet mariadb; then
    if mysql -u root -p1234567 -e "SELECT 1;" >/dev/null 2>&1; then
        echo "✅ MariaDB Root Connection: SUCCESS"
    else
        echo "❌ MariaDB Root Connection: FAILED"
    fi
    
    if mysql -u cyberpanel -pcyberpanel -e "SELECT 1;" >/dev/null 2>&1; then
        echo "✅ CyberPanel DB Connection: SUCCESS"
    else
        echo "❌ CyberPanel DB Connection: FAILED"
    fi
else
    echo "❌ MariaDB: NOT RUNNING"
fi
echo ""

echo "📁 CRITICAL DIRECTORIES:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
directories=(
    "/usr/local/lsws"
    "/usr/local/CyberCP"
    "/etc/cyberpanel"
    "/var/lib/lsphp"
    "/home/cyberpanel"
)

for dir in "${directories[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir: EXISTS"
    else
        echo "❌ $dir: MISSING"
    fi
done
echo ""

echo "🔐 SSL CERTIFICATES:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
if [ -f "/usr/local/lsws/admin/conf/cert/admin.crt" ]; then
    echo "✅ LiteSpeed Admin SSL: EXISTS"
else
    echo "❌ LiteSpeed Admin SSL: MISSING"
fi

if [ -f "/usr/local/lsws/conf/cert.pem" ]; then
    echo "✅ LiteSpeed SSL: EXISTS"
else
    echo "❌ LiteSpeed SSL: MISSING"
fi
echo ""

echo "💾 DISK USAGE:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
df -h / | tail -n1 | awk '{print "Root Filesystem: " $3 "/" $2 " (" $5 " used)"}'
echo ""

echo "🧠 MEMORY USAGE:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
free -h | grep "Mem:" | awk '{print "Memory: " $3 "/" $2 " (" int($3/$2*100) "% used)"}'
echo ""

echo "⚠️  INSTALLATION ISSUES DETECTED:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
echo "1. Database connection error for 'cyberpanel' user"
echo "2. SSL certificate generation failed"
echo "3. LiteSpeed service configuration issues"
echo "4. Missing admin console files"
echo ""

echo "🛠️  RECOMMENDED ACTIONS BEFORE RESTART:"
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"
echo "1. Fix database user permissions"
echo "2. Regenerate SSL certificates"
echo "3. Reconfigure LiteSpeed service"
echo "4. Verify all critical files exist"
echo ""

echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                                               ║"
echo "║                    🎯 READY FOR SERVER RESTART? 🎯                                                         ║"
echo "║                                                                                                               ║"
echo "║  Run this script to check service status after restart:                                                      ║"
echo "║  ./service_status_check.sh                                                                                   ║"
echo "║                                                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
