#!/usr/bin/env bash
# Stock usmannasir v3.0.2 install, then modular upgrade to master3395 v3.0.4-dev
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'provision-upgrade.sh must run as root'
  exit 1
fi
unset SUDO_USER SUDO_UID SUDO_GID SUDO_COMMAND 2>/dev/null || true
export DEBIAN_FRONTEND=noninteractive
dnf -y install curl wget git tar unzip python3 || yum -y install curl wget git tar unzip python3

curl -fsSL "https://raw.githubusercontent.com/master3395/cyberpanel/v3.0.4-dev/cyberpanel.sh" \
  -o /tmp/cyberpanel.sh
chmod 700 /tmp/cyberpanel.sh
su - root -c 'bash /tmp/cyberpanel.sh -v ols -p TestPass12 -b 3.0.2' \
  > /var/log/cp-hyperv-stock.log 2>&1
tail -n 20 /var/log/cp-hyperv-stock.log || true

curl -fsSL "https://raw.githubusercontent.com/master3395/cyberpanel/v3.0.4-dev/cyberpanel_upgrade.sh" \
  -o /usr/local/cyberpanel_upgrade.sh
chmod 700 /usr/local/cyberpanel_upgrade.sh
su - root -c 'bash /usr/local/cyberpanel_upgrade.sh -b v3.0.4-dev --repo master3395 --mariadb-version 11.8' \
  > /var/log/cp-hyperv-upgrade.log 2>&1
tail -n 40 /var/log/cp-hyperv-upgrade.log || true
if ! systemctl is-active --quiet lscpd; then
  echo 'UPGRADE_FAILED lscpd not active'
  echo '--- upgrade log tail ---'
  tail -n 80 /var/log/cp-hyperv-upgrade.log || true
  exit 1
fi
echo "UPGRADE_DONE"
