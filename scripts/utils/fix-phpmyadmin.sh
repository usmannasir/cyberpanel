#!/bin/bash
# Fix phpMyAdmin after install/upgrade. Run as root on the panel server.
# Usage: sudo bash scripts/utils/fix-phpmyadmin.sh [--restart]
set -e
CP="${CP:-/usr/local/CyberCP}"
PUBLIC="$CP/public"
PYTHON="${PYTHON:-$CP/bin/python}"

if [[ $(id -u) -ne 0 ]]; then
    echo "Run as root: sudo bash $0"
    exit 1
fi

echo "Ensuring $PUBLIC exists..."
mkdir -p "$PUBLIC"

if [[ ! -x "$PYTHON" ]]; then
    PYTHON=$(which python3 2>/dev/null || which python2 2>/dev/null || true)
fi
if [[ -z "$PYTHON" ]]; then
    echo "ERROR: No Python found."
    exit 1
fi

echo "Installing/repairing phpMyAdmin files..."
export DJANGO_SETTINGS_MODULE=CyberCP.settings
"$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.upgrade import Upgrade
Upgrade.download_install_phpmyadmin()
" 2>&1 || true

if [[ -d "$PUBLIC/phpmyadmin" ]]; then
    SIGNIN="$PUBLIC/phpmyadmin/phpmyadminsignin.php"
    if [[ ! -f "$SIGNIN" && -f "$CP/plogical/phpmyadminsignin.php" ]]; then
        cp "$CP/plogical/phpmyadminsignin.php" "$SIGNIN"
        chown lscpd:lscpd "$SIGNIN" 2>/dev/null || true
    fi
    chown -R lscpd:lscpd "$PUBLIC/phpmyadmin" 2>/dev/null || true
    chmod 755 "$PUBLIC/phpmyadmin"
    chmod 755 "$PUBLIC/phpmyadmin/tmp" 2>/dev/null || true
else
    echo "WARNING: $PUBLIC/phpmyadmin was not created."
    exit 1
fi

echo "Configuring OpenLiteSpeed PHP contexts for /phpmyadmin/ ..."
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
bash "$ROOT/CPScripts/fix-cyberpanel-phpmyadmin-ols.sh" "$@"

echo "Done. Open CyberPanel -> Databases -> phpMyAdmin -> Access Now"
