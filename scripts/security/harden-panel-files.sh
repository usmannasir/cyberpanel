#!/usr/bin/env bash
# SEC-07/08: tighten panel TLS key and discourage .git exposure under CyberCP.
set -euo pipefail
if [[ "${EUID:-0}" -ne 0 ]]; then
  echo "Run as root."
  exit 1
fi
KEY="/usr/local/lscp/key.pem"
if [ -f "$KEY" ]; then
  chown root:root "$KEY" 2>/dev/null || true
  chmod 600 "$KEY"
  echo "key.pem mode set to 600"
fi
GITDIR="/usr/local/CyberCP/.git"
if [ -d "$GITDIR" ]; then
  chmod 700 "$GITDIR" 2>/dev/null || true
  echo "CyberCP .git directory chmod 700 (remove from web root if not required)"
fi
echo "Review vhost: deny HTTP access to /.git and /usr/local/CyberCP/.git"
