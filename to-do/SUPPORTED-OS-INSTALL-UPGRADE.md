# Install/Upgrade Support Matrix (v2.5.5-dev)

This document summarizes how install and upgrade **detect and handle** each OS in the support table. It does **not** guarantee that every combination has been tested; it reflects what the code paths are.

## Summary

| OS family | Detection | Install/upgrade path | Notes |
|-----------|-----------|----------------------|--------|
| **AlmaLinux 10, 9, 8** | `AlmaLinux-8/9/10` in `/etc/os-release` | 9/10 → `AlmaLinux9` (dnf, repo fixes, venv). 8 → `CentOS` + version 8. | Explicit branches for 9/10 (EPEL, MariaDB, python3-venv). |
| **CentOS 7** | `CentOS Linux 7` in os-release | `CentOS` + version 7. | Legacy; EOL. Uses yum, requirments-old.txt. |
| **CloudLinux 9, 8** | `CloudLinux 7/8/9` in os-release | Normalized to `CentOS` + version. Same as RHEL family. | Version from VERSION_ID (e.g. 8 → 8, 9 → 9). |
| **Debian 13, 12, 11** | `Debian GNU/Linux 11/12/13` in os-release | Treated as **Ubuntu** (`Server_OS=Ubuntu`). Version 11/12/13 from VERSION_ID. | Uses **requirments-old.txt** (not requirments.txt). No Debian-specific package blocks; gets generic apt install. install_utils has Debian 13 package mappings. |
| **RHEL 9, 8** | `Red Hat Enterprise Linux` in os-release | Normalized to `CentOS` + version 8 or 9. | Same repo/package logic as CentOS 8/9. RHEL repo names differ; AlmaLinux-specific repo fixes do not run for RHEL. |
| **RockyLinux 9, 8** | `Rocky Linux` in os-release | Normalized to `CentOS`; version 8 or 9. | Same as CentOS 8/9 (EPEL, MariaDB, venv for 9/10). |
| **Ubuntu 24.04, 22.04, 20.04** | `Ubuntu 24.04` etc. in os-release | Explicit branches for 22/24 (packages, python3-venv). 20 → specific fixes. 18 → minimal. | 24.04: externally-managed-environment handled. Uses **requirments.txt** for 22 and 24. |

## Do we *know* it works on all of them?

- **Code coverage:** Detection and branching exist for all listed OSes. AlmaLinux 8/9/10, Ubuntu 18/20/22/24, Debian 11/12/13, CentOS 7/8/9, Rocky, RHEL, CloudLinux, and openEuler have explicit or normalized paths.
- **No automated proof:** There is no CI in this repo that runs install or upgrade on each OS. “Works” is based on:
  - Manual and community testing
  - Code review of detection and branches
- **RHEL:** Uses the same code path as CentOS (RedHat → CentOS). RHEL 9 uses different repo IDs than AlmaLinux; if repo issues appear on RHEL 9, RHEL-specific repo handling may be needed.
- **Debian 11/12/13:** Share the “Ubuntu” path and use **requirments-old.txt**. install_utils has Debian 13 (Trixie) package mappings. No Debian-version-specific blocks in the upgrade script.
- **CentOS 7:** Marked legacy/EOL; still in the script with yum and old requirements.

## Recommendations

1. **Staging:** Test install and upgrade on a non-production VM for your chosen OS before production.
2. **CI (optional):** Add a test matrix (e.g. GitHub Actions or other CI) that runs install and/or upgrade on a subset of OSes (e.g. AlmaLinux 9, Ubuntu 22.04, Debian 12) to catch regressions.
3. **Docs:** Keep this file (or a short “Supported platforms” section) in sync with the script when adding or dropping OS versions.

## Where to look in the repo

- **Upgrade OS detection:** `cyberpanel_upgrade.sh` (lines ~160–187), `Server_OS_Version` (~187), and branches for `CentOS`/`AlmaLinux9`/`Ubuntu`/`openEuler`.
- **Install OS detection:** `install/install.py` (`preFlightsChecks.detect_os`, `get_distro`), and `install/install_utils.py` (Debian/Ubuntu version and package helpers).
- **Requirements choice:** `cyberpanel_upgrade.sh` `Download_Requirement()`: uses `requirments.txt` for version 22, 24, 9, 10; else `requirments-old.txt`.
