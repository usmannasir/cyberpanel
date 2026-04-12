#!/bin/bash
## Script to clear caches after static file changes. Useful for development and testing.
## All credit belongs to Usman Nasir
## To use make it executable
## chmod +x /usr/local/CyberCP/upgrade.sh
## Then run it like below.
## /usr/local/CyberCP/upgrade.sh

# Check if virtual environment exists
if [[ ! -f /usr/local/CyberCP/bin/python ]]; then
    echo "Error: CyberPanel virtual environment not found at /usr/local/CyberCP/bin/python"
    echo "Please ensure CyberPanel is properly installed."
    exit 1
fi

cd /usr/local/CyberCP && /usr/local/CyberCP/bin/python manage.py collectstatic --noinput --clear
/usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/panel_static_sync.py || {
  echo "panel_static_sync failed; falling back to manual copy"
  rm -rf /usr/local/CyberCP/public/static/*
  mkdir -p /usr/local/CyberCP/public/static
  cp -a /usr/local/CyberCP/static/. /usr/local/CyberCP/public/static/ 2>/dev/null || true
}
# CSF support removed - discontinued on August 31, 2025
# mkdir /usr/local/CyberCP/public/static/csf/
find /usr/local/CyberCP -type d -exec chmod 0755 {} \;
find /usr/local/CyberCP -type f -exec chmod 0644 {} \;
chmod -R 755 /usr/local/CyberCP/bin
chown -R root:root /usr/local/CyberCP
# LiteSpeed serves panel /static/ from public/static; restore ownership after blanket root:root.
chown -R lscpd:lscpd /usr/local/CyberCP/public/static 2>/dev/null || true
chown -R lscpd:lscpd /usr/local/CyberCP/public/phpmyadmin/tmp
systemctl restart lscpd
