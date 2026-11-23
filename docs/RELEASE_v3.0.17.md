# CyberPanel v3.0.17 (build 17) — upgrade reliability and Multi-Server Manager wording

_Released 2026-11-24._

An upgrade on a busy OpenLiteSpeed server no longer stops at the
OpenLiteSpeed check because the previous OpenLiteSpeed generation is still
finishing connections, and the Multi-Server Manager pages say plainly what
to do. The changes are listed in CHANGELOG.md.

## Release gates

- On a server with the published v3.0.16 tree, leave a previous
  OpenLiteSpeed generation running (a slow client across a graceful
  restart): the published upgrade stops with code 78; the candidate upgrade
  waits, ends exactly that generation, completes, and the sites stay up.
- Anything else that is not the live OpenLiteSpeed tree still stops the
  upgrade (unit tests on a simulated process table).
- The whole Multi-Server Manager test collection passes on a server with a
  panel database (the pages' forms and addresses are unchanged).
- Run the whole test collection against the published v3.0.16 tree on
  Ubuntu 22.04, AlmaLinux 9 and AlmaLinux 8 (Python 3.6); no test may fail
  that passed there.

## Publish checklist

1. Publish the tested candidate as v3.0.17 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 17, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
