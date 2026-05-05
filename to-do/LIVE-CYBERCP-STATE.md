# Live CyberCP alignment (operator checklist)

Generated during plan execution on the host that has `/usr/local/CyberCP`.

## Recorded state

Run on the same machine as the panel:

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
git -C /usr/local/CyberCP rev-parse HEAD 2>/dev/null || echo "not a git checkout"
```

## Deploy steps (do not skip backup)

1. Put panel in maintenance or low traffic window.
2. `tar czf /root/cybercp-backup-$(date +%Y%m%d).tgz /usr/local/CyberCP /etc/cyberpanel 2>/dev/null` (adjust paths to match your layout).
3. Push `v2.5.5-dev` from [cyberpanel-v255-dev](file:///home/cyberpanel-v255-dev), then on server: `cd /usr/local/CyberCP && git fetch && git checkout v2.5.5-dev && git pull` (or your rsync procedure).
4. Install Python deps: use `requirments.txt` from that commit (includes Django **4.2.30** and related bumps).
5. `python3 manage.py migrate` if migrations changed.
6. Restart **lscpd** (or full **lsws restart**) per your CyberPanel + LiteSpeed runbook.
7. Smoke test: login, webmail, WP Manager, AI scanner if enabled.

## `manage.py check --deploy` note

Expect **warnings** for HSTS, `SECURE_SSL_REDIRECT`, cookie secure flags when TLS is terminated on a reverse proxy. Tune `settings.py` or vhost headers to match your edge TLS setup rather than blindly setting `SECURE_SSL_REDIRECT=True` behind HTTP to the app.

## Python 3.11 for new installs (`v2.5.5-dev`)

Fresh installs using `cyberpanel.sh` now:

- Install **python3.11**, **python3.11-pip**, and **python3.11-devel** on EL9-class distros (and modular `modules/deps/rhel_deps.sh` does the same).
- Export **`CYBERCP_VENV_PYTHON`** via **`ensure_cybercp_system_python`** in `install_modules/00_common.sh` (also invoked after modular `install_dependencies` in `modules/deps/manager.sh`).
- Run **`install/install.py`** with that interpreter and pass the same value into **`install.py`** so **`python -m venv /usr/local/CyberCP`** uses 3.11 even when the bootstrap `python3` is 3.9.
- Recreate venv paths in **`upgrade_modules/08_main_upgrade.sh`** and **`fix_cyberpanel_install.sh`** with the same bootstrap selection.

`requirments.txt` pins **`python-dotenv==1.2.2`** (needs Python **>=3.10**). That matches the **v2.5.5-dev** installer, which prefers **3.11** for `/usr/local/CyberCP`. If a host still has a **3.9**-only venv, recreate the venv with **python3.11** (or run `ensure_cybercp_system_python` / full upgrade path) before `pip install -r requirments.txt`.
