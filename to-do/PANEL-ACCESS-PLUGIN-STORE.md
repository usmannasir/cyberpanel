# Panel Access plugin – store distribution

**Panel Access (Custom Domain)** is a normal plugin. It is **not** in the core repo’s `INSTALLED_APPS` or main URLs.

## Install on a server

1. **From zip (repo)**  
   - Build zip: from repo root, `zip -r panelAccess.zip panelAccess -x "panelAccess/__pycache__/*" -x "*.pyc"`  
   - In CyberPanel: **Plugins → Store** (or upload zip), install **Panel Access (Custom Domain)**.  
   - Or copy `panelAccess/` to `/usr/local/CyberCP/panelAccess/`, add `'panelAccess'` to `CyberCP/settings.py` `INSTALLED_APPS` (after `'emailPremium',`), and add  
     `path('plugins/panelAccess/', include('panelAccess.urls')),` to `CyberCP/urls.py` before the generic `path('plugins/', include('pluginHolder.urls'))`, then restart lscpd.

2. **From plugin store (GitHub)**  
   - Add the `panelAccess` folder to the **cyberpanel-plugins** repo (e.g. `master3395/cyberpanel-plugins`) so it appears in the store.  
   - Users then install via **Plugins → Store** like Memcache Manager or Contabo Auto Snapshot.

## URLs

- Settings page: **/plugins/panelAccess/**  
- Same as **Settings** from **Plugins → Installed** for Panel Access.

## Zip location

- `panelAccess.zip` can be generated in the repo root and committed or published for one-off installs.
