#!/bin/bash
# Fix phpMyAdmin 404 after upgrade. Run as root on the panel server.
# Usage: sudo bash fix-phpmyadmin.sh
# Then open https://YOUR_IP:2087/phpmyadmin/ (or from Databases -> phpMyAdmin in the panel).

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
    echo "ERROR: No Python found. Install phpMyAdmin manually or fix panel Python."
    exit 1
fi

echo "Installing phpMyAdmin via panel upgrade module..."
export DJANGO_SETTINGS_MODULE=CyberCP.settings
"$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.upgrade import Upgrade
Upgrade.download_install_phpmyadmin()
" 2>&1 || true

if [[ -d "$PUBLIC/phpmyadmin" ]]; then
    echo "Setting ownership to lscpd:lscpd..."
    chown -R lscpd:lscpd "$PUBLIC/phpmyadmin" 2>/dev/null || true
    chmod 755 "$PUBLIC/phpmyadmin"
    chmod 755 "$PUBLIC/phpmyadmin/tmp" 2>/dev/null || true
    echo "Done. phpMyAdmin is at $PUBLIC/phpmyadmin"
    echo "Test: https://YOUR_IP:2087/phpmyadmin/ (or use the panel Databases -> phpMyAdmin link)"
else
    echo "WARNING: $PUBLIC/phpmyadmin was not created. Check logs above."
    exit 1
fi
