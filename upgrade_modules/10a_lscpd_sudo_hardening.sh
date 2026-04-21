#!/usr/bin/env bash
# Harden lscpd sudoers rules by replacing broad command access with allowlisted wrappers.
# Sourced by cyberpanel_upgrade.sh.

Post_Upgrade_LSCPD_Sudo_Hardening() {
  echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] Starting LSCPD sudo hardening" | tee -a /var/log/cyberpanel_upgrade_debug.log

  local src_dir="/usr/local/CyberCP/scripts/sudo"
  local dst_dir="/usr/local/bin"

  mkdir -p "$dst_dir"

  if [[ ! -d "$src_dir" ]]; then
    echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Missing $src_dir, skipping LSCPD sudo hardening" | tee -a /var/log/cyberpanel_upgrade_debug.log
    return 0
  fi

  for name in cyberpanel-safe-tail cyberpanel-safe-pm2 cyberpanel-safe-fail2ban-client; do
    if [[ -f "$src_dir/$name" ]]; then
      cp -f "$src_dir/$name" "$dst_dir/$name"
      chown root:root "$dst_dir/$name"
      chmod 755 "$dst_dir/$name"
    else
      echo -e "[$(date +"%Y-%m-%d %H:%M:%S")] WARNING: Missing wrapper $src_dir/$name" | tee -a /var/log/cyberpanel_upgrade_debug.log
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
