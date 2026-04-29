# LSCPD and Web Terminal security notes (CyberPanel 2.4.5 hardening)

## GitHub issue 1764 context

Reports describe a chain where `lscpd` update activity runs privileged commands and where a separate Web Terminal stack (`fastapi_ssh_server` on port 8888) used a predictable JWT secret. This repository ships `lscpd` binaries (for example `lscpd.0.4.0`) and installer logic that copies them into `/usr/local/lscp/bin/lscpd`. The running daemon behavior and update channel integrity are not fully represented as readable Python in this tree, so risk reduction here focuses on what this repo controls: installer and panel code paths, sudoers templates, Web Terminal JWT storage, firewall posture, and systemd unit exposure.

## What this hardening changes in code

- **Web Terminal JWT**: moved to `/etc/cyberpanel/fastapi_ssh_server.conf` (mode 600) via `plogical/fastapi_ssh_config.py`. Legacy literals are rejected. Panel code issues tokens with `iss`, `aud`, `iat`, `nbf`, `exp` matching the FastAPI verifier.
- **Uvicorn bind**: `fastapi_ssh_server.service` uses `--host 127.0.0.1` so the listener is not reachable from the network namespace as a public bind. Port **8888 stays enabled on loopback** for internal consumers.
- **Firewalld**: fresh install no longer adds a public zone allow for TCP 8888. CSF-specific "open 8888 to the world" logic was removed from the website manager path in favor of the same runtime ensure used elsewhere.
- **Upgrades**: `plogical/upgrade.py` calls `apply_security_migration()` before `systemctl restart fastapi_ssh_server` so deployed units and conf are refreshed.

## Operational note for remote Web Terminal in browsers

Panel JavaScript still builds a WebSocket URL using `window.location.hostname` and port **8888**. With uvicorn bound only to **127.0.0.1**, a browser on another machine cannot open TCP to `host:8888` unless you add a **reverse proxy** on the panel vhost (for example OpenLiteSpeed) that forwards a path on port 8090 to `https://127.0.0.1:8888/ws`, or you terminate TLS and proxy WebSocket to the loopback service. Until that proxy exists, treat Web Terminal as **loopback-only** or adjust the bind in your local fork if you must expose it (not recommended).

## Sudo and `lscpd` blast radius (repository-controlled)

- Review `/etc/sudoers` and `/etc/sudoers.d/*` on installed systems after upgrades. Prefer **command-scoped** sudoers for the `lscpd` user instead of broad `NOPASSWD: ALL` patterns.
- Keep `lscpd` and panel packages updated from trusted mirrors only. If you observe unexpected `sudo cat` of `/etc/shadow`, password stores, or mass `authorized_keys` rewrites, treat the host as compromised: rotate credentials, audit SSH keys, and compare `/usr/local/lscp/bin/lscpd` to known-good hashes from your vendor.

## References

- Upstream discussion: `https://github.com/usmannasir/cyberpanel/issues/1764`
- Related hardening PR discussion: `https://github.com/usmannasir/cyberpanel/issues/1765`
