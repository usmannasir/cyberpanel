#!/usr/bin/env bash
# First-boot CyberPanel install inside the panel container (systemd oneshot).
set -euo pipefail

MARKER="/etc/cyberpanel/.docker-initialized"
LOG="/var/log/cyberpanel-docker-firstboot.log"
INSTALLER="/usr/local/cyberpanel-installer"

mkdir -p /etc/cyberpanel /var/log
exec > >(tee -a "$LOG") 2>&1

if [ -f "$MARKER" ]; then
  echo "[first-boot] already initialized"
  exit 0
fi

export CYBERPANEL_CONTAINER=1
export DEBIAN_FRONTEND=noninteractive

ADMIN_USER="${CYBERPANEL_ADMIN_USER:-admin}"
ADMIN_PASS="${CYBERPANEL_ADMIN_PASSWORD:-}"
if [ -z "$ADMIN_PASS" ]; then
  ADMIN_PASS="$(head /dev/urandom | tr -dc A-Za-z0-9 | head -c 16)"
  echo "[first-boot] generated admin password (set CYBERPANEL_ADMIN_PASSWORD to fix)"
fi

BRANCH="${CYBERPANEL_BRANCH:-v3.0.4-dev}"
REPO="${CYBERPANEL_REPO:-master3395}"
HOSTNAME_FQDN="${CYBERPANEL_HOSTNAME:-cyberpanel.local}"
PUBLIC_IP="${CYBERPANEL_PUBLIC_IP:-127.0.0.1}"

echo "[first-boot] branch=$BRANCH repo=$REPO mode minimal=${CYBERPANEL_MINIMAL:-0}"

cd "$INSTALLER"

INSTALL_ARGS=(-v OLS -u "$ADMIN_USER" -p "$ADMIN_PASS" -b "$BRANCH" -r "$REPO")
if [ "${CYBERPANEL_MINIMAL:-0}" = "1" ]; then
  INSTALL_ARGS+=(-m)
  if [ "${CYBERPANEL_ENABLE_POSTFIX:-0}" = "1" ]; then
    INSTALL_ARGS+=(postfix)
  fi
  if [ "${CYBERPANEL_ENABLE_POWERDNS:-0}" = "1" ]; then
    INSTALL_ARGS+=(powerdns)
  fi
  if [ "${CYBERPANEL_ENABLE_PUREFTPD:-0}" = "1" ]; then
    INSTALL_ARGS+=(pureftpd)
  fi
fi

export Server_IP="$PUBLIC_IP"
export CYBERPANEL_HOSTNAME="$HOSTNAME_FQDN"
export CYBERPANEL_ADMIN_USER="$ADMIN_USER"
export CYBERPANEL_ADMIN_PASSWORD="$ADMIN_PASS"
export CYBERPANEL_BRANCH="$BRANCH"
export CYBERPANEL_REPO="$REPO"

echo "[first-boot] running: bash cyberpanel.sh ${INSTALL_ARGS[*]}"
bash "$INSTALLER/cyberpanel.sh" "${INSTALL_ARGS[@]}"

echo "[first-boot] install finished"
touch "$MARKER"
echo "1" > "$MARKER"
exit 0
