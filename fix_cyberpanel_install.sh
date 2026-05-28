#!/usr/bin/env bash
# Backward-compatible wrapper — see scripts/utils/fix_cyberpanel_install.sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$ROOT/scripts/utils/fix_cyberpanel_install.sh" "$@"
