#!/bin/sh

rm -f /usr/local/cyberpanel_upgrade.sh
wget -O /usr/local/cyberpanel_upgrade.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/cyberpanel_upgrade.sh 2>/dev/null
chmod 700 /usr/local/cyberpanel_upgrade.sh
/usr/local/cyberpanel_upgrade.sh
