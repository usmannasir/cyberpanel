#!/usr/bin/env bash
# fix-cyberpanel-500.sh – Apply common fixes for CyberPanel HTTP 500 on login.
# Run on the server: sudo bash fix-cyberpanel-500.sh
# See: to-do/CYBERPANEL-HTTP-500-LOGIN-FIX.md

set -e
LOG="/var/log/cyberpanel_500_fix.log"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

if [[ $EUID -ne 0 ]]; then
  echo "Run as root: sudo bash $0"
  exit 1
fi

log "=== CyberPanel 500 fix script started ==="

# 0. Ensure MariaDB is running (common cause: DB down -> 500)
log "Step 0: Ensuring MariaDB is running..."
systemctl start mariadb 2>/dev/null || systemctl start mysql 2>/dev/null || true
systemctl enable mariadb 2>/dev/null || systemctl enable mysql 2>/dev/null || true
log "Step 0 done."

# 1. Remove or neutralize configservercsf (common cause of 500)
log "Step 1: Cleaning configservercsf references..."
rm -rf /usr/local/CyberCP/configservercsf 2>/dev/null || true
rm -f /home/cyberpanel/plugins/configservercsf 2>/dev/null || true
rm -rf /usr/local/CyberCP/public/static/configservercsf 2>/dev/null || true
sed -i '/configservercsf/d' /usr/local/CyberCP/CyberCP/settings.py 2>/dev/null || true
sed -i '/configservercsf/d' /usr/local/CyberCP/CyberCP/urls.py 2>/dev/null || true
log "Step 1 done."

# 2. Clear Python cache
log "Step 2: Clearing __pycache__..."
find /usr/local/CyberCP -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
log "Step 2 done."

# 3. Restart panel and web server
log "Step 3: Restarting lscpd and lsws..."
systemctl restart lscpd
systemctl restart lsws
killall lsphp 2>/dev/null || true
log "Step 3 done."

log "=== Fix script finished. Try https://YOUR_IP:2087 or :8090 ==="
log "If 500 persists, enable DEBUG in /usr/local/CyberCP/CyberCP/settings.py and check logs (see to-do/CYBERPANEL-HTTP-500-LOGIN-FIX.md)."
