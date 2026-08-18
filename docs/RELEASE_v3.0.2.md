# CyberPanel v3.0.2 (build 2) — Release Notes

_Released 2026-08-18._

This release **adds Hermes Agent as a one-click Docker application** and rolls up
the fixes that landed on the `v3.0.1` branch after its initial build. See
`CHANGELOG.md` (`## v3.0.2`) for the complete list.

## Announcement blurb (forum / site)

**CyberPanel v3.0.2 (build 2) is out — one-click Hermes Agent hosting, plus a
batch of fixes.**

**🤖 Host your own Hermes Agent**
- Deploy Hermes Agent from Docker Sites the same way you deploy n8n: pick a
  domain, set CPU and RAM, choose the dashboard login, and CyberPanel builds the
  container, the reverse proxy and the SSL-terminated dashboard for you.
- The agent keeps its state in its own data volume and needs no database.
- The dashboard is reachable only through your domain over HTTPS, never on an
  open port, and it is password-protected from the first request.
- Add your model provider API key from inside the dashboard, CyberPanel never
  stores it.

**🔧 Fixes**
- Git repositories with a dot in the name (`repo.ltd`) can be attached again.
- The Email Marketing page renders its lists instead of staying empty.
- Logging out of phpMyAdmin ends the session instead of leaving a blank page.
- Docker site creation starts with valid defaults and no clipped dropdowns.

**⬆️ Rolled up from v3.0.1**
- File-manager downloads are staged in a private directory owned by the service
  account, no loosened permissions on the panel home.
- Local database credentials are repaired during upgrade, and a failed upgrade
  reports partial state instead of claiming the old build is still running.
- Scheduled local backups validate their destination and apply retention.
- Web Terminal survives upgrades and runtime rebuilds and honours a custom SSH
  port.
- Ubuntu 26 installer detection completed; login sessions persist correctly.

Full changelog: https://cyberpanel.net/KnowledgeBase/home/change-logs/

## Issues fixed in this release

#1716, #1707, #1680, #1752, #1894, #1891.

## Publish checklist (platform dev)

The version bump lives in this branch; the rollout is triggered by the website
pointer. Do these **in order**:

1. **Push the release branch**
   ```bash
   git checkout v3.0.2
   git push origin v3.0.2
   ```
2. **Update the version pointer** served at `https://cyberpanel.net/version.txt`
   to exactly (no trailing newline — the installer parses it with `sed`):
   ```
   {"version":"3.0","build":2}
   ```
   This is the switch that rolls installs/upgrades onto `v3.0.2`; the in-repo
   `version.txt` only makes the panel *report* 3.0.2.
3. **Publish the changelog** (`## v3.0.2` from `CHANGELOG.md`) to
   `https://cyberpanel.net/KnowledgeBase/home/change-logs/`.
4. **Announce on the Facebook Page** following
   `marketing_docs/FACEBOOK_PAGE_POSTING_WORKFLOW.md` — photo post, one CTA,
   one URL. Announce only after step 2, so the version people are told about is
   the version they actually receive.

**Order matters:** push the branch (1) before flipping the site pointer (2), or
upgrade runs will try to fetch a branch that doesn't exist yet.

**Rollback:** set `cyberpanel.net/version.txt` back to
`{"version":"3.0","build":1}` — upgrades immediately fall back to `v3.0.1`. No
code rollback needed.

## Hermes Agent notes for support

- Hermes needs at least 2GB RAM for the application container. The default
  Docker package ships with 1024MB, so an administrator must raise the package
  before the first Hermes site can be created.
- The dashboard credentials are the admin username and password entered on the
  creation form. Hermes refuses to start without them, by design.
- The agent has a shell inside its container. It is resource-capped like any
  other Docker site, and outbound mail ports remain blocked by the node policy.
