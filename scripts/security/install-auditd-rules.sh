#!/usr/bin/env bash
# Optional: install auditd rules for SSH key and credential file changes.
set -euo pipefail

log() { echo "[install-auditd-rules] $*"; }

if ! command -v auditctl >/dev/null 2>&1; then
  log "auditd not installed; install auditd package first"
  exit 1
fi

RULES=/etc/audit/rules.d/cyberpanel-1764-watch.rules
cat >"$RULES" <<'EOF'
-w /root/.ssh/authorized_keys -p wa -k ssh_keys_watch
-w /root/.ssh -p wa -k ssh_keys_watch
-w /etc/cyberpanel/adminPass -p wa -k cyberpanel_creds_watch
-w /etc/cyberpanel/mysqlPassword -p wa -k cyberpanel_creds_watch
EOF

if command -v augenrules >/dev/null 2>&1; then
  augenrules --load
else
  auditctl -R "$RULES" 2>/dev/null || true
fi

systemctl enable --now auditd 2>/dev/null || true
log "rules installed in $RULES"
