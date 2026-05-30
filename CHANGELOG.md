# CyberPanel changelog (cyberpanel-v255-dev fork)

This fork carries the `2.5.5-dev` brand and now incorporates every meaningful
fix from upstream `usmannasir/cyberpanel` `v2.4.7` (35 commits past `v2.4.5`).
Lineage: `2.5.5-dev` (was based on `2.4.4` + `2.4.5`) backported `v2.4.7`
on 26/05/2026.

The upstream `v2.4.7` release notes live at
https://cyberpanel.net/KnowledgeBase/home/change-logs/. This file records the
fork-specific backport decisions, not a verbatim copy of the upstream
release.

For per-host operator state (backups, deployment runs, restore drill results),
see `to-do/LIVE-CYBERCP-STATE.md`.



### Fixed: dark theme UI regression (31/05/2026)

- Restored external design system CSS (`cyberpanel-ui.css`, `dashboard.css`, `cyberpanel-harmonize.css`) that were missing from the repo; `index.html` again loads tokens from CSS instead of 3000+ lines of stale inline styles.
- Replaced bloated `index.html` / `homePage.html` with the v2.4.8 shell (flat HOSTING/ACCOUNT nav, command palette, theme toggle).
- Dark mode: sidebar, main canvas, and dashboard cards now share the same `--bg-*` tokens; harmonizer patch improves dashboard section title contrast.


### Fixed: dark mode sidebar stayed light (31/05/2026)

- `cyberpanel-ui.css` had a light-only `:root` refinement block after `[data-theme="dark"]`, which reset `--bg-sidebar` and `--bg-primary` to light colors even when dark mode was on. Scoped refinement to `:root:not([data-theme="dark"])` and added a dark token guard at end of the file.

### Fixed: SSH login banner (30/05/2026)

- Fresh installs and upgrades again deploy `/etc/profile.d/cyberpanel.sh` from `https://cyberpanel.sh/?banner`.
- Shared helper: `install/cyberpanel_ssh_login_banner.sh`, called from `apply_fixes`, `Post_Upgrade_System_Tweak`, and venvsetup.

## 2.5.5-dev - 28/05/2026

### Fixed: AlmaLinux 10 re-install exit 71 (ftpgroup already exists)

- `ensure_pureftpd_system_user()`: use `getent` before `groupadd` / `useradd` so Pure-FTPd setup does not fail with exit code 9 when `ftpgroup` or `ftpuser` already exists from a prior install.
- `restart_litespeed()`: try `lswsctrl` paths then `systemctl restart` (`lsws`, `openlitespeed`, `lshttpd`) when `/usr/local/lsws/bin/lswsctrl` is missing on re-install.

### Fixed: AlmaLinux 10 re-install OpenLiteSpeed (custom binary without lswsctrl)

- `ensure_openlitespeed_rpm_layout()`: `dnf reinstall openlitespeed` when the RPM is installed but `lswsctrl` or `httpd_config.conf` is missing.
- `should_skip_custom_ols_overlay()`: on EL10 with intact repo layout, skip CyberPanel custom OLS binary (2.4.4 rhel9) so re-install does not leave a broken `/usr/local/lsws`.
- `changePortTo80()`: port change no longer aborts when restart fails; logs a note instead of `[Errno 2] lswsctrl`.

### Fixed: AlmaLinux 10 install exit 71 (Django migration graph / emailDelivery)

- `discover_cybercp_migration_apps()`: before `makemigrations`, remove stale migration modules for **every** app with a `migrations/` package (including `emailDelivery` and `webmail`), not only the hardcoded list. Fixes `NodeNotFoundError: emailDelivery.0001_initial` depends on missing `loginSystem.0001_initial` after cleanup deleted `loginSystem` migrations only.
- `build_cyberpanel_clone_commands()` / `build_cyberpanel_archive_download()`: clone and zip fallback use `CYBERPANEL_GITHUB_OWNER` (default `master3395`), then `usmannasir` if needed, so installs from the fork pick up EL10 fixes.

