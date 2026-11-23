# CyberPanel v3.0.15 (build 15) — installer and first administrator

_Release candidate._

This release stops the sign-in page from creating an administrator with a
well-known password on a panel that has none, and makes the installer report
a panel that will not start at boot, or that was left stopped, instead of
calling the installation complete. The changes are listed in CHANGELOG.md.

## Release gates

- Install the candidate on clean Ubuntu and RPM servers, Python 3.6
  included: the installation ends complete with the panel's service enabled
  and running, the administrator signs in with the password given to the
  installer and the well-known password is refused.
- On a candidate server with its administrator removed, the sign-in page
  creates "admin" with a generated password stored only in
  /etc/cyberpanel/adminPass (mode 600), says where it is, and the
  well-known password is refused.
- Upgrade servers installed from the published v3.0.14 tree, on Ubuntu and
  on an RPM system; the panel answers and its administrator is unchanged.
- Run the whole test collection on Ubuntu and on RPM systems, Python 3.6
  included, against the same collection on the published v3.0.14 tree; no
  test may fail that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.15 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 15, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
