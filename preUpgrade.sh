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
    BRANCH_NAME=v$(curl -fsSL --retry 3 --retry-delay 2 https://cyberpanel.net/version.txt | sed -e 's|{"version":"||g' -e 's|","build":|.|g'| sed 's:}*$::')
fi

echo "Upgrading CyberPanel from branch: $BRANCH_NAME"

rm -f /usr/local/cyberpanel_upgrade.sh

# Download upgrade script with HTTP status validation (avoid executing GitHub 429 HTML).
# Custom GitHub forks: pass --repo <github-user> through to cyberpanel_upgrade.sh.
download_upgrade_script() {
    _url="$1"
    _out="/usr/local/cyberpanel_upgrade.sh"
    _tmp="${_out}.tmp.$$"
    _code=$(curl -fsSL --retry 3 --retry-delay 5 -H 'Cache-Control: no-cache' -H 'Pragma: no-cache' \
        -w '%{http_code}' -o "$_tmp" "$_url" 2>/dev/null || echo "000")
    if [ "$_code" = "200" ] && [ -s "$_tmp" ] && head -1 "$_tmp" | grep -qE '^#!'; then
        mv -f "$_tmp" "$_out"
        return 0
    fi
    rm -f "$_tmp"
    echo "Failed to download upgrade script from $_url (HTTP ${_code})."
    return 1
}

if ! download_upgrade_script "https://raw.githubusercontent.com/usmannasir/cyberpanel/$BRANCH_NAME/cyberpanel_upgrade.sh"; then
    echo "Please retry later (GitHub raw may be rate-limited with HTTP 429)."
    echo "Or clone the repo and run: bash cyberpanel_upgrade.sh -b $BRANCH_NAME"
    echo "Custom fork: bash cyberpanel_upgrade.sh -b $BRANCH_NAME --repo <github-user>"
    exit 1
fi

chmod 700 /usr/local/cyberpanel_upgrade.sh
# Pass -b and all extra args (e.g. --mariadb-version, --repo, --backup-db) to upgrade script
/usr/local/cyberpanel_upgrade.sh -b "$BRANCH_NAME" $EXTRA_ARGS
