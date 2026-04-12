#!/bin/bash
# Deploy updated templates (and related static) from this repo to live CyberPanel.
# Use after pulling template changes so the panel at /usr/local/CyberCP shows the new UI.
# Usage: sudo bash deploy-templates.sh

set -e

CYBERCP_ROOT="${CYBERCP_ROOT:-/usr/local/CyberCP}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "[$(date +%Y-%m-%d\ %H:%M:%S)] Deploying templates to $CYBERCP_ROOT..."

# userManagment templates
for name in modifyUser createUser; do
    SRC="$SCRIPT_DIR/userManagment/templates/userManagment/${name}.html"
    DST="$CYBERCP_ROOT/userManagment/templates/userManagment/${name}.html"
    if [ -f "$SRC" ]; then
        cp -f "$SRC" "$DST"
        echo "  Copied userManagment ${name}.html"
    fi
done

# loginSystem login template
if [ -f "$SCRIPT_DIR/loginSystem/templates/loginSystem/login.html" ]; then
    cp -f "$SCRIPT_DIR/loginSystem/templates/loginSystem/login.html" \
          "$CYBERCP_ROOT/loginSystem/templates/loginSystem/login.html"
    echo "  Copied loginSystem login.html"
fi

# Optional: userManagment static (if you change JS)
if [ -f "$SCRIPT_DIR/userManagment/static/userManagment/userManagment.js" ]; then
    mkdir -p "$CYBERCP_ROOT/userManagment/static/userManagment"
    cp -f "$SCRIPT_DIR/userManagment/static/userManagment/userManagment.js" \
          "$CYBERCP_ROOT/userManagment/static/userManagment/userManagment.js"
    echo "  Copied userManagment.js"
fi
if [ -f "$SCRIPT_DIR/loginSystem/static/loginSystem/webauthn.js" ]; then
    mkdir -p "$CYBERCP_ROOT/loginSystem/static/loginSystem"
    cp -f "$SCRIPT_DIR/loginSystem/static/loginSystem/webauthn.js" \
          "$CYBERCP_ROOT/loginSystem/static/loginSystem/webauthn.js"
    echo "  Copied webauthn.js"
fi

# Run collectstatic if manage.py exists (so static changes are served)
if [ -f "$CYBERCP_ROOT/manage.py" ]; then
    PYTHON="${CYBERCP_ROOT}/bin/python"
    [ -x "$PYTHON" ] || PYTHON="python3"
    echo "  Running collectstatic..."
    (cd "$CYBERCP_ROOT" && "$PYTHON" manage.py collectstatic --noinput --clear 2>&1) | tail -5
    echo "  Syncing STATIC_ROOT -> public/static for LiteSpeed /static/ (webmail, etc.)..."
    if [ -f "$CYBERCP_ROOT/plogical/panel_static_sync.py" ]; then
        "$PYTHON" "$CYBERCP_ROOT/plogical/panel_static_sync.py" || echo "  (panel_static_sync exited non-zero — check public/static/webmail)"
    else
        echo "  (panel_static_sync.py not found — skip)"
    fi
fi

echo "[$(date +%Y-%m-%d\ %H:%M:%S)] Templates deployed. Hard-refresh (Ctrl+F5) on Modify User / Create User / Login if needed."
