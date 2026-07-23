# CyberPanel v2.4.9 (build 9) — Release Notes

_Released 2026-07-23._

This is a **maintenance release focused on security and reliability** — no UI
changes, safe to upgrade. See `CHANGELOG.md` (`## v2.4.9`) for the complete list.

## Announcement blurb (forum / site)

**CyberPanel v2.4.9 (build 9) is out — a security & reliability maintenance release.**

**🔒 Security**
- Fixed two cross-tenant backup vulnerabilities (IDOR): one let any user
  cancel/delete another tenant's backups, another let any user read/delete/restore
  another tenant's incremental backups. Both were publicly reported —
  **upgrading is recommended.**
- Hardened command/cron handling, fixed command-injection / SQLi / path-traversal /
  privilege-escalation issues, added authentication to previously-open git-webhook,
  AWS-backup and AI-Scanner endpoints, and strengthened install-time password
  generation.

**🔐 SSL**
- **Renewals now actually apply.** Renewed certificates are copied to the served
  location and LiteSpeed is reloaded, and acme.sh auto-renewals now self-apply —
  fixing sites silently stuck on an old/expiring certificate.

**💾 Backups & restore**
- Restored/migrated sites are correctly re-owned by the domain user —
  **fixes WordPress asking for FTP credentials after a restore.**
- Website backups now fail loudly instead of silently producing an archive with no
  database.

**⬆️ Upgrade & install**
- The upgrade script no longer mistakes a healthy install for a corrupt one and
  triggers a destructive recovery re-clone.
- Upgrade downloads are validated (clean handling of GitHub rate-limits), PHP 8.5 no
  longer crashes the subdomain list, and OWASP CRS installs from the correct URL.

**🌐 Domain aliases**
- Alias creation, listing, SSL, and delete now work end-to-end.

**⚙️ Stack**
- Updated CyberPanel-OLS stack (core 2.5.1 / module 2.7.5 / mod_security 2.5.1),
  which resolves the 4xx-segfault / Cloudflare 520 storm.

Full changelog: https://cyberpanel.net/KnowledgeBase/home/change-logs/

## Issues fixed in this release

#1847, #1835, #1829, #1828, #1823, #1738, #1726, #1720, #1715, #1676, #1814,
#1816, #1813, #1811, #1808, #1806, #1804, #1800.

## Publish checklist (platform dev)

The version bump lives in this branch; the rollout is triggered by the website
pointer. Do these **in order**:

1. **Push the release branch**
   ```bash
   git checkout v2.4.9
   git push origin v2.4.9
   ```
2. **Update the version pointer** served at `https://cyberpanel.net/version.txt`
   to exactly (no trailing newline — the installer parses it with `sed`):
   ```
   {"version":"2.4","build":9}
   ```
   This is the switch that rolls installs/upgrades onto `v2.4.9`; the in-repo
   `version.txt` only makes the panel *report* 2.4.9.
3. **Publish the changelog** (`## v2.4.9` from `CHANGELOG.md`) to
   `https://cyberpanel.net/KnowledgeBase/home/change-logs/`.

**Order matters:** push the branch (1) before flipping the site pointer (2), or
upgrade runs will try to fetch a branch that doesn't exist yet.

**Rollback:** set `cyberpanel.net/version.txt` back to
`{"version":"2.4","build":8}` — upgrades immediately fall back to `v2.4.8`. No
code rollback needed.
