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

## Reference
- Upstream: https://github.com/jedisct1/pure-ftpd/blob/master/pure-ftpd.conf.in (comment: "Quota 1000:10").
- `pure-ftpd --help`: `-n	--quota	<opt>`.
