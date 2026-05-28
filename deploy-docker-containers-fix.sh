#!/usr/bin/env bash
# Backward-compatible wrapper — see scripts/utils/deploy-docker-containers-fix.sh
ROOT="$(cd "$(dirname "$0")" && pwd)"
exec bash "$ROOT/scripts/utils/deploy-docker-containers-fix.sh" "$@"
