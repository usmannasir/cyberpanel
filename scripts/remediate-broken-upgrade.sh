#!/usr/bin/env bash
# One-shot recovery after a failed v2.5.5-dev upgrade (see project docs). AlmaLinux/RHEL + existing CyberPanel.
set -Eeuo pipefail
LOG=/var/log/cyberpanel-upgrade/remediate-$(date +%Y%m%d-%H%M%S).log
mkdir -p "$(dirname "$LOG")"
exec > >(tee -a "$LOG") 2>&1

echo "[1/8] Build deps"
dnf install -y python3.11-devel MariaDB-devel gcc pkgconf-pkg-config || dnf install -y python3-devel MariaDB-devel gcc pkgconf-pkg-config

echo "[2/8] Re-fetch requirments.txt"
curl -fsSL -o /usr/local/requirments.txt \
  https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/requirments.txt

echo "[3/8] Reinstall venv requirements + gunicorn"
/usr/local/CyberCP/bin/pip install --no-cache-dir -r /usr/local/requirments.txt
/usr/local/CyberCP/bin/pip install --no-cache-dir 'gunicorn>=21,<24'
/usr/local/CyberCP/bin/python -c "import django, MySQLdb, gunicorn"

echo "[4/8] Backup /var/lib/mysql"
mkdir -p /root/cyberpanel_mariadb_backups
TS=$(date +%Y%m%d-%H%M%S)
tar -czf "/root/cyberpanel_mariadb_backups/var-lib-mysql-${TS}.tar.gz" -C /var/lib mysql

echo "[5/8] Disable AppStream mariadb module + install MariaDB (canonical names)"
dnf module reset -y mariadb || true
dnf module disable -y mariadb || true
dnf install -y MariaDB-server MariaDB-client MariaDB-shared \
               MariaDB-backup MariaDB-common MariaDB-devel
systemctl enable --now mariadb
if grep -q '"mysqlpassword"' /etc/cyberpanel/mysqlPassword 2>/dev/null; then
  ROOTPW=$(python3 -c "import json; print(json.load(open('/etc/cyberpanel/mysqlPassword')).get('mysqlpassword',''))" 2>/dev/null || true)
else
  ROOTPW=$(head -1 /etc/cyberpanel/mysqlPassword | tr -d '\r\n')
fi
mariadb-upgrade -u root -p"$ROOTPW"

echo "[6/8] Install gunicorn timeout drop-in (120s)"
mkdir -p /etc/systemd/system/cyberpanel.service.d
cat > /etc/systemd/system/cyberpanel.service.d/timeout.conf <<'INNER'
[Service]
ExecStart=
ExecStart=/usr/local/CyberCP/bin/gunicorn --pid /run/gunicorn/gucpid \
          --timeout 120 --graceful-timeout 30 --workers 2 \
          --bind 127.0.0.1:5003 \
          --access-logfile /var/log/gunicorn-access.log \
          --error-logfile  /var/log/gunicorn-error.log \
          CyberCP.wsgi
INNER

echo "[7/8] Restart backend + LSWS"
systemctl daemon-reload
systemctl restart cyberpanel.service
/usr/local/lsws/bin/lswsctrl restart

echo "[8/8] Verify"
CODE=$(curl -k -sS --max-time 30 -o /dev/null -w '%{http_code}' https://127.0.0.1:8090/)
if [[ "$CODE" =~ ^(200|302)$ ]]; then
  echo "OK panel returns $CODE"
else
  echo "FAIL panel returned $CODE"
  exit 1
fi
