#!/bin/bash
# CyberPanel upgrade – modular loader. Sources upgrade_modules/*.sh then runs upgrade flow.
# When upgrade_modules/ is missing (e.g. one-liner), downloads modules from GitHub.

if [[ $(id -u) -ne 0 ]] 2>/dev/null; then
  echo ""
  echo "This script must be run as root."
  echo "Run: sudo bash <(curl -sL https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh)"
  echo "     or for dev:  .../cyberpanel_upgrade.sh) -b v2.5.5-dev"
  echo "Or:   sudo su -   then run the same command without sudo"
  echo ""
  exit 1
fi

Sudo_Test=$(set)

# Parse -b/--branch for module download (when not running from repo). Default stable so one-liner works for both branches.
BRANCH_FOR_MODULES="stable"
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

# Resolve script directory (fallback when run via curl)
UPGRADE_SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-/usr/local/cyberpanel_upgrade.sh}")" 2>/dev/null && pwd)"
[[ -z "$UPGRADE_SCRIPT_DIR" ]] && UPGRADE_SCRIPT_DIR="/usr/local"

MOD_DIR=""
# A curl-installed loader lives in /usr/local and must not use stock
# /usr/local/CyberCP/upgrade_modules (those are the OLD build). Always fetch
# modules for the target branch so fork fixes (errorSanitizer, origin remap)
# actually run.
if [[ -d "$UPGRADE_SCRIPT_DIR/upgrade_modules" ]] && [[ "$UPGRADE_SCRIPT_DIR" != "/usr/local" ]]; then
  MOD_DIR="$UPGRADE_SCRIPT_DIR/upgrade_modules"
else
  MOD_DIR="/tmp/cyberpanel_upgrade_modules_$$"
  mkdir -p "$MOD_DIR"
  # Fetch modules from the fork (master3395) first so fork-only fixes apply; fall back to upstream.
  BASE_URL="https://raw.githubusercontent.com/master3395/cyberpanel/${BRANCH_FOR_MODULES}/upgrade_modules"
  BASE_URL_FALLBACK="https://raw.githubusercontent.com/usmannasir/cyberpanel/${BRANCH_FOR_MODULES}/upgrade_modules"
  for name in 00_common 01_variables 02_checks 03_mariadb 04_git_url 05_repository 06_components 07_branch_input 08_main_upgrade 09_sync 10_post_tweak 10a_lscpd_sudo_hardening 11_display_final; do
    curl -sL -H 'Cache-Control: no-cache' "$BASE_URL/${name}.sh" -o "$MOD_DIR/${name}.sh" 2>/dev/null || true
    if [[ ! -s "$MOD_DIR/${name}.sh" ]]; then
      curl -sL -H 'Cache-Control: no-cache' "$BASE_URL_FALLBACK/${name}.sh" -o "$MOD_DIR/${name}.sh" 2>/dev/null || true
    fi
  done
fi

for f in "$MOD_DIR"/00_common.sh "$MOD_DIR"/01_variables.sh "$MOD_DIR"/02_checks.sh "$MOD_DIR"/03_mariadb.sh "$MOD_DIR"/04_git_url.sh "$MOD_DIR"/05_repository.sh "$MOD_DIR"/06_components.sh "$MOD_DIR"/07_branch_input.sh "$MOD_DIR"/08_main_upgrade.sh "$MOD_DIR"/09_sync.sh "$MOD_DIR"/10_post_tweak.sh "$MOD_DIR"/10a_lscpd_sudo_hardening.sh "$MOD_DIR"/11_display_final.sh; do
  if [[ -f "$f" ]]; then
    # shellcheck source=upgrade_modules/00_common.sh
    source "$f"
  fi
done

if [[ ! -d /etc/cyberpanel ]]; then
  echo -e "\n\nCan not detect CyberCP..."
  exit 1
fi

