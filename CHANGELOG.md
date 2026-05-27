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

## 2.5.5-dev - 27/05/2026

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
