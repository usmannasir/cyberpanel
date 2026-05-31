#!/usr/bin/env bash
# Optional: restrict lscpd (2087) to trusted IPs. Usage: restrict-panel-port-2087.sh 1.2.3.4 [more IPs]
set -euo pipefail
if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Run as root."
  exit 1
fi
if [ "$#" -lt 1 ]; then
  echo "Usage: $0 <trusted-ip> [trusted-ip...]"
  echo "Adds firewalld rich rules allowing 2087/tcp only from listed IPs."
  exit 1
fi
if ! command -v firewall-cmd >/dev/null 2>&1; then
  echo "firewalld not found; configure 2087 manually."
  exit 1
fi
for ip in "$@"; do
  rule="rule family=\"ipv4\" source address=\"${ip}\" port port=\"2087\" protocol=\"tcp\" accept"
  firewall-cmd --permanent --add-rich-rule="$rule" || true
done
firewall-cmd --reload 2>/dev/null || true
echo "Rich rules added for 2087/tcp from: $*"
echo "Ensure SSH/console access remains available before locking yourself out."
