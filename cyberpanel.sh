#!/bin/bash
# CyberPanel install – modular loader. Sources install_modules/*.sh then runs main.
# When install_modules/ is missing (e.g. one-liner), downloads modules from GitHub.

set -e

# Parse -b/--branch for module download (when not running from repo)
BRANCH_FOR_MODULES="${CYBERPANEL_BRANCH:-stable}"
export BRANCH_NAME="${BRANCH_FOR_MODULES}"
export CYBERPANEL_GITHUB_OWNER="${CYBERPANEL_GITHUB_OWNER:-master3395}"
next=""
for arg in "$@"; do
  if [[ "$arg" = "-b" ]] || [[ "$arg" = "--branch" ]]; then
    next="1"
    continue
  fi
  if [[ "$next" = "1" ]] && [[ -n "$arg" ]]; then
    BRANCH_FOR_MODULES="$arg"
    break
  fi
done

# Resolve script directory
INSTALL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
[[ -z "$INSTALL_SCRIPT_DIR" ]] && INSTALL_SCRIPT_DIR="."

MOD_DIR=""
if [[ -d "$INSTALL_SCRIPT_DIR/install_modules" ]]; then
  MOD_DIR="$INSTALL_SCRIPT_DIR/install_modules"
else
  MOD_DIR="/tmp/cyberpanel_install_modules_$$"
  mkdir -p "$MOD_DIR"
  BASE_URL="https://raw.githubusercontent.com/master3395/cyberpanel/${BRANCH_FOR_MODULES}/install_modules"
  for name in 00_common 01_verify_deps 02_install_core 03_install_direct 04_fixes_status 05_menus_main 06_menus_update 07_menus_advanced 08_actions 09_parse_main; do
    dest="$MOD_DIR/${name}.sh"
    http_code=$(curl -sL -H 'Cache-Control: no-cache' -w "%{http_code}" -o "$dest" "$BASE_URL/${name}.sh" 2>/dev/null) || http_code="000"
    if [[ "$http_code" != "200" ]] || [[ ! -s "$dest" ]] || ! head -n 1 "$dest" | grep -q '^#!'; then
      echo "Failed to download install_modules/${name}.sh (HTTP ${http_code}) from branch ${BRANCH_FOR_MODULES}."
      echo "Modular install_modules/ are on master3395/cyberpanel v2.5.5-dev, not stable."
      echo "Retry: bash cyberpanel.sh -b v2.5.5-dev"
      rm -f "$dest"
      exit 1
    fi
  done
fi

for f in "$MOD_DIR"/00_common.sh "$MOD_DIR"/01_verify_deps.sh "$MOD_DIR"/02_install_core.sh "$MOD_DIR"/03_install_direct.sh "$MOD_DIR"/04_fixes_status.sh "$MOD_DIR"/05_menus_main.sh "$MOD_DIR"/06_menus_update.sh "$MOD_DIR"/07_menus_advanced.sh "$MOD_DIR"/08_actions.sh "$MOD_DIR"/09_parse_main.sh; do
  if [[ -f "$f" ]]; then
    source "$f"
  fi
done

main "$@"
