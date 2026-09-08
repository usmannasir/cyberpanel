#!/bin/bash
# Deploy the latest pluginHolder plugins.html template to CyberPanel and verify.
# Run on the server where CyberPanel is installed.
# From repo root: bash pluginHolder/deploy-plugins-template.sh
# Or from anywhere: REPO_ROOT=/path/to/cyberpanel-repo bash /path/to/deploy-plugins-template.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="${REPO_ROOT:-$(cd "$SCRIPT_DIR/.." && pwd)}"
TEMPLATE_SRC="${REPO_ROOT}/pluginHolder/templates/pluginHolder/plugins.html"
TEMPLATE_DEST="/usr/local/CyberCP/pluginHolder/templates/pluginHolder/plugins.html"
MARKER="installedFilterBtnAll"  # Present only in latest template (Show: All | Installed only | Active only)

if [ ! -f "$TEMPLATE_SRC" ]; then
    echo "Error: Template not found at $TEMPLATE_SRC"
    echo "Set REPO_ROOT to the path of your cyberpanel repo."
    exit 1
fi

echo "Source: $TEMPLATE_SRC"
echo "Dest:   $TEMPLATE_DEST"

if grep -q "$MARKER" "$TEMPLATE_SRC"; then
    echo "Source template is the latest (contains Show/Installed only/Active only)."
else
    echo "Warning: Source template does not contain expected marker. Deploy anyway? (y/N)"
    read -r ans
    if [ "$ans" != "y" ] && [ "$ans" != "Y" ]; then
        exit 1
    fi
fi

if [ -f "$TEMPLATE_DEST" ]; then
    cp -a "$TEMPLATE_DEST" "${TEMPLATE_DEST}.bak.$(date +%Y%m%d%H%M%S)"
    echo "Backed up existing template."
fi

mkdir -p "$(dirname "$TEMPLATE_DEST")"
cp -a "$TEMPLATE_SRC" "$TEMPLATE_DEST"
echo "Copied template to $TEMPLATE_DEST"

if command -v systemctl >/dev/null 2>&1 && systemctl is-active --quiet lscpd 2>/dev/null; then
    echo "Restarting lscpd..."
    systemctl restart lscpd
    echo "lscpd restarted."
else
    echo "Please restart your panel (e.g. systemctl restart lscpd)."
fi

if grep -q "$MARKER" "$TEMPLATE_DEST"; then
    echo "OK: Deployed template is latest. Verify: https://YOUR-PANEL:2087/plugins/installed#grid"
else
    echo "Warning: Deployed file missing expected marker."
    exit 1
fi
