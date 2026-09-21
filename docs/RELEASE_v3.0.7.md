# CyberPanel v3.0.7 (build 7) — Roundcube Add-on and Upgrade Reliability

_Release candidate prepared 2026-09-21._

CyberPanel 3.0.7 adds an optional paid Roundcube integration while keeping the
integrated CyberPanel webmail as the default. It also makes command-line upgrades
show live progress instead of appearing to stop while the Python upgrader runs.

## Changes

- Adds **Email → Roundcube (Paid add-on)** for entitled server administrators.
- Gives existing all-features, lifetime, and enterprise entitlements access
  through the current premium checker; standalone access uses the named
  `roundcube` entitlement.
- Installs the pinned Roundcube 1.7.4 release into an isolated PHP-FPM service
  behind CyberPanel's HTTPS endpoint and a private Unix socket.
- Keeps mailbox credentials, Roundcube sessions, runtime data, logs, and the
  encryption key outside the public web root with restrictive ownership.
- Preserves Roundcube contacts, preferences, database state, and the encryption
  key across disable, re-enable, and install/update operations.
- Fails closed when entitlement lookup fails or access expires, including for an
  already open Roundcube session after the short authorization cache expires.
- Blocks installer, configuration, SQL, arbitrary PHP, and traversal paths at
  the gateway.
- Streams `upgrade.py` output live from `cyberpanel_upgrade.sh` while preserving
  the command's real exit status and upgrade log.

## Validation completed

- 27 Roundcube integration and privileged runtime tests passed on an installed
  disposable CyberPanel server.
- 4 live-output upgrade regression tests passed.
- Browser acceptance passed for licensed installation, invalid and valid mailbox
  login, desktop and 390x844 mobile layouts, contact persistence, disable and
  re-enable, reinstall/update, entitlement revocation, and protected paths.
- Roundcube sent a message with a text attachment, punctuation, Urdu and Arabic
  text to a disposable mailbox. CyberPanel's integrated webmail opened it and
  sent a reply that Roundcube received and displayed.
- Postfix and Dovecot logs confirmed authenticated submission, DKIM signing, and
  delivery in both directions. The integrated `/webmail/` client remained
  independent and operational.
- No new failed systemd units, browser console errors, or page errors were found.

## External-delivery note

The disposable provider blocks direct outbound TCP port 25. A Mail-Tester
message was accepted and DKIM-signed by local Postfix but remained deferred when
the connection to `reception.mail-tester.com:25` timed out. This is a provider
network restriction, not a Roundcube integration failure. Public mail delivery
still requires an allowed outbound path, aligned forward and reverse DNS, and
normal SPF, DKIM, and DMARC configuration.

## Publish checklist

1. Push this exact tested source tree to `v3.0.7` and merge it into `stable`.
2. Set `https://cyberpanel.net/version.txt` to exactly
   `{"version":"3.0","build":7}`.
3. Upgrade the retained validation server through the public updater.
4. Repeat the Roundcube login, send/receive, entitlement, integrated-webmail,
   service-health, and upgrade-output checks.
5. Add the build 7 entry to the public CyberPanel change log.

If public installation or upgrade fails, restore the public pointer to build 6
while preserving the `v3.0.7` branch for diagnosis.
