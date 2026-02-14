# Firewall Banned IPs: Database Storage and "Ban IP Permanently" Fix

## Summary

- **Issue:** "Ban IP Permanently" from SSH Security Analysis did not show up in Firewall Management > Banned IPs.
- **Cause:** `addBannedIP` only wrote to a JSON file, while `getBannedIPs` tried the database first. When the `BannedIP` model was available, the list was read from the database (empty), so dashboard bans (stored only in JSON) did not appear.
- **Fix:** Primary storage is now the **database** (`BannedIP` model). `addBannedIP` saves to the database first; JSON file is used only when the model is unavailable (fallback). **JSON is used only for export/import**, not for primary storage.

## Storage Policy

| Use case              | Storage        |
|-----------------------|----------------|
| Adding a ban          | Database first, JSON fallback only if DB unavailable |
| Listing banned IPs    | Database first, JSON fallback only if DB unavailable |
| Export Banned IPs     | Output in **JSON format** (from DB or JSON store)     |
| Import Banned IPs     | Input in **JSON format**; writes to DB or JSON store |

Bans are **not** stored in a JSON file for normal operation when the database is available.

## Code Changes

1. **`firewall/firewallManager.py` – `addBannedIP`**
   - Tries to save to the `BannedIP` database model first.
   - Only uses the JSON file when the model cannot be imported (e.g. migrations not run).
   - Applies the firewall rule in both paths; rolls back the DB or JSON record if the firewall command fails.

2. **`firewall/migrations/0001_initial.py`** (new)
   - Creates the `firewall_bannedips` table and indexes for the `BannedIP` model.
   - Ensures the table exists after deploy.

## Deployment (Server)

1. **Copy updated code** from this repo to the panel (e.g. `/usr/local/CyberCP/`), including:
   - `firewall/firewallManager.py`
   - `firewall/models.py` (must define `BannedIP`)
   - `firewall/migrations/0001_initial.py`

2. **Run migrations** so the banned IPs table exists:
   ```bash
   cd /usr/local/CyberCP
   sudo -u cyberpanel /usr/local/CyberCP/bin/python manage.py migrate firewall
   ```
   If you see "table already exists" for `firewall_bannedips`, the table was created earlier; ensure `firewall.models` defines `BannedIP` and is in `INSTALLED_APPS`.

3. **Restart the panel** (e.g. lscpd / gunicorn) so the new code is loaded.

4. **Optional – one-time sync:** If you had bans only in the JSON file and want them in the DB, use **Firewall > Banned IPs > Export Banned IPs**, then **Import Banned IPs** with that file after migrations are applied (so imports go to the database).

## Verification

- Click "Ban IP Permanently" on an IP in **Dashboard > SSH Security Analysis**.
- Open **Firewall > Banned IPs** and confirm that IP appears in the list (from the database).
- Export/Import should still use JSON format for the file; listing and adding use the database when available.

## Run and test in the browser

**Done for you (on this machine):**

1. **Deployed** `firewall/firewallManager.py` to `/usr/local/CyberCP/firewall/`.
2. **Restarted** the panel backend: `systemctl restart lscpd` (lscpd is **active**).
3. Panel is listening on **port 2087** (e.g. `https://YOUR_SERVER_IP:2087`).

**Manual browser test:**

1. Open the CyberPanel URL (e.g. `https://207.180.193.210:2087` or `https://localhost:2087`). Accept the certificate warning if needed.
2. Log in as admin.
3. **Dashboard:** Scroll to **SSH Security Analysis**. If there is an alert (e.g. "Root Login Attempts Detected"), click **Ban IP Permanently** on one of the IPs (e.g. the "Top IP").
4. Confirm the success message (e.g. "IP address … has been permanently banned … You can manage it in the Firewall > Banned IPs section").
5. Go to **Firewall** (left menu) → **Banned IPs** tab.
6. **Verify:** The IP you just banned appears in the table (IP ADDRESS, REASON e.g. "Brute force attack detected from SSH Security Analysis", EXPIRES "Never", STATUS ACTIVE).
7. Optionally: **Export Banned IPs** → download JSON; **Import Banned IPs** → upload that JSON to confirm export/import still use JSON format.

**Quick API check (optional, from server):**

```bash
# After logging in in the browser, get session cookie or use a session ID, then:
curl -k -s -X POST 'https://127.0.0.1:2087/firewall/addBannedIP' \
  -H 'Content-Type: application/json' \
  -H 'Cookie: sessionid=YOUR_SESSION_ID' \
  -H 'X-CSRFToken: YOUR_CSRF_TOKEN' \
  -d '{"ip":"203.0.113.99","reason":"Test ban","duration":"permanent"}'
# Then open Firewall > Banned IPs and confirm 203.0.113.99 appears.
```
