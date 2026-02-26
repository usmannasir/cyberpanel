#!/bin/bash
# Change SnappyMail version: download chosen version, preserve data dirs, replace app files, fix data path and perms.
# Run as root: bash /usr/local/CyberCP/CPScripts/snappymail_version_changer.sh [VERSION]
# Example: bash snappymail_version_changer.sh 2.38.2
# Data under /usr/local/lscp/cyberpanel/snappymail/data is never removed.
set -e
PUBLIC_SNAPPY="/usr/local/CyberCP/public/snappymail"
DATA_PATH="/usr/local/lscp/cyberpanel/snappymail/data"
LOG="/var/log/cyberpanel_upgrade_debug.log"
log() { echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] $*" | tee -a "$LOG"; }

if [[ $(id -u) -ne 0 ]]; then
    echo "Run as root: sudo bash $0 [VERSION]"
    exit 1
fi

# Version: argument or latest from API or default
SNAPPY_VER="${1:-}"
if [[ -z "$SNAPPY_VER" ]]; then
    SNAPPY_VER=$(curl -sS "https://api.github.com/repos/the-djmaze/snappymail/releases/latest" 2>/dev/null | grep -o '"tag_name": "v[^"]*' | sed 's/"tag_name": "v//' | head -1)
    [[ -z "$SNAPPY_VER" ]] && SNAPPY_VER="2.38.2"
    log "Using SnappyMail version: $SNAPPY_VER (from API or default)"
else
    SNAPPY_VER="${SNAPPY_VER// /}"
    log "Using SnappyMail version: $SNAPPY_VER (from argument)"
fi

[[ -d "/usr/local/CyberCP/public" ]] || mkdir -p /usr/local/CyberCP/public
cd /usr/local/CyberCP/public || exit 1

# Download zip (data dirs are NOT under public/snappymail; we only replace app tree)
ZIP="snappymail-${SNAPPY_VER}.zip"
URL="https://github.com/the-djmaze/snappymail/releases/download/v${SNAPPY_VER}/${ZIP}"
log "Downloading $URL ..."
if ! wget -q -O "$ZIP" "$URL"; then
    log "ERROR: Download failed. Check version at https://github.com/the-djmaze/snappymail/releases"
    exit 1
fi

# Replace only app tree; do not remove DATA_PATH or public/snappymail/data if it exists
if [[ -d "$PUBLIC_SNAPPY" ]]; then
    rm -rf "$PUBLIC_SNAPPY"
    log "Removed existing public/snappymail app tree (data preserved under $DATA_PATH)"
fi
unzip -q "$ZIP" -d "$PUBLIC_SNAPPY"
rm -f "$ZIP"

# Fix data path in include.php
INCLUDE_PHP=""
for inc in "$PUBLIC_SNAPPY"/snappymail/v/*/include.php; do
    [[ -f "$inc" ]] && INCLUDE_PHP="$inc" && break
done
if [[ -n "$INCLUDE_PHP" ]] && [[ -f "$INCLUDE_PHP" ]]; then
    if grep -q "\$sCustomDataPath = ''" "$INCLUDE_PHP" 2>/dev/null; then
        sed -i "s|\$sCustomDataPath = '';|\$sCustomDataPath = '/usr/local/lscp/cyberpanel/snappymail/data';|" "$INCLUDE_PHP"
        log "Set data path in include.php"
    fi
fi

# Ensure data dirs exist
mkdir -p "$DATA_PATH/_data_/_default_/configs"
mkdir -p "$DATA_PATH/_data_/_default_/domains"
mkdir -p "$DATA_PATH/_data_/_default_/storage"
mkdir -p "$DATA_PATH/_data_/_default_/temp"
mkdir -p "$DATA_PATH/_data_/_default_/cache"

# Permissions
find "$PUBLIC_SNAPPY" -type d -exec chmod 755 {} \;
find "$PUBLIC_SNAPPY" -type f -exec chmod 644 {} \;
if id lscpd &>/dev/null; then
    chown -R lscpd:lscpd "$PUBLIC_SNAPPY"
    chown -R lscpd:lscpd "$DATA_PATH"
    log "Set ownership lscpd:lscpd"
fi
chmod -R 775 "$DATA_PATH" 2>/dev/null || true

# Optional: run CyberPanel SnappyMail integration if present
if [[ -f /usr/local/CyberCP/snappymail_cyberpanel.php ]]; then
    for php in /usr/local/lsws/lsphp83/bin/php /usr/local/lsws/lsphp82/bin/php /usr/local/lsws/lsphp81/bin/php /usr/local/lsws/lsphp80/bin/php; do
        [[ -x "$php" ]] && $php /usr/local/CyberCP/snappymail_cyberpanel.php 2>/dev/null && break
    done
fi

log "SnappyMail changed to version $SNAPPY_VER"
echo "SnappyMail version changed to $SNAPPY_VER. Data preserved under $DATA_PATH"
