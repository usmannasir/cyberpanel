# Pure-FTPd Quota Syntax Fix (2026-02-04)

## Problem
Pure-FTPd failed to start with:
```
/etc/pure-ftpd/pure-ftpd.conf:35:1: syntax error line 35: [Quota ...].
```

## Cause
The config used `Quota yes`, but Pure-FTPd expects **`Quota maxfiles:maxsize`** (e.g. `Quota 1000:10` for 1000 files and 10 MB). The value is not a boolean.

## Fix applied

### On the server
- `/etc/pure-ftpd/pure-ftpd.conf`: line 35 set to `Quota 100000:100000` (high default so MySQL per-user quotas apply).
- Service started successfully: `systemctl start pure-ftpd`.

### In the repo
- **install/pure-ftpd/pure-ftpd.conf** and **install/pure-ftpd-one/pure-ftpd.conf**: `Quota yes` → `Quota 100000:100000`.
- **websiteFunctions/website.py** (`enableFTPQuota`): sed/echo now write `Quota 100000:100000` instead of `Quota yes` (or tabs).

## One-time fix on server (if "Enable" still breaks it)
Run on the server as root (copy script from repo or run inline):

**Option A – script (repo root: `fix-pureftpd-quota-once.sh`):**
```bash
sudo bash /path/to/fix-pureftpd-quota-once.sh
```

**Option B – inline:**
```bash
sudo sed -i 's/^Quota.*/Quota 100000:100000/' /etc/pure-ftpd/pure-ftpd.conf
# If TLS 1 is set but cert missing, disable TLS:
sudo sed -i 's/^TLS[[:space:]]*1/TLS 0/' /etc/pure-ftpd/pure-ftpd.conf
sudo systemctl start pure-ftpd
```
Then deploy the latest panel code so "Enable" uses the correct Quota syntax.

## Code safeguards (enableFTPQuota)
- **Backup before modify**: Timestamped backup of `pure-ftpd.conf` and `pureftpd-mysql.conf` before any change.
- **Safety net before restart**: If the Quota line is not valid (`Quota maxfiles:maxsize`), it is corrected to `Quota 100000:100000` so Pure-FTPd never gets an invalid line on restart.

## Reference
- Upstream: https://github.com/jedisct1/pure-ftpd/blob/master/pure-ftpd.conf.in (comment: "Quota 1000:10").
- `pure-ftpd --help`: `-n	--quota	<opt>`.
