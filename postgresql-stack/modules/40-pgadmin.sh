#!/usr/bin/env bash
# Install pgAdmin4 web and run via gunicorn (systemd).
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=../lib/common.sh
source "${STACK_ROOT}/lib/common.sh"

load_config

PGADMIN_EMAIL="$(cfg_get pgadmin_email)"
PGADMIN_PASS="$(cfg_get pgadmin_password)"
BIND_HOST="$(cfg_get pgadmin_bind_host)"
BIND_PORT="$(cfg_get pgadmin_bind_port)"
PGADMIN_DOMAIN="$(cfg_get pgadmin_domain)"
PGADMIN_WEB="/usr/pgadmin4/web"
PGADMIN_VENV="/usr/pgadmin4/venv/bin"
LOCAL_CFG="${PGADMIN_WEB}/config_local.py"
# shellcheck source=../lib/pgadmin_env.sh
source "${STACK_ROOT}/lib/pgadmin_env.sh"

install_pgadmin_repo() {
    if rpm -q pgadmin4-web >/dev/null 2>&1; then
        log_info "pgadmin4-web already installed."
        return 0
    fi
    log_info "Installing pgAdmin 4 repository and packages..."
    if ! rpm -q pgadmin4-redhat-repo >/dev/null 2>&1; then
        retry 3 5 dnf install -y \
            "https://ftp.postgresql.org/pub/pgadmin/pgadmin4/yum/pgadmin4-redhat-repo-2-1.noarch.rpm"
    fi
    retry 3 10 dnf install -y pgadmin4-web python3-gunicorn
}

configure_pgadmin_local() {
    log_info "Writing pgAdmin local config (${LOCAL_CFG})..."
    cat > "${LOCAL_CFG}" <<EOF
# Managed by postgresql-stack installer
DEFAULT_SERVER = '0.0.0.0'
MASTER_PASSWORD_REQUIRED = False
WTF_CSRF_ENABLED = True
SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'
LOG_FILE = '/var/log/pgadmin/pgadmin.log'
SERVER_MODE = True
# Disabled so the one-click SSO launcher session is not invalidated when the
# login (performed server-side over loopback) and the browser present a
# different IP/User-Agent. Cookies remain Secure + HttpOnly + SameSite=Lax.
ENHANCED_COOKIE_PROTECTION = False
ALLOW_SPECIAL_EMAIL_DOMAINS = []
ALLOW_SPECIAL_EMAIL_ADDRESSES = ['${PGADMIN_EMAIL}']
EOF
    chmod 640 "${LOCAL_CFG}"
    chown root:apache "${LOCAL_CFG}" 2>/dev/null || chmod 644 "${LOCAL_CFG}"
    mkdir -p /var/log/pgadmin4 /var/log/pgadmin /var/lib/pgadmin
    chown -R apache:apache /var/log/pgadmin4 /var/log/pgadmin /var/lib/pgadmin 2>/dev/null || true
    chmod 750 /var/log/pgadmin4 /var/log/pgadmin /var/lib/pgadmin
}

setup_pgadmin_user() {
    log_info "Initializing pgAdmin database and admin user..."
    mkdir -p /var/log/pgadmin /var/lib/pgadmin
    chown apache:apache /var/log/pgadmin /var/lib/pgadmin 2>/dev/null || true
    chmod 750 /var/log/pgadmin /var/lib/pgadmin

    export PGADMIN_SETUP_EMAIL="${PGADMIN_EMAIL}"
    export PGADMIN_SETUP_PASSWORD="${PGADMIN_PASS}"

    local db_ok=0
    if [[ -f /var/lib/pgadmin/pgadmin4.db ]]; then
        if pgadmin_python get-users --json >/dev/null 2>&1; then
            db_ok=1
            log_info "pgAdmin SQLite DB already exists and is valid."
        else
            log_warn "pgAdmin DB invalid; backing up and reinitializing..."
            mv /var/lib/pgadmin/pgadmin4.db "/var/lib/pgadmin/pgadmin4.db.bak.$(date +%Y%m%d%H%M%S)"
        fi
    fi

    if [[ "${db_ok}" -eq 0 ]]; then
        pgadmin_python setup-db
        chown apache:apache /var/lib/pgadmin/pgadmin4.db 2>/dev/null || true
        chmod 600 /var/lib/pgadmin/pgadmin4.db 2>/dev/null || true
    fi

    if ! pgadmin_python get-users --json 2>/dev/null | grep -q "${PGADMIN_EMAIL}"; then
        pgadmin_python add-user "${PGADMIN_EMAIL}" "${PGADMIN_PASS}" --admin
    else
        log_info "pgAdmin user ${PGADMIN_EMAIL} already exists."
    fi
}

install_systemd_unit() {
    local gunicorn_py="${PGADMIN_VENV}/python3"
    log_info "Installing pgadmin4.service (gunicorn on ${BIND_HOST}:${BIND_PORT})..."
    cat > /etc/systemd/system/pgadmin4.service <<EOF
[Unit]
Description=pgAdmin 4 web (gunicorn)
After=network.target postgresql.service

[Service]
Type=simple
User=apache
Group=apache
WorkingDirectory=${PGADMIN_WEB}
Environment=PYTHONPATH=${PGADMIN_WEB}
ExecStart=${gunicorn_py} -m gunicorn --bind ${BIND_HOST}:${BIND_PORT} --workers 2 --threads 4 --timeout 120 --chdir ${STACK_ROOT}/lib pgadmin_wsgi:application
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable pgadmin4
    systemctl restart pgadmin4
    retry 10 5 systemctl is-active --quiet pgadmin4
}

install_pgadmin_repo
configure_pgadmin_local
setup_pgadmin_user
install_systemd_unit

code="$(curl -sk -o /dev/null -w '%{http_code}' "http://${BIND_HOST}:${BIND_PORT}/login" 2>/dev/null || echo 000)"
if echo "${code}" | grep -qE '200|302|301'; then
    log_info "pgAdmin responding on http://${BIND_HOST}:${BIND_PORT}/ (HTTP ${code})"
else
    log_warn "pgAdmin may still be starting (HTTP ${code}); check: journalctl -u pgadmin4 -n 50"
fi

log_info "pgAdmin installed. Public URL after proxy: https://${PGADMIN_DOMAIN}/"