### Fixed: AlmaLinux 10 install exit 71 (Django missing in CyberCP venv)

- `install_utils.ensure_cybercp_venv()`: after `git clone` into `/usr/local/CyberCP`, create or repair
  the venv with `virtualenv --system-site-packages` (or `python -m venv`), run `pip install -r requirments.txt`,
  and verify `import django` before migrations.
- `download_install_CyberPanel()`: fail fast if venv/Django setup fails instead of running
  `makemigrations` against a bare interpreter.
- Migration Python selection: only use interpreters that can `import django`; retry venv repair if needed.
- `universal_os_fixes.install_packages()`: on EL10, stop using `dnf --skip-unavailable` (removed in
  AlmaLinux 10); use batched `--skip-broken` installs and per-package fallback for optional deps.
- AlmaLinux 10: `universal_os_fixes` enables **CRB** instead of PowerTools; skips `compat-openssl11` on EL10.
- `fix_almalinux10_mariadb()`: install `openssh-server` so firewall/SSH port detection does not fail on
  minimal images missing `/etc/ssh/sshd_config`.
- `findSSHPort()`: install `openssh-server` when `sshd_config` is missing.
- `setupWebmail()`: detect Dovecot via `/etc/dovecot` + `doveadm` on EL10 (not only `dovecot.conf`).

### Fixed: AlmaLinux 10 clean install (LiteSpeed repo exit 71 + MariaDB conflicts)

- `install_utils.install_litespeed_repo_rhel()`: idempotent LiteSpeed RPM repo (`rpm -q` or `rpm -Uvh`);
  `resFailed()` treats `rpm` exit code 2 (already installed) as success.
- `installCyberPanelRepo()` / `universal_os_fixes` / `setupPHPSymlink`: use shared helper so install no longer
  aborts after OS fixes already installed `litespeed-repo`.
- `install_mariadb_server_rhel()`: on RHEL/Alma 10+, install **AppStream** `mariadb-server` first (avoids
  `mariadb-connector-c` vs `MariaDB-shared` conflicts); logs when MariaDB.org 11.8 was requested but not used.
- `installMySQL()`: skip automatic 10.x to 11.8 upgrade attempt on EL10.
- `setupAccounts()`: `getent group docker || groupadd docker` (no false error when group exists).
- `universal_os_fixes`: `dnf install --skip-unavailable`; drop `db4-devel` / `libgssapi-krb5` on EL10.

### Fixed: AlmaLinux 10 MariaDB install (false success + missing packages)

- `install_utils.resFailed()`: treat non-zero exit codes as failures on `cent8` and
  `openeuler` (AlmaLinux 10 was always reported as success, so failed `dnf install` continued).
- `install_utils.install_mariadb_server_rhel()`: MariaDB.org repo with `curl -fsSL` and
  `--skip-check-installed`, then AppStream fallback (`mariadb-server`, lowercase) when
  `MariaDB-*` RPMs are unavailable on EL10.
- `fix_almalinux10_mariadb()` / `installMySQL()` / `universal_os_fixes`: use shared helper and
  `--mariadb-version` / `MARIADB_VER` instead of hardcoded 11.8.

### Added: MariaDB version in Installation Preferences (before auto-install)

- `install_modules/00_common.sh`: `prompt_mariadb_version_preference()` menu (10.11, 11.8,
  12.1–12.3, or custom X.Y).
- `install_modules/05_menus_main.sh`: asks database version after debug mode and before
  "Auto-install without further prompts?"; summary shows MariaDB choice.
- Quick Install (option 5) also prompts for MariaDB before starting.
- `install_modules/02_install_core.sh`: skips duplicate MariaDB prompt when already chosen.
- `--mariadb-version` accepts any X.Y (not only 10.11 / 11.8 / 12.1).

### Fixed: AlmaLinux 10 install aborts after webmail (CDN / MariaDB / Django)

- `downloadCDNLibraries()`: `install_utils.call()` returns bool, not exit code; use `if result`
  instead of `if result == 0` so successful wget is recognized.
