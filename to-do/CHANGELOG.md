# CyberPanel fork changelog (master3395)

## 05/07/2026 — Dark mode legibility + SnappyMail permissions (v2.5.5-dev)

Repairs panel-wide dark mode and webmail data-dir permissions that caused unreadable
email pages and SnappyMail "Permission denied" on some hosts.

### Dark mode (#1804 stack wired)
- Load `cyberpanel-tokens.css` and `cyberpanel-dark.css` in `baseTemplate/index.html`
  (order: ui → tokens → harmonize → dark).
- Extended `cyberpanel-harmonize.css` with card surfaces, email config sidebar,
  disk usage badges, native select options, and Select2 dropdown rules.
- Fixed `listEmails.html`: `--text-primary` tokens and light-mode-only Edge select hack.
- Regenerated token/dark CSS via `tools/gen_tokens.py` and `tools/gen_dark.py`
  (ROOT path now resolves from repo location).

### SnappyMail / webmail
- New `scripts/utils/ensure-snappymail-permissions.sh`: `chown`/`chmod` for both
  `/usr/local/lscp/cyberpanel/rainloop/` and `snappymail/` plus public app tree.
- Migration, post-upgrade, and `fix-snappymail.sh` call the helper.

**Operator action:** pull `v2.5.5-dev`, run `collectstatic`, sync to `public/static`,
restart `lscpd`, or re-run upgrade post-tweak. Optional:
`bash /usr/local/CyberCP/scripts/utils/ensure-snappymail-permissions.sh --restart`

---

## 29/06/2026 — Sync upstream v2.4.8/stable fixes into v2.5.5-dev

Merged the 90 commits from `usmannasir/cyberpanel` `stable` (v2.4.8 line) into
`v2.5.5-dev-sync-v2.4.8` without resetting dev history. Version identity remains
**2.5.5-dev** (`version.txt`, install constants).

### Pulled from stable (highlights)
- Security audit fixes: command injection, SQLi, path traversal, privilege escalation
- AI Scanner unauthenticated file-access endpoint hardening
- Authentication on git webhook and AWS backup API endpoints
- SnappyMail strong admin password on install
- secMiddleware webmail false-positive fix (#1813)
- SSL manual reissue behavior (#1814)
- Remote transfer status regression fix
- `plogical/securityUtils.py` safe path helpers for remote transfers
- MailScanner installer script updates

### Preserved from v2.5.5-dev (master3395)
- Full 2.5.5-dev UI redesign and feature set (1811 dev-only commits)
- Custom firewall manager (`modifyRule`), filemanager safe-move/delete helpers
- Dev install/upgrade shell scripts and `plogical/upgrade.py` phpMyAdmin flow
- Imunify integration, origin dedupe middleware, plugin ACL changes

Branch: `v2.5.5-dev-sync-v2.4.8` → PR into `v2.5.5-dev`.
