#!/usr/bin/env bash
# CyberPanel upgrade – sync CyberCP to latest commit. Sourced by cyberpanel_upgrade.sh.

Sync_CyberCP_To_Latest() {
  if [[ ! -d /usr/local/CyberCP/.git ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] No .git in /usr/local/CyberCP, skipping sync" | tee -a /var/log/cyberpanel_upgrade_debug.log
    return 0
  fi
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Syncing /usr/local/CyberCP to latest commit for branch: $Branch_Name" | tee -a /var/log/cyberpanel_upgrade_debug.log
  # Backup production settings so sync does not overwrite DB credentials / local config
  if [[ -f /usr/local/CyberCP/CyberCP/settings.py ]]; then
    cp /usr/local/CyberCP/CyberCP/settings.py /tmp/cyberpanel_settings_backup.py
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Backed up settings.py for restore after sync" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  (
    cd /usr/local/CyberCP
    git fetch origin 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
    if git show-ref -q "refs/remotes/origin/$Branch_Name"; then
      git checkout -B "$Branch_Name" "origin/$Branch_Name" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      git checkout "$Branch_Name" 2>/dev/null || true
      git pull --ff-only origin "$Branch_Name" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log || true
    fi
  )
  local sync_code=$?
  # Restore production settings so panel keeps working (DB, secrets, etc.)
  if [[ -f /tmp/cyberpanel_settings_backup.py ]]; then
    cp /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restored settings.py after sync" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  # LiteSpeed serves /static/ from public/static/; ensure it has latest baseTemplate static files (e.g. dashboard JS)
  if [[ -d /usr/local/CyberCP/public/static ]] && [[ -d /usr/local/CyberCP/baseTemplate/static/baseTemplate ]]; then
    rsync -a /usr/local/CyberCP/baseTemplate/static/baseTemplate/ /usr/local/CyberCP/public/static/baseTemplate/ 2>/dev/null || \
    cp -r /usr/local/CyberCP/baseTemplate/static/baseTemplate/* /usr/local/CyberCP/public/static/baseTemplate/ 2>/dev/null || true
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Synced baseTemplate static to public/static" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  # Firewall UI (firewall.js) – so Firewall Rules and Banned IPs load correct layout and Modify buttons
  if [[ -d /usr/local/CyberCP/public/static ]] && [[ -f /usr/local/CyberCP/firewall/static/firewall/firewall.js ]]; then
    mkdir -p /usr/local/CyberCP/public/static/firewall
    cp -f /usr/local/CyberCP/firewall/static/firewall/firewall.js /usr/local/CyberCP/public/static/firewall/ 2>/dev/null && \
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Synced firewall static to public/static" | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  fi
  if [[ $sync_code -eq 0 ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Sync completed. Current HEAD: $(git -C /usr/local/CyberCP rev-parse HEAD 2>/dev/null || echo 'unknown')" | tee -a /var/log/cyberpanel_upgrade_debug.log
  else
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Sync returned code $sync_code (non-fatal)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  return 0
}
