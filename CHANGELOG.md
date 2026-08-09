# Changelog

All notable changes to CyberPanel are documented here. The canonical,
continuously updated changelog also lives at
https://cyberpanel.net/KnowledgeBase/home/change-logs/

## v3.0.0 (build 0) — 2026-08-09

### Platform support
- Added Ubuntu 26.04 installation and upgrade support with a Python 3.12 panel
  runtime, distribution MariaDB packages, available mail-scanning packages,
  reliable DNS handoff, and compatible Memcached fallback behavior.
- Package operations now wait for package-manager locks, DNS readiness is
  verified before downloads, and Ubuntu 26 installer sessions remain available
  while long-running setup steps complete.

### Backup and restore
- Backup archives are accepted only after they are complete, stable, and valid.
- Version 3 backups use the modern multi-user database metadata restore path;
  all established legacy format boundaries remain supported.
- Version comparisons no longer treat dotted releases as decimal numbers.
- Restores preserve whether the original website had an automatic mail child
  domain instead of always creating one.

### Security and reliability
- Backup restores reject archive path traversal, escaping links, and special
  filesystem entries before extracting any content.
- Hardened Web Terminal authentication and secret-file permissions.
- Blocked sensitive application files through generated website
  configurations and tightened certificate-file handling.
- Restored domain-alias management, free WordPress installation navigation,
  Ubuntu Pure-FTPd reset behavior, PHP 8.5 parsing, and DNS SOA serial updates.

### Release versioning
- Consolidated runtime, API, installer, upgrade, backup, and CLI version values
  into one source for v3.0.0.
- Installer and upgrade scripts now parse version metadata without fixed byte
  offsets and support multi-digit build numbers.
- Fresh installations write the machine-readable JSON format expected by the
  CyberPanel CLI.
- Upgrades now synchronize the database-backed version returned by the API.

## v2.4.9 (build 9) — 2026-07-23

A maintenance release: a broad batch of security, SSL, backup/restore and
upgrade-reliability fixes, plus the updated CyberPanel-OLS stack. Most items
below were already shipped to the `v2.4.8` branch and are consolidated here.

