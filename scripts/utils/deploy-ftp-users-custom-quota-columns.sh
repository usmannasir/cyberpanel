#!/bin/bash
# Add missing custom_quota_enabled / custom_quota_size columns to ftp Users table (users).
# Fixes: (1054, "Unknown column 'custom_quota_enabled' in 'INSERT INTO'") on FTP account creation.
#
# Usage:
#   sudo bash /home/cyberpanel-repo/deploy-ftp-users-custom-quota-columns.sh
#   sudo bash deploy-ftp-users-custom-quota-columns.sh [REPO_DIR] [CP_DIR]

set -e

log() { echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*"; }
err() { log "ERROR: $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Resolve REPO_DIR
if [[ -n "$1" && -f "$1/CPScripts/ensure_ftp_users_quota_columns.py" ]]; then
    REPO_DIR="$1"
    shift
elif [[ -f "$REPO_ROOT/CPScripts/ensure_ftp_users_quota_columns.py" ]]; then
    REPO_DIR="$REPO_ROOT"
elif [[ -f "/home/cyberpanel-repo/CPScripts/ensure_ftp_users_quota_columns.py" ]]; then
    REPO_DIR="/home/cyberpanel-repo"
elif [[ -f "./CPScripts/ensure_ftp_users_quota_columns.py" ]]; then
    REPO_DIR="$(pwd)"
else
    err "CPScripts/ensure_ftp_users_quota_columns.py not found."
    exit 1
fi

CP_DIR="${1:-/usr/local/CyberCP}"
RESTART_LSCPD="${RESTART_LSCPD:-1}"

if [[ ! -d "$CP_DIR" ]]; then
    err "CyberPanel directory not found: $CP_DIR"
    exit 1
fi

log "REPO_DIR=$REPO_DIR"
log "CP_DIR=$CP_DIR"

mkdir -p "$CP_DIR/CPScripts"
cp -f "$REPO_DIR/CPScripts/ensure_ftp_users_quota_columns.py" "$CP_DIR/CPScripts/ensure_ftp_users_quota_columns.py"
chmod 644 "$CP_DIR/CPScripts/ensure_ftp_users_quota_columns.py"
log "Copied ensure_ftp_users_quota_columns.py to $CP_DIR/CPScripts/"

log "Ensuring FTP users table has custom quota columns..."
export CP_DIR
PY="$CP_DIR/bin/python"
if [[ -x "$PY" ]]; then
    "$PY" "$CP_DIR/CPScripts/ensure_ftp_users_quota_columns.py" "$CP_DIR" || { err "Python repair failed"; exit 1; }
else
    python3 "$CP_DIR/CPScripts/ensure_ftp_users_quota_columns.py" "$CP_DIR" || { err "Python repair failed"; exit 1; }
fi

if [[ "$RESTART_LSCPD" =~ ^(1|yes|true)$ ]]; then
    if systemctl is-active --quiet lscpd 2>/dev/null; then
        log "Restarting lscpd..."
        systemctl restart lscpd || { err "lscpd restart failed"; exit 1; }
        log "lscpd restarted."
    else
        log "lscpd not running or not a systemd service; skip restart."
    fi
else
    log "Skipping restart (set RESTART_LSCPD=1 to restart lscpd)."
fi

log "Deploy complete. Test: Websites → FTP → Create FTP Account."
