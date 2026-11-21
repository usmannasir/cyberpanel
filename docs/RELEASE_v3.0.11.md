# CyberPanel v3.0.11 (build 11) — Multi-Server Manager

_Release candidate, 2026-11-22._

This release adds Multi-Server Manager: one CyberPanel server, the controller,
manages other CyberPanel servers from its own panel. It is a separately
licensed add-on for the controller and is off on every server until an
administrator turns it on. The release also lets an upgrade on Python 3.6 keep
cookie options that an administrator set by hand. The changes are listed in
CHANGELOG.md.

## Release gates

- Run the Multi-Server Manager tests on Ubuntu and on an RPM system with
  Python 3.6, and the launcher and upgrader suites against the same suites on
  the published v3.0.10 tree; no test may fail that passed there.
- Install the candidate on clean servers and upgrade servers installed from the
  published v3.0.10 tree, on Ubuntu and on RPM systems including Python 3.6.
  After each: the role is off, the key directory is root-owned, the panel
  answers, and nothing under /multiserver/ answers except the role page for a
  full administrator.
- Between two real servers, in a browser, in both directions: give each server
  its role, pair them, refuse a wrong number, approve the right one, open the
  managed server from the controller, create a website there from the
  controller's create page, see it in the combined list, pause, resume and
  revoke from the controller, end a link on the managed server, pair again.
- With the licence withdrawn on the licence server the controller offers no
  server and no list within a minute, and still pauses, revokes and forgets.
- The licence server answers `multi-server` only from its own purchases before
  this release is published: the Add-ons package, AppSumo licences and partner
  addresses do not grant it.
- Apply the [OpenLiteSpeed upgrade release gate](../CONTRIBUTING.md#openlitespeed-upgrade-release-gate):
  this release changes the installer and the upgrader.

## Publish checklist

1. Publish the tested candidate as v3.0.11 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 11, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
