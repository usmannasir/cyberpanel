# CyberCP git pull conflicts on v2.5.5-dev (server at /usr/local/CyberCP)

## Why Git asks to "remove" or "move" files

When you run `git pull --ff-only origin v2.5.5-dev` in `/usr/local/CyberCP`, Git can block for two reasons:

### 1. Modified files (would be overwritten by merge)

- **Meaning:** You have **local changes** in tracked files (e.g. `CyberCP/settings.py`, `baseTemplate/views.py`, …). The remote branch also changed those files. Git will not overwrite your working tree without you deciding what to do with your changes.
- **So:** You must either **commit** or **stash** (or discard) those local changes before the pull can apply.

### 2. Untracked files (would be overwritten by merge)

- **Meaning:** You have **untracked** files/dirs at paths where the **incoming** branch (v2.5.5-dev) **adds** files. For example: `panelAccess/`, `baseTemplate/static/baseTemplate/assets/mobile-responsive.css`, `sql/create_ftp_quotas.sql`, etc. Git will not overwrite untracked content, so it refuses to merge and says "Please move or remove them."
- **So:** You must **move or remove** those untracked paths so Git can write the version from the repo there.

## Are all these files on v2.5.5-dev?

- **Yes.** The branch `v2.5.5-dev` on `master3395/cyberpanel` contains:
  - All the modified paths (canonical versions).
  - All the "untracked" paths (e.g. `panelAccess/`, `mobile-responsive.css`, `readability-fixes.css`, `emailLimitsController.js`, `create_ftp_quotas.sql`, `firewall/migrations/0001_initial.py`, `install/ols_binaries_config.py`, etc.).
- So the **repo** is the source of truth; the server just needs to be brought in line with it. You can confirm by cloning fresh: `git clone -b v2.5.5-dev https://github.com/master3395/cyberpanel.git` and listing those paths.

## Safe way to sync the server to v2.5.5-dev

If you are **ok discarding all local and untracked changes** in `/usr/local/CyberCP` and making it exactly match `origin/v2.5.5-dev`:

```bash
cd /usr/local/CyberCP

# Optional: backup current state
tar -czf /root/cybercp-backup-before-sync-$(date +%Y%m%d-%H%M%S).tar.gz .

# Reset tracked files to current HEAD and remove untracked/ignored files
git fetch origin
git checkout v2.5.5-dev
git reset --hard origin/v2.5.5-dev
git clean -fd

# Ensure you're up to date (should already be after reset)
git pull --ff-only origin v2.5.5-dev
```

After this, **Current** in Version Management should match **Latest** (commit `c24f067e` or whatever is the tip of `origin/v2.5.5-dev`).

## If you need to keep local changes

- **Tracked changes:** Stash first, then pull, then re-apply:
  ```bash
  cd /usr/local/CyberCP
  git stash push -m "before sync v2.5.5-dev"
  # move or remove the untracked paths listed by Git (e.g. backup then delete)
  git pull --ff-only origin v2.5.5-dev
  git stash pop
  ```
- **Untracked files:** Back them up to another directory (e.g. `/root/cybercp-untracked-backup/`) before removing or moving them, then run the pull.

## Upgrade script sync step

The upgrade script’s `Sync_CyberCP_To_Latest()` runs `git fetch`, `checkout`, and `git pull --ff-only`. If the server has local or untracked conflicts like above, that pull will keep failing until you either:

- Run the "safe way" (reset + clean) on the server once, or  
- Change the script to use `git reset --hard origin/$Branch_Name` and `git clean -fd` so the install is forced to match the remote (only do this if you intend the install to always mirror the repo with no local edits).
