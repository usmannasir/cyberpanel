# HTTP 500 after git sync – recovery steps

## Cause

After running `git reset --hard origin/v2.5.5-dev` and `git clean -fd` in `/usr/local/CyberCP`, the **repo’s** `CyberCP/settings.py` replaced the **server’s** production `settings.py`. The repo file has different (or placeholder) database credentials and config, so the app can’t connect to the DB or behaves incorrectly → **500** on `/base/` and elsewhere.

## 1. Restore production `settings.py`

Use one of these options.

### A. From your tarball backup (recommended)

You created a backup before sync, e.g.:

`/root/cybercp-backup-before-sync-YYYYMMDD-HHMMSS.tar.gz`

Restore only `settings.py`:

```bash
cd /root
# List to find the exact backup name
ls -la cybercp-backup-before-sync-*.tar.gz

# Restore CyberCP/settings.py (tarball was created from /usr/local/CyberCP so paths start with . or ./)
BACKUP=$(ls -t cybercp-backup-before-sync-*.tar.gz 2>/dev/null | head -1)
if [ -n "$BACKUP" ]; then
  tar -xzf "$BACKUP" -C /usr/local/CyberCP ./CyberCP/settings.py 2>/dev/null || \
  tar -xzf "$BACKUP" -C /usr/local/CyberCP CyberCP/settings.py 2>/dev/null
  echo "Restored settings.py from $BACKUP"
else
  echo "No backup found in /root"
fi
```

If the archive has no leading `./`, try:

```bash
tar -xzf "$BACKUP" -C /usr/local/CyberCP --strip-components=0 CyberCP/settings.py
# or
tar -xzf "$BACKUP" -C /tmp cp CyberCP/settings.py && mv /tmp/CyberCP/settings.py /usr/local/CyberCP/CyberCP/
```

### B. From upgrade script backup (if a previous upgrade ran)

The upgrade script backs up to `/tmp/cyberpanel_settings_backup.py`:

```bash
if [ -f /tmp/cyberpanel_settings_backup.py ]; then
  cp /tmp/cyberpanel_settings_backup.py /usr/local/CyberCP/CyberCP/settings.py
  echo "Restored settings.py from /tmp"
fi
```

### C. If you have no backup

Edit `/usr/local/CyberCP/CyberCP/settings.py` and set the **DATABASES** section to match your server:

- Same DB name, user, and password as used before the sync (e.g. from another backup or from the MySQL/MariaDB config your install used).

## 2. Restart CyberPanel / LiteSpeed

So the app loads the restored config:

```bash
systemctl restart lscpd
# or, depending on setup:
# systemctl restart lsws
```

Wait a few seconds, then try https://207.180.193.210:2087/ and https://207.180.193.210:2087/base/ again.

## 3. If 500 persists – get the real error

Run:

```bash
# Application log (Django/CyberPanel)
tail -100 /home/cyberpanel/error-logs.txt

# LiteSpeed / WSGI errors
tail -100 /usr/local/lscp/logs/error.log

# If present
tail -100 /usr/local/CyberCP/logs/cyberpanel.log
journalctl -u lscpd -n 50 --no-pager
```

Then run Django check and migrate:

```bash
cd /usr/local/CyberCP
source /usr/local/CyberCP/bin/activate   # if venv exists
python manage.py check
python manage.py migrate --noinput
```

Fix any errors reported (e.g. missing DB user, wrong password, or migrations).

## 4. Future syncs – keep production settings

Before running `git reset --hard` again:

1. Back up `settings.py`:
   ```bash
   cp /usr/local/CyberCP/CyberCP/settings.py /root/cyberpanel_settings_production.py
   ```
2. After sync, restore it:
   ```bash
   cp /root/cyberpanel_settings_production.py /usr/local/CyberCP/CyberCP/settings.py
   systemctl restart lscpd
   ```

Or add a small script that does sync then restores `settings.py` and restarts `lscpd`.
