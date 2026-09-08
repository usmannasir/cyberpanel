#!/usr/bin/env bash
# Patch pgAdmin for Query Tool workspace server dropdown (lazy CSRF API client).
set -euo pipefail

STACK_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
bash "${STACK_ROOT}/lib/apply_pgadmin_patches.sh"