Restart_Web_Terminal() {
if [[ -x /usr/local/CyberCP/bin/python ]] && \
   [[ -f /etc/systemd/system/fastapi_ssh_server.service ]]; then
  systemctl daemon-reload
  systemctl reset-failed fastapi_ssh_server >/dev/null 2>&1 || true
  if systemctl restart fastapi_ssh_server; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Web Terminal restarted after virtualenv rebuild" | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Web Terminal could not be restarted" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
fi
}

if [[ "$*" = *"--debug"* ]]; then
  Debug="On"
  Random_Log_Name=$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 5)
  find /var/log -name 'cyberpanel_debug_upgrade_*' -exec rm {} + 2>/dev/null || true
  echo -e "$(date)" > "/var/log/cyberpanel_debug_upgrade_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
  chmod 600 "/var/log/cyberpanel_debug_upgrade_$(date +"%Y-%m-%d")_${Random_Log_Name}.log"
fi

Set_Default_Variables
Check_Root
Check_Server_IP "$@"
Check_OS
Check_Provider
Check_Argument "$@"

if [[ "$*" != *"--branch "* ]] && [[ "$*" != *"-b "* ]]; then
  Pre_Upgrade_Branch_Input
fi

if [[ "$*" != *"--mariadb"* ]] && [[ "$*" != *"--mariadb-version "* ]]; then
  echo -e "\nMariaDB version: any X.Y or X.Y.Z supported."
  echo -e "Highlighted: \e[31m10.11.16\e[39m, \e[31m11.8\e[39m LTS (default), \e[31m12.x\e[39m (e.g. 12.1, 12.2, 12.3)."
  echo -e "Press Enter for 11.8 LTS, or type version (5 sec timeout): "
  read -r -t 5 Tmp_MariaDB_Ver || true
  Tmp_MariaDB_Ver="${Tmp_MariaDB_Ver// /}"
  if [[ -n "$Tmp_MariaDB_Ver" ]]; then
    MARIADB_VER="$Tmp_MariaDB_Ver"
    echo -e "MariaDB $MARIADB_VER selected.\n"
  else
    MARIADB_VER="11.8"
    echo -e "MariaDB 11.8 LTS (default).\n"
  fi
fi

MARIADB_VER_REPO=$(echo "$MARIADB_VER" | sed -n 's/^\([0-9]*\.[0-9]*\).*/\1/p')
[[ -z "$MARIADB_VER_REPO" ]] && MARIADB_VER_REPO="11.8" && MARIADB_VER="11.8"

mkdir -p /etc/cyberpanel
echo "$MARIADB_VER" > /etc/cyberpanel/mariadb_version
chmod 644 /etc/cyberpanel/mariadb_version
echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] MariaDB version set to: $MARIADB_VER" | tee -a /var/log/cyberpanel_upgrade_debug.log

Pre_Upgrade_Setup_Repository
Pre_Upgrade_Setup_Git_URL
Pre_Upgrade_Required_Components
Main_Upgrade
CYBERPANEL_GIT_SYNC_OK=0
if Sync_CyberCP_To_Latest; then
  CYBERPANEL_GIT_SYNC_OK=1
else
  echo -e "\e[31m[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Git sync of /usr/local/CyberCP to origin/$Branch_Name failed. Panel code may be outdated. See /var/log/cyberpanel_upgrade_debug.log and /etc/cyberpanel/last_git_sync_failed\e[0m" | tee -a /var/log/cyberpanel_upgrade_debug.log
fi
export CYBERPANEL_GIT_SYNC_OK
Post_Upgrade_System_Tweak || exit 1
Restart_Web_Terminal
CyberPanel_Final_Upgrade_Verification
Post_Install_Display_Final_Info
if [[ "$CYBERPANEL_GIT_SYNC_OK" -ne 1 ]] || [[ "${CYBERPANEL_UPGRADE_VERIFY_OK:-0}" -ne 1 ]]; then
  exit 1
fi
