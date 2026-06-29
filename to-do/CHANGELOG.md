# CyberPanel fork changelog (master3395)

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
