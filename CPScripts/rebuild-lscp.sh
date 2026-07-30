#!/bin/bash
# Rebuild LSCP/WebAdmin runtime (conf + certs + pythonenv) without touching websites,
# MariaDB, OpenLiteSpeed vhosts, or user data. Addresses corrupted /usr/local/lscp/conf
# (see usmannasir/cyberpanel#1839).
set -euo pipefail

if [[ $(id -u) -ne 0 ]]; then
  echo "Must run as root."
  exit 1
fi

LOG="/var/log/cyberpanel_rebuild_lscp.log"
exec > >(tee -a "$LOG") 2>&1
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Starting LSCP rebuild"

CYBERCP="${CYBERCP:-/usr/local/CyberCP}"
LSCP_ROOT="/usr/local/lscp"
BACKUP_DIR="/usr/local/lscp-backup-$(date +%Y%m%d-%H%M%S)"

# Locate lscp.tar.gz
TAR=""
for candidate in \
  "${CYBERCP}/install/lscp.tar.gz" \
  "/usr/local/CyberCP/install/lscp.tar.gz" \
  "$(dirname "$0")/../install/lscp.tar.gz"
do
  if [[ -f "$candidate" ]]; then
    TAR="$candidate"
    break
  fi
done

if [[ -z "$TAR" ]]; then
  echo "ERROR: install/lscp.tar.gz not found. Clone the cyberpanel repo or ensure CyberCP install/ is present."
  exit 1
fi

echo "Using archive: $TAR"

# Backup existing tree if present
if [[ -d "$LSCP_ROOT" ]]; then
  mkdir -p "$BACKUP_DIR"
  cp -a "$LSCP_ROOT/." "$BACKUP_DIR/" 2>/dev/null || true
  echo "Backed up existing LSCP to $BACKUP_DIR"
fi

mkdir -p /usr/local
# Extract into /usr/local (archive contains lscp/...)
tar -xzf "$TAR" -C /usr/local

# Restore pythonenv / certs from backup when extract did not provide them
if [[ -d "$BACKUP_DIR/conf" ]]; then
  for f in pythonenv.conf bind.conf cert.pem key.pem php.ini mime.properties; do
    if [[ -f "$BACKUP_DIR/conf/$f" ]] && [[ ! -s "$LSCP_ROOT/conf/$f" ]]; then
      cp -a "$BACKUP_DIR/conf/$f" "$LSCP_ROOT/conf/$f"
      echo "Restored conf/$f from backup"
    fi
  done
  if [[ -d "$BACKUP_DIR/conf/ssl" ]] && [[ ! -d "$LSCP_ROOT/conf/ssl" ]]; then
    cp -a "$BACKUP_DIR/conf/ssl" "$LSCP_ROOT/conf/ssl"
  fi
fi

# Ensure pythonenv.conf points at CyberPanel venv
if [[ ! -f "$LSCP_ROOT/conf/pythonenv.conf" ]]; then
  cat > "$LSCP_ROOT/conf/pythonenv.conf" <<'PYENV'
path=/usr/local/CyberPanel/bin/python
PYENV
  echo "Wrote default pythonenv.conf"
fi

# Ensure TLS material for :8090 if missing
if [[ ! -f "$LSCP_ROOT/conf/cert.pem" ]] || [[ ! -f "$LSCP_ROOT/conf/key.pem" ]]; then
  mkdir -p "$LSCP_ROOT/conf"
  openssl req -x509 -nodes -days 820 -newkey rsa:2048 \
    -keyout "$LSCP_ROOT/conf/key.pem" \
    -out "$LSCP_ROOT/conf/cert.pem" \
    -subj "/CN=cyberpanel.local" >/dev/null 2>&1 || true
  echo "Generated self-signed LSCP certs"
fi

# Restore / re-link lscpd binary
mkdir -p "$LSCP_ROOT/bin"
lscpd_selection='lscpd-0.3.1'
if [[ -f /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" = "ubuntu" ]]; then
    ver="${VERSION_ID%%.*}"
    if [[ "$ver" = "22" || "$ver" = "24" || "$ver" = "26" ]]; then
      lscpd_selection='lscpd.0.4.0'
    fi
  fi
fi
if [[ "$(uname -m)" = "aarch64" ]]; then
  lscpd_selection='lscpd.aarch64'
fi

SRC=""
for c in "${CYBERCP}/${lscpd_selection}" "/usr/local/CyberCP/${lscpd_selection}"; do
  if [[ -f "$c" ]]; then SRC="$c"; break; fi
done
if [[ -n "$SRC" ]]; then
  cp -f "$SRC" "$LSCP_ROOT/bin/lscpd"
  chmod 755 "$LSCP_ROOT/bin/lscpd"
  echo "Installed lscpd from $SRC"
else
  echo "WARNING: Could not find ${lscpd_selection}; leaving existing lscpd binary in place if any"
fi

# Ownership
chown -R root:root "$LSCP_ROOT/conf" 2>/dev/null || true
chmod 700 "$LSCP_ROOT/conf" 2>/dev/null || true

systemctl daemon-reload 2>/dev/null || true
systemctl restart lscpd
sleep 2
if systemctl is-active --quiet lscpd; then
  echo "lscpd is active"
else
  echo "WARNING: lscpd failed to start; check: systemctl status lscpd"
  systemctl status lscpd --no-pager || true
  exit 1
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] LSCP rebuild complete. Panel should listen on :8090."
echo "Backup (if any): $BACKUP_DIR"
