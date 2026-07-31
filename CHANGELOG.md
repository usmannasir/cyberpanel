# Changelog

All notable changes to CyberPanel are documented here. The canonical,
continuously updated changelog also lives at
https://cyberpanel.net/KnowledgeBase/home/change-logs/

## Unreleased
### Feature: Log source dropdown on every Server Log viewer
- Main Log, Access, Error, Email, FTP, and ModSec Audit viewers include a
  **Log source** dropdown (same pattern as other required panel selects) so
  operators can jump between log types without returning to the Logs hub.

### Fix: quieter Server Error Logs (hide cyberpanel_ols gzip WARN noise)
- `/serverlogs/errorLogs` filters `[CyberPanel-OLS] Restored Content-Encoding: ...`
  WARN lines. Those are gzip header-restore notices from `cyberpanel_ols.so`, not
  PHP/site bugs. Real ERROR/NOTICE lines still show.
- Reads a wider tail window before filtering so the UI still gets ~50 useful lines.
- Note: the module may still write those WARNs to disk until a future
  `cyberpanel_ols.so` build logs them at DEBUG; the panel view no longer surfaces them.

### Fix: pluginHolder no longer traceback-spams on Fail2ban name collision
- Plugins whose `AppConfig.name` differs from the directory (e.g. `fail2ban/` with
  `name = 'fail2ban_plugin'`) are skipped once without a full traceback. That collision
  with system `site-packages/fail2ban` was flooding CyberPanel Main Log every few seconds.
- Plugin URL import now puts the plugin root first on `sys.path` and evicts a wrong
  preloaded package before `__import__`.

### Feature: Recreate DNS button on websites
- Website detail, List Websites, and child domain pages include **Recreate DNS**.
- Full recreate now repairs **existing** PowerDNS zones (missing template records and
  wrong A/AAAA updated to the current machine IP), upserts SPF, force-syncs to
  Cloudflare when sync is enabled, and returns Cloudflare zone status.
- When the Cloudflare zone is not `active`, Recreate DNS lists the required
  Cloudflare nameservers, requests Cloudflare `activation_check`, and warns that
  public DNS stays NXDOMAIN until those NS are set at the registrar (DNSSEC off).
  Registrar nameserver changes cannot be performed from CyberPanel.
- API: `POST /websites/recreateWebsiteDNS` with `domainName` and optional `includeChildren`
  (response includes `cloudflare` status object).
- CLI: `virtualHostUtilities.py RecreateDNSForDomain --virtualHostName example.com`.
- Intended for domains/subdomains created before SPF and related DNS template fixes.

### Feature: SPF record follows deployment type (CyberPersons vs self-hosted)
- `DNS.getDeploymentType()` / `DNS.buildSpfRecord()`: CyberPersons rental publishes
  `v=spf1 include:spf.cyberpersons.com ~all`; self-hosted (default) keeps
  `v=spf1 a mx ip4:<machineIP> ~all`.
- Detection: `/etc/cyberpanel/deployment_type`, then admin `config.deploymentType`, else `selfhosted`.
- Onboarding sets `deploymentType=selfhosted` when unset and runs `RepairSpfRecords` for the hostname apex.
- CLI: `virtualHostUtilities.py RepairSpfRecords [--virtualHostName domain]`.

### Fix: website/subdomain DNS and Cloudflare lifecycle
- `cfTemplate` resolves Cloudflare zones by walking parents (child hosts sync into the apex zone),
  honors `cfSync=Disable`, and no longer tries to create CF zones named like `blog.example.com`.
- DKIM and per-record CF sync use the same parent-walk zone resolver.
- LiteSpeed Enterprise website delete now cleans Cloudflare/local host DNS like the OLS path.
- Apex Cloudflare delete is host-scoped (no longer wipes every record in the CF zone blindly).
- Alias/child delete removes orphan PowerDNS apex zones when nothing else uses them.
- SOA serial bumps for **NATIVE** as well as MASTER zones (#1785).

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
