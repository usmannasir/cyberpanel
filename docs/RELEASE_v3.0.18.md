# CyberPanel v3.0.18 (build 18) — upgrades on servers that keep the vendor OpenLiteSpeed, Multi-Server Manager set-up

_Released 2026-11-24._

An upgrade no longer stops at the OpenLiteSpeed check on a server whose
configuration declares the CyberPanel module that was never installed, and a
fresh install no longer writes that declaration. Multi-Server Manager sets
up two-factor login on its role page and needs no sign-out. The changes are
listed in CHANGELOG.md.

## Release gates

- On a server with the published v3.0.17 tree put in that state with the
  package manager (vendor core, no module file, the declaration present), the
  published upgrade stops with "Failed to load module [cyberpanel_ols]"; the
  candidate upgrade completes through the terminal and through the panel,
  the module is loaded afterwards, and websites, databases and the panel
  stay as they were. Ubuntu 22.04 and AlmaLinux 9.
- Where no CyberPanel OpenLiteSpeed build exists, the candidate upgrade
  removes only the declaration and the configuration test passes afterwards.
- Mixed states (a module file of any kind, another server-wide error, two
  declarations) still stop before any package change.
- Multi-Server Manager: the whole Multi-Server test collection passes on a
  server with a panel database, and a browser walk sets up two-factor on the
  role page, becomes a controller and opens Managed servers without signing
  out.
- Run the whole test collection against the published v3.0.17 tree on
  Ubuntu 22.04, AlmaLinux 9 and AlmaLinux 8 (Python 3.6); no test may fail
  that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.18 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 18, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
