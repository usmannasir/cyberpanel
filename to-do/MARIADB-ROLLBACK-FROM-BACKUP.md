# MariaDB rollback using upgrade backups

When you run a CyberPanel upgrade with MariaDB version change, an optional full backup of all databases can be created in two places:

1. **Legacy path:** `/root/cyberpanel_mariadb_backups/mariadb_backup_before_upgrade_YYYYMMDD_HHMMSS.sql.gz`
2. **Standard path:** `/root/db-upgrade-backups/YYYY-MM-DD_HHMMSS/all_databases.sql.gz`

To roll back to the previous MariaDB state (e.g. after a failed or undesired upgrade):

1. Stop MariaDB: `systemctl stop mariadb` (or `mysql`/`mysqld` on your system).
2. Restore the dump (example for the standard path):
   ```bash
   BACKUP_DIR="/root/db-upgrade-backups/2026-02-17_010304"  # use your actual folder
   gunzip -c "$BACKUP_DIR/all_databases.sql.gz" | mariadb --skip-ssl -u root -p
   ```
   Or if the backup is in the legacy location:
   ```bash
   gunzip -c /root/cyberpanel_mariadb_backups/mariadb_backup_before_upgrade_*.sql.gz | mariadb --skip-ssl -u root -p
   ```
   You will be prompted for the MariaDB root password (stored in `/etc/cyberpanel/mysqlPassword`).
3. If you need to reinstall the previous MariaDB server version, use the official MariaDB repo for that version, then start the service and run `mariadb-upgrade --force` if required.

**Note:** Restoring over an existing data directory is destructive. Only use this when you intend to replace the current databases with the backup. For a safe test, back up the current `/var/lib/mysql` first.

## Optional standalone version managers

For advanced MariaDB/phpMyAdmin version changes without running the full upgrade, you can use the community scripts from [cyberpanel-mods](https://github.com/master3395/cyberpanel-mods) (version-managers):

- [mariadb_version_manager_enhanced.sh](https://github.com/master3395/cyberpanel-mods/blob/main/version-managers/mariadb_version_manager_enhanced.sh) – interactive MariaDB version manager (backup, remove, add repo, install, secure).
- [mariadb_v_changer.sh](https://github.com/master3395/cyberpanel-mods/blob/main/version-managers/mariadb_v_changer.sh) – simple prompt-based MariaDB version changer.
- [phpmyadmin_v_changer.sh](https://github.com/master3395/cyberpanel-mods/blob/main/version-managers/phpmyadmin_v_changer.sh) – phpMyAdmin version changer (preserves config/signon).

CyberPanel install/upgrade now integrates equivalent behaviour (version choice, backup path, config preservation) so these scripts are optional for users who prefer a standalone workflow.
