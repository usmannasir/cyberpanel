# Optional Roundcube add-on

This feature belongs to `feature/roundcube-paid-addon` until browser acceptance
and the feature-release review are complete. Do not merge it into the current
stable release as part of testing.

CyberPanel's integrated `/webmail/` client remains the default. The optional
Roundcube client is available at `https://<panel-host>:<panel-port>/roundcube/`.
Both clients access the existing IMAP mailboxes; Roundcube keeps a separate
address book and preferences. There is no mailbox migration and no SnappyMail
installation. Roundcube itself is GPL software; the paid feature is its
CyberPanel integration and management.

## Pricing and purchase integration

Roundcube integration is included in CyberPanel's **$169 lifetime premium
add-ons plan**, or available as a **$99 one-time standalone lifetime license**.
The paid product covers CyberPanel integration and management of the open-source
Roundcube client.

The management page provides distinct purchase links:

- **$169 lifetime premium plan:** <https://cyberpanel.net/cyberpanel-addons>.
- **$99 standalone Roundcube lifetime license:**
  <https://platform.cyberpersons.com/order/roundcube/>.

License management uses the existing platform account at
<https://platform.cyberpersons.com/>. The standalone order route is owned by the
platform; the existing in-panel premium pricing page uses a platform-managed
Stripe pricing table. Products, payments and fulfillment are outside this
repository.

Before making the standalone offer purchasable, the platform/billing deployment
must provide the $99 one-time Roundcube product and checkout, fulfill successful
purchases as the `roundcube` entitlement for the licensed server IP, and retain
that grant without a recurring subscription expiry. Refunds and revocations
must update that grant through the existing entitlement service. Verify the
$169 lifetime product grants `all`, or explicitly grants `roundcube`, and update
the public plan feature list to include Roundcube. Deploy and verify the
standalone order route before releasing its panel purchase link. These are
external deployment requirements; this panel change creates no billing product,
payment, or license.

## Entitlement and access

The gateway and install/enable operations require an integer `1` from the
existing premium checker for `all` or the new named feature `roundcube`. Existing
all-features/lifetime/enterprise access follows the same checker as other paid
features. Existing recurring all-features access remains supported; the panel
does not infer a billing amount or term from the `all` grant. The platform add-on
service must explicitly grant `roundcube` for a standalone purchase. A standalone
Roundcube purchase must not grant `all` or unlock unrelated premium features.

Positive entitlement results have a maximum 60-second cache lifetime; negative
results expire in 10 seconds. Lookup errors and malformed values fail closed.
After expiry/revocation, fresh requests to both PHP controllers are denied,
including static resources and an already logged-in mailbox. Removing access
can take up to the positive cache lifetime. The service is not exposed on a
public TCP port or a public PHP filesystem route.

Only a CyberPanel server administrator can install, update, enable, disable, or
view runtime status. The management endpoint uses normal Django CSRF protection.
Disable remains available after entitlement expiry and retains contacts,
preferences, and mailbox data. Mailbox users can log in directly to Roundcube
with their email credentials; they do not need a CyberPanel administrator login.

## Prerequisites

Use a supported CyberPanel installation with working local Dovecot (127.0.0.1:143)
and authenticated Postfix submission (127.0.0.1:25), a valid panel HTTPS endpoint,
`systemd`, and the existing `cyberpanel` system user/group and sudo configuration.
Local IMAP and SMTP connections stay on loopback. The installer does not change
Dovecot, Postfix, website PHP handlers, or the default webmail route.

The ready state confirms the Roundcube PHP runtime is running; mailbox login and
delivery still require the mail services to work. Dovecot must start successfully
and provide Postfix's SASL authentication socket. A missing certificate referenced
by any Dovecot `local_name` block can stop the entire mail service, including
loopback IMAP and SMTP authentication. Each configured certificate path must
exist, and its certificate must cover the corresponding mail hostname. Diagnose
login or SMTP connection failures with `systemctl status dovecot postfix`,
`doveconf -n`, and `journalctl -u dovecot -u postfix`; repair the mail-domain
certificate configuration before repeating the browser mail test. Do not weaken
TLS verification or enable unauthenticated relay to work around this failure.
Public delivery also needs the usual matching forward/reverse DNS and mail
authentication records; a successful local round trip does not prove external
deliverability.

