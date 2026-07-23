# Pull request: master3395/v2.5.5-dev → usmannasir/cyberpanel v2.5.5-dev

**Create PR (compare view):**  
https://github.com/usmannasir/cyberpanel/compare/v2.5.5-dev...master3395:cyberpanel:v2.5.5-dev?expand=1

Log in as **master3395**, click **Create pull request**, then paste title and body below.

---

## Title

```
v2.5.5-dev: dark mode, email UI fixes, SnappyMail permissions, UI static sync
```

## Body

```markdown
## Summary

Fork sync for `v2.5.5-dev` with panel-wide dark mode legibility, email list disk usage display, email forwarding UI repair, SnappyMail data-dir permissions, and automatic UI static sync on install/upgrade.

### Dark mode (#1804 stack)
- Wire `cyberpanel-tokens.css` and `cyberpanel-dark.css` in `baseTemplate/index.html` (load order: ui → tokens → harmonize → dark)
- Extend `cyberpanel-harmonize.css` for email pages, Select2 dropdowns, disk usage badges, and card surfaces
- Fix `listEmails.html` Edge select hack and text tokens for dark mode
- Regenerate token/dark CSS; fix `gen_tokens.py` / `gen_dark.py` to resolve repo ROOT dynamically

### Email
- **Disk usage badge:** replace Django `{{ record.DiskUsage }}` with `ng-bind="record.DiskUsage"` (was rendering as empty dark box)
- **Email forwarding UI:** fix perpetual loading spinner after fetch/create/delete in `mailServer.js`

### SnappyMail / webmail
- Add `scripts/utils/ensure-snappymail-permissions.sh` (chown both `rainloop/` and `snappymail/` data trees)
- Update migration, post-upgrade, and fix-snappymail scripts

### Upgrade / install
- Add `scripts/utils/sync-panel-ui-static.sh`; invoked from `09_sync.sh` and `10_post_tweak.sh` so theme CSS and `mailServer.js` reach `public/static` on every upgrade

### Recent commits (this session)
- `d0070180` fix(ui): wire #1804 dark mode stack and SnappyMail permissions
- `87b4ebb6` fix(email): stop forwarding UI stuck on loading spinner
- `589c89fd` fix(email): show disk usage in list emails badge
- `2343af58` fix(upgrade): sync UI static on every v2.5.5-dev install/upgrade

This PR also includes prior fork commits on `v2.5.5-dev` (132 commits vs upstream base): plugin ACL, Imunify integration, Cloudflare DNS/SSL fixes, listWebsites JS repair, CSRF Origin dedupe, and merged v2.4.8 security fixes.

## Test plan
- [ ] Toggle dark mode on Email → List Emails; domain dropdown and mail config sidebar readable
- [ ] Disk usage badges show values (e.g. `1.0 MB`), not empty boxes
- [ ] Email → Email Forwarding: spinner clears; forwardings list loads
- [ ] `/snappymail/` loads without rainloop data permission denied
- [ ] Run `cyberpanel_upgrade.sh -b v2.5.5-dev` or `sync-panel-ui-static.sh`; confirm theme CSS in `public/static`
- [ ] Spot-check Dashboard and Websites list in dark mode
```

---

## CLI (after `gh auth login` as master3395 with PR scope)

```bash
cd /usr/local/CyberCP
gh pr create \
  --repo usmannasir/cyberpanel \
  --base v2.5.5-dev \
  --head master3395:v2.5.5-dev \
  --title "v2.5.5-dev: dark mode, email UI fixes, SnappyMail permissions, UI static sync" \
  --body-file to-do/PR-UPSTREAM-v2.5.5-dev.md
```

Note: `gh` on the server failed with `Resource not accessible by personal access token` — use the web compare link or a PAT with fork/upstream PR permissions.
