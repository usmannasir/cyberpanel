#!/bin/bash

set -euo pipefail

VHOST_ROOT="${VHOST_ROOT:-/usr/local/lsws/conf/vhosts}"
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
CYBERPANEL_ROOT="$(dirname -- "$SCRIPT_DIR")"
RESTART=1

if [[ "${1:-}" == "--no-restart" ]]; then
    RESTART=0
elif [[ -n "${1:-}" ]]; then
    echo "Usage: $0 [--no-restart]" >&2
    exit 2
fi

if [[ ! -x /usr/local/lsws/bin/openlitespeed ]]; then
    echo "OpenLiteSpeed is not installed; no vhosts were changed."
    exit 0
fi

if [[ ! -d "$VHOST_ROOT" ]]; then
    echo "Vhost root not found: $VHOST_ROOT" >&2
    exit 1
fi

export CYBERPANEL_ROOT VHOST_ROOT
result="$({ python3 - <<'PY'
import os
import sys

sys.path.insert(0, os.environ['CYBERPANEL_ROOT'])
from plogical.sensitiveFileProtection import protect_vhost_tree

results = protect_vhost_tree(os.environ['VHOST_ROOT'])
print('{examined} {updated} {skipped} {errors}'.format(**results))
raise SystemExit(1 if results['errors'] else 0)
PY
} 2>&1)" || {
    echo "$result" >&2
    exit 1
}

read -r examined updated skipped errors <<< "$result"
echo "examined=$examined updated=$updated skipped=$skipped errors=$errors"

if [[ "$updated" -gt 0 && "$RESTART" -eq 1 ]]; then
    /usr/local/lsws/bin/lswsctrl reload
fi