- `InstallLog.writeToFile()`: removed invalid second argument on several log lines (was causing
  `TypeError` and exit code 1 after CDN download).
- `installMySQL()`: use `ensure_mariadb_client_cli()` / `resolve_mysql_cli()` (includes
  `/usr/sbin/mariadb` on EL10); abort install if MySQL install fails; abort if cyberpanel DB
  creation fails (no longer continues with a broken database).
- Django migrations: prefer `/usr/local/CyberCP/bin/python` over system `/usr/bin/python3`.
- AlmaLinux 10 / universal fixes: install `curl` and `ca-certificates` before
  `mariadb_repo_setup` (script prerequisite check).

### Fixed: fresh install NameError on setupWebmail (AlmaLinux 10 and all EL targets)

- `install/install.py` called `installCyberPanel.InstallCyberPanel.setupWebmail()` without
  importing `installCyberPanel`, causing `NameError: name 'installCyberPanel' is not defined`
  after Dovecot/Postfix setup. Added `setup_webmail_master_user()` with a lazy import to avoid
  circular import with `installCyberPanel.py`.

## 2.5.5-dev - 27/05/2026

### Fixed: install directory not found after GitHub archive extract

- `install_modules/02_install_core.sh` detects the extracted top-level folder dynamically
  (`cyberpanel-2.5.5-dev`, `cyberpanel-v2.5.5-dev`, `cyberpanel-stable`, etc.) instead of only
  `cyberpanel-v2.5.5-dev`.

### Fixed: AlmaLinux 10 upgrade PHP matrix

- `plogical/upgrade.py::get_available_php_versions()` uses PHP 81–85 only on AlmaLinux 10
  (aligned with `install_utils.get_lsphp_install_suffixes()`).

### Fixed: installer requires root (WSL / non-root users)

- `install.sh` re-runs via `sudo` with `curl | sh` when started as a normal user (fixes
  `sh <(curl ...)` where `$0` is not the script path).
- `install_modules/09_parse_main.sh` calls `require_root` before creating `/var/log/CyberPanel`.
- `log_message` no longer fails fatally when `/var/log` is not writable.

### Fixed: cyberpanel.sh one-liner default branch

- Default module branch is `v2.5.5-dev` (not `stable`) when downloading `install_modules/`
  from GitHub; `BRANCH_NAME` is exported after `-b` parsing.
- If the chosen branch 404s, installer retries `v2.5.5-dev` automatically.

### Fixed: AlmaLinux 10 install (PHP matrix, MariaDB CLI, fork archive)

- `install_modules/02_install_core.sh`: GitHub branch archive probe accepts HTTP 200/302
  (fixes false "falling back to stable" when `master3395/v2.5.5-dev` tarball exists).
- `install/install_utils.py`: EL10 installs only `lsphp81` through `lsphp85` (no 71–80
  "No match" noise); `ensure_lsphp_runtime_deps()` and `ensure_mariadb_client_cli()`.
- `install/installCyberPanel.py`: cent8 PHP install skips imap/mbstring when deps missing;
  root password uses `ALTER USER` and socket auth; MariaDB client ensured after server install.

### Fixed: AlmaLinux 10 install bootstrap (`requests` missing)

- `install_modules/03_install_direct.sh` now `pip install requests` (with OS package
  fallback) before running `install/install.py`, because `installLog.py` imports
  `requests` before the CyberCP venv exists.
- AlmaLinux 10 / Python 3.12: install `python3.12-devel` when the bootstrap
  interpreter is `/usr/bin/python3.12`.
- `install_modules/02_install_core.sh` prefers `master3395/cyberpanel` for archive
  download, with fallback to `usmannasir/cyberpanel`.

### Removed: CentOS 7 and CloudLinux 7 (EOL)

- Fresh install and upgrade now exit immediately on EL7 with a migrate-to-AlmaLinux
  message (`reject_el7_if_present` in install/upgrade entry points).
- Removed EL7-only upgrade paths (MariaDB prep, repository IUS/python36u, libzip
  psychotic RPMs, `Pre_Upgrade_CentOS7_MySQL`).
