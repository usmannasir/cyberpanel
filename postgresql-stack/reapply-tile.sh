#!/usr/bin/env bash
# Re-apply CyberPanel Quick App tile after panel upgrades.
set -euo pipefail
STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec bash "${STACK_ROOT}/modules/60-tile.sh"
