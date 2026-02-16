# MariaDB Client No-SSL (ERROR 2026 Fix) – Install and Upgrade Coverage

This document summarizes where the MariaDB client “no SSL” configuration is applied so that **install** and **upgrade** both work when the server has `have_ssl=DISABLED` (avoids `ERROR 2026 (HY000): TLS/SSL error: SSL is required, but the server does not support it`).

## What gets applied

- **`[client]`** with **`ssl=0`** and **`skip-ssl`** in:
  - `/etc/my.cnf.d/cyberpanel-client.cnf` (RHEL/AlmaLinux/CentOS)
  - `/etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf` (Debian/Ubuntu, when that directory exists)
  - Optionally appended to **`/etc/my.cnf`** if it has no `[client]` section

## Install path

| Location | What happens |
|----------|----------------|
| **install/install.py** | Writes `/root/.my.cnf` with `[client]` including `ssl=0` and `skip-ssl`. When `remotemysql == 'OFF'`, calls `_ensure_mariadb_client_no_ssl()` which creates `/etc/my.cnf.d/cyberpanel-client.cnf` (RHEL) and `/etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf` (Debian/Ubuntu). |

So every **fresh install** (local MariaDB) gets the client no-SSL config.

## Upgrade path (modular: `cyberpanel_upgrade.sh` + `upgrade_modules/`)

| Module | What happens |
|--------|----------------|
| **03_mariadb.sh** | Defines **`Ensure_MariaDB_Client_No_SSL()`** (writes `cyberpanel-client.cnf`, optional `[client]` in `my.cnf`, and Debian `99-cyberpanel-client.cnf`). Called at end of **`Pre_Upgrade_CentOS7_MySQL`** when that path runs. |
| **05_repository.sh** | After all OS-specific repository and MariaDB install/upgrade logic (CentOS, AlmaLinux 9, Ubuntu/Debian, openEuler), calls **`Ensure_MariaDB_Client_No_SSL`** once. Every RHEL/DNF path also writes `cyberpanel-client.cnf` and optional `my.cnf` [client] inline; Ubuntu/Debian get the fix via this single call. |

So every **modular upgrade** run applies the client no-SSL config on all supported OSes.

## Upgrade path (monolithic: `cyberpanel_upgrade_monolithic.sh`)

| Location | What happens |
|----------|----------------|
| **Pre_Upgrade_Setup_Repository** | Each RHEL/DNF branch already creates `/etc/my.cnf.d/cyberpanel-client.cnf` with `ssl=0` and `skip-ssl` and optionally appends `[client]` to `/etc/my.cnf`. At the **end** of the same function (after Ubuntu and openEuler blocks), a single block runs that: creates `cyberpanel-client.cnf`, appends `[client]` to `my.cnf` if missing, and creates `/etc/mysql/mariadb.conf.d/99-cyberpanel-client.cnf` on Debian/Ubuntu. |

So every **monolithic upgrade** run also ensures the client no-SSL config on all paths.

## Verification

After install or upgrade:

```bash
mariadb -e "SELECT 1"
# or
mariadb -e "SELECT @@version;"
```

If these work without `ERROR 2026`, the client no-SSL configuration is in effect.

## Manual fix (if needed)

See **to-do/fix-phpmyadmin-mariadb-version-on-server.md** for a manual one-off fix on a single server.
