# CyberPanel Behind a Reverse Proxy (Custom Domain)

When you put a **custom domain** in front of the panel (e.g. `https://panel.example.com` → proxy → `http://127.0.0.1:2087`), two things often break if the proxy is not configured for them:

1. **403 on POST requests** (e.g. Ban IP, form submissions) — **CSRF verification failed**
2. **Charts / some UI not loading** — backend may treat the request as different from “direct” IP:port access

With **IP:port** everything works because the browser and the backend agree on the same host.

---

## Why it breaks

- The **browser** sends `Origin` / `Referer` with the **public URL** (e.g. `https://panel.example.com`).
- The **proxy** often forwards the request with **Host** set to the **backend** (e.g. `127.0.0.1:2087` or `207.180.193.210:2087`).
- **Django** checks CSRF by comparing the request’s **Referer/Origin** to the request’s **Host**. They don’t match → **403 Forbidden** and the body says *“CSRF verification failed. Request aborted.”*

So: **domain in the browser, backend host in `Host`** → CSRF fails and POSTs (like Ban IP) get 403.

---

## Fix option 1: Panel Access (recommended, no env vars)

Use the built-in **Panel Access** page to add your custom domain(s):

1. In CyberPanel go to **Plugins → Panel Access (Custom Domain)**.
2. Enter your public origin(s), one per line (e.g. `https://panel.example.com`, `http://panel.example.com`).
3. Click **Save**.
4. Restart the CyberPanel backend so Django picks up the change, e.g.:
   ```bash
   systemctl restart lscpd
   ```

Origins are stored in a config file (by default `/home/cyberpanel/panel_csrf_origins.conf`). They are merged with any `CSRF_TRUSTED_ORIGINS` set via environment. No hardcoded domains; safe for GitHub.

**OpenLiteSpeed proxy (optional):** On the same page you can enable **“Also add domain in OpenLiteSpeed (reverse proxy to panel)”**. When you save, the panel will create a proxy vhost for each domain so the panel is reachable at that domain (e.g. `http://panel.example.com`) without manual OLS configuration. This only configures HTTP (port 80); for HTTPS use Manage SSL or your own certificate. The proxy forwards to the panel backend (default `https://127.0.0.1:2087`). Override with the `PANEL_BACKEND_URL` environment variable if your panel listens elsewhere.

---

## Fix option 2: Environment variable

In `CyberCP/settings.py`, `CSRF_TRUSTED_ORIGINS` is also built from the environment variable **`CSRF_TRUSTED_ORIGINS`** (comma‑separated list of origins).

When you run the panel behind a custom domain, you can set that variable to your **public** origin(s), for example:

```bash
export CSRF_TRUSTED_ORIGINS="https://panel.example.com,http://panel.example.com"
```

Then start (or restart) the CyberPanel backend. Where to set it depends on how you run the panel:

- **systemd (lscpd)**: add to `[Service]` in `/etc/systemd/system/lscpd.service`:
  ```ini
  Environment="CSRF_TRUSTED_ORIGINS=https://panel.example.com,http://panel.example.com"
  ```
  Then run `systemctl daemon-reload` and `systemctl restart lscpd`.
- **Supervisor / other**: set in the program’s `environment` or equivalent.
- **Manual run**: export in the same shell before starting the app.

Use your real domain; no need to add anything to the repo. This keeps the codebase generic for GitHub.

---

## Optional: proxy Host header

Some backends only “recognise” the panel when **Host** is the backend address (e.g. IP:port). In that case the proxy is often configured to **override** Host to that address so the initial HTML and routing work. That is why the **same** proxy setup can make the **page** load but **POSTs** fail: Referer stays the public domain, Host is the backend → CSRF fails. Fixing CSRF with `CSRF_TRUSTED_ORIGINS` (as above) addresses that.

---

## Summary

| Symptom              | Cause                          | Fix (generic, repo‑friendly) |
|----------------------|--------------------------------|--------------------------------|
| 403 on Ban IP / POST | CSRF fail (Referer vs Host)   | **Panel Access**: Plugins → Panel Access (Custom Domain), add your origin(s), save, then restart lscpd. Or set `CSRF_TRUSTED_ORIGINS` env and restart backend. |
| Charts / UI not loading | Can be session/Host/static | Ensure session cookies and static URLs work; CSRF fix above helps POSTs; adjust proxy if needed |

No domain is hardcoded in the repo. Use the Panel Access page or the `CSRF_TRUSTED_ORIGINS` environment variable for your own domain(s).
