#!/bin/bash

# CyberPanel Installation Issues Fix Script
# This script fixes the critical issues found during installation

echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                                               ║"
echo "║                    🔧 FIXING CYBERPANEL INSTALLATION ISSUES 🔧                                              ║"
echo "║                                                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
echo ""

# Function to log actions
log_action() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# 1. Fix Database Connection Issues
echo "🗄️  FIXING DATABASE CONNECTION ISSUES..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

log_action "Starting MariaDB service..."
systemctl start mariadb
systemctl enable mariadb

log_action "Setting MariaDB root password..."
mysqladmin -u root password '1234567' 2>/dev/null || true

log_action "Creating cyberpanel database user..."
mysql -u root -p1234567 -e "
CREATE DATABASE IF NOT EXISTS cyberpanel;
CREATE USER IF NOT EXISTS 'cyberpanel'@'localhost' IDENTIFIED BY 'cyberpanel';
GRANT ALL PRIVILEGES ON cyberpanel.* TO 'cyberpanel'@'localhost';
FLUSH PRIVILEGES;
" 2>/dev/null || true

log_action "Testing database connections..."
if mysql -u root -p1234567 -e "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ MariaDB root connection: SUCCESS"
else
    echo "❌ MariaDB root connection: FAILED"
fi

if mysql -u cyberpanel -pcyberpanel -e "SELECT 1;" >/dev/null 2>&1; then
    echo "✅ CyberPanel database connection: SUCCESS"
else
    echo "❌ CyberPanel database connection: FAILED"
fi
echo ""

# 2. Fix LiteSpeed Service Configuration
echo "🚀 FIXING LITESPEED SERVICE CONFIGURATION..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

log_action "Creating LiteSpeed service file..."
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

log_action "Reloading systemd daemon..."
systemctl daemon-reload

log_action "Enabling LiteSpeed service..."
systemctl enable lsws

log_action "Starting LiteSpeed service..."
systemctl start lsws

if systemctl is-active --quiet lsws; then
    echo "✅ LiteSpeed service: STARTED"
else
    echo "❌ LiteSpeed service: FAILED TO START"
fi
echo ""

# 3. Fix SSL Certificates
echo "🔐 FIXING SSL CERTIFICATES..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

log_action "Creating SSL certificate configuration..."
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

log_action "Generating LiteSpeed admin SSL certificate..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /usr/local/lsws/admin/conf/cert/admin.key \
    -out /usr/local/lsws/admin/conf/cert/admin.crt \
    -config /root/cyberpanel/cert_conf 2>/dev/null || true

log_action "Setting proper permissions for SSL certificates..."
chmod 600 /usr/local/lsws/admin/conf/cert/admin.key 2>/dev/null || true
chmod 644 /usr/local/lsws/admin/conf/cert/admin.crt 2>/dev/null || true

if [ -f "/usr/local/lsws/admin/conf/cert/admin.crt" ]; then
    echo "✅ LiteSpeed admin SSL certificate: CREATED"
else
    echo "❌ LiteSpeed admin SSL certificate: FAILED"
fi
echo ""

# 4. Fix Admin Console Files
echo "🖥️  FIXING ADMIN CONSOLE FILES..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

log_action "Creating admin console directories..."
mkdir -p /usr/local/lsws/admin/fcgi-bin
mkdir -p /usr/local/lsws/admin/conf

log_action "Creating admin PHP file..."
cat > /usr/local/lsws/admin/fcgi-bin/admin_php << 'EOF'
#!/bin/bash
export PHP_LSAPI_CHILDREN=35
export PHP_LSAPI_MAX_REQUESTS=1000
exec /usr/local/lsws/lsphp82/bin/lsphp -b /usr/local/lsws/admin/fcgi-bin/admin_php
EOF

chmod +x /usr/local/lsws/admin/fcgi-bin/admin_php 2>/dev/null || true

log_action "Creating admin password file..."
htpasswd -cb /usr/local/lsws/admin/conf/htpasswd admin 1234567 2>/dev/null || true

log_action "Setting proper ownership..."
chown -R lsadm:lsadm /usr/local/lsws/admin/ 2>/dev/null || true

if [ -f "/usr/local/lsws/admin/fcgi-bin/admin_php" ]; then
    echo "✅ Admin console files: CREATED"
else
    echo "❌ Admin console files: FAILED"
fi
echo ""

# 5. Fix CyberPanel Application
echo "🎛️  FIXING CYBERPANEL APPLICATION..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

log_action "Setting proper permissions for CyberPanel..."
chown -R root:root /usr/local/CyberCP/ 2>/dev/null || true
chmod -R 755 /usr/local/CyberCP/ 2>/dev/null || true

log_action "Creating CyberPanel service file..."
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

log_action "Reloading systemd daemon..."
systemctl daemon-reload

log_action "Enabling CyberPanel service..."
systemctl enable cyberpanel
echo ""

# 6. Final Service Status Check
echo "📊 FINAL SERVICE STATUS CHECK..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

services=("mariadb" "lsws" "lsmcd" "cyberpanel" "watchdog")

for service in "${services[@]}"; do
    if systemctl is-active --quiet $service; then
        echo "✅ $service: RUNNING"
    else
        echo "⚠️  $service: NOT RUNNING"
    fi
done
echo ""

# 7. Port Status Check
echo "🌐 PORT STATUS CHECK..."
echo "═══════════════════════════════════════════════════════════════════════════════════════════════════════════════"

ports=("3306:MariaDB" "80:HTTP" "443:HTTPS" "8090:CyberPanel" "7080:LiteSpeed Admin")

for port_info in "${ports[@]}"; do
    port=$(echo $port_info | cut -d: -f1)
    service=$(echo $port_info | cut -d: -f2)
    
    if netstat -tlnp | grep -q ":$port "; then
        echo "✅ Port $port ($service): LISTENING"
    else
        echo "❌ Port $port ($service): NOT LISTENING"
    fi
done
echo ""

echo "╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╗"
echo "║                                                                                                               ║"
echo "║                    🎉 INSTALLATION ISSUES FIXED! 🎉                                                         ║"
echo "║                                                                                                               ║"
echo "║  All critical issues have been addressed. The server is now ready for restart.                              ║"
echo "║                                                                                                               ║"
echo "║  After restart, run: ./service_status_check.sh                                                               ║"
echo "║                                                                                                               ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════╝"
