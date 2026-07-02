#!/usr/bin/env bash
# CyberPanel scripts/utils dispatcher — list and run maintenance helpers.
# Usage:
#   cyberpanel-utils.sh list
#   cyberpanel-utils.sh run <id> [args...]
#   cyberpanel-utils.sh help [id]

set -euo pipefail

UTILS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$UTILS_DIR/../.." && pwd)"
MANIFEST="${UTILS_DIR}/manifest.json"

usage() {
    cat <<'EOF'
CyberPanel utility scripts (scripts/utils/)

Usage:
  cyberpanel-utils.sh list
  cyberpanel-utils.sh run <id> [args...]
  cyberpanel-utils.sh help [id]

Examples:
  sudo cyberpanel-utils.sh run fix-phpmyadmin
  cyberpanel-utils.sh list
EOF
}

_manifest_lookup() {
    local want_id="$1"
    local id file desc needs_root
    if [[ ! -f "$MANIFEST" ]]; then
        echo "ERROR: manifest not found: $MANIFEST" >&2
        return 2
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: python3 required to read manifest.json" >&2
        return 2
    fi
    python3 - "$want_id" "$MANIFEST" <<'PY'
import json, sys
want, path = sys.argv[1], sys.argv[2]
with open(path, encoding="utf-8") as f:
    data = json.load(f)
for u in data.get("utils", []):
    if u.get("id") == want:
        print(u.get("file", ""))
        print(u.get("description", ""))
        print("1" if u.get("needs_root") else "0")
        sys.exit(0)
sys.exit(1)
PY
}

cmd_list() {
    if [[ ! -f "$MANIFEST" ]]; then
        echo "ERROR: manifest not found: $MANIFEST" >&2
        exit 2
    fi
    if ! command -v python3 >/dev/null 2>&1; then
        echo "ERROR: python3 required to read manifest.json" >&2
        exit 2
    fi
    python3 - "$MANIFEST" <<'PY'
import json, sys
with open(sys.argv[1], encoding="utf-8") as f:
    data = json.load(f)
print(f"{'ID':<40} {'ROOT':<5} DESCRIPTION")
print("-" * 90)
for u in data.get("utils", []):
    root = "yes" if u.get("needs_root") else "no"
    print(f"{u.get('id',''):<40} {root:<5} {u.get('description','')}")
PY
}

cmd_help() {
    local id="${1:-}"
    if [[ -z "$id" ]]; then
        usage
        exit 0
    fi
    local lines
    if ! lines="$(_manifest_lookup "$id")"; then
        echo "Unknown utility id: $id" >&2
        echo "Run: $0 list" >&2
        exit 1
    fi
    local file desc needs_root script
    file=$(echo "$lines" | sed -n '1p')
    desc=$(echo "$lines" | sed -n '2p')
    needs_root=$(echo "$lines" | sed -n '3p')
    script="${UTILS_DIR}/${file}"
    echo "ID:          $id"
    echo "Script:      $script"
    echo "Description: $desc"
    echo "Needs root:  $needs_root"
    if [[ -f "$script" ]]; then
        echo ""
        echo "--- Header ---"
        head -n 8 "$script" | sed 's/^/  /'
    fi
}

cmd_run() {
    local id="${1:-}"
    shift || true
    if [[ -z "$id" ]]; then
        echo "ERROR: missing utility id" >&2
        usage >&2
        exit 1
    fi
    local lines
    if ! lines="$(_manifest_lookup "$id")"; then
        echo "Unknown utility id: $id" >&2
        echo "Run: $0 list" >&2
        exit 1
    fi
    local file needs_root script
    file=$(echo "$lines" | sed -n '1p')
    needs_root=$(echo "$lines" | sed -n '3p')
    script="${UTILS_DIR}/${file}"
    if [[ ! -f "$script" ]]; then
        echo "ERROR: script not found: $script" >&2
        exit 2
    fi
    if [[ "$needs_root" = "1" ]] && [[ "$(id -u)" -ne 0 ]]; then
        echo "ERROR: $id requires root. Run: sudo $0 run $id" >&2
        exit 3
    fi
    export REPO_ROOT
    REPO_ROOT="$REPO_ROOT"
    echo "[$(date -Iseconds)] Running $id ($script) REPO_ROOT=$REPO_ROOT"
    exec bash "$script" "$@"
}

main() {
    local cmd="${1:-}"
    case "$cmd" in
        list)
            cmd_list
            ;;
        run)
            shift
            cmd_run "$@"
            ;;
        help|-h|--help)
            shift || true
            cmd_help "${1:-}"
            ;;
        "")
            usage
            exit 1
            ;;
        *)
            echo "Unknown command: $cmd" >&2
            usage >&2
            exit 1
            ;;
    esac
}

main "$@"
