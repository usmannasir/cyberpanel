# Live CyberCP alignment (operator checklist)

Generated during plan execution on the host that has `/usr/local/CyberCP`.

## Recorded state

Run on the same machine as the panel:

```bash
date -u +"%Y-%m-%dT%H:%M:%SZ"
git -C /usr/local/CyberCP rev-parse HEAD 2>/dev/null || echo "not a git checkout"
```

## Deploy steps (do not skip backup)

1. Put panel in maintenance or low traffic window.
2. `tar czf /root/cybercp-backup-$(date +%Y%m%d).tgz /usr/local/CyberCP /etc/cyberpanel 2>/dev/null` (adjust paths to match your layout).
3. Push `v2.5.5-dev` from [cyberpanel-v255-dev](file:///home/cyberpanel-v255-dev), then on server: `cd /usr/local/CyberCP && git fetch && git checkout v2.5.5-dev && git pull` (or your rsync procedure).
4. Install Python deps: use `requirments.txt` from that commit (includes Django **4.2.30** and related bumps).
5. `python3 manage.py migrate` if migrations changed.
6. Restart **lscpd** (or full **lsws restart**) per your CyberPanel + LiteSpeed runbook.
7. Smoke test: login, webmail, WP Manager, AI scanner if enabled.

## `manage.py check --deploy` note

Expect **warnings** for HSTS, `SECURE_SSL_REDIRECT`, cookie secure flags when TLS is terminated on a reverse proxy. Tune `settings.py` or vhost headers to match your edge TLS setup rather than blindly setting `SECURE_SSL_REDIRECT=True` behind HTTP to the app.

## Python 3.11 for new installs (`v2.5.5-dev`)

Fresh installs using `cyberpanel.sh` now:

- Install **python3.11**, **python3.11-pip**, and **python3.11-devel** on EL9-class distros (and modular `modules/deps/rhel_deps.sh` does the same).
- Export **`CYBERCP_VENV_PYTHON`** via **`ensure_cybercp_system_python`** in `install_modules/00_common.sh` (also invoked after modular `install_dependencies` in `modules/deps/manager.sh`).
- Run **`install/install.py`** with that interpreter and pass the same value into **`install.py`** so **`python -m venv /usr/local/CyberCP`** uses 3.11 even when the bootstrap `python3` is 3.9.
- Recreate venv paths in **`upgrade_modules/08_main_upgrade.sh`** and **`fix_cyberpanel_install.sh`** with the same bootstrap selection.

`requirments.txt` pins **`python-dotenv==1.2.2`** (needs Python **>=3.10**). That matches the **v2.5.5-dev** installer, which prefers **3.11** for `/usr/local/CyberCP`. If a host still has a **3.9**-only venv, recreate the venv with **python3.11** (or run `ensure_cybercp_system_python` / full upgrade path) before `pip install -r requirments.txt`.

## v2.4.7 backport - Phase 0 baseline backup (20260526T150128Z)

Backups taken before backporting CyberPanel v2.4.7 commits onto the
v2.5.5-dev fork. Treat this set as the rollback baseline for the whole
Phase 1, 2, and 3 sequence.

- **Location (on host):** `/root/cybercp-backup-20260526T150128Z/`
- **Filesystem tarball:** `cybercp-fs.tgz` (**1.5 GB**, 42,860 files,
  SHA-256 `439a702e538492dac6fcc725fe9baf4bf65b2a42161a183edee12cd9b6022f79`).
  Covers `/usr/local/CyberCP`, `/etc/cyberpanel`, `/etc/dovecot`,
  `/etc/postfix`, `/etc/pdns`, `/usr/local/lsws/conf`,
  `/usr/local/lscp/conf`, and the source repo
  `/home/newstargeted.com/cyberPanel-repos/cyberpanel-v255-dev`.
- **Database dumps:** 41 of 42 user databases (every DB except
  `news_webhook`), each `--single-transaction --routines --triggers
  --events` then `gzip -9`, hashes in `SHA256SUMS`. PowerDNS data is in
  the `cyberpanel` DB (`launch=gmysql, gmysql-dbname=cyberpanel`); the
  `cyberpanel.sql.gz` dump (292 K) covers PDNS, DNS zones, and panel
  state.
- **Skipped:** `news_webhook` (568 GB raw, customer application data
  unrelated to the CyberPanel upgrade). Reason recorded at
  `${BACKUP_DIR}/news_webhook.SKIPPED.txt`.
- **Permissions:** `chmod 600` on every `*.sql.gz` and `SHA256SUMS`.
  The tarball is `-rw-r--r--` (no secrets directly in the tar, but the
  repo + configs contain credentials in cleartext, so do not publish).

### Off-host copy (operator action required)

This host has no pre-configured off-host backup destination (no
rclone, no aws-cli, no second mount, no systemd backup unit; root
crontab only schedules CyberPanel's own IncScheduler). Before kicking
off Phase 1 the operator should manually copy the backup folder off
this server, for example from the operator workstation:

```bash
rsync -aP root@<live-host>:/root/cybercp-backup-20260526T150128Z/ \
  /srv/backups/cybercp/20260526T150128Z/
```

Or use the existing Contabo snapshot facility for the whole VPS before
Phase 1 starts. Record the actual destination here once it is done:

- `20260526T150128Z`: Phase 0 baseline backup. Local: `/root/cybercp-backup-20260526T150128Z/`. Off-host copy: **TODO - operator to copy**. SHA256SUMS verified. Pre-v2.4.7 backport baseline.

### Restore drill results (20260526T150128Z)

- Filesystem tarball extracted to a scratch dir: OK (42,860 files,
  exit 0).
- `version.txt` byte-for-byte match between live and restored copy.
- `/etc/pdns/pdns.conf` MD5 match between live and restored copy.
- `cyberpanel.sql.gz` reimported into `drill_cyberpanel` schema;
  row counts match live: `domains=2`, `loginSystem_administrator=2`,
  `websiteFunctions_websites=3`. Drill schema dropped after the test.

Backup is verifiably restorable. Cleared to proceed with Phase 1.

### Phase 1 deploy results (20260526T180600Z)

Phase 1 files deployed to `/usr/local/CyberCP/`:

- `loginSystem/views.py` (removed four `print()` calls that logged the raw login POST body, the admin username, and the password-check result; commit `4f18340`).
- `dns/models.py` (added `Domains.catalog`, `Domains.options`, widened `Domains.type` to `VARCHAR(8)`, added `Cryptokeys.published`; commit `bd72f75`).
- `plogical/pdnsSchemaMigration.py` (new; idempotent PDNS 4.7+/5.x schema migrator).
- `plogical/pdnsHealthCheck.py` (new; cron watchdog at `*/5 * * * *`).
- `plogical/upgrade.py` (registers `pdnsSchemaMigrations()` and `pdnsHealthCheck.py` cron line).
- `install/install.py` (calls migrator before first `systemctl start pdns`).
- `plogical/securityUtils.py` (new; `api_token_matches`, `is_safe_sql_identifier`, `is_safe_numeric_id`, `is_safe_port`, `is_safe_remote_host`, `get_terminal_jwt_secret`; commit `ad2b902`).
- `api/tests_security.py` (new; 5 tests, all green).
- `api/views.py` (added `can_change_api_account_password`, `can_change_api_website_package` ownership checks for `changeUserPassAPI` + `changePackageAPI`; replaced `cat /home/backup/transfer-...` shell-outs with safe `open()` + `os.kill` + `shutil.rmtree`; commits `7f92df8` + `522f5b1`).
- `cloudAPI/cloudManager.py` (uses `api_token_matches` for `HTTP_AUTHORIZATION` check; fixes bad return-tuple in `verifyLogin` exception path).
- `cloudAPI/views.py` (Django import compat shim for `url_has_allowed_host_and_scheme` / `is_safe_url`, uses `api_token_matches`, adds open-redirect guard around `redirectFinal`; commit `014f40c`).
- `databases/databaseManager.py` (rejects DB names/usernames that aren't `[A-Za-z0-9_]{1,64}` in `submitDBCreation` / `submitDatabaseDeletion` / `changePassword`).
- `filemanager/filemanager.py` (escapes single quotes in `returnPathEnclosed`, adds `validPermissions` + `pathInside`, quotes shell args in copy/upload/compress/ls paths, restricts `writeFileContents` to inside `data['home']`).

PDNS schema migration applied on live host:

- `add domains.catalog`
- `add domains.options`
- `widen domains.type to VARCHAR(8) NOT NULL`
- `make domains.notified_serial UNSIGNED`
- `add cryptokeys.published`
- `create domains.catalog_idx`
- PowerDNS 5.0.4 restarted, `systemctl status pdns` -> `active (running)`, watchdog confirms `restart_loop=false`, `n_restarts=0`.

`api.tests_security` -> all 5 tests pass on live. `systemctl restart lscpd` -> `active (running)`. HTTP smoke tests: `GET https://localhost:2087/` returns 200 + login page; `POST /api/changeUserPassAPI` with bogus credentials returns `status=0, "Failed to change user password"` (auth path runs).

`/var/spool/cron/root` now contains:

```
*/5 * * * * /usr/local/CyberCP/bin/python /usr/local/CyberCP/plogical/pdnsHealthCheck.py >/dev/null 2>&1
```

### Phase 2 pre-flight backup (skipped per plan)

Phase 1 finished within the last hour, so per the plan's rule
("skip if Phase 1 finished within the last 6 hours") no fresh backup
was taken for Phase 2. The Phase 0 baseline at
`/root/cybercp-backup-20260526T150128Z/` remains valid because
Phase 1 only added migration columns to the `cyberpanel` DB (the
ad2b902 / securityUtils changes are file-only) and Phase 2 is purely
file-only (SSL UI spinner, OLS module URL bumps, changelog URL,
controller registration). Phase 3 would need a fresh backup if taken
(see `phase3-prebackup` in `/root/.cursor/plans/backport-v247-into-v255-dev_abfda176.plan.md`).

### Phase 2 deploy results (20260526T183800Z)

Phase 2 files deployed to `/usr/local/CyberCP/`:

- `install/ols_binaries_config.py` and `install/installCyberPanel.py`:
  `cyberpanel_ols` module URL bumped from `2.7.0` to `2.7.1` for
  `rhel8` / `rhel9` / `ubuntu`. OLS binary itself stays at `2.4.4`.
  (Upstream `f40548b`.)
- `install_modules/04_fixes_status.sh`: added
  `Install_CyberCP_Runtime_Python_Requirements` helper and wired it
  into `apply_fixes` so a fresh install mirrors `requirments.txt`
  into system Python when `/usr/local/lscp/conf/pythonenv.conf` sets
  `PYTHONHOME=/usr`. (Upstream `13c0697`.)
- `upgrade_modules/10_post_tweak.sh`: invokes the same helper after
  the upgrade writes `PYTHONHOME=/usr` to `pythonenv.conf`.
  (Upstream `13c0697` follow-up.)
- `requirments.txt`: added the `# v2 API` comment above the
  `cloudflare==2.20.0` pin so future operators know not to bump it
  to `cloudflare 5.x` (which drops `import CloudFlare`).
- `manageSSL/static/manageSSL/manageSSL.js` and
  `static/manageSSL/manageSSL.js`: added `$scope.sslIssuing`
  re-entrancy guard to `sslIssueCtrl`, `sslIssueCtrlV2`,
  `sslIssueForHostNameCtrl`, `sslIssueForMailServer`. Guard resets
  in success and error callbacks. (Upstream `267ea44`.)
- `manageSSL/templates/manageSSL/manageSSL.html`,
  `sslForHostName.html`, `sslForMailServer.html`,
  `v2ManageSSL.html`: Issue SSL button now disables, swaps to
  spinner + "Issuing SSL..." copy, and shows an info banner while
  the request is in flight.
- `websiteFunctions/templates/websiteFunctions/listWebsites.html`
  and `listChildDomains.html`: per-domain `issuingSSL[web.domain]`
  guard on the Issue SSL link, spinner + "Issuing SSL..." label.
- `static/websiteFunctions/websiteFunctions.js` and
  `public/static/websiteFunctions/websiteFunctions.js`: same
  per-domain guard plus a `PNotify` info banner ("SSL issuance has
  started. This can take a few minutes.") when the request fires.
- `upgrade_modules/00_common.sh`:
  `CyberPanel_Final_Upgrade_Verification` now treats `200`, `302`,
  `401`, `403` as healthy panel responses (was only `200` and
  `302`). The `curl` already follows redirects. (Upstream `e7635b0`.)
- `loginSystem/templates/loginSystem/login.html` already targets
  `https://cyberpanel.net/KnowledgeBase/home/change-logs/`; no
  change needed. (Upstream `d95722d` already present.)
- `WPsitesList.html` still uses the fork's
  `try { angular.module('CyberCP'); } catch(err) { angular.module('CyberCP', []); }`
  pattern. Functionally equivalent to upstream's
  single-`DOMContentLoaded` wrapper; no change. (Upstream
  `c81542d` already covered.)

Smoke tests after Phase 2:

- `systemctl restart lscpd` -> `active (running)`.
- `curl -k -L https://127.0.0.1:2087/` -> `200`.
- `lsws`, `mariadb`, `pdns` all `active`.

### Version label alignment (20260526T184000Z)

- `loginSystem/views.py`, `install/install.py`, `plogical/upgrade.py`,
  `plogical/backupUtilities.py`, `plogical/adminPass.py`,
  `serverStatus/views.py` all bumped to `VERSION = '2.5.5'`,
  `BUILD = 'dev'`. Now agrees with `baseTemplate/views.py` and
  `version.txt`.
- Top-level `CHANGELOG.md` created at the repo root documenting the
  `v2.4.7` lineage (lives at the repo root per CyberPanel convention,
  not under `to-do/`).
- Live `lscpd` restarted, `GET https://127.0.0.1:2087/` returns
  `200`.

### Skipped: Phase 3 dashboard overhaul

Plan flags Phase 3 (`560248f` + `3638b58` + `c51121a` + `a615b8d` +
`7851b03`) as **optional**: a 5000+ line rewrite of `baseTemplate/`
(homepage, base template, two new CSS files, defer/sync script
loading). The plan also says:

> Test on a staging snapshot first because it rewrites how every
> page in the panel loads JS and CSS.

This live host has no staging copy, so Phase 3 is deferred. The
matching `phase3-prebackup` step is therefore not run, per the plan
("only if Phase 3 is taken"). To revisit later: build a staging
snapshot (Contabo snapshot + clone, or a separate VPS with the same
config), backport on the snapshot, validate the dashboard + all
plugin pages, then redo Phase 0 backups on the live host before
porting Phase 3 across.

## Restore procedure

This is the rollback runbook for the v2.4.7 backport (Phase 1 + 2),
keyed to the Phase 0 baseline at
`/root/cybercp-backup-20260526T150128Z/`. The same procedure works
with any future `${BACKUP_DIR}` produced by the Phase-0 procedure in
`/root/.cursor/plans/backport-v247-into-v255-dev_abfda176.plan.md`.

### When to use this

Run a restore if any of these is true after a deploy:

- `systemctl status lscpd` is not `active (running)` for more than
  a minute after a restart.
- `curl -k -L -sS https://127.0.0.1:2087/` returns a connection
  error or a 5xx longer than 60 seconds.
- `systemctl status pdns` is in a restart loop (more than 3
  restarts in 10 minutes; the watchdog logs to
  `/home/cyberpanel/error-logs.txt` and updates
  `/etc/cyberpanel/health.json`).
- A new API call (changeUserPassAPI / changePackageAPI / file
  manager) returns `500` or panics in `lscpd` error logs and
  cannot be patched live.
- Login is broken for the super-admin.

Do **not** use this procedure for missing customer data (file or
DB) that pre-dates the backup; that needs a customer-specific
restore from the corresponding `*.sql.gz` only.

### Steps

```bash
TS=20260526T150128Z                   # change to the matching baseline
BACKUP_DIR=/root/cybercp-backup-${TS} # filesystem + DB dumps
DRILL_DIR=/root/cybercp-restore-${TS} # scratch dir for the tarball
```

1. **Quiesce CyberPanel services.** Leave MariaDB up so we can
   reimport DB dumps:

   ```bash
   systemctl stop lscpd lsws pdns dovecot postfix
   ```

2. **Extract the filesystem tarball** to a scratch dir:

   ```bash
   mkdir -p "${DRILL_DIR}"
   tar -xzpf "${BACKUP_DIR}/cybercp-fs.tgz" -C "${DRILL_DIR}"
   ```

3. **Restore `/usr/local/CyberCP`** (the panel application):

   ```bash
   rsync -a --delete-after \
     "${DRILL_DIR}/usr/local/CyberCP/" \
     /usr/local/CyberCP/
   ```

   The tarball already contains the venv (`bin/`, `lib/`,
   `lib64/`, `pyvenv.cfg`) so do **not** strip them here. They are
   what made `lscpd` work at the baseline.

4. **Restore the service configs** that were tarball'd alongside
   the panel:

   ```bash
   for d in /etc/cyberpanel /etc/dovecot /etc/postfix /etc/pdns \
            /usr/local/lsws/conf /usr/local/lscp/conf; do
     [ -d "${DRILL_DIR}${d}" ] && \
       rsync -a --delete-after "${DRILL_DIR}${d}/" "${d}/"
   done
   ```

5. **Restore databases** that the failed phase touched. Pick the
   smallest set that matches the symptom:

   - **Phase 1 (PDNS schema or panel admin records broken):**

     ```bash
     mysql -e "DROP DATABASE IF EXISTS cyberpanel; CREATE DATABASE cyberpanel CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
     gunzip -c "${BACKUP_DIR}/cyberpanel.sql.gz" | mysql cyberpanel
     ```

     PDNS data lives inside the `cyberpanel` DB on this host
     (`launch=gmysql, gmysql-dbname=cyberpanel`); there is no
     separate `pdns` schema in the backup set.

   - **Phase 2 (file-only changes):** no DB restore needed.
   - **Phase 3 (UI-only):** no DB restore needed.

6. **Re-own the venv** if the tarball owner differs from runtime:

   ```bash
   chown -R cyberpanel:cyberpanel \
     /usr/local/CyberCP/lib /usr/local/CyberCP/lib64 \
     2>/dev/null || true
   ```

7. **Start services back in order:**

   ```bash
   systemctl start mariadb pdns dovecot postfix lsws lscpd
   for s in mariadb pdns dovecot postfix lsws lscpd; do
     systemctl is-active "$s" || echo "WARN: $s not active"
   done
   ```

8. **Smoke test the panel:**

   ```bash
   curl -k -L -sS --max-time 10 -o /dev/null \
     -w 'panel=%{http_code}\n' https://127.0.0.1:2087/
   # expect: panel=200
   systemctl status pdns --no-pager | head -5
   # expect: Active: active (running) and no restart loop
   ```

   Then in a browser: log in, list websites, open the DNS panel,
   send a test email through one of the mailboxes.

9. **Record the restore** in this file. Append a line under "Recorded
   state" or under the matching phase section:

   ```
   - <ISO ts>: Restored from /root/cybercp-backup-<ts>/ (reason: <one line>).
     Phase 1 changes rolled back, panel verified at https://127.0.0.1:2087/.
   ```

### Verifying the rollback actually rolled back

After step 8 succeeds, run these spot checks; they should match the
**baseline** (pre-Phase-1) values, not the current-deploy values:

```bash
grep '^VERSION\|^BUILD' /usr/local/CyberCP/loginSystem/views.py
# baseline: VERSION = '2.4' / BUILD = 4
grep -c 'pdnsSchemaMigration\|pdnsHealthCheck' \
  /usr/local/CyberCP/plogical/*.py
# baseline: 0 (these files did not exist pre-Phase-1)
ls /usr/local/CyberCP/plogical/securityUtils.py 2>&1
# baseline: No such file or directory
crontab -l | grep -c pdnsHealthCheck
# baseline: 0
```

If any of these still show the post-deploy values, the rsync in
step 3 did not cover that path. Rerun step 3 with `--delete-after`
(it should remove the new files that did not exist in the baseline).

### Catastrophic restore (host loss)

If the host itself is unrecoverable:

1. Provision a matching AlmaLinux 9.6 host (or whatever the panel
   was running on; see top of this file).
2. Copy `${BACKUP_DIR}` from the off-host destination back to
   `/root/cybercp-backup-${TS}/` on the new host.
3. Reinstall CyberPanel from `install_modules/` using the same
   `cyberpanel.sh` from the source repo (it will set up venv,
   `lscpd`, `lsws`, MariaDB).
4. Stop services, run steps 2-8 above to overlay the tarball + DB
   dumps on top of the fresh install.
5. Rerun `cyberpanel_upgrade.sh` (or the modular `upgrade_modules/`
   equivalent) if the new host's package versions differ; the
   upgrade script's `CyberPanel_Final_Upgrade_Verification` now
   treats `401` / `403` as healthy answers, so an auth-gated probe
   is no longer flagged as a failure.

## Upstream PR adoption deploy (PRs #1787, #1782, #1777) - 26/05/2026

Open upstream PRs adopted on top of the v2.4.7 backport.

- **Pre-deploy targeted backup of live files:**
  `/root/cybercp-prefix1782-1787-1777-20260526T181308Z/` (4 files,
  ~130 KB; covers `domainAlias.html`, `website.html`,
  `sieve_client.py`). The full Phase-0 tarball at
  `/root/cybercp-backup-20260526T150128Z/` remains the catastrophic
  rollback baseline.
- **Files deployed to `/usr/local/CyberCP` (chmod 644, root:root):**
  - `websiteFunctions/templates/websiteFunctions/domainAlias.html`
  - `websiteFunctions/templates/websiteFunctions/website.html`
  - `webmail/services/sieve_client.py`
  - `websiteFunctions/test_domain_alias_template.py` (new file)
- **Regression test:**
  `/usr/local/CyberCP/bin/python manage.py test
  websiteFunctions.test_domain_alias_template` -> `Ran 1 test ... OK`.
- **Sieve generator sanity check (eval):**
  - Forward-only rule -> no `require [...]` line.
  - Mixed forward + move rule -> `require ["fileinto"];` only.
  Matches PR #1777 test plan.
- **Repo / live sha256 match:** verified for all four files via
  `sha256sum`.
- **Automated smoke (27/05/2026):** `systemctl is-active lscpd` ->
  `active`; `curl -k -L https://127.0.0.1:2087/` -> HTTP 200;
  `manage.py test websiteFunctions.test_domain_alias_template` ->
  `Ran 1 test ... OK`.
- **Outstanding manual smoke (operator):** click through Create Alias
  -> Issue SSL -> Delete on a real alias, change PHP / open_basedir
  for one row in the child-domain table (verify no row bleed), add a
  Forward filter rule in webmail and send a test email matching it.
- **Rollback (4-file):**
  ```bash
  B=/root/cybercp-prefix1782-1787-1777-20260526T181308Z
  for f in websiteFunctions/templates/websiteFunctions/domainAlias.html \
           websiteFunctions/templates/websiteFunctions/website.html \
           webmail/services/sieve_client.py; do
    install -o root -g root -m 644 "$B/$f" "/usr/local/CyberCP/$f"
  done
  rm -f /usr/local/CyberCP/websiteFunctions/test_domain_alias_template.py
  systemctl restart lscpd
  ```
