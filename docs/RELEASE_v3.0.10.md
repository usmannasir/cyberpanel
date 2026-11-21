# CyberPanel v3.0.10 (build 10) — Automatic Updates

_Release candidate prepared 2026-11-21._

This release adds automatic updates. A server on which an administrator turns
the feature on installs a new release by itself, and only a release named in a
file signed by CyberPanel. The changes are listed in CHANGELOG.md.

## Release gates

- Run the whole panel test collection and compare it with the same collection
  on the published v3.0.9 tree; no test may fail that passed there.
- Install the candidate on clean servers and upgrade servers installed from the
  published v3.0.9 tree, on Ubuntu and on an RPM system including Python 3.6.
- On each, with a release file signed for the candidate: notify mode sends one
  message and installs nothing; install mode installs exactly the signed commit
  at the chosen hour, also when the branch holds a later commit; a file signed
  by another key, an older file and a paused release install nothing; a failed
  installation puts the previous version back and is not repeated.
- Apply the [OpenLiteSpeed upgrade release gate](../CONTRIBUTING.md#openlitespeed-upgrade-release-gate):
  this release changes the upgrader.

## Publish checklist

1. Publish the tested candidate as v3.0.10 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Set https://cyberpanel.net/version.txt to exactly
   {"version":"3.0","build":10}.
4. Install and upgrade through the public default path on owned servers and
   repeat the browser, endpoint, service and exit-status checks.
5. Only then sign the release file for the release commit and publish it at
   https://cyberpanel.net/release.json. Signing is what allows servers to
   install the release with nobody watching.
6. Publish the build 10 public changelog entry.

If public installation or upgrade fails, restore the live pointer to build 9,
do not sign, and retain v3.0.10 for diagnosis. If a signed release has to be
stopped, publish the same release file marked as paused.

## Important boundary

The signing keys are not in this repository. A release that is not signed is
never installed automatically; it can still be installed from the page and
from the command line as before.
