#!/bin/bash
# Deploy Email Limits fix to a CyberPanel installation.
# Copies recommended mailServer files and optionally restarts lscpd.
#
# Usage (run from anywhere):
#   sudo bash /home/cyberpanel-repo/deploy-email-limits-fix.sh
#   sudo bash deploy-email-limits-fix.sh [REPO_DIR] [CP_DIR]
#
# Or from repo root: cd /home/cyberpanel-repo && sudo bash deploy-email-limits-fix.sh

set -e

log() { echo "[$(date +%Y-%m-%d\ %H:%M:%S)] $*"; }
err() { log "ERROR: $*" >&2; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" 2>/dev/null && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/../.." && pwd)}"

# Resolve REPO_DIR: explicit arg, then repo root, then common locations
if [[ -n "$1" && -d "$1/mailServer" ]]; then
    REPO_DIR="$1"
    shift
elif [[ -d "$REPO_ROOT/mailServer" ]]; then
    REPO_DIR="$REPO_ROOT"
elif [[ -d "/home/cyberpanel-repo/mailServer" ]]; then
    REPO_DIR="/home/cyberpanel-repo"
elif [[ -d "./mailServer" ]]; then
    REPO_DIR="$(pwd)"
else
    err "Repo not found. Use: sudo bash /home/cyberpanel-repo/deploy-email-limits-fix.sh"
    err "Or: cd /path/to/cyberpanel-repo && sudo bash deploy-email-limits-fix.sh"
    exit 1
fi

CP_DIR="${1:-/usr/local/CyberCP}"
RESTART_LSCPD="${RESTART_LSCPD:-1}"

if [[ ! -d "$CP_DIR" ]]; then
    err "CyberPanel directory not found: $CP_DIR"
    exit 1
fi
if [[ ! -d "$REPO_DIR/mailServer" ]]; then
    err "Repo mailServer not found in: $REPO_DIR"
    exit 1
fi

log "REPO_DIR=$REPO_DIR"
log "CP_DIR=$CP_DIR"

FILES=(
    "mailServer/mailserverManager.py"
    "mailServer/templates/mailServer/EmailLimits.html"
    "mailServer/static/mailServer/mailServer.js"
    "mailServer/static/mailServer/emailLimitsController.js"
)

for rel in "${FILES[@]}"; do
    src="$REPO_DIR/$rel"
    dst="$CP_DIR/$rel"
    if [[ ! -f "$src" ]]; then
        err "Source missing: $src"
        exit 1
    fi
    mkdir -p "$(dirname "$dst")"
    cp -f "$src" "$dst"
    log "Copied: $rel"
done

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

log "Deploy complete. Hard-refresh /email/EmailLimits in the browser (Ctrl+Shift+R)."
