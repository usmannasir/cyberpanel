#!/usr/bin/env bash
# Ensure MariaDB server/client packages and service are present after CyberPanel upgrades.
# Idempotent; safe to run from cron or post-upgrade hooks.

set -euo pipefail

LOG_TAG="ensure-mariadb-server"
log() { echo "[$(date -Iseconds)] ${LOG_TAG}: $*"; }

need_install=0
for pkg in MariaDB-server MariaDB-client; do
    if ! rpm -q "${pkg}" >/dev/null 2>&1; then
        log "Missing package: ${pkg}"
        need_install=1
    fi
done

if [[ "${need_install}" -eq 1 ]]; then
    log "Installing MariaDB-server MariaDB-client MariaDB-devel..."
    dnf install -y MariaDB-server MariaDB-client MariaDB-devel || {
        log "ERROR: dnf install failed"
        exit 1
    }
fi

if ! systemctl is-enabled mariadb >/dev/null 2>&1; then
    log "Enabling mariadb service..."
    systemctl enable mariadb || true
fi

if ! systemctl is-active mariadb >/dev/null 2>&1; then
    log "Starting mariadb service..."
    systemctl start mariadb || {
        log "ERROR: systemctl start mariadb failed"
        exit 1
    }
fi

if command -v mariadb >/dev/null 2>&1; then
    if ! mariadb -e "SELECT 1" >/dev/null 2>&1; then
        log "WARNING: mariadb client cannot run SELECT 1 (auth may require root socket)"
    fi
fi

log "OK: MariaDB packages and service verified"
exit 0
