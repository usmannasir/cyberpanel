#!/usr/bin/env bash
# Stock usmannasir v3.0.2 install, then modular upgrade to master3395 v3.0.2-dev
set -euo pipefail
dnf -y install curl wget git tar unzip python3 || yum -y install curl wget git tar unzip python3

curl -fsSL "https://raw.githubusercontent.com/usmannasir/cyberpanel/v3.0.2/cyberpanel.sh" \
  -o /tmp/cyberpanel.sh
chmod 700 /tmp/cyberpanel.sh
bash /tmp/cyberpanel.sh -v ols -p TestPass12 -b 3.0.2

# Prefer the fork upgrade loader once the stock panel is up.
curl -fsSL "https://raw.githubusercontent.com/master3395/cyberpanel/v3.0.2-dev/cyberpanel_upgrade.sh" \
  -o /usr/local/cyberpanel_upgrade.sh
chmod 700 /usr/local/cyberpanel_upgrade.sh
bash /usr/local/cyberpanel_upgrade.sh -b v3.0.2-dev --repo master3395 --mariadb-version 11.8
echo "UPGRADE_DONE"
