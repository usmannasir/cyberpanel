#!/usr/bin/env bash
# Backward-compatible wrapper — see scripts/utils/deploy-ftp-users-custom-quota-columns.sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$ROOT/scripts/utils/deploy-ftp-users-custom-quota-columns.sh" "$@"
