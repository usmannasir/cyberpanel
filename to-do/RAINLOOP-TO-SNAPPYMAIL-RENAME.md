# RainLoop → SnappyMail rename

## Summary
RainLoop has been replaced by SnappyMail. All **operational** paths and the install template folder now use SnappyMail. References to "rainloop" remain only where we **migrate from** old installs (2.4.4 → 2.5.5).

## Changes made

### Repo folder
- **`install/rainloop/`** renamed to **`install/snappymail/`**
- Template file still `cyberpanel.net.ini` (SnappyMail uses same format).

### Code updated to SnappyMail paths
- **plogical/mailUtilities.py** — Template path `/usr/local/CyberCP/install/snappymail/cyberpanel.net.ini`; all data paths `/usr/local/lscp/cyberpanel/snappymail/...`.
- **install/install.py** — chown and mkdir use `snappymail`; commented blocks updated for consistency.
- **plogical/acl.py** — `chown ... /usr/local/lscp/cyberpanel/snappymail`.
- **plogical/upgrade.py** — Operational chown and backup path use snappymail.

### Left as-is (intentional)
- **Migration logic** in `plogical/upgrade.py`, `upgrade_modules/10_post_tweak.sh`, and `cyberpanel_upgrade_monolithic.sh` still uses the **source** path `/usr/local/lscp/cyberpanel/rainloop/data` when upgrading from 2.4.4: they check for old rainloop data and rsync it to `/usr/local/lscp/cyberpanel/snappymail/data/`. That "rainloop" path must stay so existing servers upgrading from RainLoop get their data migrated.

## Upgrade to 2.5.5-dev: migrate ALL links to SnappyMail

On upgrade, the following ensure every RainLoop reference becomes SnappyMail:

1. **Data migration** (existing): rsync from `/usr/local/lscp/cyberpanel/rainloop/data` to `.../snappymail/data`, and update `include.php` paths.

2. **Replace all rainloop path/URL in migrated data**: After rsync, every config file under `snappymail/data` (`.ini`, `.json`, `.php`, `.cfg`) is scanned and any occurrence of:
   - `/usr/local/lscp/cyberpanel/rainloop/data` → `.../snappymail/data`
   - `/rainloop/` → `/snappymail/`
   - `rainloop/data` → `snappymail/data`
   is replaced. So stored links and paths in SnappyMail configs point to SnappyMail.

3. **HTTP redirect /rainloop → /snappymail**: In `/usr/local/CyberCP/public/.htaccess` a 301 redirect is added (or ensured once) so that:
   - `/rainloop`, `/rainloop/`, `/rainloop/anything` → `/snappymail/...`
   Old bookmarks and shared links keep working.

Implemented in: `plogical/upgrade.py` (`migrateRainloopToSnappymail`), `upgrade_modules/10_post_tweak.sh`, `cyberpanel_upgrade_monolithic.sh`.

## Result
- New installs and day-to-day operations use only SnappyMail paths.
- Upgrades from versions that had RainLoop: data migrated, all config links updated to snappymail, and /rainloop URLs redirect to /snappymail.
