#!/usr/bin/env bash
# Remove public firewalld exposure for port 8888; add high-priority reject.
# Idempotent. Safe when fastapi_ssh_server binds 127.0.0.1 only.
set -euo pipefail

log() { echo "[harden-firewall-8888] $*"; }

if ! command -v firewall-cmd >/dev/null 2>&1; then
  log "firewall-cmd not found; skipping"
  exit 0
fi

if ! systemctl is-active firewalld >/dev/null 2>&1; then
  log "firewalld inactive; skipping"
  exit 0
fi

REMOVE_RULES=(
  'rule family="ipv4" source address="0.0.0.0/0" port port="8888" protocol="tcp" accept'
  'rule family="ipv6" port port="8888" protocol="tcp" accept'
)

for rule in "${REMOVE_RULES[@]}"; do
  firewall-cmd --permanent --remove-rich-rule="$rule" 2>/dev/null && log "removed: $rule" || true
done

firewall-cmd --permanent --remove-port=8888/tcp 2>/dev/null || true
firewall-cmd --permanent --zone=public --remove-port=8888/tcp 2>/dev/null || true

REJECT_V4='rule priority="-20" family="ipv4" port port="8888" protocol="tcp" reject'
REJECT_V6='rule priority="-20" family="ipv6" port port="8888" protocol="tcp" reject'

if ! firewall-cmd --permanent --list-rich-rules 2>/dev/null | grep -Fq 'priority="-20" family="ipv4" port port="8888"'; then
  firewall-cmd --permanent --add-rich-rule="$REJECT_V4"
  log "added $REJECT_V4"
fi
if ! firewall-cmd --permanent --list-rich-rules 2>/dev/null | grep -Fq 'priority="-20" family="ipv6" port port="8888"'; then
  firewall-cmd --permanent --add-rich-rule="$REJECT_V6"
  log "added $REJECT_V6"
fi

firewall-cmd --reload
log "done; verify: ss -tlnp | grep 8888 (expect 127.0.0.1 only)"
