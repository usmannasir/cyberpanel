#!/bin/bash
# Deploy updated plugins.html (installed-plugins search bar) to CyberPanel
# Run on the server where CyberPanel is installed (e.g. 207.180.193.210)
# Usage: sudo bash deploy-installed-plugins-search.sh
# Or from repo root: sudo bash pluginHolder/deploy-installed-plugins-search.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
SRC="$SCRIPT_DIR/templates/pluginHolder/plugins.html"
DEST="/usr/local/CyberCP/pluginHolder/templates/pluginHolder/plugins.html"

if [ ! -f "$SRC" ]; then
  echo "Error: Source not found: $SRC"
  exit 1
fi

if [ ! -f "$DEST" ]; then
  echo "Error: CyberPanel template not found: $DEST"
  exit 1
fi

echo "Backing up current template..."
cp "$DEST" "${DEST}.bak.$(date +%Y%m%d)"
echo "Copying updated plugins.html..."
cp "$SRC" "$DEST"
echo "Restarting lscpd..."
systemctl restart lscpd
echo "Done. Hard-refresh the browser (Ctrl+Shift+R) and open /plugins/installed#grid"
