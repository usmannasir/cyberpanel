# CyberPanel v3.0.16 (build 16) — installer reliability

_Release candidate._

The installer waits while another apt process holds a package lock instead
of failing at once. The change is listed in CHANGELOG.md.

## Release gates

- On clean Ubuntu servers, with another process taking the package locks
  during the installation the way the daily apt update does: the published
  v3.0.15 installer fails, the candidate completes and says what it waited
  for.
- Install the candidate on clean Ubuntu and RPM servers, Python 3.6
  included; upgrade servers installed from the published v3.0.15 tree.
- Run the installer test collection and the whole test collection against
  the published v3.0.15 tree; no test may fail that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.16 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 16, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
