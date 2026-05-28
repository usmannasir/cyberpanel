#!/usr/bin/env bash
# Backward-compatible wrapper — see scripts/utils/fix-phpmyadmin.sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$ROOT/scripts/utils/fix-phpmyadmin.sh" "$@"
