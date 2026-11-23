# CyberPanel v3.0.14 (build 14) — reliability

_Release candidate._

This release corrects the eleven Medium and Low defects found in acceptance
testing of 3.0.11 (two-factor key, Reseller Center limit, FTP user name, SRV
records, WordPress progress, website clone status, application installer
messages and links, Redis state, guide links, AI Scanner prerequisite) and
the defects of the same kind found beside them. The changes are listed in
CHANGELOG.md.

## Release gates

- On servers installed from the published v3.0.13 tree, on Ubuntu and on an
  RPM system, show each defect, upgrade, and show it gone.
- Run the whole test collection on Ubuntu and on RPM systems, Python 3.6
  included, against the same collection on the published v3.0.13 tree; no
  test may fail that passed there.
- Apply the [OpenLiteSpeed upgrade release gate](../CONTRIBUTING.md#openlitespeed-upgrade-release-gate)
  if this release changes the upgrader.

## Publish checklist

1. Publish the tested candidate as v3.0.14 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 14, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
