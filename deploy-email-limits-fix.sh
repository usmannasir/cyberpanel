#!/usr/bin/env bash
# Backward-compatible wrapper — see scripts/utils/deploy-email-limits-fix.sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$ROOT/scripts/utils/deploy-email-limits-fix.sh" "$@"
