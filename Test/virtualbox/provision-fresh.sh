#!/usr/bin/env bash
# Silent OLS install of master3395/cyberpanel v3.0.2-dev
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
dnf -y install curl wget git tar unzip python3 || yum -y install curl wget git tar unzip python3

export CYBERPANEL_BRANCH=v3.0.2-dev
export CYBERPANEL_GIT_USER=master3395
curl -fsSL "https://raw.githubusercontent.com/master3395/cyberpanel/v3.0.2-dev/cyberpanel.sh" \
  -o /tmp/cyberpanel.sh
chmod 700 /tmp/cyberpanel.sh
bash /tmp/cyberpanel.sh -v ols -p TestPass12 -b 3.0.2-dev --repo master3395
echo "FRESH_INSTALL_DONE"
