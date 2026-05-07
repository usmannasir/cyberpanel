#!/usr/bin/env bash
# Harden lscpd sudoers rules by replacing broad command access with allowlisted wrappers.
# Sourced by cyberpanel_upgrade.sh.

Post_Upgrade_LSCPD_Sudo_Hardening() {
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting LSCPD sudo hardening" | tee -a /var/log/cyberpanel_upgrade_debug.log

  local src_dir="/usr/local/CyberCP/scripts/sudo"
  local dst_dir="/usr/local/bin"
  local git_user="${Git_User:-master3395}"
  local branch="${Branch_Name:-stable}"
  local base="${Git_Content_URL:-https://raw.githubusercontent.com/${git_user}/cyberpanel}"

  mkdir -p "$dst_dir"
  mkdir -p "$src_dir"

  # Prefer scripts shipped with this checkout (works offline after git sync).
  local repo_root=""
  repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." 2>/dev/null && pwd || true)"
  if [[ -n "$repo_root" && -f "$repo_root/scripts/sudo/cyberpanel-safe-tail" ]]; then
    cp -f "$repo_root/scripts/sudo/cyberpanel-safe-tail" "$repo_root/scripts/sudo/cyberpanel-safe-pm2" \
      "$repo_root/scripts/sudo/cyberpanel-safe-fail2ban-client" "$src_dir/" 2>/dev/null || true
    chmod 755 "$src_dir"/cyberpanel-safe-tail "$src_dir"/cyberpanel-safe-pm2 "$src_dir"/cyberpanel-safe-fail2ban-client 2>/dev/null || true
  fi

  if [[ ! -f "$src_dir/cyberpanel-safe-tail" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Fetching LSCPD sudo helper scripts from ${base}/${branch}/scripts/sudo/ ..." | tee -a /var/log/cyberpanel_upgrade_debug.log
    for name in cyberpanel-safe-tail cyberpanel-safe-pm2 cyberpanel-safe-fail2ban-client; do
      local url="${base}/${branch}/scripts/sudo/${name}"
      if curl -fsSL --connect-timeout 20 "$url" -o "$src_dir/${name}.tmp" 2>/dev/null && [[ -s "$src_dir/${name}.tmp" ]]; then
        mv -f "$src_dir/${name}.tmp" "$src_dir/$name"
        chmod 755 "$src_dir/$name"
      elif wget -q --timeout=20 -O "$src_dir/${name}.tmp" "$url" 2>/dev/null && [[ -s "$src_dir/${name}.tmp" ]]; then
        mv -f "$src_dir/${name}.tmp" "$src_dir/$name"
        chmod 755 "$src_dir/$name"
      else
        rm -f "$src_dir/${name}.tmp"
        echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Could not download ${name} from branch ${branch}" | tee -a /var/log/cyberpanel_upgrade_debug.log
        return 1
      fi
    done
  fi

  if [[ ! -d "$src_dir" ]] || [[ ! -f "$src_dir/cyberpanel-safe-tail" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Missing $src_dir helpers after fetch." | tee -a /var/log/cyberpanel_upgrade_debug.log
    return 1
  fi

  for name in cyberpanel-safe-tail cyberpanel-safe-pm2 cyberpanel-safe-fail2ban-client; do
    if [[ -f "$src_dir/$name" ]]; then
      cp -f "$src_dir/$name" "$dst_dir/$name"
      chown root:root "$dst_dir/$name"
      chmod 755 "$dst_dir/$name"
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: Missing wrapper $src_dir/$name" | tee -a /var/log/cyberpanel_upgrade_debug.log
      return 1
    fi
  done

  cat > /etc/sudoers.d/pm2-logs <<'EOF'
Defaults:lscpd !requiretty
lscpd ALL=(root) NOPASSWD: /usr/local/bin/cyberpanel-safe-tail
EOF

  cat > /etc/sudoers.d/pm2-panel <<'EOF'
Defaults:lscpd !requiretty
lscpd ALL=(root) NOPASSWD: /usr/local/bin/cyberpanel-safe-pm2
EOF

  cat > /etc/sudoers.d/lscpd-fail2ban <<'EOF'
Defaults:lscpd !requiretty
lscpd ALL=(root) NOPASSWD: /usr/local/bin/cyberpanel-safe-fail2ban-client
EOF

  chown root:root /etc/sudoers.d/pm2-logs /etc/sudoers.d/pm2-panel /etc/sudoers.d/lscpd-fail2ban
  chmod 440 /etc/sudoers.d/pm2-logs /etc/sudoers.d/pm2-panel /etc/sudoers.d/lscpd-fail2ban

  if command -v visudo >/dev/null 2>&1; then
    visudo -c >/dev/null 2>&1
    if [[ $? -ne 0 ]]; then
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] ERROR: visudo validation failed, sudoers hardening not applied safely" | tee -a /var/log/cyberpanel_upgrade_debug.log
      return 1
    fi
  fi

  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Completed LSCPD sudo hardening" | tee -a /var/log/cyberpanel_upgrade_debug.log
  return 0
}
