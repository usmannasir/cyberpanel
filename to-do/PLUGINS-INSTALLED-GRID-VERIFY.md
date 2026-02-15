# Plugins Installed Grid – Install and Verify

## How install works

1. **Grid "Install" button**  
   - Tries **local install** first: plugin must exist under `/home/cyberpanel/plugins/` or `/home/cyberpanel-plugins/` (with `meta.xml`).  
   - If the API returns **404** or **"Plugin source not found"**, the UI automatically retries **store install** (download from GitHub `master3395/cyberpanel-plugins` and install).

2. **Store install**  
   - Used from the Store view or as fallback when local source is missing.  
   - Downloads the plugin from GitHub and runs the same installer (extract, pre_install, settings/URLs, inform CyberPanel, collectstatic, post_install).

3. **"Installed" status**  
   - A plugin is considered installed if the **directory** exists: `/usr/local/CyberCP/<plugin_name>/`.  
   - If that directory exists but `meta.xml` is missing, the UI still shows "Installed". On load of `/plugins/installed`, the backend tries to restore `meta.xml` from source (if source exists).

## Making sure all grid plugins install correctly

- **Local source**  
  Put plugin folders (each with `meta.xml`) in:
  - `/home/cyberpanel/plugins/<plugin_name>/`, or  
  - `/home/cyberpanel-plugins/<plugin_name>/`  
  Then use **Install** in the grid; local install will be used.

- **No local source**  
  Click **Install** in the grid; if local source is not found, the UI falls back to **store install** (GitHub). Ensure the plugin exists in `master3395/cyberpanel-plugins` (main branch).

- **Already installed but broken**  
  If a plugin directory exists under `/usr/local/CyberCP/` but `meta.xml` was missing, opening **Plugins → Installed** will try to copy `meta.xml` from source into the installed folder so version/update checks work.

## Quick checks on the server

```bash
# Installed plugin dirs
ls -la /usr/local/CyberCP/ | grep -E '^d'

# Local source (grid uses these for local install)
ls -la /home/cyberpanel/plugins/ 2>/dev/null || true
ls -la /home/cyberpanel-plugins/ 2>/dev/null || true

# Ensure meta.xml exists for an installed plugin (e.g. premiumPlugin)
ls -la /usr/local/CyberCP/premiumPlugin/meta.xml
```

After code changes, restart Gunicorn (or the CyberPanel app server) so the updated pluginHolder views and JS are used.