- `plogical/upgrade.py::FindOperatingSytem()` no longer defaults non-8 RHEL to
  `CENTOS7`; EL8+ and AlmaLinux/Rocky/RHEL use `CENTOS8` paths.
- Docs and support strings no longer list CentOS 7 or CloudLinux 7.

**Operator action:** migrate existing EL7 hosts to AlmaLinux 8, 9, or 10 before
installing or upgrading this fork.

## 2.5.5-dev (based on v2.4.7) - 26/05/2026

### Security and stability (Phase 1)

- Removed plaintext-password log lines from `loginSystem/views.py`. The four
  `print()` calls that landed admin passwords and raw POST bodies in lscpd
  stderr are gone. (Upstream `4f18340`.)
- PowerDNS 4.7+/5.x schema migration. Added
  `plogical/pdnsSchemaMigration.py` and `plogical/pdnsHealthCheck.py`,
  extended `dns/models.py` with `catalog`, `options`, `published`, widened
  `type`, wired the migrator into `install/install.py::startDeferredServices`
  and `plogical/upgrade.py::upgrade`, and registered `pdnsHealthCheck.py` in
  the root crontab. (Upstream `bd72f75`.)
- Added `plogical/securityUtils.py` and `api/tests_security.py`. Helpers:
  `api_token_matches`, `is_safe_sql_identifier`, `is_safe_numeric_id`,
  `is_safe_port`, `is_safe_remote_host`, `safe_path_under`,
  `get_terminal_jwt_secret`. (Upstream `ad2b902`.)
- Tightened API authorization in `api/views.py`. Adds
  `can_change_api_account_password` and `can_change_api_website_package`
  ownership checks; refactored helpers `get_api_admin`, `api_error`,
  `api_auth_response`. (Upstream `7f92df8`.)
- Hardened `FetchRemoteTransferStatus` and `cancelRemoteTransfer` in
  `api/views.py`: replaced `cat` / `kill` / `rm -rf` shells with
  `safe_path_under` + `os.kill` + `shutil.rmtree`; validated `dir` input.
  (Upstream `522f5b1`.)
- `cloudAPI/cloudManager.py` now routes API token comparisons through
  `securityUtils.api_token_matches`. (Upstream `ad2b902` follow-up.)
- `databases/databaseManager.py` validates database names and usernames
  through `securityUtils.is_safe_sql_identifier`. (Upstream `ad2b902`
  follow-up.)
- `filemanager/filemanager.py` adds shell-safe path quoting, plus
  `validPermissions` and `pathInside` guards on inputs.

### Bug fixes and operator quality (Phase 2)

- OpenLiteSpeed module bumped from `cyberpanel_ols-2.7.0` to `2.7.1` in
  `install/ols_binaries_config.py` and `install/installCyberPanel.py`. The
  OLS binary itself stays at `2.4.4`. (Upstream `f40548b`.)
- `Install_CyberCP_Runtime_Python_Requirements` helper added to
  `install_modules/04_fixes_status.sh` and `upgrade_modules/10_post_tweak.sh`
  for installs and upgrades where `pythonenv.conf` sets `PYTHONHOME=/usr`;
  mirrors `requirments.txt` into system Python so lswsgi can import django.
  (Upstream `13c0697`.)
- SSL issuance progress UX: `sslIssuing` re-entrancy guard and visual
  feedback added across `manageSSL/static/manageSSL/manageSSL.js`,
  `static/manageSSL/manageSSL.js`, all four issuance controllers, the
  matching templates, and the `listWebsites` / `listChildDomains`
  controllers. (Upstream `267ea44`.)
- `upgrade_modules/00_common.sh::CyberPanel_Final_Upgrade_Verification`
  now treats `200`, `302`, `401`, `403` as healthy panel responses (was
  only `200`, `302`). (Upstream `e7635b0`.)
- `loginSystem/templates/loginSystem/login.html` already targets
  `https://cyberpanel.net/KnowledgeBase/home/change-logs/`; no change
  needed. (Upstream `d95722d` already present.)
