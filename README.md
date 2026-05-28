<div align="center">

<img src="https://community.cyberpanel.net/uploads/default/original/1X/416fdec0e96357d11f7b2756166c61b1aeca5939.png" alt="CyberPanel Logo" width="480"/>

# CyberPanel

**Web Hosting Control Panel powered by OpenLiteSpeed**
Fast • Secure • Scalable — Simplify hosting management with style.

**Version**: 2.5.5-dev • **Updated**: 28.03.2026

[![GitHub](https://img.shields.io/badge/GitHub-Repo-000?style=flat-square\&logo=github)](https://github.com/usmannasir/cyberpanel)
[![Docs](https://img.shields.io/badge/Docs-Read-green?style=flat-square\&logo=gitbook)](https://cyberpanel.net/KnowledgeBase/)
[![Forum](https://img.shields.io/badge/Forum-Join-FF6F00?style=flat-square\&logo=discourse\&logoColor=white)](https://community.cyberpanel.net)
[![Discord](https://img.shields.io/badge/Discord-Chat-5865F2?style=flat-square\&logo=discord\&logoColor=white)](https://discord.gg/g8k8Db3)
[![YouTube](https://img.shields.io/badge/YouTube-Learn-FF0000?style=flat-square\&logo=youtube)](https://www.youtube.com/@Cyber-Panel)

---

</div>

## Key highlights

* ⚡ **Performance first** — OpenLiteSpeed + HTTP/3 + LSCache
* 🔒 **Security by default** — Auto SSL, FirewallD integration, 2FA, brute-force protection
* 📧 **Integrated mail** — Postfix, Dovecot, panel webmail (SSO/Sieve), SnappyMail
* 🗂 **Backups & restore** — One-click snapshots and rollbacks
* 👨‍💻 **Developer friendly** — Git manager, REST API, staging, PHP version switcher

---

## Features

**Security**

* Auto SSL (Let's Encrypt)
* Firewall integrations (FirewallD, optional CSF export)
* 2FA (TOTP + WebAuthn/Passkey)
* AI-powered security scanner (optional)

**Hosting & Websites**

* OpenLiteSpeed (HTTP/3, QUIC)
* One-click WordPress (LSCache-ready)
* PHP per-site version selector
* File manager, FTP, SFTP

**Email & DNS**

* Postfix + Dovecot
* Panel webmail + SnappyMail
* DNS (PowerDNS) with easy zone management

**Developer & Automation**

* RESTful API (create/list/manage sites, users, packages)
* Git integration & staging
* Docker command execution support

**Backups & Storage**

* Local snapshots, remote backups (S3/AWS compatible)
* One-click restore and scheduled backups

---

---

## Supported platforms (condensed)

| OS family                  | Recommended / Supported |
| -------------------------- | ----------------------: |
| AlmaLinux 10, 9, 8         |          ✅ Recommended |
| CentOS 9, 8                |            ✅ Supported |
| CloudLinux 9, 8            |            ✅ Supported |
| Debian 13, 12, 11          |            ✅ Supported |
| RHEL 9, 8                  |            ✅ Supported |
| RockyLinux 9, 8            |            ✅ Supported |
| Ubuntu 24.04, 22.04, 20.04 |          ✅ Recommended |

> **Architectures:** x86_64 (primary), aarch64/ARM64 (supported). AlmaLinux is the recommended RHEL-compatible distribution. Test unsupported OS in staging first.

---

## PHP support (short)

* ✅ **Recommended**: PHP 8.5, 8.4
* ⚠️ **Security fixes only**: PHP 8.3, 8.2, 8.1
* ❌ **EOL / Deprecated**: PHP 8.0, 7.4, 7.1, 7.2, 7.3 (no longer supported)

Third-party repositories may provide older or niche versions; verify compatibility before use. RHEL/Alma/Rocky: [Remi RPM](https://rpms.remirepo.net/). Ubuntu/Debian: [Ondrej PPA](https://launchpad.net/~ondrej/+archive/ubuntu/php). See [php.net/supported-versions](https://www.php.net/supported-versions.php).

---

## Quick install

```bash
sh <(curl -s https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
```

➡️ See `guides/INSTALLATION.md` (or `docs/` on this repo) for platform-specific options and non-interactive installs.

---

## Upgrade

The upgrade uses a **modular loader** (`cyberpanel_upgrade.sh`) that works on both **stable** and **v2.5.5-dev**. When run via the one-liner (no repo on disk), the loader fetches `upgrade_modules/` from the chosen branch. Use **preUpgrade.sh** (recommended) or the direct loader URL below.

### Upgrade to stable (recommended)

```bash
sh <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/preUpgrade.sh || wget -qO - https://raw.githubusercontent.com/master3395/cyberpanel/stable/preUpgrade.sh)
```

PreUpgrade downloads the loader from `stable` and runs it with `-b stable`, so modules are taken from the stable branch. No `-b` flag needed.

**Post-upgrade:** verify email, DNS, SSL, and run a smoke test on key sites.

### Upgrade to v2.5.5-dev

Use `-b v2.5.5-dev` so the loader fetches modules from the dev branch.

```bash
# Interactive (branch + MariaDB prompts)
sh <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/preUpgrade.sh || wget -qO - https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/preUpgrade.sh) -b v2.5.5-dev

# Non-interactive: v2.5.5-dev + MariaDB 11.8 (LTS) — recommended
sh <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/preUpgrade.sh || wget -qO - https://raw.githubusercontent.com/master3395/cyberpanel/v2.5.5-dev/preUpgrade.sh) -b v2.5.5-dev --mariadb-version 11.8
```

**MariaDB options:** `10.11`, `11.8` (LTS default), `12.x` (e.g. 12.1, 12.2). Use `--mariadb` for 10.11, or `--mariadb-version X.Y` to set explicitly.

```bash
# MariaDB 10.11
sh <(curl -sL .../preUpgrade.sh) -b v2.5.5-dev --mariadb

# MariaDB 12.1
sh <(curl -sL .../preUpgrade.sh) -b v2.5.5-dev --mariadb-version 12.1
```

### Direct loader (advanced)

If you prefer to run the upgrade script without preUpgrade (e.g. already have the branch in mind):

```bash
# Stable (default; modules fetched from stable)
sudo bash <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel_upgrade.sh)

# Dev (pass -b so modules are fetched from v2.5.5-dev)
sudo bash <(curl -sL https://raw.githubusercontent.com/master3395/cyberpanel/stable/cyberpanel_upgrade.sh) -b v2.5.5-dev
```

Optional flags (same as with preUpgrade): `--mariadb-version 11.8`, `--debug`, `--mirror`, etc.

---

## Troubleshooting (common)

**Command not found** — install curl/wget/git/python3

```bash
# Ubuntu/Debian
sudo apt update && sudo apt install -y curl wget git python3

# RHEL/CentOS/Alma/Rocky
sudo yum install -y curl wget git python3
```

**Port 8090 in use** — find and stop conflicting process:

```bash
sudo ss -tlnp | grep :8090
sudo kill -9 <PID>
```

**Logs & verification**

```bash
systemctl status lscpd
curl -I http://localhost:8090
tail -f /usr/local/lscp/logs/error.log
journalctl -u lscpd -f
```

---

## Recent fixes

* **02.02.2026** — Plugin updates: premiumPlugin & paypalPremiumPlugin unified verification (Plugin Grants, activation key, Patreon, PayPal, AES-256-CBC encryption). Installed Plugins UI: bulk activate/deactivate, freshness badges, removed Patreon messaging from front.
* **15.11.2025** — Hardened MySQL password rotation: `mysqlUtilities.changePassword` now auto-resolves the backing MySQL account (user + host) even when `DBUsers` metadata is missing, preventing the historical `[mysqlUtilities.changePassword] can only concatenate str (not "int")` error. Regression tests live under `Test/mysqlUtilities/`, and you should restart `lscpd` after deploying the patch so the helper reloads.

---

## Third-party notices

Bundled components that use licenses other than CyberPanel's GPL-3.0 are listed in [docs/THIRD_PARTY_NOTICES.md](docs/THIRD_PARTY_NOTICES.md).


## Resources

* Official site: [https://cyberpanel.net](https://cyberpanel.net)
* Docs (KnowledgeBase): [https://cyberpanel.net/KnowledgeBase/](https://cyberpanel.net/KnowledgeBase/)
* Community forum: [https://community.cyberpanel.net](https://community.cyberpanel.net)
* GitHub: [https://github.com/usmannasir/cyberpanel](https://github.com/usmannasir/cyberpanel)
* Guides folder:  [guides](https://github.com/usmannasir/cyberpanel/blob/stable/guides/INDEX.md) (API, INSTALLATION, UPGRADE, TROUBLESHOOTING)

---

<div align="center">

💡 *Hosting should be secure, simple, and fast. CyberPanel is built for that.*

</div>
