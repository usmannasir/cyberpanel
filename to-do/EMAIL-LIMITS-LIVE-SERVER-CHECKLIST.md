# Email Limits – Live Server Checklist (vs upstream v2.4.4)

## Upstream v2.4.4 behaviour

In [usmannasir/cyberpanel at v2.4.4](https://github.com/usmannasir/cyberpanel/tree/v2.4.4):

- **Template**: `mailServer/templates/mailServer/EmailLimits.html` exists and uses `ng-controller="EmailLimitsNew"` and `{$ … $}` bindings.
- **Routes**: `mailServer/urls.py` has `EmailLimits` and `SaveEmailLimitsNew`.
- **Controller**: The **`EmailLimitsNew` controller is not present** in `static/mailServer/mailServer.js`. Upstream `mailServer.js` ends at “List Emails” and has no `EmailLimitsNew` block.

So on a stock v2.4.4 install, the Email Limits page will show raw `{$ selectedEmail $}` and “Could not connect to server” because the Angular controller is never registered.

---

## How it is loaded in v2.4.4

1. **Base template** (`baseTemplate/templates/baseTemplate/index.html`) loads one script bundle:
   - `{% static 'mailServer/mailServer.js' %}?v={{ CP_VERSION }}`
   (in the “Additional Scripts” block at the bottom of the body.)

2. **Email Limits template** only provides content; it does **not** load any extra script in upstream. It expects `EmailLimitsNew` to come from `mailServer.js`, but that controller is missing in v2.4.4.

3. **Backend**: `mailServer/views.py` → `EmailLimits`, `SaveEmailLimitsNew`; `mailServer/mailserverManager.py` → `EmailLimits()`, `SaveEmailLimitsNew()`.

---

## Files that must be on the live server

Use the paths below relative to the CyberPanel app root (e.g. `/usr/local/CyberCP/` or your repo root). Django static files may be served from `STATIC_ROOT` after `collectstatic`; templates and Python files must be in the app directories.

### 1. Python / URLs / views (same as upstream + your tweaks)

| Path | Purpose |
|------|--------|
| `mailServer/urls.py` | Must include `EmailLimits` and `SaveEmailLimitsNew` routes. |
| `mailServer/views.py` | Must define `EmailLimits` and `SaveEmailLimitsNew` and call manager. |
| `mailServer/mailserverManager.py` | Must implement `EmailLimits()` and `SaveEmailLimitsNew()` and render `mailServer/EmailLimits.html` with `websiteList` and `status`. |

### 2. Template (must load the controller script)

| Path | Purpose |
|------|--------|
| `mailServer/templates/mailServer/EmailLimits.html` | Must extend `baseTemplate/index.html`, contain `ng-controller="EmailLimitsNew"`, and **include the script tag** that loads `emailLimitsController.js` at the top of `{% block content %}`. |

### 3. Base template (unchanged from upstream for Email Limits)

| Path | Purpose |
|------|--------|
| `baseTemplate/templates/baseTemplate/index.html` | Must load `{% static 'mailServer/mailServer.js' %}` in the same script block as other app JS (no `load_email_limits_controller` needed). |

### 4. Static files (at least one of the two options)

**Option A – Use main bundle (repo’s `mailServer.js` with controller)**

| Path | Purpose |
|------|--------|
| `static/mailServer/mailServer.js` | Must define `app` (e.g. `window.app` or `angular.module('CyberCP')`) at the top and register `app.controller('EmailLimitsNew', ...)`. |
| `mailServer/static/mailServer/mailServer.js` | Same as above if you use app static dirs. |

**Option B – Use standalone controller (recommended so it works even if `mailServer.js` is old)**

| Path | Purpose |
|------|--------|
| `static/mailServer/emailLimitsController.js` | Standalone script that registers `EmailLimitsNew` on the CyberCP module. |
| `mailServer/static/mailServer/emailLimitsController.js` | Same file under the app’s `static` dir. |

The Email Limits template in this repo loads `emailLimitsController.js` at the top of the content block, so the controller is registered on the Email Limits page even if the live server still has an older `mailServer.js` without `EmailLimitsNew`.

---

## Quick verification on the live server

Run from the CyberPanel app root (e.g. `/usr/local/CyberCP/`):

```bash
# 1. Template must contain the controller script and ng-controller
grep -l "emailLimitsController.js" mailServer/templates/mailServer/EmailLimits.html && \
grep -l "EmailLimitsNew" mailServer/templates/mailServer/EmailLimits.html && \
echo "Template OK" || echo "Template MISSING or WRONG"

# 2. Standalone controller script must exist (at least one location)
([ -f static/mailServer/emailLimitsController.js ] || [ -f mailServer/static/mailServer/emailLimitsController.js ]) && \
echo "emailLimitsController.js OK" || echo "emailLimitsController.js MISSING"

# 3. mailServer.js (if you rely on it for Email Limits) must define EmailLimitsNew
grep -q "EmailLimitsNew" static/mailServer/mailServer.js 2>/dev/null || grep -q "EmailLimitsNew" mailServer/static/mailServer/mailServer.js 2>/dev/null && \
echo "mailServer.js has EmailLimitsNew" || echo "mailServer.js has NO EmailLimitsNew (use emailLimitsController.js)"

# 4. Routes
grep -q "EmailLimits" mailServer/urls.py && echo "URLs OK" || echo "URLs MISSING"
```

After deploying, run:

```bash
python3 manage.py collectstatic --noinput
# Restart your app server (e.g. LiteSpeed / Gunicorn)
```

Then hard-refresh the Email Limits page (Ctrl+Shift+R).

---

## Summary

- **Upstream v2.4.4**: Email Limits template and routes exist; **controller is missing** from `mailServer.js`, so the page is broken by default.
- **This repo**: Adds `EmailLimitsNew` in `mailServer.js` and a standalone `emailLimitsController.js`, and the Email Limits template loads `emailLimitsController.js` so the page works even with an old `mailServer.js`.
- **Live server**: Ensure the template, URLs, views, manager, base template, and either the updated `mailServer.js` or `emailLimitsController.js` (or both) are present as in this checklist, then run `collectstatic` and restart the app.
