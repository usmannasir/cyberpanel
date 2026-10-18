# CyberPanel v3.0.8 (build 8) — Maintenance and Reliability

_Release candidate prepared 2026-10-18._

This release collects the maintenance fixes developed on v3.0.7 and reconciles
its history with stable through a normal merge. The detailed changes and known
runtime limitation are recorded in CHANGELOG.md.

## Release gates

- Run the installer, upgrade, authentication, SSL, backup, database, File Manager,
  website and webmail regression suites, separating opt-in/environment skips.
- Preserve the retained QA server's full deployed tree, configuration, SQL state
  and custom OpenLiteSpeed/module before any public-updater test.
- Verify a clean installation from the published candidate and the official
  updater on an owned retained panel. Compare installed commit and served assets.
- Verify authenticated website, database, backup/restore, File Manager,
  phpMyAdmin, webmail and service health. Preserve baseline failed-unit evidence.
- Do not publish announcements before installation/upgrade acceptance succeeds.

## Publish checklist

1. Publish the tested candidate as v3.0.8 and merge normally into stable.
2. Verify GitHub and Gitee release refs against the exact release commit.
3. Set https://cyberpanel.net/version.txt to exactly
   {"version":"3.0","build":8}.
4. Upgrade the retained validation server through the public default updater and
   repeat the relevant browser, endpoint, asset, service and exit-status checks.
5. Publish the build 8 public changelog and release article, then verify them
   through the public edge and the documented render checker.
6. Publish platform-specific announcements using the social engagement playbook
   and verified prior release formats; retain URLs and publication receipts.

If public installation or upgrade fails, restore the live pointer to build 7,
retain v3.0.8 for diagnosis and postpone announcements. Never overwrite divergent
historical Gitee branches to make the aggregate mirror job green.

## Important boundary

#1924 remains open. Tests reproduce ionCube/OPcache lint crashes across the
installed PHP 8.2, 8.3 and 8.4 combinations. No global extension/configuration
change is part of this release. Native external OAuth, vendor-package and OS
combinations must not be presented as tested beyond the recorded QA evidence.
