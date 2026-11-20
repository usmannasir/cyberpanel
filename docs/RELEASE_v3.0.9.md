# CyberPanel v3.0.9 (build 9) — Security and Reliability

_Release candidate prepared 2026-11-20._

This release carries the fixes published on the v3.0.8 line since 18 October
and a set of hardening changes to request handling, progress pages, website
file operations, Backup V2 and the WordPress tools. The changes are listed in
CHANGELOG.md.

## Release gates

- Run the whole panel test collection and compare it with the same collection
  on the published v3.0.8 tree; no test may fail that passed there.
- Install the candidate on clean servers and upgrade servers installed from the
  published v3.0.8 tree, on Ubuntu and on an RPM system including Python 3.6.
- On each, verify sign-in, website creation, child domains, File Manager save,
  upload and delete, permission repair, per-site SSH keys, the cron page, DKIM
  keys, list-page deletion from the panel and from an outside link, and progress
  pages for a low-privilege user.
- Apply the [OpenLiteSpeed upgrade release gate](../CONTRIBUTING.md#openlitespeed-upgrade-release-gate):
  this release changes the installer and the upgrader.

## Publish checklist

1. Publish the tested candidate as v3.0.9 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Set https://cyberpanel.net/version.txt to exactly
   {"version":"3.0","build":9}.
4. Install and upgrade through the public default path on owned servers and
   repeat the browser, endpoint, service and exit-status checks.
5. Publish the build 9 public changelog entry.

If public installation or upgrade fails, restore the live pointer to build 8 and
retain v3.0.9 for diagnosis.

## Important boundary

The Backup V2 and WordPress Manager changes sit behind paid add-ons. Record which
of them were exercised on a licensed server and which were covered by unit tests
only. #1924 (ionCube with OPcache) remains open and is not changed here.
