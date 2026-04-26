#!/usr/bin/env bash
# CyberPanel install – apply_fixes, show_status_summary. Sourced by cyberpanel.sh.

_get_cyberpanel_admin_password() {
    local password=""

    if [ -f "/root/.cyberpanel_password" ]; then
        password=$(tr -d '\r\n' < /root/.cyberpanel_password 2>/dev/null)
    fi

    if [ -z "$password" ] && [ -f "/root/cyberpanel-admin-password.txt" ]; then
        password=$(sed -n 's/^password=//p' /root/cyberpanel-admin-password.txt 2>/dev/null | tail -1 | tr -d '\r\n')
    fi

    if [ -z "$password" ] && [ -f "/etc/cyberpanel/adminPass" ]; then
        password=$(tr -d '\r\n' < /etc/cyberpanel/adminPass 2>/dev/null)
    fi

    if [ -z "$password" ] && [ -f "/var/log/CyberPanel/install_output.log" ]; then
        password=$(grep -E "Panel password:|Password:" /var/log/CyberPanel/install_output.log 2>/dev/null | tail -1 | awk '{print $NF}')
    fi

    if [ -z "$password" ]; then
        password="1234567"
    fi

    printf '%s' "$password"
}

_write_cyberpanel_admin_credentials() {
    local server_ip="$1"
    local admin_password="$2"

    mkdir -p /root /etc/cyberpanel
    printf '%s\n' "$admin_password" > /root/.cyberpanel_password
    printf '%s\n' "$admin_password" > /etc/cyberpanel/adminPass
    chmod 600 /root/.cyberpanel_password /etc/cyberpanel/adminPass 2>/dev/null || true
    if [ -n "$server_ip" ] && [ "$server_ip" != "your-server-ip" ]; then
        printf 'https://%s:8090\n' "$server_ip" > /etc/cyberpanel/csrf_trusted_origins
        chmod 600 /etc/cyberpanel/csrf_trusted_origins 2>/dev/null || true
    fi

    cat > /root/cyberpanel-admin-password.txt <<EOF
url=https://${server_ip}:8090/
username=admin
password=${admin_password}
EOF
    chmod 600 /root/cyberpanel-admin-password.txt
}

_print_cyberpanel_login_credentials() {
    local server_ip="$1"
    local admin_password="$2"

    echo ""
    echo "==============================================================================================================="
    echo "                                  CYBERPANEL LOGIN CREDENTIALS"
    echo "==============================================================================================================="
    echo "  URL:      https://${server_ip}:8090/"
    echo "  Username: admin"
    echo "  Password: ${admin_password}"
    echo ""
    echo "  Saved to: /root/cyberpanel-admin-password.txt"
    echo "  Note: Browsers may warn about the default self-signed SSL certificate until you issue a valid certificate."
    echo "==============================================================================================================="
    echo ""
}

_ensure_webmail_static_under_public() {
    local src="/usr/local/CyberCP/webmail/static/webmail"
    local dst="/usr/local/CyberCP/public/static/webmail"

    if [ -f "${dst}/webmail.js" ] && [ -f "${dst}/webmail.css" ]; then
        return 0
    fi

    if [ -d "$src" ]; then
        mkdir -p "$dst"
        cp -a "${src}/." "$dst/" 2>/dev/null || true
        chown -R lscpd:lscpd "$dst" 2>/dev/null || true
        chmod 644 "${dst}/"*.js "${dst}/"*.css 2>/dev/null || true
    fi
}

_ensure_snappymail_admin_password() {
    local server_ip="$1"
    local admin_password_plain="$2"
    local cfg="/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/application.ini"
    local phpbin=""

    [ -f "$cfg" ] || return 0
    [ -n "$admin_password_plain" ] || return 0

    if ! grep -qE '^[[:space:]]*admin_password[[:space:]]*=[[:space:]]*\"\"[[:space:]]*$' "$cfg" 2>/dev/null; then
        # Password already set (hashed). Still persist the plain password for the admin to retrieve.
        :
    else
        if [ -x /usr/local/lsws/lsphp83/bin/php ]; then
            phpbin="/usr/local/lsws/lsphp83/bin/php"
        elif command -v php >/dev/null 2>&1; then
            phpbin="$(command -v php)"
        fi

        if [ -n "$phpbin" ]; then
            local hash=""
            hash=$(PASS="$admin_password_plain" "$phpbin" -r 'echo password_hash(getenv("PASS"), PASSWORD_DEFAULT);' 2>/dev/null) || hash=""
            if [ -n "$hash" ]; then
                HASH="$hash" python3 - <<'PY' 2>/dev/null || true
import os
from pathlib import Path

cfg = Path("/usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/application.ini")
hashv = os.environ.get("HASH", "")
if not hashv:
    raise SystemExit(0)

lines = cfg.read_text(encoding="utf-8", errors="replace").splitlines(True)
out = []
for line in lines:
    if line.strip().startswith("admin_password"):
        out.append(f'admin_password = "{hashv}"\n')
    else:
        out.append(line)
cfg.write_text("".join(out), encoding="utf-8")
PY
            fi
        fi
    fi

    mkdir -p /etc/cyberpanel /root
    printf '%s\n' "$admin_password_plain" > /etc/cyberpanel/snappymailAdminPass
    chmod 600 /etc/cyberpanel/snappymailAdminPass 2>/dev/null || true

    cat > /root/snappymail-admin-password.txt <<EOF
url=https://${server_ip}:8090/snappymail/?admin
username=admin
password=${admin_password_plain}
EOF
    chmod 600 /root/snappymail-admin-password.txt 2>/dev/null || true
}

_print_snappymail_admin_credentials() {
    local server_ip="$1"
    local admin_password_plain="$2"

    [ -n "$admin_password_plain" ] || return 0

    echo ""
    echo "==============================================================================================================="
    echo "                               SNAPPYMAIL ADMIN PANEL CREDENTIALS"
    echo "==============================================================================================================="
    echo "  URL:      https://${server_ip}:8090/snappymail/?admin"
    echo "  Username: admin"
    echo "  Password: ${admin_password_plain}"
    echo ""
    echo "  Saved to: /root/snappymail-admin-password.txt"
    echo "==============================================================================================================="
    echo ""
}

apply_fixes() {
    echo ""
    echo "Applying post-installation configurations..."

    # Get the actual password that was generated during installation
    local admin_password=""
    admin_password=$(_get_cyberpanel_admin_password)

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
    local server_ip=$(curl -4 -s ifconfig.me 2>/dev/null || curl -s ifconfig.me 2>/dev/null || echo "your-server-ip")
    local admin_password
    admin_password=$(_get_cyberpanel_admin_password)
    _write_cyberpanel_admin_credentials "$server_ip" "$admin_password"
    _print_cyberpanel_login_credentials "$server_ip" "$admin_password"

    # Fix missing /static/webmail/webmail.js and set SnappyMail admin password for /snappymail/?admin
    _ensure_webmail_static_under_public
    _ensure_snappymail_admin_password "$server_ip" "$admin_password"
    _print_snappymail_admin_credentials "$server_ip" "$admin_password"

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
