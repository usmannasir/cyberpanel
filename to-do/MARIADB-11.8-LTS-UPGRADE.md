# MariaDB 11.8 LTS and 12.1

## Summary

CyberPanel install and upgrade support **MariaDB 11.8 LTS** (default) or **12.1**. User can choose at install/upgrade time; **downgrade is supported** (e.g. 12.1 → 11.8 by re-running upgrader with `--mariadb-version 11.8`).

- **New installs:** `--mariadb-version 11.8|12.1` (default 11.8); `install.py` and `venvsetup.sh` pass it through.
- **Upgrades:** `cyberpanel_upgrade.sh --mariadb-version 11.8|12.1` or interactive prompt; writes `/etc/cyberpanel/mariadb_version` for `upgrade.py`.
- **Downgrade:** Run upgrader again with the desired version (e.g. `--mariadb-version 11.8` to switch from 12.1 to 11.8). Repo and packages will target the chosen version.
- **cyberpanel_upgrade.sh:** Uses `MARIADB_VER` (default 11.8) in `MariaDB.repo` baseurl and writes `/etc/cyberpanel/mariadb_version`.
- **plogical/upgrade.py:** `fix_almalinux9_mariadb()` reads `/etc/cyberpanel/mariadb_version` (default 11.8) and runs `mariadb_repo_setup` with that version.
- **UI (Database upgrade):** `databases/databaseManager.py` offers 10.6, 10.11, **11.8** for manual upgrade.
- **mysqlUtilities.UpgradeMariaDB:** Repo baseurl uses `versionToInstall` (e.g. 11.8).

## Testing

From repo root:

- Shell (upgrader argument parsing and repo URL logic):  
  `./test/upgrader_mariadb_version_test.sh`
- Python (mariadb_version file read and downgrade):  
  `python3 test/test_upgrade_mariadb_version.py`

Both 11.8 and 12.1 paths are tested; downgrade (12.1 → 11.8) is explicitly verified.

## References

- `cyberpanel_upgrade.sh`: MARIADB_VER, --mariadb-version, /etc/cyberpanel/mariadb_version
- `plogical/upgrade.py`: fix_almalinux9_mariadb() reads mariadb_version file
- `install/install.py`: --mariadb-version, preFlightsChecks.mariadb_version
- `install/venvsetup.sh`: MARIADB_VER prompt, --mariadb-version to install.py
- `install/universal_os_fixes.py`: setup_mariadb_repository() 11.8
- `databases/databaseManager.py`: mysqlversions 10.6, 10.11, 11.8
- `plogical/mysqlUtilities.py`: UpgradeMariaDB() baseurl for RHEL
