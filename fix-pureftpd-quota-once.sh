#!/bin/bash
# One-time fix on the server: correct Pure-FTPd Quota line and start the service.
# Run as root: sudo bash fix-pureftpd-quota-once.sh
# Use when the panel has written invalid "Quota yes" and Pure-FTPd fails to start.

set -e
CONF=/etc/pure-ftpd/pure-ftpd.conf
SERVICE=pure-ftpd

if [ ! -f "$CONF" ]; then
  echo "Config not found: $CONF"
  exit 1
fi

# Fix Quota line (Pure-FTPd requires Quota maxfiles:maxsize, not "yes")
if grep -q '^Quota' "$CONF"; then
  sed -i 's/^Quota.*/Quota 100000:100000/' "$CONF"
  echo "Fixed Quota line in $CONF"
else
  echo 'Quota 100000:100000' >> "$CONF"
  echo "Appended Quota line to $CONF"
fi

# Optional: disable TLS if cert is missing (common cause of start failure)
if grep -q '^TLS[[:space:]]*1' "$CONF" && [ ! -f /etc/ssl/private/pure-ftpd.pem ]; then
  sed -i 's/^TLS[[:space:]]*1/TLS 0/' "$CONF"
  echo "Set TLS 0 (certificate missing)"
fi

# Start service
systemctl start "$SERVICE"
sleep 1
if systemctl is-active --quiet "$SERVICE"; then
  echo "Pure-FTPd is running."
  exit 0
else
  echo "Pure-FTPd failed to start. Run: systemctl status $SERVICE"
  exit 1
fi
