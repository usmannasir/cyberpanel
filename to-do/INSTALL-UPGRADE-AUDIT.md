# CyberPanel Install & Upgrade Setup – Audit (v2.5.5-dev)

This document summarizes the install/upgrade flow, required local files, and verification that everything is in place.

---

## 1. Install paths

### 1.1 Modular install (`cyberpanel.sh` + `install_modules/`)

- **Entry:** `cyberpanel.sh`
- **Branch for module download:** From `-b`/`--branch` or `CYBERPANEL_BRANCH`; default `stable`.
- **Required local dir:** `install_modules/` with:
  - `00_common.sh`, `01_verify_deps.sh`, `02_install_core.sh`, `03_install_direct.sh`, `04_fixes_status.sh`, `05_menus_main.sh`, `06_menus_update.sh`, `07_menus_advanced.sh`, `08_actions.sh`, `09_parse_main.sh`
- **Flow:** Sources all 10 modules, then calls `main "$@"`.
- **Status:** All 10 files present in repo.

### 1.2 Simplified install (`install.sh`)

- **Entry:** `install.sh` (sh)
- **Purpose:** Disk check, OS detection, then typically invokes full installer (e.g. `cyberpanel.sh` or monolithic).
- **Status:** Present; branch default `v2.5.5-dev`.

### 1.3 Monolithic install (`cyberpanel_install_monolithic.sh`)

- **Entry:** `cyberpanel_install_monolithic.sh`
- **Uses:** `install/install.py` (and `install/install_utils.py`). Requires `install/install.py` on disk.
- **Status:** `install/install.py` and `install/install_utils.py` present.

### 1.4 Install Python entry (`install/install.py`)

- **Used by:** Modular and monolithic install flows.
- **Requires:** `/root/.my.cnf` (created by install), `_ensure_mariadb_client_no_ssl()` for local MariaDB (writes `cyberpanel-client.cnf`, Debian `99-cyberpanel-client.cnf`).
- **Status:** MariaDB client no-SSL logic present; required files created at runtime.

---

## 2. Upgrade paths

### 2.1 Modular upgrade (`cyberpanel_upgrade.sh` + `upgrade_modules/`)

- **Entry:** `cyberpanel_upgrade.sh`
- **Branch for module download:** From `-b`/`--branch`; default `stable` when downloading; when run from repo uses local `upgrade_modules/`.
- **Required local dir:** `upgrade_modules/` with:
  - `00_common.sh`, `01_variables.sh`, `02_checks.sh`, `03_mariadb.sh`, `04_git_url.sh`, `05_repository.sh`, `06_components.sh`, `07_branch_input.sh`, `08_main_upgrade.sh`, `09_sync.sh`, `10_post_tweak.sh`, `11_display_final.sh`
- **Flow:**
  1. `Set_Default_Variables` → clears logs, sets `Branch_Name` (from cyberpanel.net unless overridden), `cd /root/cyberpanel_upgrade_tmp`
  2. `Check_Root`, `Check_Server_IP`, `Check_OS`, `Check_Provider`, `Check_Argument` → can set `Branch_Name` (`-b`/`--branch`), `Git_User_Override` (`-r`/`--repo`), MariaDB version, backup flags
  3. Optionally `Pre_Upgrade_Branch_Input`
  4. MariaDB version prompt if not set via args
  5. `Pre_Upgrade_Setup_Git_URL` → sets `Git_Content_URL`, `Git_Clone_URL` (default `master3395`, or CN `qtwrk`)
  6. `Pre_Upgrade_Setup_Repository` → OS-specific repos + MariaDB install/upgrade + `Ensure_MariaDB_Client_No_SSL`
  7. `Pre_Upgrade_Setup_Git_URL` (see 04)
  8. `Pre_Upgrade_Required_Components` → downloads `requirments.txt`/`requirments-old.txt`, `plogical/upgrade.py` into `/root/cyberpanel_upgrade_tmp`, venv/pip, recovery
  9. `Main_Upgrade` → ensures `ols_binaries_config.py`, **cd to dir containing upgrade.py**, runs `$CP_PYTHON upgrade.py $Branch_Name` (fallback venv if needed)
  10. `Sync_CyberCP_To_Latest` → git sync in `/usr/local/CyberCP`
  11. `Post_Upgrade_System_Tweak` → watchdog, requirments cleanup, lsphp fix, etc.
  12. `Post_Install_Display_Final_Info`
