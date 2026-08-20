# v2.5.5-dev to v3.0.2-dev port checklist

Date: 18/08/2026

This is a **selective parity port**, not a full merge of `v2.5.5-dev`.
Fork PR base is `v3.0.2` (`7011a10091`). Head is `v3.0.2-dev`.

## Already in upstream v3.0.2 (do not regress)

### Six commits v3.0.1..v3.0.2

| SHA | Status | Notes |
|-----|--------|-------|
| e6d984416a | Already in v3.0.2 | Dashboard uptime placeholder |
| 420efaa45d | Already in v3.0.2 | Hermes Agent one-click Docker app |
| 10d0051288 | Already in v3.0.2 | Git dots, email marketing, phpMyAdmin logout, git typo |
| 9b62d1b86d | Already in v3.0.2 | Merge v3.0.1 into docker-ssl-ui-fixes |
| d47bf7ae04 | Already in v3.0.2 | Release 3.0.2 |
| 7011a10091 | Already in v3.0.2 | phpMyAdmin logout test signs in first |

### 22 commits on v3.0.1 after PR 1889 base `f23f8ecf2`

These are ancestors of v3.0.2. Kept during the merge (ours where they conflicted).

| SHA | Status | Theme |
|-----|--------|-------|
| 676b139798 | Already in v3.0.2 | Self-hosted Git deployment |
| 800477c1b8 | Already in v3.0.2 | Merge git deployment |
| 0dbd1b8290 | Already in v3.0.2 | Imunify install/integration |
| c94c79346c | Already in v3.0.2 | Webmail unknown MIME charsets |
| 2de85b2d25 | Already in v3.0.2 | Unreadable website log counts |
| dec8570c5d | Already in v3.0.2 | Package and WordPress status |
| 0b3952ea1e | Already in v3.0.2 | Repair local DB during upgrade |
| cb8ca2504a | Already in v3.0.2 | Reduce ACME logging |
| 812d7d7967 | Already in v3.0.2 | Repair local DB credentials |
| 506fad022c | Already in v3.0.2 | Remote transfer error responses |
| 0144a8b752 | Already in v3.0.2 | WordPress install fail-safe |
| 50525b1473 | Already in v3.0.2 | Docker env row indexing |
| fb6cccbe14 | Already in v3.0.2 | Docker env field tests |
| c2caa78357 | Already in v3.0.2 | SSL v2 guidance |
| 966d2330cd | Already in v3.0.2 | Validate scheduled local backups |
| 5c60d2240b | Already in v3.0.2 | Retention on scheduled local backups |
| 242e8794ce | Already in v3.0.2 | Firewall interface assets |
| 67cc099407 | Already in v3.0.2 | Private service file staging |
| 9fd390ec45 | Already in v3.0.2 | Webmail content and SSH password |
| 59c71ab690 | Already in v3.0.2 | Backups without DNS or mail |
| c4ed7c1fe4 | Already in v3.0.2 | Login session persist and secret access |
| deba378fda | Already in v3.0.2 | Ubuntu 26 installer detection |

## getPHPString / #1834

| SHA | Status | Notes |
|-----|--------|-------|
| d97750b4 | Included (behavior) | #1834 merge on v2.5.5-dev; **not an ancestor**. Ported live regex `\d+\.\d+`. |
| 5fe25849 | Included (behavior) | #1834 whitespace fix. PHP 8.10 -> `810`, malformed -> `85`. |
| PR 1889 last-two-digits | Intentionally excluded | That fallback turned PHP 8.10 into `10`. |

Upstream v3.0.2 `replace("PHP","").replace(".","")` also yields `810` for `PHP 8.10` but is weaker on junk input. This branch uses the #1834 regex plus `RepoNameRegex` from v3.0.2.

Tests: `Test/test_get_php_string.py`.

## Included from v3.0.1-dev / live (PR 1889 themes)

| Theme | Status |
|-------|--------|
| Plugin ACL / store UX, patreon_verifier, plugin_access | Included |
| Firewall banned IPs, reorder, confirm-delete | Included |
| HidePromotions, Full Settings mobile cards | Included |
| Login dark mode, session rotate, remember-me | Included (plus v3.0.2 session.save) |
| List Websites / Domains, human-readable sizes | Included |
| Recreate DNS, Cloudflare helpers / DNS SSL / lifecycle | Included |
| SPF deployment-type (no dynamic plugin URL loader) | Included |
| OLS ACME webroot, phpMyAdmin OLS routes | Included |
| Sensitive-file denials #1859, CSRF Origin dedupe | Included |
| Web Terminal JWT ReadWritePaths, static under lscpd | Included |
| Restored plogical helpers (errorSanitizer, usernameUtils, machine_ip, humanSize) | Included |
| Modular cyberpanel_upgrade.sh + upgrade_modules | Included |
| Installer `--repo` / `-r` (parity with upgrade) | Included |
| Generic CSRF trusted origins + `/etc/cyberpanel/csrf_trusted_origins` | Included (no site IPs) |

## Intentionally excluded

| Item | Why |
|------|-----|
| Full git merge of v2.5.5-dev | Histories diverged by thousands of commits |
| `install_modules/`, `cyberpanel-mods/`, `modules/`, `patches/`, `bin/` | v2.5.5-dev-only trees |
| Dynamic plugin URL loader from SPF port | Skipped in original 1889 port |
| discordAuth, discordWebhooks, fail2ban, premiumPlugin, port_manager, panelAccess, googleTagManager, memcacheManager, redisManager, limitedPhpmyAdmin | Live site plugins |
| `secret_key`, `terminal_jwt_secret`, `*.bak*` | Secrets and backups |
| Hardcoded Contabo IPs in CSRF_TRUSTED_ORIGINS | Site-specific |

## Upgrade path notes

- Loader remains modular (`cyberpanel_upgrade.sh` sources `upgrade_modules/`).
- `Upgrade.repairLocalCyberPanelDatabaseAccess()` from the 22-commit set runs before clone retry.
- Ubuntu 26 detection is in both `cyberpanel.sh` and `upgrade_modules/02_checks.sh`.
- Fork clones: `cyberpanel.sh --repo master3395` and `cyberpanel_upgrade.sh --repo master3395`.

## Smoke

VirtualBox scripts: `Test/virtualbox/`. Operator notes: `to-do/VIRTUALBOX-SMOKE.md`.
Mark install/upgrade smoke **checked** only after Cursor Local on Windows reports `SMOKE_OK`.