- `WPsitesList.html` uses the fork's existing `try/catch
  angular.module('CyberCP')` pattern, which is functionally equivalent to
  upstream's single-`DOMContentLoaded` wrapper; no change needed.
  (Upstream `c81542d` already covered.)

### Version label alignment

- Synced `VERSION = '2.5.5'` and `BUILD = 'dev'` across
  `loginSystem/views.py`, `install/install.py`, `plogical/upgrade.py`,
  `plogical/backupUtilities.py`, `plogical/adminPass.py`, and
  `serverStatus/views.py` to match `baseTemplate/views.py` and
  `version.txt`.

### Explicitly skipped (deferred)

- Dashboard UI/UX overhaul (`560248f`, `3638b58`, `c51121a`, `a615b8d`,
  `7851b03`). 5000+ lines of changes across `baseTemplate/` plus new
  static assets. The backport plan flags this as optional and requires a
  staging snapshot before applying. Not deployed on this host. Operator
  may revisit on a staging copy.

## 2.5.5-dev (installer one-liner) - 27/05/2026

### install.sh / cyberpanel.sh module download

- `install.sh`: after downloading `cyberpanel.sh` from a branch (e.g.
  `v2.5.5-dev`), now runs `bash cyberpanel.sh -b "${BRANCH_NAME}"` and
  exports `CYBERPANEL_BRANCH` so modular `install_modules/` are fetched
  from the same branch (was defaulting to `stable`, which returned HTTP
  404 and produced `404:: command not found` when sourcing `00_common.sh`).
- `install.sh`: AlmaLinux 10 detection now sets `SERVER_OS=AlmaLinux10`
  (was `CentOS8`).
- `cyberpanel.sh`: remote module download validates HTTP 200 and a `#!`
  shebang before `source`; exits with a clear message on failure.

## 2.5.5-dev (open upstream PR adoption) - 26/05/2026

Three small, open upstream PRs adopted in advance of upstream merge.
File-only changes; no DB, no API contract change.

### Domain Alias UI wiring (PRs #1787, #1782)

- `websiteFunctions/templates/websiteFunctions/domainAlias.html`: the
  alias input now binds to `ng-model="aliasDomain"` (was
  `domainNameCreate`), the **Create Alias** button now calls
  `addAliasFunc()` (was `createDomain()` which posted to the
  child-domain endpoint), the success banner now reads "Alias
  succesfully created.", the **Issue SSL** button now calls the
  controller's defined `issueSSL(masterDomain, alias)` (was the
  undefined `issueAliasSSL(...)`). Dropped one duplicate `ng-hide` and
  one duplicate `ng-model="domainNameCreate"` on the search field.
  (Upstream PR #1782 and PR #1787, both still open.)
- `websiteFunctions/templates/websiteFunctions/website.html`: child-domain
  table dropdowns inside `ng-repeat` now bind to `record.childBaseDir`
  and `record.phpSelection` (were shared scope variables that bled
  across all rows). Dropped one duplicate `ng-hide` directive.
  (Upstream PR #1782.)
- `websiteFunctions/test_domain_alias_template.py`: new regression test
  (5 assertions) keeping the alias template pointed at alias actions.
  (Upstream PR #1787.)

User-visible effects: alias creation now posts cleanly to
`/websites/submitAliasCreation` (not the website-creation path with
`alias=1`), per-row PHP and open_basedir selectors no longer flip every
row, and the alias SSL button keeps working after the next
`collectstatic` (was relying on drift in `public/static/...`).

### Webmail Sieve forward rules (PR #1777)

- `webmail/services/sieve_client.py::rules_to_sieve`: removed the
  spurious `requires.add('redirect')` in the `forward` action branch.
  `redirect` is a built-in Sieve command per RFC 5228, not an extension;
  including it in `require[...]` made pigeonhole-sieve refuse to compile
  the script. Other extensions (`fileinto`, `imap4flags`) are
  unaffected. Forward filter rules added in the webmail UI now reach
  Dovecot. (Upstream PR #1777, still open.)
