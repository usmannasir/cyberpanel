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
