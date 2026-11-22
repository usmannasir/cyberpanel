# Changelog

All notable changes to CyberPanel are documented here. The canonical,
continuously updated changelog also lives at
https://cyberpanel.net/KnowledgeBase/home/change-logs/

## v3.0.12 (build 12) — 2026-11-22

Security and reliability release. It hardens databases, Docker sites, the PHP
manager, the AI Scanner and the way the panel takes requests, and adds a link
to where a Multi-Server Manager licence is bought. Upgrading is recommended for
every server, especially servers with more than one panel user.

### Databases
- A database user is granted its own database and nothing else, whatever the
  database is called. An upgrade gives the grants of earlier releases the same
  exact form, keeps every account's access to its own database, and lists in
  the upgrade log any pattern grant it did not make itself.
- The prefix of a new database name comes from the website, not from the
  browser.
- A database dump (restore, Backup V2, incremental backup, cPanel import) is
  loaded by a temporary account that can use the target database only. Views,
  triggers and routines of the dump are handed to the database's own user.
- A restore re-creates only the accounts that belong to the database, and the
  site's own user wherever the backup lists it. Deleting a database removes
  only its own accounts. Backups no longer record phpMyAdmin sign-in accounts.
- Database dumps are private files from the moment they exist, and an
  incremental backup fails when its fresh dump cannot be saved.
- A user who is not an administrator signs in to phpMyAdmin with an account
  named after the user's number. It is rebuilt at every visit from what the
  user manages then and removed when that changes (suspension, deletion, role
  change, a website moving to another owner).
- Changing a database user's password or remote access acts on the user
  registered for one's own websites only, never on an account of the server.
- The name of a new panel user starts with a letter or number and may contain
  letters and numbers of any alphabet, dots, dashes, underscores and @, 50
  characters at most. Existing users keep their names.

### Docker sites
- An application is put on an existing website, and a site's containers are
  started, stopped, restarted and deleted, only for the owner of that website.
  A site's containers are found by its Compose project and directory, never by
  part of a name.
- A new n8n site is published on the loopback address only, gets its owner
  account from the creation form before it goes online, an encryption key of
  its own, and at least 768 MB. A failed deployment says why and can be tried
  again.
- An upgrade lists n8n sites that earlier releases deployed and that still
  publish their port on every address or have no owner account yet, and
  changes nothing on them. Review the sites it names; the list can be printed
  again with `python /usr/local/CyberCP/plogical/DockerSites.py CheckN8NSites`.
- Deleting a Docker site takes only the panel's own rules out of the
  website's `.htaccess`, and a port is never given to a second site.
- Compose files are written with every value quoted and are private from the
  start; a site's directory is private to root.
- The Docker and container package installers start from the panel's own page
  only, and a command run from the container page has the container's own
  privileges.

### PHP
- A PHP version is accepted only as one of the panel's selections, in every
  request and again in the workers. Older spellings from the command line, the
  API and backups (`PHP 74`, `7.4`) are still understood.
- A PHP change for one website on the Apache backend reloads PHP-FPM instead
  of stopping it, and every PHP-FPM pool has a name of its own.
- The PHP settings pages write only the php.ini files the panel manages, from
  checked values, and replace a file in one step.
- The extension pages install and remove PHP packages only. Tuning and
  open_basedir values are checked before the worker runs.
- The first website on the Apache backend, which installs Apache and PHP-FPM
  for the whole server, is created by an administrator.

### AI Scanner
- The scanner reads and changes a website's files as the website's own user
  and only inside the site. The access token of a scan can only read; the
  scanner key reaches only the website its scan was started for, for a week.
- Backups made before a fix are kept in the website's home, outside every
  served folder, and an upgrade moves the backups of earlier releases there.
- A scan result is stored once, scheduled scans are checked and escaped, live
  progress is shown to the signed-in owner only, and tokens and keys stay out
  of the panel log.

### Requests
- The panel reads every request body to its end before it answers, so nothing
  of one request is left for the next one on the same connection.

