#!/bin/bash
# Change phpMyAdmin version: download chosen version, preserve config.inc.php and phpmyadminsignin.php.
# Run as root: bash /usr/local/CyberCP/CPScripts/phpmyadmin_version_changer.sh [VERSION]
set -e
PMA_DIR="/usr/local/CyberCP/public/phpmyadmin"
TMP_CONFIG="/tmp/cyberpanel_pma_config.inc.php.bak"
TMP_SIGNON="/tmp/cyberpanel_pma_phpmyadminsignin.php.bak"
LOG="/var/log/cyberpanel_upgrade_debug.log"
log() { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] $*" | tee -a "$LOG"; }

if [[ $(id -u) -ne 0 ]]; then
    echo "Run as root: sudo bash $0 [VERSION]"
    exit 1
fi

PMA_VER="${1:-}"
if [[ -z "$PMA_VER" ]]; then
    PMA_VER=$(curl -sS "https://api.github.com/repos/phpmyadmin/phpmyadmin/releases/latest" 2>/dev/null | grep -o '"tag_name": "[^"]*' | sed 's/"tag_name": "//;s/^RELEASE_//;s/_/./g' | head -1)
    [[ -z "$PMA_VER" ]] && PMA_VER="5.2.3"
fi
PMA_VER="${PMA_VER// /}"
[[ "$PMA_VER" =~ ^[0-9]_[0-9]_[0-9]$ ]] && PMA_VER="${PMA_VER//_/.}"
log "Using phpMyAdmin version: $PMA_VER"

[[ -d "/usr/local/CyberCP/public" ]] || mkdir -p /usr/local/CyberCP/public
SAVED_CONFIG=false
SAVED_SIGNON=false
[[ -f "$PMA_DIR/config.inc.php" ]] && cp -a "$PMA_DIR/config.inc.php" "$TMP_CONFIG" && SAVED_CONFIG=true
[[ -f "$PMA_DIR/phpmyadminsignin.php" ]] && cp -a "$PMA_DIR/phpmyadminsignin.php" "$TMP_SIGNON" && SAVED_SIGNON=true

TARBALL="/usr/local/CyberCP/public/phpmyadmin.tar.gz"
URL="https://files.phpmyadmin.net/phpMyAdmin/${PMA_VER}/phpMyAdmin-${PMA_VER}-all-languages.tar.gz"
wget -q -O "$TARBALL" "$URL" || { log "ERROR: Download failed"; exit 1; }
[[ $(stat -c%s "$TARBALL" 2>/dev/null) -gt 1000000 ]] || { log "ERROR: Tarball too small"; exit 1; }

rm -rf "$PMA_DIR"
tar -xzf "$TARBALL" -C /usr/local/CyberCP/public/
rm -f "$TARBALL"
EXTRACTED=$(ls -d /usr/local/CyberCP/public/phpMyAdmin-*-all-languages 2>/dev/null | head -1)
[[ -n "$EXTRACTED" ]] && [[ -d "$EXTRACTED" ]] && mv "$EXTRACTED" "$PMA_DIR" || { log "ERROR: Extract failed"; exit 1; }

if [[ "$SAVED_CONFIG" = true ]] && [[ -f "$TMP_CONFIG" ]]; then
    cp -a "$TMP_CONFIG" "$PMA_DIR/config.inc.php"
    rm -f "$TMP_CONFIG"
fi
if [[ ! -f "$PMA_DIR/config.inc.php" ]] && [[ -f "$PMA_DIR/config.sample.inc.php" ]]; then
    cp -a "$PMA_DIR/config.sample.inc.php" "$PMA_DIR/config.inc.php"
fi
[[ -f "$PMA_DIR/config.inc.php" ]] && (grep -q "TempDir" "$PMA_DIR/config.inc.php" 2>/dev/null || echo -e "\n\$cfg['TempDir'] = '/usr/local/CyberCP/public/phpmyadmin/tmp';" >> "$PMA_DIR/config.inc.php")
[[ "$SAVED_SIGNON" = true ]] && [[ -f "$TMP_SIGNON" ]] && cp -a "$TMP_SIGNON" "$PMA_DIR/phpmyadminsignin.php" && rm -f "$TMP_SIGNON"
[[ "$SAVED_SIGNON" != true ]] && [[ -f /usr/local/CyberCP/plogical/phpmyadminsignin.php ]] && cp -a /usr/local/CyberCP/plogical/phpmyadminsignin.php "$PMA_DIR/phpmyadminsignin.php"
sed -i "s/'localhost'/'127.0.0.1'/g" "$PMA_DIR/phpmyadminsignin.php" 2>/dev/null || true

mkdir -p "$PMA_DIR/tmp"
id lscpd &>/dev/null && chown -R lscpd:lscpd "$PMA_DIR"
chmod -R 755 "$PMA_DIR"
log "phpMyAdmin changed to version $PMA_VER"
echo "phpMyAdmin version $PMA_VER installed."
