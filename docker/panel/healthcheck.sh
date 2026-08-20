#!/usr/bin/env bash
set -euo pipefail

curl -k -sf --max-time 15 https://127.0.0.1:8090/ >/dev/null || exit 1
systemctl is-active --quiet lscpd || exit 1
systemctl is-active --quiet mariadb || systemctl is-active --quiet mysql || exit 1
systemctl is-active --quiet firewalld || exit 1
systemctl is-active --quiet docker || exit 1

CONFIG="/etc/cyberpanel/container.json"
if [ -f "$CONFIG" ]; then
  if grep -q '"powerdns": true' "$CONFIG" 2>/dev/null; then
    systemctl is-active --quiet pdns || exit 1
  fi
  if grep -q '"postfix": true' "$CONFIG" 2>/dev/null; then
    systemctl is-active --quiet postfix || exit 1
  fi
  if grep -q '"pureftpd": true' "$CONFIG" 2>/dev/null; then
    systemctl is-active --quiet pure-ftpd || systemctl is-active --quiet pure-ftpd-mysql || exit 1
  fi
fi

exit 0