### Multi-Server Manager
- The role page, the Nodes page and the combined lists link to where a
  licence for this controller is bought.

## v3.0.11 (build 11) — 2026-11-22

Multi-Server Manager. One CyberPanel server, the controller, manages your other
CyberPanel servers from its own panel. It is a separately licensed add-on for
the controller; the servers it manages need no licence. The feature is off on
every server until an administrator turns it on, and an upgrade changes nothing
for a server that does not use it.

### Multi-Server Manager
- Multi-Server in the sidebar gives a server its role: controller or managed
  server. Changing the role needs two-factor login on the administrator's
  account, the password and a fresh verification code. Root can do the same on
  the command line with `multiServer/msctl.py`.
- Two servers are paired by their administrators. The managed server makes a
  one-time pairing code for the address of the controller. The controller
  shows what the code says before it connects, connects only to the
  certificate the code names, and then shows an eight-digit number. The link
  becomes active when that number is typed on the managed server.
- On the controller: the Nodes page (status, version, pause, resume, revoke),
  combined lists of the websites, databases and mailboxes of all servers, a
  server switcher in the header, and "Open this page on another server" on
  create pages. Opening a server signs the administrator in to that server's
  own panel with a single-use ticket; the session shows which controller it
  came from and ends when the link is paused, revoked or ended.
- On the managed server: the Controllers page lists the controllers, approves
  or rejects a request, and ends a link at once.
- Every request between two servers is signed, bound to the certificate that
  was pinned when the servers were paired, and accepted only from the address
  of the controller. The managed server keeps an audit trail of what a
  controller did.
- A session opened from a controller cannot create or change panel users,
  access rights or API access, and cannot open phpMyAdmin, the terminal or SSH
  keys of the managed server.

### Upgrades
- On AlmaLinux, Rocky and CloudLinux 8 an upgrade stopped with "Cannot safely
  preserve SESSION_COOKIE_SECURE" (or CSRF_COOKIE_SECURE,
  SESSION_COOKIE_HTTPONLY) when an administrator had set these cookie options
  in the panel's settings by hand. The upgrade now keeps them there too.

## v3.0.10 (build 10) — 2026-11-21

Automatic updates. A server can now keep its own CyberPanel up to date, and
only with a release that CyberPanel signed. The feature is off until an
administrator turns it on.

### Automatic updates
- Version Management has an Automatic Updates card: do nothing, tell me by
  e-mail, or install new releases automatically during an hour you choose.
- A release is installed only when its signature verifies against keys built
  into the panel, and the server installs exactly the signed commit, whatever
  the release branch holds at that moment.
- A new release is installed after a waiting period, and servers take their
  turn over a spread of hours instead of all at once. CyberPanel can pause the
  automatic installation of a release.
- One attempt is made per release. If it fails, the previous version is put
  back, the result is sent by e-mail and the release can be installed from the
  page. Low disk space or an installed CSF stops the installation with a
  message instead of an attempt.
- Nothing is scheduled on a server that has not turned the feature on, and
  operating-system packages are not touched.

### Mail on AlmaLinux, Rocky and CloudLinux 8
- A fresh install on these systems ended up with Dovecot but without its MySQL
  driver, so no mailbox could sign in and Postfix refused every connection.
  Installation now completes the mail server, and an upgrade installs the
  missing driver on servers that were set up that way.

### Upgrade page
- Carries the upgrade page changes published on the v3.0.9 line on 21 November
  (listed under v3.0.9 below).

### Upgrades on servers with a misconfigured website (22 November)
- An upgrade stopped at its OpenLiteSpeed check when a single website was
  misconfigured, for example a website still set to a PHP version that is no
  longer installed, or a stray brace in one website's file. OpenLiteSpeed runs
  with such errors and they do not come from the upgrade. The upgrade now
  lists the affected websites and continues. It still stops for an error that
  affects the whole server, and for an error that appears in a website that
  had none when the upgrade began.
- A server running the stock OpenLiteSpeed package is checked before any
  package is changed, instead of after.