### Security
- **Backup IDOR:** `cancelBackupCreation` performed no ownership check, letting
  any authenticated user kill, delete and corrupt another tenant's backups as
  root; the incremental-backup endpoints (`deleteBackup` / `fetchRestorePoints`
  / `restorePoint`) checked one field but acted on an unscoped id, allowing
  cross-tenant read/delete/restore. Both are now ownership-scoped (#1829, #1828).
- Hardened command/cron handling, confined `tuneSettings` `phpPath` to the
  owned pool file, and rotate the 2FA secret on disable.
- Fixed command injection, SQLi, path traversal, privilege-escalation and
  crypto weaknesses across several endpoints.
- Added authentication to previously-unauthenticated git-webhook, AWS-backup
  and AI-Scanner file-access endpoints (#1806).
- Generate a strong SnappyMail admin password on install.
- Installed `fullchain.pem` files with trailing binary data no longer break
  SSL status display or block self-repair (#1847).

### SSL
- **Renewals now actually apply:** the renewed certificate is copied into
  `/etc/letsencrypt/live/<domain>` and LiteSpeed is reloaded, and acme.sh's own
  cron is registered with `--ecc`/`--reloadcmd` so auto-renewals self-apply —
  fixes sites silently stuck on the old (expiring) certificate (#1676).
- Manual "Issue SSL" forces a reissue instead of silently no-opping (#1814).

### Backups & restore
- **Restore ownership:** restored/migrated files are reliably re-owned by the
  domain user, fixing WordPress asking for FTP credentials after a restore
  (a `chown` glob was passed literally under `shell=False` and never matched)
  (#1735).
- A website backup now fails loudly instead of silently producing an archive
  with no SQL when a database dump fails (#1823).

### Domain aliases
- Alias creation, listing, SSL issuance and delete fixed end-to-end: the alias
  DB row is persisted regardless of SSL outcome, the list renders and its
  buttons call the right handlers, and orphaned aliases can be cleaned up
  (#1738).

### Upgrade & install
- The upgrade script no longer false-flags healthy installs as corrupt (a
  non-existent `manage` directory in the integrity check) and triggers a
  destructive recovery re-clone (#1720).
- Upgrade scripts validate downloads before executing them, with clear errors
  and retries when GitHub returns HTTP 429 (#1835).
- PHP 8.5 no longer raises `UnboundLocalError` on the subdomain list; version
  mapping is future-proofed (#1726).
- OWASP CRS install uses the canonical GitHub tag-archive URL (#1715).

### Other fixes
- Apache 503 after upgrade when mod_ssl re-added `Listen 443` while LiteSpeed
  owns the port.
- Remote transfer regression (status stuck on "Just started.."; silently
  dropped sends).
- `secMiddleware` no longer blocks valid webmail content (#1813).
- Re-linked Modify Website and owner transfer in the new UI (#1816); restored
  Delete/Suspend website and Delete database actions (#1800).
- Repaired the dashboard for non-admin users (#1808) and dark mode across the
  panel (#1804).
- Blank password field no longer wipes a user's password on edit (#1811).

### CyberPanel-OLS stack update (core 2.5.1 / module 2.7.5 / mod_security 2.5.1)
- Upgraded the custom OpenLiteSpeed stack shipped by `upgrade.py`:
  OpenLiteSpeed core **2.5.1**, `cyberpanel_ols.so` **2.7.5**,
  `mod_security.so` **2.5.1**.
- **Fixes the 4xx segfault / Cloudflare 520 storm**: module versions
  2.7.0–2.7.3 crashed the OLS worker on every 4xx generated for a request
  whose `Host` matched no vhost (bot probes), causing random 520s across all
  sites. Core 2.5.1 additionally hardens OLS itself
  (`HttpReq::getDocRoot` NULL-vhost check) so no module can trigger this
  crash class again. Root cause and release notes live in the
  `cyberpanel_ols` repo (`BUGREPORT_cyberpanel_ols_4xx_segfault.md`,
  `RELEASE_v2.7.4.md`, `RELEASE_v2.7.5.md`,
  `docs/FIELD_RECOVERY_AND_ROLLOUT.md`).
- All artifacts are now verified against pinned SHA256 checksums before
  install; a mismatch aborts and keeps/restores the previous binaries via the
  timestamped backup + rollback path. Rollback now also restores the module
  and mod_security binaries, not just the core.
- Binary installation now does a **full lsws stop/start** around the swap
  (never a graceful restart) and removes the target before copying.
- Ubuntu < 22.04 (e.g. 20.04, glibc 2.31) now skips the custom overlay
  entirely — the `ubuntu` artifact needs GLIBC ≥ 2.34 (ticket #OXHTOK7AH).
- AlmaLinux/Rocky/RHEL 10 now install the `rhel9` artifact (el9 binary covers
  el10).

**Support notes:**
- Servers where support removed the `module cyberpanel_ols { }` block from
  `httpd_config.conf` as the emergency 520 mitigation: **restore the block
  (`ls_enabled 1`) after this upgrade lands** — full procedure in
  `docs/FIELD_RECOVERY_AND_ROLLOUT.md` §4 (cyberpanel_ols repo).
- `ls_enabled 0` + a FULL restart is now a safe kill-switch, but **only with
  module ≥ 2.7.5**. On 2.7.0–2.7.3 it does not stop the crash — upgrade,
  don't toggle.
- Never reinstall module 2.7.0/2.7.1/2.7.2/2.7.3 (bad-build sha256 list in
  the bug report §6).
- The previous (2.4.4) artifacts remain published for rollback.

## v2.4.8 (build 8) — 2026-05-30

A panel-wide UI/UX overhaul focused on making CyberPanel easier to use, calmer
to look at, and faster — plus integrated development services. See
`docs/UI-Guide.md` for a full walkthrough.

### Navigation & information architecture
- Replaced the deep, nested sidebar with a short, **flat, object-based
  navigation** grouped into Hosting / Account / Administration / Help — no more
  accordions.
- Added category **hub pages** (Email, Databases & FTP, Backups, Users & Plans,
  Server, Security, Settings): each area's tools shown as a scannable grid of
  labelled, permission-aware tiles.
- Added a global **command palette** (`Ctrl/⌘-K`) that searches every page and
  common action, including a searchable "Build services" group.
- New per-site **Site Workspace** (`/websites/<domain>/workspace`) gathering
  files, SSL, DNS, email, databases, backups and advanced tools for one domain.

### Dashboard
- Action-first dashboard: quick actions and a getting-started checklist for new
  installs, with the health metrics and activity board retained.

### Site management page
- Reorganized the long single-scroll site page into **tabs** (Overview /
  Domains / Logs / Config / Files / Apps); hero and quick actions stay pinned.
  Degrades gracefully (all sections remain visible if scripting is unavailable).

### Visual design
- Neutralized the palette (calmer neutrals in light, neutral slate in dark),
  flattened the sidebar, softened shadows and spacing, and set comfortable
  typography.
- Added a single global **theme harmonizer** that re-skins every internal page
  (the many pages carrying their own embedded styles) to the design tokens —
  consistent and correct in both light and dark mode.

### Performance
- Preconnect to third-party origins; deferred Chart.js, QRious and the
  per-module script bundle so they no longer block first paint and download in
  parallel.
- Lightweight shell pages (dashboard, hubs, build services, site workspace) skip
  the large per-module script bundle entirely.
- Per-page code-splitting: single-controller pages load only their own module's
  JS (statically verified safe).
- Cached the non-admin dashboard disk-usage computation, which previously ran a
  `du` subprocess per website on every poll.

### Development services
- Integrated a prominent but tasteful **Build Services** area (sidebar entry,
  dashboard card, empty-state prompts, and an in-panel landing page) linking to
  the development services on cyberpanel.net, with per-service deep links and
  UTM tracking.
- Advertised the managed **Email Delivery** service via a banner on the Email
  hub and a header notification.

### Documentation
- Added `docs/UI-Guide.md` documenting the new interface for administrators,
  resellers and website owners.

## v2.4.7 (build 7) — 2026-05-19

### Dashboard UI/UX overhaul
- Extracted the large inline shell/dashboard CSS into cached static
  stylesheets (`cyberpanel-ui.css`, `dashboard.css`) and fixed
  cache-busting to track the real application version.
- Self-hosted the panel logo (no more third-party hot-link).
- Completed the dark theme so cards, tables, modals, pagination and the
  activity board switch correctly — not just the shell.
- Added usage-threshold colors (green/amber/red) to CPU/RAM/Disk bars,
  loading skeletons, and an error/retry state for system metrics.
- Replaced the fake "demo data" shown while SSH logins load with a
  proper skeleton.

### Navigation & layout
- Replaced the three stacked promo banners with a single header
  notification center (bell + dropdown, per-item dismiss, "dismiss
  all"); removed the layout shift they caused.
- Added a sidebar quick-filter search and a breadcrumb / page-context
  strip.
- Decluttered the shell: flat sidebar items, quiet section labels,
  trimmed header; neutralized the palette and lightened chrome for a
  cleaner look.
- Insight cards are now real links to their list pages.

### Accessibility & i18n
- Semantic landmarks, visible focus styles, ARIA tablist, skip link,
  reduced-motion support, SSH-activity modal focus trap + Esc-to-close.
- Full translation pass over the dashboard strings.

### Performance
- Deferred all external scripts (Angular bootstrap order preserved) to
  cut render-blocking on every page.

### Other
- Standardized UI feedback helpers (`cpToast`, `cpBusy`).
- Responsive dashboard tables on small screens.
- Continued API authorization and security hardening.
