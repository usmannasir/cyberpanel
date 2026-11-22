# CyberPanel v3.0.13 (build 13) — reliability

_Release candidate._

This release corrects nine defects found in acceptance testing of 3.0.11:
certificates on servers with more than one website, website suspension, the
Create ACL page, mail in incremental backups, the Backup V2 pages, WordPress
restore to a new site, the Web Terminal service, pattern forwarding of mail
and websites on the Apache backend. An upgrade completes the HTTPS listener
maps, puts saved pattern forwarding rules into use, starts a Web Terminal
service left in failed state and takes Apache virtual hosts that name a
missing system user out of use. The changes are listed in CHANGELOG.md.

## Release gates

- On servers installed from the published v3.0.12 tree, on Ubuntu and on an
  RPM system, show each defect, upgrade, and show it gone: the certificate
  served per address family for two websites, suspension and restoration of
  a website, a pattern forwarding rule against a catch-all, mail in an
  incremental backup and its restore, the Web Terminal service state.
- On a candidate server, in a browser: Create ACL with every box cleared but
  one stores exactly that permission; the Backup V2 create and restore pages
  list a configured repository; a WordPress backup restored to a new site
  answers 200 with its own database; a website switched to the Apache
  backend answers through Apache, and a website whose system user is missing
  is refused while the other Apache websites keep answering.
- Run the whole test collection on Ubuntu and on an RPM system against the
  same collection on the published v3.0.12 tree; no test may fail that
  passed there.
- Install the candidate on clean servers: the Web Terminal service is active
  after the installation.
- Apply the [OpenLiteSpeed upgrade release gate](../CONTRIBUTING.md#openlitespeed-upgrade-release-gate):
  this release changes the upgrader.

## Publish checklist

1. Publish the tested candidate as v3.0.13 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 13, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
