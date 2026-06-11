#!/usr/bin/env bash
# Grant cyberpanel user filesystem access for OLS + Apache hybrid vhost management.
# Idempotent; safe to run on every install/upgrade.

set -u

LOG_FILE="/var/log/cyberpanel_apache_permissions.log"

log_msg() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"
}

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    log_msg "ERROR: must run as root"
    exit 1
fi

if ! id cyberpanel >/dev/null 2>&1; then
    log_msg "cyberpanel user not found; skipping"
    exit 0
fi

if ! command -v setfacl >/dev/null 2>&1; then
    log_msg "setfacl not available; skipping ACL setup"
    exit 0
fi

apply_acl() {
    local path="$1"
    if [[ -d "$path" ]]; then
        if setfacl -m u:cyberpanel:rwx "$path" 2>/dev/null; then
            log_msg "ACL applied: $path"
        else
            log_msg "WARN: could not set ACL on $path"
        fi
    fi
}

apply_acl /etc/httpd/conf.d
apply_acl /etc/httpd/conf.d/ssl

for pool_dir in /etc/opt/remi/php*/php-fpm.d/; do
    [[ -d "$pool_dir" ]] && apply_acl "$pool_dir"
done

apply_acl /etc/apache2/sites-enabled
apply_acl /etc/apache2/conf-enabled

mkdir -p /etc/letsencrypt/accounts 2>/dev/null || true
if [[ -d /etc/letsencrypt/accounts ]]; then
    setfacl -m u:cyberpanel:rwx /etc/letsencrypt/accounts 2>/dev/null || true
    setfacl -d -m u:cyberpanel:rwx /etc/letsencrypt/accounts 2>/dev/null || true
    log_msg "ACL applied: /etc/letsencrypt/accounts"
fi

if getent group lsadm >/dev/null 2>&1; then
    if id -nG cyberpanel 2>/dev/null | tr ' ' '\n' | grep -qx lsadm; then
        log_msg "cyberpanel already in lsadm group"
    elif usermod -aG lsadm cyberpanel 2>/dev/null; then
        log_msg "Added cyberpanel to lsadm group"
    else
        log_msg "WARN: could not add cyberpanel to lsadm"
    fi
fi

log_msg "Apache permission setup complete"
exit 0