- **Status:** All 12 modules present. `08_main_upgrade.sh` now explicitly cd’s to directory containing `upgrade.py` before running it.

### 2.2 Remote files (modular upgrade)

Downloaded from `Git_Content_URL`/`Branch_Name` (e.g. `https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/`):

| Remote path | Used by | In repo? |
|-------------|---------|----------|
| `requirments.txt` | 06_components, 08 fallback, monolithic | Yes (root) |
| `requirments-old.txt` | 06 (fallback), 08 fallback, monolithic | Yes (root) |
| `install/ols_binaries_config.py` | 08 (ensure before upgrade.py) | Yes |
| `plogical/upgrade.py` | 06 (downloaded to `/root/cyberpanel_upgrade_tmp`) | Yes |
| `CPScripts/watchdog.sh` | 10_post_tweak | Yes |
| `install/litespeed/httpd_config.xml` | 06 (sed in upgrade.py for CN) | Yes |

All required remote files exist in the repo.

### 2.3 Monolithic upgrade (`cyberpanel_upgrade_monolithic.sh`)

- **Entry:** `cyberpanel_upgrade_monolithic.sh`
- **Flow:** Inlines logic equivalent to variables, checks, repository (including MariaDB client no-SSL), download requirements, upgrade.py run (with cd to dir containing upgrade.py), sync, post-tweak, display.
- **Status:** Same remote URLs; repo contains all referenced files. MariaDB client no-SSL block added at end of repository section.

---

## 3. Cross-cutting checks

### 3.1 Branch and Git user

- **Default Git user:** `master3395` (04_git_url.sh; 08_main_upgrade exports `CYBERPANEL_GIT_USER`).
- **Branch:** From `-b`/`--branch` or from cyberpanel.net version in `Set_Default_Variables`; v2.5.5-dev use `-b v2.5.5-dev`.

### 3.2 MariaDB client no-SSL (ERROR 2026)

- **Install:** `install/install.py` → `/root/.my.cnf` + `_ensure_mariadb_client_no_ssl()` (RHEL + Debian).
- **Upgrade modular:** `03_mariadb.sh` defines `Ensure_MariaDB_Client_No_SSL`; `05_repository.sh` calls it at end of `Pre_Upgrade_Setup_Repository`; `03` also calls it at end of `Pre_Upgrade_CentOS7_MySQL`.
- **Upgrade monolithic:** Inline block at end of `Pre_Upgrade_Setup_Repository`.
- See **to-do/MARIADB-CLIENT-NO-SSL-INSTALL-UPGRADE.md** for full coverage.

### 3.3 upgrade.py working directory

- **Modular:** `08_main_upgrade.sh` now cd’s to `/root/cyberpanel_upgrade_tmp` (or `/usr/local/CyberCP` if upgrade.py there) before running `upgrade.py`, so the script is always run from the directory that contains it.
- **Monolithic:** Same idea (cd to dir containing upgrade.py before running).

---

## 4. Summary

| Item | Status |
|------|--------|
| install_modules/ (10 files) | Present |
| upgrade_modules/ (12 files) | Present |
| install/install.py, install_utils.py | Present |
| install/ols_binaries_config.py | Present |
| plogical/upgrade.py | Present |
| requirments.txt, requirments-old.txt | Present (root) |
| CPScripts/watchdog.sh | Present |
| install/litespeed/httpd_config.xml | Present |
| Git default master3395, Branch from -b | Correct |
| MariaDB client no-SSL (install + upgrade) | Applied in all paths |
| upgrade.py run from correct cwd (modular) | Fixed (cd before run) |

**Conclusion:** Install and upgrade setup have all required local files. Modular upgrade now explicitly changes to the directory containing `upgrade.py` before running it. MariaDB client no-SSL is applied on install and on every upgrade path (modular and monolithic).
