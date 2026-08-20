#!/bin/bash
# Repair SnappyMail under CyberCP public/ and OLS PHP contexts.
# OLS CyberPanel vhost uses restrained=1: public/snappymail must be a real
# directory inside /usr/local/CyberCP (not a symlink to /usr/local/lscp/...).
# Usage: sudo bash scripts/utils/fix-snappymail.sh [--restart]
set -e
CP="${CP:-/usr/local/CyberCP}"
PUBLIC="$CP/public/snappymail"
LSCP="/usr/local/lscp/cyberpanel/snappymail"
PYTHON="${PYTHON:-$CP/bin/python}"
RESTART=0
[[ "${1:-}" == "--restart" ]] && RESTART=1

if [[ $(id -u) -ne 0 ]]; then
    echo "Run as root: sudo bash $0"
    exit 1
fi

if [[ ! -x "$PYTHON" ]]; then
    PYTHON=$(command -v python3 2>/dev/null || command -v python 2>/dev/null || true)
fi
if [[ -z "$PYTHON" ]]; then
    echo "ERROR: No Python found."
    exit 1
fi

echo "Ensuring SnappyMail app tree under $PUBLIC (not a symlink)..."
export DJANGO_SETTINGS_MODULE=CyberCP.settings
"$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.cyberpanelOlsPhpmyadmin import ensure_snappymail_public_tree, ensure_cyberpanel_phpmyadmin_ols
ok = ensure_snappymail_public_tree()
print('ensure_snappymail_public_tree:', ok)
ensure_cyberpanel_phpmyadmin_ols(reload=True, restart=bool($RESTART), verify=True)
" 2>&1

if [[ -L "$PUBLIC" ]]; then
    echo "ERROR: $PUBLIC is still a symlink."
    exit 1
fi
if [[ ! -f "$PUBLIC/index.php" ]]; then
    echo "WARNING: index.php still missing; attempting Upgrade.downoad_and_install_raindloop()..."
    "$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.upgrade import Upgrade
Upgrade.downoad_and_install_raindloop()
" 2>&1 || true
    "$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.cyberpanelOlsPhpmyadmin import ensure_snappymail_public_tree, ensure_cyberpanel_phpmyadmin_ols
ensure_snappymail_public_tree()
ensure_cyberpanel_phpmyadmin_ols(reload=True, restart=True, verify=True)
" 2>&1 || true
fi

if [[ ! -L "$PUBLIC" && -f "$PUBLIC/index.php" ]]; then
    chown -R lscpd:lscpd "$PUBLIC" "$LSCP/data" 2>/dev/null || true
    echo "SnappyMail repair OK: $PUBLIC"
    exit 0
fi
echo "ERROR: SnappyMail repair failed."
exit 1
