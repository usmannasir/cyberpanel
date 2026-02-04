# FTP Quotas Table Fix

## Problem
- **URL:** https://207.180.193.210:2087/ftp/quotaManagement
- **Error:** `(1146, "Table 'cyberpanel.ftp_quotas' doesn't exist")`

The `FTPQuota` model in `websiteFunctions/models.py` uses `db_table = 'ftp_quotas'`, but the table had never been created in the database.

## Solution
1. **SQL:** `sql/create_ftp_quotas.sql` – `CREATE TABLE IF NOT EXISTS ftp_quotas` with columns and FKs to `loginSystem_administrator` and `websiteFunctions_websites`.
2. **Deploy script:** `deploy-ftp-quotas-table.sh` – Copies the SQL to `/usr/local/CyberCP/sql/` and runs it using Django’s DB connection (no password on command line).

## Deploy (already run)
```bash
sudo bash /home/cyberpanel-repo/deploy-ftp-quotas-table.sh
```

## Manual run (if needed)
From repo root:
```bash
sudo bash deploy-ftp-quotas-table.sh [REPO_DIR] [CP_DIR]
```
Default `CP_DIR` is `/usr/local/CyberCP`.

After deployment, reload `/ftp/quotaManagement` in the browser.