## v3.0.9 (build 9) — 2026-11-20

Security and reliability release. It contains every fix published on the
v3.0.8 line since 18 October and the hardening below. Upgrading is recommended
for every server, especially servers with more than one panel user.

### Panel requests and progress pages
- Progress polling for website creation, application installs, backups,
  restores, DNS and FTP resets reads only the panel's own progress files, and
  restore progress now requires a signed-in user with backup permission.
- List pages delete an item only when the request comes from the panel's own
  page, so a link on another site can no longer trigger a deletion.
- Backup progress is reported only to the website's owner, and cancelling a
  remote transfer accepts a transfer number only.
- A command run for a website's account is refused if a stored value would make
  it run a second command.

### Websites, files and keys
- Permission repair, per-site SSH keys, git settings and File Manager saves act
  as the website's own user and do not follow links placed in the home directory.
- File Manager uploads, edits, rewrite rules and new cron entries pass through
  private files with unguessable names instead of four-digit names in shared
  directories.
- Website and child-domain creation options, cron line numbers, WordPress plugin
  and theme names are checked before they reach a command.
- A DKIM key is shown or created only for the owner of every site under its
  domain.

### Backups and WordPress tools
- Backup V2 restores only the selected website's own files, mail and databases,
  sets up storage without placing credentials on a command line, and keeps only
  checked values in a schedule.
- Restoring a database from a Backup V2 snapshot works from the panel again;
  the dump is read as the website's own account and passed straight to MySQL.
- Restoring a WordPress or one-click backup downloads the archive over SFTP
  instead of installing a key for the storage host on this server. Servers that
  restored such a backup with an earlier build should review
  `/root/.ssh/authorized_keys` and remove keys they do not recognise.
- Remote WordPress backup destinations, schedules and sites belong to the user
  who created them.

### Installation
- Fresh Ubuntu 22.04 and 24.04 installs since 15 November left the panel's
  interpreter configuration unreadable to website users, so a website's cron
  page showed a start-up error. Installation and upgrade now set the mode that
  website users need.

### Upgrade page (added 21 November)
- An upgrade started from Version Management rebuilds the panel's web worker,
  as the command-line upgrade does, so background jobs keep running between
  requests on those servers too.
- The newest release is selected by default, an older release is neither
  offered nor accepted, and the page asks before it starts.
- Each run has its own log, kept to its end. A failure shows its reason and the
  last lines of the log, and a second tab or click joins the running upgrade.
- If an upgrade fails after the new files are in place, or the panel does not
  start on them, the previous version is put back and the panel restarted.
- A server on the stable branch is no longer told that its commit does not
  match, and only an administrator can rewrite the stored version number.

## v3.0.8 (build 8) — 2026-10-18

Maintenance release collecting the fixes developed on the v3.0.7 line.

### Backups, databases and transfers
- Clarifies all-site versus selected-site scheduled backups, reports failed or
  exited workers, and uses private temporary backup metadata.
- Preserves restored website ownership, private modes and certificate chains;
  handles database-deletion retries without deleting MySQL filesystem paths.
- Improves remote-transfer callbacks, SSH-port handling and failure reporting.
- Keeps phpMyAdmin sign-on on the configured panel port and reports access
  failures without duplicate handoffs; refreshes stale database-controller assets.

### Websites, mail and daily administration
- Allows quoted apostrophes and parentheses in File Manager upload names while
  retaining ownership, path-containment and command-input checks.
- Corrects secondary-administrator greetings and subdomain DKIM record selection.
- Keeps webmail inbox headers intact when a long Unicode subject would make
  an unused IMAP envelope arrive as a separate literal response.
- Initializes required email-filter tables during a fresh install so native
  website deletion can complete without missing-table errors.
- Repairs domain-alias routing/certificate names and WordPress Docker readiness;
  preserves explicit host-port bindings and exact Docker image tags.
- Reloads OpenLiteSpeed once for an observed .htaccess change rather than on
  every polling cycle, and keeps SSL renewal from restarting panel backup workers.
