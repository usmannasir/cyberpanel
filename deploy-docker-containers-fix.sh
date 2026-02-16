#!/bin/bash
# Deploy Docker containers fix to live panel (/usr/local/CyberCP).
# Run this script ON the server (e.g. 84.247.184.182) as root or with sudo.
# Fix: HTTP 500 on /docker/containers - error handling + auto-migrate.

set -e
CYBERCP_ROOT="${CYBERCP_ROOT:-/usr/local/CyberCP}"
REPO_URL="${REPO_URL:-https://github.com/master3395/cyberpanel.git}"
BRANCH="${BRANCH:-v2.5.5-dev}"
WORK_DIR="/tmp/cyberpanel-deploy-docker-$$"

echo "[$(date -Iseconds)] Deploying Docker containers fix to ${CYBERCP_ROOT}"

# Clone repo (shallow, branch only)
mkdir -p "$WORK_DIR"
git clone --depth 1 --branch "$BRANCH" "$REPO_URL" "$WORK_DIR"

# Backup and copy fixed files
for f in dockerManager/container.py dockerManager/views.py; do
  src="$WORK_DIR/$f"
  dest="$CYBERCP_ROOT/$f"
  if [ ! -f "$src" ]; then
    echo "ERROR: $src not found in repo"
    exit 1
  fi
  if [ -f "$dest" ]; then
    cp -a "$dest" "${dest}.bak.$(date +%Y%m%d%H%M%S)"
  fi
  cp -a "$src" "$dest"
  echo "  -> $dest"
done

# Run migrations for dockerManager (creates table if missing)
if [ -x "$CYBERCP_ROOT/bin/python" ] && [ -f "$CYBERCP_ROOT/manage.py" ]; then
  echo "Running: manage.py migrate dockerManager --noinput"
  "$CYBERCP_ROOT/bin/python" "$CYBERCP_ROOT/manage.py" migrate dockerManager --noinput || true
fi

# Restart panel service so Django loads new code
if systemctl is-active --quiet lscpd 2>/dev/null; then
  echo "Restarting lscpd..."
  systemctl restart lscpd
elif systemctl is-active --quiet gunicorn 2>/dev/null; then
  echo "Restarting gunicorn..."
  systemctl restart gunicorn
else
  echo "Restart lscpd or gunicorn manually so the new code is loaded."
fi

# Cleanup
rm -rf "$WORK_DIR"
echo "[$(date -Iseconds)] Done. Test: https://YOUR_IP:2087/docker/containers"
