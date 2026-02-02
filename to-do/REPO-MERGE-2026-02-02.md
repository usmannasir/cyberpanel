# CyberPanel Repo Merge – 2026-02-02

## Summary

`cyberpanel-repo` and `cyberpanel-fix` have been merged into a single working directory.

## What Was Done

1. **Unique files copied from cyberpanel-fix into cyberpanel-repo:**
   - `cyberpanel_clean.sh`
   - `cyberpanel_complete.sh`
   - `cyberpanel_simple.sh`
   - `cyberpanel_standalone.sh`
   - `fix_installation_issues.sh`
   - `install_phpmyadmin.sh`
   - `simple_install.sh`
   - `INSTALLER_SUMMARY.md`
   - `UNIVERSAL_OS_COMPATIBILITY.md`
   - `to-do/MARIADB_INSTALLATION_FIXES.md`

2. **cyberpanel-fix backup:** Renamed to `cyberpanel-fix-backup-20260202`

3. **Symlink created:** `cyberpanel-fix` → `cyberpanel-repo`
   - Paths like `/home/cyberpanel-fix/` now resolve to `/home/cyberpanel-repo/`

## Single Source of Truth

Use **`/home/cyberpanel-repo`** (or `/home/cyberpanel-fix` via symlink) for all CyberPanel development and deployment.

## Backup Location

The previous cyberpanel-fix tree is preserved at:
`/home/cyberpanel-fix-backup-20260202`

You can remove it after confirming everything works:
```bash
rm -rf /home/cyberpanel-fix-backup-20260202
```
