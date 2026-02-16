#!/usr/bin/env bash
# CyberPanel install – apply_fixes, show_status_summary. Sourced by cyberpanel.sh.

apply_fixes() {
    echo ""
    echo "Applying post-installation configurations..."

    # Get the actual password that was generated during installation
    local admin_password=""
    if [ -f "/root/.cyberpanel_password" ]; then
        admin_password=$(cat /root/.cyberpanel_password 2>/dev/null)
    fi

    # If no password was captured, use the default
    if [ -z "$admin_password" ]; then
        admin_password="1234567"
        echo "$admin_password" > /root/.cyberpanel_password
        chmod 600 /root/.cyberpanel_password
    fi

    # Fix database issues
    systemctl start mariadb 2>/dev/null || true
    systemctl enable mariadb 2>/dev/null || true

    # Fix LiteSpeed service only if the web server was actually installed
    if [ -x /usr/local/lsws/bin/lswsctrl ] || [ -x /usr/local/lsws/bin/lsctrl ] || [ -f /usr/local/lsws/bin/openlitespeed ]; then
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
        systemctl start lsws || true
    else
        echo "  • LiteSpeed/OpenLiteSpeed not found at /usr/local/lsws - skipping lsws.service (install may have skipped web server)"
        echo "  • If the installer failed earlier (e.g. Python error), re-run the installer. Once it completes, open ports 8090 and 7080 in your cloud security group (e.g. AWS EC2 Security Group inbound rules)."
        systemctl disable lsws 2>/dev/null || true
        rm -f /etc/systemd/system/lsws.service
        systemctl daemon-reload
    fi

    # Set OpenLiteSpeed admin password to match CyberPanel
    echo "  • Configuring OpenLiteSpeed admin password..."
    if [ -f "/usr/local/lsws/admin/misc/admpass.sh" ]; then
        # Auto-answer the prompts for username and password
        (echo "admin"; echo "$admin_password"; echo "$admin_password") | /usr/local/lsws/admin/misc/admpass.sh >/dev/null 2>&1 || {
            # Alternative method: directly create htpasswd entry
            echo "admin:$(openssl passwd -apr1 '$admin_password')" > /usr/local/lsws/admin/htpasswd 2>/dev/null || true
        }
        echo "  ✓ OpenLiteSpeed configured"
    fi

    # Ensure CyberPanel (lscpd) service is running
    echo "  • Starting CyberPanel service..."
    systemctl enable lscpd 2>/dev/null || true
    systemctl start lscpd 2>/dev/null || true

    # Give services a moment to start
    sleep 3

    # Ensure both 8090 (CyberPanel) and 7080 (LiteSpeed/OLS) are accessible
    echo "  • Ensuring ports 8090 and 7080 are accessible..."
    port_check() {
        local port=$1
        command -v ss >/dev/null 2>&1 && ss -tlnp 2>/dev/null | grep -q ":$port " && return 0
        command -v netstat >/dev/null 2>&1 && netstat -tlnp 2>/dev/null | grep -q ":$port " && return 0
        return 1
    }
    max_attempts=18
    attempt=0
    while [ $attempt -lt $max_attempts ]; do
        need_restart=false
        systemctl is-active --quiet mariadb || { systemctl start mariadb 2>/dev/null; need_restart=true; }
        systemctl is-active --quiet lsws 2>/dev/null || { [ -x /usr/local/lsws/bin/lswsctrl ] && systemctl start lsws 2>/dev/null; need_restart=true; }
        systemctl is-active --quiet lscpd 2>/dev/null || { systemctl start lscpd 2>/dev/null; need_restart=true; }
        [ "$need_restart" = true ] && sleep 5
        if port_check 8090 && port_check 7080; then
            echo "  ✓ Port 8090 (CyberPanel) and 7080 (OpenLiteSpeed) are listening"
            break
        fi
        attempt=$((attempt + 1))
        [ $attempt -lt $max_attempts ] && sleep 5
    done
    if ! port_check 8090 || ! port_check 7080; then
        systemctl start lscpd 2>/dev/null
        systemctl start lsws 2>/dev/null
        sleep 10
        if port_check 8090 && port_check 7080; then
            echo "  ✓ Port 8090 and 7080 are now listening"
        else
            echo "  ⚠ One or both ports not yet listening. Run: systemctl start mariadb lsws lscpd"
            echo "  ⚠ On AWS/cloud: add inbound rules for TCP 8090 and 7080 in the instance security group."
        fi
    fi

    echo "  ✓ Post-installation configurations completed"
}

# Helper: check if a port is listening
_port_listening() {
    local port=$1
    command -v ss >/dev/null 2>&1 && ss -tlnp 2>/dev/null | grep -q ":$port " && return 0
    command -v netstat >/dev/null 2>&1 && netstat -tlnp 2>/dev/null | grep -q ":$port " && return 0
    return 1
}

# Function to show status summary
show_status_summary() {
    # Last-chance: try to start services so 8090 and 7080 are accessible
    if ! _port_listening 8090 || ! _port_listening 7080; then
        systemctl start mariadb 2>/dev/null || true
        systemctl start lsws 2>/dev/null || true
        systemctl start lscpd 2>/dev/null || true
        sleep 8
    fi

    echo "==============================================================================================================="
    echo "                                    FINAL STATUS CHECK"
    echo "==============================================================================================================="
    echo ""

    # Quick service check
    local all_services_running=true

    echo "Service Status:"
    if systemctl is-active --quiet mariadb; then
        echo "  ✓ MariaDB Database - Running"
    else
        echo "  ✗ MariaDB Database - Not Running"
        all_services_running=false
    fi

    if systemctl is-active --quiet lsws; then
        echo "  ✓ LiteSpeed Web Server - Running"
    else
        echo "  ✗ LiteSpeed Web Server - Not Running"
        all_services_running=false
    fi

    if systemctl is-active --quiet lscpd; then
        echo "  ✓ CyberPanel Application - Running"
    else
        echo "  ✗ CyberPanel Application - Not Running (may take a moment to start)"
        all_services_running=false
    fi

    echo ""
    echo "Port Accessibility:"
    if _port_listening 8090; then
        echo "  ✓ Port 8090 (CyberPanel) - Accessible"
    else
        echo "  ✗ Port 8090 (CyberPanel) - Not listening (run: systemctl start lscpd)"
        all_services_running=false
    fi
    if _port_listening 7080; then
        echo "  ✓ Port 7080 (OpenLiteSpeed) - Accessible"
    else
        echo "  ✗ Port 7080 (OpenLiteSpeed) - Not listening (run: systemctl start lsws)"
        all_services_running=false
    fi

    # Get the actual password that was set
    local admin_password=""
    local server_ip=$(curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")

    # Check if password was set in /root/.cyberpanel_password (if it exists)
    if [ -f "/root/.cyberpanel_password" ]; then
        admin_password=$(cat /root/.cyberpanel_password 2>/dev/null)
    fi

    # If we have a password, show access details
    if [ -n "$admin_password" ]; then
        echo ""
        echo "Access Details:"
        echo "  CyberPanel: https://$server_ip:8090"
        echo "  Username: admin"
        echo "  Password: $admin_password"
        echo ""
        echo "  OpenLiteSpeed: https://$server_ip:7080"
        echo "  Username: admin"
        echo "  Password: $admin_password"
    fi

    echo ""
    echo "==============================================================================================================="

    if [ "$all_services_running" = true ]; then
        echo "✓ Installation completed successfully! Ports 8090 and 7080 are accessible."
    else
        echo "⚠ Installation completed with warnings. Some services may need attention."
    fi
    echo ""
}

# Function to show main menu
