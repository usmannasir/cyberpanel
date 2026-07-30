#!/bin/bash
# Retrofit CyberPanel sensitive-file deny rules (#1859) into existing OLS vhosts.
# Safe to re-run: skips configs that already contain the BEGIN marker.
#
# Usage:
#   /usr/local/CyberCP/CPScripts/retrofit-sensitive-file-denials.sh
#   /usr/local/CyberCP/CPScripts/retrofit-sensitive-file-denials.sh --dry-run
#   /usr/local/CyberCP/CPScripts/retrofit-sensitive-file-denials.sh --no-restart

set -euo pipefail

VHOST_ROOT="${VHOST_ROOT:-/usr/local/lsws/conf/vhosts}"
DRY_RUN=0
RESTART=1

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=1 ;;
        --no-restart) RESTART=0 ;;
        -h|--help)
            sed -n '2,12p' "$0"
            exit 0
            ;;
        *)
            echo "Unknown argument: $arg" >&2
            exit 2
            ;;
    esac
done

if [[ ! -d "$VHOST_ROOT" ]]; then
    echo "Vhost root not found: $VHOST_ROOT" >&2
    exit 1
fi

export VHOST_ROOT
export CYBERPANEL_SENSITIVE_DENY_DRY_RUN="$DRY_RUN"

python3 - <<'PY'
import os
import sys

sys.path.insert(0, '/usr/local/CyberCP')
from plogical.vhost import vhost

vhost_root = os.environ.get('VHOST_ROOT', '/usr/local/lsws/conf/vhosts')
dry_run = os.environ.get('CYBERPANEL_SENSITIVE_DENY_DRY_RUN', '0') == '1'

modified = 0
skipped = 0
errors = 0
examined = 0

for name in sorted(os.listdir(vhost_root)):
    if name in ('Example', 'cyberpanel'):
        continue
    vh = os.path.join(vhost_root, name, 'vhost.conf')
    if not os.path.isfile(vh):
        continue
    examined += 1
    if dry_run:
        with open(vh, 'r') as fh:
            content = fh.read()
        if '# BEGIN CyberPanel sensitive-file denials (#1859)' in content:
            skipped += 1
            print('SKIP (already present): %s' % vh)
        else:
            modified += 1
            print('WOULD UPDATE: %s' % vh)
        continue

    result = vhost.ensureSensitiveFileDenials(vh)
    if result == 1:
        modified += 1
        print('UPDATED: %s' % vh)
    elif result == 0:
        skipped += 1
        print('SKIP: %s' % vh)
    else:
        errors += 1
        print('ERROR: %s' % vh, file=sys.stderr)

print('examined=%s updated=%s skipped=%s errors=%s dry_run=%s' % (
    examined, modified, skipped, errors, dry_run))
sys.exit(1 if errors else 0)
PY

rc=$?
if [[ $rc -ne 0 ]]; then
    exit "$rc"
fi

if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "Dry run complete; LiteSpeed not restarted."
    exit 0
fi

if [[ "$RESTART" -eq 1 ]]; then
    if command -v systemctl >/dev/null 2>&1 && systemctl list-unit-files lsws.service >/dev/null 2>&1; then
        systemctl restart lsws
        systemctl is-active --quiet lsws && echo "lsws restarted OK" || {
            echo "lsws restart reported not-active" >&2
            exit 1
        }
    elif [[ -x /usr/local/lsws/bin/lswsctrl ]]; then
        /usr/local/lsws/bin/lswsctrl restart
        echo "lswsctrl restart issued"
    else
        echo "Could not find lsws restart method; configs updated but not reloaded." >&2
        exit 1
    fi
else
    echo "Configs updated; restart skipped (--no-restart)."
fi
