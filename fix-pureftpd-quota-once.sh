#!/usr/bin/env bash
# Backward-compatible wrapper — see scripts/utils/fix-pureftpd-quota-once.sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$ROOT/scripts/utils/fix-pureftpd-quota-once.sh" "$@"
