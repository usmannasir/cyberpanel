# Changelog

All notable changes to CyberPanel are documented here. The canonical,
continuously updated changelog also lives at
https://cyberpanel.net/KnowledgeBase/home/change-logs/

## v3.0.21 (build 21) — 2026-11-25

Upgrades from releases older than 3.0.8 no longer stop at the mail check, and
mail that those releases had stopped runs again after the upgrade.

### Upgrade
- Releases before 3.0.8 added a mail TLS block to `/etc/dovecot/dovecot.conf`
  for every new website, also when the website had no certificate yet.
  Dovecot cannot load such a file: on 2.x servers mail stopped at once, on
  3.0.0–3.0.7 at the next restart, and the upgrade command refused to start
  with "the running Dovecot configuration cannot be reloaded" (seen upgrading
  2.4.8 and the CyberPanel 3.0.5 Cloud VPS image). The upgrade now removes
  those blocks, and only blocks exactly as CyberPanel wrote them whose
  certificate or key file is missing, keeps the previous file as
  `dovecot.conf.cyberpanel-<time>.before-tls-repair`, and continues. Mail that
  had stopped for that reason runs again after the upgrade. Any other error
  in the mail configuration still stops the upgrade, as before.

### Tests
- The OpenLiteSpeed controller test
  `test_grant_binds_the_command_symlink_and_not_only_its_old_target` no longer
  fails at random on Ubuntu 22.04 (a re-created link could get the same inode
  and change time as the one it replaced).
- The upgrade service-health tests run on Python 3.6 again (on AlmaLinux 8
  they had all errored before running).

### When the changes apply
- The repair is part of the upgrade command (`preUpgrade.sh`), the way the
  upgrade guide tells servers older than 3.0.9 to upgrade. An upgrade started
  from the panel page or by automatic updates does not run it; such an
  upgrade never stopped for this reason.

### Fixed later in build 21 (2026-11-25)
These fixes were added to the 3.0.21 branch after its release, without a new
version number. New installs and the upgrade command get them; a server that
is already on 3.0.21 gets them by running the upgrade command again.

- Dashboard, Recent SSH Logins: on Ubuntu 26.04 (which has no `last` command)
  the card showed one row "sudo: / command / N/A", the text of the error. It
  now shows the SSH daemon's accepted logins from the journal there, and never
  shows error text as a login.
- Dashboard, Recent SSH Logs: on Ubuntu 26.04 the first word of every line
  was lost (so "Failed password" and "Accepted password" looked the same), and
  the panel's own sudo commands filled the list. It now reads both date
  formats and shows the SSH daemon's lines only.
- Dashboard, Disk IO: each disk was counted together with its partitions and
  the CD-ROM drive, about twice the real figure. Each disk now counts once.
- Dashboard: a user's server card no longer shows made-up hardware (2 cores,
  4 GB, 100 GB) when its figures cannot be read.
- Changing a website's SSH/SFTP password, starting, stopping or reloading the
  firewall, and the service start/stop/restart buttons said "done" also when
  the command failed: the panel's privileged helper reports the same result
  for every command that ends, successful or not. These actions now ask the
  command for its real exit status (`ProcessUtilities.checkedExecutioner`).
- Email debugger: the mail server SSL check said a certificate was valid when
  it was self-signed (OpenSSL 3 writes "self-signed", which the check did not
  recognise) or when the connection failed. It now trusts only OpenSSL's own
  "Verify return code: 0 (ok)".
- New installs write OpenLiteSpeed's error log at NOTICE level and keep 14
  days, instead of DEBUG.

### Fixed later in build 21 (2026-11-26)
Preparation for reporting every command's real exit status (next release):
the flows below now say which exit statuses are their normal end, so they
keep working once failures are no longer hidden. Where the panel already sees
real exit statuses (scheduled jobs run as root) the fixes apply now.

- `ProcessUtilities.outputExecutioner(..., retRequired=True, okStatuses=...)`:
  the exit statuses that count as success.
- WordPress backups copy the site with one `rsync -a` as the site user, hidden
  files included. The old `cp` of `path.[^.]*` failed on a site without any
  hidden file (scheduled backups failed there), and a site path without a
  trailing slash was copied into a nested folder. A file that vanished during
  the copy (rsync 24) is normal; a full disk is not.
