#!/bin/sh

# raw.githubusercontent.com intermittently answers HTTP 429 (rate limit). Executing
# that error page as a shell script produces confusing failures, so every download
# below is validated before use.

BRANCH_NAME=v$(curl -s https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g'| sed 's:}*$::')

case "$BRANCH_NAME" in
  v[0-9]*.[0-9]*)
    ;;
  *)
    echo ""
    echo "Failed to determine the CyberPanel version from https://cyberpanel.net/version.txt (got: '$BRANCH_NAME')."
    echo "Please check your network connection and retry later."
    exit 1
    ;;
esac

UPGRADE_URL="https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh"

rm -f /usr/local/cyberpanel_upgrade.sh

ATTEMPT=1
while [ "$ATTEMPT" -le 3 ]; do
    HTTP_CODE=$(curl -s -o /usr/local/cyberpanel_upgrade.sh -w "%{http_code}" "$UPGRADE_URL" 2>/dev/null)
    if [ "$HTTP_CODE" = "200" ] && head -n 1 /usr/local/cyberpanel_upgrade.sh | grep -q '^#!'; then
        chmod 700 /usr/local/cyberpanel_upgrade.sh
        exec /usr/local/cyberpanel_upgrade.sh
    fi
    echo "Failed to download upgrade script from GitHub (HTTP ${HTTP_CODE:-unknown}), attempt $ATTEMPT of 3."
    if [ "$HTTP_CODE" = "429" ]; then
        echo "GitHub is rate limiting downloads (HTTP 429 Too Many Requests). Waiting before retry..."
    fi
    ATTEMPT=$((ATTEMPT + 1))
    [ "$ATTEMPT" -le 3 ] && sleep 15
done

rm -f /usr/local/cyberpanel_upgrade.sh
echo ""
echo "Failed to download the upgrade script from GitHub (last response: HTTP ${HTTP_CODE:-unknown})."
echo "This is usually a temporary GitHub rate limit. Please retry the upgrade later."
exit 1
