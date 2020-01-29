#!/bin/sh

BRANCH_NAME=v$(curl -s https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g'| sed 's:}*$::')

rm -f /usr/local/cyberpanel_upgrade.sh
wget -O /usr/local/cyberpanel_upgrade.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh 2>/dev/null
chmod 700 /usr/local/cyberpanel_upgrade.sh
/usr/local/cyberpanel_upgrade.sh
