#!/bin/bash
# Deploy FTP Create Account template fix to a CyberPanel installation.
# Copies the updated createFTPAccount.html and optionally restarts lscpd.
#
# Usage (run from anywhere):
#   sudo bash /home/cyberpanel-repo/deploy-ftp-create-account-fix.sh
#   sudo bash deploy-ftp-create-account-fix.sh [REPO_DIR] [CP_DIR]
#
# Or from repo root: cd /home/cyberpanel-repo && sudo bash deploy-ftp-create-account-fix.sh

set -e

log() { echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*"; }
err() { log "ERROR: $*" >&2; }

# Resolve REPO_DIR
if [[ -n "$1" && -d "$1/ftp" ]]; then
    REPO_DIR="$1"
    shift
elif [[ -d "$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)/ftp" ]]; then
    REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
elif [[ -d "/home/cyberpanel-repo/ftp" ]]; then
    REPO_DIR="/home/cyberpanel-repo"
elif [[ -d "./ftp" ]]; then
    REPO_DIR="$(pwd)"
else
    err "Repo not found. Use: sudo bash /home/cyberpanel-repo/deploy-ftp-create-account-fix.sh"
    exit 1
fi

CP_DIR="${1:-/usr/local/CyberCP}"
RESTART_LSCPD="${RESTART_LSCPD:-1}"

if [[ ! -d "$CP_DIR" ]]; then
    err "CyberPanel directory not found: $CP_DIR"
    exit 1
fi
if [[ ! -f "$REPO_DIR/ftp/templates/ftp/createFTPAccount.html" ]]; then
    err "Source template not found in: $REPO_DIR"
    exit 1
fi

log "REPO_DIR=$REPO_DIR"
log "CP_DIR=$CP_DIR"

SRC="$REPO_DIR/ftp/templates/ftp/createFTPAccount.html"
DST="$CP_DIR/ftp/templates/ftp/createFTPAccount.html"
mkdir -p "$(dirname "$DST")"
cp -f "$SRC" "$DST"
log "Copied: ftp/templates/ftp/createFTPAccount.html"

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

log "Deploy complete. Hard-refresh /ftp/createFTPAccount in the browser (Ctrl+Shift+R)."
