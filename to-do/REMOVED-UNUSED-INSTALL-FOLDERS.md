# Removed Unused install/ Folders

## Summary
Unused config folders under `install/` were removed; only the folders actually referenced by the codebase remain.

## Removed

### install/email-configs
- **Reason:** Never referenced. All code uses `install/email-configs-one` (e.g. `install/install.py`, `plogical/mailUtilities.py`, `mailServer/mailserverManager.py`).
- **Removed:** 2025-02-15.

### install/php-configs
- **Reason:** Never referenced. Code uses `install/phpconfigs` (no hyphen) only:
  - `plogical/installUtilities.py`: `shutil.copytree("phpconfigs", ...)` and `include phpconfigs/php*.conf`
  - `install/litespeed/conf/httpd_config.conf` and `serverStatus/litespeed/conf/httpd_config.conf`: `include phpconfigs/php53.conf` etc.
- **Note:** `php-configs` contained `php.ini` and `www.conf` (different purpose); `phpconfigs` contains `php53.conf` … `php80.conf` (LiteSpeed PHP version includes).
- **Removed:** 2025-02-15.

## Still in use
- `install/email-configs-one/` — mail configs used by install and mail utilities.
- `install/phpconfigs/` — LiteSpeed PHP version include configs used by install and httpd_config.
