# What Was in the Old cyberpanel-fix Repo – Pre-Removal Checklist

Before removing `/home/cyberpanel-fix-backup-20260202`, verify the merged repo has everything you need.

---

## 1. Files ONLY in cyberpanel-repo (not in old fix) ✅

These are in the merged repo and were not in the old fix:

| File | Purpose |
|------|---------|
| `commit_and_push.sh`, `commit_changes.py`, `push_fix.py`, `push_fix.sh` | Dev/utility scripts |
| `fix_todo_git.py`, `remove_todo.py`, `remove_todo_from_git.sh` | Git helpers |
| `olves issue -1654: Hostname SSL setup...` | Patch file (typo in filename) |
| `pluginHolder/patreon_verifier.py.bak`, `plugin_access.py.bak` | Backups |
| `pluginHolder/templates/pluginHolder/plugins.html.backup` | Template backup |
| `static/userManagment/modifyUser.html` | UI change |
| `to-do/PLUGIN-DEFAULT-REMOVAL-2026-02-01.md` | Notes |
| `to-do/REPO-MERGE-2026-02-02.md` | Merge notes |

**Action:** None. These are already in the merged repo.

---

## 2. Files COPIED from old fix into repo ✅

These were only in the old fix and were copied into repo during the merge:

| File | Purpose |
|------|---------|
| `cyberpanel_clean.sh` | Clean install script |
| `cyberpanel_complete.sh` | Complete install script |
| `cyberpanel_simple.sh` | Simple install script |
| `cyberpanel_standalone.sh` | Standalone install script |
| `fix_installation_issues.sh` | Installation fixes |
| `install_phpmyadmin.sh` | phpMyAdmin installer |
| `simple_install.sh` | Simple installer |
| `INSTALLER_SUMMARY.md` | Installer docs |
| `UNIVERSAL_OS_COMPATIBILITY.md` | OS compatibility docs |
| `to-do/MARIADB_INSTALLATION_FIXES.md` | MariaDB fixes |

**Action:** Confirm these exist in `/home/cyberpanel-repo/`.

---

## 3. Files that DIFFER – repo is the intended version

The merged repo keeps the **cyberpanel-repo** versions. Old fix had older or different logic.

### CyberCP/settings.py
- **Repo:** `emailMarketing` is commented out (install via Plugin Store)
- **Old fix:** `emailMarketing` was in `INSTALLED_APPS`

**Check:** Plugin Store for emailMarketing works; no need for it in core install.

### CyberCP/urls.py
- **Repo:** `path('emailMarketing/', ...)` is commented out
- **Old fix:** `path('emailMarketing/', ...)` was active

**Check:** Same as above; emailMarketing via Plugin Store.

### plogical/mailUtilities.py
- **Repo:** DNS fallback logic – falls back to **local DNS** when external API fails
- **Old fix:** Returns empty `[]` when external API fails; no local fallback

**Check:** Hostname SSL / rDNS works when cyberpanel.net API is down or unreachable.

### emailMarketing/meta.xml
- **Repo:** version `1.0.1`, category `Email`
- **Old fix:** version `1.0.0`

### examplePlugin/meta.xml
- **Repo:** version `1.0.1`, category `Utility`
- **Old fix:** version `1.0.0`

**Check:** Plugin Store shows correct versions and categories.

---

## 4. PluginHolder / Plugin Store (in repo)

The merged repo has:

- Collapsible help sections
- Freshness badges (NEW/Stable/Unstable/STALE)
- Activate All / Deactivate All
- Updated categories and premium docs
- Version 2.1.0 in the help footer

**Check:** `/plugins/help/` and `/plugins/installed` behave as expected.

---

## 5. Quick verification commands

```bash
# Copied files exist
ls -la /home/cyberpanel-repo/cyberpanel_clean.sh \
       /home/cyberpanel-repo/fix_installation_issues.sh \
       /home/cyberpanel-repo/install_phpmyadmin.sh

# Symlink works
ls -la /home/cyberpanel-fix
# Should show: cyberpanel-fix -> cyberpanel-repo

# Live deployment
ls -la /usr/local/CyberCP/pluginHolder/templates/pluginHolder/help.html
# Should have collapsible sections and version 2.1.0
```

---

## 6. Safe to remove when

- [ ] Plugin Store loads and filters work
- [ ] Plugin Development Guide (help) shows collapsible sections and 2.1.0
- [ ] Hostname SSL / rDNS works (or you accept no local DNS fallback)
- [ ] emailMarketing is installed via Plugin Store, not core (if used)
- [ ] Install scripts (`cyberpanel_clean.sh`, etc.) are present and used as needed

---

## Remove backup

```bash
rm -rf /home/cyberpanel-fix-backup-20260202
```

---

**Created:** 2026-02-02
