# MariaDB 11.8 LTS (Long Term Service)

## Summary

CyberPanel install and upgrade now target **MariaDB 11.8 LTS** instead of 10.11 or 12.1.

- **New installs:** Use `mariadb_repo_setup --mariadb-server-version=11.8` and install from official MariaDB 11.8 repo.
- **Upgrades:** Same; AlmaLinux 9 fix sets up 11.8 repo and installs MariaDB 11.8.
- **cyberpanel_upgrade.sh:** Writes `/etc/yum.repos.d/MariaDB.repo` with `baseurl = https://mirror.mariadb.org/yum/11.8/$MARIADB_REPO`.
- **UI (Database upgrade):** `databases/databaseManager.py` offers versions 10.6, 10.11, **11.8** for manual upgrade.
- **mysqlUtilities.UpgradeMariaDB:** Still accepts version argument; repo baseurl uses `versionToInstall` (e.g. 11.8).

## References

- `cyberpanel_upgrade.sh`: MariaDB.repo 11.8
- `plogical/upgrade.py`: mariadb_repo_setup 11.8, fix_almalinux9_comprehensive()
- `install/install.py`: mariadb_repo_setup 11.8, _attemptMariaDBUpgrade(), installMySQL(), disableMariaDB12RepositoryIfNeeded()
- `install/universal_os_fixes.py`: setup_mariadb_repository() 11.8
- `databases/databaseManager.py`: mysqlversions 10.6, 10.11, 11.8
- `plogical/mysqlUtilities.py`: UpgradeMariaDB() baseurl for RHEL
