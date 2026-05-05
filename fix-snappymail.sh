#!/bin/bash
# Fix SnappyMail 404 after upgrade (missing /usr/local/CyberCP/public/snappymail). Run as root on the panel server.
# Usage: sudo bash fix-snappymail.sh
# Then open https://YOUR_IP:2087/snappymail/index.php (or Webmail in the panel).

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
    PYTHON=$(command -v python3 2>/dev/null || command -v python2 2>/dev/null || true)
fi
if [[ -z "$PYTHON" ]]; then
    echo "ERROR: No Python found. Fix panel Python or install SnappyMail manually."
    exit 1
fi

echo "Installing SnappyMail via panel upgrade module..."
export DJANGO_SETTINGS_MODULE=CyberCP.settings
"$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.upgrade import Upgrade
Upgrade.downoad_and_install_raindloop()
" 2>&1 || true

if [[ -f "$PUBLIC/snappymail/index.php" ]]; then
    echo "Setting ownership to lscpd:lscpd..."
    chown -R lscpd:lscpd "$PUBLIC/snappymail" 2>/dev/null || true
    chmod 755 "$PUBLIC/snappymail" 2>/dev/null || true
    echo "Done. SnappyMail is at $PUBLIC/snappymail"
    echo "Test: https://YOUR_IP:2087/snappymail/index.php"
else
    echo "WARNING: $PUBLIC/snappymail/index.php was not created. Check logs above."
    exit 1
fi
