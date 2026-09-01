#!/usr/bin/env bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/smoke.sh"

fail=0
if systemctl is-active --quiet pdns; then echo "OK pdns"; else echo "FAIL pdns"; fail=1; fi
if systemctl is-active --quiet postfix; then echo "OK postfix"; else echo "FAIL postfix"; fail=1; fi
if systemctl is-active --quiet pure-ftpd || systemctl is-active --quiet pure-ftpd-mysql; then echo "OK pure-ftpd"; else echo "FAIL pure-ftpd"; fail=1; fi
if docker run --rm hello-world >/dev/null 2>&1; then echo "OK docker hello-world"; else echo "WARN docker hello-world"; fi

[[ "$fail" -eq 0 ]] && echo "SMOKE_FULL_OK" || { echo "SMOKE_FULL_FAIL"; exit 1; }
