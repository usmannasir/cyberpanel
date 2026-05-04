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
## Snapshot from this workspace run
2026-05-04T21:29:16Z
6f6f1dcd530ccb8ad451145c894e0da32573e31d
