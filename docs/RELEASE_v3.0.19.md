# CyberPanel v3.0.19 (build 19) — Multi-Server Manager in three steps

_Released 2026-11-25._

Connecting a server to a Multi-Server Manager controller takes three steps:
make one server the controller, connect each other server to it with the
controller's address and the password, and paste the code on the controller.
Two-factor login is needed only on the controller. The changes are listed in
CHANGELOG.md.

## Release gates

- Multi-Server Manager and sign-in test modules pass on a server with a
  panel database, with no test that passed on the published v3.0.18 tree
  failing.
- Browser walk on real servers: a server is made controller with two-factor
  set up on the role page; another server connects in one form; the code is
  pasted on the controller and the server shows Connected at once; its panel
  opens from the controller. Mixed versions in both directions: a 3.0.19
  controller with a 3.0.18 managed server (number shown and approved there),
  a 3.0.18 controller with a 3.0.19 managed server (one "check now").
- Run the whole test collection against the published v3.0.18 tree on
  Ubuntu 22.04, AlmaLinux 9 and AlmaLinux 8 (Python 3.6); no test may fail
  that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.19 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 19, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
