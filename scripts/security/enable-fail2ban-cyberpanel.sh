#!/usr/bin/env bash
# Enable CyberPanel fail2ban jail with correct log path (AlmaLinux / CyberPanel 2.5.x).
set -euo pipefail
if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Run as root."
  exit 1
fi
JAIL_LOCAL="/etc/fail2ban/jail.local"
LOG_PATH="/usr/local/lscp/logs/error.log"
mkdir -p "$(dirname "$LOG_PATH")"
touch "$LOG_PATH"
chmod 640 "$LOG_PATH" 2>/dev/null || true
if [ ! -f "$JAIL_LOCAL" ]; then
  cp /etc/fail2ban/jail.conf "$JAIL_LOCAL" 2>/dev/null || touch "$JAIL_LOCAL"
fi
if grep -q '^\[cyberpanel\]' "$JAIL_LOCAL" 2>/dev/null; then
  sed -i "s|^logpath = .*|logpath = $LOG_PATH|" "$JAIL_LOCAL" 2>/dev/null || true
else
  cat >> "$JAIL_LOCAL" <<EOF

[cyberpanel]
enabled = true
port = 8090,2087
filter = cyberpanel
logpath = $LOG_PATH
maxretry = 5
bantime = 3600
findtime = 600
EOF
fi
FILTER_DIR="/etc/fail2ban/filter.d"
mkdir -p "$FILTER_DIR"
if [ ! -f "$FILTER_DIR/cyberpanel.conf" ]; then
  cat > "$FILTER_DIR/cyberpanel.conf" <<'FILTER'
[Definition]
failregex = ^.*Authentication failure.*<HOST>.*$
            ^.*Invalid login.*<HOST>.*$
ignoreregex =
FILTER
fi
systemctl enable fail2ban 2>/dev/null || true
systemctl restart fail2ban 2>/dev/null || service fail2ban restart 2>/dev/null || true
fail2ban-client status cyberpanel 2>/dev/null || echo "fail2ban cyberpanel jail configured; verify with: fail2ban-client status cyberpanel"
