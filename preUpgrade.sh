#!/bin/sh

# Check for branch parameter
BRANCH_NAME=""
if [ "$1" = "-b" ] || [ "$1" = "--branch" ]; then
    BRANCH_NAME="$2"
    shift 2
fi

# If no branch specified, get stable version
if [ -z "$BRANCH_NAME" ]; then
    BRANCH_NAME=v$(curl -s https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g'| sed 's:}*$::')
fi

echo "Upgrading CyberPanel from branch: $BRANCH_NAME"

rm -f /usr/local/cyberpanel_upgrade.sh
wget -O /usr/local/cyberpanel_upgrade.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh 2>/dev/null
chmod 700 /usr/local/cyberpanel_upgrade.sh
/usr/local/cyberpanel_upgrade.sh $@
