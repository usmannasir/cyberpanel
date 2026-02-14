<div align="center">

<img src="https://community.cyberpanel.net/uploads/default/original/1X/416fdec0e96357d11f7b2756166c61b1aeca5939.png" alt="CyberPanel Logo" width="480"/>

# CyberPanel

**Web Hosting Control Panel powered by OpenLiteSpeed**
Fast • Secure • Scalable — Simplify hosting management with style.

**Version**: 2.5.5-dev • **Updated**: November 15, 2025

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
* 📧 **Integrated mail** — Postfix, Dovecot, SnappyMail
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
* SnappyMail webmail
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
| CentOS 7                   |      ⚠️ Legacy — EOL |
| CloudLinux 9, 8            |            ✅ Supported |
| Debian 13, 12, 11          |            ✅ Supported |
| RHEL 9, 8                  |            ✅ Supported |
| RockyLinux 9, 8            |            ✅ Supported |
| Ubuntu 24.04, 22.04, 20.04 |          ✅ Recommended |

> **Architectures:** x86_64 (primary), aarch64/ARM64 (supported). AlmaLinux is the recommended RHEL-compatible distribution. Test unsupported OS in staging first.

---

## PHP support (short)

* ✅ **Recommended**: PHP 8.5 (beta), 8.4, 8.3, 8.2, 8.1
* ⚠️ **Legacy**: PHP 8.0, PHP 7.4 (security-only)
* ❌ **Deprecated**: PHP 7.1, 7.2, 7.3 (no longer installed)

Third-party repositories (Remi, Ondrej) may provide older or niche versions; verify compatibility before use.

---

## Quick install

```bash
sh <(curl -s https://cyberpanel.net/install.sh || wget -O - https://cyberpanel.net/install.sh)
```

➡️ See `guides/INSTALLATION.md` for platform-specific options and non-interactive installs.

---

## Upgrade (recommended)

```bash
sh <(curl -s https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh || wget -O - https://raw.githubusercontent.com/usmannasir/cyberpanel/stable/preUpgrade.sh)
```

**Post-upgrade checklist:** verify email, DNS, SSL, and run a smoke test on key sites.

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

## Testing

### OLS Feature Test Suite

The OpenLiteSpeed feature test suite (128 tests) validates binary integrity, CyberPanel module, Auto-SSL config, SSL listener auto-mapping, .htaccess processing, ReadApacheConf directives, and more.

```bash
# Run from CyberPanel repo root
./tests/ols_test_setup.sh   # One-time setup
./tests/ols_feature_tests.sh
```

Requires a live CyberPanel + OLS installation.

---

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
