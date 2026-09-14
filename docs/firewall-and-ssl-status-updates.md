# Firewall preservation and certificate validity

## CSF upgrade guard

CyberPanel upgrades now stop with a nonzero exit status when `/etc/csf` exists
(including a symlink). The shell wrapper checks before clearing logs or preparing
an upgrade. The direct Python command checks before loading database recovery
code; its lightweight guard is staged alongside the downloaded upgrade script.
Both upgrade entry points reject the same condition before changing files. The panel and cloud submission endpoints reject the request before launching
a worker. The cloud worker also reports failure before backup or rollback,
and its command-line wrapper propagates a nonzero exit. This protects the firewall
policy and the installed CSF panel integration, which a clean panel replacement otherwise removes.

The legacy `removeCSF` command refuses automatic removal, reports that no firewall
changes were made, and exits nonzero. Its internal method retains the existing
convention of `0` for failure. The inactive web removal handler returns
`installStatus: 0` with the same actionable error; its route remains disabled.
No replacement firewall is installed, started, unmasked, enabled, or flushed.
Servers without CSF continue through the existing upgrade path.

Before upgrading a server that has CSF, arrange a reviewed manual firewall
migration with provider-console access and a recovery plan. Preserve the complete
CSF configuration and policy, including allow/deny entries, inbound and outbound
rules, custom SSH/panel ports, IPv4/IPv6 behavior, and custom rules. Verify the
replacement policy and remote access before removing CSF. Merely renaming or
deleting `/etc/csf` to bypass the check is not a migration.

This update prevents a future destructive conversion. It does not restore a
firewall already removed by an older upgrade. Such a server needs an assessment
of its actual packages, service state, rules, access ports and console access;
do not apply a generic firewall restart or empty replacement policy.

## Manage SSL validity

The SSL details API retains `hasSSL` to indicate a parsed certificate and adds
`validityStatus`: `valid`, `expired`, or `not_yet_valid`. Status compares the
current UTC time with both certificate validity timestamps; it does not infer
validity from rounded remaining days. A certificate at its expiry time is
expired; one with less than one day remaining can still be active. Both Manage
SSL interfaces show the corresponding label and reserve success styling for
currently valid dates.

This status describes certificate dates, not browser trust, hostname matching,
CDN certificates, renewal success, or which certificate a public service serves.
The update does not issue certificates or change renewal configuration. Issuers
without an organization attribute fall back to their common name or `Unknown`.

## Verification

Run the focused CSF migration and SSL details regressions with isolated settings,
alongside the existing upgrade runtime/database and SSL navigation, copy, renewal
and ACME tests. Validate the actual shell and Python refusal paths on an owned
server with a disposable CSF sentinel, then verify that firewall configuration,
rules, SSH/panel access and service states are unchanged. Never run a complete
upgrade merely to exercise the no-CSF path on a live server.

Exercise both Manage SSL pages against controlled valid, expired, future,
short-lived, missing and malformed certificate fixtures. Restore the fixture
files and records afterward. Preserve exact-file backups for a targeted deployment.