- Adds guarded optional Sieve configuration, certificate-aware mail SNI setup,
  improved theme fallback and Brazilian Portuguese interface coverage.

### Upgrade and authentication safeguards
- Preserves working Python environments and restores panel runtimes when an
  upgrade rebuild fails; limits retained rollback directories and preserves
  operator firewall and optional-service policies.
- Normalizes IPv4/IPv6 session binding, rejects ambiguous legacy bindings and
  permits a fresh login after a stale session's address changes.
- Isolates ACME staging state, validates production certificates before deploying
  them and reissues already-installed staging certificates.
- Keeps Google Drive authorization handoffs and feature entitlements guarded;
  publication does not validate an individual customer's external OAuth flow.

### Known limitation
- Issue #1924 remains open: PHP lint can crash when ionCube and OPcache are
  enabled together. The verified workaround is the separate PHP CLI with
  `opcache.enable_cli=0` for syntax checks. This release does not change global
  OPcache settings or claim to fix the runtime compatibility defect.

## v3.0.7 (build 7) — 2026-09-21

Feature release for optional Roundcube webmail and upgrade visibility.

### Roundcube paid add-on
- Added an optional, entitlement-gated Roundcube 1.7.4 integration while
  retaining CyberPanel's integrated webmail as the default client.
- Runs Roundcube behind the panel HTTPS endpoint in a dedicated PHP-FPM service
  with a private Unix socket, restricted runtime state, and protected sessions.
- Preserves contacts, preferences, database state, and the encryption key across
  disable, re-enable, and install/update operations.
- Blocks installer, configuration, SQL, arbitrary PHP, and traversal paths and
  fails closed when the paid entitlement expires or cannot be verified.

### Webmail and upgrades
- Updated standalone integrated webmail with the current CyberPanel branding,
  a focused mailbox layout, dark mode, and corrected mobile detail views.
- Streams Python upgrader progress live while retaining the command exit status
  and complete upgrade log.

## v3.0.6 (build 6) — 2026-09-07

Maintenance and security hardening for standalone webmail authentication.

### Webmail authentication
- The dedicated `/webmail/login` page and its login/logout APIs are reachable
  without a CyberPanel administrator session, allowing ordinary mailbox users
  to authenticate directly against IMAP.
- Standalone mailbox sessions are isolated from CyberPanel administrator
  sessions and are accepted only when all required mailbox-session fields are
  present.
- Standalone login rotates the session identifier, expires after 12 hours,
  rate-limits repeated failures, and returns a generic authentication error.
- Login and logout are POST-only and CSRF-protected. The login page now always
  issues the CSRF cookie needed by the browser client.
- Standalone users can access only their authenticated mailbox and now have a
  dedicated sign-out action.

## v3.0.5 (build 5) — 2026-08-26

Security update for API authentication and two-factor enforcement.

### Security
- Standard API, cloud API, connection verification, and panel-session handoff
  now require a current TOTP code whenever two-factor authentication is
  enabled for the account.
- API keys are versioned, cryptographically random credentials independent of
  the account password. Enabled accounts using legacy keys receive a new key
  during upgrade.
- API Access can display a newly enabled key, regenerate it on demand, and
  revoke it completely when access is disabled.
- Repeated invalid API TOTP attempts are rate-limited per account and source.
- Password-authenticated connection verification returns the account's current
  API key only after all required factors succeed and marks the response as
  non-cacheable.

### Integration guidance
- Send the current TOTP code in the `X-CyberPanel-OTP` header or the JSON
  `otp` field. TOTP values are not accepted from query strings.
- After upgrading, replace legacy password-derived keys in external tools with
  the key shown under **Users > API Access**.
- Provisioning systems can set a pre-generated `cp_api_v1_` credential with
  `adminPass.py --api 1 --api-token '<key>'`.

## v3.0.4 (build 4) — 2026-08-23

Reliability release for installation, upgrades, remote databases, SSL,
WordPress, file management, and native webmail.

