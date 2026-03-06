# Release notes – v2.5.5-dev

## Issue SSL and SSL form (install / upgrade / downgrade)

### Changes included

1. **Issue SSL**
   - **Main domain:** CONFIGURATIONS section has an **Issue SSL** tile next to **Add SSL**. Clicking it obtains or restores Let's Encrypt SSL for the main site (calls `POST /manageSSL/issueSSL` with `virtualHost`; path is resolved from DB).
   - **Child domains:** On each child domain page (e.g. **launchChild**), CONFIGURATIONS has **Add SSL** and **Issue SSL**. Issue SSL uses `issueSSL(childDomainName, childPath)` and the same backend endpoint.
   - **Backend:** `manageSSL/views.py` `issueSSL()` supports both main and child: it looks up `ChildDomains` first, then `Websites`, and uses the appropriate path and admin email.

2. **SSL form close (X) button**
   - **Main domain** (`websiteFunctions/templates/websiteFunctions/website.html`): SSL form close button is centered in the row, uses `ssl-form-close-btn` and Font Awesome `fa-times`, with CSS for centered icon.
   - **Child domain** (`websiteFunctions/templates/websiteFunctions/launchChild.html`): Same centered close button for the Add SSL form.

3. **Files touched**
   - `websiteFunctions/templates/websiteFunctions/website.html` – Issue SSL tile, SSL form close button + `.ssl-form-close-btn` CSS.
   - `websiteFunctions/templates/websiteFunctions/launchChild.html` – Issue SSL tile, SSL form close button.
   - `manageSSL/views.py` – `issueSSL` (unchanged logic; already supports main and child).
   - `websiteFunctions/static/websiteFunctions/websiteFunctions.js` – multiple controllers already define `issueSSL(virtualHost)` or `issueSSL(childDomain, path)` posting to `/manageSSL/issueSSL`.

### Install

- New installs clone the repo (e.g. `master3395/cyberpanel`) and checkout the chosen branch (e.g. `v2.5.5-dev`). All of the above files are in the repo, so **Issue SSL** and the SSL form close button are present after install.

### Upgrade

- Upgrade removes `/usr/local/CyberCP`, clones the repo, and checks out the target branch. Only a small set of critical files are restored from backup (e.g. `settings.py`, `.git/config`, custom dirs, Imunify); **website templates and static JS are not in the backup list**, so the new clone’s `website.html`, `launchChild.html`, and `websiteFunctions.js` are kept. After upgrade, **Issue SSL** and the updated SSL form are active.

### Downgrade

- Downgrade is the same flow with a different branch. If you switch to an older branch that does not include the Issue SSL tile or the new close button, the UI will reflect that branch. The backend endpoint `/manageSSL/issueSSL` exists in upstream CyberPanel, so older branches that still have the route will continue to work; no extra compatibility logic is required for downgrade.

### Version

- `version.txt`: `{"version":"2.5.5","build":"dev"}` (or as set in repo).
- `plogical/upgrade.py`: `VERSION = '2.5.5'`, `BUILD = 5` (or as configured); used for DB version and packaging.

---

**Summary:** Issue SSL and the SSL form close button are in the v2.5.5-dev codebase and work with install, upgrade, and downgrade. Push this repo to GitHub and use branch `v2.5.5-dev` (or your chosen tag) for deployments.
