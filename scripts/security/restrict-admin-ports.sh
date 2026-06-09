#!/usr/bin/env bash
# Restrict CyberPanel (8090) and LiteSpeed admin (7080) to IPs in admin_ips.conf.
# Does NOT restrict SSH (22) or FTP (21). Hosting users keep SFTP/WinSCP access.
set -euo pipefail

CONF="${ADMIN_IPS_CONF:-/etc/cyberpanel/admin_ips.conf}"
PORTS=(8090 7080)

log() { echo "[restrict-admin-ports] $*"; }

if ! command -v firewall-cmd >/dev/null 2>&1; then
  log "firewall-cmd not found; abort"
  exit 1
fi

if [[ ! -f "$CONF" ]]; then
  log "Missing $CONF (one IPv4 per line, chmod 600). Aborting."
  exit 1
fi

mapfile -t IPS < <(grep -vE '^\s*(#|$)' "$CONF" | awk '{print $1}' | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$' || true)

if [[ "${#IPS[@]}" -eq 0 ]]; then
  log "No valid IPv4 addresses in $CONF"
  exit 1
fi

for ip in "${IPS[@]}"; do
  for port in "${PORTS[@]}"; do
    allow="rule family=\"ipv4\" priority=\"-10\" source address=\"${ip}\" port port=\"${port}\" protocol=\"tcp\" accept"
    if ! firewall-cmd --permanent --list-rich-rules 2>/dev/null | grep -Fq "source address=\"${ip}\" port port=\"${port}\""; then
      firewall-cmd --permanent --add-rich-rule="$allow"
      log "allow $ip -> $port"
    fi
  done
done

for port in "${PORTS[@]}"; do
  reject="rule family=\"ipv4\" priority=\"10\" port port=\"${port}\" protocol=\"tcp\" reject"
  if ! firewall-cmd --permanent --list-rich-rules 2>/dev/null | grep -Fq "priority=\"10\" port port=\"${port}\""; then
    firewall-cmd --permanent --add-rich-rule="$reject"
    log "reject others -> $port"
  fi
done

firewall-cmd --reload
log "done; ports 22 and FTP unchanged"