### Platform support
- AlmaLinux 10 fresh installations and upgrades now use native EL10
  repositories and a matched OpenLiteSpeed ABI set: OpenLiteSpeed 2.5.2,
  `cyberpanel_ols.so` 2.7.6, and `mod_security.so` 2.5.2.
- The installer provisions the EL10 `udns`, Postfix, MariaDB, Remi, EPEL, and
  LiteSpeed dependencies without relying on EL9 packages or removed DNF
  modularity commands.
- Existing Ubuntu, EL8, EL9, and openEuler artifact selections are unchanged.

### Installation and upgrades
- Remote MySQL installations now configure every database consumer for the
  selected host and port, validate the endpoint before package setup, fail
  early when the CyberPanel database cannot be prepared, and keep database
  passwords out of installation logs and process arguments.
- Remote database settings, the Django secret, and other private configuration
  survive upgrades. Upgrade helpers load only after the new source is staged,
  preserving compatibility with older installed launchers.
- Interrupted upgrades report partial state safely, deployed firewall assets
  are validated, and unavailable legacy PHP development packages are skipped.

### Mail and webmail
- CyberPanel's integrated webmail is now the supported mail interface. Fresh
  installations no longer provision the retired RainLoop or SnappyMail clients;
  upgrades preserve and protect existing legacy data without exposing it.
- Postfix domain lookups work with MariaDB 11.8, and Dovecot 2.4 local delivery
  can read its protected SQL configuration without weakening file permissions.
- Generated Sieve redirect rules are valid and mailbox delivery was verified
  end to end through the integrated client.

### Websites and files
- WordPress can be installed on an existing website, uses an available PHP CLI,
  avoids an unnecessary PHP restart, and is registered correctly in WordPress
  Manager.
- phpMyAdmin auto-login now validates a short-lived, one-time handoff from the
  authenticated panel session instead of relying on an unrelated PHP session.
- File Manager downloads preserve filenames containing spaces, `#`, `&`, `+`,
  or `%` while retaining path traversal protection (#1902).
- Plugin routes and OpenSSH authorized-key deletion now match only the intended
  entry.

### SSL and security
- SSL renewal is reported as successful only after the renewed certificate is
  deployed. ACME account state is preserved, private keys retain owner-only
  permissions, and sensitive ACME response metadata is not logged.
- Strong database-account passwords containing shell, SQL, whitespace, and
  environment-file metacharacters are handled without interpolation.

## v3.0.3 (build 3) — 2026-08-20

Security hotfix for API authentication and account authorization.

### Security
- Placeholder and empty API tokens are rejected across all token-authenticated
  endpoints. API-created accounts now receive cryptographically random tokens,
  and upgrade rotates invalid tokens on enabled accounts.
- Cloud session access now uses uniform authentication failures, rejects
  suspended accounts, rate-limits failed attempts, rotates the session key, and
  prevents credentials from being forwarded in referrer headers.
- API-created site owners and user-management flows now evaluate the effective
  ACL configuration, preventing non-administrators from assigning an
  administrator-level custom ACL. Existing custom ACL records are synchronized
  during upgrade.
- Debug logging for website-creation API calls no longer records request
  payloads containing account credentials.

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
- Incremental backups exclude per-site logs and retain the correct Restic
  snapshot identifier even when the backup command ends with a warning.
- V2 local backups use their on-disk Rustic repository directly and remain
  available without a configured Rclone remote.
- V2 database restores use the valid MySQL defaults-file option and report
  failed database or file imports instead of returning false success.
- Full site archives omit local incremental repository directories to prevent
  nested backup growth.

### Security and reliability
- Backup restores reject archive path traversal, escaping links, and special
  filesystem entries before extracting any content.
- V2 backup diagnostics no longer record repository tokens or database
  passwords.
- Child-domain deletion now invokes certificate cleanup correctly and removes
  the dedicated certificate and ACME state directories.
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
- At the time of this release, AlmaLinux/Rocky/RHEL 10 selected the `rhel9`
  artifact. CyberPanel 3.0.4 supersedes this with a native EL10 ABI set.

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
