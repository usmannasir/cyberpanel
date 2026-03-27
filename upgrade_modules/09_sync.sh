#!/usr/bin/env bash
# CyberPanel upgrade – sync CyberCP to latest commit. Sourced by cyberpanel_upgrade.sh.
# If local edits or untracked files block checkout, stash/quarantine and reset --hard to match origin.

Sync_CyberCP_To_Latest() {
  local SYNC_STATE_FILE="/etc/cyberpanel/last_git_sync_failed"
  mkdir -p /etc/cyberpanel
  rm -f "$SYNC_STATE_FILE" 2>/dev/null || true

  if [[ ! -d /usr/local/CyberCP/.git ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] No .git in /usr/local/CyberCP, skipping sync" | tee -a /var/log/cyberpanel_upgrade_debug.log
    return 0
  fi

  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Syncing /usr/local/CyberCP to latest commit for branch: $Branch_Name" | tee -a /var/log/cyberpanel_upgrade_debug.log

  if [[ -f /usr/local/CyberCP/CyberCP/settings.py ]]; then
    cp /usr/local/CyberCP/CyberCP/settings.py /tmp/cyberpanel_settings_backup.py
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Backed up settings.py for restore after sync" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi

  if ! cd /usr/local/CyberCP; then
    echo "1" > "$SYNC_STATE_FILE"
    return 1
  fi

  local remote_ref="origin/$Branch_Name"
  local fetch_rc sync_ok=0

  git fetch origin "$Branch_Name" 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
  fetch_rc="${PIPESTATUS[0]}"
  if [[ "$fetch_rc" -ne 0 ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: git fetch origin $Branch_Name failed (exit $fetch_rc)" | tee -a /var/log/cyberpanel_upgrade_debug.log
    echo "1" > "$SYNC_STATE_FILE"
    return 1
  fi

  if ! git show-ref -q "refs/remotes/$remote_ref"; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: remote ref $remote_ref not found after fetch" | tee -a /var/log/cyberpanel_upgrade_debug.log
    echo "1" > "$SYNC_STATE_FILE"
    return 1
  fi

  _cp_force_sync_to_remote_tip() {
    local ref="$1" quarantine dest rel
    git checkout -B "$Branch_Name" "$ref" >> /var/log/cyberpanel_upgrade_debug.log 2>&1
    if [[ $? -eq 0 ]]; then
      return 0
    fi
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Checkout blocked; stashing tracked+untracked changes and resetting --hard to $ref" | tee -a /var/log/cyberpanel_upgrade_debug.log
    git stash push -u -m "cyberpanel-upgrade-auto-$(date +%s)" >> /var/log/cyberpanel_upgrade_debug.log 2>&1 || true
    git reset --hard "$ref" >> /var/log/cyberpanel_upgrade_debug.log 2>&1
    if [[ $? -eq 0 ]]; then
      return 0
    fi
    quarantine="/root/cyberpanel_git_untracked_quarantine_$(date +%s)"
    mkdir -p "$quarantine"
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] reset --hard still blocked; moving untracked paths to $quarantine" | tee -a /var/log/cyberpanel_upgrade_debug.log
    # shellcheck disable=SC2162
    while IFS= read -r line; do
      case "$line" in
        \?\?*)
          rel="${line#??}"
          rel="${rel#"${rel%%[![:space:]]*}"}"
          if [[ -n "$rel" ]] && [[ -e "$rel" ]]; then
            dest="$quarantine/$rel"
            mkdir -p "$(dirname "$dest")"
            mv "$rel" "$dest" 2>/dev/null || mv "$rel" "$quarantine/" 2>/dev/null || true
          fi
          ;;
      esac
    done < <(git status --porcelain)
    git reset --hard "$ref" >> /var/log/cyberpanel_upgrade_debug.log 2>&1
    return $?
  }

  if _cp_force_sync_to_remote_tip "$remote_ref"; then
    local local_h remote_h
    local_h=$(git rev-parse HEAD 2>/dev/null)
    remote_h=$(git rev-parse "$remote_ref" 2>/dev/null)
    if [[ -n "$local_h" ]] && [[ -n "$remote_h" ]] && [[ "$local_h" == "$remote_h" ]]; then
      sync_ok=1
    fi
  fi

  if [[ "$sync_ok" -ne 1 ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: /usr/local/CyberCP HEAD does not match $remote_ref after forced sync (local=$(git rev-parse HEAD 2>/dev/null), remote=$(git rev-parse "$remote_ref" 2>/dev/null))" | tee -a /var/log/cyberpanel_upgrade_debug.log
    echo "1" > "$SYNC_STATE_FILE"
    if [[ -f /tmp/cyberpanel_settings_backup.py ]]; then
      cp /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py
    fi
    return 1
  fi

  if [[ -f /tmp/cyberpanel_settings_backup.py ]] && [[ -f /usr/local/CyberCP/upgrade_modules/merge_production_settings.py ]]; then
    python3 /usr/local/CyberCP/upgrade_modules/merge_production_settings.py /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py 2>&1 | tee -a /var/log/cyberpanel_upgrade_debug.log
    if [[ "${PIPESTATUS[0]}" -eq 0 ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Merged production DATABASES into branch settings.py (INSTALLED_APPS from branch preserved)" | tee -a /var/log/cyberpanel_upgrade_debug.log
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: settings merge failed; keeping branch settings.py as-is" | tee -a /var/log/cyberpanel_upgrade_debug.log
    fi
  elif [[ -f /tmp/cyberpanel_settings_backup.py ]]; then
    cp /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Restored settings.py after sync (merge script missing)" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi

  if [[ -d /usr/local/CyberCP/public/static ]] && [[ -d /usr/local/CyberCP/baseTemplate/static/baseTemplate ]]; then
    rsync -a /usr/local/CyberCP/baseTemplate/static/baseTemplate/ /usr/local/CyberCP/public/static/baseTemplate/ 2>/dev/null || \
    cp -r /usr/local/CyberCP/baseTemplate/static/baseTemplate/* /usr/local/CyberCP/public/static/baseTemplate/ 2>/dev/null || true
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Synced baseTemplate static to public/static" | tee -a /var/log/cyberpanel_upgrade_debug.log
  fi
  if [[ -d /usr/local/CyberCP/public/static ]] && [[ -f /usr/local/CyberCP/firewall/static/firewall/firewall.js ]]; then
    mkdir -p /usr/local/CyberCP/public/static/firewall
    cp -f /usr/local/CyberCP/firewall/static/firewall/firewall.js /usr/local/CyberCP/public/static/firewall/ 2>/dev/null && \
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Synced firewall static to public/static" | tee -a /var/log/cyberpanel_upgrade_debug.log || true
  fi

  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Sync completed. Current HEAD: $(git -C /usr/local/CyberCP rev-parse HEAD 2>/dev/null || echo 'unknown')" | tee -a /var/log/cyberpanel_upgrade_debug.log
  return 0
}
