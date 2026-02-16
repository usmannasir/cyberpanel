# phpMyAdmin vs CLI MariaDB Version Mismatch

## Why SSH / `mariadb -V` Shows 11.8 While phpMyAdmin Shows 10.11

Two main causes:

### 1. **Different connection target (most common)**

- **CLI** (`mariadb -V`, `mariadb -e "SELECT @@version;"`) uses the default connection: usually the **main** MariaDB instance (e.g. port 3306 or default socket).
- **phpMyAdmin** previously used host **`localhost`** (hardcoded). With `localhost`, the PHP MySQL client connects via the **default Unix socket**, not necessarily the same as the main instance.
- If you have (or had) **two** MariaDB instances (e.g. main on 3306 and a second on 3307 from `mysqld_multi`, or an old 10.11 still running), the CLI can hit 11.8 while PHP’s default socket pointed at the 10.11 instance.

### 2. **Client vs server version**

- `mariadb -V` prints the **client** version (e.g. 11.8). The upgrade script banner also used that for “Database (MariaDB): 11.8”.
- The **server** version is what phpMyAdmin shows. If the server was still 10.11 (e.g. wrong service restarted or second instance), phpMyAdmin correctly showed 10.11.

## Fix applied in code

- The panel now passes **host** (and port) from `/etc/cyberpanel/mysqlPassword` into the phpMyAdmin signon form.
- When the stored host is `localhost`, we send **`127.0.0.1`** so phpMyAdmin connects via **TCP to port 3306** (the main instance), not the default socket.
- So after deploy, phpMyAdmin should show the same MariaDB version as the CLI (the main 11.8 server).

## Verification on the server

Run as root:

```bash
# Server version (what phpMyAdmin should show after fix)
mariadb -e "SELECT @@version;"

# Listeners (only one MariaDB should be on 3306)
ss -tlnp | grep 3306

# Processes (check for duplicate mysqld/mariadbd)
ps aux | grep -E 'mariadb|mysqld'
```

If `SELECT @@version` shows 11.8 but phpMyAdmin still showed 10.11 before the fix, it was almost certainly a different connection (socket vs 127.0.0.1:3306 or a second instance). After the code change and a fresh phpMyAdmin login, it should report 11.8.

## If two instances exist

- Stop the old 10.11 instance (e.g. `mysqld_multi stop 1` if using `mysqld1` on 3307, or disable its service).
- Ensure only the 11.8 service (e.g. `mariadb.service`) is running and listening on 3306.
