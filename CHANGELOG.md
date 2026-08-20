# Changelog

All notable changes to CyberPanel are documented here. The canonical,
continuously updated changelog also lives at
https://cyberpanel.net/KnowledgeBase/home/change-logs/

## Unreleased (v3.0.2-dev)

Selective v2.5.5-dev / v3.0.1-dev parity on top of upstream v3.0.2. See
`to-do/V255-DEV-TO-V302-PORT-CHECKLIST.md`. This is a fork branch, not a
full `v2.5.5-dev` merge.

### Fixes
- SnappyMail on the panel port (`/snappymail/`): replace `public/snappymail`
  symlinks that point outside CyberCP `vhRoot` (OLS `restrained=1` / Django
  404), keep app files under `public/` with data in
  `/usr/local/lscp/cyberpanel/snappymail/data`, and add local lsphp contexts
  on hostname panel proxies. Repair via
  `scripts/utils/fix-snappymail.sh`.

- Installer `--repo` / `-r` clones a GitHub fork (same switch as upgrade).
- `getPHPString` uses the #1834 major.minor regex so PHP 8.10 maps to `810`.
- Modular `cyberpanel_upgrade.sh` plus `upgrade_modules/` kept; Ubuntu 26
  detection and local DB credential repair stay in that path.
- VirtualBox / Vagrant smoke helpers live under `Test/virtualbox/` for
  Cursor Local on Windows.
- Restore `install/ols_binaries_config.py` and `install/ols_version_policy.py`
  (required by `install.py` / `upgrade.py` OLS overlay).
- Bring `install/install_utils.py` APIs from v2.5.5-dev (`debian12`, OLS/MariaDB
  helpers) while honoring `CYBERPANEL_GIT_USER` for fork clones.
- `Check_Root` now exits 1 when sudo is detected (no false install success).
- `update_settings_file` rewrites only the top-level `SECRET_KEY =` assignment
  so the env/file fallback block is not smashed, and only DATABASES `HOST`
  lines that contain `127.0.0.1` (CSRF origins stay as URLs).
- Vagrant provisioners run via `su -` and fail if `lscpd` is not active.
  Guest smoke strips CRLF so Windows checkouts still run.
- Fresh/upgrade: `lscpd` binds `127.0.0.1:5003` (WSGI backend). OLS keeps
  public HTTPS `:8090` and proxies to that backend, so the two no longer
  fight for the same socket (panel 503 / `lscpd` failed after install).
- `collectstatic` during install/upgrade uses `--verbosity 0` so Vagrant SSH
  does not drop on thousands of "Deleting" lines.
- Upgrade from stock v3.0.2: stage `plogical/errorSanitizer.py` before
  `upgrade.py` runs, point git `origin` at `--repo` (not leftover usmannasir),
  and do not abort post-tweak when optional LSCPD sudo helpers are missing.
- AlmaLinux 10 installer: EPEL 10, remi-release-10, optional htop, AppStream
  MariaDB (not MariaDB.org el9 RPMs), and an EL10-safe LiteSpeed GPG import.
  Full AlmaLinux 10 panel smoke needs x86-64-v3 (LiteSpeed lsphp el10).
  Windows VirtualBox NEM masks AVX2, so that smoke belongs on KVM or a VPS.
- **Docker panel image:** `docker/panel/` builds multi-OS images (`master3395/cyberpanel:<os>`)
  with full or minimal install via `CYBERPANEL_MINIMAL=1`. Container mode in
  `cyberpanel.sh`, `install/install_utils.py`, and `install/container.py`.
  Docs: `to-do/DOCKER-PANEL.md`. Smoke harness: `Test/docker/`.
- **Hyper-V smoke:** AlmaLinux 10 Generic Cloud harness under `test/hyperv/` for
  Windows hosts with Hyper-V enabled (AVX2 available to the guest). See
  `to-do/HYPERV-SMOKE.md`.
- EL10 upgrade path: EPEL 10, remi-release-10, AppStream MariaDB (not MariaDB.org
  el9 RPMs), AVX2 preflight in installer/upgrade, and runnable lsphp binary checks.
- `cyberpanel_upgrade.sh` installed under `/usr/local` always downloads
  `upgrade_modules/` for the target branch instead of sourcing the old
  tree's modules (which skipped `upgrade.py` and left the stock build).
- `upgrade.py` no longer requires Django-backed `errorSanitizer` at import
  time, so it can start from `/root/cyberpanel_upgrade_tmp` on a stock tree.

## v3.0.2 (build 2) — 2026-08-18

Adds Hermes Agent as a one-click Docker application and consolidates the fixes
that landed on the `v3.0.1` branch after its initial build, which were never
given their own changelog entry.

