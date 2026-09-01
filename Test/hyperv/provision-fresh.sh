#!/usr/bin/env bash
# Silent OLS install of master3395/cyberpanel v3.0.4-dev (Hyper-V smoke guest)
set -euo pipefail
if [ "$(id -u)" -ne 0 ]; then
  echo 'provision-fresh.sh must run as root'
  exit 1
fi
unset SUDO_USER SUDO_UID SUDO_GID SUDO_COMMAND 2>/dev/null || true
export DEBIAN_FRONTEND=noninteractive
dnf -y install curl wget git tar unzip python3 || yum -y install curl wget git tar unzip python3

export CYBERPANEL_BRANCH=v3.0.4-dev
export CYBERPANEL_GIT_USER=master3395
curl -fsSL "https://raw.githubusercontent.com/master3395/cyberpanel/v3.0.4-dev/cyberpanel.sh" \
  -o /tmp/cyberpanel.sh
chmod 700 /tmp/cyberpanel.sh
# Vagrant privileged:true leaves SUDO_* in the environment. Check_Root greps the output of set for SUDO.
su - root -c 'bash /tmp/cyberpanel.sh -v ols -u cpadmin -p TestPass12 -b 3.0.4-dev --repo master3395' \
  > /var/log/cp-hyperv-provision.log 2>&1
tail -n 40 /var/log/cp-hyperv-provision.log || true
if ! systemctl is-active --quiet lscpd; then
  echo 'INSTALL_FAILED lscpd not active'
  echo '--- provision log tail ---'
  tail -n 80 /var/log/cp-hyperv-provision.log || true
  exit 1
fi
echo "FRESH_INSTALL_DONE"
