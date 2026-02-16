# Firewall Rules & Banned IPs – Making Sure Changes Load

If Firewall Rules or Banned IPs don’t show the latest UI (Modify buttons, Per-page dropdown, Search, etc.), do the following.

## 1. Sync firewall JavaScript (when you change firewall JS)

The panel can serve `firewall/firewall.js` from the **firewall app** (`firewall/static/firewall/firewall.js`) or from **static/** after collectstatic. The cache-buster uses the newest mtime from:

- `firewall/static/firewall/firewall.js`
- `static/firewall/firewall.js`
- `public/static/firewall/firewall.js`

So that the query param updates when any of these change.

**After editing `firewall/static/firewall/firewall.js`, sync copies so all paths are up to date:**

```bash
# From repo root
mkdir -p static/firewall public/static/firewall
cp firewall/static/firewall/firewall.js static/firewall/
cp firewall/static/firewall/firewall.js public/static/firewall/
```

## 2. Templates

The firewall **HTML** comes from the **firewall app** template:

- `firewall/templates/firewall/firewall.html`

Django loads it when you open the firewall page. There is no separate copy under `static/` or `baseTemplate/` for that page. So any change in `firewall/templates/firewall/firewall.html` is used as long as the running app is your repo (or a deploy that includes this file).

## 3. Where CyberPanel stores files (production)

- **Production root:** `/usr/local/CyberCP` – the full repo (including `firewall/`, `baseTemplate/`, etc.) lives here after install/upgrade.
- **Upgrade sync:** `upgrade_modules/09_sync.sh` runs from that directory (`git fetch` / checkout / pull). After sync, it copies **baseTemplate** static and **firewall** static into `public/static/` so LiteSpeed serves the latest dashboard and firewall JS.
- **Firewall code:** `firewall/templates/firewall/firewall.html` and `firewall/static/firewall/firewall.js` under `/usr/local/CyberCP`. LiteSpeed serves `/static/firewall/firewall.js` from `public/static/firewall/firewall.js`, which is updated by the upgrade script.

## 4. Production (e.g. `/usr/local/CyberCP`) – manual deploy

If the panel runs from an **installed** path (e.g. `/usr/local/CyberCP`), that directory is often a copy of the repo. Then:

- Replace or update the firewall app there with your repo version:
  - `firewall/templates/firewall/firewall.html`
  - `firewall/static/firewall/firewall.js`
- If the installer or deploy uses `static/` or `public/static/`, copy the same `firewall.js` there too (as in step 1).
- Restart the app server (e.g. Gunicorn/LiteSpeed) so Django and static file serving use the new files.

## 5. Browser cache

The script tag uses a cache-buster:  
`?v={{ CP_VERSION }}&fw={{ FIREWALL_STATIC_VERSION }}&cb=4`

- Do a **hard refresh**: Ctrl+Shift+R (Windows/Linux) or Cmd+Shift+R (Mac).
- Or clear cache for the panel site and reload.

## 6. Quick checklist

- [ ] `firewall/static/firewall/firewall.js` has the latest code.
- [ ] Synced to `static/firewall/firewall.js` and `public/static/firewall/firewall.js` (see step 1).
- [ ] `firewall/templates/firewall/firewall.html` has the latest markup (Modify buttons, modals, Per page dropdown).
- [ ] If using an installed path, copy updated firewall app (and static copies) there and restart the server.
- [ ] Hard refresh (or clear cache) in the browser.

After this, Firewall Rules and Banned IPs should load the correct layout and Modify buttons.