The isolated service requires system PHP **8.1 through 8.5**, both CLI and FPM,
with ctype, DOM, fileinfo, filter, iconv, intl, mbstring, OpenSSL, PDO SQLite,
session, XML and zip. Roundcube 1.7.4's own Composer requirements support this
version range. The current package paths supported are:

- Debian/Ubuntu: `/usr/sbin/php-fpm8.x`, paired with `/usr/bin/php8.x`;
- AlmaLinux/Rocky Linux: `/usr/sbin/php-fpm`, paired with `/usr/bin/php`.

On a disposable Debian/Ubuntu test installation:

```sh
apt-get update
apt-get install php-fpm php-cli php-mbstring php-intl php-xml php-zip php-sqlite3
```

On AlmaLinux/Rocky Linux, select a distribution-supported PHP 8.1–8.5 stream
before adding the equivalent packages:

```sh
dnf install php-fpm php-cli php-mbstring php-intl php-xml php-pecl-zip php-pdo
```

Verify that `php -m` includes `pdo_sqlite`; package names can vary by repository.
The installer fails with an actionable prerequisite message if the runtime is
missing. It does not switch the server's package stream automatically. SELinux
systems must permit the dedicated FPM service to access its private data and
loopback mail services; validate enforcing mode before declaring an OS supported.

## Install and operation

1. Deploy this feature branch to an owned disposable CyberPanel node, preserving
   its `.env`, `secret_key`, installed ownership, and running services.
2. Restart LSCPD to load the new Django routes and middleware.
3. Open **Email → Roundcube (Paid add-on)**, or `/webmail/roundcube`.
4. With an authorized test entitlement, choose **Install / update Roundcube**.
5. Wait for the ready state, then open Roundcube and log in using a disposable
   mailbox. The integrated webmail button remains on the management page.

Installation downloads the **complete Roundcube 1.7.4** release from the official
GitHub release URL and verifies this pinned SHA-256 before extraction:

```
2c6c878f0093f1bf7fb6086781d2dd9269d652c016b86939c157c5f1729139a2
```

Source: <https://roundcube.net/download/> and
<https://github.com/roundcube/roundcubemail/releases/tag/1.7.4>.
Archive extraction rejects traversal, symlinks, hard links, special files and
oversized archives. The web installer is removed. Only `public_html/index.php`
and `public_html/static.php` are routed to PHP; configuration, SQL, installer,
arbitrary PHP paths and filesystem traversal are denied.

The installer creates:

- root-owned releases and the atomic `current` link at
  `/usr/local/CyberPanelRoundcube`;
- dedicated unprivileged system account `cp-roundcube`;
- private runtime state at `/var/lib/cyberpanel-roundcube`;
- configuration and the retained encryption key at `/etc/cyberpanel/roundcube`;
- a private root-owned FPM master log at `/var/log/cyberpanel-roundcube/fpm.log`;
- `cyberpanel-roundcube.service`, an isolated PHP-FPM pool with a Unix socket at
  `/run/cyberpanel-roundcube/php.sock`, accessible only to the panel user.

The PHP-FPM service has a read-only system filesystem with explicit private
state/runtime write paths, no home-directory access, no privilege escalation,
and bounded worker/request/memory limits. No web server listener is added.
The Django gateway strips panel session cookies, authorization and forwarding
headers, uses distinct secure/HttpOnly/SameSite cookies scoped to `/roundcube/`,
and marks responses private/no-store. Roundcube's own session-bound CSRF token
protects its mail forms/AJAX; only the exact Roundcube namespace bypasses Django
CSRF and the panel's incompatible free-text character filter.

Mailbox credentials are supplied to Roundcube over HTTPS and the private Unix
socket. They are not passed through a command line, logged by the integration,
or saved in Django's session. Roundcube uses its own encrypted session store.
The service's encryption key persists across upgrades.

