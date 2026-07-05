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

## 06/07/2026 — List Emails disk usage badge empty (v2.5.5-dev)

`listEmails.html` used Django `{{ record.DiskUsage }}` inside an Angular table. Django
stripped it before render, so the badge was an empty dark box. Switched to
`ng-bind="record.DiskUsage"` and improved dark-mode badge contrast.

**Upgrade/install:** `scripts/utils/sync-panel-ui-static.sh` runs from `09_sync.sh` and
`10_post_tweak.sh` so theme CSS and `mailServer.js` reach `public/static` on every
v2.5.5-dev install or upgrade.

---

Fixed `mailServer.js` `emailForwarding` controller: `forwardLoading` stayed `true`
after successful fetch/create/delete, so the forwarding page showed a perpetual
spinner even when Postfix rules were saved. Server-side forwarding verified working
(local test: `abuse@newstargeted.com` delivers to mailbox and forwards to `info@`).

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
