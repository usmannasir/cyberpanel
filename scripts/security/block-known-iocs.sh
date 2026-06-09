#!/usr/bin/env bash
# Block known CyberPanel #1764 attacker infrastructure (iptables).
set -euo pipefail

log() { echo "[block-known-iocs] $*"; }

EXTRA=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    --extra) EXTRA=1; shift ;;
    *) log "unknown arg: $1"; exit 1 ;;
  esac
done

block_ip() {
  local ip="$1"
  if iptables -C INPUT -s "$ip" -j DROP 2>/dev/null; then
    log "already blocked INPUT $ip"
  else
    iptables -A INPUT -s "$ip" -j DROP && log "blocked INPUT $ip"
  fi
  if iptables -C OUTPUT -d "$ip" -j DROP 2>/dev/null; then
    log "already blocked OUTPUT $ip"
  else
    iptables -A OUTPUT -d "$ip" -j DROP && log "blocked OUTPUT $ip"
  fi
}

block_ip "94.102.55.18"

if [[ "$EXTRA" -eq 1 ]]; then
  block_ip "80.78.18.178"
fi

log "done (persist iptables via your firewall save policy if required)"
