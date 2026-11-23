# CyberPanel v3.0.16 (build 16) — installer reliability and File Manager

_Release candidate._

The installer waits while another apt process holds a package lock instead
of failing at once, a delete in the File Manager no longer makes the
website's whole home immutable, the upgrade unlocks the homes that such
a delete locked, and an upgrade on RPM systems keeps (or restores) the Remi
repository. The changes are listed in CHANGELOG.md.

## Release gates

- On clean Ubuntu servers, with another process taking the package locks
  during the installation the way the daily apt update does: the published
  v3.0.15 installer fails, the candidate completes and says what it waited
  for.
- On a server with the published v3.0.15 tree, delete a file in the File
  Manager: the website's home becomes immutable and an upload fails. Upgrade:
  the home is unlocked, an upload works, a file its owner protected outside
  that home stays protected, and a new delete locks nothing.
- On AlmaLinux 9, upgrade from the published v3.0.15 tree: Remi is still
  installed afterwards and dnf can update the LiteSpeed PHP packages; on a
  server whose Remi an earlier upgrade removed, the upgrade installs it.
- Install the candidate on clean Ubuntu and RPM servers, Python 3.6
  included; upgrade servers installed from the published v3.0.15 tree.
- Run the installer test collection and the whole test collection against
  the published v3.0.15 tree; no test may fail that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.16 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 16, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
