#!/bin/sh

# Check for branch parameter
BRANCH_NAME=""
EXTRA_ARGS=""
while [ $# -gt 0 ]; do
    case "$1" in
        -b|--branch)
            BRANCH_NAME="$2"
            shift 2
            ;;
        *)
            EXTRA_ARGS="$EXTRA_ARGS $1"
            shift
            ;;
    esac
done

# If no branch specified, get stable version
if [ -z "$BRANCH_NAME" ]; then
    BRANCH_NAME=v$(curl -s https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g'| sed 's:}*$::')
fi

echo "Upgrading CyberPanel from branch: $BRANCH_NAME"

rm -f /usr/local/cyberpanel_upgrade.sh
# Use same repo as this script (master3395); fallback to usmannasir for compatibility
wget -O /usr/local/cyberpanel_upgrade.sh https://raw.githubusercontent.com/master3395/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh 2>/dev/null || \
wget -O /usr/local/cyberpanel_upgrade.sh https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh 2>/dev/null
chmod 700 /usr/local/cyberpanel_upgrade.sh
# Pass -b so upgrade script skips branch prompt and uses our branch
/usr/local/cyberpanel_upgrade.sh -b "$BRANCH_NAME" $EXTRA_ARGS
