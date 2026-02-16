# Fix phpMyAdmin Showing 10.11 When 11.8 Is Installed

## 1. Fix CLI SSL error and see real server version

Run as root on the server:

```bash
# Allow mariadb client to connect without SSL (11.x client requires SSL by default)
mkdir -p /etc/my.cnf.d
printf '[client]\nskip-ssl = true\n' > /etc/my.cnf.d/cyberpanel-client.cnf

# Now this should work and show the *actual* server version on 3306
mariadb -e "SELECT @@version;"
```

- If it shows **11.8.x**: the server is 11.8; phpMyAdmin should show 11.8 after you **log out, clear cookies for :2087, then log in again via CyberPanel → Databases → phpMyAdmin**.
- If it still shows **10.11.x**: the process on 3306 is still 10.11. Force the 11.8 service to take over:

```bash
systemctl stop mariadb
sleep 3
systemctl start mariadb
mariadb -e "SELECT @@version;"
```

If it still shows 10.11, check:

```bash
rpm -q MariaDB-server
ss -tlnp | grep 3306
systemctl status mariadb
```

## 2. phpMyAdmin config (already correct on your server)

Your `config.inc.php` already has `host = '127.0.0.1'` and `port = '3306'`. Once the server on 3306 is 11.8 and you log in again via the panel, phpMyAdmin will show 11.8.
