# FTP Quota Management – Browser Test Checklist

Use after deploying latest code. Open: `/ftp/quotaManagement`

## 1. Page load – status
- **Pure-FTPd stopped:** Yellow warning "Pure-FTPd is not running. Please enable Pure-FTPd first (Server Status → Services)..." and Enable button disabled/hidden.
- **Pure-FTPd running, quota on:** Green "FTP Quota system is already enabled"; button disabled.
- **Pure-FTPd running, quota off:** Blue info and enabled "Enable FTP Quota System" button.

## 2. Click Enable
- If FTP was running: success message and UI switches to "already enabled". No "Pure-FTPd did not start" error.
- If FTP was stopped: API returns "Pure-FTPd is not running. Please enable Pure-FTPd first...".

## 3. Table
- Quotas table loads; Refresh works.

## 4. One-time fix on server (if needed)
```bash
sudo sed -i 's/^Quota.*/Quota 100000:100000/' /etc/pure-ftpd/pure-ftpd.conf
sudo systemctl start pure-ftpd
```
