#!/usr/bin/env bash
# Ensure SnappyMail / RainLoop data dirs are writable by lscpd (panel webmail).
# Covers both legacy rainloop/data and snappymail/data paths.
# Usage: sudo bash ensure-snappymail-permissions.sh [--restart]
set -euo pipefail

LOG="${LOG:-/var/log/cyberpanel_upgrade_debug.log}"
RESTART_LSCPD=0
if [[ "${1:-}" == "--restart" ]]; then
    RESTART_LSCPD=1
fi

log() {
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ensure-snappymail-permissions: $*" | tee -a "$LOG"
}

if [[ $(id -u) -ne 0 ]]; then
    echo "Run as root: sudo bash $0 [--restart]" >&2
    exit 1
fi

if ! id -u lscpd >/dev/null 2>&1; then
    log "WARNING: lscpd user not found, skipping ownership fix"
    exit 0
fi

RAINLOOP_ROOT="/usr/local/lscp/cyberpanel/rainloop"
SNAPPY_ROOT="/usr/local/lscp/cyberpanel/snappymail"
PUBLIC_SNAPPY="/usr/local/CyberCP/public/snappymail"

for dir in "$RAINLOOP_ROOT" "$SNAPPY_ROOT" "$PUBLIC_SNAPPY"; do
    if [[ -d "$dir" ]]; then
        chown -R lscpd:lscpd "$dir"
        log "chown lscpd:lscpd $dir"
    fi
done

for data_dir in \
    "$RAINLOOP_ROOT/data" \
    "$SNAPPY_ROOT/data"; do
    if [[ -d "$data_dir" ]]; then
        find "$data_dir" -type d -exec chmod 775 {} \; 2>/dev/null || true
        find "$data_dir" -type f -exec chmod 664 {} \; 2>/dev/null || true
        log "chmod 775/664 under $data_dir"
    fi
done

usermod -a -G lscpd nobody 2>/dev/null || true

if [[ "$RESTART_LSCPD" -eq 1 ]]; then
    log "Restarting lscpd..."
    systemctl restart lscpd
    sleep 2
    PORT=$(grep -oE '[0-9]+' /usr/local/lscp/conf/bind.conf 2>/dev/null | head -1)
    PORT=${PORT:-8090}
    CODE=$(curl -sk -o /dev/null -w "%{http_code}" "https://127.0.0.1:${PORT}/snappymail/index.php" 2>/dev/null || echo "000")
    if [[ "$CODE" == "200" || "$CODE" == "302" ]]; then
        log "OK: SnappyMail returned HTTP $CODE"
    else
        log "WARNING: SnappyMail returned HTTP $CODE (expected 200 or 302)"
    fi
fi

log "Done"
