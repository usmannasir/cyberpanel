# OpenLiteSpeed and LSWS Version Used by CyberPanel (Install & Upgrade)

**Updated:** OLS target 1.8.5+ (LiteSpeed repo); LSWS fallback 6.3.4.

## Summary

- **Install:** OpenLiteSpeed is installed via the **OS package manager** (no fixed version in code), then optionally replaced by CyberPanel’s **custom static binary** (based on **OpenLiteSpeed 1.8.5 – v2.0.5**).
- **Upgrade:** The CyberPanel **upgrade script does not change the OpenLiteSpeed version**. It only updates **LiteSpeed Enterprise** version references. During upgrade, **custom OLS binaries** (same 1.8.5-based build) are (re)installed if OLS is present.

---

## Install

1. **Package install**
   - `install/install.py` → `installLiteSpeed(ent=0)` → `install_package('openlitespeed')`.
   - So the **base** install is whatever **openlitespeed** version the distro provides (yum/dnf or apt). There is **no fixed OLS version** in the installer for this step.

2. **Custom binary (optional)**
   - Right after that, `installCustomOLSBinaries()` runs (in both `install/install.py` and `plogical/upgrade.py`).
   - It downloads a **static binary** from `https://cyberpanel.net/` (e.g. `openlitespeed-phpconfig-x86_64-rhel8-static`) and replaces `/usr/local/lsws/bin/openlitespeed`.
   - Comments in code state this is **OpenLiteSpeed 1.8.5** (upgrade.py) or **1.8.5 – v2.0.5** (install.py). The download URLs do not include a version; the binary is a fixed build hosted by CyberPanel.

So on **install**, you get either:
- **Distro OLS** (version = whatever the OS repo has), or  
- **CyberPanel custom OLS** (based on **1.8.5 / v2.0.5** static build) if the custom binary install succeeds.

---

## Upgrade

1. **cyberpanel_upgrade.sh**
   - Fetches **LiteSpeed Enterprise** latest version from:
     - `LSWS_Latest_URL="https://cyberpanel.sh/update.litespeedtech.com/ws/latest.php"`
     - Parses `LSWS_Stable_Version` from the `LSWS_STABLE` line.
   - Uses `LSWS_Stable_Version` only to **sed**-replace hardcoded Enterprise version strings (e.g. `lsws-5.3.8`, `lsws-5.4.2`, `lsws-5.3.5`) in `/usr/local/CyberCP/serverStatus/serverStatusUtil.py`.
   - So the **upgrade script does not install or upgrade OpenLiteSpeed**; it only updates **Enterprise** version references.

2. **plogical/upgrade.py**
   - During upgrade, if OpenLiteSpeed is present (`/usr/local/lsws/bin/openlitespeed` exists), it runs:
     - `Upgrade.installCustomOLSBinaries()`
   - That (re)installs the **same custom static OLS binary** (1.8.5-based, from cyberpanel.net). So **upgrade** does not pull a “new” OLS version from upstream; it only refreshes CyberPanel’s custom binary if OLS is in use.

---

## References (in repo)

| What | Where |
|------|--------|
| OLS package install (no version) | `install/install.py` → `install_package('openlitespeed')` in `installLiteSpeed()` |
| Custom OLS binary (1.8.5 / 1.8.5–v2.0.5) | `install/install.py` and `plogical/upgrade.py` → `installCustomOLSBinaries()` and `BINARY_CONFIGS` comments |
| LSWS version used in upgrade (Enterprise only) | `cyberpanel_upgrade.sh` → `LSWS_Latest_URL`, `LSWS_Stable_Version`, and sed to `serverStatusUtil.py` |
| Custom OLS on upgrade | `plogical/upgrade.py` → `if os.path.exists('/usr/local/lsws/bin/openlitespeed'): Upgrade.installCustomOLSBinaries()` |

---

## Short answers

- **What OpenLiteSpeed version does install use?**  
  Package: **distro default**. If custom binary is used: **OpenLiteSpeed 1.8.5 (or 1.8.5–v2.0.5)** static build from cyberpanel.net.

- **What OpenLiteSpeed version does upgrade use?**  
  Upgrade does **not** change OLS version from upstream. It only (re)installs the **same custom 1.8.5-based** binary when OLS is present. **LiteSpeed Enterprise** version is the one fetched from `cyberpanel.sh/update.litespeedtech.com/ws/latest.php` and written into `serverStatusUtil.py`.
