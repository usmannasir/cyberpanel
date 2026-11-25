# CyberPanel v3.0.20 (build 20) — upgrades from the panel page

_Released 2026-11-25._

An upgrade started from Version Management now installs the release's Python
packages and panel server like a command-line upgrade, keeps phpMyAdmin when
GitHub cannot be reached, stops a run that hangs, explains a GitHub outage,
lists the steps that did not complete, and no longer refuses when
OpenLiteSpeed is restarted while the upgrade stops it. An empty Multi-Server
Manager server list names the two steps of Add a server. The changes are
listed in CHANGELOG.md.

## Release gates

- Page upgrades from the published v3.0.18 tree through a private source map
  on Ubuntu 22.04, AlmaLinux 9 and AlmaLinux 8: packages and lscpd installed,
  phpMyAdmin kept with GitHub blocked mid-run, the incomplete-steps notice,
  the GitHub message, the Stop button and the 30-minute stop with the
  previous installation put back.
- The OpenLiteSpeed refusal of the 3.0.19 delivery gate reproduced on the
  published v3.0.19 tree on AlmaLinux 9 and Ubuntu 22.04
  (`systemctl restart lsws` during the upgrade's stop), and the candidate
  passing the same race through the panel page.
- The Multi-Server Manager template test ties the number of steps in the
  empty-list hint to the steps Add a server shows.
- Run the whole test collection against the published v3.0.19 tree on
  Ubuntu 22.04, AlmaLinux 9 and AlmaLinux 8 (Python 3.6); no test may fail
  that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.20 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 20, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