### Applications
- Hermes Agent can now be deployed from Docker Sites the same way as n8n: pick
  the domain, the resources and the dashboard login, and the panel builds the
  container, the reverse proxy and the SSL-terminated dashboard. The agent keeps
  its state in its own data volume and needs no database container, and its
  dashboard is reachable only through the domain, never on a public port. The
  model provider API key is added from inside the dashboard, so no credential
  for it is stored by the panel.
- The application list, the resources shown for each application, and the
  application recorded against a Docker site are now driven by one definition,
  so every site is recorded as the application it actually runs. Previously
  every Docker site was recorded as WordPress.

### Fixes
- Git repositories whose name contains a dot, such as `repo.ltd`, can be
  attached again instead of being rejected as invalid input (#1716).
- The Email Marketing page loads its application script, so the page renders
  its lists instead of staying empty (#1707).
- Logging out of phpMyAdmin now ends the session and returns to the panel
  instead of leaving a blank page with the session still open (#1680).
- Corrected a "Pleas wait" typo on the manage git page (#1752).
- The Docker site form starts with valid owner, application and resource
  values, and the selected entry in each dropdown is no longer clipped.

### Consolidated from the v3.0.1 branch
- Ubuntu 26 installer detection completed, and login sessions persist correctly
  with tightened secret access.
- Scheduled local backups validate their destination and apply retention;
  backups of sites without DNS or mail records complete.
- Downloads staged for the file manager use a private directory owned by the
  service account instead of loosening permissions on the panel home (#1894).
- Local database credentials are repaired during upgrade, and a failed upgrade
  reports partial state instead of claiming the old build is still running
  (#1891).
- Webmail handles unknown MIME charsets, and webmail content and SSH password
  changes are hardened.
- WordPress installation fails safely, remote transfer error responses are
  handled, self-hosted git deployment is restored, and Imunify installation and
  panel integration are fixed.
- Web Terminal keeps working after upgrades and runtime rebuilds, honours a
  custom SSH port, and requires a one-time authorization.
- Docker environment variable rows are indexed correctly, ACME logging exposure
  is reduced, and the dashboard no longer renders a raw uptime placeholder.

## v3.0.0 (build 0) — 2026-08-09

## Unreleased
### Security / reliability (ported from v2.4.9)
- Backup cancel and incremental backup handlers: ownership checks and domain-scoped
  IncJob/JobSnapshots lookups (#1829, #1828).
- File Manager Fix Permissions: recursive `chown` of the directory itself instead of
  broken `path/*` globs under `shell=False` (#1735).
- SSL renew/install: `acme.sh --install-cert --ecc` with `--reloadcmd` so renewed certs
  land in `/etc/letsencrypt/live` and LiteSpeed reloads (#1676).
- Domain aliases: persist DB row before SSL; orphan-safe ACL and delete (#1738).
- Website backups: abort when `mysqldump` fails instead of shipping SQL-less archives (#1823).
- PHP version map: PHP 8.5 plus generic fallback in `getPHPString` (#1726).


### Fix: backup tar failures and premature remote transfer (#1855, #1856)
- `BackupRoot()` checks `tar` exit status and refuses `Completed` for empty/missing archives.
- `createLocalBackup()` waits until the `.tar.gz` exists with a stable non-zero size before
  reporting success to remote/SFTP/GDrive jobs.

### Fix: PHP Basic UI no longer corrupts `max_memory_limit` (#1784)
- `managePHP/phpManager.py` matches `memory_limit` without rewriting PHP 8.5 `max_memory_limit`.

### Security: default deny for sensitive web files (#1859)
- New OpenLiteSpeed and LiteSpeed Enterprise / Apache vhost templates block direct
  HTTP access to `.env`, `.git`, `.htpasswd`, `.user.ini`, and `.htaccess` (403).
- Existing sites: run `CPScripts/retrofit-sensitive-file-denials.sh` (restarts LSWS).
- Helper: `vhost.ensureSensitiveFileDenials()` for idempotent injection into OLS configs.

### Settings: option to hide promotional content (port of #1841)
- New **Hide promotional content** checkbox under Settings → Design (`HidePromotions`
  on `CyberPanelCosmetic`, default off).
- When enabled, hides Build Services / HIRE US sidebar entry, Build Services command
  palette group, and Email Delivery / AI Scanner / .htaccess promo notifications.
- Backup-not-configured notification stays visible (status warning, not a promo).
- Upgrade path: `ALTER TABLE ... ADD HidePromotions` in `plogical/upgrade.py`.

### Build metadata
- `version.txt` and panel `BUILD` advanced to **2.5.5 build 1** (still the 2.5.5-dev line; not a 2.4.9 backport of release notes).

### Mail: sieve install-first guard (#1733)
- Keep sieve when pigeonhole is present; try installing OS packages when missing;
  strip `sieve`/`managesieve` from `dovecot.conf` only if install fails; always
  verify Dovecot/Postfix afterward (`plogical/sieveGuard.py`).

### Upgrade reliability (#1727, #1853)
- Modular upgrade no longer hardcodes `/usr/bin/php` to lsphp74; picks an installed
  lsphp (prefer 8.3+). `install.py` uses `os.path.lexists` so broken symlinks are replaced.
- Modular upgrade records `UPGRADE_FAILED` from real `upgrade.py`/`PIPESTATUS` and
  refuses to print a success banner when the Python upgrade failed.

### Fix: show full PHP patch on List Websites
- List Websites now shows the live runtime version (e.g. `PHP 8.5.7`) from the
  site's `lsphp` binary, not only the selector label (`PHP 8.5`).
- Full version is cached per `lsphp` build (mtime) so listing many sites stays fast.
- `phpSelection` in the DB remains the change-PHP selector (`PHP 8.5`).

### Fix: CyberPanel List Websites PHP vs live OLS handler
- Persist `phpSelection` in the DB whenever `vhost.changePHP` succeeds (UI and CLI).
- Heal drifted panel values when listing websites by reading the live `vhost.conf` lsphp path.
- CLI `cyberpanel changePHP` also updates `websiteFunctions_websites.phpSelection`.
- Root cause: OLS could run `lsphp85` while List Websites still showed PHP 8.3.

### Security / reliability (ported from v2.4.9)
- Backup cancel and incremental backup handlers: ownership checks and domain-scoped
  IncJob/JobSnapshots lookups (#1829, #1828).
- File Manager Fix Permissions: recursive `chown` of the directory itself instead of
  broken `path/*` globs under `shell=False` (#1735).
- SSL renew/install: `acme.sh --install-cert --ecc` with `--reloadcmd` so renewed certs
  land in `/etc/letsencrypt/live` and LiteSpeed reloads (#1676).
- Domain aliases: persist DB row before SSL; orphan-safe ACL and delete (#1738).
- Website backups: abort when `mysqldump` fails instead of shipping SQL-less archives (#1823).
- PHP version map: PHP 8.5 plus generic fallback in `getPHPString` (#1726).


### CyberPanel-OLS stack update (core 2.5.1 / module 2.7.5 / mod_security 2.5.1)
- Upgraded the custom OpenLiteSpeed stack shipped via `install/ols_binaries_config.py`:
  OpenLiteSpeed core **2.5.1**, `cyberpanel_ols.so` **2.7.5**,
  `mod_security.so` **2.5.1**.
- **Fixes the 4xx segfault / Cloudflare 520 storm**: module versions
  2.7.0–2.7.3 crashed the OLS worker on every 4xx generated for a request
  whose `Host` matched no vhost (bot probes), causing random 520s across all
  sites. Core 2.5.1 additionally hardens OLS itself
  (`HttpReq::getDocRoot` NULL-vhost check) so no module can trigger this
  crash class again.
- AlmaLinux/RHEL 9: if the rhel9 OLS 2.5.1 core needs GLIBC 2.35, fall back to the rhel8 2.5.1 core and still install module 2.7.5.
- All artifacts are verified against pinned SHA256 checksums before install;
  a mismatch aborts and keeps/restores the previous binaries via the
  timestamped backup + rollback path.
- `ls_enabled 0` + a FULL restart is a safe kill-switch only with module ≥ 2.7.5.
  Never reinstall module 2.7.0–2.7.3.
- Servers where support disabled the module block: restore `ls_enabled 1` after upgrade.

### Security (ported from v2.4.8)
- Harden cron command handling with `shlex.quote`.
- Confine `tuneSettings` phpPath to the domain's own PHP-FPM pool file.
- Stop returning `secretKey` in `fetchUserDetails`; rotate secret on 2FA disable.

### Stability / UX (ported from v2.4.8 / stable)
- Fix remote transfer status stuck on "Just started..." and silent send failures.
- Re-surface SSL on the site management page as its own tab.
- Neutralize mod_ssl Listen 443 when LiteSpeed owns the port (Apache 503 after upgrade).

### Bug fixes
- Upgrade scripts: validate HTTP status before executing downloaded content (#1835); default to `usmannasir/cyberpanel`, optional `--repo` for custom GitHub users.
- ModSecurity rules pack: fix first-toggle no-op (#1824).
- Website backups: treat empty/failed SQL dumps as failures (#1823).
- WordPress install: soft-fail post-core plugins; clean up files on rollback (#1837).
- Add `CPScripts/rebuild-lscp.sh` for LSCP/WebAdmin recovery without full reinstall (#1839).
- Allowlist Ubuntu 26.04 for install/upgrade (#1832).

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