- Staging "deploy to production": a live site that changes while it is
  archived (tar 1) and a cache file that vanishes during the content copy
  (rsync 24) no longer stop the deploy. wp-config.php one folder above the
  WordPress root is accepted, as WordPress does. A failure names the program,
  not "sudo". The one-deploy-per-site lock is now held by the deploying
  process, so a worker that died cannot leave a lock that blocks every later
  deploy.
- Fix Permissions: a folder its owner cannot enter, or a cache file removed
  during the walk, no longer stops the repair (find/chown 1, logged); a child
  domain whose folder was removed is skipped.
- Website resource usage: files that vanish during the disk scan (du 1) no
  longer make disk usage "unavailable"; the total line is read even after du's
  warnings.
- Remote backup restore progress: a poll that comes before the restore has
  written its log shows "Starting the restore..." and keeps polling.
- n8n PostgreSQL setup: one broken package source (`apt-get update` 100) or
  no EPEL no longer stops it; an initialised data directory is not
  initialised again; on AlmaLinux "which: no psql in (...)" no longer counts
  as installed (nor "which: no apt-get" as an apt system); "inactive" no
  longer counts as running.
- Docker sites: a stopped Docker service is reported as "Docker service is
  not running", not as a failed check.

Upgrade:

- An upgrade no longer stops at the OpenLiteSpeed check because a website's
  own `vhost.conf` leaves a block open at the end of the file
  (`[PlainConf] [context:/] parseFile find '{' and '}' do not match in the end
  of file .../vhosts/<website>/vhost.conf, rootTag virtualHostConfig.`; seen
  with "Custom OLS configuration failed validation" from the terminal command
  and "Upgrade exited with code 78 ... OpenLiteSpeed configuration validation
  failed" from the panel page). OpenLiteSpeed runs with such a file and serves
  every other website, so the upgrade now lists the files, says how to correct
  them and continues, as it has done since 3.0.10 for a stray closing brace or
  a PHP version that is no longer installed. The upgrade does not edit these
  files. Still refused: the same message for the server's own configuration,
  and a website that was clean when the upgrade began and has the error later.

Also fixed:

- AlmaLinux 8, 9 and 10: a fresh install left `/usr/local/lsws/lsphp86` with
  PHP 8.6's development and MySQL packages but without PHP 8.6 itself, since
  LiteSpeed's repositories carry PHP 8.6. The timezone step's
  `lsphp??-devel lsphp??-mysqlnd` named every version in the repository; it
  now installs those packages for the installed versions only. On a server
  installed before, `dnf install -y lsphp86` completes PHP 8.6.
- Creating a website or a child domain on the command line
  (`cyberpanel createWebsite`/`createChild --php`) or from the panel's pages
  refuses a PHP version that is not installed ("PHP 8.6 is not installed on
  this server."). Before, such a website was created without a working PHP.

## v3.0.20 (build 20) — 2026-11-25

Upgrades started from the panel (Version Management → Upgrade) finish like a
command-line upgrade, stop when they hang, and say which steps did not
complete.

### Upgrade from the panel page
- A page upgrade now installs the release's Python packages and its panel
  server (lscpd), as the command-line upgrade does. x86 servers installed before
  20 Oct 2026 and upgraded only from the page kept lscpd 0.3.1, which ends
  large phpMyAdmin exports early; they get the current server with this
  upgrade. Packages are installed only when the panel lacks one, and the
  server binary is replaced only when it differs; the panel is restarted on
  the new binary at once, and the previous one is put back if the panel does
  not answer.
- phpMyAdmin is no longer removed before its new copy is in place. An upgrade
  that could not reach GitHub used to leave the panel without phpMyAdmin; it
  now uses the copy in the release itself and replaces the installed one only
  with a complete copy.
- Steps that fail without stopping the upgrade are listed at the end of the
  upgrade log, on the Version Management page and in the automatic-update
  report, instead of a plain "upgrade completed".
- A run that writes nothing for 30 minutes is stopped (4 hours at most), with
  everything it started, and handled like a failed upgrade: the previous
  installation is put back if it was already replaced, and the staging
  directory is removed. After 5 minutes without output the page offers a
  Stop button.
- When GitHub cannot be reached, the upgrade asks three times and then says
  so and that nothing was changed, instead of showing git's error; a download
  that slows below 1 KB/s for a minute gives up instead of waiting forever.
- An upgrade no longer refuses with "An unmanaged OLS process is also
  running" when OpenLiteSpeed is restarted (for example by a panel action)
  during the two seconds the upgrade's stop of OpenLiteSpeed takes, or when
  processes of an earlier OpenLiteSpeed generation are still ending. The
  upgrade stops the restarted instance once more, or waits for and ends the
  earlier generation, as it already did while that generation's main process
  was running.

### Multi-Server Manager
- An empty Managed servers list now says to follow the two steps of Add a
  server (it still said four after 3.0.19).

### When the changes apply
- The page runs the upgrade code of the release it installs, so an upgrade to
  3.0.20 from 3.0.9 or later already gets the packages, the panel server,
  phpMyAdmin and the OpenLiteSpeed fixes. The time limit, the Stop button,
  the GitHub message and the list of incomplete steps on the page and in the
  automatic-update report belong to the installed panel and work from the
  first upgrade after 3.0.20.

## v3.0.19 (build 19) — 2026-11-25

Multi-Server Manager: connecting a server takes three steps.

### Multi-Server Manager
- A server is connected to a controller from its own Multi-Server page in
  one form, "Connect this server to a controller": the controller's address
  and the password. The server becomes a managed server and shows a pairing
  code. Pasted on the controller (Managed servers, Add a server), the two
  servers are connected at once: there is no eight-digit number to type back
  on the managed server and no "check now" to press. The code works once,
  for ten minutes, only from the controller address that was entered, and
  only while the administrator who made it is still a full administrator.
- Two-factor login is needed only to make a server a controller, because a
  controller opens the panels of all its servers. A managed server asks for
  the password, and a code only from an account that has two-factor login.
- After a sign-in or a confirmation, the same browser session is not asked
  for the password again for 15 minutes. A confirmation without a code never
  counts where a code is needed, and a new password or two-factor key ends it.
- The role page shows the two ways to start side by side, the controller's
  page shows the address to enter on the other servers, and a server added
  without a name is named after its address.
- Mixed versions keep working: a 3.0.19 controller still shows the number
  for a managed server of 3.0.18 or older, and a 3.0.18 controller connects
  a 3.0.19 server with one "I approved it, check now". Links that were
  waiting for a number before the upgrade can still be approved with it.

## v3.0.18 (build 18) — 2026-11-24

Upgrade reliability on servers that keep the vendor OpenLiteSpeed, and a
simpler Multi-Server Manager set-up.

### Upgrade
- An upgrade no longer stops with "OpenLiteSpeed configuration failed
  validation" and "Failed to load module [cyberpanel_ols] ...
  cyberpanel_ols.so: cannot open shared object file". Earlier versions
  declared the CyberPanel OpenLiteSpeed module in httpd_config.conf also
  where they did not install it: fresh installs on systems without a
  CyberPanel OpenLiteSpeed build (ARM servers, Ubuntu before 22.04, systems
  the installer did not recognise) and upgrades from November 2025 to
  November 2026 whose download failed. OpenLiteSpeed served websites
  normally, but every upgrade since 3.0.8 stopped there. The upgrade now
  recognises exactly that state. Where a CyberPanel OpenLiteSpeed build
  exists for the system it installs the module, so the declaration becomes
  valid; elsewhere it removes only that declaration, keeps a copy of the
  previous file beside it, tests the configuration and puts the previous
  file back if the test fails. The terminal upgrade, the panel's upgrade
  page and automatic updates decide the same way. Any other configuration
  error still stops the upgrade before it changes anything.

### Installer
- A fresh install that keeps the vendor OpenLiteSpeed no longer declares
  the CyberPanel module, and the module is declared only beside the
  CyberPanel OpenLiteSpeed core and module.

### Multi-Server Manager
- Two-factor login can be set up on the role page itself: an account
  without it presses Set up two-factor login, scans the QR code (drawn on
  the server, so it works offline) or types the key, and saves the role with
  the app's code and the password. No sign-out is needed afterwards:
  changing the role counts as a sign-in with password and code, and where
  Managed servers still needs that it asks for them in place.
- The role page no longer offers to buy a licence once the server has one.
- New page design for the role, Managed servers, Controllers and Add a
  server pages, using the panel's theme colours in light and dark mode.

## v3.0.17 (build 17) — 2026-11-24

Upgrade reliability and Multi-Server Manager wording.

### Upgrade
- An upgrade no longer stops with "An unmanaged OLS process is also
  running" (code 78) on a busy server. A graceful restart or reload of
  OpenLiteSpeed starts a new main process, and the previous one keeps
  running until its open connections end; `systemctl stop lshttpd` does not
  stop it, so every retry stopped again, including right after the
  upgrade's own configuration reload. The upgrade now gives such a previous
  generation 60 seconds to finish, then ends exactly those processes and
  names them in its log. Any other unexpected OpenLiteSpeed process still
  stops the upgrade before it changes anything.

### Multi-Server Manager
- The controller's page is called Managed servers and shows the four steps
  to add a server, each server's status in plain words with what to do next,
  and actions named by what they do (Pause, Remove this server, Delete from
  this list only). The role page has a getting-started list, and the
  pairing and managed-server pages use the same names. Nothing about how
  pairing works changed.

## v3.0.16 (build 16) — 2026-11-23

Installer, upgrade and File Manager reliability release.

### File Manager
- A delete in the File Manager no longer makes the website's whole home
  immutable. From 3.0.9 every delete did, and uploads by FTP and by the
  File Manager, and the website's own writes, then failed with "Operation
  not permitted" (GitHub issue 2018).
- The upgrade unlocks every website home whose folder is immutable, which
  is what that delete left, without following links. Homes whose folder is
  not immutable, including files an owner protected with chattr, are left
  as they are.

### Upgrade
- On AlmaLinux, Rocky and other RPM systems the upgrade no longer leaves
  the server without the Remi repository. Removing and installing EPEL
  again removed Remi with it at every upgrade, and `dnf update` then failed
  for LiteSpeed PHP packages that need libicu78 from Remi. On 9 and 10 the
  upgrade installs Remi again also where an earlier upgrade removed it.

### Installer
- The installer waits while another apt process holds a package lock
  (the daily apt update or unattended upgrades on a new server) instead of
  failing at once. Before, an installation on Ubuntu could end with exit 71
  at "systemctl enable pdns" when the daily apt update started during the
  PowerDNS step. It waits at most 30 minutes and says once a minute which
  lock it is waiting for; `cyberpanel.sh` waits the same way before its own
  `apt` and `apt-get` commands.

## v3.0.15 (build 15) — 2026-11-23

Installer and first-administrator release.

### Panel sign-in
- The sign-in page never creates an administrator with a known password. A
  panel that has no administrator gets "admin" with a generated password of
  20 letters and digits, made once under a lock by
  `adminPass.py --first-administrator` and stored for root only in
  `/etc/cyberpanel/adminPass`. Until "admin" signs in, the page says that the
  password was generated and where it is stored; if no administrator could be
  made, the page says to run `adminPass` on the server.

### Installer
- An installation is reported complete only when the panel's service is set
  to start at boot; otherwise it ends as failed (`panel_setup`) with the
  command that sets it.
- A run that fails after the administrator's password was confirmed says
  that the panel is stopped and which two commands start it.
- `cyberpanel.sh` enables the panel's service itself, after the password
  check, and tells `install.py` to leave the service alone; other callers of
  `install.py` behave as before.
- `-v <serial> -v ols` installs OpenLiteSpeed without passing the earlier
  serial number on to `install.py`.

## v3.0.14 (build 14) — 2026-11-23

Reliability release. It corrects the eleven Medium and Low defects found in
acceptance testing of 3.0.11 and the defects of the same kind found beside
them.

### Users
- The two-factor set-up shows the key for typing by hand next to the QR
  code. The secret is sent only while two-factor is being set up for an
  account that does not have it yet; an enrolled account's secret is never
  sent to the browser, and loading an account no longer creates one.
- Two-factor is switched on only with a code from the authenticator app, for
  a secret issued fresh by that set-up.
- Saving a user leaves two-factor as it is unless the request changes it;
  `cyberpanel editUser`, the cloud API and a page left open no longer
  switch it off.
- The Reseller Center saves a website limit when the current owner is kept,
  refuses an unknown owner, and checks a limit sent as text like any other.
- A reseller with a website limit cannot give out unlimited websites, change
  its own limit or owner, or make a user its own owner; a user moved to a
  new owner counts against that owner's allowance as it should.

### Websites and applications
- After an FTP account is created the page shows the user name that was
  stored.
- An SRV record takes weight, port and target beside its own priority; the
  form's example says so and a record that cannot be served is refused.
- WordPress and Docker site deployment show their real progress up to 100%.
- Cloning a website reports success only when the copy works; a failed clone
  says why and removes what it created. The copy runs as the website's user
  after the site's permissions are repaired, the recorded WordPress folder is
  checked first, and the database dump is private and no longer lands in the
  new site's folder.
- Each application installer shows only its own progress; the PrestaShop
  installer names the page where a website is switched to Apache and refuses
  before it changes anything. The Visit links after an installation open the
  website itself.

### Services and pages
- Redis and Elasticsearch are shown as installed only when the program is
  there and its service runs; a busy package manager is reported as such.
  A SpamAssassin installation that failed is reported as failed.
- Links to the guides point to their current addresses.
- The AI Scanner says that an account must be connected before a scan and
  where to connect it, and why a scan was refused.

## v3.0.13 (build 13) — 2026-11-22

Reliability release. It corrects nine defects found in acceptance testing of
3.0.11: certificates on servers with more than one website, website
suspension, the Create ACL page, mail in incremental backups, the Backup V2
pages, WordPress restore to a new site, the Web Terminal service, pattern
forwarding of mail and websites on the Apache backend. Upgrading is
recommended for every server. A fresh installation now reports its steps and
its result, and installs only the components it is asked for.

### Certificates
- A website with a certificate is mapped on the IPv4 and on the IPv6 HTTPS
  listener and carries its own certificate. Before, the first website to get
  a certificate was mapped on IPv4 only and the second on IPv6 only, so each
  could be answered with the other's certificate. The DNS-validated route
  follows the same rule.
- An upgrade completes the listener maps of websites that already have a
  certificate that is in date and names the website. Listeners on other
  ports or on a single address are left as they are, and a website whose
  file cannot be changed is named in the upgrade log and skipped.
- A website that is created again after it was deleted is created over the
  self-signed certificate its predecessor left, as a first creation would
  be. Before, the creation failed when no public certificate could be
  issued.

### Websites
- A website is suspended and restored on a server whose OpenLiteSpeed
  configuration test already reports warnings or an error in another
  website. The change is refused, and undone, only when it adds an error.
  The same holds for a child domain created under a suspended website and
  for a child domain's state restored from a backup. Restoring a suspended
  website is undone only for damage (a fatal error, a web server that does
  not restart), not for an error its own configuration brings back.
- A website on the Apache backend is written only for a system user that
  exists. Apache's own configuration test runs before and after the change,
  a refused change is undone and reported, and Apache is not restarted into
  a configuration it refuses. Switching a website to Apache keeps its
  OpenLiteSpeed configuration until Apache runs with the new one. The Apache
  configuration editor and the PHP version change follow the same rule.
- The system user of a new website is named in lower case.
- An upgrade closes a virtual host of the panel that names a missing system
  user (it answers 403) and sets its PHP-FPM pool aside, so that the other
  websites on Apache answer again. Once the user exists, changing the
  website's PHP version opens it again. Files the panel did not write are
  reported and left alone.
- The OpenLiteSpeed proxy backends for Apache are defined once and on the
  right ports; duplicate definitions of earlier releases are removed.
- A backup whose website user name this system does not accept is restored
  under a new name.

### Users
- The Create ACL page shows a checkbox for every permission it saves,
  including the backup, SSL and AI Scanner permissions. The panel grants
  only what the request names; a permission that is not sent is not granted.
  Stored ACLs are not changed by the upgrade: open an ACL made on the earlier
  page in Modify ACL to review its backup and SSL permissions.
- A permission is sent as true or false (1, 0 and the words are accepted). A
  request with any other value is refused and nothing is stored.

### Backups
- An incremental backup with emails selected stores the website's mail, read
  by the mail user and stored by the website's user. It says so when the
  website has no mail folder, and fails when the mail cannot be read in
  full. Restoring mail checks the whole archive first, writes inside the
  website's mail folder only, with private permissions, and leaves Dovecot's
  index files of a mailbox in use as they are. Restore points of mail made
  by earlier releases hold no mail.
- Backup V2 stores and restores mail the same way; nothing runs as root on a
  website's own storage settings. Mail in Backup V2 snapshots of earlier
  releases is not restored by the panel: take a new backup.
- A mail folder that is a link to another location fails the mail step with
  the link named; mount the location at that path instead.
- A Backup V2 job no longer ends as successful after a step that failed.
- A restore stops at a step that failed, and a backup fails when its
  metadata could not be stored.
- The Backup V2 create, restore, schedule and repository pages, the
  incremental backup schedule and remote restore pages, and the email
  marketing and container limit pages load the script they need.

### WordPress
- Restoring a WordPress backup to a new site produces a working copy with
  its own database, or reports why not and removes the website it created.
  The new site starts from the current WordPress release. A DNS zone, mail
  folder or certificate folder that existed before the job is kept when the
  website is removed again. Multisite backups and backups that fix the site
  address in wp-config.php are refused before anything is created.
- A backup is never unpacked as root, and a restore into an existing website
  keeps that website's own database settings even when it stops half way.
- Restore steps see the real result of a copy or a database import; a
  failed step is reported instead of "Completed".
- A failed WordPress deployment to a new domain removes the website it
  created and the files it added.

### Mail
- A pattern forwarding rule reaches Postfix: the panel writes the map
  through its root helper and Postfix reads it after exact forwardings and
  mailboxes and before the catch-all. A rule is refused when the map cannot
  be written. Patterns match addresses of their own domain only and are
  limited in length and repetition; a domain holds up to 20 rules. A rule
  the mail server cannot use is left out and marked on the page. Rules of a
  deleted website or mail domain leave the map with it. An upgrade puts
  rules saved by earlier releases into use.

### Installation
- A fresh installation records each of its steps, and how it ended, in
  /var/log/cyberpanel/install_events.log (readable by root only).
- An installation that fails ends with a failing exit status and a reason;
  before, several failure paths ended with status 0. A server that already
  has the panel is recognised before any service is stopped. A panel that
  does not answer on port 8090 within about three minutes of the end of the
  installation counts as a failed installation.
- `-m` installs only the components it names (postfix, powerdns, pureftpd);
  before, `-m postfix` installed all three. Sieve and Dovecot are installed
  with the mail server only. A word the installer does not know, such as
  `nopostfix`, is now refused instead of ignored.
- The administrator password can be given in a file only root can read
  (CP_ADMIN_PASSWORD_FILE); it is not echoed or written to a log, and a
  password given with `-p` is masked in the installer's logs.
- When the hostname certificate cannot be issued the installer says how the
  panel is reached and records a warning.
- The panel is enabled and started only once the administrator's password
  has been set and confirmed, also when an older release is installed with
  `-b`. An installation that fails or is interrupted before that leaves the
  panel disabled, so that it cannot come up with a well-known password; the
  `adminPass` command sets a password and starts it.
- The values of `-p`, `-b` and `-v` are checked before anything on the
  server is changed, `--help` is answered wherever it stands, and an
  installation ended by a signal is recorded as interrupted.

### Web Terminal
- The Web Terminal service is started once its interpreter exists, at the
  end of an installation. An upgrade starts an enabled service that failed
  because its program could not be executed; a service that failed for
  another reason, or is stopped, disabled or masked, is left as it is and
  named in the upgrade output.

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
