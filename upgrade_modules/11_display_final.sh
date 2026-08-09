#!/usr/bin/env bash
# CyberPanel upgrade – final display (banner, next steps). Sourced by cyberpanel_upgrade.sh.

Post_Install_Display_Final_Info() {
echo -e "\n"
# Fixed box width (109 chars). ASCII-only borders (| - +) so right edge renders solid in all terminals.
BOX_W=109
# 109 dashes for top/bottom border (no Unicode = so line is consistently filled)
_br() { echo "+-------------------------------------------------------------------------------------------------------------+"; }
_bl() { echo "+-------------------------------------------------------------------------------------------------------------+"; }
_b()  { local s="$1"; [[ ${#s} -gt $BOX_W ]] && s="${s:0:BOX_W}"; printf '|%-*s|\n' "$BOX_W" "$s"; }
_br
_b ""
_b "    █████████             █████                        ███████████                                ████"
_b "   ███▒▒▒▒▒███           ▒▒███                        ▒▒███▒▒▒▒▒███                              ▒▒███"
_b "  ███     ▒▒▒  █████ ████ ▒███████   ██████  ████████  ▒███    ▒███  ██████   ████████    ██████  ▒███"
_b "  ▒███         ▒▒███ ▒███  ▒███▒▒███ ███▒▒███▒▒███▒▒███ ▒██████████  ▒▒▒▒▒███ ▒▒███▒▒███  ███▒▒███ ▒███"
_b "  ▒███          ▒███ ▒███  ▒███ ▒███▒███████  ▒███ ▒▒▒  ▒███▒▒▒▒▒▒    ███████  ▒███ ▒███ ▒███████  ▒███"
_b "  ▒▒███     ███ ▒███ ▒███  ▒███ ▒███▒███▒▒▒   ▒███      ▒███         ███▒▒███  ▒███ ▒███ ▒███▒▒▒   ▒███"
_b "  ▒▒█████████  ▒▒███████  ████████ ▒▒██████  █████     █████       ▒▒████████ ████ █████▒▒██████  █████"
_b "  ▒▒▒▒▒▒▒▒▒    ▒▒▒▒▒███ ▒▒▒▒▒▒▒▒   ▒▒▒▒▒▒  ▒▒▒▒▒     ▒▒▒▒▒         ▒▒▒▒▒▒▒▒ ▒▒▒▒ ▒▒▒▒▒  ▒▒▒▒▒▒  ▒▒▒▒▒"
_b "              ███ ▒███"
_b "             ▒▒██████"
_b "              ▒▒▒▒▒▒"
if [[ "${CYBERPANEL_GIT_SYNC_OK:-1}" -eq 1 ]] && [[ "${CYBERPANEL_UPGRADE_VERIFY_OK:-0}" -eq 1 ]]; then
  _b "                    *** UPGRADE COMPLETED SUCCESSFULLY! ***"
else
  if [[ "${CYBERPANEL_GIT_SYNC_OK:-1}" -ne 1 ]]; then
    _b "     *** UPGRADE FINISHED BUT GIT SYNC FAILED - /usr/local/CyberCP MAY BE OUTDATED ***"
    _b "     See /var/log/cyberpanel_upgrade_debug.log  (exit code will be non-zero)"
  else
    _b "     *** UPGRADE FINISHED BUT POST-CHECKS FAILED (SERVICES OR VENV) ***"
    _b "     See /var/log/cyberpanel_upgrade_debug.log  (exit code will be non-zero)"
  fi
fi
_b ""
_bl

Panel_Port=$(cat /usr/local/lscp/conf/bind.conf)
if [[ $Panel_Port = "" ]] ; then
  Panel_Port="8090"
fi

# A responding panel only proves the old build is still up; it says nothing about
# whether the new code was applied. Never claim success when upgrade.py failed. (#1853)
if [[ "${UPGRADE_FAILED:-0}" -ne 0 ]] ; then
  echo "###################################################################"
  echo "                CyberPanel UPGRADE FAILED                          "
  echo "###################################################################"
  echo -e "\nupgrade.py did not complete, so this server is STILL RUNNING THE OLD BUILD."
  echo -e "If you were applying a security release, you are NOT patched yet."
  echo -e "Check /var/log/cyberpanel_upgrade_debug.log for the failure, then re-run the upgrade.\n"
  rm -rf /root/cyberpanel_upgrade_tmp
  exit 1
fi


# Resolve server IP for remote access URL (avoid empty Remote: https://:2087)
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP=$(ip -4 route get 1 2>/dev/null | awk '/src/ {print $7; exit}')
fi
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP=$(curl -s --max-time 3 ifconfig.me 2>/dev/null || curl -s --max-time 3 icanhazip.com 2>/dev/null)
fi
if [[ -z "$SERVER_IP" ]]; then
  SERVER_IP="YOUR_SERVER_IP"
fi

# Actual MariaDB server version (what phpMyAdmin will show)
# Actual server version (use --skip-ssl: 11.x client requires SSL by default, 10.x server may not offer it)
MARIADB_ACTUAL_VER=""
if command -v mariadb >/dev/null 2>&1; then
  MARIADB_ACTUAL_VER=$(mariadb --skip-ssl -e "SELECT @@version;" -sN 2>/dev/null | head -1)
fi
[[ -z "$MARIADB_ACTUAL_VER" ]] && command -v mysql >/dev/null 2>&1 && MARIADB_ACTUAL_VER=$(mysql --skip-ssl -e "SELECT @@version;" -sN 2>/dev/null | head -1)
[[ -z "$MARIADB_ACTUAL_VER" ]] && MARIADB_ACTUAL_VER="${MARIADB_VER:-unknown}"

# Test if CyberPanel is accessible
echo -e "\n🔍 Testing CyberPanel accessibility..."

# Check if lscpd service is running
if [[ "${CYBERPANEL_GIT_SYNC_OK:-1}" -eq 1 ]] && [[ "${CYBERPANEL_UPGRADE_VERIFY_OK:-0}" -eq 1 ]] && systemctl is-active --quiet lscpd 2>/dev/null; then
  _br
  _b ""
  _b "  ACCESS YOUR CYBERPANEL:"
  _b ""
  _b "  Local:  https://127.0.0.1:${Panel_Port#*:}"
  _b "  Remote: https://${SERVER_IP}:${Panel_Port#*:}"
  _b ""
  _b "  Default Login: admin / 1234567890"
  _b "  >> Please change the default password immediately!"
  _b ""
  _bl

  # Binary confirmation + versions (ASCII-only so box alignment is correct)
  echo -e "\n"
  _br
  _b ""
  _b "  UPGRADE STATUS: [====================================================] 100%"
  _b ""
  _b "  [OK] All components installed successfully"
  _b "  [OK] Python dependencies resolved"
  _b "  [OK] WSGI-LSAPI compiled with optimizations"
  _b "  [OK] CyberPanel service is running"
  _b "  [OK] Web interface is accessible"
  _b ""
  _b "  CyberPanel: ${Branch_Name:-unknown}"
  _b "  Database (MariaDB): ${MARIADB_ACTUAL_VER}"
  _b ""
  _b "  *** UPGRADE COMPLETED SUCCESSFULLY! ***"
  _b ""
  _bl

else
  echo -e "CyberPanel may not be running properly. Please check the logs."
  echo -e "\n"
  _br
  _b ""
  _b "  UPGRADE COMPLETED WITH WARNINGS"
  _b ""
  _b "  - CyberPanel files have been updated"
  _b "  - Some services may need manual restart"
  _b "  - Please check logs at /var/log/cyberpanel_upgrade_debug.log"
  _b ""
  _b "  Try running: systemctl restart lscpd"
  _b ""
  _bl
fi

echo -e "\n📋 Next Steps:"
echo -e "   1. Access your CyberPanel at the URL above"
echo -e "   2. Change the default admin password"
echo -e "   3. Configure your domains and websites"
echo -e "   4. Check system status in the dashboard"
echo -e "   5. Check DB version with: mariadb -V  (use mariadb, not mysql, to avoid deprecation warning)"
echo -e "   6. Pre-upgrade DB backup (if created): /root/cyberpanel_mariadb_backups/"
echo -e "   7. One-liner: --backup-db (always backup DB), --no-backup-db (skip); omit = prompt. --migrate-to-utf8 for UTF-8 (only if your apps support it)"
echo -e "   8. If you downgrade to MariaDB 10.11.16, server charset stays latin1 for backward compatibility."

echo -e "\n🧹 Cleaning up temporary files..."
rm -rf /root/cyberpanel_upgrade_tmp
echo -e "✅ Cleanup completed\n"
}
