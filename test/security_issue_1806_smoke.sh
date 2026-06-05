#!/usr/bin/env bash
# Smoke checks for issue #1806 security patches (AI Scanner callback auth).
# Usage: PANEL_PORT=8090 bash test/security_issue_1806_smoke.sh
set -euo pipefail

PANEL_PORT="${PANEL_PORT:-8090}"
BASE="https://127.0.0.1:${PANEL_PORT}"

code_legacy="$(curl -sk -o /dev/null -w '%{http_code}' -X POST "${BASE}/aiscanner/callback/" \
  -H 'Content-Type: application/json' -d '{"scan_id":"test"}' || echo 000)"
code_api="$(curl -sk -o /dev/null -w '%{http_code}' -X POST "${BASE}/api/ai-scanner/callback" \
  -H 'Content-Type: application/json' -d '{"scan_id":"test"}' || echo 000)"

echo "legacy /aiscanner/callback/ HTTP ${code_legacy} (expect 401)"
echo "api /api/ai-scanner/callback HTTP ${code_api} (expect 401)"

if [[ "$code_legacy" != "401" || "$code_api" != "401" ]]; then
  echo "FAIL: unauthenticated callback must return 401 on port ${PANEL_PORT}" >&2
  exit 1
fi

echo "PASS: AI Scanner callbacks require authentication (port ${PANEL_PORT})"
