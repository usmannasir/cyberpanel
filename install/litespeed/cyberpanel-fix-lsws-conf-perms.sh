#!/bin/bash
# Restore CyberPanel write access to OpenLiteSpeed config (cyberpanel user is in lsadm group).
set -euo pipefail
if [ ! -d /usr/local/lsws/conf ]; then
  exit 0
fi
chgrp -R lsadm /usr/local/lsws/conf
find /usr/local/lsws/conf -type d -exec chmod 770 {} +
find /usr/local/lsws/conf -type f -exec chmod 660 {} +
exit 0
