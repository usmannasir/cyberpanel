#!/bin/bash
# CyberPanel install – modular loader. Sources install_modules/*.sh then runs main.
# When install_modules/ is missing (e.g. one-liner), downloads modules from GitHub.

set -e

# Parse -b/--branch for module download (when not running from repo)
# master3395 fork: modular install_modules/ live on v2.5.5-dev, not stable
BRANCH_FOR_MODULES="${CYBERPANEL_BRANCH:-v2.5.5-dev}"
CYBERPANEL_GITHUB_OWNER="${CYBERPANEL_GITHUB_OWNER:-master3395}"
next=""
for arg in "$@"; do
  if [[ "$arg" = "-b" ]] || [[ "$arg" = "--branch" ]]; then
    next="1"
    continue
  fi
  if [[ "$next" = "1" ]] && [[ -n "$arg" ]]; then
    BRANCH_FOR_MODULES="$arg"
    next=""
    continue
  fi
  if [[ "$arg" == -b=* ]] || [[ "$arg" == --branch=* ]]; then
    BRANCH_FOR_MODULES="${arg#*=}"
  fi
done
export BRANCH_NAME="${BRANCH_FOR_MODULES}"
export CYBERPANEL_GITHUB_OWNER

# Must be root before any logging or package installs
if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    echo "CyberPanel install requires root. Re-running with sudo..."
  _cp_script="${BASH_SOURCE[0]:-$0}"
  if [[ "$_cp_script" = "bash" ]] || [[ "$_cp_script" = "sh" ]]; then
    _cp_script="$(readlink -f "${BASH_SOURCE[1]:-$0}" 2>/dev/null || echo "")"
  fi
  if [[ -n "$_cp_script" ]] && [[ -f "$_cp_script" ]]; then
    exec sudo -E env CYBERPANEL_BRANCH="${BRANCH_FOR_MODULES}" CYBERPANEL_GITHUB_OWNER="${CYBERPANEL_GITHUB_OWNER}" bash "$_cp_script" "$@"
  fi
    exec sudo -E env CYBERPANEL_BRANCH="${BRANCH_FOR_MODULES}" CYBERPANEL_GITHUB_OWNER="${CYBERPANEL_GITHUB_OWNER}" bash -c "$(curl -sL "https://raw.githubusercontent.com/${CYBERPANEL_GITHUB_OWNER}/cyberpanel/${BRANCH_FOR_MODULES}/cyberpanel.sh")" bash "$@"
  fi
  echo "ERROR: Run as root, for example: sudo bash cyberpanel.sh -b ${BRANCH_FOR_MODULES}"
  if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "WSL: curl -sL .../install.sh | sudo sh"
  fi
  exit 1
fi

# Resolve script directory
INSTALL_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" 2>/dev/null && pwd)"
[[ -z "$INSTALL_SCRIPT_DIR" ]] && INSTALL_SCRIPT_DIR="."

_download_install_module() {
  local name="$1"
  local branch="$2"
  local dest="$3"
  local owner="${CYBERPANEL_GITHUB_OWNER:-master3395}"
  local url="https://raw.githubusercontent.com/${owner}/cyberpanel/${branch}/install_modules/${name}.sh"
  local http_code
  http_code=$(curl -sL -H 'Cache-Control: no-cache' -w "%{http_code}" -o "$dest" "$url" 2>/dev/null) || http_code="000"
  if [[ "$http_code" = "200" ]] && [[ -s "$dest" ]] && head -n 1 "$dest" | grep -q '^#!'; then
    return 0
  fi
  rm -f "$dest"
  return 1
}

MOD_DIR=""
if [[ -d "$INSTALL_SCRIPT_DIR/install_modules" ]]; then
  MOD_DIR="$INSTALL_SCRIPT_DIR/install_modules"
else
  MOD_DIR="/tmp/cyberpanel_install_modules_$$"
  mkdir -p "$MOD_DIR"
  _module_names=(00_common 01_verify_deps 02_install_core 03_install_direct 04_fixes_status 05_menus_main 06_menus_update 07_menus_advanced 08_actions 09_parse_main)
  _branches_to_try=("$BRANCH_FOR_MODULES")
  if [[ "$BRANCH_FOR_MODULES" != "v2.5.5-dev" ]]; then
    _branches_to_try+=("v2.5.5-dev")
  fi
  if [[ "$BRANCH_FOR_MODULES" != "stable" ]] && [[ "${CYBERPANEL_GITHUB_OWNER:-master3395}" = "usmannasir" ]]; then
    _branches_to_try+=("stable")
  fi
  for name in "${_module_names[@]}"; do
    dest="$MOD_DIR/${name}.sh"
    _ok=0
    for try_branch in "${_branches_to_try[@]}"; do
      if _download_install_module "$name" "$try_branch" "$dest"; then
        if [[ "$try_branch" != "$BRANCH_FOR_MODULES" ]]; then
          echo "Note: install_modules/${name}.sh loaded from branch ${try_branch} (${BRANCH_FOR_MODULES} unavailable)."
          BRANCH_FOR_MODULES="$try_branch"
          export BRANCH_NAME="${BRANCH_FOR_MODULES}"
        fi
        _ok=1
        break
      fi
    done
    if [[ "$_ok" -eq 0 ]]; then
      echo "Failed to download install_modules/${name}.sh from ${CYBERPANEL_GITHUB_OWNER}/cyberpanel (tried: ${_branches_to_try[*]})."
      echo "Set branch explicitly: CYBERPANEL_BRANCH=v2.5.5-dev bash cyberpanel.sh"
      echo "Or: bash cyberpanel.sh -b v2.5.5-dev"
      exit 1
    fi
  done
fi

for f in "$MOD_DIR"/00_common.sh "$MOD_DIR"/01_verify_deps.sh "$MOD_DIR"/02_install_core.sh "$MOD_DIR"/03_install_direct.sh "$MOD_DIR"/04_fixes_status.sh "$MOD_DIR"/05_menus_main.sh "$MOD_DIR"/06_menus_update.sh "$MOD_DIR"/07_menus_advanced.sh "$MOD_DIR"/08_actions.sh "$MOD_DIR"/09_parse_main.sh; do
  if [[ -f "$f" ]]; then
    # shellcheck source=/dev/null
    source "$f"
  fi
done

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  if command -v sudo >/dev/null 2>&1; then
    echo "CyberPanel install requires root. Re-running with sudo..."
    _self="${BASH_SOURCE[0]:-$0}"
    if [[ -f "$_self" ]]; then
      exec sudo -E env CYBERPANEL_BRANCH="${BRANCH_FOR_MODULES}" CYBERPANEL_GITHUB_OWNER="${CYBERPANEL_GITHUB_OWNER}" bash "$_self" "$@"
    fi
  fi
  echo "ERROR: Run as root: sudo bash cyberpanel.sh -b ${BRANCH_FOR_MODULES}"
  if grep -qi microsoft /proc/version 2>/dev/null; then
    echo "WSL: curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/install.sh | sudo sh"
  fi
  exit 1
fi

main "$@"
