# CyberPanel v3.0.12 (build 12) — security and reliability

_Released 2026-11-22._

This release hardens databases, Docker sites, the PHP manager, the AI Scanner
and the panel's request handling, and adds a link to where a Multi-Server
Manager licence is bought. An upgrade makes the database grants of earlier
releases exact, moves AI Scanner backups of earlier releases out of served
folders and lists n8n sites that were deployed the earlier way. The changes
are listed in CHANGELOG.md.

## Release gates

- Run the whole test collection on Ubuntu and on an RPM system with Python
  3.6, against the same collection on the published v3.0.11 tree; no test may
  fail that passed there.
- Run the database changes against MariaDB 10.3, 10.6 and 11 and MySQL 8.0
  with and without partial_revokes: grant repair, dump import with triggers,
  views and routines, deletion, phpMyAdmin account statements.
- Upgrade servers installed from the published v3.0.11 tree, on Ubuntu and on
  an RPM system with Python 3.6, that hold a database granted the earlier
  way: afterwards its user reaches its own database and no similarly named
  one, phpMyAdmin opens for an administrator and for a user who is not one,
  a website's PHP version changes, and the panel answers.
- Install the candidate on clean servers. Through the panel's root helper:
  the AI Scanner file operations work for a website and stay inside it, and a
  Docker site is deployed and deleted for its owner only.
- Apply the [OpenLiteSpeed upgrade release gate](../CONTRIBUTING.md#openlitespeed-upgrade-release-gate):
  this release changes the upgrader.

## Publish checklist

1. Publish the tested candidate as v3.0.12 and merge normally into stable.
2. Verify the release refs against the exact release commit.
3. Move the version pointer to build 12, clear both caches and compare bytes.
4. Run the public delivery gate, then sign the release file.
