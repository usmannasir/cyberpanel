#!/bin/bash
# Deploy Create User page fix (userCreationFailed / "Unknown error" on load)
# Run this on the CyberPanel server (e.g. after pulling repo or copying fixed files)
# Usage: sudo bash deploy-createuser-fix.sh

set -e

CYBERCP_ROOT="${CYBERCP_ROOT:-/usr/local/CyberCP}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PYTHON="${CYBERCP_ROOT}/bin/python"
if [ ! -x "$PYTHON" ]; then
    PYTHON="python3"
fi

echo "[$(date +%Y-%m-%d\ %H:%M:%S)] Deploying Create User fix..."

# If running from repo (this workspace), copy fixed JS into CyberCP
if [ -f "$SCRIPT_DIR/userManagment/static/userManagment/userManagment.js" ]; then
    echo "  Copying userManagment.js from repo app static..."
    mkdir -p "$CYBERCP_ROOT/userManagment/static/userManagment"
    cp -f "$SCRIPT_DIR/userManagment/static/userManagment/userManagment.js" \
          "$CYBERCP_ROOT/userManagment/static/userManagment/userManagment.js"
fi
if [ -f "$SCRIPT_DIR/static/userManagment/userManagment.js" ]; then
    echo "  Copying userManagment.js from repo static..."
    mkdir -p "$CYBERCP_ROOT/static/userManagment"
    cp -f "$SCRIPT_DIR/static/userManagment/userManagment.js" \
          "$CYBERCP_ROOT/static/userManagment/userManagment.js"
fi
if [ -f "$SCRIPT_DIR/public/static/userManagment/userManagment.js" ]; then
    echo "  Copying userManagment.js from repo public/static..."
    mkdir -p "$CYBERCP_ROOT/public/static/userManagment"
    cp -f "$SCRIPT_DIR/public/static/userManagment/userManagment.js" \
          "$CYBERCP_ROOT/public/static/userManagment/userManagment.js"
fi

# Run collectstatic so served static gets the fix
if [ -f "$CYBERCP_ROOT/manage.py" ]; then
    echo "  Running collectstatic..."
    cd "$CYBERCP_ROOT"
    "$PYTHON" manage.py collectstatic --noinput --clear 2>&1 | tail -5
    echo "  collectstatic done."
    if [ -x "$PYTHON" ] && [ -f "$CYBERCP_ROOT/plogical/panel_static_sync.py" ]; then
        echo "  Syncing panel static for LiteSpeed (/public/static/)..."
        "$PYTHON" "$CYBERCP_ROOT/plogical/panel_static_sync.py" || true
    fi
else
    echo "  No $CYBERCP_ROOT/manage.py found; skipping collectstatic."
fi

echo "[$(date +%Y-%m-%d\ %H:%M:%S)] Create User fix deployed. Hard-refresh browser (Ctrl+F5) on the Create User page."
