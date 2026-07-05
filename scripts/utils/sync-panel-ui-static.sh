#!/usr/bin/env bash
# Sync panel UI assets (dark mode CSS stack, mailServer.js) to served static paths.
# Called after git sync on upgrade/install so v2.5.5-dev UI fixes reach public/static.
# Usage: bash /usr/local/CyberCP/scripts/utils/sync-panel-ui-static.sh [--collectstatic]
set -euo pipefail

LOG="${LOG:-/var/log/cyberpanel_upgrade_debug.log}"
CP="${CP:-/usr/local/CyberCP}"
RUN_COLLECTSTATIC=0
if [[ "${1:-}" == "--collectstatic" ]]; then
    RUN_COLLECTSTATIC=1
fi

log() {
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] sync-panel-ui-static: $*" | tee -a "$LOG"
}

if [[ ! -d "$CP" ]]; then
    log "ERROR: CyberCP root not found: $CP"
    exit 1
fi

# baseTemplate CSS/JS (cyberpanel-ui, tokens, harmonize, dark)
if [[ -d "$CP/baseTemplate/static/baseTemplate" ]]; then
    mkdir -p "$CP/public/static/baseTemplate" "$CP/static/baseTemplate"
    rsync -a "$CP/baseTemplate/static/baseTemplate/" "$CP/public/static/baseTemplate/" 2>/dev/null || \
        cp -a "$CP/baseTemplate/static/baseTemplate/." "$CP/public/static/baseTemplate/" 2>/dev/null || true
    rsync -a "$CP/baseTemplate/static/baseTemplate/" "$CP/static/baseTemplate/" 2>/dev/null || \
        cp -a "$CP/baseTemplate/static/baseTemplate/." "$CP/static/baseTemplate/" 2>/dev/null || true
    log "Synced baseTemplate static"
fi

# mailServer.js (list emails disk badge, email forwarding UI)
if [[ -f "$CP/mailServer/static/mailServer/mailServer.js" ]]; then
    mkdir -p "$CP/public/static/mailServer" "$CP/static/mailServer"
    cp -f "$CP/mailServer/static/mailServer/mailServer.js" "$CP/public/static/mailServer/mailServer.js"
    cp -f "$CP/mailServer/static/mailServer/mailServer.js" "$CP/static/mailServer/mailServer.js"
    log "Synced mailServer.js"
fi

# Verify dark-mode stack is present where LiteSpeed serves /static/
THEME_CSS=(
    "baseTemplate/css/cyberpanel-ui.css"
    "baseTemplate/css/cyberpanel-tokens.css"
    "baseTemplate/css/cyberpanel-harmonize.css"
    "baseTemplate/css/cyberpanel-dark.css"
)
MISSING=0
for rel in "${THEME_CSS[@]}"; do
    if [[ ! -f "$CP/public/static/$rel" ]]; then
        log "WARNING: missing public/static/$rel"
        MISSING=1
    fi
done

if [[ "$MISSING" -eq 1 ]] || [[ "$RUN_COLLECTSTATIC" -eq 1 ]]; then
    PY=""
    for candidate in "$CP/bin/python" python3 python; do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import django" 2>/dev/null; then
            PY="$candidate"
            break
        fi
    done
    if [[ -n "$PY" ]]; then
        log "Running collectstatic (theme assets missing or --collectstatic)"
        (
            cd "$CP"
            export DJANGO_SETTINGS_MODULE=CyberCP.settings
            "$PY" manage.py collectstatic --noinput 2>&1
            "$PY" -c "import sys; sys.path.insert(0, '$CP'); from plogical.panel_static_sync import ensure_litespeed_panel_static_complete; ensure_litespeed_panel_static_complete()" 2>&1
        ) | tee -a "$LOG" || true
    else
        log "WARNING: Django not importable; run collectstatic manually if theme CSS still missing"
    fi
fi

# Verify index template wires tokens + dark (informational)
IDX="$CP/baseTemplate/templates/baseTemplate/index.html"
if [[ -f "$IDX" ]]; then
    if grep -q 'cyberpanel-tokens.css' "$IDX" && grep -q 'cyberpanel-dark.css' "$IDX"; then
        log "index.html dark-mode CSS stack OK"
    else
        log "WARNING: index.html missing cyberpanel-tokens.css or cyberpanel-dark.css link"
    fi
fi

log "Done"
