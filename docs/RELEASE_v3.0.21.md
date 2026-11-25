# CyberPanel v3.0.21 (build 21) — upgrades from older releases

_Released 2026-11-25._

The upgrade command no longer stops on servers where a release older than
3.0.8 left mail TLS settings for websites without a certificate, and mail that
those settings had stopped runs again. A flaky controller test is now
deterministic. The changes are listed in CHANGELOG.md.

## Release gates

- Real upgrades with the upgrade guide's command, verbatim, from releases
  installed by their own installers: 2.4.4 on Ubuntu 22.04, AlmaLinux 9 and
  AlmaLinux 8, 2.4.8 on Ubuntu 24.04, and the CyberPanel 3.0.5 (Ubuntu 26.04)
  Cloud VPS image; a website without SSL created on each before the upgrade.
- The mail repair against real Dovecot 2.3 and 2.4 configurations: running
  mail stays up, failed mail comes back, other configuration errors still
  stop the upgrade with the file unchanged.
- The controller test 2000 times on Ubuntu 22.04 (it failed 241 of 300 runs
  on the published 3.0.20 tree there).
- Run the whole test collection against the published v3.0.20 tree on
  Ubuntu 22.04, AlmaLinux 9 and AlmaLinux 8 (Python 3.6); no test may fail
  that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.21 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 21, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
