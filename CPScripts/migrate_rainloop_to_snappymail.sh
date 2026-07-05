#!/bin/bash
# Migrate RainLoop to SnappyMail on live server: rename public folder and/or install SnappyMail if missing, migrate data, fix paths, restart, test.
# Run as root: bash /usr/local/CyberCP/CPScripts/migrate_rainloop_to_snappymail.sh
set -e
LOG="/var/log/cyberpanel_upgrade_debug.log"
log() { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] $*" | tee -a "$LOG"; }
SNAPPY_VERSION="${SNAPPY_VERSION:-2.38.2}"

log "=== RainLoop -> SnappyMail migration ==="

# 1) Ensure public/snappymail exists: rename rainloop -> snappymail OR download and install SnappyMail
if [ -d "/usr/local/CyberCP/public/rainloop" ] && [ ! -d "/usr/local/CyberCP/public/snappymail" ]; then
    log "Renaming public/rainloop to public/snappymail..."
    mv /usr/local/CyberCP/public/rainloop /usr/local/CyberCP/public/snappymail
    log "Renamed public/rainloop -> public/snappymail"
    if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
        sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
        log "Updated include.php data path"
    fi
    for inc in /usr/local/CyberCP/public/snappymail/snappymail/v/*/include.php /usr/local/CyberCP/public/snappymail/rainloop/v/*/include.php; do
        [ -f "$inc" ] && sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' "$inc" && log "Updated $inc" && break
    done 2>/dev/null || true
elif [ ! -d "/usr/local/CyberCP/public/snappymail" ]; then
    log "public/snappymail missing - installing SnappyMail v${SNAPPY_VERSION}..."
    cd /usr/local/CyberCP/public || exit 1
    if ! wget -q "https://github.com/the-djmaze/snappymail/releases/download/v${SNAPPY_VERSION}/snappymail-${SNAPPY_VERSION}.zip" -O "snappymail-${SNAPPY_VERSION}.zip"; then
        log "ERROR: wget SnappyMail failed"
        exit 1
    fi
    unzip -q "snappymail-${SNAPPY_VERSION}.zip" -d /usr/local/CyberCP/public/snappymail
    rm -f "snappymail-${SNAPPY_VERSION}.zip"
    find /usr/local/CyberCP/public/snappymail -type d -exec chmod 755 {} \;
    find /usr/local/CyberCP/public/snappymail -type f -exec chmod 644 {} \;
    log "SnappyMail installed"
    # Configure data path and run CyberPanel integration
    if [ ! -f /usr/local/CyberCP/snappymail_cyberpanel.php ]; then
        wget -q -O /usr/local/CyberCP/snappymail_cyberpanel.php "https://raw.githubusercontent.com/the-djmaze/snappymail/master/integrations/cyberpanel/install.php" 2>/dev/null || true
        [ -f /usr/local/CyberCP/snappymail_cyberpanel.php ] && sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/snappymail_cyberpanel.php
    fi
    if [ -f /usr/local/CyberCP/snappymail_cyberpanel.php ]; then
        for php in /usr/local/lsws/lsphp83/bin/php /usr/local/lsws/lsphp82/bin/php /usr/local/lsws/lsphp81/bin/php /usr/local/lsws/lsphp80/bin/php; do
            [ -x "$php" ] && $php /usr/local/CyberCP/snappymail_cyberpanel.php 2>/dev/null && break
        done
    fi
    if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
        sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
        log "Updated include.php data path after install"
    fi
else
    log "public/snappymail already exists"
    if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
        sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
        log "Ensured include.php uses snappymail data path"
    fi
fi

# 2) Data migration: lscp/cyberpanel/rainloop/data -> snappymail/data
mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/configs/
mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/domains/
mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/storage/
mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/temp/
mkdir -p /usr/local/lscp/cyberpanel/snappymail/data/_data_/_default_/cache/

if [ -d "/usr/local/lscp/cyberpanel/rainloop/data" ] && [ "$(ls -A /usr/local/lscp/cyberpanel/rainloop/data 2>/dev/null)" ]; then
    log "Migrating rainloop data to snappymail..."
    rsync -av --ignore-existing /usr/local/lscp/cyberpanel/rainloop/data/ /usr/local/lscp/cyberpanel/snappymail/data/ 2>&1 | tee -a "$LOG"
    if [ -f "/usr/local/CyberCP/public/snappymail/include.php" ]; then
        sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g' /usr/local/CyberCP/public/snappymail/include.php
    fi
    find /usr/local/lscp/cyberpanel/snappymail/data -type f \( -name "*.ini" -o -name "*.json" -o -name "*.php" -o -name "*.cfg" \) -exec grep -l "rainloop" {} \; 2>/dev/null | while read -r f; do
        sed -i 's|/usr/local/lscp/cyberpanel/rainloop/data|/usr/local/lscp/cyberpanel/snappymail/data|g; s|/rainloop/|/snappymail/|g; s|rainloop/data|snappymail/data|g' "$f"
    done
    log "Data migration done"
fi

# 3) Ownership and permissions (both rainloop and snappymail trees)
ENSURE_PERMS="/usr/local/CyberCP/scripts/utils/ensure-snappymail-permissions.sh"
if [[ -x "$ENSURE_PERMS" ]]; then
    bash "$ENSURE_PERMS" || true
    log "Ran ensure-snappymail-permissions.sh"
elif id -u lscpd >/dev/null 2>&1; then
    chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/rainloop/ 2>/dev/null || true
    chown -R lscpd:lscpd /usr/local/lscp/cyberpanel/snappymail/
    chown -R lscpd:lscpd /usr/local/CyberCP/public/snappymail/ 2>/dev/null || true
    log "Set ownership lscpd:lscpd (fallback)"
fi
chmod -R 775 /usr/local/lscp/cyberpanel/snappymail/data/ 2>/dev/null || true
chmod -R 775 /usr/local/lscp/cyberpanel/rainloop/data/ 2>/dev/null || true

# 4) Restart panel
log "Restarting lscpd..."
systemctl restart lscpd
sleep 2

# 5) Test
PORT=$(cat /usr/local/lscp/conf/bind.conf 2>/dev/null | grep -oE '[0-9]+' | head -1)
PORT=${PORT:-8090}
log "Testing https://127.0.0.1:${PORT}/snappymail/index.php ..."
CODE=$(curl -sk -o /dev/null -w "%{http_code}" "https://127.0.0.1:${PORT}/snappymail/index.php" 2>/dev/null || echo "000")
if [ "$CODE" = "200" ] || [ "$CODE" = "302" ]; then
    log "OK: SnappyMail URL returned HTTP $CODE"
else
    log "WARNING: SnappyMail URL returned HTTP $CODE (expected 200 or 302)"
fi

log "=== Migration script finished ==="
