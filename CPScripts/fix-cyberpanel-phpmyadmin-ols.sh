#!/bin/bash
# Ensure CyberPanel :8090 serves /phpmyadmin/ via lsphp (not Django static download).
set -euo pipefail
CP="${CP:-/usr/local/CyberCP}"
PYTHON="${PYTHON:-}"
for p in "$CP/bin/python" "$CP/bin/python3" /usr/local/CyberPanel/bin/python /usr/bin/python3; do
  [[ -x "$p" ]] && PYTHON="$p" && break
done
[[ -n "$PYTHON" ]] || { echo "No Python for CyberCP"; exit 1; }
export DJANGO_SETTINGS_MODULE=CyberCP.settings
"$PYTHON" -c "
import sys
sys.path.insert(0, '$CP')
from plogical.cyberpanelOlsPhpmyadmin import ensure_cyberpanel_phpmyadmin_ols
import sys as _s
_s.exit(0 if ensure_cyberpanel_phpmyadmin_ols(restart='--restart' in sys.argv) else 1)
" "$@"
