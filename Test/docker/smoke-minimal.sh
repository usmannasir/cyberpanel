#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/smoke.sh"

fail=0
for unit in pdns postfix pure-ftpd pure-ftpd-mysql; do
  if systemctl is-active --quiet "$unit" 2>/dev/null; then
    echo "FAIL $unit should be inactive in minimal mode"
    fail=1
  fi
done
echo "OK optional services absent/inactive"

[[ "$fail" -eq 0 ]] && echo "SMOKE_MINIMAL_OK" || { echo "SMOKE_MINIMAL_FAIL"; exit 1; }