## Upgrade, backup and rollback

Install/update is serialized with an exclusive lock. The gateway is disabled and
the PHP service stopped before database migration. The installer takes a SQLite
backup as the unprivileged runtime identity (including dropping supplementary
groups), verifies it, copies it safely into a root-owned snapshot, and validates
that snapshot again before marking it usable. A backup failure never replaces
the live database. A migration/service failure restores the verified database,
prior release link, PHP-FPM configuration and systemd unit, then starts the
previous service when it was enabled. A fresh failed install remains disabled.
If a failed install already registered the service for startup, rollback removes
that registration when the previous installation was disabled or absent.

The most recent same-version release is retained as `<version>.previous` and
verified pre-update SQLite snapshots are retained as `pre-update-*.sqlite` under
the root-owned release directory. Include those snapshots, the runtime SQLite
database and `/etc/cyberpanel/roundcube/key` in the administrator's private backup
policy. Snapshots can contain contacts and encrypted mail session data.

To temporarily remove access, use **Disable** in the panel. To diagnose:

```sh
systemctl status cyberpanel-roundcube
journalctl -u cyberpanel-roundcube --since '10 minutes ago'
cat /etc/cyberpanel/roundcube/state.json
```

The root FPM master's startup/error log is `/var/log/cyberpanel-roundcube/fpm.log`
(`0700` directory, `0600` file). It is deliberately separate from runtime-owned
paths, and the service sandbox permits this dedicated log directory.
PHP/Roundcube worker error logs are under `/var/lib/cyberpanel-roundcube/logs`; restrict
access because mail-related failures can include private content. The UI only
receives controlled status text. No automatic destructive uninstall is provided.

## Required verification

Run the focused checks with the CyberPanel Python environment or an isolated
Python environment with Django installed:

```sh
python -m unittest webmail.test_roundcube_addon
python -m py_compile webmail/roundcube.py plogical/roundcubeRuntime.py CyberCP/secMiddleware.py
git diff --check
```

The ordinary suite uses real Django requests/responses and a real Unix-socket
FastCGI protocol test, while mocking only external authorization and privileged
service actions. Two additional tests must be run as root on an owned disposable
Linux node to verify actual UID/group/filesystem behavior:

```sh
CYBERPANEL_ROUNDCUBE_ROOT_TESTS=1 python -m unittest webmail.test_roundcube_addon.RuntimePermissionTests
```

Browser acceptance must include all of the following on the actual installed
feature branch, not a mocked HTTP page:

1. Unlicensed admin sees the paid notice; install and direct `/roundcube/` return
   denial. Ordinary panel users cannot perform management operations.
2. Licensed admin installs through the real UI; status becomes ready. Service
   and panel/mail health checks pass; there are no new failed systemd units.
3. Direct mailbox login works through HTTPS. Wrong passwords fail. Roundcube
   folders and INBOX load, contacts can be created, and logout rejects subsequent
   authenticated actions.
4. Send a uniquely identified message from Roundcube to a disposable mailbox and
   receive/open it there. Reply from integrated webmail and receive/open that
   reply in Roundcube. Verify Postfix delivery and Dovecot evidence. Include an
   attachment and a subject/body containing punctuation and non-Latin text.
5. Integrated `/webmail/` still loads, signs in, sends and receives independently.
6. Disable blocks fresh Roundcube requests; re-enable preserves contacts and
   preferences. Re-running install/update preserves those objects and the key.
7. Revoked/expired entitlement blocks an already open session after at most 60s.
   No test override or temporary entitlement remains afterward.
8. Direct installer/config/SQL/traversal paths stay inaccessible; no panel
   cookie reaches PHP; cookies have the expected path/security attributes.
9. Capture page/console/network errors, desktop and narrow-layout results,
   screenshots of ready/login/inbox/received message, and cleanup disposable
   accounts, mailboxes, messages and contacts. Keep credentials out of artifacts.

A local test suite alone is not completion of the requested acceptance gate.
Publish the feature only after the real browser and mail round-trip checks pass.
